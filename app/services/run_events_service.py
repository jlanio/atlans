"""Events of a run, without WebSocket.

The subscribe → LRANGE → dedup → live pub/sub loop was born inside the
`/ws/workflow/{run_id}` handler and only the execution panel consumed it. The MCP server
(docs/specs/mcp-server.md §6.4) needs the SAME sequence for
`run_workflow(wait=true)` — but with no socket, no frame and no browser on the other
end. Extracting the loop into a generator of `Lote`s makes the WS one client
among others: it wraps each batch in the usual envelope and the MCP parses only
what interests it.

Two contracts live here:

- `iter_run_events(run_id)`: history replay + live stream, in batches of
  RAW JSON strings exactly as they came out of Redis (re-serializing N events so the
  WS could concatenate them again was pure cost); ends at `__workflow_complete__`
  or at the time ceiling.
- `esperar_run(run_id)`: waits for the run to become terminal by combining the events
  (per-node progress) with a poll of `WorkflowRun.status` — because not every run
  ending publishes `__workflow_complete__` (cancel of a `pending` run, orphan
  dispatch, "all refused"), and the consumer writes the row AFTER publishing the
  event.

And the WRITER's side lives here too: the history and channel keys
(`chave_do_historico`, `canal_do_run`), the pipeline that writes a batch of events
(`anexar_eventos`) and the `__workflow_complete__` JSON (`evento_de_conclusao`)
— used by the executor WS publishers and by `publicar_conclusao`.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import Counter, deque
from contextlib import aclosing
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.constants import (
    MAX_EVENTOS_NO_HISTORICO,
    REDIS_TTL_1H,
    WORKFLOW_COMPLETE_NODE,
)
from app.core.db import get_session_async
from app.core.redis import get_redis_pool, new_pubsub_client
from app.core.utils.logger import get_logger
from app.models.workflow_run import WorkflowRun

logger = get_logger(__name__)

# Events per replay BATCH. The gain that matters is this: one WS frame (or one
# consumer iteration) per batch instead of one per event — the densest burst
# on the channel was precisely the moment the panel needs to show up. The
# READ, however, is a single one (see `_ler_historico`): paginating the LRANGE by absolute
# index lost events, because the publisher does LTRIM(-5000,-1) on every batch and
# the list slides between pages.
_REPLAY_CHUNK = 500

# How many RAWs from the end of the replay are remembered to dedup against the
# live stream. The real duplication window is the interval between SUBSCRIBE and
# LRANGE (one round-trip), so this ceiling is more than generous; it exists only
# so memory consumption does not depend on the history size.
_DEDUP_TAIL = 500

# Buffer between the pub/sub and the consumer (browser socket, MCP tool). Without
# it, a slow consumer blocks the loop that drains the pub/sub; the subscriber's
# output buffer grows until `client-output-buffer-limit pubsub` and Redis
# DISCONNECTS the subscriber — the panel stops receiving mid-run, with no error and
# no toast.
_QUEUE_MAXSIZE = 500

# Live stream heartbeat interval. If the channel stays quiet for this
# long (a heavy, slow node, with no stdout), the generator delivers an EMPTY batch
# just so the consumer keeps traffic on the connection. An idle WebSocket is
# dropped silently by Safari (and by proxies/LBs with an idle timeout) WITHOUT
# firing `onclose` on the client — so a long node killed the connection and the panel
# spun forever. The value sits comfortably below typical idle timeouts
# (30-60s), and the data loss from the performance MR (coalesced/discardable
# stdout) is what started leaving the channel silent long enough for this to
# happen.
_HEARTBEAT_S = 20.0

# Markers of discardable events when the queue fills up. The publisher's `json.dumps`
# uses separators with a space, but we accept both spellings so as not to
# depend on it. Any event that does NOT match here counts as lifecycle and
# is preserved — erring on the side of keeping is the right call.
_DROPPABLE_MARKERS = (
    '"kind": "stdout"', '"kind":"stdout"',
    '"kind": "debug"',  '"kind":"debug"',
)

# After the live `__workflow_complete__` the `workflow_runs` row may still
# be non-terminal: the consumer publishes the event and only then writes the
# status. This is the ceiling (and the step) of the short poll that closes that window; going
# past it means the consumer is stalled, and we return what the row says.
_POLL_POS_COMPLETE_MAX_S = 10.0
_POLL_POS_COMPLETE_S = 0.5

# CONSECUTIVE failures tolerated in the `WorkflowRun.status` poll before the
# wait gives up. A connection checkout that hit the pool timeout, a
# `SQLAlchemyError` from a recycled connection or a network blip are transient: the
# next attempt, `poll_s` later, usually goes through. Bringing down the whole wait
# on the first of them — with the event channel intact, delivering progress —
# traded a database hiccup for an error in the caller's face. The counter
# resets on every successful read, so only a real outage (three
# in a row) propagates.
_POLL_FALHAS_CONSECUTIVAS_MAX = 3

# What counts as a TRANSIENT poll failure. `asyncio.TimeoutError` covers the
# pool checkout that timed out (up to 3.10 it was a class separate from
# `TimeoutError`; from 3.11 on it is the same, and both stay for clarity);
# `OSError` is the database socket dropping.
# `CancelledError` is NOT included: it inherits from `BaseException` and must keep
# propagating to cancel the task.
_ERROS_POLL_TRANSITORIOS = (SQLAlchemyError, OSError, asyncio.TimeoutError, TimeoutError)

# TERMINAL vocabulary of `WorkflowRun.status` — the same one
# `executor_ws_router` uses to avoid regressing an already closed run.
_STATUS_TERMINAIS = frozenset({"success", "failed", "cancelled"})


# ── Where a run's events live ────────────────────────────────────────────────
#
# The two keys were built by hand in six places (four publishers, two
# readers) and the write pipeline was copied in four: a copy that
# diverged in spelling, ceiling or TTL broke nothing at the time — the panel
# just stopped seeing the event.


def chave_do_historico(run_id: str) -> str:
    """LIST with the run's events: the replay for whoever opens the panel later."""
    return f"workflow:{run_id}:history"


def canal_do_run(run_id: str) -> str:
    """Pub/sub channel of the run's events, live."""
    return f"workflow:{run_id}:events"


def anexar_eventos(pipe, run_id: str, payloads: list[str]) -> None:
    """Queues on `pipe` the writing of `payloads` (ready JSON) to the run.

    History BEFORE the channel and in the same pipeline: that is what makes the
    duplicates at the replay↔live boundary a prefix of the stream (see
    `_stream_ao_vivo`). The `ltrim` holds the `MAX_EVENTOS_NO_HISTORICO` ceiling and
    the `expire` renews the TTL on every write.

    The pipeline belongs to the caller, who also executes it: that is how the
    inconclusive run writes the event in the SAME round-trip in which it closes the run, and how
    a batch of node_events from several runs goes out at once.
    """
    historico = chave_do_historico(run_id)
    pipe.rpush(historico, *payloads)
    pipe.ltrim(historico, -MAX_EVENTOS_NO_HISTORICO, -1)
    pipe.expire(historico, REDIS_TTL_1H)
    canal = canal_do_run(run_id)
    for payload in payloads:
        pipe.publish(canal, payload)


# ABSENT `duration_ms` is not the same as `None`. The server-side close
# (`publicar_conclusao`) does not measure duration and never published the key; the
# job_result and the inconclusive run always published it, null when there is no
# known start. Readers treat both forms the same (`?? null` in the panel),
# so each path keeps publishing what it used to publish.
_SEM_DURACAO = object()


def evento_de_conclusao(
    run_id: str,
    status: str,
    *,
    erro: str | None = None,
    extra: dict | None = None,
    duration_ms=_SEM_DURACAO,
    timestamp: float | None = None,
) -> str:
    """The `__workflow_complete__` JSON, ready for `anexar_eventos`.

    `status` is what the panel shows (`completed`, `failed`, `cancelled`); the
    level derives from it — `error` only on failure, because cancelling is not an error. `extra`
    carries the taxonomy of a failure. `timestamp` is now, unless the caller
    has already stamped the end somewhere else and needs the SAME instant.
    """
    evento = {
        "run_id":    run_id,
        "node":      WORKFLOW_COMPLETE_NODE,
        "kind":      "lifecycle",
        "level":     "error" if status == "failed" else "info",
        "status":    status,
        "timestamp": time.time() if timestamp is None else timestamp,
    }
    if duration_ms is not _SEM_DURACAO:
        evento["duration_ms"] = duration_ms
    evento["error"] = erro
    evento["extra"] = extra
    return json.dumps(evento)


class RunEventsUnavailable(Exception):
    """Redis did not answer the subscribe/LRANGE: there is no way to follow events.

    It is its own exception (and not the originating `RuntimeError`/`RedisError`) so
    that each consumer decides its fallback: the WS closes with 4500,
    `esperar_run` falls back to the database poll.
    """


@dataclass(frozen=True)
class Lote:
    """A batch of events as the consumer receives them.

    `eventos` are the RAW JSON strings from Redis, in publication order.
    `dropped` is how many events were discarded from the buffer since the previous
    batch (always sent, 0 included, so whoever sums does not have to check for `None`).
    `heartbeat=True` marks an empty batch emitted only because the channel went quiet.
    `completo=True` marks the LAST batch: the `__workflow_complete__` is in it
    (or in an earlier batch of the same replay) and the generator ends right after.
    """

    eventos: list[str]
    dropped: int
    heartbeat: bool
    completo: bool


def _is_droppable(raw: str) -> bool:
    return any(marker in raw for marker in _DROPPABLE_MARKERS)


def _is_complete_event(raw: str) -> bool:
    """True if the RAW is the `__workflow_complete__` event.

    The substring test is the fast path (it avoids a json.loads per event);
    the parse only runs on the candidate, because a user print() containing the
    marker string would truncate the replay of a run that is still running.
    """
    if WORKFLOW_COMPLETE_NODE not in raw:
        return False
    try:
        return json.loads(raw).get("node") == WORKFLOW_COMPLETE_NODE
    except (ValueError, AttributeError):
        return False


class _EventBuffer:
    """Queue between the producer (pub/sub) and the consumer (socket, tool).

    The producer never blocks: when it fills up, it discards the OLDEST stdout/debug
    and preserves the lifecycle — the lifecycle is what paints the canvas. The
    `__workflow_complete__` is never discarded.
    """

    def __init__(self, maxsize: int):
        self._items: deque[tuple[bool, str]] = deque()
        self._maxsize = maxsize
        self._ready = asyncio.Event()
        self._dropped = 0
        # Counted SEPARATELY from the telemetry discards: these are failures of
        # completely different severity, and adding them up hid the serious one inside the trivial.
        self._dropped_lifecycle = 0
        self.closed = False  # the producer has already seen __workflow_complete__

    def push(self, raw: str, *, droppable: bool) -> None:
        if len(self._items) >= self._maxsize:
            self._evict()
        self._items.append((droppable, raw))
        self._ready.set()

    def _evict(self) -> None:
        for index, (droppable, _) in enumerate(self._items):
            if droppable:
                del self._items[index]
                self._dropped += 1
                return
        # Queue full of lifecycle events: drops the oldest one that is not the
        # end marker. Losing one event is bad; stopping draining the pub/sub
        # makes Redis drop the subscriber and loses ALL the following ones.
        #
        # THIS is the only point in the server→consumer channel that still loses
        # graph state, and each occurrence leaves a node spinning forever on the
        # user's canvas. That is why it is counted separately and goes out as ERROR: if
        # it shows up in the log, it is proven that the queue between the pub/sub and the socket
        # must stop being the last line of defense (back-pressure with
        # replay).
        for index, (_, raw) in enumerate(self._items):
            if not _is_complete_event(raw):
                del self._items[index]
                self._dropped += 1
                self._dropped_lifecycle += 1
                return

    def take_dropped_lifecycle(self) -> int:
        perdidos, self._dropped_lifecycle = self._dropped_lifecycle, 0
        return perdidos

    def close(self) -> None:
        self.closed = True
        self._ready.set()

    def take_dropped(self) -> int:
        dropped, self._dropped = self._dropped, 0
        return dropped

    @property
    def empty(self) -> bool:
        return not self._items

    async def drain(self) -> list[str]:
        """Waits for an event (or the end of the run) and returns EVERYTHING accumulated.

        Aggregating before each delivery is the coalescing: a slow consumer ends up
        receiving fewer, larger batches, instead of stalling the Redis subscriber.
        """
        while not self._items and not self.closed:
            self._ready.clear()
            await self._ready.wait()
        events = [raw for _, raw in self._items]
        self._items.clear()
        return events


async def _ler_historico(run_id: str, history_key: str) -> tuple[list[str], bool]:
    """Snapshot of the history, cut at the 1st `__workflow_complete__`.

    Returns (historico, run_ja_terminou).

    ONE read. The publisher runs `rpush + ltrim(-5000,-1)` on every batch, so
    the list slides from the HEAD while the replay happens: paginating by absolute
    index (`lrange 0..499`, then `500..999`) made the events that
    slipped into the already-read page never be read by any page
    — and, since they predated the subscribe, the pub/sub did not
    redeliver them either. A `completed` lost this way leaves the node running on the canvas
    forever. `LRANGE 0..-1` is an atomic snapshot and immune to this; the gain of
    fewer batches still holds because DELIVERY PAGINATION continues.
    """
    rc = get_redis_pool()
    history = await rc.lrange(history_key, 0, -1)
    for index, raw in enumerate(history):
        if _is_complete_event(raw):
            # Cut at the marker: whatever comes after belongs to another cycle and must not
            # revive a finished run.
            return history[: index + 1], True
    return history, False


async def iter_run_events(
    run_id: str,
    *,
    timeout_s: float,
    heartbeat_s: float = _HEARTBEAT_S,
    chunk: int = _REPLAY_CHUNK,
) -> AsyncIterator[Lote]:
    """History replay and then the live stream, in `Lote`s.

    Mandatory order: SUBSCRIBE before LRANGE, so as not to lose what is
    published while the history is read; whatever lands in both sources is
    deduplicated by the replay's tail (see `pendentes`).

    Ends (1) at the end of the replay, if the history already contains the
    `__workflow_complete__` (last batch with `completo=True`); (2) at the
    live `__workflow_complete__` (likewise); (3) when `timeout_s` elapses, with no
    completion batch — it is the consumer that decides what a still-open run
    means. Raises `RunEventsUnavailable` if Redis fails on subscribe or
    on LRANGE; the subscriber's dedicated connection is closed on any exit.
    """
    channel = canal_do_run(run_id)
    history_key = chave_do_historico(run_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s

    # Dedicated connection for the subscribe (see `new_pubsub_client`): it is held for
    # the entire run, and coming from a capped pool is what made the Nth open
    # panel die with MaxConnectionsError.
    sub_client = new_pubsub_client()
    try:
        async with sub_client.pubsub() as pubsub:
            try:
                # Subscribes BEFORE reading the history so as not to lose events that
                # arrive while the replay happens.
                await pubsub.subscribe(channel)
                history, already_complete = await _ler_historico(run_id, history_key)
            except (RuntimeError, RedisError, OSError) as exc:
                # RuntimeError is `get_redis_pool()` with no pool (shutdown/rolling
                # deploy, lifespan that did not run); the other two are Redis
                # being down. For the consumer it is all the same thing: no
                # events.
                raise RunEventsUnavailable(
                    f"Redis indisponível para os eventos do run {run_id}: {exc}"
                ) from exc

            logger.info(
                "Eventos do run %s: replay history=%d eventos", run_id, len(history),
            )
            for start in range(0, len(history), chunk):
                ultimo = start + chunk >= len(history)
                yield Lote(
                    eventos=history[start:start + chunk],
                    dropped=0,
                    heartbeat=False,
                    completo=already_complete and ultimo,
                )
            if already_complete:
                return

            # Tail of the snapshot: everything published between SUBSCRIBE and LRANGE
            # also arrives via the pub/sub and the panel would show the same print()
            # line twice (the client reassigns `seq`, so it does not dedup
            # on its own). A counter (and not a set) so that N identical copies
            # within the window discard exactly N.
            pendentes: Counter | None = Counter(history[-_DEDUP_TAIL:]) if history else None

            # `aclosing`: the consumer may stop midway (the WS on seeing the tab
            # closed, `esperar_run` on the completion batch) and a `break` in an
            # `async for` does NOT finalize the generator — without this, the pub/sub
            # producer would only be cancelled when the garbage collector came by.
            async with aclosing(_stream_ao_vivo(
                pubsub, run_id, pendentes, deadline=deadline, heartbeat_s=heartbeat_s,
            )) as ao_vivo:
                async for lote in ao_vivo:
                    yield lote
            # The unsubscribe/reset is left to the pubsub's `async with` — calling it by
            # hand after a cancellation only risks talking on an already
            # dropped connection.
    finally:
        await sub_client.aclose()


async def _stream_ao_vivo(
    pubsub,
    run_id: str,
    pendentes: Counter | None,
    *,
    deadline: float,
    heartbeat_s: float,
) -> AsyncIterator[Lote]:
    """Live loop: pub/sub producer → queue → batches for the consumer.

    Duplicates at the replay↔live boundary (`pendentes`) are necessarily a
    PREFIX of the stream (the publisher writes to the history before publishing, in the
    same pipeline), so on the first message that does not match we turn off the dedup
    — that way a repeated print() mid-run, which is legitimate, is not swallowed.
    """
    buf = _EventBuffer(_QUEUE_MAXSIZE)
    loop = asyncio.get_running_loop()

    # `completo` is only true when `__workflow_complete__` has gone through the
    # buffer: the producer also closes the buffer when the pub/sub drops, and in that
    # case the generator ends WITHOUT marking completion — the run may be alive.
    viu_complete = False

    async def produce() -> None:
        nonlocal pendentes, viu_complete
        # The `finally` closes the buffer on ANY exit (end of run, error, Redis
        # dropping the subscriber). Without it, a failure here would leave the consumer
        # waiting forever for an event that is no longer coming.
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message["data"]
                if _is_complete_event(raw):
                    viu_complete = True
                    buf.push(raw, droppable=False)
                    return
                if pendentes is not None:
                    if pendentes.get(raw):
                        pendentes[raw] -= 1
                        continue
                    pendentes = None
                buf.push(raw, droppable=_is_droppable(raw))
        finally:
            buf.close()

    producer = asyncio.create_task(produce())
    try:
        while True:
            restante = deadline - loop.time()
            if restante <= 0:
                return
            try:
                events = await asyncio.wait_for(
                    buf.drain(), timeout=min(heartbeat_s, restante),
                )
            except asyncio.TimeoutError:
                if buf.closed and buf.empty:
                    return
                if deadline - loop.time() <= 0:
                    return
                # Channel quiet beyond the interval: delivers an EMPTY batch. The WS
                # sends it as is to keep traffic on the connection (Safari and
                # proxies drop idle WebSockets without notice) and, if the socket
                # has already died, the send itself fails and the handler ends — before,
                # with no write at all during a long node, not even the server
                # noticed the drop. `drain()` is safe to cancel: nothing was
                # consumed, and the next loop iteration restarts the wait.
                yield Lote(eventos=[], dropped=0, heartbeat=True, completo=False)
                continue
            if events:
                dropped = buf.take_dropped()
                perdidos_lifecycle = buf.take_dropped_lifecycle()
                if perdidos_lifecycle:
                    # ERROR, and separate from the telemetry warning: each of these is
                    # a node that will keep spinning forever on the canvas. The previous
                    # line said "stdout descartados" (stdout discarded) for both cases,
                    # which made the serious failure pass for log noise.
                    logger.error(
                        "Eventos do run %s: %d evento(s) de CICLO DE VIDA descartados "
                        "por saturação do buffer (%d slots) — o canvas do usuário vai "
                        "ficar com nó(s) sem conclusão. Consumidor não acompanha o "
                        "ritmo do run.",
                        run_id, perdidos_lifecycle, _QUEUE_MAXSIZE,
                    )
                if dropped > perdidos_lifecycle:
                    logger.warning(
                        "Eventos do run %s: %d evento(s) de stdout descartados — "
                        "consumidor nao acompanha o ritmo do run.",
                        run_id, dropped - perdidos_lifecycle,
                    )
                # The producer closes the buffer in the same step in which it pushes the
                # complete, so the batch that contains it already goes out marked.
                completo = viu_complete and buf.closed and buf.empty
                yield Lote(eventos=events, dropped=dropped, heartbeat=False, completo=completo)
            if buf.closed and buf.empty:
                return
    finally:
        # The producer does NOT take part in the wait: it ends on seeing the
        # `__workflow_complete__`, and the consumer drains the buffer to the end before
        # getting here — cancelling it earlier would swallow precisely the last
        # event, which decides the panel's final state.
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)
        if (
            producer.done()
            and not producer.cancelled()
            and producer.exception() is not None
        ):
            # A real pub/sub error has to propagate to the consumer, not vanish
            # inside the task.
            raise producer.exception()


# ── Waiting for the end of the run ────────────────────────────────────────────


async def ler_status_do_run(db, run_id: str) -> tuple[str | None, WorkflowRun | None]:
    """(status, row) of the run by `task_id` — `(None, None)` if it does not exist."""
    stmt = select(WorkflowRun).where(WorkflowRun.task_id == run_id).limit(1)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        return None, None
    return run.status, run


@dataclass
class ResultadoEspera:
    """What `esperar_run` returns.

    `status`/`run` are what the `workflow_runs` row said on the last read
    (they may be non-terminal on `timed_out`). `concluidos` are distinct nodes
    with `completed`/`failed` seen in the events; `eventos_descartados` sums the
    `dropped` of the batches. `redis_indisponivel=True` says only the poll worked.

    `concluidos` is NOT comparable with `total_nos` as "x of N finished": a node
    skipped by a branch (`run.node_stats[no]["status"] == "skipped"`) and a node that
    never got to run after a failure publish no event at all, so
    `concluidos < total_nos` at the end is the NORMAL case for a graph with branches.
    The real picture of who ran is in `run.node_stats`; `concluidos` serves
    for incremental progress, not for checking completeness.

    `viu_complete=True` says the `__workflow_complete__` went through the events,
    that is, the executor finished the graph. Combined with a NON-terminal `status`
    it means one thing only: the run is over, but the `workflow_runs` row
    had not been written even after the short poll of `_POLL_POS_COMPLETE_MAX_S`
    — `run_result_consumer` stalled or far behind. The caller should treat it
    as "finished, outcome still unknown" (and query again later), never
    as "still executing".
    """

    status: str | None
    run: WorkflowRun | None
    concluidos: int
    eventos_descartados: int
    timed_out: bool
    redis_indisponivel: bool
    viu_complete: bool = False


ProgressoCallback = Callable[[int, int, str], Awaitable[None]]


def _formatar_duracao(duration_ms) -> str | None:
    try:
        ms = float(duration_ms)
    except (TypeError, ValueError):
        return None
    if ms < 1000:
        return f"{int(ms)} ms"
    return f"{ms / 1000:.1f} s".replace(".", ",")


async def esperar_run(
    run_id: str,
    *,
    timeout_s: float,
    total_nos: int,
    on_progress: ProgressoCallback | None = None,
    poll_s: float = 2.0,
) -> ResultadoEspera:
    """Waits for the run to finish, with per-node progress and the database as the truth.

    Two tasks: A consumes `iter_run_events` (progress + fast ending via the
    `__workflow_complete__`); B polls `WorkflowRun.status` every
    `poll_s` in its own session. Whichever finishes first decides:

    - A saw the complete → cancels B and does a SHORT poll until the row becomes
      terminal (the consumer writes after publishing);
    - B saw a terminal status → cancels A. It is the only path for the endings that
      publish no event (cancel of a `pending` run, orphan dispatch, "all
      refused");
    - A died without complete (Redis down, subscriber dropped) → only B continues;
    - neither of them by `timeout_s` → `timed_out=True` with what the row says.

    `total_nos` is only the denominator of the progress delivered to `on_progress` (the
    number of nodes in the definition). Do not expect the numerator to reach it: a node
    skipped by a branch (`node_stats[no]["status"] == "skipped"`) and a node that never
    ran after a failure do NOT publish an event, so finishing with
    `concluidos < total_nos` is normal in a graph with branches — the real total of
    who ran comes from `run.node_stats`.

    A transient poll failure (pool checkout timed out, `SQLAlchemyError`,
    `OSError`) does not bring down the wait: up to
    `_POLL_FALHAS_CONSECUTIVAS_MAX` in a row are tolerated, with a warning; beyond that (or at
    the end of the deadline) the error propagates.

    `on_progress` runs inside the event consumption: if it raises, the exception
    is logged ONCE and the notifications stop, but the counting and the wait continue
    — a broken callback from the caller cannot cost the run's outcome.

    `ResultadoEspera.viu_complete` distinguishes the two "non-terminals": without
    complete the run may really be running; WITH complete and a non-terminal status
    the run is over and it is the row write that is late (see the docstring of
    `ResultadoEspera`).

    The wait's state and the two tasks live in `_Espera`; the order lives here.
    """
    espera = _Espera(
        run_id, timeout_s=timeout_s, total_nos=total_nos,
        on_progress=on_progress, poll_s=poll_s,
    )
    status, run = await espera.disputar()
    if espera.viu_complete and status not in _STATUS_TERMINAIS:
        # The consumer publishes the event and ONLY THEN writes the row: short poll so as
        # not to return "running" for a run that has just finished.
        status, run = await espera.poll_pos_complete(status, run)
    return espera.resultado(status, run)


class _Espera:
    """One call of `esperar_run`: what the two tasks share.

    Task A (`consumir_eventos`) counts the progress and sees the fast ending via the
    `__workflow_complete__`; B (`poll_ate_terminal`) reads `WorkflowRun.status`
    until terminal or the deadline. `disputar` races the two and keeps the outcome
    of whichever counts; `poll_pos_complete` and `resultado` close the wait.
    """

    def __init__(
        self,
        run_id: str,
        *,
        timeout_s: float,
        total_nos: int,
        on_progress: ProgressoCallback | None,
        poll_s: float,
    ):
        self.run_id = run_id
        self.total_nos = total_nos
        self.on_progress = on_progress
        self.poll_s = poll_s
        self.loop = asyncio.get_running_loop()
        self.deadline = self.loop.time() + timeout_s
        self.concluidos: set[str] = set()
        self.descartados = 0
        # Turned off on the first exception from the caller's callback (see `absorver_lote`).
        self.notificar = on_progress is not None
        # Last database read that ran to completion, even if the poll task was
        # cancelled right after (see `ler_status_inteiro`).
        self.ultima_leitura: tuple[str | None, WorkflowRun | None] | None = None
        self.redis_indisponivel = False
        self.viu_complete = False

    def restante(self) -> float:
        return self.deadline - self.loop.time()

    # ── A: eventos ────────────────────────────────────────────────────────────

    async def absorver_lote(self, lote: Lote) -> None:
        """Counts the nodes that finished and notifies the caller of each one.

        Only lifecycle counts: stdout/debug, invalid JSON, events without a node, the
        `__workflow_complete__` itself and statuses that are not endings are left out,
        and a node counts only once.
        """
        self.descartados += lote.dropped
        for raw in lote.eventos:
            # stdout/debug carry no lifecycle: they do not even deserve a parse.
            if _is_droppable(raw):
                continue
            try:
                ev = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(ev, dict) or ev.get("kind", "lifecycle") != "lifecycle":
                continue
            node, status = ev.get("node"), ev.get("status")
            if node == WORKFLOW_COMPLETE_NODE or not node:
                continue
            if status not in ("completed", "failed") or node in self.concluidos:
                continue
            self.concluidos.add(node)
            if self.notificar:
                msg = f"{node}: {status}"
                duracao = _formatar_duracao(ev.get("duration_ms"))
                if duracao:
                    msg = f"{msg} ({duracao})"
                try:
                    await self.on_progress(len(self.concluidos), self.total_nos, msg)
                except Exception as exc:
                    # The callback belongs to the CALLER (an MCP progress
                    # notification, a send on a socket that has already died): breaking here
                    # killed the event consumption, and with it the counting and the
                    # fast ending via `__workflow_complete__` — the whole wait
                    # came to depend on the poll. Warns once, stops
                    # notifying and keeps absorbing.
                    self.notificar = False
                    logger.warning(
                        "Progresso do run %s: callback falhou (%s); seguindo sem "
                        "notificar.", self.run_id, exc, exc_info=exc,
                    )

    async def consumir_eventos(self) -> bool:
        """True if the `__workflow_complete__` went through the events."""
        eventos = iter_run_events(self.run_id, timeout_s=max(self.restante(), 0.0))
        # `aclosing`: leaving the loop on the completion batch does not finalize the generator
        # on its own, and it is its `finally` that closes the subscriber's connection.
        async with aclosing(eventos):
            async for lote in eventos:
                await self.absorver_lote(lote)
                if lote.completo:
                    return True
        return False

    # ── B: database poll ──────────────────────────────────────────────────────

    async def ler_status(self) -> tuple[str | None, WorkflowRun | None]:
        async with get_session_async() as db:
            status, run = await ler_status_do_run(db, self.run_id)
            if run is not None:
                # `get_session_async` rolls back on exit, and the rollback EXPIRES
                # everything the session loaded: whoever read `run.node_stats` afterwards
                # would get DetachedInstanceError. Detached beforehand, the row keeps
                # the attributes already loaded and has no session to refresh.
                db.expunge(run)
            return status, run

    async def ler_status_inteiro(self) -> tuple[str | None, WorkflowRun | None]:
        """`ler_status` that a cancellation does not interrupt midway.

        The poll task is cancelled as soon as the events see the complete — and the
        cancellation lands wherever it is, including in the middle of a statement.
        A driver interrupted there leaves the connection in an undefined state
        (the pool invalidates it, at best). The `shield` lets the read in
        progress finish and close the session; the cancellation propagates right after.

        The read that survives the cancellation is KEPT in `ultima_leitura`:
        it cost a round-trip to the database and is, by definition, the most recent
        one there is. Discarding it only to open another session right away and
        ask the same thing doubled the latency of the most common path (the
        events see the complete while the poll is already reading).
        """
        leitura = asyncio.ensure_future(self.ler_status())
        try:
            self.ultima_leitura = await asyncio.shield(leitura)
            return self.ultima_leitura
        except asyncio.CancelledError:
            await asyncio.gather(leitura, return_exceptions=True)
            if leitura.done() and not leitura.cancelled() and leitura.exception() is None:
                self.ultima_leitura = leitura.result()
            raise

    async def poll_ate_terminal(self) -> tuple[str | None, WorkflowRun | None]:
        """Polls until a terminal status or the deadline; returns the last read.

        A database failure here is almost always transient (pool with no free connection
        at peak, recycled connection, network blip) and the event channel keeps
        delivering progress: bringing down the wait on the first of them traded a
        hiccup for an error. Tolerates up to `_POLL_FALHAS_CONSECUTIVAS_MAX` in a row
        — the counter resets on every good read — and only propagates on exceeding that
        ceiling or the deadline.
        """
        falhas = 0
        while True:
            try:
                status, run = await self.ler_status_inteiro()
            except _ERROS_POLL_TRANSITORIOS as exc:
                falhas += 1
                restante = self.restante()
                if falhas >= _POLL_FALHAS_CONSECUTIVAS_MAX or restante <= 0:
                    raise
                logger.warning(
                    "Poll do run %s falhou (%d/%d): %s",
                    self.run_id, falhas, _POLL_FALHAS_CONSECUTIVAS_MAX, exc,
                )
                await asyncio.sleep(min(self.poll_s, restante))
                continue
            falhas = 0
            if status in _STATUS_TERMINAIS:
                return status, run
            restante = self.restante()
            if restante <= 0:
                return status, run
            await asyncio.sleep(min(self.poll_s, restante))

    # ── A disputa e o fim ─────────────────────────────────────────────────────

    async def disputar(self) -> tuple[str | None, WorkflowRun | None]:
        """Races A and B and returns the `(status, linha)` (status, row) of whichever decides.

        Whichever finishes first cancels the other; A without complete (Redis down,
        subscriber dropped) lets B continue alone until terminal or the deadline.
        """
        tarefa_eventos = asyncio.create_task(self.consumir_eventos())
        tarefa_poll = asyncio.create_task(self.poll_ate_terminal())
        pendentes = {tarefa_eventos, tarefa_poll}
        try:
            while pendentes:
                done, pendentes = await asyncio.wait(pendentes, return_when=asyncio.FIRST_COMPLETED)
                if tarefa_eventos not in done:
                    # Only B finished (terminal status or deadline): the outcome is its.
                    break
                # A finished — alone or in the SAME step as B. Reading its result
                # here, BEFORE any `break`, is what guarantees an accurate
                # `viu_complete`: with both in the same `done`, exiting straight through the poll lost
                # the information that the graph had finished.
                self.anotar_fim_dos_eventos(tarefa_eventos)
                if self.viu_complete or tarefa_poll in done:
                    break
                # No complete: the poll continues alone until terminal or the deadline.
        finally:
            for tarefa in (tarefa_eventos, tarefa_poll):
                tarefa.cancel()
            await asyncio.gather(tarefa_eventos, tarefa_poll, return_exceptions=True)

        if tarefa_poll.done() and not tarefa_poll.cancelled():
            # `.result()` re-raises the poll's giving up (consecutive failures beyond
            # the ceiling): without a database there is no outcome to return.
            return tarefa_poll.result()
        if self.ultima_leitura is not None:
            # The poll was cancelled (the events saw the complete), but the read that
            # it had in progress ran to completion — it is the freshest there is. Opening
            # another session to ask the same thing cost an entire round-trip on the
            # MOST common path. If it is not terminal yet, the short poll
            # (`poll_pos_complete`) continues from where it left off.
            return self.ultima_leitura
        return await self.ler_status()

    def anotar_fim_dos_eventos(self, tarefa: asyncio.Task) -> None:
        """How A finished: with the complete, without Redis or with an error."""
        exc = tarefa.exception()
        if exc is None:
            self.viu_complete = tarefa.result()
        elif isinstance(exc, RunEventsUnavailable):
            self.redis_indisponivel = True
            logger.warning(
                "Eventos do run %s indisponíveis; seguindo só pelo poll: %s", self.run_id, exc,
            )
        else:
            # The poll is the source of truth; an error in the event channel cannot
            # bring down the whole wait.
            logger.error(
                "Erro ao acompanhar eventos do run %s; seguindo só pelo poll: %s",
                self.run_id, exc, exc_info=exc,
            )

    async def poll_pos_complete(
        self, status: str | None, run: WorkflowRun | None,
    ) -> tuple[str | None, WorkflowRun | None]:
        """Short poll, up to `_POLL_POS_COMPLETE_MAX_S`, for the terminal row.

        Going past the ceiling means the consumer is stalled: what the row says stands, and
        `viu_complete` tells the caller that the graph finished.
        """
        fim = self.loop.time() + _POLL_POS_COMPLETE_MAX_S
        falhas = 0
        while status not in _STATUS_TERMINAIS and self.loop.time() < fim:
            await asyncio.sleep(_POLL_POS_COMPLETE_S)
            try:
                status, run = await self.ler_status()
            except _ERROS_POLL_TRANSITORIOS as exc:
                # Same reasoning as the long poll, and here the bet is even
                # better: the graph has provably finished, only the row is missing.
                # Giving up over a database hiccup would throw away the only
                # information the wait already has.
                falhas += 1
                if falhas >= _POLL_FALHAS_CONSECUTIVAS_MAX:
                    raise
                logger.warning(
                    "Poll pós-complete do run %s falhou (%d/%d): %s",
                    self.run_id, falhas, _POLL_FALHAS_CONSECUTIVAS_MAX, exc,
                )
                continue
            falhas = 0
        return status, run

    def resultado(self, status: str | None, run: WorkflowRun | None) -> ResultadoEspera:
        return ResultadoEspera(
            status=status,
            run=run,
            concluidos=len(self.concluidos),
            eventos_descartados=self.descartados,
            timed_out=status not in _STATUS_TERMINAIS and self.loop.time() >= self.deadline,
            redis_indisponivel=self.redis_indisponivel,
            viu_complete=self.viu_complete,
        )


# ── Completion published by the server ───────────────────────────────────────

# Runs per pipeline. The block caps the command buffer when an incident
# closes hundreds of runs at once.
_BLOCO_DE_PUBLICACAO = 200


async def publicar_conclusao(
    run_ids: list[str], *, status: str, mensagem: str | None, extra: dict | None = None,
) -> None:
    """Publishes the `__workflow_complete__` of runs the SERVER closed.

    Whoever closes a run without going through the job_result — orphan, undelivered, lost
    in the reconciliation, cancelled before reaching the executor or with the executor
    down — did not publish the completion: the open panel kept spinning and the
    cancel button stayed on "aguardando o executor" (waiting for the executor) forever. The event is
    the same `evento_de_conclusao` as the job_result, without `duration_ms` (the server
    does not measure the duration of what it closes) and with ONE instant for the whole block.

    One pipeline per block instead of 4 round-trips PER RUN: when an executor
    with 50 runs drops, it was 200 trips to Redis in series and the open panels
    closed in a slow cascade, one by one.
    """
    if not run_ids:
        return
    rc = get_redis_pool()
    ts = time.time()
    for inicio in range(0, len(run_ids), _BLOCO_DE_PUBLICACAO):
        bloco = run_ids[inicio:inicio + _BLOCO_DE_PUBLICACAO]
        async with rc.pipeline(transaction=False) as pipe:
            for run_id in bloco:
                evento = evento_de_conclusao(
                    run_id, status, erro=mensagem, extra=extra, timestamp=ts,
                )
                anexar_eventos(pipe, run_id, [evento])
            await pipe.execute()
