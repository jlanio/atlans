# tests/unit/test_consumer_local_fallback.py
"""An artifact whose upload to MinIO FAILED (local_fallback) must not become a
record pointing to a nonexistent object — the download would answer 404
forever.

The fallback writes the bytes to the SAME place as a keepLocal
(artifacts_root()/{ws}/{task}/{arquivo}), so the server registers the artifact
as executor-local (content_location='executor', s3_key=None, local_path
derived): no broken link, served from where the bytes actually are. The executor
reports content_location='minio' on purpose (the destination was the cloud) — it
is the consumer that decides, based on the `local_fallback` flag.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.run_result_consumer import _register_artifacts
from app.models.artifact import Artifact

WS = "ws-1"
TASK = "task-1"
S3 = f"artifacts/{WS}/{TASK}/buffer.geojson"


def _run():
    return MagicMock(workspace_id=WS, task_id=TASK, workflow_hash="wf-1",
                     host="executor:ag-1")


def _db(conhecidos=(), s3_conhecidas=()):
    """Session double. `conhecidos` = (node_id, filename) pairs already in the
    database for the idempotency guard (`select(Artifact.node_id, Artifact.filename)`,
    read via `.all()`); `s3_conhecidas` = what the OLD guard (by s3_key) would read."""
    db = MagicMock(commit=AsyncMock(), add=MagicMock())

    async def _execute(stmt):
        res = MagicMock()
        res.all.return_value = list(conhecidos)
        res.scalars.return_value.all.return_value = list(s3_conhecidas)
        res.scalar_one_or_none.return_value = None
        return res

    db.execute = AsyncMock(side_effect=_execute)
    return db


def _artefatos(db):
    return [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], Artifact)]


@pytest.fixture(autouse=True)
def _sem_io():
    with patch("app.core.run_result_consumer._get_retention_days",
               new=AsyncMock(return_value=None)), \
         patch("app.core.run_result_consumer._head_sizes",
               new=AsyncMock(return_value={})):
        yield


def _meta(**extra):
    base = {
        "output_key": "buffer", "format": "geojson", "features": 3,
        "filename": "buffer.geojson", "context": "artifacts", "s3_key": S3,
    }
    base.update(extra)
    return {"node-1": [base]}


@pytest.mark.asyncio
async def test_fallback_vira_executor_local_sem_s3_key():
    db = _db()
    await _register_artifacts(db, _run(), _meta(
        content_location="minio", local_fallback=True, size_bytes=123,
    ))
    arts = _artefatos(db)
    assert len(arts) == 1
    a = arts[0]
    assert a.content_location == "executor"      # not 'minio' with a dead key
    assert a.s3_key is None                       # no link that 404s
    assert a.local_path == f"{WS}/{TASK}/buffer.geojson"  # derived on the server
    assert a.size_bytes == 123                    # size came from the executor's meta
    assert a.executor_id == "ag-1"


@pytest.mark.asyncio
async def test_upload_bem_sucedido_continua_minio():
    """Without `local_fallback`, the normal artifact keeps pointing to MinIO."""
    db = _db()
    await _register_artifacts(db, _run(), _meta(
        content_location="minio", local_fallback=False,
    ))
    arts = _artefatos(db)
    assert len(arts) == 1
    a = arts[0]
    assert a.content_location == "minio"
    assert a.s3_key == S3
    assert a.local_path is None


@pytest.mark.asyncio
async def test_fallback_no_drive_vira_catalogo_sem_download():
    """context='drive' that fell into the fallback: the object never reached MinIO,
    so a 'confirmed' WorkspaceFile with an s3_key would give a 404 download. It
    becomes a catalog entry (content_location='executor', no s3_key), without
    emitting file_created."""
    from app.models.workspace_file import WorkspaceFile

    db = _db()
    eventos = []

    async def _emit(workspace_id, action, file_info, **kw):
        eventos.append((action, file_info))

    with patch("app.core.drive_events.emit_drive_event", side_effect=_emit):
        await _register_artifacts(db, _run(), _meta(
            context="drive", content_location="minio", local_fallback=True, size_bytes=200,
        ))

    wfs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkspaceFile)]
    assert len(wfs) == 1
    wf = wfs[0]
    assert wf.content_location == "executor"
    assert wf.s3_key is None
    assert wf.content_executor_id == "ag-1"
    assert wf.size == 200
    assert wf.status == "confirmed"
    assert eventos == []  # nothing for another executor to download


@pytest.mark.asyncio
async def test_drive_bem_sucedido_continua_minio_e_emite():
    """Without a fallback, the normal Drive keeps its s3_key and notifies the executors."""
    from app.models.workspace_file import WorkspaceFile

    db = _db()
    eventos = []

    async def _emit(workspace_id, action, file_info, **kw):
        eventos.append((action, file_info))

    with patch("app.core.drive_events.emit_drive_event", side_effect=_emit):
        await _register_artifacts(db, _run(), _meta(context="drive"))

    wfs = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkspaceFile)]
    assert len(wfs) == 1
    assert wfs[0].s3_key == S3
    assert wfs[0].content_location != "executor"
    assert [a for a, _ in eventos] == ["file_created"]


@pytest.mark.asyncio
async def test_keeplocal_continua_executor_local():
    """The keepLocal path (content_location='executor') does not regress."""
    db = _db()
    await _register_artifacts(db, _run(), _meta(
        content_location="executor", s3_key=None, size_bytes=77,
    ))
    arts = _artefatos(db)
    assert len(arts) == 1
    a = arts[0]
    assert a.content_location == "executor"
    assert a.s3_key is None
    assert a.size_bytes == 77


@pytest.mark.asyncio
async def test_reentrega_de_artefato_local_nao_duplica():
    """Idempotency: reprocessing the payload (dead letter / replay) with the local
    row ALREADY in the database does NOT create a second one. The guard dedups by
    stable identity (node_id, filename) within the run, not by s3_key — which for
    a local artifact is None and never matched the derived key. Mutation: going
    back to dedup by the derived s3_key makes the 2nd delivery recreate the row
    (the known s3_key is None, it never matches)."""
    db = _db(conhecidos=[("node-1", "buffer.geojson")], s3_conhecidas=[None])
    await _register_artifacts(db, _run(), _meta(
        content_location="minio", local_fallback=True, size_bytes=123,
    ))
    assert _artefatos(db) == []
