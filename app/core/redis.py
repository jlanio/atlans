# app/core/redis.py
"""
Centralized Redis pool for Atlas Studio.

Usage:
    # In the lifespan (main.py):
    from app.core.redis import init_redis, close_redis
    await init_redis()

    # In any service:
    from app.core.redis import get_redis_pool
    redis = get_redis_pool()
    await redis.get("chave")

    # Rate limit / quota counter over a time window:
    from app.core.redis import contar_na_janela
    contagem, ttl = await contar_na_janela("ratelimit:x:chave", 60)

Note: executor_connections.py and run_result_consumer.py keep their own
connections on purpose (persistent pub/sub and blocking brpop).
"""
import redis.asyncio as aioredis

from app.core.config import REDIS_URL

_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    """Return the global Redis pool. Must be initialized via init_redis() in the lifespan."""
    if _pool is None:
        raise RuntimeError(
            "Redis pool não inicializado. "
            "Certifique-se de que init_redis() foi chamado no lifespan da aplicação."
        )
    return _pool


async def init_redis() -> aioredis.Redis:
    """Initialize the global Redis pool. Called once at startup."""
    global _pool
    _pool = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _pool


def new_pubsub_client() -> aioredis.Redis:
    """DEDICATED Redis client for a long-lived pub/sub subscription.

    A subscriber holds the connection for as long as the whole run lasts. Coming
    from a pool with a ceiling (the logs WS had its own pool of 20), the Nth
    viewer got MaxConnectionsError and the panel closed with no explanation at
    all — intermittently, going away on its own when someone closed a tab. Here
    each subscriber gets its own connection, with no ceiling: the cost is one
    socket per open panel, which is what pub/sub demands anyway.

    One-off commands (GET/LRANGE) stay on the global pool — this client is only
    for the subscribe. The caller MUST close it with `await client.aclose()`.
    """
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def contar_na_janela(
    chave: str,
    janela_s: int,
    *,
    incremento: int = 1,
    deslizante: bool = False,
    redis: aioredis.Redis | None = None,
) -> tuple[int, int]:
    """Add `incremento` to the counter `chave` and return (count, ttl in seconds).

    It is the counter behind every per-window rate limit and quota in the API.
    `INCRBY`, `EXPIRE` and `TTL` go out in a single transaction (MULTI/EXEC):
    either all three happen, or none. With two loose commands — `INCR` and, if
    the counter went back to 1, `EXPIRE` —, losing the second (the process dies
    between the two, the connection breaks, the SSE is cancelled midway) left
    the key with NO EXPIRY: the counter never reset and, once over the ceiling,
    the IP, the executor, the refresh family or the user stayed blocked forever.

    Fixed window (the default): `EXPIRE ... NX` only sets the expiry of a key
    that has none — on the first count, or on a key left without an expiry
    before this function existed —, and never pushes back an expiry already
    running: otherwise the window would never close while there was traffic.
    `NX` requires Redis 7 (compose uses `redis:7-alpine`).

    `deslizante=True` renews the expiry on every count: the window only closes
    after `janela_s` seconds with NO count (the per-account login lockout).

    `redis`: a client already at hand; without one, the global pool. Redis
    errors propagate to the caller, which decides whether to fail open or closed.
    """
    rc = redis if redis is not None else get_redis_pool()
    async with rc.pipeline(transaction=True) as pipe:
        pipe.incrby(chave, incremento)
        pipe.expire(chave, janela_s, nx=not deslizante)
        pipe.ttl(chave)
        contagem, _, ttl = await pipe.execute()
    return int(contagem), int(ttl)


async def close_redis() -> None:
    """Fecha o pool Redis. Chamado no shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
