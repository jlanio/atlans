# app/api/routers/nodes_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.schemas.node import NodeDefinition
from app.services.node_service import NodeService

router = APIRouter(
    prefix="/nodes",
    tags=["nodes"]
)

def get_node_service() -> NodeService:
    """Dependency to create NodeService."""
    return NodeService()

@router.get("", response_model=List[NodeDefinition])
async def list_nodes(
    service: NodeService = Depends(get_node_service),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Lists all registered nodes, with their configurable properties.
    Nodes disabled by the admin (/admin/nodes) are filtered out here.
    """
    return await service.list_nodes(db)


# ── Proxy WFS GetCapabilities (evita bloqueio CORS no browser) ────────────────

def _validate_wfs_url(url: str) -> str:
    """Validates the URL against SSRF before making a server-side request."""
    from flow.utils.geo_helpers import validate_url_ssrf
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL inválida. Use http:// ou https://.")
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL excede o limite de 2048 caracteres.")
    try:
        validate_url_ssrf(url)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=f"URL bloqueada por segurança: {exc}")
    return url


async def _workspace_do_fluxo(db, workflow_id: str) -> str:
    """The workspace of the workflow being edited — 404 if it does not exist
    (or is in the trash). The client names the WORKFLOW, which is what the editor
    has at hand, and the server derives the workspace from it; the reach is that
    of the requester in that workspace (the same rule as Run). The server has no
    way to tie the listing to the node being edited: whoever can run in a workspace
    reaches the credentials shared with it through any workflow there."""
    from sqlalchemy import select

    from app.models.workflow import Workflow

    workspace_id = (await db.execute(
        select(Workflow.workspace_id).where(Workflow.id_hash == workflow_id, Workflow.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not workspace_id:
        raise HTTPException(status_code=404, detail="Fluxo não encontrado.")
    return workspace_id


async def _credencial_do_wfs(credential_id: str, workflow_id: str | None, user_id: str):
    """The WFS node's credential, ready to sign the GetCapabilities — or 4xx.

    The scope is the SAME as definition validation (`validate_service`): the
    requester's credentials and, when they give the workflow and can run in its
    workspace (operator or above), those shared with that workspace.
    Never another member's PRIVATE credential, even with its id on the node — the
    listing cannot reach what that person's Run does not reach.
    """
    from uuid import UUID

    from app.core.authorization.credential_loader import resolve_credentials_from_ids
    from app.core.authorization.workflow_access import get_workspace_member_role, tem_papel_minimo
    from app.core.db import get_session_async
    from app.core.rbac import ROLE_OPERATOR
    from app.services.credential_resolver import http_auth_da_credencial
    from flow.utils.credencial_wfs import autenticacao_wfs

    try:
        # The canonical form is the key of what the resolver returns.
        credential_id = str(UUID(credential_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="credential_id inválido.")

    compartilhado = None
    async with get_session_async() as db:
        if workflow_id:
            workspace_id = await _workspace_do_fluxo(db, workflow_id)
            papel = await get_workspace_member_role(db, workspace_id, user_id)
            if papel is None:
                raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
            if tem_papel_minimo(papel, ROLE_OPERATOR):
                compartilhado = workspace_id
        resolvidas = await resolve_credentials_from_ids(
            [credential_id], allowed_owner_ids={user_id}, shared_workspace_id=compartilhado, db=db,
        )
        await db.commit()  # the `last_used_at` stamp: listing with it is using it

    cred = resolvidas.get(credential_id)
    if cred is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "A credencial deste nó não está ao seu alcance: é de outra pessoa (as "
                "compartilhadas com o workspace só valem para quem pode executar nele), expirou "
                "ou foi apagada. Escolha uma sua para listar as camadas."
            ),
        )
    try:
        # A database credential does not become `http_auth`; the type is enough for the refusal.
        return autenticacao_wfs(None, http_auth_da_credencial(cred) or {"type": cred.get("type") or "?"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/wfs/layers", summary="Lista camadas de um servidor WFS")
async def wfs_discover_layers(
    url: str = Query(..., description="URL base do serviço WFS"),
    credential_id: str | None = Query(
        None, description="Credencial do nó (GeoServer authkey ou usuário e senha), para listar as camadas protegidas",
    ),
    workflow_id: str | None = Query(
        None, description="O fluxo em edição — alcança as credenciais compartilhadas com o workspace dele",
    ),
    user=Depends(get_current_user),
):
    """Proxy for GetCapabilities — returns the list of available layers.

    The body is the usual one (`{layers: [{name, title}]}`, sorted by title) and
    so are the statuses (400 invalid URL, 403 SSRF, 502 server/error, 504
    timeout, 404 no layers). The work lives in
    `app.services.fontes_service.listar_camadas_wfs`, which is the SAME probe
    the source catalog uses — the route is a thin wrapper.

    With `credential_id`, it lists as the node's run would see: a GeoServer
    hides protected layers from anonymous users. A credential outside the
    requester's reach is 403, and one of a type that does not serve WFS is 400 — never
    an anonymous listing in its place. `workflow_id` (the workflow being edited) extends
    the reach to the credentials shared with ITS workspace, for those who can run
    there; a nonexistent workflow is 404 and a workflow from someone else's workspace is 403.

    Protections (all in the service):
    - Normalizes the URL: discards query/fragment from the input
    - SSRF validation (blocks private, loopback, link-local IPs)
    - Response size limit and timeout
    - Requires JWT authentication
    """
    from flow.utils.credencial_wfs import sem_segredo
    from flow.utils.geo_helpers import normalize_ows_endpoint_url
    from app.services import fontes_service

    url = normalize_ows_endpoint_url(url)
    _validate_wfs_url(url)
    auth = await _credencial_do_wfs(credential_id, workflow_id, user.id_hash) if credential_id else None
    try:
        layers = await fontes_service.listar_camadas_wfs(url, auth=auth)
    except fontes_service.SondagemError as exc:
        status, detail = exc.como_http()
        raise HTTPException(status_code=status, detail=sem_segredo(detail, auth)) from None
    return {"layers": layers}
