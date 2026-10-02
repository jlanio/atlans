"""Rate limit de /auth/refresh por FAMÍLIA (refresh_rate_exceeded).

O limite por IP transformava o hop interno Next→API num balde único de
plataforma: estourá-lo devolvia 429, que o front tratava como "refresh
expirado" e deslogava todo mundo. Agora o limite é por sessão (família) — um
usuário nunca esgota a cota de outro. Estes testes fixam a contagem, a janela
e o teto.
"""
import pytest
from unittest.mock import patch

from app.core.utils.jwt_utils import (
    refresh_rate_exceeded,
    _REFRESH_RATE_LIMIT,
    _REFRESH_RATE_WINDOW,
    _REFRESH_RATE_PREFIX,
)
from tests.unit._mcp_harness import RedisFalso

CHAVE = f"{_REFRESH_RATE_PREFIX}fam-1"


def _redis(contagem_anterior: int | None = None) -> RedisFalso:
    """Redis em memória; `contagem_anterior` é o que a família já gastou na janela."""
    r = RedisFalso()
    if contagem_anterior is not None:
        r.dados[CHAVE] = contagem_anterior
        r.ttls[CHAVE] = _REFRESH_RATE_WINDOW
    return r


@pytest.mark.asyncio
async def test_dentro_do_teto_nao_excede():
    r = _redis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is False
    # a chave é por família, e a primeira contagem arma a janela
    assert r.dados == {CHAVE: 1}
    assert r.ttls[CHAVE] == _REFRESH_RATE_WINDOW


@pytest.mark.asyncio
async def test_no_teto_ainda_permite():
    r = _redis(_REFRESH_RATE_LIMIT - 1)
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is False
    assert r.dados[CHAVE] == _REFRESH_RATE_LIMIT


@pytest.mark.asyncio
async def test_acima_do_teto_excede():
    r = _redis(_REFRESH_RATE_LIMIT)
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await refresh_rate_exceeded("fam-1") is True


@pytest.mark.asyncio
async def test_contagens_seguintes_nao_empurram_a_janela():
    # 2ª contagem em diante NÃO re-arma o TTL (janela fixa): senão uma sessão
    # em laço nunca veria a janela fechar.
    r = _redis(1)
    r.ttls[CHAVE] = 12  # a janela já está correndo
    with patch("app.core.redis.get_redis_pool", return_value=r):
        await refresh_rate_exceeded("fam-1")
    assert r.ttls[CHAVE] == 12


@pytest.mark.asyncio
async def test_familias_distintas_baldes_distintos():
    # Duas famílias → duas chaves diferentes; uma não consome a cota da outra.
    r = _redis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        await refresh_rate_exceeded("fam-A")
        await refresh_rate_exceeded("fam-B")
    assert r.dados == {f"{_REFRESH_RATE_PREFIX}fam-A": 1, f"{_REFRESH_RATE_PREFIX}fam-B": 1}
