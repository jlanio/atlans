# tests/unit/test_restore_version_sincroniza_agendamento.py
"""Restaurar uma versao tem que levar o agendamento junto.

`restore_version` trocava a definition inteira com um `crud.update` seco, sem
passar pelo hook de agendamento. Voltar para uma versao com outro cron — ou sem
ScheduleTrigger nenhum — deixava o Schedule antigo valendo no banco: o canvas
mostrava uma coisa e o AsyncScheduler disparava por outra.

Mesmo defeito de classe do "schedule orfao" coberto em
`test_schedule_orfao_workflow_inativo.py`, por outro caminho.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.workflow_version_service import restore_version

CRON_ATUAL = "0 13 * * *"
CRON_DA_VERSAO = "0 7 * * *"


def _definition(cron: str) -> dict:
    return {
        "nodes": [
            {
                "id": "n1",
                "type": "trigger",
                "name": "ScheduleTrigger",
                "properties": {
                    "strategy": "cron",
                    "cron_expression": cron,
                    "timezone": "America/Cuiaba",
                    "active": True,
                },
            }
        ]
    }


@pytest.fixture
def crud():
    """CRUD falso: a versao guardada tem cron diferente do workflow atual."""
    c = MagicMock()
    c.db = MagicMock()
    c.get_version = AsyncMock(return_value=MagicMock(definition=_definition(CRON_DA_VERSAO)))
    c.get_by_hash = AsyncMock(
        return_value=MagicMock(id_hash="wf-1", flag_ative=True, definition=_definition(CRON_ATUAL))
    )
    c.create_version = AsyncMock()

    async def _update(wf, updates):
        for chave, valor in updates.items():
            setattr(wf, chave, valor)
        return wf

    c.update = AsyncMock(side_effect=_update)
    return c


@pytest.fixture
def schedule_service(monkeypatch):
    """Intercepta o ScheduleService dentro do hook real — o hook aqui e o de verdade."""
    fake = MagicMock()
    fake.schedule_crud = MagicMock(
        get_by_workflow_hash=AsyncMock(return_value=[
            MagicMock(
                job_id="job-antigo", strategy="cron", cron_expression=CRON_ATUAL,
                interval=None, unit=None, rrule_expression=None,
                timezone="America/Cuiaba", active=True,
            )
        ]),
        delete=AsyncMock(),
        update=AsyncMock(),
    )
    fake.create_schedule = AsyncMock()
    fake.delete_all_schedules_for_workflow = AsyncMock()
    monkeypatch.setattr("app.core.scheduling.hooks.ScheduleService", lambda db: fake)
    return fake


async def test_restaurar_versao_com_outro_cron_substitui_o_agendamento(crud, schedule_service):
    """A regressao: o Schedule ficava no cron antigo, divergente do canvas."""
    await restore_version(crud, "wf-1", 3)

    schedule_service.schedule_crud.delete.assert_awaited_once_with("job-antigo")
    schedule_service.create_schedule.assert_awaited_once()
    assert schedule_service.create_schedule.await_args.args[1].cron_expression == CRON_DA_VERSAO


async def test_restaurar_versao_sem_schedule_trigger_remove_o_agendamento(crud, schedule_service):
    """Voltar para antes de existir agendamento nao pode deixar o cron rodando."""
    crud.get_version.return_value = MagicMock(definition={"nodes": [{"id": "n1", "name": "Outro"}]})

    await restore_version(crud, "wf-1", 3)

    schedule_service.delete_all_schedules_for_workflow.assert_awaited_once_with("wf-1")


async def test_restaurar_versao_com_mesmo_cron_preserva_o_next_run_at(crud, schedule_service):
    """Recriar o schedule pularia o disparo do dia — o hook ja evita isso."""
    crud.get_version.return_value = MagicMock(definition=_definition(CRON_ATUAL))

    await restore_version(crud, "wf-1", 3)

    schedule_service.schedule_crud.delete.assert_not_awaited()
    schedule_service.create_schedule.assert_not_awaited()


async def test_falha_no_agendamento_nao_desfaz_a_restauracao(crud, schedule_service):
    """Best-effort: o update da definition ja esta commitado quando o hook roda."""
    schedule_service.create_schedule.side_effect = RuntimeError("banco fora")

    wf = await restore_version(crud, "wf-1", 3)

    assert wf.definition == _definition(CRON_DA_VERSAO)


async def test_definition_da_versao_chega_ao_workflow(crud, schedule_service):
    await restore_version(crud, "wf-1", 3)

    assert crud.update.await_args.args[1]["definition"] == _definition(CRON_DA_VERSAO)
