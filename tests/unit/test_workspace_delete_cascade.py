# tests/unit/test_workspace_delete_cascade.py
"""No workflow survives as active the deletion of its workspace.

Regression: the workspace DELETE did not touch workflows or schedules. The
workflow vanished from the UI (the listing is by accessible workspace) but the
AsyncScheduler kept triggering it — the tick filters only by Schedule.active.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.workflow_service import (
    restore_workspace_workflows,
    soft_delete_workspace_workflows,
)

# Timestamp shared between Workspace.deleted_at and the cascaded workflows.
_DELETED_AT = datetime(2026, 8, 3, 10, 5, 44)


def _rows_result(rows: list[tuple]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def _update_result(rowcount: int = 0) -> MagicMock:
    result = MagicMock()
    result.rowcount = rowcount
    return result


async def test_workspace_without_workflows_fires_no_updates():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_rows_result([]))

    out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 0, "schedules": 0}
    assert db.execute.await_count == 1  # apenas o SELECT


async def test_soft_deletes_pending_and_deactivates_schedules():
    active_a, active_b, ja_deletado = str(uuid4()), str(uuid4()), str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([
            (active_a, None),
            (active_b, None),
            (ja_deletado, datetime(2026, 7, 27, 14, 20)),
        ]),
        _update_result(),   # UPDATE workflows
        _update_result(2),  # UPDATE schedules
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ) as cleanup:
        out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 2, "schedules": 2}

    stmts = [call.args[0] for call in db.execute.await_args_list]
    wf_update, sched_update = stmts[1], stmts[2]

    assert wf_update.table.name == "workflows"
    wf_params = wf_update.compile().params
    assert wf_params["flag_ative"] is False
    # Same timestamp as the workspace — it is the mark the restore uses
    assert wf_params["deleted_at"] == _DELETED_AT

    assert sched_update.table.name == "schedules"
    assert sched_update.compile().params["active"] is False

    # ChangeDetector is only cleared for those soft-deleted just now
    assert {c.args[0] for c in cleanup.await_args_list} == {active_a, active_b}


async def test_deactivates_schedule_of_already_soft_deleted_workflow():
    """An active schedule of an already-deleted workflow also goes down — the cascade covers them all."""
    wf_id = str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([(wf_id, datetime(2026, 4, 9, 13, 43))]),
        _update_result(1),  # UPDATE schedules — no UPDATE of workflows
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ) as cleanup:
        out = await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert out == {"workflows": 0, "schedules": 1}
    assert db.execute.await_count == 2
    cleanup.assert_not_awaited()


async def test_does_not_commit_on_its_own():
    """The one that commits is delete_workspace.

    No end-to-end atomicity guarantee, though: the router calls
    `schedule_workspace_data_expiry` right afterwards, and it commits
    internally. That is why the router marks Workspace.deleted_at BEFORE this
    function — see test_delete_marks_workspace_before_the_committing_helper.
    """
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([(str(uuid4()), None)]),
        _update_result(),
        _update_result(0),
    ])

    with patch(
        "app.services.workflow_service._cleanup_change_detector_keys",
        new=AsyncMock(return_value=0),
    ):
        await soft_delete_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    db.commit.assert_not_awaited()


async def test_delete_marks_workspace_before_the_committing_helper(client, mock_current_user):
    """The order in the router is what guarantees atomicity — not the absence of a commit.

    `schedule_workspace_data_expiry` commits internally (via
    purge_workspace_storage). If the router marked Workspace.deleted_at after
    it, that commit would confirm the already soft-deleted workflows with the
    workspace still alive. That state does not show up in the trash (the filter
    is `deleted_at IS NOT NULL`), so neither the owner nor the admin can undo it
    through the UI.
    """
    from app.api.dependencies import get_db
    from app.main import app

    ws = MagicMock()
    ws.id_hash = "ws-test-001"
    ws.is_default = False
    ws.owner_id = mock_current_user.id_hash
    ws.deleted_at = None

    db = MagicMock()
    db.commit = AsyncMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = ws
    db.execute = AsyncMock(return_value=select_result)

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db

    visto: dict = {}

    async def _fake_cascade(_db, _ws_id, when):
        visto["ws_deleted_at_no_cascade"] = ws.deleted_at
        return {"workflows": 1, "schedules": 1}

    async def _fake_expiry(_db, _ws_id):
        # Internal commit point: whatever is dirty here gets committed along with it.
        visto["ws_deleted_at_no_commit_interno"] = ws.deleted_at
        return {"artifacts": 0, "drive_files": 0}

    try:
        with patch(
            "app.services.workflow_service.soft_delete_workspace_workflows", new=_fake_cascade,
        ), patch(
            "app.services.storage_purge_service.schedule_workspace_data_expiry", new=_fake_expiry,
        ):
            resp = await client.delete("/workspaces/ws-test-001")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 204
    assert visto["ws_deleted_at_no_cascade"] is not None
    assert visto["ws_deleted_at_no_commit_interno"] is not None


# ── Restore ───────────────────────────────────────────────────────────────────

async def test_restore_returns_only_workflows_from_the_same_delete():
    """A workflow deleted individually earlier does not come back with the workspace."""
    ws_id = str(uuid4())
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(2))

    restored = await restore_workspace_workflows(db, ws_id, _DELETED_AT)

    assert restored == 2
    stmt = db.execute.await_args.args[0]
    assert stmt.table.name == "workflows"

    params = stmt.compile().params
    assert params["deleted_at"] is None
    # O WHERE casa workspace + o timestamp exato do delete em cascata
    assert _DELETED_AT in params.values()
    assert ws_id in params.values()

    db.commit.assert_not_awaited()


async def test_restore_does_not_reactivate_workflow():
    """Regression: bulk reactivation resurrected what the owner had turned off.

    The cascade clears `flag_ative` on all of them, so on restore there is no
    way to know which ones were already deactivated on purpose. Returning them
    deactivated is the only honest reading — and `flag_ative` remains the lock
    that portal_router, webhook_router and schedule_service check.
    """
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(1))

    await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    params = db.execute.await_args.args[0].compile().params
    assert "flag_ative" not in params


async def test_restore_does_not_reactivate_schedules():
    """Religar cron sozinho e o lado perigoso — restore mexe so em workflows."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_update_result(1))

    await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    # Counting calls is no proof here: the restore also READS the names coming
    # back, to steer clear of names re-taken while the workspace was in the
    # trash (the name index is partial on `deleted_at IS NULL`). Reading is not
    # reactivating — what must not happen is a write to `schedules`.
    issued = [str(c.args[0]) for c in db.execute.await_args_list]
    assert not any("schedules" in sql for sql in issued), issued
    assert db.execute.await_args.args[0].table.name == "workflows"


async def test_restore_avoids_a_reoccupied_name():
    """The name of something in the trash may have been taken in the meantime.

    The name index is PARTIAL (`deleted_at IS NULL`), so soft-deleting frees
    the name. If someone creates a workflow with the name of one of those that
    went down, the restore's bulk UPDATE would fail ENTIRELY on a uniqueness
    violation and take the workspace restore down with it. Renaming the ones
    coming back returns the workspace; refusing would return nothing.
    """
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([("wf-a", "Edificações")]),   # the ones coming back
        _rows_result([("Edificações",)]),          # names already taken by live ones
        _update_result(1),                         # rename UPDATE
        _update_result(1),                         # UPDATE that clears deleted_at
    ])

    devolvidos = await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert devolvidos == 1
    rename = db.execute.await_args_list[2].args[0]
    assert rename.compile().params["name"] == "Edificações (2)"


async def test_restore_keeps_the_name_when_nobody_took_it():
    """Normal case: no collision, the workflow comes back with the name it had."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _rows_result([("wf-a", "Edificações")]),   # the ones coming back
        _rows_result([]),                          # nada ocupado
        _update_result(1),                         # UPDATE that clears deleted_at
    ])

    devolvidos = await restore_workspace_workflows(db, str(uuid4()), _DELETED_AT)

    assert devolvidos == 1
    # No rename: the only write is the one that clears `deleted_at`.
    assert db.execute.await_count == 3
    assert "name" not in db.execute.await_args.args[0].compile().params
