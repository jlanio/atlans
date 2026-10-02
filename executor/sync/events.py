# executor/sync/events.py
"""
SyncEventEmitter — emite eventos de sync via asyncio.Queue para envio pelo WebSocket.
Reutiliza a mesma fila de eventos do ExecutorEventPublisher.
"""
import asyncio
import logging
import time

logger = logging.getLogger("executor.sync")


class SyncEventEmitter:
    """Emite eventos de sync para o servidor via WebSocket (best-effort)."""

    def __init__(self, event_queue: asyncio.Queue | None = None):
        self._queue = event_queue
        self._loop: asyncio.AbstractEventLoop | None = None
        if event_queue is not None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass  # Sem event loop rodando — emissão de eventos será síncrona

    def emit(
        self,
        event: str,
        dataset: str = "",
        progress: float = 0,
        error: str = "",
        **kwargs,
    ):
        """
        Emite evento de sync. Thread-safe.

        Eventos suportados:
          sync_started, file_uploading, file_uploaded,
          file_downloading, file_downloaded,
          sync_complete, sync_error, conflict_detected
        """
        if self._queue is None:
            return

        payload = {
            "type": "sync_event",
            "event": event,
            "dataset": dataset,
            "progress": round(progress, 3),
            "timestamp": time.time(),
        }
        if error:
            payload["error"] = error
        if kwargs:
            payload.update(kwargs)

        try:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._enqueue, payload)
            else:
                self._enqueue(payload)
        except Exception as exc:
            logger.debug("Falha ao emitir evento de sync '%s': %s", event, exc)

    def _enqueue(self, payload: dict):
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.debug("Fila de eventos cheia — sync_event '%s' descartado.", payload.get("event"))
