# tests/unit/test_mcp_gatilhos.py
"""
The four trigger tools, and the default timezone they inherit.

The file has two halves with different purposes:

- **The timezone** — the invariant that the change in the scheduler's fallback
  recreates NO schedule. The owner's decision depends on it: recreating resets
  `next_run_at` and skips the day's occurrence, and that would happen to every
  scheduled workflow on the first save after the deploy.
- **The tools** — the gates (scope, role, workspace), what the description
  promises and the shape of the response.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.core.utils.encryption import encrypt_workflow_connections
from app.mcp import infra
from app.mcp.tools.gatilhos import (
    create_schedule, delete_schedule, list_schedules, update_schedule,
)
from app.models.base import Base
from app.models.models import Schedule, Workflow
from app.models.workspace_member import WorkspaceMember
from app.schemas.schedule import ScheduleBase
from tests.unit._mcp_harness import (
    TABLES, create_user, create_workspace, fake_ctx, fake_scope,
)

WS_1 = "11111111-1111-4111-8111-111111111111"
WS_2 = "22222222-2222-4222-8222-222222222222"
WF_1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
WF_2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
WF_INACTIVE = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


def ctx(**kw):
    """`ctx` with trigger read and management over workspace 1."""
    campos = {
        "scopes": {"workflows:read", "triggers:manage"},
        "workspace_ids": {WS_1},
    }
    campos.update(kw)
    return fake_ctx(fake_scope(**campos))


def _definition() -> dict:
    return {
        "nodes": [{"id": "n1", "type": "action", "name": "Buffer", "properties": {}}],
        "edges": [],
    }


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _session():
        async with fabrica() as db:
            try:
                yield db
            finally:
                await db.rollback()

    monkeypatch.setattr(infra, "sessao", _session)

    async with fabrica() as db:
        await create_user(db, "usr-1", "ana")
        await create_user(db, "usr-2", "bruno")
        await create_workspace(db, WS_1, "usr-1", "Principal")
        await create_workspace(db, WS_2, "usr-2", "De outra conta")
        db.add_all([
            Workflow(id_hash=WF_1, name="Recorte", workspace_id=WS_1,
                     definition=encrypt_workflow_connections(_definition()), flag_ative=True),
            Workflow(id_hash=WF_2, name="Alheio", workspace_id=WS_2,
                     definition=encrypt_workflow_connections(_definition()), flag_ative=True),
            Workflow(id_hash=WF_INACTIVE, name="Parado", workspace_id=WS_1,
                     definition=encrypt_workflow_connections(_definition()), flag_ative=False),
        ])
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


async def _seed(fabrica, workflow_hash, job_id="job-semeado", **campos):
    """A schedule stored directly, without going through the tools.

    Needed in two cases the tools refuse on purpose: an inactive workflow
    (`create_schedule` answers `workflow_inactive`) and another account's
    workflow (unreachable from the test's scope).
    """
    campos.setdefault("strategy", "cron")
    campos.setdefault("cron_expression", "0 9 * * *")
    campos.setdefault("timezone", FUSO_PADRAO_DO_AGENDAMENTO)
    campos.setdefault("active", True)
    campos.setdefault("retry_count", 0)
    async with fabrica() as db:
        db.add(Schedule(id_hash=job_id, workflow_hash=workflow_hash,
                        job_id=job_id, **campos))
        await db.commit()
    return job_id


async def _job_ids(fabrica, workflow_hash=WF_1):
    async with fabrica() as db:
        linhas = (await db.execute(
            select(Schedule).where(Schedule.workflow_hash == workflow_hash)
        )).scalars().all()
        return [s.job_id for s in linhas]


# ── The timezone: the invariant that nothing is recreated ────────────────────


def test_the_node_and_the_constant_state_the_SAME_timezone():
    """This is the invariant the owner's decision depends on, and it is fragile.

    The node cannot import the constant — `flow/` only imports from `app/`
    inside functions, because the executor packages `flow/` without `app/`, and
    `description()` runs at import time. So the value is written twice, and
    only this test keeps them from diverging.

    Diverging raises no error: it makes the NEXT SAVE of every scheduled
    workflow see a different `timezone` in `_same_configuration`, recreate the
    schedule, reset `next_run_at` and **skip the day's occurrence**. Silently,
    for all of them.
    """
    from flow.registry import NODE_REGISTRY

    propriedades = NODE_REGISTRY["ScheduleTrigger"].description()["properties"]
    do_no = next(p for p in propriedades if p["name"] == "timezone")["default"]

    assert do_no == FUSO_PADRAO_DO_AGENDAMENTO


def test_the_schema_inherits_the_same_constant():
    """It was `America/Cuiaba` — same offset, different name. Two names for the
    same intent is how the third value (UTC) went unnoticed."""
    assert ScheduleBase.model_fields["timezone"].default == FUSO_PADRAO_DO_AGENDAMENTO


def test_changing_the_fallback_recreates_no_schedule():
    """The direct proof of the decision: `_same_configuration` still agrees.

    The production survey (2026-09-15) counted 10 active schedules, ALL with
    the then-default timezone stored and NONE with a null column — so the new
    fallback moves no trigger today. This test is what ensures it stays that
    way when someone touches the constant.
    """
    from app.core.scheduling.hooks import _same_configuration

    gravado = SimpleNamespace(
        strategy="cron", timezone=FUSO_PADRAO_DO_AGENDAMENTO,
        cron_expression="0 9 * * *", interval=None, unit=None,
        rrule_expression=None,
    )
    # What the node sends when the workflow is saved.
    desejado = ScheduleBase(
        strategy="cron", cron_expression="0 9 * * *",
        interval=60, unit="minutes",
    )

    assert _same_configuration(gravado, desejado) is True


@pytest.mark.parametrize("valor", [None, "", "   ", "Fuso/Inexistente"])
def test_the_scheduler_no_longer_falls_back_to_UTC(valor):
    """Four hours of difference between what the screen says and the trigger time.

    The question `_tz_of` answers is a single one — "I don't know this
    schedule's timezone, which do I use?" — and both of its exits (empty
    column, unreadable value) ended in UTC, which is `datetime`'s default and
    not a choice.
    """
    from app.core.async_scheduler import AsyncScheduler

    tz = AsyncScheduler()._tz_of(SimpleNamespace(timezone=valor, job_id="j1"))

    assert str(tz) == FUSO_PADRAO_DO_AGENDAMENTO


def test_valid_timezone_is_respected():
    """The fallback must not have turned into "always the default"."""
    from app.core.async_scheduler import AsyncScheduler

    tz = AsyncScheduler()._tz_of(SimpleNamespace(timezone="Europe/Lisbon", job_id="j1"))

    assert str(tz) == "Europe/Lisbon"


# ── list_schedules ───────────────────────────────────────────────────────────


async def test_without_schedule_the_list_comes_empty(banco):
    saida = await list_schedules(ctx(), WF_1)

    assert saida["total"] == 0
    assert saida["workflow_active"] is True
    assert "hint" not in saida


async def test_the_inactive_workflow_is_LISTABLE_not_an_error(banco):
    """An inactive workflow is exactly where someone asks "why did this stop
    running". If the read goes through the writes' execution guard
    (`ScheduleService._require_active_workflow`), this test fails with
    `WorkflowInactiveError`.

    The schedule is seeded directly in the database because `create_schedule`
    refuses an inactive workflow — and it is precisely that asymmetry the pair
    of tests pins down: READING the schedule of a stopped workflow has to work;
    CREATING one, doesn't.
    """
    await _seed(banco, WF_INACTIVE)

    saida = await list_schedules(ctx(), WF_INACTIVE)

    assert saida["total"] == 1
    assert saida["workflow_active"] is False
    # And it says WHY it won't trigger — the most common cause, invisible in the item.
    assert "inativo" in saida["hint"]


async def test_only_the_field_of_the_strategy_in_use_comes_out_in_the_response(banco):
    """An old row may have all three filled in; returning all three would make
    the agent conclude there are three competing rules."""
    await create_schedule(ctx(), WF_1, "interval", interval=30, unit="minutes")

    item = (await list_schedules(ctx(), WF_1))["items"][0]

    assert item["interval"] == 30 and item["unit"] == "minutes"
    assert "cron_expression" not in item
    assert "rrule_expression" not in item


# ── create_schedule ──────────────────────────────────────────────────────────


async def test_create_cron_stores_and_returns_the_job_id(banco):
    saida = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * 1-5")

    assert saida["strategy"] == "cron"
    assert saida["cron_expression"] == "0 9 * * 1-5"
    assert saida["job_id"] in await _job_ids(banco)


async def test_the_omitted_timezone_becomes_the_product_default(banco):
    """A cron without an explicit timezone is not UTC — that is what the description promises."""
    saida = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    assert saida["timezone"] == FUSO_PADRAO_DO_AGENDAMENTO


@pytest.mark.parametrize("kwargs, esperado, motivo", [
    ({"strategy": "cron"}, "5 campos", "cron sem expressão"),
    ({"strategy": "cron", "cron_expression": "0 9 * *"}, "5 campos", "cron com 4 campos"),
    ({"strategy": "cron", "cron_expression": ""}, "5 campos", "cron com expressão vazia"),
    ({"strategy": "interval", "interval": 5}, "interval + unit", "interval sem unit"),
    ({"strategy": "rrule"}, "rrule_expression", "rrule sem expressão"),
    # These two have their OWN recipe: the tool lists the accepted values,
    # something the core doesn't do — `InvalidScheduleError` says "Strategy
    # inválida: xyz" and stops there, leaving the agent to retry in the dark.
    ({"strategy": "nao_existe"}, "'cron', 'interval', 'rrule'", "estratégia desconhecida"),
    ({"strategy": "interval", "interval": 5, "unit": "luas"},
     "'seconds', 'minutes', 'hours', 'days'", "unidade inválida"),
])
async def test_invalid_config_becomes_validation_WITH_the_recipe(banco, kwargs, esperado, motivo):
    """The code alone is not the point — the MESSAGE is.

    Measured by mutation: deleting the strategy guard and the explicit call to
    `validate_schedule_create` did NOT break this test, because the core
    validates again inside and `@ferramenta` maps `InvalidScheduleError` to
    `validation` all the same. In other words, the tool's guards are redundant
    as far as REFUSING goes.

    What only they do is say what is valid: `InvalidScheduleError` answers
    "Strategy inválida: xyz" (invalid strategy) and stops there, without listing
    the three. An agent reading that retries in the dark. That is why the
    assertion is about the `hint`.
    """
    with pytest.raises(ToolError) as exc:
        await create_schedule(ctx(), WF_1, **kwargs)

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "validation", motivo
    # The assertion is about the whole BODY (message + hint): that is where what
    # the tool adds to the core lives, and that is what the mutation erases.
    assert esperado in json.dumps(detalhe, ensure_ascii=False), motivo


async def test_nothing_is_stored_when_the_config_is_invalid(banco):
    """Validation runs BEFORE the insert — otherwise a half-written row is left behind."""
    with pytest.raises(ToolError):
        await create_schedule(ctx(), WF_1, "cron", cron_expression="invalido")

    assert await _job_ids(banco) == []


async def test_create_on_inactive_workflow_is_refused_with_the_way_out(banco):
    """The core already refused, but the REST route turned it into a generic 400
    ("Não foi possível criar o agendamento") that doesn't say what to do.

    The tool anticipates the refusal and names the way out — the agent needs to
    know the path is `set_workflow_active`, not trying another expression.
    """
    with pytest.raises(ToolError) as exc:
        await create_schedule(ctx(), WF_INACTIVE, "cron", cron_expression="0 9 * * *")

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "workflow_inactive"
    assert "set_workflow_active" in detalhe["hint"]
    assert await _job_ids(banco, WF_INACTIVE) == []


async def test_the_client_does_not_choose_the_schedule_workspace(banco):
    """`ScheduleBase` carries `workspace_id` and had no `extra="forbid"`.

    The tool builds the object field by field, so there is no way through. The
    test asserts the parameter's absence: adding it to the signature breaks here.
    """
    import inspect

    assinatura = inspect.signature(create_schedule)
    assert "workspace_id" not in assinatura.parameters


# ── update_schedule ──────────────────────────────────────────────────────────


async def test_pausing_preserves_the_configuration(banco):
    """`active=false` is what one almost always wants, and the opposite of deleting."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await update_schedule(ctx(), WF_1, criado["job_id"], active=False)

    assert saida["active"] is False
    assert saida["cron_expression"] == "0 9 * * *"


async def test_reenabling_through_the_tool_clears_next_run_at(banco):
    """The same fix as the REST PUT applies through the tool: re-enabling a
    paused schedule with `next_run_at` in the past resets the time — otherwise
    the scheduler would fire it the moment the switch is flipped. Seeded
    directly because the schedule has to be born paused and with a next stop
    in the past."""
    from datetime import datetime

    job = await _seed(
        banco, WF_1, job_id="j-religar", active=False,
        next_run_at=datetime(2020, 1, 1, 9, 0),
    )

    saida = await update_schedule(ctx(), WF_1, job, active=True)
    assert saida["active"] is True

    async with banco() as db:
        sch = (await db.execute(
            select(Schedule).where(Schedule.job_id == job)
        )).scalars().one()
        assert sch.next_run_at is None


async def test_only_the_sent_fields_change(banco):
    criado = await create_schedule(
        ctx(), WF_1, "cron", cron_expression="0 9 * * *", timezone="Europe/Lisbon",
    )

    saida = await update_schedule(ctx(), WF_1, criado["job_id"], cron_expression="30 7 * * *")

    assert saida["cron_expression"] == "30 7 * * *"
    assert saida["timezone"] == "Europe/Lisbon"


async def test_update_without_any_field_is_refused(banco):
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    with pytest.raises(ToolError) as exc:
        await update_schedule(ctx(), WF_1, criado["job_id"])

    assert corpo(exc.value)["code"] == "validation"


async def test_job_id_of_another_workflow_answers_not_found(banco):
    """`not_found` and not `forbidden`: saying "it exists, but it isn't yours"
    already reveals that it exists. It is the same rule as the service's,
    inherited from the IDOR fix."""
    other_schedule = await _seed(banco, WF_2, job_id="job-do-vizinho")

    with pytest.raises(ToolError) as exc:
        await update_schedule(ctx(), WF_1, other_schedule, active=False)

    assert corpo(exc.value)["code"] == "not_found"


# ── delete_schedule ──────────────────────────────────────────────────────────


async def test_without_confirm_nothing_is_deleted_and_the_response_describes_the_target(banco):
    """Deleting has no undo and the symptom is silent: nothing fails, the routine
    just stops happening."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await delete_schedule(ctx(), WF_1, criado["job_id"])

    assert saida["outcome"] == "not_confirmed"
    assert saida["would_delete"]["cron_expression"] == "0 9 * * *"
    assert await _job_ids(banco) == [criado["job_id"]]


async def test_with_confirm_deletes(banco):
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await delete_schedule(ctx(), WF_1, criado["job_id"], confirm=True)

    assert saida["outcome"] == "deleted"
    assert await _job_ids(banco) == []


async def test_deleting_what_does_not_exist_answers_not_found(banco):
    with pytest.raises(ToolError) as exc:
        await delete_schedule(ctx(), WF_1, "nao-existe", confirm=True)

    assert corpo(exc.value)["code"] == "not_found"


async def test_the_confirm_cannot_leak_someone_elses_schedule(banco):
    """Ownership is checked BEFORE `confirm`, otherwise the description branch
    becomes an oracle: without deleting anything, it would reveal the
    neighbor's configuration."""
    other_schedule = await _seed(banco, WF_2, job_id="job-do-vizinho")

    with pytest.raises(ToolError) as exc:
        await delete_schedule(ctx(), WF_1, other_schedule)

    assert corpo(exc.value)["code"] == "not_found"


# ── The gates ────────────────────────────────────────────────────────────────


async def test_reading_schedule_does_not_require_manage_scope(banco):
    """Parity with `get_run`: whoever only follows along doesn't need the power to
    change things. The REST route also only requires membership to list."""
    read_only = ctx(scopes={"workflows:read"})

    assert (await list_schedules(read_only, WF_1))["total"] == 0


@pytest.mark.parametrize("nome", ["create_schedule", "update_schedule", "delete_schedule"])
async def test_writing_requires_triggers_manage(banco, nome):
    from app.mcp.tools import gatilhos as modulo

    narrow = ctx(scopes={"workflows:read", "workflows:write"})
    chamadas = {
        "create_schedule": lambda: modulo.create_schedule(narrow, WF_1, "cron",
                                                          cron_expression="0 9 * * *"),
        "update_schedule": lambda: modulo.update_schedule(narrow, WF_1, "j", active=False),
        "delete_schedule": lambda: modulo.delete_schedule(narrow, WF_1, "j", confirm=True),
    }
    with pytest.raises(ToolError) as exc:
        await chamadas[nome]()

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "forbidden_scope"
    assert "triggers:manage" in json.dumps(detalhe)


async def test_operator_is_the_floor_to_schedule_not_editor(banco):
    """SCHEDULING IS EXECUTING: a one-minute schedule fires the workflow with the
    owner's credentials, indefinitely. `editor` is not enough — it is the same
    bar as `run_workflow`, and the same one the REST route applies."""
    async with banco() as db:
        db.add(WorkspaceMember(workspace_id=WS_1, user_id="usr-2", role="editor"))
        await db.commit()

    editor = fake_ctx(fake_scope(
        user_id="usr-2", username="bruno",
        scopes={"workflows:read", "triggers:manage"}, workspace_ids={WS_1},
    ))

    # Reading, yes.
    assert (await list_schedules(editor, WF_1))["total"] == 0
    # Scheduling, no.
    with pytest.raises(ToolError) as exc:
        await create_schedule(editor, WF_1, "cron", cron_expression="0 9 * * *")
    assert corpo(exc.value)["code"] == "forbidden"


@pytest.mark.parametrize("nome", [
    "list_schedules", "create_schedule", "update_schedule", "delete_schedule",
])
async def test_workflow_of_another_account_is_unreachable(banco, nome):
    from app.mcp.tools import gatilhos as modulo

    chamadas = {
        "list_schedules": lambda: modulo.list_schedules(ctx(), WF_2),
        "create_schedule": lambda: modulo.create_schedule(ctx(), WF_2, "cron",
                                                          cron_expression="0 9 * * *"),
        "update_schedule": lambda: modulo.update_schedule(ctx(), WF_2, "j", active=False),
        "delete_schedule": lambda: modulo.delete_schedule(ctx(), WF_2, "j", confirm=True),
    }
    with pytest.raises(ToolError) as exc:
        await chamadas[nome]()

    assert corpo(exc.value)["code"] in ("not_found", "forbidden")


async def test_no_response_carries_the_definition_or_the_credential(banco):
    """All four load the workflow; `decifrar=False` is what keeps the encrypted
    blob from getting here."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")
    respostas = [
        json.dumps(criado),
        json.dumps(await list_schedules(ctx(), WF_1)),
        json.dumps(await update_schedule(ctx(), WF_1, criado["job_id"], active=False)),
        json.dumps(await delete_schedule(ctx(), WF_1, criado["job_id"], confirm=True)),
    ]

    for resposta in respostas:
        assert "gAAAA" not in resposta
        assert "definition" not in resposta
