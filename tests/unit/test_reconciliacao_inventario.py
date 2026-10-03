# tests/unit/test_reconciliacao_inventario.py
"""Executor↔server reconciliation and cancellation of an unknown job.

Real cases that motivated it:
  * Sep 22 — titan stayed connected with three runs it never received; they
    stayed "Em andamento" (in progress) until it disconnected, 16 min later, and
    only then became "Executor desconectou durante a execução".
  * an executor was killed by the cgroup OOM in the middle of an analysis, came
    back in 6 s and nobody closed the run it was executing.
  * Cancelling a run the executor did not have was silence: the executor logged
    "unknown" and the run stayed "Em andamento" forever.
"""
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routers.executor_ws import inbox as IB
from app.api.routers.executor_ws import orfaos as ORF
from app.api.routers.executor_ws import resultados as RES
from app.models.base import Base
from app.models.workflow_run import WorkflowRun


# ═══ Servidor ════════════════════════════════════════════════════════════════

class _RedisFalso:
    def __init__(self, chegou=()):
        self.chegou = set(chegou)

    async def mget(self, chaves):
        return ["{}" if c in self.chegou else None for c in chaves]


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
    # No registered connection: the minimum interval between reconciliations does not apply.
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: None)
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
def efeitos(monkeypatch):
    feito = {"contabilizados": [], "publicados": [], "cancelados": [], "redis": _RedisFalso()}

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
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: feito["redis"])
    return feito


async def _run(fabrica, *, status="running", host="executor:ex-1", idade_min=5.0):
    run = WorkflowRun(
        id_hash=str(uuid4()), task_id=str(uuid4()), workflow_hash="wf-1",
        workspace_id="ws-1", status=status, host=host, node_stats={},
        start_time=datetime.now(timezone.utc) - timedelta(minutes=idade_min),
    )
    async with fabrica() as s:
        s.add(run)
        await s.commit()
    return run.task_id


async def _linha(fabrica, task_id):
    async with fabrica() as s:
        return (await s.execute(select(WorkflowRun).where(WorkflowRun.task_id == task_id))).scalar_one()


def _inventario(ativos=(), resultados=(), truncado=False):
    return {"type": "inventario", "ativos": list(ativos), "resultados": list(resultados), "truncado": truncado}


async def test_run_que_o_executor_nao_tem_e_fechado_como_perdido(banco, efeitos):
    """The titan case: connected, without the job, and the run "Em andamento"."""
    perdido = await _run(banco)

    feito = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert feito["fechados"] == 1
    linha = await _linha(banco, perdido)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert "não tinha mais esta execução" in linha.error_message
    assert efeitos["contabilizados"] == [perdido]
    assert efeitos["publicados"] == [perdido]


async def test_job_ainda_a_caminho_nao_e_fechado_como_perdido(banco, efeitos):
    """A send that timed out keeps draining through the socket for an indefinite
    time: with the pending ACK alive, the run is not lost — closing it would
    let the executor run, with side effects, a job of an already closed run."""
    a_caminho = await _run(banco)
    efeitos["redis"].chegou.add(f"executor:pending_ack:{a_caminho}")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert feito["fechados"] == 0
    assert (await _linha(banco, a_caminho)).status == "running"


async def test_run_fechado_como_perdido_recebe_cancel(banco, efeitos):
    """If the job still arrives, the cancel arrives after it on the same socket and
    interrupts it — or becomes a tombstone."""
    perdido = await _run(banco)

    await ORF._reconciliar_inventario("ex-1", _inventario())
    await asyncio.gather(*ORF._cancels_em_curso)   # saem em segundo plano

    assert ("ex-1", perdido) in efeitos["cancelados"]


async def test_run_de_job_descartado_no_relay_fecha_como_nao_entregue(banco, efeitos, monkeypatch):
    limpos = []

    async def _limpa(job_id, expected_executor_id=None):
        limpos.append((job_id, expected_executor_id))

    monkeypatch.setattr(ORF.executor_registry, "clear_pending_ack", _limpa)
    tid = await _run(banco, status="running")
    alheio = await _run(banco, status="running", host="executor:ex-2")
    terminou = await _run(banco, status="success")
    no_fechamento = await _run(banco, status="running")

    assert await ORF.fechar_run_nao_entregue("ex-1", tid) is True
    assert await ORF.fechar_run_nao_entregue("ex-1", alheio) is False     # someone else's host
    assert await ORF.fechar_run_nao_entregue("ex-1", terminou) is False   # already terminal
    assert await ORF.fechar_run_nao_entregue("ex-1", no_fechamento, conexao_fechando=True) is True

    linha = await _linha(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "envio anterior" in linha.error_message
    # The right reason for the reader: the connection was closing, there was no queue.
    assert "sendo encerrada" in (await _linha(banco, no_fechamento)).error_message
    assert efeitos["contabilizados"] == [tid, no_fechamento]
    assert efeitos["publicados"] == [tid, no_fechamento]
    assert limpos == [(tid, "ex-1"), (no_fechamento, "ex-1")]


async def test_cancels_da_reconciliacao_nao_prendem_a_drenadora(banco, efeitos, monkeypatch):
    """Reconciliation runs in the connection's drainer: with the socket congested,
    each inline cancel could wait its turn for the whole timeout, delaying that
    connection's job_results."""
    liberar = asyncio.Event()

    async def _cancel_lento(executor_id, data):
        await liberar.wait()
        efeitos["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr(ORF.executor_registry, "send_json", _cancel_lento)
    perdido = await _run(banco)

    feito = await asyncio.wait_for(ORF._reconciliar_inventario("ex-1", _inventario()), timeout=2)

    assert feito["fechados"] == 1 and efeitos["cancelados"] == []
    liberar.set()
    await asyncio.gather(*ORF._cancels_em_curso)
    assert efeitos["cancelados"] == [("ex-1", perdido)]


async def test_o_que_o_executor_tem_fica_como_esta(banco, efeitos):
    rodando = await _run(banco)
    terminou = await _run(banco)   # result in the executor's outbox, on its way

    await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[rodando], resultados=[terminou]))

    assert (await _linha(banco, rodando)).status == "running"
    assert (await _linha(banco, terminou)).status == "running"
    assert efeitos["contabilizados"] == []


async def test_run_recente_nao_e_julgado(banco, efeitos):
    """A job still in transit when the executor built the inventory is not a loss."""
    novo = await _run(banco, idade_min=1)

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, novo)).status == "running"


async def test_resultado_recem_chegado_ao_servidor_protege_o_run(banco, efeitos):
    """The job_result has already passed through the WS (key with a 300 s TTL) and the
    consumer is still going to close the run: closing it here would erase the real outcome."""
    tid = await _run(banco)
    efeitos["redis"].chegou.add(f"executor:ex-1:results:{tid}")

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, tid)).status == "running"


async def test_redis_fora_do_ar_adia_sem_fechar(banco, efeitos, monkeypatch):
    tid = await _run(banco)

    class _RedisQuebrado:
        async def mget(self, _chaves):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _RedisQuebrado())

    await ORF._reconciliar_inventario("ex-1", _inventario())

    assert (await _linha(banco, tid)).status == "running"


async def test_pending_que_o_executor_nao_tem_vira_nao_entregue(banco, efeitos):
    tid = await _run(banco, status="pending")

    await ORF._reconciliar_inventario("ex-1", _inventario())

    linha = await _linha(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "não chegou a rodar" in linha.error_message


async def test_pending_que_o_executor_tem_e_promovido(banco, efeitos):
    """Lost ACK: the inventory is the second proof of delivery."""
    tid = await _run(banco, status="pending", idade_min=0.5)

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[tid]))

    assert feito["promovidos"] == 1
    assert (await _linha(banco, tid)).status == "running"


async def test_zumbi_que_o_servidor_ja_fechou_recebe_cancel(banco, efeitos):
    """Cancelled while the executor was down: it comes back still running the job."""
    tid = await _run(banco, status="cancelled")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[tid]))
    await asyncio.gather(*ORF._cancels_em_curso)   # saem em segundo plano

    assert feito["parados"] == 1
    assert efeitos["cancelados"] == [("ex-1", tid)]


async def test_inventario_truncado_nao_fecha_por_ausencia(banco, efeitos):
    perdido = await _run(banco)
    pendente = await _run(banco, status="pending", idade_min=0.5)

    feito = await ORF._reconciliar_inventario(
        "ex-1", _inventario(ativos=[pendente], truncado=True),
    )

    assert feito["fechados"] == 0
    assert (await _linha(banco, perdido)).status == "running"
    assert (await _linha(banco, pendente)).status == "running"   # promover continua valendo


async def test_runs_de_outro_executor_nao_sao_tocados(banco, efeitos):
    alheio = await _run(banco, host="executor:ex-2")
    alheio_pendente = await _run(banco, host="executor:ex-2", status="pending", idade_min=0.5)

    await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[alheio_pendente]))

    assert (await _linha(banco, alheio)).status == "running"
    assert (await _linha(banco, alheio_pendente)).status == "pending"


async def test_inventario_malformado_e_ignorado(banco, efeitos):
    tid = await _run(banco)

    assert await ORF._reconciliar_inventario("ex-1", {"type": "inventario", "ativos": "tudo"}) == {}
    assert (await _linha(banco, tid)).status == "running"


async def test_intervalo_minimo_entre_reconciliacoes(banco, efeitos, monkeypatch):
    """A buggy executor does not turn the inventory into one SELECT per message."""
    conn = SimpleNamespace(
        ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    await _run(banco)

    primeira = await ORF._reconciliar_inventario("ex-1", _inventario())
    segunda = await ORF._reconciliar_inventario("ex-1", _inventario())

    assert primeira["fechados"] == 1
    assert segunda == {}


async def test_conexao_recem_aberta_nao_fecha_por_ausencia(banco, efeitos, monkeypatch):
    """Reconnection: the PREVIOUS connection's inbox may still be draining the
    job_result of a run that finished before the drop. The new session's first
    inventory does not list it — closing now would make the true result be
    rejected right after. Promoting and stopping zombies do not wait."""
    conn = SimpleNamespace(ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc))
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    terminou_antes_da_queda = await _run(banco)
    na_fila = await _run(banco, status="pending")

    feito = await ORF._reconciliar_inventario("ex-1", _inventario(ativos=[na_fila]))

    assert feito == {"promovidos": 1, "parados": 0, "fechados": 0}
    assert (await _linha(banco, terminou_antes_da_queda)).status == "running"
    assert (await _linha(banco, na_fila)).status == "running"


async def test_inventario_vai_pela_drenadora_depois_do_job_result(monkeypatch):
    """On the same queue: the job_result sent before the inventory is written before
    the inventory is checked — otherwise the just-finished run would look lost."""
    ordem = []

    async def _resultado(executor_id, msg, frame_bytes=0, **_kw):
        ordem.append(("job_result", msg["job_id"]))

    async def _reconcilia(executor_id, msg):
        ordem.append(("inventario", tuple(msg["ativos"])))

    monkeypatch.setattr(IB, "_handle_job_result", _resultado)
    monkeypatch.setattr(IB, "_reconciliar_inventario", _reconcilia)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("job_result", {"job_id": "j1"}, 10))
    inbox.put_nowait(("inventario", _inventario(), 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drenar_inbox("ex-1", inbox)

    assert ordem == [("job_result", "j1"), ("inventario", ())]


async def test_inventario_com_a_fila_cheia_e_descartado(monkeypatch):
    """Periodic: the next one arrives in a minute; back-pressure is not worth it."""
    chamado = []
    monkeypatch.setattr(IB, "_reconciliar_inventario", lambda *a: chamado.append(a))
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(("job_result", {"job_id": "x"}, 10))
    descartes = IB._novo_contador_de_descartes()

    await IB._enfileirar_mensagem("ex-1", inbox, descartes, "inventario", _inventario(), 10)

    assert descartes["total"] == 1 and chamado == []


# ── Consumer: o primeiro desfecho vale ───────────────────────────────────────

def _db_do_consumer(run):
    selecionado = MagicMock()
    selecionado.scalar_one_or_none.return_value = run
    db = AsyncMock()
    db.execute = AsyncMock(return_value=selecionado)
    return db


def _payload(status):
    return {"task_id": "run-1", "status": status, "stats": {},
            "end_time": datetime.now(timezone.utc).isoformat()}


async def test_desfecho_tardio_diferente_nao_sobrescreve_o_primeiro(monkeypatch):
    """The true result (success) and a late one (a 'cancelled' coming from a cancel
    that crossed paths with the end of the job) both passed the WS check before
    the first was written. The consumer wrote both, and the last one won: a
    success became cancelled — and usage was counted twice."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="success", node_stats={})
    db = _db_do_consumer(run)
    grava = AsyncMock()
    fase = AsyncMock(return_value=rrc.PHASE_OK)
    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", fase)

    assert await rrc._process_result(db, _payload("cancelled")) is True

    assert run.status == "success"
    grava.assert_not_awaited()
    fase.assert_not_awaited()          # no usage, no metrics, no notification
    db.commit.assert_awaited()         # solta a trava do FOR UPDATE
    # Two workers with the same run: the second waits for the first one's commit.
    from sqlalchemy.dialects import postgresql
    select_do_run = db.execute.await_args_list[0].args[0]
    assert "FOR UPDATE" in str(select_do_run.compile(dialect=postgresql.dialect()))


async def test_resultado_verdadeiro_corrige_o_desfecho_que_o_servidor_deduziu(monkeypatch):
    """The server closed the run as lost (executor went down, reconciliation) with the
    true result already in the queue: the result corrects the guess, as it always
    has. Only a REAL outcome (or the user's cancellation) is final."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="failed", error_category="executor_lost", node_stats={})
    grava = AsyncMock()
    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", AsyncMock(return_value=rrc.PHASE_OK))

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_awaited_once()


async def test_cancelamento_do_usuario_nao_e_desfeito_por_resultado_tardio(monkeypatch):
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="cancelled", node_stats={})
    grava = AsyncMock()
    monkeypatch.setattr(rrc, "_update_run_status", grava)

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_not_awaited()


async def test_orfao_nao_sobrescreve_resultado_gravado_no_meio(banco, efeitos, monkeypatch):
    """Between the SELECT of the orphans and the commit, the consumer wrote the true
    result. The ORM's UPDATE by PK overwrote it with 'failed' — and usage was
    counted twice."""
    from sqlalchemy import update as sa_update

    run_id = await _run(banco)
    real = ORF.get_session_async

    @asynccontextmanager
    async def _com_corrida():
        async with real() as sessao:
            original = sessao.execute
            feito = {"n": 0}

            async def _execute(stmt, *a, **k):
                resultado = await original(stmt, *a, **k)
                feito["n"] += 1
                if feito["n"] == 1:   # right after the SELECT, the consumer writes
                    async with banco() as outra:
                        await outra.execute(
                            sa_update(WorkflowRun).where(WorkflowRun.task_id == run_id)
                            .values(status="success")
                        )
                        await outra.commit()
                return resultado

            sessao.execute = _execute
            yield sessao

    monkeypatch.setattr(ORF, "get_session_async", _com_corrida)

    await ORF._fail_orphan_runs("ex-1")

    assert (await _linha(banco, run_id)).status == "success"
    assert efeitos["contabilizados"] == [] and efeitos["publicados"] == []


async def test_orfao_fecha_o_run_que_ficou_rodando(banco, efeitos):
    run_id = await _run(banco)

    await ORF._fail_orphan_runs("ex-1")

    linha = await _linha(banco, run_id)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert linha.duration_seconds and linha.duration_seconds > 0
    assert efeitos["contabilizados"] == [run_id] and efeitos["publicados"] == [run_id]


async def test_reentrega_do_mesmo_desfecho_segue_como_antes(monkeypatch):
    """Reprocessed dead letter: the phases run again, without recounting usage."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="success", node_stats={})
    grava = AsyncMock()
    chamadas = []

    async def _fase(db, run, task_id, label, fn, *args):
        chamadas.append((label, args[-1] if label == "uso diario" else None))
        return rrc.PHASE_OK

    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", _fase)

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_awaited_once()
    assert ("uso diario", False) in chamadas   # first_close=False: does not recount


# ── cancel_run with the executor down ────────────────────────────────────────

def _mock_db(*resultados):
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=list(resultados))
    return db


def _select(run):
    r = MagicMock()
    r.scalar_one_or_none.return_value = run
    return r


async def test_cancelar_com_o_executor_fora_do_ar_fecha_no_servidor():
    """It used to be a 503 and the lost run had no way to be cleaned up from the screen."""
    from app.services import workflow_execution_service as wes

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws", status="running",
                      host="executor:ex-1", node_stats={})
    db = _mock_db(_select(run), MagicMock(rowcount=1))

    with patch.object(wes, "executor_registry") as reg, \
         patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()) as contabiliza:
        reg.send_json = AsyncMock(return_value=False)
        reg.presence_or_unknown = AsyncMock(return_value=False)
        outcome = await wes.cancel_run(db, "run-1", user_id="u", como_admin=True)

    assert outcome == "cancelled"
    assert run.status == "cancelled"
    assert "fora do ar" in run.error_message
    contabiliza.assert_awaited_once()
    # Conditional: a job_result that arrives in the middle wins.
    sql = str(db.execute.await_args_list[-1].args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "status IN ('pending', 'running')" in sql


async def test_cancelar_offline_perde_para_o_resultado_que_chegou():
    from app.services import workflow_execution_service as wes

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws", status="running",
                      host="executor:ex-1", node_stats={})
    db = _mock_db(_select(run), MagicMock(rowcount=0))

    async def _refresh(obj):
        obj.status = "success"

    db.refresh = AsyncMock(side_effect=_refresh)
    with patch.object(wes, "executor_registry") as reg:
        reg.send_json = AsyncMock(return_value=False)
        reg.presence_or_unknown = AsyncMock(return_value=False)
        outcome = await wes.cancel_run(db, "run-1", user_id="u", como_admin=True)

    assert outcome == "already_finished"
    assert run.status == "success"


# ═══ Executor ════════════════════════════════════════════════════════════════

@pytest.fixture
def store(tmp_path, monkeypatch):
    from executor import result_store
    monkeypatch.setattr(result_store, "_DB_PATH", str(tmp_path / "outbox.sqlite"))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_trava_do_diario", None)
    monkeypatch.setattr(result_store, "_esperando_posse", False)
    monkeypatch.setattr(result_store, "_INTERVALO_DE_POSSE_S", 0.02)
    yield result_store
    result_store.close()
    # Whoever started without the lock retries in the background: wait for that
    # round to finish so it does not leak into the next test.
    for _ in range(300):
        if not result_store._esperando_posse:
            break
        time.sleep(0.01)
    if result_store._trava_do_diario is not None:
        result_store._trava_do_diario.close()


def test_job_aceito_fica_no_diario_ate_o_resultado(store):
    store.registrar_em_voo("j1")
    store.registrar_em_voo("j2")
    store.marcar_executando("j2")

    store.put({"job_id": "j1", "run_id": "j1", "status": "ok"})

    # The result takes the job out of the journal in the same transaction —
    # otherwise the table would grow one row per job for the whole life of the process.
    linhas = store._get_conn().execute("SELECT job_id FROM jobs_em_voo").fetchall()
    assert [r[0] for r in linhas] == ["j2"]
    # j1 finished (result in the outbox); j2 died in the middle.
    assert [o["job_id"] for o in store.carregar_em_voo()] == ["j2"]
    assert store.carregar_em_voo()[0]["estado"] == store.ESTADO_EXECUTANDO
    assert store.job_ids_pendentes() == ["j1"]


def test_outbox_guarda_a_categoria_para_o_replay(store):
    store.put({"job_id": "j1", "status": "error", "error": "x", "error_category": "executor_lost"})
    assert store.load_pending()[0]["error_category"] == "executor_lost"


def test_orfao_do_boot_vira_falha_com_a_causa(store, monkeypatch):
    """The OOM case: killed midway, the executor comes back and reports what it lost."""
    from executor import main as M

    monkeypatch.setattr("executor.sysinfo._get_cgroup_ram_total", lambda: 2 * 1024 ** 3)
    store.registrar_em_voo("rodando")
    store.marcar_executando("rodando")
    store.registrar_em_voo("na-fila")

    assert M._fechar_orfaos_do_boot_anterior() == 2

    resultados = {r["job_id"]: r for r in store.load_pending()}
    assert resultados["rodando"]["status"] == "error"
    assert resultados["rodando"]["error_category"] == "executor_lost"
    assert "no meio desta execução" in resultados["rodando"]["error"]
    assert "2,0 GB" in resultados["rodando"]["error"]
    assert "antes de começar" in resultados["na-fila"]["error"]
    # They left the journal: the next boot does not report them again.
    assert store.carregar_em_voo() == []


def test_orfaos_de_outro_processo_vivo_nao_viram_falha(store):
    """Desktop: the force-killed app leaves the old Python draining and reopening
    starts another process with the same outbox. The jobs in the journal belong to
    the old one, which still finishes them — converting them would make the true
    result be rejected."""
    fcntl = pytest.importorskip("fcntl")
    from executor import main as M

    store.registrar_em_voo("do-processo-antigo")
    store.marcar_executando("do-processo-antigo")
    with open(store._DB_PATH + ".dono", "a+b") as dono_vivo:
        fcntl.flock(dono_vivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        assert M._fechar_orfaos_do_boot_anterior() == 0

    assert store.load_pending() == []
    assert [o["job_id"] for o in store.carregar_em_voo()] == ["do-processo-antigo"]


def test_quem_subiu_sem_a_trava_assume_quando_o_outro_sai(store):
    """A holds the lock; B starts and cannot get it; A exits. If B did not try
    again, a third one (C) would grab the free lock and convert B's LIVE jobs
    into failures — the case the lock exists to prevent."""
    fcntl = pytest.importorskip("fcntl")
    a = open(store._DB_PATH + ".dono", "a+b")
    fcntl.flock(a.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    assert store.tomar_posse_do_diario() is False    # B starts with A alive
    a.close()                                         # A sai
    for _ in range(300):
        if store._trava_do_diario is not None:
            break
        time.sleep(0.01)

    assert store._trava_do_diario is not None         # B virou o dono
    with open(store._DB_PATH + ".dono", "a+b") as c:  # C starts now
        with pytest.raises(BlockingIOError):
            fcntl.flock(c.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_posse_do_diario_fica_com_o_processo(store):
    fcntl = pytest.importorskip("fcntl")

    assert store.tomar_posse_do_diario() is True
    assert store.tomar_posse_do_diario() is True   # idempotent within the same process
    with open(store._DB_PATH + ".dono", "a+b") as outro:
        with pytest.raises(BlockingIOError):
            fcntl.flock(outro.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_causa_sem_limite_de_container():
    from executor import main as M
    assert M._causa_da_interrupcao("executando", None).endswith("falta de memória na máquina.")


async def test_fila_lista_os_ativos_e_guarda_lapide():
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append((message["envelope"]["job_id"], message.get("cancel_reason")))

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    await fila.enqueue({"envelope": {"job_id": "j1"}})

    assert fila.job_ids_ativos() == ["j1"]

    await fila.encerrar_desconhecido("j9", "motivo")

    assert cancelados == [("j9", "motivo")]
    assert fila.cancelado_antes_de_chegar("j9") is True
    assert fila.cancelado_antes_de_chegar("j9") is False   # the tombstone is consumed


def _conexao_nova(result_queue=None):
    from executor.job_queue import ExecutorJobQueue

    return _conexao(ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=AsyncMock()), result_queue)


def test_resultado_enviado_ha_pouco_segue_no_inventario(store, monkeypatch):
    """`mark_sent` deletes the outbox as soon as send returns, but the server may
    not even have processed the result yet (the connection dropped right after).
    Without this memory the new session's inventory said "I don't have it" and
    the server closed the run as lost — rejecting the true result right after."""
    from executor import connection as C

    conn = _conexao_nova()
    store.put({"job_id": "j1", "status": "ok"})
    conn._lembrar_enviado("j1")
    store.mark_sent("j1")

    assert conn._montar_inventario()["resultados"] == ["j1"]

    agora = time.monotonic()
    monkeypatch.setattr(C.time, "monotonic", lambda: agora + C._ENVIADOS_TTL_S + 1)
    assert conn._montar_inventario()["resultados"] == []   # past the deadline: lost


async def test_cancel_de_job_que_acabou_de_terminar_nao_vira_cancelado(store):
    """The true result went out; a synthetic 'cancelled' on top of it could
    win in the server's consumer and erase a success."""
    conn = _conexao_nova()
    conn._lembrar_enviado("j1")

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"
    assert conn._queue.cancelado_antes_de_chegar("j1") is False   # no tombstone


async def test_cancel_com_resultado_na_fila_em_memoria_nao_vira_cancelado(store):
    fila = asyncio.Queue()
    fila.put_nowait({"job_id": "j1", "status": "ok"})
    conn = _conexao_nova(fila)

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"


async def test_outbox_ilegivel_nao_afirma_ausencia(store, monkeypatch):
    """Reading [] from a locked outbox would say "nothing pending": the server would
    close as lost runs whose result is on disk. The inventory skips the round
    and the cancel does not make up an outcome."""
    conn = _conexao_nova()
    monkeypatch.setattr(store, "_get_conn", MagicMock(side_effect=RuntimeError("database is locked")))

    assert store.job_ids_pendentes() is None
    # The inventory goes out, marked `truncado`: the server promotes and stops
    # zombies but does not close by absence — and the "speaks inventory" mark
    # does not expire (otherwise the 'pending' sweep would treat the executor as old).
    assert conn._montar_inventario()["truncado"] is True
    assert await conn._encerrar_cancelamento_desconhecido("j1") == "outbox_ilegivel"


def test_executor_movimentado_nao_desliga_a_propria_reconciliacao(store):
    """The recently sent ones only take up the space left over and do not mark
    `truncado` — at ~3 jobs/s they would fill the inventory and the server would
    never again close a lost run of this executor."""
    from executor import connection as C

    conn = _conexao_nova()
    for i in range(C._INVENTARIO_MAX + 500):
        conn._lembrar_enviado(f"j{i}")

    inventario = conn._montar_inventario()

    assert inventario["truncado"] is False
    assert len(inventario["resultados"]) == C._INVENTARIO_MAX
    assert inventario["resultados"][0] == f"j{C._INVENTARIO_MAX + 499}"   # most recent first


def test_lapide_vence(monkeypatch):
    from executor import job_queue as JQ

    fila = JQ.ExecutorJobQueue(on_execute=AsyncMock())
    fila.lapidar("j1")
    agora = time.monotonic()
    monkeypatch.setattr(JQ.time, "monotonic", lambda: agora + JQ._LAPIDE_TTL_S + 1)

    assert fila.cancelado_antes_de_chegar("j1") is False


def _conexao(fila, resultados=None):
    from executor.connection import ExecutorConnection
    return ExecutorConnection(job_queue=fila, result_queue=resultados or asyncio.Queue())


async def test_cancel_de_job_desconhecido_fecha_e_descarta_o_atrasado(store):
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append(message["envelope"]["job_id"])

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    conn = _conexao(fila)

    assert await conn._encerrar_cancelamento_desconhecido("j1") == "encerrado"
    assert cancelados == ["j1"]

    # The job arrives after the cancellation: it is discarded without running and without an ACK.
    ws = MagicMock()
    ws.send = AsyncMock()
    await conn._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert fila.job_ids_ativos() == []
    ws.send.assert_not_awaited()


async def test_cancel_de_job_que_ja_terminou_nao_mente(store):
    """Result in the outbox: the true one is on its way; no 'cancelled' on top of it."""
    from executor.job_queue import ExecutorJobQueue

    on_cancelled = AsyncMock()
    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=on_cancelled)
    store.put({"job_id": "j1", "run_id": "j1", "status": "ok"})

    assert await _conexao(fila)._encerrar_cancelamento_desconhecido("j1") == "resultado_pendente"
    on_cancelled.assert_not_awaited()


async def test_job_aceito_entra_no_diario(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    ws = MagicMock()
    ws.send = AsyncMock()

    await _conexao(fila)._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert [o["job_id"] for o in store.carregar_em_voo()] == ["j1"]


async def test_inventario_junta_ativos_outbox_e_fila_em_memoria(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    await fila.enqueue({"envelope": {"job_id": "ativo"}})
    store.put({"job_id": "no-outbox", "status": "ok"})
    memoria = asyncio.Queue()
    memoria.put_nowait({"job_id": "so-na-memoria", "status": "ok"})

    inv = _conexao(fila, memoria)._montar_inventario()

    assert inv["type"] == "inventario"
    assert inv["ativos"] == ["ativo"]
    assert inv["resultados"] == ["no-outbox", "so-na-memoria"]
    assert inv["truncado"] is False


async def test_inventario_grande_vai_marcado_truncado(store, monkeypatch):
    from executor import connection as CX
    from executor.job_queue import ExecutorJobQueue

    monkeypatch.setattr(CX, "_INVENTARIO_MAX", 2)
    fila = ExecutorJobQueue(on_execute=AsyncMock())
    for i in range(3):
        await fila.enqueue({"envelope": {"job_id": f"j{i}"}})

    inv = _conexao(fila)._montar_inventario()

    assert len(inv["ativos"]) == 2 and inv["truncado"] is True


async def test_contrato_o_inventario_do_executor_passa_no_schema_do_servidor(store):
    """Both sides of the protocol, with no mock in between: what the executor sends is
    what the server requires."""
    from app.api.routers.executor_ws.protocolo import _missing_fields
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    inv = _conexao(fila)._montar_inventario()

    assert _missing_fields(inv["type"], inv) == []
    assert ORF._ids_do_inventario(inv["ativos"]) == set()
    assert ORF._ids_do_inventario(inv["resultados"]) == set()
