# app/services/observability/estatisticas.py
# Business logic and observability queries extracted from the router.
# Contract with the web app: docs/specs/metrics-history.md (§3).

from datetime import datetime, timedelta
from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select, literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowRun


# "Typical duration" is the median of COMPLETED runs with a positive duration:
# failures, scheduler zeros and orphans went into the old average, and a 40-min
# run among a hundred of 30 s became "54 s". The 90-day window is the same as the
# stuck-run criterion (spec §3.1) and the detail's `typical_seconds`.
_TYPICAL_DAYS = 90


# Maximum size of `last_error` in the summaries (spec §3.1): the full message
# stays in the run detail; here it is a table row.
_ERROR_SUMMARY_LEN = 200


from app.core.utils.estatistica import percentil_linear
from app.services.observability.escopo import _e_postgres

# ── Percentis ─────────────────────────────────────────────────────────────────

# Only completed runs with a positive duration go into the percentiles (spec
# §3.1): failure/cancellation say nothing about how long the workflow takes, and `0` is
# what the scheduler writes when it did not even get to dispatch.
_VALID_DURATION = (WorkflowRun.status == "success", WorkflowRun.duration_seconds > 0)


def _percentile_columns(ps: Sequence[float]) -> list:
    return [
        func.percentile_cont(p).within_group(WorkflowRun.duration_seconds).label(f"p{i}")
        for i, p in enumerate(ps)
    ]


def _round(valor) -> Optional[float]:
    return round(float(valor), 3) if valor is not None else None


async def _percentis(db: AsyncSession, filtros: list, ps: Sequence[float]) -> list[Optional[float]]:
    """Duration percentiles of the completed runs that pass `filtros`.

    On PostgreSQL it is a `percentile_cont(...) WITHIN GROUP` — a single response
    row. Elsewhere it projects ONLY the `duration_seconds` column of the slice and
    interpolates in Python; `filtros` always carries the window, so the volume is
    what the screen asks for, never the table.
    """
    if _e_postgres(db):
        row = (await db.execute(
            select(*_percentile_columns(ps)).where(*_VALID_DURATION, *filtros)
        )).one()
        return [_round(getattr(row, f"p{i}")) for i in range(len(ps))]

    result = await db.execute(
        select(WorkflowRun.duration_seconds).where(*_VALID_DURATION, *filtros)
    )
    valores = [float(v) for v in result.scalars().all() if v is not None]
    return [_round(percentil_linear(valores, p)) for p in ps]


async def _percentiles_by(
    db: AsyncSession, coluna, filtros: list, ps: Sequence[float],
) -> dict:
    """`_percentis` grouped by `coluna` (workflow_hash or host) —
    `{column value: [percentiles...]}`. Groups with no completed run do not
    appear: the caller treats the absence as `None`."""
    if _e_postgres(db):
        result = await db.execute(
            select(coluna.label("grupo"), *_percentile_columns(ps))
            .where(*_VALID_DURATION, *filtros)
            .group_by(coluna)
        )
        return {
            row.grupo: [_round(getattr(row, f"p{i}")) for i in range(len(ps))]
            for row in result.all()
        }

    result = await db.execute(
        select(coluna.label("grupo"), WorkflowRun.duration_seconds)
        .where(*_VALID_DURATION, *filtros)
    )
    grupos: dict = {}
    for row in result.all():
        if row.duration_seconds is not None:
            grupos.setdefault(row.grupo, []).append(float(row.duration_seconds))
    return {g: [_round(percentil_linear(v, p)) for p in ps] for g, v in grupos.items()}


async def _p50_por_workflow(
    db: AsyncSession, workflow_hashes: Iterable[str], now: datetime,
) -> dict[str, Optional[float]]:
    """Median of the last 90 days, per workflow — the spec's `typical_seconds`.
    No workspace filter on purpose: it is an aggregate number of the workflow, and
    whoever gets here already had their access to the workflow (or the run) checked."""
    hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
    if not hashes:
        return {}
    since = now - timedelta(days=_TYPICAL_DAYS)
    grupos = await _percentiles_by(
        db, WorkflowRun.workflow_hash,
        [WorkflowRun.workflow_hash.in_(hashes), WorkflowRun.start_time >= since],
        [0.5],
    )
    return {h: v[0] for h, v in grupos.items()}


async def _last_run_per_workflow(
    db: AsyncSession, filtros: list, workflow_hashes: Optional[Iterable[str]] = None,
    *, with_error: bool = True,
) -> dict[str, object]:
    """Last run (status, error, category, start) of each workflow that
    passes `filtros`, in a single query.

    ROW_NUMBER() OVER (PARTITION BY workflow_hash ORDER BY start_time DESC)
    compiles the same on PostgreSQL and SQLite (>= 3.25), so there are not two
    paths to maintain. `filtros` always carries the window and the scope — without
    them the window function would scan the whole table.

    `with_error=False` leaves `error_message` out of the projection: the call that only
    wants the status and start of the last run sorts the whole window, and the error
    text is the widest column in the table — loading it only to discard it is a
    cost not worth paying on a large installation.
    """
    condicoes = list(filtros)
    if workflow_hashes is not None:
        hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
        if not hashes:
            return {}
        condicoes.append(WorkflowRun.workflow_hash.in_(hashes))

    posicao = (
        func.row_number()
        .over(
            partition_by=WorkflowRun.workflow_hash,
            order_by=(WorkflowRun.start_time.desc(), WorkflowRun.id.desc()),
        )
        .label("posicao")
    )
    error_columns = (
        [WorkflowRun.error_message, WorkflowRun.error_category] if with_error
        else [literal(None).label("error_message"), literal(None).label("error_category")]
    )
    sub = (
        select(
            WorkflowRun.workflow_hash,
            WorkflowRun.status,
            *error_columns,
            WorkflowRun.start_time,
            posicao,
        )
        .where(*condicoes)
        .subquery("ultimas")
    )
    result = await db.execute(select(sub).where(sub.c.posicao == 1))
    return {row.workflow_hash: row for row in result.all()}


def _summarize_error(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    texto = texto.strip()
    return texto if len(texto) <= _ERROR_SUMMARY_LEN else texto[: _ERROR_SUMMARY_LEN - 1].rstrip() + "…"


