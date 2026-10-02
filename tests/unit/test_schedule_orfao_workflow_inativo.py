# tests/unit/test_schedule_orfao_workflow_inativo.py
"""Schedule ativo apontando para workflow desativado — o "schedule orfao".

Sintoma em producao, repetido a cada ocorrencia do cron:

    AsyncScheduler: falha ao disparar workflow 'X': Workflow X esta desativado.

O switch "Ativado/Inativo" da lista de projetos manda `PUT /workflows/{id}` so
com `flag_ative` — sem `definition`, `apply_schedule_if_needed` nem rodava, e o
Schedule ficava ativo apontando para um workflow que recusa executar. O mesmo
valia para o override do admin.

Duas travas, testadas aqui:
  1. `sync_schedules_with_workflow_state` alinha `Schedule.active` ao workflow.
  2. o `_tick` do scheduler nem enxerga schedule de workflow inativo.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.async_scheduler import AsyncScheduler
from app.core.scheduling.hooks import sync_schedules_with_workflow_state
from app.models.models import Schedule, Workflow, WorkflowGroup


# ── 1. Sincronizacao de Schedule.active com flag_ative ────────────────────────


def _definition(active: bool = True) -> dict:
    return {
        "nodes": [
            {
                "id": "n1",
                "type": "trigger",
                "name": "ScheduleTrigger",
                "properties": {
                    "strategy": "cron",
                    "cron_expression": "0 13 * * *",
                    "timezone": "America/Cuiaba",
                    "active": active,
                },
            }
        ]
    }


@pytest.fixture
def workflow():
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.flag_ative = True
    wf.definition = _definition()
    return wf


@pytest.fixture
def crud(monkeypatch):
    fake = MagicMock()
    fake.schedule_crud = MagicMock(
        get_by_workflow_hash=AsyncMock(return_value=[]),
        update=AsyncMock(),
    )
    monkeypatch.setattr("app.core.scheduling.hooks.ScheduleService", lambda db: fake)
    return fake


def _schedule(active: bool = True) -> MagicMock:
    return MagicMock(job_id="job-1", active=active, next_run_at=datetime(2026, 1, 1))


async def test_desativar_workflow_desliga_o_schedule(workflow, crud):
    """A regressao: era aqui que nascia o orfao."""
    workflow.flag_ative = False
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_awaited_once()
    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}


async def test_reativar_religa_o_schedule_zerando_next_run_at(workflow, crud):
    """`next_run_at` ficou no passado enquanto o workflow esteve desligado.

    Religar sem zerar dispararia o workflow no instante do clique.
    """
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=False)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    assert crud.schedule_crud.update.await_args.args[1] == {"active": True, "next_run_at": None}


async def test_reativar_respeita_o_no_desligado_no_canvas(workflow, crud):
    """Quem manda na reativacao e o `active` do ScheduleTrigger, nao o workflow.

    Religar tudo as cegas ressuscitaria o agendamento que o dono tinha desligado
    no editor antes de desativar o workflow.
    """
    workflow.definition = _definition(active=False)
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=False)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


async def test_reativar_sem_no_no_canvas_mantem_desligado(workflow, crud):
    """Sem ScheduleTrigger na definition nao ha agendamento legitimo."""
    workflow.definition = {"nodes": [{"id": "n1", "name": "Outro"}]}
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}


async def test_estado_ja_coerente_nao_escreve(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule(active=True)]

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


async def test_workflow_sem_schedule_e_no_op(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = []

    await sync_schedules_with_workflow_state(workflow, MagicMock())

    crud.schedule_crud.update.assert_not_awaited()


# ── 2. O tick nao enxerga schedule de workflow que nao pode executar ──────────


@pytest_asyncio.fixture
async def sessao_factory():
    """SQLite em memoria compartilhado entre sessoes (StaticPool).

    O `_tick` abre a propria sessao via `AsyncSessionLocal`; sem StaticPool cada
    conexao veria um banco vazio diferente.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[WorkflowGroup.__table__, Workflow.__table__, Schedule.__table__],
        )
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _semear(factory, *, flag_ative=True, deleted_at=None, sch_active=True, vencido=True):
    passado = datetime(2020, 1, 1)
    async with factory() as db:
        db.add(Workflow(
            id_hash="wf-1", name="wf", workspace_id="ws-1", definition={},
            flag_ative=flag_ative, deleted_at=deleted_at,
        ))
        db.add(Schedule(
            id_hash="sch-1", workflow_hash="wf-1", strategy="cron",
            cron_expression="0 13 * * *", job_id="job-1", active=sch_active,
            next_run_at=passado if vencido else datetime.utcnow() + timedelta(days=1),
        ))
        await db.commit()


async def _disparados(factory, monkeypatch) -> list[str]:
    """Roda um tick e devolve os job_id que chegaram a `_process_schedule`."""
    vistos: list[str] = []
    sched = AsyncScheduler()
    monkeypatch.setattr("app.core.async_scheduler.AsyncSessionLocal", factory)
    monkeypatch.setattr(
        sched, "_process_schedule",
        AsyncMock(side_effect=lambda s, now: vistos.append(s.job_id)),
    )
    await sched._tick()
    return vistos


async def test_tick_processa_schedule_de_workflow_ativo(sessao_factory, monkeypatch):
    await _semear(sessao_factory)

    assert await _disparados(sessao_factory, monkeypatch) == ["job-1"]


async def test_tick_respeita_o_limite_e_ordena_por_next_run_at(sessao_factory, monkeypatch):
    """O tick drena em lotes: com o teto em 2, so os 2 mais atrasados (menor
    next_run_at) chegam ao _process_schedule; o 3o espera o proximo ciclo. Os
    schedules entram FORA de ordem de horario de proposito, para distinguir o
    ORDER BY de um simples scan por rowid."""
    monkeypatch.setattr("app.core.async_scheduler.TICK_MAX_SCHEDULES", 2)

    base = datetime(2020, 1, 1)
    async with sessao_factory() as db:
        db.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        for i, (job, atraso) in enumerate([("job-c", 2), ("job-b", 1), ("job-a", 0)]):
            db.add(Schedule(
                id_hash=f"sch-{i}", workflow_hash="wf-1", strategy="cron",
                cron_expression="0 13 * * *", job_id=job, active=True,
                next_run_at=base + timedelta(minutes=atraso),
            ))
        await db.commit()

    assert await _disparados(sessao_factory, monkeypatch) == ["job-a", "job-b"]


async def test_tick_ignora_schedule_de_workflow_desativado(sessao_factory, monkeypatch):
    """A trava final: mesmo com o orfao ja no banco, o scheduler nao o toca."""
    await _semear(sessao_factory, flag_ative=False)

    assert await _disparados(sessao_factory, monkeypatch) == []


async def test_tick_ignora_schedule_de_workflow_soft_deletado(sessao_factory, monkeypatch):
    await _semear(sessao_factory, deleted_at=datetime(2026, 1, 1))

    assert await _disparados(sessao_factory, monkeypatch) == []


async def test_tick_ignora_schedule_desligado(sessao_factory, monkeypatch):
    await _semear(sessao_factory, sch_active=False)

    assert await _disparados(sessao_factory, monkeypatch) == []


async def test_tick_processa_schedule_novo_sem_next_run_at(sessao_factory, monkeypatch):
    """`next_run_at IS NULL` e o sinal de "calcular a primeira execucao".

    O JOIN novo nao pode ter deixado esses schedules parados para sempre.
    """
    async with sessao_factory() as db:
        db.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        db.add(Schedule(
            id_hash="sch-1", workflow_hash="wf-1", strategy="cron",
            cron_expression="0 13 * * *", job_id="job-1", active=True, next_run_at=None,
        ))
        await db.commit()

    assert await _disparados(sessao_factory, monkeypatch) == ["job-1"]
