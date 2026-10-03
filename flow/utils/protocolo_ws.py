# flow/utils/protocolo_ws.py
"""
Vocabulary of the executor ↔ server WebSocket protocol.

Both sides import from here: the executor (executor/connection.py) and the server
(app/api/routers/executor_ws_router.py and the
app/api/routers/executor_ws/ package). `app` and `executor` never import each
other; what belongs to both lives in `flow/`, which ships in both images. The
node_event ceiling and reduction live next to the event, in
flow/utils/publisher/reducao.py.

Changing a value here is changing the wire. Server and executors are updated at
different times (the executor runs on the customer's machine), so every value
must remain understood by the old side: a new type is only safe once the
receiving side already knows it.
"""
from typing import Callable

# ── Version ──────────────────────────────────────────────────────────────────
# The one the executor declares in the handshake and the ones the server accepts
# (outside them: `error` unsupported_protocol_version and close 4426). Bump major
# only on a breaking change — and the server starts accepting both before any
# executor declares the new one.
PROTOCOL_VERSION = "1.0"

SUPPORTED_PROTOCOL_VERSIONS = frozenset({PROTOCOL_VERSION})

# ── Message types ────────────────────────────────────────────────────────────
# Executor → server: what the server's receive loop handles
# (executor_ws_router.py). A type not listed here has no effect there.
EXECUTOR_TYPES = frozenset({
    "handshake", "heartbeat", "capacity", "job_result", "node_event",
    "sync_event", "ack", "inventario",
})

# The server's response to a message it refused, with `reason` (invalid
# JSON, missing required field, invalid capacity, message before the
# handshake, unsupported version) and the detail of the reason. Informational
# only: the refused message has already been discarded, and the executor just
# logs it.
ERROR_TYPE = "error"

# Server → executor. This is the executor's allowlist: the rest is discarded
# before any processing. `control` and `cancel` additionally require an Ed25519
# signature (_SIGNED_SERVER_MESSAGES in executor/connection.py).
SERVER_TYPES = frozenset({"job", "drive_event", "control", "cancel", ERROR_TYPE})

# ── Reserved keys of the job_result's `stats` ─────────────────────────────────
# Control: they survive truncation, which only drops the per-node stats. Without
# `__response__` the synchronous webhook's BRPOP hangs until the timeout; the
# others feed artifacts, metrics and pins.
STATS_CONTROL_KEYS = (
    "__response__",
    "__artifacts__",
    "__metrics__",
    "__updated_pinned_outputs__",
)

# Truncation markers. `__control_dropped__` says not even the control keys
# fit: the server turns this into an explicit error for the synchronous
# webhook, instead of letting BRPOP wait for the timeout.
STATS_TRUNCATED = "__truncated__"
STATS_ORIGINAL_SIZE = "__original_size__"
STATS_CONTROL_DROPPED = "__control_dropped__"


def shrink_stats(
    stats: dict,
    original_size: int,
    teto: int,
    serializar: Callable[[dict], str],
) -> tuple[dict, str, bool]:
    """Truncates the `stats` of a job_result that exceeded `teto`, in two steps.

    1. Drops the per-node stats and preserves STATS_CONTROL_KEYS;
    2. if not even those fit, drops everything and sets STATS_CONTROL_DROPPED.

    Both sides apply it, each with its own ceiling and its own yardstick: the
    executor measures the whole message against the WS frame (`_dumps_result`); the
    server measures only `stats`, against the ceiling of what it stores
    (`_cap_job_result`). That is why `serializar` belongs to the caller: it receives
    the reduced stats and returns the JSON that is measured against `teto`.

    `original_size` goes into STATS_ORIGINAL_SIZE in both steps — it is the
    size before any cut.

    Returns `(stats_reduzidos, json_medido, controle_preservado)`.
    """
    mantidas = (
        {k: stats[k] for k in STATS_CONTROL_KEYS if k in stats}
        if isinstance(stats, dict) else {}
    )
    reduced = {**mantidas, STATS_TRUNCATED: True, STATS_ORIGINAL_SIZE: original_size}
    try:
        serializado = serializar(reduced)
    except (TypeError, ValueError):
        # Non-serializable (or recursive) control key: counts as large.
        serializado = None
    if serializado is not None and len(serializado) <= teto:
        return reduced, serializado, True

    reduced = {
        STATS_TRUNCATED: True,
        STATS_ORIGINAL_SIZE: original_size,
        STATS_CONTROL_DROPPED: True,
    }
    return reduced, serializar(reduced), False


# ── Handshake `system_info` ──────────────────────────────────────────────────
# The executor collects it (`_collect_system_info` in executor/sysinfo.py) and the
# server persists only these fields, each coerced to its group's type
# (`_sanitize_system_info` in app/api/routers/executor_ws/protocolo.py). A new
# field in the executor that is not added here is discarded by the server — with a
# WARNING on every connection.
SYSTEM_INFO_TEXTS = ("hostname", "os_name", "os_version")

SYSTEM_INFO_NUMBERS = ("cpu_cores", "ram_total_gb", "disk_total_gb")

SYSTEM_INFO_BOOLEANS = ("container",)
