# tests/unit/test_conclusao_publicada.py
"""A conclusão de um run que o SERVIDOR fechou chega ao painel.

Quem fecha um run sem passar pelo job_result (cancelado antes de chegar ao
executor, cancelado com o executor fora do ar, órfão, não entregue, perdido na
reconciliação) não publicava o `__workflow_complete__`: o editor respondia
"aguardando o executor interromper o job…" e esperava para sempre um evento
que ninguém mandaria.
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
    """Mesmo formato que o job_result publica para um job cancelado: nível
    `info`, sem taxonomia de erro — um cancelamento não é falha."""
    await RES.publicar_conclusao(["run-1"], status="cancelled", mensagem="Cancelado antes.")

    [comandos] = redis.executados
    assert [c[0] for c in comandos] == ["rpush", "ltrim", "expire", "publish"]
    assert comandos[0][1] == "workflow:run-1:history"
    assert comandos[1][2:] == (-MAX_EVENTOS_NO_HISTORICO, -1)
    assert comandos[2][2] == REDIS_TTL_1H
    assert comandos[3][1] == "workflow:run-1:events"
    # O histórico e o canal recebem o MESMO evento: quem abre o painel depois
    # reconstrói pelo histórico o que quem estava olhando viu ao vivo.
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
    """Um pipeline por bloco: um executor que cai com 201 runs não vira 804
    idas ao Redis em série, nem um buffer de comandos sem teto."""
    ids = [f"run-{i}" for i in range(RES._BLOCO_DE_PUBLICACAO + 1)]

    await RES.publicar_conclusao(ids, status="failed", mensagem="x")

    assert [len(p) // 4 for p in redis.executados] == [RES._BLOCO_DE_PUBLICACAO, 1]
    publicados = [c[1] for p in redis.executados for c in p if c[0] == "publish"]
    assert publicados == [f"workflow:{i}:events" for i in ids]


async def test_lista_vazia_nao_toca_no_redis(monkeypatch):
    monkeypatch.setattr(RES, "get_redis_pool", MagicMock(side_effect=AssertionError("tocou")))

    await RES.publicar_conclusao([], status="failed", mensagem="x")


async def test_orfaos_publicam_falha_repetivel(monkeypatch):
    """Nenhum run fechado pelo watchdog falhou pelo conteúdo: repetir é seguro."""
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


# ── Quem cancela publica ─────────────────────────────────────────────────────

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
    """Quem fecha é o job_result do executor, que publica a conclusão real —
    publicar aqui também seria um 'cancelado' antes da hora (o job pode terminar
    no intervalo)."""
    outcome, publica = await _cancelar(_run("running"), entregue=True)

    assert outcome == "requested"
    publica.assert_not_awaited()


async def test_perder_a_corrida_para_o_resultado_nao_publica():
    run = _run("running")
    outcome, publica = await _cancelar(run, entregue=False, rowcount=0)

    assert outcome == "already_finished"
    publica.assert_not_awaited()


async def test_redis_fora_nao_desfaz_o_cancelamento():
    """Best-effort: o run já está fechado no banco; o painel o descobre ao
    reabrir."""
    outcome, _ = await _cancelar(
        _run("running"), entregue=False, publica=AsyncMock(side_effect=ConnectionError("redis")),
    )

    assert outcome == "cancelled"


@pytest.mark.parametrize("presenca", [True, None])
async def test_envio_que_falha_com_o_executor_vivo_nao_fecha_o_run(presenca):
    """`send_json` também falha com o executor no ar (chave de assinatura
    ausente, relay reiniciando, Redis com erro). Fechar o run nesses casos daria
    "cancelado" com o job rodando — segue sendo 503, como antes."""
    from app.core.exceptions import NoExecutorAvailableError

    run = _run("running")
    with pytest.raises(NoExecutorAvailableError):
        await _cancelar(run, entregue=False, presenca=presenca)

    assert run.status == "running"
