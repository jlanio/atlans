# executor/sync/sync_config.py
"""
SyncConfig — selective sync configuration.
Controls which remote datasets should be downloaded in bidirectional mode.

This module also concentrates GeoSync's PACING parameters (concurrency, floor
between cycles, thread pool size). They live here and not in
executor/config.py because only the sync subsystem reads them — and because
tweaking them without understanding the scan cycle is the fastest way to
put the disk at 100%.
"""
import fnmatch
import json
import logging
from pathlib import Path

from executor._ambiente import ler_int
from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

_CONFIG_FILE = ".atlans-sync-config.json"


# The parameters below go through the same tolerant parsing as the rest of the
# executor (executor/_ambiente.py::ler_int): an out-of-range value is a typo,
# not an intent — `SYNC_CONCURRENCY=0` would leave the folder with no uploads
# at all and the symptom ("nothing uploads") wouldn't point to the .env.

# Simultaneous transfers per folder (upload or download). The ceiling is low on
# purpose: on a field link, high concurrency worsens the total time and also
# risks blowing the 300s PUT/GET timeout.
SYNC_CONCURRENCY: int = ler_int("EXECUTOR_SYNC_CONCURRENCY", 3, 1, 16)

# Time floor between two cycles triggered by the WATCHER. Without it, copying a
# large file into the folder made the executor scan+hash everything every ~2s,
# in back-to-back cycles, competing for I/O with the copy itself.
SYNC_MIN_CYCLE: int = ler_int("EXECUTOR_SYNC_MIN_CYCLE", 5, 0, 3600)

# CYCLE debounce (not per path): after waking up, the cycle only starts once
# the folder has gone this long without any new event — it is the
# "stabilization" of the file being copied.
SYNC_QUIET_PERIOD: int = ler_int("EXECUTOR_SYNC_QUIET_PERIOD", 3, 0, 600)

# Ceiling on the wait for stabilization: an hours-long copy must not postpone
# the cycle forever.
SYNC_MAX_QUIET_WAIT: int = ler_int("EXECUTOR_SYNC_MAX_QUIET_WAIT", 120, 1, 3600)

# Safety net for the diff's (size, mtime) shortcut: every so often the cycle
# rehashes everything, to catch the rare rewrite that preserves mtime (a copy
# with `-p`, for example).
SYNC_FULL_HASH_INTERVAL: int = ler_int("EXECUTOR_SYNC_FULL_HASH_INTERVAL", 3600, 60, 86400)

# Threads of GeoSync's HEAVY work pool — zip, validate, metadata, MD5, scan
# (see executor/sync/pool.py). Small on purpose: it is CPU-bound work and must
# not compete with the workflows' nodes.
SYNC_THREADS: int = ler_int("EXECUTOR_SYNC_THREADS", 2, 1, 8)

# Threads of the transfers' BYTE I/O pool (PUT/GET chunks). It is separate
# from the one above because the two loads are nothing alike: each call here is
# short (1 MB of read/write) but needs continuous throughput, and in the same
# 2-thread pool a `_write_zip` of a GB bundle held ALL in-flight transfers for
# minutes — socket idle the whole time, which invites MinIO to drop the
# connection for idleness and throws the upload into the retry queue.
SYNC_IO_THREADS: int = ler_int("EXECUTOR_SYNC_IO_THREADS", 8, 1, 32)

# Minimum interval between manifest writes during a batch of uploads.
SYNC_FLUSH_INTERVAL: int = ler_int("EXECUTOR_SYNC_FLUSH_INTERVAL", 5, 0, 300)


class SyncConfig:
    """
    Manages selective sync filters, read from the synced folder's local
    .atlans-sync-config.json file.

    There used to be a second source, the remote config
    (GET /drive/executor-sync-config), but nothing on the server wrote it: the
    GET always returned the default. The route and the fetch were removed; old
    executors that still call it get an HTTP error (405: the path matches
    `DELETE /drive/{id_hash}`) and carry on with the local config, as they
    already did when the fetch failed.
    """

    def __init__(self, sync_dir: str | Path):
        self.sync_dir = Path(sync_dir)

        # Filtros
        self.include_patterns: list[str] = []   # ex: ["*.geojson", "parcelas_*"]
        self.exclude_patterns: list[str] = []   # ex: ["temp_*", "backup_*"]
        self.enabled_remote_ids: set[str] | None = None  # None = all

        self._load_local()

    def _load_local(self):
        config_path = self.sync_dir / _CONFIG_FILE
        if not config_path.exists():
            return

        # Config dotfile in the user's folder: on Windows the dot doesn't hide it,
        # so we ensure the hidden attribute whenever we find it. We are not the
        # ones who create it (it comes from the user or from the remote push),
        # which is why it's here, on read, and not on a write.
        ocultar_no_windows(config_path)

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            self.include_patterns = data.get("include", [])
            self.exclude_patterns = data.get("exclude", [])
            ids = data.get("enabled_ids")
            self.enabled_remote_ids = set(ids) if ids is not None else None
            logger.info("SyncConfig carregado: include=%s, exclude=%s, ids=%s",
                        self.include_patterns, self.exclude_patterns,
                        len(self.enabled_remote_ids) if self.enabled_remote_ids is not None else "todos")
        except Exception as exc:
            logger.warning("Erro ao ler %s: %s", _CONFIG_FILE, exc)

    def should_download(self, original_name: str, id_hash: str) -> bool:
        """Checks whether a remote file should be downloaded."""
        # If specific IDs are configured, check them
        if self.enabled_remote_ids is not None:
            if id_hash not in self.enabled_remote_ids:
                return False

        # If there are exclude patterns, check them
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(original_name, pattern):
                return False

        # If there are include patterns, it must match at least one
        if self.include_patterns:
            return any(fnmatch.fnmatch(original_name, p) for p in self.include_patterns)

        return True
