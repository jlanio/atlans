# tests/unit/test_ocultar_windows.py
"""Windows HIDDEN attribute on the executor's internal files.

The files the executor writes into the user's folder are already born with a
leading dot in the name (`.atlans-sync.json`, `.executor_results.sqlite`,
`.atlans-trash/`), which is enough to hide them on Linux and macOS. Windows
Explorer ignores that convention: there they would show up in the middle of the
user's data, inviting accidental deletion — deleting the manifest re-syncs the
whole folder and deleting the outbox loses job results. Hence
`ocultar_no_windows`.

CI runs on Linux, so the real call to kernel32 is simulated. What these tests
protect is the LOGIC (when and with which bits we call SetFileAttributesW) and
the contract of never raising — plus the WIRING at the two points the user
mentioned: the manifest and the SQLite files.
"""
import asyncio
import types

import pytest

from executor import utils

FILE_ATTRIBUTE_HIDDEN = 0x02
FILE_ATTRIBUTE_ARCHIVE = 0x20


def _simulate_windows(monkeypatch, get_return, registro):
    """Makes `ocultar_no_windows` believe it is running on Windows, with a fake kernel32.

    `get_return` is what the simulated GetFileAttributesW returns; each
    SetFileAttributesW goes into `registro` as (path, attrs).
    """
    import ctypes

    def _get(_p):
        return get_return

    def _set(p, attrs):
        registro.append((p, attrs))
        return 1

    monkeypatch.setattr(utils.os, "name", "nt")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_get, SetFileAttributesW=_set,
            GetLastError=lambda: 0,  # used by the helper's diagnostic log
        )),
        raising=False,  # `windll` nao existe em Linux; criamos o atributo.
    )


# ── No-op outside Windows ──────────────────────────────────────────────────────

def test_noop_outside_windows_does_not_touch_kernel32(monkeypatch, tmp_path):
    """On Linux/macOS the dot already hides; the os.name guard must exit BEFORE
    any call to kernel32.

    The old test only checked `is None` — but the helper swallows AttributeError,
    so it passed even if the guard were removed. Here we inject a fake kernel32
    that RECORDS any call: if the guard disappears, `tocado` gets filled and the
    test breaks.
    """
    import ctypes
    tocado = []

    def _registra(*a):
        tocado.append(a)
        return 0x20

    monkeypatch.setattr(utils.os, "name", "posix")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_registra, SetFileAttributesW=_registra,
            GetLastError=lambda: 0,
        )),
        raising=False,
    )

    f = tmp_path / ".atlans-sync.json"
    f.write_text("{}")
    assert utils.ocultar_no_windows(f) is None
    assert tocado == []   # the os.name short-circuit prevented any syscall


def test_does_not_raise_on_nonexistent_path(monkeypatch):
    monkeypatch.setattr(utils.os, "name", "posix")
    assert utils.ocultar_no_windows("/nao/existe/.atlans-sync.json") is None


# ── Logic on Windows (simulated kernel32) ───────────────────────────────────────

def test_sets_hidden_preserving_other_attributes(monkeypatch, tmp_path):
    registro = []
    _simulate_windows(monkeypatch, FILE_ATTRIBUTE_ARCHIVE, registro)

    f = tmp_path / ".atlans-sync.json"
    f.write_text("{}")
    utils.ocultar_no_windows(f)

    assert len(registro) == 1
    caminho, attrs = registro[0]
    assert caminho == str(f)
    assert attrs & FILE_ATTRIBUTE_HIDDEN      # became hidden
    assert attrs & FILE_ATTRIBUTE_ARCHIVE     # without clearing what was already there


def test_does_not_reapply_if_already_hidden(monkeypatch, tmp_path):
    registro = []
    _simulate_windows(monkeypatch, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_ARCHIVE, registro)

    utils.ocultar_no_windows(tmp_path / "x")
    assert registro == []                     # already hidden → no SetFileAttributes


@pytest.mark.parametrize("invalido", [-1, 0xFFFFFFFF])
def test_bail_when_get_file_attributes_fails(monkeypatch, tmp_path, invalido):
    registro = []
    _simulate_windows(monkeypatch, invalido, registro)

    utils.ocultar_no_windows(tmp_path / "sumido")
    assert registro == []                     # Get falhou → nao tenta setar nada


def test_never_raises_even_with_broken_set(monkeypatch, tmp_path):
    import ctypes

    def _get(_p):
        return FILE_ATTRIBUTE_ARCHIVE

    def _set(_p, _a):
        raise OSError("acesso negado")

    monkeypatch.setattr(utils.os, "name", "nt")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_get, SetFileAttributesW=_set,
        )),
        raising=False,
    )

    # Best-effort by contract: never propagates to whoever just wrote the file.
    assert utils.ocultar_no_windows(tmp_path / "x") is None


# ── Fiacao: o manifesto e o outbox realmente chamam o helper ────────────────────

def test_manifest_is_hidden_after_each_write(monkeypatch, tmp_path):
    """`.atlans-sync.json` — the example the user mentioned — is hidden on save.

    Reapplied on every write on purpose: on Windows os.replace makes the
    manifest inherit the attributes of the visible `.tmp`, so a single hide at
    creation would not survive the first flush.
    """
    from executor.sync import manifest as manifest_mod

    chamadas = []
    monkeypatch.setattr(manifest_mod, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    m = manifest_mod.SyncManifest(str(tmp_path), "ws-1", "exec-1")
    m.set_dataset("parcelas", {"type": "geojson"})
    asyncio.run(m.flush())
    m.set_dataset("lotes", {"type": "geojson"})
    asyncio.run(m.flush())  # second write has to reapply

    alvo = str(tmp_path / ".atlans-sync.json")
    assert (tmp_path / ".atlans-sync.json").exists()
    assert chamadas.count(alvo) == 2


def test_outbox_sqlite_wal_and_journal_are_hidden(monkeypatch, tmp_path):
    """The 'sqlite files' (.sqlite, -wal, -shm, -journal) mentioned by the user.

    -journal is included because, when WAL does not kick in (e.g. a network share),
    SQLite silently falls back to a rollback journal and writes a visible .sqlite-journal.
    """
    from executor import result_store

    db = tmp_path / ".executor_results.sqlite"
    monkeypatch.setattr(result_store, "_DB_PATH", str(db))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_ocultado_pos_escrita", False)

    ocultos = []
    monkeypatch.setattr(result_store, "ocultar_no_windows", lambda p: ocultos.append(p))

    try:
        # A conexao e criada lazy no primeiro put → dispara o ocultar.
        result_store.put({"job_id": "j1", "status": "success"})
        for sufixo in ("", "-wal", "-shm", "-journal"):
            assert str(db) + sufixo in ocultos
    finally:
        result_store.close()


def test_real_outbox_stays_operable_after_hiding(monkeypatch, tmp_path):
    """With the REAL helper (no-op on Linux), the db is created, hidden and remains
    writable: validates result_store's premise (hiding after CREATE/write does
    not break SQLite), plus the put/count/mark_sent/load_pending cycle."""
    from executor import result_store

    db = tmp_path / ".executor_results.sqlite"
    monkeypatch.setattr(result_store, "_DB_PATH", str(db))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_ocultado_pos_escrita", False)
    # Does NOT mock ocultar_no_windows: on Linux it is a no-op, but it exercises the real path.

    try:
        result_store.put({"job_id": "j1", "status": "success"})
        result_store.put({"job_id": "j2", "status": "error"})
        assert db.exists()
        assert result_store.count_pending() == 2
        result_store.mark_sent("j1")
        assert result_store.count_pending() == 1
        assert [p["job_id"] for p in result_store.load_pending()] == ["j2"]
    finally:
        result_store.close()


def test_trash_is_hidden_on_creation(monkeypatch, tmp_path):
    from executor.sync import paths as paths_mod

    ocultos = []
    monkeypatch.setattr(paths_mod, "ocultar_no_windows", lambda p: ocultos.append(str(p)))

    origem = tmp_path / "parcelas.geojson"
    origem.write_bytes(b"{}")
    paths_mod.move_dataset_to_trash(tmp_path, "parcelas", [origem])

    assert str(tmp_path / paths_mod.TRASH_DIR_NAME) in ocultos


def test_sync_config_hides_config_dotfile(monkeypatch, tmp_path):
    """Wiring of the 4th point: .atlans-sync-config.json is hidden when read."""
    from executor.sync import sync_config as sc

    chamadas = []
    monkeypatch.setattr(sc, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    alvo = tmp_path / ".atlans-sync-config.json"
    alvo.write_text('{"include": ["*.geojson"]}', encoding="utf-8")
    sc.SyncConfig(tmp_path)   # __init__ chama _load_local

    assert str(alvo) in chamadas


def test_sync_config_does_not_hide_when_absent(monkeypatch, tmp_path):
    """Without the file, the early return prevents the call (does not hide a nonexistent path)."""
    from executor.sync import sync_config as sc

    chamadas = []
    monkeypatch.setattr(sc, "ocultar_no_windows", lambda p: chamadas.append(str(p)))
    sc.SyncConfig(tmp_path)
    assert chamadas == []


def test_ignore_hides_config_dotfile(monkeypatch, tmp_path):
    """Consistencia: .atlans-ignore recebe o mesmo tratamento do sync-config."""
    from executor.sync import ignore as ig

    chamadas = []
    monkeypatch.setattr(ig, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    alvo = tmp_path / ".atlans-ignore"
    alvo.write_text("*.tmp\n", encoding="utf-8")
    ig.IgnoreFilter(tmp_path)   # __init__ chama _load

    assert str(alvo) in chamadas


def test_ignore_does_not_hide_when_absent(monkeypatch, tmp_path):
    from executor.sync import ignore as ig

    chamadas = []
    monkeypatch.setattr(ig, "ocultar_no_windows", lambda p: chamadas.append(str(p)))
    ig.IgnoreFilter(tmp_path)
    assert chamadas == []


def test_manifest_survives_failing_os_replace(monkeypatch, tmp_path):
    """Contract for the os.replace error path (e.g. destination locked on Windows).

    The most serious risk raised in the review: if the atomic os.replace failed
    over the manifest, the executor could neither corrupt nor hang. Since on Linux
    replace always works, we simulate the failure. Expected: _write_loop returns False,
    flush() does NOT mark it as persisted, the manifest stays 'dirty' for the next
    flush to try again, nothing is written and the `.tmp` is cleaned up.
    """
    from executor.sync import manifest as manifest_mod

    m = manifest_mod.SyncManifest(str(tmp_path), "ws-1", "exec-1")
    m.set_dataset("parcelas", {"type": "geojson"})

    def _blocked_replace(*_a, **_k):
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(manifest_mod.os, "replace", _blocked_replace)

    asyncio.run(m.flush())  # must not raise

    assert m._is_dirty is True                                    # pendente p/ retry
    assert not (tmp_path / ".atlans-sync.json").exists()      # nada persistido
    assert not (tmp_path / ".atlans-sync.json.tmp").exists()  # .tmp limpo
