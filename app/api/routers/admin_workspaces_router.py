# app/api/routers/admin_workspaces_router.py
"""
Workspace trash — restore or discard soft-deleted workspaces.

Admin-only by product decision: the owner does the soft delete (DELETE
/workspaces/{id}), but only the platform administrator sees the trash and
decides the outcome. That is why the listing does NOT filter by owner_id — the admin
sees what any user deleted.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_admin
from app.core.utils.logger import get_logger
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workspace import Workspace

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/workspaces",
    tags=["admin", "workspaces"],
    dependencies=[Depends(require_admin)],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class WorkspaceTrashOut(BaseModel):
    id_hash: str
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    deleted_at: str
    workflows: int = 0   # how many workflows come back if this workspace is restored


class WorkspacePolicyAdminOut(BaseModel):
    """One row of the "Piso de isolamento" (isolation floor) admin screen: what the admin
    needs to decide where to set `no_pool` — and to see who would be left unable to run."""
    id_hash: str
    name: str
    is_default: bool = False
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
    mode: str                       # pool | isolated | dedicated_pool
    isolation_floor: str
    fallback_terminal: str
    effective_terminal: str
    primary_count: int = 0
    fallback_count: int = 0


class PurgeWorkspaceRequest(BaseModel):
    confirm: str = Field(
        ..., description="Repita o id_hash do workspace — guarda contra clique acidental.",
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_deleted_workspace(id_hash: str, db: AsyncSession) -> Workspace:
    """Workspace that is in the trash, or 404.

    No owner check — this router is admin-only. Requiring `deleted_at`
    to be set is what prevents restoring/purging a live workspace by mistake.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.isnot(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado na lixeira.")
    return ws


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/policies", response_model=List[WorkspacePolicyAdminOut],
            summary="[Admin] Política de execução de todos os workspaces vivos")
async def list_workspace_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Only the tier counts, not the executors: that is enough for the
    mode (the same computation as `mode_of`) and for the admin to see, before setting
    the floor, who would be left without a primary executor."""
    from app.models.workspace_executor import WorkspaceExecutor
    from app.services import workspace_executor_service as politica

    ws_rows = (await db.execute(
        select(Workspace).where(Workspace.deleted_at.is_(None)).order_by(Workspace.name)
    )).scalars().all()

    contagem = (await db.execute(
        select(WorkspaceExecutor.workspace_id, WorkspaceExecutor.tier, sa_func.count())
        .group_by(WorkspaceExecutor.workspace_id, WorkspaceExecutor.tier)
    )).all()
    by_ws: dict[str, dict[int, int]] = {}
    for ws_id, tier, n in contagem:
        by_ws.setdefault(ws_id, {})[int(tier)] = int(n)

    owner_ids = {w.owner_id for w in ws_rows if w.owner_id}
    donos: dict[str, str] = {}
    if owner_ids:
        for id_hash, username in (await db.execute(
            select(User.id_hash, User.username).where(User.id_hash.in_(owner_ids))
        )).all():
            donos[id_hash] = username

    saida: list[WorkspacePolicyAdminOut] = []
    for w in ws_rows:
        tiers = by_ws.get(w.id_hash, {})
        principais = tiers.get(politica.TIER_PRIMARY, 0)
        floor = w.isolation_floor or politica.FLOOR_NONE
        terminal = w.fallback_terminal or politica.TERMINAL_FAIL
        saida.append(WorkspacePolicyAdminOut(
            id_hash=w.id_hash,
            name=w.name,
            is_default=bool(getattr(w, "is_default", False)),
            owner_id=w.owner_id,
            owner_username=donos.get(w.owner_id) if w.owner_id else None,
            mode=politica.mode_of(principais > 0, floor, terminal),
            isolation_floor=floor,
            fallback_terminal=terminal,
            effective_terminal=politica.effective_terminal_of(floor, terminal),
            primary_count=principais,
            fallback_count=tiers.get(politica.TIER_FALLBACK, 0),
        ))
    return saida


@router.get("/trash", response_model=List[WorkspaceTrashOut], summary="[Admin] Listar workspaces na lixeira")
async def list_deleted_workspaces(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """All soft-deleted workspaces on the platform, from newest to oldest."""
    # LEFT OUTER JOIN: owner_id is nullable and has no FK to users, so an
    # INNER JOIN would hide precisely the orphan workspaces — the ones that
    # matter most to the admin.
    result = await db.execute(
        select(Workspace, User.username, User.email)
        .outerjoin(User, User.id_hash == Workspace.owner_id)
        .where(Workspace.deleted_at.isnot(None))
        .order_by(Workspace.deleted_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    if not rows:
        return []

    # How many workflows come back on restore: only those that went down together with
    # the workspace, matched by the shared deleted_at. Counting all deleted ones
    # would inflate the number with workflows deleted individually earlier,
    # which the restore does not bring back.
    counts = dict((await db.execute(
        select(Workflow.workspace_id, sa_func.count(Workflow.id))
        .join(Workspace, Workspace.id_hash == Workflow.workspace_id)
        .where(
            Workflow.workspace_id.in_([ws.id_hash for ws, _, _ in rows]),
            Workflow.deleted_at == Workspace.deleted_at,
        )
        .group_by(Workflow.workspace_id)
    )).all())

    return [
        WorkspaceTrashOut(
            id_hash=ws.id_hash,
            name=ws.name,
            description=ws.description,
            owner_id=ws.owner_id,
            owner_username=username,
            owner_email=email,
            deleted_at=ws.deleted_at.isoformat(),
            workflows=int(counts.get(ws.id_hash, 0)),
        )
        for ws, username, email in rows
    ]


@router.post("/{id_hash}/restore", summary="[Admin] Restaurar workspace da lixeira")
async def restore_workspace(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Takes the workspace out of the trash and brings back the workflows that went down with it.

    The workflows come back DEACTIVATED, and the schedules stay off: the
    cascading delete does not record who was already deactivated before, so
    turning everything back on would reactivate precisely what the owner had turned
    off on purpose. The owner reactivates whatever still makes sense.
    """
    ws = await _get_deleted_workspace(id_hash, db)

    from app.services.workflow_service import restore_workspace_workflows
    restored = await restore_workspace_workflows(db, id_hash, ws.deleted_at)

    ws.deleted_at = None
    await db.commit()
    logger.info(
        "Admin '%s' restaurou o workspace '%s' (dono=%s, %d workflow(s) devolvido(s))",
        current_user.username, id_hash, ws.owner_id, restored,
    )
    return {
        "workspace_id": id_hash,
        "workflows_restored": restored,
        "detail": (
            f"{restored} workflow(s) devolvido(s) ao workspace. Eles voltam "
            "desativados, assim como os agendamentos — reative manualmente."
        ),
    }


@router.post("/{id_hash}/purge", status_code=204, summary="[Admin] Remover workspace definitivamente")
async def purge_workspace(
    id_hash: str,
    payload: PurgeWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hard delete — removes the row for good. Requires the workspace to be in the trash.

    The requirement is deliberate: purging directly would mean losing in one click
    what the soft delete exists to protect. Members go away via FK CASCADE.

    `confirm` repeats the id_hash because the button sits next to each row of the
    table, and now over other users' workspaces.
    """
    if payload.confirm != id_hash:
        raise HTTPException(status_code=400, detail="Confirmação não confere com o id_hash.")

    ws = await _get_deleted_workspace(id_hash, db)

    # The workflows keep pointing to the id_hash after the hard delete — with no
    # FK, nothing removes them. They are already soft-deleted by the delete, so they
    # do not run again; their final cleanup is outside this endpoint (the
    # history of runs and metrics still references these hashes).
    #
    # The storage expiration here is a safety net: the workspace DELETE already
    # ran the same helper, so in practice it is usually a no-op. It covers the case
    # where purge_expired_artifacts has not run yet when the row disappears — without
    # it the artifacts become nameless orphans in /admin/storage.
    from app.services.storage_purge_service import schedule_workspace_data_expiry
    scheduled = await schedule_workspace_data_expiry(db, id_hash)

    await db.delete(ws)
    await db.commit()
    logger.warning(
        "Admin '%s' purgou definitivamente o workspace '%s' (dono=%s; agendados p/ "
        "remoção: %d artefato(s), %d arquivo(s) do Drive)",
        current_user.username, id_hash, ws.owner_id,
        scheduled["artifacts"], scheduled["drive_files"],
    )


# ── Isolation floor (spec §4.5, Q10) ───────────────────────────────────────────

class IsolationFloorUpdate(BaseModel):
    floor: str = Field(..., pattern="^(none|no_pool)$")


@router.put("/{id_hash}/isolation-floor", summary="[Admin] Piso de isolamento do workspace")
async def set_isolation_floor(
    id_hash: str,
    payload: IsolationFloorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """`no_pool` forbids the fallback to the shared pool: the terminal is
    forced to `fail` and the workspace owner/admin cannot loosen it (the API
    refuses with 403 and dispatch reads the floor). Only the platform admin writes it —
    it is what restores a hard guarantee where it is an external requirement."""
    from app.services import workspace_executor_service as politica
    from app.services.execution_alert_service import notify_floor_forced

    result = await db.execute(
        select(Workspace).where(Workspace.id_hash == id_hash, Workspace.deleted_at.is_(None))
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    forced = await politica.set_floor(db, ws, payload.floor, actor_id=current_user.id_hash)
    # Only notify those who have a primary tier: without a dedicated one, "is now isolated"
    # describes nothing the owner would recognize.
    if forced and (await politica.load_policy(db, ws)).has_primary:
        try:
            await notify_floor_forced(db, ws)
        except Exception as exc:  # best-effort
            logger.warning("Falha ao avisar o dono do piso em '%s': %s", id_hash, exc)
    logger.info("Admin '%s' definiu piso '%s' no workspace '%s' (terminal forçado: %s).",
                current_user.username, payload.floor, id_hash, forced)
    return {
        "workspace_id": id_hash,
        "isolation_floor": ws.isolation_floor,
        "fallback_terminal": ws.fallback_terminal,
        "terminal_forced_to_fail": forced,
    }
