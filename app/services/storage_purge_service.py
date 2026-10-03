# app/services/storage_purge_service.py
"""
Per-workspace storage purge (Drive + Artifacts).

Two uses:

1. **Admin button** in /admin/storage — frees space for an active workspace,
   or cleans up the orphans left by an already deleted workspace.
2. **DELETE /workspaces/{id}** — before, the hard delete did not touch the data, and the
   artifacts were left pointing to a nonexistent workspace: inaccessible
   (`verify_workspace_access` never matches) and taking up disk forever.

Artifacts go out through `remocao_de_artefatos.remove_artifacts`, the same rule
as the delete routes and retention: MinIO object first (a failure keeps the
row, and repeating the purge fixes it), local content only with the order DELIVERED to the
executor (offline keeps the row and the next pass resends), portal layer
along with it. Here we only add up the counters.

A cataloged Drive file (`content_location='executor'`) does NOT follow these
semantics, and the difference is deliberate: it is the user's own file,
in a folder they chose to sync, whose bytes the platform never had
and which takes up no storage. `drive_service._refuse_if_cataloged` refuses
to delete it in a standalone deletion; here it is preserved and counted in
`skipped_catalogados`.
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.workspace_file import WorkspaceFile
from app.services.remocao_de_artefatos import remove_artifacts

logger = get_logger(__name__)

SCOPES = ("all", "artifacts", "drive")


async def purge_workspace_storage(
    db: AsyncSession, workspace_id: str, *, scope: str = "all",
) -> dict:
    """Removes objects from MinIO and the corresponding rows. IRREVERSIBLE.

    `scope`: "all" | "artifacts" | "drive".
    Returns counters of what was actually removed and what was left pending
    due to an S3 failure (those are retryable: just repeat the purge).
    """
    if scope not in SCOPES:
        raise ValueError(f"scope inválido: {scope!r}. Use um de {SCOPES}.")

    from app.core import storage as s3

    removed = {
        "workspace_id":     workspace_id,
        "scope":            scope,
        "artifacts":        0,
        "artifact_bytes":   0,
        "drive_files":      0,
        "drive_bytes":      0,
        "skipped_s3_errors": 0,
        # Local artifacts whose removal order was not delivered (executor
        # offline): the row stays, and the next pass tries again.
        "pending_executor": 0,
        # Local artifacts without executor_id/local_path — no trace of where to
        # send the order; the row stays so as not to lose the file's record.
        "skipped_sem_rastro": 0,
        # Drive files cataloged on the executor: preserved by policy.
        "skipped_catalogados": 0,
        # Pin references cleared in the workspace's workflows: the pin-cache
        # objects drop along with the other artifacts, and the dangling ref would be
        # a permanent 404. Clearing (instead of removing) preserves the pin
        # intent — pin_metadata stays — and the next run rewrites the cache on its own.
        "pins_resetados": 0,
    }

    # ── Artefatos ─────────────────────────────────────────────────────────────
    if scope in ("all", "artifacts"):
        result = await db.execute(select(Artifact).where(Artifact.workspace_id == workspace_id))
        remocao = await remove_artifacts(db, result.scalars().all(), schedule_pending=False)
        removed["artifacts"] += len(remocao.apagados)
        removed["artifact_bytes"] += remocao.bytes
        removed["skipped_s3_errors"] += len(remocao.falhas_s3)
        removed["pending_executor"] += len(remocao.pendentes_local)
        removed["skipped_sem_rastro"] += len(remocao.sem_rastro)

        # Pins of this workspace's workflows: the pin-cache objects have just
        # been deleted from MinIO (right above), so every `__pin_s3_key__` ref
        # left over points to nothing — a 404 on every following run, and since
        # auto-pin only fires with an EMPTY ref, the breakage did not resolve itself.
        # Clears the ref and keeps pin_metadata: the pin intent survives and the
        # next run rewrites the cache under a new key.
        from sqlalchemy.orm.attributes import flag_modified
        from app.models.workflow import Workflow

        wf_result = await db.execute(
            select(Workflow).where(Workflow.workspace_id == workspace_id)
        )
        for wf in wf_result.scalars():
            pins = wf.pinned_outputs
            if not isinstance(pins, dict):
                continue
            zerados = {
                nid for nid, ref in pins.items()
                if isinstance(ref, dict) and "__pin_s3_key__" in ref
            }
            if not zerados:
                continue
            wf.pinned_outputs = {
                nid: ({} if nid in zerados else ref) for nid, ref in pins.items()
            }
            flag_modified(wf, "pinned_outputs")
            removed["pins_resetados"] += len(zerados)

    # ── Drive ─────────────────────────────────────────────────────────────────
    if scope in ("all", "drive"):
        result = await db.execute(
            select(WorkspaceFile).where(WorkspaceFile.workspace_id == workspace_id)
        )
        files = result.scalars().all()

        ids = []
        for wf in files:
            # CATALOGED file (GeoSync "manter apenas no executor", keep only on the
            # executor): the platform never had the bytes, and the file is in the folder the
            # user themselves chose to sync. Deleting the row would remove
            # nothing and would destroy the only record of the link; telling the
            # executor to delete it would destroy user data that never
            # belonged to the platform. It is the same refusal that
            # `drive_service._refuse_if_cataloged` applies in a standalone deletion —
            # here the record used to be deleted silently, contradicting that
            # policy. It also takes up no platform storage at all,
            # so preserving it does not conflict with the purpose of the purge.
            if getattr(wf, "content_location", "minio") == "executor":
                removed["skipped_catalogados"] += 1
                continue
            if wf.s3_key:
                try:
                    await s3.delete_strict_async(wf.s3_key, allow_missing=True)
                except Exception as exc:
                    logger.warning(
                        "Purge: mantendo arquivo %s no banco (S3 falhou: %s).", wf.s3_key, exc,
                    )
                    removed["skipped_s3_errors"] += 1
                    continue
            ids.append(wf.id)
            removed["drive_files"] += 1
            removed["drive_bytes"] += int(wf.size or 0)

        if ids:
            await db.execute(delete(WorkspaceFile).where(WorkspaceFile.id.in_(ids)))

    await db.commit()
    logger.warning(
        "Purge de armazenamento no workspace '%s' (scope=%s): %d artefato(s) e %d arquivo(s) "
        "removidos, %d pendente(s) por falha no S3.",
        workspace_id, scope, removed["artifacts"], removed["drive_files"],
        removed["skipped_s3_errors"],
    )
    return removed


async def schedule_workspace_data_expiry(db: AsyncSession, workspace_id: str) -> dict:
    """Marks the workspace's data for removal by the global cleanup.

    Used in the workspace DELETE. We prefer `expires_at` to deleting right away:
    it gives a window for second thoughts and reuses `purge_expired_artifacts`, which already
    handles MinIO, PortalLayer and retry on S3 failure.

    Drive files have no expiration column, so they are purged
    immediately — leaving them would keep in MinIO data that nobody can
    list anymore (the listing is always per workspace).
    """
    now = utc_now_naive()

    artifacts = (await db.execute(
        select(func.count(Artifact.id)).where(Artifact.workspace_id == workspace_id)
    )).scalar() or 0

    # Expires immediately: the cleanup runs periodically and does the actual removal.
    await db.execute(
        Artifact.__table__.update()
        .where(Artifact.workspace_id == workspace_id)
        .values(expires_at=now)
    )

    drive = await purge_workspace_storage(db, workspace_id, scope="drive")

    return {"artifacts": int(artifacts), "drive_files": drive["drive_files"]}
