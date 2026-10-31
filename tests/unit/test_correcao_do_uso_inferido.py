"""The server's guess (executor vanished → failure) is corrected on the day it
was COUNTED, not on the day the real result arrives (fix review)."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import run_result_consumer as rrc
from app.models.base import Base
from app.models.run_metrics import UsageDaily


@pytest.fixture
async def sessao():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[UsageDaily.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        yield s
    await engine.dispose()


async def _linhas(s):
    return {
        u.date: (u.failed_runs, u.successful_runs)
        for u in (await s.execute(select(UsageDaily))).scalars()
    }


@pytest.mark.asyncio
async def test_the_correction_lands_on_the_day_the_guess_was_counted(sessao):
    ontem, hoje = date(2026, 10, 30), date(2026, 10, 31)
    sessao.add_all([
        UsageDaily(date=ontem, workspace_id="ws", total_runs=1, failed_runs=1, successful_runs=0),
        UsageDaily(date=hoje, workspace_id="ws", total_runs=1, failed_runs=1, successful_runs=0),
    ])
    await sessao.commit()
    run = SimpleNamespace(workspace_id="ws", status="success", task_id="r1")

    # Closed by the server at 23:59 UTC yesterday; the real result arrives today.
    await rrc._correct_inferred_usage(sessao, run, datetime(2026, 10, 30, 23, 59, tzinfo=timezone.utc))

    assert await _linhas(sessao) == {ontem: (0, 1), hoje: (1, 0)}


def test_the_utc_date_of_a_moment():
    from datetime import timedelta
    assert rrc._utc_date(datetime(2026, 10, 30, 23, 30)) == date(2026, 10, 30)
    # 21:30 in UTC-3 is already the next day in UTC.
    menos3 = timezone(timedelta(hours=-3))
    assert rrc._utc_date(datetime(2026, 10, 30, 21, 30, tzinfo=menos3)) == date(2026, 10, 31)
