# tests/unit/test_jwt_blacklist.py
"""Tests for is_token_blacklisted — fail-closed behavior when Redis goes down."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.core.utils.jwt_utils import is_token_blacklisted


@pytest.mark.asyncio
async def test_token_not_blacklisted_returns_false():
    """Caminho feliz: Redis OK e chave ausente → False."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(return_value=0)

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        result = await is_token_blacklisted("token-abc")

    assert result is False


@pytest.mark.asyncio
async def test_token_blacklisted_returns_true():
    """Caminho feliz: Redis OK e chave presente → True."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(return_value=1)

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        result = await is_token_blacklisted("token-abc")

    assert result is True


@pytest.mark.asyncio
async def test_redis_unavailable_raises_503():
    """Fail-closed: Redis down → HTTPException 503.

    Before the fix, the function silently returned False (fail-OPEN), which
    accepted revoked tokens when the blacklist's backing store was
    unavailable — defeating the purpose of logout.
    """
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(side_effect=ConnectionError("redis down"))

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await is_token_blacklisted("token-abc")

    assert exc_info.value.status_code == 503
    assert "indispon" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_redis_timeout_also_raises_503():
    """TimeoutError must also fail closed (it is not a special case)."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(side_effect=TimeoutError("op timed out"))

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await is_token_blacklisted("token-abc")

    assert exc_info.value.status_code == 503
