# tests/unit/test_usage_daily_corrida.py
"""usage_daily: incremento atomico e recuperacao da corrida do INSERT.

O agregado diario e escrito por DOIS caminhos com sessoes SEPARADAS para o mesmo
(date, workspace_id): o consumer (fila run_results) e `account_terminal_run`
(falha de despacho, cancel antes do executor, watchdog de executor desconectado).
Antes, `_upsert_usage_daily` fazia SELECT -> UPDATE-em-Python OU INSERT -> commit:
duas sessoes liam o mesmo total e ambas gravavam o mesmo +1 (lost update), e no
1o run do dia os dois INSERTs colidiam em uq_usage_daily. Agora o upsert e
atomico: UPDATE `coluna = coluna + delta` no SQL e, quando a linha ainda nao
existe, um INSERT sob savepoint que, ao perder a corrida, re-faz o UPDATE.

Por que estes testes NAO usam `asyncio.gather`: o SQLite em memoria e StaticPool
(uma unica conexao), entao duas corrotinas "concorrentes" sao serializadas — a
intercalacao UPDATE/UPDATE/INSERT/INSERT nao acontece. Em lugar disso a linha
vencedora e plantada de verdade e o 1o UPDATE do perdedor e forcado a ver 0
linhas, para o INSERT dele bater na constraint REAL (nao um erro fabricado) — o
mesmo padrao de `test_versao_corrida.py`.
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
    """Le por Core (nao pelo identity map do ORM, que ficaria com o valor velho da
    linha plantada depois do UPDATE atomico)."""
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
    """A linha do dia ja existe: o incremento e `coluna = coluna + delta` no SQL
    (nao um read-modify-write em Python que perderia updates concorrentes)."""
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
    """A linha vencedora e plantada; o 1o UPDATE do perdedor e forcado a ver 0
    linhas (leitura velha), entao o INSERT dele bate na uq_usage_daily REAL. O
    savepoint isola a violacao e o run re-faz o UPDATE atomico sobre a vencedora —
    resultado: UMA linha, com a soma das duas contribuicoes, e nenhum erro sobe."""
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
            # So o 1o UPDATE (o do perdedor) enxerga 0 linhas — forca o caminho do
            # INSERT, que bate na constraint real da linha ja plantada.
            class _R:
                rowcount = 0
            return _R()
        return await real_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(db, "execute", _execute_forjado)
    await rrc._upsert_usage_daily(db, _run(status="failed"), {}, True)  # nao levanta
    monkeypatch.undo()

    linhas = await _linhas(db)
    assert len(linhas) == 1                    # o INSERT perdedor NAO criou 2a linha
    assert linhas[0]["total_runs"] == 2        # 1 (vencedora) + 1 (perdedor via retry)
    assert linhas[0]["failed_runs"] == 2


@pytest.mark.asyncio
async def test_nan_nas_metricas_nao_contamina_o_agregado(db):
    """`NaN or 0` é NaN, e NaN + x = NaN: um único run com métrica NaN
    envenenaria o total do workspace no dia para sempre. Um None viraria NULL
    na soma do SQL. As duas coisas entram como 0."""
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
    assert linha["total_duration_ms"] == 1000     # só o segundo run (1 s)
    for coluna in ("total_cpu_seconds", "total_mem_mb_seconds", "total_input_bytes",
                   "total_output_bytes", "total_features"):
        assert linha[coluna] == 0, coluna
