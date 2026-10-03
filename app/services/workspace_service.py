# app/services/workspace_service.py
"""
Reading workspaces outside a FastAPI request.

The "user's workspaces" listing used to live inline in `workspace_router.py`. A
second transport (the MCP server, docs/specs/mcp-server.md) needs the SAME
list — same dedup, same order, same `my_role` — without going through
`Depends`. This module is the only implementation; the router just calls it.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_OWNER
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace import WorkspaceOut


async def listar_workspaces_do_usuario(db: AsyncSession, user_id: str) -> list[WorkspaceOut]:
    """Workspaces created by the user + workspaces they are a member of, outside the trash.

    The order is the usual one: first the ones they own (by name), then the
    shared ones (by name). An owner who is also listed as a member appears only
    once, with `my_role="owner"` — the member role does not demote the owner.
    """
    # Workspaces owned
    owned_result = await db.execute(
        select(Workspace)
        .where(
            Workspace.owner_id == user_id,
            Workspace.deleted_at.is_(None),
        )
        .order_by(Workspace.name)
    )
    owned = owned_result.scalars().all()

    # Workspaces as member (with role)
    member_result = await db.execute(
        select(WorkspaceMember.workspace_id, WorkspaceMember.role).where(
            WorkspaceMember.user_id == user_id
        )
    )
    member_rows = member_result.all()
    role_map = {row[0]: row[1] for row in member_rows}
    member_ws_ids = list(role_map.keys())

    shared: list[Workspace] = []
    if member_ws_ids:
        shared_result = await db.execute(
            select(Workspace)
            .where(
                Workspace.id_hash.in_(member_ws_ids),
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.name)
        )
        shared = shared_result.scalars().all()

    # Deduplicates (owner may also be a member) and sorts
    seen: set[str] = set()
    combined: list[WorkspaceOut] = []
    for ws in list(owned) + shared:
        if ws.id_hash not in seen:
            seen.add(ws.id_hash)
            my_role = ROLE_OWNER if ws.owner_id == user_id else role_map.get(ws.id_hash)
            combined.append(WorkspaceOut(
                id_hash=ws.id_hash,
                name=ws.name,
                description=ws.description,
                owner_id=ws.owner_id,
                is_default=ws.is_default,
                my_role=my_role,
            ))

    return combined
