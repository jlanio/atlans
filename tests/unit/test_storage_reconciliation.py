"""
Tests for the app.core.storage_reconciliation module.

Covers the DB <-> MinIO reconciliation jobs that address the /admin/storage
tracking bugs:
- fix_artifact_null_sizes (Bug 1)
- cleanup_pending_workspace_files (Bug 4)
- abort_stale_multipart_uploads (Bug 4 — S3 side)
- compute_storage_drift (Bug 2)
- count_orphaned_workspace_artifacts (Bug 5)
- count_orphaned_pinned_artifacts (Bug 8)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── fix_artifact_null_sizes ──────────────────────────────────────────────────

class TestFixArtifactNullSizes:

    @pytest.mark.asyncio
    @patch("app.core.storage_reconciliation._s3" if False else "app.core.storage.head")
    async def test_fills_when_head_returns_size(self, mock_head):
        from app.core import storage_reconciliation as mod

        # 2 artifacts with NULL size_bytes, head() returns 1234 for both
        art_a = MagicMock(s3_key="artifacts/ws-1/file-a.json", size_bytes=None)
        art_b = MagicMock(s3_key="artifacts/ws-2/file-b.json", size_bytes=None)
        mock_head.return_value = {"size": 1234, "etag": "x"}

        db = MagicMock()
        result_obj = MagicMock()
        result_obj.scalars.return_value.all.return_value = [art_a, art_b]
        db.execute = AsyncMock(return_value=result_obj)
        db.commit = AsyncMock()

        summary = await mod.fix_artifact_null_sizes(db)

        assert summary == {"checked": 2, "fixed": 2, "still_null": 0}
        assert art_a.size_bytes == 1234
        assert art_b.size_bytes == 1234
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.core.storage.head")
    async def test_pula_s3_key_local_de_fallback_agent(self, mock_head):
        from app.core import storage_reconciliation as mod

        # Executor's local path (fallback): does not try head on MinIO
        art = MagicMock(s3_key="/data/artifacts/ws/run/file.json", size_bytes=None)

        db = MagicMock()
        result_obj = MagicMock()
        result_obj.scalars.return_value.all.return_value = [art]
        db.execute = AsyncMock(return_value=result_obj)
        db.commit = AsyncMock()

        summary = await mod.fix_artifact_null_sizes(db)

        assert summary == {"checked": 1, "fixed": 0, "still_null": 1}
        mock_head.assert_not_called()
        assert art.size_bytes is None
        # No fixes: does not commit
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.core.storage.head")
    async def test_stays_null_when_head_returns_none(self, mock_head):
        """MinIO does not have the object yet — leaves NULL and tries again next cycle."""
        from app.core import storage_reconciliation as mod

        art = MagicMock(s3_key="artifacts/ws/file.json", size_bytes=None)
        mock_head.return_value = None

        db = MagicMock()
        result_obj = MagicMock()
        result_obj.scalars.return_value.all.return_value = [art]
        db.execute = AsyncMock(return_value=result_obj)
        db.commit = AsyncMock()

        summary = await mod.fix_artifact_null_sizes(db)

        assert summary == {"checked": 1, "fixed": 0, "still_null": 1}
        assert art.size_bytes is None

    @pytest.mark.asyncio
    @patch("app.core.storage.head")
    async def test_exception_in_head_is_treated_as_still_null(self, mock_head):
        """An exception in head() does not break the loop — it stays still_null."""
        from app.core import storage_reconciliation as mod

        art = MagicMock(s3_key="artifacts/ws/file.json", size_bytes=None)
        mock_head.side_effect = Exception("MinIO down")

        db = MagicMock()
        result_obj = MagicMock()
        result_obj.scalars.return_value.all.return_value = [art]
        db.execute = AsyncMock(return_value=result_obj)
        db.commit = AsyncMock()

        summary = await mod.fix_artifact_null_sizes(db)

        assert summary["still_null"] == 1
        assert summary["fixed"] == 0


# ── cleanup_pending_workspace_files ──────────────────────────────────────────

class TestCleanupPendingWorkspaceFiles:

    @pytest.mark.asyncio
    @patch("app.core.storage.abort_multipart_upload")
    @patch("app.core.storage.list_incomplete_multipart_uploads")
    async def test_remove_stale_pending(self, mock_list_mp, mock_abort):
        from app.core import storage_reconciliation as mod

        wf_a = MagicMock(id=1, s3_key="drive/ws/a.geojson")
        wf_b = MagicMock(id=2, s3_key="drive/ws/b.csv")
        # Multipart abandonado existe para wf_a
        mock_list_mp.side_effect = [
            iter([{"key": "drive/ws/a.geojson", "upload_id": "u1", "initiated": None}]),
            iter([]),  # nothing pending for wf_b
        ]
        mock_abort.return_value = True

        db = MagicMock()

        # 1st execute: SELECT stale pending; 2nd execute: DELETE
        select_result = MagicMock()
        select_result.scalars.return_value.all.return_value = [wf_a, wf_b]
        db.execute = AsyncMock(side_effect=[select_result, MagicMock()])
        db.commit = AsyncMock()

        result = await mod.cleanup_pending_workspace_files(db)

        assert result == {"deleted_pending": 2, "aborted_multipart": 1}
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_delete_when_there_is_no_stale(self):
        from app.core import storage_reconciliation as mod

        db = MagicMock()
        select_result = MagicMock()
        select_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=select_result)
        db.commit = AsyncMock()

        result = await mod.cleanup_pending_workspace_files(db)

        assert result == {"deleted_pending": 0, "aborted_multipart": 0}
        db.commit.assert_not_awaited()


# ── abort_stale_multipart_uploads ────────────────────────────────────────────

class TestAbortStaleMultipart:

    @pytest.mark.asyncio
    async def test_aborts_only_old_uploads(self):
        from app.core import storage_reconciliation as mod

        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=48)
        fresh = now - timedelta(minutes=10)

        uploads = [
            {"key": "drive/old.geojson", "upload_id": "u_old", "initiated": old},
            {"key": "drive/fresh.geojson", "upload_id": "u_fresh", "initiated": fresh},
        ]

        with patch("app.core.storage.list_incomplete_multipart_uploads", return_value=iter(uploads)):
            with patch("app.core.storage.abort_multipart_upload", return_value=True) as mock_abort:
                result = await mod.abort_stale_multipart_uploads()

        assert result == {"scanned": 2, "aborted": 1}
        # Only the old one was aborted
        mock_abort.assert_called_once_with("drive/old.geojson", "u_old")


# ── compute_storage_drift ────────────────────────────────────────────────────

class TestComputeStorageDrift:

    @pytest.mark.asyncio
    async def test_positive_drift_when_minio_has_more_than_db(self):
        from app.core import storage_reconciliation as mod

        # DB: 1000 bytes total (drive + artifacts)
        db = MagicMock()
        scalar_drive = MagicMock()
        scalar_drive.scalar.return_value = 600
        scalar_artifact = MagicMock()
        scalar_artifact.scalar.return_value = 400
        db.execute = AsyncMock(side_effect=[scalar_drive, scalar_artifact])

        # MinIO: 1500 bytes (drive) + 500 (artifacts) — drift de +900 + +100
        drive_objs = [{"key": "drive/a", "size": 1500}]
        artifact_objs = [{"key": "artifacts/a", "size": 500}]

        def fake_list(prefix):
            if prefix == "drive/":
                return iter(drive_objs)
            return iter(artifact_objs)

        with patch("app.core.storage.list_objects", side_effect=fake_list):
            result = await mod.compute_storage_drift(db)

        by_prefix = result["by_prefix"]
        assert by_prefix["drive/"]["db_bytes"] == 600
        assert by_prefix["drive/"]["s3_bytes"] == 1500
        assert by_prefix["drive/"]["drift_bytes"] == 900
        assert by_prefix["artifacts/"]["drift_bytes"] == 100


# ── auditoria ────────────────────────────────────────────────────────────────

class TestAudit:

    @pytest.mark.asyncio
    async def test_count_orphaned_workspace_artifacts(self):
        """Counts artifacts whose workspace_id no longer exists in `workspaces`.

        The previous version filtered `workspace_id IS NULL` on a NOT NULL column:
        it always measured 0 while the real orphans (workspace removed by hard
        delete, without cascade) showed up in the panel as "(sem workspace)" (no workspace).
        """
        from app.core import storage_reconciliation as mod

        db = MagicMock()
        scalar = MagicMock()
        scalar.scalar.return_value = 7
        db.execute = AsyncMock(return_value=scalar)

        assert await mod.count_orphaned_workspace_artifacts(db) == 7

        # The query has to be a LEFT JOIN on workspaces looking for the NULL side,
        # never a filter on Artifact.workspace_id IS NULL.
        sql = str(db.execute.await_args[0][0]).lower()
        assert "join" in sql and "workspaces" in sql

    @pytest.mark.asyncio
    async def test_count_orphaned_pinned_artifacts(self):
        from app.core import storage_reconciliation as mod

        db = MagicMock()
        scalar = MagicMock()
        scalar.scalar.return_value = 3
        db.execute = AsyncMock(return_value=scalar)

        assert await mod.count_orphaned_pinned_artifacts(db) == 3


# ── run_full_reconciliation orchestration ────────────────────────────────────

class TestRunFullReconciliation:

    @pytest.mark.asyncio
    async def test_continues_when_a_job_fails(self):
        """A failure of one sub-job does not prevent the others."""
        from app.core import storage_reconciliation as mod

        # Mock AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("app.core.storage_reconciliation.AsyncSessionLocal", return_value=mock_session):
            with patch.object(mod, "fix_artifact_null_sizes", side_effect=Exception("DB down")) as fix_mock:
                with patch.object(mod, "cleanup_pending_workspace_files", return_value={"deleted_pending": 0, "aborted_multipart": 0}) as cleanup_mock:
                    with patch.object(mod, "abort_stale_multipart_uploads", return_value={"scanned": 0, "aborted": 0}) as abort_mock:
                        with patch.object(mod, "compute_storage_drift", return_value={"by_prefix": {}}) as drift_mock:
                            with patch.object(mod, "count_orphaned_workspace_artifacts", return_value=0):
                                with patch.object(mod, "count_orphaned_pinned_artifacts", return_value=0):
                                    summary = await mod.run_full_reconciliation()

        # fix_null failed but was recorded
        fix_mock.assert_awaited()
        assert "error" in summary["fix_null"]
        # The others ran
        cleanup_mock.assert_awaited()
        abort_mock.assert_awaited()
        drift_mock.assert_awaited()
        assert summary["audit"]["orphaned_workspace_artifacts"] == 0
