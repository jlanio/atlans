# tests/unit/test_geosync_catalogo.py
"""
GeoSync in catalog mode (LGPD).

The executor registers the dataset in the Drive — name, type, size, CRS, bbox — and the
bytes NEVER leave the user's folder. On read, the executor finds the
file again through its own `.atlans-sync.json`.

The design point these tests protect: **no filesystem path travels over the
network**. The server stores that the file is local and on which
executor, and nothing else. That eliminates from the start the path traversal
attack class that the artifacts path has to handle explicitly.
"""
import json
from pathlib import Path

import pytest

from flow.utils import drive_resolver


def _manifesto(pasta: Path, datasets: dict) -> None:
    (pasta / ".atlans-sync.json").write_text(
        json.dumps({"version": 1, "datasets": datasets}), encoding="utf-8",
    )


@pytest.fixture
def sync_dir(tmp_path, monkeypatch):
    pasta = tmp_path / "GeoDados"
    pasta.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", str(pasta))
    return pasta


# ── Resolution through the manifest ──────────────────────────────────────────

def test_resolves_single_file_dataset(sync_dir):
    (sync_dir / "parcelas.geojson").write_bytes(b'{"type":"FeatureCollection"}')
    _manifesto(sync_dir, {
        "parcelas": {
            "type": "geojson", "remote_id_hash": "id-1",
            "files": {"parcelas.geojson": {"md5": "x"}},
        },
    })

    temp, ext, nome = drive_resolver._resolve_do_manifesto_de_sync(
        "id-1", "exec-1", "geojson", "parcelas.geojson",
    )
    try:
        assert Path(temp).read_bytes() == b'{"type":"FeatureCollection"}'
        assert ext == "geojson" and nome == "parcelas.geojson"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_shapefile_resolves_to_the_shp_and_not_another_component(sync_dir):
    """A shapefile is a bundle. Returning the `.dbf` would make ReadShapefile fail
    in an incomprehensible way — the scanner's `primary_path` picks the `.shp`, and
    this resolution must agree with it."""
    for ext, conteudo in (("shp", b"GEOMETRIA"), ("dbf", b"ATRIBUTOS"), ("shx", b"INDICE")):
        (sync_dir / f"lotes.{ext}").write_bytes(conteudo)
    _manifesto(sync_dir, {
        "lotes": {
            "type": "shapefile", "remote_id_hash": "id-2",
            # Deliberate order: the .dbf comes first to prove that the choice
            # is not "the first in the dictionary".
            "files": {"lotes.dbf": {}, "lotes.shp": {}, "lotes.shx": {}},
        },
    })

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-2", "exec-1", "shp", "lotes.zip",
    )
    try:
        assert Path(temp).read_bytes() == b"GEOMETRIA"
    finally:
        Path(temp).unlink(missing_ok=True)


def test_copies_and_does_not_return_the_user_file(sync_dir):
    """Same pitfall as the artifacts path: the caller deletes what it receives."""
    import os

    original = sync_dir / "dados.geojson"
    original.write_bytes(b"conteudo")
    _manifesto(sync_dir, {
        "dados": {"type": "geojson", "remote_id_hash": "id-3",
                  "files": {"dados.geojson": {}}},
    })

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-3", "exec-1", "geojson", "dados.geojson",
    )
    assert Path(temp) != original
    os.unlink(temp)                       # what `read_drive_file_as` does
    assert original.is_file(), "o arquivo do usuario foi apagado pela leitura"


def test_searches_all_configured_folders(tmp_path, monkeypatch):
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", f"{a},{b}")

    _manifesto(a, {"outro": {"type": "geojson", "remote_id_hash": "id-x",
                             "files": {"outro.geojson": {}}}})
    (b / "alvo.geojson").write_bytes(b"achei")
    _manifesto(b, {"alvo": {"type": "geojson", "remote_id_hash": "id-4",
                            "files": {"alvo.geojson": {}}}})

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync(
        "id-4", "exec-1", "geojson", "alvo.geojson",
    )
    try:
        assert Path(temp).read_bytes() == b"achei"
    finally:
        Path(temp).unlink(missing_ok=True)


# ── Errors with a cause ──────────────────────────────────────────────────────

def test_dataset_from_another_executor_gives_explanatory_error(sync_dir):
    _manifesto(sync_dir, {})
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync(
            "id-inexistente", "exec-remoto", "geojson", "parcelas.geojson",
        )
    msg = str(exc.value)
    assert "exec-remoto" in msg
    assert "catalogo" in msg.lower() or "catálogo" in msg.lower()


def test_without_sync_folders_explains_what_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", "")
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync("id-1", "exec-1", "", "x.geojson")
    assert "EXECUTOR_SYNC_DIRS" in str(exc.value)


def test_file_removed_from_disk_gives_distinct_error(sync_dir):
    """The manifest knows the dataset, but the file disappeared — a different diagnosis
    from 'it is on another machine'."""
    _manifesto(sync_dir, {
        "sumido": {"type": "geojson", "remote_id_hash": "id-5",
                   "files": {"sumido.geojson": {}}},
    })
    with pytest.raises(FileNotFoundError) as exc:
        drive_resolver._resolve_do_manifesto_de_sync("id-5", "exec-1", "geojson", "sumido.geojson")
    assert "movido ou apagado" in str(exc.value)


def test_corrupted_manifest_does_not_break_the_search(tmp_path, monkeypatch):
    """A folder with an unreadable manifest must not prevent finding it in the others."""
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    monkeypatch.setenv("EXECUTOR_SYNC_DIRS", f"{a},{b}")

    (a / ".atlans-sync.json").write_text("{{{ nao e json", encoding="utf-8")
    (b / "ok.geojson").write_bytes(b"ok")
    _manifesto(b, {"ok": {"type": "geojson", "remote_id_hash": "id-6",
                          "files": {"ok.geojson": {}}}})

    temp, _, _ = drive_resolver._resolve_do_manifesto_de_sync("id-6", "exec-1", "geojson", "ok.geojson")
    try:
        assert Path(temp).read_bytes() == b"ok"
    finally:
        Path(temp).unlink(missing_ok=True)


# ── Choosing the primary file ────────────────────────────────────────────────

def test_dataset_without_files_in_manifest(sync_dir):
    assert drive_resolver._primary_file(sync_dir, {"type": "geojson", "files": {}}) is None


def test_shapefile_without_shp_in_bundle(sync_dir):
    """Incomplete bundle: better None (which becomes a named error) than returning the
    `.dbf` and failing inside geopandas."""
    ds = {"type": "shapefile", "files": {"lotes.dbf": {}, "lotes.shx": {}}}
    assert drive_resolver._primary_file(sync_dir, ds) is None
