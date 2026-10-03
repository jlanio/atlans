# tests/unit/test_sync_manager.py
"""Unit tests for the SyncManager and GeoSync components."""
import asyncio
import pytest
import os
import time as _time


_pathspec_available = True
try:
    import pathspec  # noqa: F401
except ImportError:
    _pathspec_available = False


@pytest.mark.skipif(not _pathspec_available, reason="pathspec nao instalado")
class TestIgnoreFilter:

    def test_no_ignore_file(self, tmp_path):
        """Without .atlans-ignore, nothing should be ignored."""
        from executor.sync.ignore import IgnoreFilter
        f = IgnoreFilter(str(tmp_path))
        assert f.should_ignore(tmp_path / "test.geojson") is False

    def test_ignore_pattern(self, tmp_path):
        """Should ignore files that match the pattern."""
        ignore_file = tmp_path / ".atlans-ignore"
        ignore_file.write_text("*.tmp\nbackup_*\n")

        from executor.sync.ignore import IgnoreFilter
        f = IgnoreFilter(str(tmp_path))

        assert f.should_ignore(tmp_path / "data.tmp") is True
        assert f.should_ignore(tmp_path / "backup_2026.zip") is True
        assert f.should_ignore(tmp_path / "dados.geojson") is False

    def test_reload_on_change(self, tmp_path):
        """Should reload when .atlans-ignore changes."""
        ignore_file = tmp_path / ".atlans-ignore"
        ignore_file.write_text("*.tmp\n")

        from executor.sync.ignore import IgnoreFilter
        f = IgnoreFilter(str(tmp_path))

        assert f.should_ignore(tmp_path / "x.tmp") is True
        assert f.should_ignore(tmp_path / "x.bak") is False

        # Change the file and ensure a different mtime (Windows may have ~10ms resolution)
        ignore_file.write_text("*.bak\n")
        future = _time.time() + 1.0
        os.utime(ignore_file, (future, future))
        f.reload()

        assert f.should_ignore(tmp_path / "x.bak") is True


class TestDatasetScanner:

    def test_scan_geojson(self, tmp_path):
        """Should detect a GeoJSON file as a dataset."""
        (tmp_path / "test.geojson").write_text('{"type":"FeatureCollection"}')

        from executor.sync.scanner import DatasetScanner
        scanner = DatasetScanner(str(tmp_path))
        datasets = scanner.scan()

        assert "test" in datasets
        assert datasets["test"].type == "geojson"

    def test_scan_shapefile_bundle(self, tmp_path):
        """Should group Shapefile components into a single dataset."""
        for ext in [".shp", ".dbf", ".shx", ".prj"]:
            (tmp_path / f"parcelas{ext}").write_bytes(b"\x00" * 10)

        from executor.sync.scanner import DatasetScanner
        scanner = DatasetScanner(str(tmp_path))
        datasets = scanner.scan()

        assert "parcelas" in datasets
        assert datasets["parcelas"].type == "shapefile"
        assert datasets["parcelas"].is_complete is True
        assert len(datasets["parcelas"].files) == 4

    def test_scan_ignores_hidden_files(self, tmp_path):
        """Deve ignorar arquivos ocultos e .atlans-sync.json."""
        (tmp_path / ".hidden.geojson").write_text("{}")
        (tmp_path / ".atlans-sync.json").write_text("{}")
        (tmp_path / "visible.geojson").write_text("{}")

        from executor.sync.scanner import DatasetScanner
        scanner = DatasetScanner(str(tmp_path))
        datasets = scanner.scan()

        assert "visible" in datasets
        assert ".hidden" not in datasets
        assert ".atlans-sync" not in datasets

    @pytest.mark.skipif(not _pathspec_available, reason="pathspec nao instalado")
    def test_scan_with_ignore_filter(self, tmp_path):
        """Should respect IgnoreFilter."""
        (tmp_path / "data.geojson").write_text("{}")
        (tmp_path / "temp.geojson").write_text("{}")
        ignore_file = tmp_path / ".atlans-ignore"
        ignore_file.write_text("temp*\n")

        from executor.sync.ignore import IgnoreFilter
        from executor.sync.scanner import DatasetScanner
        ignore = IgnoreFilter(str(tmp_path))
        scanner = DatasetScanner(str(tmp_path), ignore_filter=ignore)
        datasets = scanner.scan()

        assert "data" in datasets
        assert "temp" not in datasets

    def test_diff_detects_new(self, tmp_path):
        """Should detect new datasets."""
        (tmp_path / "new.geojson").write_text("{}")

        from executor.sync.scanner import DatasetScanner
        scanner = DatasetScanner(str(tmp_path))
        current = scanner.scan()
        new, modified, removed = scanner.diff(current, {})

        assert "new" in new
        assert len(modified) == 0
        assert len(removed) == 0

    def test_diff_detects_removed(self, tmp_path):
        """Should detect removed datasets."""
        from executor.sync.scanner import DatasetScanner
        scanner = DatasetScanner(str(tmp_path))
        current = scanner.scan()  # vazio
        manifest = {"old_dataset": {"files": {"old.geojson": {"md5": "abc"}}}}

        new, modified, removed = scanner.diff(current, manifest)

        assert "old_dataset" in removed


class TestSyncManifest:

    def test_create_empty_manifest(self, tmp_path):
        """Should create an empty v2 manifest."""
        from executor.sync.manifest import SyncManifest
        m = SyncManifest(str(tmp_path), "ws-1", "ag-1")

        assert m.all_datasets() == {}
        # The manifest only goes to disk on flush, after the first mutation
        assert not (tmp_path / ".atlans-sync.json").exists()
        m.set_dataset("d", {"type": "geojson"})
        asyncio.run(m.flush())
        assert (tmp_path / ".atlans-sync.json").exists()

    def test_set_and_get_dataset(self, tmp_path):
        """Should save and retrieve a dataset."""
        from executor.sync.manifest import SyncManifest
        m = SyncManifest(str(tmp_path), "ws-1", "ag-1")

        m.set_dataset("test", {"type": "geojson", "status": "synced"})
        ds = m.get_dataset("test")

        assert ds is not None
        assert ds["type"] == "geojson"

    def test_mark_synced(self, tmp_path):
        """Should mark a dataset as synced with remote_id."""
        from executor.sync.manifest import SyncManifest
        m = SyncManifest(str(tmp_path), "ws-1", "ag-1")

        m.set_dataset("test", {"type": "geojson"})
        m.mark_synced("test", "remote-123", local_md5="abc", remote_md5="abc")

        ds = m.get_dataset("test")
        assert ds["status"] == "synced"
        assert ds["remote_id_hash"] == "remote-123"
        assert ds["local_md5"] == "abc"

    def test_v1_migration(self, tmp_path):
        """Should migrate a v1 manifest to v2."""
        import json
        manifest_path = tmp_path / ".atlans-sync.json"
        manifest_path.write_text(json.dumps({
            "version": 1,
            "workspace_id": "ws-1",
            "executor_id": "ag-1",
            "last_full_scan": None,
            "datasets": {"old": {"type": "geojson", "files": {}}},
            "pending_queue": [],
        }))

        from executor.sync.manifest import SyncManifest
        m = SyncManifest(str(tmp_path), "ws-1", "ag-1")

        # Should have migrated to v2
        ds = m.get_dataset("old")
        assert ds is not None
        assert "remote_md5" in ds  # field added in the migration
