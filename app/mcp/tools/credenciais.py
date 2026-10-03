# app/mcp/tools/credenciais.py
"""Credential tools. The guards for each one are in app/mcp/guardas.py."""
from __future__ import annotations

from mcp.server.mcpserver import Context

from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolve_workspace
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.services.credential_service import list_credential_metadata


@ferramenta
async def list_credentials(ctx: Context, workspace_id: str | None = None) -> dict:
    """Lists the credentials the token's owner can use — metadata only.

    The `data` field (where password, token and connection string live) NEVER
    leaves here, not even encrypted: what a definition needs is the identifier,
    and that is what gets delivered. Whoever builds a workflow references the
    credential by `id`; the secret stays only on the server, resolved at run
    time.

    What appears: the token owner's own credentials and those shared with the
    workspaces the token reaches. A credential shared with a workspace outside
    the token's reach is not included, even if the owner sees it through the
    application — the token is the narrower restriction, and it wins.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    alcance = sorted(escopo.workspace_ids)
    if not alcance:
        # Refuse early, with the same sentence as `resolve_workspace`. It is
        # not redundant zeal: `list_credential_metadata` understands
        # `workspace_ids=None` as "no workspace filter" and would return all of
        # the owner's credentials. A token that reaches no workspace cannot be
        # the only one to answer with data.
        raise erro(
            "forbidden",
            "Este token não alcança nenhum workspace.",
            "peça acesso a um workspace, ou crie em /settings/tokens um token sem "
            "restrição de workspace (hoje, página só de administradores do sistema)",
        )

    async with infra.sessao() as db:
        alvo = (
            await resolve_workspace(db, escopo, workspace_id)
            if workspace_id is not None
            else None
        )
        # `owner_id` is required on every call: without it the CRUD lists with
        # NO scope filter — every credential in the installation.
        credenciais = await list_credential_metadata(
            db, owner_id=escopo.user_id, workspace_ids=alcance
        )
        brutas = [
            {
                # The `id` the definition carries in `credential_id` is the primary
                # key — the same one the screen saves and the resolver looks up
                # (`Credential.id`). The `id_hash` is another, independent
                # UUID: handing it over here made every credential chosen by
                # the assistant fail at resolution.
                "id": str(c.id),
                "type": c.type,
                "owner_id": c.owner_id,
                "workspace_id": c.workspace_id,
                "expires_at": iso(c.expires_at),
                "last_used_at": iso(c.last_used_at),
                "name": c.name,
                "description": c.description,
            }
            for c in credenciais
        ]

    itens = []
    for c in brutas:
        ws = c["workspace_id"]
        if ws is not None and ws not in escopo.workspace_ids:
            continue
        # With a workspace requested, what remains are the ones shared with it
        # and the owner's private ones — the latter apply in any workspace,
        # and omitting them would hide precisely the credential the workflow
        # is going to use.
        if alvo is not None and ws is not None and ws != alvo:
            continue
        itens.append(
            envelope(
                {
                    "id": c["id"],
                    "type": c["type"],
                    "owner_id": c["owner_id"],
                    "workspace_id": ws,
                    "expires_at": c["expires_at"],
                    "last_used_at": c["last_used_at"],
                    "mine": c["owner_id"] == escopo.user_id,
                    "shared": ws is not None,
                },
                name=c["name"],
                description=c["description"],
            )
        )

    return {"items": itens, "total": len(itens)}


def registrar(server) -> None:
    """Registers this domain's tools."""
    server.tool(
        name="list_credentials",
        title="Listar credenciais",
        description=(
            "Lista as credenciais disponíveis (apenas metadados: id, tipo, dono, "
            "workspace e validade). O conteúdo secreto nunca é devolvido — use o `id` "
            "na propriedade de credencial do nó."
        ),
        annotations=anotacoes("list_credentials"),
    )(list_credentials)
