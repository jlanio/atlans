# app/core/storage_reconciliation.py
"""
Reconciliation between the DB state and the actual MinIO state.

Addresses the family of bugs where the disk usage report
(/admin/storage) silently drifts from the actual disk:

- Bug 1: Artifact.size_bytes = NULL when s3.head() failed in run_result_consumer.
         The job retries the head and fills in the value.
- Bug 2: Abandoned multipart uploads and orphan objects in MinIO.
         The job measures the drift and (optionally) cleans up.
- Bug 4: WorkspaceFile with status='pending' left in limbo.
         The job deletes it after a TTL + aborts the corresponding multipart.
- Bug 5: Artifact with NULL workspace_id (legacy/orphan). Only counts + logs.
- Bug 8: Pinned Artifact whose workflow_hash is gone. Only counts + logs.

Runs as a background task in the API lifespan (in parallel with
artifact_cleanup.run_cleanup_loop). A Redis lock (`laco_periodico`) avoids
duplication across multiple uvicorn workers.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.core.tarefas_periodicas import laco_periodico
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.workflow import Workflow
from app.models.workspace_file import WorkspaceFile

logger = get_logger(__name__)

_RECONCILE_INTERVAL = int(os.getenv("STORAGE_RECONCILE_INTERVAL", "3600"))
_RECONCILE_LOCK_KEY = "storage_reconcile:lock"
_PENDING_TTL_HOURS = int(os.getenv("WORKSPACE_FILE_PENDING_TTL_HOURS", "24"))
_MULTIPART_TTL_HOURS = int(os.getenv("MULTIPART_UPLOAD_TTL_HOURS", "24"))


# Retry window for NULL size_bytes. Past this deadline the cause is no longer
# transient (the object never reached MinIO, or stayed on the executor's disk via
# local fallback) and insisting only wastes calls and keeps a permanent alert.
NULL_SIZE_RETRY_WINDOW_DAYS = int(os.getenv("ARTIFACT_NULL_SIZE_RETRY_DAYS", "7"))


# ── Bug 1: preencher size_bytes NULL via s3.head() retry ─────────────────────

async def fix_artifact_null_sizes(db: AsyncSession, limit: int = 500) -> dict:
    """Retry s3.head() on RECENT Artifacts with size_bytes IS NULL.

    When run_result_consumer fails to get the size (transient MinIO issue,
    race with the executor's upload), it writes NULL — and /admin/storage
    underestimates. This job tries again, filling in what it can.

    Retry window: only artifacts created in the last NULL_SIZE_RETRY_WINDOW_DAYS
    days. Previously the filter was just `size_bytes IS NULL`, so unsolvable
    records were re-queried once an hour forever — spending calls to MinIO
    and keeping a permanent alert on the panel that no action resolved.
    Past the window, the cause is no longer transient: either the object never
    reached MinIO, or it stayed on the executor's disk (local s3_key). Those are
    counted as `unrecoverable_size_artifacts` in /admin/storage.

    Returns: dict with counters {checked, fixed, still_null}.
    """
    from app.core import storage as _s3

    cutoff = utc_now_naive() - timedelta(days=NULL_SIZE_RETRY_WINDOW_DAYS)
    stmt = (
        select(Artifact)
        .where(Artifact.size_bytes.is_(None))
        .where(Artifact.s3_key.isnot(None))
        .where(Artifact.created_at >= cutoff)
        .limit(limit)
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    fixed = 0
    still_null = 0
    for art in candidates:
        # the executor's local fallback s3_key (sync to disk) has no head() in MinIO
        if art.s3_key.startswith("/"):
            still_null += 1
            continue
        try:
            obj = await _s3.head_async(art.s3_key)
        except Exception as exc:
            logger.debug("fix_null: head falhou para %s: %s", art.s3_key, exc)
            obj = None

        if obj and "size" in obj:
            art.size_bytes = obj["size"]
            fixed += 1
        else:
            still_null += 1

    if fixed > 0:
        await db.commit()

    summary = {"checked": len(candidates), "fixed": fixed, "still_null": still_null}
    if fixed > 0:
        logger.info("Reconcile/fix_null: %s", summary)
    return summary


# ── Bug 4: TTL para WorkspaceFile pending + abort multipart ──────────────────

async def cleanup_pending_workspace_files(db: AsyncSession) -> dict:
    """Remove WorkspaceFiles with status='pending' older than the TTL.

    Eternal pending piles up: a client requested a presigned PUT, got the URL,
    abandoned it. Without a confirm, the record lives forever in the DB and bytes
    may have been left in an abandoned multipart in MinIO. Aborts the
    corresponding multipart if there is one.

    Returns: dict {deleted_pending, aborted_multipart}.
    """
    from app.core import storage as _s3

    cutoff = utc_now_naive() - timedelta(hours=_PENDING_TTL_HOURS)
    stmt = (
        select(WorkspaceFile)
        .where(WorkspaceFile.status == "pending")
        .where(WorkspaceFile.created_at < cutoff)
    )
    result = await db.execute(stmt)
    stale = result.scalars().all()

    aborted = 0
    deleted_ids: list[Any] = []
    for wf in stale:
        # Best-effort: abort the multipart if one exists for this key
        try:
            for upload in await _s3.list_incomplete_multipart_uploads_async(prefix=wf.s3_key):
                if upload["key"] == wf.s3_key:
                    if await _s3.abort_multipart_upload_async(upload["key"], upload["upload_id"]):
                        aborted += 1
        except Exception as exc:
            logger.debug("Reconcile/pending: list_multipart falhou para %s: %s", wf.s3_key, exc)

        deleted_ids.append(wf.id)

    if deleted_ids:
        await db.execute(delete(WorkspaceFile).where(WorkspaceFile.id.in_(deleted_ids)))
        await db.commit()
        logger.info(
            "Reconcile/pending: removidos %d WorkspaceFile pending > %dh (multipart abortados: %d).",
            len(deleted_ids), _PENDING_TTL_HOURS, aborted,
        )

    return {"deleted_pending": len(deleted_ids), "aborted_multipart": aborted}


async def abort_stale_multipart_uploads(prefix: str = "") -> dict:
    """Abort multipart uploads older than the TTL, without looking at the DB.

    Covers abandoned multipart uploads that have no corresponding WorkspaceFile
    (e.g. presign failed after starting the multipart). Runs in a thread (boto3 is sync).

    Returns: dict {scanned, aborted}.
    """
    from app.core import storage as _s3

    cutoff = datetime.now(timezone.utc) - timedelta(hours=_MULTIPART_TTL_HOURS)
    scanned = 0
    aborted = 0

    def _scan_sync() -> tuple[int, int]:
        s, a = 0, 0
        for upload in _s3.list_incomplete_multipart_uploads(prefix=prefix):
            s += 1
            initiated = upload.get("initiated")
            if initiated is None:
                continue
            # initiated comes with tzinfo from boto3
            if initiated < cutoff:
                if _s3.abort_multipart_upload(upload["key"], upload["upload_id"]):
                    a += 1
        return s, a

    try:
        scanned, aborted = await asyncio.to_thread(_scan_sync)
    except Exception as exc:
        logger.warning("Reconcile/multipart: falha ao escanear: %s", exc)
        return {"scanned": 0, "aborted": 0}

    if aborted > 0:
        logger.info("Reconcile/multipart: %d abortados (de %d > %dh).",
                    aborted, scanned, _MULTIPART_TTL_HOURS)

    return {"scanned": scanned, "aborted": aborted}


# ── Bug 2: drift report DB vs MinIO ──────────────────────────────────────────

async def compute_storage_drift(db: AsyncSession, sample_prefixes: tuple[str, ...] = ("drive/", "artifacts/")) -> dict:
    """Compare the DB's SUM(size) with the actual sum of objects in MinIO per prefix.

    Does NOT delete anything — only measures and logs. The operator decides what
    to do about the drift via /admin/storage (which exposes these numbers).

    Returns: dict {by_prefix: {prefix: {db_bytes, s3_bytes, s3_objects, drift_bytes}}}.
    """
    from app.core import storage as _s3

    out: dict[str, dict] = {}

    # DB totals (conta tudo, nao filtra workspace)
    drive_db = await db.execute(
        select(func.coalesce(func.sum(WorkspaceFile.size), 0)).where(WorkspaceFile.status == "confirmed")
    )
    drive_db_bytes = int(drive_db.scalar() or 0)

    artifact_db = await db.execute(
        select(func.coalesce(func.sum(Artifact.size_bytes), 0))
    )
    artifact_db_bytes = int(artifact_db.scalar() or 0)

    db_by_prefix = {"drive/": drive_db_bytes, "artifacts/": artifact_db_bytes}

    def _sum_s3_prefix(prefix: str) -> tuple[int, int]:
        total = 0
        count = 0
        for obj in _s3.list_objects(prefix=prefix):
            total += int(obj.get("size", 0))
            count += 1
        return total, count

    for prefix in sample_prefixes:
        try:
            s3_bytes, s3_objects = await asyncio.to_thread(_sum_s3_prefix, prefix)
        except Exception as exc:
            logger.warning("Reconcile/drift: falha ao listar prefixo '%s': %s", prefix, exc)
            continue
        db_bytes = db_by_prefix.get(prefix, 0)
        out[prefix] = {
            "db_bytes": db_bytes,
            "s3_bytes": s3_bytes,
            "s3_objects": s3_objects,
            "drift_bytes": s3_bytes - db_bytes,
        }

    if out:
        logger.info("Reconcile/drift: %s", out)
    return {"by_prefix": out}


# ── Bug 5 e 8: auditoria de orfaos (so conta + loga) ─────────────────────────

async def count_orphaned_workspace_artifacts(db: AsyncSession) -> int:
    """Count Artifacts whose workspace_id no longer exists in `workspaces`.

    The previous version filtered `workspace_id IS NULL` on a column declared
    NOT NULL (see app/models/artifact.py) — so it always returned 0 and the
    audit never flagged anything, while the real orphans showed up on the panel
    labeled "(sem workspace)" (no workspace).

    The real orphan is REFERENTIAL: the artifact points to a workspace that no
    longer exists (purged) or that is in the trash. Practical effect: nobody can
    access them anymore — verify_workspace_access never matches, because a
    soft-deleted workspace is not included in get_user_workspace_ids.

    Audit only — does not delete.
    """
    from app.models.workspace import Workspace

    result = await db.execute(
        select(func.count(Artifact.id))
        .outerjoin(Workspace, Workspace.id_hash == Artifact.workspace_id)
        .where(or_(Workspace.id_hash.is_(None), Workspace.deleted_at.isnot(None)))
    )
    return int(result.scalar() or 0)


async def count_orphaned_pinned_artifacts(db: AsyncSession) -> int:
    """Count pinned Artifacts whose workflow_hash no longer exists.

    Pinned Artifacts escape the periodic cleanup (Artifact.is_pinned == False
    in the artifact_cleanup filter). If the workflow is deleted, those pinned
    ones become orphans consuming disk.
    """
    valid_hashes = select(Workflow.id_hash)
    result = await db.execute(
        select(func.count(Artifact.id))
        .where(Artifact.is_pinned == True)  # noqa: E712
        .where(Artifact.workflow_hash.isnot(None))
        .where(Artifact.workflow_hash.notin_(valid_hashes))
    )
    return int(result.scalar() or 0)


# ── Orquestrador ─────────────────────────────────────────────────────────────

async def run_full_reconciliation() -> dict:
    """Run all the reconciliation jobs in sequence. Returns a summary."""
    summary: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        try:
            summary["fix_null"] = await fix_artifact_null_sizes(db)
        except Exception as exc:
            logger.error("Reconcile/fix_null falhou: %s", exc, exc_info=True)
            summary["fix_null"] = {"error": str(exc)}

        try:
            summary["cleanup_pending"] = await cleanup_pending_workspace_files(db)
        except Exception as exc:
            logger.error("Reconcile/cleanup_pending falhou: %s", exc, exc_info=True)
            summary["cleanup_pending"] = {"error": str(exc)}

        try:
            summary["multipart"] = await abort_stale_multipart_uploads()
        except Exception as exc:
            logger.error("Reconcile/multipart falhou: %s", exc, exc_info=True)
            summary["multipart"] = {"error": str(exc)}

        try:
            summary["drift"] = await compute_storage_drift(db)
        except Exception as exc:
            logger.error("Reconcile/drift falhou: %s", exc, exc_info=True)
            summary["drift"] = {"error": str(exc)}

        try:
            orphan_ws = await count_orphaned_workspace_artifacts(db)
            orphan_pin = await count_orphaned_pinned_artifacts(db)
            summary["audit"] = {
                "orphaned_workspace_artifacts": orphan_ws,
                "orphaned_pinned_artifacts": orphan_pin,
            }
            if orphan_ws > 0:
                logger.warning(
                    "Reconcile/audit: %d artifact(s) apontam para workspace inexistente "
                    "(workspace deletado) — inacessiveis e ocupando disco.", orphan_ws,
                )
            if orphan_pin > 0:
                logger.warning("Reconcile/audit: %d artifacts pinned orfaos (workflow removido).", orphan_pin)
        except Exception as exc:
            logger.error("Reconcile/audit falhou: %s", exc, exc_info=True)
            summary["audit"] = {"error": str(exc)}

    return summary


async def run_reconciliation_loop() -> None:
    """Infinite loop. Started in the API lifespan; a Redis lock ensures 1 worker per cycle."""
    await laco_periodico(
        "Reconciliacao de storage", _RECONCILE_INTERVAL, run_full_reconciliation, lock=_RECONCILE_LOCK_KEY
    )
