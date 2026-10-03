# executor/sysinfo.py
"""
Executor system metrics: hardware, container limits and the process's own
consumption.

Extracted from connection.py, where it lived because the only consumer was the
`capacity` payload sent to the server. With the local panel reading the same
things at 1 Hz, it makes more sense to live in its own module — and it keeps the
dashboard from importing the networking module just to get free RAM.

## Cost of the reads

Everything here is a blocking syscall and ALL callers are on the event loop: the
panel at 1 Hz (`dashboard/tick.py`) and `_capacity_loop` every 10 s. That is why
the memoization lives in THIS module, and not in each caller — that way nobody has
to remember to cache, and the data never diverges between the panel and the
`capacity` sent to the server. See `TTL_DISCO_S` and the cgroup memos further down.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

logger = logging.getLogger("executor.sysinfo")


def _read_cgroup_value(path: str) -> int | None:
    """Reads a numeric value from a cgroup file (v1 or v2)."""
    try:
        with open(path) as f:
            val = int(f.read().strip())
            # cgroup v1 uses 'max' or a very large value for "no limit"
            if val >= 2**60:
                return None
            return val
    except (FileNotFoundError, ValueError, OSError):
        return None


# Outside Linux /sys/fs/cgroup does not exist and never will — THIS one is an
# immutable fact, and it is what generated two to four FileNotFoundErrors per
# second on Windows/macOS. The platform guard solves that case with no cache.
_EH_LINUX = sys.platform.startswith("linux")

# The container limits (total RAM and CPU quota), on the other hand, are NOT
# immutable, contrary to what this module assumed: `docker update --memory/--cpus`
# and k8s in-place pod resize (GA in 1.33) rewrite /sys/fs/cgroup/* with the
# container live, without recreating anything or restarting the process. With
# the permanent memo, raising the limit from 4 to 16 GiB left `ram_available_gb`
# stuck at 0.0 forever (old limit lower than current usage), and lowering it from
# 4 to 2 GiB made the executor advertise ~2.5 GB of headroom that does not exist —
# in the panel, in the desktop snapshot and in the `capacity` that drives dispatch.
#
# Memo with a short TTL: still cuts ~97% of the open() calls per tick (the reason
# for the optimization) and self-corrects shortly after a limit change.
TTL_CGROUP_S = 30.0

_NEVER_READ = float("-inf")  # never read; do not use 0.0 (monotonic may be < TTL)
_cache_ram_total: int | None = None
_cache_ram_total_em = _NEVER_READ
_cached_cpu_cores: float | None = None
_cached_cpu_cores_at = _NEVER_READ


def _get_cgroup_ram_total() -> int | None:
    """Container RAM limit via cgroup v2 or v1. Memoized with a TTL — see above."""
    global _cache_ram_total, _cache_ram_total_em
    if not _EH_LINUX:
        return None
    agora = time.monotonic()
    if agora - _cache_ram_total_em < TTL_CGROUP_S:
        return _cache_ram_total
    # cgroup v2, with fallback to v1
    val = _read_cgroup_value("/sys/fs/cgroup/memory.max")
    if val is None:
        val = _read_cgroup_value("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    _cache_ram_total = val
    _cache_ram_total_em = agora
    return _cache_ram_total


def _get_cgroup_ram_available() -> int | None:
    """Computes the RAM available inside the container via cgroup."""
    limit = _get_cgroup_ram_total()
    if limit is None:
        return None
    # cgroup v2: usage em memory.current
    usage = _read_cgroup_value("/sys/fs/cgroup/memory.current")
    if usage is not None:
        return max(limit - usage, 0)
    # cgroup v1: usage em memory.usage_in_bytes
    usage = _read_cgroup_value("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if usage is not None:
        return max(limit - usage, 0)
    return None


def _get_cgroup_cpu_cores() -> float | None:
    """Container CPU quota via cgroup v2 or v1. Memoized with a TTL — see above.

    `process_metrics()` calls this on every panel tick: without the memo it was up
    to three `open()` calls per second. With the TTL, a `docker update --cpus` is
    noticed again within 30 s, instead of leaving `cpu_pct_norm` normalized by the
    old quota (CPU bar flattened, or overflowing 100 and getting clamped)
    forever.
    """
    global _cached_cpu_cores, _cached_cpu_cores_at
    if not _EH_LINUX:
        return None
    agora = time.monotonic()
    if agora - _cached_cpu_cores_at < TTL_CGROUP_S:
        return _cached_cpu_cores
    _cached_cpu_cores = _ler_cgroup_cpu_cores()
    _cached_cpu_cores_at = agora
    return _cached_cpu_cores


def _ler_cgroup_cpu_cores() -> float | None:
    # cgroup v2: cpu.max → "quota period" (ex: "200000 100000" = 2 cores)
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            parts = f.read().strip().split()
            if parts[0] == "max":
                return None  # no limit
            return round(int(parts[0]) / int(parts[1]), 1)
    except (FileNotFoundError, ValueError, OSError, IndexError):
        pass
    # cgroup v1: cpu.cfs_quota_us / cpu.cfs_period_us
    quota = _read_cgroup_value("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_cgroup_value("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and quota > 0 and period and period > 0:
        return round(quota / period, 1)
    return None


def _safe_disk_usage(psutil_mod):
    """Cross-platform psutil.disk_usage with a silent fallback.

    Windows: some psutil C bindings (notably: Anaconda 3.12+) blow up with
    `SystemError: argument 1 (impossible<bad format char>)` even with path
    'C:\\'. Tries several forms of root (CWD drive, SystemDrive, C:\\, .\\)
    and returns the first one that works. If all of them fail, returns None —
    system_info without disk is better than an infinite reconnection loop.
    """
    if os.name == "nt":
        candidates = []
        try:
            drv = os.path.splitdrive(os.getcwd())[0]
            if drv:
                candidates.append(drv + os.sep)
        except Exception:
            pass
        sys_drive = os.environ.get("SystemDrive")
        if sys_drive:
            candidates.append(sys_drive + os.sep)
        candidates.extend(["C:\\", "."])
    else:
        candidates = ["/"]

    for path in candidates:
        try:
            return psutil_mod.disk_usage(path)
        except (SystemError, OSError, PermissionError):
            continue
    return None


def _collect_system_info() -> dict | None:
    """Collects static hardware information (CPU, RAM, disk, OS).

    Inside Docker/K8s containers, prefers cgroup limits so as to
    reflect the resources actually available to the container.
    """
    try:
        import psutil
        import platform
        # disk may be None if psutil.disk_usage fails on all the
        # candidates (Windows C-binding bug, permission denied, etc).
        # We report 0 in that case — better than aborting system_info.
        disk = _safe_disk_usage(psutil)

        # CPU: prefers the cgroup limit, fallback to psutil
        cpu_cores = _get_cgroup_cpu_cores() or psutil.cpu_count(logical=True)

        # RAM: prefers the cgroup limit, fallback to psutil
        cgroup_ram = _get_cgroup_ram_total()
        ram_total = cgroup_ram if cgroup_ram else psutil.virtual_memory().total

        # Goes in the handshake. The server only keeps the SYSTEM_INFO_* fields (the
        # protocol allowlist, in flow/utils/protocolo_ws.py), each with its
        # group's type: a new field here has to be added there, otherwise it is
        # discarded with a WARNING on every connection.
        return {
            "hostname":      platform.node(),
            "os_name":       platform.system(),
            "os_version":    platform.release(),
            "cpu_cores":     cpu_cores,
            "ram_total_gb":  round(ram_total / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1) if disk else 0,
            "container":     cgroup_ram is not None,
        }
    except ImportError:
        return None


def _artifacts_disk(psutil_mod) -> object | None:
    """Usage of the disk WHERE THE ARTIFACTS ARE WRITTEN.

    Not the same as `_safe_disk_usage`, which measures the CWD drive — in the
    desktop app the CWD is the install folder and the artifacts go to the user
    profile, which may be on another drive (the folder is configurable).

    This started to really matter with the local locality mode: an artifact
    marked not to leave the machine has ONE copy, and it is here. A full disk
    stops being an inconvenience and becomes loss of customer data.

    Walks up the tree until it finds an existing directory: the configured folder
    may not have been created yet, and `disk_usage` on a nonexistent path raises.
    """
    from executor.config import ARTIFACTS_DIR

    alvo = os.path.abspath(ARTIFACTS_DIR)
    for _ in range(8):
        if os.path.isdir(alvo):
            try:
                return psutil_mod.disk_usage(alvo)
            except (SystemError, OSError, PermissionError):
                return None
        pai = os.path.dirname(alvo)
        if pai == alvo:
            break
        alvo = pai
    return None


# ── Disk cache ───────────────────────────────────────────────────────────────
# Free disk space is the most expensive and slowest quantity this module
# measures: it is two `disk_usage` calls (the CWD one also tries several
# candidates when the Windows binding fails) preceded by up to 8 `os.path.isdir`
# calls walking up the tree until it finds the artifacts folder. With that folder
# on a network drive or on a HDD that went to sleep, each collection blocks for
# hundreds of milliseconds — and it ran at 1 Hz INSIDE the event loop, delaying
# the heartbeat, result delivery and job reception.
#
# The defense is to recollect in a thread and serve the previous value while it
# runs: the event loop NEVER waits on disk I/O, not even on the first collection
# (on a hung drive it would block the whole executor startup — no heartbeat and
# no jobs received). Until the first collection lands, the keys simply do not
# exist and the panel shows "—".
#
# Three limits apply to this cache, and each one exists because of a symptom:
#
# 1. Adaptive TTL (`_value_ttl`). Far from the disk filling up, 60 s: that is
#    what takes the collection off the hot path. Close to full, 5 s — see the
#    `_value_ttl` docstring.
# 2. Age ceiling (`DISK_MAX_AGE_S`). Past it the value becomes
#    UNKNOWN (missing keys -> None -> "—" in the panel and in the desktop) instead
#    of continuing to be served as if it were a current reading. Serving stale
#    data is acceptable; serving stale data indistinguishable from fresh data is
#    not, in a gauge whose only job is to warn before the artifact is lost.
# 3. Deadline for the in-flight collection (`DISK_COLLECTION_TIMEOUT_S`) with a
#    thread ceiling (`MAX_DISK_COLLECTIONS_IN_FLIGHT`). `psutil.disk_usage` on an NFS
#    `hard` mount or a hung FUSE NEVER returns: the thread stays hung without ever
#    releasing the counter. Without a deadline, it would be a permanent lock
#    against any future attempt; with only a deadline, the executor would leak a
#    hung thread every 30 s forever. The ceiling closes both sides — a few
#    recovery attempts and then the number simply becomes unknown, which is the
#    honest answer.
TTL_DISCO_S = 60.0
DISK_LOW_TTL_S = 5.0

# Mirrors DISCO_BAIXO_GB from desktop/src/shared/disco.ts — the threshold at
# which the desktop starts warning. If the two diverged, the executor would stop
# refreshing precisely in the range where the alert is decided.
DISK_LOW_GB = 5.0

# ~3x the long TTL: absorbs one slow collection and one isolated failure (the
# retry only comes when the next TTL expires) without wiping the number.
DISK_MAX_AGE_S = 180.0
DISK_COLLECTION_TIMEOUT_S = 30.0
MAX_DISK_COLLECTIONS_IN_FLIGHT = 3

_disco_lock = threading.Lock()
_disk_value: dict = {}
_disk_expires = 0.0
_disk_in_flight = 0                   # collection threads that have not come back yet
_disk_collected_at = _NEVER_READ   # monotonic of the last SUCCESSFUL collection
_disk_started_at = _NEVER_READ    # monotonic of the last collection trigger
_disk_stale_logged = False      # the staleness warning is evaluated at 1 Hz; log it once


def _value_ttl(valor: dict) -> float:
    """Adaptive TTL: short when the disk is tight.

    The old premise ("no decision this number supports would change with the
    value from a minute ago") is false close to a full disk. The "Disco
    quase cheio" (disk almost full) toast (desktop/src/main/ui/notificacoes.ts)
    exists to warn BEFORE the workflow fails to write, and a GIS node writing a
    raster eats the last GBs in seconds: with a fixed 60 s the warning arrived
    after the failure, and the text ("já podem falhar ao gravar") became a
    statement of fact instead of a warning.

    Far from the threshold the long TTL still applies — it is what takes disk I/O
    off the 1 Hz path.
    """
    livres = [v for k, v in valor.items()
              if k.endswith("_free_gb") and isinstance(v, (int, float))]
    if livres and min(livres) < DISK_LOW_GB:
        return DISK_LOW_TTL_S
    return TTL_DISCO_S


def _coletar_disco(psutil_mod) -> dict:
    """The actual disk syscalls. Runs OUTSIDE the lock."""
    metrics: dict = {}
    disk = _safe_disk_usage(psutil_mod)
    if disk is not None:
        metrics["disk_free_gb"] = round(disk.free / (1024**3), 1)

    # Artifacts disk, reported separately: it may be another drive, and it is
    # the one that decides whether a workflow can write its result.
    #
    # In its OWN try: `_artifacts_disk` imports `executor.config`, and an
    # ImportError there would bring down the whole collection. The effect would
    # be to also lose the system disk because of this one, silently.
    try:
        art = _artifacts_disk(psutil_mod)
        if art is not None:
            metrics["artifacts_disk_free_gb"] = round(art.free / (1024**3), 1)
            metrics["artifacts_disk_total_gb"] = round(art.total / (1024**3), 1)
    except Exception:
        pass
    return metrics


def _refresh_disk(psutil_mod) -> None:
    global _disk_value, _disk_expires, _disk_in_flight
    global _disk_collected_at, _disk_stale_logged
    try:
        novo = _coletar_disco(psutil_mod)
    except Exception as exc:
        # WARNING, not DEBUG: an inaccessible artifacts folder was completely
        # silent, and it is precisely the case where the operator needs to know
        # that the panel's number stopped being reliable.
        logger.warning("Falha ao coletar metricas de disco: %s", exc)
        novo = None
    agora = time.monotonic()
    with _disco_lock:
        if novo is not None:
            _disk_value = novo
            _disk_collected_at = agora
            _disk_stale_logged = False
        # The TTL renews even on failure: the old value keeps being served (up to the
        # age ceiling) and the next attempt comes at the following expiry, without
        # hammering a drive that disappeared on every tick.
        _disk_expires = agora + _value_ttl(_disk_value)
        _disk_in_flight = max(_disk_in_flight - 1, 0)


def _disk_metrics(psutil_mod) -> dict:
    """Memoized disk space. See the note above.

    Returns `{}` (missing keys -> `None` in the consumers) until the
    first collection lands and whenever the last good value is older than
    `DISK_MAX_AGE_S`.
    """
    global _disk_in_flight, _disk_expires, _disk_started_at, _disk_stale_logged
    agora = time.monotonic()
    with _disco_lock:
        vencido = agora >= _disk_expires
        atual = _disk_value
        # While a collection is in flight no other is triggered: on a hung network
        # drive, each tick would open a new thread. But with a deadline — a
        # collection that went past DISK_COLLECTION_TIMEOUT_S is hung and may never
        # come back, and without this way out it would block every future attempt.
        pendurada = _disk_in_flight > 0 and (agora - _disk_started_at) >= DISK_COLLECTION_TIMEOUT_S
        disparar = (
            vencido
            and (_disk_in_flight == 0 or pendurada)
            and _disk_in_flight < MAX_DISK_COLLECTIONS_IN_FLIGHT
        )
        if disparar:
            _disk_in_flight += 1
            _disk_started_at = agora
            # Push the expiry forward ALREADY at trigger time: if the collection hangs
            # and never reaches `_refresh_disk`, this is what prevents a new
            # thread per tick. The normal path overwrites this when it finishes, so
            # the short TTL of a tight disk is not lost.
            _disk_expires = agora + max(_value_ttl(atual), DISK_COLLECTION_TIMEOUT_S)
        age = agora - _disk_collected_at
        obsoleto = bool(atual) and age >= DISK_MAX_AGE_S
        log_stale = obsoleto and not _disk_stale_logged
        if log_stale:
            _disk_stale_logged = True

    if disparar:
        try:
            threading.Thread(target=_refresh_disk, args=(psutil_mod,),
                             name="sysinfo-disco", daemon=True).start()
        except Exception as exc:
            # Without returning the slot here, a single "can't start new thread"
            # would freeze the disk metrics for the rest of the process's life.
            with _disco_lock:
                _disk_in_flight = max(_disk_in_flight - 1, 0)
                _disk_expires = 0.0
            logger.warning("Nao foi possivel iniciar a coleta de disco: %s", exc)

    if obsoleto:
        if log_stale:
            logger.warning(
                "Metricas de disco obsoletas (ultima coleta ha %.0fs, teto %.0fs): "
                "reportando desconhecido em vez do valor antigo. A pasta de artefatos "
                "pode estar numa unidade de rede que parou de responder.",
                age, DISK_MAX_AGE_S,
            )
        return {}
    return atual


def _resetar_caches() -> None:
    """Resets all of the module's memoized state to its starting point.

    Exists for the TESTS. Without it, the first test that monkeypatches
    `_read_cgroup_value` or `psutil.disk_usage` leaves the result stored in the
    globals and contaminates all the following ones in the same process — even
    those that have nothing to do with sysinfo, because `_get_dynamic_metrics` is
    called from several places. Nothing in production calls this.
    """
    global _cache_ram_total, _cache_ram_total_em, _cached_cpu_cores, _cached_cpu_cores_at
    global _disk_value, _disk_expires, _disk_in_flight
    global _disk_collected_at, _disk_started_at, _disk_stale_logged
    global _PROC, _PROC_FAILED
    _cache_ram_total = None
    _cache_ram_total_em = _NEVER_READ
    _cached_cpu_cores = None
    _cached_cpu_cores_at = _NEVER_READ
    with _disco_lock:
        _disk_value = {}
        _disk_expires = 0.0
        _disk_in_flight = 0
        _disk_collected_at = _NEVER_READ
        _disk_started_at = _NEVER_READ
        _disk_stale_logged = False
    _PROC = None
    _PROC_FAILED = False


def _get_dynamic_metrics() -> dict:
    """Collects dynamic system metrics (free RAM, free disk).

    Prefers cgroup limits inside containers.

    The disk comes from the cache (`_disk_metrics`); RAM is read on the spot,
    because it is a cheap read — `GlobalMemoryStatusEx`, /proc/meminfo or a local
    cgroup file, nothing that can get stuck on a network drive — and it is precisely
    the metric the operator expects to see move in the panel while a heavy job runs.
    """
    try:
        import psutil
    except ImportError:
        return {}

    metrics = dict(_disk_metrics(psutil))
    try:
        cgroup_avail = _get_cgroup_ram_available()
        if cgroup_avail is not None:
            metrics["ram_available_gb"] = round(cgroup_avail / (1024**3), 1)
        else:
            metrics["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 1)
    except Exception as exc:
        logger.debug("Falha ao coletar RAM disponivel: %s", exc)
    return metrics


# ── Process's own consumption ────────────────────────────────────────────────
# psutil.Process().cpu_percent(interval=None) returns the average since the
# PREVIOUS call on the same object — that is why the Process is created once and
# kept. Recreating it on every tick would make every reading return 0.0.
_PROC = None
_PROC_FAILED = False


def _process() -> object | None:
    global _PROC, _PROC_FAILED
    if _PROC_FAILED:
        return None
    if _PROC is None:
        try:
            import psutil
            _PROC = psutil.Process()
            _PROC.cpu_percent(interval=None)  # aquece o baseline
        except Exception as exc:
            _PROC_FAILED = True
            logger.debug("psutil.Process indisponivel — metricas do processo desligadas: %s", exc)
            return None
    return _PROC


def process_metrics() -> dict:
    """CPU%, RSS and threads of the executor process. Non-blocking.

    A single measurement covers the whole load: the workers are coroutines and the
    flow engine uses `asyncio.to_thread` on the process's own ThreadPoolExecutor
    (main.py), so there are no children to add up.

    `cpu_pct` may exceed 100 (sum over threads); `cpu_pct_norm` divides by the
    number of cores to fit a 0 to 100 bar. Returns {} if psutil is missing
    or fails — the panel shows "—" instead of bringing down the tick.
    """
    proc = _process()
    if proc is None:
        return {}
    try:
        import psutil
        cpu = proc.cpu_percent(interval=None)
        mem = proc.memory_info()
        cores = _get_cgroup_cpu_cores() or psutil.cpu_count(logical=True) or 1
        return {
            "cpu_pct":      round(cpu, 1),
            "cpu_pct_norm": round(min(cpu / cores, 100.0), 1),
            "rss_mb":       round(mem.rss / (1024**2), 1),
            "threads":      proc.num_threads(),
            "cpu_cores":    cores,
        }
    except Exception as exc:
        # The same C binding that breaks disk_usage on Anaconda/Windows can
        # show up here. Degrading silently is better than one traceback per
        # second in the log file.
        logger.debug("Falha ao coletar metricas do processo: %s", exc)
        return {}
