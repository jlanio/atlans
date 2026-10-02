# tests/unit/test_run_trigger_source.py
"""
Origem, autor e categoria de erro do run (docs/specs/historico-metricas.md §2).

Antes, `workflow_runs` não sabia dizer se um run nasceu de um clique, de um
webhook ou do cron — e `schedule_id` só chegava ao banco quando o agendamento
FALHAVA. O Histórico precisa dos três rótulos no INSERT do run `pending` e da
`error_category` em todo caminho que fecha um run como `failed` fora da fila.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NoExecutorAvailableError
from app.models.workflow_run import WorkflowRun
from app.services import workflow_execution_service as wes
from app.services.workflow_service import DispatchResult, WorkflowService


# ── Fábricas ──────────────────────────────────────────────────────────────────

def _wf(id_hash="wf-1", workspace_id="ws-1"):
    wf = MagicMock()
    wf.id_hash, wf.workspace_id, wf.flag_ative = id_hash, workspace_id, True
    wf.name = "Bacia diária"
    wf.pinned_outputs = wf.pin_metadata = None
    wf.definition = {"nodes": [{"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}}], "edges": []}
    return wf


def _executor(id_hash="ag-1"):
    ag = MagicMock()
    ag.id_hash, ag.name, ag.public_key = id_hash, id_hash, "PEM"
    return ag


def _db_dispatch(rowcount=1):
    """INSERT/commit + o UPDATE pending→running (rowcount)."""
    atualizado = MagicMock(); atualizado.rowcount = rowcount
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock(return_value=atualizado)
    return db


def _runs_adicionados(db) -> list[WorkflowRun]:
    return [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], WorkflowRun)]


def _servico_com_dispatch_capturado():
    """WorkflowService com tudo antes do despacho mockado; devolve (service, kwargs)."""
    wf = _wf()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    service = WorkflowService(db)
    service.crud = MagicMock(db=db)
    service._load_workflow = AsyncMock(return_value=(wf, wf.definition))
    service._resolve_candidates = AsyncMock(return_value=[_executor()])
    capturado: dict = {}
    service._dispatch_job = AsyncMock(
        side_effect=lambda *a, **kw: capturado.update(kw) or DispatchResult(id="task-1")
    )
    return service, capturado


def _patches_do_start_analysis():
    return (
        patch("app.services.disabled_nodes_service.disabled_names", new=AsyncMock(return_value=set())),
        patch("app.services.workflow_service.resolve_credentials_from_ids", new=AsyncMock(return_value={})),
        patch("app.services.workflow_service._validate_trigger_credentials_only", new=AsyncMock()),
    )


# ══════════════════════════════════════════════════════════════════════════════
# start_analysis → _dispatch_job: os rótulos passam intactos
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_start_analysis_repassa_origem_autor_e_agendamento():
    service, capturado = _servico_com_dispatch_capturado()
    a, b, c = _patches_do_start_analysis()
    with a, b, c:
        await service.start_analysis(
            "wf-1", inputs={}, autenticar_entrada=False,
            triggered_by="usr-1", trigger_source="retry", schedule_id=None,
        )
    assert capturado["trigger_source"] == "retry"
    assert capturado["triggered_by"] == "usr-1"
    assert capturado["schedule_id"] is None


@pytest.mark.asyncio
async def test_start_analysis_agendado_leva_schedule_id():
    service, capturado = _servico_com_dispatch_capturado()
    a, b, c = _patches_do_start_analysis()
    with a, b, c:
        await service.start_analysis(
            "wf-1", inputs={}, autenticar_entrada=False,
            trigger_source="schedule", schedule_id=7,
        )
    assert capturado["trigger_source"] == "schedule"
    assert capturado["schedule_id"] == 7
    assert capturado["triggered_by"] is None   # cron não tem usuário


@pytest.mark.asyncio
async def test_chamador_antigo_sem_os_parametros_novos_continua_funcionando():
    """Compatibilidade: quem não passa nada cai em "manual" sem autor."""
    service, capturado = _servico_com_dispatch_capturado()
    a, b, c = _patches_do_start_analysis()
    with a, b, c:
        result = await service.start_analysis("wf-1", inputs={}, autenticar_entrada=False)
    assert result.id == "task-1"
    assert capturado["trigger_source"] == "manual"
    assert capturado["triggered_by"] is None
    assert capturado["schedule_id"] is None


# ══════════════════════════════════════════════════════════════════════════════
# _dispatch_job: INSERT do run pending e as categorias de erro do servidor
# ══════════════════════════════════════════════════════════════════════════════

def _patches_do_dispatch(reg):
    return (
        patch.object(wes, "executor_registry", reg),
        patch.object(wes, "inject_credentials", AsyncMock(side_effect=lambda d, **k: d)),
        patch.object(wes, "build_job_message", MagicMock(return_value={"envelope": {}})),
        patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()),
    )


@pytest.mark.asyncio
async def test_insert_do_run_pending_grava_os_tres_rotulos():
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=True)
    db = _db_dispatch()
    a, b, c, d = _patches_do_dispatch(reg)
    with a, b, c, d:
        result = await wes._dispatch_job(
            _wf(), _wf().definition, [_executor()], {}, False, db=db,
            trigger_source="schedule", triggered_by=None, schedule_id=7,
        )
    run = _runs_adicionados(db)[0]
    assert result.id == run.task_id
    assert run.trigger_source == "schedule"
    assert run.triggered_by is None
    assert run.schedule_id == 7
    assert run.error_category is None          # caminho feliz: sem categoria
    # A gravação é no INSERT — o primeiro commit já leva os rótulos, sem
    # UPDATE extra no caminho crítico.
    assert db.commit.await_count == 2          # INSERT + pending→running


@pytest.mark.asyncio
async def test_dispatch_sem_rotulos_grava_nulos():
    """`_dispatch_job` chamado direto (testes antigos, chamadores legados)."""
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=True)
    db = _db_dispatch()
    a, b, c, d = _patches_do_dispatch(reg)
    with a, b, c, d:
        await wes._dispatch_job(_wf(), _wf().definition, [_executor()], {}, False, db=db)
    run = _runs_adicionados(db)[0]
    assert run.trigger_source is None and run.triggered_by is None and run.schedule_id is None


@pytest.mark.asyncio
async def test_despacho_esgotado_marca_no_executor():
    """Todos recusam: a categoria da coluna é a FIXA ("no_executor"), não a
    granular da exceção — "no_executor_chain" nem cabe em VARCHAR(16)."""
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=False)
    cadeia = wes.CandidateList(
        [_executor("ag-1"), _executor("ag-2")], tiers={}, allowed=None, mode="pool",
        exhausted_message="Nenhum executor do pool aceitou.", exhausted_category="no_executor_chain",
    )
    db = _db_dispatch()
    a, b, c, d = _patches_do_dispatch(reg)
    with a, b, c, d:
        with pytest.raises(NoExecutorAvailableError) as exc:
            await wes._dispatch_job(_wf(), _wf().definition, cadeia, {}, False, db=db, trigger_source="manual")
    run = _runs_adicionados(db)[0]
    assert run.status == "failed"
    assert run.error_category == "no_executor"
    assert len(run.error_category) <= 16
    assert exc.value.category == "no_executor_chain"   # a exceção não muda
    assert run.trigger_source == "manual"


@pytest.mark.asyncio
async def test_barreira_de_isolamento_marca_isolation():
    intruso = _executor("pool-a")
    cadeia = wes.CandidateList([intruso], tiers={"pool-a": "pool"}, allowed={"geo-01"}, mode="isolated")
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=True)
    db = _db_dispatch()
    a, b, c, d = _patches_do_dispatch(reg)
    with a, b, c, d:
        with pytest.raises(NoExecutorAvailableError):
            await wes._dispatch_job(_wf(), _wf().definition, cadeia, {}, False, db=db)
    run = _runs_adicionados(db)[0]
    assert run.status == "failed"
    assert run.error_category == "isolation"
    reg.send_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_excecao_no_despacho_marca_dispatch():
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=True)
    db = _db_dispatch()
    with patch.object(wes, "executor_registry", reg), \
         patch.object(wes, "inject_credentials", AsyncMock(side_effect=TypeError("payload inválido"))), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()):
        with pytest.raises(TypeError):
            await wes._dispatch_job(_wf(), _wf().definition, [_executor()], {}, False, db=db)
    run = _runs_adicionados(db)[0]
    assert run.status == "failed"
    assert run.error_category == "dispatch"


@pytest.mark.asyncio
async def test_rede_de_seguranca_nao_reescreve_categoria_do_despacho_esgotado():
    """`_close_orphan_dispatch` é idempotente: o caminho (4) já fechou o run
    com "no_executor" e o except externo não pode trocar por "dispatch"."""
    reg = MagicMock(); reg.send_job = AsyncMock(return_value=False)
    db = _db_dispatch()
    a, b, c, d = _patches_do_dispatch(reg)
    with a, b, c, d:
        with pytest.raises(NoExecutorAvailableError):
            await wes._dispatch_job(_wf(), _wf().definition, [_executor()], {}, False, db=db)
    assert _runs_adicionados(db)[0].error_category == "no_executor"


# ══════════════════════════════════════════════════════════════════════════════
# Chamadores: execute → manual · retry → retry · webhook → webhook
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def rota_com_servico(client, mock_current_user):
    from app.api.dependencies import (
        get_accessible_workflow_with_role,
        get_workflow_service,
    )
    from app.main import app

    svc = MagicMock()
    svc.start_analysis = AsyncMock(return_value=MagicMock(id="task-1"))
    svc.get_workflow_by_hash = AsyncMock(return_value=_wf())

    async def _svc():
        return svc

    async def _wf_com_papel(id_hash: str):
        return _wf(id_hash), "owner"

    app.dependency_overrides[get_workflow_service] = _svc
    app.dependency_overrides[get_accessible_workflow_with_role] = _wf_com_papel
    yield client, svc, mock_current_user
    for dep in (get_workflow_service, get_accessible_workflow_with_role):
        app.dependency_overrides.pop(dep, None)


async def test_execute_dispara_como_manual_com_o_usuario(rota_com_servico):
    ac, svc, usuario = rota_com_servico
    resp = await ac.post("/workflows/wf-1/execute", json={"inputs": {}})
    assert resp.status_code == 202, resp.text
    kwargs = svc.start_analysis.await_args.kwargs
    assert kwargs["trigger_source"] == "manual"
    assert kwargs["triggered_by"] == usuario.id_hash
    assert "schedule_id" not in kwargs or kwargs["schedule_id"] is None


async def test_retry_dispara_como_retry_com_o_usuario(rota_com_servico):
    ac, svc, usuario = rota_com_servico
    # A rota valida que o run existe e pertence ao workflow.
    from app.api.dependencies import get_db
    from app.main import app

    res = MagicMock(); res.scalar_one_or_none.return_value = "run-1"
    db = MagicMock(); db.execute = AsyncMock(return_value=res)

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    try:
        resp = await ac.post("/workflows/wf-1/runs/run-1/retry")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 202, resp.text
    kwargs = svc.start_analysis.await_args.kwargs
    assert kwargs["trigger_source"] == "retry"
    assert kwargs["triggered_by"] == usuario.id_hash


async def test_webhook_dispara_como_webhook_sem_usuario(client):
    """Sem `triggered_by`: o chamador é um sistema externo — inventar um dono
    abriria credenciais privadas a quem só tem o token do gatilho."""
    from app.api.dependencies import get_workflow_service
    from app.main import app

    svc = MagicMock()
    svc.get_workflow_by_hash = AsyncMock(return_value=_wf())
    svc.start_analysis = AsyncMock(return_value=MagicMock(id="task-1", has_response_node=False))
    app.dependency_overrides[get_workflow_service] = lambda: svc
    try:
        resp = await client.post("/webhook/execute/wf-1", json={"x": 1})
    finally:
        app.dependency_overrides.pop(get_workflow_service, None)
    assert resp.status_code in (200, 202), resp.text
    kwargs = svc.start_analysis.await_args.kwargs
    assert kwargs["trigger_source"] == "webhook"
    assert kwargs.get("triggered_by") is None
    assert kwargs.get("schedule_id") is None


# ══════════════════════════════════════════════════════════════════════════════
# Agendador: schedule + schedule_id no caminho feliz E no de falha
# ══════════════════════════════════════════════════════════════════════════════

def _sessao(db):
    @asynccontextmanager
    async def _ctx():
        yield db
    return _ctx


@pytest.mark.asyncio
async def test_agendador_rotula_o_despacho_normal():
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(return_value=MagicMock(id="task-1"))
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.services.execution_alert_service.record_success", AsyncMock(return_value=False)):
        await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)
    kwargs = service.start_analysis.await_args.kwargs
    assert kwargs["trigger_source"] == "schedule"
    assert kwargs["schedule_id"] == 7
    assert "triggered_by" not in kwargs        # cron não inventa usuário


@pytest.mark.asyncio
async def test_agendador_sem_executor_rotula_o_run_sintetico():
    from app.core.async_scheduler import AsyncScheduler

    db = MagicMock(); db.add = MagicMock(); db.commit = AsyncMock()
    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf())
    service.start_analysis = AsyncMock(
        side_effect=NoExecutorAvailableError("Pool vazio.", category="no_dedicated_executor"),
    )
    with patch("app.core.async_scheduler.AsyncSessionLocal", _sessao(db)), \
         patch("app.services.workflow_service.WorkflowService", MagicMock(return_value=service)), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()), \
         patch("app.services.execution_alert_service.record_failure", AsyncMock(return_value=True)):
        with pytest.raises(NoExecutorAvailableError):
            await AsyncScheduler()._fire_workflow("wf-1", schedule_id=7)
    run = db.add.call_args.args[0]
    assert isinstance(run, WorkflowRun)
    assert run.trigger_source == "schedule"
    assert run.schedule_id == 7
    assert run.triggered_by is None
    assert run.error_category == "no_executor"


# ══════════════════════════════════════════════════════════════════════════════
# Consumer: categoria do job_result só no desfecho failed
# ══════════════════════════════════════════════════════════════════════════════

def _payload(status, categoria=None):
    return {
        "task_id": "run-1", "status": status,
        "error_message": "Timeout no WFS" if status == "failed" else None,
        "error_category": categoria, "stats": {},
        "end_time": "2026-09-06T03:00:00+00:00", "duration_seconds": 30.0,
    }


@pytest.mark.asyncio
async def test_consumer_grava_categoria_do_flow_no_run_failed():
    from app.core.run_result_consumer import _update_run_status

    run, db = MagicMock(), MagicMock(commit=AsyncMock())
    await _update_run_status(db, run, _payload("failed", "timeout"))
    assert run.error_category == "timeout"


@pytest.mark.asyncio
async def test_consumer_nao_carimba_categoria_em_sucesso_nem_cancelamento():
    from app.core.run_result_consumer import _update_run_status

    for status in ("success", "cancelled"):
        run, db = MagicMock(), MagicMock(commit=AsyncMock())
        # Payload antigo/forjado: categoria presente mesmo sem falha.
        await _update_run_status(db, run, _payload(status, "internal"))
        assert run.error_category is None, status


@pytest.mark.asyncio
async def test_consumer_ignora_categoria_fora_do_vocabulario():
    """Um executor fora da taxonomia não pode derrubar o commit do fechamento —
    nem gravar um texto mutilado ("no_executor_chai") que a tela agruparia
    como se fosse outra categoria: fora do vocabulário, fica None."""
    from app.core.run_result_consumer import _update_run_status

    run, db = MagicMock(), MagicMock(commit=AsyncMock())
    await _update_run_status(db, run, _payload("failed", "x" * 40))
    assert run.error_category is None

    run2 = MagicMock()
    await _update_run_status(db, run2, _payload("failed", "no_executor_chain"))
    assert run2.error_category is None

    run3 = MagicMock()
    await _update_run_status(db, run3, _payload("failed", " Timeout "))
    assert run3.error_category == "timeout"


# ══════════════════════════════════════════════════════════════════════════════
# WS router: executor caiu → executor_lost (desconexão e watchdog passam aqui)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_orfaos_do_executor_recebem_executor_lost(monkeypatch):
    from app.api.routers.executor_ws import orfaos as R

    orfao = WorkflowRun(
        task_id="run-1", workflow_hash="wf-1", workspace_id="ws-1",
        status="running", host="executor:ex-1", node_stats={},
        start_time=datetime(2026, 9, 6, 3, 0, tzinfo=timezone.utc),
    )
    res = MagicMock(); res.scalars.return_value.all.return_value = [orfao]
    db = MagicMock(); db.execute = AsyncMock(return_value=res); db.commit = AsyncMock()

    class _Pipe:
        async def __aenter__(self): return self
        async def __aexit__(self, *_a): return False
        def rpush(self, *_a): pass
        def ltrim(self, *_a): pass
        def expire(self, *_a): pass
        def publish(self, *_a): pass
        async def execute(self): return []

    rc = MagicMock(); rc.pipeline = MagicMock(return_value=_Pipe())
    monkeypatch.setattr(R, "get_session_async", _sessao(db))
    with patch("app.core.redis.get_redis_pool", return_value=rc), \
         patch("app.core.run_result_consumer.account_terminal_run", AsyncMock()) as contabiliza:
        await R._fail_orphan_runs("ex-1")

    assert orfao.status == "failed"
    assert orfao.error_category == "executor_lost"
    assert orfao.error_message == "Executor desconectou durante a execução."
    contabiliza.assert_awaited_once()
    db.commit.assert_awaited()
