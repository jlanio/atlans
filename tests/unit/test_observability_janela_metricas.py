# tests/unit/test_observability_janela_metricas.py
"""Invariants of the time window of the dashboard metrics.

Two regressions that the single query of `get_metrics` introduced and that no
test covered:

1. The 7d/14d slices became `count(*) FILTER (...)` INSIDE the query, but the
   WHERE became the requested window (`?days=`). With `days < 14` the predicate
   of `prev_7d` (`>= now-14d AND < now-7d`) intersects the WHERE (`>= now-7d`) in
   an EMPTY set: `runs_prev_7d` went to zero and the dashboard's trend arrow
   disappeared without any error.

2. The windows became NAIVE datetimes. `WorkflowRun.start_time` is timestamptz;
   a naive bind is interpreted by the asyncpg codec in the PROCESS'S LOCAL time
   zone (`TZ=America/Cuiaba` in docker-compose), shifting the threshold by 4h —
   the "Execucoes (24h)" card counted 20h.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.observability_service import ObservabilityService


def _user(role="admin"):
    """Admin on purpose (the calls pass `como_admin=True`): `_run_filter`
    returns [] and the WHERE is left with a single condition, which is exactly
    the window these tests inspect."""
    u = MagicMock()
    u.role = role
    return u


class _LinhaVazia:
    """A "no data" aggregation row: any column reads as None. Serves the
    queries these tests do NOT inspect (previous period, percentiles,
    top failures, `now` block), which only need an empty result."""

    def __getattr__(self, _nome):
        return None


def _db():
    """Session double. The 1st query is the workflow count and the 2nd is the
    main aggregation over `workflow_runs` — that is the one the tests
    inspect. Everything after that (previous period, percentiles, top
    failures, `now` block) gets a generic empty result."""
    wf = MagicMock()
    wf.one.return_value = SimpleNamespace(total=0, ativos=0)
    runs = MagicMock()
    runs.one.return_value = _LinhaVazia()

    def _vazio():
        r = MagicMock()
        r.one.return_value = _LinhaVazia()
        r.all.return_value = []
        r.scalars.return_value.all.return_value = []
        r.scalar_one_or_none.return_value = None
        return r

    respostas = [wf, runs]

    async def _execute(stmt):
        return respostas.pop(0) if respostas else _vazio()

    return MagicMock(execute=AsyncMock(side_effect=_execute))


def _query_dos_runs(db):
    return db.execute.await_args_list[1].args[0]


def _limiar_do_where(stmt) -> datetime:
    """The datetime of `WHERE start_time >= :param` — without a workspace filter,
    the WHERE has that condition and no other."""
    return stmt.whereclause.right.value


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7, 13])
async def test_where_cobre_14_dias_quando_a_janela_pedida_e_menor(days):
    """Scenario: `GET /observability/metrics?days=7` with hundreds of runs in
    the previous week. If the WHERE spans 7 days, `prev_7d` cannot possibly see
    anything and the week-over-week comparison goes to zero."""
    db = _db()
    antes = datetime.now(timezone.utc)

    await ObservabilityService.get_metrics(db, _user(), [], days=days, force=True, como_admin=True)

    limiar = _limiar_do_where(_query_dos_runs(db))
    assert antes - limiar >= timedelta(days=14) - timedelta(seconds=5)


@pytest.mark.asyncio
async def test_where_respeita_a_janela_pedida_quando_ela_e_maior_que_14_dias():
    """The widening is a floor, not a ceiling: `days=90` still scans 90
    days, or `total_runs` would under-report."""
    db = _db()
    antes = datetime.now(timezone.utc)

    await ObservabilityService.get_metrics(db, _user(), [], days=90, force=True, como_admin=True)

    limiar = _limiar_do_where(_query_dos_runs(db))
    assert timedelta(days=89) < antes - limiar < timedelta(days=91)


@pytest.mark.asyncio
async def test_agregados_da_janela_ganham_filter_para_nao_herdar_os_14_dias():
    """With the widened WHERE, `total`/`success`/`failed`/`running`/`avg` NEED
    their own FILTER: without it, `?days=7` would return the 14-day numbers
    under the 7-day label."""
    db = _db()

    await ObservabilityService.get_metrics(db, _user(), [], days=7, force=True, como_admin=True)

    sql = str(_query_dos_runs(db))
    cabecalho = sql.split("FROM", 1)[0]
    for rotulo in ("AS total", "AS success", "AS failed", "AS running", "AS avg_duration"):
        coluna = cabecalho.split(rotulo)[0].rsplit(",", 1)[-1]
        assert "FILTER" in coluna, f"{rotulo} sem recorte da janela pedida"


@pytest.mark.asyncio
async def test_todas_as_janelas_sao_timezone_aware():
    """A naive bind on a timestamptz column is read in the process time zone: with
    TZ=America/Cuiaba the 24h window becomes 20h."""
    db = _db()

    await ObservabilityService.get_metrics(db, _user(), [], days=90, force=True, como_admin=True)

    binds = _query_dos_runs(db).compile().params.values()
    momentos = [v for v in binds if isinstance(v, datetime)]
    assert momentos, "a query perdeu os limiares de tempo"
    assert all(m.tzinfo is not None for m in momentos)


@pytest.mark.asyncio
async def test_janela_dos_executores_tambem_e_aware():
    """Mesmo bug, mesma tabela timestamptz, outro endpoint."""
    resultado = MagicMock()
    resultado.all.return_value = []
    db = MagicMock(execute=AsyncMock(return_value=resultado))

    await ObservabilityService.get_executor_metrics(db, _user(), [], days=30, force=True, como_admin=True)

    stmt = db.execute.await_args_list[0].args[0]
    momentos = [v for v in stmt.compile().params.values() if isinstance(v, datetime)]
    assert momentos and all(m.tzinfo is not None for m in momentos)


@pytest.mark.asyncio
async def test_resposta_informa_o_periodo_aplicado():
    """Contract with the screen: it sends `days` and labels the card with `period_days`."""
    db = _db()

    metricas = await ObservabilityService.get_metrics(db, _user(), [], days=30, force=True, como_admin=True)

    assert metricas["period_days"] == 30
