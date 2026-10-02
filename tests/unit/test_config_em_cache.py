# tests/unit/test_config_em_cache.py
"""`app/core/config_em_cache.py` — a leitura com cache que o modelo do
assistente, a forma da cota e o plano de cada pessoa repetiam.

O que se prende aqui é a peça, com uma configuração de brinquedo (um texto
qualquer): os testes de cada serviço provam o valor de cada um, e estes provam
as três regras que valem para todos.

1. Degradação aberta: Redis ou banco fora do ar nunca viram exceção.
2. O padrão de uma FALHA do banco não vai para o cache.
3. Quem só lê grava com `NX`; quem salva grava por cima — e a corrida entre os
   dois termina com o valor salvo.
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
    assert ("set", CACHE, True, 300) in redis.chamadas     # NX: quem só leu não pisa


async def test_hit_nao_toca_o_banco():
    """`db=None` e nenhuma sessão própria: se fosse ao banco, levantaria."""
    redis = RedisFalso()
    redis.dados[CACHE] = "roxo"
    with patch("app.mcp.infra.sessao", side_effect=AssertionError("foi ao banco")):
        assert await _config().em_uso(redis=redis) == "roxo"


async def test_nada_salvo_vale_o_padrao_e_ele_vai_para_o_cache(db):
    """Sem linha no banco não é falha: o padrão é a resposta certa e pode ficar."""
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


# ── Degradação aberta ───────────────────────────────────────────────────────

async def test_redis_fora_do_ar_le_o_banco(db):
    await set_config(db, CHAVE, {"cor": "verde"})
    assert await _config().em_uso(db=db, redis=RedisQuebrado()) == "verde"


async def test_banco_fora_do_ar_da_o_padrao_e_NAO_o_grava_no_cache(db):
    """A regra 2: gravado, o padrão da falha valeria por um TTL inteiro depois
    de o banco voltar."""
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
    assert salvo["em"]                                    # ISO de quando


async def test_definir_none_apaga_e_volta_ao_padrao(db):
    await _config().definir(db, "verde", por="ana")
    await _config().definir(db, None, por="ana")

    assert await get_config(db, CHAVE) is None
    assert await _config().em_uso(db=db) == PADRAO
    assert await _config().carimbo(db) is None


async def test_definir_grava_por_cima_no_cache(db):
    redis = RedisFalso()
    await _config().em_uso(db=db, redis=redis)           # popula com o padrão
    assert redis.dados[CACHE] == PADRAO

    await _config().definir(db, "verde", redis=redis)
    assert redis.dados[CACHE] == "verde"                  # sem NX: quem salva ganha
    assert await _config().em_uso(db=db, redis=redis) == "verde"

    await _config().definir(db, None, redis=redis)
    assert redis.dados[CACHE] == PADRAO                   # voltar ao padrão também grava


async def test_leitor_atrasado_nao_repinta_o_valor_velho(db):
    """A regra 3, encenada: o leitor dá miss e vai ao banco; ENQUANTO ele lê o
    valor antigo, o admin salva outro. O leitor termina gravando o que leu — e
    o `NX` o faz desistir: o valor salvo fica no cache."""
    redis = RedisFalso()
    await set_config(db, CHAVE, {"cor": "velho"})

    async def _leitura_atropelada():
        lido = _ler(await get_config(db, CHAVE))          # o leitor lê o velho...
        await _config().definir(db, "novo", redis=redis)  # ...e o admin salva no meio
        return lido

    lido = await ler_com_cache(
        redis, CACHE, _leitura_atropelada, ttl_s=300, rotulo="Teste", so_se_vazio=True,
    )
    assert lido == "velho"                  # a conversa em curso usa o que leu
    assert redis.dados[CACHE] == "novo"     # mas não repinta o cache
    assert await _config().em_uso(db=db, redis=redis) == "novo"


# ── O carimbo que a tela mostra ─────────────────────────────────────────────

async def test_carimbo_traz_valor_quem_e_quando(db):
    await _config().definir(db, "verde", por="ana")
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por) == ("verde", "ana")
    assert carimbo.em


async def test_carimbo_le_pelo_mesmo_ler_das_conversas(db):
    """Uma linha fora do envelope (edição à mão): se as conversas a usam, a tela
    não pode dizer que vale o padrão."""
    await set_config(db, CHAVE, "verde")
    assert await _config().em_uso(db=db) == "verde"
    carimbo = await _config().carimbo(db)
    assert (carimbo.valor, carimbo.por, carimbo.em) == ("verde", None, None)


# ── `ler_com_cache` sem NX e `invalidar_cache` (o plano de cada pessoa) ──────

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
