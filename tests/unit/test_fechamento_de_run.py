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
async def _banco():
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
def efeitos(monkeypatch):
    """Accounting and publication, counted per run."""
    feito = {"contabilizados": [], "publicados": []}

    async def _contabiliza(db, run, *a, **k):
        feito["contabilizados"].append((run.task_id, run.status))

    async def _publica(run_ids, *, status, mensagem, extra=None):
        feito["publicados"].extend((rid, status) for rid in run_ids)

    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", _contabiliza)
    monkeypatch.setattr(run_events_service, "publicar_conclusao", _publica)
    monkeypatch.setattr(wes, "build_job_message", MagicMock(return_value={"envelope": {}}))
    return feito


async def _cancelar_pela_api(Sessao) -> None:
    """What `cancel_run` does to a run still 'pending', in another session."""
    async with Sessao() as outra:
        await outra.execute(
            update(WorkflowRun).where(WorkflowRun.status == "pending")
            .values(status="cancelled", error_message="Cancelado antes de ser atribuído a um executor.")
        )
        await outra.commit()


async def _o_run(Sessao) -> WorkflowRun:
    async with Sessao() as db:
        return (await db.execute(select(WorkflowRun))).scalar_one()


# ── Cancellation in the middle of dispatch wins ──────────────────────────────

@pytest.mark.asyncio
async def test_nenhum_executor_aceitou_nao_apaga_o_cancelamento(efeitos, monkeypatch):
    async with _banco() as Sessao:
        async def _envio(executor_id, job):
            await _cancelar_pela_api(Sessao)    # the user cancels while the candidate responds
            return False                        # ...e o candidato recusa

        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(side_effect=_envio)))

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(Sessao)

    assert run.status == "cancelled"            # before: 'failed', on top of the cancellation
    assert efeitos["contabilizados"] == []      # whoever closed it (the cancellation) already counted


@pytest.mark.asyncio
async def test_barreira_de_isolamento_nao_apaga_o_cancelamento(efeitos, monkeypatch):
    async with _banco() as Sessao:
        async def _credenciais(definicao, **_k):
            await _cancelar_pela_api(Sessao)
            return definicao

        monkeypatch.setattr(wes, "inject_credentials", _credenciais)
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))
        intruso = _executor("pool-a")
        cadeia = wes.CandidateList([intruso], tiers={"pool-a": "pool"}, allowed={"geo-01"}, mode="isolated")

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, cadeia, {}, False, db=db)

        run = await _o_run(Sessao)

    assert run.status == "cancelled"
    assert efeitos["contabilizados"] == []


@pytest.mark.asyncio
async def test_excecao_no_despacho_nao_apaga_o_cancelamento(efeitos, monkeypatch):
    async with _banco() as Sessao:
        async def _credenciais(definicao, **_k):
            await _cancelar_pela_api(Sessao)
            raise TypeError("payload inválido")

        monkeypatch.setattr(wes, "inject_credentials", _credenciais)
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))

        async with Sessao() as db:
            with pytest.raises(TypeError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(Sessao)

    assert run.status == "cancelled"
    assert efeitos["contabilizados"] == []


# ── No race: closes, counts and publishes ONCE ───────────────────────────────

@pytest.mark.asyncio
async def test_despacho_esgotado_fecha_conta_e_publica_uma_vez(efeitos, monkeypatch):
    """The `raise` of path (4) goes through the `except` safety net: it must not
    close again, nor count, nor publish another completion."""
    async with _banco() as Sessao:
        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=False)))

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(Sessao)

    assert (run.status, run.error_category) == ("failed", "no_executor")
    assert efeitos["contabilizados"] == [(run.task_id, "failed")]
    # The open panel receives the completion, as in the server's other closings.
    assert efeitos["publicados"] == [(run.task_id, "failed")]


@pytest.mark.asyncio
async def test_fechar_runs_so_fecha_o_que_ainda_esta_aberto(efeitos):
    from app.services.fechamento_de_run import fechar_runs

    async with _banco() as Sessao:
        async with Sessao() as db:
            db.add_all([
                WorkflowRun(task_id=t, workflow_hash="wf-1", workspace_id="ws-1", status=st,
                            node_stats={}, host=h)
                for t, st, h in [("a", "pending", "executor:ex-1"), ("b", "success", "executor:ex-1"),
                                 ("c", "pending", "executor:ex-2")]
            ])
            await db.commit()

        async with Sessao() as db:
            fechados = await fechar_runs(
                db, ["a", "b", "c"], de=("pending",), para="failed", mensagem="não chegou",
                categoria="dispatch", host="executor:ex-1",
            )
            assert [(r.task_id, r.status, r.error_category) for r in fechados] == [("a", "failed", "dispatch")]

        async with Sessao() as db:
            gravado = dict((await db.execute(select(WorkflowRun.task_id, WorkflowRun.status))).all())

    # 'b' already finished (the executor's outcome stands) and 'c' belongs to another executor.
    assert gravado == {"a": "failed", "b": "success", "c": "pending"}
    assert efeitos["contabilizados"] == [("a", "failed")]
    assert efeitos["publicados"] == [("a", "failed")]


@pytest.mark.asyncio
async def test_barreira_fecha_conta_e_publica_uma_vez(efeitos, monkeypatch):
    async with _banco() as Sessao:
        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=True)))
        cadeia = wes.CandidateList([_executor("pool-a")], tiers={}, allowed={"geo-01"}, mode="isolated")

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, cadeia, {}, False, db=db)

        run = await _o_run(Sessao)

    assert (run.status, run.error_category) == ("failed", "isolation")
    assert efeitos["contabilizados"] == [(run.task_id, "failed")]
    assert efeitos["publicados"] == [(run.task_id, "failed")]


@pytest.mark.asyncio
async def test_falha_na_contabilizacao_nao_perde_os_outros_runs_nem_a_conclusao(monkeypatch):
    """`account_terminal_run` swallows the usage_daily failure with a rollback, and
    the rollback expires the session's objects: the next run was counted with
    expired attributes, the completion was not published and the caller could no
    longer read `run.host` (the cancel to the host did not go out)."""
    from app.core import run_result_consumer as rrc
    from app.services.fechamento_de_run import fechar_runs

    publicados: list[str] = []

    async def _publica(run_ids, *, status, mensagem, extra=None):
        publicados.extend(run_ids)

    contados: list[tuple] = []

    async def _upsert(db, run, stats, first_close):
        await db.execute(select(WorkflowRun.task_id))    # opens the transaction, like the real upsert
        if run.task_id == "a":
            raise RuntimeError("usage_daily fora do ar")
        contados.append((run.task_id, run.status))

    monkeypatch.setattr(run_events_service, "publicar_conclusao", _publica)
    monkeypatch.setattr(rrc, "_upsert_usage_daily", _upsert)

    async with _banco() as Sessao:
        async with Sessao() as db:
            db.add_all([
                WorkflowRun(task_id=t, workflow_hash="wf-1", workspace_id="ws-1", status="pending",
                            node_stats={}, host=f"executor:{t}")
                for t in ("a", "b")
            ])
            await db.commit()

        async with Sessao() as db:
            fechados = await fechar_runs(
                db, ["a", "b"], de=("pending",), para="failed", mensagem="sumiu", categoria="dispatch",
            )
            hosts = [(r.task_id, r.host, r.status) for r in fechados]

    assert hosts == [("a", "executor:a", "failed"), ("b", "executor:b", "failed")]
    assert contados == [("b", "failed")]
    assert publicados == ["a", "b"]
