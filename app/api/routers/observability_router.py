# app/api/routers/observability_router.py
"""
Observability endpoints — métricas agregadas de execução dos workflows.
Contrato com a web: docs/specs/metrics-history.md (§3).

Regras de escopo:
  - admin  → vê tudo (sem filtro)
  - usuário → vê runs e workflows dos workspaces onde é dono ou membro

A visão total NÃO é deduzida pelo service a partir do `User`: é este router
que a declara, em toda chamada, com `como_admin=e_admin_global(current_user)`.
O servidor MCP (docs/specs/mcp-server.md §6.12) usa os mesmos services com a
visão de membro, e um admin com PAT não pode atravessar o escopo do token só
porque o objeto `User` carrega o papel.

Filtros comuns (opcionais): `workspace_id` (403 fora do escopo do usuário),
`workflow_id` (404 fora do escopo) e, no gráfico por dia, `tz` (422 se não for
um nome IANA).
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
    """Valida o `?tz=` na borda: um nome inválido viraria erro de SQL no
    `AT TIME ZONE` do PostgreSQL (500) em vez de um 422 que a web entende."""
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
    Retorna métricas agregadas da janela pedida (`period_days` na resposta),
    o período anterior de mesmo tamanho, percentis de duração e o bloco `now`.
    Admin vê todos os dados; usuário vê workflows do(s) seu(s) workspace(s).

    Servido de um cache Redis de ~45s: são números de painel, e sem ele cada
    aba aberta repetia as mesmas agregações sobre `workflow_runs`.
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
    Todos os workflows acessíveis — inclusive os sem execução na janela, com
    zeros — ordenados por execuções (desc) e nome. Mesmo cache curto de `/metrics`.
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
    # Teto de 1000 não era defensável: cada execução carregava métricas de
    # todos os seus nós e a tela mostra dezenas de linhas, não mil.
    limit: int = Query(20, ge=1, le=100, description="Últimas N execuções"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    Retorna métricas de um workflow específico.
    Admin acessa qualquer workflow; usuário acessa workflows do(s) seu(s) workspace(s).
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
    Estatísticas por executor na janela pedida, mais presença e capacidade
    atuais. Admin vê todos; usuário vê runs dos seus workspaces. Mesmo cache
    curto de `/metrics`.
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
    """Lista execuções. Admin vê todas; usuário vê runs dos seus workspaces.

    `total` só vem preenchido com `with_total=1`; sem ele a resposta traz
    `has_more`, que é o que o "Ver mais" precisa e não custa um count da tabela.
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
    Detalhes de uma execução. Admin acessa qualquer run;
    usuário acessa runs de workflows no(s) seu(s) workspace(s).
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
    Linha do tempo bruta de eventos de um run (o mesmo replay que o WebSocket
    entrega ao conectar). Permite ao painel de execução reabrir o log de uma
    execução já concluída. Histórico expira em 1h no Redis.
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
    Contagem de execuções por dia, com o dia cortado no fuso `tz` e todos os
    dias da janela presentes (zeros incluídos). Admin vê tudo; usuário vê runs
    dos seus workspaces.
    """
    return await _svc.get_runs_by_day(
        db, current_user, workspace_ids, days,
        workspace_id=workspace_id, workflow_id=workflow_id, tz=tz,
        como_admin=e_admin_global(current_user),
    )
