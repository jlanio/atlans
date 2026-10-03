# executor/event_publisher.py
"""
Workflow event publisher for the external executor.

Enqueues events in an asyncio.Queue to be sent to the server over WebSocket
as 'node_event' messages. The server then republishes them on
Redis pub/sub, connecting to the same pipeline used by Celery.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any

from flow.utils.publisher.events import (
    WorkflowEventPublisher, KIND_DEBUG, KIND_LIFECYCLE, KIND_STDOUT, LEVEL_INFO,
)

logger = logging.getLogger(__name__)

# Occupancy above which the queue accepts ONLY lifecycle events. The queue is
# shared by all jobs and by GeoSync: without priority, a noisy node (print in a
# loop, debug mode) filled the 500 slots and the victim of the drop was the
# `completed` of a node from ANOTHER workflow — telemetry the UI cannot recover.
_PRIORITY_THRESHOLD = 0.8
# Kinds that can be dropped under pressure: they are log, not graph state.
_DROPPABLE_KINDS = frozenset({KIND_STDOUT, KIND_DEBUG})


class LifecycleCollector:
    """Keeps the LAST lifecycle per (run_id, node) that could not be sent.

    It exists because of TWO scenarios, and the second is the more common:

      - reconnect window: on `ConnectionClosed` the sender stops, nobody drains
        the queue, the jobs keep producing and whatever arrives is dropped. Since
        the backoff reaches tens of seconds, the nodes that finished in that
        interval kept the "running" spinner forever — the user reads that as
        "the workflow is stuck", with the run alive and going fine;
      - PRESSURE with the WebSocket alive: a 300-node workflow in debug_mode
        produces faster than the sender sends, the 500-slot queue fills up and
        the `completed` of several nodes lands here. If the collector were only
        drained on reconnect (which may never happen), those nodes would keep
        spinning until the end of the run and the entries would stay held in
        memory. That is why the sender also drains as soon as the queue frees
        up — see `_ressincronizar_lifecycle`.

    Coalescing per node bounds memory to O(nodes) instead of O(events), and the
    stored events go back to the queue as normal node_events. Resending a
    `completed` the server has already seen is harmless (it orders by timestamp);
    not resending leaves the canvas wrong until the end of the run.
    """

    # Safety ceiling for the pathological case (WS down for a long time, thousands
    # of nodes): better to lose resync than to grow without bound.
    _MAX_ENTRADAS = 2_000

    def __init__(self) -> None:
        self._by_node: Dict[tuple, Dict[str, Any]] = {}
        self._warned_overflow = False

    def registrar(self, event: Dict[str, Any]) -> None:
        """Records a dropped event. Ignores everything that is not lifecycle."""
        if not isinstance(event, dict) or event.get("kind") != KIND_LIFECYCLE:
            return
        chave = (event.get("run_id"), event.get("node"))
        anterior = self._by_node.get(chave)
        if anterior is not None:
            # Last status wins — but only if it really is the most recent: the requeue
            # can return an old event after a new one has already gone through.
            if (anterior.get("timestamp") or 0.0) > (event.get("timestamp") or 0.0):
                return
        elif len(self._by_node) >= self._MAX_ENTRADAS:
            if not self._warned_overflow:
                self._warned_overflow = True
                logger.error(
                    "Buffer de ressincronizacao cheio (%d nos) — o canvas pode ficar "
                    "desatualizado para os nos que terminarem enquanto o WebSocket "
                    "estiver fora.", self._MAX_ENTRADAS,
                )
            return
        self._by_node[chave] = event

    def drenar(self) -> list:
        """Returns and forgets the accumulated snapshot.

        Called on (re)connect AND whenever the event queue frees up with the
        session alive — see `ExecutorConnection._ressincronizar_lifecycle`.
        """
        pendentes = list(self._by_node.values())
        self._by_node.clear()
        self._warned_overflow = False
        return pendentes

    def forget_run(self, run_id) -> None:
        """Discards the retained lifecycle of a run that has already finished.

        Without this, a late resend (reconnecting hours later) revived the
        per-run entries of the queue counters that `forget_run` had just
        purged — and nothing removed them again. Besides resending node_events
        of runs the server has already closed as terminal, which it rejects.
        """
        for chave in [k for k in self._by_node if k[0] == run_id]:
            del self._by_node[chave]

    def __len__(self) -> int:
        """Quantos eventos aguardam reenvio. Barato — o sender consulta a cada volta."""
        return len(self._by_node)


class ExecutorEventPublisher(WorkflowEventPublisher):
    """
    WorkflowEventPublisher implementation for the external executor.
    Puts events in an asyncio.Queue — best-effort (drops if the queue is full).

    Thread-safe: can be called from secondary threads (asyncio.to_thread)
    via call_soon_threadsafe, which schedules the enqueue on the main event loop.
    """

    def __init__(self, event_queue: asyncio.Queue):
        self._queue = event_queue
        # Captures the main event loop at the moment the publisher is created
        self._loop = asyncio.get_running_loop()
        self._dropped_under_pressure = 0

    def _safe_enqueue(self, event: Dict[str, Any]) -> None:
        """Enqueues the event, giving priority to the lifecycle.

        Two rules, in order: (1) above _PRIORITY_THRESHOLD occupancy, only
        lifecycle gets in — a noisy node's stdout/debug cannot cost another
        job's `completed`; (2) if the queue is still full, the dropped
        lifecycle goes to the collector, which resends it on reconnect.
        """
        if self._is_droppable_under_pressure(event):
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._record_drop(event)
            logger.warning(
                "Fila de eventos cheia — evento '%s' do nó '%s' (run=%s) descartado.",
                event.get("status"), event.get("node"), event.get("run_id"),
            )

    def _is_droppable_under_pressure(self, event: Dict[str, Any]) -> bool:
        """True when the event is log and the queue is already close to the limit."""
        if event.get("kind") not in _DROPPABLE_KINDS:
            return False
        maxsize = getattr(self._queue, "maxsize", 0) or 0
        if not maxsize or self._queue.qsize() < maxsize * _PRIORITY_THRESHOLD:
            return False
        self._dropped_under_pressure += 1
        if self._dropped_under_pressure % 500 == 1:
            logger.warning(
                "Fila de eventos a %d%% — descartando '%s' do nó '%s' para preservar "
                "o ciclo de vida dos jobs (%d descartado(s) até agora).",
                int(_PRIORITY_THRESHOLD * 100), event.get("kind"), event.get("node"),
                self._dropped_under_pressure,
            )
        return True

    def _record_drop(self, event: Dict[str, Any]) -> None:
        """Hands the lost event to the queue's collector, when there is one."""
        coletor = getattr(self._queue, "coletor", None)
        if coletor is not None:
            coletor.registrar(event)

    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Optional[float] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        event: Dict[str, Any] = {
            "run_id": run_id,
            "node": node,
            "kind": kind,
            "level": level,
            "status": status,
            "timestamp": time.time() if timestamp is None else timestamp,
        }
        if duration_ms is not None:
            event["duration_ms"] = duration_ms
        if error is not None:
            event["error"] = error
        if extra is not None:
            event["extra"] = extra

        # call_soon_threadsafe is safe from any thread and also from the event loop
        # itself — schedules _safe_enqueue on the main loop without blocking.
        try:
            self._loop.call_soon_threadsafe(self._safe_enqueue, event)
        except RuntimeError:
            # Loop already closed (shutdown) — drops the event
            logger.debug("Evento descartado (loop encerrado): nó '%s'", event.get("node_id", "?"))
