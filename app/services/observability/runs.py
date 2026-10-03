# app/services/observability/runs.py
# Business logic and observability queries extracted from the router.
# Contract with the web app: docs/specs/metrics-history.md (§3).


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NODE_STATS_RUN_META_KEY
from app.models.models import Workflow, WorkflowRun
from app.models.user import User
from app.models.workspace import Workspace


from app.services.observability.escopo import _iso
from app.services.observability.frota import _executor_id_do_host, _nomes_de_usuarios, _workspace_names, _resolve_agent_names

# ── Run serialization ─────────────────────────────────────────────────────────

# Columns the run listing actually uses. `select(WorkflowRun)`
# brought the whole entity — including the `node_stats` JSON, which stores the
# per-node stats of every node in the workflow and reaches megabytes — only to read
# `retry_count`, an integer the serialization extracts, with the rest discarded.
# The list's time came to depend on the SIZE of the executed workflows, not
# on the number of rows shown. `retry_count` now comes out via a JSON expression in
# the SQL itself; the blob stays in the database.
_RUN_LIST_COLUMNS = (
    WorkflowRun.task_id,
    WorkflowRun.id,
    WorkflowRun.status,
    WorkflowRun.start_time,
    WorkflowRun.end_time,
    WorkflowRun.duration_seconds,
    WorkflowRun.error_message,
    WorkflowRun.host,
    WorkflowRun.dispatch_tier,
    WorkflowRun.workflow_hash,
    WorkflowRun.workspace_id,
    WorkflowRun.trigger_source,
    WorkflowRun.triggered_by,
    WorkflowRun.error_category,
    WorkflowRun.schedule_id,
    WorkflowRun.node_stats[(NODE_STATS_RUN_META_KEY, "retry_count")]
    .as_integer()
    .label("retry_count"),
)


def _serialize_run(
    r,
    *,
    include_workflow_hash: bool = False,
    include_node_stats: bool = False,
    agent_names: dict | None = None,
    workflow_meta: dict | None = None,
    workspace_names: dict | None = None,
    user_names: dict | None = None,
    admin: bool = False,
) -> dict:
    """Canonical WorkflowRun serialization — avoids duplication across endpoints.

    `workflow_meta`, when present, must be the dict returned by
    `_resolve_workflow_meta` (mapping `workflow_hash -> meta`). From it comes
    `workflow_name` for any user in scope; `workflow_active` and
    `owner_username` only go in with `admin=True` (spec §3.5) — and the default is
    the member view, so that a caller who forgets the argument errs
    on the side of NOT leaking. The
    `workspace_id` is the RUN's (the tenant that actually produced the run), and the
    name comes from `workspace_names`; the workflow meta only serves as the name when
    it points to the same workspace.
    """
    host = r.host or None
    executor_id = _executor_id_do_host(host)
    executor_name = (agent_names or {}).get(executor_id) if executor_id else None
    if executor_id:
        # Historical `agent_host` format ("name@suffix"); the web app has
        # `executor_name` for the friendly text.
        agent_host = f"{executor_name}@{executor_id[-5:]}" if executor_name else host
    else:
        agent_host = host

    # Accepts both the WorkflowRun entity (run detail, which really needs
    # node_stats) and the Row of projected columns from the listings, where
    # `retry_count` already came extracted by the SQL.
    retry_count = getattr(r, "retry_count", None)
    if retry_count is None:
        retry_count = (
            (getattr(r, "node_stats", None) or {})
            .get(NODE_STATS_RUN_META_KEY, {})
            .get("retry_count", 0)
        )

    triggered_by = getattr(r, "triggered_by", None)
    workspace_id = getattr(r, "workspace_id", None)

    out = {
        "run_id":           r.task_id or str(r.id),
        "status":           r.status,
        "started_at":       _iso(r.start_time),
        "finished_at":      _iso(r.end_time),
        "duration_seconds": round(r.duration_seconds, 3) if r.duration_seconds else None,
        "error_message":    r.error_message,
        "retry_count":      retry_count,
        "agent_host":       agent_host,
        # Policy tier it ran in ("primary" | "fallback" | "pool");
        # null in runs older than the column — the screen hides the badge.
        "dispatch_tier":    getattr(r, "dispatch_tier", None),
        # Fields of the History redesign (spec §3.5). Null in runs
        # older than the migration — the web app shows "—".
        "executor_id":      executor_id,
        "executor_name":    executor_name,
        "trigger_source":   getattr(r, "trigger_source", None),
        "triggered_by":     triggered_by,
        "triggered_by_username": (user_names or {}).get(triggered_by) if triggered_by else None,
        "error_category":   getattr(r, "error_category", None),
        "schedule_id":      getattr(r, "schedule_id", None),
        "workspace_id":     workspace_id,
        "workspace_name":   (workspace_names or {}).get(workspace_id) if workspace_id else None,
        # Origin of the WORKFLOW ("usuario" | "assistente"), not of the trigger — it is what
        # paints the assistant badge in the lists. Null when the workflow was
        # permanently deleted (no meta).
        "workflow_origem":  None,
    }
    if include_workflow_hash:
        out["workflow_hash"] = r.workflow_hash
    if include_node_stats:
        out["node_stats"] = {k: v for k, v in (r.node_stats or {}).items() if not k.startswith("__")}

    if workflow_meta is not None:
        meta = workflow_meta.get(r.workflow_hash)
        if meta is not None:
            out["workflow_name"] = meta.get("workflow_name")
            out["workflow_origem"] = meta.get("origem")
            if out["workspace_name"] is None and meta.get("workspace_id") == workspace_id:
                out["workspace_name"] = meta.get("workspace_name")
            if admin:
                out["workflow_active"] = meta.get("workflow_active")
                out["owner_username"] = meta.get("owner_username")

    return out


async def _resolve_workflow_meta(
    db: AsyncSession, workflow_hashes: list[str]
) -> dict[str, dict]:
    """Batch-fetches workflow metadata (name, owner, workspace).

    Avoids N+1 in the run serializer. Returns a dict `{workflow_hash:
    {workflow_name, workflow_active, owner_username, workspace_id,
    workspace_name}}` — keys missing when the workflow was permanently
    deleted. `owner_username` / `workspace_name` can be None in
    legacy data (deleted users). Whoever serializes for a regular user discards the
    admin-only fields (`_serialize_run(admin=False)`).
    """
    hashes = [h for h in set(workflow_hashes) if isinstance(h, str)]
    if not hashes:
        return {}

    # Explicit `select_from(Workflow)`: without it, SQLAlchemy may
    # pick User or Workspace as the base FROM (the select has columns
    # from the 3 tables), making the outerjoins "inverted"
    # and always returning NULL for username/workspace_name.
    result = await db.execute(
        select(
            Workflow.id_hash.label("id_hash"),
            Workflow.name.label("name"),
            Workflow.flag_ative.label("flag_ative"),
            Workflow.workspace_id.label("workspace_id"),
            Workflow.origem.label("origem"),
            User.username.label("owner_username"),
            Workspace.name.label("workspace_name"),
        )
        .select_from(Workflow)
        .outerjoin(User, User.id_hash == Workflow.created_by_id)
        .outerjoin(Workspace, Workspace.id_hash == Workflow.workspace_id)
        .where(Workflow.id_hash.in_(hashes))
    )

    return {
        row.id_hash: {
            "workflow_name":   row.name,
            "workflow_active": bool(row.flag_ative),
            "owner_username":  row.owner_username,
            "workspace_id":    row.workspace_id,
            "workspace_name":  row.workspace_name,
            "origem":          row.origem,
        }
        for row in result.all()
    }


async def _runs_context(db: AsyncSession, runs) -> dict:
    """The four batch lookups that serializing a page of runs
    needs — one SELECT ... IN each (executors, workflows, workspaces,
    users), regardless of the number of rows."""
    return {
        "agent_names":     await _resolve_agent_names(db, runs),
        "workflow_meta":   await _resolve_workflow_meta(db, [r.workflow_hash for r in runs]),
        "workspace_names": await _workspace_names(db, [getattr(r, "workspace_id", None) for r in runs]),
        "user_names":      await _nomes_de_usuarios(db, [getattr(r, "triggered_by", None) for r in runs]),
    }
