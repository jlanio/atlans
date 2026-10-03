# tests/unit/test_webhook_no_executor.py
"""
Webhook with no executor (spec §6, §7.3): a GENERIC 503 to the anonymous
caller — no executor names, counts or policy — with `Retry-After`, without
creating a run, and without consuming the idempotency key (the resend really
tries again).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NoExecutorAvailableError

DETALHE_INTERNO = "Workspace isolado: nenhum dos 2 executores dedicados (geo-01, geo-02) está disponível."


def _wf_com_webhook():
    wf = MagicMock()
    wf.id_hash = "wf-1"
    wf.flag_ative = True
    wf.definition = {"nodes": [{"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}}], "edges": []}
    return wf


@pytest.fixture
def servico_sem_executor(client):
    from app.api.dependencies import get_workflow_service
    from app.main import app

    service = MagicMock()
    service.get_workflow_by_hash = AsyncMock(return_value=_wf_com_webhook())
    service.start_analysis = AsyncMock(
        side_effect=NoExecutorAvailableError(DETALHE_INTERNO, category="no_dedicated_executor"),
    )
    app.dependency_overrides[get_workflow_service] = lambda: service
    yield client, service
    app.dependency_overrides.pop(get_workflow_service, None)


async def test_503_generico_com_retry_after(servico_sem_executor):
    client, service = servico_sem_executor
    resp = await client.post("/webhook/execute/wf-1", json={"x": 1})
    assert resp.status_code == 503
    assert resp.headers.get("retry-after") == "60"
    corpo = resp.json()
    assert corpo["message"] == "Execução temporariamente indisponível para este workflow."
    # nothing about the fleet leaks to the anonymous caller
    texto = resp.text
    assert "geo-01" not in texto and "isolado" not in texto.lower() and "dedicad" not in texto.lower()
    service.start_analysis.assert_awaited_once()


async def test_reenvio_com_a_mesma_chave_tenta_de_novo(servico_sem_executor):
    """The idempotency key is only written after a successful dispatch
    (workflow_service.py, step 7): two 503s in a row = two real attempts."""
    client, service = servico_sem_executor
    for _ in range(2):
        resp = await client.post("/webhook/execute/wf-1", json={}, headers={"Idempotency-Key": "abc"})
        assert resp.status_code == 503
    assert service.start_analysis.await_count == 2
