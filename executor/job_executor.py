# executor/job_executor.py
"""
The executor's job runner.

Responsibilities:
  1. Validate the job (job_validator.validate_job)
  2. Decrypt the payload in memory (executor/crypto.py)
  3. Run flow/ locally with a timeout
  4. Clear sensitive references after execution
  5. Return the result (dict) to be sent to the server
"""
import asyncio
import json
import logging
import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse

from executor import config
from executor.crypto import decrypt_job_payload, load_private_key
from executor.job_validator import JobValidationError, validate_job

logger = logging.getLogger(__name__)

# ─── Flow engine import setup (once, at module import) ────────────────────────
# The executor runs in a separate process; flow/ is in the parent directory.
# Before, the path was adjusted and the import was done inside _run_workflow —
# that caused a re-scan of the node registry (~60 modules via importlib) on
# every job.
#
# Doing it here at top level, the cost is paid once at executor startup and every
# subsequent job reuses Python's module cache.
_AGENT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AGENT_ROOT not in sys.path:
    sys.path.insert(0, _AGENT_ROOT)

# ARTIFACT_DIR must be in the env BEFORE importing flow/nodes (the local artifact
# fallback in flow/utils/artifact_helpers.py reads the variable). setdefault
# preserves a value already set via docker-compose.
os.environ.setdefault("ARTIFACT_DIR", config.ARTIFACTS_DIR)

# Flow engine imports — done once at executor startup instead of per job.
from flow.executor import WorkflowExecutor  # type: ignore  # noqa: E402
from flow.executor.result_helpers import collect_artifacts, collect_response  # noqa: E402
from executor.event_publisher import ExecutorEventPublisher  # noqa: E402

# Private key loaded once at module initialization
_agent_private_key = None

# SEC: the anti-replay cache (`_nonce_seen`, in job_validator) is a check-and-set
# on a module-level OrderedDict. While validation ran on the event loop, the loop
# itself serialized that pair of operations for free; now it runs in the thread
# pool, and without this lock two concurrent jobs could interleave the check and
# the registration of the SAME nonce and both pass — a replay accepted. The cost
# is nil: it is off the data path and validation takes milliseconds.
_VALIDATION_LOCK = threading.Lock()

# Pool DEDICATED to the control plane (signature validation + envelope
# decryption). It is NOT the loop's default pool, which is where the nodes run —
# including PythonScript, which executes arbitrary user code.
#
# The reason is concrete: `asyncio.to_thread` cancels NOTHING. A PythonScript with
# `while True: pass` (which passes validate_code_ast) blows the node's
# `asyncio.wait_for`, frees the job's slot and leaves the THREAD alive forever.
# A few runs like that take up all the workers of the default pool; if
# validation lived there, the executor could no longer even ACCEPT or REJECT
# a job — no node_event, no job_result, the run hanging in "running" until the
# server marks it as orphaned. Here, receiving work stays immune to a stuck
# node.
#
# Two workers are enough: validation takes milliseconds and is serialized by
# _VALIDATION_LOCK anyway.
_CONTROL_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="atlas-ctrl")


def _validar_e_descriptografar(message: dict) -> dict:
    """Ed25519 signature + anti-replay + decryption, off the event loop.

    Runs entirely in a thread (see `execute_job`). Worth it even with the GIL:
    `cryptography`'s `verify`/`decrypt` are OpenSSL and RELEASE the GIL, so the
    work really leaves the loop. Before, a job with a large definition
    (pre-resolved sub-workflows + pinned_outputs) left the executor silent for
    hundreds of milliseconds BEFORE the first node_event — and, with jobs in
    bursts, the pauses added up ahead of the heartbeat and of the events of the
    jobs already in progress.
    """
    with _VALIDATION_LOCK:
        validate_job(message)
    if _agent_private_key is None:
        raise RuntimeError("Chave privada não inicializada. Chame init_private_key() no startup.")
    return decrypt_job_payload(message, _agent_private_key)


def init_private_key():
    """Loads the executor's X25519 private key. Must be called at startup.

    Uses `load_private_key` (read-only): if the enrollment key is gone, startup
    fails loudly with instructions to redo the enroll instead of generating a new
    pair — which would make the executor come up "online" and fail 100% of jobs.
    """
    global _agent_private_key
    _agent_private_key = load_private_key(
        key_b64=config.EXECUTOR_PRIVATE_KEY,
        key_path=config.EXECUTOR_PRIVATE_KEY_PATH,
    )
    logger.info("Chave privada X25519 do executor carregada.")


def _error_result(job_id, run_id, error: str, category: str, stats: dict | None = None) -> dict:
    """Builds the failure result with the taxonomy (category + retryable).

    `stats` carries what had already run before the failure (partial node_stats +
    __metrics__). Without it the server overwrote node_stats with {} — the panel
    lost the nodes that had run, workflow_run_metrics/node_run_metrics got no
    row at all and, because the UsageDaily upsert lives inside
    _persist_metrics, no failure was counted: the dashboard showed a permanent
    0% error rate.
    """
    from flow.utils.error_taxonomy import is_retryable
    return {
        "job_id": job_id, "run_id": run_id, "status": "error", "output": None,
        "stats": stats or {},
        "error": error, "error_category": category, "retryable": is_retryable(category),
    }


# ── Stats payload ceilings ───────────────────────────────────────────────────
# Limit here, at the SOURCE, not at serialization time. `_dumps_result` measured
# the size by doing `json.dumps` of the ENTIRE job_result (up to 16 MB) — and up
# to three times, when it overflowed — inside the event loop, precisely at the
# moment the workflow finishes: the heartbeat got delayed, the other jobs'
# node_events stopped going up and the `cancel` the user had just clicked was
# not read. With the payload bounded by construction, that path becomes what it
# should have been all along: a safety net that in practice never fires.
#
# The control keys (__response__/__artifacts__/__metrics__/
# __updated_pinned_outputs__) are NOT subject to the cut: without __response__
# the synchronous webhook's BRPOP gets stuck, and the others feed metrics and pins.
_MAX_NODE_STAT_BYTES  = 8 * 1024
_MAX_NODE_STATS_BYTES = 4 * 1024 * 1024
_MAX_STAT_ERROR_CHARS = 2_000
# REDUCED ceiling of columns per port when the stat exceeds _MAX_NODE_STAT_BYTES.
# The source already cuts at MAX_COLUMNS (200 — flow/executor/utils.py); dropping
# the rest all at once was all-or-nothing: the wider the table, the more certain
# the drop, and the editor was left without column suggestions exactly where
# they are worth the most. The first 50 fit comfortably under the ceiling and
# still feed the suggestions.
_MAX_STAT_COLUMNS_PER_PORT = 50
# Fields without which the node_run_metrics row no longer serves the panel.
_STAT_ESSENTIAL_FIELDS = (
    "node_name", "duration_ms", "status", "cache_hit", "started_at",
    "input_features", "output_features",
)


def _json_size(obj) -> int:
    """Tamanho serializado aproximado, em bytes. `default=str` nunca levanta."""
    try:
        return len(json.dumps(obj, default=str))
    except Exception:
        return _MAX_NODE_STAT_BYTES + 1  # unreadable = treat as too large


def _shrink_node_stat(stat: dict) -> dict:
    """Degrades a node's stat in steps, from the cheapest cut to the crudest.

    Order: (1) error message truncated; (2) each output_columns list truncated
    to the first _MAX_STAT_COLUMNS_PER_PORT; (3) output_columns dropped;
    (4) only the essential fields. Each step re-measures and stops as soon as it
    fits — dropping the columns entirely, which used to be the first cut,
    became the second-to-last resort: they feed the editor's column suggestions.
    The cut is flagged with the stat's `__truncated__`, like the others; the
    truncated list does NOT get a marker item (same rule as `_output_columns`:
    the UI would render the marker as a clickable suggestion).
    """
    reduzido = dict(stat)
    reduzido["__truncated__"] = True

    erro = reduzido.get("error")
    if isinstance(erro, str) and len(erro) > _MAX_STAT_ERROR_CHARS:
        reduzido["error"] = erro[:_MAX_STAT_ERROR_CHARS] + "…[truncado]"
        if _json_size(reduzido) <= _MAX_NODE_STAT_BYTES:
            return reduzido

    colunas = reduzido.get("output_columns")
    if isinstance(colunas, dict) and any(
        isinstance(lista, list) and len(lista) > _MAX_STAT_COLUMNS_PER_PORT
        for lista in colunas.values()
    ):
        reduzido["output_columns"] = {
            porta: lista[:_MAX_STAT_COLUMNS_PER_PORT] if isinstance(lista, list) else lista
            for porta, lista in colunas.items()
        }
        if _json_size(reduzido) <= _MAX_NODE_STAT_BYTES:
            return reduzido

    reduzido.pop("output_columns", None)
    if _json_size(reduzido) <= _MAX_NODE_STAT_BYTES:
        return reduzido
    # Last resort: only what the nodes panel needs to draw the row.
    essencial = {k: reduzido.get(k) for k in _STAT_ESSENTIAL_FIELDS if k in reduzido}
    essencial["__truncated__"] = True
    return essencial


def _cap_node_stats(node_stats: dict) -> dict:
    """Applies a per-node ceiling and an aggregate ceiling to node_stats, preserving order."""
    limitado: dict = {}
    total = 0
    omitted = 0
    for node_id, stat in (node_stats or {}).items():
        if omitted:
            omitted += 1
            continue
        if not isinstance(stat, dict):
            limitado[node_id] = stat
            continue
        tamanho = _json_size(stat)
        if tamanho > _MAX_NODE_STAT_BYTES:
            stat = _shrink_node_stat(stat)
            tamanho = _json_size(stat)
        if total + tamanho > _MAX_NODE_STATS_BYTES:
            omitted = 1
            continue
        total += tamanho
        limitado[node_id] = stat
    if omitted:
        logger.warning(
            "node_stats excedeu %d bytes — %d no(s) omitido(s) do resultado.",
            _MAX_NODE_STATS_BYTES, omitted,
        )
        limitado["__truncated__"] = True
        limitado["__nodes_omitidos__"] = omitted
    return limitado


def _collect_stats(executor, status: str) -> dict:
    """
    Builds the stats dict from the CURRENT state of the WorkflowExecutor.

    Used on both the success and the failure path — on failure the data is
    partial (only the nodes that got to run), and partial is worth much more than
    empty: it is what feeds the nodes panel and the *_run_metrics tables.
    Each collection is isolated: an error building artifacts cannot cost the
    metrics (nor, on the error path, mask the original exception).

    node_stats leaves here ALREADY bounded (see `_cap_node_stats`) — the size
    of job_result cannot depend on how many nodes the workflow has.
    """
    stats: dict = _cap_node_stats(executor.node_stats)

    try:
        artifacts = collect_artifacts(executor.final_outputs)
        if artifacts:
            stats["__artifacts__"] = artifacts
        response = collect_response(executor.final_outputs)
        if response:
            stats["__response__"] = response
    except Exception as exc:
        logger.warning("Falha ao coletar artefatos/resposta (status=%s): %s", status, exc)

    # Execution metrics (CPU, RAM, bytes, spatial). The run status does not go
    # here: the server writes the WorkflowRun's own.
    try:
        stats["__metrics__"] = executor.metrics_collector.build_metrics()
    except Exception as exc:
        logger.warning("Falha ao coletar metricas (status=%s): %s", status, exc)

    # Lightweight S3 references of the pins WRITTEN IN THIS RUN (auto-pin). Reporting
    # the whole `pinned_outputs` — as was done — included the refs that came from
    # the server and merely passed through the run; the consumer re-derives the
    # s3_key with the CURRENT task_id, so every run corrupted the refs it did not
    # rewrite, pointing them to nonexistent objects (permanent 404 on the pin).
    try:
        updated_pins = {nid: out for nid, out in getattr(executor, "updated_pin_refs", {}).items()
                        if out and isinstance(out, dict) and "__pin_s3_key__" in out}
        if updated_pins:
            stats["__updated_pinned_outputs__"] = updated_pins
    except Exception as exc:
        logger.warning("Falha ao coletar pins atualizados: %s", exc)

    return stats


def _partial_stats(holder: dict, status: str) -> dict:
    """
    Partial stats of the executor that was running when the job died.

    `holder` is filled by `_run_workflow` BEFORE `executor.run()`, so the
    WorkflowExecutor remains reachable even when the coroutine is destroyed —
    including on timeout, where the deadline (`asyncio.timeout`) cancels it and
    nothing is returned. Empty when the failure happened before an executor
    existed (validation, decrypt, unknown job_type).
    """
    executor = holder.get("executor")
    if executor is None:
        return {}
    try:
        return _collect_stats(executor, status=status)
    except Exception as exc:
        logger.warning("Falha ao coletar stats parciais (status=%s): %s", status, exc)
        return {}


async def execute_job(message: dict, event_queue: asyncio.Queue | None = None) -> dict:
    """
    Main entry point for executing a job.

    Returns a dict with:
      {
        "job_id":  str,
        "run_id":  str | None,
        "status":  "ok" | "error",
        "output":  any,        # flow result (if ok)
        "stats":   dict,       # node_stats + __metrics__/__artifacts__/...
        "error":   str | None, # error message (if error)
      }

    "stats" comes filled ALSO when the job fails or hits the timeout (with
    the nodes that got to run) — the server overwrites node_stats with whatever
    comes here and feeds workflow_run_metrics/UsageDaily from
    __metrics__. It is only empty when the failure precedes execution
    (validation, decryption, unknown job_type).
    """
    envelope = message.get("envelope", {})
    job_id   = envelope.get("job_id", "?")
    # run_id is extracted from the decrypted payload; until then job_id is used as a
    # fallback, since the server sets run_id == job_id when dispatching to the executor.
    run_id   = job_id
    payload  = None
    # Mutable holder: `_run_workflow` publishes the WorkflowExecutor here as soon as
    # it creates it, so that the error/timeout paths can reach the partial stats.
    stats_holder: dict = {}
    # Taken before the try, not right before the deadline: the duration in the
    # completion log includes validation and decryption.
    _t0 = time.monotonic()

    try:
        # ── 1 and 2. Security validation + decryption, in a thread ────────────
        # The internal order stays the same (signature → recipient → deadline →
        # nonce → decrypt): `_validar_e_descriptografar` is what guarantees it.
        logger.debug("Job '%s': validando assinatura e descriptografando payload.", job_id)
        # run_in_executor(_CONTROL_POOL, ...) and not asyncio.to_thread: to_thread
        # falls into the DEFAULT pool, the same one as the nodes and the user script.
        # See _CONTROL_POOL — a PythonScript in an infinite loop cannot prevent the
        # executor from accepting/rejecting the next job.
        payload = await asyncio.get_running_loop().run_in_executor(
            _CONTROL_POOL, _validar_e_descriptografar, message
        )
        run_id  = payload.get("run_id") or job_id
        logger.debug("Job '%s': payload descriptografado (run_id=%s).", job_id, run_id)

        job_type = envelope.get("job_type", "")
        logger.info("Job '%s': iniciando execução (type=%s, run_id=%s, timeout=%ds).",
                    job_id, job_type, run_id, config.JOB_TIMEOUT)

        # ── 3. Execution with timeout ─────────────────────────────────────────
        # `asyncio.timeout` and not `wait_for`: from Python 3.11 onward
        # `asyncio.TimeoutError` IS the built-in TimeoutError, and a node that
        # raises its own (the PythonScript deadline, a socket that times out) would
        # fall into the JOB deadline handling — "Job expirou após 3600s" (job
        # expired after 3600s) instead of the node's message. It is only the job
        # deadline if it expired; the rest goes up to `except Exception`, as in 3.10.
        prazo = asyncio.timeout(config.JOB_TIMEOUT)
        try:
            async with prazo:
                dispatch_result = await _dispatch(
                    job_type, payload, envelope,
                    event_queue=event_queue, stats_holder=stats_holder,
                )
        except TimeoutError:
            if not prazo.expired():
                raise
            msg = f"Job expirou após {config.JOB_TIMEOUT}s."
            logger.error("Job '%s': timeout — %s", job_id, msg)
            return _error_result(job_id, run_id, msg, "timeout",
                                 stats=_partial_stats(stats_holder, "timeout"))
        _elapsed = time.monotonic() - _t0

        # _dispatch returns {"result": ..., "stats": ...} for run_workflow;
        # other types may return the value directly — handles both cases.
        if isinstance(dispatch_result, dict) and "stats" in dispatch_result:
            output = dispatch_result.get("result")
            stats  = dispatch_result.get("stats") or {}
        else:
            output = dispatch_result
            stats  = {}

        logger.info("Job '%s' concluído em %.1fs (run_id=%s).", job_id, _elapsed, run_id)
        return {"job_id": job_id, "run_id": run_id, "status": "ok", "output": output,
                "stats": stats, "error": None}

    except JobValidationError as exc:
        # Rejected before an executor existed — there are no partial stats to collect.
        logger.error("Job '%s' reprovado na validação de segurança: %s", job_id, exc)
        return _error_result(job_id, run_id, str(exc), "validation")

    except Exception as exc:
        from flow.utils.error_taxonomy import classify_error
        category = classify_error(exc)
        logger.error("Job '%s' falhou (category=%s): %s", job_id, category, exc, exc_info=True)
        return _error_result(job_id, run_id, str(exc), category,
                             stats=_partial_stats(stats_holder, "error"))

    finally:
        # ── 4. Memory cleanup ─────────────────────────────────────────────────
        # Drops the executor's reference to the decrypted payload. It is NOT
        # "erasing from memory": sub-objects still referenced by nodes that ran
        # (e.g. a connectionString already copied into a node) stay alive. What
        # this guarantees is that this dict does not on its own hold the whole
        # payload after the job finishes.
        #
        # We do not call gc.collect(): it ran generation 2 on EVERY job (including
        # early exits via JobValidationError), in the coroutine and holding the
        # GIL — stalling the to_thread threads of concurrent jobs — for no gain
        # at all, since the large object (final_outputs) is alive in the return
        # value and the payload goes away by refcount.
        if payload is not None:
            payload.clear()
            del payload


async def _dispatch(job_type: str, payload: dict, envelope: dict,
                    event_queue: asyncio.Queue | None = None,
                    stats_holder: dict | None = None) -> any:
    """
    Routes the job to the correct handler based on job_type.

    Supported job_types:
      "run_workflow" — runs a workflow of the flow/ engine locally
    """
    if job_type == "run_workflow":
        return await _run_workflow(payload, envelope, event_queue=event_queue,
                                   stats_holder=stats_holder)

    raise ValueError(f"Tipo de job desconhecido: '{job_type}'")


def _apply_host_aliases(conn_str: str) -> str:
    """
    Rewrites the hostname (and port) of a connection string using HOST_ALIASES.
    E.g.: "postgresql+asyncpg://user:pass@db:5432/geobd"  # pragma: allowlist secret
        with alias db=localhost:5433
     → "postgresql+asyncpg://user:pass@localhost:5433/geobd"  # pragma: allowlist secret
    """
    if not config.HOST_ALIASES or not conn_str:
        return conn_str
    try:
        parsed = urlparse(conn_str)
        internal_host = parsed.hostname
        if internal_host and internal_host in config.HOST_ALIASES:
            external = config.HOST_ALIASES[internal_host]
            # Rebuilds netloc preserving userinfo (user:pass@)
            netloc = parsed.netloc
            at_idx = netloc.rfind("@")
            userinfo = netloc[:at_idx + 1] if at_idx >= 0 else ""
            if ":" in external:
                new_netloc = f"{userinfo}{external}"
            else:
                port_part = f":{parsed.port}" if parsed.port else ""
                new_netloc = f"{userinfo}{external}{port_part}"
            conn_str = urlunparse(parsed._replace(netloc=new_netloc))
            logger.debug("connectionString reescrito: %s → %s (alias %s=%s)",
                         internal_host, external, internal_host, external)
    except Exception as exc:
        logger.warning("Falha ao reescrever connectionString: %s", exc)
    return conn_str


def _rewrite_connection_strings(workflow_def: dict) -> None:
    """
    Walks the workflow's nodes and applies HOST_ALIASES to all connectionStrings.
    Needed when the executor runs outside Docker and the credentials use
    internal hostnames (e.g. 'db') that are not resolvable externally.
    """
    if not config.HOST_ALIASES:
        return
    for node in workflow_def.get("nodes", []):
        props = (node.get("data", {}) or {}).get("properties") or node.get("properties") or {}
        if "connectionString" in props and isinstance(props["connectionString"], str):
            props["connectionString"] = _apply_host_aliases(props["connectionString"])



async def _run_workflow(payload: dict, envelope: dict,
                        event_queue: asyncio.Queue | None = None,
                        stats_holder: dict | None = None) -> dict:
    """
    Runs a workflow locally using the flow/ engine (WorkflowExecutor).

    `stats_holder` (optional) receives the WorkflowExecutor as soon as it is
    created — see `_partial_stats`.

    The payload must contain:
      {
        "workflow_definition": dict,  — DAG definition (nodes, edges, config)
        "run_id":              str,   — WorkflowRun UUID for reporting
        "params":              dict,  — input parameters (optional)
        "workspace_id":        str,   — workspace_id for isolation (optional)
        "debug_mode":          bool,  — debug mode (optional)
      }
    """
    workflow_def = payload.get("workflow_definition")
    if not workflow_def:
        raise ValueError("Payload sem 'workflow_definition'.")

    # Rewrites internal Docker hostnames in connectionStrings (e.g. db → localhost:5433)
    _rewrite_connection_strings(workflow_def)

    params         = payload.get("params") or {}
    run_id         = payload.get("run_id") or envelope.get("job_id")
    workspace_id   = payload.get("workspace_id")
    workflow_hash  = payload.get("workflow_hash")
    debug_mode     = payload.get("debug_mode", False)
    pinned_outputs = payload.get("pinned_outputs") or {}
    pin_metadata   = payload.get("pin_metadata") or {}
    # Snapshot of the nodes disabled at dispatch time. Used by
    # SubWorkflowNode to validate sub-workflows on the executor without querying the DB.
    disabled_nodes = payload.get("disabled_nodes") or []
    # Definitions of the whole sub-workflow chain, pre-resolved by the
    # server (the executor has no access to the DB).
    subworkflow_definitions = payload.get("subworkflow_definitions") or {}

    n_nodes = len(workflow_def.get("nodes", []))
    n_edges = len(workflow_def.get("edges", []))
    logger.info("Workflow: %d nós, %d arestas (run_id=%s, workspace=%s).",
                n_nodes, n_edges, run_id, workspace_id)

    publisher = None
    if event_queue is not None:
        publisher = ExecutorEventPublisher(event_queue)

    executor = WorkflowExecutor(
        definition=workflow_def,
        task_id=run_id,
        publisher=publisher,
        debug_mode=debug_mode,
        workspace_id=workspace_id,
        workflow_hash=workflow_hash,
        pinned_outputs=pinned_outputs,
        pin_metadata=pin_metadata,
        disabled_nodes=disabled_nodes,
        subworkflow_definitions=subworkflow_definitions,
    )

    # Publishes the executor BEFORE running: if the coroutine dies (exception or
    # cancellation by the job deadline, `asyncio.timeout`), it returns nothing, and
    # this is the only way for `execute_job` to reach the stats of the nodes that
    # had already run.
    if stats_holder is not None:
        stats_holder["executor"] = executor

    logger.info("Ordem de execução calculada: %s", executor.execution_order)

    result = await executor.run(initial_inputs=params)
    logger.info("Workflow concluído. Nós executados: %d.", len(executor.node_stats))

    stats = _collect_stats(executor, status="success")
    return {"result": result, "stats": stats}
