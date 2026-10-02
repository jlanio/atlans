"""Fechar um run pelo servidor: um compare-and-swap só, para os oito caminhos.

Os fechamentos do servidor (vigias de órfãos, cancelamento) gravam o desfecho
com UPDATE condicional no status: quem chega depois de um desfecho já gravado
perde a corrida e não conta o uso de novo. Os caminhos do despacho não: o
"nenhum executor aceitou", a barreira de isolamento e a rede de segurança das
exceções atribuíam `run.status` e gravavam por PK — o segundo escritor. Entre o
INSERT do run e esse fechamento passam segundos (credenciais, cifra, envio a
cada candidato) com o run já na tela, e um cancelamento do usuário nessa janela
virava "falhou": o 'cancelled' confirmado pela API era apagado e o uso contado
duas vezes. Esses caminhos também não publicavam o `__workflow_complete__`.

Banco de verdade (SQLite): a corrida só existe entre duas sessões.
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
    """Contabilização e publicação, contadas por run."""
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
    """O que `cancel_run` faz com um run ainda 'pending', noutra sessão."""
    async with Sessao() as outra:
        await outra.execute(
            update(WorkflowRun).where(WorkflowRun.status == "pending")
            .values(status="cancelled", error_message="Cancelado antes de ser atribuído a um executor.")
        )
        await outra.commit()


async def _o_run(Sessao) -> WorkflowRun:
    async with Sessao() as db:
        return (await db.execute(select(WorkflowRun))).scalar_one()


# ── O cancelamento no meio do despacho vence ─────────────────────────────────

@pytest.mark.asyncio
async def test_nenhum_executor_aceitou_nao_apaga_o_cancelamento(efeitos, monkeypatch):
    async with _banco() as Sessao:
        async def _envio(executor_id, job):
            await _cancelar_pela_api(Sessao)    # o usuário cancela enquanto o candidato responde
            return False                        # ...e o candidato recusa

        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(side_effect=_envio)))

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(Sessao)

    assert run.status == "cancelled"            # antes: 'failed', por cima do cancelamento
    assert efeitos["contabilizados"] == []      # quem fechou (o cancelamento) já contou


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


# ── Sem corrida: fecha, conta e publica UMA vez ──────────────────────────────

@pytest.mark.asyncio
async def test_despacho_esgotado_fecha_conta_e_publica_uma_vez(efeitos, monkeypatch):
    """O `raise` do caminho (4) passa pela rede de segurança do `except`: ela não
    pode fechar de novo, nem contar, nem publicar outra conclusão."""
    async with _banco() as Sessao:
        monkeypatch.setattr(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d))
        monkeypatch.setattr(wes, "executor_registry", MagicMock(send_job=AsyncMock(return_value=False)))

        async with Sessao() as db:
            with pytest.raises(NoExecutorAvailableError):
                await wes._dispatch_job(_wf(), _DEFINICAO, [_executor()], {}, False, db=db)

        run = await _o_run(Sessao)

    assert (run.status, run.error_category) == ("failed", "no_executor")
    assert efeitos["contabilizados"] == [(run.task_id, "failed")]
    # O painel aberto recebe a conclusão, como nos outros fechamentos do servidor.
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

    # 'b' já terminou (o desfecho do executor vale) e 'c' é de outro executor.
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
    """`account_terminal_run` engole a falha do usage_daily com um rollback, e o
    rollback expira os objetos da sessão: o run seguinte era contado com
    atributos expirados, a conclusão não era publicada e quem chama não lia mais
    `run.host` (o cancel ao host não saía)."""
    from app.core import run_result_consumer as rrc
    from app.services.fechamento_de_run import fechar_runs

    publicados: list[str] = []

    async def _publica(run_ids, *, status, mensagem, extra=None):
        publicados.extend(run_ids)

    contados: list[tuple] = []

    async def _upsert(db, run, stats, first_close):
        await db.execute(select(WorkflowRun.task_id))    # abre a transação, como o upsert real
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
