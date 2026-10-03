# app/services/schedule_service.py
# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.schedule_crud import ScheduleCRUD
from app.schemas.schedule import ScheduleCreate
from app.models.models import Schedule, Workflow
from app.core.exceptions import (  # noqa: F401 — ScheduleNotFoundError re-exportado para compatibilidade
    ScheduleNotFoundError,
    InvalidScheduleError,
    WorkflowNotFoundError,
    WorkflowInactiveError,
)


def campos_de_ativacao(ativar: bool) -> dict:
    """Fields to write to the Schedule when turning the schedule on/off.

    Turning it back on clears `next_run_at` on purpose. While the schedule was
    off, the scheduler did not process it and the time stayed stuck in the past —
    turning it back on without clearing it would make `_process_schedule` see
    `now >= next_run_at` and fire the workflow right away, as an invisible side effect of
    flipping a switch. With NULL it recomputes the next FUTURE occurrence and only then
    fires.

    Canonical source for the two paths that turn it on/off without going through the
    definition: the hook (`core/scheduling/hooks.py`, which imports from here) and
    `update_schedule` below (the REST route and the MCP tool).
    """
    return {"active": True, "next_run_at": None} if ativar else {"active": False}


_CAMPOS_DE_HORARIO = ("strategy", "cron_expression", "interval", "unit", "rrule_expression", "timezone")


def _horario_mudou(updates: dict, sch: Schedule) -> bool:
    """True if any timing field PRESENT in `updates` differs from the value
    stored in `sch`.

    Compares only the fields the caller actually sent (the dict comes from
    `ScheduleUpdate.dict(exclude_unset=True)`), so re-saving the same time —
    or editing a non-timing field — does not count as a change.
    """
    return any(
        campo in updates and updates[campo] != getattr(sch, campo)
        for campo in _CAMPOS_DE_HORARIO
    )


def _como_utc(valor: Optional[datetime]) -> Optional[datetime]:
    """`next_run_at`/`last_run_at` are stored as UTC-NAIVE (see `_to_utc_naive` in the
    scheduler). Without tzinfo, Pydantic serializes with no offset and the web reads the time
    as local. Same normalization as `workflow_service._como_utc` — duplicated on
    purpose: importing it from there would close a cycle (workflow_service already imports
    from this module)."""
    if valor is None or valor.tzinfo is not None:
        return valor
    return valor.replace(tzinfo=timezone.utc)


async def listar_agendamentos_de(
    db: AsyncSession, workspace_ids: List[str], *, limit: int = 200, offset: int = 0
) -> List[dict]:
    """All schedules of the user's workspaces, one per row (not one per
    workflow, like the Projects summary). For the Home's "Meu → Agendamentos" (My → Schedules) panel.

    Does NOT filter on `Workflow.origem`, unlike the Projects listings — and the
    divergence is deliberate. An assistant workflow that is SCHEDULED fires
    runs on its own, spends quota and costs money; hiding it here too would
    leave it with no screen at all where it can be seen or paused. That is why it
    shows up with the origin badge (the web draws it) instead of vanishing. The side that
    still needs aligning is Projects, which has the `assistente` parameter on the route but
    does not yet have the toggle on the screen.

    SELECT of COLUMNS, never of the `Schedule` object: `Schedule.workflow` is
    `lazy='raise'`, and fetching the object would risk an access to the relationship that
    would raise. The JOIN with `Workflow` brings the name and `flag_ative` in the same query
    (the schedule's `active` and the workflow's `flag_ative` are the TWO causes of
    "paused" that the web distinguishes). Filters by `Workflow.workspace_id` — never
    by `Schedule.workspace_id`, which `create` does not write.

    Order: active first, then by next run (nulls last — a
    freshly created schedule without `next_run_at` still does not vanish from the top of the active ones).
    """
    if not workspace_ids:
        return []
    stmt = (
        select(
            Schedule.job_id, Schedule.id_hash, Schedule.active, Schedule.strategy,
            Schedule.cron_expression, Schedule.interval, Schedule.unit,
            Schedule.rrule_expression, Schedule.timezone,
            Schedule.next_run_at, Schedule.last_run_at, Schedule.retry_count,
            Schedule.workflow_hash,
            Workflow.name.label("workflow_name"),
            Workflow.flag_ative, Workflow.workspace_id, Workflow.origem,
        )
        .join(Workflow, Workflow.id_hash == Schedule.workflow_hash)
        .where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id.in_(workspace_ids),
        )
        .order_by(
            Schedule.active.desc(),
            Schedule.next_run_at.asc().nulls_last(),
            # Third tie-breaker: without it, two schedules with the
            # same `active`/`next_run_at` can switch pages between requests.
            Schedule.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    linhas = (await db.execute(stmt)).mappings().all()
    return [
        {
            "job_id": r["job_id"],
            "id_hash": r["id_hash"],
            "active": bool(r["active"]),
            "strategy": r["strategy"],
            "cron_expression": r["cron_expression"],
            "interval": r["interval"],
            "unit": r["unit"],
            "rrule_expression": r["rrule_expression"],
            "timezone": r["timezone"],
            "next_run_at": _como_utc(r["next_run_at"]),
            "last_run_at": _como_utc(r["last_run_at"]),
            "retry_count": r["retry_count"],
            "workflow_id": r["workflow_hash"],
            "workflow_name": r["workflow_name"],
            "flag_ative": bool(r["flag_ative"]),
            "workspace_id": r["workspace_id"],
            "origem": r["origem"],
        }
        for r in linhas
    ]


def validate_schedule_create(schedule_in: ScheduleCreate) -> None:
    """Validates a schedule config WITHOUT side effects (raises if invalid).

    Mirrors exactly the checks of `create_schedule` (shallow depth: only
    presence of the fields and 5 fields in the cron — fine syntactic validity is left to
    croniter/dateutil in the scheduler, which already handles errors without bringing down the schedule).

    It exists separately so that `apply_schedule_if_needed` can refuse an invalid
    config BEFORE deleting the current schedule. Before, validation only happened
    inside `create_schedule` — after deleting the existing ones —, so an
    invalid expression deleted the schedule and left it with no replacement (the
    exception is swallowed by the caller: the user saw "saved" and the cron vanished).
    """
    if schedule_in.strategy not in ("cron", "interval", "rrule"):
        raise InvalidScheduleError(f"Strategy inválida: {schedule_in.strategy}")

    if schedule_in.strategy == "cron":
        if not schedule_in.cron_expression:
            raise InvalidScheduleError("cron_expression é obrigatório para strategy='cron'")
        if len(schedule_in.cron_expression.strip().split()) != 5:
            raise InvalidScheduleError("cron_expression deve ter 5 campos: min hour day month dow")
    elif schedule_in.strategy == "interval":
        if schedule_in.interval is None or schedule_in.unit is None:
            raise InvalidScheduleError("Interval strategy requer interval e unit")
    elif schedule_in.strategy == "rrule":
        if not schedule_in.rrule_expression:
            raise InvalidScheduleError("rrule_expression é obrigatório para strategy='rrule'")


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.schedule_crud = ScheduleCRUD(db)

    async def _buscar_workflow(self, id_hash: str) -> Workflow:
        """The workflow, whether active or not. Does NOT authorize anything.

        The caller is the one who authorizes — the routes go through
        `workflow_com_papel(ROLE_OPERATOR)` before getting here. This query
        is the second read, done only to have the object at hand.
        """
        stmt = select(Workflow).where(Workflow.id_hash == id_hash)
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow '{id_hash}' não encontrado.")
        return workflow

    async def _exigir_workflow_ativo(self, id_hash: str) -> Workflow:
        """Likewise, but refuses a deactivated workflow — for whoever is going to WRITE.

        `WorkflowInactiveError` (409), and not `ValueError`: a bare `ValueError`
        has no handler (`app/main.py` registers `AtlasBaseError` and a generic
        `Exception`), so it became a **500** with an internal error message
        for a refusal that is a domain one.
        """
        workflow = await self._buscar_workflow(id_hash)
        if not workflow.flag_ative:
            raise WorkflowInactiveError(
                f"Workflow '{id_hash}' está desativado. Ative-o para gerenciar agendamentos."
            )
        return workflow

    async def create_schedule(self, id_hash: str, schedule_in: ScheduleCreate) -> Schedule:
        workflow = await self._exigir_workflow_ativo(id_hash)

        # Single source of the validation (also used by apply_schedule_if_needed
        # BEFORE deleting the previous schedule).
        validate_schedule_create(schedule_in)

        # Clears the fields that do not belong to the chosen strategy — the
        # ScheduleTrigger node sends the defaults of all of them.
        if schedule_in.strategy == "cron":
            schedule_in.interval = None
            schedule_in.unit = None
            schedule_in.rrule_expression = None
        elif schedule_in.strategy == "interval":
            schedule_in.cron_expression = None
            schedule_in.rrule_expression = None
        elif schedule_in.strategy == "rrule":
            schedule_in.cron_expression = None
            schedule_in.interval = None
            schedule_in.unit = None

        job_id = str(uuid4())
        sch = await self.schedule_crud.create(
            id_hash=workflow.id_hash,
            workflow_hash=workflow.id_hash,
            strategy=schedule_in.strategy,
            interval=schedule_in.interval,
            unit=schedule_in.unit,
            cron_expression=schedule_in.cron_expression,
            rrule_expression=getattr(schedule_in, "rrule_expression", None),
            timezone=schedule_in.timezone,
            active=schedule_in.active,
            job_id=job_id,
        )
        # The AsyncScheduler reloads the schedules from the database in its own loop —
        # there is no in-process registration to do here.
        return sch

    async def update_schedule(
        self, job_id: str, schedule_in: ScheduleCreate, owner_workflow_hash: str,
    ) -> Schedule:
        sch = await self.schedule_crud.get(job_id)
        # SEG (IDOR): schedules are resolved by global job_id. The route only
        # authorizes the workflow in the path — without confirming that the schedule belongs to
        # it, a user could point a DELETE/PUT on their own workflow at the
        # job_id of another tenant. 404 (not 403) so as not to reveal existence.
        #
        # `owner_workflow_hash` used to be optional, and with `None` the confirmation above
        # was SKIPPED — the defense described in this comment was off by
        # omission. Nobody used the shortcut (both routes always passed the owner),
        # and now forgetting it breaks at the call instead of reopening the IDOR.
        if not sch or sch.workflow_hash != owner_workflow_hash:
            raise ScheduleNotFoundError(f"Schedule {job_id} não encontrado.")

        updates = schedule_in.dict(exclude_unset=True)
        # Turning back on (paused -> active) clears `next_run_at`: without this, the time
        # stuck in the past would make the scheduler fire the moment the
        # toggle is flipped. Covers the REST route (PUT .../schedules/{job}) and the MCP tool
        # `update_schedule`, which both call this method. Only when there actually is a
        # transition to active — re-editing an already active schedule must not clear it.
        if updates.get("active") is True and not sch.active:
            updates.update(campos_de_ativacao(True))
        # Changing the TIMING (strategy/cron/interval/unit/rrule/timezone) also clears
        # `next_run_at`, even on a schedule that stays active: the stored value was
        # computed from the OLD expression, so keeping it would make the next occurrence
        # go out at the old time once, and a frequency change would be delayed
        # until the old time passed. `None` does NOT fire right away — just like
        # activation, `_process_schedule` recomputes the next FUTURE occurrence and only
        # then fires. Editing a non-timing field (or re-saving the same
        # time) does not touch `next_run_at`.
        elif _horario_mudou(updates, sch):
            updates["next_run_at"] = None
        return await self.schedule_crud.update_by_id(job_id, updates)

    async def delete_schedule(self, job_id: str, owner_workflow_hash: str) -> None:
        # Mesma regra e mesmo motivo do `update_schedule` acima.
        sch = await self.schedule_crud.get(job_id)
        if not sch or sch.workflow_hash != owner_workflow_hash:
            raise ScheduleNotFoundError(f"Schedule {job_id} não encontrado.")

        await self.schedule_crud.delete(job_id)

    async def delete_all_schedules_for_workflow(self, id_hash: str) -> None:
        """
        Removes all schedules of the workflow with the given id_hash.
        """
        schedules = await self.schedule_crud.get_by_workflow_hash(id_hash)
        for sch in schedules:
            await self.schedule_crud.delete(sch.job_id)

   