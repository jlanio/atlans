"""Closing a run from the server: a single compare-and-swap, for all eight paths.

The server's closings (orphan watchers, cancellation) write the outcome with a
conditional UPDATE on the status: whoever arrives after an outcome was already
written loses the race and does not count the usage again. The dispatch paths
did not: "no executor accepted", the isolation barrier and the exception safety
net assigned `run.status` and wrote by PK — the second writer. Between the
run's INSERT and that closing, seconds go by (credentials, encryption, sending
to each candidate) with the run already on screen, and a user cancellation in
that window became "failed": the 'cancelled' confirmed by the API was erased and
the usage counted twice. These paths also did not publish `__workflow_complete__`.

Real database (SQLite): the race only exists between two sessions.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import NoExecutorAvailableError
from app.models.base import Base
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service
from app.services import workflow_execution_service as wes


@asynccontextmanager
async def _from_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[WorkflowRun.__table__])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        await engine.dispose()


def _wf():
    wf = MagicMock()
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = wf.pin_metadata = None
    return wf


def _executor(id_hash="ag-1"):
    ag = MagicMock()
    ag.id_hash, ag.name, ag.public_key = id_hash, id_hash, "PEM"
    return ag


_DEFINICAO = {"nodes": [{"id": "t", "name": "WebhookTrigger"}], "edges": []}


@pytest.fixture
def effects(monkeypatch):
    """Accounting and publication, counted per run."""
    feito = {"contabilizados": [], "publicados": []}

    async def _account(db, run, *a, **k):
        feito["contabilizados"].append((run.task_id, run.status))

    async def _publish(run_ids, *, status, mensagem, extra=None):
        feito["publicados"].extend((rid, status) for rid in run_ids)

    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", _account)
    monkeypatch.setattr(run_events_service, "publicar_conclusao", _publish)
    monkeypatch.setattr(wes, "build_job_message", MagicMock(return_value={"envelope": {}}))
    return feito


async def _cancel_via_api(SessionMaker) -> None:
    """What `cancel_run` does to a run still 'pending', in another session."""
    async with SessionMaker() as outra:
        await outra.execute(
            update(WorkflowRun).where(WorkflowRun.status == "pending")
            .values(status="cancelled", error_message="Cancelado antes de ser atribuído a um executor.")
        )
        await outra.commit()


async def _o_run(SessionMaker) -> WorkflowRun:
    async with SessionMaker() as db:
        return (await db.execute(select(WorkflowRun))).scalar_one()


# ── Cancellation in the middle of dispatch wins ──────────────────────────────

@pytest.mark.asyncio
async def test_no_executor_accepted_does_not_erase_the_cancellation(effects, monkeypatch):
    async with _from_db() as SessionMaker:
        async def _send(executor_id, job):
            await _cancel_via_api(SessionMaker)    # the user cancels while the candidate responds
            return False                        # ...e o candidato recusa

        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(side_effect=_send)))

        async with SessionMaker() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(SessionMaker)

    assert run.status == "cancelled"            # before: 'failed', on top of the cancellation
    assert effects["contabilizados"] == []      # whoever closed it (the cancellation) already counted


@pytest.mark.asyncio
async def test_isolation_barrier_does_not_erase_the_cancellation(effects, monkeypatch):
    async with _from_db() as SessionMaker:
        async def _credentials(definicao, **_k):
            await _cancel_via_api(SessionMaker)
            return definicao

        monkeypatch.setattr(wes, "inject_credentials", _credentials)
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))
        intruso = _executor("pool-a")
        cadeia = wes.CandidateList([intruso], tiers={"pool-a": "pool"}, allowed={"geo-01"}, mode="isolated")

        async with SessionMaker() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, cadeia, {}, False, db=db)

        run = await _o_run(SessionMaker)

    assert run.status == "cancelled"
    assert effects["contabilizados"] == []


@pytest.mark.asyncio
async def test_dispatch_exception_does_not_erase_the_cancellation(effects, monkeypatch):
    async with _from_db() as SessionMaker:
        async def _credentials(definicao, **_k):
            await _cancel_via_api(SessionMaker)
            raise TypeError("payload inválido")

        monkeypatch.setattr(wes, "inject_credentials", _credentials)
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))

        async with SessionMaker() as db:
            with pytest.raises(TypeError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(SessionMaker)

    assert run.status == "cancelled"
    assert effects["contabilizados"] == []


# ── No race: closes, counts and publishes ONCE ───────────────────────────────

@pytest.mark.asyncio
async def test_exhausted_dispatch_closes_accounting_and_publishes_once(effects, monkeypatch):
    """The `raise` of path (4) goes through the `except` safety net: it must not
    close again, nor count, nor publish another completion."""
    async with _from_db() as SessionMaker:
        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=False)))

        async with SessionMaker() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(SessionMaker)

    assert (run.status, run.error_category) == ("failed", "no_executor")
    assert effects["contabilizados"] == [(run.task_id, "failed")]
    # The open panel receives the completion, as in the server's other closings.
    assert effects["publicados"] == [(run.task_id, "failed")]


@pytest.mark.asyncio
async def test_close_runs_only_closes_what_is_still_open(effects):
    from app.services.fechamento_de_run import fechar_runs

    async with _from_db() as SessionMaker:
        async with SessionMaker() as db:
            db.add_all([
                WorkflowRun(task_id=t, workflow_hash="wf-1", workspace_id="ws-1", status=st,
                            node_stats={}, host=h)
                for t, st, h in [("a", "pending", "executor:ex-1"), ("b", "success", "executor:ex-1"),
                                 ("c", "pending", "executor:ex-2")]
            ])
            await db.commit()

        async with SessionMaker() as db:
            fechados = await fechar_runs(
                db, ["a", "b", "c"], de=("pending",), para="failed", mensagem="não chegou",
                categoria="dispatch", host="executor:ex-1",
            )
            assert [(r.task_id, r.status, r.error_category) for r in fechados] == [("a", "failed", "dispatch")]

        async with SessionMaker() as db:
            gravado = dict((await db.execute(select(WorkflowRun.task_id, WorkflowRun.status))).all())

    # 'b' already finished (the executor's outcome stands) and 'c' belongs to another executor.
    assert gravado == {"a": "failed", "b": "success", "c": "pending"}
    assert effects["contabilizados"] == [("a", "failed")]
    assert effects["publicados"] == [("a", "failed")]


@pytest.mark.asyncio
async def test_barrier_closes_accounting_and_publishes_once(effects, monkeypatch):
    async with _from_db() as SessionMaker:
        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))
        cadeia = wes.CandidateList([_executor("pool-a")], tiers={}, allowed={"geo-01"}, mode="isolated")

        async with SessionMaker() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, cadeia, {}, False, db=db)

        run = await _o_run(SessionMaker)

    assert (run.status, run.error_category) == ("failed", "isolation")
    assert effects["contabilizados"] == [(run.task_id, "failed")]
    assert effects["publicados"] == [(run.task_id, "failed")]


@pytest.mark.asyncio
async def test_accounting_failure_loses_neither_the_other_runs_nor_the_completion(monkeypatch):
    """`account_terminal_run` swallows the usage_daily failure with a rollback, and
    the rollback expires the session's objects: the next run was counted with
    expired attributes, the completion was not published and the caller could no
    longer read `run.host` (the cancel to the host did not go out)."""
    from app.core import run_result_consumer as rrc
    from app.services.fechamento_de_run import fechar_runs

    publicados: list[str] = []

    async def _publish(run_ids, *, status, mensagem, extra=None):
        publicados.extend(run_ids)

    accounted: list[tuple] = []

    async def _upsert(db, run, stats, first_close):
        await db.execute(select(WorkflowRun.task_id))    # opens the transaction, like the real upsert
        if run.task_id == "a":
            raise RuntimeError("usage_daily fora do ar")
        accounted.append((run.task_id, run.status))

    monkeypatch.setattr(run_events_service, "publicar_conclusao", _publish)
    monkeypatch.setattr(rrc, "_upsert_usage_daily", _upsert)

    async with _from_db() as SessionMaker:
        async with SessionMaker() as db:
            db.add_all([
                WorkflowRun(task_id=t, workflow_hash="wf-1", workspace_id="ws-1", status="pending",
                            node_stats={}, host=f"executor:{t}")
                for t in ("a", "b")
            ])
            await db.commit()

        async with SessionMaker() as db:
            fechados = await fechar_runs(
                db, ["a", "b"], de=("pending",), para="failed", mensagem="sumiu", categoria="dispatch",
            )
            hosts = [(r.task_id, r.host, r.status) for r in fechados]

    assert hosts == [("a", "executor:a", "failed"), ("b", "executor:b", "failed")]
    assert accounted == [("b", "failed")]
    assert publicados == ["a", "b"]
