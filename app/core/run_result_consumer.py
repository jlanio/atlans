# app/core/run_result_consumer.py
"""
Asynchronous consumer of the run_results Redis queue.

Flow:
  Worker  →  LPUSH run_results  { task_id, status, error_message, stats, end_time, duration_seconds }
  API     ←  BRPOP run_results  →  updates WorkflowRun in PostgreSQL

The run is created SYNCHRONOUSLY in the POST /execute endpoint (via _dispatch_job
in workflow_execution_service) with status='pending', updated to
'running' after send_job, and finally updated by the consumer with the
actual result (status=ok/error + stats + metrics + artifacts).

There used to also be a run_creates queue where the consumer created the run.
That caused 4404 on the WS when run_create was slow (busy consumer
or slow Redis). Migrated to synchronous creation at dispatch to eliminate
the race between POST /execute and consumer processing.

Unprocessable items go to run_dead_letter for manual analysis — as do
the ones processed HALFWAY (status written but some auxiliary phase lost),
which go annotated with '_phases_failed'. The queue is forensic: nobody consumes
it automatically, so it is the only record of loss besides the log.
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import math
from flow.utils.backoff import com_jitter
from app.core.utils.logger import get_logger
import os
import re
import time as _time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.utils.datetime_utils import utc_now_naive

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import REDIS_URL
from app.core.constants import NODE_STATS_RUN_META_KEY
from app.core.db import AsyncSessionLocal
from app.core.utils.allowlist import hostname_matches_allowlist
from app.models.models import Workflow, WorkflowRun
from app.models.artifact import Artifact
from app.models.system_config import SystemConfig

logger = get_logger(__name__)

QUEUE_RESULTS     = "run_results"
QUEUE_DEAD_LETTER = "run_dead_letter"

# Above this payload size, json.loads leaves the event loop (mirrors the
# dumps threshold in the producer). Below it, the to_thread overhead does not pay off.
_JSON_OFFLOAD_THRESHOLD = 256 * 1024

# Maximum attempts for run_results whose run has not been created yet
_MAX_RESULT_RETRIES = 20


_NOTIFY_DELAYS = [5, 30, 120]  # seconds between attempts


class PhaseFailure(Exception):
    """One or more post-close phases of the run failed.

    The run's status WAS already written by _update_run_status; what is missing
    are auxiliary effects (usage, metrics, artifacts, pins, webhook). Raised
    by _process_result so that _consume_one sends the payload to
    run_dead_letter — without it the only trace of the loss was a log line.
    """

    def __init__(self, task_id: str, labels: list[str]):
        super().__init__(f"run {task_id}: fase(s) nao concluida(s): {', '.join(labels)}")
        self.labels = labels

# Set of background tasks for webhook notifications — prevents the GC from
# collecting them while they run and allows tracking at shutdown if needed.
# Reference: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_webhook_tasks: set[asyncio.Task] = set()



# Vocabulary of `workflow_runs.error_category` (docs/specs/metrics-history.md
# §2): the flow taxonomy plus the server categories. A value outside it is
# not written — cut at 16 characters it would become "no_executor_chai", a
# category nobody maps and that the screen would group as if it were another.
_CATEGORIAS_DE_ERRO = frozenset({
    "user", "validation", "timeout", "resource", "transient", "internal",
    "no_executor", "executor_lost", "isolation", "dispatch",
})


def _categoria_conhecida(valor) -> "str | None":
    texto = str(valor).strip().lower() if valor is not None else ""
    if texto in _CATEGORIAS_DE_ERRO:
        return texto
    logger.debug("error_category fora do vocabulario ignorada: %r", valor)
    return None


def _schedule_webhook_notification(url: str, body: dict) -> None:
    """Create a notification task and register it so it does not become orphaned."""
    task = asyncio.create_task(_send_notification_with_retry(url, body))
    _webhook_tasks.add(task)
    # Log silent exceptions and remove from the set when done.
    def _done(t: asyncio.Task) -> None:
        _webhook_tasks.discard(t)
        exc = t.exception()
        if exc is not None:
            logger.error("Webhook notification task falhou com exception não-tratada: %s", exc, exc_info=exc)
    task.add_done_callback(_done)


async def _send_notification_with_retry(url: str, body: dict) -> None:
    """Fire the run-completion webhook POST with up to 3 attempts and backoff.

    Uses safe_httpx_request: IP pinning after SSRF validation, prevents DNS
    rebinding between validation and POST. follow_redirects=False prevents the
    server from answering 302 to an internal URL (proxy attack).
    """
    from flow.utils.geo_helpers import safe_httpx_request

    # Serialize once and sign with HMAC so the receiver can validate
    payload_bytes = json.dumps(body, sort_keys=True).encode()
    timestamp = str(int(_time.time()))
    signature = hmac.new(
        os.getenv("APP_SECRET", "").encode(),
        f"{timestamp}.".encode() + payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    webhook_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp,
    }

    for attempt, delay in enumerate(_NOTIFY_DELAYS, start=1):
        try:
            resp = await safe_httpx_request(
                "POST", url,
                timeout=15,
                follow_redirects=False,
                headers=webhook_headers,
                content=payload_bytes,
            )
            if resp.status_code < 500:
                logger.debug("Notificação enviada para %s (HTTP %d).", url, resp.status_code)
                return
            logger.warning(
                "Notificação para %s retornou HTTP %d (tentativa %d/%d).",
                url, resp.status_code, attempt, len(_NOTIFY_DELAYS),
            )
        except ValueError as exc:
            # safe_httpx_request raise ValueError em SSRF block — nao re-tentar.
            logger.warning("Webhook bloqueado por SSRF: %s → %s", url, exc)
            return
        except Exception as exc:
            logger.warning(
                "Falha ao enviar notificação para %s (tentativa %d/%d): %s",
                url, attempt, len(_NOTIFY_DELAYS), exc,
            )
        if attempt < len(_NOTIFY_DELAYS):
            await asyncio.sleep(com_jitter(delay))

    logger.error("Notificação para %s falhou após %d tentativas.", url, len(_NOTIFY_DELAYS))


async def _recover_session(db, run: WorkflowRun, task_id: str) -> bool:
    """Recover the session after a phase fails. Returns False if it cannot.

    The rollback is MANDATORY: without it the AsyncSession stays in an error state
    and every following phase blows up with PendingRollbackError before even
    touching the database (that was exactly the effect of the silent except in
    _persist_metrics — the run ended "completed" with no artifacts, no pins and
    no webhook).

    Since the rollback EXPIRES the already loaded objects, we need to re-hydrate
    `run`: otherwise the next access to run.status would trigger lazy IO
    (MissingGreenlet) inside the async loop.
    """
    try:
        await db.rollback()
        await db.refresh(run)
        return True
    except Exception as exc:
        logger.error("run %s: sessao irrecuperavel apos falha de fase: %s", task_id, exc)
        return False


PHASE_OK     = "ok"      # fase concluiu
PHASE_FAILED = "failed"  # phase blew up, but the session came back — can continue
PHASE_FATAL  = "fatal"   # unrecoverable session — nothing else runs


async def _run_phase(db, run: WorkflowRun, task_id: str, label: str, fn, *args) -> str:
    """Run one pipeline phase, isolating its failure from the others.

    Previously, any exception here aborted the WHOLE payload and the run was left
    without artifacts/pins/notification. Now the failure is logged, the session
    is recovered and the following phases continue.

    Returns PHASE_FATAL when the session became unrecoverable — in that case the
    caller STOPS the pipeline, because every following phase would blow up with
    PendingRollbackError. The return value distinguishes PHASE_FAILED from
    PHASE_OK because the one that records the loss is _process_result, which
    raises PhaseFailure at the end: a log alone gives the operator nothing to
    reprocess.
    """
    try:
        await fn(*args)
        return PHASE_OK
    except Exception as exc:
        logger.error("run %s: fase '%s' falhou: %s", task_id, label, exc, exc_info=exc)
        return PHASE_FAILED if await _recover_session(db, run, task_id) else PHASE_FATAL


async def _process_result(db, payload: dict) -> bool:
    """
    Execution result processing pipeline.

    Returns False if the run does not exist yet — now unlikely because
    _dispatch_job creates the run SYNCHRONOUSLY before dispatching. It can
    happen in degraded scenarios: a manual payload via redis-cli, a deleted
    run, or an API crash between _dispatch_job and commit. _consume_one
    retries with backoff before discarding.

    Raises PhaseFailure when the status was written but some auxiliary phase
    failed: the item goes to run_dead_letter annotated with the lost phases.
    Before B11 the exception propagated raw and produced the same dead letter;
    per-phase isolation must not cost the observability of the loss.
    """
    task_id = payload["task_id"]
    # FOR UPDATE: two workers with results for the SAME run (the real one and a
    # late one) both read 'running', both counted the usage and the last to write
    # won. With the lock the second waits for the first's commit and sees the outcome.
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.task_id == task_id).with_for_update()
    )
    run = result.scalar_one_or_none()
    if not run:
        return False

    stats = payload.get("stats") or {}

    # Snapshot BEFORE the update: idempotence guard for the usage aggregate.
    # If the run was already terminal, this payload is a redelivery (reprocessed
    # dead letter, replay of the executor's outbox) and must not count twice.
    first_close = run.status in ("pending", "running")

    if (
        not first_close
        and payload.get("status") != run.status
        and not _desfecho_inferido_pelo_servidor(run)
    ):
        # A DIFFERENT outcome for a run already closed: the result passed the WS
        # idempotence check before the first one was written (both were in the
        # queue at the same time). The first outcome stands — the same rule as
        # the WS: a late 'cancelled' does not erase a success, nor the reverse,
        # nor a cancellation requested by the user. The exception is the outcome
        # the server itself INFERRED (executor vanished, run lost in
        # reconciliation): the real result already in the queue corrects the
        # guess, as it always did. Redelivery of the SAME outcome continues
        # below (dead letter).
        logger.warning(
            "run %s: ja fechado como '%s' — resultado '%s' que chegou depois ignorado.",
            task_id, run.status, payload.get("status"),
        )
        await db.commit()  # solta a trava do FOR UPDATE
        return True

    await _update_run_status(db, run, payload)

    # Usage accounting comes FIRST: it is the only billing data and must not
    # depend on metrics (which the error path may not produce).
    phases = (
        ("uso diario",  _upsert_usage_daily,                (db, run, stats, first_close)),
        ("metricas",    _persist_metrics_if_present,        (db, run, stats, payload)),
        ("artefatos",   _register_artifacts_if_present,     (db, run, stats)),
        ("pins",        _persist_pinned_outputs_if_present, (db, run, stats)),
        # The source catalog learns from the execution: WFS nodes that read
        # successfully become (or update) workspace sources. After the metrics
        # (it reads the schema they carry) and before the notification (which is the end).
        ("fontes",      _aprender_fontes_if_present,        (db, run, stats, first_close)),
        ("notificacao", _fire_notification_if_configured,   (db, run)),
    )
    failed: list[str] = []
    for idx, (label, fn, args) in enumerate(phases):
        outcome = await _run_phase(db, run, task_id, label, fn, *args)
        if outcome == PHASE_FATAL:
            # Unrecoverable session: the remaining phases never even run, so
            # ALL of them go into the loss report sent to the dead letter.
            failed.extend(p[0] for p in phases[idx:])
            break
        if outcome == PHASE_FAILED:
            failed.append(label)

    if failed:
        raise PhaseFailure(task_id, failed)
    return True


def _json_seguro(valor):
    """Replace NaN/Infinity with None, recursively.

    Python's `json.dumps` emits NaN and Infinity — an extension the JSON spec
    does not have — and `json.loads` accepts them back, so they cross the Redis
    queue intact. When they reach a JSONB column Postgres rejects the INSERT,
    the exception propagates before the commit and the whole run goes to
    run_dead_letter with its status stuck at 'running', even though it finished.

    The known source was the bbox of an empty GeoDataFrame (see
    flow/metrics/collector._bbox_finito), but the queue is an external contract:
    sanitizing here is what keeps a NaN from any other metric from breaking the
    write of the result.
    """
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, dict):
        return {k: _json_seguro(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_seguro(v) for v in valor]
    return valor


# Categories of a 'failed' that the SERVER inferred without a result from the executor:
# `executor_lost` (disconnected, or reconciliation did not find the job) and `dispatch`
# (the send was never confirmed). A real result arriving later
# replaces that outcome — see `_process_result`.
_CATEGORIAS_INFERIDAS = frozenset({"executor_lost", "dispatch"})


def _desfecho_inferido_pelo_servidor(run: WorkflowRun) -> bool:
    return run.status == "failed" and run.error_category in _CATEGORIAS_INFERIDAS


def _numero_finito(valor):
    """The number, or 0 if it is not a finite number.

    For the usage_daily increments, where `_json_seguro` is not enough: the
    None it returns for NaN would become NULL in the SQL sum (`coluna + NULL`
    nulls out the day's row), and raw NaN is worse — `NaN or 0` is NaN, and
    NaN + x = NaN contaminates the workspace aggregate forever.
    """
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and math.isfinite(valor):
        return valor
    return 0


def _stats_para_coluna(stats: dict) -> dict:
    """Keep only what the node_stats column exists to store.

    The executor sends, inside `stats`, control keys that are NOT per-node
    statistics: `__metrics__` (already normalized in workflow_run_metrics and
    node_run_metrics), `__artifacts__` (already in artifacts), `__response__`
    (the inline body of the ResponseNode, which the webhook reads from Redis) and
    `__updated_pinned_outputs__` (consumed right here, from the queue payload,
    and persisted in workflows.pinned_outputs).

    Writing all of that back into the JSON inflated the column by an order of
    magnitude — the executor only truncates the payload above 16 MB — and the
    price was paid on EVERY run listing, which brought the whole row from
    Postgres to read a single integer. What remains is `__run_meta__`, which
    only exists here.
    """
    return {
        k: v for k, v in stats.items()
        if not k.startswith("__") or k == NODE_STATS_RUN_META_KEY
    }


async def _update_run_status(db, run: WorkflowRun, payload: dict) -> None:
    run.status           = payload["status"]
    run.error_message    = payload.get("error_message")
    # Only on the 'failed' outcome: the WS router already clears the category on
    # success and cancellation, but the queue is an external contract — an old
    # (or forged) payload must not stamp a category on a run that succeeded.
    # Cut at 16 because that is the column size: an executor sending something
    # outside the taxonomy must not break the commit of the whole close.
    _categoria = payload.get("error_category")
    run.error_category   = (
        _categoria_conhecida(_categoria) if run.status == "failed" and _categoria else None
    )
    # node_stats is only overwritten when content comes in. On the error,
    # timeout or cancellation path the executor may send empty/missing stats —
    # writing {} would erase the partial stats already accumulated on the run and
    # the panel would lose the history of the nodes that did run.
    stats = payload.get("stats") or {}
    if stats:
        run.node_stats = _json_seguro(_stats_para_coluna(stats))
    # end_time comes from the queue and goes into a timestamptz column. A naive
    # value would be interpreted by Postgres in the session's time zone (the
    # containers' TZ) and stored shifted — 4h into the future in America/Cuiaba.
    # The producer already sends it aware, but old payloads may be in the queue
    # and the queue is an external contract: assume UTC when no offset comes.
    _end = datetime.fromisoformat(payload["end_time"])
    if _end.tzinfo is None:
        _end = _end.replace(tzinfo=timezone.utc)
    run.end_time         = _end
    run.duration_seconds = payload.get("duration_seconds")
    await db.commit()
    logger.debug("run atualizado: task_id=%s status=%s", payload["task_id"], run.status)


async def _persist_metrics_if_present(db, run: WorkflowRun, stats: dict, payload: dict) -> None:
    metrics_data = stats.get("__metrics__")
    if metrics_data:
        await _persist_metrics(db, run, metrics_data, payload)


async def _register_artifacts_if_present(db, run: WorkflowRun, stats: dict) -> None:
    artifacts_meta = stats.get("__artifacts__", {})
    if artifacts_meta:
        await _register_artifacts(db, run, artifacts_meta)


# ── Server-side s3_key derivation (cross-tenant SEC) ─────────────────────────
#
# The executor sends 's3_key' / '__pin_s3_key__' along with the metadata, but these
# fields are ATTACKABLE: a compromised executor pointed to
# 'artifacts/<another-workspace>/...' and the consumer wrote the Artifact row with
# credential_id=None — a PUBLIC download, with no token, of another tenant's object.
# The pin case was worse: /workflows/{id}/pin/{node} deletes the object pointed to
# by the saved '__pin_s3_key__', so the forged key became a cross-tenant delete.
#
# Every equivalent HTTP endpoint already goes through `_validate_agent_s3_key`; the
# WS -> run_results queue path went through nothing. Here we invert the flow: the
# SERVER derives the key from (prefix, the run's workspace, task_id, file name) —
# exactly the format the executor uses in flow/utils/artifact_helpers.py and
# flow/executor/pin.py — and still revalidates it with the same guard as the HTTP
# endpoints, restricted to the run's workspace.
_PIN_FORMATS = ("json", "geojson", "parquet")

# The _S3_KEY_RE (drive_router) charset minus the slash: anything left over becomes '_'.
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")
_DOT_RUN = re.compile(r"\.{2,}")
_MAX_STEM_LEN = 160
_MAX_EXT_LEN = 16


def _sanitize_filename(filename: str) -> str:
    """Reduce the name received from the executor to an S3-safe basename.

    NORMALIZES instead of rejecting. The name comes from `slugify_label` on the
    executor, which uses `str.isalnum()` — Unicode-aware, so it PRESERVES accents.
    In a pt-BR product the node label ('Relatorio 2026', 'Area Util') is the
    source of the name, so the accented case is the common one, not the exception:
    rejecting made `_derive_s3_key` return None and the artifact vanished from the
    UI leaving only a WARNING on the server.

    NFKD + dropping combining marks converts 'ó'→'o'; whatever remains outside
    the charset (space, a lone 'ç', ':') becomes '_'. Runs of dots are
    collapsed because `_validate_agent_s3_key` rejects any key with '..'.
    """
    name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if name in ("", ".", ".."):
        return ""

    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = _UNSAFE_NAME_CHARS.sub("_", name)
    name = _DOT_RUN.sub(".", name).strip(".")
    if not name:
        return ""

    # S3 limits the key to 1024 bytes and pathological names arrive from the executor
    # with no limit; cut the stem preserving the extension (the Drive mime comes from it).
    stem, dot, ext = name.rpartition(".")
    if not dot:
        return name[:_MAX_STEM_LEN]
    return f"{stem[:_MAX_STEM_LEN]}.{ext[:_MAX_EXT_LEN]}"


def _derive_s3_key(prefix: str, workspace_id: str, task_id: str, filename: str) -> str | None:
    """Build the canonical key and validate it with the same guard as the HTTP endpoints.

    Returns None only when no name is left after sanitizing or when the
    workspace/task is missing — the charset was already normalized by
    _sanitize_filename, so rejection here is the safety net, not the common path.
    """
    from fastapi import HTTPException
    from app.api.routers.executor_drive_router import _validate_agent_s3_key

    safe_name = _sanitize_filename(filename)
    if not safe_name or not workspace_id or not task_id:
        return None

    key = f"{prefix}/{workspace_id}/{task_id}/{safe_name}"
    try:
        _validate_agent_s3_key(key, [workspace_id])
    except HTTPException as exc:
        logger.warning("s3_key derivada rejeitada (%s): %s", exc.detail, key)
        return None
    return key


def _safe_pin_ref(run: WorkflowRun, nid: str, ref: dict) -> dict | None:
    """Rewrite the pin reference with the server-derived s3_key.

    The executor builds the name as '{node_id}_pin.{fmt}' and the key as
    'pin-cache/{workspace_id or "default"}/{task_id or "no-task"}/{nome}'
    (flow/executor/pin.py) — we reproduce that here so as not to break the
    legitimate path, ignoring what came in the payload.
    """
    fmt = ref.get("__pin_format__") or "json"
    if fmt not in _PIN_FORMATS:
        return None

    filename = f"{nid}_pin.{fmt}"
    s3_key = _derive_s3_key(
        "pin-cache",
        run.workspace_id or "default",
        run.task_id or "no-task",
        filename,
    )
    if not s3_key:
        return None

    safe = dict(ref)
    safe["__pin_s3_key__"]  = s3_key
    safe["__pin_format__"]  = fmt
    safe["__pin_filename__"] = filename
    return safe


async def _aprender_fontes_if_present(db, run: WorkflowRun, stats: dict, first_close: bool) -> None:
    """The "fontes" phase: register in the catalog the WFS sources this execution read.

    Only a `success` execution, only `WFS` nodes with status `completed` (one that
    failed teaches nothing), and only when the flag is on. The definition comes
    from the CURRENT Workflow — the same limitation accepted for pins: url/typeName
    are in the clear (`encrypt_workflow_connections` only encrypts
    `connectionString`). `first_close` is the redelivery guard: a redelivery does
    not count the usage twice, and the upsert by key does not duplicate the row.
    """
    from app.core.config import FONTES_APRENDER_DAS_EXECUCOES

    if not FONTES_APRENDER_DAS_EXECUCOES or run.status != "success" or not run.workspace_id:
        return
    if not isinstance(stats, dict) or not any(
        isinstance(v, dict) and v.get("node_name") == "WFS"
        for k, v in stats.items() if not str(k).startswith("__")
    ):
        return

    wf_result = await db.execute(select(Workflow).where(Workflow.id_hash == run.workflow_hash))
    wf_obj = wf_result.scalar_one_or_none()
    if not wf_obj or not isinstance(wf_obj.definition, dict):
        return

    from app.services import fontes_service

    aprendidas = await fontes_service.aprender_de_execucao(
        db, run, stats, wf_obj.definition, first_close=first_close,
    )
    if aprendidas:
        await db.commit()
        logger.info("run %s: %d fonte(s) WFS registrada(s) no catalogo.", run.task_id, aprendidas)


async def _persist_pinned_outputs_if_present(db, run: WorkflowRun, stats: dict) -> None:
    updated_pins = stats.get("__updated_pinned_outputs__")
    if not updated_pins or not isinstance(updated_pins, dict):
        return

    from sqlalchemy.orm.attributes import flag_modified
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id_hash == run.workflow_hash)
    )
    wf_obj = wf_result.scalar_one_or_none()
    if not wf_obj:
        return

    # SEC: the workflow may have been moved to another workspace while this run was
    # going (POST /workflows/{id}/move). The s3_keys are derived from
    # `run.workspace_id` — the SOURCE workspace —, so writing them now would leave
    # the workflow, already in the destination, with pins pointing to
    # pin-cache/{ws_origem}/. On the next execution the executor would request
    # those objects and, being the default executor (which sees every workspace),
    # would read the old tenant's data.
    #
    # Discarding is the safe side: the pin is a cache, not primary data, and the
    # next execution in the destination recreates it under the correct prefix.
    if run.workspace_id != wf_obj.workspace_id:
        logger.warning(
            "run %s: auto-pin descartado — o workflow %s mudou do workspace '%s' "
            "para '%s' durante a execucao.",
            run.task_id, run.workflow_hash, run.workspace_id, wf_obj.workspace_id,
        )
        return

    # Sanitize BEFORE writing: what goes into pinned_outputs is sent back to the
    # executor on the next dispatch and feeds the unpin delete.
    #
    # Only refs of THIS run: `_safe_pin_ref` derives the s3_key with the current
    # task_id, so accepting a ref the executor merely passed along (written in an
    # old run) would repoint it to an object that was never uploaded — a permanent
    # 404 on the pin. Updated executors already send only what they rewrote
    # (updated_pin_refs); this filter protects against old executors, which
    # reported the whole pinned_outputs. The declared key is attackable, but
    # using it to DISCARD is fail-safe: lying about the current task_id only leads
    # the ref to the same canonical derivation it would already have.
    task_atual = run.task_id or "no-task"
    accepted: dict[str, dict] = {}
    for nid, ref in updated_pins.items():
        if not isinstance(ref, dict) or "__pin_s3_key__" not in ref:
            continue
        if f"/{task_atual}/" not in str(ref.get("__pin_s3_key__", "")):
            logger.debug(
                "run %s: pin do node '%s' ignorado — ref de uma run anterior (passthrough).",
                run.task_id, nid,
            )
            continue
        safe_ref = _safe_pin_ref(run, nid, ref)
        if safe_ref is None:
            logger.warning(
                "run %s: pin do node '%s' descartado — nao foi possivel derivar uma s3_key valida.",
                run.task_id, nid,
            )
            continue
        accepted[nid] = safe_ref

    if not accepted:
        return

    current_pins = dict(wf_obj.pinned_outputs or {})
    current_pins.update(accepted)
    wf_obj.pinned_outputs = current_pins
    flag_modified(wf_obj, "pinned_outputs")

    for nid, ref in accepted.items():
        await _upsert_pin_artifact(db, run, wf_obj, nid, ref)

    await db.commit()
    logger.debug("Auto-pin persistido para workflow %s: %s", run.workflow_hash, list(accepted.keys()))


async def _upsert_pin_artifact(db, run: WorkflowRun, wf_obj, nid: str, ref: dict) -> None:
    # ref already went through _safe_pin_ref — s3_key/format/filename come from the server.
    s3_key = ref["__pin_s3_key__"]
    fmt = ref["__pin_format__"]
    filename = ref["__pin_filename__"]

    # `scalar_one_or_none()` here raised `MultipleResultsFound` with two
    # rows — and it is THIS function that creates the second: `artifacts` has no
    # unique constraint on (workflow_hash, node_id, is_pinned)
    # (`models/artifact.py`), so two runs of the same workflow finishing together
    # find nothing, each inserts its own, and from then on every read
    # raised. In a route that is a 500; here it is worse — this path is the one of
    # `job_result`, and the exception hangs the persistence of the execution result.
    #
    # The newest one wins and the extra ROWS are deleted, which cleans the data
    # through use. Their objects are left to reconcile: deleting from storage here
    # would be a network round trip on the hot path of `job_result`, and an orphan
    # in MinIO costs bytes, not correctness.
    #
    # The collapse stays here even after the partial unique index
    # (`uq_artifact_pin_por_no`, migration of 2026-09-15): it is what cleans a
    # database that has not migrated yet, and it is the path of the tests' SQLite,
    # which is born from `create_all`. With the index, the race no longer creates
    # the duplicate and instead raises on INSERT — handled in the SAVEPOINT below.
    existing = await db.execute(
        select(Artifact)
        .where(
            Artifact.workflow_hash == run.workflow_hash,
            Artifact.node_id == nid,
            Artifact.is_pinned.is_(True),
        )
        .order_by(Artifact.id.desc())
    )
    linhas = list(existing.scalars().all())
    old_art = linhas[0] if linhas else None
    for extra in linhas[1:]:
        logger.warning(
            "run %s: linha de pin-cache duplicada para o node '%s' (id=%s) removida.",
            run.task_id, nid, extra.id,
        )
        await db.delete(extra)
    if old_art:
        old_art.s3_key = s3_key
        old_art.filename = filename
        old_art.format = fmt
        old_art.run_id = run.task_id
        # The workspace follows the s3_key. The lookup above is by
        # (workflow_hash, node_id) and does not filter by tenant, so a leftover row
        # from before a move would be repointed to an object of the new workspace
        # while keeping the old `workspace_id` — and the download uses the literal
        # s3_key, serving destination data to someone who only has access to the source.
        old_art.workspace_id = run.workspace_id or wf_obj.workspace_id or ""
    else:
        novo = Artifact(
            # Same workspace used to derive the s3_key — the record can never
            # point to a tenant different from the object's owner.
            workspace_id=run.workspace_id or wf_obj.workspace_id or "",
            workflow_hash=run.workflow_hash,
            run_id=run.task_id,
            node_id=nid,
            output_key=f"pin-cache-{nid}",
            filename=filename,
            format=fmt,
            s3_key=s3_key,
            is_pinned=True,
        )
        # SAVEPOINT, and not a loose `try`: with the partial unique index, two runs
        # of the same workflow finishing together read "does not exist" at the same
        # time and the second INSERT violates the constraint. In Postgres an error
        # like that poisons the whole transaction — and this is the transaction that
        # persists the execution RESULT, on the `job_result` path. The savepoint
        # isolates the failure; the pattern is the one of
        # `api_token_service.marcar_uso` and `credential_loader`.
        try:
            async with db.begin_nested():
                db.add(novo)
                await db.flush()
        except IntegrityError:
            # The other run won the race. Its row is the truth; this
            # call only repointed it to the newest object, which is exactly
            # what the branch above does.
            logger.info(
                "run %s: outro run criou a linha de pin-cache do node '%s' primeiro; "
                "repontando a existente.",
                run.task_id, nid,
            )
            vencedora = (await db.execute(
                select(Artifact)
                .where(
                    Artifact.workflow_hash == run.workflow_hash,
                    Artifact.node_id == nid,
                    Artifact.is_pinned.is_(True),
                )
                .order_by(Artifact.id.desc())
            )).scalars().first()
            if vencedora is None:  # pragma: no cover - only if the row vanishes midway
                raise
            vencedora.s3_key = s3_key
            vencedora.filename = filename
            vencedora.format = fmt
            vencedora.run_id = run.task_id
            vencedora.workspace_id = run.workspace_id or wf_obj.workspace_id or ""


async def _fire_notification_if_configured(db, run: WorkflowRun) -> None:
    from urllib.parse import urlparse
    from app.models.workspace import Workspace

    wf_result = await db.execute(
        select(Workflow.notification_url, Workflow.workspace_id).where(
            Workflow.id_hash == run.workflow_hash
        )
    )
    row = wf_result.first()
    if not row:
        return
    notification_url, workspace_id = row
    if not notification_url:
        return

    try:
        target_host = urlparse(notification_url).hostname or ""
    except Exception:
        target_host = ""

    # GLOBAL whitelist (admin → Configurações (Settings)). It was saved and displayed
    # — the screen warns when it is empty —, but no firing consulted it: the
    # restriction the admin configured restricted nothing. Empty = no restriction;
    # with items, the host must be in it AND in the workspace allowlist (below).
    # What was saved before this rule (a `*`, a URL with a path) goes through
    # the same validation as saving: what the matcher would not match is ignored.
    from app.core.system_config import get_config
    from app.core.utils.allowlist import padroes_validos

    global_list = padroes_validos(await get_config(db, "webhook_whitelist", default=[]) or [])
    if global_list and not hostname_matches_allowlist(target_host, global_list):
        logger.warning(
            "Webhook bloqueado pela whitelist global: host '%s' nao esta em %s.",
            target_host, global_list,
        )
        return

    # V13: per-workspace host allowlist. Without this list, any URL that
    # passes the SSRF check is accepted — including the intranet of the operator
    # who configured the webhook, leaking run results across tenants.
    if workspace_id:
        ws_result = await db.execute(
            select(Workspace.notification_url_allowlist).where(
                Workspace.id_hash == workspace_id
            )
        )
        allowlist = ws_result.scalar_one_or_none() or []
        if allowlist:
            if not hostname_matches_allowlist(target_host, allowlist):
                logger.warning(
                    "Webhook bloqueado por allowlist do workspace '%s': host '%s' "
                    "nao esta em %s.",
                    workspace_id, target_host, allowlist,
                )
                return

    notify_body = {
        "task_id":          run.task_id,
        "workflow_hash":    run.workflow_hash,
        "status":           run.status,
        "duration_seconds": run.duration_seconds,
        "error_message":    run.error_message,
    }
    _schedule_webhook_notification(notification_url, notify_body)


async def _get_retention_days(db) -> int | None:
    """Read artifact retention days from the system settings. None = no expiration."""
    try:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == "artifact_retention_days")
        )
        cfg = result.scalar_one_or_none()
        if cfg and cfg.value is not None:
            return int(cfg.value)
    except Exception as exc:
        logger.warning("Falha ao ler artifact_retention_days: %s", exc)
        # A failing SELECT also invalidates the session — without the rollback the
        # artifacts INSERT right below would blow up with PendingRollbackError.
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.debug("Rollback apos falha em artifact_retention_days: %s", rb_exc)
    return None


# How many simultaneous HEADs to MinIO. `storage.head` is synchronous boto3, so
# each one takes a thread of asyncio's default executor (default: 32); 8 gives
# enough throughput for a run with dozens of outputs without monopolizing the pool,
# which is shared with the rest of the API on this worker.
_HEAD_CONCURRENCY = 8


async def _head_sizes(keys: list[str]) -> dict[str, int]:
    """Query the size of several keys in storage at once.

    It used to be one HEAD per artifact, serially, inside the registration loop:
    a run with 20 outputs paid 20 queued network round trips with the consumer
    stalled, and the whole queue fell behind it.

    `return_exceptions=True` preserves the old partial-failure behavior —
    a key that fails becomes a WARNING and is left without a size, without
    bringing down the others.
    """
    if not keys:
        return {}

    from app.core import storage as _s3

    sem = asyncio.Semaphore(_HEAD_CONCURRENCY)

    async def _one(key: str):
        async with sem:
            # storage.head is synchronous boto3. This consumer runs as the ONLY
            # background task on the event loop — without to_thread, each HEAD froze
            # ALL the API traffic on this worker during the round trip.
            return await asyncio.to_thread(_s3.head, key)

    resultados = await asyncio.gather(*(_one(k) for k in keys), return_exceptions=True)

    tamanhos: dict[str, int] = {}
    for key, obj in zip(keys, resultados):
        if isinstance(obj, BaseException):
            logger.warning("Falha ao obter tamanho do artefato S3 '%s': %s", key, obj)
            continue
        if obj:
            tamanhos[key] = obj["size"]
    return tamanhos


@dataclass(frozen=True)
class _Resolucao:
    """The destination of each sanitized item, decided BEFORE going to storage (phase 2)."""

    a_criar: list[dict]             # vira linha nova: Artifact ou WorkspaceFile
    drive_existentes: list[tuple]   # (WorkspaceFile, acao): a linha ja existe, so avisar
    tamanhos: dict[str, int]        # HEAD of the items that become rows and have an object in storage


async def _register_artifacts(db, run: WorkflowRun, artifacts_meta: dict) -> None:
    """
    Register artifacts produced in the run.

    - context="artifacts" (default): creates a record in the Artifact table.
    - context="drive": creates a record in the WorkspaceFile (Drive) table,
      allowing automatic synchronization with executors. Does not duplicate in Artifact.

    artifacts_meta: { node_id: [ {output_key, format, features, filename, ...} ] }

    SEC: the 's3_key' field sent by the executor is IGNORED — the key is derived
    here from the run's workspace/task (see _derive_s3_key).

    Structured in three phases with no IO inside the loop: (1) sanitizes the payload
    (`_sanear_artefatos`), (2) resolves database and storage IN BATCH
    (`_resolver_em_lote`), (3) builds the rows and persists with one commit
    (`_persistir_artefatos`) — and only then notifies the Drive (`_avisar_drive`).
    The previous version made two queries per Drive item (N+1) and one serial
    HEAD per artifact, all while processing a single queue item.
    """
    if not run.workspace_id:
        logger.warning(
            "run %s nao tem workspace_id — artefatos ignorados (nao ha prefixo seguro).",
            run.task_id,
        )
        return

    retention_days = await _get_retention_days(db)
    # The expires_at column is TIMESTAMP WITHOUT TIME ZONE — use a naive datetime (UTC)
    expires_at = (utc_now_naive() + timedelta(days=retention_days)) if retention_days else None

    executor_id = None
    if run.host and run.host.startswith("executor:"):
        executor_id = run.host[len("executor:"):]

    known = await _artefatos_ja_registrados(db, run)
    pendentes = _sanear_artefatos(run, artifacts_meta, known)
    if not pendentes:
        return

    resolucao = await _resolver_em_lote(db, run, pendentes)
    novos_no_drive = await _persistir_artefatos(
        db, run, resolucao, expires_at=expires_at, executor_id=executor_id,
    )
    # The file that already existed is notified before the new one: that is the order
    # in which each destination was decided (phase 2, then phase 3).
    drive_files = resolucao.drive_existentes + novos_no_drive

    logger.debug("run %s: %d artefato(s) registrado(s) (%d no Drive).",
                 run.task_id, len(resolucao.a_criar), len(drive_files))

    await _avisar_drive(drive_files)


async def _artefatos_ja_registrados(db, run: WorkflowRun) -> set[tuple]:
    """(node_id, filename) pairs this run already wrote to Artifact.

    Idempotence: if this payload is redelivered (reprocessed dead letter,
    outbox replay) we do not want to duplicate rows.

    STABLE dedup key (node_id, filename) within the run, NOT the s3_key: a local
    artifact writes s3_key=None (keepLocal / local_fallback), so the derived
    s3_key never matched known and the redelivery recreated the row. filename and
    node_id exist on every row, local or not. Within a run (ws/task
    fixed) the derived s3_key is 1:1 with the filename, so the dedup granularity
    of the NON-local case does not change.
    """
    known_result = await db.execute(
        select(Artifact.node_id, Artifact.filename).where(Artifact.run_id == run.task_id)
    )
    return {(nid, fn) for nid, fn in known_result.all()}


def _sanear_artefatos(run: WorkflowRun, artifacts_meta: dict, known: set[tuple]) -> list[dict]:
    """Phase 1: sanitize the payload. No IO here.

    Returns one dict per item that becomes a record — node_id, raw item, DERIVED
    s3_key, sanitized filename, whether it is local and the context —, without
    what is not an object, without invalid names and without repeats (within the
    batch itself or already in `known`).
    """
    # Copy: the batch also deduplicates against itself, and `known` belongs to the caller.
    known = set(known)
    pendentes: list[dict] = []
    for node_id, items in artifacts_meta.items():
        for item in (items if isinstance(items, list) else [items]):
            if not isinstance(item, dict):
                continue

            # Artifact kept on the executor's disk. Two paths arrive here:
            #   * keepLocal (output node with localidade=executor): LGPD policy,
            #     content_location='executor';
            #   * local_fallback: the upload to MinIO FAILED and the fallback wrote
            #     the bytes in the SAME place as a keepLocal
            #     (artifacts_root()/{ws}/{task}/{arquivo}). The executor reports
            #     content_location='minio' on purpose (the destination WAS the cloud),
            #     but the object never got there — registering it as 'minio' with the
            #     derived s3_key gave a download that answered 404 forever.
            #     The bytes are on the executor, so this artifact is served as
            #     executor-local (the platform download does not fetch local
            #     content — the UI shows "Sem download" (no download), which is
            #     honest, instead of a button that breaks).
            #
            # There is no object in storage in either of them: no s3_key derivation
            # and no HEAD.
            #
            # The FLAG is accepted from the executor, but the PATH is not. Like the
            # s3_key, `local_path` is derived here from (the run's workspace, the
            # run's task, sanitized name) — a path coming over the network would later
            # go back to the executor in the retention cleanup order, and a `../`
            # there would turn retention into an arbitrary delete on the user's disk.
            #
            # Accepting the flag itself is safe: a compromised executor lying with
            # 'executor' would only leave an orphan object in storage, and lying with
            # 'minio' would produce a broken download. Neither exposes another
            # tenant's data, which is what _derive_s3_key exists to prevent.
            local = (
                item.get("content_location") == "executor"
                or bool(item.get("local_fallback"))
            )

            s3_key = _derive_s3_key(
                "artifacts", run.workspace_id, run.task_id, item.get("filename", "")
            )
            if not s3_key:
                logger.warning(
                    "run %s / node %s: artefato com filename invalido ('%s') — ignorado.",
                    run.task_id, node_id, item.get("filename", ""),
                )
                continue
            # The displayed name must be the SAME as the key's last segment: if
            # sanitizing changed something, showing the raw name would make the UI
            # promise a download that does not exist under that name.
            filename = s3_key.rsplit("/", 1)[-1]
            if (node_id, filename) in known:
                continue
            known.add((node_id, filename))

            pendentes.append({
                "node_id":  node_id,
                "item":     item,
                "s3_key":   s3_key,
                "filename": filename,
                "local":    local,
                "context":  item.get("context") or "artifacts",
            })
    return pendentes


async def _resolver_em_lote(db, run: WorkflowRun, pendentes: list[dict]) -> _Resolucao:
    """Phase 2: resolve database and storage in batch.

    The executor returns the id_hash of the row that /drive/executor-upload-url
    created OR reused. It is the reliable guard; the lookup by s3_key does not
    work for the overwrite case.

    The key used here is DERIVED from the run's task_id (see _derive_s3_key, and
    the SEC note in the _register_artifacts docstring: the key coming from the
    executor is ignored on purpose). When the upload overwrote an existing file,
    the row kept the ORIGINAL s3_key — from an old run — and the derived one does
    not match it. The guard then found nothing and a new row was born on every
    execution, pointing to a key where the PUT never wrote. On the following run
    that orphan was the newest in the workspace, became the overwrite target,
    and the cycle repeated.
    """
    from app.models.workspace_file import WorkspaceFile

    drive_pendentes = [p for p in pendentes if p["context"] == "drive"]
    drive_ids = {
        p["item"]["drive_file_id"] for p in drive_pendentes if p["item"].get("drive_file_id")
    }

    linhas_por_id: dict[str, WorkspaceFile] = {}
    if drive_ids:
        res = await db.execute(
            select(WorkspaceFile).where(
                WorkspaceFile.id_hash.in_(drive_ids),
                # Confirm in the DATABASE that the row exists and belongs to this workspace:
                # the id comes from the executor, so it is not valid on its own. If it
                # does not match, follow the normal flow.
                WorkspaceFile.workspace_id == run.workspace_id,
            )
        )
        linhas_por_id = {linha.id_hash: linha for linha in res.scalars().all()}

    keys_ja_no_drive: set[str] = set()
    if drive_pendentes:
        # Safety net for paths that did not go through executor-upload-url.
        res = await db.execute(
            select(WorkspaceFile.s3_key).where(
                WorkspaceFile.s3_key.in_([p["s3_key"] for p in drive_pendentes])
            )
        )
        keys_ja_no_drive = set(res.scalars().all())

    # Decide each item's destination BEFORE going to storage: that way the HEADs
    # only happen for what actually becomes a new row.
    a_criar: list[dict] = []
    # (linha, acao) — a acao distingue arquivo novo de sobrescrita.
    drive_existentes: list[tuple[WorkspaceFile, str]] = []
    for p in pendentes:
        if p["context"] != "drive":
            a_criar.append(p)
            continue
        linha = linhas_por_id.get(p["item"].get("drive_file_id"))
        if linha is not None:
            # The row already exists, but the executor still needs to be notified:
            # `agent_confirm_upload` emits the event with exclude_agent_id=<executor
            # that uploaded>, and there is a single target_executor_id per workspace —
            # usually the same one. The event dies there. That is correct for
            # GeoSync, which uploads what it already has on disk (uploader.py uses the
            # SAME endpoint, so the server does not tell the origins apart), but not
            # for a run artifact: the DataOutput produced the file in memory and the
            # executor does not have it locally. Without this emission, a workspace
            # with SYNC_MODE download/bidirectional stops receiving the file.
            drive_existentes.append(
                (linha, "file_updated" if p["item"].get("drive_reused") else "file_created")
            )
            continue
        if p["s3_key"] in keys_ja_no_drive:
            continue  # Already registered by executor-upload-url/confirm
        a_criar.append(p)

    tamanhos = await _head_sizes([p["s3_key"] for p in a_criar if not p["local"]])
    return _Resolucao(a_criar=a_criar, drive_existentes=drive_existentes, tamanhos=tamanhos)


async def _persistir_artefatos(
    db, run: WorkflowRun, resolucao: _Resolucao, *, expires_at, executor_id: str | None,
) -> list[tuple]:
    """Phase 3: build the rows and persist with a single commit.

    Returns the NEW Drive files that have an object in storage, as
    (WorkspaceFile, "file_created"), for the notification to the executors.
    """
    from app.models.workspace_file import WorkspaceFile

    novos_no_drive: list[tuple[WorkspaceFile, str]] = []
    for p in resolucao.a_criar:
        item, s3_key, filename = p["item"], p["s3_key"], p["filename"]

        if p["local"]:
            # The executor reports the size: there is no object to query, and a
            # HEAD here would fail for every local artifact, polluting the log with
            # one WARNING per execution.
            bruto = item.get("size_bytes")
            size_bytes = bruto if isinstance(bruto, int) and bruto >= 0 else None
        else:
            size_bytes = resolucao.tamanhos.get(s3_key)

        if p["context"] == "drive":
            # Destination: Workspace Drive (syncs with executors)
            ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
            mime = "application/geo+json" if ext == "geojson" else "application/json"
            if p["local"]:
                # The upload to the Drive failed and fell back to local: the bytes are
                # on the executor's disk and never reached MinIO. A 'confirmed'
                # WorkspaceFile with the derived s3_key would give a 404 download — and
                # size_bytes would make it look even more real. It is registered as
                # a CATALOG entry (content_location='executor', no s3_key), the same
                # representation as /drive/executor-register: it shows up in the Drive
                # with the local badge and no download, instead of a button that
                # breaks. It does NOT go into the notifications — there is no object
                # for another executor to download.
                wf = WorkspaceFile(
                    workspace_id        = run.workspace_id,
                    s3_key              = None,
                    original_name       = filename,
                    extension           = ext,
                    mime_type           = mime,
                    size                = size_bytes,
                    uploaded_by         = executor_id,
                    status              = "confirmed",
                    content_location    = "executor",
                    content_executor_id = executor_id,
                )
                db.add(wf)
            else:
                wf = WorkspaceFile(
                    workspace_id  = run.workspace_id,
                    s3_key        = s3_key,
                    original_name = filename,
                    extension     = ext,
                    mime_type     = mime,
                    size          = size_bytes,
                    uploaded_by   = executor_id,
                    status        = "confirmed",
                )
                db.add(wf)
                novos_no_drive.append((wf, "file_created"))
        else:
            # Destino: tabela Artifact (disponivel via API de artefatos)
            db.add(Artifact(
                workspace_id     = run.workspace_id,
                workflow_hash    = run.workflow_hash,
                run_id           = run.task_id,
                node_id          = p["node_id"],
                output_key       = item.get("output_key", ""),
                filename         = filename,
                format           = item.get("format"),
                size_bytes       = size_bytes,
                features         = item.get("features"),
                # A local artifact has no object: writing the derived key would make
                # the UI offer a download that would answer 404 from MinIO.
                s3_key           = None if p["local"] else s3_key,
                content_location = "executor" if p["local"] else "minio",
                # Derived, never what the executor sent — see the note above.
                local_path       = (
                    f"{run.workspace_id}/{run.task_id}/{filename}" if p["local"] else None
                ),
                executor_id      = executor_id,
                credential_id    = item.get("credential_id") or None,
                is_published     = item.get("is_published", False),
                publish_config   = item.get("publish_config"),
                expires_at       = expires_at,
            ))

    # No new row means nothing to commit — the redelivery case, where everything
    # was already registered, no longer pays for a pointless transaction.
    if resolucao.a_criar:
        await db.commit()
    return novos_no_drive


async def _avisar_drive(drive_files: list[tuple]) -> None:
    """Notify executors about files added to the Drive.

    Runs after the commit: a notification that fails becomes a WARNING and does
    not prevent the following ones — the rows are already written.
    """
    from app.core.drive_events import emit_drive_event

    for wf, acao in drive_files:
        try:
            await emit_drive_event(
                workspace_id=wf.workspace_id,
                action=acao,
                file_info={
                    "id_hash": wf.id_hash,
                    "original_name": wf.original_name,
                    "extension": wf.extension,
                    "size": wf.size or 0,
                    # GeoSync uses the md5 to decide whether it needs to re-download the
                    # file; without it, every overwrite forces a download.
                    "content_md5": wf.content_md5,
                },
            )
        except Exception as exc:
            logger.warning("Falha ao notificar Drive para '%s': %s", wf.original_name, exc)


async def account_terminal_run(
    db, run: WorkflowRun, stats: dict | None = None, *, first_close: bool = True
) -> None:
    """Account in usage_daily for a run closed OUTSIDE the consumer.

    The run_results queue is fed by a single point (`_handle_job_result` in the
    WS router), but there are paths that write a terminal status directly to
    Postgres and never go through it: dispatch failure, a run cancelled before
    reaching an executor and the disconnected-executor watchdog. Without this
    helper those runs were left out of `total_runs`/`failed_runs` — the dashboard
    showed the workspace healthier than it is, and billing undercharged.

    Call it AFTER writing the terminal status (the classification reads
    `run.status`) and only when the transition really was pending/running ->
    terminal. Failing here must not bring down the caller: closing the run is
    more important than the aggregate, and swallowing the exception here avoids
    masking the original error that led to the run being closed.
    """
    try:
        await _upsert_usage_daily(db, run, stats or {}, first_close)
    except Exception as exc:
        logger.error(
            "run %s: falha ao contabilizar usage_daily fora do consumer: %s",
            run.task_id, exc, exc_info=exc,
        )
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.debug("Rollback apos falha de usage_daily: %s", rb_exc)


async def _upsert_usage_daily(db, run: WorkflowRun, stats: dict, first_close: bool) -> None:
    """Account for the run in the workspace's daily usage aggregate.

    This upsert used to live INSIDE _persist_metrics, which only runs when the
    executor sends '__metrics__'. Since the failure path produced no metrics,
    NO failure was ever counted and the dashboard showed a 0% error rate
    forever. Now it runs for every item of the run_results queue, with the run's
    actual status (success/failed/cancelled), even without metrics — in that case
    the resource counters go in as zero, but the run shows up in the total and in
    the error rate.

    The queue is NOT a synonym for "every run that finishes": closes done directly
    in Postgres come in through `account_terminal_run`, not through here.

    `first_close` is the idempotence guard: it only counts on the first
    pending/running -> terminal transition. Redeliveries do not inflate billing.
    """
    from app.models.run_metrics import UsageDaily
    from sqlalchemy import update as sa_update

    if not first_close:
        logger.debug("run %s: resultado reentregue — usage_daily nao recontado.", run.task_id)
        return
    if not run.workspace_id:
        # usage_daily.workspace_id is NOT NULL — a run without a workspace has nobody
        # to be attributed to in the aggregate.
        return

    run_data = ((stats or {}).get("__metrics__") or {}).get("run") or {}

    duration_ms = (
        _numero_finito(run_data.get("duration_ms"))
        or _numero_finito((run.duration_seconds or 0) * 1000)
    )
    cpu_avg = _numero_finito(run_data.get("cpu_avg_pct"))
    mem_avg = _numero_finito(run_data.get("mem_avg_mb"))
    duration_s = duration_ms / 1000

    # A run cancelled by the user is neither a success nor a failure: counting it as
    # a failure would inflate the workspace's error rate with a deliberate decision.
    _success = run.status == "success"
    _cancelled = run.status == "cancelled"

    # The date in UTC, like the rest of the pipeline (`run.end_time`, metrics).
    # Previously `date.today()` used the container's local time zone, shifting the
    # count to the wrong day near midnight.
    today = utc_now_naive().date()

    # This run's contribution, as a column -> increment map. It serves both the
    # atomic UPDATE (sum in SQL) and the values of the first row (INSERT).
    incrementos = {
        "total_runs": 1,
        "successful_runs": 1 if _success else 0,
        "failed_runs": 0 if (_success or _cancelled) else 1,
        "total_cpu_seconds": cpu_avg * duration_s / 100,
        "total_mem_mb_seconds": mem_avg * duration_s,
        "total_duration_ms": duration_ms,
        "total_input_bytes": _numero_finito(run_data.get("input_bytes")),
        "total_output_bytes": _numero_finito(run_data.get("output_bytes")),
        "total_features": _numero_finito(run_data.get("total_features")),
        "total_nodes_executed": _numero_finito(run_data.get("nodes_executed")),
    }

    async def _incrementar() -> int:
        # Atomic UPDATE (`coluna = coluna + delta` in SQL), not the earlier
        # read-modify-write in Python: the increment is not lost when the
        # consumer and a concurrent `account_terminal_run` (separate sessions)
        # close runs of the same workspace/day at the same time.
        result = await db.execute(
            sa_update(UsageDaily)
            .where(
                UsageDaily.date == today,
                UsageDaily.workspace_id == run.workspace_id,
            )
            .values({
                getattr(UsageDaily, coluna): getattr(UsageDaily, coluna) + delta
                for coluna, delta in incrementos.items()
            })
        )
        return result.rowcount or 0

    if await _incrementar() == 0:
        # The day's row does not exist yet: create it. SAVEPOINT (not a loose `try`):
        # with UniqueConstraint(date, workspace_id), two sessions read "does not
        # exist" at the same time and the second INSERT violates the constraint — in
        # Postgres that would poison the whole transaction. The savepoint isolates
        # the failure (same pattern as `_upsert_pin_artifact`); whoever loses the
        # INSERT race retries the atomic UPDATE on the row the winner created.
        try:
            async with db.begin_nested():
                db.add(UsageDaily(date=today, workspace_id=run.workspace_id, **incrementos))
                await db.flush()
        except IntegrityError:
            if await _incrementar() == 0:  # pragma: no cover - the winning row vanished midway
                raise

    await db.commit()
    logger.debug("run %s: usage_daily atualizado (status=%s).", run.task_id, run.status)


def _ip_do_payload(payload: dict) -> str | None:
    """The result's `executor_ip`, only if it is an IP that fits the column (45)."""
    return _ip_valido(payload.get("executor_ip"))


def _ip_valido(valor) -> str | None:
    """The IP in canonical form, or None.

    The `run_results` queue also receives payloads from outside the WebSocket
    (reprocessed dead letter, redis-cli): anything that is not an IP becomes None.
    So does IPv6 with a zone (`fe80::1%eth0`): the zone is free text, of any
    length, and would overflow the VARCHAR(45) — the INSERT would fail and the
    run would lose its metrics.
    """
    if not isinstance(valor, str):
        return None
    try:
        endereco = ipaddress.ip_address(valor.strip())
    except ValueError:
        return None
    if getattr(endereco, "scope_id", None):
        return None
    texto = str(endereco)
    return texto if len(texto) <= 45 else None


async def _persist_metrics(db, run: WorkflowRun, metrics: dict, payload: dict) -> None:
    """Persist execution metrics in the workflow_run_metrics and node_run_metrics tables.

    The usage_daily aggregate is NOT written here — it was extracted into
    _upsert_usage_daily, which always runs (with or without metrics).

    Exceptions propagate to _run_phase, which logs and rolls back: swallowing them
    here (as before) left the session invalid and took down artifacts, pins and
    webhook in cascade.
    """
    from app.models.run_metrics import WorkflowRunMetrics, NodeRunMetrics

    # The same sanitizing as node_stats, now on the whole dictionary: the bbox of
    # node_run_metrics and the spatial_summary/operation_types of
    # workflow_run_metrics are JSON columns, and a NaN coming from ANY metric
    # made Postgres reject the INSERT ("Token NaN is invalid") — 37 results
    # ended up in the dead-letter queue because of it before the collector's
    # `_bbox_finito`. Here it does not depend on the executor being up to date.
    metrics = _json_seguro(metrics or {})
    run_data = metrics.get("run", {})
    nodes_data = metrics.get("nodes", {})
    spatial_summary = metrics.get("spatial_summary")

    if not run.workspace_id:
        # workflow_run_metrics.workspace_id e NOT NULL.
        logger.warning("run %s sem workspace_id — metricas nao persistidas.", run.task_id)
        return

    # Idempotence: run_id is UNIQUE in workflow_run_metrics; a redelivery
    # would raise IntegrityError and kill the following phases.
    exists = await db.execute(
        select(WorkflowRunMetrics.id).where(WorkflowRunMetrics.run_id == run.task_id)
    )
    if exists.scalar_one_or_none() is not None:
        logger.debug("run %s: metricas ja persistidas — ignorando reentrega.", run.task_id)
        return

    # Busca dados do executor (nome e IP)
    _agent_id = run.host.replace("executor:", "") if run.host and run.host.startswith("executor:") else None
    _agent_name = None
    _agent_ip = None
    if _agent_id:
        from app.models.executor import Executor
        _ag_result = await db.execute(
            select(Executor.name).where(Executor.id_hash == _agent_id)
        )
        _agent_name = _ag_result.scalar_one_or_none()
        # The IP comes in the payload, written by the worker holding the WebSocket.
        # This consumer runs on any of the four workers: the local registry
        # is only used when the payload does not carry a valid IP (result
        # queued before this field existed, reprocessed dead letter) —
        # and it is only right when this worker holds the executor's connection.
        _agent_ip = _ip_do_payload(payload)
        if _agent_ip is None:
            try:
                from app.core.executor_connections import executor_registry
                _conn = executor_registry.get(_agent_id)
                if _conn:
                    _agent_ip = _ip_valido(_conn.executor_ip)
            except Exception as exc:
                # In-memory registry: failing here does not justify losing the metric.
                logger.warning("Falha ao obter IP do executor '%s': %s", _agent_id, exc)

    # ── workflow_run_metrics ─────────────────────────────────────────────────
    wrm = WorkflowRunMetrics(
        run_id=run.task_id,
        workflow_hash=run.workflow_hash,
        workspace_id=run.workspace_id,
        executor_id=_agent_id,
        executor_name=_agent_name,
        executor_ip=_agent_ip,
        user_id=None,
        started_at=run.start_time,
        ended_at=run.end_time,
        duration_ms=run_data.get("duration_ms") or (run.duration_seconds * 1000 if run.duration_seconds else None),
        cpu_avg_pct=run_data.get("cpu_avg_pct"),
        cpu_peak_pct=run_data.get("cpu_peak_pct"),
        mem_avg_mb=run_data.get("mem_avg_mb"),
        mem_peak_mb=run_data.get("mem_peak_mb"),
        input_bytes=run_data.get("input_bytes", 0),
        output_bytes=run_data.get("output_bytes", 0),
        total_features=run_data.get("total_features", 0),
        nodes_executed=run_data.get("nodes_executed", 0),
        nodes_failed=run_data.get("nodes_failed", 0),
        nodes_cached=run_data.get("nodes_cached", 0),
        operation_types=run_data.get("operation_types"),
        spatial_summary=spatial_summary,
        status=run.status,
        # error_category comes from the flow error taxonomy (published by the WS
        # router). The previous code wrote type(str).__name__ — always "str",
        # which made the column useless for grouping failures.
        error_type=payload.get("error_category") or ("error" if run.error_message else None),
    )
    db.add(wrm)

    # ── node_run_metrics ─────────────────────────────────────────────────────
    for nid, nm in nodes_data.items():
        nrm = NodeRunMetrics(
            run_id=run.task_id,
            node_id=nid,
            node_name=nm.get("node_name", ""),
            node_type=nm.get("node_type"),
            duration_ms=nm.get("duration_ms"),
            cpu_avg_pct=nm.get("cpu_avg_pct"),
            mem_peak_mb=nm.get("mem_peak_mb"),
            input_bytes=nm.get("input_bytes", 0),
            output_bytes=nm.get("output_bytes", 0),
            input_features=nm.get("input_features"),
            output_features=nm.get("output_features"),
            geometry_type=next(iter((nm.get("spatial") or {}).get("geometry_types", {}).keys()), None),
            crs=(nm.get("spatial") or {}).get("crs"),
            bbox=(nm.get("spatial") or {}).get("bbox"),
            vertex_count=(nm.get("spatial") or {}).get("vertex_count"),
            status=nm.get("status", "unknown"),
            cache_hit=nm.get("cache_hit", False),
            error_message=nm.get("error"),
        )
        db.add(nrm)

    await db.commit()
    logger.debug("run %s: metricas persistidas.", run.task_id)


async def _consume_one(r: aioredis.Redis, queue: str, handler) -> None:
    """Read one item from the queue and call the handler. Manages retry and dead letter."""
    item = await r.brpop(queue, timeout=2)
    if not item:
        return

    raw = item[1]
    try:
        # The job_result `stats` goes up to ~4MB; the dumps is already offloaded in the
        # producer, and the loads of a large payload also freezes the event loop
        # (the consumer runs on the worker's same loop). Above the threshold, to a thread.
        if len(raw) > _JSON_OFFLOAD_THRESHOLD:
            payload = await asyncio.to_thread(json.loads, raw)
        else:
            payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Payload inválido na fila %s: %s — %s", queue, raw[:200], exc)
        await r.lpush(QUEUE_DEAD_LETTER, raw)
        return

    try:
        async with AsyncSessionLocal() as db:
            ok = await handler(db, payload)

        if ok is False:
            # run_result arrived before run_create was processed
            retries = payload.get("_retry", 0) + 1
            if retries > _MAX_RESULT_RETRIES:
                logger.error(
                    "run_result descartado após %d tentativas: task_id=%s",
                    _MAX_RESULT_RETRIES, payload.get("task_id"),
                )
                await r.lpush(QUEUE_DEAD_LETTER, json.dumps(payload))
            else:
                payload["_retry"] = retries
                await asyncio.sleep(0.5)
                await r.lpush(queue, json.dumps(payload))

    except PhaseFailure as exc:
        # The main run was already closed; what was missing were auxiliary effects.
        # There is nothing to retry automatically (the status is already terminal),
        # but the annotated payload needs to remain somewhere: it is the only clue
        # that the run was left without artifact/metric/webhook. Manual reprocessing
        # is safe — usage_daily has the first_close guard and the other phases are
        # idempotent by key.
        logger.error("Item da fila %s parcialmente processado: %s", queue, exc)
        await r.lpush(
            QUEUE_DEAD_LETTER,
            json.dumps({**payload, "_phases_failed": exc.labels}),
        )

    except Exception as exc:
        logger.error(
            "Falha ao processar item da fila %s (task_id=%s): %s",
            queue, payload.get("task_id"), exc,
        )
        await r.lpush(QUEUE_DEAD_LETTER, raw)


# Exponential backoff for reconnecting to Redis: 1s, 2s, 4s, 8s, 16s, 30s (cap)
_RECONNECT_DELAYS = [1, 2, 4, 8, 16, 30]


async def run_consumer_loop() -> None:
    """
    Main loop — started as a background task in the API lifespan.
    Processes run_results (the run_creates queue was eliminated — runs are created
    synchronously in _dispatch_job).

    Resilience to Redis failures: if the connection drops, it reconnects with
    exponential backoff instead of dying and requiring a manual API restart.
    Cancellation propagates normally via CancelledError.
    """
    attempt = 0
    while True:
        r = None
        try:
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            # Ping to validate the connection before logging 'iniciado' (started)
            await r.ping()
            logger.info("Consumer run_results iniciado." if attempt == 0
                        else "Consumer run_results reconectado (tentativa %d)." % attempt)
            attempt = 0
            while True:
                await _consume_one(r, QUEUE_RESULTS, _process_result)
        except asyncio.CancelledError:
            # API shutdown — propagate without reconnecting
            logger.info("Consumer run_results encerrado (cancelado).")
            return
        except RedisConnectionError as exc:
            delay = com_jitter(_RECONNECT_DELAYS[min(attempt, len(_RECONNECT_DELAYS) - 1)])
            attempt += 1
            logger.warning(
                "Consumer: conexao Redis perdida (%s). Reconectando em %.1fs (tentativa %d).",
                exc, delay, attempt,
            )
            await asyncio.sleep(delay)
        except Exception as exc:
            # Erro inesperado: loga e reconecta. Nao mata o loop.
            delay = com_jitter(_RECONNECT_DELAYS[min(attempt, len(_RECONNECT_DELAYS) - 1)])
            attempt += 1
            logger.error(
                "Consumer: erro inesperado (%s). Reiniciando em %.1fs.", exc, delay,
            )
            await asyncio.sleep(delay)
        finally:
            if r is not None:
                try:
                    await r.aclose()
                except Exception as exc:
                    logger.debug("Falha ao fechar conexao Redis do consumer: %s", exc)
