# executor/sync/manager.py
"""
SyncManager — orquestrador principal do GeoSync.
Coordena watcher, scanner, validator, uploader e manifesto.
"""
import asyncio
import logging
import time
import weakref
from pathlib import Path

from flow.utils.backoff import espera_exponencial

from executor.sync.manifest import SyncManifest
from executor.sync.pool import em_thread
from executor.sync.scanner import DatasetScanner, Dataset, SUPPORTED_EXTENSIONS
from executor.sync.validator import validate_dataset
from executor.sync.metadata import extract_metadata
from executor.sync.uploader import DriveUploader, UploadResult
from executor.sync.watcher import FileWatcher
from executor.sync.queue import SyncQueue
from executor.sync.ignore import IgnoreFilter
from executor.sync.paths import (
    TRASH_DIR_NAME,
    TRASH_RETENTION_DAYS,
    TRASH_WARN_BYTES,
    move_dataset_to_trash,
    purge_trash,
    safe_join_or_none,
)
from executor.sync.events import SyncEventEmitter
from executor.sync.downloader import DriveDownloader
from executor.sync.trigger import SyncTrigger
from executor.sync.sync_config import (
    SYNC_CONCURRENCY,
    SYNC_FLUSH_INTERVAL,
    SYNC_FULL_HASH_INTERVAL,
    SYNC_MAX_QUIET_WAIT,
    SYNC_MIN_CYCLE,
    SYNC_QUIET_PERIOD,
    SyncConfig,
)
from executor import config as agent_config

logger = logging.getLogger("executor.sync")

# Backoff ceiling applied when a whole sync cycle fails.
_MAX_CYCLE_BACKOFF = 300

# Ceiling on simultaneous transfers for the PROCESS, not for each folder. The
# reason for the ceiling is the LINK (on a field connection, high concurrency
# worsens the total time and risks blowing the 300s PUT/GET timeout) and there
# is only one link: with one semaphore per manager, three configured folders
# became 3xSYNC_CONCURRENCY transfers competing for the same bandwidth and the
# threads that feed them.
#
# It is keyed by event loop because a module-level `asyncio.Semaphore` binds to
# the first loop that awaits it — which would break any process (or test) that
# runs more than one loop in its lifetime.
_semaforos_de_transferencia: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _semaforo_de_transferencia() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    semaforo = _semaforos_de_transferencia.get(loop)
    if semaforo is None:
        semaforo = asyncio.Semaphore(SYNC_CONCURRENCY)
        _semaforos_de_transferencia[loop] = semaforo
    return semaforo

# Interval between trash purges. The cycle runs every `interval` (30s by
# default); sweeping the trash at that pace would be pure wasted I/O.
_TRASH_PURGE_INTERVAL = 6 * 3600


class SyncManager:
    """
    Manages the synchronization of a local folder with the Workspace Drive.
    Supports the modes: upload, download, bidirectional.
    """

    def __init__(
        self,
        sync_dir: str,
        workspace_id: str,
        server_url: str,
        executor_id: str,
        interval: int = 30,
        event_queue: asyncio.Queue | None = None,
        drive_event_queue: asyncio.Queue | None = None,
    ):
        self.sync_dir = Path(sync_dir)
        self.workspace_id = workspace_id
        self.interval = interval

        # Creates the folder if it doesn't exist
        self.sync_dir.mkdir(parents=True, exist_ok=True)

        # Componentes — autenticacao via mTLS (cert + chave do EXECUTOR_CERT_DIR).
        self.ignore = IgnoreFilter(sync_dir)
        self.events = SyncEventEmitter(event_queue)
        self.manifest = SyncManifest(sync_dir, workspace_id, executor_id)
        self.scanner = DatasetScanner(sync_dir, ignore_filter=self.ignore)
        self.uploader = DriveUploader(server_url, executor_id, workspace_id, sync_dir)
        self.watcher = FileWatcher(sync_dir, self._on_change, ignore_filter=self.ignore)
        self.downloader = DriveDownloader(server_url, executor_id, workspace_id)
        self.trigger = SyncTrigger(server_url, executor_id)
        self.sync_config = SyncConfig(sync_dir)
        self.queue = SyncQueue(self.manifest, self._execute_pending)
        self.sync_mode = agent_config.SYNC_MODE  # upload | download | bidirectional

        self._change_flag = asyncio.Event()
        self._drive_events = drive_event_queue  # Queue of push events from the server
        self._drive_task: asyncio.Task | None = None
        self._syncing = False  # Flag to ignore watcher events during sync
        self._last_trash_purge = 0.0
        # Cycle pacing: `_ultimo_ciclo` sustains the floor between sweeps
        # triggered by the watcher and `_forcar_ciclo` is the UI command's bypass.
        self._ultimo_ciclo = 0.0
        self._forcar_ciclo = False
        # None = there has been no hashed sweep yet in this execution. 0.0 doesn't
        # work as "never": `time.monotonic()` is the machine's uptime, and on a
        # laptop switched on 5 minutes ago the math would say "a short while ago".
        self._ultimo_hash_completo: float | None = None
        # Scan shared by the items of ONE pass over the retry queue.
        self._scan_da_fila: dict[str, Dataset] | None = None
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None  # construido fora do loop — run() preenche

    def sincronizar_agora(self) -> bool:
        """Wakes the cycle without waiting for the interval. Returns whether it succeeded.

        The loop sleeps on `_change_flag` with an `interval` timeout — the same
        mechanism the watcher uses to signal a local change. A command coming
        from the UI is just another way of knocking on that door.

        Difference: `_forcar_ciclo` bypasses the interval floor and the wait
        for stabilization. The floor exists to contain the watchdog burst during
        a copy; a user click is an explicit intent and cannot wait.
        """
        loop = self._loop
        if loop is None:
            self._forcar_ciclo = True
            self._change_flag.set()
            return True
        try:
            loop.call_soon_threadsafe(self._acordar_forcado)
            return True
        except RuntimeError:
            return False  # loop already closed

    def _acordar_forcado(self):
        self._forcar_ciclo = True
        self._change_flag.set()

    def _emitir_inventario(self) -> None:
        """Publishes how many datasets there are, how many are up to date and how many are queued.

        Goes out as a sync event, and not as a direct read of the manifest by
        stats: the manifest belongs to another logical process (the sync task)
        and reads/writes disk — querying it at 1 Hz from the metrics collector
        would put I/O on the snapshot's path. Emitting at the end of the cycle
        costs nothing and the data only changes when the cycle runs.

        Best-effort: a failing inventory must not bring down the sync.
        """
        try:
            datasets = self.manifest.all_datasets()
            pendentes = len(self.manifest.pending_items())
            sincronizados = sum(
                1 for d in datasets.values() if d.get("status") == "synced"
            )
            self.events.emit(
                "sync_inventory",
                dataset="",
                total=len(datasets),
                synced=sincronizados,
                pending=pendentes,
            )
        except Exception:
            logger.debug("Inventario de sync de '%s' falhou.", self.sync_dir, exc_info=True)

    def _on_change(self):
        """
        Watcher callback — signals that there was a change (ignored during sync).

        Runs on the watchdog's THREAD, never on the event loop:
        `asyncio.Event.set()` schedules the waiters' callbacks with
        `loop.call_soon`, which is not thread-safe (it touches the ready queue
        without waking the selector). We marshal with `call_soon_threadsafe`;
        with no loop (synchronous use in tests) we set it directly.
        """
        if self._syncing:
            return
        loop = self._loop
        if loop is None:
            self._change_flag.set()
            return
        try:
            loop.call_soon_threadsafe(self._change_flag.set)
        except RuntimeError:
            pass  # loop already closed (shutdown) — there is no cycle to wake

    # ── Drive event fan-out ──────────────────────────────────────────────────

    def claims_event(self, msg: dict) -> bool:
        """
        Says whether THIS manager owns a drive_event.

        With several sync folders, main.py delivers each push event to a single
        manager. This predicate is the piece that decides which one: True when
        the event's file is already known to this folder (same remote id, same
        remote object, same local file name, or same dataset name).

        Contract: synchronous, cheap (three O(1) lookups in the manifest's
        indexes) and NEVER raises — when in doubt it returns False and the
        fan-out delivers to the primary.
        """
        try:
            file_info = msg.get("file") or {}
            id_hash = file_info.get("id_hash") or ""
            original_name = file_info.get("original_name") or ""
            if not id_hash and not original_name:
                return False

            if self._find_dataset(id_hash, original_name):
                return True

            if original_name:
                # Name not yet synced but that matches a dataset in this
                # folder (e.g. 'parcelas.geojson' and the dataset 'parcelas').
                stem = original_name.rsplit(".", 1)[0].lower()
                if stem in self.manifest.all_datasets():
                    return True
            return False
        except Exception:  # noqa: BLE001 — a routing predicate must never break the fan-out
            return False

    def _find_dataset(self, id_hash: str = "", original_name: str = "") -> str | None:
        """Delegates to the manifest's inverted indexes (see SyncManifest.find)."""
        return self.manifest.find(id_hash, original_name)

    async def run(self):
        """Main sync loop."""
        logger.info("GeoSync iniciado: pasta='%s' workspace='%s' modo='%s' intervalo=%ds",
                    self.sync_dir, self.workspace_id, self.sync_mode, self.interval)

        # The watcher delivers events from another thread — `_on_change` needs to know
        # which loop to marshal to.
        self._loop = asyncio.get_running_loop()
        self.watcher.start()

        try:
            # Initial reconciliation (the only call to list_remote). A failure here
            # (Drive down, disk with a file in transit) must not prevent the
            # periodic loop from starting.
            try:
                await self._full_sync()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error("Reconciliacao inicial de '%s' falhou — seguindo para o loop periodico.",
                             self.sync_dir, exc_info=True)

            # Dedicated task for drive events (runs in parallel with the loop).
            # We keep the reference: without it the GC may collect the task.
            if self._drive_events:
                self._drive_task = asyncio.create_task(self._drive_event_loop(), name="drive-event-loop")

            # A cycle dying from an exception silently killed the folder's sync
            # until the process restarted — a FileNotFoundError from a QGIS temp
            # file was enough. The cycle is now isolated and the error is visible.
            consecutive_errors = 0
            while True:
                try:
                    await self._maybe_purge_trash()

                    # Processes the pending queue (retry). The scan is shared by
                    # all the items in the pass: before, each `upload` item
                    # scanned the ENTIRE folder to find a single dataset.
                    self._scan_da_fila = None
                    try:
                        await self.queue.process_pending()
                    finally:
                        self._scan_da_fila = None
                    await self.manifest.flush()

                    # Before sleeping: the manifest state is now what the UI
                    # should show until the next cycle.
                    self._emitir_inventario()

                    # Waits for a local change or timeout
                    acordou_por_evento = False
                    try:
                        await asyncio.wait_for(self._change_flag.wait(), timeout=self.interval)
                        self._change_flag.clear()
                        acordou_por_evento = True
                    except asyncio.TimeoutError:
                        pass

                    if acordou_por_evento:
                        await self._esperar_pasta_estabilizar()
                    self._forcar_ciclo = False

                    # Sync local → remoto
                    if self.sync_mode in ("upload", "bidirectional", "catalog"):
                        await self._local_to_remote_only()

                    consecutive_errors = 0
                except asyncio.CancelledError:
                    raise
                except Exception:
                    consecutive_errors += 1
                    backoff = espera_exponencial(consecutive_errors, teto=_MAX_CYCLE_BACKOFF)
                    logger.error(
                        "Ciclo de sync de '%s' falhou (%d consecutiva(s)) — nova tentativa em %.1fs.",
                        self.sync_dir, consecutive_errors, backoff, exc_info=True,
                    )
                    await asyncio.sleep(backoff)

        except asyncio.CancelledError:
            logger.info("GeoSync encerrado.")
        finally:
            if self._drive_task:
                self._drive_task.cancel()
            self.watcher.stop()
            await self._fechar_clientes()

    async def _fechar_clientes(self):
        """Closes the long-lived httpx clients.

        They live as long as the manager lives (keep-alive is the point).
        Without an explicit close at shutdown, the sockets leak until the
        process dies — and on desktop the executor is restarted without
        restarting Electron.
        """
        for componente in (self.uploader, self.downloader, self.trigger):
            fechar = getattr(componente, "aclose", None)
            if fechar is None:
                continue
            try:
                await fechar()
            except Exception:
                logger.debug("Falha ao fechar cliente HTTP de %s.", type(componente).__name__,
                             exc_info=True)

    async def _esperar_pasta_estabilizar(self):
        """
        Holds the cycle until the folder stops changing.

        Without this, copying a large file into the folder made the executor
        scan+hash everything every ~2 seconds, in back-to-back cycles: the copy
        competed for I/O with the scan and the machine froze. Two barriers,
        both only for cycles woken by the WATCHER:

          * a floor of `SYNC_MIN_CYCLE` between the end of one cycle and the
            start of the next;
          * CYCLE debounce (not per path): only releases when no new event has
            arrived for `SYNC_QUIET_PERIOD`, with a ceiling of
            `SYNC_MAX_QUIET_WAIT` so an hours-long copy doesn't postpone the
            sync forever.

        `sincronizar_agora()` bypasses both — it is a user command.
        """
        loop = asyncio.get_running_loop()
        limite = loop.time() + SYNC_MAX_QUIET_WAIT
        piso = self._ultimo_ciclo + SYNC_MIN_CYCLE

        while not self._forcar_ciclo:
            agora = loop.time()
            if agora >= limite:
                return
            espera = min(max(piso - agora, SYNC_QUIET_PERIOD), limite - agora)
            if espera <= 0:
                return
            self._change_flag.clear()
            try:
                await asyncio.wait_for(self._change_flag.wait(), timeout=espera)
            except asyncio.TimeoutError:
                if loop.time() >= piso:
                    return  # floor met and no new event in the window

    async def _maybe_purge_trash(self):
        """
        Purges old discards from the trash, at most once every 6h.

        The trash lives inside sync_dir (so the move is a rename on the same
        volume) and therefore eats into the field laptop's quota, with nothing
        showing it to the technician: a dot folder, ignored by scanner and
        watcher. In a bidirectional folder with normal turnover — a daily
        raster replaced in Drive — that's tens of GB in a few weeks, and the
        only symptom would be the manifest no longer saving.
        """
        agora = time.monotonic()
        if self._last_trash_purge and agora - self._last_trash_purge < _TRASH_PURGE_INTERVAL:
            return
        self._last_trash_purge = agora

        removidos, restantes = await em_thread(purge_trash, self.sync_dir)
        if removidos:
            logger.info("Lixeira de '%s': %d descarte(s) com mais de %d dias removido(s).",
                        self.sync_dir, removidos, TRASH_RETENTION_DAYS)
        if restantes > TRASH_WARN_BYTES:
            logger.warning("Lixeira de '%s' ocupa %s — pasta oculta, o tecnico nao a enxerga.",
                           self.sync_dir, _format_size(restantes))
            self.events.emit("sync_error", dataset=TRASH_DIR_NAME,
                             error=f"Lixeira do sync ocupando {_format_size(restantes)}")

    async def _drive_event_loop(self):
        """Dedicated loop to process push drive events from the server."""
        logger.info("Drive event loop iniciado.")
        while True:
            try:
                event = await self._drive_events.get()
                await self._process_drive_event(event)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Erro ao processar drive_event em '%s'.", self.sync_dir, exc_info=True)

    async def _process_drive_event(self, event: dict):
        """Processa um evento push do servidor (file_created, file_deleted, file_updated)."""
        action = event.get("action", "")
        file_info = event.get("file", {})
        id_hash = file_info.get("id_hash", "")
        original_name = file_info.get("original_name", "")
        content_md5 = file_info.get("content_md5")

        logger.info("Processando drive_event: action=%s, file=%s, id=%s", action, original_name, id_hash[:8] if id_hash else "?")

        if not id_hash or not original_name:
            logger.warning("drive_event sem id_hash ou original_name — ignorado.")
            return

        # MODE gate before ANY action. The gate lived inside the
        # file_created/file_updated branch, so 'file_deleted' also ran in
        # SYNC_MODE=upload (the default): an admin cleaning up old files in
        # Drive triggered unlink() on the originals on the technician's disk,
        # including all the .shp/.dbf/.shx/.prj components. The polling path
        # always respected the mode — the divergence was the bug.
        if self.sync_mode not in ("download", "bidirectional"):
            logger.debug("drive_event '%s' ignorado: SYNC_MODE=%s nao consome mudancas do Drive.",
                         action, self.sync_mode)
            return

        self._syncing = True
        try:
            if action == "file_deleted":
                # Matches ONLY by remote id: discarding a local file by name
                # similarity would be too destructive for a push event.
                ds_name = self._find_dataset(id_hash=id_hash)
                if ds_name:
                    self._discard_dataset(ds_name, "push: deletado no Drive")

            elif action in ("file_created", "file_updated"):
                # Ignores extensions not recognized by the scanner
                if Path(original_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                    logger.debug("Push event '%s' ignorado (extensão não suportada).", original_name)
                    return

                # Sync seletivo
                if not self.sync_config.should_download(original_name, id_hash):
                    return

                # Reuses the key of the already-known dataset — deriving a new key
                # on every push duplicated the entry in the manifest.
                ds_key = self._find_dataset(id_hash, original_name)
                ds_info = (self.manifest.get_dataset(ds_key) or {}) if ds_key else {}

                # Same guard as the polling path: push consumes Drive changes
                # exactly like it does, and must not write a single-file
                # dataset over a multi-file entry.
                if ds_key and self._bundle_blocks_download(ds_key, ds_info, id_hash,
                                                           original_name, content_md5):
                    return

                # Downloads the file — destination always contained in sync_dir.
                dest = safe_join_or_none(self.sync_dir, original_name, context="push download")
                if dest is None:
                    self.events.emit("sync_error", dataset=original_name,
                                     error="Nome de arquivo rejeitado por seguranca")
                    return

                # Conflict: push inherited only half of polling's contract —
                # it wrote over the field edit without emitting conflict_detected
                # and without respecting SYNC_CONFLICT_STRATEGY.
                if ds_key and self.sync_mode == "bidirectional":
                    locais = [
                        p for p in (
                            safe_join_or_none(self.sync_dir, fname, context="push conflito")
                            for fname in (ds_info.get("files") or {})
                        )
                        if p is not None and p.exists()
                    ]
                    if locais:
                        local_md5_now = await em_thread(_paths_md5, locais)
                        if not self._resolve_conflict(ds_key, ds_info, local_md5_now, locais):
                            return

                self.events.emit("file_downloading", dataset=original_name)
                success = await self.downloader.download(id_hash, dest)

                if success:
                    from executor.sync.scanner import _compute_md5
                    downloaded_md5 = await em_thread(_compute_md5, dest)
                    ds_key = ds_key or _new_remote_ds_key(original_name, self.manifest.all_datasets())
                    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

                    # size/mtime of the file ON DISK: those are what the `diff`
                    # shortcut compares on the next cycle.
                    from executor.sync.scanner import entrada_de_manifesto
                    self.manifest.set_dataset(ds_key, {
                        "type": ext,
                        "files": {original_name: entrada_de_manifesto(dest, downloaded_md5)},
                        "status": "synced",
                        "remote_id_hash": id_hash,
                        "remote_name": original_name,
                        "remote_md5": content_md5 or downloaded_md5,
                        "local_md5": downloaded_md5,
                        "sync_direction": "remote",
                    })
                    self._emit_downloaded(original_name, dest)
                    logger.info("Push sync: '%s' baixado (%s).", original_name, action)
                else:
                    self.events.emit("sync_error", dataset=original_name, error="Download falhou")
        finally:
            await self.manifest.flush()
            # Order matters: clear the flag BEFORE reopening `_syncing`. The
            # other way around, a file event arriving in that gap was wiped by
            # clear() and the change would only be seen 30s later.
            self._change_flag.clear()
            self._syncing = False

    def _discard_dataset(self, ds_name: str, reason: str) -> bool:
        """
        Discards a local dataset on Drive's orders — to the trash, not unlink
        — and ONLY then removes the manifest entry. Returns True if it completed.

        There is no OS trash on this path and no recovery re-download: a
        mistake on the server side would erase field work irreversibly.

        The manifest entry is only dropped when ALL the files have left the
        disk. Removing it even when the move failed (QGIS with the .geojson
        open: on Windows a handle without FILE_SHARE_DELETE makes the rename
        raise PermissionError), the file stayed on disk without a manifest
        entry — and the following _local_to_remote saw it as a NEW dataset and
        re-sent it to Drive, even firing the ingestion trigger. The admin
        deleted it again and the cycle repeated. On failure: keeps the entry
        and re-enqueues the discard.
        """
        ds_info = self.manifest.get_dataset(ds_name) or {}
        alvos: list[Path] = []
        for fname in ds_info.get("files") or {}:
            local_file = safe_join_or_none(self.sync_dir, fname, context=reason)
            if local_file is not None and local_file.exists():
                alvos.append(local_file)

        falhos = move_dataset_to_trash(self.sync_dir, ds_name, alvos)
        if falhos:
            logger.warning("Dataset '%s' mantido no manifesto: %d de %d arquivo(s) nao foram "
                           "para a lixeira (%s).", ds_name, len(falhos), len(alvos), reason)
            self.manifest.mark_pending(ds_name, "discard")
            # `enqueue` is idempotent per (action, dataset): re-enqueuing the same
            # discard on every attempt neither duplicates the item nor resets the backoff.
            self.manifest.enqueue("discard", ds_name)
            self.events.emit("sync_error", dataset=ds_name,
                             error="Arquivo em uso — descarte local adiado")
            return False

        if alvos:
            logger.info("Dataset '%s': %d arquivo(s) movido(s) para a lixeira (%s).",
                        ds_name, len(alvos), reason)
        self.manifest.remove_dataset(ds_name)
        self.events.emit("file_deleted_local", dataset=ds_name)
        return True

    def _bundle_blocks_download(self, ds_name: str, ds_info: dict, remote_id: str,
                                remote_name: str, remote_md5: str | None) -> bool:
        """
        Protects a MULTI-FILE manifest entry from a single-file download.
        True = don't download (the case has already been handled or refused
        here).

        A shapefile lives in Drive as a single '<dataset>.zip' that WE upload,
        while the manifest keeps the .shp/.dbf/.shx components. Writing any
        download to that key replaces 'files' with a single-file dataset — and
        the damage doesn't stop at the manifest: the next cycle's diff() flags
        the bundle as modified, re-uploads it with a new id and asks to delete
        the id that was left in the entry, which may be ANOTHER workspace
        user's object. Two cases, same answer:

          * same remote id → it's our own bundle coming back; nothing to
            download, we just realign the remote MD5 (the zip's hash never
            matches the combined hash of the components, so the normal
            comparison would have it downloaded over them forever);
          * different id → someone else's object that merely COLLIDES by name,
            either with the derived '<ds>.zip' or with a component's name.
            There is no safe destination: the scanner groups everything by
            stem, the file would be orphaned on disk and downloaded again every
            cycle. We refuse and notify the dashboard — adopting the other id
            (what the code used to do) left our real copy orphaned in Drive and
            pointed the dataset at a third party's content.
        """
        if ds_info.get("type") != "shapefile" and len(ds_info.get("files") or {}) <= 1:
            return False

        if remote_id and remote_id == ds_info.get("remote_id_hash"):
            if remote_md5 and remote_md5 != ds_info.get("remote_md5"):
                self.manifest.mark_synced(
                    ds_name, remote_id, remote_md5=remote_md5,
                    local_md5=ds_info.get("local_md5"),
                )
            return True

        logger.warning("Objeto remoto '%s' (%s) ignorado: colide com o dataset multi-arquivo "
                       "'%s' (id remoto %s).", remote_name, (remote_id or "?")[:8], ds_name,
                       (ds_info.get("remote_id_hash") or "-")[:8])
        self.events.emit("sync_error", dataset=remote_name,
                         error=f"Nome colide com o dataset local '{ds_name}'")
        return True

    def _emit_downloaded(self, dataset: str, dest: Path) -> None:
        """Emits `file_downloaded` with the size of the file that just arrived.

        The downloader writes in streaming and doesn't tally anything;
        measuring the finished file is simpler than summing chunks in the hot
        loop, and gives the same number. Best-effort: a failing `stat` must not
        prevent the event, which is what the UI uses to know the download
        finished.
        """
        try:
            total = dest.stat().st_size
        except OSError:
            total = 0
        self.events.emit("file_downloaded", dataset=dataset, total_bytes=total)

    def _resolve_conflict(self, ds_name: str, ds_info: dict, local_md5_now: str,
                          local_paths: list[Path]) -> bool:
        """
        Conflict policy when the remote object AND the local files have changed
        since the last sync. Returns True if the download may proceed.

        Lives outside the two paths that consume Drive (polling and push) on
        purpose: push went straight from `should_download` to `download` and
        wrote over the field edit — with no `conflict_detected` on the
        dashboard and without the `_local_<timestamp>` backup that keep-both
        promises.
        """
        saved_local_md5 = ds_info.get("local_md5") or ""
        if not saved_local_md5 or local_md5_now == saved_local_md5:
            return True  # so o remoto mudou — download normal

        self.events.emit("conflict_detected", dataset=ds_name)
        strategy = agent_config.SYNC_CONFLICT_STRATEGY
        logger.warning("Conflito em '%s' — estrategia: %s", ds_name, strategy)

        if strategy == "local-wins":
            return False
        if strategy == "keep-both":
            from datetime import datetime as _dt
            suffix = _dt.now().strftime("%Y%m%dT%H%M%S")
            for path in local_paths:
                backup = path.with_name(f"{path.stem}_local_{suffix}{path.suffix}")
                try:
                    path.rename(backup)
                except OSError as exc:
                    # Without a backup there is no "keep both": aborting the download is
                    # the only outcome that doesn't lose the local version.
                    logger.error("Backup de '%s' falhou (%s) — download de '%s' abortado.",
                                 path.name, exc, ds_name)
                    self.events.emit("sync_error", dataset=ds_name, error="Backup local falhou")
                    return False
                logger.info("Backup: %s → %s", path.name, backup.name)
        return True

    async def _local_to_remote_only(self):
        """Detecta mudancas locais e faz upload. Sem polling remoto."""
        self._syncing = True
        try:
            await self._local_to_remote()
            self.manifest.set_last_scan()
        finally:
            await self.manifest.flush()
            self._change_flag.clear()
            self._syncing = False
            # Marks the end of the cycle AFTER the work: the floor counts from
            # here, otherwise a 2-minute sweep would already be born expired.
            self._ultimo_ciclo = asyncio.get_running_loop().time()

    async def _full_sync(self):
        """Executa scan completo e sincroniza diferencas."""
        self._syncing = True
        try:
            self.events.emit("sync_started")

            # ── 1. Upload local → remote ─────────────────────────────────────
            # `catalog` goes here: it registers the dataset on the server. It
            # does NOT go in the download block — there is no remote object to
            # download, and the source file is already on this machine.
            if self.sync_mode in ("upload", "bidirectional", "catalog"):
                await self._local_to_remote()

            # ── 2. Download remoto → local ───────────────────────────────────
            if self.sync_mode in ("download", "bidirectional"):
                await self._remote_to_local()

            self.manifest.set_last_scan()
            self.events.emit("sync_complete")
        finally:
            await self.manifest.flush()
            # Descarta os avisos gerados durante o sync (downloads proprios)
            self._change_flag.clear()
            self._syncing = False

    async def _em_paralelo(self, corrotinas: list, contexto: str):
        """Runs the transfers with a concurrency ceiling, without killing the batch.

        The ceiling is low (SYNC_CONCURRENCY) on purpose: on a field link, high
        concurrency worsens the total time and risks blowing the transfer's
        300s timeout. `return_exceptions=True` because a failing dataset must
        not cancel the others — each `_upload_dataset` already takes care of
        its own enqueuing for retry.
        """
        if not corrotinas:
            return
        # PROCESS semaphore (see `_semaforo_de_transferencia`): the ceiling applies
        # to the link, which all folders share. Obtained here, and not in
        # __init__, because the manager is built before the event loop exists.
        semaforo = _semaforo_de_transferencia()

        async def _limitada(coro):
            async with semaforo:
                return await coro

        resultados = await asyncio.gather(*(_limitada(c) for c in corrotinas),
                                          return_exceptions=True)
        for resultado in resultados:
            if isinstance(resultado, asyncio.CancelledError):
                raise resultado
            if isinstance(resultado, Exception):
                logger.error("Operacao de %s em '%s' falhou: %s",
                             contexto, self.sync_dir, resultado, exc_info=resultado)

    async def _local_to_remote(self):
        """Detecta mudancas locais e faz upload para o Drive."""
        # scan() is heavy synchronous I/O (stat of everything): off the event loop.
        # The executor uses ping_interval=None, so the 30s application heartbeat
        # is the ONLY keepalive — blocking the loop drops the connection (close
        # 4408) and kills the run in progress.
        current_datasets = await em_thread(self.scanner.scan)
        manifest_datasets = self.manifest.all_datasets()

        # Safety net for the (size, mtime) shortcut: every so often the diff
        # rehashes everything, to catch the rare rewrite that preserves mtime.
        agora = time.monotonic()
        hash_completo = (self._ultimo_hash_completo is None
                         or (agora - self._ultimo_hash_completo) >= SYNC_FULL_HASH_INTERVAL)

        # diff() also goes to the thread: it is what triggers `file_hashes()` and,
        # with it, the MD5 of the candidate files (the scan only does stat).
        new_ds, modified_ds, removed_ds = await em_thread(
            self.scanner.diff, current_datasets, manifest_datasets, hash_completo
        )

        # The marker is only stamped AFTER the diff completes. Stamped before, it
        # was consumed by a pass that might never happen: the diff with
        # force_hash opens ALL the files in the folder and any OSError sent the
        # whole cycle into `run()`'s backoff — but the safety net was already
        # recorded as done and would only come back 1h later (at boot, never).
        # A file rewritten with (size, mtime) preserved went hours without upload.
        if hash_completo:
            self._ultimo_hash_completo = agora

        # New datasets — only uploads if it didn't come from remote.
        # The list holds (name, dataset) and not coroutines: there is still an
        # `await` before the gather, and a coroutine created and never awaited
        # becomes a warning.
        a_enviar: list[tuple[str, Dataset]] = []
        for name in new_ds:
            old = manifest_datasets.get(name, {})
            if old.get("sync_direction") == "remote":
                continue  # Was just downloaded from Drive, don't re-upload
            a_enviar.append((name, current_datasets[name]))

        # Modified — ignores it if it came from remote and wasn't edited locally
        for name in modified_ds:
            ds = current_datasets[name]
            old = manifest_datasets.get(name, {})

            if old.get("sync_direction") == "remote":
                # Computes the local file's current MD5. It reads the disk again, so
                # it has the same window as the diff: if the file vanished or is
                # locked now, leave it for the next cycle instead of killing the
                # whole cycle (`run()` would fall into backoff and the folder would stop).
                try:
                    local_md5 = await em_thread(_dataset_md5, ds)
                except OSError as exc:
                    logger.info("Dataset '%s' indisponivel para leitura (%s) — adiado para o "
                                "proximo ciclo.", name, exc)
                    continue
                saved_md5 = old.get("local_md5", "")
                if local_md5 == saved_md5:
                    continue  # Unchanged since the download — don't re-upload

            # The DELETE of the old copy happens INSIDE _upload_dataset: it is the
            # only point both the direct upload and the queue retry go through.
            a_enviar.append((name, ds))

        # Uploads are mutually independent I/O: serially, the first sync of
        # 200 small files spent the whole time waiting on round-trips with
        # the link idle.
        await self._em_paralelo(
            [self._upload_dataset(nome, dataset) for nome, dataset in a_enviar], "upload")

        # Removidos localmente
        for name in removed_ds:
            old = manifest_datasets.get(name, {})

            # File that came from remote — re-download (the server is the source of truth)
            if old.get("sync_direction") == "remote" and self.sync_mode in ("download", "bidirectional"):
                rid = old.get("remote_id_hash")
                if rid:
                    # Rebuilds the file name from the manifest
                    fnames = list(old.get("files", {}).keys())
                    fname = fnames[0] if fnames else f"{name}.{old.get('type', 'bin')}"
                    dest = safe_join_or_none(self.sync_dir, fname, context="re-download")
                    if dest is None:
                        continue
                    logger.info("Re-baixando '%s' (deletado localmente, servidor e fonte de verdade).", fname)
                    self.events.emit("file_downloading", dataset=fname)
                    success = await self.downloader.download(rid, dest)
                    if success:
                        from executor.sync.scanner import _compute_md5
                        downloaded_md5 = await em_thread(_compute_md5, dest)
                        old["local_md5"] = downloaded_md5
                        old["status"] = "synced"
                        old["files"] = {fname: {"md5": downloaded_md5, "size": dest.stat().st_size, "mtime": dest.stat().st_mtime}}
                        self.manifest.set_dataset(name, old)
                        self._emit_downloaded(fname, dest)
                    else:
                        self.events.emit("sync_error", dataset=fname, error="Re-download falhou")
                continue

            old_id = old.get("remote_id_hash")
            if old_id:
                success = await self.uploader.delete(old_id)
                if success:
                    self.manifest.remove_dataset(name)
                    logger.info("Dataset '%s' removido do Drive.", name)
                else:
                    self.manifest.enqueue("delete", name, {"remote_id_hash": old_id})
            else:
                self.manifest.remove_dataset(name)

    async def _remote_to_local(self):
        """Detecta mudancas no Drive e baixa/remove localmente."""
        all_remote = await self.downloader.list_remote()
        if all_remote is None:
            return  # Connection error — don't make deletion decisions

        # all_remote may be [] if Drive is empty — we still need to detect deletions

        manifest_datasets = self.manifest.all_datasets()

        # The manifest ↔ remote object mapping comes from the manifest's own
        # inverted indexes (remote id → remote object name → local file name).
        # Rebuilding them here every cycle was O(datasets) for nothing — and
        # the 'remote_name' match, which keeps a shapefile's '<dataset>.zip'
        # from being mistaken for a new file, is the same on both sides.
        conhecido = self.manifest.find_by_remote_id

        # Deduplicates by original_name: keeps only the most recent (the list already
        # comes sorted by created_at desc from the endpoint) — EXCEPT when one of
        # the namesakes is precisely the object the manifest already references.
        # Someone else's newer 'parcelas.zip' dropped our own copy from the
        # iteration and the dataset ended up repointed at the other's file.
        latest_by_name: dict[str, object] = {}
        for rf in all_remote:
            anterior = latest_by_name.get(rf.original_name)
            if anterior is None or (conhecido(rf.id_hash) is not None
                                    and conhecido(anterior.id_hash) is None):
                latest_by_name[rf.original_name] = rf

        remote_files = list(latest_by_name.values())
        # Set of ALL remote IDs (for deletion detection, includes duplicates)
        all_remote_ids = {rf.id_hash for rf in all_remote}

        # A SINGLE scan for the whole loop. Before, scanner.scan() was called
        # INSIDE the per-remote-file loop: O(n x bytes) of synchronous reading
        # inside the coroutine, enough to blow the 30s heartbeat.
        local_datasets: dict[str, Dataset] = {}
        if self.sync_mode == "bidirectional":
            local_datasets = await em_thread(self.scanner.scan)

        pendentes = []
        for rf in remote_files:
            # Ignores extensions not recognized by the scanner (avoids a re-download loop)
            if Path(rf.original_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                logger.debug("Arquivo remoto '%s' ignorado (extensão não suportada).", rf.original_name)
                continue

            # Sync seletivo
            if not self.sync_config.should_download(rf.original_name, rf.id_hash):
                continue

            pendentes.append(self._sincronizar_remoto(rf, manifest_datasets, local_datasets))

        # Downloads are also independent I/O: serially, entering a new workspace
        # showed one `file_downloading` at a time with the link idle.
        await self._em_paralelo(pendentes, "download")

        # ── Detects remote deletions ─────────────────────────────────────────
        # If the manifest's remote_id_hash no longer exists in Drive, removes it locally.
        # In bidirectional mode: removes regardless of who created it (the server is the source of truth).
        # In download mode: same.
        for ds_name, ds_info in list(manifest_datasets.items()):
            rid = ds_info.get("remote_id_hash")
            if not rid:
                continue  # Was never synced with remote
            if rid not in all_remote_ids:
                self._discard_dataset(ds_name, "deletado no Drive")

    async def _sincronizar_remoto(self, rf, manifest_datasets: dict,
                                  local_datasets: dict[str, Dataset]):
        """Decides and does what to do with ONE Drive object.

        Extracted from the `_remote_to_local` loop so it can run in parallel
        with the others. There is no race in key allocation: between
        `_new_remote_ds_key` and `set_dataset` there is no `await`, so the
        second coroutine already sees the key the first one just took.
        """
        ds_name = self.manifest.find(rf.id_hash, rf.original_name)
        ds_info = manifest_datasets.get(ds_name, {}) if ds_name else {}

        # Checks whether it needs downloading
        if ds_name and ds_info:
            # Multi-file entry (shapefile bundle): never write a download
            # over it — see _bundle_blocks_download.
            if self._bundle_blocks_download(ds_name, ds_info, rf.id_hash,
                                            rf.original_name, rf.content_md5):
                return

            saved_remote_md5 = ds_info.get("remote_md5")
            saved_remote_id = ds_info.get("remote_id_hash")

            # Mesmo ID e MD5? Nada mudou.
            if saved_remote_id == rf.id_hash:
                if not rf.content_md5 or rf.content_md5 == saved_remote_md5:
                    return  # No change

            # Different MD5 or different ID → changed on remote
            if rf.content_md5 and saved_remote_md5 and rf.content_md5 == saved_remote_md5:
                # Mesmo conteudo, ID diferente (re-upload identico) — atualiza ID no manifest
                self.manifest.mark_synced(
                    ds_name, rf.id_hash, remote_md5=rf.content_md5,
                    local_md5=ds_info.get("local_md5"),
                )
                return

            # No remote MD5? Can't compare — skip (avoids an infinite loop)
            if not rf.content_md5:
                return

            # ── Conflito (bidirectional) ─────────────────────────────────────
            if self.sync_mode == "bidirectional":
                current_local = local_datasets.get(ds_name)
                if current_local:
                    local_md5_now = await em_thread(_dataset_md5, current_local)
                    if not self._resolve_conflict(
                        ds_name, ds_info, local_md5_now,
                        [finfo.path for finfo in current_local.files.values()],
                    ):
                        return

        # ── Download ─────────────────────────────────────────────────────────
        dest = safe_join_or_none(self.sync_dir, rf.original_name, context="download remoto")
        if dest is None:
            self.events.emit("sync_error", dataset=rf.original_name,
                             error="Nome de arquivo rejeitado por seguranca")
            return
        self.events.emit("file_downloading", dataset=rf.original_name)
        success = await self.downloader.download(rf.id_hash, dest)

        if not success:
            self.events.emit("sync_error", dataset=rf.original_name, error="Download falhou")
            return

        self._emit_downloaded(rf.original_name, dest)
        # Computes the MD5 of the downloaded file (for future comparison)
        from executor.sync.scanner import _compute_md5
        downloaded_md5 = await em_thread(_compute_md5, dest)

        ds_key = ds_name or _new_remote_ds_key(rf.original_name, manifest_datasets)
        # size/mtime come from the file that is ON DISK, not from what the server
        # declared: those are what the `diff` shortcut compares on the next
        # cycle, and a diverging size would make the file be rehashed forever.
        from executor.sync.scanner import entrada_de_manifesto
        self.manifest.set_dataset(ds_key, {
            "type": rf.extension,
            "files": {rf.original_name: entrada_de_manifesto(dest, downloaded_md5)},
            "status": "synced",
            "remote_id_hash": rf.id_hash,
            "remote_name": rf.original_name,
            "remote_md5": rf.content_md5 or downloaded_md5,
            "local_md5": downloaded_md5,
            "sync_direction": "remote",
            "synced_at": rf.updated_at or rf.created_at,
        })
        if not ds_name:
            logger.info("Novo arquivo remoto '%s' baixado (dataset '%s').", rf.original_name, ds_key)

    async def _upload_dataset(self, name: str, ds: Dataset,
                              enqueue_on_failure: bool = True) -> UploadResult | None:
        """Valida, extrai metadados e faz upload de um dataset."""
        # validate_dataset opens the file with geopandas/rasterio and extract_metadata
        # reads the whole dataset: heavy I/O + CPU, off the event loop.
        result = await em_thread(validate_dataset, ds)
        if not result.valid:
            for err in result.errors:
                logger.error("Validacao '%s': %s", name, err)
            return None

        # Extrai metadados espaciais
        spatial_meta = None
        if ds.primary_path:
            try:
                spatial_meta = await em_thread(extract_metadata, ds.primary_path, ds.type)
                spatial_meta["dataset_files"] = list(ds.files.keys())
            except Exception as e:
                logger.warning("Metadados de '%s' indisponiveis: %s", name, e)

        # Computes the local MD5 before the upload (also populates the FileInfo cache).
        local_md5 = await em_thread(_dataset_md5, ds)

        # Marks as uploading by MERGING into the existing entry. Replacing the
        # entry lost 'remote_id_hash' — the old copy was orphaned in Drive and
        # _remote_to_local ignored a dataset without a remote id.
        # And 'files' is NOT written here on purpose: if the process dies before
        # the upload is confirmed, a manifest with the new MD5s makes diff()
        # conclude "up to date" and the file never gets uploaded again.
        ds_info = dict(self.manifest.get_dataset(name) or {})
        old_id = ds_info.get("remote_id_hash")
        ds_info["type"] = ds.type
        ds_info["status"] = "uploading"
        ds_info["sync_direction"] = "local"
        self.manifest.set_dataset(name, ds_info)

        # Catalog mode (LGPD): registers the metadata and does NOT send the bytes.
        # The file stays in the user's folder and can only be read by workflows
        # running on this executor.
        if self.sync_mode == "catalog":
            self.events.emit("file_cataloging", dataset=name, total_bytes=ds.total_size)
            upload = await self.uploader.register(ds, spatial_meta)
        else:
            self.events.emit("file_uploading", dataset=name, total_bytes=ds.total_size)
            upload = await self.uploader.upload(ds, spatial_meta)

        if upload:
            # Only now does the local state become "the version in Drive": writes the
            # files and the name/MD5 of the remote OBJECT (for a shapefile, the '<dataset>.zip').
            ds_info = dict(self.manifest.get_dataset(name) or {})
            ds_info["files"] = {fname: finfo.to_dict() for fname, finfo in ds.files.items()}
            ds_info["remote_name"] = upload.remote_name
            self.manifest.set_dataset(name, ds_info)

            self.manifest.mark_synced(
                name, upload.id_hash, spatial_meta,
                local_md5=local_md5,
                remote_md5=upload.remote_md5,
            )
            # OPPORTUNISTIC flush: durability every SYNC_FLUSH_INTERVAL
            # seconds, instead of reserializing the whole manifest per dataset
            # (that was what made the initial sync of a large folder get
            # slower with every file). The end-of-cycle flush settles the
            # account. The order documented above still holds: what sits in
            # the window is the OLD state, which only causes a re-upload, never
            # a new MD5 taken as confirmed.
            await self.manifest.flush(min_intervalo=SYNC_FLUSH_INTERVAL)

            # UPLOAD FIRST, delete the old copy afterwards — and HERE, not in the
            # caller. Deleting before the PUT opened a window of TOTAL loss (a
            # crash between the DELETE and the PUT made the file vanish from
            # Drive while the disk still matched the manifest: diff() considered
            # it "up to date" and nobody re-sent it). But deleting in
            # _local_to_remote left out the SyncQueue retry — it calls
            # _upload_dataset directly and doesn't know the old id — and the
            # obsolete copy stayed in the bucket forever with the SAME
            # original_name, later coming back as a "new file" in
            # _remote_to_local and resurrecting old content.
            if old_id and old_id != upload.id_hash:
                if not await self.uploader.delete(old_id):
                    logger.warning("Versao antiga de '%s' (%s) permanece no Drive — delete falhou.",
                                   name, old_id[:8])

            # total_bytes/file_count go in the event because the dashboard accumulates
            # the volume transferred in the session; both values are already at
            # hand (the log on the next line uses both).
            self.events.emit("file_uploaded", dataset=name,
                             total_bytes=ds.total_size, file_count=len(ds.files))
            logger.info("Dataset '%s' sincronizado → %s (%d arquivo(s), %s).",
                        name, upload.id_hash, len(ds.files), _format_size(ds.total_size))

            # Triggers a workflow if configured
            if self.trigger.enabled:
                primary = ds.primary_path
                await self.trigger.on_file_synced(name, {
                    "id_hash": upload.id_hash,
                    "original_name": primary.name if primary else name,
                    "extension": ds.type,
                    "size": ds.total_size,
                })
            return upload

        if enqueue_on_failure:
            self.manifest.enqueue("upload", name)
        self.manifest.mark_pending(name, "upload")
        self.events.emit("sync_error", dataset=name, error="Upload falhou")
        logger.warning("Dataset '%s': upload falhou — enfileirado para retry.", name)
        return None

    async def _execute_pending(self, item: dict) -> bool:
        """Executor for the SyncQueue."""
        action = item["action"]
        dataset_name = item["dataset"]

        if action == "upload":
            # One scan per queue PASS, not per item: with 5 pending items, the
            # retry swept the whole folder 5 times just to find 5 datasets.
            if self._scan_da_fila is None:
                self._scan_da_fila = await em_thread(self.scanner.scan)
            current = self._scan_da_fila
            ds = current.get(dataset_name)
            if not ds:
                logger.info("Dataset '%s' nao existe mais — removendo da fila.", dataset_name)
                return True
            # Reuses the normal path so the retry writes 'files'/'remote_name'
            # exactly like the direct upload. enqueue_on_failure=False because
            # the item is already in the queue — the SyncQueue handles the retry.
            upload = await self._upload_dataset(dataset_name, ds, enqueue_on_failure=False)
            return upload is not None

        elif action == "delete":
            remote_id = item.get("remote_id_hash")
            if remote_id:
                return await self.uploader.delete(remote_id)
            return True

        elif action == "discard":
            # Deferred local discard: the file was locked by another process
            # (QGIS with the .shp open). Until it leaves the disk, the manifest
            # entry stays in place so diff() doesn't re-send the file.
            if self.manifest.get_dataset(dataset_name) is None:
                return True
            return self._discard_dataset(dataset_name, "retry: deletado no Drive")

        return False


def _new_remote_ds_key(original_name: str, existing: dict) -> str:
    """
    Manifest key for a remote file not yet known.

    The bare stem collides between a bundle ('parcelas', with .shp/.dbf/.shx)
    and a same-named Drive object ('parcelas.zip'): the second write overwrote
    the first's 'files'/'local_md5' and the next cycle deleted + re-sent with
    a new id, breaking any node that referenced the old id. When the stem is
    already taken, qualifies the key with the extension.
    """
    stem, _, ext = original_name.rpartition(".")
    if not stem:  # name without extension
        stem, ext = original_name, ""
    stem = stem.lower()
    if stem not in existing:
        return stem
    return f"{stem}.{ext.lower()}" if ext else stem


def _dataset_md5(ds: Dataset) -> str:
    """Computes the combined MD5 of all files in a dataset."""
    hashes = ds.file_hashes()
    if len(hashes) == 1:
        return next(iter(hashes.values()))
    return "|".join(sorted(hashes.values()))


def _paths_md5(paths: list[Path]) -> str:
    """
    Same combined hash as `_dataset_md5`, but from loose paths — the push
    path knows the files through the manifest, not through a scanned Dataset
    (scanning the whole folder on every push event would be too expensive).
    Synchronous: the caller runs it in a thread.
    """
    from executor.sync.scanner import _compute_md5

    hashes = sorted(_compute_md5(p) for p in paths)
    if len(hashes) == 1:
        return hashes[0]
    return "|".join(hashes)


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
