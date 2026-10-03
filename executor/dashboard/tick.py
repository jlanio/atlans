# executor/dashboard/tick.py
"""
Collection of a `Snapshot` — the only place that gathers the tick's numbers.

Extracted from `runtime.DashboardRuntime._pintar` when the JSON mode appeared.
Duplicating the call in both runtimes would guarantee divergence: it would take
only someone adding an argument to `stats.snapshot()` and remembering one side,
and the terminal dashboard and the GUI would start showing different numbers for
the same executor — no error, no log, no way to notice by looking at either one.

The outbox cache lives here for the same reason: it is a synchronous SQLite
query, and running it on every tick would be disk I/O at 1 Hz inside the event
loop, for a number that changes slowly.

Disk space had exactly the same problem — and worse, because the artifacts
folder may be on a network drive — but its cache lives inside `sysinfo` itself
(`TTL_DISCO_S`), not here: `connection._capacity_loop` reads the same metrics
and needs the same protection without going through this module.
"""
from __future__ import annotations

import logging

from executor import sysinfo

logger = logging.getLogger("executor.dashboard")

# Interval between outbox queries. See the module docstring.
INTERVALO_OUTBOX_S = 5.0


def contar_outbox() -> int:
    """Pending items in the SQLite outbox. Never raises — 0 beats bringing down the tick."""
    try:
        from executor import result_store
        return result_store.count_pending()
    except Exception:
        return 0


class CacheOutbox:
    """Keeps the last count and only re-queries every `INTERVALO_OUTBOX_S`.

    Takes the clock as a parameter (`loop.time`) instead of calling
    `asyncio.get_running_loop()` internally: that way it is testable without an
    event loop.
    """

    def __init__(self, intervalo: float = INTERVALO_OUTBOX_S) -> None:
        self._intervalo = intervalo
        self._valor = 0
        self._proximo = 0.0

    def get(self, agora: float) -> int:
        if agora >= self._proximo:
            self._proximo = agora + self._intervalo
            self._valor = contar_outbox()
        return self._valor


def coletar_snapshot(stats, *, capacity_source, result_queue, outbox_pending: int):
    """Builds the tick's `Snapshot`.

    `capacity_source` and `result_queue` are read "on the spot" on purpose — that
    is the contract of `stats.snapshot()`, which keeps no reference to a live
    executor object. Both are failure-tolerant: a queue that blew up on `qsize()`
    must not wipe out the whole dashboard.
    """
    try:
        capacity = capacity_source() if capacity_source else None
    except Exception as exc:
        logger.debug("capacity_source falhou no tick: %s", exc)
        capacity = None

    try:
        result_queue_size = result_queue.qsize() if result_queue else 0
    except Exception:
        result_queue_size = 0

    return stats.snapshot(
        capacity=capacity,
        recursos=sysinfo._get_dynamic_metrics(),
        processo=sysinfo.process_metrics(),
        outbox_pending=outbox_pending,
        result_queue_size=result_queue_size,
    )
