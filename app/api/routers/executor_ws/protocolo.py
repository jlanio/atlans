# app/api/routers/executor_ws/protocolo.py
"""
Sanitization and limits of the executor WS protocol: required fields,
payload ceilings and per-connection rate limit. The vocabulary (version, types,
reserved stats keys, system_info fields) is that of flow/utils/protocolo_ws.py;
the node_event ceiling and reduction, those of flow/utils/publisher/reducao.py
(see `_serialize_node_event` in resultados.py).
"""
import json
import time

from app.core.utils.logger import get_logger

from app.core.executor_connections import _DEFAULT_CAPACITY, executor_registry
from flow.utils.protocolo_ws import (
    STATS_CONTROL_DROPPED,
    STATS_TRUNCATED,
    SYSTEM_INFO_BOOLEANS,
    SYSTEM_INFO_NUMBERS,
    SYSTEM_INFO_TEXTS,
    shrink_stats,
)

logger = get_logger(__name__)


# Rate limit per executor (coarse sliding window). Does not drop the connection:
# a legitimate workflow with high fan-out emits bursts, and killing the socket
# would fail the whole run. The excess is dropped and one aggregated WARNING
# line is emitted per window.
#
# TWO node_event STRIPS on purpose. A single 200/s ceiling treated a node's
# `completed` as if it were a log line and DROPPED lifecycle events — a total
# and permanent drop, with no re-enqueuing. The executor drains the event queue
# in a burst (main.py → _drain_pending_events), so a workflow of ~300
# trivial nodes emits 600+ events in 2-3s and goes over the ceiling: the
# frontend loses the `completed` of several nodes and, since `completeExecution`
# only demotes a stuck node when the run is 'cancelled', the user sees a run
# "concluído com sucesso" (completed successfully) with half the graph spinning
# forever — and reopening the run reproduces the same state, because the
# history is the same truncated source.
# The lifecycle volume is bounded by the workflow's number of nodes, not by the
# producer's whim; the high ceiling remains a hard limit against abuse, just out
# of reach of honest traffic.
_NODE_EVENT_RATE_LIMIT = 200            # stdout/debug e futuros eventos de log

_NODE_EVENT_LIFECYCLE_RATE_LIMIT = 2000  # node started/completed/failed

_RATE_WINDOW = 1.0

# job_result is also rate-limited, but with its own ceiling: dropping one of
# them leaves the run hanging in 'running' until the watchdog, so the value must
# be WAY above honest traffic (one job_result per job; the executor's default is
# EXECUTOR_MAX_CONCURRENT=4). It exists only to plug the flood loop.
_JOB_RESULT_RATE_LIMIT = 50

# sync_event was the ONLY protocol type with no rate limit and no byte ceiling:
# the emitter sends one event per file transition, so a GeoSync of thousands of
# files generated thousands of messages that froze the loop along with the
# workflows' node_events. The ceiling is high because the UI uses these events
# for the progress bar; the terminal ones are exempt (see `_sync_event_allowed`).
_SYNC_EVENT_RATE_LIMIT = 300

_MAX_SYNC_EVENT_BYTES = 16 * 1024

# Event that closes the sync CYCLE — one per execution (sync/manager:
# `sync_complete` is emitted only once at the end). Dropping it in a burst would
# leave the progress bar stuck at 99% forever, so it is exempt from the rate limit.
#
# `sync_error` and `conflict_detected` are NOT in here: despite the name, the
# executor emits them INSIDE the per-dataset/file loops. With MinIO down or an
# expired credential, a GeoSync of 3000 files becomes 3000 exempt messages —
# exactly the burst the rate limit exists to contain, and which also fills the
# connection's queue and hampers the node_events' coalescing.
_SYNC_TERMINAL_EVENTS = frozenset({"sync_complete"})

# OWN bucket for the problem events (one per file). Separate from the progress
# bucket on purpose: an error burst must not consume the `file_uploaded` quota
# (the bar would stop moving) nor the other way around. The ceiling is loose
# enough for the UI to show a dataset's first errors and tight enough for a
# mass failure not to turn into a flood.
_SYNC_PROBLEM_EVENTS = frozenset({"sync_error", "conflict_detected"})

_SYNC_PROBLEM_RATE_LIMIT = 50

# ── job_result byte ceilings ─────────────────────────────────────────────────
# The honest executor already self-limits to 16 MB and truncates `stats`
# (executor/connection.py), but the threat model here is the COMPROMISED
# executor — for which its self-limiting is worth nothing. The job_result's
# `error` and `stats` went RAW to three durable destinations: the `run_results`
# queue (no TTL), the `workflow:{run}:history` history (ceiling of 5000
# ENTRIES, not bytes) and Postgres (WorkflowRun.error_message is unbounded Text
# and node_stats is JSON). 15 MB per message, in a loop, filled the same Redis
# that holds executor presence and the cert blacklist.
_MAX_JOB_ERROR_CHARS = 8 * 1024

# `stats` carries the ResponseNode's inline body (__response__), whose limit on
# the executor side is WEBHOOK_RESPONSE_INLINE_LIMIT (default 1 MB) — above that
# it uploads to MinIO and sends only the body_ref. 4 MB leaves slack for the
# inline body + per-node stats of a large workflow and still cuts 4x off the
# frame ceiling.
_MAX_JOB_STATS_BYTES = 4 * 1024 * 1024

def _is_lifecycle(msg: dict) -> bool:
    """True for a node_event that carries GRAPH STATE (started/completed/failed).

    A missing `kind` counts as lifecycle: it is the producer's default
    (flow/utils/publisher/events.publish_event). Erring on this side is right —
    the cost of treating a log as lifecycle is taking up a slot; the cost of the
    reverse is a node spinning forever on the user's canvas.
    """
    kind = msg.get("kind")
    return kind is None or kind == "lifecycle"

def _is_telemetry(msg_type: str, msg: dict) -> bool:
    """True for what can be lost without lying about the system's state.

    These are the `sync_event`s (GeoSync progress, which the executor emits per
    file) and the stdout/debug `node_event`s. Everything else — lifecycle and
    job_result — carries state the UI cannot rebuild on its own.
    """
    if msg_type == "sync_event":
        # `sync_complete` is emitted ONCE per cycle and closes the GeoSync
        # progress bar. Sacrificing it here would leave the bar stuck at 99%
        # forever — the same reason it is already exempt from the rate limit
        # (see `_SYNC_TERMINAL_EVENTS`). The two policies must agree.
        return msg.get("event") not in _SYNC_TERMINAL_EVENTS
    return msg_type == "node_event" and not _is_lifecycle(msg)

# Required fields per message type. Missing ones → explicit error to the
# executor instead of the old silent drop.
_REQUIRED_FIELDS: dict[str, set[str]] = {
    "job_result": {"job_id", "status"},
    "node_event": {"run_id", "node"},
    "capacity":   {"queued", "running", "max_concurrent", "max_queue"},
    "ack":        {"job_id"},
    "sync_event": {"event"},
    "inventario": {"ativos"},
}

def _missing_fields(msg_type: str, msg: dict) -> list[str]:
    """Returns the required fields missing from the payload. [] if OK."""
    req = _REQUIRED_FIELDS.get(msg_type)
    if not req:
        return []
    return [f for f in req if msg.get(f) is None]

# ── `capacity` sanitization ──────────────────────────────────────────────────
# The fields went RAW to the registry. An executor sending {"queued": {"n": 0}}
# made `_resolve_candidates` (workflow_execution_service) blow up with an
# UNHANDLED TypeError in `cap["running"] + cap["queued"]` → 500 on POST /execute
# for the ENTIRE platform while that executor was online. The defense has to be
# here, at the entrance: the service trusts the registry's format.

def _coerce_count(value, field: str, errors: list[str]) -> int | None:
    """Coerces a capacity counter to int >= 0. Accumulates the reason in `errors`."""
    # bool is a subclass of int — True would silently become 1.
    if isinstance(value, bool):
        errors.append(f"{field}: booleano não é um contador válido")
        return None
    if isinstance(value, int):
        n = value
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            errors.append(f"{field}: valor não finito")
            return None
        n = int(value)
    elif isinstance(value, str):
        try:
            n = int(value.strip())
        except ValueError:
            errors.append(f"{field}: string não numérica")
            return None
    else:
        errors.append(f"{field}: tipo {type(value).__name__} não é numérico")
        return None
    if n < 0:
        errors.append(f"{field}: negativo ({n})")
        return None
    return n

def _coerce_gauge(value) -> float | None:
    """Coerces an informational metric (free disk/RAM) to float >= 0, or None.

    Unlike the counters, a bad value here does not invalidate the message — it
    just disappears from the payload. Nobody decides dispatch based on these fields.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")) or f < 0:
        return None
    return round(f, 3)

def _sanitize_capacity(executor_id: str, msg: dict) -> tuple[dict | None, list[str]]:
    """Validates/coerces the capacity payload and applies the clamp of the database limits.

    Capacity is SELF-DECLARED. The clamp closes the CEILINGS: without it against
    Executor.max_concurrent_jobs and max_queue_size, an executor announced
    max_queue=10**9 and `is_full` never fired — an UNLIMITED drain of the
    default pool. With the clamp the drain becomes bounded (the record's
    max_concurrent + max_queue).

    WHAT THE CLAMP DOES *NOT* CLOSE — and cannot close here: `queued` and
    `running` remain raw numbers from the executor. We do not clamp these two
    DOWNWARD on purpose: reducing a declared load would only help whoever lies
    and would hurt whoever, after a limit is lowered in the database, still has
    jobs in flight above the new ceiling. In dispatch ORDERING, lying downward
    does not pay off: the load used is the one counted by the server — the
    host's `pending`/`running` runs in the database (`_executor_states` in
    workflow_execution_service) —, and the declared one only serves to say
    "full". Announcing zero does not put the executor ahead of anyone. The
    `is_full` in `send_job` still looks only at the declared one: whoever lies
    downward accumulates up to the clamped ceiling, and the boundary that holds
    this is administrative (only an admin puts a machine in the default pool).
    """
    errors: list[str] = []
    queued         = _coerce_count(msg.get("queued", 0), "queued", errors)
    running        = _coerce_count(msg.get("running", 0), "running", errors)
    max_concurrent = _coerce_count(msg.get("max_concurrent", 0), "max_concurrent", errors)
    max_queue      = _coerce_count(msg.get("max_queue", 0), "max_queue", errors)
    if errors:
        return None, errors

    conn = executor_registry.get(executor_id)
    limit_concurrent = conn.max_concurrent_limit if conn else _DEFAULT_CAPACITY["max_concurrent"]
    limit_queue      = conn.max_queue_limit if conn else _DEFAULT_CAPACITY["max_queue"]

    capacity = {
        "queued":         queued,
        "running":        running,
        "max_concurrent": min(max_concurrent, limit_concurrent),
        "max_queue":      min(max_queue, limit_queue),
        "disk_free_gb":     _coerce_gauge(msg.get("disk_free_gb")),
        "ram_available_gb": _coerce_gauge(msg.get("ram_available_gb")),
    }
    if max_concurrent > limit_concurrent or max_queue > limit_queue:
        logger.warning(
            "Executor '%s' declarou capacidade acima do registro "
            "(max_concurrent=%d>%d, max_queue=%d>%d) — clampada.",
            executor_id, max_concurrent, limit_concurrent, max_queue, limit_queue,
        )
    # A declared load above its own ceilings is incoherent (executor bug or forged
    # payload). We do not change the value — see the docstring —, but the
    # operator needs the signal: it is the only trace of lying capacity.
    if running > limit_concurrent or queued > limit_queue:
        logger.warning(
            "Executor '%s' declarou carga incoerente com o registro "
            "(running=%d>%d, queued=%d>%d) — mantida como reportada.",
            executor_id, running, limit_concurrent, queued, limit_queue,
        )
    return capacity, []

# ── `system_info` sanitization ───────────────────────────────────────────────
# It went raw to the JSONB column. `"system_info": "pwn"` (a truthy string) made
# ExecutorOut.from_model raise ValidationError → PERMANENT 500 on
# GET /executores/ and /{id}, until someone fixed the row by hand. Volume
# variant: 15 MB persisted per reconnection. Any user who can create a
# dedicated executor gets here — they don't need to be an admin. The allowlist
# (the fields the executor sends, by type) is the protocol's: SYSTEM_INFO_* in
# flow/utils/protocolo_ws.py.
_SYSTEM_INFO_STR_MAX = 200

_SYSTEM_INFO_MAX_BYTES = 8192

def _sanitize_system_info(executor_id: str, raw) -> dict | None:
    """Applies allowlist + coercion + size ceiling. None if nothing is usable."""
    if not isinstance(raw, dict):
        logger.warning(
            "Executor '%s' enviou system_info do tipo %s (esperado objeto) — descartado.",
            executor_id, type(raw).__name__,
        )
        return None

    clean: dict = {}
    for key in SYSTEM_INFO_TEXTS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            clean[key] = value.strip()[:_SYSTEM_INFO_STR_MAX]
    for key in SYSTEM_INFO_NUMBERS:
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value != value or value in (float("inf"), float("-inf")) or value < 0:
            continue
        clean[key] = round(float(value), 2)
    for key in SYSTEM_INFO_BOOLEANS:
        value = raw.get(key)
        if isinstance(value, bool):
            clean[key] = value

    dropped = set(raw) - set(clean)
    if dropped:
        logger.warning(
            "Executor '%s': campos de system_info fora da allowlist ou inválidos descartados: %s",
            executor_id, sorted(dropped)[:20],
        )

    if not clean:
        return None

    # Final ceiling: the allowlist already limits, but belt-and-braces protects
    # against any new field added without an explicit limit in the future.
    if len(json.dumps(clean)) > _SYSTEM_INFO_MAX_BYTES:
        logger.warning(
            "Executor '%s': system_info excedeu %d bytes mesmo após allowlist — descartado.",
            executor_id, _SYSTEM_INFO_MAX_BYTES,
        )
        return None
    return clean

# ── `executor_version` sanitization ──────────────────────────────────────────
# Goes to the VARCHAR(20) column that the executors screen shows. Out of format
# it is discarded, not cut — a truncated "2.3.1-beta+build.1234" is a different
# version —, and the database keeps the last good version. Without the check, a
# long value would overflow the column in the middle of the receive loop and
# bring down the connection.
_EXECUTOR_VERSION_MAX = 20

def _sanitize_executor_version(executor_id: str, raw) -> str | None:
    """The version declared in the handshake, or None if missing or invalid."""
    if raw is None:
        return None
    ver = raw.strip() if isinstance(raw, str) else ""
    if ver and len(ver) <= _EXECUTOR_VERSION_MAX and ver.isprintable():
        return ver
    # Cuts BEFORE the repr: the frame may be megabytes.
    amostra = repr(raw[:40]) if isinstance(raw, str) else type(raw).__name__
    logger.warning(
        "Executor '%s' enviou executor_version inválida (%s) — descartada.",
        executor_id, amostra,
    )
    return None

# ── Rate limit per executor ──────────────────────────────────────────────────
# (executor_id, bucket) → {"window_start": monotonic, "count": int, "suppressed": int}.
# Cleared in the handler's finally (see `agent_websocket`). Separate buckets so
# that a debug burst does not consume the lifecycle quota nor the job_result one.
_rate_state: dict[tuple[str, str], dict] = {}

def _rate_allowed(executor_id: str, bucket: str, limit: int) -> bool:
    """Janela sliding por (executor, bucket). False = descartar a mensagem."""
    now = time.monotonic()
    key = (executor_id, bucket)
    state = _rate_state.get(key)
    if state is None or (now - state["window_start"]) >= _RATE_WINDOW:
        if state is not None and state["suppressed"]:
            logger.warning(
                "Executor '%s': %d mensagem(ns) de '%s' descartadas por rate limit (>%d/%.0fs).",
                executor_id, state["suppressed"], bucket, limit, _RATE_WINDOW,
            )
        _rate_state[key] = {"window_start": now, "count": 1, "suppressed": 0}
        return True
    if state["count"] >= limit:
        state["suppressed"] += 1
        return False
    state["count"] += 1
    return True

def _drop_rate_state(executor_id: str) -> None:
    """Forgets all of an executor's buckets (called on unregister)."""
    for key in [k for k in _rate_state if k[0] == executor_id]:
        _rate_state.pop(key, None)

def _node_event_allowed(executor_id: str, msg: dict) -> bool:
    """node_event rate limit, with a separate strip for lifecycle.

    A missing `kind` counts as lifecycle: it is the producer's default
    (flow/utils/publisher/events.publish_event). An adversary who omits the field
    falls into the high strip, which is accepted on purpose — the per-event byte
    ceiling still applies and 2000 events/s of 64 KB is already a hard limit.
    """
    if _is_lifecycle(msg):
        return _rate_allowed(executor_id, "node_event:lifecycle", _NODE_EVENT_LIFECYCLE_RATE_LIMIT)
    return _rate_allowed(executor_id, "node_event:log", _NODE_EVENT_RATE_LIMIT)

def _sync_event_allowed(executor_id: str, msg: dict) -> bool:
    """sync_event rate limit, in three strips.

    The volume comes from the per-file transitions (`file_uploading`/`file_uploaded`):
    in a dataset with thousands of files that is thousands of messages. Dropping
    `sync_complete` in the burst, however, would leave the UI's progress bar stuck
    forever — it is the only one that is truly one-per-cycle and the only exempt one.

    `sync_error`/`conflict_detected` are per FILE: exempting them brought back
    the entire flood the ceiling exists to contain (MinIO down = one event per
    file in the dataset). They get their own, tighter bucket.
    """
    evento = msg.get("event")
    if evento in _SYNC_TERMINAL_EVENTS:
        return True
    if evento in _SYNC_PROBLEM_EVENTS:
        return _rate_allowed(executor_id, "sync_event:problema", _SYNC_PROBLEM_RATE_LIMIT)
    return _rate_allowed(executor_id, "sync_event", _SYNC_EVENT_RATE_LIMIT)

def _cap_job_result(executor_id: str, msg: dict) -> tuple[dict, str]:
    """Enforces the byte ceiling on `error` and `stats` at the job_result's ENTRANCE.

    Returns a shallow copy with both fields already limited, so that ALL the
    destinations (ephemeral Redis, the `run_results` queue, `workflow:{run}:history`,
    webhook_response and, via the consumer, the `error_message`/`node_stats`
    columns) use the same contained payload. The truncation of `stats` is the
    protocol's (`shrink_stats` in flow/utils/protocolo_ws.py), the same one the
    executor applies before sending: first it drops the per-node stats while
    preserving the control keys; if even those don't fit, it drops everything
    and marks `__control_dropped__`, which the webhook handler already knows how
    to turn into an explicit error instead of leaving the BRPOP to time out.

    PERF: ALSO returns the already-serialized `stats` JSON. Measuring the
    ceiling requires a `json.dumps` of up to 4 MB; the caller needed the same
    JSON for the `run_results` queue and redid the dumps — pure, synchronous CPU,
    with the worker's whole event loop stopped. Serializing once and reusing it
    halves that without changing any limit.
    """
    capped = dict(msg)

    error = capped.get("error")
    if error is not None:
        # A compromised executor sends whatever it wants here: dict/list went
        # whole into `error_message` (Text, unbounded in Postgres).
        if not isinstance(error, str):
            error = repr(error)
        if len(error) > _MAX_JOB_ERROR_CHARS:
            logger.warning(
                "Executor '%s': campo 'error' do job_result com %d chars (job=%s) "
                "excede o teto de %d — truncado.",
                executor_id, len(error), capped.get("job_id"), _MAX_JOB_ERROR_CHARS,
            )
            error = error[:_MAX_JOB_ERROR_CHARS] + "…[truncado pelo servidor]"
        capped["error"] = error

    stats = capped.get("stats")
    if stats is None:
        return capped, "{}"

    if not isinstance(stats, dict):
        logger.warning(
            "Executor '%s': 'stats' do job_result veio como %s (esperado objeto) "
            "— descartado.", executor_id, type(stats).__name__,
        )
        capped["stats"] = {}
        return capped, "{}"

    try:
        stats_json = json.dumps(stats, default=str)
    except (TypeError, ValueError):
        # Recursive/non-serializable: the consumer would blow up at the
        # run_results json.dumps and the message would become a silent error.
        logger.warning(
            "Executor '%s': 'stats' do job_result não é serializável — descartado.",
            executor_id,
        )
        capped["stats"] = {STATS_TRUNCATED: True, STATS_CONTROL_DROPPED: True}
        return capped, json.dumps(capped["stats"])

    size = len(stats_json)
    if size > _MAX_JOB_STATS_BYTES:
        # The yardstick here is only `stats`, against the ceiling of what the server stores.
        reduced, stats_json, preservou = shrink_stats(
            stats, size, _MAX_JOB_STATS_BYTES, lambda s: json.dumps(s, default=str),
        )
        if preservou:
            logger.warning(
                "Executor '%s': 'stats' do job_result com %d bytes (job=%s) excede o "
                "teto de %d — stats por-nó removidos, chaves de controle preservadas.",
                executor_id, size, capped.get("job_id"), _MAX_JOB_STATS_BYTES,
            )
        else:
            logger.warning(
                "Executor '%s': 'stats' do job_result com %d bytes (job=%s) excede o "
                "teto de %d mesmo preservando as chaves de controle — descartado.",
                executor_id, size, capped.get("job_id"), _MAX_JOB_STATS_BYTES,
            )
        capped["stats"] = reduced

    return capped, stats_json
