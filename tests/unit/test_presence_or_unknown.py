# tests/unit/test_presence_or_unknown.py
"""
Tri-state presence for dispatch (spec §5.1): a Redis blip and a reconnection in
progress become "don't know" (the candidate is TRIED), not "offline".
Before, a fail-closed `is_online` marked the whole group (or pool) offline
because of a hiccup at the moment of the trigger.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.executor_connections as ec


@pytest.mark.asyncio
async def test_local_connection_is_proof_of_life():
    reg = ec.ExecutorConnectionRegistry()
    reg._connections["ex-1"] = MagicMock()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)) as rp:
        assert await reg.presence_or_unknown("ex-1") is True
    rp.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_down_becomes_unknown():
    reg = ec.ExecutorConnectionRegistry()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=None)):
        assert await reg.presence_or_unknown("ex-1") is None


@pytest.mark.asyncio
async def test_recent_disconnect_becomes_unknown_within_grace_period():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)):
        assert await reg.presence_or_unknown("ex-1") is None


@pytest.mark.asyncio
async def test_outside_grace_period_is_really_offline():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic() - ec._DISPATCH_GRACE_SECONDS - 1
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=False)):
        assert await reg.presence_or_unknown("ex-1") is False
    assert "ex-1" not in reg._recent_disconnects


@pytest.mark.asyncio
async def test_confirmed_presence_clears_the_grace_period_and_caches():
    reg = ec.ExecutorConnectionRegistry()
    reg._recent_disconnects["ex-1"] = time.monotonic()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=True)):
        assert await reg.presence_or_unknown("ex-1") is True
    assert "ex-1" not in reg._recent_disconnects
    assert reg._presence_cache["ex-1"][0] is True


@pytest.mark.asyncio
async def test_is_online_stays_fail_closed():
    reg = ec.ExecutorConnectionRegistry()
    with patch.object(ec, "_redis_presence_or_unknown", AsyncMock(return_value=None)):
        assert await reg.is_online("ex-1") is False
