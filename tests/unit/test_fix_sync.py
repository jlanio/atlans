"""
GeoSync regressions (executor/sync/**).

Covers the findings of the executor subsystem audit:
  B5  — file_deleted deleted the local file even in SYNC_MODE=upload
  B6  — the remote delete happened BEFORE the upload and the manifest lost remote_id_hash
  B10 — the shapefile's '<dataset>.zip' never matched in the manifest and collided on key
  S4  — scanner/uploader followed symlinks (leak of files from outside the folder)
  P4  — heavy synchronous I/O inside the event loop
  D1  — the SyncManager.run() loop died silently
  B8  — claims_event() contract for the drive_events fan-out

And the findings of the adversarial review of the fixes THEMSELVES:
  R1  — the push wrote a single-file dataset over the shapefile bundle
  R2  — a failure to move to the trash deleted the manifest entry anyway
  R3  — the retry through SyncQueue never deleted the old remote copy
  R5  — the trash broke the shapefile stem (one timestamp per file)
  R6  — the trash grew without purging inside the technician's folder
  R7  — the push had no conflict check at all
  R8  — someone else's '<ds>.zip' hijacked the bundle's remote_id_hash
  R9  — the watcher never called on_change: sync only woke up on the 30s tick
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
def without_spatial_validation(monkeypatch):
    """
    Neutralizes validator/metadata: the fixtures write fake bytes and the goal
    of these tests is the ORDER of the sync operations, not reading via GDAL.
    """
    from executor.sync import manager as manager_mod
    from executor.sync.validator import ValidationResult

    monkeypatch.setattr(manager_mod, "validate_dataset", lambda ds: ValidationResult(True))
    monkeypatch.setattr(manager_mod, "extract_metadata", lambda path, tipo: {})


def _make_manager(tmp_path: Path, mode: str = "upload"):
    """Real SyncManager with uploader/downloader/trigger replaced by mocks."""
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
    assert manager_mod  # silences linters about an unused import
    return sm


def _deleted_event(id_hash: str, name: str) -> dict:
    return {"action": "file_deleted", "file": {"id_hash": id_hash, "original_name": name}}


def _created_event(id_hash: str, name: str, content_md5: str = "md5-remoto") -> dict:
    return {"action": "file_created",
            "file": {"id_hash": id_hash, "original_name": name,
                     "content_md5": content_md5, "size": 4}}


def _capture_events(sm) -> list[tuple[str, str]]:
    """Replaces the emitter with a collector — the test SyncManager has no queue."""
    eventos: list[tuple[str, str]] = []
    sm.events.emit = lambda event, dataset="", **kw: eventos.append((event, dataset))
    return eventos


# ── B5 — mode gate on drive_event ─────────────────────────────────────────────

def test_b5_file_deleted_deletes_nothing_in_upload_mode(tmp_path):
    """SYNC_MODE=upload (the default) must not consume deletions coming from the Drive."""
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
def test_b5_file_deleted_moves_to_trash_and_does_not_unlink(tmp_path, modo):
    """In the modes that consume the Drive, the file goes to .atlans-trash/."""
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


def test_b5_trash_neither_collides_nor_overwrites(tmp_path):
    """Two discards of the same dataset produce two distinct folders in the trash."""
    for conteudo in (b"primeiro", b"segundo"):
        f = tmp_path / "dados.geojson"
        f.write_bytes(conteudo)
        assert move_dataset_to_trash(tmp_path, "dados", [f]) == []

    guardados = sorted(p.read_bytes()
                       for p in (tmp_path / TRASH_DIR_NAME).glob("*/dados.geojson"))
    assert guardados == [b"primeiro", b"segundo"]


def test_b5_trash_is_invisible_to_the_scanner(tmp_path):
    """Senao a lixeira vira loop de reupload."""
    from executor.sync.scanner import DatasetScanner

    (tmp_path / "ativo.geojson").write_text("{}")
    f = tmp_path / "descartado.geojson"
    f.write_text("{}")
    move_dataset_to_trash(tmp_path, "descartado", [f])

    datasets = DatasetScanner(str(tmp_path)).scan()
    assert set(datasets) == {"ativo"}


def test_b5_watcher_ignores_events_inside_the_trash(tmp_path):
    from executor.sync.watcher import _SyncEventHandler

    h = _SyncEventHandler(lambda *_: None)
    assert h._should_process(str(tmp_path / "dados.geojson")) is True
    assert h._should_process(str(tmp_path / TRASH_DIR_NAME / "dados_20260101T000000.geojson")) is False


# ── B6 — upload before delete + manifest merge ────────────────────────────────

def test_b6_upload_happens_before_deleting_the_old_copy(tmp_path, without_spatial_validation):
    """A crash between DELETE and PUT made the file vanish from the Drive forever."""
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


def test_b6_delete_does_not_run_if_upload_fails(tmp_path, without_spatial_validation):
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
    # The old remote copy is still referenced — it can still be recovered.
    assert sm.manifest.get_dataset("dados")["remote_id_hash"] == "rid-antigo"


def test_b6_uploading_state_preserves_remote_id_hash_and_files(tmp_path, without_spatial_validation):
    """If the process dies mid-upload, the manifest must remain useful."""
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

    async def _fail_on_put(*_a, **_k):
        visto.update(sm.manifest.get_dataset("dados"))
        return None

    sm.uploader.upload = AsyncMock(side_effect=_fail_on_put)
    scan = asyncio.run(asyncio.to_thread(sm.scanner.scan))
    asyncio.run(sm._upload_dataset("dados", scan["dados"]))

    assert visto["status"] == "uploading"
    assert visto["remote_id_hash"] == "rid-antigo", "perdeu o id remoto durante o upload"
    # 'files' must NOT have been updated: diff() would conclude "up to date" and the
    # file would never be uploaded again.
    assert visto["files"]["dados.geojson"]["md5"] == "hash-antigo"


# ── B10 — remote_name do bundle shapefile ─────────────────────────────────────

def _shapefile(tmp_path: Path, stem: str = "parcelas"):
    for ext in (".shp", ".dbf", ".shx"):
        (tmp_path / f"{stem}{ext}").write_bytes(b"\x00" * 16)


class _RF:
    """RemoteFileInfo stub."""

    def __init__(self, id_hash, original_name, content_md5, extension="zip", size=10):
        self.id_hash = id_hash
        self.original_name = original_name
        self.content_md5 = content_md5
        self.extension = extension
        self.size = size
        self.created_at = None
        self.updated_at = None


def test_b10_shapefile_upload_stores_zip_remote_name(tmp_path, without_spatial_validation):
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


def test_b10_bundle_zip_is_not_downgraded_nor_key_collides(tmp_path):
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


def test_b10_bundle_remote_md5_is_realigned_without_download(tmp_path):
    """An old-version manifest stored 'a|b|c' as remote_md5 — just fix it."""
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


def test_b10_new_remote_file_key_does_not_clobber_the_bundle(tmp_path):
    from executor.sync.manager import _new_remote_ds_key

    existentes = {"parcelas": {"type": "shapefile"}}
    assert _new_remote_ds_key("municipios.geojson", existentes) == "municipios"
    assert _new_remote_ds_key("parcelas.zip", existentes) == "parcelas.zip"
    assert _new_remote_ds_key("SEM_EXTENSAO", existentes) == "sem_extensao"


# ── S4 — symlink containment on upload ────────────────────────────────────────

def _symlink_ou_skip(link: Path, alvo: Path):
    try:
        link.symlink_to(alvo)
    except (OSError, NotImplementedError):
        pytest.skip("symlink indisponivel neste ambiente")


def test_s4_scanner_pula_symlinks(tmp_path):
    from executor.sync.scanner import DatasetScanner

    segredo = tmp_path.parent / "client.key"
    # Test bait, not a key: the empty header is enough for the scenario (the
    # scanner must not follow the symlink out of the sync folder).
    segredo.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    sync = tmp_path / "gis"
    sync.mkdir()
    (sync / "real.csv").write_text("a,b\n1,2\n")
    _symlink_ou_skip(sync / "pontos.csv", segredo)

    datasets = DatasetScanner(str(sync)).scan()
    assert set(datasets) == {"real"}, "symlink para fora da pasta entrou no sync"


def test_s4_uploader_refuses_component_outside_the_folder(tmp_path):
    """TOCTOU: between the scan and the upload the component may become a symlink."""
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


def test_s4_uploader_refuses_single_file_outside_the_folder(tmp_path):
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


def test_s4_uploader_refuses_outside_component_without_needing_symlink(tmp_path):
    """Same containment as the symlink case, exercised where symlinks are not available."""
    from executor.sync.scanner import Dataset, FileInfo
    from executor.sync.uploader import DriveUploader

    sync = tmp_path / "gis"
    sync.mkdir()
    fora = tmp_path / "client.key"
    fora.write_text("-----BEGIN PRIVATE KEY-----")  # pragma: allowlist secret
    (sync / "parcelas.shp").write_bytes(b"\x00" * 8)

    ds = Dataset("parcelas", "shapefile")
    ds.add_file(FileInfo(sync / "parcelas.shp"))
    ds.add_file(FileInfo(fora))  # component resolved outside the sync folder

    up = DriveUploader(LOCAL_URL, "ag-1", "ws-1", str(sync))
    up._upload_file = AsyncMock(return_value="NAO DEVERIA SUBIR")

    assert asyncio.run(up.upload(ds)) is None
    up._upload_file.assert_not_awaited()


def test_s4_is_inside_accepts_legitimate_file(tmp_path):
    f = tmp_path / "ok.geojson"
    f.write_text("{}")
    assert is_inside(tmp_path, f) is True
    assert is_inside(tmp_path, tmp_path / "inexistente.geojson") is False


# ── P4 — no heavy synchronous I/O on the event loop ───────────────────────────

def test_p4_remote_to_local_scans_only_once(tmp_path):
    """scan() per remote file was O(n x bytes) inside the coroutine."""
    sm = _make_manager(tmp_path, mode="bidirectional")
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text("{}")

    chamadas = {"n": 0}
    real_scan = sm.scanner.scan

    def _counting():
        chamadas["n"] += 1
        return real_scan()

    sm.scanner.scan = _counting
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


def test_p4_upload_streams_and_hashes_the_content(tmp_path):
    """No f.read() of the whole file; the MD5 must be that of the uploaded object."""
    from executor.sync.uploader import _aiter_file, _file_md5

    conteudo = b"raster-grande" * 100_000
    alvo = tmp_path / "grande.tif"
    alvo.write_bytes(conteudo)

    assert _file_md5(alvo) == hashlib.md5(conteudo).hexdigest()

    async def _collect():
        pedacos = [c async for c in _aiter_file(alvo)]
        return pedacos

    pedacos = asyncio.run(_collect())
    assert b"".join(pedacos) == conteudo
    assert len(pedacos) > 1, "arquivo grande foi entregue num unico buffer"


def test_p4_local_to_remote_does_not_block_the_event_loop(tmp_path, without_spatial_validation):
    """
    The 30s application heartbeat is the only keepalive (ping_interval=None): if the
    scan/diff goes back inside the coroutine, the connection drops with 4408 and the
    run in progress dies.

    We call `_local_to_remote` FOR REAL (the previous version of this test
    exercised the stdlib's `asyncio.to_thread` and would pass even with the bug) and
    count the event loop's turns while the — deliberately slow — scan
    is running. With the scan inside the coroutine, the loop stays stopped for the whole
    window and the count comes out zero.

    A count of turns, and not the LONGEST interval between two of them: the interval
    measures the runner along with the code. A process pause (garbage collection with
    the whole suite loaded, CPU stolen from the VM) reached 0.32 s in CI with the scan
    in the thread, and the limit was 0.3 s. A pause only shortens the window: the loop
    spins again before the scan finishes.
    """
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text('{"a":1}')

    sm = _make_manager(tmp_path, mode="upload")
    sm.uploader.upload = AsyncMock(return_value=None)

    scan_real = sm.scanner.scan
    scan = {"rodando": False, "voltas_do_loop": 0}

    def _slow_scan():
        scan["rodando"] = True
        try:
            time.sleep(0.5)  # Real I/O of a large folder: stat + MD5 of everything
        finally:
            scan["rodando"] = False
        return scan_real()

    sm.scanner.scan = _slow_scan

    async def _scenario():
        async def _heartbeat():
            while True:
                await asyncio.sleep(0)
                if scan["rodando"]:
                    scan["voltas_do_loop"] += 1

        hb = asyncio.create_task(_heartbeat())
        await asyncio.sleep(0)
        await sm._local_to_remote()
        hb.cancel()

    asyncio.run(_scenario())
    assert scan["voltas_do_loop"] > 0, "o event loop parou durante o scan — scan/diff voltou para a corrotina"


# ── D1 — the run() loop must not die silently ─────────────────────────────────

def test_d1_cycle_with_exception_does_not_kill_the_sync(tmp_path, caplog):
    import logging

    sm = _make_manager(tmp_path, mode="upload")
    sm.watcher = MagicMock()
    sm.queue.process_pending = AsyncMock(return_value=None)
    sm._full_sync = AsyncMock(return_value=None)

    tentativas = {"n": 0}

    async def _fail_then_ok():
        tentativas["n"] += 1
        if tentativas["n"] == 1:
            raise FileNotFoundError("temporario do QGIS sumiu entre iterdir e md5")

    sm._local_to_remote_only = _fail_then_ok
    # `sync_now()` is the only way to wake the cycle without paying for the
    # stabilization wait: a watcher event now waits up to
    # SYNC_QUIET_PERIOD seconds for the folder to stop changing.
    sm.sync_now()

    async def _run():
        with caplog.at_level(logging.ERROR, logger="executor.sync"):
            task = asyncio.create_task(sm.run())
            # 1 failure → 2s backoff; we wait just long enough to see the log.
            await asyncio.sleep(0.2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())

    assert tentativas["n"] >= 1
    assert any("Ciclo de sync" in r.message for r in caplog.records), \
        "a falha do ciclo nao gerou nenhuma linha de ERROR"


# ── B8 — contrato claims_event() ──────────────────────────────────────────────

def test_b8_claims_event_by_remote_id(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}},
                                      "remote_id_hash": "rid-1"})
    assert sm.claims_event({"action": "file_updated",
                            "file": {"id_hash": "rid-1", "original_name": "outro-nome.geojson"}}) is True


def test_b8_claims_event_by_remote_object_name(tmp_path):
    """O bundle shapefile so casa pelo remote_name ('<dataset>.zip')."""
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("parcelas", {"type": "shapefile",
                                         "files": {"parcelas.shp": {}, "parcelas.dbf": {}},
                                         "remote_name": "parcelas.zip"})
    assert sm.claims_event({"action": "file_updated",
                            "file": {"id_hash": "rid-x", "original_name": "parcelas.zip"}}) is True


def test_b8_claims_event_by_local_file_name(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}}})
    assert sm.claims_event({"action": "file_created",
                            "file": {"id_hash": "rid-9", "original_name": "dados.geojson"}}) is True


def test_b8_claims_event_refuses_what_is_not_its_own(tmp_path):
    sm = _make_manager(tmp_path)
    sm.manifest.set_dataset("dados", {"type": "geojson", "files": {"dados.geojson": {}},
                                      "remote_id_hash": "rid-1"})
    assert sm.claims_event({"action": "file_created",
                            "file": {"id_hash": "rid-2", "original_name": "de-outra-pasta.geojson"}}) is False
    assert sm.claims_event({}) is False
    assert sm.claims_event({"file": {}}) is False


def test_b8_claims_event_never_raises(tmp_path):
    """Em duvida devolve False — o fan-out entrega ao manager primaryContent."""
    sm = _make_manager(tmp_path)
    sm.manifest.all_datasets = MagicMock(side_effect=RuntimeError("manifesto quebrado"))
    assert sm.claims_event({"file": {"id_hash": "x", "original_name": "y.geojson"}}) is False


def test_b8_claims_event_is_synchronous(tmp_path):
    sm = _make_manager(tmp_path)
    assert not asyncio.iscoroutinefunction(sm.claims_event)


# ── R1 — the push must not trample a multi-file entry ─────────────────────────

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
def test_r1_push_of_namesake_does_not_destroy_the_bundle(tmp_path, nome_alheio):
    """
    Another user uploads a 'parcelas.zip' (or a loose component) via the web: the
    push matched by remote_name/known_by_file, wrote a single-file dataset
    under the shapefile's key and, on the next cycle, ordered the third party's
    file DELETED from the Drive.
    """
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)
    eventos = _capture_events(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-alheio", nome_alheio)))

    sm.downloader.download.assert_not_awaited()
    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_id_hash"] == "rid-zip", "o bundle foi reapontado para o objeto alheio"
    assert set(ds["files"]) == {"parcelas.shp", "parcelas.dbf", "parcelas.shx"}
    assert set(sm.manifest.all_datasets()) == {"parcelas"}
    assert not (tmp_path / "parcelas.zip").exists()
    # Not even the local component may have been overwritten by the third party's file.
    assert (tmp_path / "parcelas.dbf").read_bytes() == b"\x00" * 16
    assert ("sync_error", nome_alheio) in eventos


def test_r1_push_of_own_bundle_only_realigns_the_md5(tmp_path):
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


def test_r1_destroyed_bundle_would_make_executor_delete_foreign_file(tmp_path, without_spatial_validation):
    """
    Proof of the damage the guard prevents: with the manifest intact, the next cycle
    re-sends nothing and does not call delete. (With the entry destroyed, diff() saw the
    bundle as modified and deleted 'rid-alheio' from the Drive.)
    """
    _shapefile(tmp_path)
    sm = _make_manager(tmp_path, mode="bidirectional")
    _manifesto_do_bundle(sm)
    # 'files' must match the disk for diff() to consider it up to date
    scan = sm.scanner.scan()
    sm.manifest.set_dataset("parcelas", {
        **sm.manifest.get_dataset("parcelas"),
        "files": {n: f.to_dict() for n, f in scan["parcelas"].files.items()},
    })

    asyncio.run(sm._process_drive_event(_created_event("rid-alheio", "parcelas.zip")))
    asyncio.run(sm._local_to_remote())

    sm.uploader.upload.assert_not_awaited()
    sm.uploader.delete.assert_not_awaited()


def test_r1_polling_ignores_loose_component_on_drive(tmp_path):
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


# ── R8 — someone else's '<ds>.zip' does not hijack the bundle's remote_id_hash ─

def test_r8_foreign_zip_does_not_hijack_the_bundle(tmp_path):
    """
    Legacy manifest (no remote_name) pointing to rid-A; the Drive has someone else's
    'parcelas.zip' (rid-B, more recent) and our copy rid-A. Matching
    by NAME took precedence over the id and the manifest ended up with rid-B.
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
        _RF("rid-B", "parcelas.zip", "md5-B"),  # someone else's, more recent
        _RF("rid-A", "parcelas.zip", "md5-A"),  # a nossa copia
    ])

    asyncio.run(sm._remote_to_local())

    ds = sm.manifest.get_dataset("parcelas")
    assert ds["remote_id_hash"] == "rid-A", "dataset reapontado para o objeto de outro usuario"
    assert ds["remote_md5"] == "md5-A"
    sm.downloader.download.assert_not_awaited()


# ── R2 — a trash failure must not delete the manifest entry ──────────────────

def _lock_trash(monkeypatch):
    """Simulates a locked file (QGIS open on Windows): nothing can be moved."""
    from executor.sync import manager as manager_mod
    monkeypatch.setattr(manager_mod, "move_dataset_to_trash",
                        lambda sync_dir, ds_name, files: list(files))


def test_r2_failed_discard_preserves_manifest_and_does_not_resurrect(tmp_path, monkeypatch,
                                                                   without_spatial_validation):
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
    _lock_trash(monkeypatch)

    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "campo.geojson")))

    assert alvo.exists(), "o arquivo travado sumiu"
    assert sm.manifest.get_dataset("campo") is not None, \
        "entrada removida com o arquivo ainda no disco — o proximo ciclo o re-envia"
    fila = sm.manifest.pending_items()
    assert [q["action"] for q in fila] == ["discard"]

    # And the next cycle must NOT re-send the file to the Drive.
    asyncio.run(sm._local_to_remote())
    sm.uploader.upload.assert_not_awaited()


def test_r2_queue_retry_completes_the_discard(tmp_path, monkeypatch):
    alvo = tmp_path / "campo.geojson"
    alvo.write_text("{}")

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("campo", {
        "type": "geojson",
        "files": {"campo.geojson": {"md5": "a"}},
        "remote_id_hash": "rid-1",
    })
    _lock_trash(monkeypatch)
    asyncio.run(sm._process_drive_event(_deleted_event("rid-1", "campo.geojson")))
    monkeypatch.undo()  # o QGIS fechou o arquivo

    asyncio.run(sm.queue.process_pending())

    assert not alvo.exists()
    assert sm.manifest.get_dataset("campo") is None
    assert sm.manifest.pending_items() == []
    assert len(list((tmp_path / TRASH_DIR_NAME).glob("campo_*/campo.geojson"))) == 1


def test_r2_discard_does_not_duplicate_queue_item(tmp_path, monkeypatch):
    alvo = tmp_path / "campo.geojson"
    alvo.write_text("{}")
    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("campo", {"type": "geojson",
                                      "files": {"campo.geojson": {"md5": "a"}},
                                      "remote_id_hash": "rid-1"})
    _lock_trash(monkeypatch)

    for _ in range(3):
        sm._discard_dataset("campo", "teste")

    assert len(sm.manifest.pending_items()) == 1


# ── R3 — the queue retry must also delete the old remote copy ────────────────

def test_r3_retry_deletes_the_old_remote_copy(tmp_path, without_spatial_validation):
    """
    MinIO down on the 1st attempt: the item goes to the queue and the manifest
    keeps rid-antigo (correct). When the retry uploads rid-novo, rid-antigo has
    to leave the bucket — otherwise it comes back later as a "new file" with the same
    original_name and resurrects stale content.
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

def test_r5_whole_shapefile_goes_to_the_same_trash_folder(tmp_path):
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


def test_r5_two_discards_of_the_same_dataset_do_not_mix(tmp_path):
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


# ── R6 — trash purge ─────────────────────────────────────────────────────────

def test_r6_purge_removes_old_discards_and_measures_the_rest(tmp_path):
    trash = tmp_path / TRASH_DIR_NAME
    velho = trash / "parcelas_20260101T000000"
    velho.mkdir(parents=True)
    (velho / "parcelas.shp").write_bytes(b"0" * 100)
    old_ts = time.time() - 30 * 86400
    os.utime(velho, (old_ts, old_ts))

    novo = trash / "campo_20260801T000000"
    novo.mkdir()
    (novo / "campo.geojson").write_bytes(b"0" * 50)

    removidos, restantes = purge_trash(tmp_path, max_age_days=14)

    assert removidos == 1
    assert not velho.exists() and novo.exists()
    assert restantes == 50


def test_r6_manager_purges_the_trash_in_the_cycle(tmp_path):
    trash = tmp_path / TRASH_DIR_NAME
    velho = trash / "parcelas_20260101T000000"
    velho.mkdir(parents=True)
    (velho / "parcelas.shp").write_bytes(b"0" * 10)
    old_ts = time.time() - 60 * 86400
    os.utime(velho, (old_ts, old_ts))

    sm = _make_manager(tmp_path, mode="bidirectional")
    asyncio.run(sm._maybe_purge_trash())
    assert not velho.exists()

    # A second call in the same cycle does not sweep again (wasted I/O every 30s).
    novo = trash / "campo_20260801T000000"
    novo.mkdir()
    os.utime(novo, (old_ts, old_ts))
    asyncio.run(sm._maybe_purge_trash())
    assert novo.exists()


# ── R7 — the push also respects the conflict policy ──────────────────────────

def _manager_with_conflict(tmp_path, monkeypatch, estrategia):
    from executor import config as agent_config

    monkeypatch.setattr(agent_config, "SYNC_CONFLICT_STRATEGY", estrategia)
    alvo = tmp_path / "levantamento.geojson"
    alvo.write_text('{"campo":1}')  # already EDITED offline by the technician

    sm = _make_manager(tmp_path, mode="bidirectional")
    sm.manifest.set_dataset("levantamento", {
        "type": "geojson",
        "files": {"levantamento.geojson": {"md5": "md5-do-download"}},
        "remote_id_hash": "rid-1",
        "remote_name": "levantamento.geojson",
        "remote_md5": "md5-remoto-antigo",
        "local_md5": "md5-do-download",  # != current MD5 on disk
        "status": "synced",
        "sync_direction": "remote",
    })

    async def _download(rid, dest):
        dest.write_text('{"remoto":1}')
        return True

    sm.downloader.download = AsyncMock(side_effect=_download)
    return sm, alvo


def test_r7_push_with_keep_both_preserves_the_field_edit(tmp_path, monkeypatch):
    sm, alvo = _manager_with_conflict(tmp_path, monkeypatch, "keep-both")
    eventos = _capture_events(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    backups = list(tmp_path.glob("levantamento_local_*.geojson"))
    assert len(backups) == 1, "trabalho de campo sobrescrito sem backup"
    assert backups[0].read_text() == '{"campo":1}'
    assert alvo.read_text() == '{"remoto":1}'
    assert ("conflict_detected", "levantamento") in eventos


def test_r7_push_with_local_wins_does_not_download(tmp_path, monkeypatch):
    sm, alvo = _manager_with_conflict(tmp_path, monkeypatch, "local-wins")
    eventos = _capture_events(sm)

    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    assert alvo.read_text() == '{"campo":1}'
    sm.downloader.download.assert_not_awaited()
    assert ("conflict_detected", "levantamento") in eventos


def test_r7_push_without_local_edit_downloads_without_conflict(tmp_path, monkeypatch):
    """Without local divergence there is no conflict — the normal push must not regress."""
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
        "local_md5": hashlib.md5(b'{"campo":1}').hexdigest(),  # disk matches the manifest
        "sync_direction": "remote",
    })
    eventos = _capture_events(sm)

    async def _download(rid, dest):
        dest.write_text('{"remoto":1}')
        return True

    sm.downloader.download = AsyncMock(side_effect=_download)
    asyncio.run(sm._process_drive_event(_created_event("rid-1", "levantamento.geojson")))

    assert alvo.read_text() == '{"remoto":1}'
    assert list(tmp_path.glob("levantamento_local_*.geojson")) == []
    assert ("conflict_detected", "levantamento") not in eventos


# ── R9 — o watcher acorda o sync de verdade ──────────────────────────────────

def test_r9_watchdog_event_wakes_the_sync_from_another_thread(tmp_path):
    """
    `_change_flag` is an asyncio.Event: setting it directly from the watchdog thread is
    not thread-safe. Exercises the real chain _SyncEventHandler → FileWatcher._handle_event
    → SyncManager._on_change → _change_flag, with the handler running outside the loop.
    """
    from executor.sync.watcher import _SyncEventHandler

    sm = _make_manager(tmp_path, mode="upload")
    evento = type("_Ev", (), {"is_directory": False,
                              "src_path": str(tmp_path / "novo.geojson")})()

    async def _scenario():
        sm._loop = asyncio.get_running_loop()
        handler = _SyncEventHandler(sm.watcher._handle_event)
        assert not sm._change_flag.is_set()
        await asyncio.to_thread(handler.on_created, evento)
        await asyncio.wait_for(sm._change_flag.wait(), timeout=2)
        return sm._change_flag.is_set()

    assert asyncio.run(_scenario())


def test_r9_real_watcher_wakes_the_sync(tmp_path):
    """Integration with the real watchdog: creating a file triggers the cycle."""
    sm = _make_manager(tmp_path, mode="upload")

    async def _scenario():
        sm._loop = asyncio.get_running_loop()
        sm.watcher.start()
        try:
            await asyncio.to_thread((tmp_path / "novo.geojson").write_text, "{}")
            await asyncio.wait_for(sm._change_flag.wait(), timeout=15)
        finally:
            await asyncio.to_thread(sm.watcher.stop)

    asyncio.run(_scenario())
    assert sm._change_flag.is_set()


def test_r9_event_in_trash_does_not_wake_the_sync(tmp_path):
    """Now that on_change exists, the trash filter is no longer decorative."""
    from executor.sync.watcher import _SyncEventHandler

    sm = _make_manager(tmp_path, mode="upload")
    descarte = tmp_path / TRASH_DIR_NAME / "dados_20260101T000000" / "dados.geojson"
    evento = type("_Ev", (), {"is_directory": False, "src_path": str(descarte)})()

    async def _scenario():
        sm._loop = asyncio.get_running_loop()
        handler = _SyncEventHandler(sm.watcher._handle_event)
        await asyncio.to_thread(handler.on_created, evento)
        await asyncio.sleep(0)
        return sm._change_flag.is_set()

    assert asyncio.run(_scenario()) is False


# ── P5 — GeoSync stopped eating the machine while doing nothing ──────────────
#
# The performance findings of the sync subsystem:
#   P5.1 — diff() rehashed the whole folder every 30s, ignoring (size, mtime)
#   P5.2 — the cycle woken by the watcher had no interval floor
#   P5.3 — every manifest mutation reserialized the whole JSON to disk
#   P5.4 — the queue slept up to 300s INSIDE the cycle, freezing the folder
#   P5.5 — uploads and downloads were strictly serialized

def _seed_manifest_from_disk(sm):
    """Writes the folder's current state to the manifest, like a successful cycle."""
    for nome, ds in sm.scanner.scan().items():
        sm.manifest.set_dataset(nome, {
            "type": ds.type,
            "files": {f: i.to_dict() for f, i in ds.files.items()},
            "status": "synced",
            "remote_id_hash": f"rid-{nome}",
            "sync_direction": "local",
        })


def test_p5_diff_does_not_rehash_when_size_and_mtime_match(tmp_path, monkeypatch):
    """With the disk untouched, a cycle must not open any file."""
    from executor.sync import scanner as scanner_mod

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(5):
        (tmp_path / f"d{i}.geojson").write_text('{"a":%d}' % i)
    _seed_manifest_from_disk(sm)

    leituras = {"n": 0}
    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (leituras.__setitem__("n", leituras["n"] + 1), real(p))[1])

    atual = sm.scanner.scan()
    novos, modified, removidos = sm.scanner.diff(atual, sm.manifest.all_datasets())

    assert (novos, modified, removidos) == ([], [], [])
    assert leituras["n"] == 0, "o diff releu o disco mesmo com (size, mtime) inalterados"


def test_p5_diff_still_catches_real_edit(tmp_path):
    """The shortcut must not hide a real change — mtime changes on edit."""
    sm = _make_manager(tmp_path, mode="upload")
    alvo = tmp_path / "campo.geojson"
    alvo.write_text('{"a":1}')
    _seed_manifest_from_disk(sm)

    alvo.write_text('{"a":2, "b":3}')
    futuro = time.time() + 5
    os.utime(alvo, (futuro, futuro))

    _, modified, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets())
    assert modified == ["campo"]


def test_p5_full_sweep_catches_rewrite_with_preserved_mtime(tmp_path):
    """The shortcut's safety net: `force_hash` finds what it would let through."""
    sm = _make_manager(tmp_path, mode="upload")
    alvo = tmp_path / "campo.geojson"
    alvo.write_text('{"a":1}')
    _seed_manifest_from_disk(sm)

    st = alvo.stat()
    alvo.write_text('{"b":2}')  # mesmo tamanho, mtime restaurado
    os.utime(alvo, (st.st_atime, st.st_mtime))

    _, without_hash, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets())
    _, with_hash, _ = sm.scanner.diff(sm.scanner.scan(), sm.manifest.all_datasets(),
                                     force_hash=True)
    assert without_hash == []
    assert with_hash == ["campo"]


def test_p5_manifest_writes_once_per_batch(tmp_path, without_spatial_validation):
    """There were THREE reserializations of the whole JSON per uploaded dataset — O(N²)."""
    from executor.sync.uploader import UploadResult

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(10):
        (tmp_path / f"d{i}.geojson").write_text("{}")
    sm.uploader.upload = AsyncMock(
        return_value=UploadResult(id_hash="rid", remote_name="x", remote_md5="m")
    )

    gravacoes = {"n": 0}
    real = sm.manifest._write_loop
    sm.manifest._write_loop = lambda c: (gravacoes.__setitem__("n", gravacoes["n"] + 1), real(c))[1]

    asyncio.run(sm._local_to_remote())

    assert gravacoes["n"] <= 2, f"{gravacoes['n']} gravacoes para 10 datasets"
    assert sm.manifest.get_dataset("d3")["status"] == "synced"


def test_p5_manifest_writes_atomically(tmp_path):
    """A crash in the middle of json.dump left the manifest truncated."""
    from executor.sync.manifest import SyncManifest

    m = SyncManifest(str(tmp_path), "ws-1", "ag-1")
    m.set_dataset("d", {"type": "geojson"})
    asyncio.run(m.flush())

    import json
    assert json.loads(m.path.read_text(encoding="utf-8"))["datasets"]["d"]["type"] == "geojson"
    assert not (tmp_path / ".atlans-sync.json.tmp").exists()


def test_p5_queue_schedules_the_retry_instead_of_sleeping(tmp_path):
    """An `asyncio.sleep(backoff)` here froze the FOLDER, not just the item."""
    from executor.sync.manifest import SyncManifest
    from executor.sync.queue import SyncQueue

    m = SyncManifest(str(tmp_path), "ws-1", "ag-1")
    m.enqueue("upload", "ds1")
    m._data["pending_queue"][0]["retries"] = 8  # 256s backoff

    async def _falha(item):
        return False

    inicio = time.monotonic()
    asyncio.run(SyncQueue(m, _falha).process_pending())
    assert time.monotonic() - inicio < 1.0, "a fila dormiu dentro do ciclo"
    assert m.pending_items()[0]["next_attempt_at"] > time.time()

    # Second pass: the item is not due yet, so it is not even attempted.
    tentativas = {"n": 0}

    async def _count(item):
        tentativas["n"] += 1
        return True

    asyncio.run(SyncQueue(m, _count).process_pending())
    assert tentativas["n"] == 0


def test_p5_uploads_happen_in_parallel(tmp_path, without_spatial_validation):
    """Serializados, 200 arquivos pequenos passavam o tempo esperando round-trip."""
    from executor.sync.uploader import UploadResult

    sm = _make_manager(tmp_path, mode="upload")
    for i in range(6):
        (tmp_path / f"d{i}.geojson").write_text("{}")

    simultaneos = {"agora": 0, "pico": 0}

    async def _slow_upload(ds, meta=None):
        simultaneos["agora"] += 1
        simultaneos["pico"] = max(simultaneos["pico"], simultaneos["agora"])
        await asyncio.sleep(0.05)
        simultaneos["agora"] -= 1
        return UploadResult(id_hash="rid", remote_name=ds.name, remote_md5="m")

    sm.uploader.upload = _slow_upload
    asyncio.run(sm._local_to_remote())

    assert simultaneos["pico"] > 1, "os uploads continuam estritamente em serie"


def test_p5_ui_command_skips_the_stabilization_wait(tmp_path):
    """The floor between cycles contains the watchdog burst, not the user's click."""
    sm = _make_manager(tmp_path, mode="upload")

    async def _scenario():
        sm._loop = asyncio.get_running_loop()
        sm._last_cycle = sm._loop.time()  # ciclo recem-terminado: piso em vigor
        sm.sync_now()
        inicio = sm._loop.time()
        await sm._wait_for_folder_to_settle()
        return sm._loop.time() - inicio

    assert asyncio.run(_scenario()) < 0.5


def test_p5_claims_event_does_not_sweep_the_manifest(tmp_path):
    """Push routing became an O(1) lookup in the manifest's indexes."""
    sm = _make_manager(tmp_path)
    for i in range(50):
        sm.manifest.set_dataset(f"d{i}", {"type": "geojson",
                                          "files": {f"d{i}.geojson": {}},
                                          "remote_id_hash": f"rid-{i}"})
    sm.manifest.remove_dataset("d7")

    assert sm.claims_event({"file": {"id_hash": "rid-49", "original_name": "x.geojson"}}) is True
    assert sm.claims_event({"file": {"id_hash": "", "original_name": "d3.geojson"}}) is True
    # Removed from the manifest must leave the index along with it.
    assert sm.claims_event({"file": {"id_hash": "rid-7", "original_name": "d7.geojson"}}) is False
