# tests/unit/test_consumer_aprende_fontes.py
"""The "sources" phase of the result consumer: the catalog learns from the run.

Only a `success` run, only when there is a `WFS` node in the stats, only with the
flag on — and the definition comes from the CURRENT Workflow. The phase is one
among the others in `_process_result`, isolated by `_run_phase`: failing here
does not take down the notification, and is reported as a loss like any other.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core import run_result_consumer as rrc
from app.models.models import Workflow
from tests.unit.test_fix_consumer_services import _make_run, _mock_db, _result

DEFINICAO = {"nodes": [{"id": "f1", "name": "WFS", "properties": {"url": "https://h/ows", "typeName": "a:b"}}], "edges": []}
STATS_WITH_WFS = {"f1": {"node_name": "WFS", "status": "completed"}, "__metrics__": {"nodes": {}}}


def _workflow(definition=DEFINICAO) -> Workflow:
    return Workflow(id_hash="wf-hash", name="Fluxo", workspace_id="ws-alvo", definition=definition, flag_ative=True)


async def test_disabled_flag_does_not_touch_the_db():
    db = _mock_db([])
    with patch("app.core.config.FONTES_APRENDER_DAS_EXECUCOES", False):
        await rrc._aprender_fontes_if_present(db, _make_run(status="success"), STATS_WITH_WFS, True)
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("status", ["failed", "cancelled", "running"])
async def test_only_successful_run_teaches(status):
    db = _mock_db([])
    await rrc._aprender_fontes_if_present(db, _make_run(status=status), STATS_WITH_WFS, True)
    db.execute.assert_not_awaited()


async def test_without_wfs_node_does_not_even_query_the_workflow():
    db = _mock_db([])
    stats = {"b1": {"node_name": "Buffer", "status": "completed"}, "__run_meta__": {"retry_count": 0}}
    await rrc._aprender_fontes_if_present(db, _make_run(status="success"), stats, True)
    db.execute.assert_not_awaited()


async def test_run_without_workspace_does_not_learn():
    db = _mock_db([])
    await rrc._aprender_fontes_if_present(db, _make_run(status="success", workspace_id=None), STATS_WITH_WFS, True)
    db.execute.assert_not_awaited()


async def test_loads_the_current_definition_and_delegates_to_catalog():
    run = _make_run(status="success")
    db = _mock_db([_result(_workflow())])
    learn = AsyncMock(return_value=1)
    with patch("app.services.fontes_service.aprender_de_execucao", learn):
        await rrc._aprender_fontes_if_present(db, run, STATS_WITH_WFS, False)

    learn.assert_awaited_once()
    args, kwargs = learn.await_args
    assert args[0] is db and args[1] is run and args[2] is STATS_WITH_WFS and args[3] == DEFINICAO
    assert kwargs == {"first_close": False}  # redelivery: does not count the usage again
    db.commit.assert_awaited_once()


async def test_nothing_learned_does_not_commit():
    db = _mock_db([_result(_workflow())])
    with patch("app.services.fontes_service.aprender_de_execucao", AsyncMock(return_value=0)):
        await rrc._aprender_fontes_if_present(db, _make_run(status="success"), STATS_WITH_WFS, True)
    db.commit.assert_not_awaited()


async def test_deleted_workflow_or_without_definition_does_not_learn():
    learn = AsyncMock(return_value=1)
    with patch("app.services.fontes_service.aprender_de_execucao", learn):
        await rrc._aprender_fontes_if_present(_mock_db([_result(None)]), _make_run(status="success"), STATS_WITH_WFS, True)
        await rrc._aprender_fontes_if_present(_mock_db([_result(_workflow(definition=None))]), _make_run(status="success"), STATS_WITH_WFS, True)
    learn.assert_not_awaited()


async def test_the_phase_is_in_the_pipeline_between_pins_and_notification():
    """The order is the contract: after the metrics (which bring the schema), before the end."""
    run = _make_run(status="running")
    db = _mock_db([_result(run)])
    ordem: list[str] = []

    def _mark(nome):
        async def _phase(*_a):
            ordem.append(nome)
        return _phase

    payload = {
        "task_id": run.task_id, "status": "success", "end_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "stats": {},
    }
    with patch.object(rrc, "_upsert_usage_daily", _mark("uso")), \
         patch.object(rrc, "_persist_metrics_if_present", _mark("metricas")), \
         patch.object(rrc, "_register_artifacts_if_present", _mark("artefatos")), \
         patch.object(rrc, "_persist_pinned_outputs_if_present", _mark("pins")), \
         patch.object(rrc, "_aprender_fontes_if_present", _mark("fontes")), \
         patch.object(rrc, "_fire_notification_if_configured", _mark("notificacao")):
        assert await rrc._process_result(db, payload) is True

    assert ordem == ["uso", "metricas", "artefatos", "pins", "fontes", "notificacao"]


async def test_phase_failure_is_isolated_and_reported():
    run = _make_run(status="running")
    db = _mock_db([_result(run)])

    async def _ok(*_a):
        return None

    async def _explode(*_a):
        raise RuntimeError("catálogo fora")

    payload = {"task_id": run.task_id, "status": "success", "end_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(), "stats": {}}
    with patch.object(rrc, "_upsert_usage_daily", _ok), \
         patch.object(rrc, "_persist_metrics_if_present", _ok), \
         patch.object(rrc, "_register_artifacts_if_present", _ok), \
         patch.object(rrc, "_persist_pinned_outputs_if_present", _ok), \
         patch.object(rrc, "_aprender_fontes_if_present", _explode), \
         patch.object(rrc, "_fire_notification_if_configured", _ok):
        with pytest.raises(rrc.PhaseFailure) as exc:
            await rrc._process_result(db, payload)
    assert exc.value.labels == ["fontes"]
    db.rollback.assert_awaited()
