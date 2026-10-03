# app/api/routers/assistente/editor_router.py
"""
The assistant in the editor — /assistente/editor.

Three routes, and the first is the only one that does any work: `POST /conversa`
returns the answer as `text/event-stream`, frame by frame, while the tool loop
runs against this process's MCP server.

**Why a regular router, and not an `add_route` on the side like `/mcp`.** `/mcp`
leaves the middleware stack because its transport has requirements of its own.
Here the question was whether SSE survives `SecurityHeadersMiddleware` (a
`BaseHTTPMiddleware`) and GZip — and the answer was **measured**, with uvicorn
on a real socket: the frames arrive spaced out, the security headers are
applied, and Starlette 1.6's GZip excludes `text/event-stream` internally.
There is no reason to escape the stack.

**The `Depends(get_db)` pitfall.** The request session closes when the handler
RETURNS, and the `StreamingResponse` generator runs after that. Nothing that
needs the database can happen in there. That is why the workspaces are resolved
BEFORE the `return`; from then on, each tool opens its own session, through the
MCP's `infra.sessao`, with its own lifecycle.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.api.routers._streaming import com_batimento
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.config import ASSISTENTE_ATIVO
from app.core.rate_limiter import limiter
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.schemas.assistente import AssistantQuota, AssistantState, EditorMessage
from app.services import assistente_service as assistente
from app.services import teto_do_assistente

logger = get_logger("app.api.assistente")

router = APIRouter(
    prefix="/assistente/editor",
    tags=["assistente"],
    dependencies=[Depends(get_current_user)],
)

DISABLED_REASON = (
    "O assistente não está configurado nesta instalação. "
    "Defina LLM_API_KEY (ou OPENROUTER_API_KEY) no ambiente da API para ligá-lo."
)


def _require_enabled() -> None:
    """503, not 404: whoever installed without the key needs to know the feature exists."""
    if not ASSISTENTE_ATIVO:
        raise HTTPException(status_code=503, detail=DISABLED_REASON)


def _frame(evento: assistente.Evento) -> bytes:
    """An `Evento` turned into an SSE frame.

    A named `event:` instead of everything on a single channel: the panel
    subscribes by type and does not need to unpack an envelope to know whether
    it is text, progress or the end of the conversation.
    """
    corpo = json.dumps(evento.dados, ensure_ascii=False, default=str)
    return f"event: {evento.tipo}\ndata: {corpo}\n\n".encode("utf-8")


@router.post("/conversa", summary="Conversar com o assistente (stream)")
@limiter.limit("60/hour")
async def conversar(
    request: Request,
    payload: EditorMessage,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sends a message and receives the answer as `text/event-stream`.

    The history of that workflow is loaded and saved by the server: the client
    sends only the new message. See note 2 of `assistente_service.py` — a
    transcript coming from the browser would allow forging a tool result.
    """
    _require_enabled()

    # BEFORE the `return`: the session dies when this handler leaves the scene.
    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = assistente.escopo_do_editor_para(current_user, workspace_ids)

    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover - only if the boot changes
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponível.")

    return StreamingResponse(
        # `com_batimento`: a `: ping` every 15 s of silence, otherwise a long turn
        # (building and running a workflow) stays mute for minutes and the proxy
        # drops the SSE before the first frame. Same heartbeat as the Home assistant.
        com_batimento(
            _transmitir(
                escopo=escopo,
                servidor=servidor,
                workflow_id=payload.workflow_id,
                mensagem=payload.mensagem,
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Turns off any proxy buffering along the way. Traefik does not buffer
            # by default, but the header is cheap, and the day someone puts an
            # nginx in front it is already here.
            "X-Accel-Buffering": "no",
        },
    )


async def _transmitir(*, escopo, servidor, workflow_id, mensagem) -> AsyncIterator[bytes]:
    """The SSE generator: lock, load, converse, save — and save even if it fails.

    The `finally` around `salvar` is what keeps closing the tab mid-answer from
    wiping the conversation. The quota is already protected without it:
    `conversar` charges after EACH model call, inside the loop, not at the end.
    """
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    try:
        async with assistente.conversa_exclusiva(redis, escopo.user_id, workflow_id):
            transcrito = await assistente.carregar_conversa(redis, escopo.user_id, workflow_id)
            transcrito.append({"role": "user", "content": mensagem})
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                ):
                    if evento.tipo == "fim":
                        transcrito = evento.dados.get("transcrito") or transcrito
                    yield _frame(evento)
            finally:
                # Shielded against the generator's CANCELLATION: when the client
                # closes the tab mid-answer, the `finally` runs with the
                # cancellation pending and a bare `await` would raise
                # `CancelledError` before writing — the whole turn would be lost.
                # The `shield` lets the write finish anyway (same pattern as the
                # Home assistant's `_fechar_protegido`).
                gravacao = asyncio.ensure_future(
                    assistente.salvar_conversa(redis, escopo.user_id, workflow_id, transcrito)
                )
                with suppress(asyncio.CancelledError):
                    await asyncio.shield(gravacao)
    except ToolError as exc:
        # Declared refusal (quota exceeded, conversation in progress). It goes out
        # as an error frame, not as an HTTP status, because the response has
        # already started — and because this way the panel has ONE error path only.
        yield _frame(assistente.Evento("erro", _error_body(exc)))
        yield _frame(assistente.Evento("fim", {"transcrito": transcrito, "ok": False}))
    except Exception:
        logger.exception("Assistente quebrou no stream (usuário %s).", escopo.user_id)
        yield _frame(
            assistente.Evento(
                "erro",
                {"code": "erro_interno", "message": "Algo quebrou do nosso lado."},
            )
        )
        yield _frame(assistente.Evento("fim", {"transcrito": transcrito, "ok": False}))


def _error_body(exc: ToolError) -> dict:
    """The JSON that `erro()` builds, or an equivalent envelope when it is not JSON."""
    try:
        corpo = json.loads(str(exc))
    except (TypeError, ValueError):
        return {"code": "recusado", "message": str(exc)}
    return corpo if isinstance(corpo, dict) else {"code": "recusado", "message": str(exc)}


@router.get("/estado", response_model=AssistantState, summary="O assistente está disponível?")
async def estado(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """What the panel checks before showing up on screen.

    Does not use `_require_enabled`: answering 503 here would force the panel to
    handle an error to find out something that is just a state.
    """
    if not ASSISTENTE_ATIVO:
        return AssistantState(ativo=False, motivo=DISABLED_REASON)

    redis = infra.redis_ou_none()
    gasto, falta = await cotas.spent_and_reset(redis, current_user.id_hash)
    # The ceiling may come from the PLAN (with the plans extension). This handler
    # is ordinary (no SSE generator), so the `Depends` session lives until the
    # `return` and can be reused — it is the conversation loop, which has no
    # session, that opens its own.
    # Both together, and not the plan followed by its ceiling: the ceiling that
    # applies may be the CONTRACTED one (higher than the current one, after a
    # downgrade), and showing the current one here would make the donut announce
    # a tighter limit than the quota actually enforces — the person would stop
    # chatting too early.
    plano, teto = await teto_do_assistente.plano_e_teto(
        current_user.id_hash, db=db, redis=redis
    )
    return AssistantState(
        ativo=True,
        plano=plano,
        assinaturas_ativas=teto_do_assistente.assinaturas_ativas(),
        cota=AssistantQuota(
            gasto=gasto,
            teto=teto,
            reabre_em_segundos=falta,
        ),
    )


@router.delete("/conversa", status_code=204, summary="Esquecer a conversa deste fluxo")
async def esquecer(
    workflow_id: str | None = None,
    current_user=Depends(get_current_user),
):
    """Starts over from scratch on that workflow. Deletes no workflow — only the history."""
    _require_enabled()
    await assistente.esquecer_conversa(infra.redis_ou_none(), current_user.id_hash, workflow_id)
    return None
