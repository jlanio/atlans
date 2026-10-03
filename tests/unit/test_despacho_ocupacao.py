# tests/unit/test_despacho_ocupacao.py
"""
Order of candidates in the dispatch (`_executor_states`/`_sort_key`/
`_sorted_eligible` in workflow_execution_service).

Before, the load came only from the `capacity` the executor sends every 10 s,
and only in the API worker that holds its WebSocket: in the other workers the
executor counted as zero, and in a burst all jobs went to whoever was empty in
the last report. With the pool idle, the tie fell to database order — the first
executor took everything.

  - The load is the one COUNTED by the server (the host's `pending`/`running`
    runs in the database), in a query isolated by a SAVEPOINT on the
    connection. The declared one (local or published in Redis) only comes in
    when the count fails, and to tell whether the executor is full.
  - With a free slot: a draw weighted by free slots — simultaneous decisions
    spread out. No slot: lowest occupancy relative to slots.
    Full ones (by the report or by the count): last.
"""
from __future__ import annotations

import collections
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core import executor_connections as ec
from app.models.workflow_run import WorkflowRun
from app.services import workflow_execution_service as wes

from ._mcp_harness import FakeRedis, in_memory_db


# ── Factories ─────────────────────────────────────────────────────────────────

def _executor(id_hash, *, vagas=4, fila=50):
    return SimpleNamespace(
        id_hash=id_hash, name=id_hash, status="active", public_key="PEM",
        max_concurrent_jobs=vagas, max_queue_size=fila,
    )


def _capacity(running=0, queued=0, max_concurrent=4, max_queue=50):
    return {"running": running, "queued": queued,
            "max_concurrent": max_concurrent, "max_queue": max_queue}


def _registro(declaradas=None):
    """Fake registry: all present; the declared capacity comes from the dict
    (absent = never declared), and `send_job` accepts everything and records the chosen one."""
    declaradas = declaradas or {}
    reg = MagicMock()
    reg.presence_or_unknown = AsyncMock(return_value=True)

    async def _read_capacities(ids):
        return {i: (dict(declaradas[i]) if declaradas.get(i) else None) for i in ids}

    reg.read_capacities = AsyncMock(side_effect=_read_capacities)
    reg.escolhidos = []

    async def _send_job(executor_id, job_msg):
        reg.escolhidos.append(executor_id)
        return True

    reg.send_job = AsyncMock(side_effect=_send_job)
    reg.send_json = AsyncMock(return_value=True)
    return reg


def _wf():
    wf = MagicMock()
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = wf.pin_metadata = None
    return wf


async def _runs(fabrica, executor_id, status, n):
    async with fabrica() as db:
        for _ in range(n):
            db.add(WorkflowRun(
                task_id=str(uuid4()), workflow_hash="wf-1", workspace_id="ws-1",
                status=status, host=f"executor:{executor_id}",
            ))
        await db.commit()


def _ids_in_order(candidatos):
    return [c.id_hash for c in candidatos]


def _db_error(*, connection_lost=False):
    return OperationalError(
        "SELECT host, count(*) ...", {}, Exception("lock timeout"),
        connection_invalidated=connection_lost,
    )


def _fake_session(execute):
    """Session whose connection records the savepoint and runs `execute` on the query."""
    eventos: list[str] = []

    class _Savepoint:
        async def __aenter__(self):
            eventos.append("SAVEPOINT")

        async def __aexit__(self, tipo, *_):
            eventos.append("ROLLBACK TO SAVEPOINT" if tipo else "RELEASE SAVEPOINT")
            return False

    async def _execute(consulta):
        eventos.append("SELECT")
        return await execute(consulta)

    conexao = MagicMock()
    conexao.begin_nested = MagicMock(side_effect=lambda: _Savepoint())
    conexao.execute = AsyncMock(side_effect=_execute)
    db = MagicMock()
    db.connection = AsyncMock(return_value=conexao)
    return db, eventos


@pytest.fixture
async def fabrica():
    async with in_memory_db() as f:
        yield f


@pytest.fixture
def estavel():
    """Draw fixed at 0.5, for the exact-order assertions: with slots, whoever has
    more free slots comes first; a tie stays in input order."""
    with patch.object(wes, "_desempate", lambda: 0.5):
        yield


async def _sorted_ids(fabrica, reg, pool):
    async with fabrica() as db:
        with patch.object(wes, "executor_registry", reg):
            return _ids_in_order(await wes._sorted_eligible(db, pool))


# ══════════════════════════════════════════════════════════════════════════════
# The load that orders
# ══════════════════════════════════════════════════════════════════════════════

class TestLoad:
    @pytest.mark.asyncio
    async def test_server_counted_beats_stale_declared(self, fabrica, estavel):
        # A declared 0 in the last report, but the server has already dispatched 3 to it.
        await _runs(fabrica, "A", "running", 3)
        reg = _registro({"A": _capacity(), "B": _capacity()})
        assert await _sorted_ids(fabrica, reg, [_executor("A"), _executor("B")]) == ["B", "A"]

    @pytest.mark.asyncio
    async def test_stale_declared_does_not_inflate_the_load(self, fabrica, estavel):
        # A's last report (up to 10 s ago) said 3 running; they have already
        # finished — the database shows none. B really has 1. By the larger
        # of the two, A looked busier than B.
        await _runs(fabrica, "B", "running", 1)
        reg = _registro({"A": _capacity(running=3), "B": _capacity()})
        assert await _sorted_ids(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_declared_and_counted_do_not_add_up(self, fabrica, estavel):
        # The common case: report and database see the SAME 2 jobs of A. Added up,
        # A would look full (4 of 4) and lose to B, which has 3.
        await _runs(fabrica, "A", "running", 2)
        await _runs(fabrica, "B", "running", 3)
        reg = _registro({"A": _capacity(running=2), "B": _capacity()})
        assert await _sorted_ids(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_pending_counts_and_terminal_does_not(self, fabrica, estavel):
        # The dispatch INSERT writes `pending` with the host: it already occupies.
        # Finished runs occupy no one.
        await _runs(fabrica, "A", "pending", 2)
        for status in ("success", "failed", "cancelled"):
            await _runs(fabrica, "B", status, 5)
        assert await _sorted_ids(fabrica, _registro(), [_executor("A"), _executor("B")]) == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# Full ones go last
# ══════════════════════════════════════════════════════════════════════════════

class TestFull:
    @pytest.mark.asyncio
    async def test_full_by_declared_goes_last(self, fabrica, estavel):
        # While draining, the executor announces itself as full to get out of the
        # way (queued = queue ceiling + concurrency), with no run in the database.
        # By relative occupancy (59/8) it got ahead of a 1-slot executor with 8
        # jobs (9/1) — and was tried only for send_job to refuse.
        drenando = _capacity(running=0, queued=50 + 8, max_concurrent=8)
        await _runs(fabrica, "pequeno", "running", 8)
        reg = _registro({"drenando": drenando, "pequeno": _capacity(max_concurrent=1)})
        ordem = await _sorted_ids(fabrica, reg, [_executor("drenando", vagas=8), _executor("pequeno", vagas=1)])
        assert ordem == ["pequeno", "drenando"]

    @pytest.mark.asyncio
    async def test_queue_full_by_count_goes_last(self, fabrica):
        # The report of "grande" (16 slots, queue 50) is up to 10 s old and still
        # says 56 of 66 — but the server has already dispatched 66 to it: its
        # local queue is full, and the next job would be REFUSED by it after the
        # send had been accepted — a failed run, no failover. "pequeno" has 16
        # of 54. By relative occupancy (67/16 < 17/4), "grande" came first, and
        # stayed first with every failed run. No fixed draw: it is not luck.
        await _runs(fabrica, "grande", "running", 66)
        await _runs(fabrica, "pequeno", "running", 16)
        reg = _registro({
            "grande": _capacity(running=16, queued=40, max_concurrent=16),
            "pequeno": _capacity(running=4, queued=12),
        })
        pool = [_executor("grande", vagas=16), _executor("pequeno")]
        for _ in range(50):
            assert await _sorted_ids(fabrica, reg, pool) == ["pequeno", "grande"]

    @pytest.mark.asyncio
    async def test_executor_on_another_worker_full_by_redis_capacity(
        self, fabrica, estavel, monkeypatch,
    ):
        # The REAL registry: "local" has its WebSocket in this worker; "remoto" is
        # in another, and its report (full) only exists in Redis. Before, from
        # here, "remoto" counted as zero. The read is a single Redis trip (MGET).
        redis = FakeRedis()
        await redis.set(ec._capacity_key("remoto"), json.dumps(_capacity(running=4, queued=50)))

        async def _get_redis():
            return redis

        monkeypatch.setattr(ec, "_get_redis", _get_redis)
        reg = ec.ExecutorConnectionRegistry()
        reg._connections["local"] = SimpleNamespace(capacity=_capacity(running=1))
        reg.presence_or_unknown = AsyncMock(return_value=True)

        assert await _sorted_ids(fabrica, reg, [_executor("remoto"), _executor("local")]) == ["local", "remoto"]
        leituras = [c for c in redis.chamadas if c[0] in ("get", "mget")]
        assert leituras == [("mget", (ec._capacity_key("remoto"),))]


# ══════════════════════════════════════════════════════════════════════════════
# Vagas e fila
# ══════════════════════════════════════════════════════════════════════════════

class TestSlots:
    @pytest.mark.asyncio
    async def test_with_slots_the_one_with_more_free_slots_goes_first(self, fabrica, estavel):
        # 4 jobs in 8 slots leave 4 free; 1 in 2 leaves 1. The draw is weighted
        # 4:1 — without the fixed draw, "pequeno" still comes out ahead 1 time
        # in 5, and that is what spreads simultaneous decisions.
        await _runs(fabrica, "grande", "running", 4)
        await _runs(fabrica, "pequeno", "running", 1)
        reg = _registro({
            "grande": _capacity(max_concurrent=8),
            "pequeno": _capacity(max_concurrent=2),
        })
        ordem = await _sorted_ids(fabrica, reg, [_executor("pequeno", vagas=2), _executor("grande", vagas=8)])
        assert ordem == ["grande", "pequeno"]

    @pytest.mark.asyncio
    async def test_with_no_slots_anywhere_goes_to_the_smallest_relative_queue(self, fabrica, estavel):
        # Both full: the job will wait. 12 jobs in 8 slots (4 queued for 8
        # running) move faster than 3 in 2 (1 queued for 2) — by the absolute
        # count (3 < 12) the job went to the small one.
        await _runs(fabrica, "grande", "running", 12)
        await _runs(fabrica, "pequeno", "running", 3)
        reg = _registro({
            "grande": _capacity(max_concurrent=8),
            "pequeno": _capacity(max_concurrent=2),
        })
        ordem = await _sorted_ids(fabrica, reg, [_executor("pequeno", vagas=2), _executor("grande", vagas=8)])
        assert ordem == ["grande", "pequeno"]

    @pytest.mark.asyncio
    async def test_declared_slots_below_the_db_ceiling_apply(self, fabrica, estavel):
        # The database allows 8, but the executor starts with EXECUTOR_MAX_CONCURRENT=2:
        # with 1 job it is at half, not at one eighth.
        await _runs(fabrica, "A", "running", 1)
        await _runs(fabrica, "B", "running", 2)
        reg = _registro({"A": _capacity(max_concurrent=2), "B": _capacity(max_concurrent=4)})
        ordem = await _sorted_ids(fabrica, reg, [_executor("A", vagas=8), _executor("B", vagas=4)])
        assert ordem == ["B", "A"]

    @pytest.mark.asyncio
    async def test_slots_do_not_exceed_the_db_ceiling(self, fabrica, estavel):
        # Before the first `capacity`, the worker holding the WebSocket has a
        # provisional value (4). The registration's ceiling is 1: with 1 job, A
        # is full — in every worker, not only in those without the WebSocket.
        await _runs(fabrica, "A", "running", 1)
        await _runs(fabrica, "B", "running", 2)
        reg = _registro({"A": _capacity(max_concurrent=4), "B": _capacity(max_concurrent=4)})
        ordem = await _sorted_ids(fabrica, reg, [_executor("A", vagas=1), _executor("B", vagas=4)])
        assert ordem == ["B", "A"]

    @pytest.mark.asyncio
    async def test_without_declared_capacity_slots_come_from_the_db(self, fabrica, estavel):
        # Never sent `capacity`: the registration's ceiling applies.
        await _runs(fabrica, "A", "running", 2)
        await _runs(fabrica, "B", "running", 2)
        ordem = await _sorted_ids(fabrica, _registro(), [_executor("A", vagas=2), _executor("B", vagas=8)])
        assert ordem == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# Bursts: the real dispatch, with each run's INSERT in the database
# ══════════════════════════════════════════════════════════════════════════════

async def _burst(fabrica, reg, pool, n):
    """Dispatches `n` jobs in sequence through the real `_dispatch_job`. The
    declared capacity stays frozen (the 10 s report does not arrive midway)."""
    wf, definicao = _wf(), {"nodes": [], "edges": []}
    with patch.object(wes, "executor_registry", reg), \
         patch.object(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **_: d)), \
         patch.object(wes, "build_job_message", MagicMock(return_value={"envelope": {}})):
        for _ in range(n):
            async with fabrica() as db:
                candidatos = await wes._sorted_eligible(db, pool)
                await wes._dispatch_job(wf, definicao, candidatos, {}, False, db=db)
    return collections.Counter(reg.escolhidos)


class TestBurst:
    @pytest.mark.asyncio
    async def test_burst_splits_across_idle_executors(self, fabrica):
        # Before: 30 jobs, 30 to the first in the database.
        reg = _registro({e: _capacity() for e in ("A", "B", "C")})
        pool = [_executor("A"), _executor("B"), _executor("C")]
        recebidos = await _burst(fabrica, reg, pool, 30)
        assert recebidos == {"A": 10, "B": 10, "C": 10}

    @pytest.mark.asyncio
    async def test_burst_follows_the_slot_ratio(self, fabrica, estavel):
        reg = _registro({
            "grande": _capacity(max_concurrent=8),
            "pequeno": _capacity(max_concurrent=2),
        })
        pool = [_executor("grande", vagas=8), _executor("pequeno", vagas=2)]
        recebidos = await _burst(fabrica, reg, pool, 10)
        assert recebidos == {"grande": 8, "pequeno": 2}

    @pytest.mark.asyncio
    async def test_burst_in_mixed_pool_overflows_no_queue(self, fabrica, estavel):
        # 16 slots + queue 50 (66 fit) and 4 slots + queue 50 (54 fit), report
        # frozen at zero. By relative occupancy, "grande" got ~4 jobs for every
        # 1 of "pequeno" and went past 66 before "pequeno" reached half — each
        # excess one a failed run in its local queue.
        reg = _registro({
            "grande": _capacity(max_concurrent=16),
            "pequeno": _capacity(max_concurrent=4),
        })
        pool = [_executor("grande", vagas=16), _executor("pequeno", vagas=4)]
        recebidos = await _burst(fabrica, reg, pool, 110)
        assert recebidos["grande"] <= 66 and recebidos["pequeno"] <= 54
        assert sum(recebidos.values()) == 110

    @pytest.mark.asyncio
    async def test_finished_run_frees_the_slot(self, fabrica, estavel):
        # A and B with one job each; A's finishes — the next goes to A.
        reg = _registro({e: _capacity() for e in ("A", "B")})
        pool = [_executor("A"), _executor("B")]
        await _burst(fabrica, reg, pool, 2)
        async with fabrica() as db:
            run_de_a = (await db.execute(
                select(WorkflowRun).where(WorkflowRun.host == "executor:A")
            )).scalar_one()
            run_de_a.status = "success"
            await db.commit()
        reg.escolhidos.clear()
        recebidos = await _burst(fabrica, reg, [_executor("B"), _executor("A")], 1)
        assert recebidos == {"A": 1}


# ══════════════════════════════════════════════════════════════════════════════
# Sorteio
# ══════════════════════════════════════════════════════════════════════════════

class TestDraw:
    @pytest.mark.asyncio
    async def test_tie_is_drawn_at_random(self, fabrica):
        # With the pool idle, any of them can be first — no longer always the
        # first in the database. 300 draws among 3: the chance of one of them
        # never leading is negligible (~3·(2/3)^300).
        reg = _registro({e: _capacity() for e in ("A", "B", "C")})
        pool = [_executor("A"), _executor("B"), _executor("C")]
        primeiros = collections.Counter()
        async with fabrica() as db:
            with patch.object(wes, "executor_registry", reg):
                for _ in range(300):
                    primeiros[(await wes._sorted_eligible(db, pool))[0].id_hash] += 1
        assert set(primeiros) == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_simultaneous_decisions_spread_out(self, fabrica):
        # Several dispatches at the same time start from the SAME snapshot: no INSERT
        # between them. With the strict minimum, all went to A. Now each one
        # draws by free slots (A 4, B 3, C 3): expected ~40/30/30%.
        await _runs(fabrica, "B", "running", 1)
        await _runs(fabrica, "C", "running", 1)
        pool = [_executor("A"), _executor("B"), _executor("C")]
        primeiros = collections.Counter()
        async with fabrica() as db:
            with patch.object(wes, "executor_registry", _registro()):
                for _ in range(300):
                    primeiros[(await wes._sorted_eligible(db, pool))[0].id_hash] += 1
        # Margins of at least 5 standard deviations: this is not a random-generator test.
        assert 60 <= primeiros["A"] <= 180
        assert primeiros["B"] >= 45 and primeiros["C"] >= 45

    @pytest.mark.asyncio
    async def test_without_slot_never_goes_ahead_of_one_with_slot(self, fabrica):
        # The draw only applies among those with a free slot: a full A (4 of 4) never
        # comes before B with one slot, however much the draw favors A.
        await _runs(fabrica, "A", "running", 4)
        await _runs(fabrica, "B", "running", 3)
        for _ in range(50):
            assert await _sorted_ids(fabrica, _registro(), [_executor("A"), _executor("B")]) == ["B", "A"]


# ══════════════════════════════════════════════════════════════════════════════
# A consulta ao banco: savepoint, falhas e atalhos
# ══════════════════════════════════════════════════════════════════════════════

class TestQuery:
    @pytest.mark.asyncio
    async def test_single_candidate_does_not_query_load(self):
        db = MagicMock()
        db.connection = AsyncMock()
        reg = _registro()
        with patch.object(wes, "executor_registry", reg):
            ordem = await wes._sorted_eligible(db, [_executor("A"), _executor("B")], excluir={"B"})
        assert _ids_in_order(ordem) == ["A"]
        db.connection.assert_not_awaited()
        reg.read_capacities.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_failing_db_orders_by_declared_load_in_a_savepoint(self, estavel):
        # On Postgres, an error in this query would abort the request's transaction
        # and the run's INSERT would fail right after. The savepoint — on the
        # CONNECTION, not the session — isolates the failure; the ordering falls
        # back to the declared load.
        async def _falha(_query):
            raise _db_error()

        db, eventos = _fake_session(_falha)
        reg = _registro({"A": _capacity(running=3), "B": _capacity()})
        with patch.object(wes, "executor_registry", reg), \
             patch.object(wes._logger, "warning") as aviso:
            ordem = await wes._sorted_eligible(db, [_executor("A"), _executor("B")])
        assert eventos == ["SAVEPOINT", "SELECT", "ROLLBACK TO SAVEPOINT"]
        assert _ids_in_order(ordem) == ["B", "A"]
        assert "Carga contada pelo servidor indisponível" in aviso.call_args.args[0]
        db.begin_nested.assert_not_called()

    @pytest.mark.asyncio
    async def test_lost_connection_propagates(self):
        # An invalidated connection is not degradation: the INSERT further on would
        # fail anyway, and with "Can't reconnect until invalid transaction is
        # rolled back" in place of the real error.
        async def _falha(_query):
            raise _db_error(connection_lost=True)

        db, _ = _fake_session(_falha)
        with patch.object(wes, "executor_registry", _registro()), pytest.raises(OperationalError):
            await wes._sorted_eligible(db, [_executor("A"), _executor("B")])

    @pytest.mark.asyncio
    async def test_non_db_error_propagates(self):
        # Only a driver error becomes "order by the declared load". A TypeError here
        # is our bug, and swallowed it would hide behind a warning.
        async def _bug(_query):
            raise TypeError("bug")

        db, _ = _fake_session(_bug)
        with patch.object(wes, "executor_registry", _registro()), pytest.raises(TypeError):
            await wes._sorted_eligible(db, [_executor("A"), _executor("B")])

    @pytest.mark.asyncio
    async def test_count_does_not_flush_the_session_pending(self, fabrica):
        # `Session.begin_nested()` flushes before the SAVEPOINT. If the caller's
        # session had something pending and invalid, the flush error would be
        # swallowed here as "count unavailable", with the transaction lost.
        # With the savepoint on the connection, the count does not touch what is pending.
        await _runs(fabrica, "A", "running", 1)
        async with fabrica() as db:
            existente = (await db.execute(select(WorkflowRun))).scalar_one()
            duplicado = WorkflowRun(
                task_id=existente.task_id, workflow_hash="wf-1", workspace_id="ws-1",
                status="pending", host="executor:B",
            )
            db.add(duplicado)
            counted = await wes._counted_by_server(db, ["A", "B"])
            assert counted == {"A": 1}
            assert duplicado in db.new

    @pytest.mark.asyncio
    async def test_capacity_read_that_raises_counts_as_undeclared(self, fabrica, estavel):
        await _runs(fabrica, "B", "running", 1)
        reg = _registro()
        reg.read_capacities = AsyncMock(side_effect=RuntimeError("redis fora"))
        assert await _sorted_ids(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]

    @pytest.mark.asyncio
    async def test_malformed_capacity_does_not_break_the_ordering(self, fabrica, estavel):
        # The capacity comes from outside (executor → Redis): garbage counts as nothing
        # declared — neither full nor slots —, and the slots come from the database.
        await _runs(fabrica, "B", "running", 1)
        reg = _registro({
            "A": {"running": "muitos", "queued": None, "max_concurrent": True},
            "B": _capacity(),
        })
        assert await _sorted_ids(fabrica, reg, [_executor("B"), _executor("A")]) == ["A", "B"]
