# tests/unit/test_assistente_service.py
"""
O laço do assistente — o que ele garante e o que ele recusa.

Este arquivo existe por causa de uma escolha de desenho: o assistente chama as
MESMAS ferramentas do MCP, pelo mesmo `call_tool`, com o escopo viajando num
`ContextVar`. Isso dá de graça a guarda de escopo, a cota, o papel mínimo e a
auditoria — e cria exatamente um defeito novo possível, que é o escopo
sobreviver à chamada. Os dois primeiros testes do bloco `ContextVar` existem só
para isso, e são os que mais importam no arquivo: um escopo pendurado é um
usuário enxergando o workspace de outro.
"""
from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp import cotas
from app.mcp.escopo import (
    ESCOPO_ATUAL,
    ESCOPOS_DO_EDITOR,
    PREFIXO_DO_EDITOR,
    escopo_do_editor,
)
from app.services import assistente_service as cs
from app.services import openrouter

from ._mcp_harness import RedisFalso, escopo_falso

pytestmark = pytest.mark.asyncio


# ── Dublês ────────────────────────────────────────────────────────────────────


def _uso(entrada=100, saida=50, cache_leitura=0, cache_escrita=0):
    """O `uso` como o cliente do OpenRouter o devolve: nas chaves do projeto, com
    `entrada` já INCLUINDO o que veio do cache."""
    return {
        "entrada": entrada,
        "saida": saida,
        "cache_leitura": cache_leitura,
        "cache_escrita": cache_escrita,
        "raciocinio": 0,
        "custo": 0.0,
    }


def _texto(txt: str):
    """Um bloco de texto no formato do projeto — o mesmo que o cliente remonta do
    stream e que o transcrito guarda."""
    return {"type": "text", "text": txt}


def _chamada(nome: str, argumentos, ident: str = "tu-1"):
    return {"type": "tool_use", "id": ident, "name": nome, "input": argumentos}


def _resposta(*, conteudo=None, parada="stop", uso=None):
    return openrouter.Resposta(blocos=list(conteudo or []), parada=parada, uso=uso or _uso())


class ClienteFalso:
    """O modelo, roteirizado: uma `(deltas, resposta)` por volta do laço.

    Tem a forma de `openrouter.ClienteOpenRouter`: `transmitir(**kw)` cede os
    `Delta`s e, por último, a `Resposta`. Guarda os parâmetros de cada volta.
    """

    def __init__(self, voltas):
        self._voltas = list(voltas)
        self.parametros: list[dict] = []

    async def transmitir(self, **kw):
        # Copia profunda: o laço continua mutando a `conversa` depois da chamada,
        # e o teste quer ver o que o cliente RECEBEU naquela volta.
        self.parametros.append(copy.deepcopy(kw))
        if not self._voltas:
            raise AssertionError("o laço pediu mais voltas do que o roteiro previa")
        deltas, resposta = self._voltas.pop(0)
        for delta in deltas:
            yield delta
        yield resposta


class _ToolFalsa:
    def __init__(self, nome, descricao="faz coisa", schema=None):
        self.name = nome
        self.description = descricao
        self.input_schema = schema or {"type": "object", "properties": {}}


class ServidorFalso:
    """Um `ServidorAtlans` do tamanho do que o assistente usa.

    Guarda o escopo que enxergava a cada chamada — é assim que os testes do
    `ContextVar` observam o que aconteceu por dentro.
    """

    def __init__(self, tools=None, resultados=None):
        self._tools = tools or [_ToolFalsa("search_nodes"), _ToolFalsa("create_workflow")]
        self._resultados = dict(resultados or {})
        self.escopos_vistos: list[object] = []
        self.chamadas: list[tuple[str, dict]] = []
        self.escopo_no_list_tools = "nao-chamado"

    async def list_tools(self):
        self.escopo_no_list_tools = ESCOPO_ATUAL.get()
        return list(self._tools)

    async def call_tool(self, nome, argumentos, context=None):
        self.escopos_vistos.append(ESCOPO_ATUAL.get())
        self.chamadas.append((nome, argumentos))
        acao = self._resultados.get(nome, "ok")
        if isinstance(acao, Exception):
            raise acao
        if callable(acao):
            return await acao(context)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=str(acao))],
            structured_content=None,
            is_error=False,
        )


async def _colher(gerador):
    eventos = [evento async for evento in gerador]
    # O contrato do módulo: o último quadro é SEMPRE `fim`, mesmo quando a
    # conversa acabou mal — é ele que carrega o transcrito. Conferir aqui
    # aplica a regra a todos os testes do arquivo de uma vez.
    assert eventos and eventos[-1].tipo == "fim", "a conversa não terminou em `fim`"
    return eventos


def _o_erro(eventos) -> dict:
    """O quadro de erro da conversa — e a garantia de que houve exatamente um."""
    erros = [e for e in eventos if e.tipo == "erro"]
    assert len(erros) == 1, f"esperava um erro, vieram {len(erros)}"
    return erros[0].dados


def _conversar(**kw):
    base = {
        "escopo": escopo_falso(scopes=ESCOPOS_DO_EDITOR),
        "transcrito": [{"role": "user", "content": "monta um fluxo"}],
        "servidor": ServidorFalso(),
        "cliente": ClienteFalso([([], _resposta())]),
        "redis": None,
    }
    base.update(kw)
    return cs.conversar(**base)


# ── O escopo do assistente ──────────────────────────────────────────────────────


async def test_o_escopo_do_editor_nao_carrega_os_escopos_destrutivos():
    """`triggers:manage` e `drive:write` ficaram fora da v1, por decisão do dono.

    Apagar agendamento e apagar arquivo do Drive destroem dado de outra pessoa
    do workspace, e "limpa os agendamentos antigos" é uma frase que alguém
    digita sem pensar. Se um dia entrarem, que seja por escolha — e este teste
    é o lugar onde a escolha aparece.
    """
    assert "triggers:manage" not in ESCOPOS_DO_EDITOR
    assert "drive:write" not in ESCOPOS_DO_EDITOR
    assert {"workflows:read", "workflows:write", "runs:execute", "drive:read"} == set(
        ESCOPOS_DO_EDITOR
    )


async def test_o_escopo_do_editor_tem_balde_de_cota_separado_do_PAT():
    """O `token_id` sintético é o que separa os baldes e marca a auditoria."""
    escopo = escopo_do_editor(user_id="usr-9", username="ana", workspace_ids={"ws-1", "ws-2"})

    assert escopo.token_id == f"{PREFIXO_DO_EDITOR}:usr-9"
    assert escopo.token_prefix == PREFIXO_DO_EDITOR
    assert escopo.user_id == "usr-9"
    assert escopo.workspace_ids == frozenset({"ws-1", "ws-2"})
    # Sem token restringindo, o alcance é o do usuário — hoje e amanhã.
    assert escopo.todos_os_workspaces is True
    # E nunca administrador, pelo mesmo motivo de sempre.
    assert escopo.como_usuario().role == "user"


# ── O portão de escrita ───────────────────────────────────────────────────────


async def test_a_regra_do_portao_sai_das_GUARDAS_e_nao_de_uma_lista_a_mao():
    """Lista escrita à mão envelhece na primeira ferramenta nova.

    A regra derivada faz uma ferramenta de escrita nascer BLOQUEADA — falha
    fechada. Este teste é o que garante que a derivação bate com a intenção, e
    é ele que quebra se alguém acrescentar uma exceção sem pensar.
    """
    from app.mcp.guardas import GUARDAS

    bloqueadas = {n for n in GUARDAS if cs.bloqueada_no_editor(n)}
    escrevem = {n for n, g in GUARDAS.items() if not g.read_only}

    # Exatamente as que escrevem, menos as exceções — nem uma a mais.
    assert bloqueadas == escrevem - cs.ESCREVEM_MAS_PASSAM
    # Validar e rodar (as duas originais) e o par do catálogo de fontes: sondar
    # um WFS e registrá-lo são o caminho de o assistente achar uma fonte nova.
    assert cs.ESCREVEM_MAS_PASSAM == {"validate_workflow", "run_workflow", "probe_source", "register_source"}

    # As que importam, nomeadas, para o diff mostrar a decisão:
    for nome in ("create_workflow", "update_workflow", "set_workflow_active",
                 "set_portal_access", "restore_workflow_version", "duplicate_workflow"):
        assert cs.bloqueada_no_editor(nome), f"{nome} deveria estar barrada"

    # E as excecoes continuam passando, senao o assistente fica inutil.
    assert not cs.bloqueada_no_editor("validate_workflow")
    assert not cs.bloqueada_no_editor("run_workflow")
    assert not cs.bloqueada_no_editor("probe_source")
    assert not cs.bloqueada_no_editor("register_source")
    # Leitura nunca e barrada.
    assert not cs.bloqueada_no_editor("search_nodes")


async def test_ferramenta_sem_guarda_nasce_bloqueada():
    """Falha fechada: nome que nao esta em GUARDAS nao roda."""
    assert cs.bloqueada_no_editor("ferramenta_que_nao_existe")


async def test_a_ferramenta_barrada_some_da_lista_que_o_modelo_ve():
    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("create_workflow"), _ToolFalsa("validate_workflow")]
    )
    cliente = ClienteFalso([([], _resposta())])

    await _colher(_conversar(servidor=servidor, cliente=cliente))

    ferramentas = cliente.parametros[0]["ferramentas"]
    nomes = {f["function"]["name"] for f in ferramentas}
    assert nomes == {cs.NOME_DO_DESENHO, "search_nodes", "validate_workflow"}
    # A entrega abre a lista: o que o modelo le primeiro e o que define o
    # trabalho. Enterrada entre 38 outras, ela some do raciocinio dele.
    assert ferramentas[0]["function"]["name"] == cs.NOME_DO_DESENHO


async def test_o_portao_barra_no_DESPACHO_e_nao_so_na_lista():
    """A garantia, e não o conforto.

    Esconder da lista evita que o modelo QUEIRA a ferramenta. Recusar aqui é o
    que impede que ela RODE quando ele a nomeia assim mesmo — porque leu num
    exemplo, porque alucinou, ou porque alguém mandou no texto de um fluxo
    compartilhado. Sem esta recusa, o portão inteiro é decoração.

    O `ServidorFalso` aceitaria a chamada de bom grado: se ela chegasse lá, o
    fluxo seria gravado.
    """
    servidor = ServidorFalso(tools=[_ToolFalsa("search_nodes")])
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("create_workflow", {"name": "n", "definition": {}})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("entendi, vou so mostrar")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert servidor.chamadas == [], "create_workflow chegou ao servidor: o portao nao vale nada"
    resultado = eventos[-1].dados["transcrito"][2]["content"][0]
    assert resultado["is_error"] is True
    # A recusa diz o que fazer em vez disso — senao o modelo tenta de novo.
    assert "aplicar" in resultado["content"]


async def test_o_sistema_avisa_que_o_assistente_nao_grava():
    """`INSTRUCOES` manda "chame create_workflow depois de validar", e aqui essa
    ferramenta nao existe. Sem a correcao, o modelo procura o que nao ha e
    termina a conversa sem entregar o fluxo."""
    blocos = cs.montar_sistema()
    texto = "\n".join(b["text"] for b in blocos)

    assert "create_workflow" in cs.INSTRUCOES_DO_EDITOR
    assert "NAO grava" in texto
    # A entrega e nomeada, e nomeada CEDO: e a diferenca entre "eu explico o
    # fluxo" e "eu ponho o fluxo na tela".
    assert cs.NOME_DO_DESENHO in texto
    assert "SUA ENTREGA E O FLUXO NO CANVAS" in texto
    # E o aval de execucao continua sendo pedido em texto.
    assert "pode rodar" in texto


async def test_o_roteiro_do_assistente_consulta_o_catalogo_antes_de_prospectar():
    """"Catalogo primeiro": para dado externo o passo e `search_sources` ->
    `describe_source`, ANTES de `search_nodes`, do desenho e da validacao;
    `probe_source`/`register_source` so entram quando o catalogo nao tem a fonte."""
    texto = cs.INSTRUCOES_DO_EDITOR
    assert texto.index("search_sources") < texto.index("search_nodes") < texto.index("validate_workflow")
    assert texto.index("describe_source") < texto.index("probe_source") < texto.index("register_source")
    assert {"probe_source", "register_source"} <= cs.ESCREVEM_MAS_PASSAM


# ── A entrega: `desenhar_no_canvas` ──────────────────────────────────────────

async def test_desenhar_poe_o_fluxo_na_tela_sem_precisar_validar():
    """O defeito que motivou tudo: por na tela dependia de o modelo VALIDAR.

    Antes, o painel lia a definicao do argumento de `validate_workflow`. Um
    modelo que montasse e nao validasse — ou que decidisse executar e responder
    com o dado — deixava o canvas vazio. Agora a entrega tem nome proprio, e
    validar volta a ser meio.
    """
    definicao = {"nodes": [{"id": "n1", "name": "DriveReader"}], "edges": []}
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": definicao, "nota": "li o shapefile"})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_texto("pronto")])),
        ]
    )

    eventos = await _colher(_conversar(cliente=cliente))

    propostas = [e for e in eventos if e.tipo == "proposta"]
    assert len(propostas) == 1
    assert propostas[0].dados["definicao"] == definicao
    assert propostas[0].dados["desenhar"] is True, "o painel precisa saber que e para desenhar AGORA"
    assert propostas[0].dados["nos"] == 1
    assert propostas[0].dados["nota"] == "li o shapefile"


async def test_desenhar_varias_vezes_emite_varias_propostas():
    """E o que torna o fluxo incremental: a pessoa ve crescer.

    Um unico desenho no fim seria o comportamento antigo com nome novo.
    """
    um = {"nodes": [{"id": "n1"}], "edges": []}
    dois = {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": [{"source": "n1", "target": "n2"}]}
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": um})], parada="tool_calls")),
            ([], _resposta(conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": dois})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("pronto")])),
        ]
    )

    eventos = await _colher(_conversar(cliente=cliente))

    propostas = [e.dados for e in eventos if e.tipo == "proposta"]
    assert [p["nos"] for p in propostas] == [1, 2]
    assert [p["arestas"] for p in propostas] == [0, 1]


async def test_desenhar_nao_vai_ao_servidor_MCP():
    """O canvas e do editor: nao ha nada para o servidor executar.

    E ela nao existe no MCP — um cliente externo nunca a ve, porque nao tem
    canvas nenhum.
    """
    servidor = ServidorFalso(tools=[_ToolFalsa("validate_workflow")])
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": {"nodes": [], "edges": []}})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_texto("ok")])),
        ]
    )

    await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert cs.NOME_DO_DESENHO not in [nome for nome, _ in servidor.chamadas]


async def test_definicao_torta_no_desenho_volta_como_erro_e_nao_derruba():
    """O modelo le o erro e corrige — que e o que deve acontecer."""
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": "isto nao e um objeto"})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_texto("corrigindo")])),
        ]
    )

    eventos = await _colher(_conversar(cliente=cliente))

    assert not [e for e in eventos if e.tipo == "proposta"], "definicao torta nao vai para a tela"
    fins = [e for e in eventos if e.tipo == "ferramenta_fim"]
    assert fins and fins[0].dados["erro"] is True
    assert [e for e in eventos if e.tipo == "fim"][0].dados["ok"] is True


# ── O portao de executar antes de desenhar ───────────────────────────────────

async def test_executar_antes_de_desenhar_e_recusado():
    """O caminho que produzia a resposta-GeoJSON.

    Ler o Drive, rodar e devolver o artefato atende o pedido sem nunca montar
    nada — e como `run_workflow` estava liberado desde o inicio, era o caminho
    mais curto. Recusar ate haver fluxo na tela fecha essa porta sem tirar a
    execucao do escopo.
    """
    servidor = ServidorFalso(tools=[_ToolFalsa("run_workflow")])
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("run_workflow", {"workflow_id": "w1"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("ok, vou desenhar primeiro")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    # Pelos NOMES: `chamadas` guarda tuplas `(nome, argumentos)`, e comparar a
    # string contra a lista de tuplas passaria sempre — um verde que nao mede
    # nada, que foi exatamente o que aconteceu na primeira escrita deste teste.
    assert "run_workflow" not in [nome for nome, _ in servidor.chamadas], (
        "executou antes de haver fluxo na tela"
    )
    fins = [e for e in eventos if e.tipo == "ferramenta_fim"]
    assert fins[0].dados["erro"] is True


async def test_depois_de_desenhar_a_execucao_passa():
    """A recusa e de ORDEM, nao de escopo: desenhou, pode rodar."""
    servidor = ServidorFalso(tools=[_ToolFalsa("run_workflow")])
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": {"nodes": [], "edges": []}})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_chamada("run_workflow", {"workflow_id": "w1"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("rodou")])),
        ]
    )

    await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert "run_workflow" in [nome for nome, _ in servidor.chamadas]


async def test_o_desenho_do_turno_anterior_conta_na_retomada():
    """A conversa e retomada entre turnos, e o fluxo continua na tela.

    Um contador em memoria diria "ainda nao desenhou" numa conversa que ja tem
    um fluxo inteiro desenhado — e a pessoa levaria uma recusa sem sentido ao
    pedir "agora roda".
    """
    anterior = [
        {"role": "user", "content": "monta o fluxo"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "t1", "name": cs.NOME_DO_DESENHO,
                 "input": {"definition": {"nodes": [], "edges": []}}},
            ],
        },
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
    ]
    assert cs._ja_desenhou(anterior) is True
    assert cs._ja_desenhou([{"role": "user", "content": "monta o fluxo"}]) is False


# ── O quadro `proposta`: a ponte até o botão Aplicar ──────────────────────────


def _validou(ok=True, erros=0, avisos=1):
    """O envelope que `validate_workflow` devolve, na forma real."""
    return json.dumps(
        {"workspace_id": "ws-1", "ok": ok, "error_count": erros, "warning_count": avisos},
        ensure_ascii=False,
    )


DEFINICAO = {
    "nodes": [
        {"id": "n1", "name": "ReadShapefile", "properties": {}},
        {"id": "n2", "name": "Buffer", "properties": {"distance": 500}},
    ],
    "edges": [{"source": "n1", "target": "n2"}],
}


async def test_a_definicao_validada_chega_inteira_ao_painel():
    """Sem este quadro o botão "Aplicar" não tem o que aplicar.

    É exceção deliberada ao `_resumo`, que colapsa todo argumento para chaves e
    tamanhos. A definição precisa ir INTEIRA porque o portão de escrita fez do
    Aplicar a única ponte entre a conversa e o fluxo.
    """
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow")], resultados={"validate_workflow": _validou()}
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("validate_workflow", {"definition": DEFINICAO})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("pronto, pode aplicar")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    propostas = [e for e in eventos if e.tipo == "proposta"]
    assert len(propostas) == 1
    dados = propostas[0].dados
    assert dados["definicao"] == DEFINICAO
    assert dados["nos"] == 2
    assert dados["arestas"] == 1
    assert dados["ok"] is True
    assert dados["erros"] == 0
    assert dados["avisos"] == 1
    # E vem DEPOIS do fim da ferramenta: o painel só mostra o cartão quando a
    # linha do tempo já fechou aquele passo.
    tipos = [e.tipo for e in eventos]
    assert tipos.index("ferramenta_fim") < tipos.index("proposta")


async def test_so_a_validacao_produz_proposta():
    """O resumo continua valendo para todo o resto — o stream não é despejo de JSON."""
    servidor = ServidorFalso(tools=[_ToolFalsa("search_nodes")])
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("search_nodes", {"definition": DEFINICAO, "query": "x"})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("achei")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert not [e for e in eventos if e.tipo == "proposta"]
    chamada = next(e for e in eventos if e.tipo == "ferramenta")
    assert chamada.dados["argumentos"]["definition"] == {"__campos__": 2}


async def test_validacao_que_falhou_nao_vira_proposta():
    """Aplicar o que a ferramenta recusou seria gravar o que não passou."""
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow")],
        resultados={"validate_workflow": ToolError("definição inválida")},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("validate_workflow", {"definition": DEFINICAO})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("vou corrigir")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert not [e for e in eventos if e.tipo == "proposta"]


async def test_relatorio_ilegivel_nao_derruba_a_conversa():
    """Se o formato do relatório mudar, o painel perde a contagem e segue vivo.

    Uma exceção aqui derrubaria a conversa inteira por causa de um rótulo.
    """
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow")],
        resultados={"validate_workflow": "isto não é JSON"},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("validate_workflow", {"definition": DEFINICAO})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("ok")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    proposta = next(e for e in eventos if e.tipo == "proposta")
    assert proposta.dados["definicao"] == DEFINICAO
    assert proposta.dados["ok"] is None
    assert proposta.dados["erros"] is None


async def test_validacao_com_erro_vira_proposta_mas_marcada():
    """O painel decide o que fazer; o serviço não esconde a definição.

    Quem reprova é a contagem, e ela vai junto — desligar o botão é decisão de
    interface, e esconder a definição tiraria da pessoa a chance de aplicar e
    corrigir à mão.
    """
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow")],
        resultados={"validate_workflow": _validou(ok=False, erros=2, avisos=0)},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("validate_workflow", {"definition": DEFINICAO})],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("faltam duas coisas")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    proposta = next(e for e in eventos if e.tipo == "proposta")
    assert proposta.dados["ok"] is False
    assert proposta.dados["erros"] == 2


# ── ContextVar: o defeito com a pior consequência ─────────────────────────────


async def test_o_ContextVar_volta_a_ficar_vazio_depois_da_conversa():
    """Sem o `reset`, o escopo sobrevive para a PRÓXIMA tarefa deste worker.

    Este é o teste que mata a mutação de apagar o `finally` de
    `_executar_ferramenta`: com ele fora, a variável fica preenchida aqui.
    """
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("search_nodes", {"query": "buffer"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("pronto")])),
        ]
    )

    assert ESCOPO_ATUAL.get() is None
    await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert ESCOPO_ATUAL.get() is None, "o escopo ficou pendurado depois da conversa"


async def test_o_ContextVar_volta_a_ficar_vazio_mesmo_quando_a_ferramenta_quebra():
    """O caminho de erro é o que costuma esquecer de limpar."""
    servidor = ServidorFalso(resultados={"search_nodes": RuntimeError("estourou")})
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("search_nodes", {"q": "x"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("segui em frente")])),
        ]
    )

    await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert ESCOPO_ATUAL.get() is None


async def test_duas_conversas_seguidas_nao_misturam_escopo():
    """A segunda conversa enxerga o escopo dela, não o resto da primeira."""
    servidor = ServidorFalso()
    for user_id in ("usr-a", "usr-b"):
        escopo = escopo_do_editor(user_id=user_id, username=user_id, workspace_ids={"ws-1"})
        cliente = ClienteFalso(
            [
                ([], _resposta(conteudo=[_chamada("search_nodes", {})], parada="tool_calls")),
                ([], _resposta(conteudo=[_texto("fim")])),
            ]
        )
        await _colher(_conversar(escopo=escopo, servidor=servidor, cliente=cliente))

    assert [e.user_id for e in servidor.escopos_vistos] == ["usr-a", "usr-b"]


async def test_a_ferramenta_e_o_catalogo_veem_o_escopo_de_quem_chamou():
    """`list_tools` filtra pelo mesmo `ContextVar` — é o que dá o catálogo certo."""
    servidor = ServidorFalso()
    escopo = escopo_do_editor(user_id="usr-7", username="ana", workspace_ids={"ws-3"})
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("search_nodes", {})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("fim")])),
        ]
    )

    await _colher(_conversar(escopo=escopo, servidor=servidor, cliente=cliente))

    assert servidor.escopo_no_list_tools is not None
    assert servidor.escopo_no_list_tools.user_id == "usr-7"
    assert servidor.escopos_vistos[0].user_id == "usr-7"


# ── Paridade com o MCP: a recusa é a mesma ────────────────────────────────────


async def test_recusa_de_ferramenta_vira_resultado_de_erro_e_nao_derruba_a_conversa():
    """`ToolError` é informação para o modelo corrigir, não exceção para o usuário.

    O corpo da recusa é o JSON que `erro()` monta — o mesmo que um cliente MCP
    externo recebe. Repassá-lo inteiro é o que permite ao modelo ler o `code` e
    o `hint` e mudar de rumo sozinho.
    """
    # Uma ferramenta que o portão DEIXA passar, para o teste medir a paridade da
    # recusa e não o portão (que tem testes próprios acima).
    recusa = ToolError(
        json.dumps(
            {
                "code": "forbidden",
                "message": "Você não tem papel de editor neste workspace.",
                "hint": "peça a quem administra o workspace",
            },
            ensure_ascii=False,
        )
    )
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow")], resultados={"validate_workflow": recusa}
    )
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("validate_workflow", {"definition": {}})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("não tenho permissão para isso")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    fins = [e for e in eventos if e.tipo == "ferramenta_fim"]
    assert fins and fins[0].dados["erro"] is True
    fim = eventos[-1]
    assert fim.tipo == "fim", "uma recusa não pode terminar a conversa em erro"
    resultado = fim.dados["transcrito"][2]["content"][0]
    assert resultado["is_error"] is True
    assert "forbidden" in resultado["content"]
    assert "papel de editor" in resultado["content"]


# ── A armadilha do argumento em stream ───────────────────────────────────────


async def test_resposta_truncada_por_max_tokens_nao_executa_ferramenta_nenhuma():
    """Argumento cortado no meio ainda parece bem formado — e gravá-lo destrói o fluxo.

    O argumento chega gota a gota. Uma definição que perdeu metade dos nós
    porque a geração bateu no teto pode ainda fechar como objeto JSON válido. A
    única defesa é a parada `length`, e é este teste que a mantém.
    """
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("create_workflow", {"name": "meio", "definition": {"nodes": []}})],
                    parada="length",
                ),
            )
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert servidor.chamadas == [], "uma resposta truncada não pode chegar a create_workflow"
    assert _o_erro(eventos)["code"] == "resposta_truncada"
    assert eventos[-1].tipo == "fim" and eventos[-1].dados["ok"] is False


async def test_o_transcrito_de_uma_conversa_interrompida_continua_retomavel():
    """Toda saída anormal acontece com a mensagem do modelo já na conversa.

    Se ela pedia ferramenta, sobra um `tool_use` órfão — e a API RECUSA um
    `tool_use` sem o `tool_result` correspondente. O efeito seria cruel e
    silencioso: a conversa parece salva, e a próxima mensagem que a pessoa
    mandar derruba tudo. Este teste é o que garante que o transcrito devolvido
    pode ser reenviado.
    """
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _texto("vou criar o fluxo"),
                        _chamada("create_workflow", {"name": "x"}, "tu-orfa"),
                    ],
                    parada="length",
                ),
            )
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))
    transcrito = eventos[-1].dados["transcrito"]

    pedidos = [
        b["id"]
        for m in transcrito
        if m["role"] == "assistant"
        for b in (m["content"] or [])
        if b.get("type") == "tool_use"
    ]
    respondidos = [
        b["tool_use_id"]
        for m in transcrito
        if m["role"] == "user" and isinstance(m["content"], list)
        for b in m["content"]
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    assert pedidos == ["tu-orfa"]
    assert respondidos == ["tu-orfa"], "o tool_use ficou sem resposta: a retomada seria recusada"
    # E o texto que o modelo chegou a escrever continua lá.
    assert any(
        b.get("type") == "text"
        for m in transcrito
        if m["role"] == "assistant"
        for b in (m["content"] or [])
    )


async def test_o_transcrito_sai_em_JSON_puro_e_o_raciocinio_mantem_os_detalhes():
    """O transcrito atravessa o Redis, e o bloco de raciocínio volta ao provedor.

    Duas invariantes num teste só, porque falham juntas: o transcrito tem de ser
    serializável (senão não há como guardá-lo) e o bloco de raciocínio tem de
    manter os `reasoning_details` VERBATIM (é o que o OpenRouter pede de volta
    para o modelo continuar o raciocínio na volta seguinte; perdê-los é perder o
    fio da conversa, do mesmo jeito cruel do `tool_use` órfão).
    """
    detalhes = [{"type": "reasoning.text", "text": "pensei", "signature": "assin-123", "index": 0}]
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        {"type": "thinking", "thinking": "pensei", "reasoning_details": detalhes},
                        _texto("pronto"),
                    ]
                ),
            )
        ]
    )

    eventos = await _colher(_conversar(cliente=cliente))
    transcrito = eventos[-1].dados["transcrito"]

    # Serializável: é isto que o Redis exige.
    json.dumps(transcrito, ensure_ascii=False)

    blocos = transcrito[1]["content"]
    assert all(isinstance(b, dict) for b in blocos)
    pensamento = next(b for b in blocos if b["type"] == "thinking")
    assert pensamento["reasoning_details"] == detalhes
    assert pensamento["thinking"] == "pensei"
    # E a volta seguinte o reenvia como veio: é o cliente que traduz, não o laço.
    [_, assistente] = openrouter.montar_mensagens([], transcrito)
    assert assistente["reasoning_details"] == detalhes


async def test_conversa_que_termina_bem_nao_ganha_resultado_inventado():
    """O fechamento de pendência só age quando há pendência — o contraponto."""
    cliente = ClienteFalso([([], _resposta(conteudo=[_texto("pronto")]))])

    eventos = await _colher(_conversar(cliente=cliente))
    transcrito = eventos[-1].dados["transcrito"]

    assert eventos[-1].dados["ok"] is True
    assert len(transcrito) == 2, "nada deve ser acrescentado a uma conversa que fechou sozinha"


async def test_argumento_que_nao_e_objeto_vira_erro_em_vez_de_chamada():
    """O cliente devolve o texto cru quando o JSON do argumento não fecha
    (`openrouter._argumentos`) — e o que não é objeto não pode virar chamada.
    """
    quebrado = _chamada("search_nodes", "definiti")
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[quebrado], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("refiz")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    assert servidor.chamadas == []
    fim = eventos[-1]
    assert fim.dados["transcrito"][2]["content"][0]["is_error"] is True


# ── Freios ────────────────────────────────────────────────────────────────────


async def test_o_teto_de_voltas_fecha_o_laco_sem_depender_do_redis():
    """O freio que não falha aberto: um ciclo de ferramentas gasta dinheiro de verdade."""
    servidor = ServidorFalso()
    voltas = [
        ([], _resposta(conteudo=[_chamada("search_nodes", {})], parada="tool_calls"))
        for _ in range(cs.TETO_DE_VOLTAS + 5)
    ]
    cliente = ClienteFalso(voltas)

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente, redis=None))

    assert _o_erro(eventos)["code"] == "loop_limit"
    # O numero vai a parte: a Home traduz a frase e precisa cita-lo.
    assert _o_erro(eventos)["teto"] == len(servidor.chamadas)
    assert eventos[-1].dados["ok"] is False
    assert len(servidor.chamadas) == cs.TETO_DE_VOLTAS


async def test_a_cota_estourada_recusa_antes_de_falar_com_o_modelo():
    """Recusar depois da chamada seria pagar a conta e jogar fora a resposta."""
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    cliente = ClienteFalso([])  # qualquer volta aqui é falha de teste

    with pytest.raises(ToolError) as exc:
        await _colher(_conversar(cliente=cliente, redis=redis))

    corpo = json.loads(str(exc.value))
    assert corpo["code"] == "rate_limited"
    assert cliente.parametros == []


async def test_o_teto_da_conversa_vem_do_PLANO_de_quem_fala(registro_de_teste):
    """O mesmo gasto que recusa no teto da instalação passa no plano maior — e o
    quadro `cota` mostra o teto do plano, não a constante global. O plano vem do
    registro das extensões.

    O teto aparece em quatro lugares (aqui, a checagem em `cotas.py` e os dois
    `/estado`); trocar só os endpoints faria o donut oscilar no meio do turno,
    mostrando o teto do plano ao abrir a tela e o da instalação durante a resposta.
    Por isso o laço resolve o plano UMA vez e o carrega até a cobrança.
    """
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    teto_do_plano = 10 * cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA

    async def plano_e_teto(user_id, *, db=None, redis=None):
        return "maior", teto_do_plano

    registro_de_teste.plano_e_teto = plano_e_teto

    eventos = await _colher(
        _conversar(
            servidor=ServidorFalso(),
            cliente=ClienteFalso([([], _resposta(conteudo=[_texto("fim")], uso=_uso(entrada=10, saida=5)))]),
            redis=redis,
        )
    )

    assert [e.dados["teto"] for e in eventos if e.tipo == "cota"] == [teto_do_plano]
    assert eventos[-1].tipo == "fim" and eventos[-1].dados["ok"] is True


async def test_o_uso_e_somado_e_cobrado_na_cota():
    """A cobrança é por token acumulado: tudo o que entrou (o cache já está dentro
    de `entrada`, e custa) mais tudo o que saiu."""
    redis = RedisFalso()
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("search_nodes", {})],
                    parada="tool_calls",
                    uso=_uso(entrada=1000, saida=200, cache_leitura=5000, cache_escrita=100),
                ),
            ),
            ([], _resposta(conteudo=[_texto("fim")], uso=_uso(entrada=10, saida=20))),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente, redis=redis))

    uso = eventos[-1].dados["uso"]
    assert uso["entrada"] == 1010
    assert uso["saida"] == 220
    assert uso["cache_leitura"] == 5000
    assert uso["cache_escrita"] == 100
    assert uso["total"] == 1010 + 220
    assert redis.dados["assistente:tokens:usr-1"] == uso["total"]
    # A janela precisa ter prazo, senão o usuário perde o assistente para sempre.
    assert redis.ttls["assistente:tokens:usr-1"] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_o_acumulado_da_cota_vai_ao_stream_a_cada_resposta_do_modelo():
    """O donut sobe DURANTE o turno: depois de cada resposta do modelo sai um
    quadro `cota` com o acumulado da janela (o que o INCRBY devolveu) e o teto —
    antes de a ferramenta rodar, e o `fim` continua sendo o último. Sem Redis
    não há contador, e não há quadro."""
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = 500
    respostas = [
        ([], _resposta(conteudo=[_chamada("search_nodes", {})], parada="tool_calls", uso=_uso(entrada=100, saida=20))),
        ([], _resposta(conteudo=[_texto("fim")], uso=_uso(entrada=10, saida=5))),
    ]

    eventos = await _colher(_conversar(servidor=ServidorFalso(), cliente=ClienteFalso(list(respostas)), redis=redis))

    teto = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    assert [e.dados for e in eventos if e.tipo == "cota"] == [
        {"gasto": 620, "teto": teto},
        {"gasto": 635, "teto": teto},
    ]
    tipos = [e.tipo for e in eventos]
    assert tipos.index("cota") < tipos.index("ferramenta")
    assert tipos[-1] == "fim"

    sem_redis = await _colher(_conversar(servidor=ServidorFalso(), cliente=ClienteFalso(list(respostas)), redis=None))
    assert "cota" not in [e.tipo for e in sem_redis]


# ── O que sai no SSE ──────────────────────────────────────────────────────────


async def test_o_progresso_da_execucao_vira_quadro_no_SSE():
    """`run_workflow` é a única ferramenta que usa o `ctx`, e é para isto."""

    async def executando(context):
        await context.report_progress(2, 5, "buffer: completed (1.2s)")
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"run_id": "r-1"}')],
            structured_content=None,
            is_error=False,
        )

    servidor = ServidorFalso(
        tools=[_ToolFalsa("run_workflow")], resultados={"run_workflow": executando}
    )
    # Desenha ANTES de executar: `run_workflow` e recusado enquanto nao houver
    # fluxo no canvas, que e o portao contra "executar para responder com dado".
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": {"nodes": [], "edges": []}})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_chamada("run_workflow", {"workflow_id": "w1"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("rodou")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    progresso = [e for e in eventos if e.tipo == "progresso"]
    assert progresso, "o andamento nó a nó não chegou ao SSE"
    assert progresso[0].dados == {
        "concluidos": 2,
        "total": 5,
        "mensagem": "buffer: completed (1.2s)",
        # O id da chamada dona: com as ferramentas da volta em paralelo, é por
        # ele que o navegador pinta a barra no card certo.
        "id": "tu-1",
    }
    # E na ordem certa: o progresso vem antes do fim da ferramenta QUE O EMITIU.
    # `index` cru olharia para o `ferramenta_fim` do desenho, que acontece antes
    # de a execucao comecar — e passaria por acidente, medindo outra coisa.
    tipos = [e.tipo for e in eventos]
    i_progresso = tipos.index("progresso")
    fins_depois = [i for i, t in enumerate(tipos) if t == "ferramenta_fim" and i > i_progresso]
    assert fins_depois, "o progresso saiu depois do fim da execucao"


async def test_texto_e_pensamento_saem_em_quadros_distintos():
    cliente = ClienteFalso(
        [
            (
                [
                    openrouter.Delta("pensando", "preciso do catálogo"),
                    openrouter.Delta("texto", "Vou montar"),
                ],
                _resposta(conteudo=[_texto("Vou montar")]),
            )
        ]
    )

    eventos = await _colher(_conversar(cliente=cliente))

    assert [e.tipo for e in eventos[:2]] == ["pensando", "texto"]
    assert eventos[0].dados["texto"] == "preciso do catálogo"
    assert eventos[1].dados["texto"] == "Vou montar"


async def test_os_resultados_das_ferramentas_vao_numa_unica_mensagem():
    """Dividir em várias ensina o modelo, em silêncio, a parar de pedir em paralelo."""
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada("search_nodes", {"query": "buffer"}, "tu-1"),
                        _chamada("search_nodes", {"query": "dissolve"}, "tu-2"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("achei os dois")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    transcrito = eventos[-1].dados["transcrito"]
    mensagens_de_resultado = [
        m
        for m in transcrito
        if m["role"] == "user"
        and isinstance(m["content"], list)
        and m["content"]
        and isinstance(m["content"][0], dict)
        and m["content"][0].get("type") == "tool_result"
    ]
    assert len(mensagens_de_resultado) == 1
    assert [r["tool_use_id"] for r in mensagens_de_resultado[0]["content"]] == ["tu-1", "tu-2"]


async def test_o_resumo_da_chamada_nao_vaza_o_conteudo_do_argumento():
    """O quadro do SSE é log de alguém em algum momento — e o argumento leva a definição."""
    resumo = cs._resumo(
        {
            "workflow_id": "w-1",
            "definition": {"nodes": [1, 2, 3], "edges": []},
            "change_note": "x" * 400,
        }
    )

    assert resumo["workflow_id"] == "w-1"
    assert resumo["definition"] == {"__campos__": 2}
    assert "nodes" not in json.dumps(resumo)
    assert len(resumo["change_note"]) <= 120


async def test_resultado_gigante_e_cortado_com_aviso():
    """Cortar em silêncio faria o modelo concluir que o dado não existe."""
    gigante = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="a" * (cs.MAX_CHARS_POR_RESULTADO + 500))],
        structured_content=None,
        is_error=False,
    )

    texto = cs._texto_do_resultado(gigante)

    assert len(texto) == cs.MAX_CHARS_POR_RESULTADO + len(cs.AVISO_DE_CORTE)
    assert texto.endswith(cs.AVISO_DE_CORTE)


# ── Parâmetros da chamada ao modelo ───────────────────────────────────────────


async def test_a_chamada_ao_modelo_leva_modelo_esforco_sistema_e_transcrito():
    """O laço entrega ao cliente exatamente o que ele traduz: o modelo da
    configuração, o esforço de raciocínio alto, o sistema com o ponto de corte de
    cache e o transcrito inteiro."""
    cliente = ClienteFalso([([], _resposta())])

    await _colher(_conversar(cliente=cliente))

    from app.core.config import ASSISTENTE_MODELO

    params = cliente.parametros[0]
    # O modelo vem da configuração: trocá-lo é editar o `.env`, não fazer deploy.
    assert params["modelo"] == ASSISTENTE_MODELO
    assert params["esforco"] == cs.ESFORCO_DO_RACIOCINIO == "high"
    assert params["max_tokens"] == cs.MAX_TOKENS
    # O sistema é o de `montar_sistema`, com o corte de cache no último bloco.
    assert params["sistema"] == cs.montar_sistema()
    assert params["sistema"][-1]["cache_control"] == {"type": "ephemeral"}
    # E o transcrito vai INTEIRO, no formato do projeto — a tradução é do cliente.
    assert params["conversa"] == [{"role": "user", "content": "monta um fluxo"}]


async def test_as_ferramentas_saem_no_formato_function_com_o_esquema_do_MCP():
    servidor = ServidorFalso(
        tools=[_ToolFalsa("validate_workflow", "valida", {"type": "object", "required": ["definition"]})]
    )
    cliente = ClienteFalso([([], _resposta())])

    await _colher(_conversar(servidor=servidor, cliente=cliente))

    ferramentas = cliente.parametros[0]["ferramentas"]
    assert ferramentas[0]["function"]["name"] == cs.NOME_DO_DESENHO
    assert ferramentas[0]["function"]["parameters"] == cs.FERRAMENTA_DO_DESENHO["input_schema"]
    assert ferramentas[1:] == [
        {
            "type": "function",
            "function": {
                "name": "validate_workflow",
                "description": "valida",
                # O `input_schema` do MCP vai como está: mesmo esquema, sem tradução.
                "parameters": {"type": "object", "required": ["definition"]},
            },
        }
    ]


async def test_o_sistema_e_o_texto_do_MCP_e_nao_uma_segunda_politica():
    """Duas cópias da política divergem na primeira edição distraída.

    E o aviso de `untrusted_data` é o que separa "dado escrito por alguém do
    workspace" de "ordem para o modelo" — a defesa contra injeção por nome de
    fluxo ou mensagem de erro.
    """
    from app.mcp.instrucoes import INSTRUCOES

    blocos = cs.montar_sistema()

    assert blocos[0]["text"] == INSTRUCOES
    assert "untrusted_data" in blocos[0]["text"]
    assert "DADO" in blocos[0]["text"]


async def test_o_sistema_pede_resposta_E_raciocinio_no_idioma_configurado(monkeypatch):
    """O raciocínio é mostrado à pessoa (a seção "Raciocínio" do painel), e um
    modelo que conversa em português tende a pensar em inglês. Nenhuma API
    escolhe o idioma do raciocínio: pedir no sistema é o único controle."""
    from app.core import config

    monkeypatch.setattr(config, "ASSISTENTE_IDIOMA", "português do Brasil")
    idioma = [b["text"] for b in cs.montar_sistema() if "Responda sempre" in b["text"]]

    assert len(idioma) == 1
    assert "Responda sempre em português do Brasil" in idioma[0]
    assert "Raciocine também em português do Brasil" in idioma[0]


async def test_o_prefixo_estavel_tem_um_ponto_de_corte_de_cache():
    """O prefixo (~15k tokens: ferramentas + os blocos de sistema) e IDENTICO
    entre toda conversa e todo usuario. Sem um ponto de corte explicito, cada
    conversa nova reescreve o prefixo a preco cheio.

    O corte vai no ULTIMO bloco estavel — os anteriores nao levam marcador, para
    haver um so ponto de corte no sistema. So o tipo, sem TTL: a duracao e do
    provedor por tras do roteador.
    """
    blocos = cs.montar_sistema()

    # Exatamente um ponto de corte, e no ultimo bloco.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 1]
    assert blocos[-1]["cache_control"] == {"type": "ephemeral"}
    # O bloco marcado continua sendo o guia, com o texto intacto.
    assert blocos[-1]["text"] == cs._guia_do_prefixo()


async def test_instrucoes_extras_fica_fora_do_prefixo_cacheado():
    """`instrucoes_extras` e opcional e pode ser dinamico: nunca deve empurrar o
    ponto de corte para depois dele, nem entrar no prefixo cacheado. O corte fica
    no bloco do guia, e o extra vem depois, sem marcador."""
    blocos = cs.montar_sistema(instrucoes_extras="contexto so desta conversa")

    assert blocos[-1]["text"] == "contexto so desta conversa"
    assert "cache_control" not in blocos[-1]
    # O corte segue no guia — o penultimo bloco agora.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 2]
    assert blocos[com_corte[0]]["text"] == cs._guia_do_prefixo()


async def test_a_recusa_do_modelo_termina_a_conversa_como_recusado():
    """`content_filter` e o `finish_reason` normalizado do OpenRouter para recusa."""
    cliente = ClienteFalso([([], _resposta(parada="content_filter"))])

    eventos = await _colher(_conversar(cliente=cliente))

    erro = _o_erro(eventos)
    assert erro["code"] == "recusado"
    assert eventos[-1].dados["ok"] is False


@pytest.mark.parametrize("parada", ["content_filter", "stop"])
async def test_resposta_sem_bloco_nenhum_nao_entra_no_transcrito(parada):
    """Uma mensagem vazia do assistente é recusada pelo provedor em toda retomada,
    e não há nada nela para a pessoa ver. O transcrito fica como estava."""
    tamanhos: list[int] = []

    async def gancho(conversa):
        tamanhos.append(len(conversa))

    cliente = ClienteFalso([([], _resposta(conteudo=[], parada=parada))])

    eventos = await _colher(_conversar(cliente=cliente, ao_fechar_turno=gancho))

    transcrito = eventos[-1].dados["transcrito"]
    assert transcrito == [{"role": "user", "content": "monta um fluxo"}]
    assert tamanhos == [], "nada novo para persistir"
    assert eventos[-1].dados["ok"] is (parada == "stop")


async def test_falha_ao_falar_com_o_modelo_vira_erro_e_nao_excecao():
    class ClienteQuebrado(ClienteFalso):
        def transmitir(self, **kw):
            raise openrouter.ErroDoOpenRouter("falha de rede ao falar com o OpenRouter (sem rota)")

    eventos = await _colher(_conversar(cliente=ClienteQuebrado([])))

    erro = _o_erro(eventos)
    assert erro["code"] == "modelo_indisponivel"
    # Nunca o texto da exceção: ele carrega URL, host e às vezes cabeçalho.
    assert "sem rota" not in json.dumps(erro)


# ── Superfícies: o editor é o default, a Home passa o próprio pacote ──────────
# O import da superfície Home é LOCAL a cada teste: se um dia ela quebrar ao
# importar, quebram só estes testes, não os 59 acima que provam o editor.


async def test_o_sistema_da_home_troca_o_bloco_de_instrucoes_e_mantem_o_cache():
    """A superfície Home muda o bloco [1] (as instruções), e nada mais da forma."""
    from app.mcp.instrucoes import INSTRUCOES
    from app.services.assistente_superficie import HOME, INSTRUCOES_DA_HOME

    blocos = cs.montar_sistema(superficie=HOME)

    # [0] continua sendo a política do MCP — a mesma dos dois.
    assert blocos[0]["text"] == INSTRUCOES
    # [1] agora é o bloco da Home, e não o do editor.
    assert blocos[1]["text"] == INSTRUCOES_DA_HOME
    assert blocos[1]["text"] != cs.INSTRUCOES_DO_EDITOR
    # O corte de cache fica no último bloco (o guia), como no editor: dois
    # prefixos estáveis, um por superfície.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 1]
    assert blocos[-1]["cache_control"] == {"type": "ephemeral"}
    assert blocos[-1]["text"] == cs._guia_do_prefixo()


async def test_as_ferramentas_da_home_incluem_criar_e_abrem_com_o_globo():
    """A Home permite todo o catálogo (o que o editor bloqueia), e a entrega abre a lista."""
    from app.services.assistente_superficie import HOME, NOME_DO_GLOBO

    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("create_workflow"), _ToolFalsa("run_workflow")]
    )
    ferramentas = await cs.ferramentas_para_o_modelo(servidor, escopo_falso(), HOME)
    nomes = [f["function"]["name"] for f in ferramentas]

    # A entrega da Home abre a lista — o que o modelo lê primeiro.
    assert nomes[0] == NOME_DO_GLOBO
    # create_workflow ENTRA: no editor ele é barrado, na Home o portão é a
    # confirmação por clique, não a ausência da ferramenta.
    assert "create_workflow" in nomes
    assert "run_workflow" in nomes
    # E o desenho do editor NÃO aparece na Home — é o pacote da outra superfície.
    assert cs.NOME_DO_DESENHO not in nomes


async def test_o_gancho_ao_fechar_turno_e_chamado_com_a_conversa_crescendo():
    """O gancho de persistência incremental é chamado após cada mensagem entrar.

    O editor não passa gancho nenhum (é `None` e vira no-op); quem persiste
    conversa por conversa — o assistente da Home — recebe a conversa a cada turno.
    """
    servidor = ServidorFalso()
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("search_nodes", {})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("pronto")])),
        ]
    )
    tamanhos: list[int] = []

    async def gancho(conversa):
        tamanhos.append(len(conversa))

    await _colher(_conversar(servidor=servidor, cliente=cliente, ao_fechar_turno=gancho))

    # A conversa começa com 1 (a mensagem do usuário). Chamado após: o assistente
    # do turno 1 (2), os tool_results do turno 1 (3), o assistente do turno 2 (4).
    assert tamanhos == [2, 3, 4]


async def test_o_gancho_que_quebra_nao_derruba_a_conversa():
    """Falhar ao persistir não pode perder a resposta que já está no ar."""
    cliente = ClienteFalso([([], _resposta(conteudo=[_texto("pronto")]))])

    async def gancho(conversa):
        raise RuntimeError("banco fora")

    eventos = await _colher(_conversar(cliente=cliente, ao_fechar_turno=gancho))

    # A conversa termina bem, apesar do gancho ter estourado.
    assert eventos[-1].tipo == "fim"
    assert eventos[-1].dados["ok"] is True


# ── O despacho não pode quebrar a conversa ───────────────────────────────────
# Os estágios 1 e 2 (executor local, portão da superfície) corriam FORA de
# qualquer try — só `chamar_no_servidor` tinha a rede. Um `DetachedInstanceError`
# no portão da Home (ler um atributo ORM depois da sessão fechar) derrubava o
# stream inteiro, e deixava rastro: o `tool_use` já estava no transcrito e o
# `tool_result` nunca chegava, então a mensagem SEGUINTE batia num 400 da API.


def _superficie_que_quebra(*, no_portao: bool) -> cs.Superficie:
    async def _explode(*_a, **_kw):
        raise RuntimeError("defeito no pacote da superficie")

    async def _portao_ok(_estado, _nome, _args, _tool_use_id=None):
        return None

    return cs.Superficie(
        nome="teste",
        instrucoes="",
        ferramentas_extras=(),
        executores_locais={} if no_portao else {"search_nodes": _explode},
        permitida=lambda _n: True,
        portao=_explode if no_portao else _portao_ok,
        quadros_extras=lambda *_a: [],
    )


def _estado_nu() -> cs.EstadoDoLaco:
    async def _emitir(_ev):
        return None

    return cs.EstadoDoLaco(
        escopo=escopo_falso(scopes=ESCOPOS_DO_EDITOR),
        redis=None,
        conversa_id=None,
        emitir=_emitir,
    )


@pytest.mark.parametrize("no_portao", [True, False])
async def test_defeito_no_portao_ou_no_executor_local_vira_resultado_de_erro(no_portao):
    """Vira `(texto, True)` — nunca exceção que sobe e mata a conversa.

    Mutação: tirar o try/except do despacho faz o `RuntimeError` escapar e
    derruba os dois casos.
    """
    texto, deu_erro = await cs._executar_ferramenta(
        servidor=ServidorFalso(),
        escopo=escopo_falso(scopes=ESCOPOS_DO_EDITOR),
        nome="search_nodes",
        argumentos={"query": "x"},
        contexto=None,
        superficie=_superficie_que_quebra(no_portao=no_portao),
        estado=_estado_nu(),
    )

    assert deu_erro is True
    assert "search_nodes" in texto and "RuntimeError" in texto


async def test_recusa_declarada_pelo_portao_continua_chegando_ao_modelo():
    """O conserto não pode engolir o veredito: um portão que RECUSA segue recusando."""

    async def _recusa(_estado, _nome, _args, _tool_use_id=None):
        return ("nao pode", True)

    superficie = cs.Superficie(
        nome="teste", instrucoes="", ferramentas_extras=(), executores_locais={},
        permitida=lambda _n: True, portao=_recusa, quadros_extras=lambda *_a: [],
    )

    resultado = await cs._executar_ferramenta(
        servidor=ServidorFalso(),
        escopo=escopo_falso(scopes=ESCOPOS_DO_EDITOR),
        nome="search_nodes",
        argumentos={"query": "x"},
        contexto=None,
        superficie=superficie,
        estado=_estado_nu(),
    )

    assert resultado == ("nao pode", True)


async def test_as_respostas_rapidas_entram_na_lista_da_home_depois_do_globo():
    """A segunda ferramenta local da Home: na lista do modelo, logo depois da entrega."""
    from app.services.assistente_superficie import HOME, NOME_DAS_RESPOSTAS, NOME_DO_GLOBO

    servidor = ServidorFalso(tools=[_ToolFalsa("search_nodes")])
    ferramentas = await cs.ferramentas_para_o_modelo(servidor, escopo_falso(), HOME)
    nomes = [f["function"]["name"] for f in ferramentas]

    assert nomes[:2] == [NOME_DO_GLOBO, NOME_DAS_RESPOSTAS]


async def test_sugerir_respostas_nao_vai_ao_servidor_e_vira_quadro_depois_do_fim_da_ferramenta():
    """No laco da Home: `ferramenta` -> `ferramenta_fim` -> `respostas_rapidas`, sem
    `call_tool`; o `tool_result` fica no transcrito, que e o que o replay reusa."""
    from app.services.assistente_superficie import HOME, NOME_DAS_RESPOSTAS

    servidor = ServidorFalso(tools=[_ToolFalsa("search_nodes")])
    opcoes = ["Só os últimos 7 dias", "Cruzar com o CAR"]
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_texto("Achei 128 focos."), _chamada(NOME_DAS_RESPOSTAS, {"opcoes": opcoes})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_texto("Pronto.")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente, superficie=HOME))

    tipos = [e.tipo for e in eventos]
    i = tipos.index("respostas_rapidas")
    assert tipos[i - 2:i] == ["ferramenta", "ferramenta_fim"]
    assert eventos[i].dados == {"opcoes": opcoes}
    assert NOME_DAS_RESPOSTAS not in [nome for nome, _ in servidor.chamadas]
    transcrito = eventos[-1].dados["transcrito"]
    resultados = [
        b for m in transcrito if isinstance(m.get("content"), list)
        for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    assert resultados and resultados[-1]["is_error"] is False


# ── A trava se renova enquanto a secao corre (PR 5, #2) ───────────────────────


async def test_a_trava_renova_o_prazo_enquanto_a_secao_corre(monkeypatch):
    """A trava vence em `TTL_DA_TRAVA_S`, mas um turno longo (`TETO_DE_VOLTAS`
    voltas em `high`) passa disso. Sem renovar, ela venceria no meio e uma 2a aba
    entraria no MESMO transcrito. O watchdog reemite o EXPIRE enquanto corre."""
    monkeypatch.setattr(cs, "_INTERVALO_DE_RENOVACAO_DA_TRAVA_S", 0.01)
    redis = RedisFalso()
    chave = "assistente:trava:u:w"

    async with cs.trava_exclusiva(redis, chave):
        await asyncio.sleep(0.05)  # tempo para o watchdog reemitir o EXPIRE >= 1x

    assert ("expire", chave, cs.TTL_DA_TRAVA_S) in redis.chamadas, "o watchdog nao renovou"
    assert chave not in redis.dados  # e soltou ao sair


async def test_o_renovador_da_trava_morre_ao_soltar(monkeypatch):
    """O watchdog e cancelado no fim da secao: nao fica uma task viva reemitindo
    EXPIRE numa trava ja solta."""
    monkeypatch.setattr(cs, "_INTERVALO_DE_RENOVACAO_DA_TRAVA_S", 0.01)
    redis = RedisFalso()
    chave = "assistente:trava:u:w"

    async with cs.trava_exclusiva(redis, chave):
        pass  # sai imediatamente

    antes = len([c for c in redis.chamadas if c[0] == "expire"])
    await asyncio.sleep(0.05)  # se o renovador vivesse, reemitiria aqui
    depois = len([c for c in redis.chamadas if c[0] == "expire"])
    assert depois == antes, "o renovador continuou vivo apos a trava soltar"


# ── O progresso da ferramenta chega ao vivo, nao em buffer (PR 5, #5) ─────────


async def test_o_progresso_chega_ao_vivo_antes_de_a_ferramenta_terminar():
    """A ferramenta roda numa task e o laco cede o `report_progress` ENQUANTO ela
    ainda corre. Com a fila `list` antiga (drenada so depois do `await` da
    ferramenta), o progresso de um run longo ficava em buffer e chegava tudo de
    uma vez, no fim."""
    liberar = asyncio.Event()

    async def executando(context):
        await context.report_progress(1, 3, "a meio caminho")
        await liberar.wait()  # bloqueia a ferramenta ate o teste soltar
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text='{"run_id": "r-1"}')],
            structured_content=None,
            is_error=False,
        )

    servidor = ServidorFalso(
        tools=[_ToolFalsa("run_workflow")], resultados={"run_workflow": executando}
    )
    # Desenha ANTES de executar: `run_workflow` e recusado sem um fluxo no canvas.
    cliente = ClienteFalso(
        [
            ([], _resposta(
                conteudo=[_chamada(cs.NOME_DO_DESENHO, {"definition": {"nodes": [], "edges": []}})],
                parada="tool_calls",
            )),
            ([], _resposta(conteudo=[_chamada("run_workflow", {"workflow_id": "w1"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("rodou")])),
        ]
    )

    gen = _conversar(servidor=servidor, cliente=cliente)
    vistos = []
    try:
        # Drena ate o `progresso` SEM soltar a ferramenta. Com o fix ele chega (a
        # ferramenta esta parada no `liberar.wait()`); com a fila `list`, o
        # `__anext__` bloquearia aqui ate a ferramenta terminar -> TimeoutError.
        while True:
            evento = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
            vistos.append(evento)
            if evento.tipo == "progresso":
                break
    finally:
        liberar.set()  # solta a ferramenta mesmo se falhar, para nao vazar a task

    assert vistos[-1].tipo == "progresso"
    assert vistos[-1].dados == {"concluidos": 1, "total": 3, "mensagem": "a meio caminho", "id": "tu-1"}
    resto = [evento async for evento in gen]
    assert resto and resto[-1].tipo == "fim"


async def test_cada_volta_e_registrada_no_uso_com_o_modelo_que_a_produziu():
    """O registro acompanha a COBRANÇA da cota, volta a volta.

    Dois motivos, e os dois são sobre não perder dinheiro de vista: gravar no
    mesmo ponto faz a cota e o livro de consumo contarem a mesma coisa, e uma
    conversa abandonada no meio (aba fechada, stream morto) já deixa registrado
    o que gastou até ali. Somar só no fim perderia justamente essas — e
    perderia para BAIXO, que numa tabela de custo é o lado errado de errar.

    O `modelo` vai junto porque esta tabela existe, entre outras coisas, para
    comparar antes e depois de uma troca de modelo. Deduzi-lo na leitura, do
    que estiver configurado naquele momento, tornaria a comparação impossível.
    """
    registradas: list[dict] = []

    async def _registrar(**kw):
        registradas.append(kw)

    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[_chamada("search_nodes", {})],
                    parada="tool_calls",
                    uso=_uso(entrada=1000, saida=200, cache_leitura=800),
                ),
            ),
            ([], _resposta(conteudo=[_texto("fim")], uso=_uso(entrada=10, saida=20))),
        ]
    )

    with patch("app.services.uso_service.registrar_volta", _registrar):
        await _colher(_conversar(servidor=ServidorFalso(), cliente=cliente, redis=RedisFalso()))

    assert len(registradas) == 2, "uma linha por volta, não uma por conversa"
    assert [(r["entrada"], r["saida"]) for r in registradas] == [(1000, 200), (10, 20)]
    assert registradas[0]["cache_leitura"] == 800
    assert all(r["modelo"] for r in registradas), "sem o modelo a linha não compara nada"
    assert all(r["user_id"] == "usr-1" for r in registradas)


# ── Ferramentas em paralelo na mesma volta ───────────────────────────────────
# O modelo pede varias fichas de uma vez e a volta custa a ferramenta mais
# lenta, nao a soma. A pista paralela so vale quando NAO ha ferramenta local no
# lote: o desenho muta `estado.desenhou`, e a ordem com `run_workflow` importa.


def _resultado_ok(texto="ok"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=texto)],
        structured_content=None,
        is_error=False,
    )


def _blocos_de_resultado(cliente) -> list[dict]:
    """Os `tool_result` que o modelo recebeu na volta seguinte ao lote."""
    conversa = cliente.parametros[-1]["conversa"]
    do_lote = [m for m in conversa if m.get("role") == "user" and isinstance(m.get("content"), list)]
    assert do_lote, "nenhuma mensagem de tool_result chegou ao modelo"
    return do_lote[-1]["content"]


async def test_ferramentas_da_mesma_volta_rodam_juntas_e_respondem_na_ordem():
    """Cada chamada do lote só termina quando as TRÊS começaram.

    Na pista sequencial a primeira esperaria as outras para sempre — o timeout
    do dublê viraria resultado de erro e o teste falharia. Na paralela, todas
    se encontram, e os `tool_result` voltam NA ORDEM dos `tool_use`, seja qual
    for a ordem de término.
    """
    juntas = asyncio.Event()
    comecaram = 0

    def _sincronizada(nome):
        async def _corre(_ctx):
            nonlocal comecaram
            comecaram += 1
            if comecaram == 3:
                juntas.set()
            await asyncio.wait_for(juntas.wait(), timeout=2)
            return _resultado_ok(f"{nome} pronto")

        return _corre

    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("describe_node"), _ToolFalsa("get_authoring_guide")],
        resultados={
            "search_nodes": _sincronizada("search_nodes"),
            "describe_node": _sincronizada("describe_node"),
            "get_authoring_guide": _sincronizada("get_authoring_guide"),
        },
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada("search_nodes", {"query": "x"}, "tu-1"),
                        _chamada("describe_node", {"name": "Buffer"}, "tu-2"),
                        _chamada("get_authoring_guide", {"topic": "overview"}, "tu-3"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("feito")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    # Anuncia o lote INTEIRO antes do primeiro fim: o navegador vê os três
    # cards correndo juntos.
    tipos_e_ids = [(e.tipo, e.dados.get("id")) for e in eventos if e.tipo in ("ferramenta", "ferramenta_fim")]
    anuncios = [par for par in tipos_e_ids if par[0] == "ferramenta"]
    primeiro_fim = tipos_e_ids.index(next(par for par in tipos_e_ids if par[0] == "ferramenta_fim"))
    assert [ident for _, ident in anuncios] == ["tu-1", "tu-2", "tu-3"]
    assert all(tipos_e_ids.index(par) < primeiro_fim for par in anuncios)

    resultados = _blocos_de_resultado(cliente)
    assert [r["tool_use_id"] for r in resultados] == ["tu-1", "tu-2", "tu-3"]
    assert all(r["is_error"] is False for r in resultados), (
        "alguma ferramenta estourou o timeout do dublê — o lote não rodou junto"
    )


async def test_progresso_do_lote_carrega_o_id_da_chamada_dona():
    """Com várias ferramentas correndo, o quadro `progresso` diz de quem é."""

    async def _com_progresso(ctx):
        await ctx.report_progress(1, 2, "andando")
        return _resultado_ok("fim")

    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("describe_node")],
        resultados={"search_nodes": "ok", "describe_node": _com_progresso},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada("search_nodes", {"query": "x"}, "tu-1"),
                        _chamada("describe_node", {"name": "Buffer"}, "tu-2"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("feito")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    progressos = [e.dados for e in eventos if e.tipo == "progresso"]
    assert progressos and progressos[0]["id"] == "tu-2"


async def test_o_portao_recebe_o_id_da_propria_chamada():
    """O contrato que mata a corrida: o id viaja com a chamada, não num campo
    compartilhado. Cada resultado do lote carrega o id que o portão viu."""
    vistos: set[str] = set()

    async def _portao(_estado, _nome, _args, tool_use_id):
        vistos.add(tool_use_id)
        return (f"aguardando {tool_use_id}", False)

    superficie = cs.Superficie(
        nome="teste",
        instrucoes="",
        ferramentas_extras=(),
        executores_locais={},
        permitida=lambda _n: True,
        portao=_portao,
        quadros_extras=lambda *_a: [],
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada("search_nodes", {"query": "a"}, "tu-A"),
                        _chamada("search_nodes", {"query": "b"}, "tu-B"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("feito")])),
        ]
    )

    await _colher(_conversar(cliente=cliente, superficie=superficie))

    assert vistos == {"tu-A", "tu-B"}
    resultados = _blocos_de_resultado(cliente)
    por_id = {r["tool_use_id"]: r["content"] for r in resultados}
    assert por_id["tu-A"] == "aguardando tu-A"
    assert por_id["tu-B"] == "aguardando tu-B"


async def test_volta_com_desenho_fica_em_fila_e_o_run_ve_o_desenho():
    """[desenho, run_workflow] na MESMA volta: a pista local preserva a ordem —
    o portão do run lê o `desenhou` que o desenho acabou de escrever."""
    servidor = ServidorFalso(
        tools=[_ToolFalsa("run_workflow")],
        resultados={"run_workflow": "rodou"},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada(
                            cs.NOME_DO_DESENHO,
                            {"definition": {"nodes": [{"id": "n1"}], "edges": []}},
                            "tu-1",
                        ),
                        _chamada("run_workflow", {"workflow_id": "wf-1"}, "tu-2"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("feito")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    # Em fila: o fim do desenho vem ANTES do anúncio do run.
    ordem = [(e.tipo, e.dados.get("id")) for e in eventos if e.tipo in ("ferramenta", "ferramenta_fim")]
    assert ordem == [
        ("ferramenta", "tu-1"),
        ("ferramenta_fim", "tu-1"),
        ("ferramenta", "tu-2"),
        ("ferramenta_fim", "tu-2"),
    ]
    # E o run passou no portão: o servidor foi tocado.
    assert [nome for nome, _ in servidor.chamadas] == ["run_workflow"]
    resultados = _blocos_de_resultado(cliente)
    assert all(r["is_error"] is False for r in resultados)


async def test_o_fim_do_rapido_nao_espera_o_lento_que_veio_depois():
    """Os fins saem NA ORDEM das chamadas, mas cada um assim que a própria task
    (e as anteriores) terminou — a task rápida fecha o card e entrega os quadros
    com a lenta ainda rodando. Com o dreno "todos os sentinelas primeiro", o
    primeiro fim só sairia depois da lenta — e este teste estoura o timeout."""
    liberar = asyncio.Event()

    async def _lento(_ctx):
        await liberar.wait()
        return _resultado_ok("lento pronto")

    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("describe_node")],
        resultados={"search_nodes": "rapido pronto", "describe_node": _lento},
    )
    cliente = ClienteFalso(
        [
            (
                [],
                _resposta(
                    conteudo=[
                        _chamada("search_nodes", {"query": "x"}, "tu-1"),
                        _chamada("describe_node", {"name": "Buffer"}, "tu-2"),
                    ],
                    parada="tool_calls",
                ),
            ),
            ([], _resposta(conteudo=[_texto("feito")])),
        ]
    )

    gen = _conversar(servidor=servidor, cliente=cliente)
    vistos = []
    try:
        while True:
            evento = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
            vistos.append(evento)
            if evento.tipo == "ferramenta_fim":
                break
    finally:
        liberar.set()  # solta a lenta mesmo se falhar, para não vazar a task

    assert vistos[-1].dados["id"] == "tu-1", "o fim do rápido esperou o lento"
    resto = [evento async for evento in gen]
    assert [e.dados["id"] for e in resto if e.tipo == "ferramenta_fim"] == ["tu-2"]
    assert resto[-1].tipo == "fim"
