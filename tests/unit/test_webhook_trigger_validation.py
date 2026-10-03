# tests/unit/test_webhook_trigger_validation.py
"""Tests for the WebhookTrigger validation in the POST /webhook/execute/{id_hash} endpoint.

Covers:
  - has_webhook_trigger() in app.core.utils.workflow_triggers
  - Behavior of the webhook_router router when the workflow has no WebhookTrigger
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


# ── Tests of the utility function ─────────────────────────────────────────────

class TestHasWebhookTrigger:
    def test_definition_with_webhook_trigger_returns_true(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
                {"id": "n2", "type": "action", "name": "HttpRequest", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is True

    def test_definition_with_only_schedule_trigger_returns_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": {}},
                {"id": "n2", "type": "action", "name": "HttpRequest", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_with_only_file_trigger_returns_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "FileTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_without_triggers_returns_false(self):
        definition = {
            "nodes": [
                {"id": "n1", "type": "action", "name": "HttpRequest", "properties": {}},
                {"id": "n2", "type": "action", "name": "PythonScript", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False

    def test_definition_without_nodes_returns_false(self):
        assert has_webhook_trigger({"nodes": []}) is False

    def test_empty_definition_returns_false(self):
        assert has_webhook_trigger({}) is False

    def test_definition_with_multiple_triggers_including_webhook(self):
        """Hybrid workflows (schedule + webhook) should pass validation."""
        definition = {
            "nodes": [
                {"id": "n1", "type": "trigger", "name": "ScheduleTrigger", "properties": {}},
                {"id": "n2", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is True

    def test_node_with_webhook_name_but_wrong_type_returns_false(self):
        """Anti-spoofing defense: a node of type action named 'WebhookTrigger'
        must not pass validation — the type must be 'trigger'.
        """
        definition = {
            "nodes": [
                {"id": "n1", "type": "action", "name": "WebhookTrigger", "properties": {}},
            ]
        }
        assert has_webhook_trigger(definition) is False


# ── Integration tests with the router via TestClient ─────────────────────────

@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.get_workflow_by_hash = AsyncMock()
    svc.start_analysis = AsyncMock()
    return svc


@pytest.fixture
def app(mock_service):
    """Minimal FastAPI app to test webhook_router.

    Mounts the limiter and registers the RateLimitExceeded handler as in main.py.
    Overrides the get_workflow_service dependency via dependency_overrides.
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


def test_router_returns_403_when_workflow_has_no_webhook_trigger(client, mock_service):
    """POST /webhook/execute/{id_hash} on a workflow with only a ScheduleTrigger → 403."""
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
    # start_analysis must NEVER be called in this scenario
    mock_service.start_analysis.assert_not_called()


def test_router_returns_403_when_workflow_disabled(client, mock_service):
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


def test_router_returns_404_when_workflow_does_not_exist(client, mock_service):
    """Workflow inexistente retorna 404."""
    from app.services.workflow_service import WorkflowNotFoundError

    mock_service.get_workflow_by_hash.side_effect = WorkflowNotFoundError("not found")

    response = client.post("/webhook/execute/abc123")

    assert response.status_code == 404
    mock_service.start_analysis.assert_not_called()


def test_router_triggers_workflow_with_valid_webhook_trigger(client, mock_service):
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
