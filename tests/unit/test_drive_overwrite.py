"""Sobrescrita de arquivo do Drive vinda do executor.

`create_agent_upload_url(overwrite=True)` reaproveita a linha existente em vez
de criar outra. Manter o mesmo id_hash e a mesma s3_key e o ponto: um DataInput
apontando para o arquivo continua valido e passa a ler a versao nova, e o objeto
anterior nao fica orfao no MinIO.
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
    """O confirm consulta o teto de tamanho antes de aceitar o objeto.

    O dublê de `db` aqui responde a QUALQUER query com o mesmo WorkspaceFile,
    então a consulta das configurações precisa de resposta própria. Teto
    folgado de propósito: tamanho não é o assunto deste arquivo — está em
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

    # Nenhuma linha nova.
    svc.db.add.assert_not_called()
    # A s3_key ANTIGA prevalece: o PUT sobrescreve o objeto no lugar.
    assert out["s3_key"] == "artifacts/ws-1/task-ANTIGA/resultado.geojson"
    assert out["id_hash"] == "file-existente"


async def test_overwrite_nao_marca_pending_nem_altera_size():
    """Regressão de perda de dados.

    Marcar a linha como pending a tornava elegível para
    cleanup_pending_workspace_files, que apaga pending com created_at anterior
    ao TTL de 24h — e aqui o created_at é o da criação original, já vencido em
    qualquer arquivo que esteja sendo sobrescrito. Um upload que falhasse
    destruiria o arquivo íntegro. O size também fica intocado: quem o atualiza
    é o confirm_upload, a partir do objeto real no MinIO.
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
    """Comportamento padrão preservado — é o que gera as cópias por execução."""
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


# ── O retorno diz o que aconteceu, não o que foi pedido ──────────────────────


async def test_retorno_marca_reuso():
    """Sem isso o executor só podia repetir a intenção ("pedi para sobrescrever"),
    e um overwrite que não achou o arquivo ficava indistinguível de um que achou."""
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
    """Há arquivo de mesmo nome, mas a opção está desligada — cria outra linha."""
    svc = _svc(encontrado=_existente())

    out = await svc.create_agent_upload_url(
        workspace_id="ws-1", filename="resultado.geojson", size=10,
        uploaded_by="executor-1",
        s3_key_override="artifacts/ws-1/task-NOVA/resultado.geojson",
        overwrite=False,
    )

    assert out["reused"] is False


# ── confirm_upload distingue criação de atualização ──────────────────────────

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
    """Regressão: sem coluna própria, a listagem dependia de `updated_at`.

    Numa sobrescrita com conteúdo IDÊNTICO nenhum campo muda de valor no
    confirm — o SQLAlchemy não emite UPDATE, o onupdate não dispara, e o
    arquivo recém-gravado não subia na listagem. O workflow rodava e o Drive
    não dava sinal nenhum.
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

    # Mesmo com size e md5 inalterados, a data de escrita avança.
    assert wf.content_written_at is not None


async def test_confirm_de_sobrescrita_emite_file_updated():
    """content_md5 preexistente = linha reaproveitada. O GeoSync trata os dois,
    mas o evento precisa dizer a verdade sobre o que aconteceu."""
    assert await _confirm("md5-antigo") == ["file_updated"]


async def test_confirm_de_upload_novo_emite_file_created():
    assert await _confirm(None) == ["file_created"]


# ── Ordenação pela última escrita ────────────────────────────────────────────

async def test_listagem_ordena_pela_ultima_escrita():
    """Sobrescrever mantém o created_at original.

    Ordenar por ele jogaria o conteúdo recém-gravado para o fim da lista, junto
    dos arquivos mais antigos — exatamente o oposto do que o usuário espera ao
    reexecutar um workflow.
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
