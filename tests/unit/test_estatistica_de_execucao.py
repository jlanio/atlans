"""Taxa de sucesso e percentil: uma conta só para todas as telas.

A taxa de sucesso da spec (docs/specs/metrics-history.md §3) é concluídas ÷
(concluídas + falhas): em andamento e canceladas ficam fora do denominador. O
Histórico, a visão por workflow e a por executor já usavam essa conta; o
detalhe do workflow a reescrevia como `(total - failed) / total`, contando
cada execução em andamento ou cancelada como sucesso — o mesmo fluxo aparecia
com duas taxas diferentes conforme a tela.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.utils.estatistica import percentil_linear, taxa_de_sucesso
from app.services.observability_service import ObservabilityService


def _resultado(*, linhas=None, escalar=None):
    r = MagicMock()
    r.all.return_value = list(linhas or [])
    r.scalars.return_value.all.return_value = list(linhas or [])
    r.scalar_one_or_none.return_value = escalar
    r.__iter__.return_value = iter([])
    return r


def _db(*respostas):
    """Devolve `respostas` na ordem e, esgotadas, resultados vazios."""
    fila = list(respostas)

    async def _execute(_stmt):
        return fila.pop(0) if fila else _resultado()

    db = MagicMock(execute=AsyncMock(side_effect=_execute))
    db.bind.dialect.name = "sqlite"
    return db


def _run(status: str, n: int):
    return SimpleNamespace(
        task_id=f"run-{n}", id=n, status=status,
        start_time=datetime(2026, 9, 6, 12, n, tzinfo=timezone.utc), end_time=None,
        duration_seconds=10.0 if status == "success" else None, error_message=None,
        host=None, dispatch_tier=None, workflow_hash="wf-1", workspace_id="ws-1",
        trigger_source="manual", triggered_by=None, error_category=None,
        schedule_id=None, retry_count=0,
    )


@pytest.mark.asyncio
async def test_detalhe_do_workflow_usa_a_taxa_das_outras_telas():
    runs = [_run(s, i) for i, s in enumerate(["success", "success", "failed", "running", "cancelled"])]
    db = _db(_resultado(escalar="Bacia"), _resultado(linhas=runs))

    m = await ObservabilityService.get_workflow_metrics(db, "wf-1", MagicMock(role="user"), ["ws-1"])

    assert (m["total_runs"], m["failed_runs"]) == (5, 1)
    # 2 / (2 + 1). A conta antiga dava (5 - 1) / 5 = 0.8: a execução em
    # andamento e a cancelada entravam como sucesso.
    assert m["success_rate"] == 0.6667


@pytest.mark.asyncio
async def test_detalhe_so_com_execucoes_em_andamento_nao_mostra_100_por_cento():
    runs = [_run("running", 0), _run("pending", 1)]
    db = _db(_resultado(escalar="Bacia"), _resultado(linhas=runs))

    m = await ObservabilityService.get_workflow_metrics(db, "wf-1", MagicMock(role="user"), ["ws-1"])

    assert m["success_rate"] == 0.0     # sem denominador, como nas outras telas (antes: 1.0)


# ── As peças únicas ──────────────────────────────────────────────────────────

def test_taxa_de_sucesso_so_olha_concluidas_e_falhas():
    assert taxa_de_sucesso(8, 2) == 0.8
    assert taxa_de_sucesso(2, 1) == 0.6667          # 4 casas, como a tela recebe
    assert taxa_de_sucesso(0, 0) == 0.0             # sem denominador não estoura


def test_percentil_linear_sem_valores_e_ausencia_e_nao_zero():
    """O Histórico mostra "—" sem execução concluída; quem quer zero (o custo
    por plano) decide isso na própria tela."""
    assert percentil_linear([], 0.5) is None
    assert percentil_linear([1, 2, 3, 4, 5], 0.95) == 4.8
