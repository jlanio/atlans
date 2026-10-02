"""A recusa de um upload do Drive diz o MOTIVO por código, não só por texto.

O web classificava a recusa (ícone e rótulo em /drive e nos anexos da Home)
procurando trechos em português no `detail` — "extensão", "não permitida",
"vazio". O texto daqui não tem acento ("Extensao '.x' nao permitida."), então a
recusa por extensão caía em "outra falha". E o `error` do corpo, que é estável,
era o mesmo `file_validation_error` para extensão proibida, extensão interna
perigosa e arquivo vazio: não havia como distinguir sem ler a frase.

Cada caso tem agora o seu `error_code`. O status HTTP de cada um continua o de
antes (422 para as validações, 413 para o teto) — o executor, que olha só o
status, não percebe a mudança. E todos seguem sendo `FileValidationError`: quem
captura a classe-mãe (a tool de upload do MCP) continua capturando.

Banco de verdade (SQLite) porque `validate_upload` lê as extensões permitidas e
o teto do banco.
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
    """Teto de 1 MB e só `.csv`/`.geojson` permitidos."""
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


async def _corpo(exc) -> tuple[int, dict]:
    """O que o handler global devolve ao cliente para esta exceção."""
    resp = await atlas_domain_error_handler(MagicMock(), exc)
    return resp.status_code, json.loads(resp.body)


@pytest.mark.parametrize(
    "nome, codigo",
    [
        ("relatorio.pdf", "extension_not_allowed"),
        # Sem extensão é extensão fora da lista: o mesmo caso para quem lê.
        ("LEIAME", "extension_not_allowed"),
        ("notas.sh.csv", "dangerous_inner_extension"),
        ("instalador.exe.geojson", "dangerous_inner_extension"),
    ],
)
async def test_recusa_por_nome_tem_codigo_proprio_e_continua_422(servico, nome, codigo):
    with pytest.raises(FileValidationError) as exc:
        await servico.validate_upload(nome, 10)

    status, corpo = await _corpo(exc.value)
    assert corpo["error"] == codigo
    assert status == 422
    # A frase continua a mesma — é ela que a pessoa lê no painel.
    assert corpo["message"] == exc.value.detail


async def test_arquivo_vazio_tem_codigo_proprio_e_continua_422(servico):
    with pytest.raises(FileValidationError) as exc:
        await servico.upload_file("ws-1", "dados.csv", b"", uploaded_by="u-1")

    status, corpo = await _corpo(exc.value)
    assert corpo == {"error": "empty_file", "message": "Arquivo vazio."}
    assert status == 422


async def test_arquivo_acima_do_teto_continua_413_file_too_large(servico):
    with pytest.raises(FileTooLargeError) as exc:
        await servico.validate_upload("grande.csv", 2 * UM_MB)

    status, corpo = await _corpo(exc.value)
    assert corpo["error"] == "file_too_large"
    assert status == 413


async def test_extensao_permitida_passa(servico):
    assert await servico.validate_upload("mapa.GeoJSON", 10) == "geojson"
