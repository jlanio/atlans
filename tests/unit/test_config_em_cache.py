# tests/unit/test_config_em_cache.py
"""`app/core/config_em_cache.py` — the cached read that the assistant model,
the quota shape and each person's plan used to repeat.

What is pinned here is the piece, with a toy configuration (any text at
all): each service's tests prove each one's value, and these prove the three
rules that hold for all of them.

1. Fail open: Redis or the database being down never becomes an exception.
2. The default from a database FAILURE does not go into the cache.
3. A reader writes with `NX`; a saver overwrites — and the race between the
   two ends with the saved value.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config_em_cache import (
    ConfigEmCache,
    invalidate_cache,
    read_with_cache,
)
from app.core.system_config import get_config, set_config
from app.models.base import Base
from app.models.system_config import SystemConfig

from ._mcp_harness import FakeRedis

CHAVE = "teste.cor"
CACHE = "teste:cor"
DEFAULT_VERSION = "azul"


def _read(valor):
    if isinstance(valor, dict):
        valor = valor.get("cor")
    return valor if isinstance(valor, str) and valor.isalpha() else None


def _config() -> ConfigEmCache[str]:
    return ConfigEmCache(
        chave=CHAVE, cache_key=CACHE, ttl_s=300, campo="cor",
        ler=_read, padrao=lambda: DEFAULT_VERSION, rotulo="Teste",
    )


class BrokenSession:
    async def execute(self, *a, **kw):
        raise RuntimeError("banco fora do ar")


class BrokenRedis:
    async def get(self, *a, **k):
        raise RuntimeError("fora do ar")

    async def set(self, *a, **k):
        raise RuntimeError("fora do ar")

    async def delete(self, *a, **k):
        raise RuntimeError("fora do ar")


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[SystemConfig.__table__])
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


# ── Hit e miss ───────────────────────────────────────────────────────────────

async def test_miss_reads_the_db_and_writes_with_nx_and_ttl(db):
    await set_config(db, CHAVE, {"cor": "verde", "por": "ana", "em": "2026-09-30"})
    redis = FakeRedis()

    assert await _config().in_use(db=db, redis=redis) == "verde"
    assert redis.dados[CACHE] == "verde"
    assert ("set", CACHE, True, 300) in redis.chamadas     # NX: a mere reader does not clobber


async def test_hit_does_not_touch_the_db():
    """`db=None` and no session of its own: if it went to the database, it would raise."""
    redis = FakeRedis()
    redis.dados[CACHE] = "roxo"
    with patch("app.mcp.infra.sessao", side_effect=AssertionError("foi ao banco")):
        assert await _config().in_use(redis=redis) == "roxo"


async def test_nothing_saved_uses_the_default_and_it_goes_to_cache(db):
    """No row in the database is not a failure: the default is the right answer and can stay."""
    redis = FakeRedis()
    assert await _config().in_use(db=db, redis=redis) == DEFAULT_VERSION
    assert redis.dados[CACHE] == DEFAULT_VERSION


async def test_unusable_saved_value_falls_back_to_default(db):
    await set_config(db, CHAVE, {"cor": "não é cor 123"})
    assert await _config().in_use(db=db) == DEFAULT_VERSION


async def test_cache_that_does_not_deserialize_counts_as_miss(db):
    config = ConfigEmCache(
        chave=CHAVE, cache_key=CACHE, ttl_s=300, campo="cor", ler=_read,
        padrao=lambda: DEFAULT_VERSION, rotulo="Teste",
        serializar=json.dumps, desserializar=json.loads,
    )
    await set_config(db, CHAVE, {"cor": "verde"})
    redis = FakeRedis()
    redis.dados[CACHE] = "{isto não é json"

    assert await config.in_use(db=db, redis=redis) == "verde"


# ── Fail open ───────────────────────────────────────────────────────────────

async def test_redis_down_reads_the_db(db):
    await set_config(db, CHAVE, {"cor": "verde"})
    assert await _config().in_use(db=db, redis=BrokenRedis()) == "verde"


async def test_db_down_gives_the_default_and_does_NOT_cache_it(db):
    """Rule 2: if written, the failure's default would hold for a whole TTL after
    the database came back."""
    await set_config(db, CHAVE, {"cor": "verde"})
    redis = FakeRedis()

    assert await _config().in_use(db=BrokenSession(), redis=redis) == DEFAULT_VERSION
    assert CACHE not in redis.dados
    assert await _config().in_use(db=db, redis=redis) == "verde"


async def test_without_session_opens_its_own_and_its_failure_also_gives_default():
    class Explode:
        def __call__(self):
            raise RuntimeError("sem banco")

    redis = FakeRedis()
    with patch("app.mcp.infra.sessao", Explode()):
        assert await _config().in_use(redis=redis) == DEFAULT_VERSION
    assert CACHE not in redis.dados


async def test_without_session_reads_through_own_session(db):
    await set_config(db, CHAVE, {"cor": "verde"})

    @asynccontextmanager
    async def _own_session():
        yield db

    with patch("app.mcp.infra.sessao", _own_session):
        assert await _config().in_use() == "verde"


# ── Salvar: o envelope, e o cache por cima ──────────────────────────────────

async def test_set_writes_the_envelope_with_the_stamp(db):
    await _config().definir(db, "verde", por="ana")

    salvo = await get_config(db, CHAVE)
    assert (salvo["cor"], salvo["por"]) == ("verde", "ana")
    assert salvo["em"]                                    # ISO timestamp of when


async def test_set_none_deletes_and_returns_to_default(db):
    await _config().definir(db, "verde", por="ana")
    await _config().definir(db, None, por="ana")

    assert await get_config(db, CHAVE) is None
    assert await _config().in_use(db=db) == DEFAULT_VERSION
    assert await _config().carimbo(db) is None


async def test_set_overwrites_in_the_cache(db):
    redis = FakeRedis()
    await _config().in_use(db=db, redis=redis)           # populates with the default
    assert redis.dados[CACHE] == DEFAULT_VERSION

    await _config().definir(db, "verde", redis=redis)
    assert redis.dados[CACHE] == "verde"                  # no NX: the saver wins
    assert await _config().in_use(db=db, redis=redis) == "verde"

    await _config().definir(db, None, redis=redis)
    assert redis.dados[CACHE] == DEFAULT_VERSION                   # going back to the default also writes


async def test_late_reader_does_not_repaint_the_old_value(db):
    """Rule 3, staged: the reader misses and goes to the database; WHILE it reads
    the old value, the admin saves another. The reader ends by writing what it
    read — and `NX` makes it give up: the saved value stays in the cache."""
    redis = FakeRedis()
    await set_config(db, CHAVE, {"cor": "velho"})

    async def _overrun_read():
        lido = _read(await get_config(db, CHAVE))          # the reader reads the old one...
        await _config().definir(db, "novo", redis=redis)  # ...e o admin salva no meio
        return lido

    lido = await read_with_cache(
        redis, CACHE, _overrun_read, ttl_s=300, rotulo="Teste", only_if_empty=True,
    )
    assert lido == "velho"                  # the ongoing conversation uses what it read
    assert redis.dados[CACHE] == "novo"     # but does not repaint the cache
    assert await _config().in_use(db=db, redis=redis) == "novo"


# ── O carimbo que a tela mostra ─────────────────────────────────────────────

async def test_stamp_carries_value_who_and_when(db):
    await _config().definir(db, "verde", por="ana")
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por) == ("verde", "ana")
    assert carimbo.em


async def test_stamp_reads_through_the_same_reader_as_conversations(db):
    """A row outside the envelope (hand-edited): if the conversations use it, the
    screen cannot say the default applies."""
    await set_config(db, CHAVE, "verde")
    assert await _config().in_use(db=db) == "verde"
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por, carimbo.em) == ("verde", None, None)


# ── `read_with_cache` without NX and `invalidate_cache` (each person's plan) ────

async def test_read_without_nx_overwrites_cache_garbage():
    redis = FakeRedis()
    redis.dados["plano:u"] = "lixo"

    async def _from_db():
        return "pro"

    lido = await read_with_cache(
        redis, "plano:u", _from_db, ttl_s=300, rotulo="Teste",
        desserializar=lambda t: t if t in ("free", "pro") else None,
    )
    assert lido == "pro"
    assert redis.dados["plano:u"] == "pro"
    assert redis.ttls["plano:u"] == 300


async def test_invalidate_deletes_and_tolerates_redis_missing_or_down():
    redis = FakeRedis()
    redis.dados["plano:u"] = "pro"
    await invalidate_cache(redis, "plano:u", rotulo="Teste")
    assert "plano:u" not in redis.dados

    await invalidate_cache(None, "plano:u", rotulo="Teste")
    await invalidate_cache(BrokenRedis(), "plano:u", rotulo="Teste")
