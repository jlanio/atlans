# tests/unit/test_schedule_hook_preserva_disparo.py
"""Salvar um workflow não pode custar o próximo disparo do agendamento.

O hook apagava TODOS os schedules e recriava a cada save. O schedule novo nasce
com next_run_at nulo, recalculado para a proxima ocorrencia FUTURA — entao
salvar o workflow depois do horario do cron pulava o disparo daquele dia.

Pior: `create_schedule` recusa workflow desativado e a excecao e engolida pelo
chamador (workflow_service). O delete ja tinha acontecido, entao salvar um
workflow inativo apagava o agendamento em definitivo, com "salvo com sucesso"
na tela.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.scheduling.hooks import apply_schedule_if_needed


def _definition(**props) -> dict:
    base = {
        "strategy": "cron",
        "cron_expression": "0 13 * * *",
        "interval": 60,          # o nó envia os defaults de TODAS as estratégias
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


def _schedule_existente(**kwargs) -> MagicMock:
    base = {
        "job_id": "job-existente",
        "strategy": "cron",
        "cron_expression": "0 13 * * *",
        "interval": None,        # zerado por create_schedule para strategy=cron
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
    """Intercepta o ScheduleService inteiro — só o CRUD interessa aqui."""
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


async def test_config_inalterada_nao_recria_o_schedule(workflow, crud):
    """É o que preservava o next_run_at: sem delete, sem create."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    await apply_schedule_if_needed(workflow, _definition(), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_config_inalterada_com_active_diferente_so_alterna_a_flag(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente(active=True)]

    await apply_schedule_if_needed(workflow, _definition(active=False), MagicMock())

    crud.schedule_crud.update.assert_awaited_once()
    assert crud.schedule_crud.update.await_args.args[1] == {"active": False}
    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_cron_alterado_substitui_o_schedule(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_awaited_once_with("job-existente")
    crud.create_schedule.assert_awaited_once()


async def test_timezone_alterado_substitui_o_schedule(workflow, crud):
    """Mudar o fuso muda QUANDO dispara — precisa recalcular."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    await apply_schedule_if_needed(workflow, _definition(timezone="UTC"), MagicMock())

    crud.create_schedule.assert_awaited_once()


async def test_workflow_desativado_nao_perde_o_agendamento(workflow, crud):
    """Regressao: create_schedule recusa workflow inativo e a excecao e engolida.

    Apagar antes de tentar deixava o workflow sem agendamento nenhum.
    """
    workflow.flag_ative = False
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()
    # Fix #3: o short-circuit vira aviso para o front (não some só no log).
    assert [a.code for a in avisos] == ["workflow_inactive"]


async def test_config_invalida_preserva_o_agendamento_e_avisa(workflow, crud):
    """Fix #1: uma expressão inválida não pode apagar o schedule válido anterior.

    Antes a validação só rodava DENTRO de create_schedule — depois do delete.
    Agora valida antes: sem delete, sem create, e um aviso volta para a UI.
    """
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    # cron com 4 campos (inválido) — muda a config, então cairia no caminho de
    # substituição se a guarda não existisse.
    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()
    assert [a.code for a in avisos] == ["invalid_schedule"]


async def test_cron_equivalente_nao_recria_o_schedule(workflow, crud):
    """Fix #2: "00 13 * * *" == "0 13 * * *" — croniter trata igual, então
    recriar (e zerar next_run_at, pulando o dia) seria à toa."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente(cron_expression="0 13 * * *")]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="00 13 * * *"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_cron_dias_reordenados_nao_recria_o_schedule(workflow, crud):
    """Fix #2: "... 4,2" e "... 2,4" são o mesmo conjunto de dias."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente(cron_expression="0 13 * * 2,4")]

    await apply_schedule_if_needed(workflow, _definition(cron_expression="0 13 * * 4,2"), MagicMock())

    crud.schedule_crud.delete.assert_not_awaited()
    crud.create_schedule.assert_not_awaited()


async def test_caso_normal_nao_gera_aviso(workflow, crud):
    """Substituição legítima (workflow ativo, cron válido) não avisa nada."""
    crud.schedule_crud.get_by_workflow_hash.return_value = [_schedule_existente()]

    avisos = await apply_schedule_if_needed(workflow, _definition(cron_expression="0 7 * * *"), MagicMock())

    crud.create_schedule.assert_awaited_once()
    assert avisos == []


async def test_sem_schedule_trigger_remove_tudo(workflow, crud):
    """Tirar o nó do canvas não pode deixar o scheduler zumbi disparando."""
    await apply_schedule_if_needed(workflow, {"nodes": [{"id": "n1", "name": "Outro"}]}, MagicMock())

    crud.delete_all_schedules_for_workflow.assert_awaited_once_with("wf-1")


async def test_primeiro_agendamento_e_criado(workflow, crud):
    crud.schedule_crud.get_by_workflow_hash.return_value = []

    await apply_schedule_if_needed(workflow, _definition(), MagicMock())

    crud.create_schedule.assert_awaited_once()
    enviado = crud.create_schedule.await_args.args[1]
    assert enviado.cron_expression == "0 13 * * *"
    assert enviado.timezone == "America/Cuiaba"


async def test_sem_timezone_usa_o_fuso_padrao_do_produto(workflow, crud):
    """Sem `timezone` no no, o default e o FUSO_PADRAO_DO_AGENDAMENTO unificado,
    nao o literal 'America/Cuiaba' que divergia da constante (o ultimo caso)."""
    from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO

    crud.schedule_crud.get_by_workflow_hash.return_value = []
    definicao = _definition()
    del definicao["nodes"][0]["properties"]["timezone"]

    await apply_schedule_if_needed(workflow, definicao, MagicMock())

    enviado = crud.create_schedule.await_args.args[1]
    assert enviado.timezone == FUSO_PADRAO_DO_AGENDAMENTO == "America/La_Paz"
