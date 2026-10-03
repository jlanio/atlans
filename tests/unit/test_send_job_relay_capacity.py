# tests/unit/test_send_job_relay_capacity.py
"""
`send_job` on the RELAY path (WS on another worker) has to refuse a full executor
the way the direct path does. Before, it published without checking capacity: the
executor rejected it for a full queue and the run FAILED, instead of the dispatch
trying the next candidate — the same state, opposite outcomes depending on the worker.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.executor_connections as ec


def _registry_without_local_connection():
    reg = ec.ExecutorConnectionRegistry()
    reg.record_pending_ack = AsyncMock()
    return reg


def _job():
    return {"envelope": {"job_id": "job-1"}}


@pytest.mark.asyncio
async def test_relay_refuses_full_executor():
    reg = _registry_without_local_connection()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value={
             "queued": 50, "running": 4, "max_concurrent": 4, "max_queue": 50})), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)):
        assert await reg.send_job("ex-1", _job()) is False
    rc.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_publishes_when_there_is_room():
    reg = _registry_without_local_connection()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value={
             "queued": 1, "running": 2, "max_concurrent": 4, "max_queue": 50})), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)), \
         patch.object(ec, "build_relay_envelope", MagicMock(return_value="env")):
        assert await reg.send_job("ex-1", _job()) is True
    rc.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_capacity_is_not_fail_closed():
    """Missing key = don't know = try. Refusing here would recreate the spurious 503."""
    reg = _registry_without_local_connection()
    rc = MagicMock(); rc.publish = AsyncMock(return_value=1)
    with patch.object(ec, "_redis_check_presence", AsyncMock(return_value=True)), \
         patch.object(ec, "_redis_read_capacity", AsyncMock(return_value=None)), \
         patch.object(ec, "_get_redis", AsyncMock(return_value=rc)), \
         patch.object(ec, "build_relay_envelope", MagicMock(return_value="env")):
        assert await reg.send_job("ex-1", _job()) is True


def test_same_full_calculation_on_both_paths():
    cap = {"queued": 50, "running": 4, "max_concurrent": 4, "max_queue": 50}
    conn = ec.ExecutorConnection(executor_id="ex-1", websocket=MagicMock(), capacity=cap)
    assert conn.is_full() is True
    assert ec._capacity_is_full(cap) is True
    assert ec._capacity_is_full({"queued": 0, "running": 0}) is False
    assert ec._capacity_is_full(None) is False
