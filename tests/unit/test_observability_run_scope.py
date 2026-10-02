# tests/unit/test_observability_run_scope.py
"""Escopo de acesso ao historico de execucoes.

A observabilidade autorizava runs pelo `Workflow.workspace_id` — o workspace
ATUAL do workflow. Com a rota de mover workflow entre workspaces isso vira um
vazamento nos dois sentidos: os membros do workspace de destino passariam a ver
todo o historico produzido na origem (error_message, node_stats, host do
executor), e quem so tem acesso a origem perderia a visao dele.

`WorkflowRun.workspace_id` e gravado no despacho e nunca muda — e o dado
historico correto. E tambem o criterio que o WebSocket de logs sempre usou e o
que os artefatos ja usam.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.models import WorkflowRun
from app.services.observability_service import ObservabilityService, _run_filter


def _user(role="user"):
    u = MagicMock()
    u.role = role
    return u


# ── _run_filter ──────────────────────────────────────────────────────────────

def test_filtro_usa_o_workspace_do_run_e_nao_do_workflow():
    filtros = _run_filter(_user(), ["ws-1"])

    sql = str(filtros[0])
    assert "workflow_runs.workspace_id" in sql
    # A subquery antiga sobre workflows nao pode voltar: ela seguia o workflow
    # para o novo workspace, levando o historico junto.
    assert "workflows" not in sql


def test_filtro_nao_tem_escape_por_workspace_nulo():
    """O `OR workspace_id IS NULL` nao pode voltar.

    Ele existia para preservar historico legado, mas o preco era entregar esse
    historico — error_message, node_stats, host do executor — a QUALQUER usuario
    autenticado, de qualquer tenant. A migration 20260828_0001 atribuiu os runs
    antigos ao workspace certo e tornou a coluna NOT NULL, entao nao ha mais
    legado a acomodar.
    """
    sql = str(_run_filter(_user(), ["ws-1"])[0])

    assert "IS NULL" not in sql.upper()


def test_filtro_de_workflow_tambem_nao_tem_escape_por_nulo():
    """Mesma regressao, do lado da tabela `workflows` (_wf_filter)."""
    from app.services.observability_service import _wf_filter

    sql = str(_wf_filter(_user(), ["ws-1"])[0])

    assert "IS NULL" not in sql.upper()
    assert "workflows.workspace_id" in sql


def test_admin_nao_recebe_filtro_quando_o_chamador_pede_a_visao_total():
    """O bypass de admin deixou de ser deduzido de `user.role` dentro do service:
    quem chama diz `como_admin=True` (o router REST faz isso para admin global);
    sem o kwarg, admin recebe o mesmo recorte de membro."""
    assert _run_filter(_user("admin"), ["ws-1"], como_admin=True) == []
    assert _run_filter(_user("admin"), ["ws-1"]) != []


# ── get_run_detail ───────────────────────────────────────────────────────────

def _db_com_run(run):
    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = run
    return MagicMock(execute=AsyncMock(return_value=resultado))


def _run(workspace_id):
    r = MagicMock(spec=WorkflowRun)
    r.workspace_id = workspace_id
    r.workflow_hash = "wf-1"
    r.task_id = "run-1"
    r.id = 1
    r.status = "success"
    r.start_time = None
    r.end_time = None
    r.duration_seconds = 1.0
    r.error_message = None
    r.host = "executor:abc"
    r.node_stats = {}
    r.exit_code = 0
    return r


def _where(db, chamada=0):
    """Só o WHERE da query executada — a lista do SELECT tambem cita
    `workspace_id`, e olhar o SQL inteiro daria falso-positivo."""
    return str(db.execute.await_args_list[chamada].args[0]).split("WHERE", 1)[1]


@pytest.mark.asyncio
async def test_run_de_outro_workspace_nao_e_acessivel():
    """Cenario do move: o workflow foi para ws-destino, mas este run aconteceu
    em ws-origem e nao pertence a quem so alcanca o destino.

    O recorte vai na propria query, via `_run_filter` — a mesma regra da
    listagem e das metricas. Por isso o teste verifica o filtro no SQL e nao
    so o retorno: com o dublê devolvendo qualquer linha, uma checagem em Python
    passaria mesmo se a query tivesse deixado de filtrar.
    """
    from app.core.exceptions import RunNotFoundError

    db = _db_com_run(None)   # a linha nao volta porque o WHERE a excluiu

    with pytest.raises(RunNotFoundError):
        await ObservabilityService.get_run_detail(db, "run-1", _user(), ["ws-destino"])

    sql = _where(db)
    assert "workflow_runs.workspace_id IN" in sql
    assert "workflow_runs.workspace_id IS NULL" not in sql


@pytest.mark.asyncio
async def test_run_do_proprio_workspace_e_acessivel():
    db = _db_com_run(_run("ws-origem"))

    detalhe = await ObservabilityService.get_run_detail(db, "run-1", _user(), ["ws-origem"])

    assert detalhe["run_id"] == "run-1"




@pytest.mark.asyncio
async def test_admin_acessa_run_de_qualquer_workspace():
    db = _db_com_run(_run("ws-origem"))

    detalhe = await ObservabilityService.get_run_detail(db, "run-1", _user("admin"), [], como_admin=True)

    assert detalhe["run_id"] == "run-1"
    # Com `como_admin=True`, `_run_filter` devolve lista vazia: nenhum recorte por workspace.
    assert "workspace_id" not in _where(db)
