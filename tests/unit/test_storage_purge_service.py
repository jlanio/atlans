"""
Tests for app.services.storage_purge_service.

Destructive code: removes objects from MinIO and rows from the database. The most
important invariant is the same as in artifact_cleanup.purge_expired_artifacts — if
S3 fails for a reason other than "not found", the database row MUST survive,
otherwise the object becomes an invisible orphan (takes up disk and nobody knows it exists anymore).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _db_with(artifacts=(), files=(), workflows=(), scope="all"):  # noqa: ARG001 — scope kept for clarity in the tests
    """Fake session that dispatches by SQL, not by the order of the calls.

    The sequence of `execute` calls varies with the scope and the content (the
    portal_layer DELETE only happens for a published artifact), so a positional
    `side_effect` returns the wrong result as soon as the path changes — that is
    what made the first version of these tests fail without any bug in the code.
    """
    db = MagicMock()
    art_res = MagicMock()
    art_res.scalars.return_value.all.return_value = list(artifacts)
    file_res = MagicMock()
    file_res.scalars.return_value.all.return_value = list(files)
    wf_res = MagicMock()
    wf_res.scalars.return_value = list(workflows)

    async def _execute(stmt, *a, **kw):
        sql = str(stmt).lower()
        if sql.lstrip().startswith("select"):
            if "workspace_files" in sql:
                return file_res
            if "from workflows" in sql:
                return wf_res
            if "artifacts" in sql:
                return art_res
        return MagicMock()

    db.execute = AsyncMock(side_effect=_execute)
    db.commit = AsyncMock()
    return db


def _artifact(**kw):
    base = dict(id=1, s3_key="artifacts/ws-1/run/a.geojson", size_bytes=100,
                is_published=False, workflow_hash=None, output_key="out")
    base.update(kw)
    return MagicMock(**base)


def _file(**kw):
    base = dict(id=1, s3_key="drive/ws-1/x.csv", size=50)
    base.update(kw)
    return MagicMock(**base)


# ── Caminho feliz ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_purges_artifacts_and_drive_summing_bytes(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact(size_bytes=100), _artifact(id=2, size_bytes=250)],
                 files=[_file(size=50)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="all")

    assert r["artifacts"] == 2 and r["artifact_bytes"] == 350
    assert r["drive_files"] == 1 and r["drive_bytes"] == 50
    assert r["skipped_s3_errors"] == 0
    assert mock_del.call_count == 3
    db.commit.assert_awaited()


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_purge_clears_workflow_pin_refs(mock_del):
    """The pin-cache objects go along with the other artifacts; the ref in the
    workflow must be CLEARED with them — left dangling, it was a permanent 404 on
    every run (the auto-pin only fires with an empty ref). pin_metadata stays: the
    pin intent survives and the next run rewrites the cache."""
    from app.services import storage_purge_service as mod

    wf = MagicMock()
    wf.pinned_outputs = {
        "n1": {"__pin_s3_key__": "pin-cache/ws-1/t1/n1_pin.parquet",
               "__pin_format__": "parquet"},
        "n2": {},          # pin awaiting rewrite — already as it should be
    }
    wf_without_pins = MagicMock()
    wf_without_pins.pinned_outputs = None
    pin_art = _artifact(id=7, s3_key="pin-cache/ws-1/t1/n1_pin.parquet")
    db = _db_with(artifacts=[pin_art], workflows=[wf, wf_without_pins])

    with patch("sqlalchemy.orm.attributes.flag_modified") as mock_flag:
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["pins_resetados"] == 1
    assert wf.pinned_outputs == {"n1": {}, "n2": {}}
    assert wf_without_pins.pinned_outputs is None
    mock_flag.assert_called_once_with(wf, "pinned_outputs")
    mock_del.assert_called()          # the pin object left MinIO


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_scope_drive_does_not_touch_artifacts(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact()], files=[_file()], scope="drive")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["artifacts"] == 0
    assert r["drive_files"] == 1
    mock_del.assert_called_once_with("drive/ws-1/x.csv", allow_missing=True)


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_scope_artifacts_does_not_touch_drive(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact()], files=[_file()], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    assert r["drive_files"] == 0


# ── Safety invariants ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.core.storage.delete_strict", side_effect=Exception("MinIO down"))
async def test_s3_failure_preserves_the_row_in_the_db(mock_del):
    """Never delete from the database before confirming removal from storage."""
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact()], files=[], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0, "artefato nao pode contar como removido"
    assert r["skipped_s3_errors"] == 1


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_executor_local_s3_key_does_not_go_to_minio(mock_del):
    """Local fallback (s3_key starting with '/') does not exist in MinIO."""
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact(s3_key="/data/artifacts/ws/run/a.json")], files=[], scope="artifacts")
    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    mock_del.assert_not_called()
    assert r["artifacts"] == 1, "a linha orfa ainda deve sair do banco"


@pytest.mark.asyncio
async def test_invalid_scope_is_rejected():
    from app.services import storage_purge_service as mod

    with pytest.raises(ValueError):
        await mod.purge_workspace_storage(MagicMock(), "ws-1", scope="tudo")


@pytest.mark.asyncio
@patch("app.core.storage.delete_strict")
async def test_published_artifact_removes_the_portal_layer(mock_del):
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artifact(is_published=True, workflow_hash="wf-1")], files=[], scope="artifacts")
    await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    # SELECT artifacts, DELETE portal_layer, DELETE artifacts
    assert db.execute.await_count >= 3


# ── Authorization of the endpoints (/admin/storage/.../purge) ────────────────
#
# The purge deletes data from ANY workspace on the platform, including other
# users'. The guarantee comes from the router (`dependencies=[Depends(require_admin)]`),
# not from code in the handler — and that is why it is fragile: it only takes
# someone moving the endpoint to another router, or creating a new router without
# the dependency, to open everything up. These tests fail the instant that happens.

@pytest.mark.asyncio
async def test_purge_denied_for_regular_user(client):
    """client authenticates with role='user' (see conftest)."""
    resp = await client.post(
        "/admin/storage/workspaces/ws-test-001/purge",
        json={"scope": "all", "confirm": "ws-test-001"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_purge_allowed_for_admin(client, mock_current_user):
    from app.api.dependencies import get_db
    from app.main import app

    mock_current_user.role = "admin"
    mock_current_user.username = "admin-test"

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with patch(
            "app.services.storage_purge_service.purge_workspace_storage",
            new=AsyncMock(return_value={
                "workspace_id": "ws-test-001", "scope": "all",
                "artifacts": 2, "artifact_bytes": 10,
                "drive_files": 1, "drive_bytes": 5, "skipped_s3_errors": 0,
            }),
        ):
            resp = await client.post(
                "/admin/storage/workspaces/ws-test-001/purge",
                json={"scope": "all", "confirm": "ws-test-001"},
            )
        assert resp.status_code == 200
        assert resp.json()["artifacts"] == 2
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_admin_with_mismatched_confirm_gets_400(client, mock_current_user):
    """Guard against clicking the wrong row: the body has to repeat the workspace_id."""
    from app.api.dependencies import get_db
    from app.main import app

    mock_current_user.role = "admin"
    mock_current_user.username = "admin-test"

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    try:
        with patch(
            "app.services.storage_purge_service.purge_workspace_storage",
            new=AsyncMock(),
        ) as purge_mock:
            resp = await client.post(
                "/admin/storage/workspaces/ws-alvo/purge",
                json={"scope": "all", "confirm": "ws-vizinho"},
            )
        assert resp.status_code == 400
        purge_mock.assert_not_awaited()
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Content that lives on the executor's disk ─────────────────────────────────
#
# The purge did not know about `content_location`. A local artifact has a NULL
# `s3_key`: the MinIO `if` was not entered, the `continue` did not fire, and the
# row was deleted WITHOUT ordering the removal — a retained, invisible file on the
# user's disk, which is the worst possible outcome for personal data. These tests
# lock both policies, which are deliberately DIFFERENT between artifact and Drive.


def _artefato_local(**kw):
    base = dict(id=10, id_hash="art-local", s3_key=None, size_bytes=700,
                is_published=False, workflow_hash=None, output_key="out",
                content_location="executor", executor_id="exec-1",
                local_path="ws-1/run/a.geojson")
    base.update(kw)
    return MagicMock(**base)


@pytest.mark.asyncio
async def test_local_artifact_is_deleted_only_after_the_order_is_delivered():
    """Executor ONLINE: order delivered, so the row can go."""
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artefato_local()])

    async def _deliver_all(by_executor):
        return [i["_id"] for itens in by_executor.values() for i in itens]

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_deliver_all):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    assert r["artifact_bytes"] == 700
    assert r["pending_executor"] == 0


@pytest.mark.asyncio
async def test_OFFLINE_executor_keeps_the_row_instead_of_deleting():
    """The central regression: without delivery, the row STAYS and the next pass tries again."""
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artefato_local()])

    async def _deliver_nothing(_by_executor):
        return []

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_deliver_nothing):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0, "linha nao pode ser contada como removida"
    assert r["pending_executor"] == 1

    # And, above all, no artifacts DELETE may have been issued.
    deletes = [
        str(c.args[0]).lower() for c in db.execute.await_args_list
        if str(c.args[0]).lower().lstrip().startswith("delete")
        and "artifacts" in str(c.args[0]).lower()
    ]
    assert deletes == [], f"DELETE emitido sem ordem entregue: {deletes}"


@pytest.mark.asyncio
async def test_local_artifact_without_trace_is_preserved():
    """Without executor_id/local_path there is no one to send it to — keep the record."""
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artefato_local(executor_id=None)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 0
    assert r["skipped_sem_rastro"] == 1


@pytest.mark.asyncio
async def test_published_local_artifact_removes_the_portal_layer_too():
    from app.services import storage_purge_service as mod

    db = _db_with(artifacts=[_artefato_local(is_published=True, workflow_hash="wf-1")])

    async def _deliver_all(by_executor):
        return [i["_id"] for itens in by_executor.values() for i in itens]

    with patch("app.core.artifact_cleanup._ordenar_remocao_local", new=_deliver_all):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="artifacts")

    assert r["artifacts"] == 1
    sqls = [str(c.args[0]).lower() for c in db.execute.await_args_list]
    assert any(s.lstrip().startswith("delete") and "portal_layer" in s for s in sqls)


@pytest.mark.asyncio
async def test_cataloged_drive_is_PRESERVED_not_deleted():
    """Policy opposite to the artifact's, and deliberate.

    A cataloged file belongs to the user, in the folder they chose to sync; the
    platform never had the bytes and it takes up none of its storage.
    `drive_service._refuse_if_cataloged` refuses to delete it in a single
    deletion — the purge silently deleted the record, contradicting that policy.

    Sending `purge_artifacts` does not help either: the executor resolves the path
    under `artifacts_root()`, so the order would not find the Drive file and would
    still count as delivered.
    """
    from app.services import storage_purge_service as mod

    db = _db_with(files=[_file(content_location="executor", s3_key=None, size=0)])

    r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["drive_files"] == 0
    assert r["skipped_catalogados"] == 1
    deletes = [
        str(c.args[0]).lower() for c in db.execute.await_args_list
        if str(c.args[0]).lower().lstrip().startswith("delete")
    ]
    assert deletes == [], f"arquivo catalogado nao pode ser apagado: {deletes}"


@pytest.mark.asyncio
async def test_normal_drive_is_still_purged():
    """The guard above must not paralyze the purge of the Drive that lives in MinIO."""
    from app.services import storage_purge_service as mod

    db = _db_with(files=[_file(content_location="minio", size=50)])

    with patch("app.core.storage.delete_strict"):
        r = await mod.purge_workspace_storage(db, "ws-1", scope="drive")

    assert r["drive_files"] == 1 and r["drive_bytes"] == 50
    assert r["skipped_catalogados"] == 0
