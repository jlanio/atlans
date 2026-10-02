"""O teto de tamanho do Drive vale sobre o objeto REAL, medido no confirm.

No upload por URL pre-assinada quem declara o tamanho e o cliente:
`create_upload_url` valida o numero que veio no corpo e devolve uma URL de PUT
direto para o MinIO, que nao conhece limite nenhum. Declarar 1 KB e enviar 5 GB
passava pelas duas pontas — e o `confirm_upload` ainda MEDIA o objeto e gravava
o tamanho verdadeiro em `size` sem nunca compara-lo a `max_size_mb`.

Banco de verdade (SQLite) em vez de duble: a recusa remove a linha, e e isso
que precisa ser observado — um mock de `db.delete` diria apenas que a chamada
aconteceu.
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
    """Teto de 1 MB e um upload pendente que DECLAROU 1 KB."""
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
    # `expire_on_commit=False` como em `app.core.db` — sem isso o commit expira
    # os atributos e a primeira leitura depois dele tenta IO fora do greenlet.
    async with AsyncSession(eng, expire_on_commit=False) as db:
        db.add(PlatformFileSettings(id=1, max_size_mb=1))
        db.add(WorkspaceFile(
            id_hash="f-1",
            workspace_id="ws-1",
            s3_key=CHAVE,
            original_name="mapa.geojson",
            extension="geojson",
            size=1024,          # o que o cliente disse ao pedir a URL
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

    # Os bytes nao podem ficar: uma recusa que os deixasse no storage seria
    # apenas uma forma mais lenta de aceita-los.
    apagar.assert_awaited_once_with(CHAVE)
    # E a linha some — confirmada, o Drive listaria um arquivo sem objeto.
    assert await _linha(banco) is None
    # Ninguem e avisado de um arquivo que nao entrou.
    evento.assert_not_awaited()


async def test_objeto_dentro_do_teto_confirma_normalmente(banco, apagar, evento):
    """O par do teste acima: sem ele, uma guarda que recusa tudo passaria."""
    with _head(512 * 1024):
        wf = await DriveService(banco).confirm_upload("f-1")

    apagar.assert_not_awaited()
    assert wf.status == "confirmed"
    # O tamanho gravado e o MEDIDO, nao o declarado.
    assert wf.size == 512 * 1024
    assert wf.content_md5 == "etag-do-objeto"
    evento.assert_awaited_once()


async def test_linha_ja_confirmada_e_recusada_sem_apagar_nada(banco, apagar):
    """`confirm_upload` nao filtra por status, e qualquer editor alcanca a rota.

    Se a recusa apagasse aqui, re-confirmar arquivo ALHEIO ja aceito viraria um
    botao de apagar — sem confirmacao e sem lixeira. E nem seria preciso enviar
    byte nenhum: bastava o admin baixar `max_size_mb` para todo arquivo legitimo
    maior que o teto novo ficar a um POST de ser destruido.

    Entao a confirmacao e recusada, mas objeto e registro ficam onde estao. Um
    objeto acima do teto que o reconcile acusa como divergencia e melhor que um
    caminho de exclusao sem guarda.
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
    """Artefato de run nunca teve teto — aplica-lo seria perda de dado.

    `create_agent_upload_url(s3_key_override=...)` pula `validate_upload`
    INTEIRA: extensao E tamanho. Nao ha tamanho DECLARADO para o teto reconferir,
    entao a chave sob `artifacts/{ws}/` CONFIRMA normalmente mesmo acima do teto —
    recusar derrubaria a execucao (o executor faz `raise_for_status` no confirm) e,
    com `overwrite=True`, apagaria o arquivo bom que ja estava no Drive, sem
    ninguem ter mexido em configuracao nenhuma.
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
    """`_validate_agent_s3_key` confere a chave contra TODOS os workspaces do
    executor, nao contra o da linha — entao um `s3_key_override` pode apontar
    para o objeto de outro workspace. A recusa nao pode virar o gatilho que
    destroi bytes alheios.
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
    """MinIO fora do ar na hora de apagar nao pode fazer o arquivo entrar.

    `storage.delete` e best-effort e NUNCA levanta: devolve False. Por isso o
    duble aqui devolve False em vez de levantar — um teste com `side_effect`
    exercitaria um caminho que a funcao real nao tem.
    """
    with _head(9 * UM_MB), patch(
        "app.services.drive_service.s3.delete_async", new=AsyncMock(return_value=False),
    ):
        with pytest.raises(FileTooLargeError):
            await DriveService(banco).confirm_upload("f-1")

    assert await _linha(banco) is None
    evento.assert_not_awaited()
