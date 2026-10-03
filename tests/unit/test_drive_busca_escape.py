"""Drive search escapes the LIKE wildcards (`%` and `_`).

Without escaping, `list_files(search=...)` treats the user's `_`/`%` as wildcards
and sweeps the whole listing, giving the impression of a broken filter — the same
defect that `artifact_service._filters` already fixed. A real database (SQLite, as
in `test_drive_teto_no_confirm.py`): what matters is the LIKE behavior, and a
mock would only say the call happened.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.workspace_file import WorkspaceFile
from app.services.drive_service import DriveService

WS = "ws-1"


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(WorkspaceFile.metadata.create_all, tables=[WorkspaceFile.__table__])
    async with AsyncSession(eng, expire_on_commit=False) as sessao:
        yield sessao
    await eng.dispose()


async def _seed(db, *nomes):
    for i, nome in enumerate(nomes):
        db.add(WorkspaceFile(
            id_hash=f"f-{i}",
            workspace_id=WS,
            s3_key=f"drive/{WS}/{i}_{nome}",
            original_name=nome,
            extension=nome.rsplit(".", 1)[-1],
            size=10,
            uploaded_by="u-1",
            status="confirmed",
        ))
    await db.commit()


async def test_user_underscore_is_literal_and_does_not_match_everything(db):
    # `aXb` matches the PATTERN `a_b` if `_` is a wildcard, and does not if it is literal.
    # This is the row that discriminates: without it, both versions of the code
    # return the same and the test proves nothing.
    await _seed(db, "aXb.geojson", "a_b.geojson")

    items, total = await DriveService(db).list_files(WS, search="a_b")

    assert total == 1, "o sublinhado voltou a ser curinga"
    assert items[0].original_name == "a_b.geojson"


async def test_user_percent_is_also_literal(db):
    # `100X` matches `100%` with `%` as a wildcard; only `100%` matches literally.
    await _seed(db, "100X.geojson", "100%.geojson")

    items, total = await DriveService(db).list_files(WS, search="100%")

    assert total == 1, "o porcento voltou a ser curinga"
    assert items[0].original_name == "100%.geojson"
