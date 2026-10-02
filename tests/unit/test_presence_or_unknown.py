# tests/unit/test_presence_or_unknown.py
"""
Presença em tri-estado para o dispatch (spec §5.1): blip de Redis e
reconexão em curso viram "não sei" (candidato é TENTADO), não "offline".
Antes, `is_online` fail-closed marcava o grupo (ou o pool) inteiro offline
por um soluço no instante do disparo.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.executor_connections as ec


@pytest.mark.asyncio
async def test_conexao_local_e_prova_de_vida():
    reg = ec.ExecutorConnectionRegistry()
    reg._connections["ex-1"] = MagicMock()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)) as rp:
        assert await reg.presence_or_unknown("ex-1") is True
    rp.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_fora_vira_nao_sei():
    reg = ec.ExecutorConnectionRegistry()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=None)):
        assert await reg.presence_or_unknown("ex-1") is None


@pytest.mark.asyncio
async def test_desconexao_recente_vira_nao_sei_dentro_da_carencia():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)):
        assert await reg.presence_or_unknown("ex-1") is None


@pytest.mark.asyncio
async def test_fora_da_carencia_e_offline_de_verdade():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic() - ec._DISPATCH_GRACE_SECONDS - 1
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)):
        assert await reg.presence_or_unknown("ex-1") is False
    assert "ex-1" not in reg._recent_disconnects


@pytest.mark.asyncio
async def test_presenca_confirmada_limpa_a_carencia_e_cacheia():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=True)):
        assert await reg.presence_or_unknown("ex-1") is True
    assert "ex-1" not in reg._recent_disconnects
    assert reg._presence_cache["ex-1"][0] is True


@pytest.mark.asyncio
async def test_is_online_continua_fail_closed():
    reg = ec.ExecutorConnectionRegistry()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=None)):
        assert await reg.is_online("ex-1") is False
