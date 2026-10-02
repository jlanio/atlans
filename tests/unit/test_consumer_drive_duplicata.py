# tests/unit/test_consumer_drive_duplicata.py
"""O consumer criava uma linha de Drive por execucao, apesar da sobrescrita.

Cadeia real, observada em producao com dois runs seguidos:

  run A -> DataOutput sobrescreve a linha existente, cuja s3_key e de um run
           ANTIGO (.../6f1e9667/imovel.geojson). O PUT vai para essa key.
  run A -> _register_artifacts DERIVA a key do task_id do run atual
           (.../91da8a94/imovel.geojson — ver _derive_s3_key e o SEG na
           docstring: a key vinda do executor e ignorada de proposito).
           A guarda `WHERE s3_key == <derivada>` nao acha nada e cria uma linha
           NOVA, confirmed, apontando para uma key onde ninguem escreveu.
  run B -> a busca da sobrescrita pega a mais recente do workspace, que e
           justamente essa orfa, e escreve nela. E o consumer cria outra.

Resultado: o log dizia "sobrescreveu arquivo existente" — e dizia a verdade —
enquanto o Drive acumulava uma copia por execucao. O `file_created` que o
executor recebia (em vez de `file_updated`) era o evento desta linha nova.

A guarda passou a usar o `drive_file_id` que o executor devolve, validado
contra o banco.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.run_result_consumer import _register_artifacts


WS = "ws-1"
TASK_ATUAL = "task-B"
# A linha reaproveitada guarda a key de um run antigo; o consumer deriva a do
# run atual. Esse descasamento e o coracao do bug.
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
    """Duble que responde por QUERY, nao um valor unico para todas.

    Necessario: um duble que devolve o mesmo resultado para tudo faz a busca por
    s3_key mascarar a busca por id_hash, e o teste passa mesmo com a guarda nova
    removida. O caso real e justamente aquele em que as duas discordam — o
    id_hash casa e a s3_key derivada nao existe.

    As duas guardas viraram consultas EM LOTE (`in_()`) fora do laco — antes
    eram duas queries por item de Drive, um N+1 dentro do processamento de um
    unico item da fila. Por isso o duble devolve listas por `.scalars().all()`,
    e nao um objeto por `.scalar_one_or_none()`.
    """
    db = MagicMock(commit=AsyncMock(), add=MagicMock())

    async def _execute(stmt):
        # So o WHERE distingue as consultas: `select(WorkspaceFile)` lista
        # id_hash E s3_key na clausula SELECT, entao casar no SQL inteiro faria
        # a busca por s3_key cair no ramo do id_hash.
        onde = str(stmt).split("WHERE")[-1]
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        # A guarda de idempotencia de Artifact le `.all()` de (node_id, filename);
        # itens de Drive nao geram linha Artifact, entao ela volta vazia aqui.
        res.all.return_value = []
        if "id_hash" in onde:
            # Sem o filtro de workspace no SQL, um id de OUTRO workspace casaria
            # — e a guarda suprimiria o registro deste run.
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
    """Captura o que seria publicado no Redis para os executores."""
    return []


@pytest.fixture(autouse=True)
def _sem_io(eventos):
    """Sem S3 e sem WebSocket; os eventos vao para a lista `eventos`."""
    async def _emit(workspace_id, action, file_info, **kwargs):
        eventos.append((action, file_info))

    with patch("app.core.storage.head", return_value={"size": 10}), \
         patch("app.core.drive_events.emit_drive_event", side_effect=_emit), \
         patch("app.core.run_result_consumer._get_retention_days",
               new=AsyncMock(return_value=None)):
        yield


@pytest.mark.asyncio
async def test_nao_duplica_apos_sobrescrita():
    """Regressão: era exatamente aqui que nascia uma cópia por execução.

    O id_hash casa no banco e a s3_key derivada NÃO existe — porque a linha
    reaproveitada guardou a key do run antigo. A guarda por s3_key, sozinha,
    deixa passar.
    """
    db = _db(id_hash_no_banco="file-1", s3_keys_no_banco=())

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-1"))

    assert _adicionados(db) == []


@pytest.mark.asyncio
async def test_executor_e_avisado_mesmo_sem_criar_linha(eventos):
    """Regressão introduzida ao suprimir a criação: o executor ficava sem o evento.

    `agent_confirm_upload` emite com exclude_agent_id=<executor que subiu>, e há
    um único target_executor_id por workspace — normalmente o mesmo. O evento
    morre ali. Isso é correto para o GeoSync, que sobe o que já tem em disco
    (uploader.py usa o MESMO endpoint), mas não para um artefato de run: o
    arquivo foi produzido em memória e o executor não o tem localmente. Sem
    esta emissão, SYNC_MODE download/bidirectional para de receber o arquivo.
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
    """O id vem do executor, então não vale por si só."""
    db = _db(id_hash_no_banco=None)

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-forjado"))

    assert len(_adicionados(db)) == 1


@pytest.mark.asyncio
async def test_id_de_outro_workspace_nao_impede_o_registro():
    """A guarda tem de restringir ao workspace do run — senão um id_hash válido
    de outro workspace suprimiria o registro deste."""
    db = _db(id_hash_no_banco="file-de-outro", workspace_da_linha="ws-2")

    await _register_artifacts(db, _run(), _meta(drive_file_id="file-de-outro"))

    assert len(_adicionados(db)) == 1


@pytest.mark.asyncio
async def test_sem_drive_file_id_mantem_a_guarda_por_s3_key():
    """Caminho que não passou pelo executor-upload-url continua protegido."""
    db = _db(id_hash_no_banco=None, s3_keys_no_banco=(S3_DERIVADA,))

    await _register_artifacts(db, _run(), _meta())

    assert _adicionados(db) == []


@pytest.mark.asyncio
async def test_cria_a_linha_quando_ninguem_registrou():
    db = _db(id_hash_no_banco=None, s3_keys_no_banco=())

    await _register_artifacts(db, _run(), _meta())

    criadas = _adicionados(db)
    assert len(criadas) == 1
    # A key continua sendo a DERIVADA — o SEG de _derive_s3_key não muda.
    assert criadas[0].s3_key == S3_DERIVADA
    assert criadas[0].status == "confirmed"


@pytest.mark.asyncio
async def test_artefato_comum_nao_e_afetado():
    """context="artifacts" não passa pela guarda de Drive."""
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
