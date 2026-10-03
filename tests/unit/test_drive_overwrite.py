"""Overwriting a Drive file from the executor.

`create_agent_upload_url(overwrite=True)` reuses the existing row instead of
creating another one. Keeping the same id_hash and the same s3_key is the point:
a DataInput pointing to the file stays valid and starts reading the new version,
and the previous object is not left orphaned in MinIO.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.platform_file_settings import PlatformFileSettings
from app.services.drive_service import DriveService


def _existente(**kwargs) -> MagicMock:
    base = {
        "id_hash": "file-existente",
        "s3_key": "artifacts/ws-1/task-ANTIGA/resultado.geojson",
        "original_name": "resultado.geojson",
        "status": "confirmed",
        "content_md5": "md5-antigo",
    }
    base.update(kwargs)
    return MagicMock(**base)


def _svc(encontrado=None) -> DriveService:
    db = MagicMock(commit=AsyncMock(), refresh=AsyncMock(), add=MagicMock())
    result = MagicMock()
    result.scalar_one_or_none.return_value = encontrado
    db.execute = AsyncMock(return_value=result)
    return DriveService(db)


@pytest.fixture(autouse=True)
def _teto():
    """The confirm checks the size ceiling before accepting the object.

    The `db` double here answers ANY query with the same WorkspaceFile, so the
    settings query needs its own answer. A deliberately generous ceiling: size
    is not the subject of this file — it is in
    `test_drive_teto_no_confirm.py`.
    """
    with patch.object(
        DriveService, "get_settings",
        new=AsyncMock(return_value=PlatformFileSettings(id=1, max_size_mb=200)),
    ):
        yield


@pytest.fixture(autouse=True)
def _presign():
    with patch(
        "app.services.drive_service.s3.presigned_put_async",
        new=AsyncMock(return_value="https://minio/put"),
    ):
        yield


async def test_overwrite_reaproveita_linha_e_s3_key():
    alvo = _existente()
    svc = _svc(encontrado=alvo)

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=True,
    )

    # No new row.
    svc.db.add.assert_not_called()
    # A s3_key ANTIGA prevalece: o PUT sobrescreve o objeto no lugar.
    assert out["s3_key"] == "artifacts/ws-1/task-ANTIGA/resultado.geojson"
    assert out["id_hash"] == "file-existente"


async def test_overwrite_nao_marca_pending_nem_altera_size():
    """Data-loss regression.

    Marking the row as pending made it eligible for
    cleanup_pending_workspace_files, which deletes pending rows with created_at
    older than the 24h TTL — and here created_at is the original creation time,
    already expired for any file being overwritten. A failed upload would
    destroy the intact file. The size also stays untouched: it is updated by
    confirm_upload, from the actual object in MinIO.
    """
    alvo = _existente(status="confirmed", size=1234)
    svc = _svc(encontrado=alvo)

    await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=99,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=True,
    )

    assert alvo.status == "confirmed"
    assert alvo.size == 1234


async def test_sem_overwrite_cria_outra_linha():
    """Default behavior preserved — it is what produces the per-run copies."""
    svc = _svc(encontrado=_existente())

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=False,
    )

    svc.db.add.assert_called_once()
    assert out["s3_key"] == "artifacts/ws-1/task-NOVA/resultado.geojson"


async def test_overwrite_sem_arquivo_anterior_cria_normalmente():
    svc = _svc(encontrado=None)

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="novo.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/novo.geojson",
        overwrite=True,
    )

    svc.db.add.assert_called_once()
    assert out["s3_key"] == "artifacts/ws-1/task-NOVA/novo.geojson"


# ── The return value says what happened, not what was requested ──────────────


async def test_retorno_marca_reuso():
    """Without this the executor could only repeat the intent ("I asked to overwrite"),
    and an overwrite that did not find the file was indistinguishable from one that did."""
    svc = _svc(encontrado=_existente())

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=True,
    )

    assert out["reused"] is True


async def test_retorno_nao_marca_reuso_quando_nao_havia_arquivo():
    svc = _svc(encontrado=None)

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="novo.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/novo.geojson",
        overwrite=True,
    )

    assert out["reused"] is False


async def test_retorno_nao_marca_reuso_sem_overwrite():
    """There is a file with the same name, but the option is off — creates another row."""
    svc = _svc(encontrado=_existente())

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=False,
    )

    assert out["reused"] is False


# ── confirm_upload distinguishes creation from update ────────────────────────

async def _confirm(content_md5):
    wf = _existente(content_md5=content_md5, workspace_id="ws-1", extension="geojson", size=1)
    db = MagicMock(commit=AsyncMock())
    result = MagicMock()
    result.scalar_one_or_none.return_value = wf
    db.execute = AsyncMock(return_value=result)
    svc = DriveService(db)

    emitidos = []
    with patch(
        "app.services.drive_service.s3.head_async",
        new=AsyncMock(return_value={"size": 99, "etag": "md5-novo"}),
    ), patch(
        "app.services.drive_service.emit_drive_event",
        new=AsyncMock(side_effect=lambda ws, acao, info, **kw: emitidos.append(acao)),
    ):
        await svc.confirm_upload("file-existente")
    return emitidos


async def test_confirm_marca_a_escrita_de_conteudo():
    """Regression: without a dedicated column, the listing depended on `updated_at`.

    On an overwrite with IDENTICAL content no field changes value in the
    confirm — SQLAlchemy emits no UPDATE, onupdate does not fire, and the
    freshly written file did not move up in the listing. The workflow ran and
    the Drive gave no sign at all.
    """
    wf = _existente(content_md5="md5-antigo", workspace_id="ws-1",
                    extension="geojson", size=1, content_written_at=None)
    db = MagicMock(commit=AsyncMock())
    result = MagicMock()
    result.scalar_one_or_none.return_value = wf
    db.execute = AsyncMock(return_value=result)

    with patch("app.services.drive_service.s3.head_async",
               new=AsyncMock(return_value={"size": 1, "etag": "md5-antigo"})), \
         patch("app.services.drive_service.emit_drive_event", new=AsyncMock()):
        await DriveService(db).confirm_upload("file-existente")

    # Even with size and md5 unchanged, the write date moves forward.
    assert wf.content_written_at is not None


async def test_confirm_de_sobrescrita_emite_file_updated():
    """Pre-existing content_md5 = reused row. GeoSync handles both,
    but the event has to tell the truth about what happened."""
    assert await _confirm("md5-antigo") == ["file_updated"]


async def test_confirm_de_upload_novo_emite_file_created():
    assert await _confirm(None) == ["file_created"]


# ── Ordering by last write ───────────────────────────────────────────────────

async def test_listagem_ordena_pela_ultima_escrita():
    """Overwriting keeps the original created_at.

    Ordering by it would push freshly written content to the end of the list,
    alongside the oldest files — exactly the opposite of what the user expects
    when re-running a workflow.
    """
    db = MagicMock()
    capturadas: list = []

    async def _execute(stmt):
        capturadas.append(stmt)
        result = MagicMock()
        result.scalar.return_value = 0
        result.scalars.return_value.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=_execute)

    await DriveService(db).list_files(workspace_id="ws-1")

    sql = str(capturadas[-1].compile(compile_kwargs={"literal_binds": True})).lower()
    assert "order by" in sql
    assert "coalesce" in sql.split("order by", 1)[1]
