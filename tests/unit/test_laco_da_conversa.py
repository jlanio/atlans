# tests/unit/test_laco_da_conversa.py
"""
The assistant loop (`conversar`), frame by frame and effect by effect.

Characterization: pins the sequence of frames the SSE delivers to the Home and the
editor (types, order, content) and the effects that happen between one frame and
the next — the model call, the usage record, the quota charge, the hook
that closes the turn, the tools — plus what the loop logs.

Frames are PULLED: nothing happens before the consumer asks for the next
frame. That is what makes cancellation by the client (the closed tab, which
cancels the SSE task) stop the loop exactly where it is — the tests at the
end of the file pin what runs and what doesn't in that case.
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
from app.mcp.escopo import EDITOR_SCOPES
from app.services import assistente_config_service, teto_do_assistente, uso_service
from app.services import assistente_service as cs
from app.services import assistente_superficie as agente
from app.services import openrouter

from ._mcp_harness import FakeRedis, fake_scope

pytestmark = pytest.mark.asyncio

MODEL = "fornecedor/modelo-de-teste"
TETO = 50_000
REQUEST = {"role": "user", "content": "monta um fluxo de buffer"}


def _usage(entrada, saida, cache_leitura=0, raciocinio=0, custo=0.0):
    return {"entrada": entrada, "saida": saida, "cache_leitura": cache_leitura,
            "cache_escrita": 0, "raciocinio": raciocinio, "custo": custo}


def _response(blocos, parada="stop", uso=None):
    return openrouter.Resposta(blocos=list(blocos), parada=parada, uso=uso or _usage(100, 20))


def _as_text(txt):
    return {"type": "text", "text": txt}


def _tool_call(nome, argumentos, ident):
    return {"type": "tool_use", "id": ident, "name": nome, "input": argumentos}


class _FakeModel:
    """The model, scripted: one script per round — `Delta`s, the `Resposta`, and
    where the script blocks (`asyncio.Event`) or breaks (exception)."""

    def __init__(self, linha, voltas):
        self.linha = linha
        self._turns = list(voltas)
        self.pedidos: list[dict] = []

    async def transmitir(self, **kw):
        self.pedidos.append(kw)
        self.linha.append(("modelo", len(kw["conversa"])))
        roteiro = self._turns.pop(0)
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


class _FakeServer:
    """The in-process MCP server, logging each call on the timeline."""

    def __init__(self, linha, ferramentas, resultados=None):
        self.linha = linha
        self._tools = list(ferramentas)
        self._results = dict(resultados or {})

    async def list_tools(self):
        self.linha.append(("list_tools",))
        return [
            SimpleNamespace(name=n, description=f"faz {n}", input_schema={"type": "object", "properties": {}})
            for n in self._tools
        ]

    async def call_tool(self, nome, argumentos, context=None):
        ident = getattr(context, "_ferramenta_id", None)
        self.linha.append(("call_tool", nome, ident))
        acao = self._results.get(nome, f"{nome} ok")
        if isinstance(acao, BaseException):
            raise acao
        texto = await acao(context) if callable(acao) else acao
        self.linha.append(("call_tool fim", nome, ident))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)], structured_content=None,
                               is_error=False)


@pytest.fixture
def linha(monkeypatch):
    """The timeline, with the preparation, the usage, the quota and the log recorded."""
    linha: list = []

    async def _ceiling_for(user_id, *, db=None, redis=None):
        linha.append(("teto_de", user_id))
        return TETO

    verificar = cotas.verificar_tokens_do_assistente
    cobrar = cotas.cobrar_tokens_do_assistente

    async def _check(redis, user_id, *, teto):
        linha.append(("verificar_tokens", user_id, teto))
        return await verificar(redis, user_id, teto=teto)

    async def _charge(redis, user_id, tokens):
        acumulado = await cobrar(redis, user_id, tokens)
        linha.append(("cobrar", tokens, acumulado))
        return acumulado

    async def _model_in_use(*, db=None, redis=None):
        linha.append(("modelo_em_uso",))
        return MODEL

    async def _registrar_volta(**kw):
        linha.append(("registrar_volta", kw))

    monkeypatch.setattr(teto_do_assistente, "teto_de", _ceiling_for)
    monkeypatch.setattr(cotas, "verificar_tokens_do_assistente", _check)
    monkeypatch.setattr(cotas, "cobrar_tokens_do_assistente", _charge)
    monkeypatch.setattr(assistente_config_service, "modelo_em_uso", _model_in_use)
    monkeypatch.setattr(uso_service, "registrar_volta", _registrar_volta)
    for nivel in ("debug", "info", "warning", "error", "exception"):
        monkeypatch.setattr(
            cs.logger, nivel, lambda msg, *args, _log_level=nivel, **_kw: linha.append(("log", _log_level, msg % args)),
        )
    return linha


def _hook(linha):
    async def _close_turn(conversa):
        linha.append(("gancho", len(conversa), conversa[-1]["role"]))

    return _close_turn


async def _consume(generator, linha):
    async for evento in generator:
        linha.append(("quadro", evento.tipo, evento.dados))


def _converse(linha, *, servidor, modelo, redis=None, **kw):
    return cs.conversar(
        escopo=fake_scope(scopes=EDITOR_SCOPES),
        transcrito=kw.pop("transcrito", [REQUEST]),
        servidor=servidor,
        cliente=modelo,
        redis=redis,
        **kw,
    )


SETUP = [("teto_de", "usr-1"), ("verificar_tokens", "usr-1", TETO), ("modelo_em_uso",), ("list_tools",)]


def _registro(entrada, saida, superficie="editor"):
    """What `uso_service.registrar_volta` receives in a round."""
    return ("registrar_volta", {
        "user_id": "usr-1", "modelo": MODEL, "superficie": superficie, "entrada": entrada,
        "saida": saida, "cache_leitura": 0, "raciocinio": 0, "custo_usd": 0.0,
    })


def _balance_log(voltas, tokens, superficie="editor"):
    return ("log", "info", f"Assistente: {voltas} volta(s), {tokens} tokens, US$ 0.0000 "
                           f"(usuário usr-1, superfície {superficie}).")


def _resultado(ident, texto, erro=False):
    return {"type": "tool_result", "tool_use_id": ident, "content": texto, "is_error": erro}


def _total_usage(entrada, saida):
    return {"entrada": entrada, "saida": saida, "cache_leitura": 0, "cache_escrita": 0,
            "raciocinio": 0, "custo": 0.0, "total": entrada + saida}


async def _wait_for(condicao, timeout_s=2.0):
    fim = asyncio.get_running_loop().time() + timeout_s
    while not condicao():
        assert asyncio.get_running_loop().time() < fim, "condição não ficou verdadeira a tempo"
        await asyncio.sleep(0.005)


# ── The happy path, on both surfaces ──────────────────────────────────────────


DEFINICAO = {"nodes": [{"id": "n1"}], "edges": []}
VALIDATED = '{"ok": true, "error_count": 0, "warning_count": 1}'


async def test_editor_frame_by_frame(linha):
    """Four rounds: parallel batch, queued lane (drawing + execution with
    progress), batch with one tool blocked, and the final text."""
    redis = FakeRedis()
    redis.dados["assistente:tokens:usr-1"] = 100

    async def _running(ctx):
        await ctx.report_progress(1, 2, "buffer: completed (0.3s)")
        return '{"run_id": "r-1"}'

    servidor = _FakeServer(
        linha,
        ["search_nodes", "describe_node", "validate_workflow", "run_workflow", "create_workflow"],
        {"run_workflow": _running, "validate_workflow": VALIDATED},
    )
    volta1 = [_as_text("Vou montar"), _tool_call("search_nodes", {"query": "buffer"}, "tu-1"),
              _tool_call("describe_node", {"name": "Buffer"}, "tu-2")]
    volta2 = [_tool_call(cs.NOME_DO_DESENHO, {"definition": DEFINICAO, "nota": " liguei o buffer "}, "tu-3"),
              _tool_call("run_workflow", {"workflow_id": "wf-1"}, "tu-4")]
    volta3 = [_tool_call("validate_workflow", {"definition": DEFINICAO}, "tu-5"),
              _tool_call("create_workflow", {"name": "x"}, "tu-6")]
    modelo = _FakeModel(linha, [
        [openrouter.Delta("pensando", "preciso do catálogo"), openrouter.Delta("texto", "Vou montar"),
         _response(volta1, "tool_calls")],
        [_response(volta2, "tool_calls", _usage(200, 30))],
        [_response(volta3, "tool_calls", _usage(300, 40))],
        [openrouter.Delta("texto", "Pronto."), _response([_as_text("Pronto.")], "stop", _usage(400, 50))],
    ])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, redis=redis,
                               ao_fechar_turno=_hook(linha)), linha)

    desenhado = ("Desenhado no canvas: 1 nó(s) e 0 aresta(s). A pessoa está vendo agora. Continue montando "
                 "e chame de novo a cada mudança; valide com `validate_workflow` quando o desenho estiver completo.")
    transcrito = [
        REQUEST,
        {"role": "assistant", "content": volta1},
        {"role": "user", "content": [_resultado("tu-1", "search_nodes ok"), _resultado("tu-2", "describe_node ok")]},
        {"role": "assistant", "content": volta2},
        {"role": "user", "content": [_resultado("tu-3", desenhado), _resultado("tu-4", '{"run_id": "r-1"}')]},
        {"role": "assistant", "content": volta3},
        {"role": "user", "content": [_resultado("tu-5", VALIDATED), _resultado("tu-6", cs.MENSAGEM_DO_PORTAO, True)]},
        {"role": "assistant", "content": [_as_text("Pronto.")]},
    ]
    assert linha == SETUP + [
        # Round 1: live reasoning and text; the parallel batch is announced whole.
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
        # Round 2: with a local tool in the batch, the round runs queued.
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
        # Round 3: the validation becomes a proposal with a verdict; the write is blocked.
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
        _balance_log(4, 1140),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _total_usage(1000, 140), "voltas": 4, "ok": True}),
    ]


async def test_home_frame_by_frame(linha, monkeypatch):
    """The Home: the confirmation goes out through the queue in the middle of the parallel
    batch, the created workflow becomes `fluxo`, and the local tool (quick replies) runs queued."""
    monkeypatch.setattr(agente.secrets, "token_urlsafe", lambda _n: "tok-fixo")
    redis = FakeRedis()
    criado = json.dumps({"id": "wf-9", "untrusted_data": {"name": "Focos"}})
    servidor = _FakeServer(linha, ["search_nodes", "create_workflow", "run_workflow", "cancel_run"],
                         {"create_workflow": criado})
    volta1 = [_tool_call("create_workflow", {"name": "Focos", "definition": {"nodes": []}}, "tu-1"),
              _tool_call("cancel_run", {"run_id": "run-9"}, "tu-2")]
    volta2 = [_tool_call(agente.NOME_DAS_RESPOSTAS, {"opcoes": ["Sim", "Não"]}, "tu-3")]
    modelo = _FakeModel(linha, [
        [_response(volta1, "tool_calls")],
        [_response(volta2, "tool_calls")],
        [_response([_as_text("Feito.")])],
    ])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, redis=redis, superficie=agente.HOME,
                               conversa_id="conv-1", ao_fechar_turno=_hook(linha)), linha)

    transcrito = [
        REQUEST,
        {"role": "assistant", "content": volta1},
        {"role": "user", "content": [_resultado("tu-1", criado), _resultado("tu-2", agente.AWAITING_MESSAGE)]},
        {"role": "assistant", "content": volta2},
        {"role": "user", "content": [_resultado(
            "tu-3", "Respostas rápidas na tela (2). Encerre o turno: a pessoa escolhe uma ou digita outra coisa.")]},
        {"role": "assistant", "content": [_as_text("Feito.")]},
    ]
    assert linha == SETUP + [
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
        _balance_log(3, 360, "home"),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _total_usage(300, 60), "voltas": 3, "ok": True}),
    ]


async def test_model_gets_live_chat_and_callers_transcript_stays_intact(linha):
    """Each round receives the same system, the same tools and the conversation
    that the loop keeps extending — a copy: the caller's list does not change."""
    transcrito = [REQUEST]
    servidor = _FakeServer(linha, ["search_nodes", "create_workflow"])
    modelo = _FakeModel(linha, [
        [_response([_tool_call("search_nodes", {}, "tu-1")], "tool_calls")],
        [_response([_as_text("ok")])],
    ])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, transcrito=transcrito), linha)

    primeiro, segundo = modelo.pedidos
    assert transcrito == [REQUEST]
    assert primeiro["conversa"] is segundo["conversa"] and primeiro["conversa"] is not transcrito
    assert primeiro["modelo"] == MODEL
    assert primeiro["sistema"] == cs.montar_sistema(None) and segundo["sistema"] is primeiro["sistema"]
    assert [f["function"]["name"] for f in primeiro["ferramentas"]] == [cs.NOME_DO_DESENHO, "search_nodes"]
    assert segundo["ferramentas"] is primeiro["ferramentas"]
    assert (primeiro["max_tokens"], primeiro["esforco"]) == (cs.MAX_TOKENS, cs.ESFORCO_DO_RACIOCINIO)


# ── The error exits ───────────────────────────────────────────────────────────


async def test_round_ceiling_closes_with_loop_limit(linha, monkeypatch):
    """Without Redis: no quota frame, no charge — and the in-memory ceiling applies."""
    monkeypatch.setattr(cs, "TETO_DE_VOLTAS", 2)
    servidor = _FakeServer(linha, ["search_nodes"])
    modelo = _FakeModel(linha, [
        [_response([_tool_call("search_nodes", {}, "tu-1")], "tool_calls")],
        [_response([_tool_call("search_nodes", {}, "tu-2")], "tool_calls")],
    ])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_hook(linha)), linha)

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
    assert linha[:-1] == SETUP + _volta(1, "tu-1") + _volta(3, "tu-2") + [
        ("log", "warning", "Assistente interrompido no teto de voltas (usuário usr-1, 240 tokens)."),
        ("quadro", "erro", {
            "code": "loop_limit",
            "message": "A conversa passou de 2 rodadas de ferramenta sem concluir.",
            "hint": "descreva o fluxo em partes menores, ou diga o que ficou faltando",
            "teto": 2,
        }),
        _balance_log(3, 240),
    ]
    assert fim[:2] == ("quadro", "fim")
    assert (fim[2]["voltas"], fim[2]["ok"], fim[2]["uso"]) == (3, False, _total_usage(200, 40))
    assert len(fim[2]["transcrito"]) == 5


class _ModelThatBreaksOnCall(_FakeModel):
    def transmitir(self, **kw):
        self.linha.append(("modelo", len(kw["conversa"])))
        raise openrouter.ErroDoOpenRouter("falha de rede ao falar com o OpenRouter (sem rota)")


MODEL_UNAVAILABLE = {
    "code": "modelo_indisponivel",
    "message": "Não consegui falar com o modelo agora.",
    "hint": "tente de novo em alguns instantes",
    "detalhe": "ErroDoOpenRouter",
}


@pytest.mark.parametrize("onde", ["no meio do stream", "sem a resposta final", "na chamada"])
async def test_model_failure_becomes_error_and_closes_chat(linha, onde):
    """What the model has already yielded stays on screen; the exception's text never
    goes into the frame (it carries URL and headers), only the class."""
    servidor = _FakeServer(linha, ["search_nodes"])
    if onde == "na chamada":
        modelo = _ModelThatBreaksOnCall(linha, [])
        live = []
    elif onde == "no meio do stream":
        modelo = _FakeModel(linha, [[openrouter.Delta("texto", "Vou"),
                                  openrouter.ErroDoOpenRouter("falha de rede (sem rota)")]])
        live = [("quadro", "texto", {"texto": "Vou"}), ("stream fechado",)]
    else:
        modelo = _FakeModel(linha, [[openrouter.Delta("pensando", "hm")]])
        live = [("quadro", "pensando", {"texto": "hm"}), ("stream fechado",)]

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, redis=FakeRedis(),
                               ao_fechar_turno=_hook(linha)), linha)

    assert linha == SETUP + [("modelo", 1)] + live + [
        ("log", "exception", "Falha ao falar com o modelo (usuário usr-1)."),
        ("quadro", "erro", MODEL_UNAVAILABLE),
        _balance_log(1, 0),
        ("quadro", "fim", {"transcrito": [REQUEST], "uso": _total_usage(0, 0), "voltas": 1, "ok": False}),
    ]


PENDING = "A chamada não chegou a acontecer: a conversa foi interrompida."


@pytest.mark.parametrize("parada", ["content_filter", "length"])
async def test_model_refusal_or_cutoff_closes_chat_without_running_call(linha, parada):
    """The message goes in (and the turn closes) before the error; the requested call does
    not run, and the returned transcript answers it so it stays resumable."""
    blocos = [_as_text("vou criar"), _tool_call("create_workflow", {"name": "x"}, "tu-1")]
    servidor = _FakeServer(linha, ["create_workflow"])
    modelo = _FakeModel(linha, [[_response(blocos, parada, _usage(50, 5))]])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, redis=FakeRedis(),
                               ao_fechar_turno=_hook(linha)), linha)

    if parada == "content_filter":
        corte = [("quadro", "erro", {"code": "recusado", "message": "O modelo recusou este pedido."})]
    else:
        corte = [
            ("log", "warning", "Assistente cortado por max_tokens (usuário usr-1)."),
            ("quadro", "erro", {"code": "resposta_truncada",
                                "message": "A resposta foi cortada no meio e não é segura de aplicar.",
                                "hint": "peça o fluxo em partes menores"}),
        ]
    transcrito = [REQUEST, {"role": "assistant", "content": blocos},
                  {"role": "user", "content": [_resultado("tu-1", PENDING, True)]}]
    assert linha == SETUP + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(50, 5),
        ("cobrar", 55, 55),
        ("quadro", "cota", {"gasto": 55, "teto": TETO}),
        ("gancho", 2, "assistant"),
        *corte,
        _balance_log(1, 55),
        ("quadro", "fim", {"transcrito": transcrito, "uso": _total_usage(50, 5), "voltas": 1, "ok": False}),
    ]


@pytest.mark.parametrize("parada", ["stop", "content_filter"])
async def test_response_without_any_block_does_not_enter_chat(linha, parada):
    servidor = _FakeServer(linha, [])
    modelo = _FakeModel(linha, [[_response([], parada)]])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, redis=FakeRedis(),
                               ao_fechar_turno=_hook(linha)), linha)

    recusa = [("quadro", "erro", {"code": "recusado", "message": "O modelo recusou este pedido."})]
    assert linha == SETUP + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, 120),
        ("quadro", "cota", {"gasto": 120, "teto": TETO}),
        ("log", "warning", f"Modelo devolveu uma resposta sem conteúdo (parada={parada}, usuário usr-1)."),
        *(recusa if parada == "content_filter" else []),
        _balance_log(1, 120),
        ("quadro", "fim", {"transcrito": [REQUEST], "uso": _total_usage(100, 20), "voltas": 1,
                           "ok": parada == "stop"}),
    ]


async def test_tool_request_without_any_call_ends_cleanly(linha):
    servidor = _FakeServer(linha, [])
    modelo = _FakeModel(linha, [[_response([_as_text("hm")], "tool_calls")]])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_hook(linha)), linha)

    assert linha[len(SETUP):] == [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, None),
        ("gancho", 2, "assistant"),
        _balance_log(1, 120),
        ("quadro", "fim", {"transcrito": [REQUEST, {"role": "assistant", "content": [_as_text("hm")]}],
                           "uso": _total_usage(100, 20), "voltas": 1, "ok": True}),
    ]


async def test_breaking_hook_logs_and_chat_continues(linha):
    async def _broken_import(conversa):
        linha.append(("gancho", len(conversa)))
        raise RuntimeError("banco fora")

    servidor = _FakeServer(linha, ["search_nodes"])
    modelo = _FakeModel(linha, [
        [_response([_tool_call("search_nodes", {}, "tu-1")], "tool_calls")],
        [_response([_as_text("ok")])],
    ])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_broken_import), linha)

    hooks = [e for e in linha if e[0] == "gancho" or e[:2] == ("log", "exception")]
    assert hooks == [
        ("gancho", 2), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
        ("gancho", 3), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
        ("gancho", 4), ("log", "exception", "Falha no gancho ao_fechar_turno (usuário usr-1)."),
    ]
    assert linha[-1][2]["ok"] is True


async def test_batch_tool_errors_become_error_results(linha):
    """Declared refusal, crash, argument that is not an object, and the editor's
    gate: all become an error `tool_result`, and the conversation goes on."""
    recusa = ToolError(json.dumps({"code": "forbidden", "message": "sem papel"}))
    servidor = _FakeServer(linha, ["search_nodes", "describe_node", "get_authoring_guide", "run_workflow"],
                         {"search_nodes": recusa, "describe_node": RuntimeError("quebrou")})
    lote = [
        _tool_call("search_nodes", {"query": "x"}, "tu-1"),
        _tool_call("describe_node", {"name": "Buffer"}, "tu-2"),
        _tool_call("get_authoring_guide", "texto cru", "tu-3"),
        _tool_call("run_workflow", {"workflow_id": "wf-1"}, "tu-4"),
    ]
    modelo = _FakeModel(linha, [[_response(lote, "tool_calls")], [_response([_as_text("ok")])]])

    await _consume(_converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_hook(linha)), linha)

    anuncios = [
        ("quadro", "ferramenta", {"id": c["id"], "nome": c["name"], "argumentos": cs._summarize(c["input"])})
        for c in lote
    ]
    assert linha[len(SETUP):] == [
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
        _balance_log(2, 240),
        ("quadro", "fim", {
            "transcrito": [
                REQUEST,
                {"role": "assistant", "content": lote},
                {"role": "user", "content": [
                    _resultado("tu-1", str(recusa), True),
                    _resultado("tu-2", "A ferramenta describe_node falhou de forma inesperada (RuntimeError).", True),
                    _resultado("tu-3", "O argumento não chegou como objeto JSON. Refaça a chamada.", True),
                    _resultado("tu-4", cs.MENSAGEM_DE_EXECUTAR_ANTES, True),
                ]},
                {"role": "assistant", "content": [_as_text("ok")]},
            ],
            "uso": _total_usage(200, 40), "voltas": 2, "ok": True,
        }),
    ]


async def test_exceeded_quota_refuses_before_talking_to_model(linha):
    redis = FakeRedis()
    redis.dados["assistente:tokens:usr-1"] = TETO
    modelo = _FakeModel(linha, [])

    with pytest.raises(ToolError):
        await _consume(_converse(linha, servidor=_FakeServer(linha, []), modelo=modelo, redis=redis), linha)

    assert linha == SETUP[:2]


# ── Cancellation by the client ────────────────────────────────────────────────
# The closed tab cancels the task that pulls the frames (`com_batimento`): the
# CancelledError lands where the loop is waiting and propagates. No further
# effect happens; a tool that was already running finishes on its own.


async def test_cancelled_mid_stream_neither_charges_nor_closes_turn(linha):
    trava = asyncio.Event()
    modelo = _FakeModel(linha, [[openrouter.Delta("texto", "Vou"), trava]])
    consumo = asyncio.create_task(_consume(
        _converse(linha, servidor=_FakeServer(linha, []), modelo=modelo, redis=FakeRedis(),
                   ao_fechar_turno=_hook(linha)), linha))
    await _wait_for(lambda: ("quadro", "texto", {"texto": "Vou"}) in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    trava.set()
    await asyncio.sleep(0.01)

    assert linha == SETUP + [
        ("modelo", 1),
        ("quadro", "texto", {"texto": "Vou"}),
        ("stream fechado",),
        ("cancelado",),
    ]


async def test_cancelled_with_queued_tool_running_it_finishes_on_its_own(linha):
    liberar = asyncio.Event()

    async def _running(_ctx):
        await liberar.wait()
        return "rodou"

    servidor = _FakeServer(linha, ["run_workflow"], {"run_workflow": _running})
    modelo = _FakeModel(linha, [[_response([
        _tool_call(cs.NOME_DO_DESENHO, {"definition": DEFINICAO}, "tu-1"),
        _tool_call("run_workflow", {"workflow_id": "wf-1"}, "tu-2"),
    ], "tool_calls")]])
    consumo = asyncio.create_task(_consume(
        _converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_hook(linha)), linha))
    await _wait_for(lambda: ("call_tool", "run_workflow", "tu-2") in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    liberar.set()
    await _wait_for(lambda: ("call_tool fim", "run_workflow", "tu-2") in linha)
    await asyncio.sleep(0.01)

    assert linha[len(SETUP):] == [
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


async def test_cancelled_with_parallel_batch_running_all_finish_on_their_own(linha):
    liberar = asyncio.Event()

    async def _running(_ctx):
        await liberar.wait()
        return "pronto"

    servidor = _FakeServer(linha, ["search_nodes", "describe_node"],
                         {"search_nodes": _running, "describe_node": _running})
    modelo = _FakeModel(linha, [[_response([
        _tool_call("search_nodes", {}, "tu-1"), _tool_call("describe_node", {}, "tu-2"),
    ], "tool_calls")]])
    consumo = asyncio.create_task(_consume(
        _converse(linha, servidor=servidor, modelo=modelo, ao_fechar_turno=_hook(linha)), linha))
    await _wait_for(lambda: ("call_tool", "describe_node", "tu-2") in linha)

    consumo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumo
    linha.append(("cancelado",))
    liberar.set()
    await _wait_for(lambda: ("call_tool fim", "describe_node", "tu-2") in linha)
    await asyncio.sleep(0.01)

    assert linha[len(SETUP) + 5:] == [
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "search_nodes", "argumentos": {}}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "describe_node", "argumentos": {}}),
        ("call_tool", "search_nodes", "tu-1"),
        ("call_tool", "describe_node", "tu-2"),
        ("cancelado",),
        ("call_tool fim", "search_nodes", "tu-1"),
        ("call_tool fim", "describe_node", "tu-2"),
    ]


async def _pull_until(generator, linha, parar):
    """Pulls frames until `parar(evento)` and closes the generator there (`aclose`)."""
    async for evento in generator:
        linha.append(("quadro", evento.tipo, evento.dados))
        if parar(evento):
            break
    await generator.aclose()
    linha.append(("fechado",))


async def test_closed_after_quota_response_does_not_enter_chat(linha):
    """The hook only runs when the frame after the quota one is requested."""
    modelo = _FakeModel(linha, [[_response([_tool_call("search_nodes", {}, "tu-1")], "tool_calls")]])
    generator = _converse(linha, servidor=_FakeServer(linha, ["search_nodes"]), modelo=modelo, redis=FakeRedis(),
                         ao_fechar_turno=_hook(linha))

    await _pull_until(generator, linha, lambda e: e.tipo == "cota")
    await asyncio.sleep(0.01)

    assert linha == SETUP + [
        ("modelo", 1),
        ("stream fechado",),
        _registro(100, 20),
        ("cobrar", 120, 120),
        ("quadro", "cota", {"gasto": 120, "teto": TETO}),
        ("fechado",),
    ]


async def test_closed_on_queued_tool_announcement_it_does_not_run(linha):
    modelo = _FakeModel(linha, [[_response([
        _tool_call(cs.NOME_DO_DESENHO, {"definition": DEFINICAO}, "tu-1"),
        _tool_call("run_workflow", {"workflow_id": "wf-1"}, "tu-2"),
    ], "tool_calls")]])
    generator = _converse(linha, servidor=_FakeServer(linha, ["run_workflow"]), modelo=modelo,
                         ao_fechar_turno=_hook(linha))

    await _pull_until(generator, linha, lambda e: e.tipo == "ferramenta" and e.dados["id"] == "tu-2")
    await asyncio.sleep(0.01)

    assert linha[-3:] == [
        ("quadro", "proposta", {"definicao": DEFINICAO, "nos": 1, "arestas": 0, "desenhar": True}),
        ("quadro", "ferramenta", {"id": "tu-2", "nome": "run_workflow", "argumentos": {"workflow_id": "wf-1"}}),
        ("fechado",),
    ]


async def test_closed_on_batch_announcement_none_runs(linha):
    modelo = _FakeModel(linha, [[_response([
        _tool_call("search_nodes", {}, "tu-1"), _tool_call("describe_node", {}, "tu-2"),
    ], "tool_calls")]])
    generator = _converse(linha, servidor=_FakeServer(linha, ["search_nodes", "describe_node"]), modelo=modelo,
                         ao_fechar_turno=_hook(linha))

    await _pull_until(generator, linha, lambda e: e.tipo == "ferramenta")
    await asyncio.sleep(0.01)

    assert linha[-3:] == [
        ("gancho", 2, "assistant"),
        ("quadro", "ferramenta", {"id": "tu-1", "nome": "search_nodes", "argumentos": {}}),
        ("fechado",),
    ]


async def test_closed_mid_stream_model_stream_also_closes(linha):
    modelo = _FakeModel(linha, [[openrouter.Delta("texto", "Vou"), openrouter.Delta("texto", " montar"),
                              _response([_as_text("Vou montar")])]])
    generator = _converse(linha, servidor=_FakeServer(linha, []), modelo=modelo, redis=FakeRedis(),
                         ao_fechar_turno=_hook(linha))

    await _pull_until(generator, linha, lambda e: e.tipo == "texto")
    await _wait_for(lambda: ("stream fechado",) in linha)

    assert linha == SETUP + [
        ("modelo", 1),
        ("quadro", "texto", {"texto": "Vou"}),
        ("fechado",),
        ("stream fechado",),
    ]


# ── Memory and order of the preparation ───────────────────────────────────────


async def test_loop_leaves_memory_with_stream_without_cyclic_collector(linha, monkeypatch):
    """Once the conversation ends, the loop (the whole conversation, the catalog, the client)
    leaves memory through reference counting, like the closures of the earlier
    generator. With the tools channel as a bound method of the loop, stored in the
    state and in each tool's context, the loop sat in a cycle that only the
    cyclic collector breaks: in generation 2, well after the end."""
    vivos = []

    class _Spied(cs.LacoDaConversa):
        def __init__(self, **kw):
            super().__init__(**kw)
            vivos.append(weakref.ref(self))

    monkeypatch.setattr(cs, "LacoDaConversa", _Spied)
    modelo = _FakeModel(linha, [
        [_response([_tool_call("search_nodes", {}, "tu-1")], parada="tool_calls", uso=_usage(10, 1))],
        [_response([_as_text("ok")], uso=_usage(10, 1))],
    ])
    gc.collect()
    gc.disable()
    try:
        await _consume(_converse(linha, servidor=_FakeServer(linha, ["search_nodes"]), modelo=modelo), linha)
        assert ("call_tool fim", "search_nodes", "tu-1") in linha
        assert [q for q in linha if q[0] == "quadro"][-1][1] == "fim"
        assert len(vivos) == 1 and vivos[0]() is None
    finally:
        gc.enable()


async def test_malformed_transcript_with_exceeded_quota_gives_quota_refusal(linha):
    """The tools' state is born at the end of the preparation, as before: a transcript
    item that is not an object is only read after the quota, and the refusal by
    quota (the one the route knows how to show) comes first."""
    redis = FakeRedis()
    redis.dados["assistente:tokens:usr-1"] = TETO

    with pytest.raises(ToolError):
        await _consume(
            _converse(
                linha, servidor=_FakeServer(linha, []), modelo=_FakeModel(linha, []), redis=redis,
                transcrito=["não sou um objeto", REQUEST],
            ),
            linha,
        )

    assert linha == SETUP[:2]
