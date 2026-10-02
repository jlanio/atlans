"""
Regressoes do GeoSync (executor/sync/**).

Cobre os achados da auditoria do subsistema executor:
  B5  — file_deleted apagava arquivo local mesmo em SYNC_MODE=upload
  B6  — delete remoto acontecia ANTES do upload e o manifesto perdia remote_id_hash
  B10 — o '<dataset>.zip' do shapefile nunca casava no manifesto e colidia de chave
  S4  — scanner/uploader seguiam symlinks (vazamento de arquivo de fora da pasta)
  P4  — I/O pesado sincrono dentro do event loop
  D1  — o laco do SyncManager.run() morria em silencio
  B8  — contrato claims_event() para o fan-out de drive_events

E os achados da revisao adversarial das PROPRIAS correcoes:
  R1  — o push gravava um dataset de arquivo unico por cima do bundle shapefile
  R2  — falha ao mover para a lixeira apagava a entrada do manifesto assim mesmo
  R3  — o retry pela SyncQueue nunca deletava a copia remota antiga
  R5  — a lixeira quebrava o stem do shapefile (um carimbo por arquivo)
  R6  — a lixeira crescia sem expurgo dentro da pasta do tecnico
  R7  — o push nao tinha verificacao de conflito nenhuma
  R8  — um '<ds>.zip' alheio sequestrava o remote_id_hash do bundle
  R9  — o watcher nunca chamava on_change: o sync so acordava no tick de 30s
"""
import asyncio
import hashlib
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from executor.sync.paths import (
    TRASH_DIR_NAME,
    is_inside,
    move_dataset_to_trash,
    purge_trash,
)


LOCAL_URL = "ws://localhost:8000"  # is_local_server → sem exigir cert mTLS


@pytest.fixture
def sem_validacao_espacial(monkeypatch):
    """
    Neutraliza validator/metadata: os fixtures gravam bytes falsos e o objetivo
    destes testes e a ORDEM das operacoes de sync, nao a leitura via GDAL.
    """
    from executor.sync import manager as manager_mod
    from executor.sync.validator import ValidationResult

    monkeypatch.setattr(manager_mod, "validate_dataset", lambda ds: ValidationResult(True))
    monkeypatch.setattr(manager_mod, "extract_metadata", lambda path, tipo: {})


def _make_manager(tmp_path: Path, mode: str = "upload"):
    """SyncManager real com uploader/downloader/trigger substituidos por mocks."""
    from executor.sync import manager as manager_mod
    from executor.sync.manager import SyncManager

    sm = SyncManager(
        sync_dir=str(tmp_path),
        workspace_id="ws-1",
        server_url=LOCAL_URL,
        executor_id="ag-1",
        interval=1,
    )
    sm.sync_mode = mode
    sm.uploader = MagicMock()
    sm.uploader.delete = AsyncMock(return_value=True)
    sm.uploader.upload = AsyncMock(return_value=None)
    sm.downloader = MagicMock()
    sm.downloader.download = AsyncMock(return_value=True)
    sm.downloader.list_remote = AsyncMock(return_value=[])
    sm.trigger._triggers = []
    assert manager_mod  # silencia linters sobre import nao usado
    return sm


def _deleted_event(id_hash: str, name: str) -> dict:
    return {"action": "file_deleted", "file": {"id_hash": id_hash, "original_name": name}}


def _created_event(id_hash: str, name: str, content_md5: str = "md5-remoto") -> dict:
    return {"action": "file_created",
            "file": {"id_hash": id_hash, "original_name": name,
                     "content_md5": content_md5, "size": 4}}


def _capturar_eventos(sm) -> list[tuple[str, str]]:
    """Substitui o emissor por um coletor — o SyncManager de teste nao tem fila."""
    eventos: list[tuple[str, str]] = []
    sm.events.emit = lambda event, dataset="", **kw: eventos.append((event, dataset))
    return eventos


# ── B5 — gate de modo no drive_event ──────────────────────────────────────────

def test_b5_file_deleted_nao_apaga_nada_em_modo_upload(tmp_path):
    """SYNC_MODE=upload (padrao) nao pode consumir delecoes vindas do Drive."""
    alvo = tmp_path / "parcelas.shp"
    alvo.write_bytes(b"x" * 32)

    sm = _make_manager(tmp_path, mode="upload")
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {"parcelas.shp": {"md5": "a"}},
        "remote_id_hash": "rid-1",
    })

    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "parcelas.zip")))

    assert alvo.exists(), "modo upload apagou arquivo local a partir de um evento do Drive"
    assert sm.manifest.get_dataset("parcelas") is not None


@pytest.mark.parametrize("modo", ["download", "bidirectional"])
def test_b5_file_deleted_move_para_lixeira_e_nao_unlink(tmp_path, modo):
    """Nos modos que consomem o Drive, o arquivo vai para .atlans-trash/."""
    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text("{}")

    sm = _make_manager(tmp_path, mode=modo)
    sm.manifest.set_dataset("parcelas", {
        "type": "geojson",
        "files": {"parcelas.geojson": {"md5": "a"}},
        "remote_id_hash": "rid-1",
    })

    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "parcelas.geojson")))

    assert not alvo.exists()
    assert sm.manifest.get_dataset("parcelas") is None
    recuperaveis = list((tmp_path / TRASH_DIR_NAME).glob("parcelas_*/parcelas.geojson"))
    assert len(recuperaveis) == 1, "arquivo nao foi preservado na lixeira"
    assert recuperaveis[0].read_text() == "{}"


def test_b5_lixeira_nao_colide_nem_sobrescreve(tmp_path):
    """Dois descartes do mesmo dataset geram duas pastas distintas na lixeira."""
    for conteudo in (b"primeiro", b"segundo"):
        f = tmp_path / "dados.geojson"
        f.write_bytes(conteudo)
        assert move_dataset_to_trash(tmp_path, "dados", [f]) == []

    guardados = sorted(p.read_bytes()
                       for p in (tmp_path / TRASH_DIR_NAME).glob("*/dados.geojson"))
    assert guardados == [b"primeiro", b"segundo"]


def test_b5_lixeira_e_invisivel_para_o_scanner(tmp_path):
    """Senao a lixeira vira loop de reupload."""
    from executor.sync.scanner import DatasetScanner

    (tmp_path / "ativo.geojson").write_text("{}")
    f = tmp_path / "descartado.geojson"
    f.write_text("{}")
    move_dataset_to_trash(tmp_path, "descartado", [f])

    datasets = DatasetScanner(str(tmp_path)).scan()
    assert set(datasets) == {"ativo"}


def test_b5_watcher_ignora_eventos_dentro_da_lixeira(tmp_path):
    from executor.sync.watcher import _SyncEventHandler

    h = _SyncEventHandler(lambda *_: None)
    assert h._should_process(str(tmp_path / "dados.geojson")) is True
    assert h._should_process(str(tmp_path / TRASH_DIR_NAME / "dados_20260101T000000.geojson")) is False


# ── B6 — upload antes do delete + merge do manifesto ──────────────────────────

def test_b6_upload_acontece_antes_do_delete_da_copia_antiga(tmp_path, sem_validacao_espacial):
    """Um crash entre DELETE e PUT sumia com o arquivo do Drive para sempre."""
    from executor.sync.uploader import UploadResult

    (tmp_path / "dados.geojson").write_text('{"a":1}')

    sm = _make_manager(tmp_path, mode="upload")
    sm.manifest.set_dataset("dados", {
        "type": "geojson",
        "files": {"dados.geojson": {"md5": "hash-antigo"}},
        "remote_id_hash": "rid-antigo",
        "remote_name": "dados.geojson",
        "status": "synced",
        "sync_direction": "local",
    })

    ordem: list[str] = []
    sm.uploader.upload = AsyncMock(side_effect=lambda *a, **k: (
        ordem.append("upload"),
        UploadResult(id_hash="rid-novo", remote_name="dados.geojson", remote_md5="m"),
    )[1])
    sm.uploader.delete = AsyncMock(side_effect=lambda rid: (ordem.append(f"delete:{rid}"), True)[1])

    asyncio.run(sm._local_to_remote())

    assert ordem == ["upload", "delete:rid-antigo"]
    assert sm.manifest.get_dataset("dados")["remote_id_hash"] == "rid-novo"


def test_b6_delete_nao_roda_se_o_upload_falhar(tmp_path, sem_validacao_espacial):
    (tmp_path / "dados.geojson").write_text('{"a":1}')

    sm = _make_manager(tmp_path, mode="upload")
    sm.manifest.set_dataset("dados", {
        "type": "geojson",
        "files": {"dados.geojson": {"md5": "hash-antigo"}},
        "remote_id_hash": "rid-antigo",
        "status": "synced",
        "sync_direction": "local",
    })
    sm.uploader.upload = AsyncMock(return_value=None)

    asyncio.run(sm._local_to_remote())

    sm.uploader.delete.assert_not_awaited()
    # A copia remota antiga continua referenciada — ainda da para recuperar.
    assert sm.manifest.get_dataset("dados")["remote_id_hash"] == "rid-antigo"


def test_b6_estado_uploading_preserva_remote_id_hash_e_files(tmp_path, sem_validacao_espacial):
    """Se o processo morrer no meio do upload, o manifesto tem que continuar util."""
    (tmp_path / "dados.geojson").write_text('{"a":1}')

    sm = _make_manager(tmp_path, mode="upload")
    sm.manifest.set_dataset("dados", {
        "type": "geojson",
        "files": {"dados.geojson": {"md5": "hash-antigo"}},
        "remote_id_hash": "rid-antigo",
        "status": "synced",
        "sync_direction": "local",
    })

    visto: dict = {}

    async def _falha_no_put(*_a, **_k):
        visto.update(sm.manifest.get_dataset("dados"))
        return None

    sm.uploader.upload = AsyncMock(side_effect=_falha_no_put)
    scan = asyncio.run(asyncio.to_thread(sm.scanner.scan))
    asyncio.run(sm._upload_dataset("dados", scan["dados"]))

    assert visto["status"] == "uploading"
    assert visto["remote_id_hash"] == "rid-antigo", "perdeu o id remoto durante o upload"
    # 'files' NAO pode ter sido atualizado: o diff() concluiria "em dia" e o
    # arquivo nunca mais subiria.
    assert visto["files"]["dados.geojson"]["md5"] == "hash-antigo"


# ── B10 — remote_name do bundle shapefile ─────────────────────────────────────

def _shapefile(tmp_path: Path, stem: str = "parcelas"):
    for ext in (".shp", ".dbf", ".shx"):
        (tmp_path / f"{stem}{ext}").write_bytes(b"\x00" * 16)


class _RF:
    """Stub de RemoteFileInfo."""

    def __init__(self, id_hash, original_name, content_md5, extension="zip", size=10):
        self.id_hash = id_hash
        self.original_name = original_name
        self.content_md5 = content_md5
        self.extension = extension
        self.size = size
        self.created_at = None
        self.updated_at = None


def test_b10_upload_de_shapefile_grava_remote_name_do_zip(tmp_path, sem_validacao_espacial):
    from executor.sync.uploader import UploadResult

    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="upload")
    sm.uploader.upload = AsyncMock(
        return_value=UploadResult(id_hash="rid-zip", remote_name="parcelas.zip", remote_md5="md5-do-zip")
    )

    asyncio.run(sm._local_to_remote())

    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_name"] == "parcelas.zip"
    assert ds["remote_md5"] == "md5-do-zip", "manifesto guardou o hash dos componentes, nao o do objeto enviado"
    assert set(ds["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}


def test_b10_zip_do_bundle_nao_e_rebaixado_nem_colide_de_chave(tmp_path):
    """O ciclo antigo baixava '<dataset>.zip' por cima e destruia o dataset."""
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {f"parcelas{e}": {"md5": "x"} for e in (".shp", ".dbf", ".shx")},
        "remote_id_hash": "rid-zip",
        "remote_name": "parcelas.zip",
        "remote_md5": "md5-do-zip",
        "local_md5": "a|b|c",
        "status": "synced",
        "sync_direction": "local",
    })
    sm.downloader.list_remote = AsyncMock(return_value=[_RF("rid-zip", "parcelas.zip", "md5-do-zip")])

    asyncio.run(sm._remote_to_local())

    sm.downloader.download.assert_not_awaited()
    assert set(sm.manifest.all_datasets()) == {"parcelas"}
    assert set(sm.manifest.get_dataset("parcelas")["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}
    assert not (tmp_path / "parcelas.zip").exists()


def test_b10_md5_remoto_do_bundle_e_realinhado_sem_download(tmp_path):
    """Manifesto de versao antiga guardava 'a|b|c' como remote_md5 — so corrigir."""
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {f"parcelas{e}": {"md5": "x"} for e in (".shp", ".dbf", ".shx")},
        "remote_id_hash": "rid-zip",
        "remote_md5": "a|b|c",
        "local_md5": "a|b|c",
        "status": "synced",
        "sync_direction": "local",
    })
    sm.downloader.list_remote = AsyncMock(return_value=[_RF("rid-zip", "parcelas.zip", "md5-do-zip")])

    asyncio.run(sm._remote_to_local())

    sm.downloader.download.assert_not_awaited()
    assert sm.manifest.get_dataset("parcelas")["remote_md5"] == "md5-do-zip"


def test_b10_chave_de_arquivo_remoto_novo_nao_atropela_o_bundle(tmp_path):
    from executor.sync.manager import _new_remote_ds_key

    existentes = {"parcelas": {"type": "shapefile"}}
    assert _new_remote_ds_key("municipios.geojson", existentes) == "municipios"
    assert _new_remote_ds_key("parcelas.zip", existentes) == "parcelas.zip"
    assert _new_remote_ds_key("SEM_EXTENSAO", existentes) == "sem_extensao"


# ── S4 — contencao de symlink no upload ───────────────────────────────────────

def _symlink_ou_skip(link: Path, alvo: Path):
    try:
        link.symlink_to(alvo)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")


def test_s4_scanner_pula_symlinks(tmp_path):
    from executor.sync.scanner import DatasetScanner

    segredo = tmp_path.parent / "client.key"
    # Isca do teste, nao uma chave: o header vazio basta para o cenario (o
    # scanner nao pode seguir o symlink para fora da pasta de sync).
    segredo.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    sync = tmp_path / "gis"
    sync.mkdir()
    (sync / "real.csv").write_text("a,b\n1,2\n")
    _symlink_ou_skip(sync / "pontos.csv", segredo)

    datasets = DatasetScanner(str(sync)).scan()
    assert set(datasets) == {"real"}, "symlink para fora da pasta entrou no sync"


def test_s4_uploader_recusa_componente_fora_da_pasta(tmp_path):
    """TOCTOU: entre o scan e o upload o componente pode virar symlink."""
    from executor.sync.scanner import Dataset, FileInfo
    from executor.sync.uploader import DriveUploader

    sync = tmp_path / "gis"
    sync.mkdir()
    fora = tmp_path / "client.key"
    fora.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    for ext in (".shp", ".shx"):
        (sync / f"parcelas{ext}").write_bytes(b"\x00" * 8)
    _symlink_ou_skip(sync / "parcelas.dbf", fora)

    ds = Dataset("parcelas", "shapefile")
    for p in (sync / "parcelas.shp", sync / "parcelas.shx", sync / "parcelas.dbf"):
        ds.add_file(FileInfo(p))

    up = DriveUploader(LOCAL_URL, "ag-1", "ws-1", str(sync))
    up._upload_file = AsyncMock(return_value="NAO DEVERIA SUBIR")

    assert asyncio.run(up.upload(ds)) is None
    up._upload_file.assert_not_awaited()


def test_s4_uploader_recusa_arquivo_unico_fora_da_pasta(tmp_path):
    from executor.sync.scanner import Dataset, FileInfo
    from executor.sync.uploader import DriveUploader

    sync = tmp_path / "gis"
    sync.mkdir()
    fora = tmp_path / "client.key"
    fora.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    _symlink_ou_skip(sync / "pontos.csv", fora)

    ds = Dataset("pontos", "tabular")
    ds.add_file(FileInfo(sync / "pontos.csv"))

    up = DriveUploader(LOCAL_URL, "ag-1", "ws-1", str(sync))
    up._upload_file = AsyncMock(return_value="NAO DEVERIA SUBIR")

    assert asyncio.run(up.upload(ds)) is None
    up._upload_file.assert_not_awaited()


def test_s4_uploader_recusa_componente_de_fora_sem_precisar_de_symlink(tmp_path):
    """Mesma contencao do caso symlink, exercitada onde symlink nao esta disponivel."""
    from executor.sync.scanner import Dataset, FileInfo
    from executor.sync.uploader import DriveUploader

    sync = tmp_path / "gis"
    sync.mkdir()
    fora = tmp_path / "client.key"
    fora.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    (sync / "parcelas.shp").write_bytes(b"\x00" * 8)

    ds = Dataset("parcelas", "shapefile")
    ds.add_file(FileInfo(sync / "parcelas.shp"))
    ds.add_file(FileInfo(fora))  # componente resolvido fora da pasta de sync

    up = DriveUploader(LOCAL_URL, "ag-1", "ws-1", str(sync))
    up._upload_file = AsyncMock(return_value="NAO DEVERIA SUBIR")

    assert asyncio.run(up.upload(ds)) is None
    up._upload_file.assert_not_awaited()


def test_s4_is_inside_aceita_arquivo_legitimo(tmp_path):
    f = tmp_path / "ok.geojson"
    f.write_text("{}")
    assert is_inside(tmp_path, f) is True
    assert is_inside(tmp_path, tmp_path / "inexistente.geojson") is False


# ── P4 — nada de I/O pesado sincrono no event loop ────────────────────────────

def test_p4_remote_to_local_escaneia_uma_vez_so(tmp_path):
    """scan() por arquivo remoto era O(n x bytes) dentro da corrotina."""
    sm = _make_manager(tmp_path, mode="bidirectional")
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text("{}")

    chamadas = {"n": 0}
    real_scan = sm.scanner.scan

    def _contando():
        chamadas["n"] += 1
        return real_scan()

    sm.scanner.scan = _contando
    sm.downloader.list_remote = AsyncMock(return_value=[
        _RF(f"rid-{i}", f"d{i}.geojson", f"md5-{i}", extension="geojson") for i in range(5)
    ])
    for i in range(5):
        sm.manifest.set_dataset(f"d{i}", {
            "type": "geojson",
            "files": {f"d{i}.geojson": {"md5": "x"}},
            "remote_id_hash": f"rid-{i}",
            "remote_name": f"d{i}.geojson",
            "remote_md5": "outro",
            "local_md5": "x",
            "sync_direction": "remote",
        })

    asyncio.run(sm._remote_to_local())

    assert chamadas["n"] <= 1, f"scan() chamado {chamadas['n']}x — voltou para dentro do laco"


def test_p4_upload_transmite_em_streaming_e_hasheia_o_conteudo(tmp_path):
    """Nada de f.read() do arquivo inteiro; o MD5 tem que ser o do objeto enviado."""
    from executor.sync.uploader import _aiter_file, _file_md5

    conteudo = b"raster-grande" * 100_000
    alvo = tmp_path / "grande.tif"
    alvo.write_bytes(conteudo)

    assert _file_md5(alvo) == hashlib.md5(conteudo).hexdigest()

    async def _coletar():
        pedacos = [c async for c in _aiter_file(alvo)]
        return pedacos

    pedacos = asyncio.run(_coletar())
    assert b"".join(pedacos) == conteudo
    assert len(pedacos) > 1, "arquivo grande foi entregue num unico buffer"


def test_p4_local_to_remote_nao_bloqueia_o_event_loop(tmp_path, sem_validacao_espacial):
    """
    O heartbeat aplicativo de 30s e o unico keepalive (ping_interval=None): se o
    scan/diff voltar para dentro da corrotina, a conexao cai com 4408 e o run em
    andamento morre.

    Chamamos `_local_to_remote` DE VERDADE (a versao anterior deste teste
    exercitava `asyncio.to_thread` do stdlib e passaria mesmo com o bug) e
    contamos as voltas do event loop enquanto o scan — deliberadamente lento —
    esta rodando. Com o scan dentro da corrotina, o loop fica parado a janela
    inteira e a conta da zero.

    Conta de voltas, e nao o MAIOR intervalo entre duas delas: o intervalo mede
    o runner junto com o codigo. Uma pausa do processo (coleta de lixo com a
    suite inteira carregada, CPU roubada da VM) chegou a 0,32 s no CI com o scan
    na thread, e o limite era 0,3 s. A pausa so encurta a janela: o loop volta a
    girar antes de o scan terminar.
    """
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text('{"a":1}')

    sm = _make_manager(tmp_path, mode="upload")
    sm.uploader.upload = AsyncMock(return_value=None)

    scan_real = sm.scanner.scan
    scan = {"rodando": False, "voltas_do_loop": 0}

    def _scan_lento():
        scan["rodando"] = True
        try:
            time.sleep(0.5)  # I/O real de uma pasta grande: stat + MD5 de tudo
        finally:
            scan["rodando"] = False
        return scan_real()

    sm.scanner.scan = _scan_lento

    async def _cenario():
        async def _batendo():
            while True:
                await asyncio.sleep(0)
                if scan["rodando"]:
                    scan["voltas_do_loop"] += 1

        hb = asyncio.create_task(_batendo())
        await asyncio.sleep(0)
        await sm._local_to_remote()
        hb.cancel()

    asyncio.run(_cenario())
    assert scan["voltas_do_loop"] > 0, "o event loop parou durante o scan — scan/diff voltou para a corrotina"


# ── D1 — o laco de run() nao pode morrer em silencio ──────────────────────────

def test_d1_ciclo_com_excecao_nao_mata_o_sync(tmp_path, caplog):
    import logging

    sm = _make_manager(tmp_path, mode="upload")
    sm.watcher = MagicMock()
    sm.queue.process_pending = AsyncMock(return_value=None)
    sm._full_sync = AsyncMock(return_value=None)

    tentativas = {"n": 0}

    async def _falha_depois_ok():
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise FileNotFoundError("temporario do QGIS sumiu entre iterdir e md5")

    sm._local_to_remote_only = _falha_depois_ok
    # `sincronizar_agora()` e o unico jeito de acordar o ciclo sem pagar a
    # espera por estabilizacao: um evento do watcher agora fica ate
    # SYNC_QUIET_PERIOD segundos aguardando a pasta parar de mudar.
    sm.sincronizar_agora()

    async def _rodar():
        with caplog.at_level(logging.ERROR, logger="executor.sync"):
            task = asyncio.create_task(sm.run())
            # 1 falha → backoff de 2s; esperamos so o suficiente para ver o log.
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(_rodar())

    assert tentativas["n"] >= 1
    assert any("Ciclo de sync" in r.message for r in caplog.records), \
        "a falha do ciclo nao gerou nenhuma linha de ERROR"


# ── B8 — contrato claims_event() ──────────────────────────────────────────────

def test_b8_claims_event_por_id_remoto(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}},
                                      "remote_id_hash": "rid-1"})
    assert sm.claims_event({"action": "file_updated",
                            "file": {"id_hash": "rid-1", "original_name": "outro-nome.geojson"}}) is True


def test_b8_claims_event_por_nome_do_objeto_remoto(tmp_path):
    """O bundle shapefile so casa pelo remote_name ('<dataset>.zip')."""
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("parcelas", {"type": "shapefile",
                                         "files": {"parcelas.shp": {}, "parcelas.dbf": {}},
                                         "remote_name": "parcelas.zip"})
    assert sm.claims_event({"action": "file_updated",
                            "file": {"id_hash": "rid-x", "original_name": "parcelas.zip"}}) is True


def test_b8_claims_event_por_nome_de_arquivo_local(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}}})
    assert sm.claims_event({"action": "file_created",
                            "file": {"id_hash": "rid-9", "original_name": "dados.geojson"}}) is True


def test_b8_claims_event_recusa_o_que_nao_e_dele(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}},
                                      "remote_id_hash": "rid-1"})
    assert sm.claims_event({"action": "file_created",
                            "file": {"id_hash": "rid-2", "original_name": "de-outra-pasta.geojson"}}) is False
    assert sm.claims_event({}) is False
    assert sm.claims_event({"file": {}}) is False


def test_b8_claims_event_nunca_levanta(tmp_path):
    """Em duvida devolve False — o fan-out entrega ao manager primario."""
    sm = _make_manager(tmp_path)
    sm.manifest.all_datasets = MagicMock(side_effect=RuntimeError("manifesto quebrado"))
    assert sm.claims_event({"file": {"id_hash": "x", "original_name": "y.geojson"}}) is False


def test_b8_claims_event_e_sincrono(tmp_path):
    sm = _make_manager(tmp_path)
    assert not asyncio.iscoroutinefunction(sm.claims_event)


# ── R1 — o push nao pode atropelar uma entrada multi-arquivo ──────────────────

def _manifesto_do_bundle(sm):
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {f"parcelas{e}": {"md5": "x"} for e in (".shp", ".dbf", ".shx")},
        "remote_id_hash": "rid-zip",
        "remote_name": "parcelas.zip",
        "remote_md5": "md5-do-zip",
        "local_md5": "a|b|c",
        "status": "synced",
        "sync_direction": "local",
    })


@pytest.mark.parametrize("nome_alheio", ["parcelas.zip", "parcelas.dbf"])
def test_r1_push_de_homonimo_nao_destroi_o_bundle(tmp_path, nome_alheio):
    """
    Outro usuario sobe pela web um 'parcelas.zip' (ou um componente solto): o
    push casava por remote_name/known_by_file, gravava um dataset de arquivo
    unico na chave do shapefile e, no ciclo seguinte, mandava DELETAR do Drive o
    arquivo do terceiro.
    """
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)
    eventos = _capturar_eventos(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-alheio", nome_alheio)))

    sm.downloader.download.assert_not_awaited()
    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_id_hash"] == "rid-zip", "o bundle foi reapontado para o objeto alheio"
    assert set(ds["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}
    assert set(sm.manifest.all_datasets()) == {"parcelas"}
    assert not (tmp_path / "parcelas.zip").exists()
    # Nem o componente local pode ter sido sobrescrito pelo arquivo do terceiro.
    assert (tmp_path / "parcelas.dbf").read_bytes() == b"\x00" * 16
    assert ("sync_error", nome_alheio) in eventos


def test_r1_push_do_proprio_bundle_so_realinha_o_md5(tmp_path):
    """Mesmo id: nada a baixar, so o MD5 do objeto remoto e atualizado."""
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)

    asyncio.run(sm._process_drive_event(
        _created_event("rid-zip", "parcelas.zip", content_md5="md5-novo")))

    sm.downloader.download.assert_not_awaited()
    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_md5"] == "md5-novo"
    assert set(ds["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}


def test_r1_bundle_destruido_faria_o_executor_apagar_o_arquivo_alheio(tmp_path, sem_validacao_espacial):
    """
    Prova do estrago que o guard evita: com o manifesto intacto, o ciclo seguinte
    nao re-envia nada nem chama delete. (Com a entrada destruida, o diff() via o
    bundle como modificado e deletava 'rid-alheio' do Drive.)
    """
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)
    # 'files' precisa bater com o disco para o diff() considerar em dia
    scan = sm.scanner.scan()
    sm.manifest.set_dataset("parcelas", {
        **sm.manifest.get_dataset("parcelas"),
        "files": {n: f.to_dict() for n, f in scan["parcelas"].files.items()},
    })

    asyncio.run(sm._process_drive_event(_created_event("rid-alheio", "parcelas.zip")))
    asyncio.run(sm._local_to_remote())

    sm.uploader.upload.assert_not_awaited()
    sm.uploader.delete.assert_not_awaited()


def test_r1_polling_ignora_componente_solto_no_drive(tmp_path):
    """O guard antigo exigia rf.original_name == remote_name; um '.dbf' escapava."""
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)
    sm.downloader.list_remote = AsyncMock(return_value=[
        _RF("rid-alheio", "parcelas.dbf", "md5-alheio", extension="dbf"),
        _RF("rid-zip", "parcelas.zip", "md5-do-zip"),  # a nossa copia continua la
    ])

    asyncio.run(sm._remote_to_local())

    sm.downloader.download.assert_not_awaited()
    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_id_hash"] == "rid-zip"
    assert set(ds["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}
    assert (tmp_path / "parcelas.dbf").read_bytes() == b"\x00" * 16


# ── R8 — o '<ds>.zip' alheio nao sequestra o remote_id_hash do bundle ─────────

def test_r8_zip_alheio_nao_sequestra_o_bundle(tmp_path):
    """
    Manifesto legado (sem remote_name) apontando para rid-A; o Drive tem um
    'parcelas.zip' alheio (rid-B, mais recente) e a nossa copia rid-A. O casamento
    por NOME tinha precedencia sobre o id e o manifesto acabava com rid-B.
    """
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {f"parcelas{e}": {"md5": "x"} for e in (".shp", ".dbf", ".shx")},
        "remote_id_hash": "rid-A",
        "remote_md5": "md5-A",
        "local_md5": "a|b|c",
        "status": "synced",
        "sync_direction": "local",
    })
    sm.downloader.list_remote = AsyncMock(return_value=[
        _RF("rid-B", "parcelas.zip", "md5-B"),  # alheio, mais recente
        _RF("rid-A", "parcelas.zip", "md5-A"),  # a nossa copia
    ])

    asyncio.run(sm._remote_to_local())

    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_id_hash"] == "rid-A", "dataset reapontado para o objeto de outro usuario"
    assert ds["remote_md5"] == "md5-A"
    sm.downloader.download.assert_not_awaited()


# ── R2 — falha na lixeira nao pode apagar a entrada do manifesto ─────────────

def _travar_lixeira(monkeypatch):
    """Simula arquivo travado (QGIS aberto no Windows): nada consegue ser movido."""
    from executor.sync import manager as manager_mod
    monkeypatch.setattr(manager_mod, "move_dataset_to_trash",
                        lambda sync_dir, ds_name, files: list(files))


def test_r2_descarte_que_falha_preserva_manifesto_e_nao_ressuscita(tmp_path, monkeypatch,
                                                                   sem_validacao_espacial):
    alvo = tmp_path / "campo.geojson"
    alvo.write_text('{"campo":1}')

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("campo", {
        "type": "geojson",
        "files": {"campo.geojson": {"md5": hashlib.md5(b'{"campo":1}').hexdigest(),
                                    "size": 11, "mtime": alvo.stat().st_mtime}},
        "remote_id_hash": "rid-1",
        "remote_name": "campo.geojson",
        "status": "synced",
        "sync_direction": "local",
    })
    _travar_lixeira(monkeypatch)

    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "campo.geojson")))

    assert alvo.exists(), "o arquivo travado sumiu"
    assert sm.manifest.get_dataset("campo") is not None, \
        "entrada removida com o arquivo ainda no disco — o proximo ciclo o re-envia"
    fila = sm.manifest.pending_items()
    assert [q["action"] for q in fila] == ["discard"]

    # E o ciclo seguinte NAO pode re-enviar o arquivo ao Drive.
    asyncio.run(sm._local_to_remote())
    sm.uploader.upload.assert_not_awaited()


def test_r2_retry_da_fila_conclui_o_descarte(tmp_path, monkeypatch):
    alvo = tmp_path / "campo.geojson"
    alvo.write_text("{}")

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("campo", {
        "type": "geojson",
        "files": {"campo.geojson": {"md5": "a"}},
        "remote_id_hash": "rid-1",
    })
    _travar_lixeira(monkeypatch)
    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "campo.geojson")))
    monkeypatch.undo()  # o QGIS fechou o arquivo

    asyncio.run(sm.queue.process_pending())

    assert not alvo.exists()
    assert sm.manifest.get_dataset("campo") is None
    assert sm.manifest.pending_items() == []
    assert len(list((tmp_path / TRASH_DIR_NAME).glob("campo_*/campo.geojson"))) == 1


def test_r2_descarte_nao_duplica_item_na_fila(tmp_path, monkeypatch):
    alvo = tmp_path / "campo.geojson"
    alvo.write_text("{}")
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("campo", {"type": "geojson",
                                      "files": {"campo.geojson": {"md5": "a"}},
                                      "remote_id_hash": "rid-1"})
    _travar_lixeira(monkeypatch)

    for _ in range(3):
        sm._discard_dataset("campo", "teste")

    assert len(sm.manifest.pending_items()) == 1


# ── R3 — o retry da fila tambem tem que deletar a copia remota antiga ────────

def test_r3_retry_deleta_a_copia_remota_antiga(tmp_path, sem_validacao_espacial):
    """
    MinIO fora do ar na 1a tentativa: o item vai para a fila e o manifesto
    preserva rid-antigo (correto). Quando o retry sobe rid-novo, rid-antigo tem
    que sair do bucket — senao volta depois como "arquivo novo" com o mesmo
    original_name e ressuscita conteudo obsoleto.
    """
    from executor.sync.uploader import UploadResult

    (tmp_path / "dados.geojson").write_text('{"a":2}')
    sm = _make_manager(tmp_path, mode="upload")
    sm.manifest.set_dataset("dados", {
        "type": "geojson",
        "files": {"dados.geojson": {"md5": "hash-antigo"}},
        "remote_id_hash": "rid-antigo",
        "remote_name": "dados.geojson",
        "status": "synced",
        "sync_direction": "local",
    })

    sm.uploader.upload = AsyncMock(return_value=None)  # 1a tentativa falha
    asyncio.run(sm._local_to_remote())

    assert [q["action"] for q in sm.manifest.pending_items()] == ["upload"]
    assert sm.manifest.get_dataset("dados")["remote_id_hash"] == "rid-antigo"
    sm.uploader.delete.assert_not_awaited()

    sm.uploader.upload = AsyncMock(
        return_value=UploadResult(id_hash="rid-novo", remote_name="dados.geojson", remote_md5="m")
    )
    asyncio.run(sm.queue.process_pending())

    assert sm.manifest.get_dataset("dados")["remote_id_hash"] == "rid-novo"
    sm.uploader.delete.assert_awaited_once_with("rid-antigo")
    assert sm.manifest.pending_items() == []


# ── R5 — a lixeira preserva o bundle inteiro num descarte so ─────────────────

def test_r5_shapefile_vai_inteiro_para_a_mesma_pasta_da_lixeira(tmp_path):
    """Um shapefile so abre se .shp/.dbf/.shx compartilham o mesmo stem."""
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("parcelas", {
        "type": "shapefile",
        "files": {f"parcelas{e}": {"md5": "x"} for e in (".shp", ".dbf", ".shx")},
        "remote_id_hash": "rid-zip",
    })

    assert sm._discard_dataset("parcelas", "teste") is True

    pastas = list((tmp_path / TRASH_DIR_NAME).iterdir())
    assert len(pastas) == 1 and pastas[0].is_dir()
    assert sorted(p.name for p in pastas[0].iterdir()) == \
        ["parcelas.dbf", "parcelas.shp", "parcelas.shx"]


def test_r5_dois_descartes_do_mesmo_dataset_nao_se_misturam(tmp_path):
    _shapefile(tmp_path)
    assert move_dataset_to_trash(tmp_path, "parcelas",
                                 list(tmp_path.glob("parcelas.*"))) == []
    _shapefile(tmp_path)
    assert move_dataset_to_trash(tmp_path, "parcelas",
                                 list(tmp_path.glob("parcelas.*"))) == []

    pastas = sorted((tmp_path / TRASH_DIR_NAME).iterdir())
    assert len(pastas) == 2
    for pasta in pastas:
        assert sorted(p.suffix for p in pasta.iterdir()) == [".dbf", ".shp", ".shx"]


# ── R6 — expurgo da lixeira ──────────────────────────────────────────────────

def test_r6_purge_remove_descartes_antigos_e_mede_o_resto(tmp_path):
    trash = tmp_path / TRASH_DIR_NAME
    velho = trash / "parcelas_20260101T000000"
    velho.mkdir(parents=True)
    (velho / "parcelas.shp").write_bytes(b"0" * 100)
    antigo_ts = time.time() - 30 * 86400
    os.utime(velho, (antigo_ts, antigo_ts))

    novo = trash / "campo_20260801T000000"
    novo.mkdir()
    (novo / "campo.geojson").write_bytes(b"0" * 50)

    removidos, restantes = purge_trash(tmp_path, max_age_days=14)

    assert removidos == 1
    assert not velho.exists() and novo.exists()
    assert restantes == 50


def test_r6_manager_expurga_a_lixeira_no_ciclo(tmp_path):
    trash = tmp_path / TRASH_DIR_NAME
    velho = trash / "parcelas_20260101T000000"
    velho.mkdir(parents=True)
    (velho / "parcelas.shp").write_bytes(b"0" * 10)
    antigo_ts = time.time() - 60 * 86400
    os.utime(velho, (antigo_ts, antigo_ts))

    sm = _make_manager(tmp_path, mode="bidirectional")
    asyncio.run(sm._maybe_purge_trash())
    assert not velho.exists()

    # Segunda chamada no mesmo ciclo nao varre de novo (I/O em vao a cada 30s).
    novo = trash / "campo_20260801T000000"
    novo.mkdir()
    os.utime(novo, (antigo_ts, antigo_ts))
    asyncio.run(sm._maybe_purge_trash())
    assert novo.exists()


# ── R7 — o push tambem respeita a politica de conflito ───────────────────────

def _manager_com_conflito(tmp_path, monkeypatch, estrategia):
    from executor import config as agent_config

    monkeypatch.setattr(agent_config, "SYNC_CONFLICT_STRATEGY", estrategia)
    alvo = tmp_path / "levantamento.geojson"
    alvo.write_text('{"campo":1}')  # ja EDITADO offline pelo tecnico

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("levantamento", {
        "type": "geojson",
        "files": {"levantamento.geojson": {"md5": "md5-do-download"}},
        "remote_id_hash": "rid-1",
        "remote_name": "levantamento.geojson",
        "remote_md5": "md5-remoto-antigo",
        "local_md5": "md5-do-download",  # != MD5 atual do disco
        "status": "synced",
        "sync_direction": "remote",
    })

    async def _baixa(rid, dest):
        dest.write_text('{"remoto":1}')
        return True

    sm.downloader.download = AsyncMock(side_effect=_baixa)
    return sm, alvo


def test_r7_push_com_keep_both_preserva_a_edicao_de_campo(tmp_path, monkeypatch):
    sm, alvo = _manager_com_conflito(tmp_path, monkeypatch, "keep-both")
    eventos = _capturar_eventos(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    backups = list(tmp_path.glob("levantamento_local_*.geojson"))
    assert len(backups) == 1, "trabalho de campo sobrescrito sem backup"
    assert backups[0].read_text() == '{"campo":1}'
    assert alvo.read_text() == '{"remoto":1}'
    assert ("conflict_detected", "levantamento") in eventos


def test_r7_push_com_local_wins_nao_baixa(tmp_path, monkeypatch):
    sm, alvo = _manager_com_conflito(tmp_path, monkeypatch, "local-wins")
    eventos = _capturar_eventos(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    assert alvo.read_text() == '{"campo":1}'
    sm.downloader.download.assert_not_awaited()
    assert ("conflict_detected", "levantamento") in eventos


def test_r7_push_sem_edicao_local_baixa_sem_conflito(tmp_path, monkeypatch):
    """Sem divergencia local nao ha conflito — o push normal nao pode regredir."""
    from executor import config as agent_config

    monkeypatch.setattr(agent_config, "SYNC_CONFLICT_STRATEGY", "keep-both")
    alvo = tmp_path / "levantamento.geojson"
    alvo.write_text('{"campo":1}')

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("levantamento", {
        "type": "geojson",
        "files": {"levantamento.geojson": {"md5": "x"}},
        "remote_id_hash": "rid-1",
        "remote_name": "levantamento.geojson",
        "local_md5": hashlib.md5(b'{"campo":1}').hexdigest(),  # disco bate com o manifesto
        "sync_direction": "remote",
    })
    eventos = _capturar_eventos(sm)

    async def _baixa(rid, dest):
        dest.write_text('{"remoto":1}')
        return True

    sm.downloader.download = AsyncMock(side_effect=_baixa)
    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    assert alvo.read_text() == '{"remoto":1}'
    assert list(tmp_path.glob("levantamento_local_*.geojson")) == []
    assert ("conflict_detected", "levantamento") not in eventos


# ── R9 — o watcher acorda o sync de verdade ──────────────────────────────────

def test_r9_evento_do_watchdog_acorda_o_sync_a_partir_de_outra_thread(tmp_path):
    """
    `_change_flag` e um asyncio.Event: seta-lo direto da thread do watchdog nao e
    thread-safe. Exercita a cadeia real _SyncEventHandler → FileWatcher._handle_event
    → SyncManager._on_change → _change_flag, com o handler rodando fora do loop.
    """
    from executor.sync.watcher import _SyncEventHandler

    sm = _make_manager(tmp_path, mode="upload")
    evento = type("_Ev", (), {"is_directory": False,
                              "src_path": str(tmp_path / "novo.geojson")})()

    async def _cenario():
        sm._loop = asyncio.get_running_loop()
        handler = _SyncEventHandler(sm.watcher._handle_event)
        assert not sm._change_flag.is_set()
        await asyncio.to_thread(handler.on_created, evento)
        await asyncio.wait_for(sm._change_flag.wait(), timeout=2)
        return sm._change_flag.is_set()

    assert asyncio.run(_cenario())


def test_r9_watcher_real_acorda_o_sync(tmp_path):
    """Integracao com o watchdog de verdade: criar um arquivo dispara o ciclo."""
    sm = _make_manager(tmp_path, mode="upload")

    async def _cenario():
        sm._loop = asyncio.get_running_loop()
        sm.watcher.start()
        try:
            await asyncio.to_thread((tmp_path / "novo.geojson").write_text, "{}")
            await asyncio.wait_for(sm._change_flag.wait(), timeout=15)
        finally:
            await asyncio.to_thread(sm.watcher.stop)

    asyncio.run(_cenario())
    assert sm._change_flag.is_set()


def test_r9_evento_na_lixeira_nao_acorda_o_sync(tmp_path):
    """Agora que on_change existe, o filtro da lixeira deixa de ser decorativo."""
    from executor.sync.watcher import _SyncEventHandler

    sm = _make_manager(tmp_path, mode="upload")
    descarte = tmp_path / TRASH_DIR_NAME / "dados_20260101T000000" / "dados.geojson"
    evento = type("_Ev", (), {"is_directory": False, "src_path": str(descarte)})()

    async def _cenario():
        sm._loop = asyncio.get_running_loop()
        handler = _SyncEventHandler(sm.watcher._handle_event)
        await asyncio.to_thread(handler.on_created, evento)
        await asyncio.sleep(0)
        return sm._change_flag.is_set()

    assert asyncio.run(_cenario()) is False


# ── P5 — o GeoSync parou de comer a maquina sem estar fazendo nada ───────────
#
# Os achados de desempenho do subsistema de sync:
#   P5.1 — diff() rehasheava a pasta inteira a cada 30s, ignorando (size, mtime)
#   P5.2 — o ciclo acordado pelo watcher nao tinha piso de intervalo
#   P5.3 — cada mutacao do manifesto reserializava o JSON inteiro em disco
#   P5.4 — a fila dormia ate 300s DENTRO do ciclo, congelando a pasta
#   P5.5 — uploads e downloads eram estritamente serializados

def _semear_manifesto_do_disco(sm):
    """Grava no manifesto o estado atual da pasta, como um ciclo bem-sucedido."""
    for nome, ds in sm.scanner.scan().items():
        sm.manifest.set_dataset(nome, {
            "type": ds.type,
            "files": {f: i.to_dict() for f, i in ds.files.items()},
            "status": "synced",
            "remote_id_hash": f"rid-{nome}",
            "sync_direction": "local",
        })


def test_p5_diff_nao_rehasheia_quando_size_e_mtime_batem(tmp_path, monkeypatch):
    """Com o disco intocado, um ciclo nao pode abrir nenhum arquivo."""
    from executor.sync import scanner as scanner_mod

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text('{"a":%d}' % i)
    _semear_manifesto_do_disco(sm)

    leituras = {"n": 0}
    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (leituras.__setitem__("n", leituras["n"] + 1), real(p))[1])

    atual = sm.scanner.scan()
    novos, modificados, removidos = sm.scanner.diff(atual, sm.manifest.all_datasets())

    assert (novos, modificados, removidos) == ([], [], [])
    assert leituras["n"] == 0, "o diff releu o disco mesmo com (size, mtime) inalterados"


def test_p5_diff_ainda_pega_edicao_de_verdade(tmp_path):
    """O atalho nao pode esconder mudanca real — o mtime muda na edicao."""
    sm = _make_manager(tmp_path, mode="upload")
    alvo = tmp_path / "campo.geojson"
    alvo.write_text('{"a":1}')
    _semear_manifesto_do_disco(sm)

    alvo.write_text('{"a":2, "b":3}')
    futuro = time.time() + 5
    os.utime(alvo, (futuro, futuro))

    _, modificados, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets())
    assert modificados == ["campo"]


def test_p5_varredura_completa_pega_reescrita_com_mtime_preservado(tmp_path):
    """Rede de seguranca do atalho: `force_hash` reencontra o que ele deixaria passar."""
    sm = _make_manager(tmp_path, mode="upload")
    alvo = tmp_path / "campo.geojson"
    alvo.write_text('{"a":1}')
    _semear_manifesto_do_disco(sm)

    st = alvo.stat()
    alvo.write_text('{"b":2}')  # mesmo tamanho, mtime restaurado
    os.utime(alvo, (st.st_atime, st.st_mtime))

    _, sem_hash, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets())
    _, com_hash, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets(),
                                     force_hash=True)
    assert sem_hash == []
    assert com_hash == ["campo"]


def test_p5_manifesto_grava_uma_vez_por_lote(tmp_path, sem_validacao_espacial):
    """Eram TRES reserializacoes do JSON inteiro por dataset enviado — O(N²)."""
    from executor.sync.uploader import UploadResult

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(10):
        (tmp_path / f"d{i}.geojson").write_text("{}")
    sm.uploader.upload = AsyncMock(
        return_value=UploadResult(id_hash="rid", remote_name="x", remote_md5="m")
    )

    gravacoes = {"n": 0}
    real = sm.manifest._escrever
    sm.manifest._escrever = lambda c: (gravacoes.__setitem__("n", gravacoes["n"] + 1), real(c))[1]

    asyncio.run(sm._local_to_remote())

    assert gravacoes["n"] <= 2, f"{gravacoes['n']} gravacoes para 10 datasets"
    assert sm.manifest.get_dataset("d3")["status"] == "synced"


def test_p5_manifesto_grava_de_forma_atomica(tmp_path):
    """Um crash no meio do json.dump deixava o manifesto truncado."""
    from executor.sync.manifest import SyncManifest

    m = SyncManifest(str(tmp_path), "ws-1", "ag-1")
    m.set_dataset("d", {"type": "geojson"})
    asyncio.run(m.flush())

    import json
    assert json.loads(m.path.read_text(encoding="utf-8"))["datasets"]["d"]["type"] == "geojson"
    assert not (tmp_path / ".atlans-sync.json.tmp").exists()


def test_p5_fila_agenda_o_retry_em_vez_de_dormir(tmp_path):
    """Um `asyncio.sleep(backoff)` aqui congelava a PASTA, nao so o item."""
    from executor.sync.manifest import SyncManifest
    from executor.sync.queue import SyncQueue

    m = SyncManifest(str(tmp_path), "ws-1", "ag-1")
    m.enqueue("upload", "ds1")
    m._data["pending_queue"][0]["retries"] = 8  # backoff de 256s

    async def _falha(item):
        return False

    inicio = time.monotonic()
    asyncio.run(SyncQueue(m, _falha).process_pending())
    assert time.monotonic() - inicio < 1.0, "a fila dormiu dentro do ciclo"
    assert m.pending_items()[0]["next_attempt_at"] > time.time()

    # Segunda passada: o item ainda nao venceu, entao nem e tentado.
    tentativas = {"n": 0}

    async def _conta(item):
        tentativas["n"] += 1
        return True

    asyncio.run(SyncQueue(m, _conta).process_pending())
    assert tentativas["n"] == 0


def test_p5_uploads_acontecem_em_paralelo(tmp_path, sem_validacao_espacial):
    """Serializados, 200 arquivos pequenos passavam o tempo esperando round-trip."""
    from executor.sync.uploader import UploadResult

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(6):
        (tmp_path / f"d{i}.geojson").write_text("{}")

    simultaneos = {"agora": 0, "pico": 0}

    async def _upload_lento(ds, meta=None):
        simultaneos["agora"] += 1
        simultaneos["pico"] = max(simultaneos["pico"], simultaneos["agora"])
        await asyncio.sleep(0.05)
        simultaneos["agora"] -= 1
        return UploadResult(id_hash="rid", remote_name=ds.name, remote_md5="m")

    sm.uploader.upload = _upload_lento
    asyncio.run(sm._local_to_remote())

    assert simultaneos["pico"] > 1, "os uploads continuam estritamente em serie"


def test_p5_comando_da_ui_fura_a_espera_por_estabilizacao(tmp_path):
    """O piso entre ciclos contem a rajada do watchdog, nao o clique do usuario."""
    sm = _make_manager(tmp_path, mode="upload")

    async def _cenario():
        sm._loop = asyncio.get_running_loop()
        sm._ultimo_ciclo = sm._loop.time()  # ciclo recem-terminado: piso em vigor
        sm.sincronizar_agora()
        inicio = sm._loop.time()
        await sm._esperar_pasta_estabilizar()
        return sm._loop.time() - inicio

    assert asyncio.run(_cenario()) < 0.5


def test_p5_claims_event_nao_varre_o_manifesto(tmp_path):
    """O roteamento do push virou lookup O(1) nos indices do manifesto."""
    sm = _make_manager(tmp_path)
    for i in range(50):
        sm.manifest.set_dataset(f"d{i}", {"type": "geojson",
                                          "files": {f"d{i}.geojson": {}},
                                          "remote_id_hash": f"rid-{i}"})
    sm.manifest.remove_dataset("d7")

    assert sm.claims_event({"file": {"id_hash": "rid-49", "original_name": "x.geojson"}}) is True
    assert sm.claims_event({"file": {"id_hash": "", "original_name": "d3.geojson"}}) is True
    # Removido do manifesto tem de sair do indice junto.
    assert sm.claims_event({"file": {"id_hash": "rid-7", "original_name": "d7.geojson"}}) is False
