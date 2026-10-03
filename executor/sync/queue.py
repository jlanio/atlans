# executor/sync/queue.py
"""
SyncQueue — resilient queue with exponential retry for sync operations.
"""
import logging
import time
from typing import Callable, Awaitable

from flow.utils.backoff import espera_exponencial

from executor.sync.manifest import SyncManifest

logger = logging.getLogger("executor.sync")

_MAX_RETRIES = 10
_MAX_BACKOFF = 300  # 5 minutos


class SyncQueue:
    """Processes the manifest's pending operations with exponential retry.

    The backoff is SCHEDULED, never slept: `process_pending()` runs at the top
    of the cycle, before local change detection, and an `asyncio.sleep(300)`
    in here froze the whole folder — with 5 items failing, it could go ~25
    minutes without reacting to any new file, even with the network back.
    The `SYNC_INTERVAL` tick (30s) is the retry's natural beat: each cycle
    only SKIPS what isn't due yet.
    """

    def __init__(self, manifest: SyncManifest, executor: Callable[[dict], Awaitable[bool]]):
        self.manifest = manifest
        self.executor = executor

    async def process_pending(self):
        """Processes the queue items whose attempt time is already due."""
        items = self.manifest.pending_items()
        if not items:
            return

        agora = time.time()

        for item in list(items):
            dataset_name = item["dataset"]
            retries = item.get("retries", 0)

            if retries >= _MAX_RETRIES:
                logger.error("Sync '%s': limite de retries (%d) atingido — desistindo.",
                             dataset_name, _MAX_RETRIES)
                self.manifest.dequeue(dataset_name)
                # Leaving the queue isn't enough for a DELETE operation: the dataset
                # stayed in the manifest, the next `diff` saw it again as
                # "removed locally" (it is no longer on disk), enqueued it
                # again — and the cycle restarted from zero on every scan,
                # forever. Giving up has to mean stopping trying.
                if item.get("action") == "delete":
                    self.manifest.remove_dataset(dataset_name)
                continue

            # An item without `next_attempt_at` (queue written before scheduling existed)
            # counts as "try now".
            proxima = item.get("next_attempt_at") or 0.0

            # The schedule is a WALL-CLOCK epoch and survives restarts inside
            # the manifest. On a field laptop that boots with the clock ahead
            # (bad CMOS) and is later corrected by NTP, the item stayed scheduled
            # for a future that never comes — frozen forever. For 'upload' and
            # 'delete' the diff ended up re-driving the operation; 'discard' has
            # no other engine, and the file Drive ordered deleted stayed on the
            # technician's disk with no error in the log. No legitimate schedule
            # goes beyond `agora + _MAX_BACKOFF`: anything more can only be a
            # messed-up clock.
            if proxima > agora + _MAX_BACKOFF:
                logger.warning(
                    "Sync '%s': agendamento de retry no futuro impossivel (%.0fs a frente) — "
                    "relogio do sistema mudou; tentando agora.", dataset_name, proxima - agora)
                proxima = 0.0

            if proxima > agora:
                continue

            try:
                success = await self.executor(item)
                if success:
                    self.manifest.dequeue(dataset_name)
                    logger.info("Sync '%s': operacao concluida com sucesso.", dataset_name)
                else:
                    delay = espera_exponencial(retries, teto=_MAX_BACKOFF)
                    self.manifest.update_retry(item, agora + delay)
                    logger.warning("Sync '%s': falhou (tentativa %d) — proximo retry em %.1fs.",
                                   dataset_name, retries + 1, delay)
            except Exception as e:
                delay = espera_exponencial(retries, teto=_MAX_BACKOFF)
                self.manifest.update_retry(item, agora + delay)
                logger.error("Sync '%s': erro (%s) — proximo retry em %.1fs.",
                             dataset_name, e, delay)
