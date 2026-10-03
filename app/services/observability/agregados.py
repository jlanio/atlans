# app/services/observability/agregados.py
# Business logic and observability queries extracted from the router.
# Contract with the web app: docs/specs/metrics-history.md (§3).

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowRun


# Stuck-run criterion (spec §3.1): more than
# 3x the workflow's median, never less than 15 min; with no median, 1 h. The floor
# exists because a 10 s workflow "stuck" for 40 s may still just be the queue.
_STUCK_P50_MULTIPLE = 3
_STUCK_MIN_SECONDS = 900
_STUCK_NO_P50_SECONDS = 3600
# How many old active runs the "stuck" calculation looks at. Since no
# run can be stuck before the 900 s floor, the query already cuts by
# `start_time <= now - 900 s`; the ceiling is only a guard against a
# pathological queue of thousands of pending ones — in that case `stuck_count` saturates.
_STUCK_CANDIDATES_CEILING = 500

# Statuses that count as "in progress" at query time and in the
# `running` bucket of the per-day chart (spec §3.2).
_ACTIVE_STATUSES = ("running", "pending")


from app.services.observability.escopo import _as_utc, _iso
from app.services.observability.estatisticas import _p50_por_workflow, _summarize_error, _last_run_per_workflow
from app.services.observability.frota import _confirmacoes_atrasadas, _executor_id_do_host, _executores_do_escopo, _executor_names, _presenca
from app.services.observability.runs import _resolve_workflow_meta

# ── Helpers that depend on the service (below, for top-down reading) ─────────

def _parse_iso(texto: str) -> datetime:
    """`datetime.fromisoformat` only accepts the `Z` suffix from Python 3.11 on,
    and the web app sends `toISOString()` (`…T22:05:13.123Z`). Written when the API
    ran on 3.10; on 3.12 the replacement is harmless."""
    return datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))


def _status_bucket(status: Optional[str]) -> str:
    if status in ("success", "failed", "cancelled"):
        return status
    if status in _ACTIVE_STATUSES:
        return "running"
    return "other"


async def _top_failures(db: AsyncSession, run_f: list, since: datetime) -> list[dict]:
    """Top 5 workflows by failures in the window, with rate (failures ÷ total OF THE
    WORKFLOW in the window) and the last error. Three fixed queries: the aggregation,
    each one's last failure (window function) and the names."""
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
    ultimas = await _last_run_per_workflow(
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
            "last_error":     _summarize_error(ultima.error_message) if ultima else None,
            "last_error_category": ultima.error_category if ultima else None,
            "last_failed_at": _iso(ultima.start_time) if ultima else None,
        })
    return saida


async def _execucoes_presas(db: AsyncSession, run_f: list, now: datetime) -> tuple[int, list[dict]]:
    """Active runs running longer than the workflow usually takes.

    The query only brings candidates already past the floor (900 s) — nothing
    below it can be stuck — and each one's threshold comes from the median of
    its workflow over 90 days. Returns `(how many, the 5 oldest)`.
    """
    limite = now - timedelta(seconds=_STUCK_MIN_SECONDS)
    result = await db.execute(
        select(
            WorkflowRun.task_id, WorkflowRun.id, WorkflowRun.workflow_hash,
            WorkflowRun.host, WorkflowRun.start_time,
        )
        .where(WorkflowRun.status.in_(_ACTIVE_STATUSES), WorkflowRun.start_time <= limite, *run_f)
        .order_by(WorkflowRun.start_time.asc())
        .limit(_STUCK_CANDIDATES_CEILING)
    )
    candidates = result.all()
    if not candidates:
        return 0, []

    typical_by_workflow = await _p50_por_workflow(db, [c.workflow_hash for c in candidates], now)
    presas = []
    for c in candidates:
        typical = typical_by_workflow.get(c.workflow_hash)
        if typical:
            limiar = max(_STUCK_P50_MULTIPLE * typical, _STUCK_MIN_SECONDS)
        else:
            limiar = _STUCK_NO_P50_SECONDS
        decorrido = (now - _as_utc(c.start_time)).total_seconds()
        if decorrido > limiar:
            presas.append((c, decorrido, typical))

    top = presas[:5]
    if not top:
        return 0, []
    meta = await _resolve_workflow_meta(db, [c.workflow_hash for c, _, _ in top])
    nomes = await _executor_names(
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
            "typical_seconds": typical,
        }
        for c, decorrido, typical in top
    ]


async def _now_block(
    db: AsyncSession, user, run_f: list, now: datetime, *, como_admin: bool = False,
) -> dict:
    """The `now` block of spec §3.1: the moment of the query, with NO window. What
    is in progress does not depend on the period chosen in the header.

    `como_admin` decides the fleet (all active × the accessible ones) and whether late
    ACKs are counted — it is not inferred from `user` (see `e_admin_global`)."""
    ativos = (await db.execute(
        select(
            func.count(WorkflowRun.id).filter(WorkflowRun.status == "running").label("running"),
            func.count(WorkflowRun.id).filter(WorkflowRun.status == "pending").label("pending"),
        ).where(WorkflowRun.status.in_(_ACTIVE_STATUSES), *run_f)
    )).one()

    stuck_count, stuck = await _execucoes_presas(db, run_f, now)

    frota = await _executores_do_escopo(db, user, como_admin=como_admin)
    online, capacidade = await _presenca([e["id_hash"] for e in frota])
    # Queue summed only over those that publish capacity: `null` distinguishes "nobody
    # publishes" from "empty queue", which the screen shows differently.
    queues = [
        cap["queued"] for eid, cap in capacidade.items()
        if online.get(eid) and cap is not None and cap.get("queued") is not None
    ]

    return {
        "running":     ativos.running or 0,
        "pending":     ativos.pending or 0,
        "stuck_count": stuck_count,
        "stuck":       stuck,
        "executors":   {"online": sum(1 for v in online.values() if v), "total": len(frota)},
        "queued_on_executors": int(sum(queues)) if queues else None,
        "overdue_acks": (await _confirmacoes_atrasadas()) if como_admin else None,
    }
