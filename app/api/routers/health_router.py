# app/api/routers/health_router.py
"""
Administrative endpoints: webhook whitelist and storage (usage and purge).
All require the admin role.
"""
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func, or_ as sa_or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

from app.api.dependencies import get_current_user, get_db, require_admin
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.artifact import Artifact
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-health"], dependencies=[Depends(require_admin)])


# ── Helpers ────────────────────────────────────────────────────────────────────
# get_config/set_config were moved to app/core/system_config.py for reuse
# by other admin modules (disabled_nodes_service etc.). Aliases kept as
# wrappers to keep the rest of the file unchanged.

from app.core.system_config import get_config as _get_config  # noqa: E402
from app.core.system_config import set_config as _set_config  # noqa: E402


# ── Webhook whitelist (/admin/health) ─────────────────────────────────────────

@router.get("/health", summary="Whitelist de domínios para webhook")
async def system_health(db: AsyncSession = Depends(get_db)):
    """Only the whitelist: it is what the Settings screen reads.

    The EFFECTIVE list, the same one the trigger applies (`valid_patterns`): an
    entry saved before validation that would never match (`*`, URL with a path)
    does not appear as a restriction, and the screen shows "sem restrição" (no
    restriction) when that is the case.

    The route also computed Redis INFO, the results dead-letter and the stuck
    runs (old criterion, running > 1 h) — none of that had a screen.
    The truly stuck ones are those on the Dashboard, at /observability/metrics.
    """
    from app.core.utils.allowlist import valid_patterns

    gravada = await _get_config(db, "webhook_whitelist", default=[]) or []
    return {"webhook_whitelist": valid_patterns(gravada)}


@router.patch("/health/webhook-whitelist", summary="Atualiza whitelist de domínios para webhook")
async def update_webhook_whitelist(
    domains: List[str] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Sets the list of domains allowed for workflow webhook notifications.
    Empty list = no restriction (any URL is accepted). With items, the webhook
    host must be in it (and in the workspace allowlist, when there is one) —
    applied at trigger time, in `run_result_consumer._fire_notification_if_configured`.
    """
    from app.core.utils.allowlist import normalize_domain, split_domains, validate_allowlist

    # A pasted URL becomes the HOST (as before: no scheme, path or port), and
    # what the matcher would ignore — `*`, `localhost` — is rejected with 400, the same
    # rule as the workspace allowlist. Now the list is applied at trigger time: a
    # silently accepted `*` would block every webhook on the platform.
    try:
        cleaned = validate_allowlist([normalize_domain(x) for x in split_domains(domains)])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _set_config(db, "webhook_whitelist", cleaned)
    return {"webhook_whitelist": cleaned}


# ── Armazenamento (MinIO) ─────────────────────────────────────────────────────

@router.get("/storage", summary="Uso de armazenamento por workspace (Drive + Artefatos)")
async def storage_usage(db: AsyncSession = Depends(get_db)):
    """
    Returns storage consumption aggregated per workspace,
    querying workspace_files.size and artifacts.size_bytes.

    Includes tracking health indicators — without that visibility the report
    drifts silently when something escapes the normal path (NULL sizes,
    stale pending, a failed delete leaving an orphan in S3).
    """
    # Drive: groups by workspace_id (confirmed only — pending goes in a
    # separate bucket below).
    drive_agg = await db.execute(
        select(
            WorkspaceFile.workspace_id,
            sa_func.coalesce(sa_func.sum(WorkspaceFile.size), 0).label("bytes"),
            sa_func.count(WorkspaceFile.id).label("files"),
        )
        .where(WorkspaceFile.status == "confirmed")
        .group_by(WorkspaceFile.workspace_id)
    )
    drive_map: dict[str, dict] = {}
    for row in drive_agg.all():
        drive_map[row.workspace_id] = {"bytes": int(row.bytes), "files": row.files}

    # Artifacts: groups by workspace_id
    artifact_agg = await db.execute(
        select(
            Artifact.workspace_id,
            sa_func.coalesce(sa_func.sum(Artifact.size_bytes), 0).label("bytes"),
            sa_func.count(Artifact.id).label("files"),
        )
        .group_by(Artifact.workspace_id)
    )
    artifact_map: dict[str, dict] = {}
    for row in artifact_agg.all():
        ws_id = row.workspace_id or "__none__"
        artifact_map[ws_id] = {"bytes": int(row.bytes), "files": row.files}

    # ── Tracking health indicators ───────────────────────────────────────────

    # Drive pending: presigned PUT created but not confirmed. Bytes may already
    # be in MinIO without showing up in "confirmed".
    pending_drive_row = await db.execute(
        select(
            sa_func.count(WorkspaceFile.id).label("files"),
            sa_func.coalesce(sa_func.sum(WorkspaceFile.size), 0).label("bytes"),
        ).where(WorkspaceFile.status == "pending")
    )
    pending_drive = pending_drive_row.one()

    # Artifacts with NULL size_bytes: s3.head() failed in the consumer. Contributes 0
    # to the total but the object may exist in MinIO. The
    # storage_reconciliation.fix_artifact_null_sizes job fills them periodically.
    null_size_row = await db.execute(
        select(sa_func.count(Artifact.id)).where(Artifact.size_bytes.is_(None))
    )
    null_size_artifacts = int(null_size_row.scalar() or 0)

    # Too old for the reconciliation retry: if the object existed in
    # MinIO, one of the dozens of attempts would already have filled the size. Two
    # cases remain, both permanent: the upload never reached MinIO, or the
    # artifact stayed on the executor's disk (local s3_key, via fallback when the
    # executor cannot reach MinIO).
    from app.core.storage_reconciliation import NULL_SIZE_RETRY_WINDOW_DAYS
    from app.core.utils.datetime_utils import utc_now_naive
    _cutoff = utc_now_naive() - timedelta(days=NULL_SIZE_RETRY_WINDOW_DAYS)
    unrecoverable_row = await db.execute(
        select(sa_func.count(Artifact.id)).where(
            Artifact.size_bytes.is_(None),
            Artifact.created_at < _cutoff,
        )
    )
    unrecoverable_size_artifacts = int(unrecoverable_row.scalar() or 0)

    # Artifacts whose workspace was purged (row missing) or is in the
    # trash — in both cases nobody accesses them anymore, because a soft-deleted
    # workspace does not enter get_user_workspace_ids. The previous version
    # filtered `workspace_id IS NULL` on a NOT NULL column, so it always measured 0
    # and never flagged the orphans that appeared in the table as "(sem workspace)".
    orphan_ws_row = await db.execute(
        select(sa_func.count(Artifact.id))
        .outerjoin(Workspace, Workspace.id_hash == Artifact.workspace_id)
        .where(sa_or_(Workspace.id_hash.is_(None), Workspace.deleted_at.isnot(None)))
    )
    orphaned_workspace_artifacts = int(orphan_ws_row.scalar() or 0)

    # Enrich with names
    ws_result = await db.execute(select(Workspace))
    ws_by_id = {w.id_hash: w for w in ws_result.scalars().all()}

    user_result = await db.execute(select(User))
    users_by_id = {u.id_hash: u for u in user_result.scalars().all()}

    all_ws_ids = set(drive_map.keys()) | set(artifact_map.keys())

    total_drive_bytes = 0
    total_artifact_bytes = 0
    total_drive_files = 0
    total_artifact_files = 0
    by_ws = []

    for ws_id in all_ws_ids:
        d = drive_map.get(ws_id, {"bytes": 0, "files": 0})
        a = artifact_map.get(ws_id, {"bytes": 0, "files": 0})
        ws = ws_by_id.get(ws_id)
        owner = users_by_id.get(ws.owner_id) if ws else None

        total_drive_bytes += d["bytes"]
        total_artifact_bytes += a["bytes"]
        total_drive_files += d["files"]
        total_artifact_files += a["files"]

        # Three states, not two. With soft delete the row still exists,
        # so `ws is None` (the old test) left the workspace in the trash without
        # a marker — while orphaned_workspace_artifacts already counted it. The
        # operator read "N artifacts from a deleted workspace" and could not find the row.
        # The old label ("sem workspace") also suggested a NULL workspace_id,
        # which the NOT NULL column does not even allow.
        if ws is None:
            ws_state, ws_name = "purged", "(workspace removido)"
        elif ws.deleted_at is not None:
            ws_state, ws_name = "trashed", ws.name
        else:
            ws_state, ws_name = "active", ws.name

        by_ws.append({
            "workspace_id": ws_id,
            "workspace_name": ws_name,
            "workspace_state": ws_state,          # active | trashed | purged
            "workspace_deleted": ws_state != "active",
            "owner_username": owner.username if owner else "?",
            "drive_bytes": d["bytes"],
            "drive_files": d["files"],
            "artifacts_bytes": a["bytes"],
            "artifact_files": a["files"],
            "total_bytes": d["bytes"] + a["bytes"],
        })

    by_ws.sort(key=lambda x: x["total_bytes"], reverse=True)

    return {
        "totals": {
            "drive_bytes": total_drive_bytes,
            "artifacts_bytes": total_artifact_bytes,
            "total_bytes": total_drive_bytes + total_artifact_bytes,
            "drive_files": total_drive_files,
            "artifact_files": total_artifact_files,
        },
        "tracking_health": {
            # Pending drive: bytes possibly in MinIO but not confirmed.
            # Reconcile/cleanup_pending_workspace_files cleans up after the TTL.
            "pending_drive_files": int(pending_drive.files or 0),
            "pending_drive_bytes": int(pending_drive.bytes or 0),
            # Artefatos sem tamanho conhecido. Reconcile/fix_artifact_null_sizes
            # tenta preencher enquanto forem recentes.
            "null_size_artifacts": null_size_artifacts,
            # Subset of the previous one: too old for the retry — the object
            # does not exist in MinIO (upload failed) or stayed on the executor's disk
            # (local fallback). They do not resolve on their own.
            "unrecoverable_size_artifacts": unrecoverable_size_artifacts,
            # Artefatos cujo workspace foi deletado: inacessiveis e ocupando disco.
            "orphaned_workspace_artifacts": orphaned_workspace_artifacts,
        },
        "by_workspace": by_ws,
    }


# ── Storage purge per workspace ──────────────────────────────────────────────

class PurgeStorageRequest(BaseModel):
    scope: str = Field(
        "all", pattern="^(all|artifacts|drive)$",
        description="all | artifacts | drive",
    )
    confirm: str = Field(
        ..., description="Repita o workspace_id — guarda contra clique acidental.",
    )


@router.post(
    "/storage/workspaces/{workspace_id}/purge",
    summary="[Admin] Purgar Drive e/ou Artefatos de um workspace",
)
async def storage_purge(
    workspace_id: str,
    payload: PurgeStorageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Removes objects from MinIO and the database rows. IRREVERSIBLE.

    Also accepts the id of an already deleted workspace — this is how the
    orphans that appear in /admin/storage as "(workspace deletado)" are cleaned up.

    `confirm` must repeat the workspace_id: the button sits next to each
    table row and a misclick would erase the neighboring workspace's data.
    """
    if payload.confirm != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="Confirmação não confere com o workspace_id.",
        )

    from app.services.storage_purge_service import purge_workspace_storage

    result = await purge_workspace_storage(db, workspace_id, scope=payload.scope)
    logger.warning(
        "Admin '%s' purgou armazenamento do workspace '%s' (scope=%s): "
        "%d artefato(s), %d arquivo(s) do Drive.",
        current_user.username, workspace_id, payload.scope,
        result["artifacts"], result["drive_files"],
    )
    return result
