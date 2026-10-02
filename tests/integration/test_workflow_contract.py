# tests/integration/test_workflow_contract.py
"""
Testes de contrato HTTP para o workflows_router.
Verificam que cada endpoint retorna o status code esperado — não testam lógica de negócio.
Objetivo: garantir que refatorações (Fase 2+) não alterem os contratos HTTP.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import WorkflowNotFoundError


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fake_workflow(id_hash="wf-abc123", workspace_id="ws-test-001"):
    wf = MagicMock()
    wf.id_hash = id_hash
    wf.name = "Workflow de Teste"
    wf.workspace_id = workspace_id
    wf.flag_ative = True
    wf.deleted_at = None
    wf.definition = {"nodes": [], "edges": []}
    wf.description = None
    wf.version = "1.0"
    wf.priority = 0
    wf.group_id = None
    wf.notification_url = None
    wf.portal_access = "disabled"
    wf.portal_shared_with = None
    wf.pinned_outputs = None
    wf.pin_metadata = None
    wf.params_schema = None
    wf.id = 1
    wf.created_at = "2026-01-01T00:00:00"
    wf.updated_at = "2026-01-01T00:00:00"
    wf.created_by_id = None
    wf.updated_by_id = None
    return wf


@pytest.fixture
def override_workflow_deps(client):
    """
    Injeta mocks do WorkflowService e do acesso ao workflow.
    Retorna (client, mock_service) para que os testes possam configurar comportamentos.

    Todas as rotas `/{id_hash}` pedem `workflow_com_papel(minimo)`, que se
    apoia em `get_accessible_workflow_with_role`: trocar esta troca o
    (workflow, papel) de todas, e a comparação do papel continua valendo.
    """
    from app.main import app
    from app.api.dependencies import (
        get_workflow_service,
        get_accessible_workflow_with_role,
    )

    svc = AsyncMock()
    svc.list_workflows_metadata_by_ids = AsyncMock(return_value=[])
    svc.delete_workflow = AsyncMock()
    svc.list_versions = AsyncMock(return_value=[])

    async def _svc():
        return svc

    async def _accessible_wf_with_role(id_hash: str):
        return _fake_workflow(id_hash=id_hash), "owner"

    app.dependency_overrides[get_workflow_service] = _svc
    app.dependency_overrides[get_accessible_workflow_with_role] = _accessible_wf_with_role

    yield client, svc

    for dep in [get_workflow_service, get_accessible_workflow_with_role]:
        app.dependency_overrides.pop(dep, None)


# ── Listagem ───────────────────────────────────────────────────────────────────

class TestListWorkflows:
    async def test_returns_200(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.get("/workflows")
        assert res.status_code == 200

    async def test_returns_list(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.get("/workflows")
        assert isinstance(res.json(), list)


# ── Leitura individual ─────────────────────────────────────────────────────────

class TestReadWorkflow:
    async def test_returns_200_for_existing(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.get("/workflows/wf-abc123")
        assert res.status_code == 200

    async def test_returns_404_when_not_found(self, client):
        """Sem override do acesso ao workflow: usa a implementação real, que
        levanta 404 antes de consultar o papel (o `db` nem é tocado)."""
        from unittest.mock import MagicMock

        from app.main import app
        from app.api.dependencies import (
            get_accessible_workflow_with_role, get_db, get_workflow_service,
        )

        svc = AsyncMock()
        svc.get_workflow_by_hash = AsyncMock(side_effect=WorkflowNotFoundError("nao-existe"))
        db = MagicMock()

        async def _svc():
            return svc

        async def _db():
            yield db

        app.dependency_overrides[get_workflow_service] = _svc
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides.pop(get_accessible_workflow_with_role, None)

        res = await client.get("/workflows/nao-existe")
        assert res.status_code == 404
        db.execute.assert_not_called()

        app.dependency_overrides.pop(get_workflow_service, None)
        app.dependency_overrides.pop(get_db, None)


# ── Exclusão ───────────────────────────────────────────────────────────────────

class TestDeleteWorkflow:
    async def test_returns_200(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.delete("/workflows/wf-abc123")
        assert res.status_code == 200

    async def test_calls_delete_service(self, override_workflow_deps):
        ac, svc = override_workflow_deps
        await ac.delete("/workflows/wf-abc123")
        svc.delete_workflow.assert_called_once()


# ── Versões ────────────────────────────────────────────────────────────────────

class TestWorkflowVersions:
    async def test_list_versions_returns_200(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.get("/workflows/wf-abc123/versions")
        assert res.status_code == 200

    async def test_list_versions_returns_list(self, override_workflow_deps):
        ac, _ = override_workflow_deps
        res = await ac.get("/workflows/wf-abc123/versions")
        assert isinstance(res.json(), list)


# ── Execução manual (canvas / UI) ──────────────────────────────────────────────

class TestExecuteWorkflow:
    """Contrato do endpoint POST /workflows/{id_hash}/execute — usado pelo
    botão Executar no canvas. Aceita `inputs` e `debug_mode`; é o caminho
    autenticado (role operator+) para qualquer workflow ativo, independente
    do tipo de trigger. Contrasta com /webhook/execute/{id}, que só aceita
    workflows com WebhookTrigger."""

    async def test_returns_202_with_task_id(self, override_workflow_deps):
        ac, svc = override_workflow_deps
        dispatch = MagicMock()
        dispatch.id = "task-xyz"
        svc.start_analysis = AsyncMock(return_value=dispatch)

        res = await ac.post("/workflows/wf-abc123/execute", json={"inputs": {}})

        assert res.status_code == 202
        body = res.json()
        assert body["task_id"] == "task-xyz"
        assert body["workflow"] == "wf-abc123"

    async def test_propagates_debug_mode_to_start_analysis(self, override_workflow_deps):
        ac, svc = override_workflow_deps
        dispatch = MagicMock()
        dispatch.id = "task-xyz"
        svc.start_analysis = AsyncMock(return_value=dispatch)

        await ac.post(
            "/workflows/wf-abc123/execute",
            json={"inputs": {"foo": "bar"}, "debug_mode": True},
        )

        svc.start_analysis.assert_called_once()
        _, kwargs = svc.start_analysis.call_args
        assert kwargs["debug_mode"] is True
        assert kwargs["inputs"] == {"foo": "bar"}

    async def test_debug_mode_defaults_to_false(self, override_workflow_deps):
        ac, svc = override_workflow_deps
        dispatch = MagicMock()
        dispatch.id = "task-xyz"
        svc.start_analysis = AsyncMock(return_value=dispatch)

        await ac.post("/workflows/wf-abc123/execute", json={"inputs": {}})

        _, kwargs = svc.start_analysis.call_args
        assert kwargs["debug_mode"] is False
