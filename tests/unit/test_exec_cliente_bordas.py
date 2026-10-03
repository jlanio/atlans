# tests/unit/test_exec_cliente_bordas.py
"""Executor-client edges exposed by the audit of the optimization batch.

Each test pins down an invariant that the corresponding optimization broke
without any test noticing:

  A2  — the reconnect backoff may only back off because of a SESSION that
        existed. Measuring the whole attempt, a WS upgrade hung for 10s counted
        as a "session that made progress", the delay was halved, the caller
        doubled it and the executor redid the mTLS handshake every ~1s for hours.
  A18/A26 — the stdout batch has to fit in the frame: no `extra['message']`
        duplicating the text, and closing by BYTES before closing by count.
        Above 64 KB the event is reduced to the control fields (no `extra`)
        and the panel silently loses the whole batch.
  A19 — the end-of-job barrier measures "how much is left" per RUN, but "is
        there a consumer?" across the WHOLE queue. With the per-run detector, a
        short job behind a large job's backlog reported a dead sender with the
        WS alive.
  A20 — validation/decryption must not share a pool with the nodes, and
        capacity has to be honest when the nodes' pool saturates.
  A44 — lifecycle discarded due to PRESSURE (WS alive) must be resent as soon
        as the queue has room; and `esquecer_run` has to clear the collector too.
  A59 — every re-enqueue and every final discard settles the high-water mark
        account. Without it `alvo` was unreachable and the barrier charged the
        whole stall timeout on every job with one send failure.
"""
import asyncio
import json

import pytest

from executor import connection as conn_mod
from executor.connection import ExecutorConnection, _dumps_event
from executor.event_publisher import ColetorDeLifecycle
from executor.main import _FilaContada, _drenar_eventos_pendentes
from flow.utils.publisher.reducao import TETO_NODE_EVENT_BYTES


# ── A2: backoff mede a SESSAO, nao a tentativa ────────────────────────────────

def _conn():
    return ExecutorConnection(job_queue=None, result_queue=asyncio.Queue())


def test_backoff_nao_recua_quando_o_handshake_nunca_abriu(monkeypatch):
    """Hung upgrade: `_sessao_iniciada_em` stays None and the delay is kept.

    It was the critical scenario: a 10s `open_timeout` counted as a 10s session,
    fell into the middle band and the exponential backoff ceased to exist
    precisely for the failure that is most expensive for the server.
    """
    c = _conn()
    c._sessao_iniciada_em = None
    assert c._apply_session_backoff_reset(8) == 8


def test_backoff_recua_de_verdade_apos_sessao_media(monkeypatch):
    """Middle band: it has to survive the doubling that `run()` applies afterwards.

    With /2 the net effect was exactly neutral (halve-then-double) and the delay
    oscillated between two values forever.
    """
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 10.0)
    c._sessao_iniciada_em = agora
    recuado = c._apply_session_backoff_reset(8)
    # O caller faz `min(delay * 2, MAX)` logo em seguida.
    assert recuado * 2 < 8


def test_backoff_zera_apos_sessao_saudavel(monkeypatch):
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 120.0)
    c._sessao_iniciada_em = agora
    assert c._apply_session_backoff_reset(15) == 1


def test_backoff_mantem_acumulado_em_sessao_que_morre_no_nascimento(monkeypatch):
    c = _conn()
    agora = conn_mod.time.monotonic()
    monkeypatch.setattr(conn_mod.time, "monotonic", lambda: agora + 1.0)
    c._sessao_iniciada_em = agora
    assert c._apply_session_backoff_reset(4) == 4


# ── A18/A26: the stdout batch fits in the frame ───────────────────────────────

def _stream(publicados):
    from flow.nodes.action.python_script import _LoggingStream

    return _LoggingStream(log_fn=lambda _l: None, publish_fn=publicados.append)


def test_lote_de_stdout_fecha_por_bytes_antes_do_teto_do_frame():
    """200 long lines must not become an event above 64 KB.

    The user's `for r in gdf.itertuples(): print(r)`: lines of ~200 chars.
    Before, the batch only closed at 200 lines and, with the text duplicated in
    `message`, the event went past 64 KB and reached the panel without `extra`.
    """
    from flow.nodes.action.python_script import _STDOUT_FLUSH_LINES

    publicados = []
    stream = _stream(publicados)
    linha = "x" * 200
    for _ in range(_STDOUT_FLUSH_LINES * 3):
        stream.write(linha + "\n")
    stream.flush()

    assert publicados, "nada foi publicado"
    for lote in publicados:
        evento = {"type": "node_event", "run_id": "r", "node": "n",
                  "kind": "stdout", "status": "log", "extra": {"lines": lote}}
        assert len(_dumps_event(evento)) <= TETO_NODE_EVENT_BYTES, (
            "lote serializado estourou o teto — o servidor descartaria as linhas"
        )


def test_linha_unica_gigante_e_truncada_com_marcacao():
    """A 70 KB `print(gdf.to_json())` must not take the other lines down with it."""
    publicados = []
    stream = _stream(publicados)
    stream.write("a" * 70_000 + "\n")
    stream.write("linha legitima\n")
    stream.flush()

    todas = [linha for lote in publicados for linha in lote]
    assert "linha legitima" in todas, "a linha boa foi perdida junto com a gigante"
    marcadas = [linha for linha in todas if "linha truncada" in linha]
    assert marcadas, "truncou em silencio — a saida pareceria completa"
    assert max(len(linha) for linha in todas) < 70_000


def test_reducao_de_evento_preserva_as_linhas_de_stdout():
    """Last safety net: if it still overflows, `extra['lines']` survives truncated.

    Clearing `extra` made the panel show kind=stdout with zero content — the
    node's output tab was empty, with no warning at all.
    """
    evento = {
        "type": "node_event", "run_id": "r", "node": "n",
        "kind": "stdout", "status": "log",
        "extra": {"lines": ["y" * 500 for _ in range(400)]},
    }
    bruto = _dumps_event(evento)
    reduzido = json.loads(bruto)
    assert reduzido.get("__truncated__") is True
    assert reduzido["extra"]["lines"], "as linhas foram jogadas fora"
    assert len(bruto) <= TETO_NODE_EVENT_BYTES


def test_reducao_respeita_o_teto_mesmo_com_linhas_nao_ascii():
    """Truncation by real serialization, not by character count.

    `json.dumps` escapes with ensure_ascii: a line of emoji grows up to 6x. An
    estimate based on `len(str)` would let the reduced event overflow the ceiling
    again, precisely in the branch that exists to save the content.
    """
    evento = {
        "type": "node_event", "run_id": "r", "node": "n",
        "kind": "stdout", "status": "log",
        "extra": {"lines": ["🛰️ção" * 200 for _ in range(300)]},
    }
    bruto = _dumps_event(evento)
    assert len(bruto) <= TETO_NODE_EVENT_BYTES
    assert json.loads(bruto)["extra"]["lines"]


# ── A19: stalling is a property of the QUEUE, not of the run ──────────────────

@pytest.mark.asyncio
async def test_barreira_nao_desiste_enquanto_o_sender_drena_outro_run():
    """Short job behind a large job's backlog in the shared FIFO queue.

    The per-run detector reported "consumer stopped (WS down)" with the
    WebSocket perfectly alive, and the `job_result` — which carries
    `__workflow_complete__` — was dispatched ahead of the run's node_events.
    """
    fila = _FilaContada()
    for i in range(40):
        fila.put_nowait({"run_id": "B", "node": f"b{i}"})
    for i in range(3):
        fila.put_nowait({"run_id": "A", "node": f"a{i}"})

    async def _sender():
        while True:
            ev = await fila.get()
            await asyncio.sleep(0.02)   # slow sender, but ALIVE
            fila.confirmar_envio(ev)
            fila.task_done()

    task = asyncio.create_task(_sender())
    try:
        # 0.3s of stalling against ~0.9s of B's backlog ahead of A.
        await asyncio.wait_for(
            _drenar_eventos_pendentes(fila, run_id="A", timeout=10.0, estagnado=0.3),
            timeout=5.0,
        )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert fila.confirmados_por_run.get("A") == 3, (
        "a barreira saiu antes dos eventos do proprio run subirem"
    )


@pytest.mark.asyncio
async def test_barreira_ainda_desiste_quando_ninguem_drena():
    """The original defense still holds: with no consumer, we don't wait 30s."""
    fila = _FilaContada()
    for i in range(3):
        fila.put_nowait({"run_id": "A", "node": f"a{i}"})

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    await _drenar_eventos_pendentes(fila, run_id="A", timeout=30.0, estagnado=0.3)
    assert loop.time() - inicio < 2.0


# ── A59: marca d'agua fecha em requeue e em descarte ──────────────────────────

@pytest.mark.asyncio
async def test_requeue_nao_desbalanceia_a_marca_dagua(monkeypatch):
    """A transient send failure must not cost the stall timeout.

    `_put` counts every put (including the re-enqueue) and `confirmar_envio` only
    counts success: without a counterweight, `alvo` stayed 1 above what was
    reachable forever and the barrier only exited by stalling.
    """
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)

    class _WSFalhaUmaVez:
        def __init__(self):
            self.enviadas = []
            self._falhou = False

        async def send(self, raw):
            if not self._falhou:
                self._falhou = True
                raise RuntimeError("WS em estado invalido")
            self.enviadas.append(raw)

    fila = _FilaContada(maxsize=500)
    c = ExecutorConnection(job_queue=None, result_queue=asyncio.Queue(), event_queue=fila)
    fila.put_nowait({"run_id": "A", "node": "n1", "status": "completed"})

    task = asyncio.create_task(c._event_sender_loop(_WSFalhaUmaVez()))
    try:
        await asyncio.wait_for(fila.join(), timeout=3.0)
        loop = asyncio.get_running_loop()
        inicio = loop.time()
        await _drenar_eventos_pendentes(fila, run_id="A", timeout=10.0, estagnado=3.0)
        # Se a conta estivesse desbalanceada, a barreira so sairia em ~3s.
        assert loop.time() - inicio < 1.0
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert fila.confirmados_por_run["A"] == fila.enfileirados_por_run["A"]


def test_descarte_definitivo_fecha_a_conta():
    """An event that will never be sent must not leave `alvo` unreachable."""
    fila = _FilaContada(maxsize=500)
    item = {"run_id": "A", "node": "n1"}
    fila.put_nowait(item)
    fila.resolver_sem_envio(item)
    assert fila.confirmados_por_run["A"] == fila.enfileirados_por_run["A"] == 1


# ── A44: coletor drenado com a sessao viva ────────────────────────────────────

def test_coletor_e_drenado_quando_a_fila_folga():
    """Lifecycle discarded due to PRESSURE must not wait for a reconnection.

    The queue fills up from production (a 300-node workflow in debug_mode) far
    more often than the session drops; draining only on reconnection left the
    nodes spinning until the end of the run and the events held in memory.
    """
    fila = _FilaContada(maxsize=10)
    c = ExecutorConnection(job_queue=None, result_queue=asyncio.Queue(), event_queue=fila)
    fila.coletor.registrar(
        {"run_id": "A", "node": "n1", "kind": "lifecycle", "status": "completed"}
    )

    # Fila cheia: nao devolve nada (senao o remedio realimenta o descarte).
    for i in range(10):
        fila.put_nowait({"run_id": "B", "node": f"b{i}"})
    c._ressincronizar_lifecycle(so_com_folga=True)
    assert len(fila.coletor) == 1

    # Fila folgou: devolve.
    for _ in range(10):
        fila.get_nowait()
    c._ressincronizar_lifecycle(so_com_folga=True)
    assert len(fila.coletor) == 0
    assert fila.qsize() == 1


def test_esquecer_run_limpa_o_coletor():
    """Without this, a late resend recreated the already purged per-run entries."""
    fila = _FilaContada()
    fila.coletor.registrar({"run_id": "A", "node": "n1", "kind": "lifecycle"})
    fila.coletor.registrar({"run_id": "B", "node": "n1", "kind": "lifecycle"})
    fila.esquecer_run("A")
    restantes = fila.coletor.drenar()
    assert [e["run_id"] for e in restantes] == ["B"]


def test_coletor_esquece_run_isoladamente():
    coletor = ColetorDeLifecycle()
    coletor.registrar({"run_id": "A", "node": "n1", "kind": "lifecycle"})
    coletor.registrar({"run_id": "A", "node": "n2", "kind": "lifecycle"})
    assert len(coletor) == 2
    coletor.esquecer_run("A")
    assert len(coletor) == 0


# ── A20: separate control-plane pool and honest capacity ──────────────────────

def test_validacao_nao_usa_o_pool_dos_nos():
    """An orphaned PythonScript thread must not stop the executor from accepting jobs.

    `asyncio.to_thread` falls into the loop's DEFAULT pool, which is where the
    nodes run — including the user's arbitrary script, which the node timeout
    cannot cancel. With validation there, 16 stuck threads made every new job
    hang before it was even accepted or rejected.
    """
    import inspect
    from executor import job_executor

    assert job_executor._CONTROL_POOL._max_workers <= 4
    codigo = inspect.getsource(job_executor.execute_job)
    assert "run_in_executor(\n            _CONTROL_POOL" in codigo or "_CONTROL_POOL" in codigo
    assert "asyncio.to_thread(_validar_e_descriptografar" not in codigo


class _PoolFalso:
    def __init__(self, workers, vivas, pendentes):
        self._max_workers = workers
        self._threads = set(range(vivas))

        class _Q:
            def qsize(_self):
                return pendentes

        self._work_queue = _Q()


class _FilaDeJobsFalsa:
    def get_capacity(self):
        return {"queued": 0, "running": 0, "max_concurrent": 4, "max_queue": 50}


def test_capacity_anuncia_saturacao_quando_o_pool_dos_nos_trava(monkeypatch):
    """Stuck threads do not show up in queued/running, which count JOBS.

    The executor kept announcing itself as idle with the whole pipeline stopped
    and the server kept dispatching jobs that died hanging in 'running'.
    """
    monkeypatch.setattr(conn_mod, "_get_dynamic_metrics", lambda: {})
    c = ExecutorConnection(
        job_queue=_FilaDeJobsFalsa(), result_queue=asyncio.Queue(),
        thread_pool=_PoolFalso(workers=16, vivas=16, pendentes=5),
    )
    # The first sample is not enough — a dispatch spike saturates for a moment.
    assert c._montar_capacity()["queued"] == 0
    cap = c._montar_capacity()
    assert cap["queued"] >= cap["max_queue"] + cap["max_concurrent"]


def test_capacity_normal_quando_o_pool_tem_folga(monkeypatch):
    monkeypatch.setattr(conn_mod, "_get_dynamic_metrics", lambda: {})
    c = ExecutorConnection(
        job_queue=_FilaDeJobsFalsa(), result_queue=asyncio.Queue(),
        thread_pool=_PoolFalso(workers=16, vivas=16, pendentes=0),
    )
    for _ in range(5):
        assert c._montar_capacity()["queued"] == 0
