# tests/unit/test_schedule_fluxo_inativo.py
"""Writing a schedule on a DEACTIVATED workflow is a domain refusal, not a 500.

`ScheduleService._get_workflow_by_hash` refused an inactive workflow with a
generic `ValueError`. There is no `ValueError` handler — `app/main.py` registers
`AtlasBaseError` and a generic `Exception` —, so the refusal reached the client
as a **500**, with an internal error message. Now it is `WorkflowInactiveError`
(409), and a nonexistent workflow is `WorkflowNotFoundError` (404).

Reading the schedules of a stopped workflow still works: it goes through the MCP
tool `list_schedules` (`app/mcp/tools/gatilhos.py`, tested in
`test_mcp_gatilhos.py`), which does not go through the execution guard.
"""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import WorkflowInactiveError, WorkflowNotFoundError
from app.models.base import Base
from app.models.models import Schedule, Workflow
from app.schemas.schedule import ScheduleCreate
from app.services.schedule_service import ScheduleService

pytestmark = pytest.mark.asyncio

WS = "ws-1"
ATIVO = "wf-ativo"
INATIVO = "wf-inativo"

TABELAS = [Workflow.__table__, Schedule.__table__]


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as sessao:
        sessao.add(Workflow(id_hash=ATIVO, name="Vivo", workspace_id=WS,
                            definition={"nodes": [], "edges": []}, flag_ative=True))
        sessao.add(Workflow(id_hash=INATIVO, name="Parado", workspace_id=WS,
                            definition={"nodes": [], "edges": []}, flag_ative=False))
        await sessao.commit()
        yield sessao
    await engine.dispose()


async def test_criar_em_fluxo_inexistente_e_404_de_dominio(db):
    """`WorkflowNotFoundError` (404), not `ValueError` — which would become a 500."""
    pedido = ScheduleCreate(strategy="interval", interval=10, unit="minutes",
                            workspace_id=WS, timezone="America/La_Paz")
    with pytest.raises(WorkflowNotFoundError):
        await ScheduleService(db).create_schedule("nao-existe", pedido)


async def test_criar_em_fluxo_inativo_e_409_de_dominio(db):
    """Writing STILL refuses — what changes is the code, not the rule.

    The scheduler ignores schedules of inactive workflows, so the stored row
    would never fire. `WorkflowInactiveError` carries 409 and `workflow_inactive`;
    the former `ValueError` reached the client as "erro interno" (internal error).
    """
    pedido = ScheduleCreate(strategy="interval", interval=10, unit="minutes",
                            workspace_id=WS, timezone="America/La_Paz")
    with pytest.raises(WorkflowInactiveError):
        await ScheduleService(db).create_schedule(INATIVO, pedido)


async def test_a_recusa_de_escrita_tem_status_e_codigo(db):
    """Without this, swapping the exception for another `AtlasBaseError` would go unnoticed."""
    assert WorkflowInactiveError.status_code == 409
    assert WorkflowInactiveError.error_code == "workflow_inactive"
    assert WorkflowNotFoundError.status_code == 404
