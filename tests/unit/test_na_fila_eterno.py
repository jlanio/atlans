# tests/unit/test_na_fila_eterno.py
"""Run stuck in "Na fila" (queued, 'pending') forever — the 2026-09-22 case.

The dispatch saves the run as 'pending' (already with the chosen executor's host)
BEFORE sending and only promotes it to 'running' after `send_job` returns. An
API worker that dies in that window left the run in 'pending' forever: the
orphan watchdog only looked at 'running' and nobody else closed the row.

Three defenses, one per test below:
  * the executor's ACK promotes 'pending' → 'running' (the proof of delivery
    comes from the other side, through any worker);
  * the watchdog closes as 'failed' an old 'pending' that no executor
    confirmed;
  * sending over the WebSocket has a deadline — a stalled connection doesn't
    hold up the dispatch (and the worker's scheduler) for up to 10 min.
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routers.executor_ws import inbox as IB
from app.api.routers.executor_ws import orfaos as ORF
from app.api.routers.executor_ws import resultados as RES
from app.core import executor_connections as ec
from app.models.base import Base
from app.models.workflow_run import WorkflowRun


# ── Real database (SQLite): what is tested is the conditional UPDATE ─────────

@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[WorkflowRun.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _sessao():
        async with fabrica() as s:
            yield s

    monkeypatch.setattr(RES, "get_session_async", _sessao)
    monkeypatch.setattr(ORF, "get_session_async", _sessao)
    try:
        yield fabrica
    finally:
        await engine.dispose()


async def _criar_run(fabrica, *, status="pending", host="executor:ex-1", idade_min=0.0):
    run = WorkflowRun(
        id_hash=str(uuid4()), task_id=str(uuid4()), workflow_hash="wf-1",
        workspace_id="ws-1", status=status, host=host, node_stats={},
        start_time=datetime.now(timezone.utc) - timedelta(minutes=idade_min),
    )
    async with fabrica() as s:
        s.add(run)
        await s.commit()
    return run.task_id


async def _status(fabrica, task_id):
    async with fabrica() as s:
        run = await s.get(WorkflowRun, (await _pk(s, task_id)))
        return run.status, run.error_category, run.error_message


async def _pk(s, task_id):
    from sqlalchemy import select
    return (await s.execute(select(WorkflowRun.id).where(WorkflowRun.task_id == task_id))).scalar_one()


# ── 1. O ACK promove 'pending' → 'running' ───────────────────────────────────

@pytest.fixture
def ack_limpo(monkeypatch):
    monkeypatch.setattr(ec.executor_registry, "clear_pending_ack", AsyncMock(return_value="ex-1"))


async def test_ack_promove_o_run_que_o_dispatch_nao_chegou_a_promover(banco, ack_limpo):
    """The worker that dispatched died after send_job: the executor has the job and
    confirms. Before, the run stayed "Na fila" (queued) forever with the workflow
    running."""
    tid = await _criar_run(banco)

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == "running"


async def test_ack_em_rajada_nao_vira_um_update_por_mensagem(banco, ack_limpo, monkeypatch):
    """Each ACK promotes with UPDATE + COMMIT: without a ceiling, a buggy executor
    tied up a database connection in a loop. Above the ceiling the ACK only
    loses the promotion — the inventory does it the next minute."""
    from app.api.routers.executor_ws import protocolo

    monkeypatch.setattr(protocolo, "_rate_state", {})
    monkeypatch.setattr(RES, "_JOB_RESULT_RATE_LIMIT", 2)
    ids = [await _criar_run(banco) for _ in range(3)]

    for tid in ids:
        await RES._record_job_ack("ex-1", tid, "enqueued")

    assert [(await _status(banco, tid))[0] for tid in ids] == ["running", "running", "pending"]


async def test_ack_de_outro_executor_nao_promove(banco, ack_limpo):
    tid = await _criar_run(banco, host="executor:ex-2")

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == "pending"


@pytest.mark.parametrize("terminal", ["cancelled", "failed", "success"])
async def test_ack_nao_ressuscita_run_terminal(banco, ack_limpo, terminal):
    """Cancelled between the INSERT and the delivery: the late ACK doesn't bring it back."""
    tid = await _criar_run(banco, status=terminal)

    await RES._record_job_ack("ex-1", tid, "enqueued")

    assert (await _status(banco, tid))[0] == terminal


async def test_dispatch_aceita_o_run_ja_promovido_pelo_ack():
    """The ACK usually arrives BEFORE the dispatch's own commit. If the dispatch's
    UPDATE required only 'pending', rowcount 0 would be read as a cancellation
    and the dispatch would send 'cancel' to a healthy job."""
    from app.services import workflow_execution_service as wes

    wf = MagicMock()
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = None
    wf.pin_metadata = None
    transicao = MagicMock(rowcount=1)
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=transicao)
    ag = MagicMock()
    ag.id_hash, ag.name, ag.public_key = "ag-1", "a1", "PEM"

    with patch.object(wes, "inject_credentials", new=AsyncMock(side_effect=lambda d, **k: d)), \
         patch.object(wes, "build_job_message", return_value={"ciphertext": ""}), \
         patch.object(wes, "executor_registry") as reg:
        reg.send_job = AsyncMock(return_value=True)
        reg.send_json = AsyncMock(return_value=True)
        await wes._dispatch_job(wf, {"nodes": []}, [ag], {}, False, db=db)

    stmt = db.execute.await_args_list[-1].args[0]
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "status IN ('pending', 'running')" in sql
    reg.send_json.assert_not_awaited()


async def test_ack_vai_pela_drenadora(monkeypatch):
    """The promotion is an UPDATE in Postgres: it goes through the drainer, it
    doesn't block the receive loop."""
    vistos = []

    async def _ack(executor_id, job_id, status):
        vistos.append((executor_id, job_id, status))

    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("ack", {"job_id": "j1", "status": "enqueued"}, 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drenar_inbox("ex-1", inbox)

    assert vistos == [("ex-1", "j1", "enqueued")]


async def test_ack_com_a_fila_cheia_e_processado_inline(monkeypatch):
    """If discarded, the ACK would leave in 'pending' a job the executor is running."""
    vistos = []

    async def _ack(executor_id, job_id, status):
        vistos.append(job_id)

    monkeypatch.setattr(IB, "_record_job_ack", _ack)
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(("node_event", {"run_id": "r", "node": "n", "kind": "stdout"}, 10))
    descartes = IB._novo_contador_de_descartes()

    await IB._enfileirar_mensagem("ex-1", inbox, descartes, "ack", {"job_id": "j1"}, 10)

    assert vistos == ["j1"]
    assert descartes["total"] == 0


# ── 2. The watchdog closes the 'pending' that nobody received ────────────────

@pytest.fixture
def efeitos(monkeypatch):
    """Records what the sweep does outside the database."""
    feito = {"contabilizados": [], "publicados": [], "cancelados": []}

    async def _contabiliza(db, run, *a, **k):
        feito["contabilizados"].append(run.task_id)

    async def _publica(run_ids, *, status, mensagem, extra=None):
        # None of these runs failed because of its content: retrying is safe.
        assert (status, extra) == ("failed", {"error_category": "transient", "retryable": True})
        feito["publicados"].extend(run_ids)

    async def _cancel(executor_id, data):
        feito["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", _contabiliza)
    monkeypatch.setattr("app.services.run_events_service.publicar_conclusao", _publica)
    monkeypatch.setattr(ORF.executor_registry, "send_json", _cancel)
    # By default every host speaks inventory (or is down).
    monkeypatch.setattr(ORF, "_hosts_sem_inventario", AsyncMock(return_value=set()))
    return feito


async def test_varredura_fecha_o_pending_velho_e_preserva_o_resto(banco, efeitos):
    preso = await _criar_run(banco, idade_min=11)
    recente = await _criar_run(banco, idade_min=1)
    rodando = await _criar_run(banco, status="running", idade_min=30)
    cancelado = await _criar_run(banco, status="cancelled", idade_min=30)

    assert await ORF._fechar_runs_nao_entregues() == 1

    status, categoria, mensagem = await _status(banco, preso)
    assert (status, categoria) == ("failed", "dispatch")
    assert "não chegou a rodar" in mensagem
    assert (await _status(banco, recente))[0] == "pending"
    assert (await _status(banco, rodando))[0] == "running"
    assert (await _status(banco, cancelado))[0] == "cancelled"
    # Counted once, dashboard notified and the host receives the 'cancel' just in
    # case (if the job arrived without an ACK, the executor interrupts it).
    assert efeitos["contabilizados"] == [preso]
    assert efeitos["publicados"] == [preso]
    assert efeitos["cancelados"] == [("ex-1", preso)]


async def test_varredura_concorrente_fecha_cada_run_uma_vez(banco, efeitos):
    """The 4 workers run the watchdog: the conditional UPDATE lets only one win."""
    await _criar_run(banco, idade_min=20)

    assert await ORF._fechar_runs_nao_entregues() == 1
    assert await ORF._fechar_runs_nao_entregues() == 0
    assert len(efeitos["contabilizados"]) == 1


async def test_executor_antigo_online_tem_o_prazo_de_um_job(banco, efeitos, monkeypatch):
    """An executor without inventory has no way to promote a job whose ACK was
    lost with the worker that dispatched it. Closing at 10 min would cancel a
    healthy job; it waits for a job's duration ceiling."""
    monkeypatch.setattr(ORF, "_hosts_sem_inventario", AsyncMock(return_value={"executor:ex-velho"}))
    do_antigo = await _criar_run(banco, host="executor:ex-velho", idade_min=11)
    do_antigo_esquecido = await _criar_run(banco, host="executor:ex-velho", idade_min=7 * 60)
    do_novo = await _criar_run(banco, host="executor:ex-1", idade_min=11)
    sem_host = await _criar_run(banco, host=None, idade_min=11)

    assert await ORF._fechar_runs_nao_entregues() == 3

    assert (await _status(banco, do_antigo))[0] == "pending"
    for tid in (do_antigo_esquecido, do_novo, sem_host):
        assert (await _status(banco, tid))[0] == "failed"


async def test_quem_espera_e_o_executor_online_sem_inventario(monkeypatch):
    presenca = {"ex-velho": True, "ex-novo": True, "ex-fora": False, "ex-incerto": None}
    marcados = {"executor:ex-novo:inventario"}

    async def _presenca(executor_id):
        return presenca[executor_id]

    class _Redis:
        async def exists(self, chave):
            return int(chave in marcados)

    monkeypatch.setattr(ec, "_redis_presence_or_unknown", _presenca)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _Redis())

    esperar = await ORF._hosts_sem_inventario(
        [f"executor:{e}" for e in presenca] + [None, "manual"],
    )

    # Unknown presence also waits: the decision is destructive.
    assert esperar == {"executor:ex-velho", "executor:ex-incerto"}


async def test_inventario_marca_o_executor_que_fala_inventario(banco, monkeypatch):
    gravadas = []

    class _Redis:
        async def setex(self, chave, ttl, valor):
            gravadas.append((chave, ttl))

        async def mget(self, chaves):
            return [None] * len(chaves)

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _Redis())
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: None)

    await ORF._reconciliar_inventario("ex-1", {"type": "inventario", "ativos": [], "resultados": []})

    assert gravadas == [("executor:ex-1:inventario", ORF._TTL_MARCA_DE_INVENTARIO_S)]


# ── 3. Sending over the WebSocket has a deadline ─────────────────────────────

class _RedisDeParada:
    def __init__(self):
        self.chaves = {}
        self.valores = {}                       # GET: a posse (`executor:conn_owner:{id}`)

    async def get(self, chave):
        return self.valores.get(chave)

    async def setex(self, chave, ttl, valor):
        self.chaves[chave] = ttl

    async def delete(self, chave):
        self.chaves.pop(chave, None)

    async def exists(self, chave):
        return int(chave in self.chaves)


class _WSLegado:
    """Mimics uvicorn's `--ws websockets` (websockets.legacy): writes the WHOLE
    frame and only then waits for the drain — and the drain doesn't accept two
    waiters (the `assert` in `_drain_helper`), not even on close."""

    def __init__(self):
        self.escritos = []
        self.escoou = asyncio.Event()
        self.fechado = None
        self._drenando = False

    async def send_text(self, texto):
        self.escritos.append(texto)
        assert not self._drenando, "drain concorrente"
        self._drenando = True
        try:
            await self.escoou.wait()
        finally:
            self._drenando = False

    async def close(self, code=1000, reason=""):
        assert not self._drenando, "drain concorrente no close"
        self.fechado = (code, reason)


@pytest.fixture
async def registro(monkeypatch):
    # A 50 ms deadline per send: "missing the deadline" takes milliseconds in the test.
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 0.05)
    redis = _RedisDeParada()

    async def _get_redis():
        return redis

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    reg = ec.ExecutorConnectionRegistry()
    reg.record_pending_ack = AsyncMock()
    reg.unregister = AsyncMock()
    reg.redis = redis
    yield reg
    # Shuts down the outputs and stray tasks created by the test.
    for ws in list(ec._saidas.keys()):
        ec.encerrar_saida(ws)
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)


def _conectar(registro, ws, executor_id="ex-1"):
    conn = ec.ExecutorConnection(executor_id=executor_id, websocket=ws)
    registro._connections[executor_id] = conn
    return conn


async def _ate(condicao, prazo_s=2.0):
    fim = asyncio.get_running_loop().time() + prazo_s
    while not condicao():
        assert asyncio.get_running_loop().time() < fim, "condição não ficou verdadeira a tempo"
        await asyncio.sleep(0.005)


async def test_envio_para_conexao_parada_estoura_o_prazo(registro):
    """Before, send_text waited for the drain until the ping timeout (10 min), with
    the run "Na fila" (queued) and the worker's scheduler stuck behind it."""
    ws = _WSLegado()
    _conectar(registro, ws)

    enviado = await asyncio.wait_for(
        registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}), timeout=5,
    )

    # The frame is already in the buffer and keeps going out: delivered WITHOUT
    # confirmation. Treating it as a refusal would send the job to another
    # executor — and both would run it.
    assert enviado is True
    registro.record_pending_ack.assert_awaited_once_with("j1", "ex-1")
    # A slow link is not a dead connection: dropping it erased the presence and the
    # watchdog closed all of the executor's runs as orphans.
    registro.unregister.assert_not_awaited()
    assert ec._saida_de(ws).atrasada()
    # The other workers see the delay and stop relaying.
    await _ate(lambda: "executor:parada:ex-1" in registro.redis.chaves)


async def test_um_escritor_por_vez_e_quem_nao_saiu_da_fila_nao_e_escrito(registro):
    """With the socket under backpressure, a second writer competed for the first
    one's drain: AssertionError with its frame ALREADY in the buffer — treated
    as a failure, it turned into failover or unregister. With the queue, only
    one writes."""
    ws = _WSLegado()

    primeiro, segundo = await asyncio.gather(
        ec.enviar_ao_executor(ws, "job-grande"), ec.enviar_ao_executor(ws, "cancel"),
    )

    assert (primeiro, segundo) == (ec.ESCOANDO, ec.OCUPADO)
    assert ws.escritos == ["job-grande"]       # whoever gave up in the queue didn't go out

    ws.escoou.set()                             # o link voltou
    await _ate(lambda: not ec._saida_de(ws).atrasada())
    assert await ec.enviar_ao_executor(ws, "depois") == ec.ENVIADO
    assert ws.escritos == ["job-grande", "depois"]


async def test_com_envio_atrasado_quem_manda_nao_espera_o_prazo(registro, monkeypatch):
    """With the in-progress write past its own deadline, the new message would wait
    behind it for the whole deadline and come out BUSY anyway — holding up the
    cancel, the control message and the watchdog's cancel loop."""
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)

    resultado = await asyncio.wait_for(ec.enviar_ao_executor(ws, "cancel", "ex-1"), timeout=1)

    assert resultado == ec.OCUPADO
    assert list(ec._saida_de(ws).fila) == []   # didn't even enter the queue


async def test_espera_conta_os_bytes_da_fila_e_nao_um_prazo_por_mensagem(registro, monkeypatch):
    """The 30 s base added per message ahead made 40 small events hold up a
    cancel for 20 minutes."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # the write started, within the deadline
    for _ in range(40):
        saida.enfileirar("evento")
    cancel = saida.enfileirar("cancel")

    # The own deadline + what remains of the in-progress send + the queue's bytes at 512 KB/s.
    assert saida._espera(cancel) < 2 * 30.0 + 1


async def test_fechar_resolve_a_fila_mesmo_sem_o_escritor_ter_rodado(registro, monkeypatch):
    """A writer cancelled before its first step never reaches its own
    `except`: whoever was in the queue waited the whole deadline for a BUSY."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    envio = saida.enfileirar("job")             # the writer hasn't had its turn yet

    saida.encerrar()

    assert await asyncio.wait_for(saida.aguardar(envio), timeout=1) == ec.FECHANDO
    assert ws.escritos == []


async def test_resposta_de_erro_enfileira_sem_prender_o_loop_de_recebimento(registro, monkeypatch):
    """What answers is the receive loop, the only one that renews the presence:
    stuck behind a slow frame, a live executor's presence expired."""
    from app.api.routers import executor_ws_router as rota

    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # socket congestionado

    rota._responder_erro(ws, "ex-1", "invalid_json")   # synchronous

    assert [e.texto for e in saida.fila] == ['{"type": "error", "reason": "invalid_json"}']
    ws.escoou.set()
    await _ate(lambda: len(ws.escritos) == 2)


async def test_resposta_de_erro_com_envio_atrasado_e_descartada(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    assert ec.enfileirar_ao_executor(ws, "erro", "ex-1") is False
    assert list(ec._saida_de(ws).fila) == []


async def test_mensagem_atras_de_transferencia_saudavel_espera_a_vez(registro, monkeypatch):
    """A large transfer WITHIN its own deadline doesn't quarantine the
    executor: whoever arrives behind waits for what is ahead and goes out later
    (before, the relay gave up at 5 s, closed the run and marked the executor
    as stalled)."""
    # Deadline = 0.1 s + 1 s per 512 KB: the large frame gets ~1.1 s; the small one, 0.1 s.
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 0.1)
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    grande_texto = "x" * (512 * 1024)
    grande = saida.enfileirar(grande_texto)
    await asyncio.sleep(0.05)                   # the write started

    seguinte = asyncio.create_task(saida.enviar("relayado"))
    await asyncio.sleep(0.4)                    # past the small one's deadline, within the large one's
    ws.escoou.set()

    assert await saida.aguardar(grande) == ec.ENVIADO
    assert await seguinte == ec.ENVIADO         # waited for what was ahead
    assert ws.escritos == [grande_texto, "relayado"]
    assert not saida.atrasada()
    assert "executor:parada:ex-1" not in registro.redis.chaves


async def test_fechar_no_meio_de_um_envio_nao_vaza_cancelamento(registro):
    """The close cancels the writer's wait. Whoever was still waiting for its own
    send got CancelledError — which escapes `except Exception`: the dispatch
    left the run in 'pending' and the worker's scheduler died silently."""
    ws = _WSLegado()
    saida = ec._saida_de(ws, "ex-1")
    envio = saida.enfileirar("job")
    na_fila = saida.enfileirar("depois")
    await asyncio.sleep(0.01)

    aguardando = asyncio.create_task(saida.aguardar(envio))
    await asyncio.sleep(0.01)
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await aguardando == ec.ESCOANDO       # written; not CancelledError
    assert await saida.aguardar(na_fila) == ec.FECHANDO
    assert ws.fechado == (4408, "Heartbeat timeout.")
    assert await saida.enviar("mais") == ec.FECHANDO
    assert ws.escritos == ["job"]


async def test_close_chega_ao_fim_mesmo_se_quem_pediu_desistir_de_esperar(registro):
    """The unregister waits at most 2 s for the close; cancelling the close midway
    abandoned it forever (socket and buffer alive until TCP gave up)."""
    fechou = asyncio.Event()

    class _WSDemorado(_WSLegado):
        async def close(self, code=1000, reason=""):
            await asyncio.sleep(0.1)
            self.fechado = (code, reason)
            fechou.set()

    ws = _WSDemorado()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ec.fechar_ws_do_executor(ws, code=4409), timeout=0.01)

    await asyncio.wait_for(fechou.wait(), timeout=2)
    assert ws.fechado == (4409, "")


async def test_conexao_parada_fica_fora_do_despacho_direto(registro):
    ws = _WSLegado()
    _conectar(registro, ws)
    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is True   # atrasou

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j2"}}) is False
    assert ws.escritos == [ws.escritos[0]]      # the second one didn't get in behind the delayed one


class _Publicados(list):
    redis = None


@pytest.fixture
def relay_publicado(monkeypatch):
    """The relay path with presence and free capacity; returns the channels on
    which something was published (one recipient each)."""
    monkeypatch.setattr(ec, "_redis_check_presence", AsyncMock(return_value=True))
    monkeypatch.setattr(ec, "_redis_read_capacity", AsyncMock(return_value={}))
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    publicados = _Publicados()

    class _RedisComPublish(_RedisDeParada):
        async def publish(self, canal, envelope):
            publicados.append(canal)
            return 1

    publicados.redis = redis = _RedisComPublish()

    async def _get_redis():
        return redis

    monkeypatch.setattr(ec, "_get_redis", _get_redis)
    return publicados


@pytest.fixture
def fechados(monkeypatch):
    """Runs the relay deemed undelivered: (executor, job, connection closing)."""
    from app.api.routers.executor_ws import orfaos

    fechados = []

    async def _fecha(executor_id, job_id, *, conexao_fechando=False):
        fechados.append((executor_id, job_id, conexao_fechando))
        return True

    monkeypatch.setattr(orfaos, "fechar_run_nao_entregue", _fecha)
    return fechados


async def test_socket_substituido_cai_no_relay_sem_marcar_parada(registro, relay_publicado):
    """On a connection swap the old socket takes seconds to close. Before, its
    sends answered "stalled" and flagged for a minute an executor that was
    already healthy on another worker."""
    ws = _WSLegado()
    _conectar(registro, ws)
    ec._saida_de(ws, "ex-1").encerrar(substituida=True)   # takeover em andamento

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is True

    assert relay_publicado == [ec._relay_channel("ex-1")]   # went through the relay
    assert ws.escritos == []
    assert "executor:parada:ex-1" not in relay_publicado.redis.chaves


async def test_executor_indo_embora_recusa_o_envio_em_vez_de_relayar(registro, relay_publicado):
    """Heartbeat, protocol error, disconnect: with no new session, the relay's only
    listener was this same socket's listener, which discarded the job after the
    publish counted one recipient — send_job answered True and the run went to
    'running' without the job ever going out."""
    ws = _WSLegado()
    _conectar(registro, ws)
    ec._saida_de(ws, "ex-1")
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is False

    assert relay_publicado == [] and ws.escritos == []
    registro.record_pending_ack.assert_not_awaited()


async def test_mensagem_de_controle_com_prazo_estourado_conta_como_entregue(registro, monkeypatch):
    """A cancel that misses the deadline keeps going out: whoever cancelled must not
    treat the executor as down (and close the run with the job still running)."""
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    ws = _WSLegado()
    _conectar(registro, ws)

    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is True
    registro.unregister.assert_not_awaited()


async def test_cancel_atras_de_envio_atrasado_nao_e_escrito_nem_derruba(registro, monkeypatch):
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    ws = _WSLegado()
    _conectar(registro, ws)
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    enviado = await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"})

    # Nothing went out: whoever cancelled gets False (and cancel_run, with the executor
    # alive, returns 503 instead of closing the run with the job running).
    assert enviado is False
    assert ws.escritos == ["job-grande"]
    registro.unregister.assert_not_awaited()


async def test_erro_de_envio_so_derruba_a_propria_conexao(registro):
    """If the executor reconnected to this worker while the send was failing, the
    new connection stays."""
    ws = MagicMock()
    ws.send_text = AsyncMock(side_effect=RuntimeError("socket fechado"))
    _conectar(registro, ws)

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False

    registro.unregister.assert_awaited_once_with("ex-1", expected_ws=ws)


async def test_outros_workers_nao_relayam_para_socket_atrasado(registro, monkeypatch):
    monkeypatch.setattr(ec, "_redis_check_presence", AsyncMock(return_value=True))
    monkeypatch.setattr(ec, "_redis_read_capacity", AsyncMock(return_value={}))
    monkeypatch.setattr("app.core.control_crypto.sign_if_needed", lambda data, _eid: data)
    await ec._redis_marcar_parada("ex-1")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await registro.send_json("ex-1", {"type": "cancel", "job_id": "j1"}) is False
    registro.record_pending_ack.assert_not_awaited()


async def test_a_marca_de_parada_some_quando_a_escrita_termina(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    await _ate(lambda: "executor:parada:ex-1" in registro.redis.chaves)

    ws.escoou.set()

    await _ate(lambda: "executor:parada:ex-1" not in registro.redis.chaves)
    assert not ec._saida_de(ws).atrasada()


async def test_relay_enfileira_e_segue_sem_prender_o_listener(registro, monkeypatch):
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    envelope = ec.build_relay_envelope('{"type": "job", "envelope": {"job_id": "j-relay"}}', executor_id="ex-1")

    continua = await asyncio.wait_for(ec._handle_relay_message("ex-1", ws, "dono", envelope), timeout=0.02)

    assert continua is True
    registro.unregister.assert_not_awaited()
    # The socket's writer is what writes, later. Up to 3.11 `wait_for` ran the
    # coroutine in a separate task and the loop iterations gave the writer time
    # before reaching here; from 3.12 onward it runs in the task itself and returns directly.
    await _ate(lambda: ws.escritos == ['{"type": "job", "envelope": {"job_id": "j-relay"}}'])


_JOB_RELAYADO = '{"type": "job", "envelope": {"job_id": "j-relay"}}'


async def test_job_relayado_que_nao_saiu_da_fila_tem_o_run_fechado(registro, monkeypatch, fechados):
    """Whoever published to the relay already deemed the job delivered. Without
    leaving the queue, the run stayed "Em andamento" (in progress) until the
    pending ACK expired (10 min)."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True

    await _ate(lambda: fechados == [("ex-1", "j-relay", False)])
    assert ws.escritos == ["job-grande"]


async def test_job_relayado_para_socket_substituido_fica_com_a_sessao_nova(registro, monkeypatch, fechados):
    """After the takeover the NEW session's listener also receives the message and
    delivers it — closing the run through the old listener would deem it undelivered."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    ec._saida_de(ws, "ex-1").encerrar(substituida=True)
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True
    await asyncio.sleep(0.05)

    assert fechados == [] and ws.escritos == []


async def test_job_relayado_para_executor_indo_embora_tem_o_run_fechado(registro, monkeypatch, fechados):
    """With no new session (heartbeat, disconnect), this listener was the only
    recipient: silently discarding left the run 'running' without the job going out."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    ec._saida_de(ws, "ex-1").encerrar()
    envelope = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", envelope) is True

    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == []


async def test_socket_fechado_antes_de_qualquer_envio_tambem_fica_fechando(registro, monkeypatch, fechados):
    """An idle executor that drops on heartbeat had no output channel: the relay created
    a new one, the writer hit the closed socket and the relayed job was lost
    without closing the run (the socket error doesn't close it)."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)

    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")

    assert await registro.send_job("ex-1", {"envelope": {"job_id": "j1"}}) is False
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == []
    registro.unregister.assert_not_awaited()     # CLOSING, not the error path


async def test_job_na_fila_quando_chega_o_takeover_tem_o_run_fechado(registro, monkeypatch, fechados):
    """What was in the queue was published BEFORE the takeover, and the new
    session's listener only subscribes after announcing it: nobody else delivers it."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)          # socket busy, within the deadline
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"   # already took over
    takeover = ec.build_relay_envelope(
        json.dumps({"__internal__": {"takeover": {"owner": "sessao-nova"}}}), executor_id="ex-1",
    )

    assert await ec._handle_relay_message("ex-1", ws, "dono", takeover) is False

    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    assert ws.escritos == ["job-grande"] and ws.fechado[0] == 4409
    assert saida.substituida and saida.avisada


async def test_job_nao_e_dado_por_nao_entregue_se_outra_sessao_tem_a_posse(registro, monkeypatch, fechados):
    """The executor reconnected on another worker without the notice reaching here
    (the old session's ownership expired in the middle of the heartbeat close):
    the new session also receives the job and delivers it. Closing the run would
    make the inventory order the running job to stop."""
    ws = _WSLegado()
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    await ec.fechar_ws_do_executor(ws, code=4408, reason="Heartbeat timeout.")
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"

    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)

    assert fechados == [] and ws.escritos == []


async def test_fila_da_posse_perdida_nao_e_dada_por_nao_entregue(registro, monkeypatch, fechados):
    """Ownership lost without the takeover notice: the new session may have
    received what was in the queue here — only the notice guarantees it didn't."""
    monkeypatch.setattr(ec, "_PRAZO_DE_ENVIO_BASE_S", 30.0)
    monkeypatch.setattr(ec, "_redis_renew_presence", AsyncMock(return_value=False))
    ws = _WSLegado()
    conn = _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    saida = ec._saida_de(ws, "ex-1")
    saida.enfileirar("job-grande")
    await _ate(lambda: saida.atual is not None)
    assert await ec._handle_relay_message(
        "ex-1", ws, "dono", ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1"),
    ) is True
    registro.redis.valores[ec._conn_owner_key("ex-1")] = "sessao-nova"
    conn.last_presence_renew = time.monotonic() - ec._PRESENCE_RENEW_INTERVAL - 1

    await registro._renew_presence_or_drop(conn)
    await asyncio.gather(*list(ec._tarefas_soltas), return_exceptions=True)

    assert saida.substituida and not saida.avisada
    assert fechados == []


async def test_socket_morto_no_relay_fecha_o_run(registro, monkeypatch, fechados):
    """The executor disconnected and the handler is still draining the queue: the
    relayed job hit the dead socket, and neither the error nor the ended
    listener closed the run (reconciliation skipped it because of the pending
    ACK for 10 min)."""
    ws = MagicMock()
    ws.send_text = AsyncMock(side_effect=RuntimeError("Unexpected ASGI message 'websocket.send'"))
    _conectar(registro, ws)
    monkeypatch.setattr(ec, "executor_registry", registro)
    primeiro = ec.build_relay_envelope(_JOB_RELAYADO, executor_id="ex-1")
    segundo = ec.build_relay_envelope('{"type": "job", "envelope": {"job_id": "j-2"}}', executor_id="ex-1")

    assert await ec._handle_relay_message("ex-1", ws, "dono", primeiro) is True
    await _ate(lambda: fechados == [("ex-1", "j-relay", True)])
    # The next one doesn't even enter the queue (the error is kept): the listener ends, and the run closes.
    assert await ec._handle_relay_message("ex-1", ws, "dono", segundo) is False
    await _ate(lambda: fechados == [("ex-1", "j-relay", True), ("ex-1", "j-2", True)])


async def test_takeover_e_anunciado_mesmo_sem_dono_anterior(registro, monkeypatch):
    """The ownership of a session that is still closing (heartbeat) expires in the
    middle of the close: with no previous owner, the notice didn't go out and its
    listener didn't know it had been replaced."""
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value=None))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())
    anuncios = []

    async def _anuncia(executor_id, owner_token):
        anuncios.append(executor_id)

    async def _escuta(*_a):
        await asyncio.sleep(3600)

    monkeypatch.setattr(registro, "_announce_takeover", _anuncia)
    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)

    assert anuncios == ["ex-1"]
    registro._listener_tasks["ex-1"].cancel()


async def test_sessao_antiga_nao_apaga_a_capacidade_da_nova(monkeypatch):
    """After a takeover the capacity key already belongs to the new session."""
    reg = ec.ExecutorConnectionRegistry()
    apagou = AsyncMock()
    monkeypatch.setattr(ec, "_redis_delete_capacity", apagou)
    monkeypatch.setattr(ec, "fechar_ws_do_executor", AsyncMock())
    for liberou, esperado in ((False, 0), (True, 1), (None, 2)):
        monkeypatch.setattr(ec, "_redis_release_presence", AsyncMock(return_value=liberou))
        reg._connections["ex-1"] = ec.ExecutorConnection(executor_id="ex-1", websocket=MagicMock())

        await reg.unregister("ex-1")

        assert apagou.await_count == esperado, liberou


async def test_drive_event_nao_engrossa_a_fila_atras_de_envio_atrasado(registro):
    ws = _WSLegado()
    assert await ec.enviar_ao_executor(ws, "job-grande", "ex-1") == ec.ESCOANDO

    assert await ec._handle_drive_message("ex-1", ws, ec.build_signed_envelope('{"type": "drive_event"}')) is True

    assert list(ec._saida_de(ws).fila) == []


async def test_takeover_sai_antes_de_o_listener_novo_subscrever(registro, monkeypatch):
    """With the new listener already subscribed, whatever was published before the
    takeover would reach BOTH sessions (job running twice) — and the old one,
    when closing, wouldn't know whether the new one received it."""
    ordem = []
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value="dono-antigo"))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())

    async def _escuta(*_a):
        ordem.append("listener")
        await asyncio.sleep(3600)

    async def _anuncia(executor_id, owner_token):
        await asyncio.sleep(0)                  # o publish de verdade espera o Redis
        ordem.append("takeover")

    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    monkeypatch.setattr(registro, "_announce_takeover", _anuncia)
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)
    await _ate(lambda: len(ordem) == 2)

    assert ordem == ["takeover", "listener"]
    registro._listener_tasks["ex-1"].cancel()


async def test_posse_perdida_manda_o_resto_pelo_relay(registro, monkeypatch):
    """The renewal found another owner: until the unregister (which waits for the
    lock), whatever is sent to this executor goes to the new session through the
    relay, not to the old socket."""
    monkeypatch.setattr(ec, "_redis_renew_presence", AsyncMock(return_value=False))
    ws = _WSLegado()                            # nothing has gone out through this socket yet
    conn = _conectar(registro, ws)
    conn.last_presence_renew = time.monotonic() - ec._PRESENCE_RENEW_INTERVAL - 1

    await registro._renew_presence_or_drop(conn)

    registro.unregister.assert_awaited_once_with("ex-1", expected_ws=ws)
    saida = ec._saidas[ws]
    assert saida.fechando and saida.substituida
    assert registro._conexao_para_envio("ex-1") is None


async def test_reconexao_limpa_a_marca_de_parada(registro, monkeypatch):
    """New socket, nothing draining: the previous session's mark would refuse the
    relay for a healthy executor."""
    monkeypatch.setattr(ec, "_redis_claim_presence", AsyncMock(return_value=None))
    monkeypatch.setattr(ec, "_redis_store_capacity", AsyncMock())

    async def _escuta(*_a):
        await asyncio.sleep(3600)

    monkeypatch.setattr(ec, "_executor_pubsub_listener", _escuta)
    await ec._redis_marcar_parada("ex-1")
    ws = MagicMock()
    ws.client = None

    await registro.register("ex-1", ws)

    assert "executor:parada:ex-1" not in registro.redis.chaves
    registro._listener_tasks["ex-1"].cancel()


def test_prazo_cresce_com_o_tamanho_do_frame():
    assert ec._prazo_de_envio(0) == ec._PRAZO_DE_ENVIO_BASE_S
    # 16 MB (the frame ceiling) gets ~32 s more than an empty frame.
    assert ec._prazo_de_envio(16 * 1024 * 1024) == pytest.approx(ec._PRAZO_DE_ENVIO_BASE_S + 32)


def test_a_api_fixa_a_implementacao_de_websocket_que_o_envio_pressupoe():
    """`_Saida` counts on the whole frame being written before the drain
    (uvicorn's legacy `websockets`). With `websockets-sansio`/`wsproto` the write
    waits for the socket FIRST — a missed deadline would be a job deemed
    delivered without having gone out. `auto` picks the right one today; the
    pin prevents a silent switch."""
    from pathlib import Path

    import yaml

    raiz = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((raiz / "docker-compose.yml").read_text(encoding="utf-8"))
    for servico in ("api-prod", "api"):
        assert "--ws websockets" in compose["services"][servico]["command"], servico
    assert '"--ws", "websockets"' in (raiz / "Dockerfile.api").read_text(encoding="utf-8")
