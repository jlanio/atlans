# app/api/routers/admin_workflows_router.py
"""
Administrative endpoints for workflow management.

Scope: the global admin has an override — can read/mutate a workflow of any
workspace even without membership. This lets the admin:

  - Deactivate misconfigured workflows (broken schedule, webhook
    pointing to nothing, infinite loop), preventing dispatch, schedule
    and webhook without having to delete the workflow or ask the owner.

Auditing: each change produces a structured `logger.info` (who, what,
workflow, owner). There is no persisted column — the history stays in
stdout/Loki. If compliance requires an auditable trail, a future extension
adds an `audit_events` table.

Conscious trade-off: the owner can reactivate via `PUT /workflows/{id}`
(update of their own workflow in `/projects`), overriding the admin's
action. Accepted behavior — if it becomes a real problem, migrate to a
dedicated `admin_disabled_at` column in a future iteration.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.core.scheduling.hooks import sync_schedules_with_workflow_state
from app.core.utils.logger import get_logger
from app.crud.workflow_crud import WorkflowCRUD

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/workflows",
    tags=["admin", "workflows"],
    dependencies=[Depends(require_admin)],
)


class SetWorkflowStatusBody(BaseModel):
    flag_ative: bool


@router.put(
    "/{id_hash}/status",
    summary="[Admin] Alterar flag_ative de um workflow (bypassa membership de workspace)",
)
async def set_workflow_status(
    id_hash: str,
    payload: SetWorkflowStatusBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Toggles `Workflow.flag_ative`. Unlike the owner user's
    `PUT /workflows/{id}`, this endpoint does NOT check `_has_min_workspace_role`
    — the global admin has an override on any workspace.
    """
    wf = await WorkflowCRUD(db).get_by_hash(id_hash)
    if wf is None or wf.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado.")

    old_value = bool(wf.flag_ative)
    wf.flag_ative = payload.flag_ative
    await db.commit()

    if old_value != payload.flag_ative:
        # Deactivating the workflow without turning off its schedules left the
        # AsyncScheduler firing in a loop against a workflow that refuses to
        # run. Best-effort: failing here does not undo the admin's decision, which
        # is already committed — and the scheduler itself ignores schedules of
        # inactive workflows thanks to the JOIN in `_tick`.
        try:
            await sync_schedules_with_workflow_state(wf, db)
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar agendamentos do workflow '%s' apos mudanca de flag_ative: %s",
                wf.id_hash, exc,
            )

        logger.info(
            "Admin '%s' alterou flag_ative de workflow '%s' (dono='%s') de %s para %s",
            current_user.username,
            wf.id_hash,
            wf.created_by_id,
            old_value,
            payload.flag_ative,
        )

    return {"id_hash": wf.id_hash, "flag_ative": bool(wf.flag_ative)}
