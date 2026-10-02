# app/services/workspace_service.py
"""
Leitura de workspaces fora de uma request FastAPI.

A listagem "workspaces do usuário" vivia inline em `workspace_router.py`. Um
segundo transporte (o servidor MCP, docs/specs/mcp-server.md) precisa da MESMA
lista — mesma dedup, mesma ordem, mesmo `my_role` — sem passar por `Depends`.
Este módulo é a única implementação; o router só chama.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_OWNER
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace import WorkspaceOut


async def listar_workspaces_do_usuario(db: AsyncSession, user_id: str) -> list[WorkspaceOut]:
    """Workspaces criados pelo usuário + workspaces dos quais é membro, fora da lixeira.

    A ordem é a de sempre: primeiro os que ele é dono (por nome), depois os
    compartilhados (por nome). Dono que também consta como membro aparece uma
    vez só, com `my_role="owner"` — o papel de membro não rebaixa o dono.
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

    # Workspaces como membro (com role)
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

    # Deduplica (owner pode também ser membro) e ordena
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
