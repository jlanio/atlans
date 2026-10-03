# executor/main.py
"""
Atlas executor entry point.

Startup flow:
  1. Loads configuration (env vars)
  2. Pins the server's signing key (enroll or on-disk TOFU)
  3. Loads the X25519 private key generated at enrollment — never generates another
  4. Starts ExecutorJobQueue with workers
  5. Starts ExecutorConnection (automatic reconnect loop)
  6. Waits for SIGTERM/SIGINT for a graceful shutdown

Usage:
  python -m executor.main
  # or
  python executor/main.py
"""
import asyncio
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from executor import config as _cfg  # noqa: F401  (loads .env before anything else)
from executor.logging_setup import configure_logging

# Runs at import, as it always has: any module imported below already logs
# to a configured root. The contents live in executor/logging_setup.py.
configure_logging()

logger = logging.getLogger("executor")


# ── Auto-restart ──────────────────────────────────────────────────────────────
# Under Docker (`restart: on-failure`), exiting with code 1 is enough — and lets
# a new image be picked up. Running directly on Python there is no supervisor:
# without re-exec, a `config_changed` would just stop the executor and it would
# not come back.
#
# EXECUTOR_AUTO_RESTART: auto (default) | always | never
_AUTO_RESTART_MODE = os.getenv("EXECUTOR_AUTO_RESTART", "auto").strip().lower()

# Anti-loop guard: if the cause of the restart persists (e.g. the server resending
# config_changed on every connection), re-executing without a limit would spin forever.
_RESTART_COUNT_VAR  = "_EXECUTOR_RESTART_COUNT"
_RESTART_SINCE_VAR  = "_EXECUTOR_RESTART_SINCE"
_MAX_RESTARTS       = 5
_RESTART_WINDOW_SEC = 300


def _in_container() -> bool:
    """Detects running in a container (Docker/K8s), where a supervisor already exists."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", encoding="utf-8") as f:
            content = f.read()
        return "docker" in content or "kubepods" in content or "containerd" in content
    except OSError:
        return False


def _build_restart_argv() -> list[str]:
    """Rebuilds the original command line.

    `python -m executor` leaves sys.argv[0] pointing to __main__.py; re-executing
    that path directly would break the package imports. The __spec__ of __main__
    says whether we came from `-m` and which module it was.
    """
    import __main__
    spec = getattr(__main__, "__spec__", None)
    if spec is not None and getattr(spec, "name", None):
        modulo = spec.name.removesuffix(".__main__")
        return [sys.executable, "-m", modulo, *sys.argv[1:]]
    return [sys.executable, *sys.argv]


def _restart_process() -> None:
    """Replaces the current process with a new instance (os.execv).

    No-op when there is an external supervisor (container) or when disabled —
    in those cases the caller proceeds to sys.exit(1). Only returns on a no-op
    or failure; on success, the process is replaced and nothing after this runs.
    """
    if _AUTO_RESTART_MODE == "never":
        logger.info("Auto-restart desabilitado (EXECUTOR_AUTO_RESTART=never) — encerrando.")
        return
    if _AUTO_RESTART_MODE == "auto" and _in_container():
        logger.info("Em container — encerrando com codigo 1 para o supervisor reiniciar.")
        return

    # Unconditional guard: applies even to EXECUTOR_AUTO_RESTART=always.
    #
    # `os.execve` replaces the process on POSIX, but on Windows CPython's
    # implementation CREATES a new process and terminates the current one. The
    # supervisor would see the child it knows die, lose track of the real
    # executor — which stays alive, with a new PID, holding the WebSocket
    # connection under the same EXECUTOR_ID — and start a second one. Two
    # connections of the same executor.
    #
    # If there is a supervisor, restarting is ITS job: just exit with code != 0.
    from executor.supervisor import VAR_PID, pid_configurado
    if pid_configurado() is not None:
        logger.info(
            "Sob supervisor externo (%s) — encerrando com codigo 1 em vez de "
            "re-executar; o restart e responsabilidade dele.", VAR_PID,
        )
        return

    # Sliding window of attempts, propagated to the new process via env.
    agora = int(time.time())
    try:
        desde = int(os.getenv(_RESTART_SINCE_VAR, "") or agora)
        contagem = int(os.getenv(_RESTART_COUNT_VAR, "") or 0)
    except ValueError:
        desde, contagem = agora, 0
    if agora - desde > _RESTART_WINDOW_SEC:
        desde, contagem = agora, 0  # janela expirou

    if contagem >= _MAX_RESTARTS:
        logger.error(
            "Auto-restart abortado: %d reinicios em menos de %ds. A causa persiste "
            "(servidor reenviando config_changed?). Encerrando para nao entrar em loop.",
            contagem, _RESTART_WINDOW_SEC,
        )
        return

    env = {**os.environ, _RESTART_COUNT_VAR: str(contagem + 1), _RESTART_SINCE_VAR: str(desde)}
    argv = _build_restart_argv()
    logger.info("Reiniciando executor no mesmo processo (tentativa %d)...", contagem + 1)
    try:
        # execve replaces the process: without closing the dashboard first, the NEW
        # process would inherit a terminal in alternate mode, with no cursor.
        from executor import dashboard
        dashboard.emergency_stop()
        sys.stdout.flush()
        sys.stderr.flush()
        os.execve(argv[0], argv, env)
    except Exception as exc:
        logger.error("Falha ao reiniciar automaticamente (%s) — encerrando.", exc)


# NOTE: register_public_key_if_needed was removed. The X25519 public key is now
# sent at enrollment (POST /executores/enroll) along with the Ed25519 CSR.
# Re-enrollment requires a new OTP — there is no silent auto-registration.


def _observar_task(task: asyncio.Task) -> None:
    """Logs at ERROR if the background task dies with an exception.

    A task created and never observed dies silently: a trivial FileNotFoundError
    killed the sync of a folder and nothing showed up in the logs — the
    shutdown's `gather(..., return_exceptions=True)` also CONSUMED the
    exception, so not even asyncio's "Task exception was never retrieved" showed up.
    """
    def _callback(t: asyncio.Task) -> None:
        if t.cancelled():
            return  # cancelamento e o caminho normal de shutdown
        exc = t.exception()
        if exc is not None:
            logger.error(
                "Task de background '%s' terminou com excecao: %s",
                t.get_name(), exc, exc_info=exc,
            )

    task.add_done_callback(_callback)


# Sentinel for "count the whole queue, without discriminating by run". It must be
# its own object because `None` is a legitimate run_id: it is the bucket for
# events that belong to no job (GeoSync).
_QUALQUER_RUN = object()


class _FilaContada(asyncio.Queue):
    """asyncio.Queue that counts ENQUEUED and SENT items, per run.

    It exists to measure the consumer's REAL progress. `qsize` does not work: in
    a queue shared by N jobs and by GeoSync it goes up and down with other
    parties' production — with a producer faster than the sender, qsize NEVER
    decreases, even though the WebSocket is perfectly alive. That is how the
    node_events barrier started giving up after 3s claiming "sem conexao" (no
    connection) and dispatching the job_result before the job's own events.

    TWO decisions that the name "confirmados" has already hidden once:

      1. `confirmados` advances in `confirmar_envio()`, called by the sender ONLY
         when `ws.send` has returned. Before, it was glued to `task_done()`,
         which is unconditional (the item may have been re-enqueued or dropped
         by the attempt ceiling): the barrier took as "sent" what had
         FAILED and dispatched the job_result — carrying `__workflow_complete__`
         — ahead of the events it exists to wait for.

      2. The count is PER run_id, not only global. The queue is shared: waiting
         for the global watermark made a short workflow wait for the backlog of
         a large workflow and of GeoSync before sending its own result up.

    The optional `sink` peeks at each item in passing — it is how the dashboard
    finds out which node each run is on and how much GeoSync has transferred.
    Peeking here, and not in the emitters, is one touch point instead of two
    (ExecutorEventPublisher and SyncEventEmitter already converge on this queue)
    and catches any future emitter for free. Nothing is consumed: the
    `_event_sender_loop` keeps receiving everything.

    The `coletor` keeps the last lifecycle per node that could NOT be sent,
    for the sender to resend on reconnect (see ColetorDeLifecycle). It lives in
    the queue because the queue is the only object that the producer
    (ExecutorEventPublisher) and the consumer (ExecutorConnection) already share.
    """

    def __init__(self, maxsize: int = 0, sink=None):
        super().__init__(maxsize)
        self.enfileirados: int = 0
        self.confirmados:  int = 0
        self.enfileirados_por_run: dict = {}
        self.confirmados_por_run:  dict = {}
        self._sink = sink
        from executor.event_publisher import ColetorDeLifecycle
        self.coletor = ColetorDeLifecycle()

    @staticmethod
    def _run_de(item) -> object:
        return item.get("run_id") if isinstance(item, dict) else None

    def _put(self, item):
        self.enfileirados += 1
        run_id = self._run_de(item)
        self.enfileirados_por_run[run_id] = self.enfileirados_por_run.get(run_id, 0) + 1
        if self._sink is not None:
            try:
                self._sink.on_event(item)
            except Exception:
                # Telemetry NEVER brings down the publisher: this exception would go up
                # through event_publisher's call_soon_threadsafe, which runs outside
                # any try/except of the caller.
                pass
        super()._put(item)

    def confirmar_envio(self, item) -> None:
        """Marks that the item actually WENT OUT through the WebSocket. Only the sender calls it."""
        self._resolver(item)

    def resolver_sem_envio(self, item) -> None:
        """Settles the account of an item that left the queue WITHOUT having been sent.

        There are two cases, and both unbalanced the watermark:

          - re-enqueueing: `_put` counts the item AGAIN (`enfileirados +1`)
            but `confirmar_envio` only happens on a successful send. Each
            retry left a permanent deficit of 1 on that run, and the
            end-of-job barrier — which waits for `confirmados >= alvo` — never
            closed: it always exited via the stagnation timeout, delaying the
            `job_result` (and the `__workflow_complete__`) by seconds;
          - permanent drop (attempt ceiling, queue full on requeue): the
            item was counted on entry and will never be sent — without a
            counterweight, `alvo` stays unreachable forever.

        In both cases the item's PREVIOUS entry is closed; if it comes back
        to the queue, it comes back as a new item and is counted again in `_put`.
        """
        self._resolver(item)

    def _resolver(self, item) -> None:
        self.confirmados += 1
        run_id = self._run_de(item)
        self.confirmados_por_run[run_id] = self.confirmados_por_run.get(run_id, 0) + 1

    def esquecer_run(self, run_id) -> None:
        """Purges the counters of a finished run.

        Without this both dicts grow forever on a long-lived executor —
        one entry per run executed.
        """
        self.enfileirados_por_run.pop(run_id, None)
        self.confirmados_por_run.pop(run_id, None)
        # The collector keeps lifecycle per (run_id, node) to resend later. Without
        # this purge, a resend hours later revived the per-run entries we
        # just deleted — and nothing would remove them again, reopening the
        # O(runs) leak through the back door.
        coletor = getattr(self, "coletor", None)
        if coletor is not None:
            coletor.esquecer_run(run_id)


async def _aguardar_confirmacao(
    fila: _FilaContada,
    *,
    rotulo: str,
    timeout: float,
    estagnado: float,
    run_id=_QUALQUER_RUN,
) -> bool:
    """Waits for the consumer to send everything that was ALREADY in the queue. True = sent.

    WATERMARK barrier: snapshots `enfileirados` and waits for `confirmados` to
    reach that mark. Since the queue is FIFO with a single consumer, this is
    exactly "all the items that existed at this instant have been sent" —
    without waiting for what other producers enqueue later (that was the defect
    of the global `join()`, which made job A wait for job B's events) and
    without cutting off early while there is a live sender making progress.

    With `run_id`, the watermark is THAT run's: the job only waits for its own
    events, not for the backlog that another job or GeoSync had already enqueued
    ahead of it in the same queue.

    Gives up in two cases:
      - `estagnado` seconds without ANY confirmation in the WHOLE queue — there
        is no consumer (WS down, sender canceled, executor reconnecting with
        backoff);
      - total `timeout`, the worst-case ceiling even with a slow sender.

    The asymmetry between target and detector is intentional: "how much is left"
    is a property of THIS run, but "the sender is alive" is a property of the
    QUEUE. Measuring stagnation by the per-run counter accused the sender of
    being dead with the WebSocket perfectly alive: the queue is a single shared
    FIFO, so a short job's events sit physically behind the backlog of a large
    workflow and of GeoSync. While the sender drained that backlog (easily over
    3s on a client's upload link), the short job's `confirmados_por_run` did not
    budge, the barrier returned False and the `job_result` — which carries
    `__workflow_complete__` — was dispatched ahead of the run's own node_events,
    closing the canvas with the nodes still spinning.
    """
    if run_id is _QUALQUER_RUN:
        enfileirados = lambda: fila.enfileirados          # noqa: E731
        confirmados  = lambda: fila.confirmados           # noqa: E731
    else:
        enfileirados = lambda: fila.enfileirados_por_run.get(run_id, 0)   # noqa: E731
        confirmados  = lambda: fila.confirmados_por_run.get(run_id, 0)    # noqa: E731

    # Always GLOBAL: it is the evidence that there is a consumer draining.
    progresso_global = lambda: fila.confirmados                            # noqa: E731

    agora  = asyncio.get_running_loop().time
    limite = agora() + timeout
    alvo   = enfileirados()
    marca  = progresso_global()
    ultimo_progresso = agora()

    while confirmados() < alvo:
        await asyncio.sleep(0.05)
        if progresso_global() > marca:
            marca = progresso_global()
            ultimo_progresso = agora()
        pendentes = alvo - confirmados()
        if pendentes <= 0:
            break
        if agora() - ultimo_progresso >= estagnado:
            logger.warning(
                "Nenhum %s confirmado em %.0fs — consumidor parado (WS caido ou "
                "sender encerrado); %d pendente(s) seguem para o proximo envio.",
                rotulo, estagnado, pendentes,
            )
            return False
        if agora() >= limite:
            logger.warning(
                "Timeout de %.0fs drenando %s — %d pendente(s) seguem para o "
                "proximo envio.",
                timeout, rotulo, pendentes,
            )
            return False
    return True


async def _drenar_eventos_pendentes(
    fila: _FilaContada,
    run_id=_QUALQUER_RUN,
    timeout: float = 30.0,
    estagnado: float = 3.0,
) -> None:
    """Waits for the already-emitted node_events to go up before dispatching the result.

    `__workflow_complete__` travels with the job_result; without this barrier it
    arrived before the job's own node_events and the UI closed the run with the
    graph frozen/incomplete.

    The wait covers exactly the events of THIS run that existed when the job
    finished (see `_aguardar_confirmacao`) — not those of other jobs, nor those
    of GeoSync, which share the same queue.
    """
    # ExecutorEventPublisher enqueues via `call_soon_threadsafe` (it publishes from
    # inside asyncio.to_thread): the job's last events are still in the loop's
    # callback queue, not in _event_queue. Yielding control once makes those
    # callbacks run before we snapshot the watermark — without it the barrier
    # would exit precisely without the final events it exists to cover.
    await asyncio.sleep(0)
    await _aguardar_confirmacao(
        fila, rotulo="node_event", timeout=timeout, estagnado=estagnado, run_id=run_id,
    )


async def _drive_event_fanout(
    entrada: asyncio.Queue,
    managers: list,
    filas: list[asyncio.Queue],
) -> None:
    """Routes each drive_event received from the server to the SyncManager that owns the folder.

    Contract with executor/sync/manager.py: the manager exposes the SYNCHRONOUS
    method `claims_event(msg) -> bool`, which answers True when the event belongs
    to its folder. If nobody claims it, the event goes to the FIRST manager (the
    "primary") — that is the case of a new file, which is not in any manifest
    yet. `getattr` because the method may not exist yet: its absence counts as
    "does not claim" instead of breaking the routing.
    """
    while True:
        msg = await entrada.get()
        try:
            destino = 0
            for i, sm in enumerate(managers):
                claims = getattr(sm, "claims_event", None)
                if claims is None:
                    continue
                try:
                    if claims(msg):
                        destino = i
                        break
                except Exception as exc:
                    logger.warning(
                        "claims_event de '%s' falhou (%s) — ignorando este manager no roteamento.",
                        getattr(sm, "sync_dir", "?"), exc,
                    )
            try:
                filas[destino].put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning(
                    "Fila de drive_events de '%s' cheia — evento '%s' descartado.",
                    getattr(managers[destino], "sync_dir", "?"), msg.get("action", "?"),
                )
        finally:
            entrada.task_done()



def _causa_da_interrupcao(estado: str, limite_bytes: int | None) -> str:
    """Result text for a job that the previous process did not finish.

    The executor does not know WHY it died — Docker resets OOMKilled on restart —,
    so it says what it knows (it restarted, and at what point of the job) and the
    most likely cause, with the container's memory limit for whoever investigates.
    """
    from executor import result_store

    if estado == result_store.ESTADO_NA_FILA:
        base = (
            "O executor foi encerrado antes de começar esta execução — o processo "
            "ou o container reiniciou enquanto ela esperava na fila."
        )
    else:
        base = (
            "O executor foi encerrado no meio desta execução e ela não terminou — "
            "o processo ou o container reiniciou."
        )
    if limite_bytes:
        gb = f"{limite_bytes / 1024 ** 3:.1f}".replace(".", ",")
        return f"{base} A causa mais comum é falta de memória: o limite do container é de {gb} GB."
    return f"{base} A causa mais comum é falta de memória na máquina."


def _fechar_orfaos_do_boot_anterior() -> int:
    """Turns into a failure, with the probable cause, each job the previous
    process accepted and did not finish. Returns how many.

    Without this the server kept the run "Em andamento" (in progress): the
    executor came back in seconds (restart: on-failure), reconnected within the
    server's grace period and nobody knew about the job anymore — that is what
    happened with an executor killed by the cgroup OOM in the middle of an analysis.

    Best-effort: a failure here is logged and the boot continues.
    """
    from executor import result_store

    if not result_store.tomar_posse_do_diario():
        logger.warning(
            "Outro processo do executor ainda usa este outbox (o anterior drenando?) — "
            "os jobs do diário são dele; nenhum foi convertido em falha."
        )
        return 0
    try:
        orfaos = result_store.carregar_em_voo()
    except Exception as exc:
        logger.warning("Falha ao ler o diário de jobs do boot anterior: %s", exc)
        return 0
    if not orfaos:
        return 0
    from executor.sysinfo import _get_cgroup_ram_total
    limite = _get_cgroup_ram_total()
    for orfao in orfaos:
        result_store.put({
            "job_id":         orfao["job_id"],
            "run_id":         orfao["job_id"],
            "status":         "error",
            "error":          _causa_da_interrupcao(orfao["estado"], limite),
            "error_category": "executor_lost",
        })
    logger.warning(
        "%d job(s) do processo anterior não terminaram (reinício abrupto) — "
        "reportados como falha: %s",
        len(orfaos), [o["job_id"] for o in orfaos],
    )
    return len(orfaos)

async def main():
    # Configuration and enrollment are prerequisites, not something the executor
    # resolves on its own when starting. There used to be an interactive wizard
    # here that ran when EXECUTOR_ID was missing; it was removed along with
    # executor/setup.py.
    #
    # Reason: `input()` does not exist in any of the environments where the
    # executor actually runs — a container without -it, a service, and the
    # desktop app, which spawns it with the pipes captured. The wizard only
    # worked in the developer's terminal, and elsewhere it blew up with EOFError
    # instead of the useful message.
    #
    # The remaining paths work in all of them:
    #   python -m executor enroll --executor-id=<ID> --otp=<OTP> --server=<URL>
    #   the desktop app's link form
    #
    # The actual check happens in `config.assert_configured()` /
    # `assert_enrolled()`, further below — AFTER the channel with the supervisor
    # comes up, so that the failure becomes an event instead of an exit code.
    from executor import config

    from executor.job_executor import execute_job, init_private_key
    from executor.job_queue import ExecutorJobQueue
    from executor.connection import ExecutorConnection
    from executor import dashboard, result_store
    from executor.stats import ExecutorStats, NullStats

    # ── Dashboard: decide early, turn on late ─────────────────────────────────
    # The decision comes right away, so the queues and the connection are born
    # with the right collector. The `Live` only takes over the screen in step 7 —
    # the whole boot (banner, server key, outbox replay, GeoSync errors) must go
    # out on the normal console, which is where the operator expects to see what
    # went wrong at startup.
    #
    # Exception to "turn on late": in JSON mode the channel comes up RIGHT AWAY,
    # just below. The consumer is a program, not the screen — and an error in
    # phase 0 (server key, cert) must reach it as a `state` event, not as
    # "the process exited with code 1".
    _dash_modo, _dash_motivo = dashboard.should_enable_from_process()
    _dash_on = _dash_modo != dashboard.MODO_OFF
    stats = (
        ExecutorStats(
            executor_id=config.EXECUTOR_ID,
            version=config.EXECUTOR_VERSION,
            server_url=config.SERVER_URL,
        )
        if _dash_on else NullStats()
    )

    # ── Banner ────────────────────────────────────────────────────────────────
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║       Atlans Executor v%s                ║", config.EXECUTOR_VERSION)
    logger.info("╚══════════════════════════════════════════╝")
    logger.info("  Executor ID:  %s", config.EXECUTOR_ID)
    logger.info("  Servidor:  %s", config.SERVER_URL)
    logger.info("  Workers:   %d  |  Fila: %d  |  Timeout: %ds", config.MAX_CONCURRENT, config.MAX_QUEUE_SIZE, config.JOB_TIMEOUT)
    if config.SYNC_DIRS.strip():
        logger.info("  GeoSync:   %s", config.SYNC_DIRS)
    if not _dash_on:
        # A dashboard that fails to appear without explanation becomes a support ticket.
        logger.info("  Painel:    desligado (%s)", _dash_motivo)
    logger.info("")

    from executor.sysinfo import _collect_system_info
    stats.system = _collect_system_info() or {}
    stats.sync_dirs = tuple(
        d.strip() for d in config.SYNC_DIRS.split(",") if d.strip()
    )

    # ── Channel with the supervisor (JSON mode) ───────────────────────────────
    # Comes up BEFORE phase 0. The `shutdown_event` is born here, not in phase 5,
    # because of that: the `shutdown` command must work during the whole boot
    # — a desktop app that asks to stop while the executor resolves the server
    # key cannot go unanswered until phase 5.
    shutdown_event = asyncio.Event()

    # The connection only exists in phase 4. Until then, `reconnect` is an honest
    # no-op: there is no backoff to interrupt. The holder avoids having to rewire
    # the handler later, which would be one more subtle ordering to keep correct.
    _conn_holder: dict = {}

    def _reconectar_agora() -> bool:
        conn_ = _conn_holder.get("conn")
        return bool(conn_.reconectar_agora()) if conn_ is not None else False

    _dash = None
    if _dash_modo == dashboard.MODO_JSON:
        _dash = await dashboard.start(
            stats,
            modo=dashboard.MODO_JSON,
            # Wired in phase 3 by `vincular_fontes`: the queue does not exist yet.
            capacity_source=None,
            result_queue=None,
            intervalo=config.DASHBOARD_INTERVAL,
            ao_sair=shutdown_event.set,
            ao_reconectar=_reconectar_agora,
        )

    def _fase(nome: str, passo: str | None = None, detalhe: str | None = None) -> None:
        """Reports the boot phase to the supervisor. No-op without a channel.

        Without this, a failure in phase 0 reaches the desktop app only as "the
        process exited with 1" — and the difference between "cert expired" and
        "no network" turns into phone support.
        """
        if _dash is not None and hasattr(_dash, "emitir"):
            _dash.emitir("state", {"phase": nome, "step": passo, "detail": detalhe})

    async def _falhar_boot(passo: str, exc: BaseException) -> None:
        """Reports the failure and exits with 1.

        Without this, a boot failure reaches the supervisor only as an exit code.
        The difference between "cert expired" and "no network" is the difference
        between the UI offering 'redo enrollment' and offering 'try again' — and
        the exact step only exists here.
        """
        _fase("failed", passo, detalhe=str(exc))
        if _dash is not None and _dash_modo == dashboard.MODO_JSON:
            await _dash.stop()          # drains the buffer before the process goes away
        raise SystemExit(1)

    # ── Supervisor watchdog (anti-orphan) ─────────────────────────────────────
    from executor import supervisor as _supervisor
    _watchdog_task = _supervisor.criar_task(shutdown_event.set)

    # ── Configuration and enrollment ──────────────────────────────────────────
    # These checks run AFTER the channel comes up, not before.
    #
    # They used to be up top, right after the config import, and the effect was
    # bad for a supervisor: the process exited with 1 without emitting any event,
    # so the app had no way to tell "enrollment missing" from "the executor
    # crashed" — and treated it as a crash, restarting with backoff forever a
    # condition only the user can resolve.
    #
    # The two steps are separate because the user's action is different:
    # `config` asks to configure EXECUTOR_ID, `enrollment` asks to redo the enroll.
    _fase("booting", "config")
    try:
        config.assert_configured()
    except SystemExit as exc:
        logger.error("%s", exc)     # the message only showed up because it was a SystemExit
        await _falhar_boot("config", exc)
    try:
        config.assert_enrolled()
    except SystemExit as exc:
        logger.error("%s", exc)
        await _falhar_boot("enrollment", exc)

    _fase("booting", "server_key")

    # ── 0. Server signing key (pinned locally) ───────────────────────────────
    # This used to be a GET on every boot, without pinning and with
    # follow_redirects=True: whoever won the channel on any restart delivered
    # their own key and could then sign arbitrary jobs. Now the key comes from
    # the enroll (no window at all) or from a one-time TOFU that stays pinned on disk.
    # See executor/server_key.py for the full order of precedence.
    from executor.server_key import ServerKeyError, resolve_server_signing_key
    try:
        config.SERVER_SIGNING_PUBLIC_KEY = await resolve_server_signing_key(
            config.EXECUTOR_CERT_DIR, config.SERVER_URL,
        )
    except ServerKeyError as exc:
        logger.error(
            "Chave de assinatura do servidor indisponivel — o executor NAO sobe sem "
            "ela (rodar sem verificacao de assinatura aceitaria job de qualquer "
            "origem).\n%s", exc,
        )
        await _falhar_boot("server_key", exc)

    # ── 1. Initializes the X25519 private key (envelope decryption) ───────────
    # init_private_key() loads the key via `crypto.load_private_key` (READ-only)
    # and keeps it in job_executor's global. The key was generated a single time
    # at enrollment and saved to config.EXECUTOR_PRIVATE_KEY_PATH — if it is gone,
    # generating another would make the executor come up "online" with a public
    # key that does not match the one registered on the server and fail 100% of
    # jobs. See crypto.PrivateKeyMissingError.
    from executor.crypto import PrivateKeyMissingError
    try:
        init_private_key()
    except PrivateKeyMissingError as exc:
        # Same handling as ServerKeyError above: the exception exists precisely to
        # give the operator a clear instruction (redo the enroll) — burying it in
        # a raw traceback would defeat its purpose.
        logger.error("%s", exc)
        await _falhar_boot("private_key", exc)

    # ── 2. Own thread pool ────────────────────────────────────────────────────
    # Every `asyncio.to_thread` of the flow engine falls into the loop's DEFAULT
    # executor, sized at min(32, cpu_count + 4). Two problems: (a) N concurrent
    # jobs compete for the same pool with no relation to MAX_CONCURRENT;
    # (b) in Docker, cpu_count() reports the HOST's cores, not the container's
    # quota — the pool gets huge and the threads just fight over CPU.
    # Sizing from MAX_CONCURRENT gives each job predictable headroom.
    loop = asyncio.get_running_loop()
    _thread_pool = ThreadPoolExecutor(
        max_workers=max(8, config.MAX_CONCURRENT * 4),
        thread_name_prefix="atlas-exec",
    )
    loop.set_default_executor(_thread_pool)

    # ── 3. Creates communication queues ───────────────────────────────────────
    # Results queue (executor → server). It needs a LIMIT: without a live WS
    # nobody drains it, and each retained result holds memory until the next send.
    # Sized for the worst legitimate case — everything that can be in flight
    # (queue + running jobs) plus headroom for the outbox replay at boot.
    _result_queue = _FilaContada(
        maxsize=config.MAX_QUEUE_SIZE + config.MAX_CONCURRENT + 32
    )
    # Node events queue (ExecutorEventPublisher → connection → server).
    # The dashboard's `sink` peeks in passing; with the dashboard off it is a NullStats.
    _event_queue = _FilaContada(maxsize=500, sink=stats if _dash_on else None)
    # Drive push events queue (server → executor via WebSocket). It is the INPUT
    # queue: the fan-out below distributes to each SyncManager's own queue.
    _drive_event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    def _enqueue_result(result: dict) -> None:
        """Enqueues a result for the sender without EVER blocking.

        `await put()` on a full queue would hold the job's worker indefinitely
        when the WS is down (nobody drains). If it overflows, the result is
        already persisted in the result_store (outbox) — but we log at ERROR
        because the immediate send was lost: dropping silently would leave the
        run "running" on the server without any clue.

        Careful with the log's promise: the outbox replay RESENDS, but the server
        REJECTS (`_is_run_terminal` in executor_ws_router) everything that arrives
        after `_fail_orphan_runs_if_gone` has closed the run as orphaned — and the
        queue only fills when the WS has been down for quite a while, exactly the
        scenario in which the runs have already been closed. Do not promise
        recovery here.
        """
        try:
            _result_queue.put_nowait(result)
        except asyncio.QueueFull:
            logger.error(
                "Fila de resultados cheia (%d) — job '%s' nao sera enviado agora. "
                "O resultado fica no outbox e sera reenviado no proximo start, mas "
                "o servidor o recusa se ja tiver fechado o run como orfao.",
                _result_queue.qsize(), result.get("job_id", "?"),
            )

    async def on_execute(message: dict):
        """Executa o job e envia resultado ao servidor via WebSocket."""
        # The SINGLE point every job goes through — and therefore the natural place
        # to measure. The duration here is end-to-end (includes the events barrier).
        job_id = message.get("envelope", {}).get("job_id", "?")
        _t0 = time.monotonic()
        # run_id == job_id in the server's dispatch (see job_executor.execute_job).
        # Reporting it already here is what lets the node events be matched to the
        # right job: without it, with MAX_CONCURRENT simultaneous jobs they would all
        # start without a run_id and the first event to arrive would be assigned to any of them.
        stats.on_job_started(job_id, run_id=job_id)
        # Journal: the job left the queue and started. If the process dies from here
        # until `result_store.put`, the next boot reports it as interrupted midway.
        result_store.marcar_executando(job_id)
        result = None
        status = "error"
        try:
            result = await execute_job(message, event_queue=_event_queue)
            status = result.get("status", "error")
            # The barrier is PER RUN: with the shared queue, waiting for the global
            # watermark made this job also wait for the backlog of a large
            # workflow and of GeoSync — up to 30s of "almost done" on the dashboard.
            await _drenar_eventos_pendentes(_event_queue, result.get("run_id") or job_id)
            # 'output' carries the ENTIRE final_outputs (GeoDataFrames, hundreds of
            # MB). The server never uses this field — the sender already dropped it
            # at serialization time — but until then it kept the whole object graph
            # alive inside the queue and the outbox. Removed here, at the source.
            result.pop("output", None)
            # Persists the result BEFORE enqueueing — guarantees that a process restart
            # does not lose the send. mark_sent() is called by the sender loop
            # after the server confirms.
            result_store.put(result)
            _enqueue_result(result)
        except asyncio.CancelledError:
            # Cancellation of the job (job_queue.cancel) or of the worker (shutdown).
            # Without this branch the `finally` would count the interruption as an error.
            status = "cancelled"
            raise
        finally:
            # Per-run counters are O(runs) and nothing deletes them on its own: without
            # this purge, a long-lived executor accumulates one entry per job
            # executed in both dicts.
            _event_queue.esquecer_run((result or {}).get("run_id") or job_id)
            stats.on_job_finished(
                job_id, status, time.monotonic() - _t0,
                run_id=(result or {}).get("run_id"),
                metrics=((result or {}).get("stats") or {}).get("__metrics__"),
            )

    # Maximum space the outbox replay may take up in _result_queue. The rest
    # stays reserved for the results of the jobs running NOW — they use
    # put_nowait and would be DROPPED if the historical backlog filled the queue.
    _RESERVA_OUTBOX = 8

    async def _replay_outbox() -> None:
        """Resends, at the sender's pace, the results left over from the previous boot.

        This used to be a synchronous for loop with put_nowait BEFORE the
        connection existed: with the bounded queue (86 slots by default) and
        `load_pending()` without a LIMIT, an outbox with 300 rows lost 214 of
        them at ERROR — and since the outbox is only read at boot, it only
        drained 86 per restart. Here the replay becomes a background task that
        waits for space: nothing is dropped and nothing competes with the live
        jobs.

        Best-effort: any failure is swallowed with a log — replay can never
        keep the executor from operating.
        """
        try:
            pending = await asyncio.to_thread(result_store.load_pending)
        except Exception as exc:
            logger.warning("Falha ao restaurar resultados pendentes (ignorando): %s", exc)
            return
        if not pending:
            return

        logger.info("Restaurando %d resultado(s) pendente(s) de execucoes anteriores.", len(pending))
        for r in pending:
            # No await between the check and the put: put_nowait cannot fail.
            while _result_queue.qsize() >= _RESERVA_OUTBOX:
                await asyncio.sleep(0.2)
            _result_queue.put_nowait(r)

    async def on_cancelled(message: dict):
        """Reports to the server that the job was canceled.

        Without this the run would stay "running" forever: the interrupted task
        never gets to produce a result, and the server only knows something
        changed when it receives a job_result.
        """
        envelope = message.get("envelope", {})
        job_id = envelope.get("job_id", "?")
        # `cancel_reason` comes from job_queue when the cancellation did NOT come from
        # the user (e.g. a job that was still in the queue when the executor shut
        # down). Without it the operator saw "cancelada pelo usuario" (canceled by
        # the user) for something nobody canceled. No 'output': the server does
        # not use it and it would only take up memory/outbox.
        motivo = message.get("cancel_reason") or "Execução cancelada pelo usuário."
        # The server dispatches with run_id == job_id (see job_executor.execute_job).
        result = {
            "job_id": job_id,
            "run_id": job_id,
            "status": "cancelled",
            "error": motivo,
        }
        result_store.put(result)
        _enqueue_result(result)
        # Covers the job canceled BEFORE starting (drained from the queue on shutdown):
        # that one never goes through on_execute, so it would not be counted
        # anywhere. If it was already running, on_execute's `finally` counted it —
        # and the collector's on_job_cancelled ignores the id that has already left.
        stats.on_job_cancelled(job_id, motivo)

    job_queue = ExecutorJobQueue(
        on_execute=on_execute,
        max_concurrent=config.MAX_CONCURRENT,
        max_queue_size=config.MAX_QUEUE_SIZE,
        on_cancelled=on_cancelled,
    )
    await job_queue.start()

    # ── 4. Connects to the server ─────────────────────────────────────────────
    # `thread_pool`: the connection needs it to report honest capacity —
    # queued/running count JOBS and do not see threads stuck on a node that the
    # timeout cannot cancel. See ExecutorConnection._pool_saturado.
    conn = ExecutorConnection(job_queue, _result_queue, event_queue=_event_queue,
                           drive_event_queue=_drive_event_queue, stats=stats,
                           thread_pool=_thread_pool)

    # The queue notifies the connection the instant it starts draining, so the
    # saturated capacity goes out right away instead of waiting for the
    # _capacity_loop's 10s tick (see ExecutorJobQueue.shutdown and
    # conn.push_capacity). Wired here because the queue is built BEFORE the
    # connection — it is an argument of the connection's constructor.
    job_queue.set_on_draining(conn.push_capacity)

    # Now the channel with the supervisor has somewhere to read capacity from, and
    # the `reconnect` command starts having an effect.
    _conn_holder["conn"] = conn
    if _dash is not None and hasattr(_dash, "vincular_fontes"):
        _dash.vincular_fontes(capacity_source=job_queue.get_capacity,
                              result_queue=_result_queue)
    _fase("booting", "connection")

    # ── 5. Graceful shutdown ──────────────────────────────────────────────────
    # The `shutdown_event` was created up above, before phase 0, so that the
    # supervisor's `shutdown` command works during the whole boot.

    def _on_signal():
        logger.info("Sinal de shutdown recebido — encerrando...")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except NotImplementedError:
            # Windows does not support add_signal_handler in asyncio
            pass

    # ── 6. GeoSync — local folder synchronization ──────────────────────────────
    sync_tasks = []
    # Declared outside ALL the `if`s below: `_sincronizar_agora` (further on) closes
    # over it and is called by the UI's "Sincronizar agora" (Sync now) button. With
    # EXECUTOR_SYNC_DIRS empty the name was never bound, and the closure raised
    # NameError in the most common case of all — an executor without GeoSync
    # configured — instead of returning the 0 the UI uses to say "no folder configured".
    _sync_managers: list = []
    if config.SYNC_DIRS.strip():
        from executor.sync.manager import SyncManager

        # Resolve workspace_id: .env > API (auto-detection with validation)
        _sync_ws_id = config.WORKSPACE_ID
        _workspaces: list = []

        # Always queries the API to get the accessible workspaces (mTLS verifies identity).
        try:
            from executor.utils import ws_to_http, mtls_httpx_kwargs
            base_url = ws_to_http(config.SERVER_URL)
            async with httpx.AsyncClient(timeout=15, follow_redirects=True, **mtls_httpx_kwargs(base_url)) as _c:
                _r = await _c.get(f"{base_url}/executores/{config.EXECUTOR_ID}/status")
                if _r.status_code == 200:
                    _agent_data = _r.json()
                    _workspaces = _agent_data.get("workspaces", [])
        except Exception as _exc:
            logger.warning("GeoSync: falha ao consultar status do executor: %s", _exc)

        if _sync_ws_id:
            # EXECUTOR_WORKSPACE_ID set — validates that it is in the list of accessible workspaces
            _accessible_ids = [w["id_hash"] for w in _workspaces]
            if _accessible_ids and _sync_ws_id not in _accessible_ids:
                logger.error(
                    "GeoSync desabilitado: workspace '%s' nao esta acessivel a este executor. "
                    "Verifique EXECUTOR_WORKSPACE_ID ou a configuracao de workspace no servidor.",
                    _sync_ws_id,
                )
                _sync_ws_id = None
            else:
                logger.info("GeoSync: workspace_id definido via .env: %s", _sync_ws_id)
        else:
            # Auto-detection: only if the API returns exactly 1 workspace
            if len(_workspaces) == 1:
                _sync_ws_id = _workspaces[0]["id_hash"]
                logger.info(
                    "GeoSync: workspace auto-detectado: %s (%s)",
                    _workspaces[0].get("name", ""), _sync_ws_id,
                )
            elif len(_workspaces) > 1:
                logger.warning(
                    "GeoSync desabilitado: executor tem %d workspaces vinculados. "
                    "Defina EXECUTOR_WORKSPACE_ID no .env para ativar o GeoSync.",
                    len(_workspaces),
                )
            elif not _workspaces:
                logger.warning(
                    "GeoSync desabilitado: executor nao tem workspaces acessiveis "
                    "ou e do tipo default. Defina EXECUTOR_WORKSPACE_ID no .env ou "
                    "vincule um workspace ao executor no servidor.",
                )

        if _sync_ws_id:
            # One queue PER SyncManager. Before, they all received the SAME queue, and
            # `Queue.get()` wakes only ONE waiter: with N folders, each
            # drive_event ended up at 1 randomly picked manager and the other N-1
            # never saw it. The fan-out below is what decides the destination.
            _sync_queues: list[asyncio.Queue] = []

            for sync_dir in config.SYNC_DIRS.split(","):
                sync_dir = sync_dir.strip()
                if not sync_dir:
                    continue
                sm_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
                sm = SyncManager(
                    sync_dir=sync_dir,
                    workspace_id=_sync_ws_id,
                    server_url=config.SERVER_URL,
                    executor_id=config.EXECUTOR_ID,
                    interval=config.SYNC_INTERVAL,
                    event_queue=_event_queue,
                    drive_event_queue=sm_queue,
                )
                _sync_managers.append(sm)
                _sync_queues.append(sm_queue)
                task = asyncio.create_task(sm.run(), name=f"geosync-{sync_dir}")
                _observar_task(task)
                sync_tasks.append(task)
                logger.info("GeoSync ativado: '%s' → workspace '%s'", sync_dir, _sync_ws_id)

            if _sync_managers:
                fanout = asyncio.create_task(
                    _drive_event_fanout(_drive_event_queue, _sync_managers, _sync_queues),
                    name="drive-event-fanout",
                )
                _observar_task(fanout)
                sync_tasks.append(fanout)

    # ── 6.5. Renewal automatico do cert mTLS (loop em background) ────────────
    from executor.renewal import renewal_loop
    renewal_task = asyncio.create_task(
        renewal_loop(config.SERVER_URL, config.EXECUTOR_CERT_DIR),
        name="cert-renewal",
    )

    # ── 7. Main loop ──────────────────────────────────────────────────────────
    # Orphans from the previous process become results BEFORE the connection: they
    # go into the outbox, go out through the replay just below and already show up
    # in the first inventory as "pending result" — the server does not close them
    # as lost.
    _fechar_orfaos_do_boot_anterior()

    conn_task = asyncio.create_task(conn.run(), name="executor-connection")

    # Outbox replay ONLY after the connection exists: it pays out at the pace of
    # _result_sender_loop and has nothing to do before there is a sender.
    replay_task = asyncio.create_task(_replay_outbox(), name="outbox-replay")
    _observar_task(replay_task)

    # Dashboard: takes over the screen now, with the whole boot already in the
    # scrollback. From here on the step-by-step log goes to the file — `start()`
    # returns None (and the console stays as it was) if the file does not open.
    def _sincronizar_agora() -> int:
        """Wakes up the cycle of each GeoSync folder. Returns how many responded.

        Zero means "no active GeoSync" — folder not configured, ambiguous
        workspace, or the mode turned off. `json_runtime` turns that number into
        the `detalhe` of the `sync_now` ack ("N pasta(s) acordada(s)" or "nenhuma
        pasta do GeoSync configurada").

        CAVEAT: the desktop app does NOT show that detail yet. `window.atlas.
        comando()` resolves to the return of `Supervisor.enviar()`, which only
        says whether the write to stdin worked (desktop/src/main/index.ts), and
        the renderer prints "Varredura solicitada." (scan requested) in any case
        (GeoSync.tsx). Bringing the ack back to the renderer is work in the IPC
        layer, not here — but the number already comes out correct on this side.

        It must be defined BEFORE the `dashboard.start` below: it is passed
        as an argument in a call that runs immediately, and defining it later
        made the name an unbound local — `UnboundLocalError` at boot in
        RICH mode, which is the default for anyone running the executor in a terminal.
        """
        return sum(1 for sm in _sync_managers if sm.sincronizar_agora())

    # The JSON runtime comes up before phase 0 and receives the handler here,
    # through the same door it already uses for capacity and queue. Without this,
    # `sync_now` — the command the desktop app fires from the "Sincronizar agora"
    # button — always answered "sem handler de sincronizacao" (no sync handler):
    # the handler was only delivered to the rich dashboard, which the desktop does
    # not use.
    if _dash is not None and hasattr(_dash, "vincular_fontes"):
        _dash.vincular_fontes(ao_sincronizar=_sincronizar_agora)

    if _dash_modo == dashboard.MODO_RICH:
        _dash = await dashboard.start(
            stats,
            modo=dashboard.MODO_RICH,
            capacity_source=job_queue.get_capacity,
            result_queue=_result_queue,
            intervalo=config.DASHBOARD_INTERVAL,
            # The 'q' key goes through the same path as a SIGTERM: an orderly
            # shutdown, no shortcut. On Windows this matters even more, because
            # there `add_signal_handler` registers nothing and Ctrl+C can kill
            # the process before any `finally` runs.
            ao_sair=shutdown_event.set,
            # 'r' key: cuts the reconnect backoff short. Whoever presses it knows
            # something the process does not — the network is back, the server is up.
            ao_reconectar=conn.reconectar_agora,
            # The UI's "Sincronizar agora" (Sync now): wakes the GeoSync cycle without
            # waiting for the interval. Whoever asks knows something the executor has not seen yet.
            ao_sincronizar=_sincronizar_agora,
        )

    _fase("running")

    # Waits for WHICHEVER COMES FIRST: an OS signal or the connection closing on its own.
    #
    # Watching only shutdown_event left the process hanging forever
    # whenever the server closed the connection (control revoked/shutdown/
    # config_changed, or terminal deny 401/403/404): conn.run() returned, the
    # conn_task finished and nobody noticed — executor alive, disconnected and
    # not restarting. Since restart_requested is only read after this await, the
    # `sys.exit(1)` that triggers Docker's restart was never reached.
    #
    # `revoked`/`shutdown` emitted no signal at all (hung on any OS) and
    # `config_changed` only emitted SIGTERM on POSIX (hung on Windows, where
    # add_signal_handler does not even get to register the handler).
    stop_task = asyncio.create_task(shutdown_event.wait(), name="shutdown-signal")
    try:
        await asyncio.wait({stop_task, conn_task}, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        pass
    finally:
        stop_task.cancel()
        if _watchdog_task is not None:
            _watchdog_task.cancel()
        # The RICH dashboard exits BEFORE block 8, not after: shutdown is
        # precisely when the operator needs to read the text — "aguardando jobs
        # em andamento" (waiting for running jobs), results left behind, fatal
        # traceback. With the `Live` still up, the screen would clear and none of
        # that would show.
        #
        # The JSON channel does the OPPOSITE: it stays up until the end of block 8.
        # It is during draining that the supervisor needs it most — it is what lets
        # the UI show "3 jobs finishing" with a real number instead of a blind
        # spinner, and tell an orderly shutdown from a crash via `state: stopped`.
        if _dash is not None and _dash_modo == dashboard.MODO_RICH:
            await _dash.stop()
        _fase("draining")

    # ── 8. ORDERLY shutdown ───────────────────────────────────────────────────
    # The order here is critical and was inverted: `conn_task.cancel()` came
    # BEFORE `job_queue.shutdown()`. Without a connection there is no
    # _result_sender_loop, so no result of a running job reached the server: it
    # marked the runs as orphaned (_fail_orphan_runs) and the outbox replay on the
    # next boot was rejected by idempotency (_is_run_terminal). It happened on EVERY
    # deploy with a job running.
    #
    # Correct: 1) finish the jobs, 2) drain the results through the still-live WS,
    # 3) only then tear down the connection, renewal and sync.
    # `job_queue.shutdown()` marks the queue as draining RIGHT on its first line,
    # and `get_capacity()` announces saturation from then on — that is what takes
    # this executor off the top of the server's least-loaded ranking while it dies.
    logger.info("Shutdown: aguardando jobs em andamento...")
    await job_queue.shutdown(timeout=120)

    # The outbox replay stops HERE: from now on _result_queue has a fixed target
    # (what the jobs just produced) and injecting historical backlog would only
    # delay the draining that still has a chance of being accepted by the server.
    replay_task.cancel()

    if conn_task.done():
        # Connection closed for good (revoked/shutdown/config_changed or terminal
        # deny): conn.run() returned and there will be no reconnect — there is no
        # sender and waiting would be pure delay.
        if not _result_queue.empty():
            logger.warning(
                "Conexao ja encerrada — %d resultado(s) ficam para o replay do outbox.",
                _result_queue.qsize(),
            )
    else:
        # A live `conn_task` does NOT mean a live WS session: during the reconnect
        # backoff conn.run() is just sleeping, with no _result_sender_loop at
        # all, and the previous `wait_for(join(), 30)` paid the full 30s with
        # nobody on the other side — 150s of shutdown in the worst case, above
        # any default grace period. Instead of guessing from the task state,
        # we MEASURE: `_aguardar_confirmacao` gives up after 5s if no result is
        # confirmed, and only keeps waiting while the sender makes progress.
        await _aguardar_confirmacao(
            _result_queue, rotulo="resultado", timeout=30, estagnado=5,
        )

    conn_task.cancel()
    renewal_task.cancel()
    for t in sync_tasks:
        t.cancel()
    # renewal_task was being canceled but NOT awaited here — the loop could
    # be destroyed with the task still pending ("Task was destroyed but it is
    # pending!") and the renewal's `finally` never ran.
    await asyncio.gather(
        conn_task, renewal_task, replay_task, *sync_tasks, return_exceptions=True,
    )

    # Closes asyncpg pools explicitly before the event loop shuts down
    # (avoids RuntimeError: There is no current event loop in pool.release())
    try:
        from flow.utils.get_asyncpg_pool import close_all_pools
        await close_all_pools()
    except Exception as exc:
        logger.warning("Falha ao fechar pools asyncpg no shutdown: %s", exc)

    # Shuts down our own thread pool: cancel_futures drops what never
    # started; joining the live threads is left to the shutdown_default_executor()
    # that asyncio.run() executes when closing the loop.
    _thread_pool.shutdown(wait=False, cancel_futures=True)
    # Same handling for the control plane pool (validation/crypto), which
    # is separate precisely so it does not share a fate with the nodes.
    from executor.job_executor import _CONTROL_POOL
    _CONTROL_POOL.shutdown(wait=False, cancel_futures=True)

    logger.info("Executor encerrado.")

    # The channel's last event, and only then does it close (draining the buffer).
    # A supervisor that sees `stopped` knows it was an orderly shutdown; its
    # absence means a crash, and the two call for different handling — restart
    # with backoff in one case, respect the user's decision in the other.
    #
    # An authoritative deny (close 4401/4403/4404, or control `revoked`) is a
    # THIRD case, and cannot go out as `stopped`: the executor was removed or
    # revoked on the server, and only a new enrollment brings it back. Reported
    # as `failed` so the supervisor stops instead of restarting against a
    # server that has already said no — it was a restart loop every 2s.
    if conn.terminal_deny:
        _fase("failed", "revoked", detalhe=conn.terminal_deny)
    else:
        _fase("stopped", detalhe="restart_requested" if conn.restart_requested else None)

    if _dash is not None and _dash_modo == dashboard.MODO_JSON:
        await _dash.stop()

    if conn.restart_requested:
        _restart_process()
        sys.exit(1)  # Docker restart: on-failure → reinicia o container

    if conn.terminal_deny:
        # Code != 0 for Docker's supervisor too: `restart: on-failure`
        # restarts, but the operator sees the reason in the log instead of a silent
        # exit 0 that suggests a normal shutdown.
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        # Dashboard safety net. The normal path has already closed it in block 7,
        # but an exception before that (or Windows' Ctrl+C, where there is no
        # signal handler registered) would leave the terminal in the alternate
        # buffer and with no cursor. emergency_stop is idempotent.
        from executor import dashboard
        dashboard.emergency_stop()
