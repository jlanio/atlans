# app/api/routers/assistente_router.py
"""
The Home assistant — /assistente (persisted conversations + click confirmation).

Sibling of /assistente/editor, with three differences that shape the module:

- **The surface is the HOME** (`app/services/assistente_superficie.py`): full
  reach, delivery as a layer on the globe, and click confirmation for whatever
  touches what already existed.
- **The conversation is PERSISTED in the database** (several per person, no
  expiry), not in the editor's ephemeral Redis. The user's message is written in
  the handler (before the `return`, while the request session lives); the
  assistant's turns, in the generator, through the `ao_fechar_turno` hook, which
  opens its own session (`infra.sessao`).
- **The confirmation** is a second SSE: it validates ownership and token, executes
  the args STORED by the gate (never those from the click) and RESUMES the loop on
  the same stream.

The `Depends(get_db)` pitfall is the same as in /assistente/editor: the request
session closes when the handler RETURNS and the generator runs afterwards. That is
why everything on the read path that needs the database happens BEFORE the
`return`; from then on, each hook opens its own session, with its own lifecycle.
"""
from __future__ import annotations

import asyncio
import hmac
import json
from contextlib import suppress
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.config import ASSISTENTE_ATIVO
from app.core.rate_limiter import limiter
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.mcp.escopo import assistant_scope
from app.schemas.assistente import (
    ConversationDetail,
    ConversationList,
    ConversationSummary,
    ConfirmationDecision,
    Localizacao,
    HomeMessage,
    ReplayFrame,
    RenameConversation,
)
from app.api.routers._streaming import com_batimento
from app.schemas.assistente import AssistantQuota, AssistantState
from app.services import assistente_conversas
from app.services import assistente_superficie as agente
from app.services import assistente_service as assistente
from app.services import teto_do_assistente

logger = get_logger("app.api.agente")

router = APIRouter(
    prefix="/assistente",
    tags=["assistente"],
    dependencies=[Depends(get_current_user)],
)

DISABLED_REASON = (
    "O assistente nao esta configurado nesta instalacao. "
    "Defina LLM_API_KEY (ou OPENROUTER_API_KEY) no ambiente da API para liga-lo."
)

# The prefix of the synthetic confirmation messages — the guard that rejects it
# on input (`agente.parece_sintetica`), the text the server writes
# (`agente.MENSAGEM_CONFIRMADA`/`MENSAGEM_RECUSADA`) and what the prompt teaches
# the model to recognize all three live in `assistente_superficie`, in a single
# spelling.


def _require_enabled() -> None:
    if not ASSISTENTE_ATIVO:
        raise HTTPException(status_code=503, detail=DISABLED_REASON)


def _frame(evento: assistente.Evento) -> bytes:
    """Um `Evento` virando quadro SSE (`event:`/`data:` JSON, datas em ISO)."""
    corpo = json.dumps(evento.dados, ensure_ascii=False, default=str)
    return f"event: {evento.tipo}\ndata: {corpo}\n\n".encode("utf-8")


def _error_body(exc: ToolError) -> dict:
    try:
        corpo = json.loads(str(exc))
    except (TypeError, ValueError):
        return {"code": "recusado", "message": str(exc)}
    return corpo if isinstance(corpo, dict) else {"code": "recusado", "message": str(exc)}


def _conversation_summary(conv) -> ConversationSummary:
    return ConversationSummary(
        id=conv.id_hash,
        titulo=conv.titulo,
        workflow_id=conv.workflow_id,
        tokens_total=conv.tokens_total or 0,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def _lock_key(user_id: str, conversa_id: str) -> str:
    return f"agente:trava:{user_id}:{conversa_id}"


def _workspace_extra(workspace_id: str | None) -> str | None:
    if not workspace_id:
        return None
    return f"Workspace preferido para os fluxos que voce criar: {workspace_id}."


def _extra_location(loc: Localizacao | None) -> str | None:
    if loc is None:
        return None
    precisao = f" (precisao ~{loc.precisao_m:.0f} m)" if loc.precisao_m is not None else ""
    return (
        f"Localizacao atual da pessoa: {loc.lat:.4f}, {loc.lon:.4f}{precisao}. "
        'Use como referencia para pedidos relativos ("perto de mim", "num raio de '
        'N km"); nao repita a coordenada na resposta salvo se ajudar.'
    )


# The name of each language in the instruction that overrides the installation
# default. Portuguese is left out: it is the default, and its prompt stays byte
# for byte the usual one.
_LANGUAGE_NAME = {"en": "ingles (English)", "es": "espanhol (espanol)"}


def _extra_language(idioma: str | None) -> str | None:
    """The person's screen in another language: the answer and the reasoning go in it.

    Goes in the EXTRA block (not cached), after the system's language rule — and
    says explicitly that it replaces it, so the model is not caught between the two.
    """
    nome = _LANGUAGE_NAME.get(idioma or "")
    if not nome:
        return None
    return (
        f"A tela desta pessoa esta em {nome}. Responda e raciocine em {nome}, "
        "inclusive nas respostas rapidas que sugerir — isto substitui a regra de "
        "idioma acima."
    )


def _extra_instructions(
    workspace_id: str | None, localizacao: Localizacao | None, idioma: str | None = None
) -> str | None:
    """Joins the optional system prompt extras into a single string — or None.

    Each part (preferred workspace, current location, screen language) may be
    missing. With none, returns None: the usual no-op (`montar_sistema` attaches
    no block). With one or more, joins them with a blank line, in the order the
    model reads them.
    """
    partes = [
        p
        for p in (_workspace_extra(workspace_id), _extra_location(localizacao), _extra_language(idioma))
        if p
    ]
    return "\n\n".join(partes) if partes else None


def _valid_workspace(pedido: str | None, workspace_ids) -> str | None:
    """The client's `workspace_id`, only if it really is one of the person's workspaces.

    The value becomes SYSTEM prompt text (`_workspace_extra`), outside the
    `untrusted_data` envelope. Without checking, a client holding the person's
    JWT could send a free-form instruction of up to 64 chars into the prompt —
    and store a `workspace_id` that might not even be theirs.
    """
    if not pedido:
        return None
    return pedido if pedido in set(workspace_ids or ()) else None


# ── Persistencia incremental (nos hooks, sessao propria) ───────────────────


class _Cursor:
    """How many items OF THIS in-memory list have already been written.

    Previously, the index came from the database COUNT (`conversa[ja:]` with
    `ja = contar_mensagens()`), an invariant that only holds if the database rows
    are exactly `conversa[0:ja]`. It took only another tab writing to the same
    conversation for the count to jump ahead and a whole assistant message to be
    skipped silently — leaving `tool_use` and `tool_result` unpaired in the
    database. The cursor is per STREAM: it counts only what THIS stream wrote.
    """

    __slots__ = ("ja",)

    def __init__(self, ja: int = 0) -> None:
        self.ja = ja


async def _persist_turn(conversa_id: str, conversa: list[dict], cursor: _Cursor) -> None:
    """Writes the messages this stream has not written yet."""
    if len(conversa) <= cursor.ja:
        return
    novas = list(conversa[cursor.ja:])
    try:
        async with infra.sessao() as db:
            await assistente_conversas.append_messages(
                db,
                conversa_id,
                novas,
                initial_order=await assistente_conversas.next_order(db, conversa_id),
            )
        # Only advances AFTER the commit: a failure leaves the same messages
        # pending for the next attempt, instead of losing them.
        cursor.ja += len(novas)
    except Exception:  # pragma: no cover - persisting must not bring down the response
        logger.exception("Falha ao persistir turno (conversa %s).", conversa_id)


async def _close_persistence(
    conversa_id: str,
    final_transcript: list[dict],
    cursor: _Cursor,
    tokens_total: int | None,
) -> None:
    """At the end: writes what is left (closed pending items) and stamps tokens/updated_at.

    `tokens_total=None` when the `fim` event never arrived — and then nothing is
    stamped, instead of adding 0 (or, as before, zeroing the conversation's total).
    """
    try:
        await _persist_turn(conversa_id, final_transcript, cursor)
        async with infra.sessao() as db:
            await assistente_conversas.touch_conversation(db, conversa_id, tokens_total=tokens_total)
    except Exception:  # pragma: no cover
        logger.exception("Falha ao fechar a persistencia (conversa %s).", conversa_id)


async def _fechar_protegido(
    conversa_id: str,
    final_transcript: list[dict],
    cursor: _Cursor,
    tokens_total: int | None,
) -> None:
    """`_close_persistence` shielded against the generator's CANCELLATION.

    When the client disconnects, the `finally` runs with the cancellation pending
    and the first `await` inside it would raise `CancelledError` before any
    write. The `shield` lets the task finish anyway.
    """
    tarefa = asyncio.ensure_future(
        _close_persistence(conversa_id, final_transcript, cursor, tokens_total)
    )
    with suppress(asyncio.CancelledError):
        await asyncio.shield(tarefa)


# ── POST /assistente/conversa ────────────────────────────────────────────────────


@router.post("/conversa", summary="Conversar com o assistente da Home (stream)")
@limiter.limit("120/hour")
async def conversar(
    request: Request,
    payload: HomeMessage,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_enabled()
    if agente.parece_sintetica(payload.mensagem):
        # Only the server writes this prefix (confirmation). Rejecting it here is
        # what prevents the person (or a client) from forging it.
        raise HTTPException(status_code=422, detail="Mensagem invalida.")

    # BEFORE the return: the session dies when this handler leaves the scene.
    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = assistant_scope(
        user_id=current_user.id_hash,
        username=getattr(current_user, "username", None),
        workspace_ids=workspace_ids,
    )
    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover - only if the boot changes
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponivel.")

    nova = payload.conversa_id is None
    if nova:
        conv = await assistente_conversas.create_conversation(
            db,
            user_id=current_user.id_hash,
            workspace_id=_valid_workspace(payload.workspace_id, workspace_ids),
            titulo=assistente_conversas.automatic_title(payload.mensagem),
        )
    else:
        conv = await assistente_conversas.load_user_conversation(
            db, current_user.id_hash, payload.conversa_id
        )

    # The transcript and the writing of the user's message happen INSIDE the
    # lock, in the generator: writing here put the message in the database before
    # the lock was even checked, and the rejected second tab had already
    # corrupted the order.
    return StreamingResponse(
        com_batimento(
            _stream_conversation(
                escopo=escopo,
                servidor=servidor,
                conversa_id=conv.id_hash,
                titulo=conv.titulo,
                nova=nova,
                mensagem=payload.mensagem,
                workspace_id=conv.workspace_id,
                localizacao=payload.localizacao,
                idioma=payload.idioma,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_conversation(
    *, escopo, servidor, conversa_id, titulo, nova, mensagem, workspace_id, localizacao, idioma=None
) -> AsyncIterator[bytes]:
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    final_transcript: list[dict] = []
    cursor = _Cursor(0)
    tokens_total: int | None = None
    # 1st frame: the conversation's identity (the client learns the id of a new one).
    yield _frame(assistente.Evento("conversa", {"conversa_id": conversa_id, "titulo": titulo, "nova": nova}))
    try:
        async with assistente.trava_exclusiva(redis, _lock_key(escopo.user_id, conversa_id)):
            # Read the history and write the person's message, already under the lock.
            async with infra.sessao() as db:
                transcrito = await assistente_conversas.transcript_of(db, conversa_id, persist_closing=True)
                await assistente_conversas.append_messages(
                    db,
                    conversa_id,
                    [{"role": "user", "content": mensagem}],
                    initial_order=await assistente_conversas.next_order(db, conversa_id),
                )
            transcrito.append({"role": "user", "content": mensagem})
            # Everything in the transcript has already been written — the cursor starts here.
            cursor.ja = len(transcrito)
            final_transcript = list(transcrito)

            async def _hook(conversa: list[dict]) -> None:
                await _persist_turn(conversa_id, conversa, cursor)

            # The wrap-up runs UNDER the lock: `_fechar_protegido` recomputes
            # `next_order` and stamps tokens; in the OUTER `finally`, after
            # the lock is released, a 2nd tab that grabbed it in this window
            # would collide on UNIQUE(conversa, ordem) — the message was lost
            # in the except.
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                    superficie=agente.HOME,
                    conversa_id=conversa_id,
                    instrucoes_extras=_extra_instructions(workspace_id, localizacao, idioma),
                    ao_fechar_turno=_hook,
                ):
                    if evento.tipo == "fim":
                        final_transcript = evento.dados.get("transcrito") or final_transcript
                        tokens_total = (evento.dados.get("uso") or {}).get("total", 0)
                    yield _frame(evento)
            finally:
                await _fechar_protegido(conversa_id, final_transcript, cursor, tokens_total)
    except ToolError as exc:
        yield _frame(assistente.Evento("erro", _error_body(exc)))
        yield _frame(assistente.Evento("fim", {"ok": False}))
    except Exception:
        logger.exception("Assistente quebrou no stream (conversa %s).", conversa_id)
        yield _frame(assistente.Evento("erro", {"code": "erro_interno", "message": "Algo quebrou do nosso lado."}))
        yield _frame(assistente.Evento("fim", {"ok": False}))


# ── POST /assistente/conversas/{id}/confirmacoes/{tool_use_id} ───────────────────


@router.post(
    "/conversas/{conversa_id}/confirmacoes/{tool_use_id}",
    summary="Confirmar ou recusar uma acao (stream)",
)
# Tighter than the conversation's 120/h, and not because it is cheap: each click
# RESUMES the whole loop (up to `TETO_DE_VOLTAS` model rounds), and each round
# can open new confirmations — which would generate new POSTs here. Without a
# limiter, the whole path escaped the conversation route's bucket.
@limiter.limit("60/hour")
async def confirmar(
    conversa_id: str,
    tool_use_id: str,
    payload: ConfirmationDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_enabled()
    conv = await assistente_conversas.load_user_conversation(db, current_user.id_hash, conversa_id)

    redis = infra.redis_ou_none()
    guardado = await assistente_conversas.read_confirmation(redis, current_user.id_hash, conv.id_hash, tool_use_id)
    if guardado is None:
        # The key expired (15 min) or never existed — there is nothing to confirm.
        raise HTTPException(status_code=409, detail="Confirmacao expirada ou ja decidida.")
    # `compare_digest`, not `==`: the token is a secret, and the comparison must
    # not leak through timing which character matched.
    if not hmac.compare_digest(str(guardado.get("token", "")), payload.token):
        raise HTTPException(status_code=403, detail="Token de confirmacao invalido.")
    # The CONSUMPTION (one-shot DELETE) does NOT happen here: it lives in the
    # generator, under the lock and immediately before the effect. That way, if
    # the client drops between this return and the generator running, the
    # confirmation SURVIVES and can be redone — instead of vanishing, consumed,
    # without the action having happened. Here it is only validated (read).

    workspace_ids = await listar_workspace_ids(db, current_user.id_hash)
    escopo = assistant_scope(
        user_id=current_user.id_hash,
        username=getattr(current_user, "username", None),
        workspace_ids=workspace_ids,
    )
    servidor = getattr(request.app.state, "mcp_server", None)
    if servidor is None:  # pragma: no cover
        raise HTTPException(status_code=503, detail="Servidor de ferramentas indisponivel.")

    # The transcript is NOT read here: `persist_closing=True` WRITES (the closing
    # tool_result, via `append_messages`, which commits) and the lock is only
    # taken inside the generator. The read lives there, under the lock — as in
    # the sibling conversation route.
    return StreamingResponse(
        com_batimento(
            _stream_confirmation(
                escopo=escopo,
                servidor=servidor,
                conversa_id=conv.id_hash,
                tool_use_id=tool_use_id,
                guardado=guardado,
                decisao=payload.decisao,
                workspace_id=conv.workspace_id,
                localizacao=payload.localizacao,
                idioma=payload.idioma,
            )
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_confirmation(
    *, escopo, servidor, conversa_id, tool_use_id, guardado, decisao, workspace_id, localizacao=None,
    idioma=None,
) -> AsyncIterator[bytes]:
    redis = infra.redis_ou_none()
    transcrito: list[dict] = []
    final_transcript: list[dict] = []
    cursor = _Cursor(0)
    tokens_total: int | None = None
    tool = guardado.get("tool")
    args = guardado.get("args") or {}
    had_error = False
    try:
        async with assistente.trava_exclusiva(redis, _lock_key(escopo.user_id, conversa_id)):
            # Consumes the confirmation HERE — under the lock and before any effect,
            # not in the handler. If the client drops after the handler returns
            # but before this, the key SURVIVES and the person can reconfirm,
            # instead of the confirmed action vanishing with no retry. The lock
            # serializes the tabs, so the DELETE decides the race: 0 = another
            # tab already consumed it.
            if not await assistente_conversas.consume_confirmation(
                redis, escopo.user_id, conversa_id, tool_use_id
            ):
                yield _frame(
                    assistente.Evento(
                        "erro",
                        {"code": "confirmacao_ja_decidida", "message": "Esta acao ja foi decidida."},
                    )
                )
                yield _frame(assistente.Evento("fim", {"ok": False}))
                return
            # Read the history already under the lock. `persist_closing=True` WRITES
            # the closing tool_result; outside the lock, a tab that clicked a card
            # while another was still running the loop wrote that synthetic
            # closing and then had the real tool_result written over it — two
            # results for the same `tool_use`, and the API rejecting the
            # conversation forever.
            async with infra.sessao() as db:
                transcrito = await assistente_conversas.transcript_of(db, conversa_id, persist_closing=True)
            # Everything in the transcript has already been written — the cursor starts here.
            cursor.ja = len(transcrito)
            final_transcript = list(transcrito)

            if decisao == "confirmar":
                # Executes the STORED args, through the same path as the loop and under
                # the assistant's scope — never the args the client sent in the click.
                fila: list[assistente.Evento] = []

                async def _emit(evento: assistente.Evento) -> None:
                    fila.append(evento)

                # With the call id: this path's `progresso` frame goes out
                # with the same label as the loop's, and the reducer does not
                # depend on the legacy "the one that is running" criterion.
                contexto = assistente.ContextoLocal(_emit, tool_id=tool_use_id)
                yield _frame(
                    assistente.Evento("ferramenta", {"id": tool_use_id, "nome": tool, "argumentos": assistente._summarize(args)})
                )
                resultado, had_error = await assistente.chamar_no_servidor(servidor, escopo, tool, args, contexto)
                while fila:
                    yield _frame(fila.pop(0))
                yield _frame(assistente.Evento("ferramenta_fim", {"id": tool_use_id, "nome": tool, "erro": had_error}))
                for evento in agente.HOME.quadros_extras(None, tool, args, resultado, had_error):
                    yield _frame(evento)
                synthetic = (
                    f"{agente.MENSAGEM_CONFIRMADA}\n"
                    f"Ferramenta: {tool}\nResultado:\n{resultado}"
                )
            else:
                synthetic = agente.MENSAGEM_RECUSADA

            # Writes the synthetic message (with `meta`) and appends it to the
            # transcript, and leaves the AUDITABLE TRAIL of what the assistant
            # just wrote — the transcript does not serve as a trail: the person
            # deletes it with DELETE.
            async with infra.sessao() as db:
                ordem = await assistente_conversas.next_order(db, conversa_id)
                await assistente_conversas.append_messages(
                    db,
                    conversa_id,
                    [{"role": "user", "content": synthetic}],
                    initial_order=ordem,
                    metas={ordem: {"tipo": "confirmacao", "decisao": decisao, "tool": tool}},
                )
                await assistente_conversas.record_confirmed_action(
                    db,
                    user_id=escopo.user_id,
                    conversa_id=conversa_id,
                    tool=tool,
                    args=args,
                    tool_use_id=tool_use_id,
                    decisao=decisao,
                    erro=had_error,
                    default_workspace=workspace_id,
                    # The target only resolves its workspace if it is one of the ACTOR's:
                    # otherwise the assistant's trail would land in a workspace
                    # the person is not even a member of.
                    workspace_ids=escopo.workspace_ids,
                )
            transcrito.append({"role": "user", "content": synthetic})
            final_transcript = list(transcrito)
            cursor.ja = len(transcrito)

            # RESUMES the loop on the SAME SSE — the model continues from the outcome.
            async def _hook(conversa: list[dict]) -> None:
                await _persist_turn(conversa_id, conversa, cursor)

            # The wrap-up runs UNDER the lock (as in the conversation route): outside
            # it, `_fechar_protegido` would recompute `next_order` in a window
            # in which another tab would already hold the lock, colliding on
            # UNIQUE(conversa, ordem).
            try:
                async for evento in assistente.conversar(
                    escopo=escopo,
                    transcrito=transcrito,
                    servidor=servidor,
                    cliente=assistente.criar_cliente(),
                    redis=redis,
                    superficie=agente.HOME,
                    conversa_id=conversa_id,
                    # The resumption still knows the "near me": the client
                    # resends the shared location in the decision body
                    # (the server does not keep it — it lives only in the
                    # stream's prompt).
                    instrucoes_extras=_extra_instructions(workspace_id, localizacao, idioma),
                    ao_fechar_turno=_hook,
                ):
                    if evento.tipo == "fim":
                        final_transcript = evento.dados.get("transcrito") or final_transcript
                        tokens_total = (evento.dados.get("uso") or {}).get("total", 0)
                    yield _frame(evento)
            finally:
                await _fechar_protegido(conversa_id, final_transcript, cursor, tokens_total)
    except ToolError as exc:
        yield _frame(assistente.Evento("erro", _error_body(exc)))
        yield _frame(assistente.Evento("fim", {"ok": False}))
    except Exception:
        logger.exception("Confirmacao quebrou no stream (conversa %s).", conversa_id)
        yield _frame(assistente.Evento("erro", {"code": "erro_interno", "message": "Algo quebrou do nosso lado."}))
        yield _frame(assistente.Evento("fim", {"ok": False}))


# ── Leitura e gestao das conversas (JSON) ────────────────────────────────────


@router.get("/conversas", response_model=ConversationList, summary="Minhas conversas")
async def listar(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    linhas, total = await assistente_conversas.list_conversations(
        db, current_user.id_hash, limit=limit, offset=offset
    )
    return ConversationList(itens=[_conversation_summary(c) for c in linhas], total=total)


@router.get("/conversas/{conversa_id}", response_model=ConversationDetail, summary="Uma conversa (replay)")
async def detalhe(
    conversa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conv = await assistente_conversas.load_user_conversation(db, current_user.id_hash, conversa_id)
    quadros = await assistente_conversas.replay_frames(
        db,
        conv.id_hash,
        redis=infra.redis_ou_none(),
        user_id=current_user.id_hash,
        tokens_total=conv.tokens_total or 0,
    )
    return ConversationDetail(
        id=conv.id_hash,
        titulo=conv.titulo,
        workflow_id=conv.workflow_id,
        quadros=[ReplayFrame(**q) for q in quadros],
    )


@router.patch("/conversas/{conversa_id}", response_model=ConversationSummary, summary="Renomear")
async def renomear(
    conversa_id: str,
    payload: RenameConversation,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conv = await assistente_conversas.rename_conversation(db, current_user.id_hash, conversa_id, payload.titulo)
    return _conversation_summary(conv)


@router.delete("/conversas/{conversa_id}", status_code=204, summary="Apagar (soft)")
async def apagar(
    conversa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await assistente_conversas.delete_conversation(db, current_user.id_hash, conversa_id)
    return None


@router.get("/estado", response_model=AssistantState, summary="O assistente esta disponivel?")
async def estado(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """No `_require_enabled`: answering 503 would force the panel to handle an error
    to find out something that is just a state. The token quota is the SAME as the
    editor's (`assistente:tokens:{user}`), shared — and that is why the ceiling
    must come from the SAME place there and here, otherwise the same donut would
    show two ceilings depending on the screen that asked for it."""
    if not ASSISTENTE_ATIVO:
        return AssistantState(ativo=False, motivo=DISABLED_REASON)
    redis = infra.redis_ou_none()
    gasto, falta = await cotas.spent_and_reset(redis, current_user.id_hash)
    # Both together, and not the plan followed by its ceiling: with plans, the
    # ceiling that applies may be the CONTRACTED one (higher than the current one,
    # after a downgrade), and showing the current one here would make the donut
    # announce a tighter limit than the quota actually enforces — the person
    # would stop chatting too early.
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
