# tests/unit/test_scheduler_no_executor.py
"""
Agendador sem executor (spec §7.4): a ocorrência não some. Antes, o laço
engolia a exceção e só avançava `next_run_at` — um cron cujo grupo (ou o
pool) estava fora desaparecia sem run e sem aviso.
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
    db.add.assert_not_called()   # nenhum run sintético quando o dispatch deu certo
    # o workflow já carregado vai no start_analysis (sem SELECT duplicado)
    assert service.start_analysis.await_args.kwargs["workflow"] is not None


@pytest.mark.asyncio
async def test_outras_excecoes_tambem_materializam_run_e_alerta():
    """Qualquer falha do dispatch agendado — não só a falta de executor — vira um
    run `failed` visível + alerta, em vez de sumir no log enquanto o `next_run_at`
    avança. A exceção original ainda sobe (o laço a registra)."""
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
    assert run.error_category == "internal"   # única categoria legal (≤16) p/ erro genérico
    assert "boom" in (run.error_message or "")
    db.commit.assert_awaited()
    fechar.assert_awaited_once()
    alerta.assert_awaited_once()
    assert alerta.await_args.kwargs["category"] == "internal"


@pytest.mark.asyncio
async def test_excecao_com_run_id_nao_materializa_segundo_run():
    """`_dispatch_job` já criou e fechou um run `failed` (dedicado caiu na
    janela de graça, fila cheia): o agendador NÃO grava outro — senão o
    histórico e o usage_daily contam a mesma falha duas vezes."""
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
    # O alerta ao dono continua: a ocorrência falhou de qualquer jeito.
    alerta.assert_awaited_once()
