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
    invalidar_cache,
    ler_com_cache,
)
from app.core.system_config import get_config, set_config
from app.models.base import Base
from app.models.system_config import SystemConfig

from ._mcp_harness import RedisFalso

CHAVE = "teste.cor"
CACHE = "teste:cor"
PADRAO = "azul"


def _ler(valor):
    if isinstance(valor, dict):
        valor = valor.get("cor")
    return valor if isinstance(valor, str) and valor.isalpha() else None


def _config() -> ConfigEmCache[str]:
    return ConfigEmCache(
        chave=CHAVE, chave_cache=CACHE, ttl_s=300, campo="cor",
        ler=_ler, padrao=lambda: PADRAO, rotulo="Teste",
    )


class SessaoQuebrada:
    async def execute(self, *a, **kw):
        raise RuntimeError("banco fora do ar")


class RedisQuebrado:
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

async def test_miss_le_o_banco_e_grava_com_nx_e_ttl(db):
    await set_config(db, CHAVE, {"cor": "verde", "por": "ana", "em": "2026-09-30"})
    redis = RedisFalso()

    assert await _config().em_uso(db=db, redis=redis) == "verde"
    assert redis.dados[CACHE] == "verde"
    assert ("set", CACHE, True, 300) in redis.chamadas     # NX: a mere reader does not clobber


async def test_hit_nao_toca_o_banco():
    """`db=None` and no session of its own: if it went to the database, it would raise."""
    redis = RedisFalso()
    redis.dados[CACHE] = "roxo"
    with patch("app.mcp.infra.sessao", side_effect=AssertionError("foi ao banco")):
        assert await _config().em_uso(redis=redis) == "roxo"


async def test_nada_salvo_vale_o_padrao_e_ele_vai_para_o_cache(db):
    """No row in the database is not a failure: the default is the right answer and can stay."""
    redis = RedisFalso()
    assert await _config().em_uso(db=db, redis=redis) == PADRAO
    assert redis.dados[CACHE] == PADRAO


async def test_valor_salvo_que_nao_serve_cai_no_padrao(db):
    await set_config(db, CHAVE, {"cor": "não é cor 123"})
    assert await _config().em_uso(db=db) == PADRAO


async def test_cache_que_nao_se_desserializa_conta_como_miss(db):
    config = ConfigEmCache(
        chave=CHAVE, chave_cache=CACHE, ttl_s=300, campo="cor", ler=_ler,
        padrao=lambda: PADRAO, rotulo="Teste",
        serializar=json.dumps, desserializar=json.loads,
    )
    await set_config(db, CHAVE, {"cor": "verde"})
    redis = RedisFalso()
    redis.dados[CACHE] = "{isto não é json"

    assert await config.em_uso(db=db, redis=redis) == "verde"


# ── Fail open ───────────────────────────────────────────────────────────────

async def test_redis_fora_do_ar_le_o_banco(db):
    await set_config(db, CHAVE, {"cor": "verde"})
    assert await _config().em_uso(db=db, redis=RedisQuebrado()) == "verde"


async def test_banco_fora_do_ar_da_o_padrao_e_NAO_o_grava_no_cache(db):
    """Rule 2: if written, the failure's default would hold for a whole TTL after
    the database came back."""
    await set_config(db, CHAVE, {"cor": "verde"})
    redis = RedisFalso()

    assert await _config().em_uso(db=SessaoQuebrada(), redis=redis) == PADRAO
    assert CACHE not in redis.dados
    assert await _config().em_uso(db=db, redis=redis) == "verde"


async def test_sem_sessao_abre_uma_propria_e_a_falha_dela_tambem_e_padrao():
    class Explode:
        def __call__(self):
            raise RuntimeError("sem banco")

    redis = RedisFalso()
    with patch("app.mcp.infra.sessao", Explode()):
        assert await _config().em_uso(redis=redis) == PADRAO
    assert CACHE not in redis.dados


async def test_sem_sessao_le_pela_sessao_propria(db):
    await set_config(db, CHAVE, {"cor": "verde"})

    @asynccontextmanager
    async def _propria():
        yield db

    with patch("app.mcp.infra.sessao", _propria):
        assert await _config().em_uso() == "verde"


# ── Salvar: o envelope, e o cache por cima ──────────────────────────────────

async def test_definir_grava_o_envelope_com_o_carimbo(db):
    await _config().definir(db, "verde", por="ana")

    salvo = await get_config(db, CHAVE)
    assert (salvo["cor"], salvo["por"]) == ("verde", "ana")
    assert salvo["em"]                                    # ISO timestamp of when


async def test_definir_none_apaga_e_volta_ao_padrao(db):
    await _config().definir(db, "verde", por="ana")
    await _config().definir(db, None, por="ana")

    assert await get_config(db, CHAVE) is None
    assert await _config().em_uso(db=db) == PADRAO
    assert await _config().carimbo(db) is None


async def test_definir_grava_por_cima_no_cache(db):
    redis = RedisFalso()
    await _config().em_uso(db=db, redis=redis)           # populates with the default
    assert redis.dados[CACHE] == PADRAO

    await _config().definir(db, "verde", redis=redis)
    assert redis.dados[CACHE] == "verde"                  # no NX: the saver wins
    assert await _config().em_uso(db=db, redis=redis) == "verde"

    await _config().definir(db, None, redis=redis)
    assert redis.dados[CACHE] == PADRAO                   # going back to the default also writes


async def test_leitor_atrasado_nao_repinta_o_valor_velho(db):
    """Rule 3, staged: the reader misses and goes to the database; WHILE it reads
    the old value, the admin saves another. The reader ends by writing what it
    read — and `NX` makes it give up: the saved value stays in the cache."""
    redis = RedisFalso()
    await set_config(db, CHAVE, {"cor": "velho"})

    async def _leitura_atropelada():
        lido = _ler(await get_config(db, CHAVE))          # the reader reads the old one...
        await _config().definir(db, "novo", redis=redis)  # ...e o admin salva no meio
        return lido

    lido = await ler_com_cache(
        redis, CACHE, _leitura_atropelada, ttl_s=300, rotulo="Teste", so_se_vazio=True,
    )
    assert lido == "velho"                  # the ongoing conversation uses what it read
    assert redis.dados[CACHE] == "novo"     # but does not repaint the cache
    assert await _config().em_uso(db=db, redis=redis) == "novo"


# ── O carimbo que a tela mostra ─────────────────────────────────────────────

async def test_carimbo_traz_valor_quem_e_quando(db):
    await _config().definir(db, "verde", por="ana")
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por) == ("verde", "ana")
    assert carimbo.em


async def test_carimbo_le_pelo_mesmo_ler_das_conversas(db):
    """A row outside the envelope (hand-edited): if the conversations use it, the
    screen cannot say the default applies."""
    await set_config(db, CHAVE, "verde")
    assert await _config().em_uso(db=db) == "verde"
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por, carimbo.em) == ("verde", None, None)


# ── `ler_com_cache` without NX and `invalidar_cache` (each person's plan) ────

async def test_leitura_sem_nx_sobrescreve_o_lixo_do_cache():
    redis = RedisFalso()
    redis.dados["plano:u"] = "lixo"

    async def _banco():
        return "pro"

    lido = await ler_com_cache(
        redis, "plano:u", _banco, ttl_s=300, rotulo="Teste",
        desserializar=lambda t: t if t in ("free", "pro") else None,
    )
    assert lido == "pro"
    assert redis.dados["plano:u"] == "pro"
    assert redis.ttls["plano:u"] == 300


async def test_invalidar_apaga_e_tolera_redis_ausente_ou_fora():
    redis = RedisFalso()
    redis.dados["plano:u"] = "pro"
    await invalidar_cache(redis, "plano:u", rotulo="Teste")
    assert "plano:u" not in redis.dados

    await invalidar_cache(None, "plano:u", rotulo="Teste")
    await invalidar_cache(RedisQuebrado(), "plano:u", rotulo="Teste")
