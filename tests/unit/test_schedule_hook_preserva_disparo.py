# tests/unit/test_schedule_hook_preserva_disparo.py
"""Saving a workflow must not cost the schedule's next trigger.

The hook deleted ALL schedules and recreated them on every save. The new schedule
is born with a null next_run_at, recomputed to the next FUTURE occurrence — so
saving the workflow after the cron time skipped that day's trigger.

Worse: `create_schedule` refuses a deactivated workflow and the exception is
swallowed by the caller (workflow_service). The delete had already happened, so
saving an inactive workflow deleted the schedule for good, with "salvo com sucesso"
(saved successfully) on the screen.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.scheduling.hooks import apply_schedule_if_needed


def _definition(**props) -> dict:
    base = {
        "strategy": "cron",
        "cron_expression": "0 13 * * *",
        "interval": 60,          # the node sends the defaults of ALL strategies
        "unit": "minutes",
        "timezone": "America/Cuiaba",
        "active": True,
    }
    base.update(props)
    return {
        "nodes": [
            {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": base},
        ]
    }


def _existing_schedule(**kwargs) -> MagicMock:
    base = {
        "job_id": "job-existente",
        "strategy": "cron",
        "cron_expression": "0 13 * * *",
        "interval": None,        # zeroed by create_schedule for strategy=cron
        "unit": None,
        "rrule_expression": None,
        "timezone": "America/Cuiaba",
        "active": True,
    }
    base.update(kwargs)
    return MagicMock(**base)


@pytest.fixture
def workflow():
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.flag_ative = True
    return wf


@pytest.fixture
def crud(monkeypatch):
    """Intercepts the whole ScheduleService — only the CRUD matters here."""
    fake = MagicMock()
    fake.schedule_crud = MagicMock(
        get_by_workflow_hash=AsyncMock(return_value=[]),
        delete=AsyncMock(),
        update=AsyncMock(),
    )
    fake.create_schedule = AsyncMock()
    fake.delete_all_schedules_for_workflow = AsyncMock()
    monkeypatch.setattr("app.core.scheduling.hooks.ScheduleService", lambda db: fake)
    return fake


async def test_unchanged_config_does_not_recreate_the_schedule(workflow, crud):
    """This is what preserved next_run_at: no delete, no create."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    await apply_schedule_if_needed(workflow, _definition(), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_unchanged_config_with_different_active_only_toggles_the_flag(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule(active=True)]

    await apply_schedule_if_needed(workflow, _definition(active=False), MagicMock())

    crud.schedule_crud.update.assert_awaited_once()
    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}
    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_changed_cron_replaces_the_schedule(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_awaited_once_with("job-existente")
    crud.create_schedule.assert_awaited_once()


async def test_changed_timezone_replaces_the_schedule(workflow, crud):
    """Mudar o fuso muda QUANDO dispara — precisa recalcular."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    await apply_schedule_if_needed(workflow, _definition(timezone="UTC"), MagicMock())

    crud.create_schedule.assert_awaited_once()


async def test_deactivated_workflow_does_not_lose_the_schedule(workflow, crud):
    """Regression: create_schedule refuses an inactive workflow and the exception is swallowed.

    Deleting before trying left the workflow with no schedule at all.
    """
    workflow.flag_ative = False
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()
    # Fix #3: the short-circuit becomes a warning to the front end (does not vanish into the log).
    assert [a.code for a in avisos] == ["workflow_inactive"]


async def test_invalid_config_preserves_the_schedule_and_warns(workflow, crud):
    """Fix #1: an invalid expression must not delete the previous valid schedule.

    Before, validation only ran INSIDE create_schedule — after the delete.
    Now it validates first: no delete, no create, and a warning goes back to the UI.
    """
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    # cron with 4 fields (invalid) — it changes the config, so it would fall into the
    # replacement path if the guard did not exist.
    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()
    assert [a.code for a in avisos] == ["invalid_schedule"]


async def test_equivalent_cron_does_not_recreate_the_schedule(workflow, crud):
    """Fix #2: "00 13 * * *" == "0 13 * * *" — croniter treats them the same, so
    recreating (and zeroing next_run_at, skipping the day) would be pointless."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule(cron_expression="0 13 * * *")]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="00 13 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_cron_reordered_days_does_not_recreate_the_schedule(workflow, crud):
    """Fix #2: "... 4,2" and "... 2,4" are the same set of days."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule(cron_expression="0 13 * * 2,4")]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="0 13 * * 4,2"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_normal_case_produces_no_warning(workflow, crud):
    """A legitimate replacement (active workflow, valid cron) warns about nothing."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_existing_schedule()]

    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.create_schedule.assert_awaited_once()
    assert avisos == []


async def test_without_schedule_trigger_removes_everything(workflow, crud):
    """Removing the node from the canvas must not leave the scheduler firing as a zombie."""
    await apply_schedule_if_needed(workflow, {"nodes": [{"id": "n1", "name": "Outro"}]}, MagicMock())

    crud.delete_all_schedules_for_workflow.assert_awaited_once_with("wf-1")


async def test_first_schedule_is_created(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = []

    await apply_schedule_if_needed(workflow, _definition(), MagicMock())

    crud.create_schedule.assert_awaited_once()
    enviado = crud.create_schedule.await_args.args[1]
    assert enviado.cron_expression == "0 13 * * *"
    assert enviado.timezone == "America/Cuiaba"


async def test_without_timezone_uses_the_product_default_timezone(workflow, crud):
    """Without `timezone` on the node, the default is the unified FUSO_PADRAO_DO_AGENDAMENTO,
    not the literal 'America/Cuiaba' that diverged from the constant (the last case)."""
    from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO

    crud.schedule_crud.get_by_workflow_hash.return_value = []
    definicao = _definition()
    del definicao["nodes"][0]["properties"]["timezone"]

    await apply_schedule_if_needed(workflow, definicao, MagicMock())

    enviado = crud.create_schedule.await_args.args[1]
    assert enviado.timezone == FUSO_PADRAO_DO_AGENDAMENTO == "America/La_Paz"
