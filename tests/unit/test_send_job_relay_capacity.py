# tests/unit/test_send_job_relay_capacity.py
"""
`send_job` no caminho RELAY (WS em outro worker) tem de recusar um executor
cheio como o caminho direto recusa. Antes publicava sem olhar capacidade: o
executor rejeitava por fila cheia e o run FALHAVA, em vez de o dispatch tentar
o próximo candidato — o mesmo estado, desfechos opostos conforme o worker.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.executor_connections as ec


def _registry_sem_conexao_local():
    reg = ec.ExecutorConnectionRegistry()
    reg.record_pending_ack = AsyncMock()
    return reg


def _job():
    return {"envelope": {"job_id": "job-1"}}


@pytest.mark.asyncio
async def test_relay_recusa_executor_cheio():
    reg = _registry_sem_conexao_local()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value={
             "queued": 50, "running": 4, "max_concurrent": 4, "max_queue": 50})), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)):
        assert await reg.send_job("ex-1", _job()) is False
    rc.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_publica_quando_ha_folga():
    reg = _registry_sem_conexao_local()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value={
             "queued": 1, "running": 2, "max_concurrent": 4, "max_queue": 50})), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)), \
         patch.object(ec, "build_relay_envelope", MagicMock(return_value="env")):
        assert await reg.send_job("ex-1", _job()) is True
    rc.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_capacidade_desconhecida_nao_e_fail_closed():
    """Chave ausente = não sei = tenta. Recusar aqui recriaria o 503 espúrio."""
    reg = _registry_sem_conexao_local()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value=None)), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)), \
         patch.object(ec, "build_relay_envelope", MagicMock(return_value="env")):
        assert await reg.send_job("ex-1", _job()) is True


def test_mesma_conta_de_cheio_nos_dois_caminhos():
    cap = {"queued": 50, "running": 4, "max_concurrent": 4, "max_queue": 50}
    conn = ec.ExecutorConnection(executor_id="ex-1", websocket=MagicMock(), capacity=cap)
    assert conn.is_full() is True
    assert ec._capacity_is_full(cap) is True
    assert ec._capacity_is_full({"queued": 0, "running": 0}) is False
    assert ec._capacity_is_full(None) is False
