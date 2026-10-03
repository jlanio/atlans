# app/mcp/tools/gatilhos.py
"""
Triggers: when a workflow fires on its own.

This is the domain that turns a workflow into a routine. Without it, an agent
can build and run a workflow, but cannot answer the next question — "and now,
how does this run every day at seven?" — nor find out why the routine that
exists is not running.

`triggers:manage` is the scope the tokens screen has offered since Phase 0 and
that until now **triggered nothing**: it was a chip on the token card with no
tool behind it. This module is what makes that promise true.

Four decisions shape the module:

- **Scheduling is executing.** A one-minute schedule fires the workflow with
  the owner's credentials, indefinitely. That is why the three write tools
  require `operator`, the same role as `run_workflow` — and it is the same
  yardstick the REST route applies (`workflow_com_papel(ROLE_OPERATOR)` in
  `schedules_router`).
- **`list_schedules` lists inactive workflows.** "Why did this workflow stop
  running?" is exactly the question asked about an inactive workflow, so
  reading does not go through the execution guard that writes use
  (`ScheduleService._require_active_workflow`). The query goes directly to
  `ScheduleCRUD`: the tool already has the workflow in hand from
  `carregar_workflow`.
- **`delete_schedule` requires `confirm`.** Deleting a schedule cannot be
  undone and the symptom is silent: nothing fails, the routine just stops
  happening. The parameter forces the agent to have read what it is deleting.
- **Nothing from the client goes into a schema wholesale.** `ScheduleBase`
  carries `workspace_id` and did not have `extra="forbid"`; the tools build
  the object field by field, with an allowlist.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import exigir_papel
from app.core.exceptions import AtlasBaseError
from app.core.rbac import ROLE_OPERATOR, ROLE_VIEWER
from app.crud.schedule_crud import ScheduleCRUD
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.schedule_service import (
    ScheduleService, validate_schedule_create,
)

_READ_ROLE_MESSAGE = "Requer papel 'viewer' ou superior neste workspace."
_WRITE_ROLE_MESSAGE = (
    "Requer papel 'operator' ou superior neste workspace — agendar é executar."
)

ESTRATEGIAS = ("cron", "interval", "rrule")
UNIDADES = ("seconds", "minutes", "hours", "days")


def _summarize(sch) -> dict:
    """What identifies and describes a schedule.

    Nothing here is free human text: strategy and unit are enums, the timezone
    is a zone name, and the expressions are the configuration the caller itself
    sent. That is why the item goes out at the top and not in `untrusted_data`.
    """
    return {
        "job_id": sch.job_id,
        "strategy": sch.strategy,
        "active": bool(sch.active),
        "timezone": sch.timezone,
        # Only the field of the strategy in use: the `ScheduleTrigger` node sends
        # the defaults of ALL of them, and the service clears the ones that do
        # not belong — but an old row may have all three filled in, and
        # returning all three would make the agent conclude three rules compete.
        **({"cron_expression": sch.cron_expression} if sch.strategy == "cron" else {}),
        **({"interval": sch.interval, "unit": sch.unit}
           if sch.strategy == "interval" else {}),
        **({"rrule_expression": sch.rrule_expression}
           if sch.strategy == "rrule" else {}),
        "next_run_at": iso(sch.next_run_at),
        "last_run_at": iso(sch.last_run_at),
        "retry_count": sch.retry_count or 0,
    }


def _config_error(exc: Exception):
    return erro(
        "validation",
        str(exc),
        "cron precisa de 5 campos (min hora dia mês dia-da-semana); "
        "interval precisa de interval + unit; rrule precisa de rrule_expression",
    )


# ── Leitura ──────────────────────────────────────────────────────────────────


@ferramenta
async def list_schedules(ctx: Context, workflow_id: str) -> dict:
    """This workflow's schedules — when it fires on its own.

    Answers the two questions a scheduled workflow raises: "when does it run?"
    (`next_run_at`) and "why didn't it run?". For the second, look in this
    order:

    1. `workflow_active: false` at the top — the scheduler **ignores** schedules
       of an inactive workflow, however correct they are. It is the most common
       cause, and nothing in the schedule itself gives it away.
    2. `active: false` on the item — the schedule exists and is turned off.
    3. `next_run_at` in the past — the scheduler has not gone over it yet.

    `timezone` is the timezone the expression is read in: `"0 9 * * *"` in
    `America/Sao_Paulo` fires at 9 AM there, not at 9 AM UTC.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _READ_ROLE_MESSAGE)
        workflow_id_hash, ativo = wf.id_hash, bool(wf.flag_ative)

        # Directly on the CRUD, without the writes' execution guard: the workflow
        # already came from `carregar_workflow` above, and an inactive workflow
        # is listable.
        itens = [_summarize(s) for s in await ScheduleCRUD(db).get_by_workflow_hash(workflow_id_hash)]

    return envelope({
        "workflow_id": workflow_id_hash,
        "workflow_active": ativo,
        "items": itens,
        "total": len(itens),
        **({"hint": (
            "o workflow está inativo: o agendador ignora agendamentos de fluxo "
            "inativo, então nenhum destes vai disparar até set_workflow_active"
        )} if itens and not ativo else {}),
    })


# ── Escrita ──────────────────────────────────────────────────────────────────


@ferramenta
async def create_schedule(
    ctx: Context,
    workflow_id: str,
    strategy: str,
    cron_expression: Optional[str] = None,
    interval: Optional[int] = None,
    unit: Optional[str] = None,
    rrule_expression: Optional[str] = None,
    timezone: Optional[str] = None,
    active: bool = True,
) -> dict:
    """Creates a schedule: makes the workflow fire on its own, without anyone asking.

    Three strategies, and each uses different fields:

    - `cron` — `cron_expression` with **5 fields** (`min hour day month
      day-of-week`). `"0 9 * * 1-5"` is 9 AM on weekdays.
    - `interval` — `interval` + `unit` (`seconds`/`minutes`/`hours`/`days`).
    - `rrule` — RFC 5545 `rrule_expression`, for calendars
      (`"FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1"` = first Monday of the month).

    `timezone` is the timezone the expression is read in; if omitted, the
    product default is used. A cron without an explicit timezone is not UTC.

    Ask for confirmation before calling. A schedule fires the workflow with
    the owner's credentials, repeatedly and with no one watching — an
    `interval` of 1 `minutes` on an expensive workflow is a bill that runs up
    on its own.

    **The workflow must be active.** Scheduling an inactive workflow is
    refused, and not on a whim: the scheduler ignores schedules of inactive
    workflows, so the saved row would be a promise never kept. Activate it
    first with `set_workflow_active(active=true)`.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    if strategy not in ESTRATEGIAS:
        raise erro("validation", f"strategy deve ser uma de {list(ESTRATEGIAS)}.",
                   "cron para horário, interval para repetição, rrule para calendário")
    if unit is not None and unit not in UNIDADES:
        raise erro("validation", f"unit deve ser uma de {list(UNIDADES)}.")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _WRITE_ROLE_MESSAGE)
        workflow_id_hash = wf.id_hash

        # The refusal also belongs to the core (`_require_active_workflow` raises
        # `WorkflowInactiveError`). Anticipating it here gives the code and the
        # way out before building and validating the whole configuration — and
        # the message here explains the WHY, which the core's has no room to say.
        if not wf.flag_ative:
            raise erro(
                "workflow_inactive",
                "Este workflow está inativo, e o agendador ignora agendamento de "
                "fluxo inativo — a linha gravada nunca dispararia.",
                "ative com set_workflow_active(workflow_id, active=true) e agende depois",
            )

        # Allowlist, field by field. `ScheduleBase` has no `extra="forbid"` and
        # carries `workspace_id` — passing a client dict here would let it pick
        # the schedule's tenant.
        campos: dict[str, Any] = {"strategy": strategy, "active": bool(active)}
        for nome, valor in (
            ("cron_expression", cron_expression), ("interval", interval),
            ("unit", unit), ("rrule_expression", rrule_expression),
        ):
            if valor is not None:
                campos[nome] = valor
        if timezone:
            campos["timezone"] = timezone

        try:
            config = ScheduleCreate(**campos)
            # The same validation the route uses, called BEFORE saving.
            validate_schedule_create(config)
        except AtlasBaseError as exc:
            raise _config_error(exc)
        except ValueError as exc:
            # Pydantic and `InvalidScheduleError` land here.
            raise _config_error(exc)

        criado = await ScheduleService(db).create_schedule(workflow_id_hash, config)
        # `create_schedule` does not commit; the MCP session rolls back in the finally.
        await db.commit()
        item = _summarize(criado)

    return envelope({"workflow_id": workflow_id_hash, **item})


@ferramenta
async def update_schedule(
    ctx: Context,
    workflow_id: str,
    job_id: str,
    strategy: Optional[str] = None,
    cron_expression: Optional[str] = None,
    interval: Optional[int] = None,
    unit: Optional[str] = None,
    rrule_expression: Optional[str] = None,
    timezone: Optional[str] = None,
    active: Optional[bool] = None,
) -> dict:
    """Changes an existing schedule. Only the fields sent change.

    To **pause without losing the configuration**, send `active=false` — it is
    what one wants almost always, and it deletes nothing. `delete_schedule` is
    for when the routine no longer exists.

    Switching strategy requires sending the new one's fields: switching to
    `cron` without `cron_expression` is refused.

    The `job_id` comes from `list_schedules`. A `job_id` that does not belong
    to this workflow answers `not_found`, not `forbidden`: saying "it exists,
    but is not yours" would already give away that it exists.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    if strategy is not None and strategy not in ESTRATEGIAS:
        raise erro("validation", f"strategy deve ser uma de {list(ESTRATEGIAS)}.")
    if unit is not None and unit not in UNIDADES:
        raise erro("validation", f"unit deve ser uma de {list(UNIDADES)}.")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _WRITE_ROLE_MESSAGE)
        workflow_id_hash = wf.id_hash

        campos: dict[str, Any] = {}
        for nome, valor in (
            ("strategy", strategy), ("cron_expression", cron_expression),
            ("interval", interval), ("unit", unit),
            ("rrule_expression", rrule_expression), ("timezone", timezone),
            ("active", active),
        ):
            if valor is not None:
                campos[nome] = valor
        if not campos:
            raise erro(
                "validation", "Nenhum campo para alterar.",
                "mande ao menos um: strategy, cron_expression, interval, unit, "
                "rrule_expression, timezone ou active",
            )

        try:
            mudancas = ScheduleUpdate(**campos)
        except ValueError as exc:
            raise _config_error(exc)

        try:
            atualizado = await ScheduleService(db).update_schedule(
                job_id, mudancas, owner_workflow_hash=workflow_id_hash,
            )
        except AtlasBaseError as exc:
            # `ScheduleNotFoundError` covers both "does not exist" and "belongs to
            # another workflow" — on purpose, so it does not become an oracle.
            raise erro(
                "not_found", str(exc),
                "use list_schedules(workflow_id) para ver os job_id deste fluxo",
            )
        await db.commit()
        item = _summarize(atualizado)

    return envelope({"workflow_id": workflow_id_hash, **item})


@ferramenta
async def delete_schedule(
    ctx: Context, workflow_id: str, job_id: str, confirm: bool = False
) -> dict:
    """Deletes a schedule for good. Requires `confirm=true`.

    **Before deleting, consider `update_schedule(active=false)`**: pausing
    keeps the expression, the timezone and the history, and is reversible with
    one call. Deleting cannot be undone, and the symptom is silent — nothing
    fails, the routine just stops happening, and it may take weeks for anyone
    to notice.

    Without `confirm=true` nothing is deleted: the response describes what
    would be removed, for you to show whoever asked before repeating the call.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _WRITE_ROLE_MESSAGE)
        workflow_id_hash = wf.id_hash

        crud = ScheduleCRUD(db)
        alvo = await crud.get(job_id)
        # The same rule as the service: ownership confirmed through the path's
        # workflow, and `not_found` for both cases.
        if alvo is None or alvo.workflow_hash != workflow_id_hash:
            raise erro(
                "not_found", f"Agendamento {job_id} não encontrado neste workflow.",
                "use list_schedules(workflow_id) para ver os job_id deste fluxo",
            )
        item = _summarize(alvo)

        if not confirm:
            return envelope({
                "workflow_id": workflow_id_hash,
                "outcome": "not_confirmed",
                "would_delete": item,
                "hint": (
                    "nada foi apagado. Repita com confirm=true para apagar, ou "
                    "use update_schedule(active=false) para só pausar"
                ),
            })

        await ScheduleService(db).delete_schedule(job_id, owner_workflow_hash=workflow_id_hash)
        await db.commit()

    return envelope({
        "workflow_id": workflow_id_hash,
        "outcome": "deleted",
        "deleted": item,
    })


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_schedules",
        title="Agendamentos do fluxo",
        description=(
            "Quando este workflow dispara sozinho: estratégia, expressão, fuso e a próxima "
            "execução. Traz workflow_active no topo, porque o agendador ignora agendamento "
            "de fluxo inativo e nada no agendamento em si denuncia isso."
        ),
        annotations=anotacoes("list_schedules"),
    )(list_schedules)

    server.tool(
        name="create_schedule",
        title="Criar agendamento",
        description=(
            "Faz o workflow disparar sozinho por cron, intervalo ou regra de calendário. "
            "Peça confirmação antes: o fluxo passa a rodar com as credenciais do dono, "
            "repetidamente e sem ninguém olhando."
        ),
        annotations=anotacoes("create_schedule"),
    )(create_schedule)

    server.tool(
        name="update_schedule",
        title="Alterar agendamento",
        description=(
            "Muda só os campos enviados. Para pausar sem perder a configuração, mande "
            "active=false — é o que se quer quase sempre, e é reversível."
        ),
        annotations=anotacoes("update_schedule"),
    )(update_schedule)

    server.tool(
        name="delete_schedule",
        title="Apagar agendamento",
        description=(
            "Remove o agendamento de vez; exige confirm=true. Sem ele, descreve o que seria "
            "apagado e não apaga nada. Apagar não tem desfazer e falha em silêncio: a rotina "
            "só deixa de acontecer."
        ),
        annotations=anotacoes("delete_schedule"),
    )(delete_schedule)
