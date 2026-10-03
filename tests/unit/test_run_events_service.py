"""`app/services/run_events_service.py` — a run's events without WebSocket.

The subscribe → LRANGE → dedup → pub/sub loop moved out of the WS handler into a
generator of `Lote`s that the MCP server also consumes. Each test here pins a
behavior the run panel already depended on (and that the WS keeps observing
through the generator):

- the replay is ONE read, cut at the 1st `__workflow_complete__`, and a run
  that has already ended never goes live;
- the replay's tail deduplicates the boundary with pub/sub, but a legitimate
  repeat after it gets through;
- when the buffer fills up, stdout is dropped before lifecycle and `dropped` counts;
- a quiet channel emits an empty heartbeat batch; an exceeded deadline ends
  without `completo`;
- the subscriber's dedicated connection closes on every exit; Redis down becomes
  `RunEventsUnavailable`.

`esperar_run` combines the generator with the database poll (file-backed SQLite):
the live complete waits for the row to become terminal; a cancel of a `pending`
run, which publishes no event, ends via the poll; without Redis only the poll
works; progress arrives per distinct node.

The contract the socketless consumer reads from the result is also pinned here:
`viu_complete` separates "the graph finished, the row is missing" from "still
running" (including when both tasks finish in the same step); an `on_progress`
that raises does not bring down the wait; a transient database failure is
tolerated up to the ceiling and only then propagates; and the read the poll
already had in flight is reused instead of redone.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.core.constants import WORKFLOW_COMPLETE_NODE
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service as svc


# ── Test doubles ──────────────────────────────────────────────────────────────


class FakePubSub:
    """`segurar=True` simulates a run still alive: `listen()` never ends.

    `listens` counts how many times the body of `listen()` actually ran — it is
    what proves whether or not the generator went to listen live (a `listen()`
    that is only called, without being iterated, never executes the body).
    """

    def __init__(self, mensagens: list[str], *, segurar: bool = False):
        self._messages = mensagens
        self._hold = segurar
        self.channels: list[str] = []
        self.listens = 0

    async def subscribe(self, canal: str) -> None:
        self.channels.append(canal)

    async def listen(self):
        self.listens += 1
        for raw in self._messages:
            yield {"type": "message", "data": raw}
        if self._hold:
            await asyncio.Event().wait()


class _PubSubCtx:
    def __init__(self, pubsub):
        self._pubsub = pubsub

    async def __aenter__(self):
        return self._pubsub

    async def __aexit__(self, *_):
        return False


class FakeSubClient:
    def __init__(self, pubsub):
        self._pubsub = pubsub
        self.fechado = False

    def pubsub(self):
        return _PubSubCtx(self._pubsub)

    async def aclose(self):
        self.fechado = True


def stdout(node: str, texto: str = "") -> str:
    return json.dumps({"node": node, "kind": "stdout", "status": "log", "msg": texto})


def lifecycle(node: str, status: str, duration_ms=None) -> str:
    ev = {"node": node, "kind": "lifecycle", "status": status}
    if duration_ms is not None:
        ev["duration_ms"] = duration_ms
    return json.dumps(ev)


COMPLETE = json.dumps({"node": WORKFLOW_COMPLETE_NODE, "kind": "lifecycle", "status": "completed"})


def _redis(historico: list[str]) -> MagicMock:
    rc = MagicMock()
    rc.lrange = AsyncMock(return_value=list(historico))
    return rc


async def _collect(gen, *, maximo: int | None = None) -> list[svc.Lote]:
    """Consumes the generator (up to `maximo` batches), closing it as a client would."""
    lotes: list[svc.Lote] = []
    try:
        async for lote in gen:
            lotes.append(lote)
            if maximo is not None and len(lotes) >= maximo:
                break
    finally:
        await gen.aclose()
    return lotes


def _nodes(lotes: list[svc.Lote]) -> list[str]:
    return [json.loads(raw)["node"] for lote in lotes for raw in lote.eventos]


# ── iter_run_events: replay ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_reads_the_history_in_a_single_call_and_delivers_in_batches():
    historico = [stdout(f"n{i}") for i in range(1200)]
    rc = _redis(historico)
    sub = FakeSubClient(FakePubSub([COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5))

    rc.lrange.assert_awaited_once_with("workflow:run-1:history", 0, -1)
    assert sub._pubsub.channels == ["workflow:run-1:events"]
    # SENDING is still paginated (500/500/200) and then comes the live complete.
    assert [len(lote.eventos) for lote in lotes] == [500, 500, 200, 1]
    assert [lote.completo for lote in lotes] == [False, False, False, True]
    assert _nodes(lotes) == [f"n{i}" for i in range(1200)] + [WORKFLOW_COMPLETE_NODE]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_replay_stops_at_complete_and_does_not_go_live():
    """Run already ended: last batch with `completo=True`, pub/sub never read."""
    rc = _redis([stdout("n1"), COMPLETE, stdout("n2")])
    # If the generator went live, it would get stuck here — the test would hang.
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _collect(svc.iter_run_events("run-1", timeout_s=5)), timeout=2,
        )

    assert len(lotes) == 1
    assert lotes[0].completo is True
    assert lotes[0].dropped == 0 and lotes[0].heartbeat is False
    assert _nodes(lotes) == ["n1", WORKFLOW_COMPLETE_NODE]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_replay_marks_complete_only_on_the_last_batch():
    historico = [stdout(f"n{i}") for i in range(7)] + [COMPLETE]
    rc = _redis(historico)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5, chunk=3))

    assert [len(lote.eventos) for lote in lotes] == [3, 3, 2]
    assert [lote.completo for lote in lotes] == [False, False, True]


@pytest.mark.asyncio
async def test_empty_replay_goes_straight_live():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "started"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5))

    assert _nodes(lotes) == ["n1", WORKFLOW_COMPLETE_NODE]
    assert lotes[-1].completo is True


# ── iter_run_events: dedup da fronteira ───────────────────────────────────────


@pytest.mark.asyncio
async def test_dedup_drops_the_replay_tail_repeated_live():
    duplicados = [stdout("n8", "linha"), stdout("n8", "linha"), stdout("n9")]
    novos = [stdout("n10"), stdout("n8", "linha")]
    rc = _redis(duplicados)
    sub = FakeSubClient(FakePubSub([*duplicados, *novos, COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5))

    replay, live = lotes[0], lotes[1:]
    assert _nodes([replay]) == ["n8", "n8", "n9"]
    # The `n8` repeated AFTER the boundary is legitimate and has to get through.
    assert _nodes(live) == ["n10", "n8", WORKFLOW_COMPLETE_NODE]


@pytest.mark.asyncio
async def test_dedup_turns_off_at_the_first_non_matching_message():
    """A repeat in the MIDDLE of the run is not swallowed: the dedup is prefix-only."""
    cauda = [stdout("n1", "x")]
    rc = _redis(cauda)
    sub = FakeSubClient(FakePubSub([stdout("n2"), stdout("n1", "x"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5))

    assert _nodes(lotes[1:]) == ["n2", "n1", WORKFLOW_COMPLETE_NODE]


# ── iter_run_events: buffer, heartbeat, prazo, falhas ─────────────────────────


@pytest.mark.asyncio
async def test_full_buffer_drops_stdout_before_lifecycle_and_counts_dropped():
    mensagens = [
        stdout("s1"), stdout("s2"),
        lifecycle("n1", "completed"), lifecycle("n2", "completed"),
        COMPLETE,
    ]
    rc = _redis([])
    sub = FakeSubClient(FakePubSub(mensagens))

    # The fake pub/sub delivers everything without yielding the loop, so the producer
    # fills the buffer before the consumer drains it — the slow-browser scenario.
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc), \
            patch.object(svc, "_QUEUE_MAXSIZE", 3):
        lotes = await _collect(svc.iter_run_events("run-1", timeout_s=5))

    assert len(lotes) == 1
    assert lotes[0].dropped == 2
    assert _nodes(lotes) == ["n1", "n2", WORKFLOW_COMPLETE_NODE]
    assert lotes[0].completo is True


@pytest.mark.asyncio
async def test_complete_is_never_dropped_from_the_buffer():
    buf = svc._EventBuffer(2)
    buf.push(lifecycle("a", "started"), droppable=False)
    buf.push(COMPLETE, droppable=False)
    buf.push(lifecycle("b", "started"), droppable=False)
    assert buf.take_dropped() == 1
    assert buf.take_dropped_lifecycle() == 1
    assert [json.loads(raw)["node"] for raw in await buf.drain()] == [WORKFLOW_COMPLETE_NODE, "b"]


@pytest.mark.asyncio
async def test_quiet_channel_emits_empty_heartbeat():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _collect(svc.iter_run_events("run-1", timeout_s=5, heartbeat_s=0.01), maximo=2),
            timeout=2,
        )

    assert len(lotes) == 2
    assert all(lote.heartbeat and lote.eventos == [] and not lote.completo for lote in lotes)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_deadline_exceeded_ends_without_complete():
    rc = _redis([stdout("n1")])
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _collect(svc.iter_run_events("run-1", timeout_s=0.05, heartbeat_s=0.01)),
            timeout=2,
        )

    assert lotes[0].eventos == [stdout("n1")]
    assert not any(lote.completo for lote in lotes)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_consumer_that_stops_midway_closes_the_subscriber_connection():
    rc = _redis([])
    sub = FakeSubClient(FakePubSub([stdout("n1")], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=rc):
        lotes = await asyncio.wait_for(
            _collect(svc.iter_run_events("run-1", timeout_s=5), maximo=1), timeout=2,
        )

    assert _nodes(lotes) == ["n1"]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_redis_down_becomes_run_events_unavailable_and_closes_the_subscriber():
    sub = FakeSubClient(FakePubSub([]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(
                svc, "get_redis_pool",
                MagicMock(side_effect=RuntimeError("Redis pool não inicializado.")),
            ):
        with pytest.raises(svc.RunEventsUnavailable):
            await _collect(svc.iter_run_events("run-1", timeout_s=5))

    assert sub.fechado is True


@pytest.mark.asyncio
async def test_subscribe_failure_is_also_run_events_unavailable():
    from redis.exceptions import ConnectionError as RedisConnectionError

    pubsub = FakePubSub([])
    pubsub.subscribe = AsyncMock(side_effect=RedisConnectionError("recusada"))
    sub = FakeSubClient(pubsub)

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        with pytest.raises(svc.RunEventsUnavailable):
            await _collect(svc.iter_run_events("run-1", timeout_s=5))

    assert sub.fechado is True


# ── esperar_run ───────────────────────────────────────────────────────────────


@pytest.fixture
async def banco(tmp_path):
    """FILE-backed SQLite: the poll and whoever updates the run use their own
    sessions, and in memory each connection would see a different empty database (a
    `StaticPool` would share the same transaction, and the poll's rollback would undo the UPDATE)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'runs.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[WorkflowRun.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def sessao():
        async with fabrica() as s:
            try:
                yield s
            finally:
                await s.rollback()

    async with fabrica() as s:
        s.add(WorkflowRun(task_id="run-1", workflow_hash="wf-1", workspace_id="ws-1", status="running"))
        await s.commit()

    with patch.object(svc, "get_session_async", sessao):
        yield fabrica
    await engine.dispose()


async def _change_status(fabrica, status: str, *, after_s: float) -> None:
    await asyncio.sleep(after_s)
    async with fabrica() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status=status))
        await s.commit()


@pytest.mark.asyncio
async def test_read_run_status_by_task_id(banco):
    async with banco() as db:
        status, run = await svc.ler_status_do_run(db, "run-1")
        assert status == "running" and run.task_id == "run-1"
        assert await svc.ler_status_do_run(db, "nao-existe") == (None, None)


@pytest.mark.asyncio
async def test_wait_run_live_complete_waits_for_the_row_to_become_terminal(banco):
    """The consumer publishes the event and ONLY THEN writes the row."""
    mensagens = [
        stdout("n1", "print ignorado"),
        lifecycle("n1", "started"),
        lifecycle("n1", "completed", duration_ms=1234),
        lifecycle("n1", "completed", duration_ms=1234),  # repeated: counts once
        lifecycle("n2", "failed", duration_ms=80),
        COMPLETE,
    ]
    sub = FakeSubClient(FakePubSub(mensagens))
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    updater = asyncio.create_task(_change_status(banco, "failed", after_s=0.05))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=2, on_progress=on_progress, poll_s=1.0),
            timeout=3,
        )
    await updater

    assert resultado.status == "failed"
    assert resultado.run is not None and resultado.run.task_id == "run-1"
    assert resultado.concluidos == 2
    assert resultado.timed_out is False
    assert resultado.redis_indisponivel is False
    assert progresso == [(1, 2, "n1: completed (1,2 s)"), (2, 2, "n2: failed (80 ms)")]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_wait_run_cancel_of_pending_run_ends_via_poll(banco):
    """No `__workflow_complete__` published: the database poll is what ends it."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    updater = asyncio.create_task(_change_status(banco, "cancelled", after_s=0.05))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=3, poll_s=0.01), timeout=3,
        )
    await updater

    assert resultado.status == "cancelled"
    assert resultado.concluidos == 0
    assert resultado.timed_out is False
    # The events task was cancelled and the subscriber closed.
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_wait_run_without_redis_continues_only_via_poll(banco):
    sub = FakeSubClient(FakePubSub([]))
    updater = asyncio.create_task(_change_status(banco, "success", after_s=0.05))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(
                svc, "get_redis_pool",
                MagicMock(side_effect=RuntimeError("Redis pool não inicializado.")),
            ):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )
    await updater

    assert resultado.redis_indisponivel is True
    assert resultado.status == "success"
    assert resultado.timed_out is False


@pytest.mark.asyncio
async def test_wait_run_deadline_exceeded_returns_timed_out(banco):
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "completed")], segurar=True))
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=0.1, total_nodes=4, on_progress=on_progress, poll_s=0.02),
            timeout=3,
        )

    assert resultado.timed_out is True
    assert resultado.status == "running"
    assert resultado.concluidos == 1
    assert progresso == [(1, 4, "n1: completed")]
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_wait_run_sums_dropped_events(banco):
    mensagens = [stdout("s1"), stdout("s2"), lifecycle("n1", "completed"), COMPLETE]
    sub = FakeSubClient(FakePubSub(mensagens))
    updater = asyncio.create_task(_change_status(banco, "success", after_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_QUEUE_MAXSIZE", 2), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=1.0), timeout=3,
        )
    await updater

    assert resultado.eventos_descartados == 2
    assert resultado.concluidos == 1
    assert resultado.status == "success"


@pytest.mark.asyncio
async def test_wait_run_already_complete_replay_does_not_listen_to_pubsub(banco):
    """History already holding the marker: `listen()` is never iterated.

    The double counts the entries into the body of `listen()` and would be stuck
    in it forever (`segurar=True`); `poll_s` is longer than the test's deadline,
    so what ends the wait is the replay. If the generator went live, the 1 s
    `wait_for` would time out instead of returning a result.
    """
    pubsub = FakePubSub([], segurar=True)
    sub = FakeSubClient(pubsub)
    updater = asyncio.create_task(_change_status(banco, "success", after_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nodes=1, poll_s=30.0), timeout=1,
        )
    await updater

    # Subscribed (the SUBSCRIBE-before-LRANGE order does not change), but never listened to.
    assert pubsub.channels == ["workflow:run-1:events"]
    assert pubsub.listens == 0
    assert resultado.viu_complete is True
    assert resultado.status == "success"
    assert resultado.concluidos == 1
    assert resultado.timed_out is False
    assert sub.fechado is True
    assert (await _row(banco)).status == "success"


@pytest.mark.asyncio
async def test_wait_run_complete_without_terminal_row_returns_saw_complete(banco):
    """Consumer stopped: the graph finished, the row did not. The caller needs to know.

    Without `viu_complete` the result was indistinguishable from a run still
    running: `status="running"` and `timed_out=False`, because the overall
    deadline was nowhere near expiring.
    """
    sub = FakeSubClient(FakePubSub([lifecycle("n1", "completed"), COMPLETE]))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01), \
            patch.object(svc, "_POLL_POS_COMPLETE_MAX_S", 0.05):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nodes=1, poll_s=30.0), timeout=3,
        )

    assert resultado.viu_complete is True
    assert resultado.status == "running"
    assert resultado.timed_out is False
    assert resultado.concluidos == 1


@pytest.mark.asyncio
async def test_wait_run_without_complete_does_not_mark_saw_complete(banco):
    """An end that publishes no event: `viu_complete` stays False even with an outcome."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    updater = asyncio.create_task(_change_status(banco, "cancelled", after_s=0.02))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )
    await updater

    assert resultado.status == "cancelled"
    assert resultado.viu_complete is False


@pytest.mark.asyncio
async def test_wait_run_reuses_the_in_flight_read_after_complete(banco):
    """The read the poll already had in flight is not thrown away (doubled latency).

    The read is slow on purpose, so the replay's complete arrives while it is in
    progress: the `shield` lets it finish and the result has to come FROM IT. A
    second trip to the database here would be a whole round trip on the most
    common path of the wait.
    """
    leituras: list[str] = []
    real = svc.ler_status_do_run

    async def read_slowly(db, run_id):
        leituras.append(run_id)
        await asyncio.sleep(0.05)
        return await real(db, run_id)

    async with banco() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status="success"))
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "ler_status_do_run", read_slowly):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nodes=1, poll_s=30.0), timeout=3,
        )

    assert resultado.status == "success"
    assert resultado.viu_complete is True
    assert leituras == ["run-1"]


@pytest.mark.asyncio
async def test_wait_run_failing_callback_does_not_break_the_wait(banco, caplog):
    """The caller's `on_progress` is broken: warns once and keeps counting."""
    mensagens = [
        lifecycle("n1", "completed"),
        lifecycle("n2", "completed"),
        lifecycle("n3", "failed"),
        COMPLETE,
    ]
    sub = FakeSubClient(FakePubSub(mensagens))
    chamadas: list[int] = []

    async def on_progress(n, total, msg):
        chamadas.append(n)
        raise RuntimeError("consumidor do progresso caiu")

    updater = asyncio.create_task(_change_status(banco, "failed", after_s=0.02))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        with caplog.at_level("WARNING"):
            resultado = await asyncio.wait_for(
                svc.esperar_run(
                    "run-1", timeout_s=5, total_nodes=3, on_progress=on_progress, poll_s=1.0,
                ),
                timeout=3,
            )
    await updater

    # Notified once, gave up notifying — and counted all three anyway.
    assert chamadas == [1]
    assert resultado.concluidos == 3
    assert resultado.status == "failed"
    assert resultado.viu_complete is True
    avisos = [r for r in caplog.records if "callback falhou" in r.message]
    assert len(avisos) == 1


@pytest.mark.asyncio
async def test_wait_run_tolerates_transient_poll_failures(banco, caplog):
    """Database blip with the events channel healthy: the wait goes on."""
    from sqlalchemy.exc import SQLAlchemyError

    real = svc.ler_status_do_run
    tentativas = {"n": 0}

    async def read_flaky(db, run_id):
        tentativas["n"] += 1
        if tentativas["n"] <= svc._POLL_MAX_CONSECUTIVE_FAILURES - 1:
            raise SQLAlchemyError("checkout do pool estourou")
        return await real(db, run_id)

    sub = FakeSubClient(FakePubSub([], segurar=True))
    updater = asyncio.create_task(_change_status(banco, "success", after_s=0.02))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", read_flaky):
        with caplog.at_level("WARNING"):
            resultado = await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
            )
    await updater

    assert resultado.status == "success"
    assert resultado.timed_out is False
    assert any("Poll do run run-1 falhou" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_wait_run_propagates_when_the_poll_fails_beyond_the_ceiling(banco):
    """Real unavailability (not a hiccup): the error propagates to the caller."""
    from sqlalchemy.exc import SQLAlchemyError

    chamadas = {"n": 0}

    async def always_fails(db, run_id):
        chamadas["n"] += 1
        raise SQLAlchemyError("banco fora")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", always_fails):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == svc._POLL_MAX_CONSECUTIVE_FAILURES


async def _row(fabrica) -> WorkflowRun:
    async with fabrica() as s:
        return (await s.execute(select(WorkflowRun).where(WorkflowRun.task_id == "run-1"))).scalar_one()


@pytest.mark.asyncio
async def test_wait_run_saw_complete_when_both_tasks_finish_together(banco):
    """Events and poll finishing in the SAME loop step.

    It is a real race — the `__workflow_complete__` arrives while the poll's
    read comes back — and in it `asyncio.wait` returns BOTH tasks in `done`. The
    window lasts one loop step, so it is forced here by a double that waits for
    both before returning. Exiting straight through the poll's outcome, without
    looking at the events' result, delivered `viu_complete=False` for a run whose
    graph had demonstrably finished.
    """
    wait_real = asyncio.wait

    async def wait_both(tarefas, **kw):
        done, pendentes = await wait_real(tarefas, **kw)
        if pendentes:
            await wait_real(pendentes)
            done, pendentes = done | pendentes, set()
        return done, pendentes

    async with banco() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status="success"))
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(asyncio, "wait", wait_both):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )

    assert resultado.status == "success"
    assert resultado.viu_complete is True
    assert resultado.concluidos == 1


# ── esperar_run: deadlines, outcomes and discarding (characterization) ───────
#
# Pinned before splitting the loop into parts: the deadline that reaches the
# generator and the poll, what comes back in each outcome (including the error
# ones) and which events do NOT count as progress.


def _outcome(resultado: svc.WaitResult) -> tuple:
    return (
        resultado.status, resultado.concluidos, resultado.eventos_descartados,
        resultado.timed_out, resultado.redis_indisponivel, resultado.viu_complete,
    )


async def _mark_terminal(fabrica, status: str) -> None:
    async with fabrica() as s:
        await s.execute(update(WorkflowRun).where(WorkflowRun.task_id == "run-1").values(status=status))
        await s.commit()


@pytest.mark.asyncio
async def test_wait_run_passes_only_the_remaining_deadline_to_events(banco):
    timeouts: list[float] = []

    async def fake_events(run_id, *, timeout_s):
        timeouts.append(timeout_s)
        await asyncio.Event().wait()
        yield  # pragma: no cover - never gets here

    updater = asyncio.create_task(_change_status(banco, "success", after_s=0.02))
    with patch.object(svc, "iter_run_events", fake_events):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=7, total_nodes=1, poll_s=0.01), timeout=3,
        )
    await updater

    assert len(timeouts) == 1 and 6.5 < timeouts[0] <= 7
    assert _outcome(resultado) == ("success", 0, 0, False, False, False)


@pytest.mark.asyncio
async def test_wait_run_long_poll_does_not_exceed_the_deadline(banco):
    """`poll_s` longer than the deadline: the wait ends at the deadline, not at the next poll."""
    sub = FakeSubClient(FakePubSub([], segurar=True))
    inicio = asyncio.get_running_loop().time()

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=0.1, total_nodes=1, poll_s=30.0), timeout=3,
        )

    assert asyncio.get_running_loop().time() - inicio < 1.5
    assert _outcome(resultado) == ("running", 0, 0, True, False, False)
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_wait_run_nonexistent_run_exceeds_the_deadline_without_row(banco):
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("nao-existe", timeout_s=0.1, total_nodes=1, poll_s=0.02), timeout=3,
        )

    assert resultado.run is None
    assert _outcome(resultado) == (None, 0, 0, True, False, False)


@pytest.mark.asyncio
async def test_wait_run_generic_error_in_events_continues_via_poll(banco, caplog):
    async def broken_events(run_id, *, timeout_s):
        raise ValueError("canal quebrou")
        yield  # pragma: no cover - generator

    updater = asyncio.create_task(_change_status(banco, "failed", after_s=0.02))
    with patch.object(svc, "iter_run_events", broken_events), \
            caplog.at_level("ERROR"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )
    await updater

    assert _outcome(resultado) == ("failed", 0, 0, False, False, False)
    assert any(
        r.getMessage() == "Erro ao acompanhar eventos do run run-1; seguindo só pelo poll: canal quebrou"
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_wait_run_redis_down_warns_and_marks_redis_unavailable(banco, caplog):
    updater = asyncio.create_task(_change_status(banco, "cancelled", after_s=0.02))
    sub = FakeSubClient(FakePubSub([]))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", MagicMock(side_effect=RuntimeError("sem pool"))), \
            caplog.at_level("WARNING"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )
    await updater

    assert _outcome(resultado) == ("cancelled", 0, 0, False, True, False)
    assert any(
        r.getMessage() == (
            "Eventos do run run-1 indisponíveis; seguindo só pelo poll: "
            "Redis indisponível para os eventos do run run-1: sem pool"
        )
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_wait_run_returns_the_detached_readable_row(banco):
    """`run` comes back without a session, with the attributes already loaded."""
    async with banco() as s:
        await s.execute(
            update(WorkflowRun).where(WorkflowRun.task_id == "run-1")
            .values(status="success", node_stats={"n1": {"status": "completed"}}),
        )
        await s.commit()

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
        )

    assert resultado.run.node_stats == {"n1": {"status": "completed"}}
    assert resultado.run.workflow_hash == "wf-1"


def _post_complete_read(falhas: int):
    """1st read: 'running' (the consumer has not written yet); then `falhas`
    consecutive transient failures; then the real row."""
    from sqlalchemy.exc import SQLAlchemyError

    real = svc.ler_status_do_run
    chamadas = {"n": 0}

    async def ler(db, run_id):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            _status, run = await real(db, run_id)
            return "running", run
        if chamadas["n"] <= 1 + falhas:
            raise SQLAlchemyError("conexão reciclada")
        return await real(db, run_id)

    return ler, chamadas


@pytest.mark.asyncio
async def test_wait_run_post_complete_poll_tolerates_transient_failures(banco, caplog):
    await _mark_terminal(banco, "success")
    ler, chamadas = _post_complete_read(falhas=svc._POLL_MAX_CONSECUTIVE_FAILURES - 1)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([lifecycle("n1", "completed"), COMPLETE])), \
            patch.object(svc, "ler_status_do_run", ler), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01), \
            caplog.at_level("WARNING"):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=30, total_nodes=1, poll_s=30.0), timeout=3,
        )

    assert _outcome(resultado) == ("success", 1, 0, False, False, True)
    assert chamadas["n"] == 1 + svc._POLL_MAX_CONSECUTIVE_FAILURES
    avisos = [r.getMessage() for r in caplog.records if "Poll pós-complete" in r.getMessage()]
    assert avisos == [
        f"Poll pós-complete do run run-1 falhou ({i}/{svc._POLL_MAX_CONSECUTIVE_FAILURES}): conexão reciclada"
        for i in range(1, svc._POLL_MAX_CONSECUTIVE_FAILURES)
    ]


@pytest.mark.asyncio
async def test_wait_run_post_complete_poll_propagates_at_the_ceiling(banco):
    from sqlalchemy.exc import SQLAlchemyError

    ler, chamadas = _post_complete_read(falhas=99)
    sub = FakeSubClient(FakePubSub([], segurar=True))

    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([COMPLETE])), \
            patch.object(svc, "ler_status_do_run", ler), \
            patch.object(svc, "_POLL_POS_COMPLETE_S", 0.01):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=30, total_nodes=1, poll_s=30.0), timeout=3,
            )

    assert chamadas["n"] == 1 + svc._POLL_MAX_CONSECUTIVE_FAILURES


@pytest.mark.asyncio
async def test_wait_run_non_transient_error_propagates_on_first(banco):
    chamadas = {"n": 0}

    async def ler(db, run_id):
        chamadas["n"] += 1
        raise ValueError("bug na consulta")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", ler):
        with pytest.raises(ValueError, match="bug na consulta"):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=5, total_nodes=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == 1
    assert sub.fechado is True


@pytest.mark.asyncio
async def test_wait_run_transient_failure_after_deadline_propagates_without_waiting_for_the_ceiling(banco):
    from sqlalchemy.exc import SQLAlchemyError

    chamadas = {"n": 0}

    async def read_slow(db, run_id):
        chamadas["n"] += 1
        await asyncio.sleep(0.1)
        raise SQLAlchemyError("pool esgotado")

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis([])), \
            patch.object(svc, "ler_status_do_run", read_slow):
        with pytest.raises(SQLAlchemyError):
            await asyncio.wait_for(
                svc.esperar_run("run-1", timeout_s=0.05, total_nodes=1, poll_s=0.01), timeout=3,
            )

    assert chamadas["n"] == 1


@pytest.mark.asyncio
async def test_wait_run_only_counts_valid_lifecycle_and_drops_what_comes_after_complete(banco):
    """What is NOT progress: stdout/debug, invalid JSON or JSON that is not an
    object, a kind that is not lifecycle, an event without a node, a non-final
    status — and what the history stored AFTER `__workflow_complete__` (another cycle)."""
    historico = [
        "nao-e-json",
        "[1, 2]",
        json.dumps({"node": "n0", "status": "completed"}),  # no kind: counts as lifecycle
        stdout("n1", "print"),
        json.dumps({"node": "n1", "kind": "debug", "status": "completed"}),
        json.dumps({"kind": "lifecycle", "status": "completed"}),
        json.dumps({"node": "n2", "kind": "lifecycle", "status": "skipped"}),
        json.dumps({"node": "n3", "kind": "metric", "status": "completed"}),
        lifecycle("n4", "failed", duration_ms=2500),
        COMPLETE,
        lifecycle("n5", "completed"),
    ]
    await _mark_terminal(banco, "failed")
    progresso: list[tuple[int, int, str]] = []

    async def on_progress(n, total, msg):
        progresso.append((n, total, msg))

    sub = FakeSubClient(FakePubSub([], segurar=True))
    with patch.object(svc, "new_pubsub_client", lambda: sub), \
            patch.object(svc, "get_redis_pool", return_value=_redis(historico)):
        resultado = await asyncio.wait_for(
            svc.esperar_run("run-1", timeout_s=5, total_nodes=6, on_progress=on_progress, poll_s=30.0),
            timeout=3,
        )

    assert progresso == [(1, 6, "n0: completed"), (2, 6, "n4: failed (2,5 s)")]
    assert _outcome(resultado) == ("failed", 2, 0, False, False, True)
    assert sub._pubsub.listens == 0
