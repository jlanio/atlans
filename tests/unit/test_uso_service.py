# tests/unit/test_uso_service.py
"""The record of how much each assistant turn consumed.

This table is the basis for money decisions — how much each person who uses the
assistant costs, whether what is charged for it pays for itself, and what
switching models would do to the bill.
That is why what is locked down here is, in order of how costly it is to get wrong:

1. **The model is recorded**, not inferred from what is configured now. Without
   that column, comparing "before and after" the first model switch is already
   impossible — and the switch is precisely the decision the table exists to
   inform.
2. **Failing to record does not bring down the conversation.** It already
   happened and the platform already paid for it; losing the note is the right
   side to err on.
3. **A turn with no tokens does not become a row.** A row of zeros would pull
   the median down, and it is the median that sets the price.
4. **The cost never goes through a float.** `Decimal(float)` drags the binary
   error into the decimal, which is what the NUMERIC column exists to avoid.
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
    """Happens when the provider responds without consuming anything (immediate
    refusal). A row of zeros would skew the median — and it is the median that
    sets the price."""
    await uso_service.registrar_volta(
        user_id="usr-1", modelo="m", superficie="home", entrada=0, saida=0,
    )
    assert await _linhas(sessoes) == []


@pytest.mark.parametrize("faltando", [
    {"user_id": ""},
    {"modelo": ""},
])
async def test_sem_dono_ou_sem_modelo_nao_grava(sessoes, faltando):
    """A row missing either of the two answers no question at all — you cannot
    tell whose spending it was nor which model it was done with."""
    campos = dict(user_id="usr-1", modelo="m", superficie="home", entrada=10, saida=5)
    campos.update(faltando)
    await uso_service.registrar_volta(**campos)
    assert await _linhas(sessoes) == []


async def test_falha_de_banco_NAO_derruba_a_conversa():
    """The conversation already happened and has already been paid for. Raising
    here would throw the work away because of a note — the same reasoning as the
    quota charge."""
    class Explode:
        def __call__(self):
            raise RuntimeError("banco fora do ar")

    with patch("app.mcp.infra.sessao", Explode()):
        await uso_service.registrar_volta(
            user_id="usr-1", modelo="m", superficie="home", entrada=10, saida=5,
        )
    # Getting here is the test: nothing was raised.


async def test_o_custo_nao_passa_pelo_erro_binario_do_float(sessoes):
    """`Decimal(0.1)` is 0.1000000000000000055511151231257827. Summed over
    thousands of rows, that remainder shows up in the total — and the total is
    the bill."""
    await uso_service.registrar_volta(
        user_id="usr-1", modelo="m", superficie="home", entrada=1, saida=1, custo_usd=0.1,
    )
    linha, = await _linhas(sessoes)
    assert Decimal(str(linha.custo_usd)) == Decimal("0.1")
