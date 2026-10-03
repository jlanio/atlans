# executor/sync/manifest.py
"""
Local sync manifest (.atlans-sync.json).
Persists each dataset's state: hash, remote_id, status, metadata.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from executor.sync.pool import em_thread
from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

_MANIFEST_FILE = ".atlans-sync.json"
_VERSION = 2


def remote_name_of(ds_name: str, ds_info: dict) -> str | None:
    """
    Name of the OBJECT in Drive that represents this dataset.

    For a shapefile this is not any local file: the uploader sends the bundle
    as '<dataset>.zip'. Manifests written before 'remote_name' existed fall
    back to the same deterministic name.
    """
    name = ds_info.get("remote_name")
    if name:
        return name
    if ds_info.get("type") == "shapefile":
        return f"{ds_name}.zip"
    return None


class SyncManifest:
    def __init__(self, sync_dir: str, workspace_id: str, executor_id: str):
        self.path = Path(sync_dir) / _MANIFEST_FILE
        self.workspace_id = workspace_id
        self.executor_id = executor_id
        self._data: dict = self._load()
        # Write-behind: each mutation only advances a version counter; the one that
        # writes is the end-of-cycle `flush()`. Before, a single upload triggered
        # THREE reserializations of the whole JSON — syncing N datasets cost O(N²)
        # bytes written, on the same loop that sustains the WebSocket.
        #
        # It is a COUNTER, and not a boolean flag, because the flush writes off
        # the loop: with a flag, either it was cleared before the write (and a
        # full disk left the state only in memory, with the manifest marked
        # clean — a kill in that window re-sent the whole folder and left
        # orphaned copies in Drive), or it was cleared after (and mutations
        # made DURING the write were forgotten). With a version, we know exactly
        # which snapshot reached the disk.
        self._versao = 0
        self._versao_no_disco = 0
        self._ultimo_flush = 0.0
        self._gravando = False

        # Inverted indexes for drive_event routing. Without them,
        # `claims_event` swept every dataset of every folder on EACH push
        # event — with 3 folders of 2000 datasets and a batch publication,
        # that's millions of dictionary comparisons inside the event loop.
        self._by_remote_id: dict[str, str] = {}
        self._by_remote_name: dict[str, str] = {}
        self._by_file: dict[str, str] = {}
        self._reindexar()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ver = data.get("version", 1)
                if ver == _VERSION:
                    return data
                if ver == 1:
                    return self._migrate_v1(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Manifesto corrompido, recriando: %s", e)
        return self._empty()

    def _migrate_v1(self, data: dict) -> dict:
        """Migra manifesto v1 para v2 (adiciona campos bidi-sync)."""
        data["version"] = 2
        data.setdefault("sync_mode", "upload")
        for ds in data.get("datasets", {}).values():
            ds.setdefault("remote_md5", None)
            ds.setdefault("local_md5", None)
            ds.setdefault("sync_direction", "local")
        logger.info("Manifesto migrado de v1 para v2.")
        return data

    def _empty(self) -> dict:
        return {
            "version": _VERSION,
            "workspace_id": self.workspace_id,
            "executor_id": self.executor_id,
            "sync_mode": "upload",
            "last_full_scan": None,
            "datasets": {},
            "pending_queue": [],
        }

    # ── Persistencia ─────────────────────────────────────────────────────────

    def _escrever(self, conteudo: str) -> bool:
        """Writes the manifest atomically (.tmp + os.replace).

        A crash in the middle of `json.dump` left the file truncated; `_load`
        recreated it from scratch and the executor re-sent the whole folder.

        Returns whether the content really reached the disk: the caller NEEDS
        to know, because only then can it consider the version persisted.
        Swallowing the OSError and treating the write as done turned a full
        disk into silent state loss — the symptom would be the manifest no
        longer saving, with no visible error in the sync flow.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(conteudo)
            os.replace(str(tmp), str(self.path))
            # Reapplied on EVERY write, not just on creation: on Windows
            # os.replace (MoveFileEx) makes the manifest inherit the attributes
            # of the `.tmp`, which is born visible — without this the file would
            # show up again in Explorer on the first flush. Writing to the `.tmp`
            # and then hiding the destination also avoids the other side of the
            # pitfall: open("w") with CREATE_ALWAYS on an ALREADY hidden file
            # fails with access denied on Windows — which is why we never write
            # directly to the final path.
            ocultar_no_windows(self.path)
            return True
        except OSError as e:
            logger.error("Erro ao salvar manifesto: %s", e)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _serializar(self) -> str:
        # No `indent=2`: it is a machine file, and indentation doubled the volume
        # written every cycle for no benefit at all.
        return json.dumps(self._data, default=str)

    def _marcar_sujo(self) -> None:
        self._versao += 1

    @property
    def _sujo(self) -> bool:
        """Is there a mutation not yet confirmed on disk?"""
        return self._versao != self._versao_no_disco

    async def flush(self, min_intervalo: float = 0.0) -> None:
        """Writes the manifest if it changed, off the event loop.

        `min_intervalo` > 0 is the opportunistic flush from inside a batch of
        uploads: durability every T seconds, instead of a full reserialization
        per dataset. The end of the cycle calls it with no interval (forced).

        Serialization happens HERE, on the loop, and not in the thread: the
        dict is mutated by the loop and a concurrent `json.dumps` would see the
        dictionary changing size in the middle of iteration.

        With concurrent uploads, two simultaneous writes would compete for the
        same `.tmp`: whoever arrives during a write gives up and leaves the
        manifest dirty — the end-of-cycle flush carries the newest state.

        The written version is captured BEFORE serialization and only becomes
        `_versao_no_disco` if the write is confirmed. That way: a failing write
        (full disk) keeps the manifest dirty and the next flush tries again; and
        a mutation made during the write stays pending, instead of being taken
        as saved along with the previous snapshot.
        """
        if not self._sujo or self._gravando:
            return
        if min_intervalo and (time.monotonic() - self._ultimo_flush) < min_intervalo:
            return
        versao = self._versao
        conteudo = self._serializar()
        # The rate-limit clock advances even if the write fails: otherwise, with a
        # full disk, every dataset in the batch would pay a full reserialization.
        self._ultimo_flush = time.monotonic()
        self._gravando = True
        try:
            gravou = await em_thread(self._escrever, conteudo)
        finally:
            self._gravando = False
        if gravou:
            self._versao_no_disco = versao

    # ── Indices invertidos ───────────────────────────────────────────────────

    def _reindexar(self):
        self._by_remote_id.clear()
        self._by_remote_name.clear()
        self._by_file.clear()
        for name, ds in self._data["datasets"].items():
            if isinstance(ds, dict):
                self._indexar(name, ds)

    def _indexar(self, name: str, ds: dict):
        rid = ds.get("remote_id_hash")
        if rid:
            self._by_remote_id[rid] = name
        rname = remote_name_of(name, ds)
        if rname:
            self._by_remote_name[rname] = name
        for fname in ds.get("files") or {}:
            self._by_file[fname] = name

    def _desindexar(self, name: str, ds: dict | None):
        """Removes from the index the keys of the entry's PREVIOUS version.

        A stale index would make a push land in the wrong folder or duplicate
        the entry, so removal is by VALUE: only what still points to this
        dataset leaves the index.
        """
        if not isinstance(ds, dict):
            return
        rid = ds.get("remote_id_hash")
        if rid and self._by_remote_id.get(rid) == name:
            del self._by_remote_id[rid]
        rname = remote_name_of(name, ds)
        if rname and self._by_remote_name.get(rname) == name:
            del self._by_remote_name[rname]
        for fname in ds.get("files") or {}:
            if self._by_file.get(fname) == name:
                del self._by_file[fname]

    def find(self, id_hash: str = "", original_name: str = "") -> str | None:
        """
        Finds the manifest key that represents a remote object.

        Order of confidence: remote id → remote object name → local file name.
        The 'remote_name' match is what recognizes a shapefile's
        '<dataset>.zip' — whose files in the manifest are the .shp/.dbf/...
        components, never the name of the package that was actually sent.
        """
        if id_hash:
            achado = self._by_remote_id.get(id_hash)
            if achado is not None:
                return achado
        if original_name:
            return (self._by_remote_name.get(original_name)
                    or self._by_file.get(original_name))
        return None

    def find_by_remote_id(self, id_hash: str) -> str | None:
        return self._by_remote_id.get(id_hash) if id_hash else None

    # ── Datasets ─────────────────────────────────────────────────────────────

    def get_dataset(self, name: str) -> dict | None:
        return self._data["datasets"].get(name)

    def set_dataset(self, name: str, dataset: dict):
        self._desindexar(name, self._data["datasets"].get(name))
        self._data["datasets"][name] = dataset
        self._indexar(name, dataset)
        self._marcar_sujo()

    def remove_dataset(self, name: str):
        self._desindexar(name, self._data["datasets"].get(name))
        self._data["datasets"].pop(name, None)
        self._marcar_sujo()

    def all_datasets(self) -> dict:
        return self._data["datasets"]

    def mark_synced(self, name: str, remote_id_hash: str, spatial_metadata: dict | None = None,
                    local_md5: str | None = None, remote_md5: str | None = None):
        ds = self._data["datasets"].get(name, {})
        self._desindexar(name, ds)
        ds["remote_id_hash"] = remote_id_hash
        ds["status"] = "synced"
        ds["synced_at"] = datetime.now(timezone.utc).isoformat()
        if spatial_metadata:
            ds["spatial_metadata"] = spatial_metadata
        if local_md5:
            ds["local_md5"] = local_md5
        if remote_md5:
            ds["remote_md5"] = remote_md5
        self._data["datasets"][name] = ds
        self._indexar(name, ds)
        self._marcar_sujo()

    def mark_pending(self, name: str, action: str):
        ds = self._data["datasets"].get(name, {})
        ds["status"] = "pending"
        ds["pending_action"] = action
        self._data["datasets"][name] = ds
        self._indexar(name, ds)
        self._marcar_sujo()

    # ── Queue ────────────────────────────────────────────────────────────────

    def enqueue(self, action: str, dataset_name: str, extra: dict | None = None):
        """Enqueues a pending operation. IDEMPOTENT per (action, dataset).

        The queue is a set of operations to perform, not a history: two
        `('upload', 'parcelas')` items mean the same thing. And the duplicate
        wasn't harmless — since each upload failure leaves the manifest entry
        without 'files', the next cycle's `diff` re-enqueued the same dataset,
        and the queue grew by one item per cycle. Each of them ran without
        backoff (scheduling only reaches the item actually executed), paying
        validate + extract_metadata + MD5 of the whole dataset every 30s.

        Re-enqueuing does NOT reset the backoff of the item already there: it
        only updates the extras (a delete's `remote_id_hash`, for example).
        """
        existente = next(
            (q for q in self._data["pending_queue"]
             if q.get("dataset") == dataset_name and q.get("action") == action),
            None,
        )
        if existente is not None:
            if extra:
                existente.update(extra)
                self._marcar_sujo()
            return

        item = {
            "action": action,
            "dataset": dataset_name,
            "retries": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_attempt": None,
            # Epoch of the next attempt. 0 = try on the next cycle. It is what
            # replaced the `asyncio.sleep(backoff)` that froze the whole
            # folder inside the cycle.
            "next_attempt_at": 0.0,
            **(extra or {}),
        }
        self._data["pending_queue"].append(item)
        self._marcar_sujo()

    def dequeue(self, dataset_name: str):
        self._data["pending_queue"] = [
            q for q in self._data["pending_queue"] if q["dataset"] != dataset_name
        ]
        self._marcar_sujo()

    def pending_items(self) -> list[dict]:
        return self._data["pending_queue"]

    def update_retry(self, item: dict, next_attempt_at: float = 0.0):
        """Records the failure ON THE ITEM that was executed.

        Takes the queue's own dict (and not the dataset name) because matching
        by name always updated the FIRST namesake: with the queue holding
        equivalent items, the others stayed forever with next_attempt_at=0 and
        retries=0 — re-executed every cycle, without backoff and without ever
        exhausting the attempts.
        """
        item["retries"] = item.get("retries", 0) + 1
        item["last_attempt"] = datetime.now(timezone.utc).isoformat()
        item["next_attempt_at"] = next_attempt_at
        self._marcar_sujo()

    # ── Scan ─────────────────────────────────────────────────────────────────

    def set_last_scan(self):
        self._data["last_full_scan"] = datetime.now(timezone.utc).isoformat()
        self._marcar_sujo()
