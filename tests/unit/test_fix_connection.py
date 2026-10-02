# tests/unit/test_fix_connection.py
"""Regressoes dos loops de envio e do backoff de reconexao do executor.

Bugs cobertos:
  B3 — task_done() so era chamado quando o item NAO era re-enfileirado. Cada
       falha de envio deslocava _unfinished_tasks +1 permanentemente e o
       `_event_queue.join()` de main.py (on_execute) nunca mais resolvia: todo
       job seguinte pagava 30s de timeout ("Timeout ao drenar fila de eventos
       — 0 evento(s) pendente(s)"). Agravantes: `await put()` numa fila cheia
       cujo unico consumidor e o proprio loop = deadlock; json.dumps cru no
       node_event; ausencia de teto de tentativas.
  B4 — excecao pos-handshake era engolida (logger.debug) e o retorno "limpo"
       de _connect_and_run zerava o backoff, reconectando sem sleep.
  P2 — o filtro de 'output' no result_sender_loop virou codigo morto (o descarte
       acontece na origem, em main.py on_execute).

Segunda rodada (revisao adversarial das proprias correcoes):
  R1 — o result loop ficou SEM teto de tentativas (assimetrico com o de
       eventos): um resultado que falha de forma deterministica girava para
       sempre e travava o `_result_queue.join()` do shutdown.
  R2 — cancelamento durante o `ws.send` perdia o item: CancelledError nao e
       Exception, nao caia em nenhum handler, e o `finally` ja tinha feito
       task_done() — o join() dava a fila por drenada com o item nunca enviado.
  R3 — `_safe_dumps` (truncagem modelada para job_result) reaproveitado no
       node_event: nao reduzia nada, injetava uma chave 'stats' inexistente e
       logava "job_result descartado" para algo que nao era job_result.
  R4 — `asyncio.wait` nao cancela o que aguarda: cancelar o conn_task deixava
       os 5 loops filhos vivos depois do gather do shutdown.
  R5 — close terminal (4401/4403/4404) se perdia quando um loop auxiliar
       terminava (limpo, por `break`) antes do _receive_loop.

Os testes de B4/R5 rodam o `_connect_and_run` REAL com um `websockets.connect`
falso. Monkeypatchar `_connect_and_run` — como a primeira versao fazia — anula
exatamente o codigo sob teste: o teste "de propagacao" so provava que uma
excecao levantada pelo proprio teste chegava ao classificador.
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
        self._restantes = raise_times  # None = sempre
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
    """WS falso completo o bastante para rodar o `_connect_and_run` REAL.

    Precisa ser iteravel (`async for raw in ws` do _receive_loop) e expor
    `close_code`/`close_reason` — que sao a fonte de verdade consultada quando
    nenhuma task em `done` trouxe a excecao do close.
    """

    def __init__(self, *, send_exc=None, send_exc_after=1, send_delay=0.0,
                 recv_exc=None, recv_delay=0.0, close_code=None, close_reason=""):
        self.enviadas = []
        self.fechado = False
        self.close_code = close_code
        self.close_reason = close_reason
        # O handshake e o primeiro send: deixa-lo passar e obrigatorio, senao a
        # excecao subiria de fora do asyncio.wait e o teste passaria pelo
        # caminho errado.
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
        # Sem mensagens: dorme ate ser cancelado (simula sessao ociosa).
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
    """Roda um sender_loop em task e cancela quando ele fica ocioso."""
    task = asyncio.create_task(coro_fn)
    await asyncio.sleep(0)
    return task


# ── B3: saldo do task_done fecha em TODOS os caminhos ────────────────────────

@pytest.mark.asyncio
async def test_event_join_resolve_apos_falha_de_envio(monkeypatch):
    """O caso que travava o executor: falha generica no envio de node_event.

    Antes: put() sem task_done => _unfinished_tasks nunca voltava a zero e o
    join() de on_execute estourava 30s em todo job subsequente.
    """
    monkeypatch.setattr(conn_mod, "_SEND_RETRY_PAUSE", 0)
    events = asyncio.Queue(maxsize=500)
    c = _conn(events=events)
    # Falha nas 2 primeiras tentativas, envia na terceira.
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
    """Erro deterministico (payload impossivel) nao pode reciclar para sempre."""
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
    """A chave interna de retry nao pode vazar no protocolo node_event."""
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

    # Nao deve bloquear: descarta com log.
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

    # Evento voltou para a fila (sera reenviado apos reconexao) e o saldo
    # corresponde exatamente a 1 item pendente — nao 2.
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


# ── R1: o result loop tambem precisa de teto ─────────────────────────────────

@pytest.mark.asyncio
async def test_result_descartado_apos_teto_e_continua_no_outbox(monkeypatch):
    """Resultado 'imortal' prendia o unico consumidor e o join() do shutdown.

    Cenario real: stats com referencia circular => json.dumps levanta sempre.
    Sem teto, o item voltava para a fila indefinidamente (1 tentativa/s) e o
    `_result_queue.join()` de main.py pagava os 30s inteiros de timeout em todo
    deploy. Com teto, a fila drena — e o resultado NAO e dado como enviado
    (mark_sent nunca chamado), entao o outbox o reenvia no proximo start.
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
    """O `mark_sent` apaga o outbox assim que o send retorna, mas o servidor pode
    ainda nem ter processado o resultado. Até lá o inventário segue dizendo que
    o job terminou aqui — senão o servidor fecharia o run como perdido."""
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


# ── R2: cancelamento durante o ws.send nao pode perder o item ────────────────

@pytest.mark.asyncio
async def test_result_volta_para_a_fila_quando_cancelado_durante_o_send(monkeypatch):
    """`for task in pending: task.cancel()` roda em TODA queda de sessao.

    Se o cancelamento pega o loop dentro do `ws.send`, o resultado ja saiu da
    fila: sem o handler de CancelledError ele sumia (o `finally` fazia
    task_done) e o `join()` do shutdown reportava 'drenado' sem log algum.
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


# ── R3: serializacao de node_event tem teto PROPRIO ──────────────────────────

def test_dumps_event_reduz_evento_gigante_aos_campos_de_controle():
    """A truncagem de job_result (por 'stats') nao servia para node_event.

    Reaproveitada, ela devolvia uma string MAIOR que a entrada, injetava uma
    chave 'stats' que node_event nunca teve e logava 'job_result descartado'.
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
    assert payload["type"] == "node_event"      # sem isso o servidor nao roteia
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
    """Teto tem que ser garantia: um 'node' gigante nao pode passar inteiro."""
    evento = {"type": "node_event", "run_id": "r1",
              "node": {"lixo": "y" * (TETO_NODE_EVENT_BYTES + 100)},
              "status": "log"}
    raw = conn_mod._dumps_event(evento)
    assert len(raw) < TETO_NODE_EVENT_BYTES


def test_dumps_result_preserva_chaves_de_controle_ao_truncar(monkeypatch):
    """A truncagem por 'stats' continua viva — no lugar certo (job_result)."""
    monkeypatch.setattr(conn_mod, "_MAX_WS_PAYLOAD", 2_000)
    obj = {"type": "job_result", "job_id": "j1", "status": "success",
           "stats": {"__response__": {"ok": True}, "no1": "z" * 5_000}}

    payload = json.loads(conn_mod._dumps_result(obj))

    assert payload["stats"]["__response__"] == {"ok": True}
    assert payload["stats"]["__truncated__"] is True
    assert "no1" not in payload["stats"]


# ── P2: o result vai inteiro; quem descarta 'output' e o main.py ─────────────

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


# ── B4: backoff nao pode ser zerado por sessao curta ─────────────────────────

@pytest.mark.asyncio
async def test_retorno_limpo_ainda_dorme_antes_de_reconectar(monkeypatch):
    """Sessao que termina sem excecao continua sendo desconexao: precisa sleep."""
    dormidas = []
    tentativas = {"n": 0}

    # A espera do backoff virou `_esperar_retry` (um wait_for interrompivel pela
    # tecla 'r' do painel), entao e nele que o teste observa — a intencao segue
    # a mesma: nao reconectar sem esperar.
    async def _fake_espera(self, d):
        dormidas.append(d)
        return False  # timeout normal, ninguem pediu retry antecipado

    async def _fake_connect(self):
        tentativas["n"] += 1
        if tentativas["n"] >= 4:
            self._should_reconnect = False  # encerra o teste
        return  # retorno "limpo", sem excecao

    monkeypatch.setattr(ExecutorConnection, "_esperar_retry", _fake_espera)
    monkeypatch.setattr(ExecutorConnection, "_connect_and_run", _fake_connect)

    c = _conn()
    await asyncio.wait_for(c.run(), timeout=3.0)

    assert len(dormidas) == 3, "reconectou sem sleep em algum ciclo"
    # Backoff cresce: sessao curta nao reseta delay para 1.
    assert dormidas[-1] > dormidas[0]


@pytest.mark.asyncio
async def test_sessao_longa_reseta_o_backoff(monkeypatch):
    relogio = {"t": 0.0}
    dormidas = []

    # Relogio falso apenas para o modulo connection — patchar time.monotonic
    # global quebraria os timers do proprio event loop (loop.time()).
    class _FakeTime:
        @staticmethod
        def monotonic():
            return relogio["t"]

    monkeypatch.setattr(conn_mod, "time", _FakeTime)

    # Ver a nota do teste anterior: a espera do backoff agora e `_esperar_retry`.
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
    """Propagacao ponta a ponta: close 4403 -> first_exc -> classificador.

    Roda o `_connect_and_run` REAL. A versao anterior deste teste substituia
    `_connect_and_run` por uma funcao que levantava o proprio 4403 — ou seja,
    testava o `raise` do teste, nao o `raise first_exc` da producao.
    """
    ws = _SessionWS(recv_exc=_closed(4403, "cert revogado"))
    _patch_connect(monkeypatch, ws)

    c = _conn()
    await asyncio.wait_for(c.run(), timeout=5.0)

    assert c._should_reconnect is False, "deny autoritativo tem que encerrar o executor"
    # O handshake chegou a ser enviado: a sessao caiu DEPOIS do accept.
    assert json.loads(ws.enviadas[0])["type"] == "handshake"


@pytest.mark.asyncio
async def test_close_terminal_sobrevive_a_loop_auxiliar_que_termina_primeiro(monkeypatch):
    """Loop auxiliar que trata ConnectionClosed com `break` termina LIMPO.

    Se ele vence a corrida com o _receive_loop, `done` nao tem excecao alguma e
    o 4403 morria junto com os `pending` cancelados — o executor reconectava em
    backoff em vez de mandar refazer o enrollment. O close_code do ws sobrevive
    ao cancelamento e e a fonte de verdade.
    """
    from executor import result_store
    monkeypatch.setattr(result_store, "mark_sent", lambda *_a: None)

    ws = _SessionWS(
        send_exc=_closed(4403, "cert revogado"),  # o send do resultado falha...
        recv_delay=3600,                          # ...e o receive nunca acorda
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
    """`asyncio.wait` NAO cancela o que aguarda.

    Sem o try/finally, cancelar o conn_task (SIGTERM) fazia o CancelledError
    subir de dentro do `wait` e os 5 filhos continuavam vivos DEPOIS do gather
    do shutdown, consumindo das filas que o main ja deu por drenadas.
    """
    ws = _SessionWS(recv_delay=3600)
    _patch_connect(monkeypatch, ws)

    c = _conn(events=asyncio.Queue(maxsize=500))
    task = asyncio.create_task(c._connect_and_run())
    await asyncio.sleep(0.05)  # deixa os filhos nascerem

    nomes = {"heartbeat", "capacity", "receive", "results", "events"}
    filhos = [t for t in asyncio.all_tasks() if t.get_name() in nomes]
    assert len(filhos) == 5, f"filhos esperados nao subiram: {[t.get_name() for t in filhos]}"

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    vivos = [t.get_name() for t in filhos if not t.done()]
    assert vivos == [], f"loops sobreviveram ao cancelamento: {vivos}"
    assert ws.fechado is True, "o __aexit__ do connect precisa fechar o ws"
