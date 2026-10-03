# tests/unit/test_assistente_service.py
"""
The assistant loop — what it guarantees and what it refuses.

This file exists because of a design choice: the assistant calls the SAME MCP
tools, through the same `call_tool`, with the scope traveling in a `ContextVar`.
That gives the scope guard, the quota, the minimum role and auditing for free —
and creates exactly one possible new defect, which is the scope outliving the
call. The first two tests of the `ContextVar` block exist only for that, and
they are the ones that matter most in the file: a dangling scope is one user
seeing another's workspace.
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


# ── Doubles ───────────────────────────────────────────────────────────────────


def _uso(entrada=100, saida=50, cache_leitura=0, cache_escrita=0):
    """The `uso` as the OpenRouter client returns it: in the project's keys, with
    `entrada` already INCLUDING what came from the cache."""
    return {
        "entrada": entrada,
        "saida": saida,
        "cache_leitura": cache_leitura,
        "cache_escrita": cache_escrita,
        "raciocinio": 0,
        "custo": 0.0,
    }


def _texto(txt: str):
    """A text block in the project's format — the same one the client reassembles
    from the stream and that the transcript stores."""
    return {"type": "text", "text": txt}


def _chamada(nome: str, argumentos, ident: str = "tu-1"):
    return {"type": "tool_use", "id": ident, "name": nome, "input": argumentos}


def _resposta(*, conteudo=None, parada="stop", uso=None):
    return openrouter.Resposta(blocos=list(conteudo or []), parada=parada, uso=uso or _uso())


class ClienteFalso:
    """The model, scripted: one `(deltas, resposta)` per loop turn.

    It has the shape of `openrouter.ClienteOpenRouter`: `transmitir(**kw)` yields
    the `Delta`s and, last, the `Resposta`. Records the parameters of each turn.
    """

    def __init__(self, voltas):
        self._voltas = list(voltas)
        self.parametros: list[dict] = []

    async def transmitir(self, **kw):
        # Deep copy: the loop keeps mutating `conversa` after the call,
        # and the test wants to see what the client RECEIVED on that turn.
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
    """A `ServidorAtlans` the size of what the assistant uses.

    Records the scope it saw on each call — that is how the `ContextVar` tests
    observe what happened inside.
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
    # The module's contract: the last frame is ALWAYS `fim`, even when the
    # conversation ended badly — it is what carries the transcript. Checking it
    # here applies the rule to every test in the file at once.
    assert eventos and eventos[-1].tipo == "fim", "a conversa não terminou em `fim`"
    return eventos


def _o_erro(eventos) -> dict:
    """The conversation's error frame — and the guarantee that there was exactly one."""
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


# ── The assistant's scope ───────────────────────────────────────────────────────


async def test_o_escopo_do_editor_nao_carrega_os_escopos_destrutivos():
    """`triggers:manage` and `drive:write` were left out of v1, by the owner's decision.

    Deleting a schedule and deleting a Drive file destroy another workspace
    member's data, and "clean up the old schedules" is a sentence someone types
    without thinking. If they ever get in, let it be by choice — and this test is
    the place where the choice shows up.
    """
    assert "triggers:manage" not in ESCOPOS_DO_EDITOR
    assert "drive:write" not in ESCOPOS_DO_EDITOR
    assert {"workflows:read", "workflows:write", "runs:execute", "drive:read"} == set(
        ESCOPOS_DO_EDITOR
    )


async def test_o_escopo_do_editor_tem_balde_de_cota_separado_do_PAT():
    """The synthetic `token_id` is what separates the buckets and tags the audit."""
    escopo = escopo_do_editor(user_id="usr-9", username="ana", workspace_ids={"ws-1", "ws-2"})

    assert escopo.token_id == f"{PREFIXO_DO_EDITOR}:usr-9"
    assert escopo.token_prefix == PREFIXO_DO_EDITOR
    assert escopo.user_id == "usr-9"
    assert escopo.workspace_ids == frozenset({"ws-1", "ws-2"})
    # With no token restricting it, the reach is the user's — today and tomorrow.
    assert escopo.todos_os_workspaces is True
    # And never administrator, for the usual reason.
    assert escopo.como_usuario().role == "user"


# ── The write gate ────────────────────────────────────────────────────────────


async def test_a_regra_do_portao_sai_das_GUARDAS_e_nao_de_uma_lista_a_mao():
    """A hand-written list goes stale with the first new tool.

    The derived rule makes a write tool be born BLOCKED — failing closed. This
    test is what guarantees that the derivation matches the intent, and it is the
    one that breaks if someone adds an exception without thinking.
    """
    from app.mcp.guardas import GUARDAS

    bloqueadas = {n for n in GUARDAS if cs.bloqueada_no_editor(n)}
    escrevem = {n for n, g in GUARDAS.items() if not g.read_only}

    # Exactly the ones that write, minus the exceptions — not one more.
    assert bloqueadas == escrevem - cs.ESCREVEM_MAS_PASSAM
    # Validate and run (the original two) and the source catalog pair: probing
    # a WFS and registering it are the way for the assistant to find a new source.
    assert cs.ESCREVEM_MAS_PASSAM == {"validate_workflow", "run_workflow", "probe_source", "register_source"}

    # The ones that matter, named, so the diff shows the decision:
    for nome in ("create_workflow", "update_workflow", "set_workflow_active",
                 "set_portal_access", "restore_workflow_version", "duplicate_workflow"):
        assert cs.bloqueada_no_editor(nome), f"{nome} deveria estar barrada"

    # And the exceptions still pass, otherwise the assistant becomes useless.
    assert not cs.bloqueada_no_editor("validate_workflow")
    assert not cs.bloqueada_no_editor("run_workflow")
    assert not cs.bloqueada_no_editor("probe_source")
    assert not cs.bloqueada_no_editor("register_source")
    # Reads are never blocked.
    assert not cs.bloqueada_no_editor("search_nodes")


async def test_ferramenta_sem_guarda_nasce_bloqueada():
    """Fail closed: a name that isn't in GUARDAS doesn't run."""
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
    # The delivery opens the list: what the model reads first is what defines the
    # job. Buried among 38 others, it disappears from its reasoning.
    assert ferramentas[0]["function"]["name"] == cs.NOME_DO_DESENHO


async def test_o_portao_barra_no_DESPACHO_e_nao_so_na_lista():
    """The guarantee, not the comfort.

    Hiding it from the list keeps the model from WANTING the tool. Refusing here
    is what prevents it from RUNNING when the model names it anyway — because it
    read it in an example, because it hallucinated, or because someone ordered it
    in the text of a shared workflow. Without this refusal, the whole gate is
    decoration.

    `ServidorFalso` would gladly accept the call: if it got there, the workflow
    would be saved.
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
    # The refusal says what to do instead — otherwise the model tries again.
    assert "aplicar" in resultado["content"]


async def test_o_sistema_avisa_que_o_assistente_nao_grava():
    """`INSTRUCOES` says "call create_workflow after validating", and here that
    tool doesn't exist. Without the correction, the model looks for what isn't
    there and ends the conversation without delivering the workflow."""
    blocos = cs.montar_sistema()
    texto = "\n".join(b["text"] for b in blocos)

    assert "create_workflow" in cs.INSTRUCOES_DO_EDITOR
    assert "NAO grava" in texto
    # The delivery is named, and named EARLY: it is the difference between "I explain
    # the workflow" and "I put the workflow on the screen".
    assert cs.NOME_DO_DESENHO in texto
    assert "SUA ENTREGA E O FLUXO NO CANVAS" in texto
    # E o aval de execucao continua sendo pedido em texto.
    assert "pode rodar" in texto


async def test_o_roteiro_do_assistente_consulta_o_catalogo_antes_de_prospectar():
    """"Catalog first": for external data the step is `search_sources` ->
    `describe_source`, BEFORE `search_nodes`, the drawing and the validation;
    `probe_source`/`register_source` only come in when the catalog lacks the source."""
    texto = cs.INSTRUCOES_DO_EDITOR
    assert texto.index("search_sources") < texto.index("search_nodes") < texto.index("validate_workflow")
    assert texto.index("describe_source") < texto.index("probe_source") < texto.index("register_source")
    assert {"probe_source", "register_source"} <= cs.ESCREVEM_MAS_PASSAM


# ── The delivery: `desenhar_no_canvas` ───────────────────────────────────────

async def test_desenhar_poe_o_fluxo_na_tela_sem_precisar_validar():
    """The defect that motivated everything: putting it on the screen depended on the model VALIDATING.

    Before, the panel read the definition from the `validate_workflow` argument. A
    model that assembled and didn't validate — or that decided to execute and
    answer with the data — left the canvas empty. Now the delivery has its own
    name, and validating is a means again.
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
    """It is what makes the workflow incremental: the person watches it grow.

    A single drawing at the end would be the old behavior with a new name.
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
    """The canvas belongs to the editor: there is nothing for the server to execute.

    And it doesn't exist in MCP — an external client never sees it, because it
    has no canvas at all.
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
    """The model reads the error and corrects it — which is what should happen."""
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


# ── The execute-before-drawing gate ──────────────────────────────────────────

async def test_executar_antes_de_desenhar_e_recusado():
    """The path that produced the GeoJSON answer.

    Reading the Drive, running and returning the artifact fulfills the request
    without ever assembling anything — and since `run_workflow` was allowed from
    the start, it was the shortest path. Refusing until there is a workflow on the
    screen closes that door without taking execution out of scope.
    """
    servidor = ServidorFalso(tools=[_ToolFalsa("run_workflow")])
    cliente = ClienteFalso(
        [
            ([], _resposta(conteudo=[_chamada("run_workflow", {"workflow_id": "w1"})], parada="tool_calls")),
            ([], _resposta(conteudo=[_texto("ok, vou desenhar primeiro")])),
        ]
    )

    eventos = await _colher(_conversar(servidor=servidor, cliente=cliente))

    # By NAMES: `chamadas` stores `(nome, argumentos)` tuples, and comparing the
    # string against the list of tuples would always pass — a green that measures
    # nothing, which is exactly what happened in the first version of this test.
    assert "run_workflow" not in [nome for nome, _ in servidor.chamadas], (
        "executou antes de haver fluxo na tela"
    )
    fins = [e for e in eventos if e.tipo == "ferramenta_fim"]
    assert fins[0].dados["erro"] is True


async def test_depois_de_desenhar_a_execucao_passa():
    """The refusal is about ORDER, not scope: once drawn, it can run."""
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
    """The conversation is resumed across turns, and the workflow stays on the screen.

    An in-memory counter would say "hasn't drawn yet" in a conversation that
    already has a whole workflow drawn — and the person would get a senseless
    refusal when asking "now run it".
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


# ── The `proposta` frame: the bridge to the Apply button ──────────────────────


def _validou(ok=True, erros=0, avisos=1):
    """The envelope `validate_workflow` returns, in its real shape."""
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
    """Without this frame the "Aplicar" (Apply) button has nothing to apply.

    It is a deliberate exception to `_resumo`, which collapses every argument to
    keys and sizes. The definition has to go WHOLE because the write gate made
    Apply the only bridge between the conversation and the workflow.
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
    # And it comes AFTER the tool end: the panel only shows the card when the
    # timeline has already closed that step.
    tipos = [e.tipo for e in eventos]
    assert tipos.index("ferramenta_fim") < tipos.index("proposta")


async def test_so_a_validacao_produz_proposta():
    """The summary still applies to everything else — the stream is not a JSON dump."""
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
    """Applying what the tool rejected would be saving what didn't pass."""
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
    """If the report format changes, the panel loses the count and stays alive.

    An exception here would bring down the whole conversation because of a label.
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
    """The panel decides what to do; the service doesn't hide the definition.

    What fails it is the count, and it goes along — disabling the button is an
    interface decision, and hiding the definition would take from the person the
    chance to apply it and fix it by hand.
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


# ── ContextVar: the defect with the worst consequence ─────────────────────────


async def test_o_ContextVar_volta_a_ficar_vazio_depois_da_conversa():
    """Without the `reset`, the scope survives into this worker's NEXT task.

    This is the test that kills the mutation of deleting the `finally` of
    `_executar_ferramenta`: with it gone, the variable stays set here.
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
    """The error path is the one that usually forgets to clean up."""
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
    """The second conversation sees its own scope, not the leftovers of the first."""
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
    """`list_tools` filters by the same `ContextVar` — that is what gives the right catalog."""
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


# ── Parity with MCP: the refusal is the same ──────────────────────────────────


async def test_recusa_de_ferramenta_vira_resultado_de_erro_e_nao_derruba_a_conversa():
    """`ToolError` is information for the model to correct, not an exception for the user.

    The body of the refusal is the JSON that `erro()` builds — the same one an
    external MCP client receives. Passing it on whole is what lets the model read
    the `code` and the `hint` and change course on its own.
    """
    # A tool the gate LETS through, so the test measures the parity of the refusal
    # and not the gate (which has its own tests above).
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
    """An argument cut off midway still looks well-formed — and saving it destroys the workflow.

    The argument arrives drop by drop. A definition that lost half its nodes
    because generation hit the ceiling may still close as a valid JSON object. The
    only defense is the `length` stop, and this test is what keeps it.
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
    """Every abnormal exit happens with the model's message already in the conversation.

    If it asked for a tool, an orphaned `tool_use` is left over — and the API
    REJECTS a `tool_use` without the matching `tool_result`. The effect would be
    cruel and silent: the conversation looks saved, and the next message the
    person sends brings everything down. This test is what guarantees that the
    returned transcript can be resent.
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
    # And the text the model managed to write is still there.
    assert any(
        b.get("type") == "text"
        for m in transcrito
        if m["role"] == "assistant"
        for b in (m["content"] or [])
    )


async def test_o_transcrito_sai_em_JSON_puro_e_o_raciocinio_mantem_os_detalhes():
    """The transcript crosses Redis, and the reasoning block goes back to the provider.

    Two invariants in a single test, because they fail together: the transcript
    has to be serializable (otherwise there is no way to store it) and the
    reasoning block has to keep the `reasoning_details` VERBATIM (it is what
    OpenRouter asks back for the model to continue reasoning on the next turn;
    losing them is losing the thread of the conversation, in the same cruel way as
    the orphaned `tool_use`).
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

    # Serializable: this is what Redis requires.
    json.dumps(transcrito, ensure_ascii=False)

    blocos = transcrito[1]["content"]
    assert all(isinstance(b, dict) for b in blocos)
    pensamento = next(b for b in blocos if b["type"] == "thinking")
    assert pensamento["reasoning_details"] == detalhes
    assert pensamento["thinking"] == "pensei"
    # And the next turn resends it as it came: the client translates, not the loop.
    [_, assistente] = openrouter.montar_mensagens([], transcrito)
    assert assistente["reasoning_details"] == detalhes


async def test_conversa_que_termina_bem_nao_ganha_resultado_inventado():
    """Closing a pending item only acts when there is one pending — the counterpoint."""
    cliente = ClienteFalso([([], _resposta(conteudo=[_texto("pronto")]))])

    eventos = await _colher(_conversar(cliente=cliente))
    transcrito = eventos[-1].dados["transcrito"]

    assert eventos[-1].dados["ok"] is True
    assert len(transcrito) == 2, "nada deve ser acrescentado a uma conversa que fechou sozinha"


async def test_argumento_que_nao_e_objeto_vira_erro_em_vez_de_chamada():
    """The client returns the raw text when the argument's JSON doesn't close
    (`openrouter._argumentos`) — and what is not an object cannot become a call.
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
    """The brake that doesn't fail open: a tool cycle spends real money."""
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
    """Refusing after the call would be paying the bill and throwing away the answer."""
    redis = RedisFalso()
    redis.dados["assistente:tokens:usr-1"] = cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    cliente = ClienteFalso([])  # any turn here is a test failure

    with pytest.raises(ToolError) as exc:
        await _colher(_conversar(cliente=cliente, redis=redis))

    corpo = json.loads(str(exc.value))
    assert corpo["code"] == "rate_limited"
    assert cliente.parametros == []


async def test_o_teto_da_conversa_vem_do_PLANO_de_quem_fala(registro_de_teste):
    """The same spend that is refused at the installation's ceiling passes on the bigger
    plan — and the `cota` frame shows the plan's ceiling, not the global constant. The
    plan comes from the extension registry.

    The ceiling shows up in four places (here, the check in `cotas.py` and the two
    `/estado`); changing only the endpoints would make the donut oscillate mid-turn,
    showing the plan's ceiling when the screen opens and the installation's during
    the response. That is why the loop resolves the plan ONCE and carries it to billing.
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
    """Billing is by accumulated token: everything that went in (the cache is already
    inside `entrada`, and it costs) plus everything that came out."""
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
    # The window needs an expiry, otherwise the user loses the assistant forever.
    assert redis.ttls["assistente:tokens:usr-1"] == cotas.JANELA_DO_ASSISTENTE_SEGUNDOS


async def test_o_acumulado_da_cota_vai_ao_stream_a_cada_resposta_do_modelo():
    """The donut rises DURING the turn: after each model response a `cota` frame goes
    out with the window's running total (what INCRBY returned) and the ceiling —
    before the tool runs, and `fim` is still the last one. Without Redis there is
    no counter, and no frame."""
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


# ── What goes out on the SSE ──────────────────────────────────────────────────


async def test_o_progresso_da_execucao_vira_quadro_no_SSE():
    """`run_workflow` is the only tool that uses `ctx`, and this is what for."""

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
    # Draws BEFORE executing: `run_workflow` is refused while there is no
    # workflow on the canvas, which is the gate against "execute to answer with data".
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
        # The id of the owning call: with the turn's tools running in parallel, it is
        # by it that the browser paints the bar on the right card.
        "id": "tu-1",
    }
    # And in the right order: the progress comes before the end of the tool THAT EMITTED IT.
    # A raw `index` would look at the drawing's `ferramenta_fim`, which happens
    # before execution starts — and would pass by accident, measuring something else.
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
    """Splitting into several silently teaches the model to stop asking in parallel."""
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
    """The SSE frame is someone's log at some point — and the argument carries the definition."""
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
    """Truncating silently would make the model conclude the data doesn't exist."""
    gigante = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="a" * (cs.MAX_CHARS_POR_RESULTADO + 500))],
        structured_content=None,
        is_error=False,
    )

    texto = cs._texto_do_resultado(gigante)

    assert len(texto) == cs.MAX_CHARS_POR_RESULTADO + len(cs.AVISO_DE_CORTE)
    assert texto.endswith(cs.AVISO_DE_CORTE)


# ── Model call parameters ─────────────────────────────────────────────────────


async def test_a_chamada_ao_modelo_leva_modelo_esforco_sistema_e_transcrito():
    """The loop hands the client exactly what it translates: the configured model,
    high reasoning effort, the system with the cache breakpoint and the whole
    transcript."""
    cliente = ClienteFalso([([], _resposta())])

    await _colher(_conversar(cliente=cliente))

    from app.core.config import ASSISTENTE_MODELO

    params = cliente.parametros[0]
    # The model comes from configuration: changing it is editing `.env`, not deploying.
    assert params["modelo"] == ASSISTENTE_MODELO
    assert params["esforco"] == cs.ESFORCO_DO_RACIOCINIO == "high"
    assert params["max_tokens"] == cs.MAX_TOKENS
    # The system is the one from `montar_sistema`, with the cache breakpoint on the last block.
    assert params["sistema"] == cs.montar_sistema()
    assert params["sistema"][-1]["cache_control"] == {"type": "ephemeral"}
    # And the transcript goes WHOLE, in the project's format — translation is the client's job.
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
                # The MCP `input_schema` goes as-is: same schema, no translation.
                "parameters": {"type": "object", "required": ["definition"]},
            },
        }
    ]


async def test_o_sistema_e_o_texto_do_MCP_e_nao_uma_segunda_politica():
    """Two copies of the policy diverge on the first careless edit.

    And the `untrusted_data` warning is what separates "data written by someone in
    the workspace" from "an order for the model" — the defense against injection
    via workflow name or error message.
    """
    from app.mcp.instrucoes import INSTRUCOES

    blocos = cs.montar_sistema()

    assert blocos[0]["text"] == INSTRUCOES
    assert "untrusted_data" in blocos[0]["text"]
    assert "DADO" in blocos[0]["text"]


async def test_o_sistema_pede_resposta_E_raciocinio_no_idioma_configurado(monkeypatch):
    """The reasoning is shown to the person (the panel's "Raciocínio" section), and a
    model that converses in Portuguese tends to think in English. No API chooses
    the language of the reasoning: asking in the system is the only control."""
    from app.core import config

    monkeypatch.setattr(config, "ASSISTENTE_IDIOMA", "português do Brasil")
    idioma = [b["text"] for b in cs.montar_sistema() if "Responda sempre" in b["text"]]

    assert len(idioma) == 1
    assert "Responda sempre em português do Brasil" in idioma[0]
    assert "Raciocine também em português do Brasil" in idioma[0]


async def test_o_prefixo_estavel_tem_um_ponto_de_corte_de_cache():
    """The prefix (~15k tokens: tools + the system blocks) is IDENTICAL across every
    conversation and every user. Without an explicit breakpoint, each new
    conversation rewrites the prefix at full price.

    The breakpoint goes on the LAST stable block — the earlier ones carry no
    marker, so there is a single breakpoint in the system. Only the type, no TTL:
    the duration is up to the provider behind the router.
    """
    blocos = cs.montar_sistema()

    # Exactly one breakpoint, and on the last block.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 1]
    assert blocos[-1]["cache_control"] == {"type": "ephemeral"}
    # O bloco marcado continua sendo o guia, com o texto intacto.
    assert blocos[-1]["text"] == cs._guia_do_prefixo()


async def test_instrucoes_extras_fica_fora_do_prefixo_cacheado():
    """`instrucoes_extras` is optional and may be dynamic: it must never push the
    breakpoint past it, nor enter the cached prefix. The breakpoint stays on the
    guide block, and the extra comes after, with no marker."""
    blocos = cs.montar_sistema(instrucoes_extras="contexto so desta conversa")

    assert blocos[-1]["text"] == "contexto so desta conversa"
    assert "cache_control" not in blocos[-1]
    # The breakpoint stays on the guide — the second-to-last block now.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 2]
    assert blocos[com_corte[0]]["text"] == cs._guia_do_prefixo()


async def test_a_recusa_do_modelo_termina_a_conversa_como_recusado():
    """`content_filter` is OpenRouter's normalized `finish_reason` for a refusal."""
    cliente = ClienteFalso([([], _resposta(parada="content_filter"))])

    eventos = await _colher(_conversar(cliente=cliente))

    erro = _o_erro(eventos)
    assert erro["code"] == "recusado"
    assert eventos[-1].dados["ok"] is False


@pytest.mark.parametrize("parada", ["content_filter", "stop"])
async def test_resposta_sem_bloco_nenhum_nao_entra_no_transcrito(parada):
    """An empty assistant message is rejected by the provider on every resume, and
    there is nothing in it for the person to see. The transcript stays as it was."""
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
    # Never the exception text: it carries URL, host and sometimes headers.
    assert "sem rota" not in json.dumps(erro)


# ── Surfaces: the editor is the default, the Home passes its own bundle ───────
# The Home surface import is LOCAL to each test: if it ever breaks on import,
# only these tests break, not the 59 above that prove the editor.


async def test_o_sistema_da_home_troca_o_bloco_de_instrucoes_e_mantem_o_cache():
    """The Home surface changes block [1] (the instructions), and nothing else of the shape."""
    from app.mcp.instrucoes import INSTRUCOES
    from app.services.assistente_superficie import HOME, INSTRUCOES_DA_HOME

    blocos = cs.montar_sistema(superficie=HOME)

    # [0] is still the MCP policy — the same for both.
    assert blocos[0]["text"] == INSTRUCOES
    # [1] is now the Home block, not the editor's.
    assert blocos[1]["text"] == INSTRUCOES_DA_HOME
    assert blocos[1]["text"] != cs.INSTRUCOES_DO_EDITOR
    # The cache breakpoint stays on the last block (the guide), as in the editor: two
    # stable prefixes, one per surface.
    com_corte = [i for i, b in enumerate(blocos) if "cache_control" in b]
    assert com_corte == [len(blocos) - 1]
    assert blocos[-1]["cache_control"] == {"type": "ephemeral"}
    assert blocos[-1]["text"] == cs._guia_do_prefixo()


async def test_as_ferramentas_da_home_incluem_criar_e_abrem_com_o_globo():
    """The Home allows the whole catalog (what the editor blocks), and the delivery opens the list."""
    from app.services.assistente_superficie import HOME, NOME_DO_GLOBO

    servidor = ServidorFalso(
        tools=[_ToolFalsa("search_nodes"), _ToolFalsa("create_workflow"), _ToolFalsa("run_workflow")]
    )
    ferramentas = await cs.ferramentas_para_o_modelo(servidor, escopo_falso(), HOME)
    nomes = [f["function"]["name"] for f in ferramentas]

    # The Home delivery opens the list — what the model reads first.
    assert nomes[0] == NOME_DO_GLOBO
    # create_workflow GETS IN: in the editor it is blocked, on the Home the gate is
    # click confirmation, not the absence of the tool.
    assert "create_workflow" in nomes
    assert "run_workflow" in nomes
    # And the editor's drawing does NOT show up on the Home — it is the other surface's bundle.
    assert cs.NOME_DO_DESENHO not in nomes


async def test_o_gancho_ao_fechar_turno_e_chamado_com_a_conversa_crescendo():
    """The incremental persistence hook is called after each message comes in.

    The editor passes no hook at all (it is `None` and becomes a no-op); whoever
    persists conversation by conversation — the Home assistant — gets the
    conversation on every turn.
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

    # The conversation starts with 1 (the user's message). Called after: the assistant
    # of turn 1 (2), the tool_results of turn 1 (3), the assistant of turn 2 (4).
    assert tamanhos == [2, 3, 4]


async def test_o_gancho_que_quebra_nao_derruba_a_conversa():
    """Failing to persist must not lose the response that is already on the air."""
    cliente = ClienteFalso([([], _resposta(conteudo=[_texto("pronto")]))])

    async def gancho(conversa):
        raise RuntimeError("banco fora")

    eventos = await _colher(_conversar(cliente=cliente, ao_fechar_turno=gancho))

    # A conversa termina bem, apesar do gancho ter estourado.
    assert eventos[-1].tipo == "fim"
    assert eventos[-1].dados["ok"] is True


# ── Dispatch must not break the conversation ─────────────────────────────────
# Stages 1 and 2 (local executor, surface gate) ran OUTSIDE any try — only
# `chamar_no_servidor` had the net. A `DetachedInstanceError` in the Home gate
# (reading an ORM attribute after the session closed) brought down the whole
# stream, and left a trace: the `tool_use` was already in the transcript and the
# `tool_result` never arrived, so the NEXT message hit a 400 from the API.


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
    """Becomes `(texto, True)` — never an exception that propagates and kills the conversation.

    Mutation: removing the try/except from the dispatch lets the `RuntimeError`
    escape and breaks both cases.
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
    """The fix must not swallow the verdict: a gate that REFUSES keeps refusing."""

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
    """The Home's second local tool: in the model's list, right after the delivery."""
    from app.services.assistente_superficie import HOME, NOME_DAS_RESPOSTAS, NOME_DO_GLOBO

    servidor = ServidorFalso(tools=[_ToolFalsa("search_nodes")])
    ferramentas = await cs.ferramentas_para_o_modelo(servidor, escopo_falso(), HOME)
    nomes = [f["function"]["name"] for f in ferramentas]

    assert nomes[:2] == [NOME_DO_GLOBO, NOME_DAS_RESPOSTAS]


async def test_sugerir_respostas_nao_vai_ao_servidor_e_vira_quadro_depois_do_fim_da_ferramenta():
    """In the Home loop: `ferramenta` -> `ferramenta_fim` -> `respostas_rapidas`, with no
    `call_tool`; the `tool_result` stays in the transcript, which is what replay reuses."""
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
    """The lock expires in `TTL_DA_TRAVA_S`, but a long turn (`TETO_DE_VOLTAS`
    turns at `high`) goes past that. Without renewal, it would expire midway and a
    2nd tab would enter the SAME transcript. The watchdog reissues the EXPIRE while it runs."""
    monkeypatch.setattr(cs, "_INTERVALO_DE_RENOVACAO_DA_TRAVA_S", 0.01)
    redis = RedisFalso()
    chave = "assistente:trava:u:w"

    async with cs.trava_exclusiva(redis, chave):
        await asyncio.sleep(0.05)  # tempo para o watchdog reemitir o EXPIRE >= 1x

    assert ("expire", chave, cs.TTL_DA_TRAVA_S) in redis.chamadas, "o watchdog nao renovou"
    assert chave not in redis.dados  # and released on exit


async def test_o_renovador_da_trava_morre_ao_soltar(monkeypatch):
    """The watchdog is cancelled at the end of the section: no task is left alive
    reissuing EXPIRE on an already released lock."""
    monkeypatch.setattr(cs, "_INTERVALO_DE_RENOVACAO_DA_TRAVA_S", 0.01)
    redis = RedisFalso()
    chave = "assistente:trava:u:w"

    async with cs.trava_exclusiva(redis, chave):
        pass  # sai imediatamente

    antes = len([c for c in redis.chamadas if c[0] == "expire"])
    await asyncio.sleep(0.05)  # if the renewer were alive, it would reissue here
    depois = len([c for c in redis.chamadas if c[0] == "expire"])
    assert depois == antes, "o renovador continuou vivo apos a trava soltar"


# ── Tool progress arrives live, not buffered (PR 5, #5) ───────────────────────


async def test_o_progresso_chega_ao_vivo_antes_de_a_ferramenta_terminar():
    """The tool runs in a task and the loop yields the `report_progress` WHILE it is
    still running. With the old `list` queue (drained only after the tool's
    `await`), a long run's progress stayed buffered and arrived all at once, at
    the end."""
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
    # Draws BEFORE executing: `run_workflow` is refused without a workflow on the canvas.
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
        # Drains until the `progresso` WITHOUT releasing the tool. With the fix it arrives
        # (the tool is parked on `liberar.wait()`); with the `list` queue, the
        # `__anext__` would block here until the tool finished -> TimeoutError.
        while True:
            evento = await asyncio.wait_for(gen.__anext__(), timeout=2.0)
            vistos.append(evento)
            if evento.tipo == "progresso":
                break
    finally:
        liberar.set()  # releases the tool even if it fails, so the task doesn't leak

    assert vistos[-1].tipo == "progresso"
    assert vistos[-1].dados == {"concluidos": 1, "total": 3, "mensagem": "a meio caminho", "id": "tu-1"}
    resto = [evento async for evento in gen]
    assert resto and resto[-1].tipo == "fim"


async def test_cada_volta_e_registrada_no_uso_com_o_modelo_que_a_produziu():
    """The record follows the quota BILLING, turn by turn.

    Two reasons, and both are about not losing sight of money: writing at the same
    point makes the quota and the usage ledger count the same thing, and a
    conversation abandoned midway (tab closed, dead stream) already leaves on
    record what it spent up to there. Adding up only at the end would lose
    precisely those — and would lose DOWNWARD, which in a cost table is the wrong
    side to err on.

    The `modelo` goes along because this table exists, among other things, to
    compare before and after a model change. Deducing it at read time, from
    whatever is configured at that moment, would make the comparison impossible.
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


# ── Tools in parallel on the same turn ───────────────────────────────────────
# The model asks for several data sheets at once and the turn costs the slowest
# tool, not the sum. The parallel lane only applies when there is NO local tool in
# the batch: the drawing mutates `estado.desenhou`, and the order with
# `run_workflow` matters.


def _resultado_ok(texto="ok"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=texto)],
        structured_content=None,
        is_error=False,
    )


def _blocos_de_resultado(cliente) -> list[dict]:
    """The `tool_result`s the model received on the turn after the batch."""
    conversa = cliente.parametros[-1]["conversa"]
    do_lote = [m for m in conversa if m.get("role") == "user" and isinstance(m.get("content"), list)]
    assert do_lote, "nenhuma mensagem de tool_result chegou ao modelo"
    return do_lote[-1]["content"]


async def test_ferramentas_da_mesma_volta_rodam_juntas_e_respondem_na_ordem():
    """Each call in the batch only finishes when all THREE have started.

    In the sequential lane the first would wait for the others forever — the
    double's timeout would become an error result and the test would fail. In the
    parallel one, they all meet, and the `tool_result`s come back IN THE ORDER of
    the `tool_use`s, whatever the order of completion.
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

    # Announces the WHOLE batch before the first end: the browser sees the three
    # cards running together.
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
    """With several tools running, the `progresso` frame says whose it is."""

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
    """The contract that kills the race: the id travels with the call, not in a
    shared field. Each result in the batch carries the id the gate saw."""
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
    """[drawing, run_workflow] on the SAME turn: the local lane preserves the order —
    the run's gate reads the `desenhou` the drawing has just written."""
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

    # In sequence: the drawing's end comes BEFORE the run's announcement.
    ordem = [(e.tipo, e.dados.get("id")) for e in eventos if e.tipo in ("ferramenta", "ferramenta_fim")]
    assert ordem == [
        ("ferramenta", "tu-1"),
        ("ferramenta_fim", "tu-1"),
        ("ferramenta", "tu-2"),
        ("ferramenta_fim", "tu-2"),
    ]
    # And the run passed the gate: the server was touched.
    assert [nome for nome, _ in servidor.chamadas] == ["run_workflow"]
    resultados = _blocos_de_resultado(cliente)
    assert all(r["is_error"] is False for r in resultados)


async def test_o_fim_do_rapido_nao_espera_o_lento_que_veio_depois():
    """The ends go out IN THE ORDER of the calls, but each one as soon as its own task
    (and the earlier ones) finished — the fast task closes the card and delivers the
    frames with the slow one still running. With the "all sentinels first" drain, the
    first end would only go out after the slow one — and this test hits the timeout."""
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
        liberar.set()  # releases the slow one even if it fails, so the task doesn't leak

    assert vistos[-1].dados["id"] == "tu-1", "o fim do rápido esperou o lento"
    resto = [evento async for evento in gen]
    assert [e.dados["id"] for e in resto if e.tipo == "ferramenta_fim"] == ["tu-2"]
    assert resto[-1].tipo == "fim"
