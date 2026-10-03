# app/api/routers/admin_assistente_router.py
"""Switching the assistant's model — with the provider's catalog up front.

`GET` returns the model in use and the provider's catalog (with each model's
price, when the provider reports it); `PUT` switches the model, after probing it.

An extension can add fields to the panel (`Registro.painel_do_modelo`, in
`app/extensoes`): the paid plans add each plan's quota and each option's cost,
because there switching models changes the plans' economics. URL parameters
the core does not know reach it intact.

Admin only (`require_admin` on the whole router), and the page that consumes this is
`/dashboard/admin/settings` — the dashboard route, which administrators can reach.
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


class CatalogModel(BaseModel):
    id: str
    nome: str
    # `None`, and never 0: a model with no known price cannot show up as
    # free in a cost table — that is the reading that would lead to a wrong choice.
    entrada_por_milhao: Optional[float] = None
    saida_por_milhao: Optional[float] = None
    contexto: Optional[int] = None


class ModelStatus(BaseModel):
    modelo: str
    origem: Literal["banco", "ambiente"]
    definido_por: Optional[str] = None
    definido_em: Optional[str] = None
    padrao_do_ambiente: str


class ModelPanel(BaseModel):
    # `allow`: the fields an extension adds to the panel (the plans add
    # `cota`, `custos`, `fatia_de_saida`, `dias_da_janela` and `dias_de_lastro`).
    model_config = ConfigDict(extra="allow")

    atual: ModelStatus
    catalogo: list[CatalogModel]
    catalogo_indisponivel: Optional[str] = Field(
        default=None,
        description="Motivo de o catálogo ter vindo vazio — o provedor fora do ar não "
                    "pode derrubar a tela inteira, mas a tela precisa dizer o que houve",
    )


class ModelSwitch(BaseModel):
    """`extra=forbid`: nothing but the id gets in through here. Price and ceiling belong
    to the server, and silently accepting an unknown field is the first step
    toward someone trying to send one of them."""

    model_config = ConfigDict(extra="forbid")

    # `None` goes back to the environment default — it is the screen's "back to default".
    modelo: Optional[str] = None


async def build_panel(
    db: AsyncSession, *, simular: str | None, consulta: Mapping[str, str],
) -> ModelPanel:
    """The panel: the model in use and the catalog, plus whatever each extension adds.

    `consulta` is the URL parameters; the core only reads `simular`, and the rest
    belongs to the extensions.
    """
    atual = await config_svc.get_status(db=db)

    catalogo: list[dict[str, Any]] = []
    falha: str | None = None
    if OPENROUTER_API_KEY:
        try:
            catalogo = await openrouter.listar_modelos(base_url=OPENROUTER_BASE_URL, chave=OPENROUTER_API_KEY)
        except Exception as exc:
            # A provider being down must not take down the screen: the admin still
            # needs to see what is in use and be able to go back to the default.
            logger.warning("Assistente: falha ao listar modelos (%s).", exc.__class__.__name__)
            falha = exc.__class__.__name__
    else:
        falha = "sem_credencial"

    extras: dict[str, Any] = {}
    for contribution in registro().painel_do_modelo:
        extras.update(await contribution(
            db, atual=atual, catalogo=catalogo, simular=simular, consulta=consulta,
        ))

    return ModelPanel(
        atual=ModelStatus(**atual),
        catalogo=[CatalogModel(**m) for m in catalogo],
        catalogo_indisponivel=falha,
        **extras,
    )


@router.get("/modelo", response_model=ModelPanel, summary="Modelo em uso e catálogo")
async def painel(
    request: Request,
    simular: Optional[str] = Query(
        default=None,
        description="Recalcula o que depende do modelo (o custo, com os planos) com este, sem salvar nada",
    ),
    db: AsyncSession = Depends(get_db),
):
    return await build_panel(db, simular=simular, consulta=request.query_params)


async def _probe_or_400(modelo: str | None) -> None:
    """A real call to the provider before saving the choice.

    **The catalog lists what EXISTS, not what works.** Among the provider's hundreds
    of models there are variants the chat endpoint rejects outright (the `:batch`
    ones), models without tools — and the assistant sends all 42 on every call —
    and models whose output ceiling is lower than ours. Saving one of them took the
    assistant down for ALL users with a generic "não consegui falar com o modelo"
    (couldn't reach the model), while whoever made the switch saw nothing. It was
    the screen offering choices that could not work.

    The probe has the shape of the real request, so the provider's refusal reaches
    whoever is switching, in the provider's own words, at the moment of the click.

    **`None` is not probed**, and that is deliberate: it is "back to the environment
    default", the emergency exit. If the provider is down, that exit has to stay
    open — probing it would lock the door precisely when it is needed.

    Any probe failure BLOCKS the switch, including a timeout. The expensive error
    is the other one: letting an unverified model through breaks the product for
    everyone, while blocking a legitimate switch during an outage costs trying
    again a bit later. The message distinguishes the two cases so the admin knows
    which one it is.
    """
    if modelo is None:
        return
    if not OPENROUTER_API_KEY:
        # Without a credential there is nothing to probe — and the screen already announces
        # that the catalog did not arrive. Blocking here would prevent configuring the
        # model before the key, which is a legitimate installation order.
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


@router.put("/modelo", response_model=ModelPanel, summary="Trocar o modelo do assistente")
async def trocar(
    payload: ModelSwitch,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """The switch applies from the NEXT conversation on.

    Those already in progress finish on the model they started with — the loop
    resolves the model once, at the start. Switching between two rounds of the same
    reasoning would change the behavior midway.

    **Before saving, the model is PROBED** — see `_probe_or_400`.
    """
    await _probe_or_400(payload.modelo)
    try:
        await config_svc.set_model(
            db, payload.modelo,
            por=getattr(current_user, "username", None) or getattr(current_user, "id_hash", None),
            redis=infra.redis_ou_none(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await build_panel(db, simular=None, consulta={})
