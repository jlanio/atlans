"""Rate limit of /auth/refresh per FAMILY (refresh_rate_exceeded).

The per-IP limit turned the internal Next→API hop into a single platform-wide
bucket: exceeding it returned 429, which the front end treated as "refresh
expired" and logged everyone out. Now the limit is per session (family) — one
user never exhausts another's quota. These tests pin the counting, the window
and the ceiling.
"""
import pytest
from unittest.mock import patch

from app.core.utils.jwt_utils import (
    refresh_rate_exceeded,
    _REFRESH_RATE_LIMIT,
    _REFRESH_RATE_WINDOW,
    _REFRESH_RATE_PREFIX,
)
from tests.unit._mcp_harness import FakeRedis

CHAVE = f"{_REFRESH_RATE_PREFIX}fam-1"


def _redis(previous_count: int | None = None) -> FakeRedis:
    """In-memory Redis; `previous_count` is what the family has already spent in the window."""
    r = FakeRedis()
    if previous_count is not None:
        r.dados[CHAVE] = previous_count
        r.ttls[CHAVE] = _REFRESH_RATE_WINDOW
    return r


@pytest.mark.asyncio
async def test_within_the_ceiling_does_not_exceed():
    r = _redis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is False
    # the key is per family, and the first count arms the window
    assert r.dados == {CHAVE: 1}
    assert r.ttls[CHAVE] == _REFRESH_RATE_WINDOW


@pytest.mark.asyncio
async def test_at_the_ceiling_still_allows():
    r = _redis(_REFRESH_RATE_LIMIT - 1)
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is False
    assert r.dados[CHAVE] == _REFRESH_RATE_LIMIT


@pytest.mark.asyncio
async def test_above_the_ceiling_exceeds():
    r = _redis(_REFRESH_RATE_LIMIT)
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is True


@pytest.mark.asyncio
async def test_subsequent_counts_do_not_push_the_window():
    # From the 2nd count on it does NOT re-arm the TTL (fixed window): otherwise a
    # session in a loop would never see the window close.
    r = _redis(1)
    r.ttls[CHAVE] = 12  # the window is already running
    with patch("app.core.redis.get_redis_pool", return_value=r):
        await refresh_rate_exceeded("fam-1")
    assert r.ttls[CHAVE] == 12


@pytest.mark.asyncio
async def test_distinct_families_distinct_buckets():
    # Two families → two different keys; one does not consume the other's quota.
    r = _redis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        await refresh_rate_exceeded("fam-A")
        await refresh_rate_exceeded("fam-B")
    assert r.dados == {f"{_REFRESH_RATE_PREFIX}fam-A": 1, f"{_REFRESH_RATE_PREFIX}fam-B": 1}
