# app/api/routers/api_tokens_router.py
"""
Personal access tokens of the authenticated user — /auth/tokens.

Only the JWT session creates, lists and revokes tokens (a PAT never manages PATs). The
secret appears once, in the POST response. Revoking is marking, not deleting:
the token stays in the list as "revogado" (revoked) so the user knows what existed.

The POST's 422s come in two formats, on purpose: name, scopes, validity
and empty list fall to the schema (`validation_error`, with `details`, like every
route in the repo); the service revalidates with the same sentences (defense in
depth), but the only domain 422 that actually comes out of here is
`api_token_invalid` for "a workspace the user does not belong to" — that one
needs the database.
"""
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.rate_limiter import limiter
from app.core.utils.datetime_utils import utc_now_naive
from app.schemas.api_token import ApiTokenCreate, ApiTokenCreated, ApiTokenOut
from app.services import api_token_service as svc

router = APIRouter(
    prefix="/auth/tokens",
    tags=["auth"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=ApiTokenCreated, status_code=201, summary="Criar token de acesso")
@limiter.limit("10/hour")
async def criar_token(
    request: Request,
    payload: ApiTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Creates a personal token. The secret (`token`) appears only ONCE, in this response."""
    token, segredo = await svc.criar(
        db,
        current_user,
        name=payload.name,
        scopes=payload.scopes,
        workspace_ids=payload.workspace_ids,
        expires_in_days=payload.expires_in_days,
    )
    return ApiTokenCreated.com_segredo(token, segredo, utc_now_naive())


@router.get("", response_model=List[ApiTokenOut], summary="Listar tokens de acesso")
async def listar_tokens(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    agora = utc_now_naive()
    return [ApiTokenOut.de_modelo(t, agora) for t in await svc.listar(db, current_user.id_hash)]


@router.delete("/{id_hash}", response_model=ApiTokenOut, summary="Revogar token de acesso")
async def revogar_token(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revokes (does not delete) one of the user's own tokens. Idempotent."""
    token = await svc.revogar(db, current_user.id_hash, id_hash)
    return ApiTokenOut.de_modelo(token, utc_now_naive())
