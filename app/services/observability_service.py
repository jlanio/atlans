# app/services/observability_service.py
# Business logic and observability queries extracted from the router.
# Contract with the web app: docs/specs/metrics-history.md (§3).

import json
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import List, Optional

from app.core.exceptions import (
    InvalidDateFormatError,
    RunNotFoundError,
    WorkflowNotFoundError as _WfNotFound,
)
from sqlalchemy import and_, cast, Date as SaDate, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.busca import contem
from app.core.utils.estatistica import taxa_de_sucesso
from app.core.utils.logger import get_logger
from app.models.executor import Executor
from app.models.models import Workflow, WorkflowRun
from app.models.run_metrics import NodeRunMetrics
from app.models.workspace import Workspace

logger = get_logger(__name__)

# Default window for the dashboard aggregations. Without it, the per-status count,
# the average duration and the top failures scanned the ENTIRE workflow_runs on every
# opening of the screen — and `avg(duration_seconds)` has no supporting index at all,
# so it was a guaranteed seq scan, getting worse every month. With the cut, the same
# counts fit in ix_wfrun_workspace_time.
_METRICS_DEFAULT_DAYS = 90

from app.services.observability.escopo import (  # noqa: F401 — fachada p/ testes e rotas
    _agora_utc, _cache_get, _cache_set, _como_utc, _e_postgres, _iso, _metrics_cache_key, _resolver_escopo, _run_filter, _wf_filter, _zona, e_admin_global,
)
from app.services.observability.estatisticas import (  # noqa: F401 — fachada p/ testes e rotas
    _p50_por_workflow, _percentis, _percentis_por, _resumir_erro, _ultima_execucao_por_workflow,
)
from app.services.observability.frota import (  # noqa: F401 — fachada p/ testes e rotas
    _executor_id_do_host, _executores_do_escopo, _presenca,
)
from app.services.observability.runs import (  # noqa: F401 — fachada p/ testes e rotas
    _RUN_LIST_COLUMNS, _contexto_dos_runs, _resolve_workflow_meta, _serialize_run,
)
from app.services.observability.agregados import (  # noqa: F401 — fachada p/ testes e rotas
    _STATUS_ATIVOS,
    _balde_do_status, _bloco_agora, _parse_iso, _top_falhas,
)

# ── Service ───────────────────────────────────────────────────────────────────

class ObservabilityService:

    @staticmethod
    async def get_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """Aggregated metrics for the dashboard and the History, all with a time cut.

        `como_admin` is the full view (no workspace filter, entire fleet,
        late ACKs): only the edge that confirmed the global role turns it on —
        see `e_admin_global`.

        There used to be 8 sequential queries, three of them with NO date filter at all
        (per-status count, `avg(duration_seconds)` and top failures over the ENTIRE
        history). Since no index covers `duration_seconds`, the average was a
        seq scan of the whole table on every opening of the screen — and it got worse every
        month, because `workflow_runs` has no retention policy.

        The per-status aggregations over `workflow_runs` fit into a single one, with
        `count(*) FILTER (WHERE ...)` per cut. `total_runs` is no longer
        lifetime: it is the total OF THE WINDOW, and the response's `period_days` exists
        so the UI can label that.

        This query's WHERE is `max(requested window, 14 days)` because the
        7d/14d cuts live in its `FILTER`s: a 7-day WHERE would make the
        week-over-week comparison mathematically empty (see `janela_where` below). The
        previous period of the same size (`prev_period`) gets a query of its
        own instead of widening that WHERE to 2×days: with `days=90` that would
        double the cost of the main aggregation to serve four numbers.

        Do NOT use `asyncio.gather` here. An `AsyncSession` maps to ONE
        asyncpg connection, and a connection does not accept concurrent statements: the
        `gather` that existed before promised "8 queries in parallel" and delivered
        no parallelism at all — at best the driver serialized them
        (zero gain), at worst it raised InvalidRequestError under concurrency.
        """
        run_f, wf_f = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "metrics", user, workspace_ids, days, como_admin=como_admin,
            workspace_id=workspace_id, workflow_id=workflow_id,
        )
        now       = _agora_utc()
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                # The window aggregations come from the cache; the "now" block is the
                # instant of this query and is never served stale — it is what the
                # Agora strip queries every 30 s.
                fresco = dict(cached)
                fresco["now"] = await _bloco_agora(db, user, run_f, now, como_admin=como_admin)
                return fresco

        since     = now - timedelta(days=days)
        since_24h = now - timedelta(hours=24)
        since_7d  = now - timedelta(days=7)
        since_14d = now - timedelta(days=14)
        since_prev = now - timedelta(days=2 * days)
        prev_7d   = and_(WorkflowRun.start_time >= since_14d, WorkflowRun.start_time < since_7d)

        # The WHERE has to cover the LARGER of the two cuts, not the requested one. The
        # 7d/14d counters are `FILTER`s INSIDE this query: with
        # `?days=7` the WHERE `>= now-7d` intersected with the prev_7d
        # predicate (`>= now-14d AND < now-7d`) gives an empty set, and the dashboard
        # started showing `runs_prev_7d: 0` and `success_rate_prev_7d: null`
        # forever — the trend arrow vanished silently. With `days=1`,
        # worse: `runs_last_7d` was worth the same as `runs_last_24h`.
        janela_where = min(since, since_14d)
        # ...and the aggregates that DO belong to the requested window get the cut back
        # as a FILTER, otherwise `total_runs` would inflate to 14 days when the
        # user asked for 7.
        na_janela = WorkflowRun.start_time >= since

        def _na_janela(status: str):
            return func.count(WorkflowRun.id).filter(na_janela, WorkflowRun.status == status)

        wf_row = (await db.execute(
            select(
                func.count(Workflow.id).label("total"),
                func.count(Workflow.id).filter(Workflow.flag_ative == True).label("ativos"),  # noqa: E712
            ).where(*wf_f)
        )).one()

        row = (await db.execute(
            select(
                func.count(WorkflowRun.id).filter(na_janela).label("total"),
                _na_janela("success").label("success"),
                _na_janela("failed").label("failed"),
                _na_janela("running").label("running"),
                _na_janela("pending").label("pending"),
                _na_janela("cancelled").label("cancelled"),
                func.avg(WorkflowRun.duration_seconds).filter(na_janela).label("avg_duration"),
                func.count(WorkflowRun.id).filter(WorkflowRun.start_time >= since_24h).label("last_24h"),
                func.count(WorkflowRun.id).filter(WorkflowRun.start_time >= since_7d).label("last_7d"),
                func.count(WorkflowRun.id).filter(prev_7d).label("prev_7d"),
                func.count(WorkflowRun.id)
                .filter(prev_7d, WorkflowRun.status == "success")
                .label("prev_7d_success"),
                func.count(WorkflowRun.id)
                .filter(prev_7d, WorkflowRun.status == "failed")
                .label("prev_7d_failed"),
            ).where(WorkflowRun.start_time >= janela_where, *run_f)
        )).one()

        # Previous period of the same size: [now-2d, now-d). It is what gives
        # meaning to "1,284 runs" — whether that is a lot or a little only the comparison tells.
        no_prev = [WorkflowRun.start_time >= since_prev, WorkflowRun.start_time < since]
        prev = (await db.execute(
            select(
                func.count(WorkflowRun.id).label("total"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed"),
            ).where(*no_prev, *run_f)
        )).one()

        p50, p95 = await _percentis(db, [na_janela, *run_f], [0.5, 0.95])
        (prev_p50,) = await _percentis(db, [*no_prev, *run_f], [0.5])

        top_failing = await _top_falhas(db, run_f, since)
        agora = await _bloco_agora(db, user, run_f, now, como_admin=como_admin)

        total_runs     = row.total or 0
        success_runs   = row.success or 0
        failed_runs    = row.failed or 0
        running_runs   = row.running or 0
        pending_runs   = row.pending or 0
        cancelled_runs = row.cancelled or 0
        runs_prev_7d   = row.prev_7d or 0
        prev_7d_ok     = row.prev_7d_success or 0
        prev_7d_falha  = row.prev_7d_failed or 0
        prev_success   = prev.success or 0
        prev_failed    = prev.failed or 0

        metrics = {
            "period_days":      days,
            "total_workflows":  wf_row.total or 0,
            "active_workflows": wf_row.ativos or 0,
            "total_runs":       total_runs,
            "by_status": {
                "success":   success_runs,
                "failed":    failed_runs,
                "running":   running_runs,
                "pending":   pending_runs,
                "cancelled": cancelled_runs,
                "other":     total_runs - success_runs - failed_runs - running_runs - pending_runs - cancelled_runs,
            },
            "success_runs":    success_runs,
            "failed_runs":     failed_runs,
            "running_runs":    running_runs,
            "pending_runs":    pending_runs,
            "cancelled_runs":  cancelled_runs,
            # Completed ÷ (completed + failed): in-progress and cancelled ones
            # are not a verdict — with them in the denominator the rate dropped on every
            # load peak.
            "success_rate":    taxa_de_sucesso(success_runs, failed_runs),
            "avg_duration_seconds": round(float(row.avg_duration or 0.0), 3),
            "runs_last_24h":   row.last_24h or 0,
            "runs_last_7d":    row.last_7d or 0,
            "runs_prev_7d":    runs_prev_7d,
            # `null` (and not 0.0) with no denominator: it is what hides the trend
            # arrow in the Overview instead of showing "dropped to 0%".
            "success_rate_prev_7d": (
                taxa_de_sucesso(prev_7d_ok, prev_7d_falha) if (prev_7d_ok + prev_7d_falha) else None
            ),
            "prev_period": {
                "total_runs":   prev.total or 0,
                "success_runs": prev_success,
                "failed_runs":  prev_failed,
                "success_rate": taxa_de_sucesso(prev_success, prev_failed),
                "p50_seconds":  prev_p50,
            },
            "duration": {"p50_seconds": p50, "p95_seconds": p95},
            "now": agora,
            "top_failing_workflows": top_failing,
        }

        await _cache_set(cache_key, metrics)
        return metrics

    @staticmethod
    async def get_workflow_metrics(
        db: AsyncSession,
        workflow_hash: str,
        user,
        workspace_ids: List[str],
        limit: int = 20,
        *,
        como_admin: bool = False,
    ) -> dict:
        """Detailed metrics for a specific workflow.

        The per-node summary comes from `node_run_metrics`, which already stores the
        normalized data (duration_ms, status, cache_hit, features per node). This
        method used to download the `node_stats` JSON of the last N runs and
        re-aggregate everything in Python on every request: the page's time came to
        depend on the SIZE of the executed workflows, and the worker's event loop
        was stuck deserializing JSON.
        """
        wf_conditions = [
            Workflow.id_hash == workflow_hash,
            *_wf_filter(user, workspace_ids, como_admin=como_admin),
        ]

        # Only the name is used — `select(Workflow)` dragged along the workflow's entire
        # `definition` (tens of KB) for nothing.
        wf_result = await db.execute(select(Workflow.name).where(*wf_conditions))
        workflow_name = wf_result.scalar_one_or_none()
        if workflow_name is None:
            raise _WfNotFound("Workflow não encontrado.")

        # Admin meta (owner + workspace) to show in the workflow detail.
        admin_meta = {}
        if como_admin:
            meta_map = await _resolve_workflow_meta(db, [workflow_hash])
            admin_meta = meta_map.get(workflow_hash) or {}

        # Access to the workflow (above) does not authorize the history: a workflow
        # moved between workspaces would carry with it runs produced in the previous
        # workspace. The runs are filtered by their own workspace_id — see
        # _run_filter, which we reuse so as not to duplicate the rule.
        runs_result = await db.execute(
            select(*_RUN_LIST_COLUMNS)
            .where(
                WorkflowRun.workflow_hash == workflow_hash,
                *_run_filter(user, workspace_ids, como_admin=como_admin),
            )
            .order_by(WorkflowRun.start_time.desc())
            .limit(limit)
        )
        runs = runs_result.all()

        if not runs:
            return {
                "workflow_id":           workflow_hash,
                "workflow_name":         workflow_name,
                "total_runs":            0,
                "failed_runs":           0,
                "success_rate":          0.0,
                "avg_duration_seconds":  0.0,
                "min_duration_seconds":  None,
                "max_duration_seconds":  None,
                "last_runs":             [],
                "node_stats_summary":    [],
                **admin_meta,
            }

        total    = len(runs)
        failed   = sum(1 for r in runs if r.status == "failed")
        success  = sum(1 for r in runs if r.status == "success")
        durations = [r.duration_seconds for r in runs if r.duration_seconds is not None]

        contexto = await _contexto_dos_runs(db, runs)
        last_runs = [_serialize_run(r, admin=como_admin, **contexto) for r in runs]

        # Per-node summary: one SQL aggregation over node_run_metrics, restricted
        # to the run_ids above (ix_node_metrics_run covers the IN). Runs whose executor
        # never sent metrics — failure before executing any node —
        # simply have no row here, which is the same as having empty node_stats.
        run_ids = [r.task_id for r in runs if r.task_id]
        node_stats_summary: list[dict] = []
        if run_ids:
            summary_result = await db.execute(
                select(
                    NodeRunMetrics.node_id,
                    func.max(NodeRunMetrics.node_name).label("node_name"),
                    func.count(NodeRunMetrics.id).label("execution_count"),
                    func.avg(NodeRunMetrics.duration_ms).label("avg_duration_ms"),
                    func.count(NodeRunMetrics.id)
                    .filter(NodeRunMetrics.status == "failed")
                    .label("failure_count"),
                    func.count(NodeRunMetrics.id)
                    .filter(NodeRunMetrics.cache_hit == True)  # noqa: E712
                    .label("cache_hits"),
                    func.avg(NodeRunMetrics.input_features).label("avg_input_features"),
                    func.avg(NodeRunMetrics.output_features).label("avg_output_features"),
                )
                .where(NodeRunMetrics.run_id.in_(run_ids))
                .group_by(NodeRunMetrics.node_id)
                .order_by(func.avg(NodeRunMetrics.duration_ms).desc().nullslast())
            )
            node_stats_summary = [
                {
                    "node_id":          s.node_id,
                    "node_name":        s.node_name or s.node_id,
                    "execution_count":  s.execution_count,
                    "avg_duration_ms":  round(float(s.avg_duration_ms), 2) if s.avg_duration_ms is not None else 0,
                    "failure_count":    s.failure_count,
                    "cache_hits":       s.cache_hits,
                    "avg_input_features":  round(float(s.avg_input_features)) if s.avg_input_features is not None else None,
                    "avg_output_features": round(float(s.avg_output_features)) if s.avg_output_features is not None else None,
                }
                for s in summary_result
            ]

        return {
            "workflow_id":           workflow_hash,
            "workflow_name":         workflow_name,
            "total_runs":            total,
            "failed_runs":           failed,
            # The same rate as the other screens. It was `(total - failed) / total`, which
            # counted in-progress and cancelled runs as successes.
            "success_rate":          taxa_de_sucesso(success, failed),
            "avg_duration_seconds":  round(sum(durations) / len(durations), 3) if durations else 0.0,
            "min_duration_seconds":  round(min(durations), 3) if durations else None,
            "max_duration_seconds":  round(max(durations), 3) if durations else None,
            "last_runs":             last_runs,
            "node_stats_summary":    node_stats_summary,
            **admin_meta,
        }

    @staticmethod
    async def get_workflows_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """The "Por workflow" (per workflow) view (spec §3.3): ALL accessible workflows, with
        zeros for those that did not run in the window — the list is an inventory, and an
        active workflow that never runs is information, not absence.

        Four queries, none per row: the inventory (workflows +
        workspace), the aggregation by `workflow_hash` in the window, the median per
        workflow and each one's last run (window function). The "last"
        is the last one IN THE WINDOW: fetching each workflow's lifetime last one is a
        scan of the whole scope on every opening, and the period governs all
        the blocks of the screen.
        """
        run_f, wf_f = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "workflows", user, workspace_ids, days, como_admin=como_admin, workspace_id=workspace_id,
        )
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                return cached

        now = _agora_utc()
        since = now - timedelta(days=days)
        na_janela = [WorkflowRun.start_time >= since, *run_f]

        inventario = (await db.execute(
            select(
                Workflow.id_hash,
                Workflow.name,
                Workflow.flag_ative,
                Workflow.workspace_id,
                Workflow.origem,
                Workspace.name.label("workspace_name"),
            )
            .select_from(Workflow)
            .outerjoin(Workspace, Workspace.id_hash == Workflow.workspace_id)
            .where(Workflow.deleted_at.is_(None), *wf_f)
        )).all()

        agregados = {
            row.workflow_hash: row
            for row in (await db.execute(
                select(
                    WorkflowRun.workflow_hash,
                    func.count(WorkflowRun.id).label("total"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed"),
                    func.count(WorkflowRun.id).filter(WorkflowRun.status.in_(_STATUS_ATIVOS)).label("running"),
                )
                .where(*na_janela)
                .group_by(WorkflowRun.workflow_hash)
            )).all()
        }
        medianas = await _percentis_por(db, WorkflowRun.workflow_hash, na_janela, [0.5])
        com_execucao = list(agregados)
        ultimas = await _ultima_execucao_por_workflow(db, na_janela, workflow_hashes=com_execucao, com_erro=False)
        # "Last error" is that of the last FAILURE, as in the top failures and the
        # attention list — the last run may have completed and the workflow still
        # have dozens of failures in the window.
        com_falha = [h for h, row in agregados.items() if (row.failed or 0) > 0]
        ultimas_falhas = (
            await _ultima_execucao_por_workflow(
                db, [WorkflowRun.status == "failed", *na_janela], workflow_hashes=com_falha,
            ) if com_falha else {}
        )

        linhas = []
        for wf in inventario:
            agg = agregados.get(wf.id_hash)
            ultima = ultimas.get(wf.id_hash)
            falha = ultimas_falhas.get(wf.id_hash)
            success = (agg.success or 0) if agg else 0
            failed = (agg.failed or 0) if agg else 0
            linhas.append({
                "workflow_hash":  wf.id_hash,
                "workflow_name":  wf.name,
                "workspace_id":   wf.workspace_id,
                "workspace_name": wf.workspace_name,
                "active":         bool(wf.flag_ative),
                # Who created the workflow ("usuario" | "assistente") — the list's
                # badge. Not to be confused with `trigger_source`, which is the trigger.
                "origem":         wf.origem,
                "total_runs":     (agg.total or 0) if agg else 0,
                "success_runs":   success,
                "failed_runs":    failed,
                "running_runs":   (agg.running or 0) if agg else 0,
                "success_rate":   taxa_de_sucesso(success, failed),
                "p50_seconds":    (medianas.get(wf.id_hash) or [None])[0],
                "last_run_at":    _iso(ultima.start_time) if ultima else None,
                "last_status":    ultima.status if ultima else None,
                "last_error":     _resumir_erro(falha.error_message) if falha else None,
                "last_error_category": falha.error_category if falha else None,
            })

        linhas.sort(key=lambda linha: (-linha["total_runs"], (linha["workflow_name"] or "").casefold()))

        payload = {"period_days": days, "workflows": linhas}
        await _cache_set(cache_key, payload)
        return payload

    @staticmethod
    async def get_executor_metrics(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        days: int = _METRICS_DEFAULT_DAYS,
        force: bool = False,
        workspace_id: Optional[str] = None,
        como_admin: bool = False,
    ) -> dict:
        """Per-executor statistics, in the `days` window (spec §3.4).

        There used to be TWO full aggregations over `workflow_runs` (`GROUP BY host` and
        `GROUP BY host, status`) with no date cut at all — two seq scans +
        hash aggregate per request, since there was no index on `host`. Now it is
        a single query, with the per-status counters in `FILTER`, bounded by the
        window (which fits in ix_wfrun_workspace_time) and served from the same short
        cache as `get_metrics`.

        The whole fleet goes in: online executors in scope that ran
        nothing in the window appear with zeros, otherwise the "Por executor" view would
        only show who worked and would hide precisely the idle ones.
        """
        run_f, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, como_admin=como_admin,
        )
        cache_key = _metrics_cache_key(
            "executores", user, workspace_ids, days, como_admin=como_admin, workspace_id=workspace_id,
        )
        if not force:
            cached = await _cache_get(cache_key)
            if cached is not None:
                return cached

        since = _agora_utc() - timedelta(days=days)
        na_janela = [WorkflowRun.start_time >= since, *run_f]

        result = await db.execute(
            select(
                WorkflowRun.host,
                func.count(WorkflowRun.id).label("total_runs"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "success").label("success_runs"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed_runs"),
                func.avg(WorkflowRun.duration_seconds).label("avg_duration"),
                func.max(WorkflowRun.start_time).label("last_run_at"),
            )
            .where(*na_janela)
            .group_by(WorkflowRun.host)
            .order_by(func.count(WorkflowRun.id).desc())
        )
        rows = result.all()
        medianas = await _percentis_por(db, WorkflowRun.host, na_janela, [0.5])

        frota = {
            e["id_hash"]: e
            for e in await _executores_do_escopo(db, user, como_admin=como_admin)
        }
        # Hosts with runs that are not in the scope's fleet (executor
        # removed from a workspace, deactivated, or outside the user's access)
        # still need a name — one SELECT IN for all of them.
        ids_da_frota = list(frota.keys())
        ids_com_runs = [_executor_id_do_host(row.host) for row in rows if _executor_id_do_host(row.host)]
        faltantes = [i for i in ids_com_runs if i not in frota]
        if faltantes:
            extra = await db.execute(
                select(
                    Executor.id_hash, Executor.name, Executor.executor_type,
                    Executor.is_default, Executor.status,
                ).where(Executor.id_hash.in_(faltantes))
            )
            for r in extra.all():
                frota[r.id_hash] = {
                    "id_hash": r.id_hash, "name": r.name, "executor_type": r.executor_type,
                    "is_default": bool(r.is_default), "status": r.status,
                }

        # Presence and capacity ONLY for the accessible fleet: an executor that ran one of
        # the user's runs and then left the scope shows up with a name, but its
        # current state (online, queue) is not the user's information.
        online, capacidade = await _presenca(ids_da_frota)

        def _linha(host: Optional[str], executor_id: Optional[str], row) -> dict:
            info = frota.get(executor_id) if executor_id else None
            total = (row.total_runs or 0) if row is not None else 0
            success = (row.success_runs or 0) if row is not None else 0
            failed = (row.failed_runs or 0) if row is not None else 0
            if host is None:
                display_name = "Sem executor"
            elif executor_id:
                nome = info["name"] if info else None
                display_name = f"{nome}@{executor_id[-5:]}" if nome else host
            else:
                display_name = host
            return {
                "agent_host":     host,
                "display_name":   display_name,
                "executor_id":    executor_id,
                "executor_type":  info["executor_type"] if info else None,
                "is_default":     bool(info["is_default"]) if info else False,
                "status":         info["status"] if info else None,
                "online":         bool(online.get(executor_id)) if executor_id else False,
                "capacity":       capacidade.get(executor_id) if executor_id else None,
                # Runs without a host are dispatch failures (no executor
                # ever received the job) — the screen needs that distinction.
                "unassigned":     host is None,
                "total_runs":     total,
                "success_runs":   success,
                "failed_runs":    failed,
                "success_rate":   taxa_de_sucesso(success, failed),
                "avg_duration_seconds": (
                    round(float(row.avg_duration), 3) if row is not None and row.avg_duration else None
                ),
                "p50_seconds":    (medianas.get(host) or [None])[0] if host is not None else None,
                "last_run_at":    _iso(row.last_run_at) if row is not None and row.last_run_at else None,
            }

        agents_stats = [_linha(row.host or None, _executor_id_do_host(row.host), row) for row in rows]
        vistos = {row.host for row in rows if row.host}
        for eid, info in frota.items():
            host = f"executor:{eid}"
            if host not in vistos and online.get(eid):
                agents_stats.append(_linha(host, eid, None))

        agents_stats.sort(key=lambda a: (-a["total_runs"], a["display_name"].casefold()))

        payload = {"executores": agents_stats, "period_days": days}
        await _cache_set(cache_key, payload)
        return payload

    @staticmethod
    async def list_runs(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        *,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        worker_host: Optional[str] = None,
        workspace_id: Optional[str] = None,
        trigger_source: Optional[str] = None,
        tier: Optional[str] = None,
        workflow_origem: Optional[str] = None,
        q: Optional[str] = None,
        q_inclui_erro: bool = True,
        limit: int = 50,
        offset: int = 0,
        with_total: bool = False,
        como_admin: bool = False,
    ) -> dict:
        """Lists runs, paginated, with filters.

        The full `COUNT(*)` left the default path: it does not use LIMIT, grows
        with the table and was paid on EVERY page — including the polling of active
        runs, which runs every 10s on every dashboard screen. Now it is only
        computed with `with_total=True` (the UI asks for it on the first page, for the
        "N execuções" label); navigation uses `has_more`, obtained by requesting
        `limit + 1` rows and discarding the extra one.

        The `q` search is the only thing that joins `workflows` to this query (to
        match the name), and only when present: on the common path the listing
        is still just an index scan on `workflow_runs`.

        `workflow_origem` filters by the WORKFLOW's origin ("usuario" |
        "assistente" — who created the workflow, not who triggered the run; the
        trigger is `trigger_source`). It is the History's "Assistente" chip.
        Like `q`, it needs the join with `workflows`; runs of permanently deleted
        workflows are left out of the slice, which is about live workflows.

        `q_inclui_erro=False` removes `error_message` from the search's `or_`, leaving
        only the workflow name and the `task_id`. It exists for the caller that does NOT
        hand out the error message as it is in the database: the MCP server only
        publishes it after `scrub_text`, and a substring filter on the raw
        column would return the same text through another channel, as yes/no —
        the caller repeats the query extending the prefix (`...:a` with no
        result, `...:b` with no result, `...:S` with one item) and recovers,
        character by character, exactly what the redaction erased. The default is
        `True` because REST shows the whole message on screen: there the search
        reveals nothing the response itself does not already carry.
        """
        filters, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )

        if status:
            filters.append(WorkflowRun.status == status)
        if worker_host:
            filters.append(WorkflowRun.host == worker_host)
        if trigger_source:
            filters.append(WorkflowRun.trigger_source == trigger_source)
        if tier:
            filters.append(WorkflowRun.dispatch_tier == tier)
        if date_from:
            try:
                filters.append(WorkflowRun.start_time >= _como_utc(_parse_iso(date_from)))
            except ValueError:
                raise InvalidDateFormatError(f"date_from inválido: {date_from}")
        if date_to:
            try:
                filters.append(WorkflowRun.start_time <= _como_utc(_parse_iso(date_to)))
            except ValueError:
                raise InvalidDateFormatError(f"date_to inválido: {date_to}")

        busca = (q or "").strip()
        if busca:
            alvos = [
                contem(Workflow.name, busca),
                # The id pasted from the panel's "Copiar ID" (copy ID) button also finds the run.
                contem(WorkflowRun.task_id, busca),
            ]
            if q_inclui_erro:
                alvos.insert(0, contem(WorkflowRun.error_message, busca))
            filters.append(or_(*alvos))

        if workflow_origem:
            filters.append(Workflow.origem == workflow_origem)

        def _com_workflows(stmt):
            if busca or workflow_origem:
                return stmt.outerjoin(Workflow, Workflow.id_hash == WorkflowRun.workflow_hash)
            return stmt

        total = None
        if with_total:
            total_result = await db.execute(
                _com_workflows(select(func.count(WorkflowRun.id)).select_from(WorkflowRun)).where(*filters)
            )
            total = total_result.scalar() or 0

        runs_result = await db.execute(
            _com_workflows(select(*_RUN_LIST_COLUMNS))
            .where(*filters)
            .order_by(WorkflowRun.start_time.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        runs = runs_result.all()
        has_more = len(runs) > limit
        runs = runs[:limit]

        contexto = await _contexto_dos_runs(db, runs)

        return {
            # `null` when the client did not ask for `with_total` — the UI uses
            # `has_more` to decide whether there is still more to load.
            "total":    total,
            "has_more": has_more,
            "limit":  limit,
            "offset": offset,
            "runs":   [
                _serialize_run(r, include_workflow_hash=True, admin=como_admin, **contexto)
                for r in runs
            ],
        }

    @staticmethod
    async def get_run_detail(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> dict:
        """Details of a specific run."""
        # Access by the RUN's workspace, not the workflow's: the workflow may have
        # been moved after this run, and the history belongs to whoever had
        # access to it when it happened. The rule comes from `_run_filter`, the same
        # one the listing and the metrics use — rewriting it in Python here would give
        # two formulations of the same criterion. Applied in the query, "no access" and
        # "does not exist" fall into the same 404, which is the desired behavior: a 403
        # would confirm the run's existence.
        run_f = _run_filter(user, workspace_ids, como_admin=como_admin)

        run_result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.task_id == run_id, *run_f)
        )
        run = run_result.scalar_one_or_none()

        if run is None and run_id.isdigit():
            run_result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == int(run_id), *run_f)
            )
            run = run_result.scalar_one_or_none()

        if run is None:
            raise RunNotFoundError(f"Execução '{run_id}' não encontrada.")

        contexto = await _contexto_dos_runs(db, [run])

        # The 90-day median (typical_seconds) only matters once the run has FINISHED:
        # it exists so the panel can say "took 8 min; usually takes 40 s".
        # While the run is going, the client polls (run_workflow instructs "follow
        # with get_run") and recomputing the 90-day percentile on every poll was a scan
        # per call with no value — the comparison does not even make sense yet. Only computes
        # on a terminal (non-ACTIVE) status.
        tipicos: dict = {}
        if run.status not in _STATUS_ATIVOS:
            tipicos = await _p50_por_workflow(db, [run.workflow_hash], _agora_utc())

        detalhe = _serialize_run(
            run, include_workflow_hash=True, include_node_stats=True,
            admin=como_admin, **contexto,
        )
        # The workflow's median over the last 90 days: it is what lets the panel
        # say "took 8 min; usually takes 40 s". None while the run has not finished.
        detalhe["typical_seconds"] = tipicos.get(run.workflow_hash) if isinstance(run.workflow_hash, str) else None
        return detalhe

    @staticmethod
    async def get_run_events(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> dict:
        """Raw events of a run, in the order they were published.

        The same list the WebSocket replays on (re)connecting — exposed here over
        HTTP so the execution panel can open the log of a run that has already
        finished. Without this, closing the workflow erased the log forever: the
        frontend store is volatile and the observability page only has node_stats.

        The history lives in Redis with a 1h TTL; after that we return an
        empty list with `expired=True` so the panel says "the log expired" instead
        of "there was no output".
        """
        eventos, _ = await ObservabilityService.get_run_events_com_detalhe(
            db, run_id, user, workspace_ids, como_admin=como_admin,
        )
        return eventos

    @staticmethod
    async def get_run_events_com_detalhe(
        db: AsyncSession,
        run_id: str,
        user,
        workspace_ids: List[str],
        *,
        como_admin: bool = False,
    ) -> tuple[dict, dict]:
        """The events PLUS the detail of the run that authorized them.

        It exists for whoever needs both — today the MCP `get_run_events` tool,
        which uses the run's status and dates to say whether the empty list is "expired",
        "still running" or "there was no output". Without this, it loaded the detail
        from outside and the service loaded it again inside: `get_run_detail` has no
        cache and does 3 to 6 queries (among them a three-table join and
        a percentile over a 90-day window), so it was 6 to 12 database round trips
        per call, half of them waste.

        There is deliberately no parameter to "skip authorization": the caller
        receives the detail THIS method authorized, instead of being able to pass in a
        detail of other provenance. The savings are the same and it does not open a path
        to an IDOR through a badly passed argument.
        """
        # Reuses the detail's access check — raises RunNotFoundError if the
        # run does not exist or does not belong to the user's workspace(s).
        detalhe = await ObservabilityService.get_run_detail(
            db, run_id, user, workspace_ids, como_admin=como_admin,
        )

        from app.core.redis import get_redis_pool
        from app.services.run_events_service import chave_do_historico

        # The key comes from the run's CANONICAL `task_id`, never from what the caller
        # typed. `get_run_detail` also resolves by the row's NUMERIC id
        # (see the `run_id.isdigit()` branch above), and the history key is
        # `workflow:{task_id}:history`. Using the raw value authorized one run and read the
        # key of another: `GET /observability/runs/123/events` answered 200 with
        # `expired: true` and the whole log alive under the other key. It is not a
        # leak — the keys are written with a uuid and a number never collides —,
        # it is a silently wrong response, which is the worst kind of missing log.
        alvo = str(detalhe.get("run_id") or run_id)

        history_key = chave_do_historico(alvo)
        try:
            raw = await get_redis_pool().lrange(history_key, 0, -1)
        except Exception as exc:
            logger.warning("Falha ao ler histórico de eventos do run '%s': %s", alvo, exc)
            return {"run_id": alvo, "events": [], "expired": True}, detalhe

        events = []
        for item in raw:
            try:
                events.append(json.loads(item))
            except (TypeError, ValueError):
                continue

        return {"run_id": alvo, "events": events, "expired": not events}, detalhe

    @staticmethod
    async def get_runs_by_day(
        db: AsyncSession,
        user,
        workspace_ids: List[str],
        days: int = 7,
        *,
        workspace_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        tz: str = "UTC",
        como_admin: bool = False,
    ) -> dict:
        """Run count per day for the chart (spec §3.2).

        The day is cut in the requested time zone — for someone in Cuiaba, a
        run at 10 p.m. cannot show up on the next day just because in UTC it was already
        2 a.m. The window starts at LOCAL midnight `days - 1` days ago,
        so the chart has exactly `days` bars of whole days (the last one
        is today, up to now); and every day comes out, with zeros, because a day without
        runs is information and the missing bar looked like a hole in the axis.

        On PostgreSQL the cut is `start_time AT TIME ZONE tz` (the
        `timezone()` function), grouped in the database. Elsewhere (SQLite, in tests and the
        harness) it projects only `(start_time, status)` of the window and groups in
        Python — the old `CAST(start_time AS DATE)` returned the YEAR on SQLite.
        """
        zona = _zona(tz)
        run_f, _ = await _resolver_escopo(
            db, user, workspace_ids, workspace_id=workspace_id, workflow_id=workflow_id,
            como_admin=como_admin,
        )

        now = _agora_utc()
        hoje = now.astimezone(zona).date()
        primeiro_dia = hoje - timedelta(days=days - 1)
        since = datetime.combine(primeiro_dia, dt_time.min, tzinfo=zona).astimezone(timezone.utc)
        base_filter = [WorkflowRun.start_time >= since, *run_f]

        dias = {
            (primeiro_dia + timedelta(days=i)).isoformat(): {
                "day": (primeiro_dia + timedelta(days=i)).isoformat(),
                "total": 0, "success": 0, "failed": 0, "running": 0, "cancelled": 0, "other": 0,
            }
            for i in range(days)
        }

        if _e_postgres(db):
            dia_local = cast(func.timezone(tz, WorkflowRun.start_time), SaDate)
            result = await db.execute(
                select(dia_local.label("day"), WorkflowRun.status, func.count(WorkflowRun.id).label("count"))
                .where(*base_filter)
                .group_by(dia_local, WorkflowRun.status)
            )
            contagens = [(str(row.day), row.status, row.count or 0) for row in result.all()]
        else:
            result = await db.execute(
                select(WorkflowRun.start_time, WorkflowRun.status).where(*base_filter)
            )
            contagens = [
                (_como_utc(row.start_time).astimezone(zona).date().isoformat(), row.status, 1)
                for row in result.all()
                if row.start_time is not None
            ]

        for dia, status, n in contagens:
            balde = dias.get(dia)
            if balde is None:
                continue
            balde["total"] += n
            balde[_balde_do_status(status)] += n

        return {"days": list(dias.values())}


