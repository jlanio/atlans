# tests/unit/test_jwt_blacklist.py
"""Testes para is_token_blacklisted — comportamento fail-closed quando Redis cai."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.core.utils.jwt_utils import is_token_blacklisted


@pytest.mark.asyncio
async def test_token_nao_blacklisted_retorna_false():
    """Caminho feliz: Redis OK e chave ausente → False."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(return_value=0)

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        result = await is_token_blacklisted("token-abc")

    assert result is False


@pytest.mark.asyncio
async def test_token_blacklisted_retorna_true():
    """Caminho feliz: Redis OK e chave presente → True."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(return_value=1)

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        result = await is_token_blacklisted("token-abc")

    assert result is True


@pytest.mark.asyncio
async def test_redis_indisponivel_levanta_503():
    """Fail-closed: Redis fora do ar → HTTPException 503.

    Antes do fix, a função retornava False silenciosamente (fail-OPEN), o
    que aceitava tokens revogados quando o backing store da blacklist
    estava indisponível — anulando a função de logout.
    """
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(side_effect=ConnectionError("redis down"))

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await is_token_blacklisted("token-abc")

    assert exc_info.value.status_code == 503
    assert "indispon" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_redis_timeout_tambem_levanta_503():
    """TimeoutError também deve fail-close (não é caso especial)."""
    mock_redis = MagicMock()
    mock_redis.exists = AsyncMock(side_effect=TimeoutError("op timed out"))

    with patch("app.core.redis.get_redis_pool", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await is_token_blacklisted("token-abc")

    assert exc_info.value.status_code == 503
