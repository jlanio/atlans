# app/services/observability/agregados.py
# Lógica de negócio e consultas de observabilidade extraídas do router.
# Contrato com a web: docs/specs/historico-metricas.md (§3).

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowRun


# Criterio de execucao presa (spec §3.1): mais que
# 3x a mediana do workflow, nunca menos que 15 min; sem mediana, 1 h. O piso
# existe porque um workflow de 10 s "preso" ha 40 s ainda pode ser so a fila.
_PRESA_MULTIPLO_P50 = 3
_PRESA_MINIMO_SEGUNDOS = 900
_PRESA_SEM_P50_SEGUNDOS = 3600
# Quantas execucoes ativas antigas o calculo de "presas" olha. Como nenhuma
# execucao pode estar presa antes do piso de 900 s, a consulta ja corta por
# `start_time <= now - 900 s`; o teto e so uma trava contra uma fila
# patologica de milhares de pendentes — nesse caso `stuck_count` satura.
_PRESA_TETO_CANDIDATAS = 500

# Status que contam como "em andamento" no instante da consulta e no balde
# `running` do grafico por dia (spec §3.2).
_STATUS_ATIVOS = ("running", "pending")


from app.services.observability.escopo import _como_utc, _iso
from app.services.observability.estatisticas import _p50_por_workflow, _resumir_erro, _ultima_execucao_por_workflow
from app.services.observability.frota import _confirmacoes_atrasadas, _executor_id_do_host, _executores_do_escopo, _nomes_de_executores, _presenca
from app.services.observability.runs import _resolve_workflow_meta

# ── Helpers que dependem do servico (abaixo para leitura de cima para baixo) ─

def _parse_iso(texto: str) -> datetime:
    """`datetime.fromisoformat` so aceita o sufixo `Z` a partir do Python 3.11,
    e a web manda `toISOString()` (`…T22:05:13.123Z`). Escrito quando a API
    rodava em 3.10; no 3.12 a troca e inofensiva."""
    return datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))


def _balde_do_status(status: Optional[str]) -> str:
    if status in ("success", "failed", "cancelled"):
        return status
    if status in _STATUS_ATIVOS:
        return "running"
    return "other"


async def _top_falhas(db: AsyncSession, run_f: list, since: datetime) -> list[dict]:
    """Top 5 workflows por falhas na janela, com taxa (falhas ÷ total DO
    WORKFLOW na janela) e o ultimo erro. Tres consultas fixas: a agregacao,
    a ultima falha de cada um (funcao de janela) e os nomes."""
    falhas = func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed")
    result = await db.execute(
        select(
            WorkflowRun.workflow_hash,
            func.count(WorkflowRun.id).label("total_runs"),
            falhas.label("failure_count"),
        )
        .where(WorkflowRun.start_time >= since, *run_f)
        .group_by(WorkflowRun.workflow_hash)
        .having(falhas > 0)
        .order_by(falhas.desc(), func.count(WorkflowRun.id).desc())
        .limit(5)
    )
    linhas = result.all()
    if not linhas:
        return []

    hashes = [linha.workflow_hash for linha in linhas]
    ultimas = await _ultima_execucao_por_workflow(
        db, [WorkflowRun.status == "failed", WorkflowRun.start_time >= since, *run_f], hashes,
    )
    meta = await _resolve_workflow_meta(db, hashes)

    saida = []
    for linha in linhas:
        total = linha.total_runs or 0
        falhou = linha.failure_count or 0
        ultima = ultimas.get(linha.workflow_hash)
        saida.append({
            "workflow_hash":  linha.workflow_hash,
            "workflow_name":  (meta.get(linha.workflow_hash) or {}).get("workflow_name"),
            "failure_count":  falhou,
            "total_runs":     total,
            "failure_rate":   round(falhou / total, 4) if total else 0.0,
            "last_error":     _resumir_erro(ultima.error_message) if ultima else None,
            "last_error_category": ultima.error_category if ultima else None,
            "last_failed_at": _iso(ultima.start_time) if ultima else None,
        })
    return saida


async def _execucoes_presas(db: AsyncSession, run_f: list, now: datetime) -> tuple[int, list[dict]]:
    """Execucoes ativas ha mais tempo do que o workflow costuma levar.

    A consulta so traz candidatas que ja passaram do piso (900 s) — nada
    abaixo dele pode estar preso — e o limiar de cada uma vem da mediana do
    seu workflow em 90 dias. Devolve `(quantas, as 5 mais antigas)`.
    """
    limite = now - timedelta(seconds=_PRESA_MINIMO_SEGUNDOS)
    result = await db.execute(
        select(
            WorkflowRun.task_id, WorkflowRun.id, WorkflowRun.workflow_hash,
            WorkflowRun.host, WorkflowRun.start_time,
        )
        .where(WorkflowRun.status.in_(_STATUS_ATIVOS), WorkflowRun.start_time <= limite, *run_f)
        .order_by(WorkflowRun.start_time.asc())
        .limit(_PRESA_TETO_CANDIDATAS)
    )
    candidatas = result.all()
    if not candidatas:
        return 0, []

    tipicos = await _p50_por_workflow(db, [c.workflow_hash for c in candidatas], now)
    presas = []
    for c in candidatas:
        tipico = tipicos.get(c.workflow_hash)
        if tipico:
            limiar = max(_PRESA_MULTIPLO_P50 * tipico, _PRESA_MINIMO_SEGUNDOS)
        else:
            limiar = _PRESA_SEM_P50_SEGUNDOS
        decorrido = (now - _como_utc(c.start_time)).total_seconds()
        if decorrido > limiar:
            presas.append((c, decorrido, tipico))

    top = presas[:5]
    if not top:
        return 0, []
    meta = await _resolve_workflow_meta(db, [c.workflow_hash for c, _, _ in top])
    nomes = await _nomes_de_executores(
        db, [_executor_id_do_host(c.host) for c, _, _ in top if _executor_id_do_host(c.host)]
    )
    return len(presas), [
        {
            "run_id":          c.task_id or str(c.id),
            "workflow_hash":   c.workflow_hash,
            "workflow_name":   (meta.get(c.workflow_hash) or {}).get("workflow_name"),
            "agent_host":      c.host,
            "executor_name":   nomes.get(_executor_id_do_host(c.host)) if _executor_id_do_host(c.host) else None,
            "started_at":      _iso(c.start_time),
            "elapsed_seconds": int(decorrido),
            "typical_seconds": tipico,
        }
        for c, decorrido, tipico in top
    ]


async def _bloco_agora(
    db: AsyncSession, user, run_f: list, now: datetime, *, como_admin: bool = False,
) -> dict:
    """O bloco `now` da spec §3.1: o instante da consulta, SEM janela. O que
    esta em andamento nao depende do periodo escolhido no cabecalho.

    `como_admin` decide a frota (toda a ativa × a acessivel) e se os ACKs
    atrasados sao contados — nao e deduzido do `user` (ver `e_admin_global`)."""
    ativos = (await db.execute(
        select(
            func.count(WorkflowRun.id).filter(WorkflowRun.status == "running").label("running"),
            func.count(WorkflowRun.id).filter(WorkflowRun.status == "pending").label("pending"),
        ).where(WorkflowRun.status.in_(_STATUS_ATIVOS), *run_f)
    )).one()

    stuck_count, stuck = await _execucoes_presas(db, run_f, now)

    frota = await _executores_do_escopo(db, user, como_admin=como_admin)
    online, capacidade = await _presenca([e["id_hash"] for e in frota])
    # Fila somada so de quem publica capacidade: `null` distingue "ninguem
    # publica" de "fila vazia", que a tela mostra de forma diferente.
    filas = [
        cap["queued"] for eid, cap in capacidade.items()
        if online.get(eid) and cap is not None and cap.get("queued") is not None
    ]

    return {
        "running":     ativos.running or 0,
        "pending":     ativos.pending or 0,
        "stuck_count": stuck_count,
        "stuck":       stuck,
        "executors":   {"online": sum(1 for v in online.values() if v), "total": len(frota)},
        "queued_on_executors": int(sum(filas)) if filas else None,
        "overdue_acks": (await _confirmacoes_atrasadas()) if como_admin else None,
    }
