"""A Drive upload rejection states the REASON by code, not just by text.

The web app classified the rejection (icon and label in /drive and in the Home
attachments) by searching for Portuguese snippets in `detail` — "extensão", "não
permitida", "vazio". The text here has no accents ("Extensao '.x' nao
permitida."), so the extension rejection fell into "other failure". And the
body's `error`, which is stable, was the same `file_validation_error` for a
forbidden extension, a dangerous inner extension and an empty file: there was no
way to tell them apart without reading the sentence.

Each case now has its own `error_code`. The HTTP status of each stays as before
(422 for the validations, 413 for the ceiling) — the executor, which only looks
at the status, does not notice the change. And all of them are still
`FileValidationError`: whoever catches the parent class (the MCP upload tool)
still catches them.

Real database (SQLite) because `validate_upload` reads the allowed extensions
and the ceiling from the database.
"""
import json
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import FileTooLargeError, FileValidationError
from app.core.utils.error_handlers import atlas_domain_error_handler
from app.models.platform_file_settings import AllowedFileExtension, PlatformFileSettings
from app.models.workspace_file import WorkspaceFile
from app.services.drive_service import DriveService

UM_MB = 1024 * 1024


@pytest_asyncio.fixture
async def servico():
    """1 MB ceiling and only `.csv`/`.geojson` allowed."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            WorkspaceFile.metadata.create_all,
            tables=[
                WorkspaceFile.__table__,
                PlatformFileSettings.__table__,
                AllowedFileExtension.__table__,
            ],
        )
    async with AsyncSession(eng, expire_on_commit=False) as db:
        db.add(PlatformFileSettings(id=1, max_size_mb=1))
        db.add(AllowedFileExtension(extension="csv"))
        db.add(AllowedFileExtension(extension="geojson"))
        await db.commit()
        yield DriveService(db)
    await eng.dispose()


async def _response_body(exc) -> tuple[int, dict]:
    """What the global handler returns to the client for this exception."""
    resp = await atlas_domain_error_handler(MagicMock(), exc)
    return resp.status_code, json.loads(resp.body)


@pytest.mark.parametrize(
    "nome, codigo",
    [
        ("relatorio.pdf", "extension_not_allowed"),
        # No extension is an extension outside the list: the same case for the reader.
        ("LEIAME", "extension_not_allowed"),
        ("notas.sh.csv", "dangerous_inner_extension"),
        ("instalador.exe.geojson", "dangerous_inner_extension"),
    ],
)
async def test_name_rejection_has_its_own_code_and_stays_422(servico, nome, codigo):
    with pytest.raises(FileValidationError) as exc:
        await servico.validate_upload(nome, 10)

    status, corpo = await _response_body(exc.value)
    assert corpo["error"] == codigo
    assert status == 422
    # The sentence stays the same — it is what the person reads in the panel.
    assert corpo["message"] == exc.value.detail


async def test_empty_file_has_its_own_code_and_stays_422(servico):
    with pytest.raises(FileValidationError) as exc:
        await servico.upload_file("ws-1", "dados.csv", b"", uploaded_by="u-1")

    status, corpo = await _response_body(exc.value)
    assert corpo == {"error": "empty_file", "message": "Arquivo vazio."}
    assert status == 422


async def test_file_above_the_ceiling_stays_413_file_too_large(servico):
    with pytest.raises(FileTooLargeError) as exc:
        await servico.validate_upload("grande.csv", 2 * UM_MB)

    status, corpo = await _response_body(exc.value)
    assert corpo["error"] == "file_too_large"
    assert status == 413


async def test_allowed_extension_passes(servico):
    assert await servico.validate_upload("mapa.GeoJSON", 10) == "geojson"
