# tests/unit/test_fix_connection.py
"""Regressions for the executor's send loops and reconnect backoff.

Bugs covered:
  B3 — task_done() was only called when the item was NOT re-enqueued. Every
       send failure shifted _unfinished_tasks by +1 permanently and the
       `_event_queue.join()` in main.py (on_execute) never resolved again: every
       following job paid a 30s timeout ("Timeout ao drenar fila de eventos
       — 0 evento(s) pendente(s)"). Aggravating factors: `await put()` on a full
       queue whose only consumer is the loop itself = deadlock; raw json.dumps
       on node_event; no cap on attempts.
  B4 — a post-handshake exception was swallowed (logger.debug) and the "clean"
       return of _connect_and_run reset the backoff, reconnecting without sleep.
  P2 — the 'output' filter in result_sender_loop became dead code (the discard
       happens at the source, in main.py on_execute).

Second round (adversarial review of our own fixes):
  R1 — the result loop was left WITHOUT an attempt cap (asymmetric with the
       events one): a result that fails deterministically spun forever and
       froze the shutdown's `_result_queue.join()`.
  R2 — cancellation during `ws.send` lost the item: CancelledError is not an
       Exception, fell into no handler, and the `finally` had already called
       task_done() — join() considered the queue drained with the item never sent.
  R3 — `_safe_dumps` (truncation modeled for job_result) reused on
       node_event: it reduced nothing, injected a nonexistent 'stats' key and
       logged "job_result descartado" (discarded) for something that was not a
       job_result.
  R4 — `asyncio.wait` does not cancel what it awaits: canceling conn_task left
       the 5 child loops alive after the shutdown gather.
  R5 — a terminal close (4401/4403/4404) got lost when an auxiliary loop
       finished (cleanly, via `break`) before _receive_loop.

The B4/R5 tests run the REAL `_connect_and_run` with a fake `websockets.connect`.
Monkeypatching `_connect_and_run` — as the first version did — nullifies exactly
the code under test: the "propagation" test only proved that an exception raised
by the test itself reached the classifier.
"""
import asyncio
import json

import pytest
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from executor import connection as conn_mod
from executor.connection import ExecutorConnection
from flow.utils.publisher.reducao import TETO_NODE_EVENT_BYTES


def _closed(code=1006, reason=""):
    return ConnectionClosedError(Close(code, reason), None)


class _WS:
    """WebSocket falso: grava envios ou levanta a excecao configurada."""

    def __init__(self, raise_exc=None, raise_times=None, send_delay=0.0):
        self.enviadas = []
        self._raise_exc = raise_exc
        self._restantes = raise_times  # None = always
        self._send_delay = send_delay

    async def send(self, raw):
        if self._send_delay:
            await asyncio.sleep(self._send_delay)
        if self._raise_exc is not None and (self._restantes is None or self._restantes > 0):
            if self._restantes is not None:
                self._restantes -= 1
            raise self._raise_exc
        self.enviadas.append(raw)


class _SessionWS:
    """A fake WS complete enough to run the REAL `_connect_and_run`.

    It must be iterable (`async for raw in ws` in _receive_loop) and expose
    `close_code`/`close_reason` — which are the source of truth consulted when
    no task in `done` carried the close exception.
    """

    def __init__(self, *, send_exc=None, send_exc_after=1, send_delay=0.0,
                 recv_exc=None, recv_delay=0.0, close_code=None, close_reason=""):
        self.enviadas = []
        self.fechado = False
        self.close_code = close_code
        self.close_reason = close_reason
        # The handshake is the first send: letting it through is mandatory, otherwise
        # the exception would be raised outside asyncio.wait and the test would
        # pass via the wrong path.
        self._send_exc = send_exc
        self._send_restantes_ok = send_exc_after
        self._send_delay = send_delay
        self._recv_exc = recv_exc
        self._recv_delay = recv_delay

    async def send(self, raw):
        if self._send_delay:
            await asyncio.sleep(self._send_delay)
        if self._send_exc is not None:
            if self._send_restantes_ok > 0:
                self._send_restantes_ok -= 1
            else:
                raise self._send_exc
        self.enviadas.append(raw)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._recv_delay:
            await asyncio.sleep(self._recv_delay)
        if self._recv_exc is not None:
            raise self._recv_exc
        # No messages: sleeps until canceled (simulates an idle session).
        await asyncio.sleep(3600)
        raise StopAsyncIteration


class _FakeConnect:
    """Substitui `websockets.connect`: async CM que devolve o WS falso."""

    def __init__(self, ws):
        self._ws = ws

    async def __aenter__(self):
        return self._ws

    async def __aexit__(self, *_exc):
        self._ws.fechado = True
        return False


def _patch_connect(monkeypatch, ws):
    # ws:// local => is_local_server True => nao tenta montar contexto mTLS.
    monkeypatch.setattr(conn_mod.config, "SERVER_URL", "ws://localhost:8000")
    monkeypatch.setattr(conn_mod.websockets, "connect", lambda *a, **k: _FakeConnect(ws))


def _conn(results=None, events=None):
    return ExecutorConnection(
        job_queue=None,
        result_queue=results if results is not None else asyncio.Queue(),
        event_queue=events,
    )


async def _rodar(coro_fn, timeout=3.0):
    """Runs a sender_loop in a task and cancels it when it goes idle."""
    task = asyncio.create_task(coro_fn)
    await asyncio.sleep(0)
    return task


# ── B3: the task_done balance closes on ALL paths ────────────────────────────

@pytest.mark.asyncio
async def test_event_join_resolve_apos_falha_de_envio(monkeypatch):
    """The case that froze the executor: a generic failure sending a node_event.

    Before: put() without task_done => _unfinished_tasks never returned to zero
    and on_execute's join() hit 30s on every subsequent job.
    """
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    # Fails on the first 2 attempts, sends on the third.
    ws = _WS(raise_exc=RuntimeError("WS em estado invalido"), raise_times=2)

    await events.put({"node": "n1", "status": "running"})
    task = await _rodar(c._event_sender_loop(ws))

    await asyncio.wait_for(events.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert events._unfinished_tasks == 0
    assert len(ws.enviadas) == 1


@pytest.mark.asyncio
async def test_event_descartado_apos_teto_de_tentativas(monkeypatch):
    """A deterministic error (impossible payload) must not recycle forever."""
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    ws = _WS(raise_exc=RuntimeError("sempre falha"))

    await events.put({"node": "n1", "status": "error"})
    task = await _rodar(c._event_sender_loop(ws))

    await asyncio.wait_for(events.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert events.qsize() == 0, "evento imortal ficou na fila"
    assert events._unfinished_tasks == 0


@pytest.mark.asyncio
async def test_contador_de_tentativas_nunca_vai_no_payload(monkeypatch):
    """The internal retry key must not leak into the node_event protocol."""
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    ws = _WS(raise_exc=RuntimeError("falha unica"), raise_times=1)

    await events.put({"node": "n1", "status": "ok"})
    task = await _rodar(c._event_sender_loop(ws))
    await asyncio.wait_for(events.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(ws.enviadas) == 1
    assert conn_mod._ATTEMPTS_KEY not in ws.enviadas[0]


@pytest.mark.asyncio
async def test_requeue_em_fila_cheia_nao_deadlocka():
    """`await put()` numa fila cheia travaria o unico consumidor dela."""
    events = asyncio.Queue(maxsize=1)
    c = _conn(events=events)
    await events.put({"node": "ocupa", "status": "running"})

    # Must not block: discards with a log.
    c._requeue_event({"node": "n2", "status": "running"}, 1)
    assert events.qsize() == 1


@pytest.mark.asyncio
async def test_connection_closed_no_event_loop_nao_faz_task_done_duplo():
    """Com o finally incondicional, o task_done explicito viraria duplo
    (ValueError: task_done() called too many times)."""
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    ws = _WS(raise_exc=_closed(1006))

    await events.put({"node": "n1", "status": "running"})
    await asyncio.wait_for(c._event_sender_loop(ws), timeout=3.0)

    # The event went back to the queue (will be resent after reconnection) and the
    # balance matches exactly 1 pending item — not 2.
    assert events.qsize() == 1
    assert events._unfinished_tasks == 1


@pytest.mark.asyncio
async def test_result_join_resolve_apos_falha_de_envio(monkeypatch):
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    from executor import result_store
    monkeypatch.setattr(result_store, "increment_attempts", lambda *_a: None)
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS(raise_exc=RuntimeError("falha transitoria"), raise_times=1)

    await results.put({"job_id": "j1", "run_id": "j1", "status": "success"})
    task = await _rodar(c._result_sender_loop(ws))

    await asyncio.wait_for(results.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert results._unfinished_tasks == 0
    assert len(ws.enviadas) == 1


@pytest.mark.asyncio
async def test_connection_closed_no_result_loop_nao_faz_task_done_duplo(monkeypatch):
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS(raise_exc=_closed(1006))

    await results.put({"job_id": "j1", "status": "success"})
    await asyncio.wait_for(c._result_sender_loop(ws), timeout=3.0)

    assert results.qsize() == 1
    assert results._unfinished_tasks == 1


# ── R1: the result loop also needs a cap ─────────────────────────────────────

@pytest.mark.asyncio
async def test_result_descartado_apos_teto_e_continua_no_outbox(monkeypatch):
    """An 'immortal' result held the only consumer and the shutdown's join().

    Real scenario: stats with a circular reference => json.dumps always raises.
    Without a cap, the item went back to the queue indefinitely (1 attempt/s) and
    `_result_queue.join()` in main.py paid the full 30s timeout on every deploy.
    With a cap, the queue drains — and the result is NOT considered sent
    (mark_sent never called), so the outbox resends it on the next start.
    """
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    from executor import result_store
    chamadas = {"mark_sent": 0, "increment": 0}
    monkeypatch.setattr(result_store, "mark_sent",
                        lambda *_a: chamadas.__setitem__("mark_sent", chamadas["mark_sent"] + 1))
    monkeypatch.setattr(result_store, "increment_attempts",
                        lambda *_a: chamadas.__setitem__("increment", chamadas["increment"] + 1))

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS(raise_exc=ValueError("Circular reference detected"))

    await results.put({"job_id": "j1", "run_id": "j1", "status": "success"})
    task = await _rodar(c._result_sender_loop(ws))

    await asyncio.wait_for(results.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert results.qsize() == 0, "resultado imortal ficou na fila"
    assert results._unfinished_tasks == 0
    assert chamadas["increment"] == conn_mod._MAX_RESULT_SEND_ATTEMPTS
    assert chamadas["mark_sent"] == 0, "resultado nunca enviado nao pode sair do outbox"


@pytest.mark.asyncio
async def test_contador_de_tentativas_do_result_nao_vai_no_payload(monkeypatch):
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    from executor import result_store
    monkeypatch.setattr(result_store, "increment_attempts", lambda *_a: None)
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS(raise_exc=RuntimeError("falha unica"), raise_times=1)

    await results.put({"job_id": "j1", "status": "success"})
    task = await _rodar(c._result_sender_loop(ws))
    await asyncio.wait_for(results.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(ws.enviadas) == 1
    assert conn_mod._ATTEMPTS_KEY not in ws.enviadas[0]


async def test_resultado_enviado_fica_lembrado_para_o_inventario(monkeypatch):
    """`mark_sent` deletes the outbox as soon as the send returns, but the server
    may not even have processed the result yet. Until then the inventory keeps
    saying the job finished here — otherwise the server would close the run as lost."""
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)
    monkeypatch.setattr(result_store, "job_ids_pendentes", lambda: [])

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS()

    await results.put({"job_id": "j1", "run_id": "j1", "status": "success"})
    task = await _rodar(c._result_sender_loop(ws))
    await asyncio.wait_for(results.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(ws.enviadas) == 1
    assert c._montar_inventario()["resultados"] == ["j1"]


# ── R2: cancellation during ws.send must not lose the item ───────────────────

@pytest.mark.asyncio
async def test_result_volta_para_a_fila_quando_cancelado_durante_o_send(monkeypatch):
    """`for task in pending: task.cancel()` runs on EVERY session drop.

    If the cancellation catches the loop inside `ws.send`, the result has
    already left the queue: without the CancelledError handler it vanished (the
    `finally` called task_done) and the shutdown's `join()` reported 'drenado'
    (drained) without any log.
    """
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS(send_delay=1.0)  # send lento: o cancel cai no meio dele

    await results.put({"job_id": "j1", "run_id": "j1", "status": "success"})
    task = asyncio.create_task(c._result_sender_loop(ws))
    await asyncio.sleep(0.05)  # deixa o loop entrar no ws.send
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert ws.enviadas == [], "o send nao chegou a completar"
    assert results.qsize() == 1, "resultado perdido no cancelamento"
    assert results._unfinished_tasks == 1, "join() daria a fila por drenada"


@pytest.mark.asyncio
async def test_event_volta_para_a_fila_quando_cancelado_durante_o_send():
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    ws = _WS(send_delay=1.0)

    await events.put({"node": "n1", "status": "running"})
    task = asyncio.create_task(c._event_sender_loop(ws))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert events.qsize() == 1
    assert events._unfinished_tasks == 1


# ── R3: node_event serialization has its OWN cap ─────────────────────────────

def test_dumps_event_reduz_evento_gigante_aos_campos_de_controle():
    """The job_result truncation (by 'stats') did not work for node_event.

    Reused, it returned a string LARGER than the input, injected a 'stats' key
    that node_event never had and logged 'job_result descartado' (discarded).
    """
    grande = "x" * (TETO_NODE_EVENT_BYTES + 5_000)
    evento = {
        "type": "node_event", "run_id": "r1", "node": "n1", "status": "log",
        "kind": "stdout", "level": "info", "timestamp": 1.0,
        "extra": {"message": grande},
    }

    raw = conn_mod._dumps_event(evento)

    assert len(raw) < TETO_NODE_EVENT_BYTES, "nao reduziu nada"
    payload = json.loads(raw)
    assert payload["type"] == "node_event"      # without this the server does not route
    assert payload["run_id"] == "r1"
    assert payload["node"] == "n1"
    assert payload["status"] == "log"
    assert payload["__truncated__"] is True
    assert payload["__original_size__"] > TETO_NODE_EVENT_BYTES
    assert "extra" not in payload, "o campo pesado tinha que sair"
    assert "stats" not in payload, "chave espuria do truncador de job_result"


def test_dumps_event_nao_mexe_em_evento_normal():
    evento = {"type": "node_event", "run_id": "r1", "node": "n1", "status": "completed",
              "extra": {"branch": "a"}}
    payload = json.loads(conn_mod._dumps_event(evento))
    assert payload == evento


def test_dumps_event_coage_campo_de_controle_nao_escalar():
    """A cap has to be a guarantee: a giant 'node' must not get through whole."""
    evento = {"type": "node_event", "run_id": "r1",
              "node": {"lixo": "y" * (TETO_NODE_EVENT_BYTES + 100)},
              "status": "log"}
    raw = conn_mod._dumps_event(evento)
    assert len(raw) < TETO_NODE_EVENT_BYTES


def test_dumps_result_preserva_chaves_de_controle_ao_truncar(monkeypatch):
    """Truncation by 'stats' is still alive — in the right place (job_result)."""
    monkeypatch.setattr(conn_mod, "_MAX_WS_PAYLOAD", 2_000)
    obj = {"type": "job_result", "job_id": "j1", "status": "success",
           "stats": {"__response__": {"ok": True}, "no1": "z" * 5_000}}

    payload = json.loads(conn_mod._dumps_result(obj))

    assert payload["stats"]["__response__"] == {"ok": True}
    assert payload["stats"]["__truncated__"] is True
    assert "no1" not in payload["stats"]


# ── P2: the result goes whole; main.py is the one that discards 'output' ─────

@pytest.mark.asyncio
async def test_result_enviado_sem_filtro_local(monkeypatch):
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    results = asyncio.Queue()
    c = _conn(results=results)
    ws = _WS()

    await results.put({"job_id": "j1", "run_id": "j1", "status": "success",
                       "stats": {"__response__": {"ok": True}}})
    task = await _rodar(c._result_sender_loop(ws))
    await asyncio.wait_for(results.join(), timeout=3.0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    payload = json.loads(ws.enviadas[0])
    assert payload["type"] == "job_result"
    assert payload["stats"]["__response__"] == {"ok": True}


# ── B4: backoff must not be reset by a short session ─────────────────────────

@pytest.mark.asyncio
async def test_retorno_limpo_ainda_dorme_antes_de_reconectar(monkeypatch):
    """A session that ends without an exception is still a disconnection: it needs a sleep."""
    dormidas = []
    tentativas = {"n": 0}

    # The backoff wait became `_esperar_retry` (a wait_for interruptible by the
    # panel's 'r' key), so that is where the test observes — the intent stays
    # the same: do not reconnect without waiting.
    async def _fake_espera(self, d):
        dormidas.append(d)
        return False  # timeout normal, ninguem pediu retry antecipado

    async def _fake_connect(self):
        tentativas["n"] += 1
        if tentativas["n"] >= 4:
            self._should_reconnect = False  # encerra o teste
        return  # "clean" return, without an exception

    monkeypatch.setattr(ExecutorConnection, "_esperar_retry", _fake_espera)
    monkeypatch.setattr(ExecutorConnection, "_connect_and_run", _fake_connect)

    c = _conn()
    await asyncio.wait_for(c.run(), timeout=3.0)

    assert len(dormidas) == 3, "reconectou sem sleep em algum ciclo"
    # Backoff grows: a short session does not reset the delay to 1.
    assert dormidas[-1] > dormidas[0]


@pytest.mark.asyncio
async def test_sessao_longa_reseta_o_backoff(monkeypatch):
    relogio = {"t": 0.0}
    dormidas = []

    # Fake clock only for the connection module — patching the global
    # time.monotonic would break the event loop's own timers (loop.time()).
    class _FakeTime:
        @staticmethod
        def monotonic():
            return relogio["t"]

    monkeypatch.setattr(conn_mod, "time", _FakeTime)

    # See the note in the previous test: the backoff wait is now `_esperar_retry`.
    async def _fake_espera(self, d):
        dormidas.append(d)
        return False

    tentativas = {"n": 0}

    async def _fake_connect(self):
        tentativas["n"] += 1
        relogio["t"] += 600 if tentativas["n"] == 1 else 1  # 1a sessao saudavel
        if tentativas["n"] >= 3:
            self._should_reconnect = False
        raise RuntimeError("queda de rede")

    monkeypatch.setattr(ExecutorConnection, "_esperar_retry", _fake_espera)
    monkeypatch.setattr(ExecutorConnection, "_connect_and_run", _fake_connect)

    c = _conn()
    await asyncio.wait_for(c.run(), timeout=3.0)

    # 1a sessao durou 600s > _SESSION_STABLE_SECONDS => delay volta a 1
    # (jitter mantem o sleep entre 0.5 e 1.0).
    assert dormidas[0] <= 1.0


# ── B4/R5: sessao REAL (websockets.connect falso, _connect_and_run de verdade) ─

@pytest.mark.asyncio
async def test_excecao_do_receive_loop_propaga_e_encerra_por_close_terminal(monkeypatch):
    """End-to-end propagation: close 4403 -> first_exc -> classifier.

    Runs the REAL `_connect_and_run`. The previous version of this test replaced
    `_connect_and_run` with a function that raised the 4403 itself — that is, it
    tested the test's `raise`, not production's `raise first_exc`.
    """
    ws = _SessionWS(recv_exc=_closed(4403, "cert revogado"))
    _patch_connect(monkeypatch, ws)

    c = _conn()
    await asyncio.wait_for(c.run(), timeout=5.0)

    assert c._should_reconnect is False, "deny autoritativo tem que encerrar o executor"
    # The handshake did get sent: the session dropped AFTER the accept.
    assert json.loads(ws.enviadas[0])["type"] == "handshake"


@pytest.mark.asyncio
async def test_close_terminal_sobrevive_a_loop_auxiliar_que_termina_primeiro(monkeypatch):
    """An auxiliary loop that handles ConnectionClosed with `break` ends CLEANLY.

    If it wins the race against _receive_loop, `done` has no exception at all
    and the 4403 died along with the canceled `pending` — the executor
    reconnected with backoff instead of asking to redo the enrollment. The ws
    close_code survives the cancellation and is the source of truth.
    """
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    ws = _SessionWS(
        send_exc=_closed(4403, "cert revogado"),  # the result send fails...
        recv_delay=3600,                          # ...and the receive never wakes up
        close_code=4403, close_reason="cert revogado",
    )
    _patch_connect(monkeypatch, ws)

    results = asyncio.Queue()
    await results.put({"job_id": "j1", "run_id": "j1", "status": "success"})
    c = _conn(results=results)

    with pytest.raises(ConnectionClosedError) as info:
        await asyncio.wait_for(c._connect_and_run(), timeout=5.0)

    assert info.value.code == 4403
    msg, _tb, terminal = conn_mod._classify_connection_error(info.value)
    assert terminal is True, msg


@pytest.mark.asyncio
async def test_cancelar_a_conexao_encerra_todos_os_loops_filhos(monkeypatch):
    """`asyncio.wait` does NOT cancel what it awaits.

    Without the try/finally, canceling conn_task (SIGTERM) made the
    CancelledError rise from inside the `wait` and the 5 children stayed alive
    AFTER the shutdown gather, consuming from queues that main had already
    considered drained.
    """
    ws = _SessionWS(recv_delay=3600)
    _patch_connect(monkeypatch, ws)

    c = _conn(events=asyncio.Queue(maxsize=500))
    task = asyncio.create_task(c._connect_and_run())
    await asyncio.sleep(0.05)  # lets the children be born

    nomes = {"heartbeat", "capacity", "receive", "results", "events"}
    filhos = [t for t in asyncio.all_tasks() if t.get_name() in nomes]
    assert len(filhos) == 5, f"filhos esperados nao subiram: {[t.get_name() for t in filhos]}"

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    vivos = [t.get_name() for t in filhos if not t.done()]
    assert vivos == [], f"loops sobreviveram ao cancelamento: {vivos}"
    assert ws.fechado is True, "o __aexit__ do connect precisa fechar o ws"
