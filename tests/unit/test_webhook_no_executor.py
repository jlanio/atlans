# tests/unit/test_webhook_no_executor.py
"""
Webhook sem executor (spec §6, §7.3): 503 GENÉRICO ao chamador anônimo — sem
nomes de executores, contagens ou política — com `Retry-After`, sem criar run,
e sem consumir a chave de idempotência (o reenvio tenta de verdade).
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
    # nada da frota vaza para o anônimo
    texto = resp.text
    assert "geo-01" not in texto and "isolado" not in texto.lower() and "dedicad" not in texto.lower()
    service.start_analysis.assert_awaited_once()


async def test_reenvio_com_a_mesma_chave_tenta_de_novo(servico_sem_executor):
    """A chave de idempotência só é gravada após um dispatch bem-sucedido
    (workflow_service.py, passo 7): dois 503 seguidos = duas tentativas reais."""
    client, service = servico_sem_executor
    for _ in range(2):
        resp = await client.post("/webhook/execute/wf-1", json={}, headers={"Idempotency-Key": "abc"})
        assert resp.status_code == 503
    assert service.start_analysis.await_count == 2
