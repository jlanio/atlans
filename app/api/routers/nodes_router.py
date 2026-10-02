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
    """Dependência para criar NodeService."""
    return NodeService()

@router.get("", response_model=List[NodeDefinition])
async def list_nodes(
    service: NodeService = Depends(get_node_service),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Lista todos os nodes registrados, com suas properties configuráveis.
    Nodes desabilitados pelo admin (/admin/nodes) sao filtrados aqui.
    """
    return await service.list_nodes(db)


# ── Proxy WFS GetCapabilities (evita bloqueio CORS no browser) ────────────────

def _validate_wfs_url(url: str) -> str:
    """Valida URL contra SSRF antes de fazer request server-side."""
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
    """O workspace do fluxo que está sendo editado — 404 se ele não existe
    (ou está na lixeira). O cliente nomeia o FLUXO, que é o que o editor tem
    em mãos, e o servidor tira dele o workspace; o alcance é o de quem pede
    nesse workspace (a mesma regra do Executar). O servidor não tem como
    prender a listagem ao nó em edição: quem pode executar num workspace
    alcança as credenciais compartilhadas com ele por qualquer fluxo de lá."""
    from sqlalchemy import select

    from app.models.workflow import Workflow

    workspace_id = (await db.execute(
        select(Workflow.workspace_id).where(Workflow.id_hash == workflow_id, Workflow.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not workspace_id:
        raise HTTPException(status_code=404, detail="Fluxo não encontrado.")
    return workspace_id


async def _credencial_do_wfs(credential_id: str, workflow_id: str | None, user_id: str):
    """A credencial do nó WFS, pronta para assinar o GetCapabilities — ou 4xx.

    O escopo é o MESMO da validação de definição (`validate_service`): as
    credenciais de quem pede e, quando ele informa o fluxo e pode executar no
    workspace dele (operator ou acima), as compartilhadas com esse workspace.
    Nunca a credencial PRIVADA de outro membro, mesmo com o id dela no nó — a
    listagem não pode alcançar o que o Executar dessa pessoa não alcança.
    """
    from uuid import UUID

    from app.core.authorization.credential_loader import resolve_credentials_from_ids
    from app.core.authorization.workflow_access import get_workspace_member_role, tem_papel_minimo
    from app.core.db import get_session_async
    from app.core.rbac import ROLE_OPERATOR
    from app.services.credential_resolver import http_auth_da_credencial
    from flow.utils.credencial_wfs import autenticacao_wfs

    try:
        # A forma canônica é a chave do que o resolver devolve.
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
        await db.commit()  # o carimbo de `last_used_at`: listar com ela é usá-la

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
        # Uma credencial de banco não vira `http_auth`; o tipo basta para a recusa.
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
    """Proxy para GetCapabilities — retorna lista de camadas disponíveis.

    O corpo é o de sempre (`{layers: [{name, title}]}`, ordenado por título) e
    os status também (400 URL inválida, 403 SSRF, 502 servidor/erro, 504
    timeout, 404 sem camadas). O trabalho mora em
    `app.services.fontes_service.listar_camadas_wfs`, que é a MESMA sondagem
    que o catálogo de fontes usa — a rota é um wrapper fino.

    Com `credential_id`, lista como a execução do nó veria: um GeoServer
    esconde do anônimo as camadas protegidas. Credencial fora do alcance de
    quem pede é 403, e de tipo que não serve ao WFS é 400 — nunca uma listagem
    anônima no lugar. `workflow_id` (o fluxo em edição) estende o alcance às
    credenciais compartilhadas com o workspace DELE, para quem pode executar
    ali; fluxo inexistente é 404 e fluxo de um workspace alheio é 403.

    Proteções (todas no serviço):
    - Normaliza URL: descarta query/fragment do input
    - Validação SSRF (bloqueia IPs privados, loopback, link-local)
    - Limite de tamanho da resposta e timeout
    - Requer autenticação JWT
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
