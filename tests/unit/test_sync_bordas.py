# tests/unit/test_sync_bordas.py
"""
GeoSync edge cases exposed by the audit of the performance optimizations.

Every invariant here has the same outcome when broken: USER FILE NOT
SYNCED — with no error at all in the log.

  A21 — the full-scan marker (the safety net for the size/mtime shortcut) may
        only be stamped AFTER the scan runs, and one unreadable file must not
        bring down the whole cycle.
  A22 — on a coarse-mtime FS (a USB stick's FAT32/exFAT), the (size, mtime)
        pair only attests "unchanged" if it was collected with the mtime
        already settled.
  A45 — the backoff has to reach the item that was executed, and the queue
        must not accumulate equivalent items.
  A46 — a clock that goes backwards must not freeze an item forever.
  A47 — the transfers' byte I/O does not wait for the heavy-work pool.
  A57 — a manifest write that fails keeps the manifest dirty.
"""
import asyncio
import os
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

LOCAL_URL = "ws://localhost:8000"  # is_local_server → sem exigir cert mTLS


@pytest.fixture(autouse=True)
def _clean_pools():
    """The GeoSync pools are process-global: tear them down between tests."""
    from executor.sync import pool

    def _tear_down():
        for p in (pool._pool, pool._pool_io):
            if p is not None:
                p.shutdown(wait=False)
        pool._pool = pool._pool_io = None

    _tear_down()
    yield
    _tear_down()


def _manager(tmp_path: Path):
    from executor.sync.manager import SyncManager

    sm = SyncManager(sync_dir=str(tmp_path), workspace_id="ws-1", server_url=LOCAL_URL,
                     executor_id="ag-1", interval=1)
    sm.sync_mode = "upload"
    sm.uploader = MagicMock()
    sm.uploader.delete = AsyncMock(return_value=True)
    sm.uploader.upload = AsyncMock(return_value=None)
    sm.downloader = MagicMock()
    sm.downloader.list_remote = AsyncMock(return_value=[])
    sm.trigger._triggers = []
    return sm


def _manifesto_do_disco(scanner, stat_at=None) -> dict:
    """Synthetic manifest describing the folder as it is now."""
    manifesto = {}
    for nome, ds in scanner.scan().items():
        arquivos = {}
        for fname, finfo in ds.files.items():
            entrada = finfo.to_dict()
            if stat_at is not None:
                entrada["stat_at"] = stat_at(finfo)
            arquivos[fname] = entrada
        manifesto[nome] = {"type": ds.type, "files": arquivos, "status": "synced"}
    return manifesto


# ── A21 — the safety net must not be consumed without having run ──────────────

def test_a21_full_scan_marker_is_stamped_only_if_it_completes(tmp_path):
    """The diff with force_hash opens ALL the files in the folder. If it raises,
    the cycle dies — and by marking beforehand, the full pass was taken as done
    and would only come back 1h later, failing to upload the mtime-preserving
    rewrite."""
    sm = _manager(tmp_path)
    (tmp_path / "parcelas.geojson").write_text('{"a":1}')

    def _explode(*a, **kw):
        raise OSError("arquivo sumiu durante a varredura")

    sm.scanner.diff = _explode
    with pytest.raises(OSError):
        asyncio.run(sm._local_to_remote())

    assert sm._last_full_hash is None, \
        "a varredura completa foi consumida sem nunca ter acontecido"

    # A cycle that completes: now the marker does count.
    sm.scanner.diff = lambda *a, **kw: ([], [], [])
    asyncio.run(sm._local_to_remote())
    assert sm._last_full_hash is not None


def test_a21_unreadable_file_does_not_break_the_folder_diff(tmp_path, monkeypatch):
    """A temp file that vanishes (QGIS/ArcGIS create and delete them all the time)
    carried an OSError out of the diff and killed change detection for the
    ENTIRE folder."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    (tmp_path / "some.geojson").write_text('{"a":1}')
    (tmp_path / "fica.geojson").write_text('{"a":1}')
    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner)

    # Both change content; only one of them becomes unreadable at hash time.
    for nome in ("some", "fica"):
        alvo = tmp_path / f"{nome}.geojson"
        alvo.write_text('{"a":2,"b":3}')

    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (_ for _ in ()).throw(FileNotFoundError(p))
                        if p.name == "some.geojson" else real(p))

    _, modified, _ = scanner.diff(scanner.scan(), manifesto, force_hash=True)
    assert modified == ["fica"], "um arquivo ilegivel cegou a pasta inteira"


# ── A22 — testemunho (size, mtime) em FS de mtime grosseiro ──────────────────

def test_a22_edit_in_the_same_usb_drive_mtime_bucket_is_detected(tmp_path):
    """FAT32/exFAT record mtime in 2s steps. Editing an attribute in QGIS
    rewrites only the .dbf, which has fixed-width records: same size. If the
    write lands in the same bucket as the stat that produced the manifest, size
    and mtime stay identical and the shortcut concludes 'unchanged' — the file
    is never uploaded."""
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)     # INTEGER mtime, as on FAT32
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    # Evidence collected half a second after the mtime: inside the 2s bucket.
    manifesto = _manifesto_do_disco(scanner, stat_at=lambda f: t + 0.5)

    alvo.write_text('{"a":2}')            # mesmo tamanho...
    os.utime(alvo, (t, t))                # ...e mesmo mtime (balde de 2s)

    _, modified, _ = scanner.diff(scanner.scan(), manifesto)
    assert modified == ["parcelas"], "edicao invisivel para (size, mtime) nao subiu"


def test_a22_mature_witness_preserves_the_shortcut(tmp_path, monkeypatch):
    """The gain still holds: with the mtime already settled when the stat was
    taken, no later write fits in the same bucket — and the cycle opens nothing."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner, stat_at=lambda f: t + 30)

    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: pytest.fail(f"o diff releu {p.name} sem necessidade"))
    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])


def test_a22_witness_is_reanchored_after_the_hash_confirms(tmp_path, monkeypatch):
    """An entry without `stat_at` (manifest from an earlier version) or collected
    too early must heal itself: otherwise the dataset is rehashed every cycle
    forever — nothing changes, nothing is uploaded, and so nobody rewrites the
    manifest."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner)
    del manifesto["parcelas"]["files"]["parcelas.geojson"]["stat_at"]

    leituras = {"n": 0}
    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (leituras.__setitem__("n", leituras["n"] + 1), real(p))[1])

    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])
    assert leituras["n"] == 1, "entrada sem testemunho tem de cair no hash"
    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])
    assert leituras["n"] == 1, "o testemunho nao foi reancorado: rehashearia para sempre"


# ── A45 — backoff has to reach the executed item ─────────────────────────────

def _manifesto(tmp_path):
    from executor.sync.manifest import SyncManifest
    return SyncManifest(str(tmp_path), "ws-1", "ag-1")


def test_a45_all_executed_items_get_scheduled(tmp_path):
    """Matching by name only and breaking, the backoff always went to the FIRST
    namesake: the others retried every cycle, each attempt paying for
    validate + metadata + MD5 of the entire dataset."""
    from executor.sync.queue import SyncQueue

    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    # Queue inherited from before deduplication — the scenario the audit describes.
    m._data["pending_queue"].append(dict(m._data["pending_queue"][0]))

    async def _falha(item):
        return False

    asyncio.run(SyncQueue(m, _falha).process_pending())

    agora = time.time()
    assert len(m.pending_items()) == 2
    for item in m.pending_items():
        assert item["retries"] == 1
        assert item["next_attempt_at"] > agora, "item executado ficou sem backoff"


def test_a45_enqueuing_again_neither_duplicates_nor_resets_the_backoff(tmp_path):
    """Each upload failure leaves the entry without 'files', the next cycle's diff
    re-enqueues it, and the queue grew by one item per cycle."""
    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = 12345.0
    m.pending_items()[0]["retries"] = 3

    m.enqueue("upload", "parcelas")

    assert len(m.pending_items()) == 1
    assert m.pending_items()[0]["retries"] == 3
    assert m.pending_items()[0]["next_attempt_at"] == 12345.0

    m.enqueue("delete", "parcelas", {"remote_id_hash": "abc"})
    assert len(m.pending_items()) == 2, "acoes diferentes sao operacoes diferentes"


# ── A46 — the wall clock must not freeze the queue ───────────────────────────

def test_a46_clock_going_back_in_time_does_not_freeze_the_discard(tmp_path):
    """A field laptop that boots with its clock ahead and is later corrected by
    NTP: the schedule recorded in the manifest becomes a future that never
    arrives. For 'discard' there is no other engine — the file the Drive said to
    delete would stay on the technician's disk forever, with no error in the
    log."""
    from executor.sync.queue import SyncQueue

    m = _manifesto(tmp_path)
    m.enqueue("discard", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = time.time() + 86400  # relogio adiantado

    executados = []

    async def _execute(item):
        executados.append(item["dataset"])
        return True

    asyncio.run(SyncQueue(m, _execute).process_pending())
    assert executados == ["parcelas"]


def test_a46_legitimate_schedule_is_still_respected(tmp_path):
    """The sanitizing must not turn into 'ignore the backoff'."""
    from executor.sync.queue import SyncQueue, _MAX_BACKOFF

    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = time.time() + _MAX_BACKOFF - 5

    async def _never(item):
        raise AssertionError("item ainda nao venceu")

    asyncio.run(SyncQueue(m, _never).process_pending())


# ── A47 — transfers do not wait for the heavy-work pool ──────────────────────

def test_a47_transfer_io_has_its_own_pool():
    """With everything in the same 2-thread pool, two heavy `_write_zip`/
    `extract_metadata` calls stalled ALL in-flight transfers for minutes: the
    PUT/GET socket went without data and MinIO dropped the connection as idle."""
    from executor.sync import pool
    from executor.sync.sync_config import SYNC_THREADS

    async def cenario():
        travar = threading.Event()
        heavy_tasks = [asyncio.create_task(pool.em_thread(travar.wait, 10))
                   for _ in range(SYNC_THREADS)]
        await asyncio.sleep(0.2)  # all heavy threads busy
        try:
            assert await asyncio.wait_for(pool.em_thread_io(lambda: "ok"), timeout=5) == "ok"
        finally:
            travar.set()
            await asyncio.gather(*heavy_tasks)

    asyncio.run(cenario())


# ── A57 — gravacao que falha mantem o manifesto sujo ─────────────────────────

def test_a57_failing_flush_does_not_consider_the_state_saved(tmp_path):
    """Disk full: the state of N freshly synced datasets lived only in memory
    with the manifest marked as clean. A kill in that window re-sent
    everything and left orphan copies in the Drive with the same original_name."""
    m = _manifesto(tmp_path)
    m.set_dataset("parcelas", {"type": "geojson"})

    m._write_loop = lambda conteudo: False          # OSError engolido la dentro
    asyncio.run(m.flush())
    assert m._is_dirty, "manifesto dado como salvo sem ter chegado ao disco"

    gravados = []
    m._write_loop = lambda conteudo: (gravados.append(conteudo), True)[1]
    asyncio.run(m.flush())
    assert gravados and "parcelas" in gravados[0]
    assert not m._is_dirty


def test_a57_mutation_during_the_write_stays_pending(tmp_path):
    """The write runs outside the loop: whatever changes in the middle of it did
    not make it into the snapshot and cannot be considered saved."""
    m = _manifesto(tmp_path)
    m.set_dataset("a", {"type": "geojson"})

    liberar = threading.Event()

    def _write_slowly(conteudo):
        liberar.wait(5)
        return True

    m._write_loop = _write_slowly

    async def cenario():
        tarefa = asyncio.create_task(m.flush())
        await asyncio.sleep(0.2)              # the write has already started
        m.set_dataset("b", {"type": "geojson"})
        liberar.set()
        await tarefa

    asyncio.run(cenario())
    assert m._is_dirty, "a mutacao feita durante a gravacao foi dada como salva"
