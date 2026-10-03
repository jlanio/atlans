# app/core/agent_connections.py
"""
Global registry of active executor WebSocket connections.

ExecutorConnectionRegistry keeps two planes of state:
  - In memory (per worker): an executor_id → ExecutorConnection map with the real WebSocket.
    Used exclusively for sending jobs and reading capacity/connected_at.
  - Redis (shared): key executor:presence:{id} with a 120s TTL.
    Used to determine whether the executor is online — works correctly with
    multiple uvicorn workers (--workers N), since it is global state.
    Next to it lives executor:conn_owner:{id}, with the token of the connection that holds
    global OWNERSHIP of the executor. Two connections with the same executor_id on different
    workers would make the job run twice (the relay is PUBLISH, that
    is, broadcast); and the unregister of one of them deleted the other's presence.
    With the owner: whoever connects last takes over, the loser closes its socket
    and presence removal is by CAS.

Relay via Redis pub/sub:
  When the HTTP request that dispatches a job lands on a different worker from the one
  holding the WebSocket, the job is published on the 'executor:job_relay:{executor_id}' channel.
  The worker holding the WS subscribes to that channel and forwards the job to the executor.

TTL renewal: happens on every heartbeat/capacity received (~30s).
The 120s TTL is a safety net for workers that crash without calling unregister().
"""
import asyncio
import collections
import hashlib
import hmac
import json
from flow.utils.backoff import com_jitter
from app.core.utils.logger import get_logger
import os
import time
import uuid
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as _aioredis
from redis.exceptions import TimeoutError as _RedisTimeoutError
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.config import REDIS_URL

logger = get_logger(__name__)

# TTL of the presence key in Redis (seconds).
# Must be > the server's HEARTBEAT_TIMEOUT (90s) to avoid false negatives.
_PRESENCE_TTL = 120

# Pub/sub channel for relaying jobs between workers
_RELAY_CHANNEL_PREFIX = "executor:job_relay:"

# Local cache (short TTL) for is_online answers — avoids a Redis round-trip
# on endpoints that list every executor (GET /executores, list_agents).
_PRESENCE_CACHE_TTL = 5.0  # segundos

# Minimum interval between two presence-renewal EVALs of the SAME connection.
# The executor sends capacity every 10s and a heartbeat every 30s: without a throttle that was
# ~14 EVAL/min/executor (with 200 executors, ~47 EVAL/s of pure "I'm still
# alive") to maintain a key whose TTL is 120s. Renewing every TTL/4 the
# margin is still huge and the background load drops ~8x. Takeover detection through
# this path now takes up to 30s, but it is only the safety net — the
# `__internal__.takeover` marker published on the relay closes the duplicate right away.
#
# TTL/4 (and not TTL/3) on purpose: with TTL/3 there was ONE spare renewal, so
# a single lost renewal already brushed against the key's expiry. With TTL/4
# three attempts remain before the presence vanishes — and absent presence with a live WS
# makes `orphan_runs_watchdog` kill runs that are executing.
_PRESENCE_RENEW_INTERVAL = _PRESENCE_TTL / 4

# Wait before RETRYING a renewal that could not be done (Redis down).
# Without this, a Redis failure advanced the throttle clock as if the key
# had been renewed and the next attempt would only come a whole interval
# later — a ~45s blip was enough for the key to expire with the executor alive.
_PRESENCE_RENEW_RETRY_INTERVAL = 5.0


def _relay_secret() -> bytes:
    """HMAC secret for authenticating relay messages between workers.

    Reuses APP_SECRET (already mandatory via config) — shared by all the
    uvicorn workers but NOT by Redis. Even if Redis is compromised or
    a hostile container manages to publish on the channel, messages without a valid
    HMAC are discarded by the listener.
    """
    from app.core.config import APP_SECRET
    return APP_SECRET.encode() if isinstance(APP_SECRET, str) else APP_SECRET


# ── Signed relay envelope ─────────────────────────────────────────────────────
# The HMAC covered ONLY the raw payload — no channel, recipient, nonce or timestamp.
# Consequence: a captured envelope was valid FOREVER and on ANY channel.
# It was enough to record a legitimate `control/revoked` and republish it on each
# executor's channel to bring down the whole fleet. Now the signed material includes the
# purpose (audience), the target executor, a nonce and the timestamp; the
# consumer refuses an envelope outside the freshness window or with a nonce already seen.
_AUDIENCE_RELAY = "relay"
_AUDIENCE_DRIVE = "drive_events"

# Recipient wildcard. Only the drive events fan-out uses it: `emit_drive_event`
# signs ONE envelope and publishes it to the workspace's N executors. The relay
# ALWAYS carries the concrete executor_id — that binding is what prevents reusing
# one executor's control message on another's channel.
_ANY_EXECUTOR = "*"

# Envelope freshness window. Producer and consumer are processes on the same
# host/stack, so wall-clock time is comparable between them.
_RELAY_FRESHNESS_WINDOW = 60.0
_RELAY_NONCE_TTL = 2 * _RELAY_FRESHNESS_WINDOW
_RELAY_NONCE_MAX = 20_000

# "nonce|recipient" already consumed → monotonic deadline. IN-PROCESS cache on
# purpose: the adversary in the threat model is precisely whoever talks to
# Redis, so a seen-set there could be erased by them. Each worker only needs to
# deduplicate what IT receives.
#
# The TTL is FIXED, so the dict's insertion order is the expiry order — that is
# what allows purging by prefix in O(expired) further below.
_seen_relay_nonces: dict[str, float] = {}

# Counter of STILL-VALID nonces discarded due to cache saturation. While
# the saturation lasts, the relay's anti-replay is effectively off for those
# entries; the log is aggregated so it doesn't become one ERROR per envelope received.
_relay_nonce_evictions: dict[str, float] = {"total": 0.0, "since_log": 0.0, "last_log": 0.0}
_RELAY_NONCE_EVICTION_LOG_EVERY = 10.0  # segundos


def _relay_signing_material(
    *, payload: str, audience: str, executor_id: str, nonce: str, ts: str,
) -> bytes:
    """Serializes the signed fields with a length prefix.

    The prefix removes concatenation ambiguity: without it, shifting characters
    between `audience` and `executor_id` would produce the same signed material.
    """
    parts = (payload, audience, executor_id, nonce, ts)
    return b"".join(f"{len(p)}:{p}".encode() for p in parts)


def _relay_mac(**fields: str) -> str:
    """HMAC-SHA256 hex do material assinado, usando APP_SECRET."""
    return hmac.new(
        _relay_secret(), _relay_signing_material(**fields), hashlib.sha256,
    ).hexdigest()


def _seal_envelope(payload: str, *, audience: str, executor_id: str) -> str:
    nonce = uuid.uuid4().hex
    ts = f"{time.time():.3f}"
    mac = _relay_mac(
        payload=payload, audience=audience, executor_id=executor_id,
        nonce=nonce, ts=ts,
    )
    return json.dumps({
        "payload":     payload,
        "aud":         audience,
        "executor_id": executor_id,
        "nonce":       nonce,
        "ts":          ts,
        "hmac":        mac,
    })


def build_signed_envelope(payload: str) -> str:
    """Signed envelope for the DRIVE EVENTS channel (fan-out).

    `emit_drive_event` signs once and publishes to all of the workspace's
    executors, so this envelope cannot be bound to a concrete executor —
    but it is still bound to the 'drive_events' purpose, the nonce and the timestamp.
    Accepted consequence: within the freshness window a drive envelope may
    be replayed to ANOTHER executor. The drive listener only accepts
    {"type":"drive_event"}, so the damage is limited to an out-of-order file
    notification — nothing on control/job.
    """
    return _seal_envelope(payload, audience=_AUDIENCE_DRIVE, executor_id=_ANY_EXECUTOR)


def build_relay_envelope(payload: str, *, executor_id: str) -> str:
    """Signed envelope for the job/control relay of ONE executor.

    Every pub/sub channel that ends in `ws.send_text()` to the executor MUST use
    a signed envelope — the listener validates before forwarding. Anyone without
    APP_SECRET (hostile container, compromised Redis) cannot inject
    messages into the executor's WebSocket.
    """
    return _seal_envelope(payload, audience=_AUDIENCE_RELAY, executor_id=executor_id)


def _nonce_already_seen(nonce: str, executor_id: str) -> bool:
    """Records the nonce for this recipient; True if it had already been consumed."""
    now = time.monotonic()
    key = f"{nonce}|{executor_id}"
    deadline = _seen_relay_nonces.get(key)
    if deadline is not None and deadline > now:
        return True
    # PERF: fixed TTL ⇒ insertion order == expiry order, so the
    # expired entries are always a PREFIX. Purging from the start until the first
    # live one costs O(expired). The previous version scanned all 20k entries and also
    # ran `sorted()` over them — on the hot path of EVERY envelope received.
    while _seen_relay_nonces:
        oldest_key, oldest_deadline = next(iter(_seen_relay_nonces.items()))
        if oldest_deadline > now:
            break
        _seen_relay_nonces.pop(oldest_key, None)

    # SEC: if the ceiling is reached with only STILL-VALID entries, evicting reopens
    # the replay window of the corresponding envelope. Discarding SILENTLY — as
    # was done before — left the operator unaware that the relay's anti-replay
    # was effectively off. The executor's sibling cache
    # (executor/job_validator.py) shouts in this same situation; here the shout is
    # aggregated because, when saturated, it happens on every envelope.
    if len(_seen_relay_nonces) >= _RELAY_NONCE_MAX:
        evicted_key, evicted_deadline = next(iter(_seen_relay_nonces.items()))
        _seen_relay_nonces.pop(evicted_key, None)
        _relay_nonce_evictions["total"] += 1
        _relay_nonce_evictions["since_log"] += 1
        if (now - _relay_nonce_evictions["last_log"]) >= _RELAY_NONCE_EVICTION_LOG_EVERY:
            logger.error(
                "Cache anti-replay do relay cheio (%d entradas, TTL %.0fs): %d nonce(s) "
                "AINDA VÁLIDO(S) descartado(s) nos últimos %.0fs (%d no total desta "
                "instância; o mais recente ainda tinha %.1fs de vida). Enquanto durar a "
                "saturação, um replay dos envelopes correspondentes não seria detectado.",
                _RELAY_NONCE_MAX, _RELAY_NONCE_TTL,
                int(_relay_nonce_evictions["since_log"]), _RELAY_NONCE_EVICTION_LOG_EVERY,
                int(_relay_nonce_evictions["total"]),
                max(0.0, evicted_deadline - now),
            )
            _relay_nonce_evictions["since_log"] = 0.0
            _relay_nonce_evictions["last_log"] = now

    _seen_relay_nonces[key] = now + _RELAY_NONCE_TTL
    return False


def open_signed_envelope(
    raw: str, *, channel_label: str, executor_id: str, audience: str,
) -> str | None:
    """Validates the signed envelope and returns the payload, or None if invalid.

    Besides the HMAC, it requires: purpose equal to the expected one, recipient equal to
    this channel's executor (or the wildcard, only in drive events), timestamp within
    `_RELAY_FRESHNESS_WINDOW` and a never-seen nonce.
    """
    try:
        envelope = json.loads(raw)
        payload = envelope.get("payload")
        mac     = envelope.get("hmac")
        aud     = envelope.get("aud")
        target  = envelope.get("executor_id")
        nonce   = envelope.get("nonce")
        ts      = envelope.get("ts")
        if not all(isinstance(v, str) for v in (payload, mac, aud, target, nonce, ts)):
            raise ValueError("envelope com campo ausente ou de tipo inesperado")
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        logger.warning(
            "%s: envelope malformado no canal do executor '%s': %s",
            channel_label, executor_id, exc,
        )
        return None

    # HMAC first: aud/target/nonce/ts are part of the signed material, so
    # any tampering with them is detected here before they are used.
    expected = _relay_mac(
        payload=payload, audience=aud, executor_id=target, nonce=nonce, ts=ts,
    )
    if not hmac.compare_digest(expected, mac):
        logger.warning(
            "%s: mensagem com HMAC inválido no canal do executor '%s' — descartada.",
            channel_label, executor_id,
        )
        return None

    if aud != audience:
        logger.warning(
            "%s: envelope assinado para propósito '%s' apresentado no canal '%s' "
            "do executor '%s' — descartado.",
            channel_label, aud, audience, executor_id,
        )
        return None

    if target != executor_id and not (audience == _AUDIENCE_DRIVE and target == _ANY_EXECUTOR):
        logger.warning(
            "%s: envelope destinado a '%s' apresentado no canal do executor '%s' "
            "— descartado (replay cross-executor).",
            channel_label, target, executor_id,
        )
        return None

    try:
        age = abs(time.time() - float(ts))
    except ValueError:
        logger.warning(
            "%s: envelope com timestamp ilegível no canal do executor '%s'.",
            channel_label, executor_id,
        )
        return None
    if age > _RELAY_FRESHNESS_WINDOW:
        logger.warning(
            "%s: envelope fora da janela de frescor (%.1fs > %.0fs) no canal do "
            "executor '%s' — descartado (replay).",
            channel_label, age, _RELAY_FRESHNESS_WINDOW, executor_id,
        )
        return None

    if _nonce_already_seen(nonce, executor_id):
        logger.warning(
            "%s: nonce repetido no canal do executor '%s' — descartado (replay).",
            channel_label, executor_id,
        )
        return None

    return payload


def _presence_key(executor_id: str) -> str:
    return f"executor:presence:{executor_id}"


def _conn_owner_key(executor_id: str) -> str:
    """Key of the GLOBAL OWNER of an executor's WebSocket connection.

    The de-dup in `register()` is per process, but the deployment runs `--workers 4`:
    nothing prevented two workers from each having a live WS for the same
    executor_id. Since the relay uses PUBLISH (broadcast), the job was delivered twice
    → duplicated INSERTs and emails. This key carries the token of the connection
    that holds ownership; whoever connects last takes over and the loser closes its
    socket.
    """
    return f"executor:conn_owner:{executor_id}"


def _relay_channel(executor_id: str) -> str:
    return f"{_RELAY_CHANNEL_PREFIX}{executor_id}"


def _drive_channel(executor_id: str) -> str:
    return f"executor:{executor_id}:drive_events"


# Renews presence + owner ONLY if the token is still the owner (or if ownership
# expired and nobody took over). Returns 1 if renewed, 0 if another worker took over.
_LUA_RENEW_PRESENCE = """
local owner = redis.call('GET', KEYS[2])
if owner and owner ~= ARGV[1] then
  return 0
end
redis.call('SET', KEYS[2], ARGV[1], 'EX', tonumber(ARGV[2]))
redis.call('SET', KEYS[1], '1', 'EX', tonumber(ARGV[2]))
return 1
"""

# Releases presence + owner by CAS. The previous unconditional DELETE was a serious
# availability bug: the worker whose connection DIED deleted the global presence
# of a session that already belonged to another worker → "503 Nenhum executor
# disponível" (no executor available) with the executor online and idle.
_LUA_RELEASE_PRESENCE = """
local owner = redis.call('GET', KEYS[2])
if owner and owner ~= ARGV[1] then
  return 0
end
redis.call('DEL', KEYS[1])
redis.call('DEL', KEYS[2])
return 1
"""


# ── Send deadline on the executor's WebSocket ────────────────────────────────
# Without a deadline, `send_text` to a stalled connection (frozen executor, half-open
# network) waited on the drain until the API's ping timeout (`--ws-ping-timeout
# 600`): the dispatch — and with it that worker's scheduler, which processes one
# schedule at a time — was stuck for up to ~10 min on a single send, with the run in
# "Na fila" (queued). The deadline grows with the frame size so as not to cut off a large
# envelope on a slow network: 30 s + 1 s per 512 KB (16 MB, the frame ceiling,
# gives ~62 s).
#
# Exceeding the deadline is NOT a refusal nor a dead connection. The whole frame is already in the
# transport buffer (websockets writes it before the drain; the deadline only
# cancels the wait) and keeps going out in the background. Therefore:
#   - the connection is not dropped: a live executor with a slow link used to lose its
#     presence, the watchdog closed all of its runs as orphans and, on return,
#     the inventory ordered the jobs still running to be canceled;
#   - the job counts as delivered without confirmation (ACK pending), with no failover —
#     sending it to another executor would make both run the same job. If it does not
#     arrive, the inventory and the 'pending' sweep close the run;
#   - while the write is late (beyond its own deadline), the connection
#     is left out of dispatch — on the worker that holds it and, via a mark in Redis,
#     on those that reach it through the relay. A truly dead connection drops out through
#     the heartbeat timeout and presence.
_PRAZO_DE_ENVIO_BASE_S = 30.0
_PRAZO_DE_ENVIO_BYTES_POR_S = 512 * 1024
# The stall mark in Redis expires on its own if nobody renews it (worker died
# in the middle of a late write); the writer renews it while the delay lasts.
_TTL_DA_PARADA_S = 60
_RENOVA_PARADA_S = 30.0


def _prazo_de_envio(n_bytes: int) -> float:
    return _PRAZO_DE_ENVIO_BASE_S + n_bytes / _PRAZO_DE_ENVIO_BYTES_POR_S


def _chave_de_parada(executor_id: str) -> str:
    return f"executor:parada:{executor_id}"


async def _redis_parada(executor_id: str) -> bool:
    """The worker holding this executor's socket has a late write
    (see `_Saida._sinalizar_atraso`). Redis down: False — the mark is an optimization,
    not a safety lock."""
    try:
        rc = await _get_redis()
        return bool(await rc.exists(_chave_de_parada(executor_id)))
    except Exception:
        return False


# ── Executor WebSocket output: one queue, one writer ─────────────────────────
# uvicorn's `--ws websockets` (pinned in compose) writes the WHOLE frame to the
# transport and only then waits for the drain — and the drain does not accept two waiters:
# with the socket under backpressure (a multi-MB envelope on a slow link), a second
# writer raised AssertionError with its frame ALREADY in the buffer, and the
# caller treated it as a failure (failover: the job ran on two executors; or
# unregister: presence deleted for a live executor).
#
# That is why each socket has a `_Saida`: a queue and ONE task that writes, in
# order, with no deadline at all on the drain. The sender waits for its own outcome
# with a deadline that counts what is ahead of it (the send in progress and the queue):
#   ENVIADO   went out whole;
#   ESCOANDO  the write started (the frame is in the buffer) and passed the deadline —
#             it keeps going out; for the sender, delivered without confirmation;
#   OCUPADO   the deadline ran out while still in the queue: the sender gives up and NOTHING is written;
#   FECHANDO  the socket is being closed: nothing is written.
# A socket error (dead connection) propagates to the waiter. The waiter never
# receives the writer's CancelledError: the outcome is a Future of its own.
ENVIADO = "enviado"
ESCOANDO = "escoando"
OCUPADO = "ocupado"
FECHANDO = "fechando"

# ws → _Saida. Removed from here at the end of the connection handler (see `encerrar_saida`).
_saidas: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
# Strong references to loose tasks (asyncio only keeps weakrefs).
_tarefas_soltas: set = set()


def _em_segundo_plano(coro, nome: str) -> "asyncio.Task":
    tarefa = asyncio.create_task(coro, name=nome)
    _tarefas_soltas.add(tarefa)

    def _fim(t: "asyncio.Task") -> None:
        _tarefas_soltas.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.debug("Tarefa '%s' terminou com erro: %r", nome, t.exception())

    tarefa.add_done_callback(_fim)
    return tarefa


async def _redis_marcar_parada(executor_id: str) -> None:
    try:
        await (await _get_redis()).setex(_chave_de_parada(executor_id), _TTL_DA_PARADA_S, "1")
    except Exception as exc:
        logger.debug("Marca de parada de '%s' não gravada: %s", executor_id, exc)


async def _redis_limpar_parada(executor_id: str) -> None:
    try:
        await (await _get_redis()).delete(_chave_de_parada(executor_id))
    except Exception as exc:
        logger.debug("Marca de parada de '%s' não limpa: %s", executor_id, exc)


@dataclass(eq=False)
class _Envio:
    texto: str
    prazo: float
    feito: "asyncio.Future"
    estado: str = "na_fila"   # na_fila → escrevendo → fim | desistiu
    inicio: float = 0.0       # monotonic, when the write started


class _Saida:
    """Output queue of ONE executor WebSocket, with a single writer."""

    def __init__(self, ws, executor_id: str | None = None):
        self.ws = ws
        self.executor_id = executor_id
        self.fila: "collections.deque[_Envio]" = collections.deque()
        self.atual: _Envio | None = None
        self.fechando = False
        # Closed because another session took over the executor (takeover, ownership
        # lost): whatever arrives now is delivered by it — see
        # `_conexao_para_envio` and `_encaminhar`.
        self.substituida = False
        # Closed by the takeover NOTICE this listener received: whatever
        # was in the queue was published before the new session subscribed (see
        # `register`), so it only existed here — see `_fechar_nao_entregue`.
        self.avisada = False
        self.erro: BaseException | None = None
        self._tem_item = asyncio.Event()
        self._alarme: "asyncio.TimerHandle | None" = None
        self._marcou_parada = False
        self.escritor = asyncio.create_task(self._escrever(), name="saida-executor")

    # ── the sender ────────────────────────────────────────────────────────────
    def enfileirar(self, texto: str) -> "_Envio | str":
        """Enqueues and returns the send — or FECHANDO. Synchronous on purpose:
        whoever enqueues in sequence (the relay listener) preserves the order."""
        if self.fechando:
            return FECHANDO
        if self.erro is not None:
            raise self.erro
        feito = asyncio.get_running_loop().create_future()
        # An error delivered to someone who already gave up does not become "exception never retrieved".
        feito.add_done_callback(lambda f: f.cancelled() or f.exception())
        envio = _Envio(texto=texto, prazo=_prazo_de_envio(len(texto)), feito=feito)
        self.fila.append(envio)
        self._tem_item.set()
        return envio

    def _espera(self, envio: _Envio) -> float:
        """Its own deadline plus what is ahead: what remains of the deadline of the
        send in progress and the queue's BYTES before it, at the design floor
        (512 KB/s). The 30 s base is counted only once: added per message, a
        queue of 40 small events held the sender for 20 minutes."""
        espera = envio.prazo
        atual = self.atual
        if atual is not None:
            espera += max(0.0, atual.prazo - (time.monotonic() - atual.inicio))
        for outro in self.fila:
            if outro is envio:
                break
            if outro.estado == "na_fila":
                espera += len(outro.texto) / _PRAZO_DE_ENVIO_BYTES_POR_S
        return espera

    async def aguardar(self, envio: _Envio) -> str:
        await asyncio.wait({envio.feito}, timeout=self._espera(envio))
        if envio.feito.done():
            return envio.feito.result()   # ENVIADO, ESCOANDO, FECHANDO — or the socket error
        if envio.estado == "na_fila":
            envio.estado = "desistiu"     # the writer skips it: nothing is written
            return OCUPADO
        return ESCOANDO                   # the write started: the frame is in the buffer

    async def enviar(self, texto: str) -> str:
        if self.atrasada() and not self.fechando:
            # The link is below the floor: in the queue, the message would wait behind the
            # late frame for the whole deadline and come out OCUPADO anyway.
            return OCUPADO
        envio = self.enfileirar(texto)
        if isinstance(envio, str):
            return envio
        return await self.aguardar(envio)

    def atrasada(self) -> bool:
        """The write in progress passed its own deadline (link below the floor)."""
        atual = self.atual
        return atual is not None and time.monotonic() - atual.inicio > atual.prazo

    def encerrar(self, *, substituida: bool = False, avisada: bool = False) -> None:
        """No new sends; the writer's WAIT is canceled — what it already put
        in the buffer keeps going out before the close frame. The queue is resolved right
        here: a writer canceled before its first step never reaches its
        own `except`, and whoever was waiting would wait the whole deadline for an OCUPADO."""
        self.fechando = True
        self.substituida = self.substituida or substituida or avisada
        self.avisada = self.avisada or avisada
        if not self.escritor.done():
            self.escritor.cancel()
        self._resolver_fila(FECHANDO)

    # ── o escritor ────────────────────────────────────────────────────────────
    async def _escrever(self) -> None:
        envio: _Envio | None = None
        try:
            while True:
                while not self.fila:
                    self._tem_item.clear()
                    await self._tem_item.wait()
                envio = self.fila.popleft()
                if envio.estado != "na_fila":     # the sender gave up
                    envio = None
                    continue
                envio.estado = "escrevendo"
                envio.inicio = time.monotonic()
                self.atual = envio
                self._armar_alarme(envio)
                try:
                    await self.ws.send_text(envio.texto)
                finally:
                    self._desarmar_alarme()
                    self.atual = None
                envio.estado = "fim"
                if not envio.feito.done():
                    envio.feito.set_result(ENVIADO)
                envio = None
        except asyncio.CancelledError:
            # Closing: what was being written is already in the buffer.
            if envio is not None and envio.estado == "escrevendo" and not envio.feito.done():
                envio.feito.set_result(ESCOANDO)
            self._resolver_fila(FECHANDO)
            raise
        except Exception as exc:
            # Dead socket: whoever was waiting gets the error, and so do the next ones.
            self.erro = exc
            if envio is not None and not envio.feito.done():
                envio.feito.set_exception(exc)
            self._resolver_fila(exc)

    def _resolver_fila(self, desfecho) -> None:
        while self.fila:
            envio = self.fila.popleft()
            if envio.feito.done():
                continue
            if isinstance(desfecho, BaseException):
                envio.feito.set_exception(desfecho)
            else:
                envio.feito.set_result(desfecho)

    # ── the stall mark ────────────────────────────────────────────────────────
    # Turns on when the write in progress passes its own deadline and turns off when it
    # finishes: the other workers stop relaying ONLY while the link is
    # actually below the floor — not a fixed minute after a large,
    # healthy transfer.
    def _armar_alarme(self, envio: _Envio) -> None:
        if self.executor_id:
            self._alarme = asyncio.get_running_loop().call_later(envio.prazo, self._sinalizar_atraso)

    def _sinalizar_atraso(self) -> None:
        self._marcou_parada = True
        _em_segundo_plano(_redis_marcar_parada(self.executor_id), "marca-parada")
        self._alarme = asyncio.get_running_loop().call_later(_RENOVA_PARADA_S, self._sinalizar_atraso)

    def _desarmar_alarme(self) -> None:
        if self._alarme is not None:
            self._alarme.cancel()
            self._alarme = None
        if self._marcou_parada:
            self._marcou_parada = False
            _em_segundo_plano(_redis_limpar_parada(self.executor_id), "limpa-parada")


def _ws_aberto(ws) -> bool:
    """The app has not requested the close yet and the executor has not disconnected."""
    return (
        getattr(ws, "application_state", None) != WebSocketState.DISCONNECTED
        and getattr(ws, "client_state", None) != WebSocketState.DISCONNECTED
    )


def _saida_de(ws, executor_id: str | None = None) -> _Saida:
    saida = _saidas.get(ws)
    if saida is None:
        saida = _saidas[ws] = _Saida(ws, executor_id)
    elif executor_id and not saida.executor_id:
        saida.executor_id = executor_id
    return saida


async def enviar_ao_executor(ws, texto: str, executor_id: str | None = None) -> str:
    """Sends `texto` through the socket's output — see `_Saida`."""
    return await _saida_de(ws, executor_id).enviar(texto)


def enfileirar_ao_executor(ws, texto: str, executor_id: str | None = None) -> bool:
    """Puts `texto` on the socket's output and moves on, without waiting its turn (for the
    receive loop, which must not get stuck behind a slow frame). With the send
    in progress running late, it discards and returns False: it would only swell the queue."""
    saida = _saida_de(ws, executor_id)
    if saida.atrasada():
        return False
    return not isinstance(saida.enfileirar(texto), str)


def encerrar_envios(ws) -> None:
    """The connection handler is finishing: nothing else goes out through this socket. The
    output stays in the map — whoever sends gets FECHANDO and the relay treats the job as not
    delivered, instead of hitting the dead socket — until `encerrar_saida`, at the end of the
    same handler."""
    _saida_de(ws).encerrar()


def encerrar_saida(ws) -> None:
    """End of the socket's life (the connection handler finished): its output leaves
    the map. It holds the ws, so the WeakKeyDictionary alone would not release it."""
    saida = _saidas.pop(ws, None)
    if saida is not None:
        saida.encerrar()


async def _fechar_depois_do_escritor(ws, saida: "_Saida | None", code: int, reason: str) -> None:
    if saida is not None:
        await asyncio.gather(saida.escritor, return_exceptions=True)
    await ws.close(code=code, reason=reason)


async def fechar_ws_do_executor(
    ws, code: int = 1000, reason: str = "", *, substituida: bool = False, avisada: bool = False,
) -> None:
    """Closes an executor's WebSocket. Every executor socket close goes
    through here.

    With a write draining, its drain stays pending — and with it pending, the
    legacy websockets close raised AssertionError immediately, never reaching
    close_timeout → abort: the socket of a frozen executor stayed alive with
    up to 16 MB in the buffer. That is why the output is shut down first (the writer's
    wait is canceled; what it already wrote goes out before the close frame).
    The close runs in its own task: a caller's `wait_for` does not
    abandon it midway (it reaches the abort even if the requester gives up waiting).

    `substituida`: another session took over the executor — whatever comes for it goes
    through the relay to the new session (see `_conexao_para_envio`). `avisada`: it was the
    takeover notice that arrived (see `_Saida.avisada`).
    """
    saida = _marcar_fechando(ws, substituida=substituida, avisada=avisada)
    fechamento = _em_segundo_plano(_fechar_depois_do_escritor(ws, saida, code, reason), "fecha-ws")
    await asyncio.shield(fechamento)


def _marcar_fechando(ws, *, substituida: bool, avisada: bool = False) -> "_Saida | None":
    """Shuts down the socket's output — creating it, if nothing has gone out through it yet: whoever
    sends during the close gets FECHANDO. Without it, the relay created a new
    output, the writer hit the closed socket and the relayed job was silently lost
    (the socket error does not close the run). What removes it from the map is the end of the handler
    (`encerrar_saida`); on an already-closed socket nothing is created."""
    saida = _saidas.get(ws)
    if saida is None and _ws_aberto(ws):
        saida = _saida_de(ws)
    if saida is not None:
        saida.encerrar(substituida=substituida, avisada=avisada)
    return saida


# ── Tracking of pending ACKs (shared between workers via Redis) ───────────────
# Each in-flight job becomes: executor:pending_ack:{job_id} -> "{executor_id}|{sent_at_unix}"
# with an automatic TTL. The executor:pending_acks:set index lists live IDs so the
# monitor can enumerate without SCAN. The lock ensures only one worker emits the
# warning per cycle in multi-worker deployments.
_PENDING_ACK_TTL_SECONDS = 600
_PENDING_ACKS_INDEX_KEY = "executor:pending_acks:set"
_ACK_MONITOR_LOCK_KEY = "executor:ack_monitor:lock"


def _pending_ack_key(job_id: str) -> str:
    return f"executor:pending_ack:{job_id}"


# Compare-and-delete of the pending_ack in ONE round-trip. Before it was two (GET to
# check the owner, then a GETDEL+SREM pipeline), with a window between them in which
# another session could swap the value.
#
# SEC: ARGV[1] is the executor that SENT the ACK; we only delete if the job was
# dispatched to it. An empty ARGV[1] is the wildcard mode (a caller with no binding to
# prove) — executor_id is never an empty string, so there is no way for an ACK to forge
# that mode. Returns: nil (unknown job), {0, owner} (impostor),
# {1, value} (clean).
_LUA_CLEAR_PENDING_ACK = """
local raw = redis.call('GET', KEYS[1])
if not raw then
  return nil
end
local sep = string.find(raw, '|', 1, true)
local owner = sep and string.sub(raw, 1, sep - 1) or raw
if ARGV[1] ~= '' and owner ~= ARGV[1] then
  return {0, owner}
end
redis.call('DEL', KEYS[1])
redis.call('SREM', KEYS[2], ARGV[2])
return {1, raw}
"""


# ── Singleton Redis pool ──────────────────────────────────────────────────────
# Reuses the same connection across all registry operations. Creating+closing
# a connection on every setex/exists/delete (as before) is costly: heartbeat
# (30s) + capacity (10s) × N executors turn into needless connect pressure.
_redis_singleton: _aioredis.Redis | None = None
_redis_lock = asyncio.Lock()


async def _get_redis() -> _aioredis.Redis:
    """Returns the registry's singleton Redis client.

    Lazy initialization, thread-safe via Lock. Do NOT call aclose() on the return value.
    """
    global _redis_singleton
    if _redis_singleton is not None:
        return _redis_singleton
    async with _redis_lock:
        if _redis_singleton is None:
            _redis_singleton = _aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_singleton


async def _reset_redis_singleton() -> None:
    """Invalidates the singleton — the next _get_redis() recreates the client.

    Called when an operation fails with ConnectionError or a protocol error,
    preventing the singleton from getting stuck in a bad state after a Redis blip.
    """
    global _redis_singleton
    if _redis_singleton is None:
        return
    async with _redis_lock:
        old = _redis_singleton
        _redis_singleton = None
    try:
        await asyncio.wait_for(old.aclose(), timeout=1.0)
    except Exception:
        pass  # aclose on an already-bad conn may fail; that's fine


async def _redis_claim_presence(executor_id: str, owner_token: str) -> str | None:
    """Takes global ownership of the connection and marks presence. Returns the token of the
    previous owner (None if there was no owner, or on a Redis failure).

    Whoever connects last wins: the executor only opens a new WS after the
    old one has dropped from ITS point of view, so the most recent session is the
    good one. The notice to the losing worker always goes out, with or without a previous owner (see
    `register`): the ownership of a session that is still closing may have expired.
    """
    try:
        rc = await _get_redis()
        owner_key = _conn_owner_key(executor_id)
        async with rc.pipeline(transaction=True) as p:
            p.getset(owner_key, owner_token)
            p.expire(owner_key, _PRESENCE_TTL)
            p.setex(_presence_key(executor_id), _PRESENCE_TTL, "1")
            previous, _, _ = await p.execute()
        return previous
    except Exception as exc:
        logger.warning("Redis: falha ao assumir posse do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_renew_presence(executor_id: str, owner_token: str) -> bool | None:
    """Renews presence + owner as a TRI-STATE.

    True  = renewed, the key is written with a full TTL.
    False = ANOTHER worker is the owner — this WS is the duplicate and must drop.
    None  = couldn't ask (Redis down).

    The `None` exists because "renewed" and "couldn't try" had the same
    return value: the caller marked the renewal as DONE and only tried again a whole
    interval later, while the real key kept aging until it
    expired with the executor alive — and absent presence makes the orphan watchdog
    kill running runs. It remains fail-open where it matters (the WS does not drop over a
    Redis blip): whoever handles the None just reschedules the attempt.
    """
    try:
        rc = await _get_redis()
        kept = await rc.eval(
            _LUA_RENEW_PRESENCE, 2,
            _presence_key(executor_id), _conn_owner_key(executor_id),
            owner_token, str(_PRESENCE_TTL),
        )
        return bool(kept)
    except Exception as exc:
        logger.warning("Redis: falha ao renovar presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_release_presence(executor_id: str, owner_token: str) -> bool | None:
    """Removes presence + ownership by CAS — only if `owner_token` is still the owner.
    Returns whether it released; False when ownership already belongs to another session; None on error."""
    try:
        rc = await _get_redis()
        released = await rc.eval(
            _LUA_RELEASE_PRESENCE, 2,
            _presence_key(executor_id), _conn_owner_key(executor_id),
            owner_token,
        )
        if not released:
            logger.info(
                "Presença do executor '%s' preservada: a posse já é de outra sessão.",
                executor_id,
            )
        return bool(released)
    except Exception as exc:
        logger.warning("Redis: falha ao remover presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_presence_or_unknown(executor_id: str) -> bool | None:
    """Presence in Redis as a TRI-STATE: True (online), False (offline), None (don't know).

    The `None` exists because "the query failed" and "the executor vanished" are different
    facts with opposite costs. Whoever decides DISPATCH can collapse both into
    offline at no cost (not dispatching is the safe side) — that is what
    `_redis_check_presence` does. But whoever decides to DESTROY state (failing orphan
    runs) cannot: a pool blip at the exact moment of the check would kill 40-minute
    runs that are alive and progressing on another worker. That caller
    treats None as "I'll reassess later".
    """
    try:
        rc = await _get_redis()
        exists = await rc.exists(_presence_key(executor_id))
        return bool(exists)
    except Exception as exc:
        logger.warning("Redis: falha ao verificar presença do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_check_presence(executor_id: str) -> bool:
    """Presence as a boolean, FAIL-CLOSED: "don't know" becomes offline.

    Use only where denying is the safe side (dispatch, relay, is_online). For
    destructive decisions use `_redis_presence_or_unknown` and handle the None.
    """
    return (await _redis_presence_or_unknown(executor_id)) is True


# DISPATCH grace period after a clean disconnect (spec §5.1). Presence is
# deleted immediately in the handler's `finally`; without a grace period, an executor that is
# reconnecting (network blip, restart) vanished from the candidate list and the job went
# to the next one — or failed, under the `fail` terminal. Within this window
# absent presence becomes "don't know" and the candidate is TRIED: the real `send_job`
# decides (it fails fast if the executor has not come back). Same order of magnitude as the WS router's
# orphan grace.
_DISPATCH_GRACE_SECONDS = 20.0

# Capacity in Redis (`executor:capacity:{id}`), so that `send_job`'s RELAY path
# refuses a full executor as the direct path does. Rewritten only
# when it changes or every interval — capacity arrives every ~10s per executor.
_CAPACITY_STORE_INTERVAL = 30.0


def _capacity_key(executor_id: str) -> str:
    return f"executor:capacity:{executor_id}"


def _capacity_is_full(c: dict | None) -> bool:
    """Fila local cheia (back-pressure) — a MESMA conta nos dois caminhos."""
    if not c:
        return False
    return (c.get("queued", 0) + c.get("running", 0)) >= (
        c.get("max_concurrent", 4) + c.get("max_queue", 50)
    )


async def _redis_store_capacity(executor_id: str, capacity: dict) -> None:
    try:
        rc = await _get_redis()
        await rc.set(_capacity_key(executor_id), json.dumps(capacity), ex=_PRESENCE_TTL)
    except Exception as exc:
        logger.warning("Redis: falha ao gravar capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()


async def _redis_delete_capacity(executor_id: str) -> None:
    """Deletes the published capacity when the WS drops: without this, a saturated
    executor that reconnects on ANOTHER worker stays "full" for the relay for up to
    one TTL — and in an isolated single-executor workspace that is a failed run."""
    try:
        rc = await _get_redis()
        await rc.delete(_capacity_key(executor_id))
    except Exception as exc:
        logger.warning("Redis: falha ao apagar capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()


def _capacidade_de(raw) -> dict | None:
    """The value of `executor:capacity:{id}` as a dict; None if absent or unreadable."""
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode()
        cap = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    return cap if isinstance(cap, dict) else None


async def _redis_read_capacity(executor_id: str) -> dict | None:
    """Capacity published by the worker that holds the WS; None = unknown."""
    try:
        rc = await _get_redis()
        return _capacidade_de(await rc.get(_capacity_key(executor_id)))
    except Exception as exc:
        logger.warning("Redis: falha ao ler capacidade do executor '%s': %s", executor_id, exc)
        await _reset_redis_singleton()
        return None


async def _redis_read_capacities(executor_ids: list[str]) -> dict[str, dict | None]:
    """`_redis_read_capacity` of several executors in a single trip (MGET)."""
    try:
        rc = await _get_redis()
        valores = await rc.mget(*[_capacity_key(i) for i in executor_ids])
    except Exception as exc:
        logger.warning("Redis: falha ao ler a capacidade de %d executores: %s", len(executor_ids), exc)
        await _reset_redis_singleton()
        return dict.fromkeys(executor_ids)
    return {i: _capacidade_de(v) for i, v in zip(executor_ids, valores)}


# Default capacity reported before the executor's first capacity heartbeat
_DEFAULT_CAPACITY = {
    "queued": 0,
    "running": 0,
    "max_concurrent": 4,
    "max_queue": 50,
}


@dataclass
class ExecutorConnection:
    executor_id:    str
    websocket:   WebSocket
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executor_version: Optional[str] = None
    executor_ip:    Optional[str] = None
    capacity:    dict = field(default_factory=lambda: dict(_DEFAULT_CAPACITY))
    system_info: Optional[dict] = None
    # Set when the executor sent the handshake — earlier messages are
    # rejected. See SEG/R3 in the WS router.
    handshake_received: bool = False
    # Unique token of this connection. It is what appears in `executor:conn_owner:{id}`
    # while this session is the owner — see `_conn_owner_key`.
    owner_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    # Ceilings from the Executor's record in the database (max_concurrent_jobs /
    # max_queue_size). The `capacity` is SELF-DECLARED by the executor: without a clamp,
    # announcing max_queue=10**9 attracted every job in the pool to it.
    max_concurrent_limit: int = _DEFAULT_CAPACITY["max_concurrent"]
    max_queue_limit:      int = _DEFAULT_CAPACITY["max_queue"]
    # Authorization memo run_id → (authorized, monotonic deadline). Avoids one
    # Postgres SELECT per node_event (the run→host binding is immutable after the
    # dispatch). Lives IN THE CONNECTION: never crosses executors and vanishes on unregister.
    run_auth_cache: dict[str, tuple[bool, float]] = field(default_factory=dict)
    # Instant (monotonic) of the last presence renewal in Redis. register
    # already writes the key with a full TTL, so the connection is born "renewed" — see
    # `_PRESENCE_RENEW_INTERVAL`.
    last_presence_renew: float = field(default_factory=time.monotonic)
    # Short authorization circuit breaker: while it holds, the verdict is denied
    # WITHOUT touching the database. See `_run_belongs_to_agent` in the WS router.
    db_auth_cooldown_until: float = 0.0

    # Throttle of capacity publication to Redis (see _CAPACITY_STORE_INTERVAL).
    last_capacity_store: float = 0.0
    last_capacity_stored: tuple | None = None
    # Instant (monotonic) of the last reconciliation from the executor's inventory.
    # Zero on purpose: the first one, right after connecting, never waits. See
    # `_reconciliar_inventario` in the WS router.
    ultima_reconciliacao: float = 0.0

    def is_full(self) -> bool:
        """Returns True if the executor's local queue is full (back-pressure)."""
        return _capacity_is_full(self.capacity)


async def _redis_outra_sessao(executor_id: str, owner_token: str | None) -> bool | None:
    """Does another session hold ownership of this executor? None: couldn't tell."""
    try:
        dono = await (await _get_redis()).get(_conn_owner_key(executor_id))
    except Exception as exc:
        logger.debug("Posse do executor '%s' não conferida: %s", executor_id, exc)
        return None
    return dono is not None and dono != owner_token


async def _fechar_nao_entregue(
    executor_id: str, job_id: str, motivo: str, dono: str | None, *, so_aqui: bool = False,
) -> None:
    """Whoever published on the relay already treated the job as delivered (the run goes to 'running'):
    without this it stayed "Em andamento" (in progress) until the pending ACK expired (10 min).

    Only closes it if no other session could have received it. `so_aqui`: it was
    in the queue when the takeover notice arrived — published before the new session
    subscribed. Otherwise, the ownership in Redis decides: still this session's (or
    nobody's) means no new session subscribed before this instant,
    so none received it. With ownership held by another (an executor that reconnected without
    the notice reaching here) it may have delivered it, and closing the run would make the
    inventory order the running job to stop: it is left to reconciliation.
    """
    if not so_aqui:
        outra = await _redis_outra_sessao(executor_id, dono)
        if outra is not False:
            logger.warning(
                "Job '%s' não saiu pelo socket do executor '%s' (%s), mas %s — a reconciliação decide o run.",
                job_id, executor_id, motivo,
                "outra sessão já assumiu o executor" if outra else "a posse não pôde ser conferida",
            )
            return
    from app.api.routers.executor_ws.orfaos import fechar_run_nao_entregue
    try:
        await fechar_run_nao_entregue(executor_id, job_id, conexao_fechando=motivo != OCUPADO)
    except Exception as exc:
        logger.error("Run '%s' não entregue pelo relay não pôde ser fechado: %s", job_id, exc)


async def _acompanhar_encaminhamento(
    executor_id: str, saida: _Saida, envio: _Envio, canal: str, tipo: str | None,
    job_id: str | None, dono: str | None,
) -> None:
    """Waits for the outcome of a message the listener enqueued — without holding up
    the listener, which handles ALL of the executor's messages (including the close
    marker) and must not let them age behind a large frame."""
    try:
        resultado = await saida.aguardar(envio)
    except Exception as exc:
        # Dead socket: nothing went out through it (a frame cut off midway is never
        # read by the executor).
        logger.debug("%s: mensagem ao executor '%s' não saiu: %s", canal, executor_id, exc)
        if job_id:
            await _fechar_nao_entregue(executor_id, job_id, "erro do socket", dono)
        return
    if resultado == ENVIADO:
        return
    if resultado == ESCOANDO:
        logger.warning("%s: envio ao executor '%s' passou do prazo — link lento; o frame segue saindo.",
                       canal, executor_id)
        return
    logger.warning("%s: mensagem '%s' ao executor '%s' não saiu (%s).", canal, tipo or "?", executor_id, resultado)
    if job_id:
        # FECHANDO here belongs to a message that was already in the queue when the socket
        # started closing.
        await _fechar_nao_entregue(
            executor_id, job_id, resultado, dono, so_aqui=resultado == FECHANDO and saida.avisada,
        )


def _encaminhar(
    executor_id: str, ws, payload: str, canal: str, tipo: str | None, job_id: str | None, dono: str | None,
) -> None:
    saida = _saida_de(ws, executor_id)
    try:
        envio = saida.enfileirar(payload)
    except Exception:
        # Dead socket: the error propagates (the listener ends), but whoever published
        # counted on this listener.
        if job_id:
            _em_segundo_plano(
                _fechar_nao_entregue(executor_id, job_id, "erro do socket", dono), f"nao-entregue-{job_id[:8]}",
            )
        raise
    if not isinstance(envio, str):
        _em_segundo_plano(
            _acompanhar_encaminhamento(executor_id, saida, envio, canal, tipo, job_id, dono),
            f"encaminha-{executor_id[:8]}",
        )
        return
    if saida.substituida:
        # Arrived after the takeover: the new session's listener also receives it.
        # Rare window: published between the notice and its subscription (one round
        # trip to Redis, more if the subscription fails), nobody delivers it — the
        # reconciliation closes the run when the pending ACK expires.
        logger.debug("%s: socket do executor '%s' substituído — '%s' fica com a sessão nova.",
                     canal, executor_id, tipo or "?")
        return
    # The executor is going away (heartbeat, protocol error, disconnect):
    # this listener may be the only recipient, and whoever published counted on it.
    if not job_id:
        logger.debug("%s: socket do executor '%s' fechando — '%s' descartado.", canal, executor_id, tipo or "?")
        return
    logger.warning("%s: socket do executor '%s' fechando — job '%s' não encaminhado.", canal, executor_id, job_id)
    _em_segundo_plano(_fechar_nao_entregue(executor_id, job_id, FECHANDO, dono), f"nao-entregue-{job_id[:8]}")


async def _handle_relay_message(
    executor_id: str, ws: "WebSocket", owner_token: str, raw: str,
) -> bool:
    """Handles a message from the relay channel. Returns False to end the listener.

    Extracted from the loop so that relay and drive events can share ONE single
    pubsub — see `_executor_pubsub_listener`.
    """
    # ── Verifies the envelope's HMAC ──────────────────────────────────────────
    # Any publisher without APP_SECRET (e.g. an external container
    # accessing Redis) produces messages without a valid signature and is discarded here.
    payload = open_signed_envelope(
        raw, channel_label="Relay",
        executor_id=executor_id, audience=_AUDIENCE_RELAY,
    )
    if payload is None:
        return True

    # Parse the payload once — used to detect the internal close marker
    # (not forwarded). Backpressure is the CLIENT's job
    # (executor/connection.py:_handle_job), which already emits `job_result` with the error
    # "fila cheia" (queue full) so that the server marks the run as failed. Filtering here was
    # a duplicate and left runs "running" forever.
    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError:
        parsed_payload = None

    # ── Internal close marker (disconnect_executor) ───────────────────────────
    # Payload published by `disconnect_executor` to force a remote close
    # of the WS. Not forwarded to the client — it only causes a local close, cleanup and
    # ends the listener.
    if isinstance(parsed_payload, dict):
        internal = parsed_payload.get("__internal__")

        # ── Takeover marker (another session took ownership) ──
        # Only arrives here via an envelope signed with APP_SECRET and bound to THIS
        # executor, so it cannot be forged from outside.
        if isinstance(internal, dict) and "takeover" in internal:
            new_owner = (internal.get("takeover") or {}).get("owner")
            if new_owner == owner_token:
                return True  # echo of my own register
            logger.warning(
                "Executor '%s': outra sessão assumiu a conexão — "
                "fechando este WS duplicado (evita execução dupla de job).",
                executor_id,
            )
            try:
                # 4409 (conflict) is NOT terminal on the client: if this socket is still
                # alive on its side, reconnecting is the correct behavior.
                await fechar_ws_do_executor(
                    ws, code=4409, reason="Conexao assumida por outra sessao.", avisada=True,
                )
            except Exception as exc:
                logger.debug(
                    "Relay: falha ao fechar WS duplicado de '%s': %s", executor_id, exc,
                )
            try:
                await executor_registry.unregister(executor_id, expected_ws=ws)
            except Exception as exc:
                logger.debug(
                    "Relay: falha no unregister pos-takeover de '%s': %s", executor_id, exc,
                )
            return False

        if isinstance(internal, dict) and "close" in internal:
            close_cfg = internal.get("close") or {}
            close_code = int(close_cfg.get("code", 1000))
            close_reason = str(close_cfg.get("reason", ""))
            try:
                await fechar_ws_do_executor(ws, code=close_code, reason=close_reason)
            except Exception as exc:
                logger.debug(
                    "Relay: falha ao fechar WS do executor '%s' via marker: %s",
                    executor_id, exc,
                )
            # Immediate cleanup — without waiting the 90s heartbeat timeout. Removes
            # presence + local entry + cancels the listener. The WS handler will fall
            # into its finally right after and will be a no-op via the expected_ws guard.
            try:
                await executor_registry.unregister(executor_id, expected_ws=ws)
            except Exception as exc:
                logger.debug(
                    "Relay: falha no unregister pos-close remoto de '%s': %s",
                    executor_id, exc,
                )
            logger.info(
                "Relay: WS do executor '%s' fechado remotamente (code=%d reason=%r).",
                executor_id, close_code, close_reason,
            )
            return False

    # Forwards the payload to the client. If it is a job and the client's queue is full,
    # it replies with a `job_result` error "back-pressure" and the server marks the run
    # failed via `_handle_job_result` (executor_ws_router.py). Enqueues and moves on:
    # the outcome is tracked outside the listener (see `_acompanhar_encaminhamento`).
    tipo = parsed_payload.get("type") if isinstance(parsed_payload, dict) else None
    job_id = ((parsed_payload or {}).get("envelope") or {}).get("job_id") if tipo == "job" else None
    try:
        _encaminhar(executor_id, ws, payload, "Relay", tipo, str(job_id) if job_id else None, owner_token)
    except Exception as exc:
        logger.warning(
            "Relay: falha ao encaminhar mensagem ao executor '%s': %s", executor_id, exc,
        )
        return False
    return True


async def _handle_drive_message(executor_id: str, ws: "WebSocket", raw: str) -> bool:
    """Handles a message from the drive events channel. False ends the listener."""
    # SEC: same HMAC check as the job relay. Before, this channel passed the
    # raw Redis payload straight to the WS — anyone able to publish on it could inject
    # any message into the executor, including
    # {"type":"control","action":"shutdown"} (DoS) and
    # {"type":"control","action":"config_changed"} (SIGTERM in a loop), besides
    # forged drive_events.
    payload = open_signed_envelope(
        raw, channel_label="Drive event",
        executor_id=executor_id, audience=_AUDIENCE_DRIVE,
    )
    if payload is None:
        return True
    # Only drive_event travels on this channel — control/job have their own route.
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        parsed = None
    if not isinstance(parsed, dict) or parsed.get("type") != "drive_event":
        logger.warning(
            "Drive event: tipo inesperado no canal do executor '%s' — descartado.",
            executor_id,
        )
        return True
    saida = _saidas.get(ws)
    if saida is not None and saida.atrasada():
        # Link below the floor: the event would only swell the queue behind the late
        # frame. A drive event is best-effort — GeoSync resynchronizes.
        logger.debug("Drive event ao executor '%s' descartado: envio anterior atrasado.", executor_id)
        return True
    try:
        # Same listener as the job relay: enqueues and moves on.
        _encaminhar(executor_id, ws, payload, "Drive event", "drive_event", None, None)
    except Exception as exc:
        logger.warning("Drive event: falha ao encaminhar ao executor '%s': %s", executor_id, exc)
        return False
    return True


async def _executor_pubsub_listener(executor_id: str, ws: "WebSocket", owner_token: str) -> None:
    """
    Subscribes to the 'executor:job_relay:{id}' and 'executor:{id}:drive_events' channels
    on a SINGLE pubsub and forwards each message to the executor's WebSocket. Runs
    as a task while the executor is connected.

    Lets uvicorn workers that don't hold the WS in memory send jobs via Redis pub/sub.

    PERF: there used to be TWO dedicated Redis connections per connected executor per worker
    (one per listener), each with its own pool — in a fleet of 200 executors
    and 4 workers that added up to ~1600 sockets just for pubsub, and a burst
    reconnection (deploy, network blip) brought them all up at once, pressuring
    `maxclients` precisely when dispatch needs Redis the most. One pubsub
    subscribes to both channels and dispatch is by `message["channel"]`, each with
    the envelope validation of ITS purpose (audience RELAY vs DRIVE) — the cross-channel
    anti-replay binding stays exactly where it was.

    ROBUSTNESS:
      - Validates backpressure before forwarding (the publisher on another worker does not
        know the local capacity).
      - Auto-restart with exponential backoff if the Redis connection drops (timeout/
        connection refused). Without it, a single transient error leaves the executor
        unreachable via relay until it reconnects — which caused the
        "online in Redis but no active relay listener" scenario in production.
      - Backoff only resets after staying healthy for _HEALTHY_THRESHOLD seconds —
        avoids TCP churn in a tight loop when the problem is persistent
        (e.g. a socket_timeout misconfig making the read blow up every 5s).
      - A read TimeoutError on the pubsub is demoted to DEBUG (a routine
        cause); every _NOISY_WARN_EVERY reconnections it logs 1 aggregated
        WARNING for operations. Other errors remain an immediate WARNING.
      - Per-executor restart counter (increment_listener_restart) feeds
        the aggregated WARNING above.
      - Clean exit on CancelledError (the registry canceled) via try/finally
        (CancelledError inherits from BaseException, it does not fall into except Exception).

    `owner_token` identifies THIS session. The channel also carries the internal
    `__internal__.takeover` marker, published by whoever takes global ownership of the
    connection: a listener that receives a takeover with a token different from its own knows
    it has become a duplicate and closes its own WS right away (without waiting for the heartbeat).
    """
    relay_ch = _relay_channel(executor_id)
    drive_ch = _drive_channel(executor_id)
    channels = (relay_ch, drive_ch)
    backoff = 1.0
    _MAX_BACKOFF = 30.0
    _HEALTHY_THRESHOLD = 60.0    # seconds of health before the backoff is reset
    _NOISY_WARN_EVERY = 50       # aggregated logs every N consecutive reconnections
    iteration = 0

    while True:
        iteration += 1
        rc: _aioredis.Redis | None = None
        pubsub = None
        ws_closed = False
        subscribed_at: float | None = None
        try:
            # PubSub uses a dedicated connection (not the singleton) — listen() blocks
            # and we accommodate one connection per active listener.
            # Explicit override: production showed an effective socket_timeout of ~5s
            # coming from somewhere opaque (probably REDIS_URL with a query).
            # socket_timeout=None ensures pubsub.listen() blocks while idle.
            # socket_keepalive=True + health_check_interval=30 cover detection
            # of dead connections at the OS level and the redis protocol level.
            rc = _aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=None,
                socket_connect_timeout=10,
                socket_keepalive=True,
                health_check_interval=30,
            )
            pubsub = rc.pubsub()
            await pubsub.subscribe(*channels)
            subscribed_at = time.monotonic()
            if iteration == 1:
                logger.debug("Pubsub listener iniciado para executor '%s'.", executor_id)
            else:
                restart_count = executor_registry.increment_listener_restart(executor_id, "pubsub")
                if restart_count % _NOISY_WARN_EVERY == 0:
                    logger.warning(
                        "Pubsub listener para executor '%s' acumulou %d reconexões — "
                        "investigar saúde do Redis pubsub.",
                        executor_id, restart_count,
                    )
                else:
                    logger.debug(
                        "Pubsub listener reconectado para executor '%s' (tentativa %d).",
                        executor_id, restart_count,
                    )
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                # The channel decides the validation: a drive envelope presented on the
                # relay channel (or vice versa) is still rejected by the
                # envelope's `audience`.
                if message["channel"] == relay_ch:
                    alive = await _handle_relay_message(
                        executor_id, ws, owner_token, message["data"],
                    )
                else:
                    alive = await _handle_drive_message(executor_id, ws, message["data"])
                if not alive:
                    ws_closed = True
                    break
        except _RedisTimeoutError as exc:
            # Routine cause (pubsub read hitting socket_timeout). Kept at DEBUG
            # by default; the aggregated WARNING already alerts operations.
            logger.debug(
                "Pubsub listener: timeout no read (executor '%s'): %s", executor_id, exc,
            )
        except Exception as exc:
            logger.warning(
                "Pubsub listener erro (executor '%s'): %s — reiniciando em %.1fs.",
                executor_id, exc, backoff,
            )
        finally:
            # CancelledError inherits from BaseException and lands here too.
            # _cleanup_pubsub is best-effort and idempotent.
            await _cleanup_pubsub(pubsub, rc, channels, "pubsub", executor_id)

        # Do not restart if the WS is already down — whoever handles unregister will cancel.
        if ws_closed or ws.client_state == WebSocketState.DISCONNECTED:
            break

        # Reset the backoff only if it stayed healthy long enough.
        # In a tight loop (recurring timeout), backoff grows up to MAX_BACKOFF.
        elapsed = (time.monotonic() - subscribed_at) if subscribed_at else 0.0
        if elapsed >= _HEALTHY_THRESHOLD:
            backoff = 1.0
        else:
            backoff = min(backoff * 2, _MAX_BACKOFF)

        # Spread out the wait (50–100%) — see flow/utils/backoff.py. All the
        # listeners of an API that lost Redis restart together; without jitter
        # they hit it again at the same instant.
        await asyncio.sleep(com_jitter(backoff))

    logger.debug("Pubsub listener encerrado para executor '%s'.", executor_id)


async def _cleanup_pubsub(
    pubsub, rc: "_aioredis.Redis | None", channels, label: str, executor_id: str,
) -> None:
    """Close a listener's Redis pubsub/connection — best-effort, never raises."""
    if isinstance(channels, str):
        channels = (channels,)
    if pubsub is not None:
        try:
            await asyncio.wait_for(pubsub.unsubscribe(*channels), timeout=2.0)
            await asyncio.wait_for(pubsub.aclose(), timeout=2.0)
        except Exception as exc:
            logger.debug("Falha ao fechar pubsub do %s (executor '%s'): %s", label, executor_id, exc)
    if rc is not None:
        try:
            await asyncio.wait_for(rc.aclose(), timeout=2.0)
        except Exception as exc:
            logger.debug("Falha ao fechar conexão Redis do %s (executor '%s'): %s", label, executor_id, exc)




class ExecutorConnectionRegistry:
    """
    Keeps an executor_id → ExecutorConnection map for active WebSocket connections.

    Thread-safety: asyncio is single-threaded per worker; we use asyncio.Lock
    in update_capacity to guarantee logical atomicity when multiple
    await points occur in sequence.
    """

    def __init__(self):
        self._connections: dict[str, ExecutorConnection] = {}
        # ONE pubsub task per executor: relay and drive events share the same
        # Redis client (see `_executor_pubsub_listener`).
        self._listener_tasks: dict[str, asyncio.Task] = {}
        # Local presence cache (executor_id → (online, timestamp)) with a short TTL.
        self._presence_cache: dict[str, tuple[bool, float]] = {}
        # executor_id → monotonic time of the last clean disconnect (dispatch grace period).
        self._recent_disconnects: dict[str, float] = {}
        # Listener restart counters (executor_id → {"pubsub": N}): every
        # _NOISY_WARN_EVERY reconnections the listener logs an aggregated WARNING.
        # Reset on unregister.
        self._listener_restarts: dict[str, dict[str, int]] = {}
        # Lock per registration operation to avoid concurrent register+unregister.
        self._register_lock = asyncio.Lock()
        self._capacity_lock = asyncio.Lock()

    def increment_listener_restart(self, executor_id: str, label: str) -> int:
        """Atomically increment a listener's restart counter and return the new value."""
        counters = self._listener_restarts.setdefault(executor_id, {})
        counters[label] = counters.get(label, 0) + 1
        return counters[label]

    # ── Connection management ─────────────────────────────────────────────────

    async def register(
        self,
        executor_id: str,
        ws: WebSocket,
        executor_version: str | None = None,
        *,
        max_concurrent_limit: int | None = None,
        max_queue_limit: int | None = None,
    ):
        """Register the connection and take GLOBAL OWNERSHIP of it.

        `max_concurrent_limit`/`max_queue_limit` come from the Executor's record
        in the database (read by the router during mTLS validation, with no extra
        query) and act as a ceiling for the self-declared capacity — see S3 in the
        WS router.
        """
        # Idempotence: if a connection already exists for this executor_id, drop the old one
        # before registering the new one (avoids two workers fighting over the same slot).
        async with self._register_lock:
            if executor_id in self._connections:
                logger.warning("Executor '%s' já registrado — substituindo conexão anterior.", executor_id)
                await self._unregister_locked(executor_id)

            executor_ip = ip_do_websocket(ws)
            conn = ExecutorConnection(
                executor_id=executor_id,
                websocket=ws,
                executor_version=executor_version,
                executor_ip=executor_ip,
            )
            if max_concurrent_limit is not None:
                conn.max_concurrent_limit = max_concurrent_limit
            if max_queue_limit is not None:
                conn.max_queue_limit = max_queue_limit
            # Until the first `capacity`, assume the executor is empty with the
            # database limits — dispatch must not see more headroom than exists.
            conn.capacity = {
                "queued":         0,
                "running":        0,
                "max_concurrent": conn.max_concurrent_limit,
                "max_queue":      conn.max_queue_limit,
            }
            self._connections[executor_id] = conn

            await _redis_claim_presence(executor_id, conn.owner_token)
            # New socket, nothing draining: a stop mark from the previous session
            # would refuse the relay to a healthy executor for up to 60 s.
            try:
                await (await _get_redis()).delete(_chave_de_parada(executor_id))
            except Exception as exc:
                logger.debug("Marca de parada de '%s' não limpa no registro: %s", executor_id, exc)
            # Publish the initial (empty) capacity: the relay of other workers
            # must not inherit an old "full" until the first heartbeat.
            await _redis_store_capacity(executor_id, conn.capacity)
            conn.last_capacity_store = time.monotonic()
            # Invalidate the local cache — the executor is online now.
            self._presence_cache[executor_id] = (True, time.monotonic())

            # Notify any previous session through the relay (possibly on ANOTHER
            # uvicorn worker, with the WS still alive) to close immediately —
            # without this, both would receive the same job via PUBLISH and the
            # workflow would run twice. Even with no previous owner in Redis: the
            # ownership of a session that is still closing (heartbeat timed out)
            # expires mid-close, and its listener needs to know it was replaced.
            #
            # The notice goes out BEFORE this session's listener exists: whatever
            # was published before it stays only with the old session, which on
            # closing treats it as undelivered (see `_Saida.avisada`) — never
            # with both.
            await self._announce_takeover(executor_id, conn.owner_token)

            # A single listener covers relay (jobs dispatched by other
            # workers) AND drive events — both channels arrive on the same pubsub.
            task = asyncio.create_task(
                _executor_pubsub_listener(executor_id, ws, conn.owner_token),
                name=f"pubsub-{executor_id[:8]}",
            )
            self._listener_tasks[executor_id] = task

            logger.info("Executor '%s' conectado (versão=%s).", executor_id, executor_version)

    async def _unregister_locked(
        self, executor_id: str, expected_ws: "WebSocket | None" = None,
    ) -> None:
        """Internal implementation — assumes the caller already holds self._register_lock.

        If `expected_ws` is passed, removal only happens when the currently
        registered WS is identically that one (`is`). Avoids the classic
        race: handler A falls into finally and calls unregister AFTER the
        executor has already reconnected and handler B registered WS_B —
        without this check, A removed the legitimate WS_B and the executor
        started flapping.
        """
        current = self._connections.get(executor_id)
        if expected_ws is not None and current is not None and current.websocket is not expected_ws:
            # The current WS belongs to another session (recent reconnection). Leave it alone.
            logger.debug(
                "unregister ignorado para '%s': WS atual pertence a sessao diferente.",
                executor_id,
            )
            return

        conn = self._connections.pop(executor_id, None)
        # Release via CAS: only deletes presence/owner if THIS session is still
        # the owner. Without a local connection there is no token, so nothing
        # to prove — and the unconditional DELETE that used to be here
        # invalidated another uvicorn worker's live session ("503 Nenhum
        # executor disponível" (no executor available) with the executor
        # online). The 120s TTL covers the case of a worker dying without
        # unregister.
        if conn is not None:
            # Capacity only goes away with ownership: after a takeover the key already
            # belongs to the new session, and deleting it zeroed the capacity it published.
            if await _redis_release_presence(executor_id, conn.owner_token) is not False:
                await _redis_delete_capacity(executor_id)
            self._recent_disconnects[executor_id] = time.monotonic()
        self._presence_cache[executor_id] = (False, time.monotonic())
        # Reset the restart counter — the next register is a new cycle.
        self._listener_restarts.pop(executor_id, None)

        task = self._listener_tasks.pop(executor_id, None)
        if task and not task.done():
            task.cancel()

        if conn:
            # Defensive timeout — ws.close() normally returns quickly (it only sends
            # a frame), but we want an absolute guarantee of not stalling the register lock.
            try:
                await asyncio.wait_for(fechar_ws_do_executor(conn.websocket), timeout=2.0)
            except Exception:
                pass
            logger.info("Executor '%s' desconectado.", executor_id)

    async def _announce_takeover(self, executor_id: str, owner_token: str) -> None:
        """Publish on the relay the marker that tells the old session to close itself."""
        try:
            payload = json.dumps({"__internal__": {"takeover": {"owner": owner_token}}})
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            await rc.publish(_relay_channel(executor_id), envelope)
        except Exception as exc:
            # Not fatal: the loser also finds out on the next presence renewal
            # (`_redis_renew_presence` returns False) — it just takes longer.
            logger.warning(
                "Falha ao anunciar takeover da conexão do executor '%s': %s",
                executor_id, exc,
            )

    async def _renew_presence_or_drop(self, conn: ExecutorConnection) -> None:
        """Renew presence; if global ownership changed, close this duplicate WS.

        THROTTLE: the key lasts 120s and the messages that call this arrive every
        10s — renewing on all of them was one Lua EVAL per message, inside the
        receive loop, delaying the node_event/job_result that came right behind.
        We only renew every `_PRESENCE_RENEW_INTERVAL`; otherwise the local
        connection is sufficient proof that the executor is alive for the cache.

        The throttle timestamp only advances when the renewal ACTUALLY happened.
        Advancing it before the attempt (with `_redis_renew_presence` returning
        "success" on a Redis error) turned a blip into "renewed" for a whole
        interval: the key expired with the WebSocket alive and
        `orphan_runs_watchdog` marked runs that were making progress as failed.
        """
        now = time.monotonic()
        if (now - conn.last_presence_renew) < _PRESENCE_RENEW_INTERVAL:
            self._presence_cache[conn.executor_id] = (True, now)
            return
        resultado = await _redis_renew_presence(conn.executor_id, conn.owner_token)
        if resultado is None:
            # Could not talk to Redis: do NOT stamp the renewal. Reschedule the
            # next attempt for shortly after instead of a full interval, so
            # that Redis recovery rewrites the key before the TTL.
            conn.last_presence_renew = (
                now - _PRESENCE_RENEW_INTERVAL + _PRESENCE_RENEW_RETRY_INTERVAL
            )
            return
        conn.last_presence_renew = time.monotonic()
        if resultado:
            self._presence_cache[conn.executor_id] = (True, conn.last_presence_renew)
            return
        logger.warning(
            "Executor '%s': posse da conexão pertence a outra sessão — "
            "encerrando este WS duplicado.",
            conn.executor_id,
        )
        # Right away, before waiting for the unregister lock: whatever is sent
        # to this executor from now on goes through the relay to the new session.
        # (What was already in the queue is treated as undelivered on close;
        # without the takeover notice, the new session may have received it
        # too — a rare case: it requires the lost notice and a full queue at
        # this very instant.)
        _marcar_fechando(conn.websocket, substituida=True)
        await self.unregister(conn.executor_id, expected_ws=conn.websocket)

    async def unregister(
        self, executor_id: str, expected_ws: "WebSocket | None" = None,
    ):
        """Remove the executor from the registry. If `expected_ws` is passed,
        only removes when the registered WS is identically that one — protects
        against a race when a handler finishes after the executor has already
        reconnected in another session."""
        async with self._register_lock:
            await self._unregister_locked(executor_id, expected_ws=expected_ws)

    def _conexao_para_envio(self, executor_id: str) -> "ExecutorConnection | str | None":
        """The local connection, if it is still usable for sending; None to go
        through the relay (the executor is not on this worker); FECHANDO if it
        is going away — the sender returns False and dispatch tries the next one.

        A connection being closed is not usable. If it was REPLACED (another
        session took over the executor), the sender falls back to the relay and
        the new session's listener delivers. In the other closures (heartbeat,
        protocol error, disconnect, revocation) there is no new session: the only
        relay listener would be this same socket's listener, which would discard
        the message after the publish counted one recipient — the job would go
        to 'running' without ever leaving."""
        conn = self._connections.get(executor_id)
        if conn is None:
            return None
        saida = _saidas.get(conn.websocket)
        if saida is None or not saida.fechando:
            return conn
        return None if saida.substituida else FECHANDO

    async def presence_or_unknown(self, executor_id: str) -> bool | None:
        """TRI-STATE presence for DISPATCH (spec §5.1).

        True  = there is proof of life (WS on this worker, positive cache or live key).
        None  = unknown: Redis down, or a clean disconnect less than
                `_DISPATCH_GRACE_SECONDS` ago (may be reconnecting). Whoever builds
                candidates TRIES the executor — the actual `send_job` decides.
        False = presence absent and outside the grace period: excluded.

        `is_online` remains fail-closed for those who need a boolean.
        """
        if executor_id in self._connections:
            return True
        now = time.monotonic()
        cached = self._presence_cache.get(executor_id)
        if cached is not None and cached[0] and (now - cached[1]) < _PRESENCE_CACHE_TTL:
            return True
        presenca = await _redis_presence_or_unknown(executor_id)
        if presenca is True:
            self._presence_cache[executor_id] = (True, now)
            self._recent_disconnects.pop(executor_id, None)
            return True
        if presenca is None:
            return None
        desconectou_em = self._recent_disconnects.get(executor_id)
        if desconectou_em is not None and (now - desconectou_em) < _DISPATCH_GRACE_SECONDS:
            return None
        self._recent_disconnects.pop(executor_id, None)
        return False

    async def read_capacity(self, executor_id: str) -> dict | None:
        """Known capacity: the local one (WS on this worker) or the one published in Redis."""
        conn = self._connections.get(executor_id)
        if conn is not None:
            return dict(conn.capacity)
        return await _redis_read_capacity(executor_id)

    async def read_capacities(self, executor_ids: list[str]) -> dict[str, dict | None]:
        """`read_capacity` for several executors: local ones from memory, the rest
        in a single round trip to Redis. Dispatch reads every candidate of a tier
        for each job — one GET per candidate opened one Redis connection per executor."""
        capacidades: dict[str, dict | None] = {}
        remotos: list[str] = []
        for eid in executor_ids:
            conn = self._connections.get(eid)
            if conn is not None:
                capacidades[eid] = dict(conn.capacity)
            else:
                remotos.append(eid)
        if remotos:
            capacidades.update(await _redis_read_capacities(remotos))
        return capacidades

    async def read_presence_and_capacities(
        self, executor_ids: list[str],
    ) -> tuple[dict[str, bool], dict[str, dict | None]]:
        """Presence and published capacity of several executors in a single round
        trip to Redis (one MGET of each one's two keys): the same snapshot on any
        worker. It is what the screens read, and therefore:

        - without the positive cache of `is_online`, which on one worker still
          reported "online" until `_PRESENCE_CACHE_TTL` after going down;
        - with the published copy of the capacity even for this worker's
          WebSocket. It is only rewritten when the load changes or every
          `_CAPACITY_STORE_INTERVAL`, so the free disk and RAM in it may be
          up to that old — but they are the same on every worker;
        - offline has no capacity: the copy may outlive presence by up to
          one TTL (removal on unregister failed, or the keys expire at
          different moments).

        Redis down: all offline, as in `is_online`."""
        if not executor_ids:
            return {}, {}
        chaves = [chave for eid in executor_ids for chave in (_presence_key(eid), _capacity_key(eid))]
        try:
            rc = await _get_redis()
            valores = await rc.mget(*chaves)
        except Exception as exc:
            logger.warning(
                "Redis: falha ao ler presença e capacidade de %d executores: %s", len(executor_ids), exc,
            )
            await _reset_redis_singleton()
            return dict.fromkeys(executor_ids, False), dict.fromkeys(executor_ids)
        online: dict[str, bool] = {}
        capacidades: dict[str, dict | None] = {}
        for n, eid in enumerate(executor_ids):
            presenca, capacidade = valores[2 * n], valores[2 * n + 1]
            online[eid] = presenca is not None
            capacidades[eid] = _capacidade_de(capacidade) if online[eid] else None
        return online, capacidades

    async def is_online(self, executor_id: str) -> bool:
        """Check presence in Redis with a short-lived POSITIVE cache.

        Negative caching was removed: a momentary Redis blip or a reconnection
        in progress must not pin the executor as "offline" for 5s in the
        cache — that caused "Nenhum executor disponível" (no executor
        available) right after a normal reconnection. Only positive answers
        are cached; any miss always goes to Redis.
        """
        cached = self._presence_cache.get(executor_id)
        now = time.monotonic()
        if cached is not None and cached[0] and (now - cached[1]) < _PRESENCE_CACHE_TTL:
            return True
        online = await _redis_check_presence(executor_id)
        if online:
            self._presence_cache[executor_id] = (True, now)
        else:
            # Do not cache False: forces a re-check on the next is_online.
            self._presence_cache.pop(executor_id, None)
        return online

    def get(self, executor_id: str) -> ExecutorConnection | None:
        return self._connections.get(executor_id)

    # ── Metadata updates ──────────────────────────────────────────────────────

    async def update_capacity(self, executor_id: str, capacity: dict):
        # The lock prevents two concurrent capacity updates from flipping readers
        # (is_full) to an intermediate state. Rebinding the dict is atomic
        # thanks to the GIL, but pairing it with last_seen_at benefits from the lock.
        async with self._capacity_lock:
            conn = self._connections.get(executor_id)
            if conn:
                conn.capacity = dict(capacity)  # defensive copy
                conn.last_seen_at = datetime.now(timezone.utc)
        # Renew the presence TTL in Redis on every capacity message.
        # Without a local connection there is no way to prove ownership — the one
        # renewing would be a worker without the WS, resurrecting a dead session's presence.
        if conn:
            await self._renew_presence_or_drop(conn)
            # The renewal may have found that another session is the owner and
            # dropped this one: publishing now would overwrite the new session's
            # capacity — in dispatch and on screen — until it rewrites it (30 s).
            if self._connections.get(executor_id) is not conn:
                return
            await self._store_capacity(conn)

    async def _store_capacity(self, conn: ExecutorConnection) -> None:
        """Publish the capacity for the relay; only when it changes or on an interval."""
        c = conn.capacity
        assinatura = (c.get("queued", 0), c.get("running", 0),
                      c.get("max_concurrent", 4), c.get("max_queue", 50))
        now = time.monotonic()
        if assinatura == conn.last_capacity_stored and (now - conn.last_capacity_store) < _CAPACITY_STORE_INTERVAL:
            return
        conn.last_capacity_stored = assinatura
        conn.last_capacity_store = now
        await _redis_store_capacity(conn.executor_id, c)

    async def update_last_seen(self, executor_id: str):
        conn = self._connections.get(executor_id)
        if not conn:
            return
        conn.last_seen_at = datetime.now(timezone.utc)
        # Renew the presence TTL in Redis on every heartbeat
        await self._renew_presence_or_drop(conn)

    # ── Job sending ───────────────────────────────────────────────────────────

    # Window (seconds) after which a job sent without an ACK is considered lost.
    JOB_ACK_WARN_SECONDS = 15.0

    async def record_pending_ack(self, job_id: str, executor_id: str) -> None:
        """Register an in-flight job awaiting the executor's ACK (shared via Redis).

        The main key carries the executor_id and the send timestamp; the index
        set allows enumerating live IDs without a SCAN of the whole database.
        """
        if not job_id or job_id == "?":
            return
        try:
            rc = await _get_redis()
            value = f"{executor_id}|{time.time()}"
            async with rc.pipeline(transaction=True) as p:
                p.set(_pending_ack_key(job_id), value, ex=_PENDING_ACK_TTL_SECONDS)
                p.sadd(_PENDING_ACKS_INDEX_KEY, job_id)
                await p.execute()
        except Exception as exc:
            logger.warning("Redis: falha ao registrar pending_ack '%s': %s", job_id, exc)
            await _reset_redis_singleton()

    async def clear_pending_ack(
        self, job_id: str, *, expected_executor_id: str | None = None,
    ) -> str | None:
        """Remove the job from the pending list — called upon receiving the ACK.

        Returns the executor_id that had been registered, or None if the ACK
        arrived for an unknown job_id (TTL expired, cleanup by another
        worker, or coming from another installation).

        SEC: with `expected_executor_id`, the ACK is only accepted if the job was
        dispatched to that executor. Without this binding, an executor could
        confirm another's jobs (job_id is global), erasing the lost-job evidence
        used by overdue_acks(). The owner check and the removal are ONE Lua
        script: besides cutting a round trip from the hot path of every ACK,
        they close the window that existed between the GET and the GETDEL.
        """
        if not job_id:
            return None
        try:
            rc = await _get_redis()
            result = await rc.eval(
                _LUA_CLEAR_PENDING_ACK, 2,
                _pending_ack_key(job_id), _PENDING_ACKS_INDEX_KEY,
                expected_executor_id or "", job_id,
            )
            if not result:
                return None
            cleared, value = result[0], result[1]
            if not cleared:
                logger.warning(
                    "ACK do job '%s' recusado: enviado por '%s' mas despachado para '%s'.",
                    job_id, expected_executor_id, value,
                )
                return None
            return value.split("|", 1)[0]
        except Exception as exc:
            logger.warning("Redis: falha ao limpar pending_ack '%s': %s", job_id, exc)
            await _reset_redis_singleton()
            return None

    async def overdue_acks(self) -> list[tuple[str, str, float]]:
        """Return (job_id, executor_id, elapsed) tuples for jobs without an ACK for more
        than JOB_ACK_WARN_SECONDS. A background task can consume them for alerts.

        Performs opportunistic cleanup of the index: IDs whose TTL expired are
        removed from the set so ghosts do not pile up.
        """
        try:
            rc = await _get_redis()
            ids = await rc.smembers(_PENDING_ACKS_INDEX_KEY)
            if not ids:
                return []
            keys = [_pending_ack_key(jid) for jid in ids]
            values = await rc.mget(*keys)
            now = time.time()
            overdue: list[tuple[str, str, float]] = []
            ghosts: list[str] = []
            for jid, raw in zip(ids, values):
                if raw is None:
                    ghosts.append(jid)
                    continue
                try:
                    executor_id, sent_at_str = raw.split("|", 1)
                    elapsed = now - float(sent_at_str)
                except (ValueError, TypeError):
                    ghosts.append(jid)
                    continue
                if elapsed >= self.JOB_ACK_WARN_SECONDS:
                    overdue.append((jid, executor_id, elapsed))
            if ghosts:
                await rc.srem(_PENDING_ACKS_INDEX_KEY, *ghosts)
            return overdue
        except Exception as exc:
            logger.warning("Redis: falha ao listar overdue_acks: %s", exc)
            await _reset_redis_singleton()
            return []

    async def list_pending_acks(self) -> list[dict]:
        """List all pending_acks with elapsed (for the admin endpoint)."""
        try:
            rc = await _get_redis()
            ids = await rc.smembers(_PENDING_ACKS_INDEX_KEY)
            if not ids:
                return []
            keys = [_pending_ack_key(jid) for jid in ids]
            values = await rc.mget(*keys)
            now = time.time()
            items: list[dict] = []
            for jid, raw in zip(ids, values):
                if raw is None:
                    continue
                try:
                    executor_id, sent_at_str = raw.split("|", 1)
                    elapsed = round(now - float(sent_at_str), 2)
                except (ValueError, TypeError):
                    continue
                items.append({"job_id": jid, "executor_id": executor_id, "elapsed_seconds": elapsed})
            return items
        except Exception as exc:
            logger.warning("Redis: falha ao listar pending_acks: %s", exc)
            await _reset_redis_singleton()
            return []

    async def send_job(self, executor_id: str, job_message: dict) -> bool:
        """
        Send a job to the executor via WebSocket.

        If the WebSocket is on this worker: sends directly.
        If it is on another worker: publishes on the Redis relay channel.

        Returns True if the send/relay succeeded.
        Returns False if the executor is not online or the queue is full.
        """
        wire_message = {"type": "job", **job_message}
        wire_text    = json.dumps(wire_message)
        job_id       = job_message.get("envelope", {}).get("job_id", "?")

        conn = self._conexao_para_envio(executor_id)
        if conn is FECHANDO:
            logger.warning(
                "Executor '%s' desconectando — job '%s' vai ao próximo candidato.", executor_id, job_id,
            )
            return False

        # ── Direct path: WS is on this worker ────────────────────────────────
        if conn is not None:
            saida = _saida_de(conn.websocket, executor_id)
            if saida.atrasada():
                # The link is below the floor: the next candidate gets this job
                # instead of it queuing behind the delayed frame.
                logger.warning(
                    "Executor '%s' com envio anterior atrasado — tentando o próximo candidato.",
                    executor_id,
                )
                return False
            if conn.is_full():
                logger.warning(
                    "Executor '%s' com fila cheia (queued=%d, running=%d) — back-pressure.",
                    executor_id,
                    conn.capacity.get("queued", 0),
                    conn.capacity.get("running", 0),
                )
                return False
            try:
                resultado = await saida.enviar(wire_text)
            except Exception as exc:
                logger.error("Erro ao enviar job ao executor '%s': %s", executor_id, exc)
                # `expected_ws`: the executor may have already reconnected on THIS worker
                # while the send was failing — dropping the new connection would only
                # cause another reconnection.
                await self.unregister(executor_id, expected_ws=conn.websocket)
                return False
            if resultado in (OCUPADO, FECHANDO):
                # Nothing was written: the next candidate gets the job.
                logger.warning(
                    "Job '%s' não saiu para o executor '%s' (%s) — vai ao próximo candidato.",
                    job_id, executor_id, resultado,
                )
                return False
            if resultado == ESCOANDO:
                # Delivered without confirmation — see `_PRAZO_DE_ENVIO_BASE_S`.
                logger.warning(
                    "Job '%s': envio ao executor '%s' passou do prazo — link lento. O frame "
                    "segue saindo; o ACK, o inventário ou a varredura confirmam ou fecham o run.",
                    job_id, executor_id,
                )
            else:
                logger.info("Job '%s' enviado ao executor '%s' via WebSocket.", job_id, executor_id)
            await self.record_pending_ack(job_id, executor_id)
            return True

        # ── Relay path: WS is on another uvicorn worker ──────────────────────
        # Check presence in Redis before attempting the relay
        if not await _redis_check_presence(executor_id):
            logger.debug("Executor '%s' offline — job não enviado.", executor_id)
            return False

        # The SAME rule as the direct path: full ⇒ refuse ⇒ dispatch tries the
        # next candidate. Previously the relay published without checking capacity,
        # the executor rejected it for a full queue and the run FAILED — the same
        # state produced opposite outcomes depending on which worker served the request.
        capacidade = await _redis_read_capacity(executor_id)
        if _capacity_is_full(capacidade):
            logger.warning(
                "Executor '%s' com fila cheia (relay; queued=%d, running=%d) — back-pressure.",
                executor_id,
                capacidade.get("queued", 0), capacidade.get("running", 0),
            )
            return False
        if await _redis_parada(executor_id):
            # The worker holding the socket is stuck behind a stalled frame:
            # a job published now would wait its turn and be discarded for age.
            logger.warning(
                "Executor '%s' com envio parado noutro worker — job '%s' vai ao próximo candidato.",
                executor_id, job_id,
            )
            return False

        try:
            # Signed envelope — the listener validates the HMAC before forwarding to the WS.
            # Protects against an unauthorized publisher on the Redis channel.
            envelope = build_relay_envelope(wire_text, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                # Executor appears in Redis but no worker has subscribed to the channel yet
                # (race condition at startup — unlikely but possible)
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — job não enviado.",
                    executor_id,
                )
                return False
            logger.info("Job '%s' encaminhado via relay Redis ao executor '%s'.", job_id, executor_id)
            # Tracking shared via Redis: registering here is safe even
            # with the WS on another worker — the ACK will be cleared there.
            await self.record_pending_ack(job_id, executor_id)
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis para executor '%s': %s", executor_id, exc)
            return False

    async def send_json(self, executor_id: str, data: dict) -> bool:
        """Send an arbitrary JSON payload to the executor (e.g. cancel, control).

        Multi-worker uvicorn: if the WS is on another worker, publishes on the
        Redis channel 'executor:job_relay:{id}' (same channel as send_job) —
        the listener holding the WS delivers. Without this relay, control messages
        (e.g. 'action:revoked') died silently when the admin landed on a
        worker without the WS, leaving the executor connected indefinitely
        even though the DB said 'revoked'.

        SEC (S7): `control` and `cancel` are signed HERE, at the single exit
        point, instead of in each router that emits them — there are 6 call sites
        today and a forgotten one would be a command discarded by the executor.
        The relay HMAC only protects the Redis→worker hop; the Ed25519 signature
        protects the command end to end up to the executor and binds it to one
        recipient, a short deadline and a nonce.
        """
        from app.core.control_crypto import sign_if_needed

        try:
            data = sign_if_needed(data, executor_id)
        except RuntimeError as exc:
            # Without a signing key the executor would discard the message
            # anyway. Failing here leaves the reason in the server log
            # instead of becoming "command vanished" on the executor side.
            logger.error(
                "Não foi possível assinar '%s' para o executor '%s': %s",
                data.get("type"), executor_id, exc,
            )
            return False

        conn = self._conexao_para_envio(executor_id)
        if conn is FECHANDO:
            logger.warning(
                "Mensagem '%s' ao executor '%s' não enviada: conexão fechando.", data.get("type"), executor_id,
            )
            return False

        # Caminho direto: WS neste worker.
        if conn is not None:
            try:
                resultado = await enviar_ao_executor(conn.websocket, json.dumps(data), executor_id)
            except Exception as exc:
                logger.warning("Falha ao enviar mensagem direta ao executor '%s': %r", executor_id, exc)
                await self.unregister(executor_id, expected_ws=conn.websocket)
                return False
            if resultado == ENVIADO:
                return True
            logger.warning(
                "Mensagem '%s' ao executor '%s': %s.", data.get("type"), executor_id,
                "link lento; o frame segue saindo" if resultado == ESCOANDO else f"não saiu ({resultado})",
            )
            # ESCOANDO: for the caller — a cancel, for example — the message was
            # delivered. OCUPADO (including right away, with an earlier send
            # delayed) and FECHANDO: nothing went out.
            return resultado == ESCOANDO

        # Caminho relay: WS em outro worker uvicorn.
        if not await _redis_check_presence(executor_id):
            return False
        if await _redis_parada(executor_id):
            # Published now, it would wait its turn behind the stalled frame and be
            # discarded for age — the caller (cancel_run) needs to know.
            return False
        try:
            payload = json.dumps(data)
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — send_json ignorado.",
                    executor_id,
                )
                return False
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis (send_json) para executor '%s': %s", executor_id, exc)
            return False

    async def disconnect_executor(
        self, executor_id: str, *, code: int = 1000, reason: str = "",
    ) -> bool:
        """Force the executor's WebSocket to close.

        If the WS is on this worker: closes directly + local unregister.
        If it is on another worker: publishes the '__internal__.close' marker on
        the Redis relay; the listener detects the marker (does not forward it to
        the client) and closes the local WS.

        Unlike send_json with a control message (which trusts the client
        to leave on its own), this method guarantees the kick even if the client
        is buggy or an old version that ignores control.
        """
        conn = self._connections.get(executor_id)

        # Caminho direto.
        if conn is not None:
            try:
                await fechar_ws_do_executor(conn.websocket, code=code, reason=reason)
            except Exception as exc:
                logger.warning("Falha ao fechar WS local do executor '%s': %s", executor_id, exc)
            await self.unregister(executor_id)
            return True

        # Caminho relay.
        if not await _redis_check_presence(executor_id):
            return False
        try:
            # The '__internal__' marker is removed by the listener before
            # any send_text — the client never sees this payload.
            payload = json.dumps({
                "__internal__": {"close": {"code": code, "reason": reason}},
            })
            envelope = build_relay_envelope(payload, executor_id=executor_id)
            rc = await _get_redis()
            recipients = await rc.publish(_relay_channel(executor_id), envelope)
            if recipients == 0:
                logger.warning(
                    "Executor '%s' online no Redis mas sem relay listener ativo — disconnect ignorado.",
                    executor_id,
                )
                return False
            return True
        except Exception as exc:
            logger.error("Erro no relay Redis (disconnect) para executor '%s': %s", executor_id, exc)
            return False


# Singleton instance — imported by routers and services
executor_registry = ExecutorConnectionRegistry()


def ip_do_websocket(ws) -> Optional[str]:
    """Real IP of the executor at the end of this WebSocket.

    Behind Traefik, `ws.client.host` is the proxy's IP for ALL
    executors — `RunMetrics.executor_ip` recorded the same address for the
    whole fleet. `get_client_ip` only trusts X-Forwarded-For when the peer is
    a proxy listed in TRUSTED_PROXIES.

    No peer, None: preserves the column's NULL — "unknown" would be worse than
    absent because it looks like a value.
    """
    from app.core.trusted_proxy import get_client_ip
    return get_client_ip(ws.client.host, ws.headers.get("x-forwarded-for")) if ws.client else None


# ── Overdue ACK monitor ───────────────────────────────────────────────────────
# Logs periodic warnings for the operator. Launched in the app lifespan
# (app/main.py). In multi-worker deploys, every worker enters here but
# only the one that acquires the distributed lock for the cycle emits the log —
# avoids multiplying warnings across N workers. The automatic TTL in Redis
# takes care of GC.

_ACK_MONITOR_INTERVAL = 30.0    # seconds between sweeps


async def overdue_acks_monitor() -> None:
    """Periodically sweep jobs without an ACK and alert in the log. Cancel on shutdown."""
    worker_token = f"{os.getpid()}-{id(executor_registry)}"
    try:
        while True:
            await asyncio.sleep(_ACK_MONITOR_INTERVAL)
            # Distributed lock: only one worker logs per cycle. A TTL slightly shorter
            # than the interval avoids windows in which nobody takes the lock.
            try:
                rc = await _get_redis()
                got_lock = await rc.set(
                    _ACK_MONITOR_LOCK_KEY,
                    worker_token,
                    nx=True,
                    ex=int(_ACK_MONITOR_INTERVAL) - 5,
                )
            except Exception as exc:
                logger.warning("Redis: falha ao adquirir lock do ACK monitor: %s", exc)
                await _reset_redis_singleton()
                continue
            if not got_lock:
                continue
            items = await executor_registry.overdue_acks()
            if items:
                sample = [(jid[:8], aid[:8], round(e, 1)) for jid, aid, e in items[:5]]
                logger.warning(
                    "ACK overdue: %d job(s) sem confirmação do executor (amostra: %s)",
                    len(items), sample,
                )
    except asyncio.CancelledError:
        pass
