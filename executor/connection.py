# executor/connection.py
"""
Executor WebSocket client with:
  - Authentication via mTLS cert (no intermediate JWT)
  - Reconnect with exponential backoff
  - Periodic sending of heartbeat and capacity
  - Receiving and queueing of jobs
"""
import asyncio
import json
import logging
import time
from datetime import datetime, date

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError
from websockets.frames import Close

from flow.utils.backoff import with_jitter
from flow.utils.protocolo_ws import (
    PROTOCOL_VERSION,
    ERROR_TYPE,
    SERVER_TYPES,
    shrink_stats,
)
from flow.utils.publisher.reducao import (
    CONTROL_FIELDS,
    NODE_EVENT_BYTES_CEILING,
    shrink_node_event,
)
from executor import config
from executor.job_queue import ExecutorJobQueue
from executor.job_validator import JobValidationError, validate_control_message

logger = logging.getLogger(__name__)


def _json_default(obj):
    """Serializes types the standard json does not support (Timestamp, datetime, date, etc.)."""
    # pandas.Timestamp e datetime.datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # numpy int/float
    try:
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    # pandas.Timestamp (in case it is not a datetime subclass in this environment)
    try:
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, pd.NA.__class__):
            return None
        # GeoDataFrame/DataFrame — nunca serializar inteiro, retorna apenas resumo
        if isinstance(obj, pd.DataFrame):
            return f"<DataFrame {obj.shape[0]}x{obj.shape[1]}>"
    except ImportError:
        pass
    # Limita strings muito longas para evitar payload gigante
    s = str(obj)
    if len(s) > 500:
        return s[:500] + "...[truncated]"
    return s


# WebSocket payload limit (16 MB) — matches uvicorn's ws_max_size in app/main.py.
# Protects against a crash from a large message and sets the auto-truncation limit in
# _dumps_result.
_MAX_WS_PAYLOAD = 16 * 1024 * 1024


def _dumps_result(obj: dict) -> str:
    """Serializes a job_result; truncates via 'stats' if it exceeds the WS limit.

    EXCLUSIVE to job_result. The truncation here knows how to touch a single key —
    'stats' —, which only exists in this message type. Reusing this function
    for node_event reduced nothing (the weight of the event is in extra/error),
    injected a spurious 'stats' key into the event and logged "job_result
    descartado" (discarded) for something that was neither a job_result nor discarded.
    node_event has its own _dumps_event.
    """
    result = json.dumps(obj, default=_json_default)
    if len(result) > _MAX_WS_PAYLOAD:
        # Truncation of the protocol's `stats` (flow/utils/protocolo_ws.py), the same
        # one the server reapplies: drops the per-node stats, which are heavy, and
        # keeps the control keys (HTTP response, artifacts, metrics).
        # __response__ is required for the synchronous webhook pattern — without
        # it, webhook_router's BRPOP hangs. The yardstick here is the whole
        # message against the WS frame.
        _stats, result, preservou = shrink_stats(
            obj.get("stats") or {}, len(result), _MAX_WS_PAYLOAD,
            lambda stats: json.dumps({**obj, "stats": stats}, default=_json_default),
        )
        if preservou:
            logger.warning(
                "job_result excedeu %d bytes; stats por-nó removidos, chaves de controle preservadas.",
                _MAX_WS_PAYLOAD,
            )
        else:
            # Not even the control keys alone fit: they go too — the caller
            # will get a timeout or a clear error.
            logger.warning(
                "job_result excede %d bytes mesmo após preservar chaves de controle — descartado.",
                _MAX_WS_PAYLOAD,
            )
    return result


def _dumps_event(obj: dict) -> str:
    """Serializes a node_event; above the ceiling, reduces it by the protocol rule.

    The `default=_json_default` is still required: a non-serializable object
    in `extra` raised TypeError, fell into the sender's generic branch and recycled
    the same event in a loop. The ceiling and the reduction are those of
    flow/utils/publisher/reducao.py — the same rule the server reapplies
    before Redis: it cuts the event's weight (traceback, debug, stdout that does not
    fit) and keeps what the panel uses, `output_columns` and `duration_ms`
    included.
    """
    result = json.dumps(obj, default=_json_default)
    if len(result) <= NODE_EVENT_BYTES_CEILING:
        return result
    logger.warning(
        "node_event node=%s status=%s de %d bytes excede %d — reduzido.",
        obj.get("node"), obj.get("status"), len(result), NODE_EVENT_BYTES_CEILING,
    )
    return shrink_node_event(obj, result, default=_json_default)


# The server → executor type allowlist is SERVER_TYPES, from the protocol
# vocabulary in flow/utils/protocolo_ws.py (see `_receive_loop`).
#
# `purge_artifacts` deletes files from the user's disk. It is already covered by
# _SIGNED_SERVER_MESSAGES below (every `control` requires an Ed25519 signature) — without
# that, whoever won the connection would have a data-destruction channel.
_CONTROL_ACTIONS = frozenset({"revoked", "shutdown", "config_changed", "purge_artifacts"})

# Types that require an Ed25519 signature from the server before any effect.
# Keep in sync with SIGNED_MESSAGE_TYPES in app/core/control_crypto.py.
_SIGNED_SERVER_MESSAGES = frozenset({"control", "cancel"})

# Interval of the heartbeat sent to the server
_HEARTBEAT_INTERVAL = 30  # segundos
# Interval for sending the capacity report
_CAPACITY_INTERVAL = 10  # segundos
# Interval of the job inventory (see `_inventory_loop`). The first goes out right
# after the handshake; from then on, one per minute is enough — the server only
# closes lost runs more than 3 min old.
_INVENTORY_INTERVAL = 60  # segundos
# Ceiling on ids per inventory. Above it, the inventory goes out marked `truncado` and the
# server closes nothing for absence (there is no way to know what was left out).
_INVENTARIO_MAX = 1000
# For how long a SENT result still counts as "on its way" — see
# `_remember_sent`. Slack over what the server takes to process it
# (draining the inbox of a connection that dropped: ~20 s); after that the server's own
# result key (TTL 300 s) already protects it. Short on purpose:
# on a busy executor the sent ones must not fill the whole inventory.
_SENT_TTL_S = 90.0
_SENT_MAX = 2000
# Reason of the 'cancelled' result of a job the executor did not have when the
# cancellation arrived (see `_close_unknown_cancellation`).
_UNKNOWN_CANCELLATION_REASON = (
    "Cancelada. O executor não tinha esta execução quando o pedido chegou — "
    "ela já tinha se perdido antes de rodar ou de o resultado sair."
)
# Consecutive samples of a full pool before announcing zero capacity — see
# `_pool_saturated`. With the capacity's 10s tick, that is ~10s of uninterrupted
# thread queue: a dispatch spike does not pass, an orphan thread does.
_POOL_SATURATED_TICKS = 2

# Minimum duration of a WS session to consider it "stable" and reset the backoff.
# Without this guard, any post-accept close (4408 heartbeat timeout, 4426
# protocol, 1003 invalid JSON, 1011, network drop) reset delay=1 and the
# executor redid the TLS+mTLS handshake in a tight loop, hammering the server.
_SESSION_STABLE_SECONDS = 60
# Duration OF THE SESSION (counted from the accepted handshake onward) from which it
# has at least PROGRESSED and the accumulated backoff steps back — see
# `_apply_session_backoff_reset`. Time spent in connect/TLS/upgrade does not count:
# an upgrade hanging for 10s is not progress, and treating it as such undid the
# exponential backoff exactly on the failure most expensive for the server.
_SESSION_PROGRESS_SECONDS = 5

# Ceiling on resend attempts for the same node_event. node_event is UI
# telemetry: losing a graph update is bad, but re-queueing forever an
# event that fails deterministically (non-serializable payload) traps the
# queue's single consumer in a loop and hangs main.py's _event_queue.join().
_MAX_EVENT_SEND_ATTEMPTS = 3
# Equivalent ceiling for job_result. Mandatory symmetry: the result loop has the
# SAME topology (single consumer, requeue at the tail), so a result that
# fails deterministically (circular reference in stats, an object whose
# __str__ raises inside _json_default) spun forever at 1 attempt/s,
# held the shutdown's _result_queue.join() for the entire 30s timeout and
# never let the queue through. The ceiling is higher than node_event's because
# a result is business data, not telemetry — and when giving up we do NOT call
# mark_sent(): the outbox copy (sanitized, without stats — precisely the field
# that tends to be the poison) is resent on the next start.
_MAX_RESULT_SEND_ATTEMPTS = 5
# Internal attempt-count key. Removed from the payload before the send —
# never travels to the server.
_ATTEMPTS_KEY = "__send_attempts__"
# Backoff after a generic send failure. It is per BURST, not per item: the pause only
# kicks in after _SEND_FAIL_STREAK_LIMIT CONSECUTIVE failures and the counter resets
# on every successful send.
#
# It used to be 1.0s per ITEM, and since these loops have a single consumer the queue
# became a funnel of 1 event/s: a transient transport error with a few
# hundred events in the queue froze the canvas for minutes and also filled the
# queue, which then started discarding everything that arrived. The ceiling is still the same
# 1.0s — what changes is paying nothing for an isolated failure.
_SEND_RETRY_PAUSE = 1.0
_SEND_RETRY_PAUSE_MIN = 0.05
_SEND_FAIL_STREAK_LIMIT = 3


def _burst_pause(consecutive_failures: int) -> float:
    """How long to sleep after N consecutive send failures. 0 up to the burst limit."""
    if consecutive_failures < _SEND_FAIL_STREAK_LIMIT:
        return 0.0
    growth = _SEND_RETRY_PAUSE_MIN * (2 ** (consecutive_failures - _SEND_FAIL_STREAK_LIMIT))
    return min(_SEND_RETRY_PAUSE, growth)

# Close codes the server emits in the post-handshake accept() (executor_ws_router)
# to deny authoritatively: 4401 not authenticated, 4403 revoked/forbidden,
# 4404 nonexistent executor. Reconnecting in these cases only generates noise.
_TERMINAL_CLOSE_CODES = frozenset({4401, 4403, 4404})


# System metrics live in executor/sysinfo.py since the local panel
# started reading them too — before, the only consumer was the capacity payload.
from executor.sysinfo import _collect_system_info, _get_dynamic_metrics  # noqa: E402


def _classify_connection_error(exc: Exception) -> tuple[str, bool, bool]:
    """Translates WS connection exceptions into a friendly message for the operator.

    Returns `(mensagem, include_traceback, terminal)`:
      - `mensagem` — explanatory text in Portuguese, without a stack trace.
      - `include_traceback` — True for genuinely unexpected errors
        (bugs, exotic C bindings). False for well-categorized errors
        (they would pollute the log on every backoff).
      - `terminal` — True when the server authoritatively denies. IMPORTANT:
        the app NEVER denies via HTTP status in the handshake — every authoritative deny
        (revoked cert, executor removed/not found, invalid status) arrives
        as WS close code 4401/4403/4404 (see executor_ws_router.py). Hence, an
        HTTP 4xx/5xx status in the handshake can only come from the EDGE (Traefik/Cloudflare)
        and, during a deploy, is transient (a proxy with no route yet to the freshly
        recreated backend returns 404/502/503). That is why NO HTTP status is treated
        as terminal here — only the 44xx close codes (further below) are.
    """
    from websockets.exceptions import InvalidStatus, InvalidURI, ConnectionClosed

    if isinstance(exc, InvalidStatus):
        status = getattr(exc.response, "status_code", None)
        # HTTP 4xx/5xx in the handshake = response from the reverse proxy, NOT from the app.
        # During deploy/restart Traefik answers 404 (no route yet) or
        # 502/503 (backend starting). All transient → reconnect with backoff.
        # The app's real deny (executor removed/revoked) comes as close 4404/4403,
        # treated as terminal in the ConnectionClosed section. Treating HTTP 404 as
        # terminal took the executor down on every deploy (exit 0, the container did not
        # restart with restart: on-failure).
        return (
            f"Handshake recusado pelo proxy (HTTP {status or '???'}) — provavel "
            "servidor em deploy/reinicio (sem rota ou backend subindo).",
            False, False,
        )

    if isinstance(exc, InvalidURI):
        return (f"URL do servidor invalida: {exc}", False, True)

    # Specific SSL errors — expired cert, invalid chain, etc.
    # `ssl.SSLError` falls into `OSError` (inherits) — must come BEFORE OSError.
    import ssl as _ssl
    if isinstance(exc, _ssl.SSLError):
        reason = getattr(exc, "reason", "") or ""
        msg = str(exc)
        # Known libssl patterns:
        if "CERTIFICATE_VERIFY_FAILED" in msg or "CERTIFICATE_VERIFY_FAILED" in reason:
            if "expired" in msg.lower():
                return (
                    "Cert mTLS local expirado. O renewal automatico falhou — "
                    "refaca enrollment com novo OTP OU verifique renewal.py "
                    "logs para diagnostico.",
                    False, True,
                )
            return (
                "Falha na verificacao do cert TLS do servidor. Verifique se "
                "atlans-root.crt esta atualizado (delete o arquivo em "
                "EXECUTOR_CERT_DIR e reinicie para forcar re-download).",
                False, False,
            )
        if "SSLV3_ALERT_CERTIFICATE_EXPIRED" in msg or "certificate has expired" in msg.lower():
            return (
                "Cert mTLS do cliente expirado. Refaca enrollment com novo OTP.",
                False, True,
            )
        if "SSLV3_ALERT_HANDSHAKE_FAILURE" in msg or "handshake_failure" in reason.lower():
            return (
                "TLS handshake rejeitado pelo servidor. Cert mTLS local pode "
                "estar corrompido ou nao pertencer mais a esta CA. "
                "Refaca enrollment.",
                False, True,
            )
        return (f"Erro TLS: {reason or msg}", False, False)

    if isinstance(exc, ConnectionClosed):
        code = getattr(exc, "code", None)
        reason = getattr(exc, "reason", None) or ""
        # Codes 4401/4403/4404 are the ones the server emits in the post-handshake
        # accept() (executor_ws_router). Semantics aligned with HTTP.
        terminal = code in _TERMINAL_CLOSE_CODES
        return (f"Conexao fechada pelo servidor (code={code} reason={reason!r}).", False, terminal)

    if isinstance(exc, OSError):
        return (
            f"Falha de rede: {type(exc).__name__}: {exc}. "
            "Verifique DNS, firewall e conectividade com o servidor.",
            False, False,
        )

    # Categoria desconhecida — inclui traceback para diagnostico
    return (f"Erro inesperado na conexao: {type(exc).__name__}: {exc}.", True, False)


class ExecutorConnection:
    """
    Manages the executor's WebSocket connection with the server.

    Usage:
        conn = ExecutorConnection(job_queue, result_queue)
        await conn.run()  # infinite loop with automatic reconnect
    """

    def __init__(self, job_queue: ExecutorJobQueue, result_queue: asyncio.Queue,
                 event_queue: asyncio.Queue | None = None,
                 drive_event_queue: asyncio.Queue | None = None,
                 stats=None, thread_pool=None):
        self._queue      = job_queue
        # Pool where the nodes run (main.py installs it as the loop's default). It is
        # here only so the capacity can be HONEST: threads stuck in a
        # PythonScript in an infinite loop do not show up in queued/running, which
        # count jobs — the executor kept announcing free capacity with the
        # whole pipeline stalled, and the server kept dispatching to it.
        self._thread_pool = thread_pool
        self._pool_saturated_streak = 0
        self._results    = result_queue
        self._events     = event_queue
        self._drive_events = drive_event_queue
        self._should_reconnect = True
        self.restart_requested: bool = False
        # Message of the server's authoritative deny (close 4401/4403/4404), or
        # None. Unlike `restart_requested`, this does NOT resolve itself:
        # only a new enrollment brings the executor back up. Whoever supervises the
        # process needs to know the difference — restarting a revoked executor is
        # an infinite loop against a server that has already said no.
        self.terminal_deny: str | None = None
        # Signals "don't wait for the backoff, try now" — see _esperar_retry.
        self._retry_now = asyncio.Event()
        # Null object instead of None: the call sites call self._stats.on_X()
        # directly, without an `if` scattered over every connection state point.
        if stats is None:
            from executor.stats import NullStats
            stats = NullStats()
        self._stats = stats
        # Socket of the CURRENT session, or None during the reconnect backoff.
        # Exists only for `push_capacity()` — the rest of the code receives the `ws`
        # as a parameter, which is harder to misuse.
        self._ws = None
        # Instant the WS handshake was ACCEPTED (not the start of the attempt),
        # or None when the attempt never got to open a session. It is the only honest
        # marker for the backoff: see `_apply_session_backoff_reset`.
        self._session_started_at: float | None = None
        # job_id -> instant the result was sent; see `_remember_sent`.
        self._sent: dict[str, float] = {}

    async def push_capacity(self) -> None:
        """Sends a capacity report NOW, outside the `_capacity_loop` tick.

        The periodic loop sleeps BEFORE sending, so a state change only
        reached the server up to 10s later. That matters in one specific case: when
        entering drain, `get_capacity()` starts announcing saturation to
        leave the least-loaded ranking, and during those 10s dispatch could still
        pick this executor — the job came back as "Executor em shutdown." and the
        run closed as FAILED without failover. Pushing right away closes the window.

        Never raises: it is called from within the shutdown path, and failing to
        notify the server must not prevent the executor from shutting down.
        """
        ws = self._ws
        if ws is None:
            logger.debug("push_capacity: sem sessão WS ativa — nada a enviar.")
            return
        try:
            cap = self._build_capacity()
            await ws.send(json.dumps({"type": "capacity", **cap}))
            logger.info(
                "Capacity enviado imediatamente (queued=%s running=%s).",
                cap.get("queued"), cap.get("running"),
            )
        except Exception as exc:
            logger.warning("Não foi possível enviar capacity imediato: %s", exc)

    # ── Main loop (automatic reconnect) ───────────────────────────────────────

    async def run(self):
        """Infinite loop: connects, receives jobs, reconnects with backoff on failure."""
        delay = 1
        while True:
            # `t0` serves ONLY the log ("conexao encerrada apos X"): it measures the
            # whole attempt, TCP + TLS/mTLS + upgrade included. What decides
            # the backoff is `self._session_started_at`, set after the
            # handshake is accepted — see `_apply_session_backoff_reset`.
            t0 = time.monotonic()
            # Reset on every attempt: without this the good session from the previous round
            # would make the backoff of an attempt that never even opened a socket look like
            # a "healthy session" and step back.
            self._session_started_at = None
            self._stats.on_connecting()
            try:
                await self._connect_and_run()
                if not self._should_reconnect:
                    logger.info("Executor encerrado pelo servidor.")
                    self._stats.on_disconnected(terminal=True)
                    break
                # Clean return = the server closed the connection without error (close 1000/1001)
                # or the receive_loop ended. It is still a disconnection: it needs
                # the same sleep as the exception path, otherwise it reconnects in a spin.
                delay = self._apply_session_backoff_reset(delay)
                actual = with_jitter(delay)
                logger.warning(
                    "Conexão encerrada pelo servidor após %.1fs. Reconectando em %.1fs.",
                    time.monotonic() - t0, actual,
                )
                self._stats.on_disconnected(next_retry_s=actual)
                rescheduled = await self._esperar_retry(actual)
                delay = 1 if rescheduled else min(delay * 2, config.RECONNECT_MAX_DELAY)
            except asyncio.CancelledError:
                logger.info("Conexão cancelada — encerrando.")
                self._stats.on_disconnected(terminal=True)
                break
            except Exception as exc:
                if not self._should_reconnect:
                    logger.info("Reconnect desabilitado — encerrando executor.")
                    self._stats.on_disconnected(terminal=True)
                    break

                msg, include_tb, terminal = _classify_connection_error(exc)

                if terminal:
                    # 401/403/404 from the server = authoritative deny (revoked cert,
                    # executor removed, id not found). Reconnecting in a loop
                    # only generates noise; stop the process and the operator sees the
                    # clear message in the logs. Runs again only after re-enrollment.
                    logger.error("%s Encerrando executor — refaça enrollment se necessario.", msg)
                    self._should_reconnect = False
                    self.terminal_deny = msg
                    self._stats.on_disconnected(terminal=True)
                    break

                delay = self._apply_session_backoff_reset(delay)
                # A 50-100% jitter avoids a thundering herd when N executors
                # reconnect in sync after a server outage. The formula
                # was born here and now lives in `flow/utils/backoff.py`, from which
                # the platform's other loops now read it.
                actual = with_jitter(delay)
                logger.error("%s Reconectando em %.1fs.", msg, actual, exc_info=include_tb)
                self._stats.on_disconnected(next_retry_s=actual)
                rescheduled = await self._esperar_retry(actual)
                delay = 1 if rescheduled else min(delay * 2, config.RECONNECT_MAX_DELAY)

    async def _esperar_retry(self, segundos: float) -> bool:
        """Sleeps until the next attempt, but wakes up if someone asks for it now.

        Returns True if the wait was cut short by `reconnect_now()` — the
        caller then resets the backoff, because whoever asked knows something the
        process did not (the network came back, the server came up). Without this, an
        operator who has just fixed the network would wait out the whole backoff,
        which reaches RECONNECT_MAX_DELAY (15s by default).
        """
        self._retry_now.clear()
        try:
            await asyncio.wait_for(self._retry_now.wait(), timeout=segundos)
            return True
        except asyncio.TimeoutError:
            return False

    def reconnect_now(self) -> bool:
        """Interrupts the backoff in progress. Returns False if there was no wait.

        Safe to call at any time: with the WS alive, the event just stays
        set and is cleared on the next wait.
        """
        if self._retry_now.is_set():
            return False
        self._retry_now.set()
        return True

    def _apply_session_backoff_reset(self, delay: int | float) -> int | float:
        """Adjusts the backoff according to the WS SESSION that has just ended.

        The clock starts at `self._session_started_at`, set after the
        handshake was ACCEPTED — never at the start of the attempt. Measuring the whole
        attempt broke the anti-spin defense in the most expensive scenario: a server in
        deploy/overload accepts the TCP and never completes the upgrade, the
        `websockets.connect` hits open_timeout (10s) and that wait counted
        as a "session that progressed". The delay was then halved and `run()`
        doubled it right after — halve-then-double is neutral —, so it oscillated 1<->2
        forever and the fleet redid the mTLS handshake every ~1s for hours.

        Three bands, not two:
          - healthy session (> _SESSION_STABLE_SECONDS): reset;
          - session that at least WORKED for a while
            (>= _SESSION_PROGRESS_SECONDS): steps back to a QUARTER. It has to be
            less than half precisely because the caller doubles right after: with
            /2 the net was zero and the band did not step back at all. Without this band, a
            59s session that dropped repeatedly (unstable network, proxy
            recycling the connection) never reduced the delay: it only grew, and the
            executor vanished from the panel for tens of seconds on every outage of
            a few seconds of real unavailability;
          - session that dies right after the handshake — or that never got to
            exist (`_session_started_at is None`: DNS, TCP refused, TLS
            rejected, hung upgrade): keeps the accumulated delay, which is what
            guarantees exponential growth against a repeated error.
        """
        inicio = self._session_started_at
        if inicio is None:
            return delay
        duracao = time.monotonic() - inicio
        if duracao > _SESSION_STABLE_SECONDS:
            return 1
        if duracao >= _SESSION_PROGRESS_SECONDS:
            return max(1, delay / 4)
        return delay

    async def _connect_and_run(self):
        ws_url = f"{config.SERVER_URL}/ws/executores/{config.EXECUTOR_ID}"

        logger.info("Conectando a %s ...", config.SERVER_URL)
        from executor.utils import is_local_server, build_mtls_ssl_context
        if is_local_server(config.SERVER_URL):
            ssl_ctx = None  # local ws:// does not need SSL
        else:
            # production wss:// with mTLS — cert + key + CA pinned at enrollment.
            # The executor's identity comes from the cert; the backend validates CN/serial and
            # checks the Redis blacklist. No intermediate JWT.
            ssl_ctx = build_mtls_ssl_context()
        async with websockets.connect(
            ws_url,
            # The application heartbeat (30s) is the source of truth. Native WS ping
            # was forcing a close at 10s when behind a proxy/Traefik with
            # latency — disabled to keep the pre-change behavior.
            ping_interval=None,
            close_timeout=10,
            ssl=ssl_ctx,
            max_size=_MAX_WS_PAYLOAD,  # matches uvicorn's ws_max_size
        ) as ws:
            logger.info("Conectado a %s (executor v%s).", config.SERVER_URL, config.EXECUTOR_VERSION)
            # Backoff marker: from HERE on there is a session. Everything that came
            # before (TCP, TLS/mTLS, upgrade) is attempt cost, not service
            # time — see `_apply_session_backoff_reset`.
            self._session_started_at = time.monotonic()
            self._stats.on_connected()
            # Handle of the live session, so `push_capacity()` can send outside the
            # _capacity_loop's 10s tick. Cleared in the `finally` below: during the
            # reconnect backoff there is NO socket, and sending to a dead ws would only
            # raise an exception in the shutdown path.
            self._ws = ws

            # Sends the handshake with the executor version and hardware info.
            # protocol_version declares compatibility — the server rejects it if
            # it is not in SUPPORTED_PROTOCOL_VERSIONS (flow/utils/protocolo_ws.py).
            sys_info = _collect_system_info()
            await ws.send(json.dumps({
                "type":             "handshake",
                "protocol_version": PROTOCOL_VERSION,
                "executor_version":    config.EXECUTOR_VERSION,
                **({"system_info": sys_info} if sys_info else {}),
            }))

            # Starts parallel work as Tasks to allow cancellation
            tasks: list[asyncio.Task] = [
                asyncio.create_task(self._heartbeat_loop(ws),     name="heartbeat"),
                asyncio.create_task(self._capacity_loop(ws),      name="capacity"),
                asyncio.create_task(self._inventory_loop(ws),    name="inventario"),
                asyncio.create_task(self._receive_loop(ws),       name="receive"),
                asyncio.create_task(self._result_sender_loop(ws), name="results"),
            ]
            if self._events is not None:
                tasks.append(asyncio.create_task(self._event_sender_loop(ws), name="events"))

            # Waits for the FIRST task to finish — normally _receive_loop when the
            # server closes the connection. Cancelling the others immediately lets the
            # outer loop reconnect without waiting for the heartbeat to sleep 30 seconds.
            try:
                done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                # try/finally is MANDATORY: `asyncio.wait` does NOT cancel what it
                # waits on. When main cancels conn_task (SIGTERM), the
                # CancelledError rises from inside the wait and, without this finally, the
                # 5 child loops survived the shutdown gather — they stayed up to
                # 5s blocked in `wait_for(get(), 5.0)` consuming from the SAME
                # queues main had already considered drained, and whatever arrived in that
                # window was taken out and discarded (ws closed). Cancelling here is
                # what makes main.py's "ORDERLY shutdown" label hold for
                # the connection's children.
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                # SessionMaker acabou: sem socket ate a proxima conexao.
                self._ws = None

            # The exception that brought the session down MUST rise to run(): the
            # `async with websockets.connect` does not re-raise in __aexit__, so
            # swallowing it here made _connect_and_run return as if it were a clean
            # shutdown — the real reason (close 4408/4426/1003/1011, network drop) vanished
            # from the log at LOG_LEVEL=INFO and the backoff was skipped. Propagating is also
            # what carries a ConnectionClosed with code 4401/4403/4404 up to
            # _classify_connection_error, which marks it as terminal.
            #
            # `done` is a SET: iterating it directly picked an ARBITRARY exception
            # when more than one task finished in the same batch. The _receive_loop
            # is the authoritative source of the reason (it is the one carrying the
            # ConnectionClosed with the server's close code); the other loops only
            # reflect the same close. Hence the explicit priority.
            first_exc: Exception | None = None
            for task in sorted(done, key=lambda t: 0 if t.get_name() == "receive" else 1):
                exc = task.exception() if not task.cancelled() else None
                if exc is None or isinstance(exc, asyncio.CancelledError):
                    continue
                if first_exc is None:
                    first_exc = exc
                else:
                    logger.debug("Task '%s' encerrada com exceção: %s", task.get_name(), exc)

            if first_exc is None:
                # No exception in `done` — but the auxiliary loops handle
                # ConnectionClosed with `break` and end CLEANLY. If one of them
                # wins the race with _receive_loop, receive goes into
                # `pending` and is cancelled before raising: an authoritative
                # deny (4401 revoked / 4403 / 4404) became "connection
                # closed, reconnect with backoff" and the operator never saw
                # "refaca enrollment" (redo enrollment). The ws has already recorded the code in
                # the close handshake — it is the source of truth that survives cancellation.
                code = getattr(ws, "close_code", None)
                if code in _TERMINAL_CLOSE_CODES:
                    first_exc = ConnectionClosedError(
                        Close(code, getattr(ws, "close_reason", "") or ""), None
                    )

            if first_exc is not None:
                raise first_exc

    # ── Loops paralelos ───────────────────────────────────────────────────────

    async def _receive_loop(self, ws):
        """Recebe mensagens do servidor e enfileira jobs."""
        # Counter of consecutive invalid JSONs. Serves as a client-side
        # backoff: N errors in a row -> a short sleep before continuing,
        # avoiding a tight spin if the server goes buggy sending a corrupted
        # payload in a loop. Without this, the server disconnected after 5 invalid
        # msgs (code 1003) and the client reconnected immediately, and the same
        # bug repeated in a cycle.
        _CLIENT_JSON_BACKOFF_THRESHOLD = 3
        _CLIENT_JSON_BACKOFF_SLEEP = 2.0
        invalid_streak = 0

        async for raw in ws:
            try:
                msg = json.loads(raw)
                invalid_streak = 0
            except json.JSONDecodeError:
                invalid_streak += 1
                logger.warning(
                    "Mensagem inválida recebida (streak=%d): %r",
                    invalid_streak, raw[:200],
                )
                if invalid_streak >= _CLIENT_JSON_BACKOFF_THRESHOLD:
                    # Backoff to avoid a tight spin — lets the
                    # server or the operator step in before it piles up
                    # until the server fires close 1003.
                    await asyncio.sleep(_CLIENT_JSON_BACKOFF_SLEEP)
                continue

            msg_type = msg.get("type")
            # Allowlist of the server → executor protocol. Everything outside it is
            # discarded before any processing. Defense in depth
            # alongside the HMAC on the relay channels: if some day an unauthenticated
            # message reaches the WS, it finds no new/experimental
            # handler exposed by accident.
            if msg_type not in SERVER_TYPES:
                logger.debug("Mensagem desconhecida do servidor: %s", msg_type)
                continue

            # SEC (S7): commands that CHANGE THE STATE of the executor (shut down,
            # restart, interrupt a job) require an Ed25519 signature from the server,
            # just like `job`. Before, the type allowlist above was enough: whoever
            # managed to write to the WS or publish on the Redis relay took down the
            # fleet with a "control/shutdown" without forging anything. `job` has
            # its own validation in job_executor; `drive_event` does not change state and
            # stays unsigned.
            if msg_type in _SIGNED_SERVER_MESSAGES:
                try:
                    validate_control_message(msg)
                except JobValidationError as exc:
                    logger.error(
                        "Comando '%s' REJEITADO pela validação de segurança: %s",
                        msg_type, exc,
                    )
                    continue

            if msg_type == "job":
                await self._handle_job(ws, msg)
            elif msg_type == "drive_event":
                await self._handle_drive_event(msg)
            elif msg_type == "control":
                action = msg.get("action", "")
                reason = msg.get("reason", "")
                if action not in _CONTROL_ACTIONS:
                    logger.warning("Acao de control desconhecida ignorada: %r", action)
                    continue
                if action == "revoked":
                    logger.warning("Servidor: executor revogado — %s", reason)
                    self._should_reconnect = False
                    # Mesma classe do close 4404: so um enrollment novo resolve.
                    self.terminal_deny = f"Executor revogado pelo servidor. {reason}".strip()
                    return  # Leaves the loop, connection.run() will shut down
                elif action == "shutdown":
                    logger.warning("Servidor: shutdown solicitado — %s", reason)
                    self._should_reconnect = False
                    # NOT a deny: the server asked to stop, the enrollment
                    # is still valid and the executor comes back up when restarted.
                    return
                elif action == "purge_artifacts":
                    # Retention expired: the server orders deletion of artifacts that
                    # live only on this disk. Does not close the connection — it is cleanup,
                    # not a deny.
                    from executor.artifact_purge import purgar
                    # `purgar` does stat/unlink/rmdir per artifact — synchronous disk I/O
                    # in the WS receive loop. It goes to a thread so as
                    # not to hold up heartbeat/job delivery on a retention order
                    # with many artifacts.
                    n = await asyncio.to_thread(purgar, msg.get("artifacts") or [])
                    logger.info(
                        "Servidor: remocao de artefatos locais — %d apagado(s). %s",
                        n, reason,
                    )
                    continue
                elif action == "config_changed":
                    logger.info("Servidor: configuração alterada — %s. Reiniciando executor...", reason)
                    self._should_reconnect = False
                    self.restart_requested = True
                    # Exits through the normal asyncio path: _receive_loop ->
                    # _connect_and_run -> run() -> main(), which observes the end
                    # of conn_task and does the orderly shutdown before
                    # sys.exit(1) (Docker restart: on-failure restarts it).
                    #
                    # We do not self-send SIGTERM: on POSIX it was redundant and on
                    # Windows there was no registered handler (add_signal_handler
                    # raises NotImplementedError), leaving the process
                    # hanging without restarting.
                    return
            elif msg_type == "cancel":
                job_id = msg.get("job_id")
                if not job_id:
                    logger.warning("Mensagem 'cancel' sem job_id — ignorada.")
                    continue
                outcome = self._queue.cancel(job_id)
                if outcome == "unknown":
                    outcome = await self._close_unknown_cancellation(job_id)
                logger.info("Cancelamento do job '%.8s': %s", job_id, outcome)
            elif msg_type == ERROR_TYPE:
                # The server refused (and discarded) a message from this executor:
                # invalid JSON, missing required field, invalid capacity,
                # message before the handshake, unsupported version. There is nothing
                # to redo, but the reason has to show up HERE: before, `error`
                # was outside the allowlist and fell into "Mensagem desconhecida" (unknown message), at
                # DEBUG — the refusal only existed in the server log, which the executor's
                # operator does not see. Logging only, no effect: the message is not
                # signed.
                detalhe = {k: v for k, v in msg.items() if k not in ("type", "reason")}
                logger.warning(
                    "Servidor recusou uma mensagem deste executor: reason=%r %s",
                    str(msg.get("reason"))[:100],
                    json.dumps(detalhe, ensure_ascii=False)[:500] if detalhe else "",
                )

    async def _handle_job(self, ws, message: dict):
        """Checks back-pressure and queues the job for execution."""
        job_id   = message.get("envelope", {}).get("job_id", "?")
        job_type = message.get("envelope", {}).get("job_type", "?")
        logger.info("Job recebido  id=%.8s  type=%s", job_id, job_type)

        # Cancelled while in transit: the server has already closed the run as cancelled
        # (see `_close_unknown_cancellation`). Running it now would be
        # executing — with side effects — something the user told to stop.
        if self._queue.cancelled_before_arrival(job_id):
            logger.info("Job '%.8s' descartado: foi cancelado antes de chegar.", job_id)
            return

        if self._queue.is_full():
            # Tells the server it cannot accept
            await ws.send(json.dumps({
                "type":   "job_result",
                "job_id": job_id,
                "status": "error",
                "error":  "Fila do executor cheia — back-pressure.",
            }))
            logger.warning("Job '%s' rejeitado por back-pressure.", job_id)
            return

        accepted = await self._queue.enqueue(message)
        if accepted:
            logger.info("Job '%s' enfileirado.", job_id)
            # On-disk journal: if the process dies before the job produces a
            # result, the next boot reports it as interrupted instead of the
            # run staying "Em andamento" (in progress) on the server (see result_store).
            from executor import result_store
            result_store.registrar_em_voo(job_id)
            # Receipt ACK — the server uses it to detect jobs lost between
            # "send_text returned OK" and "the executor actually queued it".
            try:
                await ws.send(json.dumps({
                    "type":   "ack",
                    "job_id": job_id,
                    "status": "enqueued",
                }))
            except Exception as exc:
                logger.warning("Falha ao enviar ACK do job '%s': %s", job_id, exc)
        else:
            await ws.send(json.dumps({
                "type":   "job_result",
                "job_id": job_id,
                "status": "error",
                "error":  "Executor em shutdown.",
            }))

    async def _handle_drive_event(self, msg: dict):
        """Forwards a Drive event to the SyncManager queue."""
        if self._drive_events is not None:
            try:
                self._drive_events.put_nowait(msg)
                action = msg.get("action", "?")
                fname = msg.get("file", {}).get("original_name", "?")
                logger.info("Drive event recebido: %s → %s", action, fname)
            except asyncio.QueueFull:
                logger.warning("Fila de drive_events cheia — evento descartado.")

    async def _result_sender_loop(self, ws):
        """Reads results from the output queue and sends them to the server as job_result."""
        from executor import result_store

        failure_streak = 0
        while True:
            try:
                result: dict = await asyncio.wait_for(self._results.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            sent_ok = False
            closed = False
            # Internal attempt counter (same key as the event loop): leaves the
            # dict before the send so it never travels in the protocol. Read outside the
            # try because the exception handlers depend on it.
            attempts = result.pop(_ATTEMPTS_KEY, 0) if isinstance(result, dict) else 0
            try:
                # The 'output' was already dropped at the source (executor/main.py, on_execute):
                # it never enters the _result_queue. The server only uses job_id, run_id,
                # status, error and stats to update the WorkflowRun.
                # _dumps_result is still required: 'stats' may still carry
                # Timestamp/numpy and blow the WS payload limit.
                await ws.send(_dumps_result({"type": "job_result", **result}))
                logger.info("Job %.8s → %s", result.get("job_id", "?"), (result.get("status") or "?").upper())
                sent_ok = True
                failure_streak = 0
                # SEND watermark (not consumption): the `task_done()` below
                # is unconditional and does not distinguish sent from re-queued.
                self._mark_sent(self._results, result)
            except ConnectionClosed:
                # Puts the result back in the queue — it will be resent after reconnecting.
                # The result_store still keeps a persistent copy, so a restart
                # of the process also preserves the result.
                self._requeue_result(result, attempts)
                closed = True
            except asyncio.CancelledError:
                # CancelledError is NOT an Exception: without this branch, a cancellation
                # during `ws.send` (happens on EVERY session drop — the
                # _connect_and_run cancels the loops) left the result out of the
                # queue, the `finally` did task_done() and the shutdown's
                # `_result_queue.join()` reported "drained" for
                # something that was never sent. Silent loss, without even the
                # ERROR log of the other paths: the run only moved again on the next
                # process start, through the outbox.
                self._requeue_result(result, attempts)
                raise
            except Exception as exc:
                # Any other error (json dump, encoding, RuntimeError) —
                # put it back in the queue. Without this, the result would vanish from the
                # in-memory queue and the executor needed a restart for
                # result_store.load_pending() to drain it. But with a CEILING: see
                # _MAX_RESULT_SEND_ATTEMPTS.
                attempts += 1
                # DELETE/UPDATE by key in SQLite WAL costs microseconds and the
                # whole store is already serialized by an RLock with the `put()` calls of this
                # same event loop — calling it synchronously is correct. The version with
                # `asyncio.to_thread` worsened what it claimed to fix: it fell into the
                # DEFAULT pool (main.py installs _thread_pool there), the same one used by the
                # GIS nodes' `to_thread`, and a batch of heavy nodes held up the
                # delivery of ALL results for minutes.
                result_store.increment_attempts(str(result.get("job_id") or ""))
                failure_streak += 1
                if attempts >= _MAX_RESULT_SEND_ATTEMPTS:
                    # Out of the queue for good — settles the watermark account,
                    # otherwise the shutdown's `_await_confirmation` waits for a
                    # result that will only come back through the outbox on the next start.
                    self._mark_resolved(self._results, result)
                    logger.error(
                        "Resultado do job '%s' descartado da fila apos %d tentativas (%s) — "
                        "permanece no outbox e sera reenviado no proximo start.",
                        result.get("job_id"), attempts, exc,
                    )
                else:
                    logger.error(
                        "Erro ao enviar resultado do job '%s' (tentativa %d) — re-enfileirando: %s",
                        result.get("job_id"), attempts, exc,
                    )
                    self._requeue_result(result, attempts)
                    # Pause per BURST: an isolated failure costs nothing; only an error
                    # that repeats turns into a sleep (this is the queue's only
                    # consumer, so a tight spin would lock it up).
                    pausa = _burst_pause(failure_streak)
                    if pausa:
                        await asyncio.sleep(pausa)
            finally:
                # UNCONDITIONAL task_done(). The re-enqueue counts as a new item
                # (put() increments _unfinished_tasks), so the balance closes:
                # get() -> put() (+1) -> task_done() (-1) = 0. The former 'if not requeued'
                # shifted the counter by +1 PERMANENTLY and hung
                # any join() on this queue.
                self._results.task_done()

            if closed:
                break

            # Outside the try/except so it does not run on ConnectionClosed (retry)
            if sent_ok:
                enviado = str(result.get("job_id") or "")
                self._remember_sent(enviado)
                result_store.mark_sent(enviado)

    def _requeue_result(self, result: dict, attempts: int = 0) -> None:
        """Puts an unsent result back in the queue without ever blocking.

        put_nowait instead of await put(): this loop is the ONLY consumer of the queue,
        so waiting for space in a full queue would be a guaranteed deadlock — and the
        _result_queue IS bounded (main.py sizes it at MAX_QUEUE_SIZE +
        MAX_CONCURRENT + 32). A full queue means giving up the in-memory send;
        the result_store keeps the persistent copy for replay on restart.
        """
        # Settles the account of the PREVIOUS entry before the put, which opens a new one.
        self._mark_resolved(self._results, result)
        if attempts:
            result[_ATTEMPTS_KEY] = attempts
        try:
            self._results.put_nowait(result)
        except asyncio.QueueFull:
            logger.error(
                "Fila de resultados cheia — job '%s' sera reenviado apenas no "
                "proximo restart (result_store.load_pending).",
                result.get("job_id"),
            )
        except Exception:
            logger.exception("Falha ao re-enfileirar resultado do job '%s'", result.get("job_id"))

    async def _event_sender_loop(self, ws):
        """Drains the node event queue and sends them to the server as node_event."""
        # New session: puts back in the queue the lifecycle that was lost while
        # there was no socket (see LifecycleCollector).
        self._ressincronizar_lifecycle()
        failure_streak = 0
        try:
            while True:
                # The queue has room again: put back into it the lifecycle that PRESSURE made
                # fall into the collector. Without this, only reconnection drained it — and the queue
                # fills up from production (a 300-node workflow in debug_mode) far
                # more often than the session drops. The nodes kept their spinner until
                # the end of the run and the events stayed stuck in memory; and the resend, if
                # it came at all, came hours later, for a run the server had already closed.
                self._ressincronizar_lifecycle(only_with_slack=True)
                try:
                    event: dict = await asyncio.wait_for(self._events.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break

                closed = False
                # The attempt counter is internal: it leaves the dict before the send
                # so it never travels in the protocol. Read outside the try because the
                # exception handlers depend on it.
                attempts = event.pop(_ATTEMPTS_KEY, 0) if isinstance(event, dict) else 0
                try:
                    # _dumps_event (and not raw json.dumps): a node_event with a
                    # non-serializable object raised TypeError, fell into the
                    # generic branch, re-queued the SAME event and repeated forever
                    # in a tight loop. It also applies the event's OWN
                    # size ceiling — job_result's truncation via 'stats'
                    # did not work here (an event has no 'stats').
                    await ws.send(_dumps_event({"type": "node_event", **event}))
                    failure_streak = 0
                    # See the equivalent comment in _result_sender_loop: the
                    # end-of-job barrier can only count what LEFT through the WS.
                    self._mark_sent(self._events, event)
                except ConnectionClosed:
                    logger.warning(
                        "Node event descartado por ConnectionClosed — re-enfileirando node=%s status=%s",
                        event.get("node"), event.get("status"),
                    )
                    self._requeue_event(event, attempts)
                    closed = True
                except asyncio.CancelledError:
                    # See the equivalent branch in _result_sender_loop: without it the
                    # event left the queue on cancellation and on_execute's
                    # `_event_queue.join()` considered the queue
                    # drained with a lost UI update.
                    self._requeue_event(event, attempts)
                    raise
                except Exception as exc:
                    # Any other error (serialization, invalid WS state) —
                    # re-queue instead of discarding. Without this the UI loses
                    # graph updates and shows the workflow frozen. But with a
                    # ceiling: after _MAX_EVENT_SEND_ATTEMPTS the event is discarded,
                    # because the failure is probably deterministic and an
                    # immortal event traps the queue's single consumer.
                    attempts += 1
                    failure_streak += 1
                    if attempts >= _MAX_EVENT_SEND_ATTEMPTS:
                        # Gave up on this event — but if it was lifecycle, the
                        # canvas would show the node as "running" forever. Keep
                        # the last status for the next session's resync.
                        # Only the control fields: the failure here is
                        # DETERMINISTIC (non-serializable payload), and resending the
                        # whole event would only repeat the 3 attempts on every
                        # reconnection.
                        self._record_loss(event, minimo=True)
                        # Does not go back to the queue: settles the account so the end-of-job
                        # barrier does not keep waiting for an event that will never come.
                        self._mark_resolved(self._events, event)
                        logger.error(
                            "Node event node=%s status=%s descartado apos %d tentativas: %s",
                            event.get("node"), event.get("status"), attempts, exc,
                        )
                    else:
                        logger.warning(
                            "Erro ao enviar node_event node=%s status=%s (tentativa %d) — re-enfileirando: %s",
                            event.get("node"), event.get("status"), attempts, exc,
                        )
                        self._requeue_event(event, attempts)
                        # Pause per BURST (see _burst_pause): the 1s per item
                        # turned the queue into a funnel of 1 event/s.
                        pausa = _burst_pause(failure_streak)
                        if pausa:
                            await asyncio.sleep(pausa)
                finally:
                    # UNCONDITIONAL task_done() — see the comment in
                    # _result_sender_loop. Here the bug's effect was worse:
                    # main.py's _event_queue.join() (on_execute) never
                    # resolved again and EVERY subsequent job paid a 30s timeout
                    # ("Timeout ao drenar fila de eventos — 0 evento(s) pendente(s)").
                    self._events.task_done()

                if closed:
                    break
        except Exception:
            logger.exception("Erro fatal no event_sender_loop")

    def _requeue_event(self, event: dict, attempts: int) -> None:
        """Puts an unsent node_event back in the queue without ever blocking.

        `await put()` on a full queue with maxsize=500 was a DEADLOCK: this loop is the
        only consumer of _event_queue, so it would block in its own
        put waiting for itself to consume. With put_nowait, a full queue means
        dropping the event — node_event is UI telemetry, not business data.
        """
        # Settles the account of the PREVIOUS entry before the put, which opens a new one.
        # Also applies when the put fails because the queue is full: there the event is lost
        # for good and the watermark has to be closed all the same.
        self._mark_resolved(self._events, event)
        if attempts:
            event[_ATTEMPTS_KEY] = attempts
        try:
            self._events.put_nowait(event)
        except asyncio.QueueFull:
            self._record_loss(event)
            logger.warning(
                "Fila de node_events cheia — evento node=%s status=%s descartado.",
                event.get("node"), event.get("status"),
            )
        except Exception:
            logger.exception("Falha ao re-enfileirar node_event")

    # ── Lifecycle resync after a drop ─────────────────────────────────────────

    @staticmethod
    def _mark_sent(fila, item: dict) -> None:
        """Tells the counting queue that the item actually left through the WebSocket.

        Duck typing on purpose: in tests (and in any ad-hoc use) the queues
        are plain `asyncio.Queue`, which count nothing — and do not need to.
        """
        marcar = getattr(fila, "confirmar_envio", None)
        if marcar is not None:
            marcar(item)

    @staticmethod
    def _mark_resolved(fila, item: dict) -> None:
        """Settles the account of an item that left the queue WITHOUT having been sent.

        Mandatory on EVERY re-queue and definitive-drop path: `_put`
        counts each entry in the queue, so without this
        counterweight a single retry left that run's watermark owing 1
        forever — and the end-of-job barrier, which waits for
        `confirmados >= alvo`, only exited through the stagnation timeout (3s delay
        on the `__workflow_complete__` of every job that had a send failure).
        """
        marcar = getattr(fila, "resolver_sem_envio", None)
        if marcar is not None:
            marcar(item)

    def _record_loss(self, event: dict, minimo: bool = False) -> None:
        """Keeps the last lifecycle of a lost event, to resend later."""
        coletor = getattr(self._events, "coletor", None)
        if coletor is None:
            return
        if minimo:
            guardado = {k: event[k] for k in CONTROL_FIELDS if k in event}
        else:
            # Without the internal attempt key: it must not come back along with it and
            # make the resynced event start out already at the retry ceiling.
            guardado = {k: v for k, v in event.items() if k != _ATTEMPTS_KEY}
        coletor.registrar(guardado)

    def _ressincronizar_lifecycle(self, only_with_slack: bool = False) -> None:
        """Re-queues the lifecycle that was lost (session drop OR pressure).

        Without this, a 30-60s network drop in the middle of a long workflow
        left the canvas permanently wrong: the nodes that finished in that window
        kept their spinner until the whole run closed. These are ordinary
        node_events — the server already knows how to rebuild the canvas from them and
        orders by timestamp, so resending an already-seen `completed` is harmless.

        With `only_with_slack=True` (the call on each turn of the sender, with the session
        ALIVE) the resend only happens when the queue is below half. That is what
        keeps the remedy from becoming the disease: putting the events back into a still
        full queue would trigger the pressure drop again, in a loop between collector and
        queue that would not let the sender drain the backlog that would free up room.
        """
        coletor = getattr(self._events, "coletor", None)
        if coletor is None:
            return
        if only_with_slack:
            if not len(coletor):
                return
            maxsize = getattr(self._events, "maxsize", 0) or 0
            if maxsize and self._events.qsize() >= maxsize // 2:
                return
        pendentes = coletor.drenar()
        if not pendentes:
            return
        logger.info(
            "Reenviando %d evento(s) de ciclo de vida que nao couberam antes "
            "(%s).", len(pendentes),
            "fila folgou" if only_with_slack else "sessao restabelecida",
        )
        for i, evento in enumerate(pendentes):
            try:
                self._events.put_nowait(evento)
            except asyncio.QueueFull:
                # Queue already full with new production: return what is left to the
                # collector and try again on the next session. Insisting here would only
                # generate logs in a loop.
                for restante in pendentes[i:]:
                    coletor.registrar(restante)
                logger.warning(
                    "Fila de node_events cheia na ressincronizacao — %d evento(s) "
                    "adiados para a proxima sessao.", len(pendentes) - i,
                )
                return

    async def _heartbeat_loop(self, ws):
        """Sends a periodic heartbeat to the server."""
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            try:
                await ws.send(json.dumps({"type": "heartbeat"}))
                # Set AFTER the send: the heartbeat's age only means something
                # if it counts from the last one that actually left through the connection.
                self._stats.on_heartbeat()
            except ConnectionClosed:
                break

    async def _capacity_loop(self, ws):
        """Periodically reports the queue capacity to the server."""
        while True:
            await asyncio.sleep(_CAPACITY_INTERVAL)
            try:
                cap = self._build_capacity()
                await ws.send(json.dumps({"type": "capacity", **cap}))
            except ConnectionClosed:
                break

    async def _inventory_loop(self, ws):
        """Sends the server, right after the handshake and every minute, the jobs that
        this executor HAS: active (queue, semaphore, execution) and with a result
        not yet confirmed.

        It is what closes the hole of the run "Em andamento" (in progress) forever: a job that
        got lost on the way (API worker dead, relay with no destination, executor
        restart) is not here, and the server closes the run within minutes instead of
        waiting for a disconnection that may never come — on Sep 22 titan stayed
        connected with three lost runs until 09:16.
        """
        while True:
            # Auxiliary loop: an error while BUILDING the inventory (unreadable outbox, for
            # example) skips this turn, it does not bring down the session — the
            # _connect_and_run's `wait` would close the whole connection with the first task
            # that finished.
            try:
                inventario = self._build_inventory()
            except Exception as exc:
                logger.warning("Inventário de jobs não montado nesta volta: %s", exc)
                inventario = None
            if inventario is not None:
                try:
                    await ws.send(json.dumps(inventario))
                except ConnectionClosed:
                    break
            await asyncio.sleep(_INVENTORY_INTERVAL)

    def _remember_sent(self, job_id: str) -> None:
        """Keeps for a few minutes the id of a result that has just gone out.

        `mark_sent` deletes the result from the outbox as soon as `ws.send` returns,
        but the server may not have processed it yet: the connection dropped right
        after and its inbox keeps draining on another worker, or the consumer is
        behind. In that interval the job was nowhere here, and:
          - the new session's inventory said "I don't have it" — the server closed
            the run as lost and then refused the real result;
          - a cancel became a synthetic 'cancelled' on top of a success.
        """
        if not job_id:
            return
        self._sent.pop(job_id, None)
        self._sent[job_id] = time.monotonic()
        while len(self._sent) > _SENT_MAX:
            self._sent.pop(next(iter(self._sent)))

    def _pending_results(self) -> set[str] | None:
        """Results that have not gone out yet: in the outbox or in the in-memory queue.
        None when the outbox could not be read."""
        from executor import result_store

        pendentes = result_store.job_ids_pendentes()
        if pendentes is None:
            return None
        in_transit = set(pendentes)
        # The in-memory queue also counts: with the outbox disabled (disk without
        # permission, corrupted SQLite) it is the only record of a result
        # that has not gone out yet.
        for item in list(getattr(self._results, "_queue", ()) or ()):
            if isinstance(item, dict) and item.get("job_id"):
                in_transit.add(str(item["job_id"]))
        return in_transit

    def _recently_sent(self) -> list[str]:
        """Results sent less than `_SENT_TTL_S` ago, from the most recent to the
        oldest."""
        vence = time.monotonic() - _SENT_TTL_S
        for job_id in [j for j, quando in self._sent.items() if quando < vence]:
            del self._sent[job_id]
        return list(reversed(self._sent))

    def _results_in_flight(self) -> set[str] | None:
        """Jobs that FINISHED here and whose result the server may not have
        processed yet. None when the outbox could not be read — then there is no way to
        assert that a job did NOT finish here."""
        pendentes = self._pending_results()
        if pendentes is None:
            return None
        return pendentes | set(self._recently_sent())

    def _build_inventory(self) -> dict:
        ativos = self._queue.active_job_ids() if self._queue is not None else []
        pendentes = self._pending_results()
        # Unreadable outbox: the inventory goes out marked `truncado` — the server
        # promotes and stops zombies, but closes nothing for absence (an empty list
        # would assert "nothing pending"). Sending nothing would let the inventory
        # mark expire, and the sweep would treat this executor as an old one.
        truncado = pendentes is None
        pendentes = sorted((pendentes or set()) - set(ativos))
        truncado = truncado or len(ativos) + len(pendentes) > _INVENTARIO_MAX
        resultados = pendentes[:max(0, _INVENTARIO_MAX - len(ativos))]
        # The recently sent ones only take the space that is left, most recent
        # first, and do not mark `truncado`: on a busy executor they
        # would turn off its reconciliation forever. Whatever is left out is already
        # protected by the server's result key.
        vaga = _INVENTARIO_MAX - len(ativos) - len(resultados)
        if vaga > 0:
            ja = set(ativos) | set(resultados)
            resultados += [j for j in self._recently_sent() if j not in ja][:vaga]
        return {
            "type":       "inventario",
            "ativos":     ativos[:_INVENTARIO_MAX],
            "resultados": resultados,
            "truncado":   truncado,
        }

    async def _close_unknown_cancellation(self, job_id: str) -> str:
        """Cancellation of a job that is not on this instance.

        The executor used to answer "unknown" only in the log and stay silent: the run
        remained "Em andamento" (in progress) on the server forever, and cancelling did not
        clear it. Now it returns a 'cancelled' result — the server
        closes the run, unless it is already terminal — and leaves a tombstone to
        drop the job if it arrives late.

        With the result on its way (outbox, in-memory queue or recently sent)
        the job FINISHED here: the real result is arriving, and a
        'cancelled' on top of it would be a lie — and, if the server's consumer
        had not written it yet, could even beat it. With an unreadable outbox
        there is no way to know: it answers nothing, and the inventory sorts it out later.
        """
        in_transit = self._results_in_flight()
        if in_transit is None:
            return "outbox_ilegivel"
        if job_id in in_transit:
            return "resultado_pendente"
        await self._queue.close_unknown(job_id, _UNKNOWN_CANCELLATION_REASON)
        return "encerrado"

    def _build_capacity(self) -> dict:
        """Capacity payload, with the thread pool taken into account.

        `get_capacity()` counts JOBS. That stopped describing the executor once
        every node started running in the thread pool: a PythonScript with an infinite
        loop blows the node timeout, gives back the job's slot and leaves the thread
        alive forever (`asyncio.to_thread` does not cancel). A few executions
        like that fill the whole pool; from then on queued/running show an
        idle executor while NO node can run, and the server keeps
        dispatching jobs that die hanging in "running" until they become orphans.

        When the pool is saturated we announce saturation through the same means
        draining uses (queued = queue ceiling + concurrency ceiling): the
        server's dispatch puts us last (group of the full ones) and
        `is_full` refuses the send, which then falls to the next candidate instead of
        failing the run.
        """
        cap = {**self._queue.get_capacity(), **_get_dynamic_metrics()}
        if not self._pool_saturated():
            return cap
        return {
            **cap,
            "queued": cap.get("max_queue", 0) + cap.get("max_concurrent", 0),
        }

    def _pool_saturated(self) -> bool:
        """True when the nodes' pool is full AND has work waiting.

        Requires `_POOL_SATURATED_TICKS` CONSECUTIVE samples: a normal spike (N
        nodes dispatched at the same instant) saturates the pool for milliseconds, and
        announcing the executor as full because of that would take the machine out of the
        ranking for nothing. Orphan threads do not resolve themselves — the condition persists.
        """
        pool = self._thread_pool
        if pool is None:
            return False
        try:
            # Private attributes on purpose: ThreadPoolExecutor does not expose
            # occupancy publicly and the alternative would be wrapping every submit.
            # Any surprise falls into the except and becomes "not saturated", which is the
            # previous behavior.
            cheio = len(pool._threads) >= pool._max_workers and pool._work_queue.qsize() > 0
        except Exception:
            return False
        if not cheio:
            self._pool_saturated_streak = 0
            return False
        self._pool_saturated_streak += 1
        if self._pool_saturated_streak == _POOL_SATURATED_TICKS:
            logger.error(
                "Pool de threads dos nos saturado (%d workers ocupados, %d tarefa(s) na "
                "espera) — anunciando capacidade zero. Suspeite de no travado "
                "(PythonScript em laco infinito nao e cancelavel pelo timeout).",
                pool._max_workers, pool._work_queue.qsize(),
            )
        return self._pool_saturated_streak >= _POOL_SATURATED_TICKS

