# app/core/scheduling/hooks.py
"""
Scheduling hook: creates/updates schedules when a workflow is saved.
Canonical source — import directly from here.
"""
from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.core.exceptions import InvalidScheduleError
from app.core.utils.logger import get_logger
from app.models.models import Schedule, Workflow
from app.services.schedule_service import ScheduleService, validate_schedule_create, activation_fields
from app.schemas.schedule import ScheduleCreate, ScheduleNotice

logger = get_logger(__name__)


def extract_schedule_node(definition: dict) -> dict | None:
    """Return the first ScheduleTrigger node found in the definition, or None."""
    for node in definition.get("nodes", []):
        if node.get("type") == "trigger" and node.get("name") == "ScheduleTrigger":
            return node
    return None


def disable_schedule_node(definition: dict) -> bool:
    """Turn off the ScheduleTrigger in the definition itself. Returns whether there was one.

    Rule shared by duplicate and move: the derived workflow is born turned off, so
    it does not fire on its own before the user reviews it. Turning it off in the
    definition (and not only in the table) keeps canvas and schedule consistent —
    `apply_schedule_if_needed` reads the node's `active`, so what the user sees on
    the canvas is what counts.
    """
    node = extract_schedule_node(definition)
    if node is None:
        return False
    node.setdefault("properties", {})["active"] = False
    return True


def _update_de_active(ativar: bool) -> dict:
    """Fields to write to the Schedule when turning scheduling on/off.

    Thin alias of `activation_fields` (the canonical source lives in
    `schedule_service`, next to the `update_schedule` that the REST route and the
    MCP tool use). Kept under the old name so the callers of this module are not
    touched. Turning it back on resets `next_run_at` on purpose — see the
    canonical function's docstring.
    """
    return activation_fields(ativar)


async def sync_schedules_with_workflow_state(workflow: Workflow, db_session) -> None:
    """Align `Schedule.active` with the workflow's `flag_ative`.

    Called by every path that turns the workflow on/off WITHOUT going through the
    definition: the "Ativado/Inativo" (Enabled/Inactive) switch in the project
    list (`PUT /workflows/{id}` with only `flag_ative`) and the admin override.
    Neither of them touched schedules, so deactivating a workflow left the
    Schedule active in the database and the AsyncScheduler kept trying to fire on
    every cron occurrence, reaping `WorkflowInactiveError` in a loop that only
    existed in the error log.

    On reactivation, the ScheduleTrigger node's `active` is what decides — what
    the user sees on the canvas, and the same source `apply_schedule_if_needed`
    uses. Blindly turning everything back on would resurrect the schedule the
    owner had turned off in the editor before deactivating the workflow. With no
    node in the definition there is no legitimate schedule: whatever is left in
    the database stays off.

    Reads `properties.active` directly from `workflow.definition`, without
    decrypting: encryption covers `connectionString`, and
    `decrypt_workflow_connections` writes into the dict it receives — calling it
    here would mark the definition as dirty in the session and the next commit
    would save the plaintext to the database.
    """
    crud = ScheduleService(db_session).schedule_crud
    existentes = await crud.get_by_workflow_hash(workflow.id_hash)
    if not existentes:
        return

    if workflow.flag_ative:
        node = extract_schedule_node(workflow.definition or {})
        desejado = bool(node.get("properties", {}).get("active", True)) if node else False
    else:
        desejado = False

    for sch in existentes:
        if bool(sch.active) != desejado:
            await crud.update(sch, _update_de_active(desejado))


def _normalized_cron_field(campo: str) -> str:
    """Normalize a cron field for comparison: "09" -> "9", "4,2" -> "2,4".

    Only touches fields that are lists of plain integers — wildcards, ranges and
    steps ("*", "1-5", "*/15") stay intact (compared literally).
    """
    partes = campo.split(",")
    if partes and all(p.isdigit() for p in partes):
        return ",".join(str(n) for n in sorted({int(p) for p in partes}))
    return campo


def _normalized_cron(expr: str | None) -> str | None:
    """Canonical form of a cron for the configuration comparator."""
    if not expr:
        return None
    campos = expr.strip().split()
    if len(campos) != 5:
        return expr.strip()   # not a 5-field cron: compare literally
    return " ".join(_normalized_cron_field(c) for c in campos)


def _same_configuration(atual: Schedule, desejado: ScheduleCreate) -> bool:
    """Compare only what defines WHEN the schedule fires.

    `active` is left out on purpose — changing from active to inactive must not
    recreate the schedule, only toggle the flag. And each strategy looks only at
    its own fields: the ScheduleTrigger node always sends the defaults of all of
    them (interval=60, unit="minutes"), while `create_schedule` clears the ones
    that do not belong to the chosen strategy. Comparing everything would always
    differ.

    The cron is compared NORMALIZED ("00 09 * * *" == "0 9 * * *", "... 4,2" ==
    "... 2,4"): croniter treats both forms identically, so treating them as
    "different" would recreate the schedule for nothing — which resets
    `next_run_at` and makes the day's occurrence be skipped.
    """
    if atual.strategy != desejado.strategy:
        return False
    if (atual.timezone or None) != (desejado.timezone or None):
        return False

    if desejado.strategy == "cron":
        return _normalized_cron(atual.cron_expression) == _normalized_cron(desejado.cron_expression)
    if desejado.strategy == "interval":
        return atual.interval == desejado.interval and (atual.unit or None) == (desejado.unit or None)
    if desejado.strategy == "rrule":
        return (atual.rrule_expression or None) == (desejado.rrule_expression or None)
    return False


async def apply_schedule_if_needed(
    workflow: Workflow, definition: dict, db_session,
) -> list[ScheduleNotice]:
    """
    Sync the workflow's schedules with its current definition.

    - No ScheduleTrigger in the definition: removes the existing schedules.
      Without this, removing the node from the canvas left the async_scheduler
      firing from the old Schedule — the "zombie scheduler".
    - ScheduleTrigger with UNCHANGED configuration: leaves it alone. Recreating
      would reset `next_run_at`, which is recomputed to the next FUTURE
      occurrence — so saving the workflow after the cron time made that day's
      firing be silently skipped.
    - ScheduleTrigger with changed configuration: replaces it.

    Returns notices (`ScheduleNotice`) about what was NOT applied — inactive
    workflow, invalid expression. Previously these cases only became logs and the
    user saw "saved successfully" without knowing the schedule had been kept
    (or, in the invalid case, destroyed). The caller exposes the notices in the
    save response so they become toasts.
    """
    notices: list[ScheduleNotice] = []
    scheduler = ScheduleService(db_session)
    node = extract_schedule_node(definition)

    if not node:
        await scheduler.delete_all_schedules_for_workflow(workflow.id_hash)
        return notices

    props = node.get("properties", {})
    desejado = ScheduleCreate(
        strategy=props.get("strategy", "cron"),
        cron_expression=props.get("cron_expression") or None,
        interval=props.get("interval"),
        unit=props.get("unit") or None,
        rrule_expression=props.get("rrule_expression") or None,
        timezone=props.get("timezone", FUSO_PADRAO_DO_AGENDAMENTO),
        active=bool(props.get("active", True)),
    )

    existentes = await scheduler.schedule_crud.get_by_workflow_hash(workflow.id_hash)

    if len(existentes) == 1 and _same_configuration(existentes[0], desejado):
        atual = existentes[0]
        if bool(atual.active) != bool(desejado.active):
            await scheduler.schedule_crud.update(atual, _update_de_active(bool(desejado.active)))
        return notices

    # From here on the schedule would need to be replaced. Two guards
    # BEFORE deleting anything — deleting and only then finding out it cannot
    # be recreated left the workflow with no schedule at all, with the failure
    # swallowed by the caller (the user saw "saved" and the cron died).

    # 1) `create_schedule` rejects a deactivated workflow. Keep the current schedule
    #    and warn: the new config only takes effect when the workflow is reactivated and saved.
    if not workflow.flag_ative:
        logger.warning(
            "Workflow '%s' está desativado: agendamento preservado como está, "
            "a nova configuração NÃO foi aplicada. Reative o workflow e salve "
            "de novo para atualizar o agendamento.",
            workflow.id_hash,
        )
        notices.append(ScheduleNotice(
            code="workflow_inactive",
            severity="warning",
            message=(
                "O workflow está inativo, então a nova configuração de "
                "agendamento não foi aplicada. Reative o workflow e salve de "
                "novo para atualizar o agendamento."
            ),
        ))
        return notices

    # 2) An invalid config must not destroy a previous valid schedule.
    #    (The ScheduleTrigger in the front end already validates; this is defense in
    #    depth for legacy/API payloads that arrive invalid.)
    try:
        validate_schedule_create(desejado)
    except InvalidScheduleError as exc:
        logger.warning(
            "Workflow '%s': configuração de agendamento inválida (%s) — "
            "agendamento anterior preservado.",
            workflow.id_hash, exc,
        )
        notices.append(ScheduleNotice(
            code="invalid_schedule",
            severity="warning",
            message=f"Configuração de agendamento inválida: {exc}. O agendamento anterior foi mantido.",
        ))
        return notices

    for sch in existentes:
        await scheduler.schedule_crud.delete(sch.job_id)

    await scheduler.create_schedule(workflow.id_hash, desejado)
    return notices
