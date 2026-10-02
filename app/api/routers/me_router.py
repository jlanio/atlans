# app/api/routers/me_router.py
"""Rotas do escopo "Meu": recortes por PESSOA, entre todos os workspaces dela.

Prefixo próprio `/me` de propósito. `GET /workflows/schedules` seria sombreado
por `GET /workflows/{id_hash}` (o `schedules` cairia como um `id_hash`), e as
rotas de schedule de hoje são aninhadas em `/workflows/{id}/schedules` — por
fluxo, não por pessoa. A listagem transversal do dono não tem casa entre elas.
"""
from typing import List

from fastapi import APIRouter, Depends, Request

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_user_workspace_ids
from app.core.rate_limiter import limiter
from app.models.models import Schedule, Workflow
from app.schemas.me import AgendamentoMeu
from app.services.schedule_service import listar_agendamentos_de

router = APIRouter(prefix="/me", tags=["me"])

# O mesmo teto do acervo da Home (`useAcervo`): o painel do sidebar não
# virtualiza, e uma instalação grande devolveria centenas de linhas por resposta.
LIMITE_PADRAO = 200
LIMITE_MAXIMO = 500


class AgendamentosMeus(BaseModel):
    """Página + TOTAL, o mesmo envelope de `ConversaLista` (`GET /assistente/conversas`).

    O teto sozinho truncava em silêncio: a web recebia 200 linhas e não tinha como
    saber que havia mais. Com o total ela desenha o rodapé "Ver mais" — e o padrão
    de resposta das listas da Home (Chats, Acervo) passa a ser um só.
    """

    itens: List[AgendamentoMeu]
    total: int


@router.get(
    "/schedules",
    response_model=AgendamentosMeus,
    summary="Agendamentos da pessoa, entre todos os seus workspaces",
)
@limiter.limit("60/minute")
async def meus_agendamentos(
    request: Request,
    limit: int = LIMITE_PADRAO,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """Todos os agendamentos dos workspaces do usuário, ativos e pausados,
    ordenados por próxima execução. A escrita (pausar/ativar) continua na rota
    por fluxo `PUT /workflows/{id}/schedules/{job_id}`.

    Paginada e com limiter porque era a única listagem nova sem teto: Chats corta
    em 50, Acervo em 200, e esta devolvia a tabela inteira dos workspaces. O
    `total` vem junto da página para que o teto deixe de ser um truncamento
    invisível — ver `AgendamentosMeus`."""
    itens = await listar_agendamentos_de(
        db,
        workspace_ids,
        limit=max(1, min(int(limit), LIMITE_MAXIMO)),
        offset=max(0, int(offset)),
    )
    return AgendamentosMeus(itens=itens, total=await _contar_agendamentos(db, workspace_ids))


async def _contar_agendamentos(db: AsyncSession, workspace_ids: List[str]) -> int:
    """Quantos agendamentos a página recorta — o MESMO filtro de
    `listar_agendamentos_de` (JOIN com Workflow, não apagado, workspace do ator).

    A contagem mora aqui, e não no serviço, porque é o envelope da ROTA que a
    pede; o filtro é curto o bastante para ser repetido sem risco de divergir
    silenciosamente — qualquer mudança no recorte quebra o teste de paginação.
    """
    if not workspace_ids:
        return 0
    total = (
        await db.execute(
            select(func.count(Schedule.id))
            .join(Workflow, Workflow.id_hash == Schedule.workflow_hash)
            .where(
                Workflow.deleted_at.is_(None),
                Workflow.workspace_id.in_(workspace_ids),
            )
        )
    ).scalar()
    return int(total or 0)
