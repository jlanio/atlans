# executor/sync/pool.py
"""
GeoSync's own thread pools.

Every `asyncio.to_thread` lands on the loop's DEFAULT executor — which main.py
sizes from MAX_CONCURRENT precisely to give the JOBS headroom. The sync sent
there the scan, the whole folder's MD5, `validate_dataset`
(geopandas/rasterio), `extract_metadata` and the shapefile zip: a `diff` of a
large folder held a thread for minutes and the workflows' I/O nodes were left
waiting for a free thread, with nothing on the dashboard explaining the
slowness.

With separate, small pools, the sync never consumes more than
`SYNC_THREADS + SYNC_IO_THREADS` threads, whatever happens. They are UNIQUE in
the process (not per folder): with one folder or with five, GeoSync's thread
ceiling is the same.

There are TWO pools because the loads are nothing alike:

  * `em_thread` — heavy, slow work: scan, MD5, validation, metadata, bundle
    zip, manifest write. Few threads.
  * `em_thread_io` — the 1 MB chunks of the transfers' PUT/GET. Each call is
    very short, but needs CONTINUOUS throughput: with everything in the same
    2-thread pool, two heavy `_write_zip`/`extract_metadata` calls were enough
    to stall every in-flight transfer for minutes. The socket went without
    data, MinIO dropped the connection for idleness and the upload went to
    the retry queue — throughput lost exactly when there was the most to send.
"""
import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor

from executor.sync.sync_config import SYNC_IO_THREADS, SYNC_THREADS

logger = logging.getLogger("executor.sync")

_pool: ThreadPoolExecutor | None = None
_pool_io: ThreadPoolExecutor | None = None


def _obter_pool() -> ThreadPoolExecutor:
    """Creates the heavy-work pool on first use.

    Lazy because the SyncManagers are built before the event loop starts (and
    before any scan happens) — creating threads there would mean paying for a
    GeoSync that might not even be configured.
    """
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=SYNC_THREADS, thread_name_prefix="geosync")
        logger.debug("Pool do GeoSync criado com %d thread(s).", SYNC_THREADS)
    return _pool


def _obter_pool_io() -> ThreadPoolExecutor:
    """Creates the transfers' I/O pool on first use."""
    global _pool_io
    if _pool_io is None:
        _pool_io = ThreadPoolExecutor(max_workers=SYNC_IO_THREADS,
                                      thread_name_prefix="geosync-io")
        logger.debug("Pool de I/O do GeoSync criado com %d thread(s).", SYNC_IO_THREADS)
    return _pool_io


async def _executar(pool: ThreadPoolExecutor, func, *args, **kwargs):
    """`run_in_executor` doesn't accept kwargs — hence the `partial`."""
    loop = asyncio.get_running_loop()
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(pool, func, *args)


async def em_thread(func, *args, **kwargs):
    """Trabalho pesado do sync (varredura, MD5, validacao, zip, manifesto)."""
    return await _executar(_obter_pool(), func, *args, **kwargs)


async def em_thread_io(func, *args, **kwargs):
    """Reading/writing the transfers' bytes — its own pool, with throughput.

    Using `em_thread` here coupled the progress of every in-flight PUT/GET to
    the duration of whatever zip/validate was occupying the heavy pool's 2
    threads.
    """
    return await _executar(_obter_pool_io(), func, *args, **kwargs)
