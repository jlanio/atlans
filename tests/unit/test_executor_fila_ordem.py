# tests/unit/test_executor_fila_ordem.py
"""
Order of the executor's local queue (executor/job_queue.py).

The PriorityQueue heap is not stable, and the server sends no priority: every
job ties at 5. Without a tiebreaker, with ten jobs waiting, the second to arrive
was the ninth to run — and stayed "Em andamento" (in progress) on the screen
that whole time. The arrival `seq` breaks the tie; explicit priority still applies.
"""
from __future__ import annotations

import asyncio

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id, **envelope):
    return {"envelope": {"job_id": job_id, **envelope}}


async def _execution_order(mensagens):
    """Enqueues everything BEFORE starting the single worker — the output order is
    the queue's, with no race between enqueue and consumption."""
    ordem: list[str] = []

    async def _execute(msg):
        ordem.append(msg["envelope"]["job_id"])

    fila = ExecutorJobQueue(on_execute=_execute, max_concurrent=1, max_queue_size=100)
    for m in mensagens:
        assert await fila.enqueue(m)
    await fila.start(n_workers=1)
    try:
        for _ in range(500):
            if len(ordem) == len(mensagens):
                break
            await asyncio.sleep(0.01)
    finally:
        await fila.shutdown(timeout=5)
    return ordem


@pytest.mark.asyncio
async def test_equal_priority_runs_in_arrival_order():
    ids = [f"job{i}" for i in range(1, 21)]
    assert await _execution_order([_job(i) for i in ids]) == ids


@pytest.mark.asyncio
async def test_explicit_priority_still_jumps_ahead():
    mensagens = [
        _job("a"), _job("b"), _job("urgente", priority=1), _job("c"), _job("depois", priority=9),
    ]
    assert await _execution_order(mensagens) == ["urgente", "a", "b", "c", "depois"]
