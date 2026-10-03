# executor/sync/watcher.py
"""
FileWatcher — detecta mudancas em pastas de ingestao usando watchdog + polling.
"""
import logging
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from executor.sync.paths import TRASH_DIR_NAME
from executor.sync.scanner import SUPPORTED_EXTENSIONS

logger = logging.getLogger("executor.sync")


class _SyncEventHandler(FileSystemEventHandler):
    """Watchdog handler that forwards the relevant events to the FileWatcher.

    No per-path debounce: the minimum interval between cycles (SYNC_MIN_CYCLE)
    and the wait for stabilization live in the SyncManager, which is what can
    actually defer work. The `caminho -> timestamp` dict that used to live here
    was never pruned — every QGIS temp file left an entry forever, and the
    executor's RSS grew for no apparent reason — and it also DISCARDED the
    event instead of deferring it, delaying by up to 30s a write that finished
    within the window. The watcher's only job is to wake the cycle up.
    """

    def __init__(self, callback: Callable[[str, str], None], ignore_filter=None):
        self.callback = callback
        self._ignore = ignore_filter

    def _should_process(self, path: str) -> bool:
        p = Path(path)
        name = p.name
        if name.startswith(".") or name in {".atlans-sync.json", ".DS_Store", "Thumbs.db"}:
            return False
        # Moving a file to the trash produces an event with dest_path inside it.
        # Without this filter, discarding an obsolete copy would wake the sync — and
        # the scanner does not even see the trash, so it would be pure wasted work.
        if TRASH_DIR_NAME in p.parts:
            return False
        if self._ignore and self._ignore.should_ignore(p):
            return False
        return p.suffix.lower() in SUPPORTED_EXTENSIONS

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback("created", event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory and self._should_process(event.src_path):
            self.callback("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            if self._should_process(event.src_path):
                self.callback("deleted", event.src_path)
            if hasattr(event, "dest_path") and self._should_process(event.dest_path):
                self.callback("created", event.dest_path)


class FileWatcher:
    """Watches a folder with watchdog and fires callbacks for the SyncManager."""

    def __init__(self, sync_dir: str, on_change: Callable[[], None], ignore_filter=None):
        self.sync_dir = sync_dir
        self.on_change = on_change
        self._ignore = ignore_filter
        self._observer: Observer | None = None

    def _handle_event(self, action: str, path: str):
        # Reloads the filters if .atlans-ignore was modified
        if Path(path).name == ".atlans-ignore" and self._ignore:
            self._ignore.reload()
        logger.debug("Watcher: %s → %s", action, Path(path).name)
        # Wakes the SyncManager up. Without this call the whole watcher was
        # decorative — the filters and `_syncing` existed, but `on_change` was never
        # invoked and the sync only happened on the `interval` timeout (30s).
        # Runs on the watchdog THREAD: whoever receives the callback is the one
        # that has to marshal it onto the event loop.
        self.on_change()

    def start(self):
        handler = _SyncEventHandler(self._handle_event, ignore_filter=self._ignore)
        self._observer = Observer()
        self._observer.schedule(handler, self.sync_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("Watcher iniciado em '%s'.", self.sync_dir)

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            logger.info("Watcher encerrado.")
