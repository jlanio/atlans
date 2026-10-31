"""POST /drive/executor-trigger-workflow called a method that never existed
(review of 2026-10-31): every GeoSync trigger answered 500."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_the_geosync_trigger_dispatches_through_start_analysis(monkeypatch):
    from app.services import drive_service as D
    from app.services.workflow_service import WorkflowService

    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-1", flag_ative=True)
    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = wf
    db = MagicMock()
    db.execute = AsyncMock(return_value=resultado)
    start = AsyncMock(return_value=SimpleNamespace(id="run-9"))
    monkeypatch.setattr(WorkflowService, "start_analysis", start)

    resposta = await D.DriveService(db).trigger_workflow("wf-1", ["ws-1"], {"arquivo": "x.gpkg"})

    assert resposta == {"task_id": "run-9", "workflow_id_hash": "wf-1", "status": "dispatched"}
    args, kwargs = start.await_args
    assert args[0] == "wf-1"
    assert kwargs["inputs"] == {"arquivo": "x.gpkg"}
    assert kwargs["autenticar_entrada"] is False and kwargs["workflow"] is wf
