# app/services/execution_alert_service.py
"""
Alerts for scheduled runs with no executor (spec §7.4).

A cron whose workspace has no executor — dedicated group down, or the whole
pool — cannot vanish silently nor turn into an email on every tick. The state
per `schedule_id` lives in Redis and the notification is on TRANSITION:

  1st failure of the window → email "as execuções agendadas de X estão falhando"
  subsequent failures       → at most ONE reminder every REMINDER_INTERVAL
  next one that runs        → recovery email, and the state is cleared

Recipients: workspace owner + members with the admin role. The `Schedule` has
no owner of its own; whoever answers for the workspace answers for the cron.

Best-effort throughout: a Redis or email failure is logged and never brings
down the scheduler — the `failed` run was already recorded in the history before this.
"""
from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.logger import get_logger
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.email_service import send_email_background

logger = get_logger(__name__)

REMINDER_INTERVAL_SECONDS = 6 * 60 * 60
_STATE_TTL_SECONDS = 30 * 24 * 60 * 60  # an unavailability window does not last a month

_TEMPLATE_FAILURE = "schedule_no_executor.html"
_TEMPLATE_RECOVERED = "schedule_recovered.html"


def _state_key(schedule_id: int | str) -> str:
    return f"sched_alert:{schedule_id}"


def _get_redis():
    from app.core.redis import get_redis_pool
    return get_redis_pool()


async def _load_state(schedule_id) -> dict | None:
    try:
        raw = await _get_redis().get(_state_key(schedule_id))
    except Exception as exc:
        logger.warning("Alerta de agendamento: falha ao ler estado no Redis: %s", exc)
        return None
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        return json.loads(raw)
    except ValueError:
        return None


async def _save_state(schedule_id, state: dict) -> None:
    try:
        await _get_redis().set(_state_key(schedule_id), json.dumps(state), ex=_STATE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Alerta de agendamento: falha ao gravar estado no Redis: %s", exc)


async def _clear_state(schedule_id) -> None:
    try:
        await _get_redis().delete(_state_key(schedule_id))
    except Exception as exc:
        logger.warning("Alerta de agendamento: falha ao limpar estado no Redis: %s", exc)


def decide_failure(state: dict | None, now: float) -> tuple[dict, bool]:
    """Pure (testable) transition: returns (new_state, notify?)."""
    if not state:
        return {"first_failure_at": now, "last_notified_at": now, "failures": 1}, True
    novo = dict(state)
    novo["failures"] = int(state.get("failures", 0)) + 1
    ultimo = float(state.get("last_notified_at") or 0)
    if now - ultimo >= REMINDER_INTERVAL_SECONDS:
        novo["last_notified_at"] = now
        return novo, True
    return novo, False


async def record_failure(db: AsyncSession, *, schedule_id, workflow, reason: str, category: str) -> bool:
    """Records the occurrence's failure; sends an email if it is a transition or a reminder.
    Returns whether it notified."""
    now = time.time()
    estado, notificar = decide_failure(await _load_state(schedule_id), now)
    await _save_state(schedule_id, estado)
    if not notificar:
        return False
    await _send_to_workspace(
        db, workflow.workspace_id, _TEMPLATE_FAILURE,
        subject=f"[Atlans] Execuções agendadas de \"{getattr(workflow, 'name', workflow.id_hash)}\" estão falhando",
        context={
            "workflow_name": getattr(workflow, "name", workflow.id_hash),
            "reason": reason,
            "category": category,
            "failures": estado["failures"],
            "since": _fmt(estado["first_failure_at"]),
            "is_reminder": estado["failures"] > 1,
        },
    )
    return True


async def record_success(db: AsyncSession, *, schedule_id, workflow) -> bool:
    """The occurrence ran: if there was an unavailability window, announces the
    recovery and clears the state. Returns whether it notified."""
    estado = await _load_state(schedule_id)
    if not estado:
        return False
    await _clear_state(schedule_id)
    await _send_to_workspace(
        db, workflow.workspace_id, _TEMPLATE_RECOVERED,
        subject=f"[Atlans] Execuções agendadas de \"{getattr(workflow, 'name', workflow.id_hash)}\" voltaram a rodar",
        context={
            "workflow_name": getattr(workflow, "name", workflow.id_hash),
            "failures": int(estado.get("failures", 0)),
            "since": _fmt(float(estado.get("first_failure_at") or time.time())),
        },
    )
    return True


async def workspace_recipients(db: AsyncSession, workspace_id: str | None) -> list[User]:
    """Owner + admin members of the workspace, with an email address."""
    if not workspace_id:
        return []
    ws = (await db.execute(
        select(Workspace).where(Workspace.id_hash == workspace_id)
    )).scalar_one_or_none()
    if ws is None:
        return []
    ids: set[str] = set()
    if ws.owner_id:
        ids.add(ws.owner_id)
    admins = await db.execute(
        select(WorkspaceMember.user_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role.in_(("admin", "owner")),
        )
    )
    ids.update(admins.scalars().all())
    if not ids:
        return []
    users = await db.execute(select(User).where(User.id_hash.in_(ids)))
    return [u for u in users.scalars().all() if getattr(u, "email", None)]


async def _send_to_workspace(db: AsyncSession, workspace_id: str | None, template: str, *, subject: str, context: dict) -> None:
    try:
        destinatarios = await workspace_recipients(db, workspace_id)
    except Exception as exc:
        logger.warning("Alerta de agendamento: falha ao resolver destinatários de %s: %s", workspace_id, exc)
        return
    if not destinatarios:
        logger.info("Alerta de agendamento: workspace %s sem destinatários com e-mail.", workspace_id)
        return
    for user in destinatarios:
        send_email_background(user.email, subject, template, {**context, "username": user.username})


async def notify_primary_emptied(db: AsyncSession, esvaziados: list[dict], *, executor_name: str) -> None:
    """A forced removal of an executor emptied the primary tier of these
    workspaces (spec §4.4): every future execution will fail (terminal `fail`)
    or overflow (terminal `pool`). The owner has to know now."""
    for d in esvaziados:
        await _send_to_workspace(
            db, d.get("workspace_id"), "policy_primary_emptied.html",
            subject=f"[Atlans] O workspace \"{d.get('workspace_name')}\" ficou sem executor dedicado",
            context={"workspace_name": d.get("workspace_name"), "executor_name": executor_name},
        )


def notify_primary_emptied_background(esvaziados: list[dict], *, executor_name: str) -> None:
    """Fire-and-forget version of `notify_primary_emptied` with its OWN session.

    The request session is closed as soon as the handler responds; a task
    that kept using it would race against the teardown's `rollback()`/`close()`
    (and the email would never go out)."""
    if not esvaziados:
        return
    import asyncio

    from app.core.db import AsyncSessionLocal

    async def _task():
        try:
            async with AsyncSessionLocal() as db:
                await notify_primary_emptied(db, esvaziados, executor_name=executor_name)
        except Exception as exc:  # best-effort
            logger.warning("Falha ao avisar donos sobre nível esvaziado: %s", exc)

    asyncio.create_task(_task())


async def notify_floor_forced(db: AsyncSession, ws) -> None:
    """The platform admin set the `no_pool` floor and the terminal was forced from
    `pool` to `fail`: the owner needs to know that the fallback no longer exists."""
    await _send_to_workspace(
        db, ws.id_hash, "policy_floor_forced.html",
        subject=f"[Atlans] O workspace \"{ws.name}\" passou a ser isolado",
        context={"workspace_name": ws.name},
    )


def _fmt(ts: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
