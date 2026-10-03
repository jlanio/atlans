# executor/job_queue.py
"""
Local job queue with concurrency control and back-pressure.

Architecture:
  - asyncio.PriorityQueue: buffer of jobs awaiting execution
  - asyncio.Semaphore: limits parallel flow/ executions
  - N worker coroutines: consume the queue and run jobs
  - Capacity reporting: informs the server of the queue's current state
"""
import asyncio
import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Any

from executor import config

logger = logging.getLogger(__name__)


# Tombstone of a job canceled BEFORE it reached this executor (see `add_tombstone`).
# The job may be in transit — dispatched by an API worker whose send has not
# gone out yet — and, if it arrives after the cancellation, it is discarded
# instead of running a run the server has already closed. Ten minutes comfortably
# cover the server's send deadline; the ceiling keeps a buggy server from filling
# memory.
_TOMBSTONE_TTL_S = 600.0
_TOMBSTONE_MAX = 1000


@dataclass(order=True)
class _QueueItem:
    """Priority queue item. Lower value = higher priority; among equal
    priorities, whoever arrived first (`seq`).

    Without `seq` ties had no order: the PriorityQueue heap is not stable,
    and since the server sends no priority, EVERY job ties at 5. With ten jobs
    in the queue, the second to arrive was the ninth to run.
    """
    priority:  int
    seq:       int
    message:   dict    = field(compare=False, default_factory=dict)


class ExecutorJobQueue:
    """
    Job queue with concurrency control for the executor.

    Usage:
        queue = ExecutorJobQueue(on_execute=executor_coroutine)
        await queue.start()          # starts workers in the background
        accepted = await queue.enqueue(job_message)
        capacity = queue.get_capacity()
        await queue.shutdown()       # stops accepting, waits for running jobs
    """

    def __init__(
        self,
        on_execute: Callable[[dict], Coroutine[Any, Any, dict]],
        max_concurrent: int = config.MAX_CONCURRENT,
        max_queue_size: int = config.MAX_QUEUE_SIZE,
        on_cancelled: Callable[[dict], Coroutine[Any, Any, None]] | None = None,
    ):
        self._on_execute   = on_execute
        # Called when a job is canceled — the one canceling is the server, and without
        # this notice the execution would simply vanish: the interrupted `on_execute`
        # never gets to produce a result, and the run would stay "running" forever.
        self._on_cancelled = on_cancelled
        # Called on the FIRST line of shutdown, so the server learns about the
        # draining without waiting for the capacity_loop's 10s tick. Injected after
        # construction (`set_on_draining`) because the connection only exists after
        # this queue — it receives the queue in its own constructor.
        self._on_draining: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._max_concurrent = max_concurrent
        self._max_queue    = max_queue_size

        self._queue        = asyncio.PriorityQueue(maxsize=max_queue_size)
        # Arrival order, the priority tiebreaker — see `_QueueItem`.
        self._seq          = itertools.count()
        self._semaphore    = asyncio.Semaphore(max_concurrent)
        self._running      = 0
        self._shutting_down = False
        self._workers: list[asyncio.Task] = []
        self._active_jobs: dict[str, dict] = {}  # job_id → message
        self._active_tasks: dict[str, asyncio.Task] = {}  # job_id → running task
        # Jobs canceled while still waiting in the queue. An item cannot be removed
        # from the middle of a PriorityQueue, so the worker discards it on pickup.
        self._cancelled: set[str] = set()
        # Jobs accepted and not yet finished (in the queue, stuck on the semaphore or
        # running). This is what lets `cancel()` answer "unknown" honestly
        # instead of marking any unknown id in `_cancelled` forever —
        # the set grew without bound and the UI said "cancelamento solicitado"
        # (cancellation requested) for a job that did not even exist on this instance.
        self._known: set[str] = set()
        # job_id → (monotonic) instant at which the tombstone expires. See `add_tombstone`.
        self._tombstones: dict[str, float] = {}
        # Signals "no job running". Replaces shutdown's 0.5s polling — the
        # `await` wakes up the instant the last job finishes.
        self._idle = asyncio.Event()
        self._idle.set()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, n_workers: int | None = None):
        """Starts N async workers consuming the queue."""
        n = n_workers or self._max_concurrent
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"executor-worker-{i}")
            for i in range(n)
        ]
        logger.info("ExecutorJobQueue iniciada com %d workers.", n)

    # Reason sent to the server for jobs that were in the queue and never got to
    # run. Distinct from a user-requested cancellation — it is what keeps the UI
    # from saying "cancelada pelo usuário" (canceled by the user) for something
    # nobody canceled.
    # WARNING: this asserts a LOCAL invariant (nothing was executed, no side
    # effect happened on this executor, so redispatching is safe). There is NO
    # automatic redispatch: the server records the run as terminal 'cancelled'
    # and nobody resends it. Implementing re-dispatch requires a server change
    # (executor_ws_router._handle_job_result) — do not assume it already exists.
    NAO_INICIADO = "Job não iniciado — executor encerrando."

    async def shutdown(self, timeout: int = 120):
        """
        Graceful shutdown:
          1. Stops accepting new jobs
          2. Tells the server RIGHT AWAY that we are draining
          3. Returns (as canceled) the jobs that were still waiting in the queue
          4. Waits for running jobs to finish (max timeout seconds)
          5. Cancels workers
        """
        self._shutting_down = True

        # Step 2 BEFORE draining the queue, and before any wait: from the line
        # above on `get_capacity()` announces saturation, but the sender is
        # `_capacity_loop`, which sleeps 10s BEFORE each send. In that window the
        # server's `_resolve_candidates` could still pick this executor as
        # least-loaded, and the job came back as "Executor em shutdown." — run
        # FAILED with no failover, which is exactly the problem the saturation
        # announcement exists to avoid. The immediate push closes the window.
        await self._notify_draining()

        await self._drain_queued()
        logger.info("ExecutorJobQueue: aguardando jobs em execução (%ds timeout)...", timeout)

        try:
            await asyncio.wait_for(self._wait_for_running(), timeout=timeout)
        except asyncio.TimeoutError:
            abandoned = list(self._active_jobs.keys())
            logger.warning(
                "ExecutorJobQueue: timeout no shutdown — %d job(s) abandonado(s): %s",
                len(abandoned),
                abandoned,
            )

        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

        # Jobs still active after the workers were canceled
        if self._active_jobs:
            logger.warning(
                "Executor encerrado com %d job(s) ainda em execução (serão marcados como falha pelo servidor): %s",
                len(self._active_jobs),
                list(self._active_jobs.keys()),
            )

        logger.info("ExecutorJobQueue encerrada.")

    async def _wait_for_running(self):
        await self._idle.wait()

    async def _drain_queued(self) -> None:
        """Empties the PriorityQueue, notifying each job that it will not run.

        `_wait_for_running` only sees `self._running`: the items still in the
        queue were invisible and nobody called `_notify_cancelled`. The server,
        which already marked the run as 'running' on dispatch, ended up closing
        everything as "Executor desconectou durante a execucao" (executor
        disconnected during execution) for jobs that never started.
        """
        pendentes: list[dict] = []
        while True:
            try:
                item: _QueueItem = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            # Balances the queue's internal counter — without this a future `join()`
            # would never complete.
            self._queue.task_done()
            pendentes.append(item.message)

        if not pendentes:
            return

        job_ids = [m.get("envelope", {}).get("job_id", "?") for m in pendentes]
        logger.warning(
            "ExecutorJobQueue: %d job(s) descartado(s) da fila no shutdown (nunca iniciaram): %s",
            len(job_ids), job_ids,
        )
        for message, job_id in zip(pendentes, job_ids):
            self._known.discard(job_id)
            self._cancelled.discard(job_id)
            await self._notify_cancelled(message, reason=self.NAO_INICIADO)

    # ── Enqueue ───────────────────────────────────────────────────────────────

    async def enqueue(self, message: dict) -> bool:
        """
        Puts a job in the queue.

        Returns False (back-pressure) if:
          - Shutdown in progress
          - Queue full (max_queue_size reached)
        """
        if self._shutting_down:
            return False

        envelope = message.get("envelope", {})
        priority = envelope.get("priority", 5)
        item = _QueueItem(priority=priority, seq=next(self._seq), message=message)

        try:
            self._queue.put_nowait(item)
            self._known.add(envelope.get("job_id", "?"))
            return True
        except asyncio.QueueFull:
            logger.warning(
                "Fila do executor cheia (%d/%d) — back-pressure ativado.",
                self._queue.qsize(), self._max_queue,
            )
            return False

    # ── Worker ────────────────────────────────────────────────────────────────

    async def _worker(self, worker_id: int):
        logger.debug("Worker %d iniciado.", worker_id)
        while not self._shutting_down:
            try:
                item: _QueueItem = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            job_id = item.message.get("envelope", {}).get("job_id", "?")

            # Shutdown started between the `get()` and now: `_drain_queued()` has already
            # run and this item escaped the draining. Notify instead of running —
            # otherwise the job would run with the executor shutting down and die midway.
            if self._shutting_down:
                await self._discard_cancelled(item.message, job_id, reason=self.NAO_INICIADO)
                break

            # Canceled while waiting in the queue — it never even runs.
            if self._take_cancelled(job_id):
                await self._discard_cancelled(item.message, job_id)
                continue

            async with self._semaphore:
                # Re-check AFTER the semaphore: with the executor saturated a job sits
                # here for quite a while, and a cancellation arriving in that
                # window was lost — `cancel()` found no active task, marked it
                # for discard, and the worker was already past the first
                # check. The job ran to the end while the UI said
                # "cancelamento solicitado" (cancellation requested).
                if self._take_cancelled(job_id):
                    await self._discard_cancelled(item.message, job_id)
                    continue

                self._running += 1
                self._idle.clear()
                self._active_jobs[job_id] = item.message
                # Runs in its own task so that `cancel()` has something to
                # cancel — with a direct `await self._on_execute(...)` there was no
                # handle and no way to interrupt a job in progress.
                task = asyncio.create_task(self._on_execute(item.message), name=f"job-{job_id}")
                self._active_tasks[job_id] = task
                try:
                    await task
                except asyncio.CancelledError:
                    if task.cancelled():
                        # Cancellation of THIS job (via cancel()). Does not propagate:
                        # the worker stays alive for the next queue item.
                        logger.info("Job '%s' cancelado durante a execução.", job_id)
                        await self._notify_cancelled(item.message)
                    else:
                        # What is being canceled is the WORKER (shutdown with
                        # timeout). Canceling an `await task` does NOT cancel the task:
                        # without this explicit cancel the job would keep running
                        # orphaned after shutdown — a regression compared to the
                        # direct `await self._on_execute(...)`, which died along with it.
                        task.cancel()
                        raise
                except Exception as exc:
                    logger.error("Worker %d: erro ao executar job '%s': %s", worker_id, job_id, exc)
                finally:
                    self._running -= 1
                    if self._running == 0:
                        self._idle.set()
                    self._active_jobs.pop(job_id, None)
                    self._active_tasks.pop(job_id, None)
                    self._cancelled.discard(job_id)
                    self._known.discard(job_id)
                    self._queue.task_done()

        logger.debug("Worker %d encerrado.", worker_id)

    def _take_cancelled(self, job_id: str) -> bool:
        """Consumes the job's cancellation mark, if there is one."""
        if job_id in self._cancelled:
            self._cancelled.discard(job_id)
            return True
        return False

    async def _discard_cancelled(self, message: dict, job_id: str, reason: str | None = None) -> None:
        """Discards a job canceled before starting and closes the queue item."""
        logger.info("Job '%s' descartado (%s).", job_id, reason or "cancelado antes de iniciar")
        self._known.discard(job_id)
        await self._notify_cancelled(message, reason=reason)
        self._queue.task_done()

    def set_on_draining(self, callback: Callable[[], Coroutine[Any, Any, None]] | None) -> None:
        """Registers whom to notify when draining starts (see `shutdown`)."""
        self._on_draining = callback

    async def _notify_draining(self) -> None:
        """Tells the outside world that we are draining. Never raises.

        Best-effort on purpose: if the WS is already down, the server finds out
        from the missing heartbeat anyway. Failing here cannot keep the shutdown
        from proceeding — the notice serves to save a misrouted job, it is not a
        prerequisite for shutting down.
        """
        if self._on_draining is None:
            return
        try:
            await self._on_draining()
        except Exception as exc:
            logger.warning("Falha ao anunciar drenagem ao servidor: %s", exc)

    async def _notify_cancelled(self, message: dict, reason: str | None = None) -> None:
        if self._on_cancelled is None:
            return
        if reason:
            # The reason travels inside the message itself because the callback's
            # signature is public (`on_cancelled(message)`) — changing it would break
            # every call site. Shallow copy: we do not touch the caller's dict.
            message = {**message, "cancel_reason": reason}
        try:
            await self._on_cancelled(message)
        except Exception as exc:
            logger.error("Falha ao notificar cancelamento do job: %s", exc)

    # ── Cancelamento ──────────────────────────────────────────────────────────

    def cancel(self, job_id: str) -> str:
        """Cancels a job that is running or still queued.

        Returns "running" (task interrupted), "queued" (known job, marked
        for discard when a worker picks it up) or "unknown" (not on this
        instance — nothing was marked).
        """
        task = self._active_tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
            logger.info("Cancelamento solicitado para job '%s' em execução.", job_id)
            return "running"

        # Not running. Only marks for discard if the job really belongs to
        # this instance: it may be in the queue or stuck on the semaphore (already
        # out of the queue, not yet a task). Marking unknown ids made `_cancelled`
        # grow forever and promised a cancellation that would never happen.
        if job_id in self._known:
            self._cancelled.add(job_id)
            logger.info("Job '%s' marcado para descarte na fila.", job_id)
            return "queued"

        logger.info("Cancelamento ignorado: job '%s' nao esta neste executor.", job_id)
        return "unknown"

    def active_job_ids(self) -> list[str]:
        """Jobs accepted and not yet finished: in the queue, stuck on the semaphore
        or running. It is the inventory the server checks — a run it thinks is
        here and is not in this list (nor has a pending result) has been
        lost."""
        return sorted(self._known)

    async def close_unknown(self, job_id: str, motivo: str) -> None:
        """Closes a job that is not here: tombstone + 'cancelled' result through
        the same path as normal cancellations (`on_cancelled`)."""
        self.add_tombstone(job_id)
        await self._notify_cancelled({"envelope": {"job_id": job_id}}, reason=motivo)

    def add_tombstone(self, job_id: str) -> None:
        """Marks a job that was canceled without being here. If it arrives later,
        `cancelled_before_arrival` discards it."""
        agora = time.monotonic()
        if len(self._tombstones) >= _TOMBSTONE_MAX:
            for jid in [j for j, vence in self._tombstones.items() if vence <= agora]:
                del self._tombstones[jid]
            while len(self._tombstones) >= _TOMBSTONE_MAX:
                # The dict keeps insertion order: the oldest tombstone goes first.
                del self._tombstones[next(iter(self._tombstones))]
        self._tombstones[job_id] = agora + _TOMBSTONE_TTL_S

    def cancelled_before_arrival(self, job_id: str) -> bool:
        """True if the job was canceled (and closed on the server) before arriving.
        Consumes the tombstone."""
        vence = self._tombstones.pop(job_id, None)
        return vence is not None and vence > time.monotonic()

    # ── Capacidade (para back-pressure e reporting) ───────────────────────────

    def get_capacity(self) -> dict:
        if self._shutting_down:
            # Draining: the WS stays alive for up to ~150s (jobs finishing +
            # results going up) and the executor REMAINS in the server's registry.
            # Reporting the real load here was a trap: `_drain_queued()`
            # empties the queue right away and the jobs keep finishing, so
            # queued/running PLUMMET to zero — and the old `_resolve_candidates`
            # (workflow_execution_service) sorted the pool by running+queued.
            # The dying executor became the least-loaded favorite and
            # every job routed to it came back as "Executor em shutdown."
            # (connection._handle_job), closing the run as FAILED with no failover.
            #
            # We announce saturation: queued = queue ceiling + concurrency ceiling.
            #   - full by declared load -> dispatch puts us LAST
            #     (`_sort_key`, the group of full ones);
            #   - queued+running >= max_concurrent+max_queue -> the server's
            #     `is_full()` (ExecutorConnection.is_full) returns True and `send_job`
            #     refuses, making dispatch fall through to the next candidate.
            # Works even with the server's clamp (`_sanitize_capacity` reduces
            # max_* to the database limits, never increases) — the clamped sum is
            # always <= the `queued` we declare.
            return {
                "queued":         self._max_queue + self._max_concurrent,
                "running":        self._running,
                "max_concurrent": self._max_concurrent,
                "max_queue":      self._max_queue,
            }
        return {
            "queued":        self._queue.qsize(),
            "running":       self._running,
            "max_concurrent": self._max_concurrent,
            "max_queue":     self._max_queue,
        }

    def is_full(self) -> bool:
        return self._queue.full()
