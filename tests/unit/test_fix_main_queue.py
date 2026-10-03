# tests/unit/test_fix_main_queue.py
"""
Fixes for the executor entry point (main.py), the job queue (job_queue.py)
and config validation (config.py).

Covers:
  D2 — shutdown silently discarded the jobs that were still in the queue
  D3 — EXECUTOR_MAX_CONCURRENT=0 started the executor with no worker at all
  D4 — `cancel()` of an unknown job leaked into the `_cancelled` set and lied "queued"
  B8 — a single drive_events queue shared by N SyncManagers
  D1 — background task dying silently
"""
import asyncio
import logging

import pytest

from executor.job_queue import ExecutorJobQueue


def _job(job_id: str, priority: int = 5) -> dict:
    return {"envelope": {"job_id": job_id, "priority": priority}}


# ── D2: shutdown notifies the jobs that never got to run ─────────────────────

@pytest.mark.asyncio
async def test_shutdown_warns_about_jobs_left_in_queue():
    """Without this the server closed as 'desconectou durante a execucao' (disconnected
    during execution) a job that had not even started — and there was no safe way to redispatch."""
    liberar = asyncio.Event()
    avisados: list[tuple[str, str]] = []

    async def on_execute(message):
        if message["envelope"]["job_id"] == "bloqueia":
            await liberar.wait()

    async def on_cancelled(message):
        avisados.append((message["envelope"]["job_id"], message.get("cancel_reason") or ""))

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1,
                             max_queue_size=10, on_cancelled=on_cancelled)
    await queue.start(n_workers=1)

    await queue.enqueue(_job("bloqueia"))
    await asyncio.sleep(0.05)                 # worker pega o primeiro
    await queue.enqueue(_job("na-fila-1"))
    await queue.enqueue(_job("na-fila-2"))

    liberar.set()
    await queue.shutdown(timeout=2)

    ids = {job_id for job_id, _ in avisados}
    assert ids == {"na-fila-1", "na-fila-2"}
    assert all(motivo == ExecutorJobQueue.NAO_INICIADO for _, motivo in avisados)
    # The PriorityQueue really did empty. (`get_capacity()["queued"]` NO longer
    # works as proof: after shutdown it advertises saturation on purpose —
    # see test_capacity_announces_saturation_during_shutdown.)
    assert queue._queue.qsize() == 0


@pytest.mark.asyncio
async def test_shutdown_does_not_wait_for_polling_when_there_is_no_job():
    """_wait_for_running became an Event: with no job running, shutdown is immediate
    (the 0.5s polling charged half a second to every deploy)."""
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=2, max_queue_size=10)
    await queue.start(n_workers=1)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await queue.shutdown(timeout=5)
    assert loop.time() - inicio < 0.4


@pytest.mark.asyncio
async def test_capacity_announces_saturation_during_shutdown():
    """A draining executor must not keep being the 'least loaded' in the pool.

    Reproduces the server's rule: `ExecutorConnection.is_full()` compares
    queued+running >= max_concurrent+max_queue, and `_resolve_candidates` puts
    last whoever that same arithmetic says is full. With the real load (queue drained,
    jobs finishing) the executor in shutdown ended up FIRST in the ranking and every
    routed job came back as "Executor em shutdown." without failover.
    """
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=4, max_queue_size=50)
    await queue.start(n_workers=1)

    antes = queue.get_capacity()
    assert antes["queued"] + antes["running"] < antes["max_concurrent"] + antes["max_queue"]

    await queue.shutdown(timeout=2)

    cap = queue.get_capacity()
    # The server's is_full() rule — even if it clamps max_* down.
    assert cap["queued"] + cap["running"] >= cap["max_concurrent"] + cap["max_queue"]
    # And the advertised load must be higher than that of any healthy executor.
    assert cap["queued"] + cap["running"] > antes["queued"] + antes["running"]


# ── D4: cancel() of an unknown job ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_of_unknown_job_returns_unknown_without_leaking():
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)

    assert queue.cancel("nunca-visto") == "unknown"
    assert queue._cancelled == set(), "id desconhecido nao pode ficar marcado para sempre"


@pytest.mark.asyncio
async def test_cancel_of_enqueued_job_stays_queued():
    """The 'queued' answer must stay valid for a job that IS in the queue."""
    liberar = asyncio.Event()
    executados: list[str] = []

    async def on_execute(message):
        job_id = message["envelope"]["job_id"]
        if job_id == "bloqueia":
            await liberar.wait()
        executados.append(job_id)

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)
    await queue.start(n_workers=1)
    try:
        await queue.enqueue(_job("bloqueia"))
        await asyncio.sleep(0.05)
        await queue.enqueue(_job("na-fila"))

        assert queue.cancel("na-fila") == "queued"
        liberar.set()
        await asyncio.sleep(0.1)
        assert executados == ["bloqueia"]
    finally:
        await queue.shutdown(timeout=2)


# ── D3: config ranges ────────────────────────────────────────────────────────

def test_env_int_rejects_zero_and_garbage(monkeypatch, caplog):
    """MAX_CONCURRENT=0 left the executor online, with capacity 0 (preferred by the
    least-loaded scheduler), accepting jobs that would never execute."""
    from executor._ambiente import ler_int

    monkeypatch.setenv("_TESTE_INT", "0")
    with caplog.at_level(logging.WARNING):
        assert ler_int("_TESTE_INT", 4, minimo=1) == 4

    monkeypatch.setenv("_TESTE_INT", "nao-e-numero")
    assert ler_int("_TESTE_INT", 4, minimo=1) == 4

    monkeypatch.setenv("_TESTE_INT", "999999")
    assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == 4

    monkeypatch.setenv("_TESTE_INT", "8")
    assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == 8

    monkeypatch.delenv("_TESTE_INT")
    assert ler_int("_TESTE_INT", 4) == 4


def test_config_exposes_sanitized_values():
    from executor import config

    assert config.MAX_CONCURRENT >= 1
    assert config.MAX_QUEUE_SIZE >= 1
    assert config.JOB_TIMEOUT >= 1


def test_assert_configured_complains_without_executor_id(monkeypatch):
    """The requirement lives here, not in the import of config.py, which no longer aborts."""
    from executor import config

    monkeypatch.setattr(config, "EXECUTOR_ID", "")
    with pytest.raises(SystemExit):
        config.assert_configured()


# ── B8: fan-out dos drive_events ─────────────────────────────────────────────

class _ManagerFake:
    def __init__(self, sync_dir: str, claims: set[str] | None = None):
        self.sync_dir = sync_dir
        self._claims = claims or set()

    def claims_event(self, msg: dict) -> bool:
        return msg.get("file", {}).get("original_name", "") in self._claims


class _ManagerWithoutContract:
    """A manager that has not implemented claims_event yet — must not break the fan-out."""
    def __init__(self, sync_dir: str):
        self.sync_dir = sync_dir


async def _run_fanout(entrada, managers, queues, eventos):
    from executor.main import _drive_event_fanout

    task = asyncio.create_task(_drive_event_fanout(entrada, managers, queues))
    for ev in eventos:
        entrada.put_nowait(ev)
    await asyncio.wait_for(entrada.join(), timeout=2.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def _evento(nome: str) -> dict:
    return {"action": "file_created", "file": {"original_name": nome, "id_hash": "x"}}


@pytest.mark.asyncio
async def test_fanout_delivers_to_the_claiming_manager():
    """A single shared queue woke ONE waiter: with 2 folders each event went
    to a random manager and the owner never saw it."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a", {"a.gpkg"}), _ManagerFake("/b", {"b.gpkg"})]
    queues = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _run_fanout(entrada, managers, queues, [_evento("b.gpkg"), _evento("a.gpkg")])

    assert queues[0].qsize() == 1 and queues[1].qsize() == 1
    assert queues[0].get_nowait()["file"]["original_name"] == "a.gpkg"
    assert queues[1].get_nowait()["file"]["original_name"] == "b.gpkg"


@pytest.mark.asyncio
async def test_fanout_sends_orphan_to_the_primary():
    """A new file is in no manifest at all — it goes to the first manager."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a"), _ManagerFake("/b")]
    queues = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _run_fanout(entrada, managers, queues, [_evento("novo.gpkg")])

    assert queues[0].qsize() == 1
    assert queues[1].qsize() == 0


@pytest.mark.asyncio
async def test_fanout_tolerates_manager_without_claims_event():
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerWithoutContract("/a"), _ManagerFake("/b", {"b.gpkg"})]
    queues = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _run_fanout(entrada, managers, queues, [_evento("b.gpkg"), _evento("?.gpkg")])

    assert queues[1].qsize() == 1   # reivindicado
    assert queues[0].qsize() == 1   # orphan falls to the primary


@pytest.mark.asyncio
async def test_fanout_drops_with_log_when_target_queue_is_full(caplog):
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a")]
    queues = [asyncio.Queue(maxsize=1)]

    with caplog.at_level(logging.WARNING, logger="executor"):
        await _run_fanout(entrada, managers, queues, [_evento("1.gpkg"), _evento("2.gpkg")])

    assert queues[0].qsize() == 1
    assert any("cheia" in r.getMessage() for r in caplog.records)


# ── P5: waiting for node_events without a global 30s barrier ─────────────────

def _event_queue(n: int = 0):
    from executor.main import _CountedQueue

    fila = _CountedQueue()
    for i in range(n):
        fila.put_nowait({"node": f"n{i}"})
    return fila


async def _sender_fake(fila, intervalo: float, enviados: list | None = None):
    """Consumer with the SAME contract as _event_sender_loop.

    There are THREE steps, and the distinction matters: `task_done()` is unconditional
    (it settles the join balance even when the item goes back to the queue), while
    `confirmar_envio()` only happens when `ws.send` has returned — that is what the
    end-of-job barrier watches.
    """
    while True:
        ev = await fila.get()
        await asyncio.sleep(intervalo)
        fila.confirmar_envio(ev)
        fila.task_done()
        if enviados is not None:
            enviados.append(ev)


@pytest.mark.asyncio
async def test_drain_gives_up_fast_when_nobody_drains():
    """With the WS down the job paid the full 30s while HOLDING the semaphore slot."""
    from executor.main import _drain_pending_events

    fila = _event_queue(5)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await _drain_pending_events(fila, timeout=30.0, stall_timeout=0.3)
    decorrido = loop.time() - inicio

    assert decorrido < 2.0, "nao pode esperar o timeout cheio sem ninguem drenando"
    assert fila.qsize() == 5


@pytest.mark.asyncio
async def test_drain_waits_while_there_is_progress():
    """Sender vivo: a espera continua ate os eventos deste job serem enviados."""
    from executor.main import _drain_pending_events

    fila = _event_queue(6)

    sender = asyncio.create_task(_sender_fake(fila, 0.1))
    try:
        await _drain_pending_events(fila, timeout=10.0, stall_timeout=0.3)
        assert fila.confirmados == 6
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_drain_does_not_give_up_with_producer_faster_than_sender():
    """The bug the qsize heuristic introduced.

    Shared queue: job B keeps producing node_events faster than the network
    delivers them, so qsize NEVER decreases — the previous version read that
    as "no connection", gave up after 3s and dispatched A's job_result with A's
    final events still unsent (the UI closed the run with the graph
    frozen). Here the sender is alive and making progress: the barrier must wait.
    """
    from executor.main import _drain_pending_events

    fila = _event_queue(0)
    enviados: list[dict] = []
    # A backlog big enough that, within the `stall_timeout` window, the sender does not
    # even get close to A's events — and the premature cutoff really hurts.
    for i in range(40):
        fila.put_nowait({"node": f"backlog-{i}"})
    # The last two events belong to the job that just finished: they are at the END
    # of the FIFO, right behind the other job's backlog.
    fila.put_nowait({"node": "A-node-final"})
    fila.put_nowait({"node": "A-workflow-complete"})

    async def _producer():
        # Faster than the sender: qsize only grows.
        while True:
            await asyncio.sleep(0.02)
            fila.put_nowait({"node": "B-ruido"})

    sender = asyncio.create_task(_sender_fake(fila, 0.03, enviados))
    produtor = asyncio.create_task(_producer())
    try:
        await _drain_pending_events(fila, timeout=10.0, stall_timeout=0.3)
        nomes = [e["node"] for e in enviados]
        assert "A-node-final" in nomes and "A-workflow-complete" in nomes, (
            "o resultado nao pode ser despachado antes dos eventos do proprio job"
        )
        assert fila.qsize() > 0, "o cenario so vale se o produtor alheio esta a frente"
    finally:
        for t in (sender, produtor):
            t.cancel()
        await asyncio.gather(sender, produtor, return_exceptions=True)


@pytest.mark.asyncio
async def test_drain_does_not_wait_for_events_of_other_jobs():
    """The barrier is by watermark: it only covers what was already in the queue.

    The global `join()` made job A also wait for the events that job B
    enqueued AFTERWARDS — with B producing nonstop, the wait never ended.
    """
    from executor.main import _drain_pending_events

    fila = _event_queue(3)

    async def _producer():
        while True:
            await asyncio.sleep(0.01)
            fila.put_nowait({"node": "B-depois"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0))
    produtor = asyncio.create_task(_producer())
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    try:
        await _drain_pending_events(fila, timeout=10.0, stall_timeout=0.5)
        assert loop.time() - inicio < 2.0, "nao pode esperar producao de outros jobs"
    finally:
        for t in (sender, produtor):
            t.cancel()
        await asyncio.gather(sender, produtor, return_exceptions=True)


@pytest.mark.asyncio
async def test_drain_covers_events_published_via_call_soon_threadsafe():
    """ExecutorEventPublisher enqueues via a loop callback, not immediately.

    Without the initial yield the watermark was taken before the job's last
    events entered the queue — the barrier 'passed' without covering anything.
    """
    from executor.main import _drain_pending_events

    fila = _event_queue(0)
    enviados: list[dict] = []
    loop = asyncio.get_running_loop()
    loop.call_soon(fila.put_nowait, {"node": "A-node-final"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0, enviados))
    try:
        await _drain_pending_events(fila, timeout=5.0, stall_timeout=0.3)
        assert [e["node"] for e in enviados] == ["A-node-final"]
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_await_confirmation_gives_up_without_consumer_on_shutdown():
    """Shutdown guard: a `conn_task` alive in backoff is not a live sender.

    Before, shutdown paid a guaranteed 30s of `wait_for(join(), 30)` whenever the
    connection was in reconnection backoff (task alive, no sender).
    """
    from executor.main import _await_confirmation

    fila = _event_queue(3)
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    ok = await _await_confirmation(fila, rotulo="resultado", timeout=30, stall_timeout=0.4)
    assert ok is False
    assert loop.time() - inicio < 2.0


# ── D1: observed background task ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_background_task_with_exception_is_logged(caplog):
    """Um FileNotFoundError trivial matava o GeoSync em silencio."""
    from executor.main import _watch_task

    async def _explode():
        raise FileNotFoundError("pasta sumiu")

    task = asyncio.create_task(_explode(), name="geosync-teste")
    _watch_task(task)
    with caplog.at_level(logging.ERROR, logger="executor"):
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)   # deixa o done_callback rodar

    assert any("geosync-teste" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_cancelled_task_does_not_become_error():
    from executor.main import _watch_task

    async def _sleep_forever():
        await asyncio.sleep(30)

    task = asyncio.create_task(_sleep_forever(), name="geosync-cancelada")
    _watch_task(task)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    # Not raising anything is the contract: the callback returns early on cancellation.


# ── Immediate drain notice ───────────────────────────────────────────────────
# `get_capacity()` starts advertising saturation as soon as `_shutting_down` becomes
# True, but what SENDS it is `_capacity_loop`, which sleeps 10s BEFORE each send.
# In that window the server's `_resolve_candidates` still picked this executor
# as least-loaded and the job came back as "Executor em shutdown." — run FAILED
# without failover, the very problem the saturation notice exists to avoid.


@pytest.mark.asyncio
async def test_shutdown_announces_drain_before_any_wait():
    """The order is the point: notifying AFTER draining/waiting would not close the window.

    There must be a QUEUED job for the order to be observable — `_drain_queued`
    only produces a visible effect (`on_cancelled`) if it has something to drain. Without
    it both orders produce the same list and the test passes either way.
    """
    ordem: list[str] = []

    async def _execute(_msg):
        await asyncio.sleep(60)  # never completes; the job stays stuck in the queue

    async def _cancelado(_msg, reason=None):
        ordem.append("drenou-fila")

    fila = ExecutorJobQueue(
        on_execute=_execute, max_concurrent=1, max_queue_size=4,
        on_cancelled=_cancelado,
    )

    async def _notify():
        ordem.append("avisou-drenagem")

    fila.set_on_draining(_notify)
    # No start(): no worker consumes, so the job stays in the queue until the drain.
    assert await fila.enqueue(_job("preso"))
    await fila.shutdown(timeout=1)

    assert "drenou-fila" in ordem, "o job enfileirado precisa ter sido drenado"
    assert ordem[0] == "avisou-drenagem", (
        "o aviso precisa sair na PRIMEIRA coisa do shutdown; qualquer trabalho "
        f"antes dele reabre a janela de dispatch. Ordem observada: {ordem}"
    )


@pytest.mark.asyncio
async def test_drain_notice_carries_saturated_capacity():
    """Notifying right away is useless if the advertised number does not take the
    executor off the top of the least-loaded ranking."""
    capturado: dict = {}

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=2, max_queue_size=5)

    async def _notify():
        capturado.update(fila.get_capacity())

    fila.set_on_draining(_notify)
    await fila.start()
    await fila.shutdown(timeout=1)

    # is_full() do servidor: queued + running >= max_concurrent + max_queue
    soma = capturado["queued"] + capturado["running"]
    assert soma >= capturado["max_concurrent"] + capturado["max_queue"], (
        f"capacidade anunciada ({soma}) nao satura o is_full() do servidor"
    )


@pytest.mark.asyncio
async def test_notice_failure_does_not_block_shutdown():
    """The notice is best-effort: if the WS has already dropped, shutting down must still work."""
    async def _explode():
        raise RuntimeError("WS ja fechado")

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=1, max_queue_size=2)
    fila.set_on_draining(_explode)
    await fila.start()
    await fila.shutdown(timeout=1)  # must not raise
