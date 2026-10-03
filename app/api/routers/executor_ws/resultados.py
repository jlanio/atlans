# app/api/routers/executor_ws/resultados.py
"""
Run results and events: run→executor authorization, writing the
job_result, publishing node_events and sync events.
"""
import asyncio
import json
import time
from dataclasses import dataclass

from app.core.utils.logger import get_logger

from sqlalchemy import select

from app.core.executor_connections import executor_registry
from app.core.constants import REDIS_TTL_1H
from app.core.db import get_session_async
# Owner of the history/channel keys, of the pipeline that writes events and of
# the `__workflow_complete__` JSON. Through the module, as in `fechamento_de_run`.
from app.services import run_events_service
from flow.utils.protocolo_ws import (
    STATS_CONTROLE_DESCARTADO,
    STATS_TAMANHO_ORIGINAL,
    STATS_TRUNCADO,
)
from flow.utils.publisher.reducao import (
    TETO_NODE_EVENT_BYTES,
    TETO_POR_CAMPO,
    reduzir_node_event,
)

logger = get_logger(__name__)

from .protocolo import (
    _JOB_RESULT_RATE_LIMIT,
    _MAX_SYNC_EVENT_BYTES,
    _RATE_WINDOW,
    _cap_job_result,
    _coerce_gauge,
    _rate_allowed,
)

def _desfecho(job_status: str, is_cancelled: bool, *, ok: str) -> str:
    """Translates a job's outcome into the reader's vocabulary.

    The fall-through (`cancelled` before `failed`) is the same in both consumers
    and was copied in two places in this file; the real difference is only the
    name of the success case — the `WorkflowRun` row says "success", the panel's
    lifecycle event says "completed" —, which is why it is an explicit parameter
    and not a default.

    The ORDER matters: a cancelled job arrives with status != "ok", and testing
    `is_cancelled` after "ok" and before "failed" is what prevents a
    cancellation from being reported to the user as a failure.
    """
    if job_status == "ok":
        return ok
    return "cancelled" if is_cancelled else "failed"

# TTLs of the run→executor authorization memo (see _run_belongs_to_agent).
# Positive is long because the run→host binding is IMMUTABLE after dispatch;
# negative is short so that a malicious executor in a loop does not generate a
# SELECT per attempt and, at the same time, a binding created right after is seen.
_RUN_AUTH_TTL_OK = 3600.0

_RUN_AUTH_TTL_DENY = 5.0

_RUN_AUTH_CACHE_MAX = 2048

# Wait ceiling for the authorization query. Waiting POOL_TIMEOUT (30s) for a
# pool connection on the WS hot path is never the right answer: the receive
# loop stalls, the heartbeat is not read and the server drops a healthy
# executor on timeout — and then `_fail_orphan_runs` kills runs that were alive.
_RUN_AUTH_QUERY_TIMEOUT = 3.0

# Degraded-database circuit breaker. The `None` verdict (DB failure) is not
# memoized on purpose — it is transient —, but without any lock each node_event
# in a burst opened a new session and could wait for the whole pool.
# During the cooldown we deny right away, at zero cost: the same verdict as today.
#
# Applies ONLY to node_event. The job_result ignores the cooldown (see
# `_handle_job_result`): it is business data, it is not resent by the executor
# and losing it leaves the run hanging — it cannot fall victim to a lock created
# to contain telemetry.
_RUN_AUTH_DB_COOLDOWN = 2.0

# Retries of the run read on the job_result path. Covers a short failover
# (pgbouncer restarting, replica switching) without turning the drainer into a
# queue of long waits.
_JOB_RESULT_DB_RETRIES = 3

_JOB_RESULT_DB_RETRY_DELAY = 0.25

# Above this frame size, the job_result serializations go to a thread: a
# multi-MB `stats` froze the worker's ENTIRE event loop (other executors stopped
# being read, in-flight HTTP requests stalled) for tens of ms. Below it, the
# to_thread overhead would be larger than the dumps itself.
_JSON_OFFLOAD_THRESHOLD = 256 * 1024

async def _dumps(obj, *, offload: bool) -> str:
    """json.dumps that leaves the event loop when the payload is large.

    A multi-MB `stats` serialized inline stopped the WHOLE worker — other
    executors were no longer read and in-flight HTTP requests stalled along with
    it. For a small payload the to_thread cost would be larger than the dumps
    itself, hence the explicit switch instead of an internal heuristic.
    """
    if offload:
        return await asyncio.to_thread(json.dumps, obj)
    return json.dumps(obj)

async def _register_webhook_response_artifact(run_id: str, executor_id: str, body_ref: dict) -> None:
    """Creates an Artifact row for a webhook body stored in MinIO, with expires_at
    based on artifact_retention_days (same policy as the other artifacts).

    The global cleanup (app/core/artifact_cleanup.py) removes the MinIO object and
    the DB row when expires_at is reached. The webhook_router tries to delete it
    right after streaming; this record is the safety net for orphans.
    """
    from datetime import timedelta
    from app.core.run_result_consumer import _get_retention_days
    from app.core.utils.datetime_utils import utc_now_naive
    from app.models.artifact import Artifact
    from app.models.models import WorkflowRun

    s3_key = body_ref.get("s3_key")
    if not s3_key:
        return

    async with get_session_async() as db:
        run_res = await db.execute(
            select(WorkflowRun).where(WorkflowRun.task_id == run_id)
        )
        run = run_res.scalar_one_or_none()
        workspace_id = run.workspace_id if run else None
        workflow_hash = run.workflow_hash if run else None

        if not workspace_id:
            logger.warning("Webhook response sem workspace_id (run=%s) — artifact não registrado.", run_id)
            return

        # The s3_key comes RAW from the executor, which is a machine under the
        # user's control. Without this guard, an executor answered with
        # `body_ref.s3_key = "drive/<workspace_alheio>/<arquivo>"` and the server
        # created an Artifact — with no credential_id, hence PUBLIC download —
        # pointing to another tenant's object; the expires_at even made the
        # purge delete it later. Same vector run_result_consumer already closes
        # for pins and node artifacts; this path had been left out.
        from fastapi import HTTPException
        from app.api.routers.executor_drive_router import _validate_agent_s3_key
        try:
            _validate_agent_s3_key(s3_key, [workspace_id])
        except HTTPException as exc:
            logger.warning(
                "Webhook response com s3_key rejeitada (%s) do executor %s no run %s: %s",
                exc.detail, executor_id, run_id, s3_key,
            )
            return

        retention_days = await _get_retention_days(db)
        expires_at = (
            utc_now_naive() + timedelta(days=retention_days)
            if retention_days else None
        )

        artifact = Artifact(
            workspace_id=workspace_id,
            workflow_hash=workflow_hash,
            run_id=run_id,
            node_id=None,
            output_key="__webhook_response__",
            filename=s3_key.rsplit("/", 1)[-1],
            format=None,
            size_bytes=body_ref.get("size"),
            s3_key=s3_key,
            executor_id=executor_id,
            expires_at=expires_at,
        )
        db.add(artifact)
        await db.commit()

async def _record_job_ack(executor_id: str, job_id: str | None, status: str) -> None:
    """Receipt confirmation: removes the job from those pending ACK and promotes
    the run from 'pending' to 'running'.

    Called when the executor sends {type: "ack", job_id, status}. The absence
    of an ACK after send_job is tracked via executor_registry.overdue_acks().

    The PROMOTION is what closes the hole of the run stuck in "Na fila" (queued):
    dispatch only writes 'running' after `send_job` returns, so a worker that
    dies in that window left 'pending' forever a job the executor received and
    is running. The ACK is the proof of delivery coming from the other side — and
    it arrives through any worker, even after the death of the one that
    dispatched. The UPDATE is conditional ('pending' and this executor's host): it
    does not resurrect a cancelled or terminal run, and an ACK from another
    executor promotes nothing.

    SEC: the ACK only clears jobs dispatched to THIS executor. Without the
    binding, any executor could confirm another's job and blind the lost-jobs
    monitor.
    """
    if not job_id:
        return
    who = await executor_registry.clear_pending_ack(job_id, expected_executor_id=executor_id)
    if who:
        logger.debug("ACK recebido: job=%s status=%s executor=%s", job_id, status, who)
    # The promotion is one UPDATE + COMMIT in Postgres per ACK: without a ceiling, a
    # buggy (or hostile) executor would tie up a database connection in a loop. The
    # ceiling is the job_result's — one ACK per job, far below that in honest
    # traffic. An ACK above it only loses the promotion; the inventory does it the
    # next minute.
    if not _rate_allowed(executor_id, "ack", _JOB_RESULT_RATE_LIMIT):
        return
    try:
        await _promover_para_running(executor_id, job_id)
    except Exception as exc:
        # Best-effort: a live dispatch promotes on its own, and the undelivered
        # sweep closes whatever is left behind.
        logger.warning(
            "ACK do job '%s' (executor '%s'): falha ao promover para 'running': %s",
            job_id, executor_id, exc,
        )


async def _promover_para_running(executor_id: str, job_ids) -> int:
    """'pending' → 'running' for jobs THIS executor confirmed it has. Returns
    how many runs changed.

    Conditional on status and host: a cancelled run, a terminal one or one
    dispatched to another executor stays as it is.
    """
    from sqlalchemy import update as sa_update

    from app.models.models import WorkflowRun

    ids = [job_ids] if isinstance(job_ids, str) else list(job_ids)
    if not ids:
        return 0
    async with get_session_async() as db:
        result = await db.execute(
            sa_update(WorkflowRun)
            .where(
                WorkflowRun.task_id.in_(ids),
                WorkflowRun.status == "pending",
                WorkflowRun.host == f"executor:{executor_id}",
            )
            .values(status="running")
            .execution_options(synchronize_session=False)
        )
        await db.commit()
    if result.rowcount:
        logger.info(
            "Executor '%s' confirmou %d job(s) ainda em 'pending' — promovidos para 'running'.",
            executor_id, result.rowcount,
        )
    return result.rowcount or 0

async def _query_run_belongs_to_agent(executor_id: str, run_id: str) -> bool | None:
    """SELECT that checks WorkflowRun.host == 'executor:{executor_id}'.

    Returns True/False, or None when the query itself failed (DB error) —
    the caller treats it as denied, but does NOT memoize a result that came from
    a transient unavailability.

    FAIL-CLOSED: a nonexistent run or one with a NULL host is rejected. The
    previous version returned True in those cases ("benefit of the doubt"),
    inherited from when the run's INSERT was asynchronous via a Redis queue. Since
    the dispatcher now persists run + host synchronously before sending the job,
    that fail-open became pure attack surface: it allowed any executor to claim
    another tenant's run during the window in which host was still NULL.
    """
    from app.models.models import WorkflowRun
    try:
        async with get_session_async() as db:
            result = await db.execute(
                select(WorkflowRun.host).where(WorkflowRun.task_id == run_id)
            )
            host = result.scalar_one_or_none()
            if host is None:
                logger.warning(
                    "WS event auth: run=%s inexistente ou sem host atribuído — "
                    "evento do executor '%s' descartado (fail-closed).",
                    run_id, executor_id,
                )
                return False
            expected = f"executor:{executor_id}"
            ok = host == expected
            if not ok:
                logger.warning(
                    "WS event auth mismatch: run=%s expected_host=%s actual_host=%s "
                    "— node_event será descartado (causa comum de canvas sem feedback).",
                    run_id, expected, host,
                )
            return ok
    except Exception as exc:
        # On DB failure, fail-closed to protect against cross-tenant access.
        logger.error("Erro ao validar propriedade de run '%s' pelo executor '%s': %s", run_id, executor_id, exc)
        return None

def _store_run_auth(cache: dict, run_id: str, authorized: bool, now: float) -> None:
    """Memoriza o veredito com TTL, mantendo o cache limitado."""
    if len(cache) >= _RUN_AUTH_CACHE_MAX:
        # A malicious executor can make up run_ids at will: purges the expired ones
        # and, if still full, drops the entries closest to expiring.
        for key, (_ok, deadline) in list(cache.items()):
            if deadline <= now:
                cache.pop(key, None)
        while len(cache) >= _RUN_AUTH_CACHE_MAX:
            cache.pop(min(cache, key=lambda k: cache[k][1]), None)
    ttl = _RUN_AUTH_TTL_OK if authorized else _RUN_AUTH_TTL_DENY
    cache[run_id] = (authorized, now + ttl)

async def _run_belongs_to_agent(executor_id: str, run_id: str) -> bool:
    """Validates that the WorkflowRun belongs to the executor_id that is reporting.

    Prevents cross-tenant injection: a compromised executor cannot manipulate
    another tenant's/workspace's runs by sending a job_result or node_event with
    an arbitrary run_id. The dispatcher sets WorkflowRun.host = f"executor:{executor_id}"
    BEFORE send_job, so authorship is always verifiable.

    PERF: the verdict is memoized ON THE executor's CONNECTION. Before, there was
    a session + SELECT + teardown PER EVENT to revalidate a run→host binding that
    is IMMUTABLE after dispatch — with POOL_PRE_PING that is ~2 round-trips per
    event, so a 100-node workflow cost 400-600 round-trips and 200-300 pool
    checkouts, SERIALIZED in the receive loop (job_result and heartbeat sat in
    the queue behind the events).

    The memo is NOT a bypass: it only stores the result of a check already
    performed for THAT PAIR (executor_id, run_id) — it lives inside the
    `ExecutorConnection`, so it never crosses executors and disappears on
    unregister. NEGATIVE verdicts are memoized too (short TTL) so that a
    malicious executor in a loop does not generate a SELECT per attempt.
    """
    conn = executor_registry.get(executor_id)
    cache = conn.run_auth_cache if conn is not None else None
    now = time.monotonic()

    if cache is not None:
        memo = cache.get(run_id)
        if memo is not None and memo[1] > now:
            return memo[0]

    # Degraded database: denies without opening a session. See `_RUN_AUTH_DB_COOLDOWN`.
    if conn is not None and conn.db_auth_cooldown_until > now:
        return False

    try:
        verdict = await asyncio.wait_for(
            _query_run_belongs_to_agent(executor_id, run_id), _RUN_AUTH_QUERY_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Autorização do run '%s' (executor '%s') não respondeu em %.1fs — "
            "evento descartado (fail-closed).",
            run_id, executor_id, _RUN_AUTH_QUERY_TIMEOUT,
        )
        verdict = None
    if verdict is None:
        # DB error/timeout: denies now and opens the cooldown so that the next
        # burst does not turn into N pool checkout attempts.
        if conn is not None:
            conn.db_auth_cooldown_until = now + _RUN_AUTH_DB_COOLDOWN
        return False
    if cache is not None:
        _store_run_auth(cache, run_id, verdict, now)
    return verdict

def _forget_run_auth(executor_id: str, run_id: str) -> None:
    """Invalidates a run's memo — called when its job_result arrives."""
    conn = executor_registry.get(executor_id)
    if conn is not None:
        conn.run_auth_cache.pop(run_id, None)

async def _query_run_snapshot(run_id: str):
    """Reads the WorkflowRun's host, status and start_time in a SINGLE query.

    The job_result's three verdicts (does it belong to this executor? is it
    already terminal? how long did it take?) came from three independent
    functions, each with its own session: 3 pool checkouts + 3 pre-pings + 3
    SELECTs to read the SAME row — and the third loaded the whole ORM object,
    including `node_stats` (JSON) and `error_message` (Text) from the previous
    execution, to use only `start_time`. Under concurrency this competed for the
    pool with HTTP traffic and visibly delayed "concluído" (done) in the UI.

    Returns `(host, status, start_time)`, or None when the row does not exist.
    RAISES on database failure on purpose: the caller needs to tell "nonexistent
    run" (memoizable rejection) apart from "database down" (cooldown, no memo).
    """
    from app.models.models import WorkflowRun
    async with get_session_async() as db:
        result = await db.execute(
            select(
                WorkflowRun.host, WorkflowRun.status, WorkflowRun.start_time,
            ).where(WorkflowRun.task_id == run_id)
        )
        return result.first()

def _posse_ja_provada(executor_id: str, run_id: str) -> bool:
    """True when this connection's memo has already proven the run is this executor's.

    Serves the paths in which the job_result could not be processed and we need
    to close the run: without proof of ownership, a compromised executor could
    close another tenant's runs by sending a job_result with an arbitrary run_id
    precisely during a database outage.
    """
    conn = executor_registry.get(executor_id)
    if conn is None:
        return False
    memo = conn.run_auth_cache.get(run_id)
    return memo is not None and memo[0] and memo[1] > time.monotonic()

async def _fechar_run_inconclusivo(executor_id: str, run_id: str, motivo: str) -> None:
    """Closes as FAILED a run whose job_result could not be processed.

    WHY: the executor deletes the outbox row as soon as `send_text` returns, so
    a job_result dropped here never comes back. Without this closing the
    WorkflowRun stays in 'running' forever — the executor's presence stays
    healthy, so the `orphan_runs_watchdog` (which only acts when presence goes
    away) never reconciles —, the user's panel spins indefinitely and the
    synchronous webhook's BRPOP times out. Failed/inconclusive is bad; stuck in
    'running' is worse.

    SEC: only call it with ownership of the run by THIS executor already proven
    (`_posse_ja_provada` or a snapshot read).
    """
    from datetime import datetime as _dt, timezone as _tz

    from app.core.redis import get_redis_pool

    mensagem = f"Resultado do executor não pôde ser processado: {motivo}"
    agora = _dt.now(_tz.utc)
    try:
        resultado = json.dumps({
            "task_id":          run_id,
            "status":           "failed",
            "error_message":    mensagem,
            "error_category":   "internal",
            "retryable":        True,
            "end_time":         agora.isoformat(),
            "duration_seconds": None,
            # Empty `stats` on purpose: the consumer preserves the partial stats
            # already accumulated on the run instead of wiping them.
            "stats":            {},
        })
        # O evento carimba o MESMO instante do `end_time` acima.
        evento = run_events_service.evento_de_conclusao(
            run_id, "failed", erro=mensagem,
            extra={"error_category": "internal", "retryable": True},
            duration_ms=None, timestamp=agora.timestamp(),
        )
        webhook_key = f"webhook_response:{run_id}"
        rc = get_redis_pool()
        # All in a single pipeline: there can be no intermediate state in which the
        # database closes the run but the UI never receives the completion event.
        async with rc.pipeline(transaction=False) as pipe:
            pipe.lpush("run_results", resultado)
            run_events_service.anexar_eventos(pipe, run_id, [evento])
            # Unblocks the synchronous webhook, which otherwise waits for the whole timeout.
            pipe.lpush(webhook_key, json.dumps({
                "job_status": "error", "error": mensagem, "response": None,
            }))
            pipe.expire(webhook_key, 300)
            await pipe.execute()
        logger.error(
            "Run '%s' (executor '%s') fechado como falho — %s.",
            run_id, executor_id, motivo,
        )
    except Exception as exc:
        logger.error(
            "Run '%s': não foi possível fechar o run após perder o job_result (%s): %s",
            run_id, motivo, exc,
        )

async def _ler_snapshot_com_retentativa(run_id: str):
    """Reads the run's snapshot, insisting a little before giving up.

    The job_result path has no second chance: losing the result to a 200ms
    pgbouncer restart left the run hanging. Two short retries cover the typical
    failover without turning into a long wait inside the drainer.
    """
    ultimo_erro: Exception | None = None
    for tentativa in range(_JOB_RESULT_DB_RETRIES):
        try:
            return await asyncio.wait_for(
                _query_run_snapshot(run_id), _RUN_AUTH_QUERY_TIMEOUT,
            )
        except Exception as exc:
            ultimo_erro = exc
            if tentativa + 1 < _JOB_RESULT_DB_RETRIES:
                await asyncio.sleep(_JOB_RESULT_DB_RETRY_DELAY)
    raise ultimo_erro  # type: ignore[misc]

async def _descartar_por_rate_limit(executor_id: str, job_id, msg: dict) -> None:
    """Drops the job_result that went over the ceiling — without leaving the run hanging.

    ERROR and not WARNING because dropping a legitimate job_result leaves the run
    hanging until the watchdog — if this shows up, the ceiling is wrong or there
    is abuse.
    """
    logger.error(
        "Executor '%s': job_result do job '%s' descartado por rate limit (>%d/%.0fs).",
        executor_id, job_id, _JOB_RESULT_RATE_LIMIT, _RATE_WINDOW,
    )
    # Dropped is dropped, but the run cannot stay in 'running' forever
    # because of it — closes it as failed when ownership is already proven.
    run_descartado = msg.get("run_id") or job_id
    if _posse_ja_provada(executor_id, run_descartado):
        await _fechar_run_inconclusivo(
            executor_id, run_descartado, "rate limit de job_result",
        )

async def _ler_veredito(executor_id: str, job_id, run_id):
    """Ownership and idempotency of the job_result, in a SINGLE read of the WorkflowRun.

    The three verdicts — does it belong to this executor? is it already
    terminal? how long did it take? — come from the same row. Returns that row,
    `(host, status, start_time)`, when the result must be written; None when it
    is dropped: another executor's run (memoized refusal), database down
    (cooldown armed and the run closed as failed if ownership was already
    proven) or a run that is already terminal.
    """
    conn = executor_registry.get(executor_id)
    cache = conn.run_auth_cache if conn is not None else None
    agora = time.monotonic()

    # The memo only comes in here as a REFUSAL shortcut: a positive verdict does
    # not spare the query (we need status and start_time from the same row), but
    # the negative one must stay cheap so that an executor in a loop does not
    # generate a SELECT per attempt.
    memo = cache.get(run_id) if cache is not None else None
    if memo is not None and memo[1] > agora and not memo[0]:
        logger.warning(
            "Executor '%s' tentou reportar job_result para run '%s' que não lhe pertence — rejeitado.",
            executor_id, run_id,
        )
        return None
    # The database cooldown does NOT apply here on purpose. It exists for
    # telemetry (node_event: high volume, cheap to lose); applying it to the
    # job_result turned a transient 200ms error (pgbouncer restart, replica
    # failover) into the loss of ALL results of the following 2s on that
    # connection — and each loss leaves a run hanging in 'running' forever. One
    # job_result per job, capped at _JOB_RESULT_RATE_LIMIT/s, is a negligible
    # cost in SELECTs.
    try:
        linha = await _ler_snapshot_com_retentativa(run_id)
    except Exception as exc:
        # Fail-closed on WRITING the result: without proving ownership of the run
        # there is no way to accept it. The cooldown is still armed to contain
        # the node_event burst coming behind it.
        logger.error(
            "Não foi possível ler o run '%s' para o job_result do executor '%s': %s "
            "— resultado descartado (fail-closed).", run_id, executor_id, exc,
        )
        if conn is not None:
            conn.db_auth_cooldown_until = time.monotonic() + _RUN_AUTH_DB_COOLDOWN
        # If ownership was already proven by previous events of this same run,
        # we close it as failed: the executor does not resend job_result.
        if _posse_ja_provada(executor_id, run_id):
            await _fechar_run_inconclusivo(
                executor_id, run_id, f"banco indisponível ({exc})",
            )
        return None

    # FAIL-CLOSED: a nonexistent run or one with a NULL host is rejected — during
    # the window in which host was still NULL, any executor could claim another
    # tenant's run.
    host = linha[0] if linha is not None else None
    if host != f"executor:{executor_id}":
        logger.warning(
            "Executor '%s' tentou reportar job_result para run '%s' que não lhe pertence "
            "(host=%s) — rejeitado.", executor_id, run_id, host,
        )
        if cache is not None:
            _store_run_auth(cache, run_id, False, agora)
        return None

    # The job_result is the run's last message: the authorization memo is of no
    # further use and leaves here instead of waiting for the TTL.
    _forget_run_auth(executor_id, run_id)

    # ── Idempotency: a terminal run does not accept updates ──────────────
    # Scenario: network partition > heartbeat_timeout → _fail_orphan_runs marks
    # the run as failed. The executor finishes later and replays from the outbox;
    # the "failed" state must not retroactively become "success".
    # `cancelled` is included for the same reason: once the user has cancelled
    # and the terminal state was written, a later job_result (redelivery, or a
    # compromised executor) cannot resurrect the run as success/failed.
    if linha[1] in ("success", "failed", "cancelled"):
        logger.info(
            "Job '%s' (run '%s'): run já está em estado terminal — resultado ignorado (idempotência).",
            job_id, run_id,
        )
        return None
    return linha

@dataclass(frozen=True)
class _ResultadoDoJob:
    """The outcome the executor reported, already in the server's taxonomy.

    Read ONCE from the contained job_result and used by all destinations — the
    ephemeral key, the `run_results` queue, the synchronous webhook and the
    `__workflow_complete__`. The last three each recomputed the same
    `msg.get("error") if job_status != "ok"`.
    """

    job_status: object    # o status cru do executor: "ok", "error", "cancelled"…
    cancelado: bool
    falhou: bool          # neither "ok" nor cancelled
    error_category: object
    retryable: bool
    erro: object          # the executor's `error` when the job did not finish "ok"

def _ler_resultado(executor_id: str, job_id, msg: dict) -> _ResultadoDoJob:
    """Classifies the job's outcome and logs the receipt."""
    job_status = msg.get("status", "unknown")
    # Cancellation is not failure: the user asked to stop. It has its own status
    # so it does not pollute the error rate nor show up as "falhou" (failed) in the panel.
    cancelado = job_status == "cancelled"
    # Error taxonomy (flow.utils.error_taxonomy): stable category + retryable.
    falhou = job_status != "ok" and not cancelado
    resultado = _ResultadoDoJob(
        job_status=job_status,
        cancelado=cancelado,
        falhou=falhou,
        error_category=msg.get("error_category") if falhou else None,
        retryable=bool(msg.get("retryable", False)) if falhou else False,
        erro=msg.get("error") if job_status != "ok" else None,
    )
    if job_status == "ok":
        logger.info("Resultado do job '%s' recebido do executor '%s': status=ok.", job_id, executor_id)
    else:
        logger.info(
            "Resultado do job '%s' recebido do executor '%s': status=%s category=%s retryable=%s.",
            job_id, executor_id, job_status, resultado.error_category or "internal", resultado.retryable,
        )
    return resultado

async def _persistir_resultado(
    executor_id: str, job_id, msg: dict, resultado: _ResultadoDoJob,
) -> None:
    """Ephemeral key `executor:{id}:results:{job}` (TTL 300 s) with the summary.

    Goes BEFORE the `run_results` queue: the inventory reconciliation
    (`orfaos.py`) reads it so as not to consider lost a job whose result has
    just arrived.
    """
    from app.core.redis import get_redis_pool

    try:
        rc = get_redis_pool()
        # Sanitizes data before persisting — removes fields that may contain credentials
        sanitized_msg = {
            "job_id": msg.get("job_id"),
            "status": msg.get("status"),
            "run_id": msg.get("run_id"),
            "error": msg.get("error", "")[:500] if msg.get("error") else None,
            "error_category": resultado.error_category,
            "retryable": resultado.retryable,
        }
        key = f"executor:{executor_id}:results:{job_id}"
        await rc.setex(key, 300, json.dumps(sanitized_msg))
    except Exception as exc:
        logger.error("Erro ao persistir resultado do job '%s' no Redis: %s", job_id, exc)

def _medir_duracao(inicio) -> tuple[float | None, float | None]:
    """`(duration_seconds, duration_ms)` since the run's `start_time`, or `(None, None)`.

    The `start_time` already came in the verdict read; naive is read as UTC.
    """
    from datetime import datetime as _dt, timezone as _tz

    if inicio is None:
        return None, None
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=_tz.utc)
    decorrido = (_dt.now(_tz.utc) - inicio).total_seconds()
    return round(decorrido, 3), round(decorrido * 1000, 2)

async def _notificar_consumer(
    executor_id: str, run_id, resultado: _ResultadoDoJob, duration_seconds,
    stats_json: str, executor_ip: str | None,
) -> None:
    """Enqueues the result in `run_results`, from where the consumer closes the run in the database."""
    from datetime import datetime as _dt, timezone as _tz

    from app.core.redis import get_redis_pool

    try:
        # AWARE, with an explicit offset. `utcnow().isoformat()` produced a
        # string WITHOUT an offset; the consumer did fromisoformat and handed
        # a naive datetime to WorkflowRun.end_time, which is timestamptz.
        # Postgres then assumed the session's time zone (TZ=America/Cuiaba in
        # the containers) and converted to UTC, writing the end 4h in the
        # future — every execution showed ~4h of duration when the UI
        # subtracted end_time - start_time. duration_seconds was always
        # right, since it compares two aware datetimes (`_medir_duracao`).
        end_ts = _dt.now(_tz.utc).isoformat()
        # `stats` was already serialized a single time in `_cap_job_result` (up
        # to 4 MB): repeating the dumps here was the second of the three
        # serializations that froze the event loop every time a heavy
        # workflow finished. We build the envelope with only the light keys
        # and splice in the ready string — the dict literal is never empty,
        # so the `[:-1]` always cuts the closing brace.
        # The connection's IP goes along: only this worker has it. The
        # run_results consumer runs on all four workers and, looking it up in
        # the local registry, wrote an empty `executor_ip` in ~3 out of 4
        # executions. It is the server that writes the key, outside `stats` —
        # the executor has no way to declare its own IP. `executor_ip` is that
        # of the connection that received the frame (the session's queue
        # carries it); the registry only comes in for callers without it.
        _head = json.dumps({
            "task_id":          run_id,
            "status":           _desfecho(resultado.job_status, resultado.cancelado, ok="success"),
            "error_message":    resultado.erro,
            "error_category":   resultado.error_category,
            "retryable":        resultado.retryable,
            "end_time":         end_ts,
            "duration_seconds": duration_seconds,
            "executor_ip":      executor_ip or getattr(executor_registry.get(executor_id), "executor_ip", None),
        })
        await get_redis_pool().lpush(
            "run_results", f'{_head[:-1]},"stats":{stats_json}}}',
        )
    except Exception as exc:
        logger.error("Erro ao publicar run_results para run '%s': %s", run_id, exc)

async def _notificar_webhook(
    run_id, stats: dict, resposta, resultado: _ResultadoDoJob, *, offload: bool,
) -> None:
    """Unblocks the synchronous webhook (ResponseNode or failure).

    The webhook_router waits via BRPOP on `webhook_response:{run}` if the workflow
    has a ResponseNode. We also notify on error to keep the webhook from getting
    stuck until the timeout.
    """
    from app.core.redis import get_redis_pool

    # Markers of the `stats` truncation — the protocol's, which the executor
    # applies before sending and `_cap_job_result` reapplies on entry.
    truncado = stats.get(STATS_TRUNCADO) is True
    controle_descartado = stats.get(STATS_CONTROLE_DESCARTADO) is True
    # If the payload was truncated and even the control keys are gone, the webhook
    # has no way to receive the response — we publish an explicit error to
    # unblock the BRPOP instead of leaving the caller to time out.
    if truncado and resposta is None and controle_descartado:
        job_status = "error"
        erro = (
            f"Resposta do workflow excedeu o limite de {stats.get(STATS_TAMANHO_ORIGINAL, '?')} bytes "
            "no transporte executor→servidor. Reduza o tamanho do body (ex: compactar geometria, "
            "paginar resultados) ou consuma via runner assíncrono."
        )
    else:
        job_status = resultado.job_status
        erro = resultado.erro

    if resposta is not None or job_status != "ok":
        try:
            # The ResponseNode's inline body goes up to 1 MB: above the threshold
            # this serialization also leaves the event loop.
            payload = await _dumps(
                {
                    "job_status": job_status,
                    "error":      erro,
                    "response":   resposta,
                },
                offload=offload,
            )
            rc = get_redis_pool()
            await rc.lpush(f"webhook_response:{run_id}", payload)
            await rc.expire(f"webhook_response:{run_id}", 300)
        except Exception as exc:
            logger.error("Erro ao publicar webhook_response para run '%s': %s", run_id, exc)

async def _registrar_body(run_id, executor_id: str, resposta) -> None:
    """Artifact for the body the ResponseNode uploaded straight to MinIO.

    Ensures a row with expires_at so the global cleanup removes the object
    in case the webhook_router's immediate post-streaming delete fails (orphan).
    """
    body_ref = (resposta or {}).get("body_ref") if isinstance(resposta, dict) else None
    # Out of format (defective or compromised executor), the `.get` raised
    # here, outside the try, and the `__workflow_complete__` did not go out: the
    # run closed in the database and the open panel never knew.
    if isinstance(body_ref, dict) and body_ref.get("s3_key"):
        try:
            await _register_webhook_response_artifact(run_id, executor_id, body_ref)
        except Exception as exc:
            logger.error("Falha ao registrar Artifact de webhook response (run=%s): %s", run_id, exc)

async def _publicar_conclusao(run_id, resultado: _ResultadoDoJob, duration_ms) -> None:
    """Publishes the job's `__workflow_complete__` to the run's history and channel.

    It is the end the panel sees. The runs the SERVER closes, without a
    job_result, publish through `run_events_service.publicar_conclusao`, with the
    event built in the same place (`evento_de_conclusao`), only without
    `duration_ms`: the server does not measure the duration of what it closes.
    """
    from app.core.redis import get_redis_pool

    try:
        # The level comes from the status: "failed" ⇔ failure (`resultado.falhou`).
        evento = run_events_service.evento_de_conclusao(
            run_id,
            _desfecho(resultado.job_status, resultado.cancelado, ok="completed"),
            erro=resultado.erro,
            # Taxonomy of the whole job — the panel uses it to say whether it is
            # worth repeating the execution or the user needs to fix the input.
            extra={
                "error_category": resultado.error_category,
                "retryable":      resultado.retryable,
            } if resultado.falhou else None,
            duration_ms=duration_ms,
        )
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            run_events_service.anexar_eventos(pipe, run_id, [evento])
            await pipe.execute()
    except Exception as exc:
        logger.error("Erro ao publicar __workflow_complete__ para run '%s': %s", run_id, exc)

async def _handle_job_result(
    executor_id: str, msg: dict, frame_bytes: int = 0, executor_ip: str | None = None,
):
    """
    Processes the result of a job reported by the executor.

    Checks the run in the database and takes the outcome to each destination, in
    the order below. The result's ephemeral key lives 300 s; the one that writes
    the run to the database is the consumer of the `run_results` queue.

    LIMITS: rate limit and byte ceiling, equal in spirit to node_event's.
    Without them, `error` and `stats` went raw to the `run_results` queue (no
    TTL), the run's history and Postgres — and the loop cost only 3 SELECTs per
    iteration.

    ORDER of the effects, which is a contract: run read (`_ler_veredito`) →
    the result's ephemeral key (`_persistir_resultado`) → `run_results` queue
    (`_notificar_consumer`) → `webhook_response` (`_notificar_webhook`) →
    the body's Artifact (`_registrar_body`) → `__workflow_complete__`
    (`_publicar_conclusao`). Each destination has its own try: one failing does
    not prevent the following ones.

    `frame_bytes` is the size of the frame that brought this message. It only
    serves to decide whether the large serializations go to a thread — see
    `_JSON_OFFLOAD_THRESHOLD`.
    """
    job_id = msg.get("job_id")
    if not job_id:
        logger.warning("Executor '%s' enviou job_result sem job_id.", executor_id)
        return

    # Before the authorization on purpose: it is the cost in SELECTs that the flood exploits.
    if not _rate_allowed(executor_id, "job_result", _JOB_RESULT_RATE_LIMIT):
        await _descartar_por_rate_limit(executor_id, job_id, msg)
        return

    # `stats` can be megabytes: above the threshold, measuring the ceiling (which
    # serializes) leaves the event loop so as not to freeze the whole worker.
    offload = frame_bytes > _JSON_OFFLOAD_THRESHOLD
    if offload:
        msg, stats_json = await asyncio.to_thread(_cap_job_result, executor_id, msg)
    else:
        msg, stats_json = _cap_job_result(executor_id, msg)

    # Fallback to job_id: the server sets run_id == job_id when dispatching to the
    # executor; if the failure happened before decryption (e.g. invalid
    # signature), run_id will not be present in the result, but job_id is
    # enough to locate the WorkflowRun.
    run_id = msg.get("run_id") or job_id

    linha = await _ler_veredito(executor_id, job_id, run_id)
    if linha is None:
        return

    resultado = _ler_resultado(executor_id, job_id, msg)
    await _persistir_resultado(executor_id, job_id, msg, resultado)
    duration_seconds, duration_ms = _medir_duracao(linha[2])
    await _notificar_consumer(
        executor_id, run_id, resultado, duration_seconds, stats_json, executor_ip,
    )
    # The ResponseNode returns the synchronous webhook's body inside `stats`.
    stats = msg.get("stats") or {}
    resposta = stats.get("__response__")
    await _notificar_webhook(run_id, stats, resposta, resultado, offload=offload)
    await _registrar_body(run_id, executor_id, resposta)
    await _publicar_conclusao(run_id, resultado, duration_ms)

def _serialize_node_event(executor_id: str, msg: dict) -> str:
    """Serializes the node_event already contained by the byte ceiling.

    LIMIT: without it, a buggy (or compromised) executor pushes 16 MB per
    frame straight into Redis, which has no maxmemory in the compose — it grows
    until the OOM-kill and takes dispatch, auth and the results consumer with it.

    The reduction is the protocol's (flow/utils/publisher/reducao.py), the same
    one the executor already applies before sending: here it is a defense, and an
    event the executor has reduced passes through intact.
    """
    # Removes the "type" field — the Redis channel expects the event without it
    event = {k: v for k, v in msg.items() if k != "type"}
    payload = json.dumps(event)

    # `json.dumps` usa ensure_ascii, logo len(str) == tamanho em bytes.
    if len(payload) > TETO_NODE_EVENT_BYTES:
        logger.warning(
            "Executor '%s': node_event de %d bytes (run=%s node=%s) excede o teto de %d — truncado.",
            executor_id, len(payload), msg.get("run_id"), msg.get("node"), TETO_NODE_EVENT_BYTES,
        )
        payload = reduzir_node_event(event, payload)
    return payload

async def _publish_node_events(executor_id: str, msgs: list[dict]) -> None:
    """
    Republishes a BATCH of node events on Redis pub/sub, on the same channel that
    log_workflows_router.py listens to. That is how the frontend receives visual
    updates in real time when the workflow runs on an external executor.

    PERF: the whole batch goes out in a SINGLE pipeline — the events are grouped
    by run and each run spends one variadic `rpush` + one `ltrim` + one `expire`
    + the `publish`es. Before, it was 1 Redis round-trip PER EVENT, issued from
    inside the receive loop: in a high fan-out burst the final job_result and the
    heartbeat got stuck behind hundreds of trips to Redis. With a batch of up to
    `_INBOX_COALESCE_MAX`, the same burst costs one round-trip.

    SEC: run_id is validated against executor_id — an executor cannot inject
    events into runs that do not belong to it (cross-tenant). The validation is
    per run (memoized on the connection), not per event, so grouping does not
    loosen it.
    """
    from app.core.redis import get_redis_pool

    por_run: dict[str, list[str]] = {}
    negados: set[str] = set()
    for msg in msgs:
        run_id = msg.get("run_id")
        if not run_id or run_id in negados:
            continue
        if run_id not in por_run:
            if not await _run_belongs_to_agent(executor_id, run_id):
                logger.warning(
                    "Executor '%s' tentou publicar node_event em run '%s' que não lhe "
                    "pertence — rejeitado.", executor_id, run_id,
                )
                negados.add(run_id)
                continue
            por_run[run_id] = []
        por_run[run_id].append(_serialize_node_event(executor_id, msg))

    if not por_run:
        return

    try:
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            for run_id, payloads in por_run.items():
                run_events_service.anexar_eventos(pipe, run_id, payloads)
            await pipe.execute()
    except Exception as exc:
        logger.warning(
            "Erro ao publicar %d node_event(s) no Redis (runs=%s): %s",
            sum(len(p) for p in por_run.values()), list(por_run), exc,
        )

async def _handle_sync_event(executor_id: str, msg: dict):
    """
    Publishes the executor's sync events to Redis for consumption by the frontend.
    Channel: executor:{executor_id}:sync_events

    PERF: publish + hset + expire go out in a single pipeline — they were three
    loose `await`s, and the emitter sends one event per FILE transition. In a
    GeoSync of thousands of files that took 3 round-trips per file, in series,
    along with the node_events of the workflows running on the same executor.

    LIMIT: the event dictionary copies any `**kwargs` the emitter may have put
    in, with no ceiling. Above `_MAX_SYNC_EVENT_BYTES` the event is reduced to
    the fields the UI actually uses.
    """
    from app.core.redis import get_redis_pool

    event = {k: v for k, v in msg.items() if k != "type"}
    event["executor_id"] = executor_id
    payload = json.dumps(event)

    if len(payload) > _MAX_SYNC_EVENT_BYTES:
        logger.warning(
            "Executor '%s': sync_event de %d bytes (event=%s) excede o teto de %d — reduzido.",
            executor_id, len(payload), msg.get("event"), _MAX_SYNC_EVENT_BYTES,
        )
        payload = json.dumps({
            "executor_id":   executor_id,
            "event":         str(msg.get("event", ""))[:TETO_POR_CAMPO],
            "dataset":       str(msg.get("dataset", ""))[:TETO_POR_CAMPO],
            "progress":      _coerce_gauge(msg.get("progress")) or 0,
            "timestamp":     _coerce_gauge(msg.get("timestamp")),
            "__truncated__": True,
        })

    channel = f"executor:{executor_id}:sync_events"
    status_key = f"executor:{executor_id}:sync_status"

    try:
        rc = get_redis_pool()
        async with rc.pipeline(transaction=False) as pipe:
            pipe.publish(channel, payload)
            # Saves the current state for lookup
            pipe.hset(status_key, mapping={
                "last_event": str(msg.get("event", ""))[:TETO_POR_CAMPO],
                "dataset": str(msg.get("dataset", ""))[:TETO_POR_CAMPO],
                "progress": str(msg.get("progress", 0))[:64],
                "timestamp": str(msg.get("timestamp", ""))[:64],
            })
            pipe.expire(status_key, REDIS_TTL_1H)
            await pipe.execute()
    except Exception as exc:
        logger.warning("Erro ao publicar sync_event no Redis (executor=%s): %s", executor_id, exc)
