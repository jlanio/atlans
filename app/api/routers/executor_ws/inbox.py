# app/api/routers/executor_ws/inbox.py
"""
Per-connection dispatch queue: enqueue with back-pressure, drain in
batches, rescue job_results on teardown.
"""
import asyncio
import time

from app.core.utils.logger import get_logger



logger = get_logger(__name__)

from .protocolo import _e_telemetria
from .resultados import (
    _fechar_run_inconclusivo,
    _handle_job_result,
    _handle_sync_event,
    _posse_ja_provada,
    _publish_node_events,
    _record_job_ack,
)
from .orfaos import _reconciliar_inventario

# ── Per-connection dispatch queue (see `_drenar_inbox`) ──────────────────────
# The receive loop used to process each message INLINE: the next
# `ws.receive_text()` only happened after Redis (and sometimes Postgres)
# answered. Heartbeat, capacity, ack and the final job_result got stuck behind
# the SAME executor's telemetry burst — the canvas received updates in choppy
# bursts, "concluído" (done) arrived seconds after the real end and, at high
# fan-out, the executor got close to the 90s timeout.
#
# Now the loop only does parse + schema + rate limit + enqueue; a draining
# task talks to Redis/Postgres. EVERYTHING goes on the SAME queue to preserve
# the relative order between a run's node_event and job_result.
#
# A full queue is NOT symmetric: telemetry is dropped; lifecycle and job_result
# wait for a slot (back-pressure) and, at the limit, are processed inline.
# See `_InboxQueue` and `_enfileirar_mensagem`.
_INBOX_MAXSIZE = 5000

# Maximum consecutive node_events merged into a single pipeline. There is no
# timer: the drainer only gathers what is ALREADY in the queue, so an isolated
# message goes out right away (zero latency) and the burst groups itself while
# Redis answers.
_INBOX_COALESCE_MAX = 64

# Ceiling on waiting for the drainer's flush on WS teardown. Without the flush,
# the run's last events (including __workflow_complete__) would be lost.
_INBOX_FLUSH_TIMEOUT = 10.0

# Minimum interval between two full-queue drop WARNINGs.
_INBOX_DROP_LOG_EVERY = 5.0

# Grace period given to the job_result already being written when the teardown
# gives up waiting for the drain. See `_drenar_inbox` and the handler's `finally`.
_INBOX_CANCEL_GRACE = 5.0

# Queue shutdown sentinel — see `_drenar_inbox`.
_INBOX_STOP = object()

# Ceiling on waiting for a slot when the queue fills up and the message must NOT
# be lost. It exists only so the receive loop does not get stuck forever if the
# drainer hangs: once the deadline runs out, the message is processed INLINE
# (slow, but lossless), never dropped. Well below the 90s _HEARTBEAT_TIMEOUT so
# the executor is not disconnected because of its own wait.
_INBOX_PUT_TIMEOUT = 30.0

class _InboxQueue(asyncio.Queue):
    """Connection queue with a SELECTIVE drop policy when it fills up.

    CONTRACT of what is NEVER dropped (state no client safety net rebuilds):

      * `job_result` — it is, by construction, the LAST message of a run, and the
        executor deletes the outbox row as soon as `send_text` returns.
        If lost, the WorkflowRun is stuck in 'running' forever (the executor's
        presence stays healthy, so neither `orphan_runs_watchdog` nor
        `_fail_orphan_runs_if_gone` reconcile; the webhook's BRPOP times out).
      * `sync_complete` — closes the GeoSync progress bar; losing it leaves the
        bar stuck at 99% (see `_SYNC_TERMINAL_EVENTS`).

    All the REST — telemetry (stdout/debug, progress sync_event) AND the
    lifecycle node_events — can be dropped under pressure. Losing a node's
    `completed` leaves the node 'started' during the run, but at the end
    `completeExecution` paints it as 'unknown' ("sem resposta", no response);
    and if the live channel dies, the client's watchdog reconnects and
    reconciles. It is honest degradation covered by the safety net — not worth
    the back-pressure cost here. (It used to be: Option B kept the lifecycle
    under back-pressure/inline, which fixed a symptom whose real cause was in
    the transport, now covered by heartbeat+watchdog.)
    """

    # IP of the connection that received this queue's messages (the route sets it
    # when creating it). The job_result carries THIS IP to run_results, not that
    # of whoever is in the registry when it is written: on a takeover the listener
    # removes the connection from the registry before the queue finishes emptying.
    ip_da_conexao: str | None = None

    def job_results_pendentes(self) -> list[tuple]:
        """job_results still queued, in order of arrival.

        Used on teardown to rescue what the cancelled drainer did not get to
        process — residual telemetry may vanish, results may not.
        """
        return [
            item for item in self._queue
            if isinstance(item, tuple) and item[0] == "job_result"
        ]

def _novo_contador_de_descartes() -> dict:
    """State of the aggregated per-connection drop WARNING."""
    return {"total": 0, "desde_log": 0, "ultimo_log": 0.0}

def _contabilizar_descarte(
    executor_id: str, descartes: dict, quantidade: int = 1,
) -> None:
    """Counts an event dropped because of a full queue, with an aggregated WARNING.

    One line per message would drown the log precisely in the incident in which
    it needs to be read. Covers stdout/debug, progress sync_event AND lifecycle
    node_event — a `completed` lost here shows up as "sem resposta" (no response)
    in the panel, not as an error.
    """
    descartes["total"] += quantidade
    descartes["desde_log"] += quantidade
    agora = time.monotonic()
    if (agora - descartes["ultimo_log"]) >= _INBOX_DROP_LOG_EVERY:
        logger.warning(
            "Executor '%s': fila de processamento cheia (%d) — %d evento(s) "
            "descartado(s) nos últimos %.0fs (%d nesta conexão). node_event perdido "
            "vira 'sem resposta' no painel.",
            executor_id, _INBOX_MAXSIZE, descartes["desde_log"],
            _INBOX_DROP_LOG_EVERY, descartes["total"],
        )
        descartes["desde_log"] = 0
        descartes["ultimo_log"] = agora

async def _enfileirar_mensagem(
    executor_id: str,
    inbox: "_InboxQueue",
    descartes: dict,
    msg_type: str,
    msg: dict,
    frame_bytes: int,
) -> None:
    """Enqueues for the drainer. Under a full queue, only job_result, ack and
    sync_complete escape being dropped.

    A full queue means the executor produces faster than Redis accepts.
    The response depends on what the message CARRIES:

      * node_event (stdout/debug AND lifecycle) and progress sync_event —
        DROPPED, with an aggregated WARNING. Losing a `completed` turns into an
        'unknown' node at the end of the run (completeExecution), and the client's
        watchdog recovers if the live channel dies: honest degradation, covered
        by the safety net.
      * job_result, ack and sync_complete — NEVER dropped. They carry state
        no safety net rebuilds (the run stuck in 'running' in Postgres; the
        delivered run stuck in 'pending'; the GeoSync bar at 99%).
        job_result and ack go INLINE right away; sync_complete waits for a slot
        and, at the limit, also goes inline.

    The `await` on the happy path does not suspend (put_nowait does not yield the
    loop), so the latency gain from enqueuing stays intact.
    """
    entrada = (msg_type, msg, frame_bytes)
    try:
        inbox.put_nowait(entrada)
        return
    except asyncio.QueueFull:
        pass

    # ── Full queue ────────────────────────────────────────────────────────────
    # node_event (any kind) and progress sync_event can be dropped: the loss
    # degrades honestly (node 'unknown', bar keeps going) and the client's
    # safety net covers it. Only job_result and sync_complete go ahead.
    # The inventory too: it is periodic, and the next one arrives in a minute.
    if msg_type in ("node_event", "inventario") or _e_telemetria(msg_type, msg):
        _contabilizar_descarte(executor_id, descartes)
        return

    # The ACK promotes the run from 'pending' to 'running'. If lost, a job the
    # executor received would stay "Na fila" (queued) until the sweep of
    # undelivered runs closes it as failed — with the executor running it. It is
    # a short UPDATE per job: inline, without waiting for a slot.
    if msg_type == "ack":
        try:
            await _record_job_ack(executor_id, msg.get("job_id"), msg.get("status") or "enqueued")
        except Exception as exc:
            logger.error(
                "Executor '%s': erro ao processar ACK inline do job '%s': %s",
                executor_id, msg.get("job_id"), exc,
            )
        return

    # job_result neither waits nor tries to open a slot: it is ONE message per run
    # and inline resolves it right away, losslessly. Blocking the receive loop
    # costs less than leaving the run hanging in 'running' forever.
    if msg_type == "job_result":
        logger.error(
            "Executor '%s': fila cheia — job_result do job '%s' processado INLINE "
            "(o loop de recepção vai bloquear).",
            executor_id, msg.get("job_id"),
        )
        try:
            await _handle_job_result(executor_id, msg, frame_bytes)
        except Exception as exc:
            logger.error(
                "Executor '%s': erro ao processar job_result inline do job '%s': %s",
                executor_id, msg.get("job_id"), exc,
            )
        return

    # What remains is sync_complete (GeoSync's terminal event). Losing it leaves
    # the bar stuck at 99% and no watchdog recovers it — so it WAITS for a slot
    # (back-pressure: the loop stops reading, TCP fills up, the executor slows
    # down on its own) and, once the deadline runs out, goes INLINE. It is the
    # only event that still pays the back-pressure cost here.
    try:
        await asyncio.wait_for(inbox.put(entrada), timeout=_INBOX_PUT_TIMEOUT)
        return
    except asyncio.TimeoutError:
        # A cancelled `asyncio.Queue.put` raises BEFORE the internal put_nowait,
        # so the item did not enter the queue and there is no risk of a duplicate here.
        pass

    logger.error(
        "Executor '%s': fila de processamento saturada por %.0fs — sync_event "
        "terminal processado INLINE. Investigar Redis/Postgres.",
        executor_id, _INBOX_PUT_TIMEOUT,
    )
    try:
        await _handle_sync_event(executor_id, msg)
    except Exception as exc:
        logger.error(
            "Executor '%s': erro ao processar sync_event inline: %s",
            executor_id, exc,
        )

async def _flush_node_events(executor_id: str, eventos: list[dict]) -> None:
    """Publishes the accumulated batch. Does not propagate: the drainer must not die."""
    if not eventos:
        return
    try:
        await _publish_node_events(executor_id, eventos)
    except Exception as exc:
        logger.error(
            "Executor '%s': falha ao drenar lote de %d node_event(s): %s",
            executor_id, len(eventos), exc,
        )

async def _processar_job_result_blindado(
    executor_id: str, msg: dict, frame_bytes: int, inflight: set | None,
    executor_ip: str | None = None,
) -> None:
    """Runs `_handle_job_result` in a task shielded against cancellation.

    WHY: writing the result is a NON-atomic sequence (setex of the result →
    lpush to `run_results`, which turns the WorkflowRun terminal in Postgres →
    webhook_response → publish of `__workflow_complete__`), with several Redis
    `await`s in between. A `cancel()` of the drainer landing between them leaves
    the run terminal in the database and the canvas WITHOUT the completion
    event — the panel spins forever on a run that has already finished. With
    `shield`, the cancellation reaches whoever waits, never whoever writes; the
    task goes on to the end and the teardown gives it a grace period before
    shutting down (see `_INBOX_CANCEL_GRACE`).
    """
    tarefa = asyncio.create_task(
        _handle_job_result(executor_id, msg, frame_bytes, executor_ip=executor_ip),
        name=f"job-result-{executor_id[:8]}",
    )
    # asyncio keeps only weakrefs to tasks — without a strong reference, a
    # shielded task can be garbage-collected in the middle of the write.
    if inflight is not None:
        inflight.add(tarefa)
        tarefa.add_done_callback(inflight.discard)
    await asyncio.shield(tarefa)

async def _drenar_inbox(
    executor_id: str, inbox: asyncio.Queue, inflight: set | None = None,
) -> None:
    """Consumes the connection's queue and does the heavy work (Redis/Postgres).

    Separating receiving from processing is what removes the head-of-line
    blocking: the receive loop never waits for I/O again, so heartbeat, capacity
    and ack no longer get stuck behind a telemetry burst.

    COALESCING WITHOUT A TIMER: each round takes what is ALREADY queued (up to
    `_INBOX_COALESCE_MAX`). In a burst the queue fills up while this task waits
    for Redis, and the next round takes dozens of events in a single pipeline;
    with low traffic, the isolated message goes out immediately. A fixed-window
    timer would do the opposite — it would delay precisely the single event,
    which is what the user sees.

    ORDER: everything comes from the SAME queue and a job_result/sync_event
    closes the accumulated batch of node_events before being processed, so the
    relative order within a run is the order of arrival.
    """
    try:
        while True:
            item = await inbox.get()
            lote = [item]
            while len(lote) < _INBOX_COALESCE_MAX:
                try:
                    lote.append(inbox.get_nowait())
                except asyncio.QueueEmpty:
                    break

            eventos: list[dict] = []
            for entrada in lote:
                if entrada is _INBOX_STOP:
                    await _flush_node_events(executor_id, eventos)
                    return
                msg_type, msg, frame_bytes = entrada
                if msg_type == "node_event":
                    eventos.append(msg)
                    continue
                await _flush_node_events(executor_id, eventos)
                eventos = []
                try:
                    if msg_type == "job_result":
                        await _processar_job_result_blindado(
                            executor_id, msg, frame_bytes, inflight,
                            executor_ip=getattr(inbox, "ip_da_conexao", None),
                        )
                    elif msg_type == "ack":
                        await _record_job_ack(
                            executor_id, msg.get("job_id"), msg.get("status") or "enqueued",
                        )
                    elif msg_type == "inventario":
                        await _reconciliar_inventario(executor_id, msg)
                    else:
                        await _handle_sync_event(executor_id, msg)
                except Exception as exc:
                    logger.error(
                        "Executor '%s': erro ao processar '%s': %s",
                        executor_id, msg_type, exc,
                    )
            await _flush_node_events(executor_id, eventos)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("Drenagem da conexão do executor '%s' abortada: %s", executor_id, exc)

async def _resgatar_job_results_pendentes(executor_id: str, inbox: "_InboxQueue") -> None:
    """Last chance for the job_results left in the cancelled queue.

    The teardown's `cancel()` stops the drainer with the queue still full.
    Residual telemetry may vanish; job_result may not — without it the
    WorkflowRun stays in 'running' forever. We try to write each one here and,
    if even that fails, we close the run as failed instead of leaving it hanging.
    """
    pendentes = inbox.job_results_pendentes()
    if not pendentes:
        return
    logger.warning(
        "Executor '%s': %d job_result(s) na fila após o cancelamento da drenagem — "
        "processando no teardown.", executor_id, len(pendentes),
    )
    for _tipo, msg, frame_bytes in pendentes:
        run_id = msg.get("run_id") or msg.get("job_id")
        try:
            await _handle_job_result(
                executor_id, msg, frame_bytes,
                executor_ip=getattr(inbox, "ip_da_conexao", None),
            )
        except Exception as exc:
            logger.error(
                "Executor '%s': job_result do job '%s' perdido no teardown: %s",
                executor_id, msg.get("job_id"), exc,
            )
            if run_id and _posse_ja_provada(executor_id, run_id):
                await _fechar_run_inconclusivo(
                    executor_id, run_id, f"teardown da conexão ({exc})",
                )

async def _encerrar_drenagem(inbox: asyncio.Queue, drain_task: asyncio.Task) -> None:
    """Enqueues the sentinel and waits for the drainer to finish what it already received.

    `put` (and not `put_nowait`) on purpose: if the queue is full at the moment
    of the drop, the sentinel waits for the slot the drainer itself opens — with
    `put_nowait` it would be dropped and the task would hang.
    """
    await inbox.put(_INBOX_STOP)
    await drain_task
