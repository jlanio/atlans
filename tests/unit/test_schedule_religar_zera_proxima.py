# tests/unit/test_schedule_religar_zera_proxima.py
"""Religar um agendamento pausado ZERA `next_run_at`.

O bug: enquanto o agendamento esteve pausado, o `next_run_at` ficou parado num
horário passado. Ao religar (`active=true`) sem zerar, `_process_schedule` vê
`now >= next_run_at` e dispara o workflow na hora — efeito colateral invisível
de virar o interruptor. A correção mora em `ScheduleService.update_schedule`, no
caminho que a rota REST (`PUT /workflows/{id}/schedules/{job}`) e a tool MCP
`update_schedule` compartilham.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.models import Schedule, Workflow
from app.schemas.schedule import ScheduleUpdate
from app.services.schedule_service import ScheduleService, campos_de_ativacao

WF = "wf-1"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[Workflow.__table__, Schedule.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _semear(db, *, active, next_run_at):
    job_id = f"job-{uuid4()}"
    db.add(Schedule(
        workflow_hash=WF, strategy="cron", cron_expression="0 6 * * *",
        timezone="America/Cuiaba", active=active, next_run_at=next_run_at,
        job_id=job_id, workspace_id="ws-1",
    ))
    await db.commit()
    return job_id


PASSADO = datetime(2020, 1, 1, 6, 0)  # muito antes de agora, naive (como o banco grava)


@pytest.mark.asyncio
async def test_religar_pausado_zera_next_run_at(db):
    job = await _semear(db, active=False, next_run_at=PASSADO)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=True), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    # O ponto: o horário parado no passado NÃO sobrevive à reativação.
    assert atualizado.next_run_at is None


@pytest.mark.asyncio
async def test_mudar_o_horario_com_ativo_zera_next_run_at(db):
    """Já ativo, mas o HORÁRIO mudou: o `next_run_at` gravado foi calculado da
    cron ANTIGA, então mantê-lo faria a próxima ocorrência sair no horário velho
    uma vez. Zerar força `_process_schedule` a recalcular a partir da cron nova
    (e `None` não dispara na hora — recomputa a próxima ocorrência FUTURA)."""
    futuro = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    job = await _semear(db, active=True, next_run_at=futuro)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=True, cron_expression="30 7 * * *"), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    assert atualizado.next_run_at is None


@pytest.mark.asyncio
async def test_reeditar_ativo_sem_mudar_o_horario_nao_zera(db):
    """Já ativo e o horário NÃO mudou (re-salvar a mesma cron): a próxima
    ocorrência calculada é preservada — só uma mudança real de temporização, ou a
    transição pausado→ativo, zera."""
    futuro = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    job = await _semear(db, active=True, next_run_at=futuro)
    atualizado = await ScheduleService(db).update_schedule(
        # Mesma cron que `_semear` grava ("0 6 * * *").
        job, ScheduleUpdate(active=True, cron_expression="0 6 * * *"), owner_workflow_hash=WF,
    )
    assert atualizado.active is True
    assert atualizado.next_run_at == futuro


@pytest.mark.asyncio
async def test_pausar_nao_toca_next_run_at(db):
    """Desligar preserva o `next_run_at` (nada a recalcular ao pausar)."""
    job = await _semear(db, active=True, next_run_at=PASSADO)
    atualizado = await ScheduleService(db).update_schedule(
        job, ScheduleUpdate(active=False), owner_workflow_hash=WF,
    )
    assert atualizado.active is False
    assert atualizado.next_run_at == PASSADO


def test_campos_de_ativacao_e_a_fonte_canonica():
    """A semântica que o hook e o update_schedule compartilham, num lugar só."""
    assert campos_de_ativacao(True) == {"active": True, "next_run_at": None}
    assert campos_de_ativacao(False) == {"active": False}
