# tests/unit/test_scheduler_no_executor.py
"""
Scheduler without an executor (spec §7.4): the occurrence does not vanish.
Before, the loop swallowed the exception and only advanced `next_run_at` — a
cron whose group (or the pool) was down disappeared with no run and no warning.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NoExecutorAvailableError


def _wf():
    wf = MagicMock(); wf.id_hash = "wf-1"; wf.workspace_id = "ws-1"; wf.name = "Bacia diária"
    return wf


def _sessao(db):
    @asynccontextmanager
    async def _ctx():
        yield db
    return _ctx


@pytest.mark.asyncio
async def test_sem_executor_registra_run_failed_e_alerta():
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(
        side_effect=NoExecutorAvailableError("Workspace isolado: nenhum dos 2 executores dedicados está disponível. O job NÃO foi enviado ao pool compartilhado.",
                                             category="no_dedicated_executor"),
    )
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()) as fechar, \
         patch("app.services.execution_alert_service.record_failure", AsyncMock(return_value=True)) as alerta, \
         patch("app.services.execution_alert_service.record_success", AsyncMock()) as recuperou:
        with pytest.raises(NoExecutorAvailableError):
            await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)

    run = db.add.call_args.args[0]
    assert type(run).__name__ == "WorkflowRun"
    assert run.status == "failed" and run.schedule_id == 7 and run.workspace_id == "ws-1"
    assert run.host is None and run.dispatch_tier is None
    assert "Execução agendada não despachada" in run.error_message
    db.commit.assert_awaited()
    fechar.assert_awaited_once()
    alerta.assert_awaited_once()
    assert alerta.await_args.kwargs["category"] == "no_dedicated_executor"
    recuperou.assert_not_awaited()


@pytest.mark.asyncio
async def test_ocorrencia_que_roda_registra_recuperacao():
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(return_value=MagicMock(id="task-1"))
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.services.execution_alert_service.record_success", AsyncMock(return_value=False)) as recuperou:
        await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)
    recuperou.assert_awaited_once()
    db.add.assert_not_called()   # no synthetic run when the dispatch succeeded
    # the already loaded workflow goes into start_analysis (no duplicate SELECT)
    assert service.start_analysis.await_args.kwargs["workflow"] is not None


@pytest.mark.asyncio
async def test_outras_excecoes_tambem_materializam_run_e_alerta():
    """Any failure of the scheduled dispatch — not only a missing executor — becomes
    a visible `failed` run + alert, instead of vanishing into the log while
    `next_run_at` advances. The original exception still propagates (the loop logs it)."""
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()) as fechar, \
         patch("app.services.execution_alert_service.record_failure", AsyncMock(return_value=True)) as alerta:
        with pytest.raises(RuntimeError):
            await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)

    run = db.add.call_args.args[0]
    assert type(run).__name__ == "WorkflowRun"
    assert run.status == "failed" and run.schedule_id == 7 and run.workspace_id == "ws-1"
    assert run.error_category == "internal"   # the only legal category (≤16) for a generic error
    assert "boom" in (run.error_message or "")
    db.commit.assert_awaited()
    fechar.assert_awaited_once()
    alerta.assert_awaited_once()
    assert alerta.await_args.kwargs["category"] == "internal"


@pytest.mark.asyncio
async def test_excecao_com_run_id_nao_materializa_segundo_run():
    """`_dispatch_job` already created and closed a `failed` run (dedicated one
    dropped within the grace window, queue full): the scheduler does NOT write
    another — otherwise the history and usage_daily count the same failure twice."""
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(
        side_effect=NoExecutorAvailableError("Nenhum executor aceitou o job.", category="no_executor_chain", run_id="run-1"),
    )
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()) as fechar, \
         patch("app.services.execution_alert_service.record_failure", AsyncMock(return_value=True)) as alerta:
        with pytest.raises(NoExecutorAvailableError):
            await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)

    db.add.assert_not_called()
    fechar.assert_not_awaited()
    # The alert to the owner still goes out: the occurrence failed either way.
    alerta.assert_awaited_once()
