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
    """Handler do watchdog que repassa ao FileWatcher os eventos relevantes.

    Sem debounce por caminho: o piso de intervalo entre ciclos (SYNC_MIN_CYCLE)
    e a espera por estabilizacao vivem no SyncManager, que e quem tem como
    adiar trabalho de verdade. O dict `caminho -> timestamp` que existia aqui
    nunca era podado — cada temporario do QGIS deixava uma entrada para sempre,
    e o RSS do executor crescia sem causa aparente — e ainda DESCARTAVA o
    evento em vez de adia-lo, atrasando ate 30s uma gravacao que terminasse
    dentro da janela. O unico papel do watcher e acordar o ciclo.
    """

    def __init__(self, callback: Callable[[str, str], None], ignore_filter=None):
        self.callback = callback
        self._ignore = ignore_filter

    def _should_process(self, path: str) -> bool:
        p = Path(path)
        name = p.name
        if name.startswith(".") or name in {".atlans-sync.json", ".DS_Store", "Thumbs.db"}:
            return False
        # Mover um arquivo para a lixeira gera um evento com dest_path la dentro.
        # Sem este filtro, descartar uma copia obsoleta acordaria o sync — e o
        # scanner nem enxerga a lixeira, entao seria trabalho puro em vao.
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
    """Monitora uma pasta com watchdog e dispara callbacks para o SyncManager."""

    def __init__(self, sync_dir: str, on_change: Callable[[], None], ignore_filter=None):
        self.sync_dir = sync_dir
        self.on_change = on_change
        self._ignore = ignore_filter
        self._observer: Observer | None = None

    def _handle_event(self, action: str, path: str):
        # Recarrega filtros se o .atlans-ignore foi modificado
        if Path(path).name == ".atlans-ignore" and self._ignore:
            self._ignore.reload()
        logger.debug("Watcher: %s → %s", action, Path(path).name)
        # Acorda o SyncManager. Sem esta chamada o watcher inteiro era
        # decorativo — os filtros e o `_syncing` existiam, mas `on_change` nunca
        # era invocado e o sync so acontecia no timeout de `interval` (30s).
        # Roda na THREAD do watchdog: quem recebe o callback e que precisa
        # marshalar para o event loop.
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
