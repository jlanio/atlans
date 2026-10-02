# app/api/routers/api_tokens_router.py
"""
Tokens pessoais de acesso do usuário autenticado — /auth/tokens.

Só a sessão JWT cria, lista e revoga tokens (um PAT nunca gerencia PATs). O
segredo aparece uma vez, na resposta do POST. Revogar é marcar, não apagar:
o token continua na lista como "revogado" para o usuário saber o que existiu.

Os 422 do POST chegam em dois formatos, de propósito: nome, escopos, validade
e lista vazia caem no schema (`validation_error`, com `details`, como toda
rota do repo); o service revalida com as mesmas frases (defesa em
profundidade), mas o único 422 de domínio que de fato sai daqui é
`api_token_invalid` para "workspace de que o usuário não participa" — esse
precisa do banco.
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
    """Cria um token pessoal. O segredo (`token`) aparece UMA única vez nesta resposta."""
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
    """Revoga (não apaga) um token do próprio usuário. Idempotente."""
    token = await svc.revogar(db, current_user.id_hash, id_hash)
    return ApiTokenOut.de_modelo(token, utc_now_naive())
