"""The Drive size ceiling applies to the REAL object, measured at confirm.

In a pre-signed URL upload, the client is the one declaring the size:
`create_upload_url` validates the number in the body and returns a direct PUT
URL to MinIO, which knows no limit at all. Declaring 1 KB and sending 5 GB got
through both ends — and `confirm_upload` even MEASURED the object and wrote the
true size into `size` without ever comparing it to `max_size_mb`.

Real database (SQLite) instead of a double: the rejection removes the row, and
that is what needs to be observed — a mock of `db.delete` would only say the
call happened.
"""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.exceptions import FileTooLargeError
from app.models.platform_file_settings import AllowedFileExtension, PlatformFileSettings
from app.models.workspace_file import WorkspaceFile
from app.services.drive_service import DriveService

UM_MB = 1024 * 1024
CHAVE = "drive/ws-1/abc_mapa.geojson"


@pytest_asyncio.fixture
async def banco():
    """1 MB ceiling and a pending upload that DECLARED 1 KB."""
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
    # `expire_on_commit=False` as in `app.core.db` — without it the commit expires
    # the attributes and the first read after it attempts IO outside the greenlet.
    async with AsyncSession(eng, expire_on_commit=False) as db:
        db.add(PlatformFileSettings(id=1, max_size_mb=1))
        db.add(WorkspaceFile(
            id_hash="f-1",
            workspace_id="ws-1",
            s3_key=CHAVE,
            original_name="mapa.geojson",
            extension="geojson",
            size=1024,          # what the client said when requesting the URL
            uploaded_by="u-1",
            status="pending",
        ))
        await db.commit()
        yield db
    await eng.dispose()


def _head(tamanho: int):
    return patch(
        "app.services.drive_service.s3.head_async",
        new=AsyncMock(return_value={"size": tamanho, "etag": "etag-do-objeto"}),
    )


@pytest.fixture
def apagar():
    with patch(
        "app.services.drive_service.s3.delete_async", new=AsyncMock(return_value=True),
    ) as m:
        yield m


@pytest.fixture(autouse=True)
def evento():
    with patch(
        "app.services.drive_service.emit_drive_event", new=AsyncMock(),
    ) as m:
        yield m


async def _linha(db, id_hash="f-1"):
    return (await db.execute(
        select(WorkspaceFile).where(WorkspaceFile.id_hash == id_hash)
    )).scalar_one_or_none()


async def test_objeto_acima_do_teto_e_recusado_e_apagado(banco, apagar, evento):
    """Declarou 1 KB, enviou 5 MB contra um teto de 1 MB."""
    with _head(5 * UM_MB):
        with pytest.raises(FileTooLargeError):
            await DriveService(banco).confirm_upload("f-1")

    # The bytes cannot stay: a rejection that left them in storage would be
    # just a slower way of accepting them.
    apagar.assert_awaited_once_with(CHAVE)
    # E a linha some — confirmada, o Drive listaria um arquivo sem objeto.
    assert await _linha(banco) is None
    # Nobody is notified about a file that did not get in.
    evento.assert_not_awaited()


async def test_objeto_dentro_do_teto_confirma_normalmente(banco, apagar, evento):
    """The counterpart of the test above: without it, a guard that rejects everything would pass."""
    with _head(512 * 1024):
        wf = await DriveService(banco).confirm_upload("f-1")

    apagar.assert_not_awaited()
    assert wf.status == "confirmed"
    # O tamanho gravado e o MEDIDO, nao o declarado.
    assert wf.size == 512 * 1024
    assert wf.content_md5 == "etag-do-objeto"
    evento.assert_awaited_once()


async def test_linha_ja_confirmada_e_recusada_sem_apagar_nada(banco, apagar):
    """`confirm_upload` does not filter by status, and any editor can reach the route.

    If the rejection deleted here, re-confirming SOMEONE ELSE'S already accepted
    file would become a delete button — with no confirmation and no trash. And no
    bytes would even need to be sent: it would be enough for the admin to lower
    `max_size_mb` for every legitimate file larger than the new ceiling to be one
    POST away from destruction.

    So the confirmation is rejected, but object and record stay where they are.
    An object above the ceiling that reconcile flags as a discrepancy is better
    than an unguarded deletion path.
    """
    alvo = await _linha(banco)
    alvo.status = "confirmed"
    alvo.content_md5 = "md5-do-conteudo-antigo"
    await banco.commit()

    with _head(3 * UM_MB):
        with pytest.raises(FileTooLargeError):
            await DriveService(banco).confirm_upload("f-1")

    apagar.assert_not_awaited()
    sobrevivente = await _linha(banco)
    assert sobrevivente is not None
    assert sobrevivente.content_md5 == "md5-do-conteudo-antigo"  # intacta


async def test_artefato_de_execucao_acima_do_teto_confirma_sem_recusar(banco, apagar, evento):
    """A run artifact never had a ceiling — applying it would mean data loss.

    `create_agent_upload_url(s3_key_override=...)` skips `validate_upload`
    ENTIRELY: extension AND size. There is no DECLARED size for the ceiling to
    re-check, so the key under `artifacts/{ws}/` CONFIRMS normally even above the
    ceiling — rejecting would bring down the run (the executor does
    `raise_for_status` on the confirm) and, with `overwrite=True`, would delete
    the good file already in the Drive, without anyone having touched any setting.
    """
    alvo = await _linha(banco)
    alvo.s3_key = "artifacts/ws-1/task-abc/resultado.geojson"
    await banco.commit()

    with _head(7 * UM_MB):
        wf = await DriveService(banco).confirm_upload("f-1")

    apagar.assert_not_awaited()
    assert wf.status == "confirmed"
    assert wf.size == 7 * UM_MB          # o objeto grande entra, nao e recusado
    assert await _linha(banco) is not None
    evento.assert_awaited_once()


async def test_chave_apontando_para_outro_workspace_nao_e_apagada(banco, apagar):
    """`_validate_agent_s3_key` checks the key against ALL of the executor's
    workspaces, not against the row's — so an `s3_key_override` can point to
    another workspace's object. The rejection cannot become the trigger that
    destroys someone else's bytes.
    """
    alvo = await _linha(banco)
    alvo.s3_key = "drive/ws-VITIMA/abc_alvo.gpkg"
    await banco.commit()

    with _head(7 * UM_MB):
        with pytest.raises(FileTooLargeError):
            await DriveService(banco).confirm_upload("f-1")

    apagar.assert_not_awaited()
    assert await _linha(banco) is not None


async def test_falha_ao_apagar_nao_transforma_recusa_em_aceite(banco, evento):
    """MinIO being down at deletion time must not let the file in.

    `storage.delete` is best-effort and NEVER raises: it returns False. That is
    why the double here returns False instead of raising — a test with
    `side_effect` would exercise a path the real function does not have.
    """
    with _head(9 * UM_MB), patch(
        "app.services.drive_service.s3.delete_async", new=AsyncMock(return_value=False),
    ):
        with pytest.raises(FileTooLargeError):
            await DriveService(banco).confirm_upload("f-1")

    assert await _linha(banco) is None
    evento.assert_not_awaited()
