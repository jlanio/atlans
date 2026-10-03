# tests/unit/test_assistente_config_service.py
"""Which model the assistant uses — env as the floor, database on top.

What is pinned here, in order of how costly it is to get wrong:

1. **Never returns empty.** Redis down, database down, corrupted row: everything
   falls back to the environment default. Having no model would mean the whole
   assistant down because of a setting.
2. **The admin's choice beats the env**, otherwise the button does nothing.
3. **Saving invalidates the cache.** Without that, the change takes up to five
   minutes to take effect, and the admin concludes the button is broken — and
   clicks again.
4. **An invalid id is rejected on SAVE**, not on each user's next conversation.
   A mistyped `antropic/claude-opus-5` does not fail when saving; it fails in
   production, for everyone, with nobody knowing why.
"""
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import ASSISTENTE_MODELO
from app.models.base import Base
from app.models.system_config import SystemConfig
from app.services import assistente_config_service as svc

from ._mcp_harness import RedisFalso

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[SystemConfig.__table__])
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


# ── Precedence ───────────────────────────────────────────────────────────────

async def test_sem_escolha_salva_vale_o_padrao_do_ambiente(db):
    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO
    situacao = await svc.situacao(db=db)
    assert situacao["origem"] == "ambiente"
    assert situacao["definido_em"] is None


async def test_a_escolha_do_admin_vence_o_ambiente(db):
    await svc.definir_modelo(db, "outro/modelo", por="jose")

    assert await svc.modelo_em_uso(db=db) == "outro/modelo"
    situacao = await svc.situacao(db=db)
    assert (situacao["origem"], situacao["definido_por"]) == ("banco", "jose")
    # The default stays visible: it is what the screen offers as "back to default".
    assert situacao["padrao_do_ambiente"] == ASSISTENTE_MODELO


async def test_voltar_ao_padrao_apaga_a_escolha(db):
    await svc.definir_modelo(db, "outro/modelo", por="jose")
    await svc.definir_modelo(db, None, por="jose")

    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO
    assert (await svc.situacao(db=db))["origem"] == "ambiente"


# ── O cache ──────────────────────────────────────────────────────────────────

async def test_salvar_grava_o_valor_novo_no_cache(db):
    """Without this the change takes up to five minutes to take effect, and the admin
    concludes the button didn't work — and clicks again."""
    redis = RedisFalso()
    await svc.modelo_em_uso(db=db, redis=redis)          # popula
    assert redis.dados[svc._CACHE] == ASSISTENTE_MODELO

    await svc.definir_modelo(db, "outro/modelo", por="jose", redis=redis)

    # WRITES, does not delete — see the race test right below.
    assert redis.dados[svc._CACHE] == "outro/modelo"
    assert await svc.modelo_em_uso(db=db, redis=redis) == "outro/modelo"


async def test_leitor_atrasado_nao_repinta_o_modelo_VELHO_por_cima(db):
    """The race the adversarial review found, staged step by step.

    A reader misses the cache and goes to the database. WHILE it reads, the admin
    saves another model. If the reader finished with a blind SET, it would paint
    the old value over the new one and pin it for the five minutes of the TTL: the
    change "wouldn't take", and whoever saved would conclude the button is broken.
    """
    redis = RedisFalso()

    # The reader has already read the database (old model) and only needs to write
    # to the cache. In between, the change happens:
    await svc.definir_modelo(db, "novo/modelo", por="jose", redis=redis)

    # Now the late reader tries to write what it read. `nx` makes it give up.
    await redis.set(svc._CACHE, "velho/modelo", ex=svc._TTL_S, nx=True)

    assert redis.dados[svc._CACHE] == "novo/modelo"
    assert await svc.modelo_em_uso(db=db, redis=redis) == "novo/modelo"


async def test_redis_fora_do_ar_nao_deixa_ninguem_sem_modelo(db):
    class RedisQuebrado:
        async def get(self, *a, **k): raise RuntimeError("fora do ar")
        async def set(self, *a, **k): raise RuntimeError("fora do ar")

    await svc.definir_modelo(db, "outro/modelo")
    assert await svc.modelo_em_uso(db=db, redis=RedisQuebrado()) == "outro/modelo"


async def test_falha_do_banco_nao_prende_o_padrao_no_cache(db):
    """The default from a database ERROR does not go into the cache.

    Writing it would lock the installation into the environment's model for five
    minutes AFTER the database came back: the admin's choice would vanish with
    nothing on the screen explaining it. It is the rule another copy of the
    "SystemConfig + cache" skeleton already followed — and that this one didn't take.
    """
    await svc.definir_modelo(db, "outro/modelo", por="jose")
    redis = RedisFalso()

    class SessaoQuebrada:
        async def execute(self, *a, **kw):
            raise RuntimeError("banco fora do ar")

    assert await svc.modelo_em_uso(db=SessaoQuebrada(), redis=redis) == ASSISTENTE_MODELO
    assert svc._CACHE not in redis.dados

    # Once the database is back, the first read already sees the admin's choice.
    assert await svc.modelo_em_uso(db=db, redis=redis) == "outro/modelo"


async def test_banco_fora_do_ar_cai_no_padrao_em_vez_de_levantar():
    """The whole assistant down because of a setting would be a bad trade: the
    environment default is always better than nothing."""
    class Explode:
        def __call__(self): raise RuntimeError("banco fora do ar")

    with patch("app.mcp.infra.sessao", Explode()):
        assert await svc.modelo_em_uso() == ASSISTENTE_MODELO


# ── Validation ───────────────────────────────────────────────────────────────

# Without a slash it is valid: it is the name on a local server (`llama3.1`, `qwen3:14b`).
@pytest.mark.parametrize("ruim", [
    "", "   ", "fornecedor//modelo", "fornecedor/", "/modelo",
    "com espaço/no meio", "https://openrouter.ai/api/v1/x", "a/" + "x" * 200,
])
async def test_id_invalido_e_recusado_ao_salvar(db, ruim):
    """Rejecting here is rejecting once; letting it through is failing on the next
    conversation of EVERY user, without the screen saying why."""
    with pytest.raises(ValueError):
        await svc.definir_modelo(db, ruim)
    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO


async def test_linha_corrompida_no_banco_nao_derruba_a_leitura(db):
    """Someone editing `system_config` by hand, a botched migration: the read
    ignores what doesn't look like an id and falls back to the default."""
    from app.core.system_config import set_config

    await set_config(db, svc.CHAVE, {"modelo": "isto não é um id"})
    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO
    assert (await svc.situacao(db=db))["origem"] == "ambiente"
