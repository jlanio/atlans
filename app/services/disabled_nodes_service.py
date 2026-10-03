# app/services/disabled_nodes_service.py
"""
Service for managing nodes disabled by the admin.

Persistence: SystemConfig with key `disabled_nodes` -> dict of
metadata per node name:

    {
      "SendEmail": {
        "disabled_at": "2026-06-18T14:30:00Z",
        "disabled_by": "<user_id_hash>",
        "reason": "Security audit in progress"
      }
    }

No migration — reuses an existing table.
"""
from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_config import get_config, set_config
from app.core.utils.logger import get_logger

_logger = get_logger(__name__)

_CONFIG_KEY = "disabled_nodes"

# ── In-memory cache, coordinated across workers by an epoch in Redis ─────────
#
# Symptom the CACHE fixes: EVERY workflow trigger (POST /execute, webhook and
# cron) did a SELECT on SystemConfig in the hot path just to find out a value
# that changes once a month — a whole round trip to Postgres added to the
# latency between the click on "Executar" (Run) and the job leaving the server.
#
# Symptom the EPOCH fixes: production runs the API with `uvicorn --workers 4`,
# so `_cache` exists in 4 independent copies and `invalidate_cache()` only
# reaches the process that served the admin's PATCH. With a pure TTL this gave
# (a) a node disabled because of an incident still being dispatched by the other
# 3 workers for up to 30 s — and the `disabled_nodes` snapshot that goes in the
# job envelope comes out of THIS same cache, so the executor revalidates against
# the stale list and lets it through all the same (there is no second
# independent source) — and (b) broken read-after-write in the UI: the next
# GET /admin/nodes landed on another worker, returned `enabled: true` and the
# toggle undid itself on screen.
#
# How it works: every write does an INCR on the epoch key; the read checks the
# epoch (a GET on Redis — which dispatch already uses and costs a fraction of the
# SELECT+deserialization on Postgres) and only goes to the database when it has
# changed. The local TTL was kept as the degradation for Redis being unavailable:
# in that case the 30 s staleness ceiling applies again, and dispatch does not
# break because of it.
_EPOCH_KEY = "disabled_nodes:epoch"
_CACHE_TTL_S = 30.0
_cache: dict[str, dict[str, Any]] | None = None
_cache_epoch: str | None = None
_cache_expires_at: float = 0.0


def _redis():
    from app.core.redis import get_redis_pool
    return get_redis_pool()


async def _read_epoch() -> str | None:
    """Current epoch, or None when Redis cannot be queried.

    A missing key counts as "0" (initial state, no write yet) — and is different
    from None, which means "could not tell" and falls back to the local TTL.
    """
    try:
        valor = await _redis().get(_EPOCH_KEY)
    except Exception as exc:
        # Downgraded to debug on purpose: it happens once per read and the
        # degradation path (local TTL) is the behavior documented above.
        _logger.debug("Epoca de disabled_nodes indisponivel no Redis: %s", exc)
        return None
    return valor if valor is not None else "0"


async def _publish_invalidation() -> None:
    """Tells the OTHER workers that the map changed, by incrementing the epoch."""
    try:
        await _redis().incr(_EPOCH_KEY)
    except Exception as exc:
        _logger.warning(
            "Falha ao publicar invalidacao de disabled_nodes no Redis (%s): os "
            "demais workers so verao a mudanca quando o TTL de %.0fs vencer.",
            exc, _CACHE_TTL_S,
        )


def invalidate_cache() -> None:
    """Discards the process cache. Every write calls it; so do tests."""
    global _cache, _cache_epoch, _cache_expires_at
    _cache = None
    _cache_epoch = None
    _cache_expires_at = 0.0


async def list_disabled(db: AsyncSession) -> dict[str, dict[str, Any]]:
    """Returns the current map of disabled nodes {name: metadata}.

    The returned dict is the cached object itself — whoever needs to change it
    copies it first (see `set_disabled`/`set_enabled`).
    """
    global _cache, _cache_epoch, _cache_expires_at

    # The epoch is read BEFORE the SELECT on purpose: if a write comes in between,
    # the new map is stored under the old epoch and the next read reloads it
    # (cost: one extra SELECT). Reading the epoch AFTER would stamp old data as
    # current and the cache would stay stale until the TTL expired.
    epoch = await _read_epoch()
    agora = monotonic()

    if _cache is not None:
        if epoch is not None:
            if epoch == _cache_epoch:
                return _cache
        elif agora < _cache_expires_at:
            return _cache

    raw = await get_config(db, _CONFIG_KEY, default={})
    # Defense: the type returned from the JSON may come as a list in a corrupted config
    if not isinstance(raw, dict):
        raw = {}

    _cache = raw
    _cache_epoch = epoch
    _cache_expires_at = agora + _CACHE_TTL_S
    return _cache


async def disabled_names(db: AsyncSession) -> set[str]:
    """Shortcut: just the names (for use in set-based filters)."""
    cfg = await list_disabled(db)
    return set(cfg.keys())


async def set_disabled(
    db: AsyncSession, name: str, *, by: str, reason: str
) -> dict[str, Any]:
    """Marca um node como desabilitado. Idempotente: atualiza metadata."""
    cfg = dict(await list_disabled(db))
    entry = {
        "disabled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "disabled_by": by,
        "reason": reason,
    }
    cfg[name] = entry
    await set_config(db, _CONFIG_KEY, cfg)
    invalidate_cache()
    # After set_config's commit: whoever reads the new epoch must find the new
    # map in the database, never the other way around.
    await _publish_invalidation()
    return entry


async def set_enabled(db: AsyncSession, name: str) -> bool:
    """Removes the node from the map. Returns True if it removed something."""
    cfg = dict(await list_disabled(db))
    if name not in cfg:
        return False
    cfg.pop(name)
    await set_config(db, _CONFIG_KEY, cfg)
    invalidate_cache()
    await _publish_invalidation()
    return True
