# tests/unit/test_usage_daily_corrida.py
"""usage_daily: atomic increment and recovery from the INSERT race.

The daily aggregate is written by TWO paths with SEPARATE sessions for the same
(date, workspace_id): the consumer (run_results queue) and `account_terminal_run`
(dispatch failure, cancel before the executor, disconnected-executor watchdog).
Before, `_upsert_usage_daily` did SELECT -> UPDATE-in-Python OR INSERT -> commit:
two sessions read the same total and both wrote the same +1 (lost update), and on
the 1st run of the day the two INSERTs collided on uq_usage_daily. Now the upsert
is atomic: UPDATE `coluna = coluna + delta` in SQL and, when the row does not
exist yet, an INSERT under a savepoint that, on losing the race, redoes the UPDATE.

Why these tests do NOT use `asyncio.gather`: the in-memory SQLite is a StaticPool
(a single connection), so two "concurrent" coroutines are serialized — the
UPDATE/UPDATE/INSERT/INSERT interleaving does not happen. Instead, the winning
row is actually planted and the loser's 1st UPDATE is forced to see 0 rows, so
that its INSERT hits the REAL constraint (not a fabricated error) — the same
pattern as `test_versao_corrida.py`.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import run_result_consumer as rrc
from app.core.utils.datetime_utils import utc_now_naive
from app.models.models import WorkflowRun
from app.models.run_metrics import UsageDaily


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(UsageDaily.metadata.create_all, tables=[UsageDaily.__table__])
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


def _run(status="failed", ws="ws-1") -> WorkflowRun:
    run = WorkflowRun(
        task_id="t-1", workflow_hash="wf-1", workspace_id=ws, status=status, node_stats={},
    )
    run.duration_seconds = 1.0
    return run


async def _linhas(db, ws="ws-1") -> list[dict]:
    """Reads via Core (not via the ORM's identity map, which would keep the stale
    value of the planted row after the atomic UPDATE)."""
    hoje = utc_now_naive().date()
    res = await db.execute(
        sa_select(UsageDaily.__table__).where(
            UsageDaily.date == hoje,
            UsageDaily.workspace_id == ws,
        )
    )
    return list(res.mappings().all())


@pytest.mark.asyncio
async def test_cria_linha_quando_nao_existe(db):
    await rrc._upsert_usage_daily(db, _run(status="failed"), {}, True)

    linhas = await _linhas(db)
    assert len(linhas) == 1
    assert linhas[0]["total_runs"] == 1
    assert linhas[0]["failed_runs"] == 1
    assert linhas[0]["successful_runs"] == 0


@pytest.mark.asyncio
async def test_incrementa_linha_existente_no_sql(db):
    """The day's row already exists: the increment is `coluna = coluna + delta` in
    SQL (not a read-modify-write in Python that would lose concurrent updates)."""
    hoje = utc_now_naive().date()
    db.add(UsageDaily(
        date=hoje, workspace_id="ws-1",
        total_runs=3, successful_runs=3, failed_runs=0,
        total_cpu_seconds=0.0, total_mem_mb_seconds=0.0, total_duration_ms=0.0,
        total_input_bytes=0, total_output_bytes=0, total_features=0, total_nodes_executed=0,
    ))
    await db.commit()

    await rrc._upsert_usage_daily(db, _run(status="failed"), {}, True)

    linhas = await _linhas(db)
    assert len(linhas) == 1
    assert linhas[0]["total_runs"] == 4       # 3 + 1
    assert linhas[0]["failed_runs"] == 1      # 0 + 1
    assert linhas[0]["successful_runs"] == 3  # inalterado


@pytest.mark.asyncio
async def test_perdedor_da_corrida_do_insert_reincrementa(db, monkeypatch):
    """The winning row is planted; the loser's 1st UPDATE is forced to see 0 rows
    (stale read), so its INSERT hits the REAL uq_usage_daily. The savepoint
    isolates the violation and the run redoes the atomic UPDATE on the winner —
    result: ONE row, with the sum of both contributions, and no error surfaces."""
    hoje = utc_now_naive().date()
    db.add(UsageDaily(
        date=hoje, workspace_id="ws-1",
        total_runs=1, successful_runs=0, failed_runs=1,
        total_cpu_seconds=0.0, total_mem_mb_seconds=0.0, total_duration_ms=0.0,
        total_input_bytes=0, total_output_bytes=0, total_features=0, total_nodes_executed=0,
    ))
    await db.commit()

    real_execute = db.execute
    chamadas = {"n": 0}

    async def _execute_forjado(stmt, *args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            # Only the 1st UPDATE (the loser's) sees 0 rows — it forces the INSERT
            # path, which hits the real constraint of the already-planted row.
            class _R:
                rowcount = 0
            return _R()
        return await real_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(db, "execute", _execute_forjado)
    await rrc._upsert_usage_daily(db, _run(status="failed"), {}, True)  # does not raise
    monkeypatch.undo()

    linhas = await _linhas(db)
    assert len(linhas) == 1                    # o INSERT perdedor NAO criou 2a linha
    assert linhas[0]["total_runs"] == 2        # 1 (vencedora) + 1 (perdedor via retry)
    assert linhas[0]["failed_runs"] == 2


@pytest.mark.asyncio
async def test_nan_nas_metricas_nao_contamina_o_agregado(db):
    """`NaN or 0` is NaN, and NaN + x = NaN: a single run with a NaN metric would
    poison the workspace's total for the day forever. A None would become NULL
    in the SQL sum. Both go in as 0."""
    nan = float("nan")
    stats = {"__metrics__": {"run": {
        "duration_ms": nan, "cpu_avg_pct": nan, "mem_avg_mb": float("inf"),
        "input_bytes": None, "output_bytes": "10", "total_features": nan, "nodes_executed": 3,
    }}}
    run = _run(status="success")
    run.duration_seconds = nan

    await rrc._upsert_usage_daily(db, run, stats, True)
    await rrc._upsert_usage_daily(db, _run(status="success"), {}, True)

    [linha] = await _linhas(db)
    assert linha["total_runs"] == 2
    assert linha["total_nodes_executed"] == 3
    assert linha["total_duration_ms"] == 1000     # only the second run (1 s)
    for coluna in ("total_cpu_seconds", "total_mem_mb_seconds", "total_input_bytes",
                   "total_output_bytes", "total_features"):
        assert linha[coluna] == 0, coluna
