# app/api/routers/admin_assistente_router.py
"""Trocar o modelo do assistente — com o catálogo do provedor na frente.

O `GET` devolve o modelo em uso e o catálogo do provedor (com o preço de cada
modelo, quando ele informa); o `PUT` troca o modelo, depois de sondá-lo.

Uma extensão pode somar campos ao painel (`Registro.painel_do_modelo`, em
`app/extensoes`): os planos pagos somam a cota de cada plano e o custo de cada
opção, porque ali trocar de modelo muda a economia dos planos. Os parâmetros da
URL que o núcleo não conhece chegam a ela intactos.

Só admin (`require_admin` no router inteiro), e a página que consome isto é
`/dashboard/admin/settings` — a rota do painel, que quem administra alcança.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_admin
from app.core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from app.core.utils.logger import get_logger
from app.extensoes import registro
from app.mcp import infra
from app.services import assistente_config_service as config_svc
from app.services import openrouter

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/assistente",
    tags=["admin-assistente"],
    dependencies=[Depends(require_admin)],
)


class ModeloDoCatalogo(BaseModel):
    id: str
    nome: str
    # `None`, e nunca 0: um modelo sem preço conhecido não pode aparecer como
    # gratuito numa tabela de custo — é a leitura que faria escolher errado.
    entrada_por_milhao: Optional[float] = None
    saida_por_milhao: Optional[float] = None
    contexto: Optional[int] = None


class SituacaoDoModelo(BaseModel):
    modelo: str
    origem: Literal["banco", "ambiente"]
    definido_por: Optional[str] = None
    definido_em: Optional[str] = None
    padrao_do_ambiente: str


class PainelDoModelo(BaseModel):
    # `allow`: os campos que uma extensão soma ao painel (os planos somam
    # `cota`, `custos`, `fatia_de_saida`, `dias_da_janela` e `dias_de_lastro`).
    model_config = ConfigDict(extra="allow")

    atual: SituacaoDoModelo
    catalogo: list[ModeloDoCatalogo]
    catalogo_indisponivel: Optional[str] = Field(
        default=None,
        description="Motivo de o catálogo ter vindo vazio — o provedor fora do ar não "
                    "pode derrubar a tela inteira, mas a tela precisa dizer o que houve",
    )


class TrocaDeModelo(BaseModel):
    """`extra=forbid`: nada além do id entra por aqui. Preço e teto são do
    servidor, e aceitar um campo desconhecido em silêncio é o primeiro passo
    para alguém tentar mandar um deles."""

    model_config = ConfigDict(extra="forbid")

    # `None` volta ao padrão do ambiente — é o «voltar ao padrão» da tela.
    modelo: Optional[str] = None


async def montar_painel(
    db: AsyncSession, *, simular: str | None, consulta: Mapping[str, str],
) -> PainelDoModelo:
    """O painel: o modelo em uso e o catálogo, mais o que cada extensão soma.

    `consulta` são os parâmetros da URL; o núcleo só lê `simular`, e o resto é
    das extensões.
    """
    atual = await config_svc.situacao(db=db)

    catalogo: list[dict[str, Any]] = []
    falha: str | None = None
    if OPENROUTER_API_KEY:
        try:
            catalogo = await openrouter.listar_modelos(base_url=OPENROUTER_BASE_URL, chave=OPENROUTER_API_KEY)
        except Exception as exc:
            # Provedor fora do ar não pode derrubar a tela: o admin ainda
            # precisa ver o que está em uso e poder voltar ao padrão.
            logger.warning("Assistente: falha ao listar modelos (%s).", exc.__class__.__name__)
            falha = exc.__class__.__name__
    else:
        falha = "sem_credencial"

    extras: dict[str, Any] = {}
    for contribuicao in registro().painel_do_modelo:
        extras.update(await contribuicao(
            db, atual=atual, catalogo=catalogo, simular=simular, consulta=consulta,
        ))

    return PainelDoModelo(
        atual=SituacaoDoModelo(**atual),
        catalogo=[ModeloDoCatalogo(**m) for m in catalogo],
        catalogo_indisponivel=falha,
        **extras,
    )


@router.get("/modelo", response_model=PainelDoModelo, summary="Modelo em uso e catálogo")
async def painel(
    request: Request,
    simular: Optional[str] = Query(
        default=None,
        description="Recalcula o que depende do modelo (o custo, com os planos) com este, sem salvar nada",
    ),
    db: AsyncSession = Depends(get_db),
):
    return await montar_painel(db, simular=simular, consulta=request.query_params)


async def _sondar_ou_400(modelo: str | None) -> None:
    """Uma chamada real ao provedor antes de gravar a escolha.

    **O catálogo lista o que EXISTE, não o que serve.** Entre as centenas de
    modelos do provedor há variantes que o endpoint de conversa recusa por
    inteiro (as `:batch`), modelos sem ferramentas — e o assistente manda as 42
    em toda chamada — e modelos cujo teto de saída é menor que o nosso. Salvar
    um deles derrubava o assistente para TODOS os usuários com um genérico
    «não consegui falar com o modelo», enquanto quem trocou não via nada. Era
    a tela oferecendo escolhas que não podiam funcionar.

    A sonda tem a forma do pedido real, então a recusa do provedor chega a
    quem está trocando, com as palavras dele, no momento do clique.

    **`None` não é sondado**, e isso é deliberado: é o «voltar ao padrão do
    ambiente», a saída de emergência. Se o provedor estiver fora do ar, essa
    saída tem de continuar aberta — sondá-la trancaria a porta justamente na
    hora em que ela é necessária.

    Qualquer falha da sonda BLOQUEIA a troca, inclusive um tempo esgotado. O
    erro caro é o outro: deixar passar um modelo não verificado quebra o
    produto para todo mundo, enquanto barrar uma troca legítima durante uma
    instabilidade custa tentar de novo daqui a pouco. A mensagem separa os dois
    casos para o admin saber qual é.
    """
    if modelo is None:
        return
    if not OPENROUTER_API_KEY:
        # Sem credencial não há o que sondar — e a tela já anuncia que o
        # catálogo não veio. Barrar aqui impediria de configurar o modelo antes
        # da chave, que é uma ordem legítima de instalação.
        return
    from app.core.config import ASSISTENTE_ATRIBUICAO, FRONTEND_URL
    from app.services.assistente_service import ESFORCO_DO_RACIOCINIO, MAX_TOKENS

    try:
        await openrouter.sondar_modelo(
            modelo,
            chave=OPENROUTER_API_KEY,
            max_tokens=MAX_TOKENS,
            esforco=ESFORCO_DO_RACIOCINIO,
            base_url=OPENROUTER_BASE_URL,
            referer=(FRONTEND_URL or None) if ASSISTENTE_ATRIBUICAO else None,
            titulo="Atlans" if ASSISTENTE_ATRIBUICAO else None,
        )
    except openrouter.ErroDoOpenRouter as exc:
        logger.warning("Assistente: sonda recusou o modelo %s — %s", modelo, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"O provedor recusou «{modelo}»: {exc}. O modelo não foi salvo — "
                "o assistente continua no que estava."
            ),
        ) from exc
    except Exception as exc:
        logger.warning("Assistente: sonda do modelo %s falhou (%s).", modelo, exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Não deu para conferir «{modelo}» com o provedor agora "
                f"({exc.__class__.__name__}). O modelo não foi salvo — tente de novo em "
                "alguns instantes."
            ),
        ) from exc


@router.put("/modelo", response_model=PainelDoModelo, summary="Trocar o modelo do assistente")
async def trocar(
    payload: TrocaDeModelo,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """A troca vale da PRÓXIMA conversa em diante.

    As que já estão em curso terminam no modelo em que começaram — o laço
    resolve o modelo uma vez, no início. Trocar entre duas voltas do mesmo
    raciocínio mudaria o comportamento no meio do caminho.

    **Antes de salvar, o modelo é SONDADO** — ver `_sondar_ou_400`.
    """
    await _sondar_ou_400(payload.modelo)
    try:
        await config_svc.definir_modelo(
            db, payload.modelo,
            por=getattr(current_user, "username", None) or getattr(current_user, "id_hash", None),
            redis=infra.redis_ou_none(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await montar_painel(db, simular=None, consulta={})
