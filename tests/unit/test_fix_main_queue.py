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
async def test_shutdown_avisa_jobs_que_ficaram_na_fila():
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
    # see test_capacity_anuncia_saturacao_durante_o_shutdown.)
    assert queue._queue.qsize() == 0


@pytest.mark.asyncio
async def test_shutdown_nao_espera_polling_quando_nao_ha_job():
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
async def test_capacity_anuncia_saturacao_durante_o_shutdown():
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
async def test_cancel_de_job_desconhecido_retorna_unknown_sem_vazar():
    async def on_execute(message):
        return None

    queue = ExecutorJobQueue(on_execute=on_execute, max_concurrent=1, max_queue_size=10)

    assert queue.cancel("nunca-visto") == "unknown"
    assert queue._cancelled == set(), "id desconhecido nao pode ficar marcado para sempre"


@pytest.mark.asyncio
async def test_cancel_de_job_enfileirado_continua_queued():
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

def test_env_int_rejeita_zero_e_lixo(monkeypatch, caplog):
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


def test_config_expoe_valores_saneados():
    from executor import config

    assert config.MAX_CONCURRENT >= 1
    assert config.MAX_QUEUE_SIZE >= 1
    assert config.JOB_TIMEOUT >= 1


def test_assert_configured_reclama_sem_executor_id(monkeypatch):
    """The requirement lives here, not in the import of config.py, which no longer aborts."""
    from executor import config

    monkeypatch.setattr(config, "EXECUTOR_ID", "")
    with pytest.raises(SystemExit):
        config.assert_configured()


# ── B8: fan-out dos drive_events ─────────────────────────────────────────────

class _ManagerFake:
    def __init__(self, sync_dir: str, reivindica: set[str] | None = None):
        self.sync_dir = sync_dir
        self._reivindica = reivindica or set()

    def claims_event(self, msg: dict) -> bool:
        return msg.get("file", {}).get("original_name", "") in self._reivindica


class _ManagerSemContrato:
    """A manager that has not implemented claims_event yet — must not break the fan-out."""
    def __init__(self, sync_dir: str):
        self.sync_dir = sync_dir


async def _rodar_fanout(entrada, managers, filas, eventos):
    from executor.main import _drive_event_fanout

    task = asyncio.create_task(_drive_event_fanout(entrada, managers, filas))
    for ev in eventos:
        entrada.put_nowait(ev)
    await asyncio.wait_for(entrada.join(), timeout=2.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def _evento(nome: str) -> dict:
    return {"action": "file_created", "file": {"original_name": nome, "id_hash": "x"}}


@pytest.mark.asyncio
async def test_fanout_entrega_ao_manager_que_reivindica():
    """A single shared queue woke ONE waiter: with 2 folders each event went
    to a random manager and the owner never saw it."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a", {"a.gpkg"}), _ManagerFake("/b", {"b.gpkg"})]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("b.gpkg"), _evento("a.gpkg")])

    assert filas[0].qsize() == 1 and filas[1].qsize() == 1
    assert filas[0].get_nowait()["file"]["original_name"] == "a.gpkg"
    assert filas[1].get_nowait()["file"]["original_name"] == "b.gpkg"


@pytest.mark.asyncio
async def test_fanout_manda_orfao_para_o_primario():
    """A new file is in no manifest at all — it goes to the first manager."""
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a"), _ManagerFake("/b")]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("novo.gpkg")])

    assert filas[0].qsize() == 1
    assert filas[1].qsize() == 0


@pytest.mark.asyncio
async def test_fanout_tolera_manager_sem_claims_event():
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerSemContrato("/a"), _ManagerFake("/b", {"b.gpkg"})]
    filas = [asyncio.Queue(maxsize=10), asyncio.Queue(maxsize=10)]

    await _rodar_fanout(entrada, managers, filas, [_evento("b.gpkg"), _evento("?.gpkg")])

    assert filas[1].qsize() == 1   # reivindicado
    assert filas[0].qsize() == 1   # orphan falls to the primary


@pytest.mark.asyncio
async def test_fanout_descarta_com_log_quando_fila_do_destino_enche(caplog):
    entrada: asyncio.Queue = asyncio.Queue()
    managers = [_ManagerFake("/a")]
    filas = [asyncio.Queue(maxsize=1)]

    with caplog.at_level(logging.WARNING, logger="executor"):
        await _rodar_fanout(entrada, managers, filas, [_evento("1.gpkg"), _evento("2.gpkg")])

    assert filas[0].qsize() == 1
    assert any("cheia" in r.getMessage() for r in caplog.records)


# ── P5: waiting for node_events without a global 30s barrier ─────────────────

def _fila_eventos(n: int = 0):
    from executor.main import _FilaContada

    fila = _FilaContada()
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
async def test_drenagem_desiste_rapido_quando_ninguem_drena():
    """With the WS down the job paid the full 30s while HOLDING the semaphore slot."""
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(5)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await _drenar_eventos_pendentes(fila, timeout=30.0, estagnado=0.3)
    decorrido = loop.time() - inicio

    assert decorrido < 2.0, "nao pode esperar o timeout cheio sem ninguem drenando"
    assert fila.qsize() == 5


@pytest.mark.asyncio
async def test_drenagem_espera_enquanto_ha_progresso():
    """Sender vivo: a espera continua ate os eventos deste job serem enviados."""
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(6)

    sender = asyncio.create_task(_sender_fake(fila, 0.1))
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.3)
        assert fila.confirmados == 6
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_drenagem_nao_desiste_com_produtor_mais_rapido_que_o_sender():
    """The bug the qsize heuristic introduced.

    Shared queue: job B keeps producing node_events faster than the network
    delivers them, so qsize NEVER decreases — the previous version read that
    as "no connection", gave up after 3s and dispatched A's job_result with A's
    final events still unsent (the UI closed the run with the graph
    frozen). Here the sender is alive and making progress: the barrier must wait.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(0)
    enviados: list[dict] = []
    # A backlog big enough that, within the `estagnado` window, the sender does not
    # even get close to A's events — and the premature cutoff really hurts.
    for i in range(40):
        fila.put_nowait({"node": f"backlog-{i}"})
    # The last two events belong to the job that just finished: they are at the END
    # of the FIFO, right behind the other job's backlog.
    fila.put_nowait({"node": "A-node-final"})
    fila.put_nowait({"node": "A-workflow-complete"})

    async def _produtor():
        # Faster than the sender: qsize only grows.
        while True:
            await asyncio.sleep(0.02)
            fila.put_nowait({"node": "B-ruido"})

    sender = asyncio.create_task(_sender_fake(fila, 0.03, enviados))
    produtor = asyncio.create_task(_produtor())
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.3)
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
async def test_drenagem_nao_espera_eventos_de_outros_jobs():
    """The barrier is by watermark: it only covers what was already in the queue.

    The global `join()` made job A also wait for the events that job B
    enqueued AFTERWARDS — with B producing nonstop, the wait never ended.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(3)

    async def _produtor():
        while True:
            await asyncio.sleep(0.01)
            fila.put_nowait({"node": "B-depois"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0))
    produtor = asyncio.create_task(_produtor())
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    try:
        await _drenar_eventos_pendentes(fila, timeout=10.0, estagnado=0.5)
        assert loop.time() - inicio < 2.0, "nao pode esperar producao de outros jobs"
    finally:
        for t in (sender, produtor):
            t.cancel()
        await asyncio.gather(sender, produtor, return_exceptions=True)


@pytest.mark.asyncio
async def test_drenagem_cobre_eventos_publicados_via_call_soon_threadsafe():
    """ExecutorEventPublisher enqueues via a loop callback, not immediately.

    Without the initial yield the watermark was taken before the job's last
    events entered the queue — the barrier 'passed' without covering anything.
    """
    from executor.main import _drenar_eventos_pendentes

    fila = _fila_eventos(0)
    enviados: list[dict] = []
    loop = asyncio.get_running_loop()
    loop.call_soon(fila.put_nowait, {"node": "A-node-final"})

    sender = asyncio.create_task(_sender_fake(fila, 0.0, enviados))
    try:
        await _drenar_eventos_pendentes(fila, timeout=5.0, estagnado=0.3)
        assert [e["node"] for e in enviados] == ["A-node-final"]
    finally:
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


@pytest.mark.asyncio
async def test_aguardar_confirmacao_desiste_sem_consumidor_no_shutdown():
    """Shutdown guard: a `conn_task` alive in backoff is not a live sender.

    Before, shutdown paid a guaranteed 30s of `wait_for(join(), 30)` whenever the
    connection was in reconnection backoff (task alive, no sender).
    """
    from executor.main import _aguardar_confirmacao

    fila = _fila_eventos(3)
    loop = asyncio.get_running_loop()
    inicio = loop.time()
    ok = await _aguardar_confirmacao(fila, rotulo="resultado", timeout=30, estagnado=0.4)
    assert ok is False
    assert loop.time() - inicio < 2.0


# ── D1: observed background task ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_de_background_com_excecao_e_logada(caplog):
    """Um FileNotFoundError trivial matava o GeoSync em silencio."""
    from executor.main import _observar_task

    async def _explode():
        raise FileNotFoundError("pasta sumiu")

    task = asyncio.create_task(_explode(), name="geosync-teste")
    _observar_task(task)
    with caplog.at_level(logging.ERROR, logger="executor"):
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)   # deixa o done_callback rodar

    assert any("geosync-teste" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_task_cancelada_nao_vira_erro():
    from executor.main import _observar_task

    async def _dorme():
        await asyncio.sleep(30)

    task = asyncio.create_task(_dorme(), name="geosync-cancelada")
    _observar_task(task)
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
async def test_shutdown_avisa_drenagem_antes_de_qualquer_espera():
    """The order is the point: notifying AFTER draining/waiting would not close the window.

    There must be a QUEUED job for the order to be observable — `_drain_queued`
    only produces a visible effect (`on_cancelled`) if it has something to drain. Without
    it both orders produce the same list and the test passes either way.
    """
    ordem: list[str] = []

    async def _executa(_msg):
        await asyncio.sleep(60)  # never completes; the job stays stuck in the queue

    async def _cancelado(_msg, reason=None):
        ordem.append("drenou-fila")

    fila = ExecutorJobQueue(
        on_execute=_executa, max_concurrent=1, max_queue_size=4,
        on_cancelled=_cancelado,
    )

    async def _avisa():
        ordem.append("avisou-drenagem")

    fila.set_on_draining(_avisa)
    # No start(): no worker consumes, so the job stays in the queue until the drain.
    assert await fila.enqueue(_job("preso"))
    await fila.shutdown(timeout=1)

    assert "drenou-fila" in ordem, "o job enfileirado precisa ter sido drenado"
    assert ordem[0] == "avisou-drenagem", (
        "o aviso precisa sair na PRIMEIRA coisa do shutdown; qualquer trabalho "
        f"antes dele reabre a janela de dispatch. Ordem observada: {ordem}"
    )


@pytest.mark.asyncio
async def test_aviso_de_drenagem_carrega_capacidade_saturada():
    """Notifying right away is useless if the advertised number does not take the
    executor off the top of the least-loaded ranking."""
    capturado: dict = {}

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=2, max_queue_size=5)

    async def _avisa():
        capturado.update(fila.get_capacity())

    fila.set_on_draining(_avisa)
    await fila.start()
    await fila.shutdown(timeout=1)

    # is_full() do servidor: queued + running >= max_concurrent + max_queue
    soma = capturado["queued"] + capturado["running"]
    assert soma >= capturado["max_concurrent"] + capturado["max_queue"], (
        f"capacidade anunciada ({soma}) nao satura o is_full() do servidor"
    )


@pytest.mark.asyncio
async def test_falha_no_aviso_nao_impede_o_shutdown():
    """The notice is best-effort: if the WS has already dropped, shutting down must still work."""
    async def _explode():
        raise RuntimeError("WS ja fechado")

    fila = ExecutorJobQueue(on_execute=lambda _m: None, max_concurrent=1, max_queue_size=2)
    fila.set_on_draining(_explode)
    await fila.start()
    await fila.shutdown(timeout=1)  # must not raise
