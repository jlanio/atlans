# tests/unit/test_drive_executor_delete.py
"""DELETE /drive/executor-file/{id} — the mTLS route GeoSync uses to delete a
Drive file when it leaves the synced folder.

Regression these routes lock down: the executor sent `DELETE /drive/{id}` (a
user route, requires JWT), and on the `agents.atlans.example.org` host Traefik only
routes `/drive/executor-*` to the API — the request died with a 404 in Traefik
itself and the WorkspaceFile stayed listed in the UI forever, even after F5.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import InvalidFileOperationError


URL = "/drive/executor-file/file-1"


# ── Endpoint (via app) ────────────────────────────────────────────────────────

@contextmanager
def _bypass(svc, *, ws_ids=("ws-1",), executor_id="ag-1"):
    """Simulates a successful mTLS auth and injects a mocked DriveService.

    Mirrors the pattern of test_change_detector_router: the real router
    authenticates the executor via `_auth_agent` (mTLS cert) — here it is enough
    to return a fake executor with the resolved workspaces, and override the
    service dependency.
    """
    from app.main import app
    from app.api.dependencies import get_db
    from app.api.routers.drive_router import get_drive_service

    async def _fake_db():
        yield AsyncMock()

    fake_agent = MagicMock()
    fake_agent.id_hash = executor_id
    fake_agent._resolved_ws_ids = list(ws_ids)

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_drive_service] = lambda: svc
    auth = patch(
        "app.api.routers.executor_drive_router._auth_agent",
        new_callable=AsyncMock, return_value=fake_agent,
    )
    auth.start()
    try:
        yield fake_agent
    finally:
        auth.stop()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_drive_service, None)


def _svc(wf=None, *, missing=False):
    svc = MagicMock()
    svc.get_file = (
        AsyncMock(side_effect=FileNotFoundError("nao existe"))
        if missing else AsyncMock(return_value=wf)
    )
    svc.delete_agent_file = AsyncMock()
    return svc


def _wf(ws="ws-1"):
    wf = MagicMock()
    wf.workspace_id = ws
    wf.id_hash = "file-1"
    return wf


@pytest.mark.asyncio
async def test_delete_remove_e_devolve_204(client):
    wf = _wf("ws-1")
    svc = _svc(wf)
    with _bypass(svc):
        resp = await client.delete(URL)
    assert resp.status_code == 204
    # Delegated to the service with the wf and the AUTHENTICATED executor's id (not
    # a value the client picks) — the per-workspace authorization already passed.
    svc.delete_agent_file.assert_awaited_once()
    args = svc.delete_agent_file.call_args.args
    assert args[0] is wf and args[1] == "ag-1"


@pytest.mark.asyncio
async def test_delete_inexistente_e_idempotente_204(client):
    """Missing record = already in the desired state. 204, without touching the service."""
    svc = _svc(missing=True)
    with _bypass(svc):
        resp = await client.delete(URL)
    assert resp.status_code == 204
    svc.delete_agent_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_de_outro_workspace_da_403(client):
    """A file outside the executor's workspaces: 403, and nothing is deleted."""
    svc = _svc(_wf("ws-OUTRO"))
    with _bypass(svc, ws_ids=("ws-1",)):
        resp = await client.delete(URL)
    assert resp.status_code == 403
    svc.delete_agent_file.assert_not_awaited()


# ── Service (direto) ──────────────────────────────────────────────────────────

def _service():
    from app.services.drive_service import DriveService
    db = AsyncMock()
    return DriveService(db), db


@pytest.mark.asyncio
async def test_service_minio_apaga_s3_primeiro_e_emite():
    svc, db = _service()
    wf = MagicMock(content_location="minio", s3_key="drive/ws-1/f_1", content_executor_id=None,
                   workspace_id="ws-1", id_hash="f1", original_name="a.geojson", extension="geojson", size=10)
    with patch("app.services.drive_service.s3.delete_strict_async", new_callable=AsyncMock) as s3del, \
         patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock) as emit:
        await svc.delete_agent_file(wf, "ag-1")
    s3del.assert_awaited_once()
    db.delete.assert_awaited_once_with(wf)
    db.commit.assert_awaited_once()
    # excludes the executor itself from the fan-out (it already removed it locally)
    assert emit.await_args.kwargs.get("exclude_agent_id") == "ag-1"


@pytest.mark.asyncio
async def test_service_catalogo_do_proprio_executor_apaga_sem_s3():
    """Catalog entry (content_location='executor', s3_key=None): no object in MinIO,
    only the record. It is the case that `delete_file` (web) refuses and that this
    path exists to serve — the owning executor itself reporting the file left."""
    svc, db = _service()
    wf = MagicMock(content_location="executor", s3_key=None, content_executor_id="ag-1",
                   workspace_id="ws-1", id_hash="f2", original_name="b.tif", extension="tif", size=5)
    with patch("app.services.drive_service.s3.delete_strict_async", new_callable=AsyncMock) as s3del, \
         patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock):
        await svc.delete_agent_file(wf, "ag-1")
    s3del.assert_not_awaited()
    db.delete.assert_awaited_once_with(wf)


@pytest.mark.asyncio
async def test_service_catalogo_de_outro_executor_e_negado():
    """An executor does not delete the record of content that lives in ANOTHER one."""
    svc, db = _service()
    wf = MagicMock(content_location="executor", s3_key=None, content_executor_id="ag-OUTRO",
                   workspace_id="ws-1", id_hash="f3", original_name="c.tif", extension="tif", size=5)
    with patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock) as emit:
        with pytest.raises(InvalidFileOperationError):
            await svc.delete_agent_file(wf, "ag-1")
    db.delete.assert_not_awaited()
    emit.assert_not_awaited()


# ── Batch delete (web) also emits file_deleted ───────────────────────────────
# Without this, the batch deletion vanished from the Drive but the executor in
# download/bidirectional did not remove the local copy — `delete_file` for a
# single file notified, the batch did not.

def _batch_service(files, *, owned=("ws-1",), roles=()):
    from app.services.drive_service import DriveService
    db = AsyncMock()
    files_res = MagicMock()
    files_res.scalars.return_value.all.return_value = files
    owner_res = MagicMock()
    owner_res.all.return_value = [(w,) for w in owned]
    member_res = MagicMock()
    member_res.all.return_value = [(w, r) for w, r in roles]
    # The three batch_delete_files queries, in order: files, owners, members.
    db.execute = AsyncMock(side_effect=[files_res, owner_res, member_res])
    return DriveService(db), db


def _bwf(id_hash, ws="ws-1", *, location="minio", s3_key="drive/ws-1/x"):
    wf = MagicMock()
    wf.id_hash = id_hash
    wf.workspace_id = ws
    wf.content_location = location
    wf.s3_key = None if location == "executor" else s3_key
    wf.original_name = f"{id_hash}.geojson"
    wf.extension = "geojson"
    wf.size = 1
    return wf


@pytest.mark.asyncio
async def test_batch_delete_emite_um_evento_por_arquivo():
    svc, _ = _batch_service([_bwf("a1", s3_key="drive/ws-1/a1"),
                             _bwf("a2", s3_key="drive/ws-1/a2")], owned=("ws-1",))
    with patch("app.services.drive_service.s3.delete_strict_async", new_callable=AsyncMock), \
         patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock) as emit:
        deleted, skipped_local = await svc.batch_delete_files(["a1", "a2"], ["ws-1"], "user-1")
    assert deleted == 2 and skipped_local == 0
    assert emit.await_count == 2
    ids = {c.args[2]["id_hash"] for c in emit.await_args_list}
    acoes = {c.args[1] for c in emit.await_args_list}
    assert ids == {"a1", "a2"} and acoes == {"file_deleted"}


@pytest.mark.asyncio
async def test_batch_delete_nao_emite_para_catalogado():
    """A cataloged one is skipped (bytes live on the executor) — and with no event."""
    svc, _ = _batch_service([_bwf("a1", s3_key="drive/ws-1/a1"),
                             _bwf("cat", location="executor")], owned=("ws-1",))
    with patch("app.services.drive_service.s3.delete_strict_async", new_callable=AsyncMock), \
         patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock) as emit:
        deleted, skipped_local = await svc.batch_delete_files(["a1", "cat"], ["ws-1"], "user-1")
    assert deleted == 1 and skipped_local == 1
    assert emit.await_count == 1
    assert emit.await_args.args[2]["id_hash"] == "a1"


@pytest.mark.asyncio
async def test_batch_delete_falha_de_s3_nao_emite_esse_arquivo():
    """S3 failed → file skipped (reconcile retries later) → no event for it; an
    event would be a lie, the object is still in MinIO."""
    svc, _ = _batch_service([_bwf("ok", s3_key="drive/ws-1/ok"),
                             _bwf("ruim", s3_key="drive/ws-1/ruim")], owned=("ws-1",))

    async def _s3(key, allow_missing=True):
        if key == "drive/ws-1/ruim":
            raise RuntimeError("s3 fora do ar")

    with patch("app.services.drive_service.s3.delete_strict_async", side_effect=_s3), \
         patch("app.services.drive_service.emit_drive_event", new_callable=AsyncMock) as emit:
        deleted, _skip = await svc.batch_delete_files(["ok", "ruim"], ["ws-1"], "user-1")
    assert deleted == 1
    assert emit.await_count == 1
    assert emit.await_args.args[2]["id_hash"] == "ok"
