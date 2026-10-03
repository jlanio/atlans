# app/services/assistente_conversas.py
"""
Persistence and replay of the Home assistant's conversations.

The loop (`assistente_service.conversar`) and the surface (`assistente_superficie.HOME`)
know nothing about the database: what stores the conversation is this service, and
the route (`assistente_router`) stitches the two together. The responsibilities here:

- **Conversation CRUD** — create, load (with an owner gate), list, rename,
  delete (soft), and the `tocar` that stamps `updated_at`/`tokens_total`.
- **Transcript and incremental persistence** — `transcrito_de` builds what the
  model receives (`[{"role", "content"}]`), and `anexar_mensagens` writes the new
  messages with a contiguous `ordem`. The route persists turn by turn through the
  `ao_fechar_turno` hook, and not as a blob at the end.
- **Replay** — `quadros_do_replay` rebuilds the conversation in the SAME SSE
  frames, so the panel reapplies them along the same path as a live frame. Two
  security rules: a `tool_result` NEVER goes out (it is the server's word, not
  screen content), and a `confirmacao` only reappears with its token if its key
  still exists in Redis (otherwise it would be a dead button).
- **Confirmation** — `ler`/`consumir` the key that the Home gate has already
  WRITTEN (surfaces PR). Consumption is a `get`+`delete`: whoever deleted it
  executes, whoever arrived later lost the race.
"""
from __future__ import annotations

import json
from contextlib import suppress
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.audit_event import AuditEvent
from app.models.conversa import Conversa, Mensagem
from app.models.models import Workflow
from app.services import assistente_superficie as ag
from app.services import assistente_service as cs

logger = get_logger("app.agente.service")

TAMANHO_DO_TITULO = 60


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def carregar_conversa_da_pessoa(db: AsyncSession, user_id: str, conversa_id: str) -> Conversa:
    """The conversation, if it belongs to the person and was not deleted. Uniform 404 otherwise.

    404 and not 403 on purpose: distinguishing "does not exist" from "exists but is
    not yours" would answer the question "does this id exist?" — which nobody should
    be able to ask by sweeping ids. The same criterion as the MCP edge
    (`resolucao.carregar_workflow`).
    """
    conv = (
        await db.execute(
            select(Conversa).where(
                Conversa.id_hash == conversa_id,
                Conversa.user_id == user_id,
                Conversa.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada.")
    return conv


async def criar_conversa(
    db: AsyncSession,
    *,
    user_id: str,
    workspace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    titulo: Optional[str] = None,
) -> Conversa:
    conv = Conversa(
        user_id=user_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        titulo=titulo,
        origem="home",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


def titulo_automatico(mensagem: str) -> str:
    """The first words of the 1st message, up to 60 chars. A model-generated title
    is left for later — this is the cheap one that already says what the conversation is about."""
    limpo = " ".join((mensagem or "").split())
    return limpo[:TAMANHO_DO_TITULO] if limpo else "Nova conversa"


async def listar_conversas(
    db: AsyncSession, user_id: str, *, limit: int = 50, offset: int = 0
) -> tuple[list[Conversa], int]:
    """My non-deleted conversations, most recently active on top."""
    base = select(Conversa).where(Conversa.user_id == user_id, Conversa.deleted_at.is_(None))
    total = (
        await db.execute(
            select(func.count(Conversa.id)).where(
                Conversa.user_id == user_id, Conversa.deleted_at.is_(None)
            )
        )
    ).scalar() or 0
    linhas = (
        await db.execute(
            base.order_by(Conversa.updated_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(linhas), int(total)


async def renomear_conversa(db: AsyncSession, user_id: str, conversa_id: str, titulo: str) -> Conversa:
    conv = await carregar_conversa_da_pessoa(db, user_id, conversa_id)
    conv.titulo = titulo
    conv.updated_at = utc_now_naive()
    await db.commit()
    await db.refresh(conv)
    return conv


async def apagar_conversa(db: AsyncSession, user_id: str, conversa_id: str) -> None:
    """Soft delete: it disappears from the list, the history stays."""
    conv = await carregar_conversa_da_pessoa(db, user_id, conversa_id)
    conv.deleted_at = utc_now_naive()
    await db.commit()


# ── Transcrito e persistencia incremental ────────────────────────────────────


async def transcrito_de(
    db: AsyncSession, conversa_id: str, *, persistir_fecho: bool = False
) -> list[dict[str, Any]]:
    """What the model receives: `[{"role", "content"}]` in order, VERBATIM.

    `blocos` is already in the project's format (what the loop writes and the
    model client translates on the way out — `app/services/openrouter.py`), so
    there is no conversion here — only the read in order.

    `persistir_fecho=True` also writes to the database the closing `tool_result`
    that `_fechar_pendencias` appended. Whoever is going to RESUME the conversation
    (append a new message afterwards) needs this: closing only in memory would
    leave the orphan in the database and, with the new message written after it,
    the closing on the next read would no longer happen (`_fechar_pendencias`
    only looks at the LAST message).
    """
    linhas = (
        await db.execute(
            select(Mensagem.papel, Mensagem.blocos)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.ordem)
        )
    ).all()
    # `_fechar_pendencias` ON READ, and not only on write: the loop only closes
    # pending items on the `fim` event, which never happens when the generator is
    # CANCELLED (the person switched chats and the fetch aborted in the middle of
    # a tool). The orphan `tool_use` stayed recorded and the API rejected the
    # whole conversation on resume ("tool_use ids were found without tool_result
    # blocks"), forever. Closing here, what comes out of the database is always
    # well formed, whatever the cause of the interruption.
    cru = [{"role": papel, "content": blocos} for papel, blocos in linhas]
    fechado = cs._fechar_pendencias(cru)
    if persistir_fecho and len(fechado) > len(cru):
        await anexar_mensagens(
            db, conversa_id, fechado[len(cru):], ordem_inicial=await proxima_ordem(db, conversa_id)
        )
    return fechado


async def proxima_ordem(db: AsyncSession, conversa_id: str) -> int:
    """The next free `ordem` — `MAX(ordem)+1`, never the COUNT of rows.

    The count only matches the next order while nothing writes in parallel.
    Two tabs on the same conversation read the same count and collided on the
    UNIQUE `uq_mensagens_conversa_ordem` (unhandled 500), or silently skipped a
    whole message — leaving `tool_use` and `tool_result` unpaired.
    """
    maior = (
        await db.execute(
            select(func.max(Mensagem.ordem)).where(Mensagem.conversa_id == conversa_id)
        )
    ).scalar()
    return 0 if maior is None else int(maior) + 1


async def anexar_mensagens(
    db: AsyncSession,
    conversa_id: str,
    entradas: list[dict[str, Any]],
    *,
    ordem_inicial: int,
    metas: Optional[dict[int, dict[str, Any]]] = None,
) -> int:
    """Writes messages in the loop's format (`[{"role", "content"}]`), with a
    contiguous `ordem` starting at `ordem_inicial`. Returns the next free order.

    `metas` (optional) marks a message by the ABSOLUTE index of the order — used
    only by the synthetic confirmation message, which carries `meta={"tipo":...}`.
    """
    metas = metas or {}
    ordem = ordem_inicial
    for entrada in entradas:
        db.add(
            Mensagem(
                conversa_id=conversa_id,
                ordem=ordem,
                papel=entrada.get("role", "assistant"),
                blocos=entrada.get("content"),
                meta=metas.get(ordem),
            )
        )
        ordem += 1
    if entradas:
        await db.commit()
    return ordem


async def tocar_conversa(
    db: AsyncSession, conversa_id: str, *, tokens_total: Optional[int] = None
) -> None:
    """Stamps `updated_at` (and `tokens_total`, when given). Never raises: it is
    bookkeeping, it must not bring down the response that has already gone out."""
    conv = (
        await db.execute(select(Conversa).where(Conversa.id_hash == conversa_id))
    ).scalar_one_or_none()
    if conv is None:
        return
    conv.updated_at = utc_now_naive()
    if tokens_total is not None:
        # ADDS, does not assign: the field name, the model's docstring and
        # `ConversaResumo` promise the CONVERSATION total. When assigning, it kept
        # the cost of the last turn — and any abnormal exit before `fim` (lock
        # taken by another tab, quota exceeded) wrote 0 over the accumulated
        # value. Whoever did not observe `fim` passes `None` and stamps nothing.
        conv.tokens_total = int(conv.tokens_total or 0) + int(tokens_total)
    await db.commit()


# ── Confirmation (the key is already written by the Home gate) ────────────────


async def ler_confirmacao(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> Optional[dict[str, Any]]:
    """The stored `{token, tool, args, criado_em}`, or None if it expired/does not exist."""
    if redis is None:
        return None
    try:
        cru = await redis.get(ag.chave_de_confirmacao(user_id, conversa_id, tool_use_id))
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao ler a confirmacao: %s", exc.__class__.__name__)
        return None
    if not cru:
        return None
    try:
        corpo = json.loads(cru)
    except (TypeError, ValueError):  # pragma: no cover - corrupted value
        return None
    return corpo if isinstance(corpo, dict) else None


async def consumir_confirmacao(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> bool:
    """Deletes the key exactly once. True if THIS call deleted it (won the race),
    False if it had already been decided (delete returned 0)."""
    if redis is None:
        return False
    try:
        apagadas = await redis.delete(ag.chave_de_confirmacao(user_id, conversa_id, tool_use_id))
    except Exception as exc:  # pragma: no cover - depends on Redis
        logger.warning("Falha ao consumir a confirmacao: %s", exc.__class__.__name__)
        return False
    return bool(apagadas)


# ── Auditable trail of what the assistant WRITES ─────────────────────────────


async def _workspace_do_alvo(
    db: AsyncSession, args: Any, workspace_ids: Any = None
) -> Optional[str]:
    """The target workflow's workspace, when the arguments carry a `workflow_id`.

    It only resolves what is WITHIN the actor's reach (`workspace_ids`) and was
    not deleted. The `workflow_id` comes from the confirmation's stored arguments:
    without the filter, an id from another workspace made the `AuditEvent` land on
    the trail of a workspace the person is not a member of — a cross-tenant write,
    even if only an audit one. With no match, the caller falls back to the
    conversation's workspace.
    """
    ref = args.get("workflow_id") if isinstance(args, dict) else None
    if not ref:
        return None
    alcance = list(workspace_ids or ())
    if not alcance:
        return None
    return (
        await db.execute(
            select(Workflow.workspace_id).where(
                Workflow.id_hash == str(ref),
                Workflow.deleted_at.is_(None),
                Workflow.workspace_id.in_(alcance),
            )
        )
    ).scalar_one_or_none()


async def registrar_acao_confirmada(
    db: AsyncSession,
    *,
    user_id: str,
    conversa_id: str,
    tool: Optional[str],
    args: Any,
    tool_use_id: str,
    decisao: str,
    erro: bool,
    workspace_padrao: Optional[str] = None,
    workspace_ids: Any = None,
) -> None:
    """Writes one `AuditEvent` per action decided on the confirmation card.

    Without this, the only record of what the assistant wrote was the transcript
    in `mensagens.blocos` — which the person themselves deletes with `DELETE
    /assistente/conversas/{id}`. An admin investigating missing Drive files had
    nowhere to start. The trail covers exactly what goes through the gate: the
    writes to resources that already existed.

    The row's workspace is the target workflow's, but only when it is within the
    actor's reach (`workspace_ids`); otherwise, the conversation's. See
    `_workspace_do_alvo`.

    Never raises: auditing must not bring down an action that has already
    happened — the `logger.exception` is the signal that the trail failed.
    """
    try:
        workspace_id = (
            await _workspace_do_alvo(db, args, workspace_ids) or workspace_padrao or "desconhecido"
        )
        db.add(
            AuditEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                action=f"assistente.{decisao}",
                resource_type="assistente_tool",
                resource_id=(ag._alvo(args) or tool or "")[:255],
                details={
                    "tool": tool,
                    "argumentos": cs._resumo(args),
                    "conversa_id": conversa_id,
                    "tool_use_id": tool_use_id,
                    "erro": bool(erro),
                },
            )
        )
        await db.commit()
    except Exception:  # pragma: no cover - auditoria e best-effort
        logger.exception("Falha ao auditar a acao do assistente (conversa %s).", conversa_id)
        # Undoes the flush that failed: without this the session stays in
        # `PendingRollback` and brings down the next write — auditing is the last
        # link, it must not contaminate whoever comes after.
        with suppress(Exception):
            await db.rollback()


# ── Replay ───────────────────────────────────────────────────────────────────


def _texto_do_tool_result(bloco: dict[str, Any]) -> tuple[str, bool]:
    conteudo = bloco.get("content")
    if isinstance(conteudo, str):
        texto = conteudo
    elif isinstance(conteudo, list):
        texto = "\n".join(
            b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("text")
        )
    else:
        texto = ""
    return texto, bool(bloco.get("is_error"))


async def _confirmacao_reaberta(
    redis, user_id: str, conversa_id: str, tool_use_id: str
) -> Optional[dict[str, Any]]:
    """The `confirmacao` frame of a call STILL PENDING — only when the Redis key
    exists. A vanished key (decided or expired) does not become a dead button."""
    guardado = await ler_confirmacao(redis, user_id, conversa_id, tool_use_id)
    if not guardado:
        return None
    args = guardado.get("args")
    return {
        "tool_use_id": tool_use_id,
        "token": guardado.get("token"),
        "acao": {
            "tool": guardado.get("tool"),
            "argumentos": cs._resumo(args),
            "alvo": ag._alvo(args),
        },
    }


async def quadros_do_replay(
    db: AsyncSession, conversa_id: str, *, redis, user_id: str, tokens_total: int
) -> list[dict[str, Any]]:
    """The conversation rebuilt in the SAME SSE frames.

    A user message becomes `usuario`; the assistant's text and reasoning become
    `texto`/`pensando`; each `tool_use` becomes `ferramenta` (with SUMMARIZED
    arguments) and, if it already had a result, `ferramenta_fim` plus the Home
    frames (`fluxo`/`camada`) of that result — through the SAME `quadros_extras`
    as the loop. A `tool_use` still without a result that has a live confirmation
    in Redis reopens the `confirmacao`. `tool_result` never goes out. A `fim`
    closes with the token total.
    """
    rows = (
        await db.execute(
            select(Mensagem.papel, Mensagem.blocos, Mensagem.meta)
            .where(Mensagem.conversa_id == conversa_id)
            .order_by(Mensagem.ordem)
        )
    ).all()

    # Map tool_use_id -> (text, error), gathered from the tool_results (which do not go out).
    resultados: dict[str, tuple[str, bool]] = {}
    for _papel, blocos, _meta in rows:
        if isinstance(blocos, list):
            for b in blocos:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    resultados[b.get("tool_use_id")] = _texto_do_tool_result(b)

    quadros: list[dict[str, Any]] = []
    for papel, blocos, meta in rows:
        if papel == "user":
            # The person's text (or the synthetic confirmation message, with meta).
            # List = tool_results, which NEVER go out in the replay.
            if isinstance(blocos, str):
                dados: dict[str, Any] = {"texto": blocos}
                if meta:
                    dados["meta"] = meta
                quadros.append({"tipo": "usuario", "dados": dados})
            continue
        if not isinstance(blocos, list):
            continue
        for b in blocos:
            if not isinstance(b, dict):
                continue
            tipo = b.get("type")
            if tipo == "text" and b.get("text"):
                quadros.append({"tipo": "texto", "dados": {"texto": b["text"]}})
            elif tipo == "thinking" and b.get("thinking"):
                quadros.append({"tipo": "pensando", "dados": {"texto": b["thinking"]}})
            elif tipo == "tool_use":
                nome = b.get("name")
                args = b.get("input")
                tuid = b.get("id")
                quadros.append(
                    {"tipo": "ferramenta", "dados": {"id": tuid, "nome": nome, "argumentos": cs._resumo(args)}}
                )
                resultado = resultados.get(tuid)
                if resultado is not None:
                    texto_res, deu_erro = resultado
                    quadros.append(
                        {"tipo": "ferramenta_fim", "dados": {"id": tuid, "nome": nome, "erro": deu_erro}}
                    )
                    for evento in ag.HOME.quadros_extras(None, nome, args, texto_res, deu_erro):
                        quadros.append({"tipo": evento.tipo, "dados": evento.dados})
                else:
                    reaberta = await _confirmacao_reaberta(redis, user_id, conversa_id, tuid)
                    if reaberta is not None:
                        quadros.append({"tipo": "confirmacao", "dados": reaberta})

    quadros.append({"tipo": "fim", "dados": {"uso": {"total": int(tokens_total or 0)}, "ok": True}})
    return quadros
