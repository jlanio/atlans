# tests/unit/test_uso_service.py
"""O registro de quanto cada volta do assistente consumiu.

Esta tabela é a base das decisões de dinheiro — quanto custa cada pessoa que usa
o assistente, se o que se cobra por ele se paga, e o que a troca de modelo faria
com a conta.
Por isso o que se prende aqui é, em ordem de quanto custa errar:

1. **O modelo é gravado**, não deduzido do que está configurado agora. Sem essa
   coluna, comparar "antes e depois" da primeira troca de modelo já é
   impossível — e a troca é justamente a decisão que a tabela existe para
   informar.
2. **Falhar ao registrar não derruba a conversa.** Ela já aconteceu e a
   plataforma já pagou por ela; perder a anotação é o lado certo de errar.
3. **Volta sem token não vira linha.** Uma linha de zeros puxaria a mediana
   para baixo, e é a mediana que decide o preço.
4. **O custo não passa por float.** `Decimal(float)` arrasta o erro binário
   para dentro do decimal, que é o que a coluna NUMERIC existe para não ter.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.uso_do_assistente import UsoDoAssistente
from app.services import uso_service

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def sessoes():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[UsoDoAssistente.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    with patch("app.mcp.infra.sessao", fabrica):
        yield fabrica
    await engine.dispose()


async def _linhas(fabrica):
    async with fabrica() as s:
        return (await s.execute(select(UsoDoAssistente))).scalars().all()


async def test_grava_a_volta_com_o_modelo_que_a_produziu(sessoes):
    await uso_service.registrar_volta(
        user_id="usr-1", modelo="anthropic/claude-opus-5", superficie="home",
        entrada=1010, saida=220, cache_leitura=5000, raciocinio=180, custo_usd=0.0412,
    )

    linha, = await _linhas(sessoes)
    assert linha.modelo == "anthropic/claude-opus-5"
    assert (linha.entrada, linha.saida) == (1010, 220)
    assert (linha.cache_leitura, linha.raciocinio) == (5000, 180)
    assert linha.superficie == "home"
    assert Decimal(str(linha.custo_usd)) == Decimal("0.0412")


async def test_volta_sem_token_nao_vira_linha(sessoes):
    """Acontece quando o provedor responde sem consumir nada (recusa imediata).
    Uma linha de zeros distorceria a mediana — e é a mediana que decide o preço."""
    await uso_service.registrar_volta(
        user_id="usr-1", modelo="m", superficie="home", entrada=0, saida=0,
    )
    assert await _linhas(sessoes) == []


@pytest.mark.parametrize("faltando", [
    {"user_id": ""},
    {"modelo": ""},
])
async def test_sem_dono_ou_sem_modelo_nao_grava(sessoes, faltando):
    """Uma linha sem uma das duas não responde pergunta nenhuma — não dá para
    dizer de quem foi o gasto nem com que modelo ele foi feito."""
    campos = dict(user_id="usr-1", modelo="m", superficie="home", entrada=10, saida=5)
    campos.update(faltando)
    await uso_service.registrar_volta(**campos)
    assert await _linhas(sessoes) == []


async def test_falha_de_banco_NAO_derruba_a_conversa():
    """A conversa já aconteceu e já foi paga. Levantar aqui jogaria fora o
    trabalho por causa de uma anotação — o mesmo raciocínio da cobrança de cota."""
    class Explode:
        def __call__(self):
            raise RuntimeError("banco fora do ar")

    with patch("app.mcp.infra.sessao", Explode()):
        await uso_service.registrar_volta(
            user_id="usr-1", modelo="m", superficie="home", entrada=10, saida=5,
        )
    # Chegar aqui já é o teste: nada foi levantado.


async def test_o_custo_nao_passa_pelo_erro_binario_do_float(sessoes):
    """`Decimal(0.1)` é 0.1000000000000000055511151231257827. Somado sobre
    milhares de linhas, esse resto aparece no total — e o total é a conta."""
    await uso_service.registrar_volta(
        user_id="usr-1", modelo="m", superficie="home", entrada=1, saida=1, custo_usd=0.1,
    )
    linha, = await _linhas(sessoes)
    assert Decimal(str(linha.custo_usd)) == Decimal("0.1")
