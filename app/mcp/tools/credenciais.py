# app/mcp/tools/credenciais.py
"""Tools de credenciais. As guardas de cada uma estão em app/mcp/guardas.py."""
from __future__ import annotations

from mcp.server.mcpserver import Context

from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import resolver_workspace
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.services.credential_service import list_credential_metadata


@ferramenta
async def list_credentials(ctx: Context, workspace_id: str | None = None) -> dict:
    """Lista as credenciais que o dono do token pode usar — só os metadados.

    O campo `data` (onde moram senha, token e string de conexão) NUNCA sai daqui,
    nem cifrado: o que uma definição precisa é o identificador, e é isso que se
    entrega. Quem monta um fluxo referencia a credencial por `id`; o segredo
    continua só no servidor, resolvido na hora da execução.

    O que aparece: as credenciais do próprio dono do token e as compartilhadas
    com os workspaces que o token alcança. Uma credencial compartilhada com um
    workspace fora do alcance do token não entra, mesmo que o dono a enxergue
    pela aplicação — o token é a restrição mais estreita, e ela vence.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    alcance = sorted(escopo.workspace_ids)
    if not alcance:
        # Recusa cedo, com a mesma frase de `resolver_workspace`. Não é zelo
        # redundante: `list_credential_metadata` entende `workspace_ids=None`
        # como "sem filtro de workspace" e devolveria as credenciais do dono
        # inteiras. Um token que não alcança workspace nenhum não pode ser o
        # único a responder com dados.
        raise erro(
            "forbidden",
            "Este token não alcança nenhum workspace.",
            "peça acesso a um workspace, ou crie em /settings/tokens um token sem "
            "restrição de workspace (hoje, página só de administradores do sistema)",
        )

    async with infra.sessao() as db:
        alvo = (
            await resolver_workspace(db, escopo, workspace_id)
            if workspace_id is not None
            else None
        )
        # `owner_id` é obrigatório em toda chamada: sem ele o CRUD lista SEM
        # filtro de escopo — todas as credenciais da instalação.
        credenciais = await list_credential_metadata(
            db, owner_id=escopo.user_id, workspace_ids=alcance
        )
        brutas = [
            {
                # O `id` que a definição leva em `credential_id` é a chave
                # primária — a mesma que a tela grava e que o resolver procura
                # (`Credential.id`). O `id_hash` é outro UUID, independente:
                # entregá-lo aqui fazia toda credencial escolhida pelo
                # assistente falhar na resolução.
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
        # Com um workspace pedido, ficam as compartilhadas com ele e as privadas
        # do dono — estas valem em qualquer workspace, e omiti-las esconderia
        # justamente a credencial que o fluxo vai usar.
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
    """Registra as tools deste domínio."""
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
