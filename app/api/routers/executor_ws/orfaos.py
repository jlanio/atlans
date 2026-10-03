# app/api/routers/executor_ws/orfaos.py
"""
Orphan runs: closing them as executor_lost when the executor goes away, and
the periodic watchdog that covers server downtime windows.
"""
import asyncio
import time

from app.core.utils.logger import get_logger

from sqlalchemy import select

from app.core.executor_connections import executor_registry
from app.core.db import get_session_async

logger = get_logger(__name__)


# Grace period before concluding that an executor that disconnected is really gone.
# See `_fail_orphan_runs_if_gone`.
_DISCONNECT_GRACE_SECONDS = 20

# Strong references to the post-disconnect check tasks (asyncio only keeps
# weakrefs; without this the task may vanish in the middle of the grace period).
_orphan_check_tasks: set[asyncio.Task] = set()

async def _fail_orphan_runs_if_gone(executor_id: str) -> None:
    """Fails the orphan runs ONLY if the executor is really gone.

    The handler's `finally` runs on EVERY socket drop, including a 1-second
    network blip. The executor's local queue is independent of the connection: it
    keeps executing the jobs and reconnects right after — but the N runs would
    already have been marked 'failed', and the real `job_result` would later be
    discarded by `_handle_job_result`'s idempotency check. One blip destroyed 20
    live workflows at once.

    That is why we wait for a grace period and only fail if, once it has passed,
    the executor is neither registered on this worker (local reconnection) NOR
    has presence in Redis (reconnection on another uvicorn worker) — the same
    check `orphan_runs_watchdog` does, and which remains the safety net for the
    case where the worker itself dies without running the `finally`.

    The presence query is TRI-STATE. `_redis_check_presence` is fail-closed
    (Redis error = offline), which is right for dispatch but destructive here: a
    pool blip at the exact moment of the check would fail precisely the runs this
    grace period exists to save. "Don't know" is not "gone" — in that case we do
    nothing and the watchdog re-evaluates in ≤180s.
    """
    from app.core.executor_connections import _redis_presence_or_unknown

    # CancelledError (worker shutdown) propagates on purpose: in that scenario
    # we do not want to fail any run — the watchdog sorts it out later.
    await asyncio.sleep(_DISCONNECT_GRACE_SECONDS)

    if executor_registry.get(executor_id) is not None:
        logger.info(
            "Executor '%s' reconectou dentro da carência — runs em voo preservados.",
            executor_id,
        )
        return
    presence = await _redis_presence_or_unknown(executor_id)
    if presence is True:
        logger.info(
            "Executor '%s' com presença no Redis (reconectou em outro worker) — "
            "runs em voo preservados.",
            executor_id,
        )
        return
    if presence is None:
        logger.warning(
            "Executor '%s': não foi possível consultar a presença no Redis após a "
            "carência — runs em voo PRESERVADOS por precaução; o watchdog reavalia "
            "em até %ds.",
            executor_id, _ORPHAN_WATCHDOG_INTERVAL,
        )
        return

    try:
        await _fail_orphan_runs(executor_id)
    except Exception as exc:
        # The task is detached: without this log the exception would only show up
        # as "Task exception was never retrieved" at shutdown.
        logger.error(
            "Falha ao limpar runs órfãos do executor '%s' pós-desconexão: %s",
            executor_id, exc,
        )

async def _fail_orphan_runs(executor_id: str) -> None:
    """
    On disconnect, marks as 'failed' every WorkflowRun with status='running'
    assigned to this executor (host = 'executor:{executor_id}').

    The closing is the same as for every run closed by the server (`fechar_runs`):
    a conditional UPDATE per run — the consumer may write the real result between
    the SELECT and the commit, and it wins —, accounting in usage_daily (this
    path never goes through the run_results queue) and `__workflow_complete__`
    with status=failed, so the frontend closes the log WebSocket and shows the error.
    """
    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    host_key = f"executor:{executor_id}"

    try:
        async with get_session_async() as db:
            result = await db.execute(
                select(_WFRun).where(
                    _WFRun.host == host_key,
                    _WFRun.status == "running",
                )
            )
            candidatos = result.scalars().all()

            if not candidatos:
                return

            # `executor_lost` applies to both paths that reach here — the WS
            # finally and the presence watchdog. The published event stays
            # "transient" (the flow's taxonomy, so the log panel offers a
            # retry); the column stores the cause as seen by the server.
            orphans = await fechar_runs(
                db, candidatos, de=("running",), para="failed",
                mensagem="Executor desconectou durante a execução.",
                categoria="executor_lost", host=host_key, duracao=True, extra=REPETIVEL,
            )
        if orphans:
            logger.warning(
                "Executor '%s' desconectou com %d run(s) em execução — marcados como failed.",
                executor_id, len(orphans),
            )

    except Exception as exc:
        logger.error("Erro ao limpar runs órfãos do executor '%s': %s", executor_id, exc)


# ── Runs in 'pending' that no executor received ──────────────────────────────

# Age beyond which a run in 'pending' is no longer being dispatched. Dispatch
# takes milliseconds, sending to the executor has a deadline (see
# `_prazo_de_envio` in executor_connections) and the executor's ACK promotes the
# run to 'running' as soon as the job arrives. A 'pending' this old belongs to a
# worker that died mid-send — and nobody else would close it: the orphan
# watchdog only looks at 'running', and the run stayed "Na fila" (queued)
# forever (the September 22 case).
_PENDING_SEM_ENTREGA_SECONDS = 600

# Ceiling per sweep: an incident with thousands of stuck runs is drained in
# batches, one per watchdog cycle, without a giant transaction.
_PENDING_LOTE = 200

_MSG_NAO_ENTREGUE = (
    "O servidor foi interrompido enquanto enviava esta execução ao executor, e "
    "nenhum executor confirmou o recebimento — ela não chegou a rodar."
)

# An executor older than the inventory has no way to promote a job whose ACK was
# lost along with the worker that dispatched it (the dead worker also takes down
# its direct connection). For the runs of an ONLINE executor that sends no
# inventory, the sweep waits for a job's duration ceiling (1 h by default, plus
# the queue) before concluding the send did not arrive — otherwise it would
# close, and order the cancellation of, a healthy job.
_PENDING_SEM_INVENTARIO_SECONDS = 6 * 3600
# "This executor sends inventory": renewed on every inventory received.
_TTL_MARCA_DE_INVENTARIO_S = 180


def _chave_de_inventario(executor_id: str) -> str:
    return f"executor:{executor_id}:inventario"


async def _hosts_sem_inventario(hosts) -> set[str]:
    """Of the given hosts (`executor:{id}`), those that may have the job with no way
    to say so: online — or with unknown presence, because the decision is
    destructive — and with no recent inventory."""
    from app.core.executor_connections import _redis_presence_or_unknown
    from app.core.redis import get_redis_pool

    esperar: set[str] = set()
    for host in hosts:
        if not host or not host.startswith("executor:"):
            continue
        executor_id = host[len("executor:"):]
        if await _redis_presence_or_unknown(executor_id) is False:
            continue
        try:
            fala_inventario = bool(await get_redis_pool().exists(_chave_de_inventario(executor_id)))
        except Exception:
            fala_inventario = False
        if not fala_inventario:
            esperar.add(host)
    return esperar


async def _fechar_runs_nao_entregues() -> int:
    """Closes as 'failed' the runs stuck in 'pending' beyond the deadline. Returns
    how many it closed.

    The closing is conditional (`status='pending'`, see `fechar_runs`), so the
    4 workers can sweep at the same time: each run is closed — and accounted
    for — by only one. The stored host gets a 'cancel' anyway: if the job did
    arrive without an ACK, the executor interrupts it; if not, it answers that it
    does not know it.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import and_, or_

    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(seconds=_PENDING_SEM_ENTREGA_SECONDS)
    async with get_session_async() as db:
        # The hosts before the runs: filtering after the LIMIT would leave the batch
        # full of runs that are waiting, and the others would never be swept.
        hosts = (await db.execute(
            select(_WFRun.host)
            .where(_WFRun.status == "pending", _WFRun.start_time < corte)
            .distinct()
        )).scalars().all()
        esperar = await _hosts_sem_inventario(hosts)
        prazo = _WFRun.start_time < corte
        if esperar:
            corte_sem_inventario = agora - timedelta(seconds=_PENDING_SEM_INVENTARIO_SECONDS)
            prazo = or_(
                and_(prazo, or_(_WFRun.host.is_(None), _WFRun.host.notin_(sorted(esperar)))),
                _WFRun.start_time < corte_sem_inventario,
            )
        result = await db.execute(
            select(_WFRun)
            .where(_WFRun.status == "pending", prazo)
            .order_by(_WFRun.start_time)
            .limit(_PENDING_LOTE)
        )
        fechados = await fechar_runs(
            db, result.scalars().all(), de=("pending",), para="failed",
            mensagem=_MSG_NAO_ENTREGUE, categoria="dispatch", extra=REPETIVEL,
        )

    if not fechados:
        return 0
    logger.warning(
        "%d run(s) preso(s) em 'pending' há mais de %ds sem confirmação de entrega "
        "— fechados como failed: %s",
        len(fechados), _PENDING_SEM_ENTREGA_SECONDS,
        [run.task_id for run in fechados[:20]],
    )
    for run in fechados:
        host = run.host or ""
        if not host.startswith("executor:"):
            continue
        try:
            await executor_registry.send_json(
                host[len("executor:"):], {"type": "cancel", "job_id": run.task_id},
            )
        except Exception as exc:
            logger.debug("Cancel do run não entregue '%s' não enviado: %s", run.task_id, exc)
    return len(fechados)

_MSG_RELAY_NAO_ENTREGUE = (
    "O executor ainda estava recebendo um envio anterior e esta execução não "
    "chegou a ele — ela não rodou. Tente de novo."
)
_MSG_CONEXAO_FECHANDO = (
    "A conexão com o executor estava sendo encerrada e esta execução não "
    "chegou a ele — ela não rodou. Tente de novo."
)


async def fechar_run_nao_entregue(
    executor_id: str, task_id: str, *, conexao_fechando: bool = False,
) -> bool:
    """Closes as failed/dispatch the run whose job was PROVABLY not written to the
    executor's socket — the relay dropped it without its turn, or
    (`conexao_fechando`) because the socket was closing. Returns whether it closed.

    The worker that published to the relay had already considered the job
    delivered; without this closing the run stayed "Em andamento" (in progress)
    until the pending ACK expired (10 min) and only then failed as lost.
    Conditional on status and host, like the server's other closings
    (`fechar_runs`).
    """
    from app.services.fechamento_de_run import ABERTOS, REPETIVEL, fechar_runs

    mensagem = _MSG_CONEXAO_FECHANDO if conexao_fechando else _MSG_RELAY_NAO_ENTREGUE
    async with get_session_async() as db:
        fechados = await fechar_runs(
            db, [task_id], de=ABERTOS, para="failed", mensagem=mensagem,
            categoria="dispatch", host=f"executor:{executor_id}", extra=REPETIVEL,
        )
    if not fechados:
        return False
    try:
        await executor_registry.clear_pending_ack(task_id, expected_executor_id=executor_id)
    except Exception as exc:
        logger.debug("ACK pendente do run '%s' não limpo: %s", task_id, exc)
    logger.warning(
        "Run '%s' fechado: o job relayado ao executor '%s' não foi escrito (%s).",
        task_id, executor_id, "conexão fechando" if conexao_fechando else "sem a vez",
    )
    return True


# ── Periodic orphan-run watchdog ─────────────────────────────────────────────

# Interval between sweeps. Aligns with the registry's _PRESENCE_TTL=120s —
# small network latencies can make a legitimate heartbeat arrive right at
# the limit; 180s gives comfortable slack without leaving orphans alive for hours.
_ORPHAN_WATCHDOG_INTERVAL = 180

async def orphan_runs_watchdog() -> None:
    """Background task that enumerates 'running' runs whose executor has NO
    presence in Redis. Calls `_fail_orphan_runs` for each one.

    Motivation: the WS handler's `_fail_orphan_runs` only runs in the
    `finally` of `agent_websocket`. If the uvicorn worker dies (SIGKILL/OOM/crash),
    the finally never executes — runs stay with status='running'
    forever, even though presence expires in 120s.

    This watchdog is the safety net.
    """
    import asyncio
    import re
    from app.models.models import WorkflowRun as _WFRun
    from app.core.executor_connections import _redis_presence_or_unknown

    # Accepts UUID-like hashes (with hyphens) and old ones (without hyphens) —
    # avoids matching residual garbage values.
    _HOST_RE = re.compile(r"^executor:([A-Fa-f0-9\-]{8,})$")

    logger.info("Watchdog de runs orfaos iniciado (intervalo %ds).", _ORPHAN_WATCHDOG_INTERVAL)

    while True:
        try:
            await asyncio.sleep(_ORPHAN_WATCHDOG_INTERVAL)

            # Before the orphans in 'running': it is independent of presence, and an
            # error here must not prevent the sweep below.
            try:
                await _fechar_runs_nao_entregues()
            except Exception as exc:
                logger.error("Watchdog: falha ao fechar runs não entregues: %s", exc)

            async with get_session_async() as db:
                result = await db.execute(
                    select(_WFRun.host).where(
                        _WFRun.status == "running",
                        _WFRun.host.like("executor:%"),
                    ).distinct()
                )
                hosts = [row[0] for row in result.all() if row[0]]

            candidates: set[str] = set()
            for host in hosts:
                m = _HOST_RE.match(host)
                if m:
                    candidates.add(m.group(1))

            if not candidates:
                continue

            offline: list[str] = []
            for executor_id in candidates:
                # Tri-state: if the worker died and did not renew the TTL, the key
                # really is gone (False). None is "couldn't ask" — in that case
                # we do NOT fail the runs; the next cycle re-evaluates. Collapsing
                # both into "offline" would let a Redis blip destroy live runs.
                presence = await _redis_presence_or_unknown(executor_id)
                if presence is False:
                    offline.append(executor_id)
                elif presence is None:
                    logger.warning(
                        "Watchdog: presence de '%s' indisponivel (Redis) — runs "
                        "preservados, reavalia no proximo ciclo.",
                        executor_id,
                    )

            if not offline:
                continue

            logger.warning(
                "Watchdog detectou %d executor(es) sem presence com runs 'running': %s. "
                "Marcando como failed.",
                len(offline), sorted(offline),
            )
            for executor_id in offline:
                try:
                    await _fail_orphan_runs(executor_id)
                except Exception as exc:
                    logger.error(
                        "Watchdog: falha ao limpar orfaos de '%s': %s",
                        executor_id, exc,
                    )
        except asyncio.CancelledError:
            logger.info("Watchdog de runs orfaos encerrado.")
            raise
        except Exception as exc:
            # Does not let the loop die from a one-off error. Short backoff.
            logger.error("Erro no watchdog de runs orfaos: %s", exc)
            await asyncio.sleep(30)


# ── Reconciliation from the executor's inventory ─────────────────────────────
# The executor sends, on connecting and every minute, the jobs it HAS: `ativos`
# (in the queue, in the semaphore or running) and `resultados` (finished, result
# not yet confirmed). Before, the server only found out about a lost run when
# the executor DISCONNECTED — on September 22 titan stayed connected with three
# runs it never received, and they stayed "Em andamento" (in progress) until
# 09:16, only to then become an "Executor desconectou durante a execução"
# (executor disconnected during execution) that blamed someone who was not at
# fault.
#
# Three actions per inventory:
#   1. promotes to 'running' the 'pending' ones the executor has (lost ACK);
#   2. sends 'cancel' for what it keeps running but the server already closed;
#   3. closes its runs that it does NOT have, older than 3 min and with no
#      result freshly arrived at the server.

# Minimum age for a run to be judged lost for not being in the inventory.
# Above the maximum send deadline (~62 s for a 16 MB frame), with slack: a
# job still in transit when the executor built the inventory is not a loss.
_RECONCILIACAO_IDADE_MIN_S = 180

# Minimum interval between two reconciliations of the same executor. An honest
# executor sends one inventory per minute; a buggy (or hostile) one does not
# turn the inventory into a SELECT per message.
_RECONCILIACAO_INTERVALO_S = 30

# Grace period after a new connection before closing anything due to ABSENCE.
# The PREVIOUS connection's inbox may still be draining (10 s flush + grace
# + rescue, ~20 s) a job_result that went out before the drop: the new
# session's first inventory does not list it, and closing the run now would get
# the real result rejected right after. Promoting and stopping zombies don't wait.
_RECONCILIACAO_CARENCIA_DA_CONEXAO_S = 45

_INVENTARIO_MAX_IDS = 2000
_JOB_ID_MAX_CHARS = 64

_MSG_PERDIDO = (
    "O executor não tinha mais esta execução quando o servidor conferiu com ele — "
    "ela se perdeu entre o servidor e o executor (queda da conexão, do servidor "
    "ou do próprio executor)."
)


def _ids_do_inventario(valor) -> set[str] | None:
    """Valid ids from an inventory list; None if the list is malformed."""
    if valor is None:
        return set()
    if not isinstance(valor, list) or len(valor) > _INVENTARIO_MAX_IDS:
        return None
    return {v for v in valor if isinstance(v, str) and 0 < len(v) <= _JOB_ID_MAX_CHARS}


async def _reconciliar_inventario(executor_id: str, msg: dict) -> dict:
    """Checks this executor's runs against what it says it has. Returns the
    counts (for logging and tests); {} when it did not reconcile.

    SEC: everything is restricted to runs whose `host` is this executor. A lying
    inventory only affects the executor's own runs — whose outcome it already
    controls through the job_result anyway.
    """
    from app.core.redis import get_redis_pool

    from .resultados import _promover_para_running

    # Marks that this executor speaks inventory — the 'pending' sweep treats
    # those that don't differently (see `_PENDING_SEM_INVENTARIO_SECONDS`).
    try:
        await get_redis_pool().setex(
            _chave_de_inventario(executor_id), _TTL_MARCA_DE_INVENTARIO_S, "1",
        )
    except Exception as exc:
        logger.debug("Marca de inventário do executor '%s' não gravada: %s", executor_id, exc)

    conn = executor_registry.get(executor_id)
    if conn is not None:
        agora_mono = time.monotonic()
        if agora_mono - conn.ultima_reconciliacao < _RECONCILIACAO_INTERVALO_S:
            return {}
        conn.ultima_reconciliacao = agora_mono

    ativos = _ids_do_inventario(msg.get("ativos"))
    resultados = _ids_do_inventario(msg.get("resultados"))
    if ativos is None or resultados is None:
        logger.warning("Executor '%s' mandou inventário malformado — ignorado.", executor_id)
        return {}

    promovidos = await _promover_para_running(executor_id, ativos) if ativos else 0
    parados = await _parar_zumbis(executor_id, ativos) if ativos else 0
    # Truncated: there is no way to know what was left out, so nothing is closed
    # due to absence — promoting and stopping still apply to what came in. Same
    # right after connecting (see `_RECONCILIACAO_CARENCIA_DA_CONEXAO_S`).
    if msg.get("truncado") or _conexao_recente(conn):
        fechados = 0
    else:
        fechados = await _fechar_perdidos(executor_id, ativos | resultados)
    return {"promovidos": promovidos, "parados": parados, "fechados": fechados}


def _conexao_recente(conn) -> bool:
    from datetime import datetime, timezone

    if conn is None:
        return False
    idade = (datetime.now(timezone.utc) - conn.connected_at).total_seconds()
    return idade < _RECONCILIACAO_CARENCIA_DA_CONEXAO_S


# Strong references to the background cancels (asyncio only keeps weakrefs).
_cancels_em_curso: set[asyncio.Task] = set()


def _cancelar_em_segundo_plano(executor_id: str, task_ids: list[str], rotulo: str) -> None:
    """Sends `cancel` for each job without holding up the caller: the reconciliation
    runs in the connection's drainer, and with a congested socket each send may
    wait its turn for up to the whole deadline — delaying the drainer's job_results."""
    if not task_ids:
        return

    async def _mandar():
        for task_id in task_ids:
            try:
                await executor_registry.send_json(executor_id, {"type": "cancel", "job_id": task_id})
            except Exception as exc:
                logger.debug("Cancel do %s '%s' não enviado: %s", rotulo, task_id, exc)

    task = asyncio.create_task(_mandar(), name=f"cancel-{rotulo}-{executor_id[:8]}")
    _cancels_em_curso.add(task)
    task.add_done_callback(_cancels_em_curso.discard)


async def _parar_zumbis(executor_id: str, ativos: set[str]) -> int:
    """'cancel' for what the executor keeps running but the server already closed
    (cancelled with the executor offline, failed by disconnection, undelivered).
    The result of those runs would be rejected anyway — running to the end
    would only waste the machine and produce effects nobody expects."""
    from app.models.models import WorkflowRun as _WFRun

    async with get_session_async() as db:
        result = await db.execute(
            select(_WFRun.task_id).where(
                _WFRun.task_id.in_(sorted(ativos)),
                _WFRun.host == f"executor:{executor_id}",
                _WFRun.status.in_(("cancelled", "failed")),
            )
        )
        zumbis = [row[0] for row in result.all()]
    _cancelar_em_segundo_plano(executor_id, zumbis, "zumbi")
    if zumbis:
        logger.warning(
            "Executor '%s' ainda rodava %d job(s) que o servidor já fechou — cancel enviado: %s",
            executor_id, len(zumbis), zumbis[:20],
        )
    return len(zumbis)


async def _fechar_perdidos(executor_id: str, tem: set[str]) -> int:
    """Closes this executor's runs that it does not have. Returns how many it closed."""
    from datetime import datetime, timedelta, timezone

    from app.core.redis import get_redis_pool
    from app.models.models import WorkflowRun as _WFRun
    from app.services.fechamento_de_run import REPETIVEL, fechar_runs

    host = f"executor:{executor_id}"
    corte = datetime.now(timezone.utc) - timedelta(seconds=_RECONCILIACAO_IDADE_MIN_S)
    async with get_session_async() as db:
        result = await db.execute(
            select(_WFRun.task_id, _WFRun.status).where(
                _WFRun.host == host,
                _WFRun.status.in_(("pending", "running")),
                _WFRun.start_time < corte,
            )
        )
        candidatos = [(tid, st) for tid, st in result.all() if tid not in tem]
    if not candidatos:
        return 0

    # Two reasons for not being in the inventory without being lost, both in
    # Redis: the result just arrived (`_handle_job_result` writes the result key,
    # TTL 300 s, before sending it to the consumer), or the job is still on its
    # way — a send that exceeded the deadline keeps trickling through the socket
    # for an indefinite time, and the pending ACK (TTL 600 s) is the mark of
    # that. Without Redis there is no way to know: closes nothing.
    from app.core.executor_connections import _pending_ack_key

    try:
        chaves = [f"executor:{executor_id}:results:{tid}" for tid, _ in candidatos]
        chaves += [_pending_ack_key(tid) for tid, _ in candidatos]
        valores = await get_redis_pool().mget(chaves)
    except Exception as exc:
        logger.warning(
            "Reconciliação de '%s' adiada: Redis indisponível para conferir resultados (%s).",
            executor_id, exc,
        )
        return 0
    n = len(candidatos)
    candidatos = [
        c for c, chegou, a_caminho in zip(candidatos, valores[:n], valores[n:])
        if chegou is None and a_caminho is None
    ]
    if not candidatos:
        return 0

    async with get_session_async() as db:
        # A 'pending' the executor does not have never reached it: it is the same
        # case as the undelivered sweep, only detected earlier. Each group closes
        # only if it is still in the status in which it was read.
        fechados = await fechar_runs(
            db, [tid for tid, st in candidatos if st == "pending"], de=("pending",),
            para="failed", mensagem=_MSG_NAO_ENTREGUE, categoria="dispatch", host=host,
            extra=REPETIVEL,
        )
        fechados += await fechar_runs(
            db, [tid for tid, st in candidatos if st == "running"], de=("running",),
            para="failed", mensagem=_MSG_PERDIDO, categoria="executor_lost", host=host,
            extra=REPETIVEL,
        )

    if not fechados:
        return 0
    logger.warning(
        "Executor '%s' não tinha %d run(s) que o servidor dava como em andamento — "
        "fechados como failed: %s",
        executor_id, len(fechados), [run.task_id for run in fechados[:20]],
    )
    # If the job still arrives (a frame that kept trickling past the pending ACK),
    # the cancel arrives AFTER it on the same socket and interrupts it — or
    # becomes a tombstone, if the job never comes. Without this it would run,
    # with effects, for a run that is already closed.
    _cancelar_em_segundo_plano(executor_id, [run.task_id for run in fechados], "perdido")
    return len(fechados)

