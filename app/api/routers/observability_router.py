# app/api/routers/observability_router.py
"""
Observability endpoints — aggregated workflow run metrics.
Contract with the web: docs/specs/metrics-history.md (§3).

Scope rules:
  - admin  → sees everything (no filter)
  - user → sees runs and workflows of the workspaces where they are owner or member

The full view is NOT inferred by the service from the `User`: it is this router
that declares it, on every call, with `como_admin=e_admin_global(current_user)`.
The MCP server (docs/specs/mcp-server.md §6.12) uses the same services with the
member view, and an admin with a PAT cannot cross the token's scope just
because the `User` object carries the role.

Common filters (optional): `workspace_id` (403 outside the user's scope),
`workflow_id` (404 outside the scope) and, in the per-day chart, `tz` (422 if it
is not an IANA name).
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.api.dependencies import get_db, get_current_user, get_user_workspace_ids
from app.services.observability_service import ObservabilityService, e_admin_global

router = APIRouter(
    prefix="/observability",
    tags=["observability"],
    dependencies=[Depends(get_current_user)],
)

_svc = ObservabilityService


def _tz_valido(
    tz: str = Query("UTC", description="Fuso IANA para cortar o dia (ex.: America/Sao_Paulo)"),
) -> str:
    """Validates `?tz=` at the edge: an invalid name would become an SQL error in
    PostgreSQL's `AT TIME ZONE` (500) instead of a 422 the web understands."""
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tz inválido: {tz!r} não é um fuso IANA.",
        )
    return tz


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/metrics", summary="Métricas gerais de execução dos workflows")
async def get_metrics(
    days:  int  = Query(90, ge=1, le=365, description="Janela em dias das agregações"),
    force: bool = Query(False, description="Ignora o cache (botão Atualizar)"),
    workspace_id: Optional[str] = Query(None, description="Restringe a um workspace acessível"),
    workflow_id:  Optional[str] = Query(None, description="Restringe a um workflow acessível"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Returns aggregated metrics for the requested window (`period_days` in the response),
    the previous period of the same size, duration percentiles and the `now` block.
    Admin sees all data; a user sees workflows of their workspace(s).

    Served from a ~45s Redis cache: these are dashboard numbers, and without it each
    open tab repeated the same aggregations over `workflow_runs`.
    """
    return await _svc.get_metrics(
        db, current_user, workspace_ids,
        days=days, force=force, workspace_id=workspace_id, workflow_id=workflow_id,
        como_admin=e_admin_global(current_user),
    )


@router.get("/metrics/workflows", summary="Métricas por workflow na janela (visão 'Por workflow')")
async def get_workflows_metrics(
    days:  int  = Query(90, ge=1, le=365, description="Janela em dias das agregações"),
    force: bool = Query(False, description="Ignora o cache (botão Atualizar)"),
    workspace_id: Optional[str] = Query(None, description="Restringe a um workspace acessível"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    All accessible workflows — including those with no runs in the window, with
    zeros — ordered by runs (desc) and name. Same short cache as `/metrics`.
    """
    return await _svc.get_workflows_metrics(
        db, current_user, workspace_ids, days=days, force=force, workspace_id=workspace_id,
        como_admin=e_admin_global(current_user),
    )


@router.get(
    "/metrics/workflow/{id_hash}",
    summary="Métricas detalhadas de um workflow específico",
)
async def get_workflow_metrics(
    id_hash: str,
    # A ceiling of 1000 was not defensible: each run loaded metrics for
    # all its nodes and the screen shows dozens of rows, not a thousand.
    limit: int = Query(20, ge=1, le=100, description="Últimas N execuções"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Returns metrics for a specific workflow.
    Admin accesses any workflow; a user accesses workflows of their workspace(s).
    """
    return await _svc.get_workflow_metrics(
        db, id_hash, current_user, workspace_ids, limit,
        como_admin=e_admin_global(current_user),
    )


@router.get("/metrics/executores", summary="Métricas de execução agrupadas por executor")
async def get_executor_metrics(
    days:  int  = Query(90, ge=1, le=365, description="Janela em dias das agregações"),
    force: bool = Query(False, description="Ignora o cache (botão Atualizar)"),
    workspace_id: Optional[str] = Query(None, description="Restringe a um workspace acessível"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Per-executor statistics in the requested window, plus current presence and
    capacity. Admin sees all; a user sees runs of their workspaces. Same short
    cache as `/metrics`.
    """
    return await _svc.get_executor_metrics(
        db, current_user, workspace_ids, days=days, force=force, workspace_id=workspace_id,
        como_admin=e_admin_global(current_user),
    )


@router.get("/runs", summary="Lista execuções com filtros")
async def list_runs(
    workflow_id: Optional[str] = Query(None, description="Filtrar por workflow"),
    workspace_id: Optional[str] = Query(None, description="Filtrar por workspace acessível"),
    status:      Optional[str] = Query(None, description="Filtrar por status"),
    date_from:   Optional[str] = Query(None, description="ISO 8601 — início do período"),
    date_to:     Optional[str] = Query(None, description="ISO 8601 — fim do período"),
    worker_host: Optional[str] = Query(None, description="Filtrar por hostname do worker"),
    trigger_source: Optional[str] = Query(
        None, pattern="^(manual|retry|webhook|schedule|mcp)$", description="Origem do disparo",
    ),
    tier: Optional[str] = Query(
        None, pattern="^(primary|fallback|pool)$", description="Nível da política em que rodou",
    ),
    workflow_origem: Optional[str] = Query(
        None, pattern="^(usuario|assistente)$",
        description="Origem do FLUXO (quem o criou) — não confundir com trigger_source, que é o disparo",
    ),
    q: Optional[str] = Query(
        None, max_length=200, description="Busca no erro e no nome do workflow",
    ),
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0,  ge=0),
    with_total: bool = Query(
        False, description="Calcula o COUNT(*) total — peça só na primeira página"
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """Lists runs. Admin sees all; a user sees runs of their workspaces.

    `total` is only filled with `with_total=1`; without it the response carries
    `has_more`, which is what "Ver mais" (See more) needs and does not cost a table count.
    """
    return await _svc.list_runs(
        db, current_user, workspace_ids,
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        worker_host=worker_host,
        trigger_source=trigger_source,
        tier=tier,
        workflow_origem=workflow_origem,
        q=q,
        limit=limit,
        offset=offset,
        with_total=with_total,
        como_admin=e_admin_global(current_user),
    )


@router.get("/runs/{run_id}", summary="Detalhes de uma execução específica")
async def get_run_detail(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Details of a run. Admin accesses any run;
    a user accesses runs of workflows in their workspace(s).
    """
    return await _svc.get_run_detail(
        db, run_id, current_user, workspace_ids, como_admin=e_admin_global(current_user),
    )


@router.get("/runs/{run_id}/events", summary="Eventos brutos de uma execução")
async def get_run_events(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Raw event timeline of a run (the same replay the WebSocket
    delivers on connect). Lets the run panel reopen the log of an
    already finished run. History expires after 1h in Redis.
    """
    return await _svc.get_run_events(
        db, run_id, current_user, workspace_ids, como_admin=e_admin_global(current_user),
    )


@router.get("/runs-by-day", summary="Execuções agrupadas por dia (últimos N dias)")
async def runs_by_day(
    days: int = Query(7, ge=1, le=90, description="Quantos dias incluir, contando hoje"),
    workspace_id: Optional[str] = Query(None, description="Restringe a um workspace acessível"),
    workflow_id:  Optional[str] = Query(None, description="Restringe a um workflow acessível"),
    tz: str = Depends(_tz_valido),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Run count per day, with the day cut in the `tz` time zone and every
    day of the window present (zeros included). Admin sees everything; a user sees
    runs of their workspaces.
    """
    return await _svc.get_runs_by_day(
        db, current_user, workspace_ids, days,
        workspace_id=workspace_id, workflow_id=workflow_id, tz=tz,
        como_admin=e_admin_global(current_user),
    )
