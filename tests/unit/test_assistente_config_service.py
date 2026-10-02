# tests/unit/test_assistente_config_service.py
"""Qual modelo o assistente usa — env como piso, banco por cima.

O que se prende aqui, em ordem de quanto custa errar:

1. **Nunca devolve vazio.** Redis fora, banco fora, linha corrompida: tudo cai
   no padrão do ambiente. Ficar sem modelo significaria o assistente inteiro
   fora do ar por causa de uma configuração.
2. **A escolha do admin vence o env**, senão o botão não faz nada.
3. **Salvar invalida o cache.** Sem isso a troca demora até cinco minutos para
   valer, e o admin conclui que o botão está quebrado — e clica de novo.
4. **Id inválido é recusado ao SALVAR**, não na próxima conversa de cada
   usuário. Um `antropic/claude-opus-5` digitado errado não falha ao gravar;
   falha em produção, para todo mundo, sem ninguém saber por quê.
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


# ── A precedência ────────────────────────────────────────────────────────────

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
    # O padrão continua visível: é o que a tela oferece como «voltar ao padrão».
    assert situacao["padrao_do_ambiente"] == ASSISTENTE_MODELO


async def test_voltar_ao_padrao_apaga_a_escolha(db):
    await svc.definir_modelo(db, "outro/modelo", por="jose")
    await svc.definir_modelo(db, None, por="jose")

    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO
    assert (await svc.situacao(db=db))["origem"] == "ambiente"


# ── O cache ──────────────────────────────────────────────────────────────────

async def test_salvar_grava_o_valor_novo_no_cache(db):
    """Sem isto a troca demora até cinco minutos para valer, e o admin conclui
    que o botão não funcionou — e clica de novo."""
    redis = RedisFalso()
    await svc.modelo_em_uso(db=db, redis=redis)          # popula
    assert redis.dados[svc._CACHE] == ASSISTENTE_MODELO

    await svc.definir_modelo(db, "outro/modelo", por="jose", redis=redis)

    # ESCREVE, não apaga — ver o teste da corrida logo abaixo.
    assert redis.dados[svc._CACHE] == "outro/modelo"
    assert await svc.modelo_em_uso(db=db, redis=redis) == "outro/modelo"


async def test_leitor_atrasado_nao_repinta_o_modelo_VELHO_por_cima(db):
    """A corrida que a revisão adversária achou, encenada passo a passo.

    Um leitor dá miss no cache e vai ao banco. ENQUANTO ele lê, o admin salva
    outro modelo. Se o leitor terminasse com um SET cego, ele repintaria o
    valor velho por cima do novo e o fixaria pelos cinco minutos do TTL: a
    troca «não pegaria», e quem salvou concluiria que o botão está quebrado.
    """
    redis = RedisFalso()

    # O leitor já leu o banco (modelo velho) e só falta escrever no cache.
    # Entre uma coisa e outra, a troca acontece:
    await svc.definir_modelo(db, "novo/modelo", por="jose", redis=redis)

    # Agora o leitor atrasado tenta gravar o que leu. `nx` o faz desistir.
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
    """O padrão de um ERRO de banco não vai para o cache.

    Gravá-lo prenderia a instalação no modelo do ambiente por cinco minutos
    DEPOIS de o banco voltar: a escolha do admin sumiria sem nada na tela
    explicando. É a regra que outra cópia do esqueleto «SystemConfig + cache»
    já seguia — e que esta não levou.
    """
    await svc.definir_modelo(db, "outro/modelo", por="jose")
    redis = RedisFalso()

    class SessaoQuebrada:
        async def execute(self, *a, **kw):
            raise RuntimeError("banco fora do ar")

    assert await svc.modelo_em_uso(db=SessaoQuebrada(), redis=redis) == ASSISTENTE_MODELO
    assert svc._CACHE not in redis.dados

    # Voltando o banco, a primeira leitura já vê a escolha do admin.
    assert await svc.modelo_em_uso(db=db, redis=redis) == "outro/modelo"


async def test_banco_fora_do_ar_cai_no_padrao_em_vez_de_levantar():
    """O assistente inteiro fora do ar por causa de uma configuração seria uma
    troca ruim: o padrão do ambiente é sempre melhor que nada."""
    class Explode:
        def __call__(self): raise RuntimeError("banco fora do ar")

    with patch("app.mcp.infra.sessao", Explode()):
        assert await svc.modelo_em_uso() == ASSISTENTE_MODELO


# ── A validação ──────────────────────────────────────────────────────────────

# Sem barra é válido: é o nome num servidor local (`llama3.1`, `qwen3:14b`).
@pytest.mark.parametrize("ruim", [
    "", "   ", "fornecedor//modelo", "fornecedor/", "/modelo",
    "com espaço/no meio", "https://openrouter.ai/api/v1/x", "a/" + "x" * 200,
])
async def test_id_invalido_e_recusado_ao_salvar(db, ruim):
    """Recusar aqui é recusar uma vez; deixar passar é falhar na próxima
    conversa de CADA usuário, sem a tela dizer por quê."""
    with pytest.raises(ValueError):
        await svc.definir_modelo(db, ruim)
    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO


async def test_linha_corrompida_no_banco_nao_derruba_a_leitura(db):
    """Alguém editando `system_config` à mão, uma migração malfeita: a leitura
    ignora o que não tem forma de id e volta ao padrão."""
    from app.core.system_config import set_config

    await set_config(db, svc.CHAVE, {"modelo": "isto não é um id"})
    assert await svc.modelo_em_uso(db=db) == ASSISTENTE_MODELO
    assert (await svc.situacao(db=db))["origem"] == "ambiente"
