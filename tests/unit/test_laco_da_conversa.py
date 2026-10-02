# tests/unit/test_laco_da_conversa.py
"""
O laço do assistente (`conversar`), quadro a quadro e efeito a efeito.

Caracterização: prende a sequência de quadros que o SSE entrega à Home e ao
editor (tipos, ordem, conteúdo) e os efeitos que acontecem entre um quadro e o
seguinte — a chamada ao modelo, o registro de uso, a cobrança da cota, o gancho
que fecha o turno, as ferramentas —, além do que o laço loga.

Os quadros são PUXADOS: nada acontece antes de quem consome pedir o quadro
seguinte. É isso que faz o cancelamento pelo cliente (a aba fechada, que
cancela a tarefa do SSE) parar o laço exatamente onde ele está — os testes do
fim do arquivo prendem o que roda e o que não roda nesse caso.
"""
from __future__ import annotations

import asyncio
import gc
import json
import weakref
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import cotas
from app.mcp.escopo import ESCOPOS_DO_EDITOR
from app.services import assistente_config_service, teto_do_assistente, uso_service
from app.services import assistente_service as cs
from app.services import assistente_superficie as agente
from app.services import openrouter

from ._mcp_harness import RedisFalso, escopo_falso

pytestmark = pytest.mark.asyncio

MODELO = "fornecedor/modelo-de-teste"
TETO = 50_000
PEDIDO = {"role": "user", "content": "monta um fluxo de buffer"}


def _uso(entrada, saida, cache_leitura=0, raciocinio=0, custo=0.0):
    return {"entrada": entrada, "saida": saida, "cache_leitura": cache_leitura,
            "cache_escrita": 0, "raciocinio": raciocinio, "custo": custo}


def _resposta(blocos, parada="stop", uso=None):
    return openrouter.Resposta(blocos=list(blocos), parada=parada, uso=uso or _uso(100, 20))


def _texto(txt):
    return {"type": "text", "text": txt}


def _chamada(nome, argumentos, ident):
    return {"type": "tool_use", "id": ident, "name": nome, "input": argumentos}


class _Modelo:
    """O modelo, roteirizado: um roteiro por volta — `Delta`s, a `Resposta`, e
    onde o roteiro trava (`asyncio.Event`) ou quebra (exceção)."""

    def __init__(self, linha, voltas):
        self.linha = linha
        self._voltas = list(voltas)
        self.pedidos: list[dict] = []

    async def transmitir(self, **kw):
        self.pedidos.append(kw)
        self.linha.append(("modelo", len(kw["conversa"])))
        roteiro = self._voltas.pop(0)
        try:
            for passo in roteiro:
                if isinstance(passo, BaseException):
                    raise passo
                if isinstance(passo, asyncio.Event):
                    await passo.wait()
                    continue
                yield passo
        finally:
            self.linha.append(("stream fechado",))


class _Servidor:
    """O servidor MCP em processo, anotando cada chamada na linha do tempo."""

    def __init__(self, linha, ferramentas, resultados=None):
        self.linha = linha
        self._ferramentas = list(ferramentas)
        self._resultados = dict(resultados or {})

    async def list_tools(self):
        self.linha.append(("list_tools",))
        return [
            SimpleNamespace(name=n, description=f"faz {n}", input_schema={"type": "object", "properties": {}})
            for n in self._ferramentas
        ]

    async def call_tool(self, nome, argumentos, context=None):
        ident = getattr(context, "_ferramenta_id", None)
        self.linha.append(("call_tool", nome, ident))
        acao = self._resultados.get(nome, f"{nome} ok")
        if isinstance(acao, BaseException):
            raise acao
        texto = await acao(context) if callable(acao) else acao
        self.linha.append(("call_tool fim", nome, ident))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)], structured_content=None,
                               is_error=False)


@pytest.fixture
def linha(monkeypatch):
    """A linha do tempo, com a preparação, o uso, a cota e o log anotados."""
    linha: list = []

    async def _teto_de(user_id, *, db=None, redis=None):
        linha.append(("teto_de", user_id))
        return TETO

    verificar = cotas.verificar_tokens_do_assistente
    cobrar = cotas.cobrar_tokens_do_assistente

    async def _verificar(redis, user_id, *, teto):
        linha.append(("verificar_tokens", user_id, teto))
        return await verificar(redis, user_id, teto=teto)

    async def _cobrar(redis, user_id, tokens):
        acumulado = await cobrar(redis, user_id, tokens)
        linha.append(("cobrar", tokens, acumulado))
        return acumulado

    async def _modelo_em_uso(*, db=None, redis=None):
        linha.append(("modelo_em_uso",))
        return MODELO

    async def _registrar_volta(**kw):
        linha.append(("registrar_volta", kw))

    monkeypatch.setattr(teto_do_assistente, "teto_de", _teto_de)
    monkeypatch.setattr(cotas, "verificar_tokens_do_assistente", _verificar)
    monkeypatch.setattr(cotas, "cobrar_tokens_do_assistente", _cobrar)
    monkeypatch.setattr(assistente_config_service, "modelo_em_uso", _modelo_em_uso)
    monkeypatch.setattr(uso_service, "registrar_volta", _registrar_volta)
    for nivel in ("debug", "info", "warning", "error", "exception"):
        monkeypatch.setattr(
            cs.logger, nivel, lambda msg, *args, _nivel=nivel, **_kw: linha.append(("log", _nivel, msg % args)),
        )
    return linha


def _gancho(linha):
    async def _fechar_turno(conversa):
        linha.append(("gancho", len(conversa), conversa[-1]["role"]))

    return _fechar_turno


async def _consumir(gerador, linha):
    async for evento in gerador:
        linha.append(("quadro", evento.tipo, evento.dados))


def _conversar(linha, *, servidor, modelo, redis=None, **kw):
    return cs.conversar(
        escopo=escopo_falso(scopes=ESCOPOS_DO_EDITOR),
        transcrito=kw.pop("transcrito", [PEDIDO]),
        servidor=servidor,
        cliente=modelo,
        redis=redis,
        **kw,
    )


PREPARO = [("teto_de", "usr-1"), ("verificar_tokens", "usr-1", TETO), ("modelo_em_uso",), ("list_tools",)]


def _registro(entrada, saida, superficie="editor"):
    """O que `uso_service.registrar_volta` recebe numa volta."""
    return ("registrar_volta", {
        "user_id": "usr-1", "modelo": MODELO, "superficie": superficie, "entrada": entrada,
        "saida": saida, "cache_leitura": 0, "raciocinio": 0, "custo_usd": 0.0,
    })


def _balanco(voltas, tokens, superficie="editor"):
    return ("log", "info", f"Assistente: {voltas} volta(s), {tokens} tokens, US$ 0.0000 "
                           f"(usuário usr-1, superfície {superficie}).")


def _resultado(ident, texto, erro=False):
    return {"type": "tool_result", "tool_use_id": ident, "content": texto, "is_error": erro}


def _uso_total(entrada, saida):
    return {"entrada": entrada, "saida": saida, "cache_leitura": 0, "cache_escrita": 0,
            "raciocinio": 0, "custo": 0.0, "total": entrada + saida}


async def _esperar(condicao, prazo_s=2.0):
    fim = asyncio.get_running_loop().time() + prazo_s
    while not condicao():
        assert asyncio.get_running_loop().time() < fim, "condição não ficou verdadeira a tempo"
        await asyncio.sleep(0.005)


# ── O caminho feliz, nas duas superfícies ─────────────────────────────────────


DEFINICAO = {"nodes": [{"id": "n1"}], "edges": []}
VALIDOU = '{"ok": true, "error_count": 0, "warning_count": 1}'


async def test_editor_quadro_a_quadro(linha):
    """Quatro voltas: lote paralelo, pista em fila (desenho + execução com
    progresso), lote com uma ferramenta barrada, e o texto final."""
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = 100

    async def _rodando(ctx):
        await ctx.report_progress(1, 2, "buffer: completed (0.3s)")
        return '{"run_id": "r-1"}'

    servidor = _Servidor(
        linha,
        ["search_nodes", "describe_node", "validate_workflow", "run_workflow", "create_workflow"],
        {"run_workflow": _rodando, "validate_workflow": VALIDOU},
    )
    volta1 = [_texto("Vou montar"), _chamada("search_nodes", {"query": "buffer"}, "tu-1"),
              _chamada("describe_node", {"name": "Buffer"}, "tu-2")]
    volta2 = [_chamada(cs.NOME_DO_DESENHO, {"definition": DEFINICAO, "nota": " liguei o buffer "}, "tu-3"),
              _chamada("run_workflow", {"workflow_id": "wf-1"}, "tu-4")]
    volta3 = [_chamada("validate_workflow", {"definition": DEFINICAO}, "tu-5"),
              _chamada("create_workflow", {"name": "x"}, "tu-6")]
    modelo = _Modelo(linha, [
        [openrouter.Delta("pensando", "preciso do catálogo"), openrouter.Delta("texto", "Vou montar"),
         _resposta(volta1, "tool_calls")],
        [_resposta(volta2, "tool_calls", _uso(200, 30))],
        [_resposta(volta3, "tool_calls", _uso(300, 40))],
        [openrouter.Delta("texto", "Pronto."), _resposta([_texto("Pronto.")], "stop", _uso(400, 50))],
    ])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, redis=redis,
                               ao_fechar_turno=_gancho(linha)), linha)

    desenhado = ("Desenhado no canvas: 1 nó(s) e 0 aresta(s). A pessoa está vendo agora. Continue montando "
                 "e chame de novo a cada mudança; valide com `validate_workflow` quando o desenho estiver completo.")
    transcrito = [
        PEDIDO,
        {"role": "assistant", "content": volta1},
        {"role": "user", "content": [_resultado("tu-1", "search_nodes ok"), _resultado("tu-2", "describe_node ok")]},
        {"role": "assistant", "content": volta2},
        {"role": "user", "content": [_resultado("tu-3", desenhado), _resultado("tu-4", '{"run_id": "r-1"}')]},
        {"role": "assistant", "content": volta3},
        {"role": "user", "content": [_resultado("tu-5", VALIDOU), _resultado("tu-6", cs.MENSAGEM_DO_PORTAO, True)]},
        {"role": "assistant", "content": [_texto("Pronto.")]},
    ]
    assert linha == PREPARO + [
        # Volta 1: raciocínio e texto ao vivo; o lote paralelo é anunciado inteiro.
        ("modelo", 1),
        ("quadro", "pensando", {"texto": "preciso do catálogo"}),
        ("quadro", "texto", {"texto": "Vou montar"}),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, 220),
        ("quadro", "cota", {"gasto": 220, "teto": TETO}),
        ("gancho", 2, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "search_nodes", "argumentos": {"query": "buffer"}}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "describe_node", "argumentos": {"name": "Buffer"}}),
        ("call_tool", "search_nodes", "tu-1"),
        ("call_tool fim", "search_nodes", "tu-1"),
        ("call_tool", "describe_node", "tu-2"),
        ("call_tool fim", "describe_node", "tu-2"),
        ("quadro", "ferramenta_fim", {"id": "tu-1", "nome": "search_nodes", "erro": False}),
        ("quadro", "ferramenta_fim", {"id": "tu-2", "nome": "describe_node", "erro": False}),
        ("gancho", 3, "user"),
        # Volta 2: com uma ferramenta local no lote, a volta roda em fila.
        ("modelo", 3),
        ("stream fechado",),
        _registro(200, 30),
        ("cobrar", 230, 450),
        ("quadro", "cota", {"gasto": 450, "teto": TETO}),
        ("gancho", 4, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-3", "nome": cs.NOME_DO_DESENHO,
                                  "argumentos": {"definition": {"__campos__": 2}, "nota": " liguei o buffer "}}),
        ("quadro", "ferramenta_fim", {"id": "tu-3", "nome": cs.NOME_DO_DESENHO, "erro": False}),
        ("quadro", "proposta", {"definicao": DEFINICAO, "nos": 1, "arestas": 0, "desenhar": True,
                                "nota": "liguei o buffer"}),
        ("quadro", "ferramenta", {"id": "tu-4", "nome": "run_workflow", "argumentos": {"workflow_id": "wf-1"}}),
        ("call_tool", "run_workflow", "tu-4"),
        ("call_tool fim", "run_workflow", "tu-4"),
        ("quadro", "progresso", {"concluidos": 1, "total": 2, "mensagem": "buffer: completed (0.3s)", "id": "tu-4"}),
        ("quadro", "ferramenta_fim", {"id": "tu-4", "nome": "run_workflow", "erro": False}),
        ("gancho", 5, "user"),
        # Volta 3: a validação vira proposta com veredito; a escrita é barrada.
        ("modelo", 5),
        ("stream fechado",),
        _registro(300, 40),
        ("cobrar", 340, 790),
        ("quadro", "cota", {"gasto": 790, "teto": TETO}),
        ("gancho", 6, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-5", "nome": "validate_workflow",
                                  "argumentos": {"definition": {"__campos__": 2}}}),
        ("quadro", "ferramenta", {"id": "tu-6", "nome": "create_workflow", "argumentos": {"name": "x"}}),
        ("call_tool", "validate_workflow", "tu-5"),
        ("call_tool fim", "validate_workflow", "tu-5"),
        ("log", "info", "Assistente barrou create_workflow (usuário usr-1)."),
        ("quadro", "ferramenta_fim", {"id": "tu-5", "nome": "validate_workflow", "erro": False}),
        ("quadro", "proposta", {"definicao": DEFINICAO, "nos": 1, "arestas": 0, "desenhar": False,
                                "ok": True, "erros": 0, "avisos": 1}),
        ("quadro", "ferramenta_fim", {"id": "tu-6", "nome": "create_workflow", "erro": True}),
        ("gancho", 7, "user"),
        # Volta 4: o texto final fecha a conversa.
        ("modelo", 7),
        ("quadro", "texto", {"texto": "Pronto."}),
        ("stream fechado",),
        _registro(400, 50),
        ("cobrar", 450, 1240),
        ("quadro", "cota", {"gasto": 1240, "teto": TETO}),
        ("gancho", 8, "assistant"),
        _balanco(4, 1140),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _uso_total(1000, 140), "voltas": 4, "ok": True}),
    ]


async def test_home_quadro_a_quadro(linha, monkeypatch):
    """A Home: a confirmação sai pela fila no meio do lote paralelo, o fluxo
    criado vira `fluxo`, e a ferramenta local (respostas rápidas) roda em fila."""
    monkeypatch.setattr(agente.secrets, "token_urlsafe", lambda _n: "tok-fixo")
    redis = RedisFalso()
    criado = json.dumps({"id": "wf-9", "untrusted_data": {"name": "Focos"}})
    servidor = _Servidor(linha, ["search_nodes", "create_workflow", "run_workflow", "cancel_run"],
                         {"create_workflow": criado})
    volta1 = [_chamada("create_workflow", {"name": "Focos", "definition": {"nodes": []}}, "tu-1"),
              _chamada("cancel_run", {"run_id": "run-9"}, "tu-2")]
    volta2 = [_chamada(agente.NOME_DAS_RESPOSTAS, {"opcoes": ["Sim", "Não"]}, "tu-3")]
    modelo = _Modelo(linha, [
        [_resposta(volta1, "tool_calls")],
        [_resposta(volta2, "tool_calls")],
        [_resposta([_texto("Feito.")])],
    ])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, redis=redis, superficie=agente.HOME,
                               conversa_id="conv-1", ao_fechar_turno=_gancho(linha)), linha)

    transcrito = [
        PEDIDO,
        {"role": "assistant", "content": volta1},
        {"role": "user", "content": [_resultado("tu-1", criado), _resultado("tu-2", agente.MENSAGEM_AGUARDANDO)]},
        {"role": "assistant", "content": volta2},
        {"role": "user", "content": [_resultado(
            "tu-3", "Respostas rápidas na tela (2). Encerre o turno: a pessoa escolhe uma ou digita outra coisa.")]},
        {"role": "assistant", "content": [_texto("Feito.")]},
    ]
    assert linha == PREPARO + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20, "home"),
        ("cobrar", 120, 120),
        ("quadro", "cota", {"gasto": 120, "teto": TETO}),
        ("gancho", 2, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "create_workflow",
                                  "argumentos": {"name": "Focos", "definition": {"__campos__": 1}}}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "cancel_run", "argumentos": {"run_id": "run-9"}}),
        ("call_tool", "create_workflow", "tu-1"),
        ("call_tool fim", "create_workflow", "tu-1"),
        ("quadro", "confirmacao", {"tool_use_id": "tu-2", "token": "tok-fixo",
                                   "acao": {"tool": "cancel_run", "argumentos": {"run_id": "run-9"}, "alvo": "run-9"}}),
        ("quadro", "ferramenta_fim", {"id": "tu-1", "nome": "create_workflow", "erro": False}),
        ("quadro", "fluxo", {"workflow_id": "wf-9", "nome": "Focos"}),
        ("quadro", "ferramenta_fim", {"id": "tu-2", "nome": "cancel_run", "erro": False}),
        ("gancho", 3, "user"),
        ("modelo", 3),
        ("stream fechado",),
        _registro(100, 20, "home"),
        ("cobrar", 120, 240),
        ("quadro", "cota", {"gasto": 240, "teto": TETO}),
        ("gancho", 4, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-3", "nome": agente.NOME_DAS_RESPOSTAS,
                                  "argumentos": {"opcoes": {"__itens__": 2}}}),
        ("quadro", "ferramenta_fim", {"id": "tu-3", "nome": agente.NOME_DAS_RESPOSTAS, "erro": False}),
        ("quadro", "respostas_rapidas", {"opcoes": ["Sim", "Não"]}),
        ("gancho", 5, "user"),
        ("modelo", 5),
        ("stream fechado",),
        _registro(100, 20, "home"),
        ("cobrar", 120, 360),
        ("quadro", "cota", {"gasto": 360, "teto": TETO}),
        ("gancho", 6, "assistant"),
        _balanco(3, 360, "home"),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _uso_total(300, 60), "voltas": 3, "ok": True}),
    ]


async def test_o_modelo_recebe_a_conversa_viva_e_o_transcrito_do_chamador_fica_intacto(linha):
    """Cada volta recebe o mesmo sistema, as mesmas ferramentas e a conversa
    que o laço vai estendendo — uma cópia: a lista de quem chamou não muda."""
    transcrito = [PEDIDO]
    servidor = _Servidor(linha, ["search_nodes", "create_workflow"])
    modelo = _Modelo(linha, [
        [_resposta([_chamada("search_nodes", {}, "tu-1")], "tool_calls")],
        [_resposta([_texto("ok")])],
    ])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, transcrito=transcrito), linha)

    primeiro, segundo = modelo.pedidos
    assert transcrito == [PEDIDO]
    assert primeiro["conversa"] is segundo["conversa"] and primeiro["conversa"] is not transcrito
    assert primeiro["modelo"] == MODELO
    assert primeiro["sistema"] == cs.montar_sistema(None) and segundo["sistema"] is primeiro["sistema"]
    assert [f["function"]["name"] for f in primeiro["ferramentas"]] == [cs.NOME_DO_DESENHO, "search_nodes"]
    assert segundo["ferramentas"] is primeiro["ferramentas"]
    assert (primeiro["max_tokens"], primeiro["esforco"]) == (cs.MAX_TOKENS, cs.ESFORCO_DO_RACIOCINIO)


# ── As saídas por erro ────────────────────────────────────────────────────────


async def test_teto_de_voltas_fecha_com_loop_limit(linha, monkeypatch):
    """Sem Redis: nem quadro de cota, nem cobrança — e o teto em memória vale."""
    monkeypatch.setattr(cs, "TETO_DE_VOLTAS", 2)
    servidor = _Servidor(linha, ["search_nodes"])
    modelo = _Modelo(linha, [
        [_resposta([_chamada("search_nodes", {}, "tu-1")], "tool_calls")],
        [_resposta([_chamada("search_nodes", {}, "tu-2")], "tool_calls")],
    ])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_gancho(linha)), linha)

    def _volta(n, ident):
        return [
            ("modelo", n),
            ("stream fechado",),
            _registro(100, 20),
            ("cobrar", 120, None),
            ("gancho", n + 1, "assistant"),
            ("quadro", "ferramenta", {"id": ident, "nome": "search_nodes", "argumentos": {}}),
            ("call_tool", "search_nodes", ident),
            ("call_tool fim", "search_nodes", ident),
            ("quadro", "ferramenta_fim", {"id": ident, "nome": "search_nodes", "erro": False}),
            ("gancho", n + 2, "user"),
        ]

    fim = linha[-1]
    assert linha[:-1] == PREPARO + _volta(1, "tu-1") + _volta(3, "tu-2") + [
        ("log", "warning", "Assistente interrompido no teto de voltas (usuário usr-1, 240 tokens)."),
        ("quadro", "erro", {
            "code": "loop_limit",
            "message": "A conversa passou de 2 rodadas de ferramenta sem concluir.",
            "hint": "descreva o fluxo em partes menores, ou diga o que ficou faltando",
            "teto": 2,
        }),
        _balanco(3, 240),
    ]
    assert fim[:2] == ("quadro", "fim")
    assert (fim[2]["voltas"], fim[2]["ok"], fim[2]["uso"]) == (3, False, _uso_total(200, 40))
    assert len(fim[2]["transcrito"]) == 5


class _ModeloQueQuebraNaChamada(_Modelo):
    def transmitir(self, **kw):
        self.linha.append(("modelo", len(kw["conversa"])))
        raise openrouter.ErroDoOpenRouter("falha de rede ao falar com o OpenRouter (sem rota)")


MODELO_INDISPONIVEL = {
    "code": "modelo_indisponivel",
    "message": "Não consegui falar com o modelo agora.",
    "hint": "tente de novo em alguns instantes",
    "detalhe": "ErroDoOpenRouter",
}


@pytest.mark.parametrize("onde", ["no meio do stream", "sem a resposta final", "na chamada"])
async def test_falha_do_modelo_vira_erro_e_fecha_a_conversa(linha, onde):
    """O que o modelo já cedeu continua na tela; o texto da exceção nunca vai
    ao quadro (carrega URL e cabeçalho), só a classe."""
    servidor = _Servidor(linha, ["search_nodes"])
    if onde == "na chamada":
        modelo = _ModeloQueQuebraNaChamada(linha, [])
        ao_vivo = []
    elif onde == "no meio do stream":
        modelo = _Modelo(linha, [[openrouter.Delta("texto", "Vou"),
                                  openrouter.ErroDoOpenRouter("falha de rede (sem rota)")]])
        ao_vivo = [("quadro", "texto", {"texto": "Vou"}), ("stream fechado",)]
    else:
        modelo = _Modelo(linha, [[openrouter.Delta("pensando", "hm")]])
        ao_vivo = [("quadro", "pensando", {"texto": "hm"}), ("stream fechado",)]

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, redis=RedisFalso(),
                               ao_fechar_turno=_gancho(linha)), linha)

    assert linha == PREPARO + [("modelo", 1)] + ao_vivo + [
        ("log", "exception", "Falha ao falar com o modelo (usuário usr-1)."),
        ("quadro", "erro", MODELO_INDISPONIVEL),
        _balanco(1, 0),
        ("quadro", "fim", {"transcrito": [PEDIDO], "uso": _uso_total(0, 0), "voltas": 1, "ok": False}),
    ]


PENDENTE = "A chamada não chegou a acontecer: a conversa foi interrompida."


@pytest.mark.parametrize("parada", ["content_filter", "length"])
async def test_recusa_ou_corte_do_modelo_fecha_a_conversa_sem_rodar_a_chamada(linha, parada):
    """A mensagem entra (e o turno fecha) antes do erro; a chamada pedida não
    roda, e o transcrito devolvido a responde para continuar retomável."""
    blocos = [_texto("vou criar"), _chamada("create_workflow", {"name": "x"}, "tu-1")]
    servidor = _Servidor(linha, ["create_workflow"])
    modelo = _Modelo(linha, [[_resposta(blocos, parada, _uso(50, 5))]])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, redis=RedisFalso(),
                               ao_fechar_turno=_gancho(linha)), linha)

    if parada == "content_filter":
        corte = [("quadro", "erro", {"code": "recusado", "message": "O modelo recusou este pedido."})]
    else:
        corte = [
            ("log", "warning", "Assistente cortado por max_tokens (usuário usr-1)."),
            ("quadro", "erro", {"code": "resposta_truncada",
                                "message": "A resposta foi cortada no meio e não é segura de aplicar.",
                                "hint": "peça o fluxo em partes menores"}),
        ]
    transcrito = [PEDIDO, {"role": "assistant", "content": blocos},
                  {"role": "user", "content": [_resultado("tu-1", PENDENTE, True)]}]
    assert linha == PREPARO + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(50, 5),
        ("cobrar", 55, 55),
        ("quadro", "cota", {"gasto": 55, "teto": TETO}),
        ("gancho", 2, "assistant"),
        *corte,
        _balanco(1, 55),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _uso_total(50, 5), "voltas": 1, "ok": False}),
    ]


@pytest.mark.parametrize("parada", ["stop", "content_filter"])
async def test_resposta_sem_bloco_nenhum_nao_entra_na_conversa(linha, parada):
    servidor = _Servidor(linha, [])
    modelo = _Modelo(linha, [[_resposta([], parada)]])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, redis=RedisFalso(),
                               ao_fechar_turno=_gancho(linha)), linha)

    recusa = [("quadro", "erro", {"code": "recusado", "message": "O modelo recusou este pedido."})]
    assert linha == PREPARO + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, 120),
        ("quadro", "cota", {"gasto": 120, "teto": TETO}),
        ("log", "warning", f"Modelo devolveu uma resposta sem conteúdo (parada={parada}, usuário usr-1)."),
        *(recusa if parada == "content_filter" else []),
        _balanco(1, 120),
        ("quadro", "fim", {"transcrito": [PEDIDO], "uso": _uso_total(100, 20), "voltas": 1,
                           "ok": parada == "stop"}),
    ]


async def test_pedido_de_ferramenta_sem_chamada_nenhuma_encerra_bem(linha):
    servidor = _Servidor(linha, [])
    modelo = _Modelo(linha, [[_resposta([_texto("hm")], "tool_calls")]])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_gancho(linha)), linha)

    assert linha[len(PREPARO):] == [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, None),
        ("gancho", 2, "assistant"),
        _balanco(1, 120),
        ("quadro", "fim", {"transcrito": [PEDIDO, {"role": "assistant", "content": [_texto("hm")]}],
                           "uso": _uso_total(100, 20), "voltas": 1, "ok": True}),
    ]


async def test_gancho_que_quebra_loga_e_a_conversa_segue(linha):
    async def _quebra(conversa):
        linha.append(("gancho", len(conversa)))
        raise RuntimeError("banco fora")

    servidor = _Servidor(linha, ["search_nodes"])
    modelo = _Modelo(linha, [
        [_resposta([_chamada("search_nodes", {}, "tu-1")], "tool_calls")],
        [_resposta([_texto("ok")])],
    ])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_quebra), linha)

    ganchos = [e for e in linha if e[0] == "gancho" or e[:2] == ("log", "exception")]
    assert ganchos == [
        ("gancho", 2), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
        ("gancho", 3), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
        ("gancho", 4), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
    ]
    assert linha[-1][2]["ok"] is True


async def test_erros_das_ferramentas_do_lote_viram_resultado_de_erro(linha):
    """Recusa declarada, quebra, argumento que não é objeto e o portão do
    editor: todas viram `tool_result` de erro, e a conversa segue."""
    recusa = ToolError(json.dumps({"code": "forbidden", "message": "sem papel"}))
    servidor = _Servidor(linha, ["search_nodes", "describe_node", "get_authoring_guide", "run_workflow"],
                         {"search_nodes": recusa, "describe_node": RuntimeError("quebrou")})
    lote = [
        _chamada("search_nodes", {"query": "x"}, "tu-1"),
        _chamada("describe_node", {"name": "Buffer"}, "tu-2"),
        _chamada("get_authoring_guide", "texto cru", "tu-3"),
        _chamada("run_workflow", {"workflow_id": "wf-1"}, "tu-4"),
    ]
    modelo = _Modelo(linha, [[_resposta(lote, "tool_calls")], [_resposta([_texto("ok")])]])

    await _consumir(_conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_gancho(linha)), linha)

    anuncios = [
        ("quadro", "ferramenta", {"id": c["id"], "nome": c["name"], "argumentos": cs._resumo(c["input"])})
        for c in lote
    ]
    assert linha[len(PREPARO):] == [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, None),
        ("gancho", 2, "assistant"),
        *anuncios,
        ("call_tool", "search_nodes", "tu-1"),
        ("call_tool", "describe_node", "tu-2"),
        ("log", "exception", "Ferramenta describe_node quebrou no assistente (usuário usr-1)."),
        ("log", "info", "Assistente barrou run_workflow antes do desenho (usuário usr-1)."),
        *[("quadro", "ferramenta_fim", {"id": c["id"], "nome": c["name"], "erro": True}) for c in lote],
        ("gancho", 3, "user"),
        ("modelo", 3),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, None),
        ("gancho", 4, "assistant"),
        _balanco(2, 240),
        ("quadro", "fim", {
            "transcrito": [
                PEDIDO,
                {"role": "assistant", "content": lote},
                {"role": "user", "content": [
                    _resultado("tu-1", str(recusa), True),
                    _resultado("tu-2", "A ferramenta describe_node falhou de forma inesperada (RuntimeError).", True),
                    _resultado("tu-3", "O argumento não chegou como objeto JSON. Refaça a chamada.", True),
                    _resultado("tu-4", cs.MENSAGEM_DE_EXECUTAR_ANTES, True),
                ]},
                {"role": "assistant", "content": [_texto("ok")]},
            ],
            "uso": _uso_total(200, 40), "voltas": 2, "ok": True,
        }),
    ]


async def test_cota_estourada_recusa_antes_de_falar_com_o_modelo(linha):
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = TETO
    modelo = _Modelo(linha, [])

    with pytest.raises(ToolError):
        await _consumir(_conversar(linha, servidor=_Servidor(linha, []), modelo=modelo, redis=redis), linha)

    assert linha == PREPARO[:2]


# ── O cancelamento pelo cliente ───────────────────────────────────────────────
# A aba fechada cancela a tarefa que puxa os quadros (`com_batimento`): o
# CancelledError cai onde o laço está esperando e sobe. Nenhum efeito seguinte
# acontece; uma ferramenta que já estava rodando termina sozinha.


async def test_cancelado_no_meio_do_stream_nao_cobra_nem_fecha_turno(linha):
    trava = asyncio.Event()
    modelo = _Modelo(linha, [[openrouter.Delta("texto", "Vou"), trava]])
    consumo = asyncio.create_task(_consumir(
        _conversar(linha, servidor=_Servidor(linha, []), modelo=modelo, redis=RedisFalso(),
                   ao_fechar_turno=_gancho(linha)), linha))
    await _esperar(lambda: ("quadro", "texto", {"texto": "Vou"}) in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    trava.set()
    await asyncio.sleep(0.01)

    assert linha == PREPARO + [
        ("modelo", 1),
        ("quadro", "texto", {"texto": "Vou"}),
        ("stream fechado",),
        ("cancelado",),
    ]


async def test_cancelado_com_ferramenta_em_fila_rodando_ela_termina_sozinha(linha):
    liberar = asyncio.Event()

    async def _rodando(_ctx):
        await liberar.wait()
        return "rodou"

    servidor = _Servidor(linha, ["run_workflow"], {"run_workflow": _rodando})
    modelo = _Modelo(linha, [[_resposta([
        _chamada(cs.NOME_DO_DESENHO, {"definition": DEFINICAO}, "tu-1"),
        _chamada("run_workflow", {"workflow_id": "wf-1"}, "tu-2"),
    ], "tool_calls")]])
    consumo = asyncio.create_task(_consumir(
        _conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_gancho(linha)), linha))
    await _esperar(lambda: ("call_tool", "run_workflow", "tu-2") in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    liberar.set()
    await _esperar(lambda: ("call_tool fim", "run_workflow", "tu-2") in linha)
    await asyncio.sleep(0.01)

    assert linha[len(PREPARO):] == [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, None),
        ("gancho", 2, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-1", "nome": cs.NOME_DO_DESENHO,
                                  "argumentos": {"definition": {"__campos__": 2}}}),
        ("quadro", "ferramenta_fim", {"id": "tu-1", "nome": cs.NOME_DO_DESENHO, "erro": False}),
        ("quadro", "proposta", {"definicao": DEFINICAO, "nos": 1, "arestas": 0, "desenhar": True}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "run_workflow", "argumentos": {"workflow_id": "wf-1"}}),
        ("call_tool", "run_workflow", "tu-2"),
        ("cancelado",),
        ("call_tool fim", "run_workflow", "tu-2"),
    ]


async def test_cancelado_com_o_lote_paralelo_rodando_todas_terminam_sozinhas(linha):
    liberar = asyncio.Event()

    async def _rodando(_ctx):
        await liberar.wait()
        return "pronto"

    servidor = _Servidor(linha, ["search_nodes", "describe_node"],
                         {"search_nodes": _rodando, "describe_node": _rodando})
    modelo = _Modelo(linha, [[_resposta([
        _chamada("search_nodes", {}, "tu-1"), _chamada("describe_node", {}, "tu-2"),
    ], "tool_calls")]])
    consumo = asyncio.create_task(_consumir(
        _conversar(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_gancho(linha)), linha))
    await _esperar(lambda: ("call_tool", "describe_node", "tu-2") in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    liberar.set()
    await _esperar(lambda: ("call_tool fim", "describe_node", "tu-2") in linha)
    await asyncio.sleep(0.01)

    assert linha[len(PREPARO) + 5:] == [
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "search_nodes", "argumentos": {}}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "describe_node", "argumentos": {}}),
        ("call_tool", "search_nodes", "tu-1"),
        ("call_tool", "describe_node", "tu-2"),
        ("cancelado",),
        ("call_tool fim", "search_nodes", "tu-1"),
        ("call_tool fim", "describe_node", "tu-2"),
    ]


async def _puxar_ate(gerador, linha, parar):
    """Puxa quadros até `parar(evento)` e fecha o gerador ali (`aclose`)."""
    async for evento in gerador:
        linha.append(("quadro", evento.tipo, evento.dados))
        if parar(evento):
            break
    await gerador.aclose()
    linha.append(("fechado",))


async def test_fechado_depois_da_cota_a_resposta_nao_entra_na_conversa(linha):
    """O gancho só roda quando o quadro seguinte à cota é pedido."""
    modelo = _Modelo(linha, [[_resposta([_chamada("search_nodes", {}, "tu-1")], "tool_calls")]])
    gerador = _conversar(linha, servidor=_Servidor(linha, ["search_nodes"]), modelo=modelo, redis=RedisFalso(),
                         ao_fechar_turno=_gancho(linha))

    await _puxar_ate(gerador, linha, lambda e: e.tipo == "cota")
    await asyncio.sleep(0.01)

    assert linha == PREPARO + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, 120),
        ("quadro", "cota", {"gasto": 120, "teto": TETO}),
        ("fechado",),
    ]


async def test_fechado_no_anuncio_da_ferramenta_em_fila_ela_nao_roda(linha):
    modelo = _Modelo(linha, [[_resposta([
        _chamada(cs.NOME_DO_DESENHO, {"definition": DEFINICAO}, "tu-1"),
        _chamada("run_workflow", {"workflow_id": "wf-1"}, "tu-2"),
    ], "tool_calls")]])
    gerador = _conversar(linha, servidor=_Servidor(linha, ["run_workflow"]), modelo=modelo,
                         ao_fechar_turno=_gancho(linha))

    await _puxar_ate(gerador, linha, lambda e: e.tipo == "ferramenta" and e.dados["id"] == "tu-2")
    await asyncio.sleep(0.01)

    assert linha[-3:] == [
        ("quadro", "proposta", {"definicao": DEFINICAO, "nos": 1, "arestas": 0, "desenhar": True}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "run_workflow", "argumentos": {"workflow_id": "wf-1"}}),
        ("fechado",),
    ]


async def test_fechado_no_anuncio_do_lote_nenhuma_roda(linha):
    modelo = _Modelo(linha, [[_resposta([
        _chamada("search_nodes", {}, "tu-1"), _chamada("describe_node", {}, "tu-2"),
    ], "tool_calls")]])
    gerador = _conversar(linha, servidor=_Servidor(linha, ["search_nodes", "describe_node"]), modelo=modelo,
                         ao_fechar_turno=_gancho(linha))

    await _puxar_ate(gerador, linha, lambda e: e.tipo == "ferramenta")
    await asyncio.sleep(0.01)

    assert linha[-3:] == [
        ("gancho", 2, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "search_nodes", "argumentos": {}}),
        ("fechado",),
    ]


async def test_fechado_no_meio_do_stream_o_stream_do_modelo_tambem_fecha(linha):
    modelo = _Modelo(linha, [[openrouter.Delta("texto", "Vou"), openrouter.Delta("texto", " montar"),
                              _resposta([_texto("Vou montar")])]])
    gerador = _conversar(linha, servidor=_Servidor(linha, []), modelo=modelo, redis=RedisFalso(),
                         ao_fechar_turno=_gancho(linha))

    await _puxar_ate(gerador, linha, lambda e: e.tipo == "texto")
    await _esperar(lambda: ("stream fechado",) in linha)

    assert linha == PREPARO + [
        ("modelo", 1),
        ("quadro", "texto", {"texto": "Vou"}),
        ("fechado",),
        ("stream fechado",),
    ]


# ── Memória e ordem da preparação ─────────────────────────────────────────────


async def test_o_laco_sai_da_memoria_com_o_stream_sem_o_coletor_ciclico(linha, monkeypatch):
    """Terminada a conversa, o laço (a conversa inteira, o catálogo, o cliente)
    sai da memória por contagem de referência, como as closures do gerador de
    antes. Com o canal das ferramentas como método ligado do laço, guardado no
    estado e no contexto de cada ferramenta, o laço ficava num ciclo que só o
    coletor cíclico desfaz: na geração 2, bem depois do fim."""
    vivos = []

    class _Espiado(cs.LacoDaConversa):
        def __init__(self, **kw):
            super().__init__(**kw)
            vivos.append(weakref.ref(self))

    monkeypatch.setattr(cs, "LacoDaConversa", _Espiado)
    modelo = _Modelo(linha, [
        [_resposta([_chamada("search_nodes", {}, "tu-1")], parada="tool_calls", uso=_uso(10, 1))],
        [_resposta([_texto("ok")], uso=_uso(10, 1))],
    ])
    gc.collect()
    gc.disable()
    try:
        await _consumir(_conversar(linha, servidor=_Servidor(linha, ["search_nodes"]), modelo=modelo), linha)
        assert ("call_tool fim", "search_nodes", "tu-1") in linha
        assert [q for q in linha if q[0] == "quadro"][-1][1] == "fim"
        assert len(vivos) == 1 and vivos[0]() is None
    finally:
        gc.enable()


async def test_transcrito_fora_do_formato_com_a_cota_estourada_da_a_recusa_da_cota(linha):
    """O estado das ferramentas nasce no fim da preparação, como antes: um item
    do transcrito que não é objeto só é lido depois da cota, e a recusa por
    cota (a que a rota sabe mostrar) vem primeiro."""
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = TETO

    with pytest.raises(ToolError):
        await _consumir(
            _conversar(
                linha, servidor=_Servidor(linha, []), modelo=_Modelo(linha, []), redis=redis,
                transcrito=["não sou um objeto", PEDIDO],
            ),
            linha,
        )

    assert linha == PREPARO[:2]
