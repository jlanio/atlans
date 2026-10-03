# app/mcp/infra.py
"""
The MCP's two points of contact with the infrastructure — and the two `patch`
points of the tests.

The database session and the Redis pool are ALWAYS obtained through here, never
by importing `get_session_async`/`get_redis_pool` directly in an MCP module. The
reason is practical: `patch("app.mcp.infra.sessao")` and
`patch("app.mcp.infra.redis_ou_none")` swap the server's entire infrastructure
at once, and no test needs a real Postgres or Redis. If a module imported the
original function, that `patch` would pass it by.

Consequence for whoever writes a tool: import the MODULE (`from app.mcp import
infra`) and call `infra.sessao()`; a `from app.mcp.infra import sessao` at the
top freezes the reference and escapes the patch.
"""
from __future__ import annotations

from app.core.db import get_session_async
from app.core.redis import get_redis_pool, new_pubsub_client

# Database session: an async context manager that rolls back in `finally` —
# whoever writes has to commit on their own.
sessao = get_session_async

# `new_pubsub_client` (a dedicated Redis client for a long pub/sub subscription,
# such as waiting on a run) is re-exported from here for the same reason: a
# single swap point in the tests.


def redis_ou_none():
    """The Redis pool, or `None` when it has not been initialized.

    `get_redis_pool()` raises `RuntimeError` outside the lifespan (tests,
    scripts, a worker that started without `init_redis`). Nothing in the MCP
    should die because of that: quotas fail open and the last-used stamp simply
    does not happen. Redis being down is a transient failure, not an operating
    mode.
    """
    try:
        return get_redis_pool()
    except RuntimeError:
        return None


__all__ = ["sessao", "redis_ou_none", "new_pubsub_client"]
