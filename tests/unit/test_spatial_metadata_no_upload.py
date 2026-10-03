# tests/unit/test_spatial_metadata_no_upload.py
"""
Propagation of `spatial_metadata` in GeoSync's `upload` mode.

CRS, bbox and feature count can only be computed by whoever HAS the file — the
executor. `DriveUploader.register` (catalog mode) already sent them. `DriveUploader.upload`
(the DEFAULT mode) accepted the parameter in its signature, the manager passed it,
and it was discarded: it did not reach `_upload_file`, and the confirm went out with
no body at all.

Result: every dataset synced through the normal path showed up in the Drive with no
spatial data. There was no error, no log, no obviously empty field — the column
simply stayed null, and the only way to notice was to compare a file synced in
catalog mode with one synced in upload mode.

The audit classified the parameter as "dead". It was right about the fact and
wrong about the action: the fix is to PROPAGATE, not to remove.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

META = {"crs": "EPSG:4326", "bbox": [0, 0, 1, 1], "feature_count": 7}


def _generous_ceiling():
    """The confirm checks the size ceiling before accepting the object.

    The `db` double in these tests answers ANY query with the same
    WorkspaceFile, so the settings query needs its own answer. A generous
    ceiling on purpose: size is not the subject here — that is in
    `test_drive_teto_no_confirm.py`.
    """
    from unittest.mock import AsyncMock, patch

    from app.models.platform_file_settings import PlatformFileSettings
    from app.services.drive_service import DriveService

    return patch.object(
        DriveService, "get_settings",
        new=AsyncMock(return_value=PlatformFileSettings(id=1, max_size_mb=200)),
    )


# ── The propagation chain ────────────────────────────────────────────────────

@pytest.mark.parametrize("funcao", ["upload", "_upload_file", "_upload_shapefile"])
def test_each_link_of_the_chain_uses_the_parameter(funcao):
    """Um elo que aceita e ignora e exatamente o bug original."""
    from executor.sync.uploader import DriveUploader

    arvore = ast.parse(inspect.getsource(getattr(DriveUploader, funcao)).lstrip())
    alvo = next(
        n for n in ast.walk(arvore)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == funcao
    )
    assert "spatial_metadata" in [a.arg for a in alvo.args.args], (
        f"{funcao} deixou de aceitar spatial_metadata"
    )
    usado = any(
        isinstance(n, ast.Name) and n.id == "spatial_metadata" and isinstance(n.ctx, ast.Load)
        for n in ast.walk(alvo)
    )
    assert usado, f"{funcao} aceita spatial_metadata e NAO usa — o dado morre aqui"


def test_the_confirm_sends_the_metadata_in_the_body():
    from executor.sync.uploader import DriveUploader

    fonte = inspect.getsource(DriveUploader._upload_file)
    assert "executor-confirm-upload" in fonte
    assert "spatial_metadata" in fonte.split("executor-confirm-upload", 1)[1][:400], (
        "o POST de confirm voltou a ir sem o metadado"
    )


# ── O servidor persiste ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_upload_writes_the_received_metadata():
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.services.drive_service import DriveService

    wf = MagicMock(id_hash="f-1", workspace_id="ws-1", s3_key="k", content_md5=None,
                   original_name="a.gpkg", extension="gpkg", size=1, spatial_metadata=None)
    db = MagicMock()
    res = MagicMock(); res.scalar_one_or_none.return_value = wf
    db.execute = AsyncMock(return_value=res); db.commit = AsyncMock()

    svc = DriveService(db)
    with patch("app.core.storage.head_async", new=AsyncMock(return_value={"size": 10, "etag": "e"})), \
            _generous_ceiling(), \
            patch("app.services.drive_service.emit_drive_event", new=AsyncMock()):
        await svc.confirm_upload("f-1", spatial_metadata=META)

    assert wf.spatial_metadata == META


@pytest.mark.asyncio
async def test_confirm_without_metadata_does_not_erase_what_existed():
    """An old executor confirms with no body — it must not wipe what was already stored."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.services.drive_service import DriveService

    wf = MagicMock(id_hash="f-1", workspace_id="ws-1", s3_key="k", content_md5=None,
                   original_name="a.gpkg", extension="gpkg", size=1, spatial_metadata=META)
    db = MagicMock()
    res = MagicMock(); res.scalar_one_or_none.return_value = wf
    db.execute = AsyncMock(return_value=res); db.commit = AsyncMock()

    svc = DriveService(db)
    with patch("app.core.storage.head_async", new=AsyncMock(return_value={"size": 10, "etag": "e"})), \
            _generous_ceiling(), \
            patch("app.services.drive_service.emit_drive_event", new=AsyncMock()):
        await svc.confirm_upload("f-1")

    assert wf.spatial_metadata == META


# ── Compatibility with old executors ─────────────────────────────────────────

def test_the_endpoint_tolerates_confirm_without_body():
    """An upload already stored in MinIO must not stay 'pending' because of the JSON.

    Executors prior to this version confirm with no body at all; an unguarded
    `await request.json()` would raise and the file would be stuck.
    """
    fonte = inspect.getsource(
        __import__("app.api.routers.executor_drive_router", fromlist=["x"]).agent_confirm_upload
    )
    assert "try:" in fonte and "request.json()" in fonte, (
        "a leitura do corpo precisa continuar tolerante a ausencia"
    )
    body_after_json = fonte.split("request.json()", 1)[1]
    assert "except" in body_after_json, "sem except, executor antigo quebra o confirm"
