# tests/unit/test_assistente_superficie.py
"""
The assistant's Home surface — what asks for a click and what doesn't.

The loop already has tests (`test_assistente_service.py`); here only the Home
BUNDLE is measured: the confirmation gate (stores the args in Redis, emits the
frame, returns "waiting" without touching the server), the "person's workflow ×
assistant's workflow" rule, the `fluxo`/`camada` frames, and the
`exibir_no_globo` delivery.

The functions are exercised DIRECTLY, without spinning up the loop:
`_home_gate` and `_home_frames` receive a hand-built `EstadoDoLaco`.
`carregar_workflow` and `infra.sessao` are doubled in the two tests that look at
the workflow's origin — what is measured there is the gate's decision, not the
database query.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.authorization.pat import ESCOPOS as PAT_SCOPES
from app.mcp.escopo import ASSISTANT_SCOPES, assistant_scope
from app.mcp.guardas import GUARDAS
from app.models.base import Base
from app.models.workflow import Workflow
from app.services import assistente_superficie as ag
from app.services.assistente_service import EstadoDoLaco, Evento

from ._mcp_harness import FakeRedis, fake_scope

pytestmark = pytest.mark.asyncio


def _estado(*, redis=None, conversa_id="conv-1", user_id="usr-1"):
    """A Home `EstadoDoLaco`, with an `emitir` that captures the frames."""
    eventos: list[Evento] = []

    async def emitir(ev):
        eventos.append(ev)

    escopo = fake_scope(
        user_id=user_id,
        scopes=ASSISTANT_SCOPES,
        origem_dos_fluxos="assistente",
        todos_os_workspaces=True,
    )
    estado = EstadoDoLaco(
        escopo=escopo,
        redis=redis,
        conversa_id=conversa_id,
        emitir=emitir,
    )
    return estado, eventos


def _doubled_session(monkeypatch):
    """Doubles `infra.sessao` to yield any session — the tests' `carregar_workflow`
    ignores `db`, so what it yields doesn't matter."""

    @asynccontextmanager
    async def _session():
        yield None

    monkeypatch.setattr(ag.infra, "sessao", _session)


# ── The assistant's scope ─────────────────────────────────────────────────────


async def test_the_assistant_scope_has_full_reach_and_marks_the_origin():
    """Six scopes (not the editor's four), origin stamped, never admin."""
    escopo = assistant_scope(user_id="u9", username="ana", workspace_ids={"ws-1", "ws-2"})

    assert escopo.token_id == "assistente:u9"
    assert escopo.token_prefix == "assistente"
    assert escopo.scopes == frozenset(PAT_SCOPES)
    # The two the editor's assistant does NOT carry get in here.
    assert "triggers:manage" in escopo.scopes
    assert "drive:write" in escopo.scopes
    assert escopo.origem_dos_fluxos == "assistente"
    assert escopo.todos_os_workspaces is True
    # And never administrator, for the same reason as the PAT and the assistant.
    assert escopo.as_user().role == "user"


# ── The confirmation gate ───────────────────────────────────────────────────


async def test_delete_schedule_asks_for_click_without_touching_the_server():
    """Confirmable ALWAYS: stores the args in Redis, emits the frame, returns a non-error.

    The gate INTERCEPTS — it returns a result, and the dispatcher never even calls
    the server. And `is_error` is False on purpose: an error would make the model
    repeat the call and duplicate the button.
    """
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)
    args = {"workflow_id": "wf-1", "job_id": "job-1"}

    veredito = await ag._home_gate(estado, "delete_schedule", args, "tu-9")

    assert veredito is not None
    texto, is_error = veredito
    assert is_error is False, "um erro faria o modelo repetir e duplicar o botão"
    assert "confirm" in texto.lower()

    confirmacoes = [e for e in eventos if e.tipo == "confirmacao"]
    assert len(confirmacoes) == 1
    dados = confirmacoes[0].dados
    assert dados["tool_use_id"] == "tu-9"
    token = dados["token"]
    assert token
    assert dados["acao"]["tool"] == "delete_schedule"
    # The summary, not the raw content (it is the same `_summarize` as the editor's).
    assert dados["acao"]["alvo"] == "wf-1"

    # The key stores the ARGS: it is what the click executes, never what the client
    # sends in the confirmation POST.
    chave = ag.chave_de_confirmacao("usr-1", "conv-1", "tu-9")
    guardado = json.loads(redis.dados[chave])
    assert guardado["token"] == token
    assert guardado["tool"] == "delete_schedule"
    assert guardado["args"] == args
    assert redis.ttls[chave] == ag.TTL_DA_CONFIRMACAO_S


async def test_confirmation_without_redis_fails_closed():
    """Without Redis there is no way to validate the click later: refuse, not an empty confirmation."""
    estado, eventos = _estado(redis=None)

    veredito = await ag._home_gate(estado, "delete_schedule", {"job_id": "j"}, "tu-1")

    assert veredito is not None and veredito[1] is True
    assert not [e for e in eventos if e.tipo == "confirmacao"]


async def test_running_the_assistants_own_workflow_does_not_ask_for_click(monkeypatch):
    """The assistant creates and runs its OWN workflows without a click — it is the answer reaching the globe."""
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)
    _doubled_session(monkeypatch)

    async def _load(db, escopo, ref, **kw):
        return SimpleNamespace(origem="assistente", id_hash=ref), "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _load)

    veredito = await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-assist"}, "tu-1")

    assert veredito is None, "o assistente roda os próprios fluxos sem clique"
    assert not eventos
    assert not redis.dados


async def test_running_the_persons_workflow_asks_for_click(monkeypatch):
    """Running a workflow the PERSON created is touching what already existed: requires a click."""
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)
    _doubled_session(monkeypatch)

    async def _load(db, escopo, ref, **kw):
        return SimpleNamespace(origem="usuario", id_hash=ref), "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _load)

    veredito = await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-pessoa"}, "tu-1")

    assert veredito is not None and veredito[1] is False
    assert len([e for e in eventos if e.tipo == "confirmacao"]) == 1


async def test_workflow_that_fails_to_load_asks_for_click_for_safety(monkeypatch):
    """Fail closed: unable to prove the workflow is the assistant's, it confirms."""
    redis = FakeRedis()
    estado, _events = _estado(redis=redis)
    _doubled_session(monkeypatch)

    async def _load(db, escopo, ref, **kw):
        raise RuntimeError("não encontrado")

    monkeypatch.setattr(ag, "carregar_workflow", _load)

    veredito = await ag._home_gate(estado, "update_workflow", {"workflow_id": "sumido"}, "tu-1")

    assert veredito is not None and veredito[1] is False


async def test_read_goes_straight_through_without_click():
    """A non-confirmable tool (read) goes straight to the server."""
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._home_gate(estado, "search_nodes", {"query": "buffer"}, "tu-1")

    assert veredito is None
    assert not eventos
    assert not redis.dados


async def test_name_outside_guards_is_refused():
    """A name that doesn't exist in MCP: uniform refusal, doesn't leak the server's error."""
    estado, _events = _estado(redis=FakeRedis())

    veredito = await ag._home_gate(estado, "ferramenta_inexistente", {}, "tu-1")

    assert veredito is not None and veredito[1] is True


# ── The frames the Home emits ────────────────────────────────────────────────


async def test_create_workflow_becomes_workflow_frame():
    estado, _events = _estado()
    resultado = json.dumps(
        {"id": "wf-novo", "workspace_id": "ws-1", "untrusted_data": {"name": "assistente: focos"}}
    )

    quadros = ag._home_frames(estado, "create_workflow", {}, resultado, False)

    assert len(quadros) == 1
    assert quadros[0].tipo == "fluxo"
    assert quadros[0].dados == {"workflow_id": "wf-novo", "nome": "assistente: focos"}


async def test_run_workflow_creates_layer_only_from_geojson():
    """One `camada` per GeoJSON artifact; shapefile left out; executor-local with a hint."""
    estado, _events = _estado()
    resultado = json.dumps(
        {
            "run_id": "run-1",
            "status": "success",
            "artifacts": [
                {
                    "id": "a-geo",
                    "format": "geojson",
                    "available": True,
                    "untrusted_data": {"filename": "focos.geojson", "output_key": "saida"},
                },
                {
                    "id": "a-shp",
                    "format": "shapefile",
                    "available": True,
                    "untrusted_data": {"filename": "focos.zip"},
                },
                {
                    "id": "a-exec",
                    "format": "geojson",
                    "available": False,
                    "hint": "o conteúdo permanece no executor",
                    "untrusted_data": {"filename": "local.geojson"},
                },
            ],
        }
    )

    quadros = ag._home_frames(estado, "run_workflow", {}, resultado, False)

    assert all(q.tipo == "camada" for q in quadros)
    assert [q.dados["artifact_id"] for q in quadros] == ["a-geo", "a-exec"]
    geo = next(q for q in quadros if q.dados["artifact_id"] == "a-geo")
    assert geo.dados["available"] is True
    assert geo.dados["nome"] == "focos.geojson"
    exe = next(q for q in quadros if q.dados["artifact_id"] == "a-exec")
    assert exe.dados["available"] is False
    assert "executor" in exe.dados["hint"]


async def test_get_run_artifacts_uses_the_items_list():
    """`get_run_artifacts` lists in `items` (not `artifacts`) — both are valid."""
    estado, _events = _estado()
    resultado = json.dumps(
        {
            "run_id": "r",
            "items": [
                {"id": "a1", "format": "geojson", "available": True, "untrusted_data": {"filename": "x.geojson"}}
            ],
        }
    )

    quadros = ag._home_frames(estado, "get_run_artifacts", {}, resultado, False)

    assert [q.dados["artifact_id"] for q in quadros] == ["a1"]


async def test_result_with_error_does_not_become_a_frame():
    estado, _events = _estado()
    assert ag._home_frames(estado, "run_workflow", {}, "qualquer coisa", True) == []


async def test_unreadable_result_does_not_crash():
    """A result that doesn't parse becomes neither a frame nor an exception."""
    estado, _events = _estado()
    assert ag._home_frames(estado, "create_workflow", {}, "isto não é JSON", False) == []


# ── The delivery: `exibir_no_globo` ──────────────────────────────────────────


async def test_show_on_globe_builds_the_layer_via_the_extra_frames():
    """The `camada` frame comes out of `quadros_extras`, NOT from a local `emitir`.

    It is what makes replay rebuild the layer: it only re-runs `quadros_extras`.
    An `emitir` inside the local executor went out on the SSE and vanished when
    the chat was reopened.
    """
    estado, eventos = _estado()
    argumentos = {"artifact_id": "art-9", "nome": "Focos"}

    texto, is_error = await ag._show_on_globe(argumentos, estado)

    assert is_error is False
    assert not eventos  # nothing emitted by the local executor

    quadros = ag._home_frames(estado, ag.NOME_DO_GLOBO, argumentos, texto, False)
    assert [q.tipo for q in quadros] == ["camada"]
    assert quadros[0].dados["artifact_id"] == "art-9"
    assert quadros[0].dados["nome"] == "Focos"
    # `available` present: without it the front end normalized to False and the card
    # said "sem previa no globo" (no preview on the globe) with the layer already drawn.
    assert quadros[0].dados["available"] is True


async def test_show_on_globe_without_id_is_error():
    estado, eventos = _estado()

    _as_text, is_error = await ag._show_on_globe({}, estado)

    assert is_error is True
    assert not eventos
    # And the frame also doesn't go out when the call errored.
    assert ag._home_frames(estado, ag.NOME_DO_GLOBO, {}, "", True) == []


# ── The surface ──────────────────────────────────────────────────────────────


# ── Quick replies: `sugerir_respostas` ───────────────────────────────────────


async def test_suggest_replies_builds_the_frame_via_the_extra_frames():
    """Like the globe: the executor emits nothing; the frame is born from the arguments in
    `quadros_extras` — including with `estado=None`, which is how replay calls it."""
    estado, eventos = _estado()
    argumentos = {"opcoes": ["Só os últimos 7 dias", "Cruzar com o CAR"]}

    texto, is_error = await ag._suggest_answers(argumentos, estado)

    assert is_error is False
    assert "Encerre o turno" in texto
    assert not eventos  # nothing emitted by the local executor

    for est in (estado, None):
        quadros = ag._home_frames(est, ag.NOME_DAS_RESPOSTAS, argumentos, texto, False)
        assert [q.tipo for q in quadros] == ["respostas_rapidas"]
        assert quadros[0].dados == {"opcoes": ["Só os últimos 7 dias", "Cruzar com o CAR"]}


async def test_suggest_replies_cleans_and_limits_the_options():
    """Strings only, whitespace normalized, no empty or repeated ones, cut at 80, three at most."""
    longa = "x" * 100
    argumentos = {"opcoes": ["  Agendar  ", "", "Agendar", 7, longa, "Ver  por município", "Quinta"]}

    assert ag._requested_options(argumentos) == ["Agendar", "x" * 80, "Ver por município"]

    quadros = ag._home_frames(None, ag.NOME_DAS_RESPOSTAS, argumentos, "", False)
    assert quadros[0].dados["opcoes"] == ["Agendar", "x" * 80, "Ver por município"]


@pytest.mark.parametrize(
    "argumentos",
    [{}, {"opcoes": []}, {"opcoes": ["", "  ", 3]}, {"opcoes": "Agendar"}, "lixo", None],
)
async def test_suggest_replies_without_valid_option_is_error(argumentos):
    estado, eventos = _estado()

    _as_text, is_error = await ag._suggest_answers(argumentos, estado)

    assert is_error is True
    assert not eventos
    assert ag._home_frames(estado, ag.NOME_DAS_RESPOSTAS, argumentos, "", True) == []
    # And even without the error flagged, arguments with no valid option don't become a frame.
    assert ag._home_frames(None, ag.NOME_DAS_RESPOSTAS, argumentos, "", False) == []


async def test_the_home_instructions_teach_the_quick_replies():
    assert ag.NOME_DAS_RESPOSTAS in ag.INSTRUCOES_DA_HOME


async def test_the_home_surface_allows_the_whole_catalog_and_the_delivery():
    """Alcance completo (o que o editor bloqueia, a Home permite); a entrega abre a lista."""
    assert ag.HOME.nome == "home"
    assert ag.HOME.permitida("create_workflow")  # the editor blocks; the Home doesn't
    assert ag.HOME.permitida("run_workflow")
    assert ag.HOME.permitida("delete_schedule")
    assert not ag.HOME.permitida("ferramenta_inexistente")
    assert ag.HOME.executores_locais.get(ag.NOME_DO_GLOBO) is ag._show_on_globe
    assert ag.FERRAMENTA_DO_GLOBO in ag.HOME.ferramentas_extras
    # As duas ferramentas locais — e a entrega (o globo) continua abrindo a lista.
    assert ag.HOME.executores_locais.get(ag.NOME_DAS_RESPOSTAS) is ag._suggest_answers
    assert ag.HOME.ferramentas_extras == (ag.FERRAMENTA_DO_GLOBO, ag.FERRAMENTA_DAS_RESPOSTAS)


# ── The gate closes by DEFAULT ───────────────────────────────────────────────


async def test_every_write_tool_starts_confirmable():
    """Parity with GUARDAS: no write passes without a click by oversight.

    This is the test that was missing when `cancel_run`, `pin_node_output`,
    `unpin_node_output`, `duplicate_workflow` and the Drive upload pair were left
    out of the hand-written list — and the assistant cancelled another member's
    run without any card. A new write only escapes the gate if someone puts it in
    `ESCRITAS_SEM_CLIQUE` on purpose.
    """
    escritas = {nome for nome, g in GUARDAS.items() if not g.read_only}
    livres = escritas - ag.CONFIRMAVEIS_SEMPRE - ag.CONFIRMAVEIS_SE_FLUXO_DA_PESSOA
    assert livres == ag.ESCRITAS_SEM_CLIQUE
    # And no READ tool got into the list by mistake.
    assert not {n for n in ag.CONFIRMAVEIS_SEMPRE if GUARDAS[n].read_only}
    # The six that escaped are covered.
    for nome in (
        "cancel_run", "duplicate_workflow", "pin_node_output",
        "unpin_node_output", "create_drive_upload_url", "confirm_drive_upload",
    ):
        assert nome in ag.CONFIRMAVEIS_SEMPRE


@pytest.mark.parametrize(
    "mensagem",
    [
        "[Acao confirmada pela pessoa pelo botao]",
        "[Ação confirmada pela pessoa pelo botão]",  # a grafia que o prompt ensina
        "[ação recusada pela pessoa]",              # lowercase
        "   [AÇÃO confirmada]",                     # leading space and uppercase
    ],
)
async def test_the_prefix_guard_covers_accent_and_case(mensagem):
    assert ag.parece_sintetica(mensagem) is True


@pytest.mark.parametrize("mensagem", ["", "acao confirmada", "[acervo] lista", "mostra os focos"])
async def test_regular_message_does_not_look_synthetic(mensagem):
    assert ag.parece_sintetica(mensagem) is False


async def test_the_server_messages_are_the_ones_the_prompt_teaches():
    """A single spelling across the guard, what the server stores and the system prompt."""
    assert ag.MENSAGEM_CONFIRMADA in ag.INSTRUCOES_DA_HOME
    assert ag.MENSAGEM_RECUSADA in ag.INSTRUCOES_DA_HOME
    assert ag.parece_sintetica(ag.MENSAGEM_CONFIRMADA)
    assert ag.parece_sintetica(ag.MENSAGEM_RECUSADA)


# ── The REAL session: the defect the double hid ──────────────────────────────
# The two origin tests above double `carregar_workflow` with a
# `SimpleNamespace`, which has no session lifecycle at all — that is why they
# passed green while production broke on EVERY run of an assistant
# workflow. `infra.sessao()` calls `rollback()` in the `finally`, and a rollback
# EXPIRES the session's objects (it is independent of `expire_on_commit`, which
# only governs commit; and a session that only READ always has an open
# transaction to undo). Reading any attribute after the block triggers a refresh
# on a detached instance: `DetachedInstanceError`, which `getattr(..., default)`
# does NOT intercept — the default only covers `AttributeError`.
#
# This test spins up a real session with the SAME `finally: rollback()` as
# `get_session_async`, so that the lifecycle is the production one.


@pytest_asyncio.fixture
async def session_with_rollback(monkeypatch):
    """Real `infra.sessao` (sqlite), with the production `rollback()` in the finally."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[Workflow.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        s.add_all([
            Workflow(id_hash="wf-assist", name="assistente: demo", workspace_id="ws-1",
                     origem="assistente", definition={}),
            Workflow(id_hash="wf-pessoa", name="meu fluxo", workspace_id="ws-1",
                     origem="usuario", definition={}),
        ])
        await s.commit()

    @asynccontextmanager
    async def _session():
        async with fabrica() as nova:
            try:
                yield nova
            finally:
                await nova.rollback()

    monkeypatch.setattr(ag.infra, "sessao", _session)

    async def _load(db, escopo, ref, **kw):
        linha = (
            await db.execute(select(Workflow).where(Workflow.id_hash == str(ref)))
        ).scalar_one()
        return linha, "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _load)
    yield
    await engine.dispose()


async def test_the_origin_is_read_with_the_session_still_open(session_with_rollback):
    """REGRESSION: reading `origem` outside the `async with` raises DetachedInstanceError.

    Mutation: moving the `getattr` to after the block breaks ONLY this test and
    the next. In production the effect was the assistant being unable to run any
    of its own workflows — the whole Home path (create, run, layer on the globe).
    """
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-assist"}, "tu-1")

    assert veredito is None, "fluxo do assistente roda sem clique, com sessão real"
    assert not eventos
    assert not redis.dados


async def test_with_real_session_the_persons_workflow_still_asks_for_a_click(session_with_rollback):
    """The fix must not loosen the gate: the person's workflow still requires a click."""
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._home_gate(estado, "run_workflow", {"workflow_id": "wf-pessoa"}, "tu-1")

    assert veredito is not None and veredito[1] is False
    assert len([e for e in eventos if e.tipo == "confirmacao"]) == 1


async def test_the_home_script_checks_the_catalog_before_prospecting():
    """"Catalog first": for external data the step is `search_sources` →
    `describe_source`, BEFORE `search_nodes` and `validate_workflow`; probing and
    registering only come in as the path for when the catalog lacks the source."""
    texto = ag.INSTRUCOES_DA_HOME
    assert texto.index("search_sources") < texto.index("search_nodes") < texto.index("validate_workflow")
    assert texto.index("describe_source") < texto.index("probe_source") < texto.index("register_source")
    # And the two that probe are among the ones that pass without a click.
    assert {"probe_source", "register_source"} <= ag.ESCRITAS_SEM_CLIQUE


async def test_two_parallel_confirmations_each_match_their_own_call():
    """The race regression: with the batch running together, each confirmation stores
    ITS args under ITS `tool_use_id`. With a shared "current call" field (the old
    design), both would match the id that was written last — and a click would
    execute the wrong action."""
    redis = FakeRedis()
    estado, eventos = _estado(redis=redis)

    verdict_a, verdict_b = await asyncio.gather(
        ag._home_gate(estado, "delete_schedule", {"job_id": "job-a"}, "tu-A"),
        ag._home_gate(estado, "delete_schedule", {"job_id": "job-b"}, "tu-B"),
    )

    assert verdict_a is not None and verdict_b is not None
    assert verdict_a[1] is False and verdict_b[1] is False

    stored_a = json.loads(redis.dados[ag.chave_de_confirmacao("usr-1", "conv-1", "tu-A")])
    stored_b = json.loads(redis.dados[ag.chave_de_confirmacao("usr-1", "conv-1", "tu-B")])
    assert stored_a["args"] == {"job_id": "job-a"}
    assert stored_b["args"] == {"job_id": "job-b"}

    confirmacoes = {e.dados["tool_use_id"]: e.dados for e in eventos if e.tipo == "confirmacao"}
    assert set(confirmacoes) == {"tu-A", "tu-B"}
    assert confirmacoes["tu-A"]["token"] == stored_a["token"]
    assert confirmacoes["tu-B"]["token"] == stored_b["token"]
