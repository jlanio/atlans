# app/core/rate_limiter.py
"""Application-wide rate limiter.

slowapi's `get_remote_address` returns `request.client.host`, which behind
Traefik is ALWAYS the proxy's IP — every limit (`10/hour` on enrollment,
`10/minute` on the executor patch, etc.) became a single bucket shared by
the whole platform. Any client could exhaust everyone's quota.

`_client_key` resolves the real IP via X-Forwarded-For, trusting the header only
when the peer is a proxy listed in TRUSTED_PROXIES (see app/core/trusted_proxy.py).

Counter storage. With `uvicorn --workers 4` (api-prod) and in-memory
counters, each worker has its own bucket and a `10/minute` is, in practice,
up to 4x that — Traefik spreads connections across the workers — and everything
resets on each deploy. That is why, with no configuration, the counters go to
the application's Redis (`REDIS_URL`) and apply to the whole API. Order of choice:

1. `RATE_LIMIT_STORAGE_URI`, if set: `redis://...` or `memory://` (the
   explicit way out to per-worker memory);
2. `REDIS_URL`, if set and it is `redis://` or `rediss://`;
3. process memory (tests, dev without Redis).

The `limits` Redis storage is synchronous: it runs on the worker's event loop,
one short round trip on the compose network per request on rate-limited routes.
Without a deadline, a stuck Redis (accepts the connection and does not answer)
holds the whole worker forever — measured: the `hit` is still blocked after
5 s. Hence the 0.25 s deadline in `_PRAZO_DO_REDIS` (the round trip to Redis in
compose takes well under 1 ms; parameters in the URI query, such as
`?socket_timeout=2`, take precedence). `in_memory_fallback_enabled` makes slowapi
fall back to memory on the first failure and return on its own when Redis
answers, instead of bringing the API down with it. With Redis stuck, the cost
is: the first failure stalls the loop for two round trips (the `hit` and an
immediate check) and, after that, slowapi checks Redis again at 2, 4, 8, 16 and
32 s intervals, and starts over — each check stalls the loop for up to one
deadline. Resolving the `redis` name (DNS) is not covered by the deadline: with
the container down, Docker forwards the query to the host's DNS.

A URI that `limits` rejects (unknown scheme, invalid port, a typo such as
`memory` without `://`) falls back to memory with an error in the log, instead
of breaking the import — and with it the four workers.
"""
import os
from urllib.parse import urlsplit

from slowapi import Limiter

from app.core.trusted_proxy import get_client_ip
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

# Deadline of each limiter round trip to Redis, in seconds (see the docstring).
# redis-py 7 does not retry a timeout.
_PRAZO_DO_REDIS = {"socket_timeout": 0.25, "socket_connect_timeout": 0.25}
# `limits` schemes that open a direct redis-py connection and accept the deadline.
# Sentinel and cluster take other parameters: whoever uses them passes the
# deadline in the URI query.
_ESQUEMAS_COM_PRAZO = ("redis", "rediss", "redis+unix", "valkey", "valkeys", "valkey+unix")
_ESQUEMAS_REDIS = ("redis", "rediss")


def _client_key(request) -> str:
    return get_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )


def _storage_do_limiter() -> str:
    """URI of the counter storage (see the order in the module docstring)."""
    explicita = (os.getenv("RATE_LIMIT_STORAGE_URI") or "").strip()
    if explicita:
        return explicita
    redis_da_aplicacao = (os.getenv("REDIS_URL") or "").strip()
    if not redis_da_aplicacao:
        return "memory://"
    if _esquema(redis_da_aplicacao) not in _ESQUEMAS_REDIS:
        # `unix://` and the like work for redis-py, but `limits` does not know the
        # scheme and would reject it at import — the API would not even start.
        # Here, since it is only the default, memory with a warning; whoever wants
        # the socket sets RATE_LIMIT_STORAGE_URI=redis+unix://...
        logger.warning(
            "Rate limit: REDIS_URL com esquema %r nao serve ao limiter; contadores em memoria de cada worker.",
            _esquema(redis_da_aplicacao),
        )
        return "memory://"
    return redis_da_aplicacao


def _esquema(uri: str) -> str:
    """The URI scheme in lowercase; "" if it cannot even be parsed."""
    try:
        return urlsplit(uri).scheme.lower()
    except ValueError:
        return ""


def _onde_ficam_os_contadores(storage_uri: str) -> str:
    """For the startup log: scheme, host, port and database — never the password.

    The URI path is not emitted whole: a password containing `/` makes `urlsplit`
    push the rest of it into the path.
    """
    if _esquema(storage_uri) == "memory":
        return "memoria de cada worker (cada limite vale por worker)"
    try:
        partes = urlsplit(storage_uri)
        host = partes.hostname or "?"
        porta = f":{partes.port}" if partes.port else ""
    except ValueError:
        return f"{_esquema(storage_uri) or '?'}://? (compartilhados; memoria se cair)"
    banco = partes.path if partes.path[1:].isdigit() else ""
    return f"{partes.scheme}://{host}{porta}{banco} (compartilhados; memoria se cair)"


def _novo_limiter(storage_uri: str) -> Limiter:
    esquema = _esquema(storage_uri)
    return Limiter(
        key_func=_client_key,
        storage_uri=storage_uri,
        storage_options=dict(_PRAZO_DO_REDIS) if esquema in _ESQUEMAS_COM_PRAZO else {},
        # Only makes sense with external storage — in memory there is nothing to "go down".
        in_memory_fallback_enabled=esquema != "memory",
    )


def criar_limiter() -> Limiter:
    """Redis (with in-memory fallback) by default; memory without Redis or with `memory://`."""
    storage_uri = _storage_do_limiter()
    try:
        limiter = _novo_limiter(storage_uri)
    except Exception as exc:
        # Scheme that `limits` does not know, invalid port, uppercase that redis-py
        # rejects: breaking the import would bring down the whole API. Only the
        # exception TYPE goes to the log: the message quotes pieces of the URI, and
        # with them the password ("Port could not be cast to integer value as '<password>'").
        logger.error(
            "Rate limit: storage %s recusado (%s); contadores em memoria de cada worker.",
            _onde_ficam_os_contadores(storage_uri), type(exc).__name__,
        )
        storage_uri = "memory://"
        limiter = _novo_limiter(storage_uri)
    logger.info("Rate limit: contadores em %s", _onde_ficam_os_contadores(storage_uri))
    return limiter


# single rate-limiter instance for the whole application
limiter = criar_limiter()
