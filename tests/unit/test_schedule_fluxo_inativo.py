# tests/unit/test_schedule_fluxo_inativo.py
"""Escrever agendamento em fluxo DESATIVADO é recusa de domínio, não 500.

`ScheduleService._get_workflow_by_hash` recusava workflow inativo com um
`ValueError` genérico. Não há handler de `ValueError` — `app/main.py` registra
`AtlasBaseError` e um `Exception` genérico —, então a recusa chegava ao cliente
como **500**, com mensagem de erro interno. Agora é `WorkflowInactiveError`
(409), e workflow inexistente é `WorkflowNotFoundError` (404).

Ler os agendamentos de um fluxo parado continua valendo: é pela tool MCP
`list_schedules` (`app/mcp/tools/gatilhos.py`, testada em
`test_mcp_gatilhos.py`), que não passa pelo guardião de execução.
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
    """`WorkflowNotFoundError` (404), e não `ValueError` — que viraria 500."""
    pedido = ScheduleCreate(strategy="interval", interval=10, unit="minutes",
                            workspace_id=WS, timezone="America/La_Paz")
    with pytest.raises(WorkflowNotFoundError):
        await ScheduleService(db).create_schedule("nao-existe", pedido)


async def test_criar_em_fluxo_inativo_e_409_de_dominio(db):
    """Escrever CONTINUA recusando — o que muda é o código, não a regra.

    O agendador ignora agendamento de fluxo inativo, então a linha gravada
    nunca dispararia. `WorkflowInactiveError` carrega 409 e `workflow_inactive`;
    o `ValueError` de antes chegava ao cliente como "erro interno".
    """
    pedido = ScheduleCreate(strategy="interval", interval=10, unit="minutes",
                            workspace_id=WS, timezone="America/La_Paz")
    with pytest.raises(WorkflowInactiveError):
        await ScheduleService(db).create_schedule(INATIVO, pedido)


async def test_a_recusa_de_escrita_tem_status_e_codigo(db):
    """Sem isto, trocar a exceção por outra `AtlasBaseError` passaria batido."""
    assert WorkflowInactiveError.status_code == 409
    assert WorkflowInactiveError.error_code == "workflow_inactive"
    assert WorkflowNotFoundError.status_code == 404
