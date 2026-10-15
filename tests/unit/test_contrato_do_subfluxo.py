# tests/unit/test_contrato_do_subfluxo.py
"""
A sub-workflow's contract, seen from the workflows that call it.

A workflow called by others declares its contract in the `ports` of
SubWorkflowInput and SubWorkflowOutput. Renaming or removing a port there and
saving broke every caller in silence: a caller's edge whose `from_key` named
the old output delivered nothing at run, and an input mapped by the old name
was dropped by the child. Nobody was told when the child was saved.

The save still goes through — the choice was to warn, not to pin versions —
and the PUT now lists the callers IN THE SAME WORKSPACE that use what was
removed, and only them.

Real SQLite where it matters: which rows the query reaches (another workspace,
the trash) is exactly what a mock of `db.execute` would not prove.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.routers import workflows_router as WR
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowRead, WorkflowUpdate
from app.services.contrato_do_subfluxo import (
    avisos_aos_pais, contratos_dos_filhos, diagnosticos_de_contrato, portas_removidas,
)
from tests.unit._mcp_harness import TABLES, in_memory_db

FILHO = "filho-1"


def _filho(saidas=("faixa", "mapa"), entradas=("focos", "bbox"), com_entrada=True):
    nos = [{"id": "out", "name": "SubWorkflowOutput", "type": "output", "properties": {"ports": list(saidas)}}]
    if com_entrada:
        nos.insert(0, {"id": "in", "name": "SubWorkflowInput", "type": "trigger",
                       "properties": {"ports": list(entradas)}})
    return {"nodes": nos, "edges": []}


def _pai(*, saindo=(), chegando=(), mapping=None, filho=FILHO):
    """A caller whose node `sub` calls `filho`: `saindo` are the from_keys of the
    edges leaving it, `chegando` the to_keys of the edges arriving at it."""
    props = {"workflowHash": filho}
    if mapping is not None:
        props["inputsMapping"] = mapping
    return {
        "nodes": [
            {"id": "t", "name": "WebhookTrigger", "type": "trigger", "properties": {}},
            {"id": "sub", "name": "SubWorkflow", "type": "control", "properties": props},
        ],
        "edges": [
            *({"source": "t", "target": "sub", "from_key": "output", "to_key": k} for k in chegando),
            *({"source": "sub", "target": f"d{i}", "source_handle": k, "from_key": k}
              for i, k in enumerate(saindo)),
        ],
    }


def _wf(id_hash, definition, *, ws="ws-1", name=None, **colunas):
    return Workflow(id_hash=id_hash, name=name or id_hash, workspace_id=ws,
                    definition=definition, flag_ative=True, **colunas)


def _aviso(side, ports, edges, workflow_id="pai", workflow_name="Relatório"):
    return {"workflow_id": workflow_id, "workflow_name": workflow_name, "node_id": "sub",
            "side": side, "ports": ports, "edges": edges}


# ── What counts as removed ────────────────────────────────────────────────────

def test_renomear_uma_saida_conta_como_remover():
    assert portas_removidas(_filho(), _filho(saidas=("faixa_risco", "mapa"))) == ({"faixa"}, set())


def test_porta_nova_nao_remove_nada():
    assert portas_removidas(_filho(), _filho(saidas=("faixa", "mapa", "extra"))) == (set(), set())


def test_entrada_sem_portas_volta_a_aceitar_tudo():
    # SubWorkflowInput with no ports is passthrough: every key a caller maps
    # still reaches the child, so nothing it sends is dropped.
    assert portas_removidas(_filho(), _filho(entradas=())) == (set(), set())


def test_tirar_o_no_de_entrada_remove_as_entradas():
    assert portas_removidas(_filho(), _filho(com_entrada=False)) == (set(), {"focos", "bbox"})


def test_workflow_que_nao_e_subfluxo_nao_tem_o_que_remover():
    comum = {"nodes": [{"id": "a", "name": "ReadGeoJSON", "properties": {}}], "edges": []}
    assert portas_removidas(comum, {"nodes": [], "edges": []}) == (set(), set())


# ── Who is listed ─────────────────────────────────────────────────────────────

@pytest.fixture
async def banco():
    async with in_memory_db() as fabrica:
        yield fabrica


async def _gravar(fabrica, *workflows):
    async with fabrica() as db:
        db.add_all(workflows)
        await db.commit()


async def _avisos(fabrica, saidas=(), entradas=()):
    async with fabrica() as db:
        return await avisos_aos_pais(db, FILHO, "ws-1", set(saidas), set(entradas))


async def test_pai_que_usa_a_saida_removida_e_listado(banco):
    await _gravar(banco, _wf("pai", _pai(saindo=("faixa", "faixa", "mapa")), name="Relatório"))
    assert await _avisos(banco, saidas={"faixa"}) == [_aviso("saida", ["faixa"], 2)]


async def test_pai_que_so_usa_portas_que_ficaram_nao_e_listado(banco):
    await _gravar(banco, _wf("pai", _pai(saindo=("mapa",), chegando=("bbox",))))
    assert await _avisos(banco, saidas={"faixa"}, entradas={"focos"}) == []


async def test_pai_de_outro_workspace_nunca_e_listado(banco):
    await _gravar(banco, _wf("pai-alheio", _pai(saindo=("faixa",)), ws="ws-2"))
    assert await _avisos(banco, saidas={"faixa"}) == []


async def test_pai_na_lixeira_nao_e_listado(banco):
    await _gravar(banco, _wf("pai", _pai(saindo=("faixa",)), deleted_at=datetime(2026, 1, 1)))
    assert await _avisos(banco, saidas={"faixa"}) == []


async def test_pai_desativado_ainda_e_listado(banco):
    # Deactivated is not gone: it is still in the project list and breaks the
    # moment someone turns it back on.
    pai = _wf("pai", _pai(saindo=("faixa",)), name="Relatório")
    pai.flag_ative = False
    await _gravar(banco, pai)
    assert await _avisos(banco, saidas={"faixa"}) == [_aviso("saida", ["faixa"], 1)]


async def test_aresta_so_com_source_handle_tambem_conta(banco):
    pai = _pai()
    pai["edges"] += [
        {"source": "sub", "target": "d", "source_handle": "faixa"},
        # The run reads the from_key, and the editor re-anchors from it: a stale
        # handle next to a valid from_key breaks nothing.
        {"source": "sub", "target": "e", "source_handle": "faixa", "from_key": "mapa"},
    ]
    await _gravar(banco, _wf("pai", pai, name="Relatório"))
    assert await _avisos(banco, saidas={"faixa"}) == [_aviso("saida", ["faixa"], 1)]


async def test_aresta_salva_da_porta_com_o_envelope_conta_como_a_porta(banco):
    # The old drag defect saved port `faixa` as the handle and the envelope as
    # the key. The run reads that pair as `faixa` (`from_key_efetiva`), so
    # removing `faixa` breaks this caller too.
    pai = _pai()
    pai["edges"].append({"source": "sub", "target": "d", "source_handle": "faixa", "from_key": "subWorkflowResult"})
    await _gravar(banco, _wf("pai", pai, name="Relatório"))
    assert await _avisos(banco, saidas={"faixa"}) == [_aviso("saida", ["faixa"], 1)]


def test_validacao_le_a_aresta_antiga_como_a_porta():
    # Not "uses the envelope": it is validated as the port it was pulled from.
    contratos = {FILHO: {"inputs": [], "outputs": [{"name": "faixa"}, {"name": "mapa"}]}}
    antiga = {"source": "sub", "target": "d", "source_handle": "faixa", "from_key": "subWorkflowResult"}
    assert diagnosticos_de_contrato({**_pai(), "edges": [antiga]}, contratos) == []

    sem_a_porta = {FILHO: {"inputs": [], "outputs": [{"name": "mapa"}]}}
    [diag] = diagnosticos_de_contrato({**_pai(), "edges": [antiga]}, sem_a_porta)
    assert (diag["code"], diag["from_key"]) == ("edge_from_key_unknown", "faixa")

    # The envelope chosen on purpose (no handle) still gets the warning.
    envelope = {"source": "sub", "target": "d", "from_key": "subWorkflowResult"}
    assert [d["code"] for d in diagnosticos_de_contrato({**_pai(), "edges": [envelope]}, contratos)] \
        == ["edge_subworkflow_envelope"]


async def test_id_de_no_numerico_sai_como_texto(banco):
    # A definition written by hand through the API may carry a numeric id; the
    # notice is validated after the save committed, and must not become a 500.
    pai = _pai(saindo=("faixa",))
    pai["nodes"][1]["id"] = 7
    pai["edges"][0]["source"] = 7
    await _gravar(banco, _wf("pai", pai, name="Relatório"))
    assert [a["node_id"] for a in await _avisos(banco, saidas={"faixa"})] == ["7"]


async def test_entrada_removida_no_mapeamento_gravado_pelo_editor(banco):
    # The editor stores `inputsMapping` as JSON text (`setNodeField` only takes
    # primitives) and the run decodes it — reading only a dict would miss every
    # caller wired in the editor.
    pai = _pai(mapping='{"focos": "output", "bbox": "regiao"}')
    await _gravar(banco, _wf("pai", pai, name="Relatório"))
    assert await _avisos(banco, entradas={"focos"}) == [_aviso("entrada", ["focos"], 0)]


async def test_entrada_removida_no_to_key_de_aresta_que_chega(banco):
    await _gravar(banco, _wf("pai", _pai(chegando=("focos", "bbox")), name="Relatório"))
    assert await _avisos(banco, entradas={"focos"}) == [_aviso("entrada", ["focos"], 1)]


async def test_com_mapeamento_o_to_key_e_chave_do_pai(banco):
    # With a mapping only the mapped keys reach the child (sub_workflow.py,
    # step 4): the edge's to_key names the parent's key, not a child port.
    pai = _pai(chegando=("focos",), mapping={"bbox": "focos"})
    await _gravar(banco, _wf("pai", pai))
    assert await _avisos(banco, entradas={"focos"}) == []


async def test_saida_e_entrada_do_mesmo_no_viram_dois_avisos(banco):
    await _gravar(banco, _wf("pai", _pai(saindo=("faixa",), chegando=("focos",)), name="Relatório"))
    assert await _avisos(banco, saidas={"faixa"}, entradas={"focos"}) == [
        _aviso("saida", ["faixa"], 1), _aviso("entrada", ["focos"], 1),
    ]


async def test_sem_nada_removido_nao_consulta_o_banco():
    db = MagicMock(execute=AsyncMock(side_effect=AssertionError("consultou o banco")))
    assert await avisos_aos_pais(db, FILHO, "ws-1", set(), set()) == []


async def test_falha_na_consulta_nao_vira_erro():
    # The save already happened: a broken notice must not turn it into a 500.
    db = MagicMock(execute=AsyncMock(side_effect=RuntimeError("banco fora")))
    assert await avisos_aos_pais(db, FILHO, "ws-1", {"faixa"}, set()) == []


# ── The PUT ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def api(client, monkeypatch):
    """The real app, service and route over SQLite: the child, a caller in its
    workspace and a caller in someone else's."""
    from app.api.dependencies import get_current_user, get_db
    from app.core.rate_limiter import limiter
    from app.main import app
    from app.models.base import Base
    from app.models.user import User
    from app.models.workflow_group import WorkflowGroup
    from app.models.workspace import Workspace

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[*TABLES, WorkflowGroup.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        db.add_all([User(id_hash=u, username=u, email=f"{u}@t", hashed_password="x") for u in ("u-1", "u-2")])
        db.add_all([
            Workspace(id_hash="ws-1", name="Equipe", owner_id="u-1"),
            Workspace(id_hash="ws-2", name="Outra", owner_id="u-2"),
        ])
        db.add_all([
            _wf(FILHO, _filho(), name="Filho"),
            _wf("pai", _pai(saindo=("faixa",)), name="Relatório"),
            _wf("pai-alheio", _pai(saindo=("faixa",)), ws="ws-2", name="De outra equipe"),
        ])
        await db.commit()

    async def _db():
        async with fabrica() as sessao:
            yield sessao

    async def _quem():
        return SimpleNamespace(id_hash="u-1", username="u-1", email="u-1@t", role="user", is_active=True)

    anteriores = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _quem
    monkeypatch.setattr(limiter, "enabled", False)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t",
        ) as ac:
            yield ac, fabrica
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)
        await engine.dispose()


async def test_salvar_o_filho_lista_os_pais_que_usam_a_porta_removida(api):
    ac, fabrica = api
    nova = _filho(saidas=("faixa_risco", "mapa"))
    resposta = await ac.put(f"/workflows/{FILHO}", json={"definition": nova})

    assert resposta.status_code == 200, resposta.text
    # The caller in the other workspace uses the same port and is not listed.
    assert resposta.json()["subworkflow_notices"] == [_aviso("saida", ["faixa"], 1)]
    # Warned, not blocked: the child is stored with the new contract.
    async with fabrica() as db:
        salva = (await db.execute(select(Workflow.definition).where(Workflow.id_hash == FILHO))).scalar_one()
    assert salva["nodes"][1]["properties"]["ports"] == ["faixa_risco", "mapa"]


async def test_salvar_sem_mexer_no_contrato_nao_avisa(api):
    ac, _ = api
    nova = _filho()
    nova["viewport"] = {"x": 10, "y": 0, "zoom": 1}
    resposta = await ac.put(f"/workflows/{FILHO}", json={"definition": nova})

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["subworkflow_notices"] == []


class _Wf:
    id_hash = FILHO
    workspace_id = "ws-1"
    definition = _filho()


class _Resultado:
    def __init__(self, definition):
        self.definition = definition


@pytest.fixture
def rota(monkeypatch):
    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(WR, "_recusar_segredo", lambda *a, **k: None)

    class _Service:
        async def update_workflow(self, id_hash, workflow_in, **kw):
            return _Resultado(workflow_in.definition)

    def salvar(nova, db):
        return WR.update_workflow(
            request=None, workflow_in=WorkflowUpdate(definition=nova), service=_Service(),
            wf=_Wf(), db=db, current_user=SimpleNamespace(id_hash="u-1"),
        )

    return salvar


async def test_contrato_igual_nao_consulta_os_pais(rota):
    db = MagicMock(execute=AsyncMock(side_effect=AssertionError("consultou o banco")))
    nova = _filho()
    nova["nodes"][0]["position"] = {"x": 300, "y": 0}

    resposta = await rota(nova, db)

    db.execute.assert_not_awaited()
    assert getattr(resposta, "subworkflow_notices", []) == []


async def test_aviso_que_falha_nao_impede_o_save(rota):
    db = MagicMock(execute=AsyncMock(side_effect=RuntimeError("banco fora")))
    resposta = await rota(_filho(saidas=("mapa",)), db)

    assert resposta.definition["nodes"][1]["properties"]["ports"] == ["mapa"]
    assert resposta.subworkflow_notices == []


def test_objeto_que_responde_qualquer_atributo_ainda_serializa():
    # Read from the object the route returns, which only has it when the route
    # set it. Anything that is not a list is "no notice", never a 500.
    campos = dict(
        id=1, id_hash="wf-1", name="x", flag_ative=True, description=None, version=None,
        priority=0, definition={"nodes": [], "edges": []},
        created_at="2026-01-01T00:00:00", updated_at="2026-01-01T00:00:00",
    )
    for qualquer in (MagicMock(), Mock()):
        assert WorkflowRead.model_validate({**campos, "subworkflow_notices": qualquer}).subworkflow_notices == []
    lido = WorkflowRead.model_validate({**campos, "subworkflow_notices": [_aviso("saida", ["faixa"], 1)]})
    assert lido.model_dump()["subworkflow_notices"] == [_aviso("saida", ["faixa"], 1)]


# ── Validation reads the child's contract — in the workspace only ────────────

async def test_contrato_do_filho_vem_so_do_workspace_e_so_se_ativo(banco):
    inativo = _wf("filho-inativo", _filho())
    inativo.flag_ative = False
    await _gravar(banco, _wf(FILHO, _filho()), _wf("filho-alheio", _filho(), ws="ws-2"), inativo)
    pai = {"nodes": [
        {"id": f"s{i}", "name": "SubWorkflow", "properties": {"workflowHash": h}}
        for i, h in enumerate((FILHO, "filho-alheio", "filho-inativo"))
    ], "edges": []}

    async with banco() as db:
        contratos = await contratos_dos_filhos(db, pai, "ws-1")

    assert list(contratos) == [FILHO]
    assert [p["name"] for p in contratos[FILHO]["outputs"]] == ["faixa", "mapa"]


async def test_sem_subfluxo_nao_consulta_o_banco():
    db = MagicMock(execute=AsyncMock(side_effect=AssertionError("consultou o banco")))
    comum = {"nodes": [{"id": "a", "name": "ReadGeoJSON", "properties": {}}], "edges": []}
    assert await contratos_dos_filhos(db, comum, "ws-1") == {}
