# app/api/routers/me_router.py
"""Routes of the "Mine" scope: slices per PERSON, across all of their workspaces.

Own `/me` prefix on purpose. `GET /workflows/schedules` would be shadowed
by `GET /workflows/{id_hash}` (`schedules` would land as an `id_hash`), and
today's schedule routes are nested under `/workflows/{id}/schedules` — per
workflow, not per person. The owner's cross-cutting listing has no home among them.
"""
from typing import List

from fastapi import APIRouter, Depends, Request

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_user_workspace_ids
from app.core.rate_limiter import limiter
from app.models.models import Schedule, Workflow
from app.schemas.me import MySchedule
from app.services.schedule_service import list_schedules_for

router = APIRouter(prefix="/me", tags=["me"])

# The same ceiling as the Home collection (`useAcervo`): the sidebar panel does not
# virtualize, and a large installation would return hundreds of rows per response.
DEFAULT_LIMIT = 200
MAX_LIMIT = 500


class MySchedules(BaseModel):
    """Page + TOTAL, the same envelope as `ConversationList` (`GET /assistente/conversas`).

    The ceiling alone truncated silently: the web received 200 rows and had no way
    to know there were more. With the total it draws the "Ver mais" (See more)
    footer — and the response pattern of the Home lists (Chats, Collection) becomes one.
    """

    itens: List[MySchedule]
    total: int


@router.get(
    "/schedules",
    response_model=MySchedules,
    summary="Agendamentos da pessoa, entre todos os seus workspaces",
)
@limiter.limit("60/minute")
async def meus_agendamentos(
    request: Request,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """All schedules of the user's workspaces, active and paused,
    ordered by next run. Writing (pause/activate) stays on the per-workflow
    route `PUT /workflows/{id}/schedules/{job_id}`.

    Paginated and with a limiter because it was the only new listing without a ceiling:
    Chats cuts at 50, Collection at 200, and this one returned the workspaces' entire
    table. The `total` comes along with the page so the ceiling stops being an
    invisible truncation — see `MySchedules`."""
    itens = await list_schedules_for(
        db,
        workspace_ids,
        limit=max(1, min(int(limit), MAX_LIMIT)),
        offset=max(0, int(offset)),
    )
    return MySchedules(itens=itens, total=await _count_schedules(db, workspace_ids))


async def _count_schedules(db: AsyncSession, workspace_ids: List[str]) -> int:
    """How many schedules the page slices — the SAME filter as
    `list_schedules_for` (JOIN with Workflow, not deleted, the actor's workspace).

    The count lives here, and not in the service, because it is the ROUTE's
    envelope that asks for it; the filter is short enough to be repeated without
    risk of silently diverging — any change to the slice breaks the pagination test.
    """
    if not workspace_ids:
        return 0
    total = (
        await db.execute(
            select(func.count(Schedule.id))
            .join(Workflow, Workflow.id_hash == Schedule.workflow_hash)
            .where(
                Workflow.deleted_at.is_(None),
                Workflow.workspace_id.in_(workspace_ids),
            )
        )
    ).scalar()
    return int(total or 0)
