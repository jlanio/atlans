# tests/unit/test_execution_alert_service.py
"""
Alerta de agendamento sem executor (spec §7.4): por TRANSIÇÃO, não por tick.
Um cron de 5 min com o grupo fora por 2 h não pode gerar 24 e-mails.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import execution_alert_service as alert


class TestDecideFailure:
    def test_primeira_falha_notifica(self):
        estado, notificar = alert.decide_failure(None, now=1000.0)
        assert notificar is True
        assert estado["failures"] == 1 and estado["first_failure_at"] == 1000.0

    def test_falha_dentro_do_intervalo_nao_notifica(self):
        estado = {"first_failure_at": 1000.0, "last_notified_at": 1000.0, "failures": 1}
        novo, notificar = alert.decide_failure(estado, now=1000.0 + 60)
        assert notificar is False and novo["failures"] == 2
        assert novo["last_notified_at"] == 1000.0

    def test_lembrete_apos_o_intervalo(self):
        estado = {"first_failure_at": 1000.0, "last_notified_at": 1000.0, "failures": 5}
        novo, notificar = alert.decide_failure(estado, now=1000.0 + alert.REMINDER_INTERVAL_SECONDS)
        assert notificar is True and novo["last_notified_at"] == 1000.0 + alert.REMINDER_INTERVAL_SECONDS
        assert novo["first_failure_at"] == 1000.0  # a janela é a mesma


def _redis_com(estado):
    rc = MagicMock()
    rc.get = AsyncMock(return_value=json.dumps(estado) if estado else None)
    rc.set = AsyncMock()
    rc.delete = AsyncMock()
    return rc


def _wf():
    wf = MagicMock(); wf.id_hash = "wf-1"; wf.name = "Bacia diária"; wf.workspace_id = "ws-1"
    return wf


@pytest.mark.asyncio
async def test_record_failure_envia_na_primeira_e_grava_estado():
    rc = _redis_com(None)
    with patch.object(alert, "_get_redis", MagicMock(return_value=rc)), \
         patch.object(alert, "_send_to_workspace", AsyncMock()) as enviar:
        assert await alert.record_failure(MagicMock(), schedule_id=7, workflow=_wf(),
                                          reason="grupo fora", category="no_dedicated_executor") is True
    enviar.assert_awaited_once()
    rc.set.assert_awaited_once()
    assert rc.set.await_args.args[0] == "sched_alert:7"


@pytest.mark.asyncio
async def test_record_failure_repetida_nao_envia():
    import time
    rc = _redis_com({"first_failure_at": time.time() - 60, "last_notified_at": time.time() - 60, "failures": 1})
    with patch.object(alert, "_get_redis", MagicMock(return_value=rc)), \
         patch.object(alert, "_send_to_workspace", AsyncMock()) as enviar:
        assert await alert.record_failure(MagicMock(), schedule_id=7, workflow=_wf(),
                                          reason="grupo fora", category="x") is False
    enviar.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_success_avisa_recuperacao_uma_vez_e_limpa():
    rc = _redis_com({"first_failure_at": 1.0, "last_notified_at": 1.0, "failures": 3})
    with patch.object(alert, "_get_redis", MagicMock(return_value=rc)), \
         patch.object(alert, "_send_to_workspace", AsyncMock()) as enviar:
        assert await alert.record_success(MagicMock(), schedule_id=7, workflow=_wf()) is True
        rc.delete.assert_awaited_once_with("sched_alert:7")
    enviar.assert_awaited_once()
    # sem estado, rodar de novo não avisa
    rc2 = _redis_com(None)
    with patch.object(alert, "_get_redis", MagicMock(return_value=rc2)), \
         patch.object(alert, "_send_to_workspace", AsyncMock()) as enviar2:
        assert await alert.record_success(MagicMock(), schedule_id=7, workflow=_wf()) is False
    enviar2.assert_not_awaited()
