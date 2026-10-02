# tests/unit/test_webhook_trigger_validation.py
"""Testes para a validação de WebhookTrigger no endpoint POST /webhook/execute/{id_hash}.

Cobre:
  - has_webhook_trigger() em app.core.utils.workflow_triggers
  - Comportamento do router webhook_router quando o workflow não possui WebhookTrigger
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.routers.webhook_router import router as webhook_router
from app.api.dependencies import get_workflow_service
from app.core.rate_limiter import limiter
from app.core.utils.workflow_triggers import has_webhook_trigger


# ── Testes da função utilitária ───────────────────────────────────────────────

class TestHasWebhookTrigger:
    def test_definition_com_webhook_trigger_retorna_true(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
                {"id": "n2", "type": "action", "name": "HttpRequest", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is True

    def test_definition_apenas_com_schedule_trigger_retorna_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": {}},
                {"id": "n2", "type": "action", "name": "HttpRequest", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_apenas_com_file_trigger_retorna_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "FileTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_sem_triggers_retorna_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "action", "name": "HttpRequest", "properties": {}},
                {"id": "n2", "type": "action", "name": "PythonScript", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_sem_nodes_retorna_false(self):
        assert has_webhook_trigger({"nodes": []}) is False

    def test_definition_vazia_retorna_false(self):
        assert has_webhook_trigger({}) is False

    def test_definition_com_multiplos_triggers_incluindo_webhook(self):
        """Workflows híbridos (schedule + webhook) devem passar na validação."""
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": {}},
                {"id": "n2", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is True

    def test_node_com_name_webhook_mas_type_errado_retorna_false(self):
        """Defesa anti-spoofing: um node do tipo action chamado 'WebhookTrigger'
        não deve passar na validação — o type deve ser 'trigger'.
        """
        definition = {
            "nodes": [
                {"id": "n1", "type": "action", "name": "WebhookTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False


# ── Testes de integração com o router via TestClient ─────────────────────────

@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.get_workflow_by_hash = AsyncMock()
    svc.start_analysis = AsyncMock()
    return svc


@pytest.fixture
def app(mock_service):
    """FastAPI app mínima para testar o webhook_router.

    Monta o limiter e registra o handler de RateLimitExceeded como em main.py.
    Sobrescreve a dependência get_workflow_service via dependency_overrides.
    """
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(webhook_router)
    app.dependency_overrides[get_workflow_service] = lambda: mock_service
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_router_retorna_403_quando_workflow_nao_tem_webhook_trigger(client, mock_service):
    """POST /webhook/execute/{id_hash} em workflow só com ScheduleTrigger → 403."""
    wf = MagicMock()
    wf.flag_ative = True
    wf.definition = {
        "nodes": [
            {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": {}},
        ]
    }
    mock_service.get_workflow_by_hash.return_value = wf

    response = client.post("/webhook/execute/abc123")

    assert response.status_code == 403
    assert "WebhookTrigger" in response.json()["detail"]
    # start_analysis NUNCA deve ser chamado nesse cenário
    mock_service.start_analysis.assert_not_called()


def test_router_retorna_403_quando_workflow_desativado(client, mock_service):
    """Workflow desativado retorna 403 mesmo se tiver WebhookTrigger."""
    wf = MagicMock()
    wf.flag_ative = False
    wf.definition = {
        "nodes": [
            {"id": "n1", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
        ]
    }
    mock_service.get_workflow_by_hash.return_value = wf

    response = client.post("/webhook/execute/abc123")

    assert response.status_code == 403
    assert "desativado" in response.json()["detail"].lower()
    mock_service.start_analysis.assert_not_called()


def test_router_retorna_404_quando_workflow_nao_existe(client, mock_service):
    """Workflow inexistente retorna 404."""
    from app.services.workflow_service import WorkflowNotFoundError

    mock_service.get_workflow_by_hash.side_effect = WorkflowNotFoundError("not found")

    response = client.post("/webhook/execute/abc123")

    assert response.status_code == 404
    mock_service.start_analysis.assert_not_called()


def test_router_dispara_workflow_com_webhook_trigger_valido(client, mock_service):
    """Workflow ativo com WebhookTrigger → chama start_analysis e retorna 202."""
    wf = MagicMock()
    wf.flag_ative = True
    wf.definition = {
        "nodes": [
            {"id": "n1", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
        ]
    }
    mock_service.get_workflow_by_hash.return_value = wf

    dispatch_result = MagicMock()
    dispatch_result.id = "task-xyz"
    dispatch_result.has_response_node = False
    mock_service.start_analysis.return_value = dispatch_result

    response = client.post("/webhook/execute/abc123", json={"param": "value"})

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-xyz"}
    mock_service.start_analysis.assert_called_once()
