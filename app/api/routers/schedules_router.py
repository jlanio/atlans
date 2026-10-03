from fastapi import APIRouter, Depends, Request

from app.schemas.schedule import ScheduleRead, ScheduleUpdate
from app.services.schedule_service import ScheduleService
from app.api.dependencies import (
    get_schedule_service,
    workflow_com_papel,
)
from app.core.rate_limiter import limiter
from app.core.rbac import ROLE_OPERATOR

router = APIRouter(
    prefix="/workflows/{id_hash}/schedules",
    tags=["schedules"]
)


# Role 'operator' or higher. Scheduling is running: a schedule with a 1-minute
# interval triggers the workflow with the owner's credentials indefinitely.
# These routes once depended only on workspace membership — and a 'viewer'
# member created schedules and deleted production ones, exactly what the 403
# of POST /workflows/{id}/execute exists to prevent. rbac.py already defines
# operator as the one who "runs workflows and manages schedules".
#
# Today only the PUT remains (pause/resume, on Home): schedules are born from the
# ScheduleTrigger node when the workflow is saved, and MCP uses ScheduleService directly.
# Listing, creating and deleting through here were removed — they had no caller.
_MANAGE_SCHEDULES = workflow_com_papel(
    ROLE_OPERATOR, "Requer role 'operator' ou superior para gerenciar agendamentos.",
)


@router.put("/{job_id}", response_model=ScheduleRead)
@limiter.limit("20/minute")
async def update_schedule(
    request: Request,
    job_id: str,
    schedule_in: ScheduleUpdate,
    service: ScheduleService = Depends(get_schedule_service),
    wf=Depends(_MANAGE_SCHEDULES),
):
    return await service.update_schedule(job_id, schedule_in, owner_workflow_hash=wf.id_hash)
