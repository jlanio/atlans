# tests/unit/test_consumer_drive_duplicata.py
"""The consumer created one Drive row per run, despite the overwrite.

Real chain, observed in production with two consecutive runs:

  run A -> DataOutput overwrites the existing row, whose s3_key is from an
           OLD run (.../6f1e9667/imovel.geojson). The PUT goes to that key.
  run A -> _register_artifacts DERIVES the key from the current run's task_id
           (.../91da8a94/imovel.geojson — see _derive_s3_key and the SEG in
           the docstring: the key coming from the executor is ignored on purpose).
           The guard `WHERE s3_key == <derivada>` finds nothing and creates a
           NEW row, confirmed, pointing to a key nobody wrote to.
  run B -> the overwrite lookup takes the workspace's most recent one, which
           is precisely that orphan, and writes to it. And the consumer creates
           another.

Result: the log said "sobrescreveu arquivo existente" (overwrote existing file)
— and it was telling the truth — while the Drive piled up one copy per run. The
`file_created` the executor received (instead of `file_updated`) was the event
for this new row.

The guard now uses the `drive_file_id` that the executor returns, validated
against the database.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.run_result_consumer import _register_artifacts


WS = "ws-1"
TASK_ATUAL = "task-B"
# The reused row holds the key of an old run; the consumer derives the
# current run's. That mismatch is the heart of the bug.
S3_ANTIGA = f"artifacts/{WS}/task-ANTIGO/imovel.geojson"
S3_DERIVADA = f"artifacts/{WS}/{TASK_ATUAL}/imovel.geojson"


def _run() -> MagicMock:
    return MagicMock(workspace_id=WS, task_id=TASK_ATUAL, workflow_hash="wf-1", host=None)


def _meta(**extra) -> dict:
    base = {
        "output_key": "imovel", "format": "geojson", "features": 51,
        "filename": "imovel.geojson", "context": "drive", "s3_key": S3_ANTIGA,
    }
    base.update(extra)
    return {"node-1": [base]}


def _db(*, id_hash_no_banco: str | None = None, workspace_da_linha: str = WS,
        s3_keys_no_banco: tuple[str, ...] = ()):
    """Test double that answers per QUERY, not a single value for all of them.

    Necessary: a double that returns the same result for everything makes the
    s3_key lookup mask the id_hash lookup, and the test passes even with the new
    guard removed. The real case is precisely the one where the two disagree —
    the id_hash matches and the derived s3_key does not exist.

    Both guards became BATCH queries (`in_()`) outside the loop — before, they
    were two queries per Drive item, an N+1 inside the processing of a single
    queue item. That is why the double returns lists via `.scalars().all()`,
    and not an object via `.scalar_one_or_none()`.
    """
    db = MagicMock(commit=AsyncMock(), add=MagicMock())

    async def _execute(stmt):
        # Only the WHERE distinguishes the queries: `select(WorkspaceFile)` lists
        # id_hash AND s3_key in the SELECT clause, so matching on the whole SQL
        # would make the s3_key lookup fall into the id_hash branch.
        onde = str(stmt).split("WHERE")[-1]
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        # The Artifact idempotency guard reads `.all()` of (node_id, filename);
        # Drive items do not produce an Artifact row, so it comes back empty here.
        res.all.return_value = []
        if "id_hash" in onde:
            # Without the workspace filter in the SQL, an id from ANOTHER workspace would
            # match — and the guard would suppress this run's record.
            casa_ws = (workspace_da_linha == WS) if "workspace_id" in onde else True
            achou = bool(id_hash_no_banco) and casa_ws
            linhas = [MagicMock(id_hash=id_hash_no_banco)] if achou else []
        elif "s3_key" in onde:
            linhas = [S3_DERIVADA] if S3_DERIVADA in s3_keys_no_banco else []
        else:
            linhas = []
        res.scalars.return_value.all.return_value = linhas
        return res

    db.execute = AsyncMock(side_effect=_execute)
    return db


def _adicionados(db) -> list:
    from app.models.workspace_file import WorkspaceFile
    return [c.args[0] for c in db.add.call_args_list
            if isinstance(c.args[0], WorkspaceFile)]


@pytest.fixture
def eventos():
    """Captures what would be published to Redis for the executors."""
    return []


@pytest.fixture(autouse=True)
def _sem_io(eventos):
    """No S3 and no WebSocket; the events go to the `eventos` list."""
    async def _emit(workspace_id, action, file_info, **kwargs):
        eventos.append((action, file_info))

    with patch("app.core.storage.head", return_value={"size": 10}), \
         patch("app.core.drive_events.emit_drive_event", side_effect=_emit), \
         patch("app.core.run_result_consumer._get_retention_days",
               new=AsyncMock(return_value=None)):
        yield


@pytest.mark.asyncio
async def test_nao_duplica_apos_sobrescrita():
    """Regression: this is exactly where one copy per run was born.

    The id_hash matches in the database and the derived s3_key does NOT exist —
    because the reused row kept the old run's key. The s3_key guard alone lets
    it through.
    """
    db = _db(id_hash_no_banco="file-1", s3_keys_no_banco=())

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-1"))

    assert _adicionados(db) == []


@pytest.mark.asyncio
async def test_executor_e_avisado_mesmo_sem_criar_linha(eventos):
    """Regression introduced when suppressing the creation: the executor was left without the event.

    `agent_confirm_upload` emits with exclude_agent_id=<executor that uploaded>,
    and there is a single target_executor_id per workspace — usually the same one.
    The event dies there. That is correct for GeoSync, which uploads what it
    already has on disk (uploader.py uses the SAME endpoint), but not for a run
    artifact: the file was produced in memory and the executor does not have it
    locally. Without this emission, SYNC_MODE download/bidirectional stops
    receiving the file.
    """
    db = _db(id_hash_no_banco="file-1")

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-1", drive_reused=True))

    assert _adicionados(db) == []
    assert len(eventos) == 1
    acao, _info = eventos[0]
    assert acao == "file_updated"


@pytest.mark.asyncio
async def test_arquivo_novo_avisa_como_criacao(eventos):
    db = _db(id_hash_no_banco="file-1")

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-1", drive_reused=False))

    assert [a for a, _ in eventos] == ["file_created"]


@pytest.mark.asyncio
async def test_linha_criada_aqui_tambem_avisa(eventos):
    db = _db(id_hash_no_banco=None, s3_keys_no_banco=())

    await _register_artifacts(db, _run(), _meta())

    assert [a for a, _ in eventos] == ["file_created"]


@pytest.mark.asyncio
async def test_id_inexistente_nao_impede_o_registro():
    """The id comes from the executor, so it is not trusted on its own."""
    db = _db(id_hash_no_banco=None)

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-forjado"))

    assert len(_adicionados(db)) == 1


@pytest.mark.asyncio
async def test_id_de_outro_workspace_nao_impede_o_registro():
    """The guard has to restrict to the run's workspace — otherwise a valid id_hash
    from another workspace would suppress this one's record."""
    db = _db(id_hash_no_banco="file-de-outro", workspace_da_linha="ws-2")

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-de-outro"))

    assert len(_adicionados(db)) == 1


@pytest.mark.asyncio
async def test_sem_drive_file_id_mantem_a_guarda_por_s3_key():
    """A path that did not go through executor-upload-url is still protected."""
    db = _db(id_hash_no_banco=None, s3_keys_no_banco=(S3_DERIVADA,))

    await _register_artifacts(db, _run(), _meta())

    assert _adicionados(db) == []


@pytest.mark.asyncio
async def test_cria_a_linha_quando_ninguem_registrou():
    db = _db(id_hash_no_banco=None, s3_keys_no_banco=())

    await _register_artifacts(db, _run(), _meta())

    criadas = _adicionados(db)
    assert len(criadas) == 1
    # The key is still the DERIVED one — the SEG of _derive_s3_key does not change.
    assert criadas[0].s3_key == S3_DERIVADA
    assert criadas[0].status == "confirmed"


@pytest.mark.asyncio
async def test_artefato_comum_nao_e_afetado():
    """context="artifacts" does not go through the Drive guard."""
    from app.models.workspace_file import WorkspaceFile

    db = _db(id_hash_no_banco="file-1")

    await _register_artifacts(db, _run(), _meta(context="artifacts", drive_file_id="file-1"))

    adicionados = [c.args[0] for c in db.add.call_args_list]
    assert adicionados and not any(isinstance(a, WorkspaceFile) for a in adicionados)


@pytest.mark.asyncio
async def test_run_sem_workspace_nao_registra_nada():
    db = _db(id_hash_no_banco=None)
    run = MagicMock(workspace_id=None, task_id=TASK_ATUAL, host=None)

    await _register_artifacts(db, run, _meta(drive_file_id="file-1"))

    db.add.assert_not_called()
