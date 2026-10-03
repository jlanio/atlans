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

class _FakeRedis:
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
    async def _session():
        async with fabrica() as s:
            yield s

    monkeypatch.setattr(RES, "get_session_async", _session)
    monkeypatch.setattr(ORF, "get_session_async", _session)
    # No registered connection: the minimum interval between reconciliations does not apply.
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: None)
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
def effects(monkeypatch):
    feito = {"contabilizados": [], "publicados": [], "cancelados": [], "redis": _FakeRedis()}

    async def _account(db, run, *a, **k):
        feito["contabilizados"].append(run.task_id)

    async def _publish(run_ids, *, status, mensagem, extra=None):
        # None of these runs failed because of its content: retrying is safe.
        assert (status, extra) == ("failed", {"error_category": "transient", "retryable": True})
        feito["publicados"].extend(run_ids)

    async def _cancel(executor_id, data):
        feito["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", _account)
    monkeypatch.setattr("app.services.run_events_service.publicar_conclusao", _publish)
    monkeypatch.setattr(ORF.executor_registry, "send_json", _cancel)
    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: feito["redis"])
    return feito


async def _run(fabrica, *, status="running", host="executor:ex-1", age_min=5.0):
    run = WorkflowRun(
        id_hash=str(uuid4()), task_id=str(uuid4()), workflow_hash="wf-1",
        workspace_id="ws-1", status=status, host=host, node_stats={},
        start_time=datetime.now(timezone.utc) - timedelta(minutes=age_min),
    )
    async with fabrica() as s:
        s.add(run)
        await s.commit()
    return run.task_id


async def _row(fabrica, task_id):
    async with fabrica() as s:
        return (await s.execute(select(WorkflowRun).where(WorkflowRun.task_id == task_id))).scalar_one()


def _inventory(ativos=(), resultados=(), truncado=False):
    return {"type": "inventario", "ativos": list(ativos), "resultados": list(resultados), "truncado": truncado}


async def test_run_the_executor_lacks_is_closed_as_lost(banco, effects):
    """The titan case: connected, without the job, and the run "Em andamento"."""
    perdido = await _run(banco)

    feito = await ORF._reconciliar_inventario("ex-1", _inventory())

    assert feito["fechados"] == 1
    linha = await _row(banco, perdido)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert "não tinha mais esta execução" in linha.error_message
    assert effects["contabilizados"] == [perdido]
    assert effects["publicados"] == [perdido]


async def test_job_still_in_transit_is_not_closed_as_lost(banco, effects):
    """A send that timed out keeps draining through the socket for an indefinite
    time: with the pending ACK alive, the run is not lost — closing it would
    let the executor run, with side effects, a job of an already closed run."""
    in_transit = await _run(banco)
    effects["redis"].chegou.add(f"executor:pending_ack:{in_transit}")

    feito = await ORF._reconciliar_inventario("ex-1", _inventory())

    assert feito["fechados"] == 0
    assert (await _row(banco, in_transit)).status == "running"


async def test_run_closed_as_lost_receives_cancel(banco, effects):
    """If the job still arrives, the cancel arrives after it on the same socket and
    interrupts it — or becomes a tombstone."""
    perdido = await _run(banco)

    await ORF._reconciliar_inventario("ex-1", _inventory())
    await asyncio.gather(*ORF._cancels_in_flight)   # saem em segundo plano

    assert ("ex-1", perdido) in effects["cancelados"]


async def test_run_of_job_dropped_in_the_relay_closes_as_undelivered(banco, effects, monkeypatch):
    cleaned = []

    async def _clean(job_id, expected_executor_id=None):
        cleaned.append((job_id, expected_executor_id))

    monkeypatch.setattr(ORF.executor_registry, "clear_pending_ack", _clean)
    tid = await _run(banco, status="running")
    alheio = await _run(banco, status="running", host="executor:ex-2")
    terminou = await _run(banco, status="success")
    at_close = await _run(banco, status="running")

    assert await ORF.fechar_run_nao_entregue("ex-1", tid) is True
    assert await ORF.fechar_run_nao_entregue("ex-1", alheio) is False     # someone else's host
    assert await ORF.fechar_run_nao_entregue("ex-1", terminou) is False   # already terminal
    assert await ORF.fechar_run_nao_entregue("ex-1", at_close, connection_closing=True) is True

    linha = await _row(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "envio anterior" in linha.error_message
    # The right reason for the reader: the connection was closing, there was no queue.
    assert "sendo encerrada" in (await _row(banco, at_close)).error_message
    assert effects["contabilizados"] == [tid, at_close]
    assert effects["publicados"] == [tid, at_close]
    assert cleaned == [(tid, "ex-1"), (at_close, "ex-1")]


async def test_reconciliation_cancels_do_not_block_the_drainer(banco, effects, monkeypatch):
    """Reconciliation runs in the connection's drainer: with the socket congested,
    each inline cancel could wait its turn for the whole timeout, delaying that
    connection's job_results."""
    liberar = asyncio.Event()

    async def _slow_cancel(executor_id, data):
        await liberar.wait()
        effects["cancelados"].append((executor_id, data["job_id"]))
        return True

    monkeypatch.setattr(ORF.executor_registry, "send_json", _slow_cancel)
    perdido = await _run(banco)

    feito = await asyncio.wait_for(ORF._reconciliar_inventario("ex-1", _inventory()), timeout=2)

    assert feito["fechados"] == 1 and effects["cancelados"] == []
    liberar.set()
    await asyncio.gather(*ORF._cancels_in_flight)
    assert effects["cancelados"] == [("ex-1", perdido)]


async def test_what_the_executor_has_stays_as_is(banco, effects):
    rodando = await _run(banco)
    terminou = await _run(banco)   # result in the executor's outbox, on its way

    await ORF._reconciliar_inventario("ex-1", _inventory(ativos=[rodando], resultados=[terminou]))

    assert (await _row(banco, rodando)).status == "running"
    assert (await _row(banco, terminou)).status == "running"
    assert effects["contabilizados"] == []


async def test_recent_run_is_not_judged(banco, effects):
    """A job still in transit when the executor built the inventory is not a loss."""
    novo = await _run(banco, age_min=1)

    await ORF._reconciliar_inventario("ex-1", _inventory())

    assert (await _row(banco, novo)).status == "running"


async def test_result_just_arrived_at_the_server_protects_the_run(banco, effects):
    """The job_result has already passed through the WS (key with a 300 s TTL) and the
    consumer is still going to close the run: closing it here would erase the real outcome."""
    tid = await _run(banco)
    effects["redis"].chegou.add(f"executor:ex-1:results:{tid}")

    await ORF._reconciliar_inventario("ex-1", _inventory())

    assert (await _row(banco, tid)).status == "running"


async def test_redis_down_defers_without_closing(banco, effects, monkeypatch):
    tid = await _run(banco)

    class _BrokenRedis:
        async def mget(self, _keys):
            raise ConnectionError("redis fora")

    monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: _BrokenRedis())

    await ORF._reconciliar_inventario("ex-1", _inventory())

    assert (await _row(banco, tid)).status == "running"


async def test_pending_the_executor_lacks_becomes_undelivered(banco, effects):
    tid = await _run(banco, status="pending")

    await ORF._reconciliar_inventario("ex-1", _inventory())

    linha = await _row(banco, tid)
    assert (linha.status, linha.error_category) == ("failed", "dispatch")
    assert "não chegou a rodar" in linha.error_message


async def test_pending_the_executor_has_is_promoted(banco, effects):
    """Lost ACK: the inventory is the second proof of delivery."""
    tid = await _run(banco, status="pending", age_min=0.5)

    feito = await ORF._reconciliar_inventario("ex-1", _inventory(ativos=[tid]))

    assert feito["promovidos"] == 1
    assert (await _row(banco, tid)).status == "running"


async def test_zombie_already_closed_by_the_server_receives_cancel(banco, effects):
    """Cancelled while the executor was down: it comes back still running the job."""
    tid = await _run(banco, status="cancelled")

    feito = await ORF._reconciliar_inventario("ex-1", _inventory(ativos=[tid]))
    await asyncio.gather(*ORF._cancels_in_flight)   # saem em segundo plano

    assert feito["parados"] == 1
    assert effects["cancelados"] == [("ex-1", tid)]


async def test_truncated_inventory_does_not_close_for_absence(banco, effects):
    perdido = await _run(banco)
    pendente = await _run(banco, status="pending", age_min=0.5)

    feito = await ORF._reconciliar_inventario(
        "ex-1", _inventory(ativos=[pendente], truncado=True),
    )

    assert feito["fechados"] == 0
    assert (await _row(banco, perdido)).status == "running"
    assert (await _row(banco, pendente)).status == "running"   # promover continua valendo


async def test_runs_of_another_executor_are_not_touched(banco, effects):
    alheio = await _run(banco, host="executor:ex-2")
    foreign_pending = await _run(banco, host="executor:ex-2", status="pending", age_min=0.5)

    await ORF._reconciliar_inventario("ex-1", _inventory(ativos=[foreign_pending]))

    assert (await _row(banco, alheio)).status == "running"
    assert (await _row(banco, foreign_pending)).status == "pending"


async def test_malformed_inventory_is_ignored(banco, effects):
    tid = await _run(banco)

    assert await ORF._reconciliar_inventario("ex-1", {"type": "inventario", "ativos": "tudo"}) == {}
    assert (await _row(banco, tid)).status == "running"


async def test_minimum_interval_between_reconciliations(banco, effects, monkeypatch):
    """A buggy executor does not turn the inventory into one SELECT per message."""
    conn = SimpleNamespace(
        ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    await _run(banco)

    primeira = await ORF._reconciliar_inventario("ex-1", _inventory())
    segunda = await ORF._reconciliar_inventario("ex-1", _inventory())

    assert primeira["fechados"] == 1
    assert segunda == {}


async def test_freshly_opened_connection_does_not_close_for_absence(banco, effects, monkeypatch):
    """Reconnection: the PREVIOUS connection's inbox may still be draining the
    job_result of a run that finished before the drop. The new session's first
    inventory does not list it — closing now would make the true result be
    rejected right after. Promoting and stopping zombies do not wait."""
    conn = SimpleNamespace(ultima_reconciliacao=0.0, connected_at=datetime.now(timezone.utc))
    monkeypatch.setattr(ORF.executor_registry, "get", lambda _eid: conn)
    finished_before_the_crash = await _run(banco)
    na_fila = await _run(banco, status="pending")

    feito = await ORF._reconciliar_inventario("ex-1", _inventory(ativos=[na_fila]))

    assert feito == {"promovidos": 1, "parados": 0, "fechados": 0}
    assert (await _row(banco, finished_before_the_crash)).status == "running"
    assert (await _row(banco, na_fila)).status == "running"


async def test_inventory_goes_through_the_drainer_after_job_result(monkeypatch):
    """On the same queue: the job_result sent before the inventory is written before
    the inventory is checked — otherwise the just-finished run would look lost."""
    ordem = []

    async def _resultado(executor_id, msg, frame_bytes=0, **_kw):
        ordem.append(("job_result", msg["job_id"]))

    async def _reconcile(executor_id, msg):
        ordem.append(("inventario", tuple(msg["ativos"])))

    monkeypatch.setattr(IB, "_handle_job_result", _resultado)
    monkeypatch.setattr(IB, "_reconciliar_inventario", _reconcile)
    inbox = IB._InboxQueue(maxsize=10)
    inbox.put_nowait(("job_result", {"job_id": "j1"}, 10))
    inbox.put_nowait(("inventario", _inventory(), 10))
    inbox.put_nowait(IB._INBOX_STOP)

    await IB._drain_inbox("ex-1", inbox)

    assert ordem == [("job_result", "j1"), ("inventario", ())]


async def test_inventory_with_full_queue_is_discarded(monkeypatch):
    """Periodic: the next one arrives in a minute; back-pressure is not worth it."""
    chamado = []
    monkeypatch.setattr(IB, "_reconciliar_inventario", lambda *a: chamado.append(a))
    inbox = IB._InboxQueue(maxsize=1)
    inbox.put_nowait(("job_result", {"job_id": "x"}, 10))
    descartes = IB._new_drop_counter()

    await IB._enfileirar_mensagem("ex-1", inbox, descartes, "inventario", _inventory(), 10)

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


async def test_different_late_outcome_does_not_overwrite_the_first(monkeypatch):
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


async def test_real_result_corrects_the_outcome_the_server_inferred(monkeypatch):
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


async def test_user_cancellation_is_not_undone_by_late_result(monkeypatch):
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="cancelled", node_stats={})
    grava = AsyncMock()
    monkeypatch.setattr(rrc, "_update_run_status", grava)

    assert await rrc._process_result(_db_do_consumer(run), _payload("success")) is True

    grava.assert_not_awaited()


async def test_orphan_does_not_overwrite_result_written_in_between(banco, effects, monkeypatch):
    """Between the SELECT of the orphans and the commit, the consumer wrote the true
    result. The ORM's UPDATE by PK overwrote it with 'failed' — and usage was
    counted twice."""
    from sqlalchemy import update as sa_update

    run_id = await _run(banco)
    real = ORF.get_session_async

    @asynccontextmanager
    async def _with_race():
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

    monkeypatch.setattr(ORF, "get_session_async", _with_race)

    await ORF._fail_orphan_runs("ex-1")

    assert (await _row(banco, run_id)).status == "success"
    assert effects["contabilizados"] == [] and effects["publicados"] == []


async def test_orphan_closes_the_run_left_running(banco, effects):
    run_id = await _run(banco)

    await ORF._fail_orphan_runs("ex-1")

    linha = await _row(banco, run_id)
    assert (linha.status, linha.error_category) == ("failed", "executor_lost")
    assert linha.duration_seconds and linha.duration_seconds > 0
    assert effects["contabilizados"] == [run_id] and effects["publicados"] == [run_id]


async def test_redelivery_of_the_same_outcome_works_as_before(monkeypatch):
    """Reprocessed dead letter: the phases run again, without recounting usage."""
    from app.core import run_result_consumer as rrc

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws",
                      status="success", node_stats={})
    grava = AsyncMock()
    chamadas = []

    async def _phase(db, run, task_id, label, fn, *args):
        chamadas.append((label, args[-1] if label == "uso diario" else None))
        return rrc.PHASE_OK

    monkeypatch.setattr(rrc, "_update_run_status", grava)
    monkeypatch.setattr(rrc, "_run_phase", _phase)

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


async def test_cancel_with_the_executor_offline_closes_on_the_server():
    """It used to be a 503 and the lost run had no way to be cleaned up from the screen."""
    from app.services import workflow_execution_service as wes

    run = WorkflowRun(task_id="run-1", workflow_hash="wf", workspace_id="ws", status="running",
                      host="executor:ex-1", node_stats={})
    db = _mock_db(_select(run), MagicMock(rowcount=1))

    with patch.object(wes, "executor_registry") as reg, \
         patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()) as account_terminal:
        reg.send_json = AsyncMock(return_value=False)
        reg.presence_or_unknown = AsyncMock(return_value=False)
        outcome = await wes.cancel_run(db, "run-1", user_id="u", como_admin=True)

    assert outcome == "cancelled"
    assert run.status == "cancelled"
    assert "fora do ar" in run.error_message
    account_terminal.assert_awaited_once()
    # Conditional: a job_result that arrives in the middle wins.
    sql = str(db.execute.await_args_list[-1].args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "status IN ('pending', 'running')" in sql


async def test_offline_cancel_loses_to_the_result_that_arrived():
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


def test_accepted_job_stays_in_the_journal_until_the_result(store):
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
    assert store.carregar_em_voo()[0]["estado"] == store.STATE_RUNNING
    assert store.job_ids_pendentes() == ["j1"]


def test_outbox_keeps_the_category_for_replay(store):
    store.put({"job_id": "j1", "status": "error", "error": "x", "error_category": "executor_lost"})
    assert store.load_pending()[0]["error_category"] == "executor_lost"


def test_boot_orphan_becomes_failure_with_the_cause(store, monkeypatch):
    """The OOM case: killed midway, the executor comes back and reports what it lost."""
    from executor import main as M

    monkeypatch.setattr("executor.sysinfo._get_cgroup_ram_total", lambda: 2 * 1024 ** 3)
    store.registrar_em_voo("rodando")
    store.marcar_executando("rodando")
    store.registrar_em_voo("na-fila")

    assert M._close_previous_boot_orphans() == 2

    resultados = {r["job_id"]: r for r in store.load_pending()}
    assert resultados["rodando"]["status"] == "error"
    assert resultados["rodando"]["error_category"] == "executor_lost"
    assert "no meio desta execução" in resultados["rodando"]["error"]
    assert "2,0 GB" in resultados["rodando"]["error"]
    assert "antes de começar" in resultados["na-fila"]["error"]
    # They left the journal: the next boot does not report them again.
    assert store.carregar_em_voo() == []


def test_orphans_of_another_live_process_do_not_become_failures(store):
    """Desktop: the force-killed app leaves the old Python draining and reopening
    starts another process with the same outbox. The jobs in the journal belong to
    the old one, which still finishes them — converting them would make the true
    result be rejected."""
    fcntl = pytest.importorskip("fcntl")
    from executor import main as M

    store.registrar_em_voo("do-processo-antigo")
    store.marcar_executando("do-processo-antigo")
    with open(store._DB_PATH + ".dono", "a+b") as live_owner:
        fcntl.flock(live_owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        assert M._close_previous_boot_orphans() == 0

    assert store.load_pending() == []
    assert [o["job_id"] for o in store.carregar_em_voo()] == ["do-processo-antigo"]


def test_whoever_started_without_the_lock_takes_over_when_the_other_exits(store):
    """A holds the lock; B starts and cannot get it; A exits. If B did not try
    again, a third one (C) would grab the free lock and convert B's LIVE jobs
    into failures — the case the lock exists to prevent."""
    fcntl = pytest.importorskip("fcntl")
    a = open(store._DB_PATH + ".dono", "a+b")
    fcntl.flock(a.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    assert store.take_journal_ownership() is False    # B starts with A alive
    a.close()                                         # A sai
    for _ in range(300):
        if store._trava_do_diario is not None:
            break
        time.sleep(0.01)

    assert store._trava_do_diario is not None         # B virou o dono
    with open(store._DB_PATH + ".dono", "a+b") as c:  # C starts now
        with pytest.raises(BlockingIOError):
            fcntl.flock(c.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_journal_ownership_stays_with_the_process(store):
    fcntl = pytest.importorskip("fcntl")

    assert store.take_journal_ownership() is True
    assert store.take_journal_ownership() is True   # idempotent within the same process
    with open(store._DB_PATH + ".dono", "a+b") as outro:
        with pytest.raises(BlockingIOError):
            fcntl.flock(outro.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_cause_without_container_limit():
    from executor import main as M
    assert M._interruption_cause("executando", None).endswith("falta de memória na máquina.")


async def test_queue_lists_the_active_and_keeps_tombstone():
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append((message["envelope"]["job_id"], message.get("cancel_reason")))

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    await fila.enqueue({"envelope": {"job_id": "j1"}})

    assert fila.active_job_ids() == ["j1"]

    await fila.close_unknown("j9", "motivo")

    assert cancelados == [("j9", "motivo")]
    assert fila.cancelled_before_arrival("j9") is True
    assert fila.cancelled_before_arrival("j9") is False   # the tombstone is consumed


def _new_connection(result_queue=None):
    from executor.job_queue import ExecutorJobQueue

    return _connection(ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=AsyncMock()), result_queue)


def test_recently_sent_result_stays_in_the_inventory(store, monkeypatch):
    """`mark_sent` deletes the outbox as soon as send returns, but the server may
    not even have processed the result yet (the connection dropped right after).
    Without this memory the new session's inventory said "I don't have it" and
    the server closed the run as lost — rejecting the true result right after."""
    from executor import connection as C

    conn = _new_connection()
    store.put({"job_id": "j1", "status": "ok"})
    conn._remember_sent("j1")
    store.mark_sent("j1")

    assert conn._build_inventory()["resultados"] == ["j1"]

    agora = time.monotonic()
    monkeypatch.setattr(C.time, "monotonic", lambda: agora + C._SENT_TTL_S + 1)
    assert conn._build_inventory()["resultados"] == []   # past the deadline: lost


async def test_cancel_of_job_that_just_finished_does_not_become_cancelled(store):
    """The true result went out; a synthetic 'cancelled' on top of it could
    win in the server's consumer and erase a success."""
    conn = _new_connection()
    conn._remember_sent("j1")

    assert await conn._close_unknown_cancellation("j1") == "resultado_pendente"
    assert conn._queue.cancelled_before_arrival("j1") is False   # no tombstone


async def test_cancel_with_result_in_the_in_memory_queue_does_not_become_cancelled(store):
    fila = asyncio.Queue()
    fila.put_nowait({"job_id": "j1", "status": "ok"})
    conn = _new_connection(fila)

    assert await conn._close_unknown_cancellation("j1") == "resultado_pendente"


async def test_unreadable_outbox_does_not_assert_absence(store, monkeypatch):
    """Reading [] from a locked outbox would say "nothing pending": the server would
    close as lost runs whose result is on disk. The inventory skips the round
    and the cancel does not make up an outcome."""
    conn = _new_connection()
    monkeypatch.setattr(store, "_get_conn", MagicMock(side_effect=RuntimeError("database is locked")))

    assert store.job_ids_pendentes() is None
    # The inventory goes out, marked `truncado`: the server promotes and stops
    # zombies but does not close by absence — and the "speaks inventory" mark
    # does not expire (otherwise the 'pending' sweep would treat the executor as old).
    assert conn._build_inventory()["truncado"] is True
    assert await conn._close_unknown_cancellation("j1") == "outbox_ilegivel"


def test_busy_executor_does_not_disable_its_own_reconciliation(store):
    """The recently sent ones only take up the space left over and do not mark
    `truncado` — at ~3 jobs/s they would fill the inventory and the server would
    never again close a lost run of this executor."""
    from executor import connection as C

    conn = _new_connection()
    for i in range(C._INVENTARIO_MAX + 500):
        conn._remember_sent(f"j{i}")

    inventario = conn._build_inventory()

    assert inventario["truncado"] is False
    assert len(inventario["resultados"]) == C._INVENTARIO_MAX
    assert inventario["resultados"][0] == f"j{C._INVENTARIO_MAX + 499}"   # most recent first


def test_tombstone_expires(monkeypatch):
    from executor import job_queue as JQ

    fila = JQ.ExecutorJobQueue(on_execute=AsyncMock())
    fila.add_tombstone("j1")
    agora = time.monotonic()
    monkeypatch.setattr(JQ.time, "monotonic", lambda: agora + JQ._TOMBSTONE_TTL_S + 1)

    assert fila.cancelled_before_arrival("j1") is False


def _connection(fila, resultados=None):
    from executor.connection import ExecutorConnection
    return ExecutorConnection(job_queue=fila, result_queue=resultados or asyncio.Queue())


async def test_cancel_of_unknown_job_closes_and_discards_the_late_one(store):
    from executor.job_queue import ExecutorJobQueue

    cancelados = []

    async def _on_cancelled(message):
        cancelados.append(message["envelope"]["job_id"])

    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=_on_cancelled)
    conn = _connection(fila)

    assert await conn._close_unknown_cancellation("j1") == "encerrado"
    assert cancelados == ["j1"]

    # The job arrives after the cancellation: it is discarded without running and without an ACK.
    ws = MagicMock()
    ws.send = AsyncMock()
    await conn._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert fila.active_job_ids() == []
    ws.send.assert_not_awaited()


async def test_cancel_of_job_already_finished_does_not_lie(store):
    """Result in the outbox: the true one is on its way; no 'cancelled' on top of it."""
    from executor.job_queue import ExecutorJobQueue

    on_cancelled = AsyncMock()
    fila = ExecutorJobQueue(on_execute=AsyncMock(), on_cancelled=on_cancelled)
    store.put({"job_id": "j1", "run_id": "j1", "status": "ok"})

    assert await _connection(fila)._close_unknown_cancellation("j1") == "resultado_pendente"
    on_cancelled.assert_not_awaited()


async def test_accepted_job_enters_the_journal(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    ws = MagicMock()
    ws.send = AsyncMock()

    await _connection(fila)._handle_job(ws, {"envelope": {"job_id": "j1"}})

    assert [o["job_id"] for o in store.carregar_em_voo()] == ["j1"]


async def test_inventory_merges_active_outbox_and_in_memory_queue(store):
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    await fila.enqueue({"envelope": {"job_id": "ativo"}})
    store.put({"job_id": "no-outbox", "status": "ok"})
    memoria = asyncio.Queue()
    memoria.put_nowait({"job_id": "so-na-memoria", "status": "ok"})

    inv = _connection(fila, memoria)._build_inventory()

    assert inv["type"] == "inventario"
    assert inv["ativos"] == ["ativo"]
    assert inv["resultados"] == ["no-outbox", "so-na-memoria"]
    assert inv["truncado"] is False


async def test_large_inventory_is_marked_truncated(store, monkeypatch):
    from executor import connection as CX
    from executor.job_queue import ExecutorJobQueue

    monkeypatch.setattr(CX, "_INVENTARIO_MAX", 2)
    fila = ExecutorJobQueue(on_execute=AsyncMock())
    for i in range(3):
        await fila.enqueue({"envelope": {"job_id": f"j{i}"}})

    inv = _connection(fila)._build_inventory()

    assert len(inv["ativos"]) == 2 and inv["truncado"] is True


async def test_contract_the_executor_inventory_passes_the_server_schema(store):
    """Both sides of the protocol, with no mock in between: what the executor sends is
    what the server requires."""
    from app.api.routers.executor_ws.protocolo import _missing_fields
    from executor.job_queue import ExecutorJobQueue

    fila = ExecutorJobQueue(on_execute=AsyncMock())
    inv = _connection(fila)._build_inventory()

    assert _missing_fields(inv["type"], inv) == []
    assert ORF._inventory_ids(inv["ativos"]) == set()
    assert ORF._inventory_ids(inv["resultados"]) == set()
