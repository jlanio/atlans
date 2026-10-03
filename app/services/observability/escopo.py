# app/services/observability/escopo.py
# Business logic and observability queries extracted from the router.
# Contract with the web app: docs/specs/metrics-history.md (§3).

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import (
    InvalidDateFormatError,
    WorkflowNotFoundError as _WfNotFound,
    WorkspaceAccessDeniedError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_ADMIN
from app.core.utils.logger import get_logger
from app.models.models import Workflow, WorkflowRun

logger = get_logger(__name__)


# Dashboard numbers do not need to be transactional: a 45s lag is
# invisible on screen and cuts the repeated aggregations of several tabs/users
# looking at the same thing. The "Atualizar" (refresh) button sends `force` and bypasses the cache.
_METRICS_CACHE_TTL = 45


# ── Helpers ───────────────────────────────────────────────────────────────────

def _agora_utc() -> datetime:
    """Current UTC instant, AWARE.

    `WorkflowRun.start_time` is `DateTime(timezone=True)` — timestamptz. A
    NAIVE datetime sent as a bind for timestamptz is not read as UTC: the
    asyncpg codec does `obj.astimezone(utc)`, which on a naive one assumes the
    PROCESS'S LOCAL time zone. Since docker-compose injects `TZ` into the api (.env.example
    has America/Cuiaba, UTC-4), every window of this service reached Postgres
    shifted by 4 hours: the "Execucoes (24h)" card counted only the last 20h and
    left out the whole early morning, with no error at all.
    """
    return datetime.now(timezone.utc)


def _como_utc(valor: datetime) -> datetime:
    """Normalizes a user datetime to AWARE, assuming UTC if it comes without a
    time zone — the same pitfall as `_agora_utc`, now coming from `?date_from=`.

    It also serves what COMES BACK from the database: SQLite (tests, the screenshot
    harness) does not store the time zone and returns naive, which would break the
    subtraction with `_agora_utc()` and send ISO without an offset to the web app.
    """
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)


def _iso(valor: Optional[datetime]) -> Optional[str]:
    return _como_utc(valor).isoformat() if valor else None


def _zona(tz: str) -> ZoneInfo:
    """IANA time zone from `?tz=`. The router already rejects with 422; this is the safety
    net for direct calls to the service."""
    try:
        return ZoneInfo(tz or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        raise InvalidDateFormatError(f"tz inválido: {tz}")


def _e_postgres(db) -> bool:
    """Decides between native PostgreSQL SQL (percentile_cont, AT TIME ZONE) and the
    Python fallback. SQLite comes in for tests and the screenshot harness; it has
    no ordered-set aggregates nor time zones, and is not worth a dialect of its own."""
    try:
        return str(db.bind.dialect.name) == "postgresql"
    except Exception:
        return False


def e_admin_global(user) -> bool:
    """Tells whether the user has the global `admin` role.

    It is the ONLY entry point to the full view: what decides that an admin sees
    everything is the edge (the REST router, via `como_admin=e_admin_global(user)`), and
    not the service. The MCP server (docs/specs/mcp-server.md §6.12) calls the
    same services with the admin `User` and the member view — if the service
    inferred the role from the object itself, an admin PAT would cross the
    token's workspace scope without any line of the MCP having
    allowed it.
    """
    return getattr(user, "role", None) == ROLE_ADMIN


def _wf_filter(user, workspace_ids: List[str], *, como_admin: bool = False) -> list:
    """
    Filter for the Workflow table.
    With `como_admin=True` there is no filter; otherwise the user sees the workflows
    of their workspace(s) — even when `user` has the admin role,
    because the role is only worth what the edge declared (see `e_admin_global`).

    The `OR workspace_id IS NULL` that used to be here was a leak: it handed
    every authenticated user every legacy workflow without a workspace. The column is NOT NULL
    since migration 20260828_0001, so there is nothing left to accommodate.
    """
    if como_admin:
        return []
    return [Workflow.workspace_id.in_(workspace_ids)]


def _run_filter(user, workspace_ids: List[str], *, como_admin: bool = False) -> list:
    """
    Filter for WorkflowRun by the run's OWN workspace.
    With `como_admin=True` there is no filter; the `user`'s role alone is not enough
    (see `e_admin_global`).

    This used to be a subquery over `Workflow.workspace_id` — the workflow's
    CURRENT workspace. Since a workflow can change workspaces (POST
    /workflows/{id}/move), authorizing by the workflow handed the members of the
    new workspace all the history produced in the old one (error_message,
    node_stats, executor host), and took that history away from those who only have
    access to the workspace where it actually happened.

    `WorkflowRun.workspace_id` is written at dispatch and never changes: it is the correct
    historical data, and already indexed. It is also the same criterion the logs
    WebSocket has always used (log_workflows_router) and that artifacts use
    (artifacts_router filters by Artifact.workspace_id).

    The `is_(None)` that accompanied this filter went away along with the column's
    nullability (migration 20260828_0001). It existed to preserve legacy history,
    but the price was handing that history — error_message, node_stats,
    executor host — to any authenticated user. The migration assigns the
    old runs to the correct workspace instead of leaving them public.
    """
    if como_admin:
        return []
    return [WorkflowRun.workspace_id.in_(workspace_ids)]


async def _resolver_escopo(
    db: AsyncSession,
    user,
    workspace_ids: List[str],
    *,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    como_admin: bool = False,
) -> tuple[list, list]:
    """Common filters of spec §3 on top of the tenant scope.

    Returns `(WorkflowRun filters, Workflow filters)`. The requested `workspace_id`
    must be among the user's (403 `workspace_access_denied`) —
    with `como_admin=True` it filters any. The `workflow_id` must exist
    in an accessible workspace; otherwise it is 404, the same as "does not exist", so as
    not to confirm the existence of other tenants' workflows.
    """
    run_f = _run_filter(user, workspace_ids, como_admin=como_admin)
    wf_f = _wf_filter(user, workspace_ids, como_admin=como_admin)

    if workspace_id:
        if not como_admin and workspace_id not in workspace_ids:
            raise WorkspaceAccessDeniedError("Você não tem acesso a este workspace.")
        run_f.append(WorkflowRun.workspace_id == workspace_id)
        wf_f.append(Workflow.workspace_id == workspace_id)

    if workflow_id:
        existe = (await db.execute(
            select(Workflow.id_hash).where(Workflow.id_hash == workflow_id, *wf_f)
        )).scalar_one_or_none()
        if existe is None:
            raise _WfNotFound("Workflow não encontrado.")
        run_f.append(WorkflowRun.workflow_hash == workflow_id)
        wf_f.append(Workflow.id_hash == workflow_id)

    return run_f, wf_f


def _metrics_cache_key(
    prefix: str, user, workspace_ids: List[str], days: int, *, como_admin: bool = False, **filtros,
) -> str:
    """Metrics cache key.

    SEC: the tenant scope is PART of the key. The full view (`como_admin`)
    has its own key, and a regular user is keyed by the exact list of
    workspaces that `Depends(get_user_workspace_ids)` returned. Without that, the
    first request to fill the cache would serve its tenant's numbers to
    everyone. The same admin with and without `como_admin` (REST × MCP) also cannot
    share a key: the "all" response would sit 45 s in the cache and be
    served to a PAT restricted to one workspace.

    The optional filters (workspace_id, workflow_id, tz) also go in: without
    them, the first "all workspaces" request would be served to whoever asked for
    "only workspace X" for the next 45 s.
    """
    # The user goes into the key along with the workspaces: the fleet of the "now" block
    # and of /metrics/executores comes from `get_user_accessible_agents`, which includes
    # executors assigned DIRECTLY to the user — two people with the same
    # workspaces do not necessarily have the same fleet.
    visao = "todos" if como_admin else "membro"
    escopo = f"{visao}:{getattr(user, 'id_hash', '')}:" + ",".join(sorted(workspace_ids))
    chave = f"obs:{prefix}:{hashlib.sha256(escopo.encode()).hexdigest()[:16]}:{days}"
    extra = "&".join(f"{k}={v}" for k, v in sorted(filtros.items()) if v)
    if extra:
        chave += f":{hashlib.sha256(extra.encode()).hexdigest()[:12]}"
    return chave


async def _cache_get(key: str):
    """Reads the cache. Redis being down must never bring down the dashboard."""
    try:
        from app.core.redis import get_redis_pool
        raw = await get_redis_pool().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("Cache de metricas indisponivel na leitura (%s): %s", key, exc)
        return None


async def _cache_set(key: str, value: dict) -> None:
    try:
        from app.core.redis import get_redis_pool
        await get_redis_pool().setex(key, _METRICS_CACHE_TTL, json.dumps(value))
    except Exception as exc:
        logger.debug("Cache de metricas indisponivel na escrita (%s): %s", key, exc)


