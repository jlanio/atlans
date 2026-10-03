# tests/unit/test_assistente_superficie.py
"""
The assistant's Home surface — what asks for a click and what doesn't.

The loop already has tests (`test_assistente_service.py`); here only the Home
BUNDLE is measured: the confirmation gate (stores the args in Redis, emits the
frame, returns "waiting" without touching the server), the "person's workflow ×
assistant's workflow" rule, the `fluxo`/`camada` frames, and the
`exibir_no_globo` delivery.

The functions are exercised DIRECTLY, without spinning up the loop:
`_portao_da_home` and `_quadros_da_home` receive a hand-built `EstadoDoLaco`.
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

from app.core.authorization.pat import ESCOPOS as ESCOPOS_DO_PAT
from app.mcp.escopo import ESCOPOS_DO_ASSISTENTE, escopo_do_assistente
from app.mcp.guardas import GUARDAS
from app.models.base import Base
from app.models.workflow import Workflow
from app.services import assistente_superficie as ag
from app.services.assistente_service import EstadoDoLaco, Evento

from ._mcp_harness import RedisFalso, escopo_falso

pytestmark = pytest.mark.asyncio


def _estado(*, redis=None, conversa_id="conv-1", user_id="usr-1"):
    """A Home `EstadoDoLaco`, with an `emitir` that captures the frames."""
    eventos: list[Evento] = []

    async def emitir(ev):
        eventos.append(ev)

    escopo = escopo_falso(
        user_id=user_id,
        scopes=ESCOPOS_DO_ASSISTENTE,
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


def _sessao_dublada(monkeypatch):
    """Doubles `infra.sessao` to yield any session — the tests' `carregar_workflow`
    ignores `db`, so what it yields doesn't matter."""

    @asynccontextmanager
    async def _sessao():
        yield None

    monkeypatch.setattr(ag.infra, "sessao", _sessao)


# ── The assistant's scope ─────────────────────────────────────────────────────


async def test_o_escopo_do_assistente_tem_alcance_completo_e_marca_a_origem():
    """Six scopes (not the editor's four), origin stamped, never admin."""
    escopo = escopo_do_assistente(user_id="u9", username="ana", workspace_ids={"ws-1", "ws-2"})

    assert escopo.token_id == "assistente:u9"
    assert escopo.token_prefix == "assistente"
    assert escopo.scopes == frozenset(ESCOPOS_DO_PAT)
    # The two the editor's assistant does NOT carry get in here.
    assert "triggers:manage" in escopo.scopes
    assert "drive:write" in escopo.scopes
    assert escopo.origem_dos_fluxos == "assistente"
    assert escopo.todos_os_workspaces is True
    # And never administrator, for the same reason as the PAT and the assistant.
    assert escopo.como_usuario().role == "user"


# ── The confirmation gate ───────────────────────────────────────────────────


async def test_delete_schedule_pede_clique_sem_tocar_no_servidor():
    """Confirmable ALWAYS: stores the args in Redis, emits the frame, returns a non-error.

    The gate INTERCEPTS — it returns a result, and the dispatcher never even calls
    the server. And `is_error` is False on purpose: an error would make the model
    repeat the call and duplicate the button.
    """
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)
    args = {"workflow_id": "wf-1", "job_id": "job-1"}

    veredito = await ag._portao_da_home(estado, "delete_schedule", args, "tu-9")

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
    # The summary, not the raw content (it is the same `_resumo` as the editor's).
    assert dados["acao"]["alvo"] == "wf-1"

    # The key stores the ARGS: it is what the click executes, never what the client
    # sends in the confirmation POST.
    chave = ag.chave_de_confirmacao("usr-1", "conv-1", "tu-9")
    guardado = json.loads(redis.dados[chave])
    assert guardado["token"] == token
    assert guardado["tool"] == "delete_schedule"
    assert guardado["args"] == args
    assert redis.ttls[chave] == ag.TTL_DA_CONFIRMACAO_S


async def test_confirmacao_sem_redis_recusa_fechado():
    """Without Redis there is no way to validate the click later: refuse, not an empty confirmation."""
    estado, eventos = _estado(redis=None)

    veredito = await ag._portao_da_home(estado, "delete_schedule", {"job_id": "j"}, "tu-1")

    assert veredito is not None and veredito[1] is True
    assert not [e for e in eventos if e.tipo == "confirmacao"]


async def test_rodar_o_proprio_fluxo_do_assistente_nao_pede_clique(monkeypatch):
    """The assistant creates and runs its OWN workflows without a click — it is the answer reaching the globe."""
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)
    _sessao_dublada(monkeypatch)

    async def _carregar(db, escopo, ref, **kw):
        return SimpleNamespace(origem="assistente", id_hash=ref), "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _carregar)

    veredito = await ag._portao_da_home(estado, "run_workflow", {"workflow_id": "wf-assist"}, "tu-1")

    assert veredito is None, "o assistente roda os próprios fluxos sem clique"
    assert not eventos
    assert not redis.dados


async def test_rodar_fluxo_da_pessoa_pede_clique(monkeypatch):
    """Running a workflow the PERSON created is touching what already existed: requires a click."""
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)
    _sessao_dublada(monkeypatch)

    async def _carregar(db, escopo, ref, **kw):
        return SimpleNamespace(origem="usuario", id_hash=ref), "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _carregar)

    veredito = await ag._portao_da_home(estado, "run_workflow", {"workflow_id": "wf-pessoa"}, "tu-1")

    assert veredito is not None and veredito[1] is False
    assert len([e for e in eventos if e.tipo == "confirmacao"]) == 1


async def test_fluxo_que_nao_carrega_pede_clique_por_seguranca(monkeypatch):
    """Fail closed: unable to prove the workflow is the assistant's, it confirms."""
    redis = RedisFalso()
    estado, _eventos = _estado(redis=redis)
    _sessao_dublada(monkeypatch)

    async def _carregar(db, escopo, ref, **kw):
        raise RuntimeError("não encontrado")

    monkeypatch.setattr(ag, "carregar_workflow", _carregar)

    veredito = await ag._portao_da_home(estado, "update_workflow", {"workflow_id": "sumido"}, "tu-1")

    assert veredito is not None and veredito[1] is False


async def test_leitura_passa_direto_sem_clique():
    """A non-confirmable tool (read) goes straight to the server."""
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._portao_da_home(estado, "search_nodes", {"query": "buffer"}, "tu-1")

    assert veredito is None
    assert not eventos
    assert not redis.dados


async def test_nome_fora_de_guardas_e_recusado():
    """A name that doesn't exist in MCP: uniform refusal, doesn't leak the server's error."""
    estado, _eventos = _estado(redis=RedisFalso())

    veredito = await ag._portao_da_home(estado, "ferramenta_inexistente", {}, "tu-1")

    assert veredito is not None and veredito[1] is True


# ── The frames the Home emits ────────────────────────────────────────────────


async def test_create_workflow_vira_quadro_fluxo():
    estado, _eventos = _estado()
    resultado = json.dumps(
        {"id": "wf-novo", "workspace_id": "ws-1", "untrusted_data": {"name": "assistente: focos"}}
    )

    quadros = ag._quadros_da_home(estado, "create_workflow", {}, resultado, False)

    assert len(quadros) == 1
    assert quadros[0].tipo == "fluxo"
    assert quadros[0].dados == {"workflow_id": "wf-novo", "nome": "assistente: focos"}


async def test_run_workflow_gera_camada_so_de_geojson():
    """One `camada` per GeoJSON artifact; shapefile left out; executor-local with a hint."""
    estado, _eventos = _estado()
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

    quadros = ag._quadros_da_home(estado, "run_workflow", {}, resultado, False)

    assert all(q.tipo == "camada" for q in quadros)
    assert [q.dados["artifact_id"] for q in quadros] == ["a-geo", "a-exec"]
    geo = next(q for q in quadros if q.dados["artifact_id"] == "a-geo")
    assert geo.dados["available"] is True
    assert geo.dados["nome"] == "focos.geojson"
    exe = next(q for q in quadros if q.dados["artifact_id"] == "a-exec")
    assert exe.dados["available"] is False
    assert "executor" in exe.dados["hint"]


async def test_get_run_artifacts_usa_a_lista_items():
    """`get_run_artifacts` lists in `items` (not `artifacts`) — both are valid."""
    estado, _eventos = _estado()
    resultado = json.dumps(
        {
            "run_id": "r",
            "items": [
                {"id": "a1", "format": "geojson", "available": True, "untrusted_data": {"filename": "x.geojson"}}
            ],
        }
    )

    quadros = ag._quadros_da_home(estado, "get_run_artifacts", {}, resultado, False)

    assert [q.dados["artifact_id"] for q in quadros] == ["a1"]


async def test_resultado_com_erro_nao_vira_quadro():
    estado, _eventos = _estado()
    assert ag._quadros_da_home(estado, "run_workflow", {}, "qualquer coisa", True) == []


async def test_resultado_ilegivel_nao_derruba():
    """A result that doesn't parse becomes neither a frame nor an exception."""
    estado, _eventos = _estado()
    assert ag._quadros_da_home(estado, "create_workflow", {}, "isto não é JSON", False) == []


# ── The delivery: `exibir_no_globo` ──────────────────────────────────────────


async def test_exibir_no_globo_monta_a_camada_pelos_quadros_extras():
    """The `camada` frame comes out of `quadros_extras`, NOT from a local `emitir`.

    It is what makes replay rebuild the layer: it only re-runs `quadros_extras`.
    An `emitir` inside the local executor went out on the SSE and vanished when
    the chat was reopened.
    """
    estado, eventos = _estado()
    argumentos = {"artifact_id": "art-9", "nome": "Focos"}

    texto, is_error = await ag._exibir_no_globo(argumentos, estado)

    assert is_error is False
    assert not eventos  # nothing emitted by the local executor

    quadros = ag._quadros_da_home(estado, ag.NOME_DO_GLOBO, argumentos, texto, False)
    assert [q.tipo for q in quadros] == ["camada"]
    assert quadros[0].dados["artifact_id"] == "art-9"
    assert quadros[0].dados["nome"] == "Focos"
    # `available` present: without it the front end normalized to False and the card
    # said "sem previa no globo" (no preview on the globe) with the layer already drawn.
    assert quadros[0].dados["available"] is True


async def test_exibir_no_globo_sem_id_e_erro():
    estado, eventos = _estado()

    _texto, is_error = await ag._exibir_no_globo({}, estado)

    assert is_error is True
    assert not eventos
    # And the frame also doesn't go out when the call errored.
    assert ag._quadros_da_home(estado, ag.NOME_DO_GLOBO, {}, "", True) == []


# ── The surface ──────────────────────────────────────────────────────────────


# ── Quick replies: `sugerir_respostas` ───────────────────────────────────────


async def test_sugerir_respostas_monta_o_quadro_pelos_quadros_extras():
    """Like the globe: the executor emits nothing; the frame is born from the arguments in
    `quadros_extras` — including with `estado=None`, which is how replay calls it."""
    estado, eventos = _estado()
    argumentos = {"opcoes": ["Só os últimos 7 dias", "Cruzar com o CAR"]}

    texto, is_error = await ag._sugerir_respostas(argumentos, estado)

    assert is_error is False
    assert "Encerre o turno" in texto
    assert not eventos  # nothing emitted by the local executor

    for est in (estado, None):
        quadros = ag._quadros_da_home(est, ag.NOME_DAS_RESPOSTAS, argumentos, texto, False)
        assert [q.tipo for q in quadros] == ["respostas_rapidas"]
        assert quadros[0].dados == {"opcoes": ["Só os últimos 7 dias", "Cruzar com o CAR"]}


async def test_sugerir_respostas_limpa_e_limita_as_opcoes():
    """Strings only, whitespace normalized, no empty or repeated ones, cut at 80, three at most."""
    longa = "x" * 100
    argumentos = {"opcoes": ["  Agendar  ", "", "Agendar", 7, longa, "Ver  por município", "Quinta"]}

    assert ag._opcoes_pedidas(argumentos) == ["Agendar", "x" * 80, "Ver por município"]

    quadros = ag._quadros_da_home(None, ag.NOME_DAS_RESPOSTAS, argumentos, "", False)
    assert quadros[0].dados["opcoes"] == ["Agendar", "x" * 80, "Ver por município"]


@pytest.mark.parametrize(
    "argumentos",
    [{}, {"opcoes": []}, {"opcoes": ["", "  ", 3]}, {"opcoes": "Agendar"}, "lixo", None],
)
async def test_sugerir_respostas_sem_opcao_valida_e_erro(argumentos):
    estado, eventos = _estado()

    _texto, is_error = await ag._sugerir_respostas(argumentos, estado)

    assert is_error is True
    assert not eventos
    assert ag._quadros_da_home(estado, ag.NOME_DAS_RESPOSTAS, argumentos, "", True) == []
    # And even without the error flagged, arguments with no valid option don't become a frame.
    assert ag._quadros_da_home(None, ag.NOME_DAS_RESPOSTAS, argumentos, "", False) == []


async def test_as_instrucoes_da_home_ensinam_as_respostas_rapidas():
    assert ag.NOME_DAS_RESPOSTAS in ag.INSTRUCOES_DA_HOME


async def test_a_superficie_home_permite_o_catalogo_inteiro_e_a_entrega():
    """Alcance completo (o que o editor bloqueia, a Home permite); a entrega abre a lista."""
    assert ag.HOME.nome == "home"
    assert ag.HOME.permitida("create_workflow")  # the editor blocks; the Home doesn't
    assert ag.HOME.permitida("run_workflow")
    assert ag.HOME.permitida("delete_schedule")
    assert not ag.HOME.permitida("ferramenta_inexistente")
    assert ag.HOME.executores_locais.get(ag.NOME_DO_GLOBO) is ag._exibir_no_globo
    assert ag.FERRAMENTA_DO_GLOBO in ag.HOME.ferramentas_extras
    # As duas ferramentas locais — e a entrega (o globo) continua abrindo a lista.
    assert ag.HOME.executores_locais.get(ag.NOME_DAS_RESPOSTAS) is ag._sugerir_respostas
    assert ag.HOME.ferramentas_extras == (ag.FERRAMENTA_DO_GLOBO, ag.FERRAMENTA_DAS_RESPOSTAS)


# ── The gate closes by DEFAULT ───────────────────────────────────────────────


async def test_toda_tool_de_escrita_nasce_confirmavel():
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
async def test_a_guarda_do_prefixo_cobre_acento_e_caixa(mensagem):
    assert ag.parece_sintetica(mensagem) is True


@pytest.mark.parametrize("mensagem", ["", "acao confirmada", "[acervo] lista", "mostra os focos"])
async def test_mensagem_comum_nao_parece_sintetica(mensagem):
    assert ag.parece_sintetica(mensagem) is False


async def test_as_mensagens_do_servidor_sao_as_que_o_prompt_ensina():
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
async def sessao_com_rollback(monkeypatch):
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
    async def _sessao():
        async with fabrica() as nova:
            try:
                yield nova
            finally:
                await nova.rollback()

    monkeypatch.setattr(ag.infra, "sessao", _sessao)

    async def _carregar(db, escopo, ref, **kw):
        linha = (
            await db.execute(select(Workflow).where(Workflow.id_hash == str(ref)))
        ).scalar_one()
        return linha, "editor"

    monkeypatch.setattr(ag, "carregar_workflow", _carregar)
    yield
    await engine.dispose()


async def test_a_origem_e_lida_com_a_sessao_ainda_aberta(sessao_com_rollback):
    """REGRESSION: reading `origem` outside the `async with` raises DetachedInstanceError.

    Mutation: moving the `getattr` to after the block breaks ONLY this test and
    the next. In production the effect was the assistant being unable to run any
    of its own workflows — the whole Home path (create, run, layer on the globe).
    """
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._portao_da_home(estado, "run_workflow", {"workflow_id": "wf-assist"}, "tu-1")

    assert veredito is None, "fluxo do assistente roda sem clique, com sessão real"
    assert not eventos
    assert not redis.dados


async def test_com_sessao_real_o_fluxo_da_pessoa_continua_pedindo_clique(sessao_com_rollback):
    """The fix must not loosen the gate: the person's workflow still requires a click."""
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)

    veredito = await ag._portao_da_home(estado, "run_workflow", {"workflow_id": "wf-pessoa"}, "tu-1")

    assert veredito is not None and veredito[1] is False
    assert len([e for e in eventos if e.tipo == "confirmacao"]) == 1


async def test_o_roteiro_da_home_consulta_o_catalogo_antes_de_prospectar():
    """"Catalog first": for external data the step is `search_sources` →
    `describe_source`, BEFORE `search_nodes` and `validate_workflow`; probing and
    registering only come in as the path for when the catalog lacks the source."""
    texto = ag.INSTRUCOES_DA_HOME
    assert texto.index("search_sources") < texto.index("search_nodes") < texto.index("validate_workflow")
    assert texto.index("describe_source") < texto.index("probe_source") < texto.index("register_source")
    # And the two that probe are among the ones that pass without a click.
    assert {"probe_source", "register_source"} <= ag.ESCRITAS_SEM_CLIQUE


async def test_duas_confirmacoes_em_paralelo_casam_cada_uma_com_sua_chamada():
    """The race regression: with the batch running together, each confirmation stores
    ITS args under ITS `tool_use_id`. With a shared "current call" field (the old
    design), both would match the id that was written last — and a click would
    execute the wrong action."""
    redis = RedisFalso()
    estado, eventos = _estado(redis=redis)

    veredito_a, veredito_b = await asyncio.gather(
        ag._portao_da_home(estado, "delete_schedule", {"job_id": "job-a"}, "tu-A"),
        ag._portao_da_home(estado, "delete_schedule", {"job_id": "job-b"}, "tu-B"),
    )

    assert veredito_a is not None and veredito_b is not None
    assert veredito_a[1] is False and veredito_b[1] is False

    guardado_a = json.loads(redis.dados[ag.chave_de_confirmacao("usr-1", "conv-1", "tu-A")])
    guardado_b = json.loads(redis.dados[ag.chave_de_confirmacao("usr-1", "conv-1", "tu-B")])
    assert guardado_a["args"] == {"job_id": "job-a"}
    assert guardado_b["args"] == {"job_id": "job-b"}

    confirmacoes = {e.dados["tool_use_id"]: e.dados for e in eventos if e.tipo == "confirmacao"}
    assert set(confirmacoes) == {"tu-A", "tu-B"}
    assert confirmacoes["tu-A"]["token"] == guardado_a["token"]
    assert confirmacoes["tu-B"]["token"] == guardado_b["token"]
