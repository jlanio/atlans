# app/core/authorization/workflow_access.py
"""
Authorization of workflows and workspaces — the home of the guards, without FastAPI `Depends`.

Until now the access rules (the resource's workspace, minimum role, deleted
workflow) lived only in the REST dependencies and routers. A second
transport — the MCP server (docs/specs/mcp-server.md §1) — needs the
SAME rules without going through a FastAPI request. This module is the only
implementation; `app/api/dependencies.py` imports from here and re-exports the old
names, so no router changes.

The responses are still `HTTPException` with the usual statuses and messages —
MCP translates them into its tool error. Divergences that exist on
purpose and are preserved:
- a nonexistent or deleted (`deleted_at`) workflow is a 404 BEFORE any 403
  (does not reveal whether the id exists in another workspace);
- `verify_workspace_access` gives 403 (not 404) for a resource without a workspace;
- a run (`WorkflowRun`) is authorized by the RUN'S workspace, not the workflow's
  current one — a moved workflow does not hand the old history to the new workspace;
- `owner` is above `admin` in the workspace hierarchy.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowNotFoundError
from app.core.rbac import ROLE_OWNER
from app.models.workspace import Workspace

# ── Workspace roles ───────────────────────────────────────────────────────────

WORKSPACE_ROLE_ORDER: List[str] = ["viewer", "editor", "operator", "admin", ROLE_OWNER]


def _has_min_workspace_role(actual: Optional[str], minimum: str) -> bool:
    """True if `actual` >= `minimum` in the workspace role hierarchy."""
    if actual is None:
        return False
    try:
        return WORKSPACE_ROLE_ORDER.index(actual) >= WORKSPACE_ROLE_ORDER.index(minimum)
    except ValueError:
        return False


tem_papel_minimo = _has_min_workspace_role


def exigir_papel(role: Optional[str], minimo: str, mensagem: Optional[str] = None) -> None:
    """403 if the role does not reach the minimum. The message is the route's, when it has its own.

    Every route role comparison goes through here: REST via the
    `workflow_com_papel` dependency and via `exigir_papel_no_workspace`, MCP directly.
    """
    if not _has_min_workspace_role(role, minimo):
        raise HTTPException(
            status_code=403,
            detail=mensagem or f"Requer role '{minimo}' ou superior.",
        )


# ── Pertencimento a workspace ─────────────────────────────────────────────────


def verify_workspace_access(resource_workspace_id: Optional[str], user_workspace_ids: List[str]) -> None:
    """
    Raises HTTP 403 if the resource does not belong to any of the user's workspaces.
    Resources without a workspace_id are blocked — they must be migrated to have an explicit workspace.
    """
    if not resource_workspace_id:
        raise HTTPException(
            status_code=403,
            detail="Recurso sem workspace associado. Contate o administrador para migração.",
        )
    if resource_workspace_id not in user_workspace_ids:
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")


async def listar_workspace_ids(db: AsyncSession, user_id: str) -> List[str]:
    """id_hash of the workspaces accessible to the user: owner OR member, never from the trash.

    ONE query instead of two round-trips. Members survive the soft delete (the FK
    CASCADE only fires on purge), so the `deleted_at` filter on the outer
    Workspace covers both cases — otherwise a workspace in the trash would keep
    granting access to artifacts, Drive and logs.
    """
    from app.models.workspace_member import WorkspaceMember

    resultado = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.deleted_at.is_(None),
            or_(
                Workspace.owner_id == user_id,
                Workspace.id_hash.in_(
                    select(WorkspaceMember.workspace_id).where(
                        WorkspaceMember.user_id == user_id,
                    )
                ),
            ),
        )
    )
    return [row[0] for row in resultado.all()]


async def get_workspace_member_role(
    db: AsyncSession, workspace_id: str, user_id: str
) -> Optional[str]:
    """
    Returns the user's effective role in the workspace:
    - "owner" if they own the workspace
    - the WorkspaceMember role if they are a member
    - None if they have no access (or if the workspace is in the trash)
    """
    from app.models.workspace_member import WorkspaceMember

    ws_result = await db.execute(
        select(Workspace.owner_id).where(
            Workspace.id_hash == workspace_id,
            Workspace.deleted_at.is_(None),
        )
    )
    owner_id = ws_result.scalar_one_or_none()
    if owner_id is None:
        return None
    if owner_id == user_id:
        return ROLE_OWNER

    member_result = await db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return member_result.scalar_one_or_none()


async def exigir_papel_no_workspace(
    db: AsyncSession,
    workspace_id: Optional[str],
    user_id: str,
    minimo: str,
    mensagem: Optional[str] = None,
) -> str:
    """The user's role in the workspace — or 403 if it does not reach `minimo`.

    It is the "fetch the role + compare" pair of the routes whose workspace comes from the body or
    from the resource (groups, members, artifacts, Drive, workflow creation): written
    by hand, it was repeated route after route, and a forgotten copy is a route without a
    role check. A non-member (or a nonexistent workspace, or one in the trash) falls into the
    same 403 — `get_workspace_member_role` returns None in all three, and distinguishing them
    would allow enumerating other people's workspaces by id.

    Routes that load a WORKFLOW from the path use the
    `workflow_com_papel` dependency (app/api/dependencies.py), which also gives the 404 first.
    """
    papel = await get_workspace_member_role(db, workspace_id, user_id)
    exigir_papel(papel, minimo, mensagem)
    return papel


# ── Workflows and runs ────────────────────────────────────────────────────────


async def carregar_workflow_acessivel(
    service,
    db: AsyncSession,
    id_hash: str,
    user_id: str,
    *,
    decifrar: bool = True,
    aceitar_sem_papel: bool = False,
) -> Tuple[object, Optional[str]]:
    """(workflow, role) — or 404 if it does not exist/is deleted, 403 if the user is not in the workspace.

    `service` is a `WorkflowService`. With `decifrar=True` (REST) the workflow comes
    from `get_workflow_by_hash`, which decrypts the `connectionString`s and
    assigns them into `wf.definition`. With `decifrar=False` it comes raw from `crud.get_by_hash`:
    it is the path for callers that will only read metadata, redact the definition or execute —
    nobody needs the secret in clear text in the session, and a decrypted definition
    attached to a dirty ORM object is exactly what an accidental flush would leak. The
    access rules are the same on both paths.

    The 404-before-403 order is deliberate: it does not reveal whether the id exists in another
    workspace.
    """
    if decifrar:
        try:
            wf = await service.get_workflow_by_hash(id_hash)
        except WorkflowNotFoundError:
            raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    else:
        wf = await service.crud.get_by_hash(id_hash)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    if wf.deleted_at is not None:
        raise HTTPException(status_code=404, detail=f"Workflow '{id_hash}' não encontrado")
    role = await get_workspace_member_role(db, wf.workspace_id, user_id)
    if role is None:
        # A member of a workspace WITHOUT an owner (`owner_id` null: old or hand-edited
        # data) has no role, because `get_workspace_member_role` exits early without
        # an owner. But they belong to the workspace, as `listar_workspace_ids` says, and the
        # listing shows them the workflow. With `aceitar_sem_papel` (REST), they
        # get (wf, None): reading goes through, and every route with a minimum role
        # refuses them, as before the single guard.
        if aceitar_sem_papel and wf.workspace_id in await listar_workspace_ids(db, user_id):
            return wf, None
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
    return wf, role


async def papel_no_workspace_do_run(db: AsyncSession, run, user_id: str) -> Optional[str]:
    """The user's role in the workspace where the run actually ran (`run.workspace_id`).

    It is the criterion for canceling/viewing a run: a workflow may have been moved
    after the trigger, and whoever controls the new workspace has no say over the old
    one's history. No global admin bypass — anyone who wants that shortcut does it in the
    route, explicitly, as today.
    """
    return await get_workspace_member_role(db, run.workspace_id, user_id)
