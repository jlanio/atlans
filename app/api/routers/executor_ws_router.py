# app/api/routers/executor_ws_router.py
"""
WebSocket for connecting external Executors.

Endpoint: GET /ws/executores/{executor_id}?token=<JWT>

Message protocol (JSON). Types per direction, version and reserved keys
live in flow/utils/protocolo_ws.py, which the executor also imports:

  Executor → Server:
    {"type": "handshake",  "protocol_version": str, "executor_version": str, "system_info": dict?}
    {"type": "heartbeat"}
    {"type": "capacity",   "queued": int, "running": int, "max_concurrent": int, "max_queue": int}
    {"type": "job_result", "job_id": str, "status": "ok"|"error", "output": any, "error": str?}
    {"type": "node_event", "run_id": str, "node": str, "status": str, "timestamp": float, ...}
    {"type": "sync_event", "event": str, "dataset": str, "progress": float, ...}
    {"type": "ack",        "job_id": str, "status": "enqueued"}
    {"type": "inventario", "ativos": [str], "resultados": [str], "truncado": bool}

  Server → Executor:
    {"type": "job",  ...job_message...}   ← build_job_message() from job_crypto.py
    {"type": "cancel", "job_id": str}         ← signed (see control_crypto)
    {"type": "control", "action": str, "reason": str}   ← signed (ditto)
    {"type": "drive_event", "action": str, "file": dict} ← app/core/drive_events.py
    {"type": "error", "reason": str, ...}     ← rejected message (`_responder_erro`)
"""
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, NamedTuple

from app.core.utils.logger import get_logger

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.executor_connections import (
    encerrar_envios,
    encerrar_saida,
    enfileirar_ao_executor,
    executor_registry,
    fechar_ws_do_executor,
    ip_do_websocket,
)
from app.core.db import get_session_async
from app.models.executor import Executor
from app.services.executor_service import (
    motivo_da_revogacao, registrar_fim_da_sessao, update_agent_last_seen,
)
from flow.utils.protocolo_ws import (
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    TIPO_ERRO,
)

from .executor_ws.inbox import (
    _INBOX_CANCEL_GRACE,
    _INBOX_FLUSH_TIMEOUT,
    _INBOX_MAXSIZE,
    _InboxQueue,
    _drenar_inbox,
    _encerrar_drenagem,
    _enfileirar_mensagem,
    _novo_contador_de_descartes,
    _resgatar_job_results_pendentes,
)
from .executor_ws.orfaos import (
    _fail_orphan_runs_if_gone,
    _orphan_check_tasks,
)
from .executor_ws.protocolo import (
    _drop_rate_state,
    _missing_fields,
    _node_event_allowed,
    _sanitize_capacity,
    _sanitize_executor_version,
    _sanitize_system_info,
    _sync_event_allowed,
)

# ── Reexports ────────────────────────────────────────────────────────────────
# main imports the watchdog (and the task registry, already imported above for
# the teardown) from here. The rest of the package is imported directly from
# app.api.routers.executor_ws.*.
from .executor_ws.orfaos import orphan_runs_watchdog  # noqa: F401

logger = get_logger(__name__)

router = APIRouter(tags=["executores-ws"])

# Maximum interval without a heartbeat before considering the executor disconnected
_HEARTBEAT_TIMEOUT = 90  # segundos

# Strong reference to the retention purge task fired on reconnection (asyncio
# only keeps weakrefs). Losing that task means expired personal data that stays
# on the user's disk until the next cycle of the cleanup loop.
_purge_tasks_pendentes: set[asyncio.Task] = set()


def _responder_erro(ws: WebSocket, executor_id: str, reason: str, **detalhe) -> None:
    """Error response to the executor: `{"type": "error", "reason": ..., **detalhe}`.
    Best-effort, through the same queue as the other sends to the socket (see
    `_Saida`): writing on the side competed with the drain of a send in progress.

    The type is the protocol's (TIPO_ERRO, in flow/utils/protocolo_ws.py), which
    the executor recognizes and logs at WARNING with the `reason`.

    Only enqueues, without waiting its turn: the caller is the receive loop, the
    only one that renews presence — stuck behind a slow frame, it let a live
    executor's presence expire (and the watchdog closed its runs).
    A close right after discards the response still in the queue; what matters
    to the executor in those cases is the close code."""
    corpo = {"type": TIPO_ERRO, "reason": reason, **detalhe}
    try:
        enfileirar_ao_executor(ws, json.dumps(corpo), executor_id)
    except Exception:
        pass  # the socket may have closed


# Deadline for writing the session's end on teardown — see `_gravar_fim_da_sessao`.
_FIM_DA_SESSAO_TIMEOUT = 5.0


async def _gravar_fim_da_sessao(executor_id: str, ultimo_contato) -> None:
    """Writes the session's end to `last_seen_at`. Without this it stopped at the
    handshake, and the executors screen showed an executor that was up for three
    days and went down ten minutes ago as "visto há 3 dias" (seen 3 days ago).

    Writes the session's last contact (the last message received), not the
    moment of the teardown: after a missed heartbeat, that moment comes ~100 s
    after the last sign of life. And only if it is later than what is in the
    database (see `registrar_fim_da_sessao`)."""
    if not isinstance(ultimo_contato, datetime):
        ultimo_contato = datetime.now(timezone.utc)
    if ultimo_contato.tzinfo is None:
        ultimo_contato = ultimo_contato.replace(tzinfo=timezone.utc)
    visto_em = ultimo_contato.astimezone(timezone.utc).replace(tzinfo=None)   # column in UTC without time zone
    async with get_session_async() as db:
        await registrar_fim_da_sessao(db, executor_id, visto_em)


# Interval of the revocation check while the session is open — see `_vigiar_revogacao`.
_REVOGACAO_INTERVALO = 60.0


async def _vigiar_revogacao(executor_id: str, ws: WebSocket) -> None:
    """Closes with 4403 the session of an executor revoked while the session is open.

    mTLS is only checked on connect. Revocations request the close through the
    relay, but the notice gets lost when Redis restarts, when the session's
    listener reconnects or with a session born in the middle of the revocation —
    and the revoked session stayed alive (receiving jobs) until it reconnected.
    Every `_REVOGACAO_INTERVALO` the database says whether it still holds
    (`motivo_da_revogacao`). Database down is left for the next round: dropping
    the fleet's live sessions over a database blip would be worse."""
    while True:
        await asyncio.sleep(_REVOGACAO_INTERVALO)
        try:
            async with get_session_async() as db:
                motivo = await motivo_da_revogacao(db, executor_id)
        except Exception as exc:
            logger.warning(
                "Executor '%s': conferência de revogação falhou (%r) — tento de novo.", executor_id, exc,
            )
            continue
        if motivo:
            logger.warning("Executor '%s' revogado com a sessão aberta (%s) — fechando.", executor_id, motivo)
            try:
                await fechar_ws_do_executor(ws, code=4403, reason=motivo)
            except Exception as exc:
                logger.warning("Executor '%s': falha ao fechar a sessão revogada: %r", executor_id, exc)
            return


@router.websocket("/ws/executores/{executor_id}")
async def agent_websocket(executor_id: str, ws: WebSocket):
    """
    WebSocket connection authenticated by mTLS cert.

    Traefik validates the client cert against the internal CA in the TLS handshake
    and injects X-Forwarded-Tls-Client-Cert-Info with CN and serial. Here:
      1. Parse the header → (cn, serial).
      2. CN must be `executor-{executor_id}` (from the URL path).
      3. Executor exists + status='active' + serial matches cert_serial in the DB.
      4. Cert serial is not in the Redis blacklist.

    The session phases live below, in the order they run:
    `_autenticar_ou_recusar` (before the accept), `_abrir_sessao`,
    `_tratar_mensagem` for each message and `_encerrar_sessao` on teardown.
    """
    # ── 1. Validate the mTLS cert before accept() ────────────────────────────
    tetos = await _autenticar_ou_recusar(ws, executor_id)
    if tetos is None:
        return

    # ── 2. Accept the connection ──────────────────────────────────────────────
    sessao = await _abrir_sessao(ws, executor_id, tetos)
    try:
        # Inside the try ON PURPOSE: if the database is down, the exception went up
        # before the try and the `finally` with the unregister never ran — the
        # connection stayed registered (and renewing presence) with nobody
        # reading the socket.
        async with get_session_async() as db:
            await update_agent_last_seen(db, executor_id)

        logger.info("Executor '%s' conectado via WebSocket.", executor_id)

        # ── 3. Receive loop ───────────────────────────────────────────────────
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=_HEARTBEAT_TIMEOUT)
            except asyncio.TimeoutError:
                # No message within the timeout — closes the connection
                logger.warning("Executor '%s' sem heartbeat por %ds — desconectando.", executor_id, _HEARTBEAT_TIMEOUT)
                await fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")
                break
            if not await _tratar_mensagem(sessao, raw):
                break

    except WebSocketDisconnect:
        logger.info("Executor '%s' desconectou (WebSocketDisconnect).", executor_id)
    except Exception as exc:
        logger.error("Erro no WebSocket do executor '%s': %s", executor_id, exc)
    finally:
        await _encerrar_sessao(sessao)


# ── 1. Authentication ────────────────────────────────────────────────────────


class _Tetos(NamedTuple):
    """The record's ceilings — clamp of the self-declared capacity (see S3)."""

    max_concurrent: int | None
    max_queue: int | None


async def _autenticar_ou_recusar(ws: WebSocket, executor_id: str) -> _Tetos | None:
    """Validates the mTLS cert BEFORE accept() — single pipeline: see
    dependencies.validate_executor_mtls, shared with HTTP.

    Returns the ceilings from the executor's record, or None when it refused: in
    that case the connection was already accepted and closed with the reason's
    44xx, and nothing else runs."""
    from app.api.dependencies import (
        validate_executor_mtls, ExecutorMtlsError, _MTLS_WS_CODE,
    )
    try:
        async with get_session_async() as db:
            ag = await validate_executor_mtls(
                header_value=ws.headers.get("x-forwarded-tls-client-cert-info", ""),
                client_host=ws.client.host if ws.client else None,
                url_path=str(ws.url.path),
                db=db,
                expected_executor_id=executor_id,
                require_public_key=True,
            )
            # Extracts before closing the session (avoids DetachedInstanceError).
            # The version does NOT come from here: the database holds the
            # previous session's, and this one's arrives in the handshake.
            return _Tetos(max_concurrent=ag.max_concurrent_jobs, max_queue=ag.max_queue_size)
    except ExecutorMtlsError as exc:
        # AUTHORITATIVE DENY: it must reach the executor as a CLOSE 44xx, never
        # as an HTTP status. Raising WebSocketException BEFORE accept() turns
        # the deny into a status in the HTTP handshake, and the client classifies
        # HTTP statuses as NON-terminal ON PURPOSE (during a deploy Traefik
        # answers 404/502/503). The result was a revoked/removed executor
        # reconnecting forever, with the client's terminal branch becoming dead
        # code. We accept and close right after: nothing is processed and the
        # registry is NOT populated.
        close_code = _MTLS_WS_CODE.get(exc.reason, 4401)
        # The close `reason` fits in 123 bytes in the frame — truncates with slack.
        close_reason = (exc.detail or "")[:100]
        logger.warning(
            "Executor '%s' recusado na autenticação mTLS (%s) — fechando com code=%d.",
            executor_id, exc.reason, close_code,
        )
        try:
            await ws.accept()
            await fechar_ws_do_executor(ws, code=close_code, reason=close_reason)
        except Exception as close_exc:
            logger.debug(
                "Falha ao notificar deny ao executor '%s': %s", executor_id, close_exc,
            )
        finally:
            encerrar_saida(ws)
        return None


# ── 2. Abertura ──────────────────────────────────────────────────────────────


@dataclass(eq=False)
class _Sessao:
    """What an accepted connection carries from the accept to the teardown."""

    executor_id: str
    ws: WebSocket
    # THIS session's connection in the registry: at the end, its last contact
    # becomes the "visto há" (seen ... ago). None when another session registered
    # over it before the check — then this one's end is not written (see
    # `_abrir_sessao`).
    minha_conexao: Any
    # This connection's queue + drainer: the loop only validates and enqueues,
    # never waits for Redis/Postgres. See `_drenar_inbox`.
    inbox: _InboxQueue
    drain_task: asyncio.Task
    # job_results in flight in the drainer. The teardown waits for them before
    # cancelling: cutting a split commit in the middle leaves the run terminal in
    # the database without ever publishing `__workflow_complete__` (panel
    # spinning forever).
    inflight: set[asyncio.Task]
    descartes: dict
    # The revocation check (`_vigiar_revogacao`). Strong reference (asyncio
    # only keeps weakrefs); cancelled on teardown.
    vigia: asyncio.Task
    # Counter of consecutive invalid JSONs — avoids flapping from a buggy
    # executor that sends a corrupted payload repeatedly.
    invalid_json_streak: int = 0
    # The version and system_info belong to the connection: those of the FIRST
    # handshake apply. The following ones write nothing — each was a SELECT +
    # UPDATE in the database, with no limit, and a different system_info only in
    # this worker's memory made the screen change depending on which worker
    # answered.
    identificacao_gravada: bool = False


async def _abrir_sessao(ws: WebSocket, executor_id: str, tetos: _Tetos) -> _Sessao:
    """Accepts the connection, registers it, schedules the retention purge and sets up
    the session's queue, drainer and watcher.

    Outside the handler's `finally`, as it always was: the teardown only runs for
    a session that managed to open completely."""
    await ws.accept()

    await executor_registry.register(
        executor_id, ws,
        max_concurrent_limit=tetos.max_concurrent,
        max_queue_limit=tetos.max_queue,
    )

    # In a separate task on purpose: the handshake cannot wait for a database
    # query, and a failure here must not drop the connection that just came up.
    # Strong reference required: asyncio keeps only weakrefs to tasks, and
    # without this the purge may be garbage-collected in the middle of the
    # database query — the same care as `_orphan_check_tasks` on teardown.
    _purge_tasks_pendentes.add(
        t := asyncio.create_task(_purgar_pendentes(executor_id), name=f"purge-{executor_id[:8]}")
    )
    t.add_done_callback(_purge_tasks_pendentes.discard)

    # THIS session's connection: at the end, its last contact becomes the "visto
    # há" (seen ... ago). Stored now because, by the teardown, the registry may
    # hold another one — and checked by socket, because another session may have
    # registered over it between the register and here (then this one's end is
    # not written).
    minha_conexao = executor_registry.get(executor_id)
    if getattr(minha_conexao, "websocket", None) is not ws:
        minha_conexao = None

    inbox = _InboxQueue(maxsize=_INBOX_MAXSIZE)
    # From the websocket itself, not from the registry: a takeover may remove this
    # connection from there before the queue empties (see `_InboxQueue.ip_da_conexao`).
    inbox.ip_da_conexao = ip_do_websocket(ws)
    inflight: set[asyncio.Task] = set()
    drain_task = asyncio.create_task(
        _drenar_inbox(executor_id, inbox, inflight), name=f"inbox-{executor_id[:8]}",
    )
    descartes = _novo_contador_de_descartes()
    vigia = asyncio.create_task(_vigiar_revogacao(executor_id, ws), name=f"revogacao-{executor_id[:8]}")
    return _Sessao(
        executor_id=executor_id, ws=ws, minha_conexao=minha_conexao,
        inbox=inbox, drain_task=drain_task, inflight=inflight,
        descartes=descartes, vigia=vigia,
    )


async def _purgar_pendentes(executor_id: str) -> None:
    """Pending retention: this executor's local artifacts that expired while the
    machine was off. The periodic loop would only come by within up to an hour,
    and in that interval there is expired personal data on the user's disk —
    reconnecting is the first moment the order can be delivered."""
    from app.core.artifact_cleanup import purgar_pendentes_do_executor
    try:
        n = await purgar_pendentes_do_executor(executor_id)
        if n:
            logger.info(
                "Executor '%s': %d artefato(s) local(is) vencido(s) purgado(s) na reconexão.",
                executor_id, n,
            )
    except Exception as exc:
        logger.warning(
            "Executor '%s': falha ao purgar artefatos pendentes na reconexão (%s). "
            "O ciclo periódico tenta de novo.", executor_id, exc,
        )


# ── 3. Each message ──────────────────────────────────────────────────────────

# Consecutive invalid JSONs that drop the session (close 1003).
_MAX_INVALID_JSON_STREAK = 5


async def _tratar_mensagem(sessao: _Sessao, raw: str) -> bool:
    """One message from the executor: parse, schema, handshake gate and dispatch
    by type (`_TRATADORES`).

    False when the session is over — the close was already sent (too many invalid
    JSONs or an unsupported protocol version)."""
    executor_id, ws = sessao.executor_id, sessao.ws
    try:
        msg = json.loads(raw)
        sessao.invalid_json_streak = 0  # reset after a valid parse
    except json.JSONDecodeError as exc:
        return await _json_invalido(sessao, raw, exc)

    msg_type = msg.get("type")

    # ── Schema validation: required fields per type ─────────────────────────
    missing = _missing_fields(msg_type, msg) if isinstance(msg_type, str) else []
    if missing:
        logger.warning(
            "Executor '%s' enviou '%s' com campos obrigatórios ausentes: %s",
            executor_id, msg_type, missing,
        )
        _responder_erro(
            ws, executor_id, "invalid_schema",
            missing_fields=missing, message_type=msg_type,
        )
        return True

    # SEC: the handshake must be the FIRST message — blocks any other type
    # until the executor identifies itself. This becomes a barrier against
    # spurious messages from badly implemented executors or adversaries
    # that managed to connect but did not complete the contract.
    conn_state = executor_registry.get(executor_id)
    if conn_state and not getattr(conn_state, "handshake_received", False):
        if msg_type != "handshake":
            logger.warning(
                "Executor '%s' enviou '%s' antes de handshake — rejeitado.",
                executor_id, msg_type,
            )
            _responder_erro(ws, executor_id, "handshake_required")
            return True
        if not await _protocolo_aceito(sessao, msg):
            return False
        conn_state.handshake_received = True

    # Only text is a type: a list or object `type` does not work as a key, and
    # falls into "unknown" like any other.
    tratador = _TRATADORES.get(msg_type) if isinstance(msg_type, str) else None
    if tratador is None:
        logger.debug("Executor '%s' enviou tipo desconhecido: %s", executor_id, msg_type)
        return True
    await tratador(sessao, msg_type, msg, len(raw))
    return True


async def _json_invalido(sessao: _Sessao, raw: str, exc: json.JSONDecodeError) -> bool:
    """Answers `invalid_json` and counts the streak. On the
    `_MAX_INVALID_JSON_STREAK`-th in a row, closes with 1003 and returns False."""
    sessao.invalid_json_streak += 1
    logger.warning(
        "Executor '%s' enviou JSON inválido (streak=%d): %s | raw=%r",
        sessao.executor_id, sessao.invalid_json_streak, exc, raw[:200],
    )
    # Feedback to the executor — avoids a loop where it waits for an ACK and retries.
    _responder_erro(sessao.ws, sessao.executor_id, "invalid_json", detail=str(exc)[:200])
    if sessao.invalid_json_streak < _MAX_INVALID_JSON_STREAK:
        return True
    logger.error(
        "Executor '%s' enviou %d JSONs inválidos seguidos — desconectando.",
        sessao.executor_id, sessao.invalid_json_streak,
    )
    await fechar_ws_do_executor(sessao.ws, code=1003, reason="Too many invalid messages.")
    return False


async def _protocolo_aceito(sessao: _Sessao, msg: dict) -> bool:
    """Protocol validation of the first handshake: rejects executors with an
    incompatible version — answers `unsupported_protocol_version`, closes with
    4426 and returns False."""
    claimed = str(msg.get("protocol_version") or "1.0")
    if claimed in SUPPORTED_PROTOCOL_VERSIONS:
        return True
    logger.warning(
        "Executor '%s' declarou protocol_version='%s' não suportado (aceitos: %s).",
        sessao.executor_id, claimed, sorted(SUPPORTED_PROTOCOL_VERSIONS),
    )
    _responder_erro(
        sessao.ws, sessao.executor_id, "unsupported_protocol_version",
        server_protocol_version=PROTOCOL_VERSION,
        supported=list(SUPPORTED_PROTOCOL_VERSIONS),
    )
    await fechar_ws_do_executor(sessao.ws, code=4426, reason="Unsupported protocol version.")
    return False


# The per-type handlers all have the same signature:
# (session, type, message, frame size in bytes).


async def _tratar_heartbeat(sessao: _Sessao, _tipo: str, _msg: dict, _frame_bytes: int) -> None:
    await executor_registry.update_last_seen(sessao.executor_id)


async def _tratar_capacity(sessao: _Sessao, _tipo: str, msg: dict, _frame_bytes: int) -> None:
    capacity, cap_errors = _sanitize_capacity(sessao.executor_id, msg)
    if capacity is None:
        logger.warning(
            "Executor '%s' enviou capacity inválida: %s", sessao.executor_id, cap_errors,
        )
        _responder_erro(sessao.ws, sessao.executor_id, "invalid_capacity", errors=cap_errors)
        return
    # `update_capacity` already updates last_seen_at and renews
    # presence — the `update_last_seen` that used to come right here doubled
    # the renewal Lua EVAL every 10 seconds, per executor.
    await executor_registry.update_capacity(sessao.executor_id, capacity)


async def _tratar_handshake(sessao: _Sessao, _tipo: str, msg: dict, _frame_bytes: int) -> None:
    """The first handshake writes the connection's identification (version and
    system_info); the following ones only renew presence."""
    executor_id = sessao.executor_id
    if sessao.identificacao_gravada:
        await executor_registry.update_last_seen(executor_id)
        return

    sessao.identificacao_gravada = True
    conn = executor_registry.get(executor_id)
    ver = _sanitize_executor_version(executor_id, msg.get("executor_version"))
    raw_sys_info = msg.get("system_info")
    sys_info = (
        _sanitize_system_info(executor_id, raw_sys_info)
        if raw_sys_info is not None else None
    )
    if conn:
        if ver:
            conn.executor_version = ver
        if sys_info:
            conn.system_info = sys_info
    if sys_info or ver:
        await _persistir_identificacao(executor_id, ver, sys_info)
    await executor_registry.update_last_seen(executor_id)


async def _persistir_identificacao(executor_id: str, ver: str | None, sys_info: dict | None) -> None:
    """Persists version and system_info to the database (once per connection, see
    `identificacao_gravada`): the executors screen reads both from the
    database — the connection only exists on the WebSocket's worker. The
    version used to stay only in memory, and the screen's "versão" (version)
    column showed "—" for every executor."""
    async with get_session_async() as db:
        result = await db.execute(
            select(Executor).where(Executor.id_hash == executor_id)
        )
        ag = result.scalar_one_or_none()
        if ag:
            if sys_info:
                ag.system_info = sys_info
            if ver:
                ag.executor_version = ver
            await db.commit()


async def _enfileirar(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    """Stops the connection's drainer (see `_drenar_inbox`)."""
    await _enfileirar_mensagem(
        sessao.executor_id, sessao.inbox, sessao.descartes, msg_type, msg, frame_bytes,
    )


async def _tratar_node_event(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    if _node_event_allowed(sessao.executor_id, msg):
        await _enfileirar(sessao, msg_type, msg, frame_bytes)


async def _tratar_sync_event(sessao: _Sessao, msg_type: str, msg: dict, frame_bytes: int) -> None:
    if _sync_event_allowed(sessao.executor_id, msg):
        await _enfileirar(sessao, msg_type, msg, frame_bytes)


# The dispatch: the keys are the protocol's TIPOS_DO_EXECUTOR
# (flow/utils/protocolo_ws.py). A type not in here only goes to debug.
_TRATADORES: dict[str, Callable[[_Sessao, str, dict, int], Awaitable[None]]] = {
    "handshake": _tratar_handshake,
    "heartbeat": _tratar_heartbeat,
    "capacity": _tratar_capacity,
    # The three below cost Redis (and the job_result, Postgres):
    # they are validated here and processed by the drainer, so that the
    # next receive_text() does not wait for I/O.
    "job_result": _enfileirar,
    "node_event": _tratar_node_event,
    "sync_event": _tratar_sync_event,
    # Job receipt ACK: clears the pending ACK and promotes the
    # run from 'pending' to 'running' (see `_record_job_ack`). The
    # promotion is an UPDATE in Postgres, so it goes through the drainer —
    # on the same queue as the job_result, which arrives after it.
    "ack": _enfileirar,
    # Jobs the executor HAS. The reconciliation closes the runs it
    # does not have (see `_reconciliar_inventario`) and goes through the
    # drainer ON PURPOSE: on the same queue, a job_result sent before the
    # inventory is written before the inventory is checked — otherwise
    # the just-finished run would look lost.
    "inventario": _enfileirar,
}


# ── 4. Teardown ──────────────────────────────────────────────────────────────


async def _encerrar_sessao(sessao: _Sessao) -> None:
    """The end of the session, in this order: the watcher and the sends stop, the
    queue empties (before the unregister), the presence goes away, the orphan
    check is scheduled and, last, the session's end is stamped."""
    executor_id, ws = sessao.executor_id, sessao.ws
    sessao.vigia.cancel()
    # Nothing else goes out through this socket: during the flush below (up to
    # 10 s) the connection stays registered and the relay listener alive, and a
    # job relayed now would hit the dead socket with nobody closing the run.
    encerrar_envios(ws)
    await _esvaziar_a_fila(sessao)
    if sessao.descartes["total"]:
        logger.warning(
            "Executor '%s': %d mensagem(ns) descartada(s) por fila cheia nesta conexão.",
            executor_id, sessao.descartes["total"],
        )
    # expected_ws=ws ensures we only remove if the registered WS is still
    # this one — avoids killing a fast reconnection that registered WS_novo.
    await executor_registry.unregister(executor_id, expected_ws=ws)
    _drop_rate_state(executor_id)
    # End of this socket's life: its outgoing queue leaves the map (see
    # `encerrar_saida`) — this also applies when the unregister did not close it
    # because the executor already reconnected in another session.
    encerrar_saida(ws)
    _agendar_verificacao_de_orfaos(executor_id)
    # Last on purpose: a cancellation here (shutdown) only loses this
    # stamp, never the orphan check above. Best-effort and with a
    # deadline — the teardown does not wait for a database that is down; the
    # next handshake writes it again.
    if sessao.minha_conexao is not None:
        try:
            await asyncio.wait_for(
                _gravar_fim_da_sessao(executor_id, sessao.minha_conexao.last_seen_at),
                timeout=_FIM_DA_SESSAO_TIMEOUT,
            )
        except Exception as exc:
            logger.warning("Executor '%s': fim da sessão não gravado (%r).", executor_id, exc)


async def _esvaziar_a_fila(sessao: _Sessao) -> None:
    """FLUSH BEFORE the unregister: whatever is still in the queue are the run's
    LAST events (including the job_result and the __workflow_complete__).
    Cancelling the drainer here would leave the user's panel spinning
    forever on a run that actually finished."""
    executor_id, inbox, drain_task, inflight = (
        sessao.executor_id, sessao.inbox, sessao.drain_task, sessao.inflight,
    )
    try:
        await asyncio.wait_for(
            _encerrar_drenagem(inbox, drain_task), timeout=_INBOX_FLUSH_TIMEOUT,
        )
    except Exception as exc:
        logger.warning(
            "Executor '%s': drenagem final não concluiu em %.0fs (%s) — "
            "eventos residuais podem ter sido perdidos.",
            executor_id, _INBOX_FLUSH_TIMEOUT, exc,
        )
        # Graceful stop before the cancellation: a bare `cancel()` could land
        # in the middle of writing a job_result (database terminal, canvas
        # without the `__workflow_complete__`). The write runs shielded in its
        # own task; here we give it the grace period to finish.
        drain_task.cancel()
        if inflight:
            pendentes = set(inflight)
            _, faltando = await asyncio.wait(
                pendentes, timeout=_INBOX_CANCEL_GRACE,
            )
            if faltando:
                logger.error(
                    "Executor '%s': %d gravação(ões) de job_result ainda em voo "
                    "após %.0fs de carência — run pode ficar sem conclusão.",
                    executor_id, len(faltando), _INBOX_CANCEL_GRACE,
                )
        # What the cancelled drainer did not get to consume: telemetry may
        # vanish, job_result may not.
        try:
            await asyncio.wait_for(
                _resgatar_job_results_pendentes(executor_id, inbox),
                timeout=_INBOX_CANCEL_GRACE,
            )
        except Exception as resgate_exc:
            logger.error(
                "Executor '%s': resgate dos job_result pendentes não concluiu: %s",
                executor_id, resgate_exc,
            )


def _agendar_verificacao_de_orfaos(executor_id: str) -> None:
    """Orphan check in a separate task: it waits for a grace period
    (see `_fail_orphan_runs_if_gone`) and must not hold up the WS teardown."""
    try:
        check = asyncio.create_task(
            _fail_orphan_runs_if_gone(executor_id),
            name=f"orphan-check-{executor_id[:8]}",
        )
        # asyncio keeps only weakrefs to tasks — without this strong reference
        # the task may be garbage-collected in the middle of the sleep.
        _orphan_check_tasks.add(check)
        check.add_done_callback(_orphan_check_tasks.discard)
    except RuntimeError:
        # Loop already shutting down: the orphan_runs_watchdog takes care of it on the way back.
        logger.debug(
            "Sem loop para agendar verificação de órfãos de '%s' — watchdog assume.",
            executor_id,
        )
