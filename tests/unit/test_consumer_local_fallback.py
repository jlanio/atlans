# tests/unit/test_consumer_local_fallback.py
"""Artefato cujo upload ao MinIO FALHOU (local_fallback) não pode virar um
registro apontando para um objeto inexistente — o download responderia 404 para
sempre.

O fallback grava os bytes no MESMO lugar de um keepLocal
(artifacts_root()/{ws}/{task}/{arquivo}), então o servidor registra o artefato
como executor-local (content_location='executor', s3_key=None, local_path
derivado): sem link quebrado, servido de onde os bytes de fato estão. O executor
reporta content_location='minio' de propósito (o destino era a nuvem) — é o
consumer que decide, pelo flag `local_fallback`.
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
    """Sessao duble. `conhecidos` = pares (node_id, filename) ja no banco para
    a guarda de idempotencia (`select(Artifact.node_id, Artifact.filename)`, lida
    por `.all()`); `s3_conhecidas` = o que a guarda ANTIGA (por s3_key) leria."""
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
    assert a.content_location == "executor"      # não 'minio' com key morta
    assert a.s3_key is None                       # sem link que 404
    assert a.local_path == f"{WS}/{TASK}/buffer.geojson"  # derivado no servidor
    assert a.size_bytes == 123                    # tamanho veio do meta do executor
    assert a.executor_id == "ag-1"


@pytest.mark.asyncio
async def test_upload_bem_sucedido_continua_minio():
    """Sem `local_fallback`, o artefato normal segue apontando para o MinIO."""
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
    """context='drive' que caiu no fallback: o objeto nunca subiu ao MinIO, então
    um WorkspaceFile 'confirmed' com s3_key daria download 404. Vira catálogo
    (content_location='executor', sem s3_key), sem emitir file_created."""
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
    assert eventos == []  # nada para outro executor baixar


@pytest.mark.asyncio
async def test_drive_bem_sucedido_continua_minio_e_emite():
    """Sem fallback, o Drive normal segue com s3_key e avisa os executores."""
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
    """O caminho keepLocal (content_location='executor') não regride."""
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
    """Idempotencia: reprocessar o payload (dead letter / replay) com a linha
    local JA no banco NAO cria uma segunda. A guarda dedup por identidade estavel
    (node_id, filename) no run, nao pela s3_key — que num artefato local e None e
    nunca casava com a key derivada. Mutacao: voltar a dedup pela s3_key derivada
    faz a 2a entrega recriar a linha (a s3_key conhecida e None, nunca casa)."""
    db = _db(conhecidos=[("node-1", "buffer.geojson")], s3_conhecidas=[None])
    await _register_artifacts(db, _run(), _meta(
        content_location="minio", local_fallback=True, size_bytes=123,
    ))
    assert _artefatos(db) == []
