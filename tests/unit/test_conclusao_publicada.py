# tests/unit/test_conclusao_publicada.py
"""The completion of a run that the SERVER closed reaches the panel.

Whoever closed a run without going through job_result (canceled before reaching
the executor, canceled with the executor offline, orphaned, undelivered, lost in
reconciliation) did not publish `__workflow_complete__`: the editor answered
"aguardando o executor interromper o job…" (waiting for the executor to stop
the job) and waited forever for an event nobody would send.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.constants import MAX_EVENTOS_NO_HISTORICO, REDIS_TTL_1H, WORKFLOW_COMPLETE_NODE
from app.models.workflow_run import WorkflowRun
from app.services import run_events_service as RES


class _Pipeline:
    def __init__(self, dono):
        self.dono = dono
        self.comandos = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def rpush(self, chave, valor):
        self.comandos.append(("rpush", chave, valor))

    def ltrim(self, chave, inicio, fim):
        self.comandos.append(("ltrim", chave, inicio, fim))

    def expire(self, chave, ttl):
        self.comandos.append(("expire", chave, ttl))

    def publish(self, canal, valor):
        self.comandos.append(("publish", canal, valor))

    async def execute(self):
        self.dono.executados.append(self.comandos)


class _RedisFalso:
    def __init__(self):
        self.executados = []

    def pipeline(self, transaction=True):
        assert transaction is False
        return _Pipeline(self)


@pytest.fixture
def redis(monkeypatch):
    falso = _RedisFalso()
    monkeypatch.setattr(RES, "get_redis_pool", lambda: falso)
    return falso


# ── O publicador ─────────────────────────────────────────────────────────────

async def test_cancelado_sai_no_formato_do_job_result(redis):
    """Same format that job_result publishes for a canceled job: level
    `info`, no error taxonomy — a cancellation is not a failure."""
    await RES.publicar_conclusao(["run-1"], status="cancelled", mensagem="Cancelado antes.")

    [comandos] = redis.executados
    assert [c[0] for c in comandos] == ["rpush", "ltrim", "expire", "publish"]
    assert comandos[0][1] == "workflow:run-1:history"
    assert comandos[1][2:] == (-MAX_EVENTOS_NO_HISTORICO, -1)
    assert comandos[2][2] == REDIS_TTL_1H
    assert comandos[3][1] == "workflow:run-1:events"
    # The history and the channel receive the SAME event: whoever opens the panel
    # later rebuilds from the history what whoever was watching saw live.
    assert comandos[0][2] == comandos[3][2]

    evento = json.loads(comandos[3][2])
    assert evento["run_id"] == "run-1"
    assert evento["node"] == WORKFLOW_COMPLETE_NODE
    assert (evento["kind"], evento["level"], evento["status"]) == ("lifecycle", "info", "cancelled")
    assert evento["error"] == "Cancelado antes."
    assert evento["extra"] is None


async def test_falha_leva_nivel_de_erro_e_a_taxonomia(redis):
    await RES.publicar_conclusao(
        ["run-1"], status="failed", mensagem="perdido",
        extra={"error_category": "transient", "retryable": True},
    )

    evento = json.loads(redis.executados[0][3][2])
    assert (evento["level"], evento["status"]) == ("error", "failed")
    assert evento["extra"] == {"error_category": "transient", "retryable": True}


async def test_centenas_de_runs_vao_em_blocos(redis):
    """One pipeline per batch: an executor that drops with 201 runs does not turn
    into 804 sequential Redis round trips, nor a command buffer with no ceiling."""
    ids = [f"run-{i}" for i in range(RES._BLOCO_DE_PUBLICACAO + 1)]

    await RES.publicar_conclusao(ids, status="failed", mensagem="x")

    assert [len(p) // 4 for p in redis.executados] == [RES._BLOCO_DE_PUBLICACAO, 1]
    publicados = [c[1] for p in redis.executados for c in p if c[0] == "publish"]
    assert publicados == [f"workflow:{i}:events" for i in ids]


async def test_lista_vazia_nao_toca_no_redis(monkeypatch):
    monkeypatch.setattr(RES, "get_redis_pool", MagicMock(side_effect=AssertionError("tocou")))

    await RES.publicar_conclusao([], status="failed", mensagem="x")


async def test_orfaos_publicam_falha_repetivel(monkeypatch):
    """No run closed by the watchdog failed because of its content: retrying is safe."""
    from contextlib import asynccontextmanager

    from app.api.routers.executor_ws import orfaos as ORF

    orfaos = [_run("running"), WorkflowRun(
        task_id="job-2", workflow_hash="wf-1", workspace_id="ws-1",
        status="running", node_stats={}, host="executor:ag-1",
    )]
    selecionados = MagicMock()
    selecionados.scalars.return_value.all.return_value = orfaos
    db = MagicMock(commit=AsyncMock())
    db.execute = AsyncMock(side_effect=[selecionados, MagicMock(rowcount=1), MagicMock(rowcount=1)])

    @asynccontextmanager
    async def _sessao():
        yield db

    publica = AsyncMock()
    monkeypatch.setattr(ORF, "get_session_async", _sessao)
    monkeypatch.setattr(RES, "publicar_conclusao", publica)
    monkeypatch.setattr("app.core.run_result_consumer.account_terminal_run", AsyncMock())

    await ORF._fail_orphan_runs("ag-1")

    publica.assert_awaited_once_with(
        ["job-1", "job-2"], status="failed", mensagem="Executor desconectou durante a execução.",
        extra={"error_category": "transient", "retryable": True},
    )


# ── Whoever cancels publishes ────────────────────────────────────────────────

def _run(status):
    return WorkflowRun(
        task_id="job-1", workflow_hash="wf-1", workspace_id="ws-1",
        status=status, node_stats={}, host="executor:ag-1",
    )


def _db(run, rowcount=1):
    """db.execute: 1º SELECT devolve o run; 2º UPDATE devolve o rowcount."""
    selecionado = MagicMock()
    selecionado.scalar_one_or_none = MagicMock(return_value=run)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[selecionado, MagicMock(rowcount=rowcount)])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


async def _cancelar(run, *, entregue, rowcount=1, publica=None, presenca=False):
    from app.services import workflow_execution_service as svc

    publica = publica or AsyncMock()
    registry = MagicMock()
    registry.send_json = AsyncMock(return_value=entregue)
    registry.presence_or_unknown = AsyncMock(return_value=presenca)
    with (
        patch.object(svc, "executor_registry", registry),
        patch("app.core.run_result_consumer.account_terminal_run", new=AsyncMock()),
        patch.object(RES, "publicar_conclusao", publica),
    ):
        outcome = await svc.cancel_run(_db(run, rowcount), "job-1", user_id="u", como_admin=True)
    return outcome, publica


async def test_cancelar_run_na_fila_publica_a_conclusao():
    outcome, publica = await _cancelar(_run("pending"), entregue=True)

    assert outcome == "cancelled"
    publica.assert_awaited_once_with(
        ["job-1"], status="cancelled", mensagem="Cancelado antes de ser atribuído a um executor.",
        extra=None,
    )


async def test_cancelar_com_o_executor_fora_do_ar_publica_a_conclusao():
    outcome, publica = await _cancelar(_run("running"), entregue=False)

    assert outcome == "cancelled"
    publica.assert_awaited_once()
    assert publica.await_args.kwargs["status"] == "cancelled"
    assert "fora do ar" in publica.await_args.kwargs["mensagem"]


async def test_pedido_entregue_ao_executor_nao_publica():
    """The one that closes it is the executor's job_result, which publishes the
    real completion — publishing here too would be a premature 'canceled' (the
    job may finish in the meantime)."""
    outcome, publica = await _cancelar(_run("running"), entregue=True)

    assert outcome == "requested"
    publica.assert_not_awaited()


async def test_perder_a_corrida_para_o_resultado_nao_publica():
    run = _run("running")
    outcome, publica = await _cancelar(run, entregue=False, rowcount=0)

    assert outcome == "already_finished"
    publica.assert_not_awaited()


async def test_redis_fora_nao_desfaz_o_cancelamento():
    """Best-effort: the run is already closed in the database; the panel finds
    out when it reopens."""
    outcome, _ = await _cancelar(
        _run("running"), entregue=False, publica=AsyncMock(side_effect=ConnectionError("redis")),
    )

    assert outcome == "cancelled"


@pytest.mark.parametrize("presenca", [True, None])
async def test_envio_que_falha_com_o_executor_vivo_nao_fecha_o_run(presenca):
    """`send_json` also fails with the executor online (signing key missing,
    relay restarting, Redis erroring). Closing the run in those cases would
    report "cancelado" with the job running — it stays a 503, as before."""
    from app.core.exceptions import NoExecutorAvailableError

    run = _run("running")
    with pytest.raises(NoExecutorAvailableError):
        await _cancelar(run, entregue=False, presenca=presenca)

    assert run.status == "running"
