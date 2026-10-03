import asyncpg
import asyncio
import os
from cachetools import TTLCache
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_pg_conn_str(conn_str: str) -> str:
    parts = conn_str.split('@', 1)
    return parts[1] if len(parts) > 1 else ''


class _PoolCache(TTLCache):
    """TTLCache that closes the asyncpg.Pool when evicting entries."""

    def popitem(self):
        key, pool = super().popitem()
        self._close_pool(pool)
        return key, pool

    def __delitem__(self, key):
        pool = self.get(key)
        if pool is not None:
            self._close_pool(pool)
        super().__delitem__(key)

    @staticmethod
    def _close_pool(pool: asyncpg.Pool) -> None:
        try:
            loop = asyncio.get_running_loop()
            # Loop is running: schedule the close asynchronously
            asyncio.ensure_future(pool.close(), loop=loop)
        except RuntimeError:
            # No event loop running (e.g. shutdown after asyncio.run() finished)
            # It cannot be closed properly; asyncpg's GC will take care of the cleanup.
            pass
        except Exception as e:
            logger.warning(f"[PoolCache] Erro ao fechar pool asyncpg: {e}")


# Keyed by (loop_id, conn_str) — see _cache_key. The earlier premise of
# "one event loop per process" no longer holds since sub-workflows started
# running nested.
_pool_cache = _PoolCache(maxsize=50, ttl=600)


async def close_all_pools() -> None:
    """
    Explicitly closes all cached pools.
    Must be called during the executor's graceful shutdown, before the event loop closes.
    """
    keys = list(_pool_cache.keys())
    for key in keys:
        pool = _pool_cache.pop(key, None)
        if pool is not None:
            try:
                await pool.close()
                logger.info("[close_all_pools] Pool fechado para: %s", _sanitize_pg_conn_str(key[1] if isinstance(key, tuple) else key))
            except Exception as e:
                logger.warning("[close_all_pools] Erro ao fechar pool: %s", e)


def _cache_key(conn_str: str) -> tuple:
    """Cache key: (event loop, connection string).

    An asyncpg.Pool is tied to the event loop that created it — reusing it in
    another loop fails with "got Future attached to a different loop". The
    previous key was only the conn_str, relying on the premise of "one loop per
    process", which any path creating a new loop (e.g. asyncio.run in a thread)
    breaks intermittently and in a way that is hard to diagnose.

    Outside a loop (synchronous call) it falls back to None — without a loop
    there is no pool to reuse anyway.
    """
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = None
    return (loop_id, conn_str)


async def get_asyncpg_pool(conn_str: str) -> asyncpg.Pool:
    """
    Returns or creates an asyncpg.Pool for the given connectionString.
    The pool is reused while it is in the cache (TTL=600s, max=50 entries)
    AND while the event loop is the same one that created it (see _cache_key).
    When evicted, the pool is closed properly to release connections.
    """
    key = _cache_key(conn_str)
    if key not in _pool_cache:
        logger.info(f"[get_asyncpg_pool] Criando pool para: {_sanitize_pg_conn_str(conn_str)}")
        try:
            # application_name shows up in pg_stat_activity — makes it easy to identify
            # Atlas Studio connections in the database (e.g. SELECT * FROM pg_stat_activity)
            executor_id = os.getenv("EXECUTOR_ID", "")
            app_name = f"apolo/{executor_id[-5:]}" if executor_id else "apolo"
            pool = await asyncpg.create_pool(
                dsn=conn_str,
                min_size=0,
                max_size=5,
                timeout=30.0,
                max_inactive_connection_lifetime=60,
                server_settings={"application_name": app_name},
            )
            _pool_cache[key] = pool
        except asyncpg.TooManyConnectionsError:
            logger.error("[get_asyncpg_pool] Banco atingiu limite de conexões.")
            raise RuntimeError("Banco recusou conexão: too many clients.")
    return _pool_cache[key]
