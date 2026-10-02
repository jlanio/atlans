# tests/unit/test_observability_janela_metricas.py
"""Invariantes da janela temporal das metricas de dashboard.

Duas regressoes que a query unica de `get_metrics` introduziu e que nenhum teste
cobria:

1. Os recortes de 7d/14d viraram `count(*) FILTER (...)` DENTRO da query, mas o
   WHERE passou a ser a janela pedida (`?days=`). Com `days < 14` o predicado de
   `prev_7d` (`>= now-14d AND < now-7d`) intersecta o WHERE (`>= now-7d`) num
   conjunto VAZIO: `runs_prev_7d` zerava e a seta de tendencia do dashboard
   sumia sem erro nenhum.

2. As janelas viraram datetime NAIVE. `WorkflowRun.start_time` e timestamptz;
   um bind naive e interpretado pelo codec do asyncpg no fuso LOCAL DO PROCESSO
   (`TZ=America/Cuiaba` no docker-compose), deslocando o limiar em 4h — o card
   "Execucoes (24h)" contava 20h.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.observability_service import ObservabilityService


def _user(role="admin"):
    """Admin de proposito (as chamadas passam `como_admin=True`): `_run_filter`
    devolve [] e o WHERE fica com uma condicao so, que e exatamente a janela
    que estes testes inspecionam."""
    u = MagicMock()
    u.role = role
    return u


class _LinhaVazia:
    """Linha de agregacao "sem dados": qualquer coluna le como None. Serve as
    consultas que estes testes NAO inspecionam (periodo anterior, percentis,
    top de falhas, bloco `now`), que so precisam de um resultado vazio."""

    def __getattr__(self, _nome):
        return None


def _db():
    """Dublê de sessão. A 1a consulta é a contagem de workflows e a 2a é a
    agregação principal sobre `workflow_runs` — é essa que os testes
    inspecionam. Tudo o que vem depois (período anterior, percentis, top de
    falhas, bloco `now`) recebe um resultado vazio genérico."""
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
    """O datetime do `WHERE start_time >= :param` — sem filtro de workspace, o
    WHERE tem essa condicao e mais nenhuma."""
    return stmt.whereclause.right.value


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7, 13])
async def test_where_cobre_14_dias_quando_a_janela_pedida_e_menor(days):
    """Cenario: `GET /observability/metrics?days=7` com centenas de execucoes na
    semana anterior. Se o WHERE for de 7 dias, `prev_7d` nao tem como enxergar
    nada e a comparacao semana-a-semana zera."""
    db = _db()
    antes = datetime.now(timezone.utc)

    await ObservabilityService.get_metrics(db, _user(), [], days=days, force=True, como_admin=True)

    limiar = _limiar_do_where(_query_dos_runs(db))
    assert antes - limiar >= timedelta(days=14) - timedelta(seconds=5)


@pytest.mark.asyncio
async def test_where_respeita_a_janela_pedida_quando_ela_e_maior_que_14_dias():
    """O alargamento e um piso, nao um teto: `days=90` continua varrendo 90
    dias, senao `total_runs` mentiria para baixo."""
    db = _db()
    antes = datetime.now(timezone.utc)

    await ObservabilityService.get_metrics(db, _user(), [], days=90, force=True, como_admin=True)

    limiar = _limiar_do_where(_query_dos_runs(db))
    assert timedelta(days=89) < antes - limiar < timedelta(days=91)


@pytest.mark.asyncio
async def test_agregados_da_janela_ganham_filter_para_nao_herdar_os_14_dias():
    """Com o WHERE alargado, `total`/`success`/`failed`/`running`/`avg` PRECISAM
    do seu proprio FILTER: sem ele, `?days=7` devolveria os numeros de 14 dias
    sob o rotulo de 7."""
    db = _db()

    await ObservabilityService.get_metrics(db, _user(), [], days=7, force=True, como_admin=True)

    sql = str(_query_dos_runs(db))
    cabecalho = sql.split("FROM", 1)[0]
    for rotulo in ("AS total", "AS success", "AS failed", "AS running", "AS avg_duration"):
        coluna = cabecalho.split(rotulo)[0].rsplit(",", 1)[-1]
        assert "FILTER" in coluna, f"{rotulo} sem recorte da janela pedida"


@pytest.mark.asyncio
async def test_todas_as_janelas_sao_timezone_aware():
    """Bind naive em coluna timestamptz e lido no fuso do processo: com
    TZ=America/Cuiaba a janela de 24h vira 20h."""
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
    """Contrato com a tela: ela manda `days` e rotula o card com `period_days`."""
    db = _db()

    metricas = await ObservabilityService.get_metrics(db, _user(), [], days=30, force=True, como_admin=True)

    assert metricas["period_days"] == 30
