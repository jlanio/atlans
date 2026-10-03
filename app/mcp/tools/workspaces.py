# app/mcp/tools/workspaces.py
"""Workspace tools. The guards for each one are in app/mcp/guardas.py."""
from __future__ import annotations

from mcp.server.mcpserver import Context
from mcp_types import ToolAnnotations

from app.mcp import infra
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.saida import envelope
from app.mcp.tools.base import ferramenta
from app.services.workspace_service import listar_workspaces_do_usuario


@ferramenta
async def list_workspaces(ctx: Context) -> dict:
    """Lists the workspaces this token reaches.

    It is the first call of almost every conversation: the other `workspace_id`
    parameters accept the id from here (or the name, when there are no
    duplicates).

    Filtering by the token's reach is done here, over the user's list: a token
    restricted to one workspace does not reveal even the names of the others,
    even if the owner is a member of them.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        todos = await listar_workspaces_do_usuario(db, escopo.user_id)

    itens = [
        envelope(
            {
                "id": ws.id_hash,
                "my_role": ws.my_role,
                "is_default": bool(ws.is_default),
            },
            name=ws.name,
            description=ws.description,
        )
        for ws in todos
        if ws.id_hash in escopo.workspace_ids
    ]
    return {
        "items": itens,
        "total": len(itens),
        "all_workspaces_token": escopo.todos_os_workspaces,
    }


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_workspaces",
        title="Listar workspaces",
        description=(
            "Lista os workspaces que este token alcança, com o papel do dono do token "
            "em cada um. Use o `id` devolvido aqui no parâmetro `workspace_id` das "
            "demais ferramentas."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )(list_workspaces)
