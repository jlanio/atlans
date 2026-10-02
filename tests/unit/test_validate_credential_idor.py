# tests/unit/test_validate_credential_idor.py
"""A validação não pode tocar credencial alheia.

`validar_definicao` aceita uma definition ARBITRÁRIA, sem workflow persistido
e sem workspace. A simulação de nós com `dynamic_output` (hoje o
DatabaseSpatialQuery) resolve o credential_id recebido e CONECTA ao banco,
dentro do processo da API. Sem a guarda, qualquer usuário autenticado que
conhecesse o UUID de uma credencial alheia executava SQL nela.

Nasceu como teste de `POST /workflows/validate`; a rota saiu (não tinha
chamador), e a guarda continua no núcleo que a tool `validate_workflow` do MCP
consome — por isso o teste chama o service direto.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import CredentialAccessDeniedError
from app.services.validate_service import validar_definicao

USUARIO = "usr-test-001"


def _definition(credential_id: str) -> dict:
    return {
        "nodes": [{
            "id": "n1",
            "name": "DatabaseSpatialQuery",
            "type": "datasource",
            "parameters": {"credential_id": credential_id, "query": "SELECT 1"},
        }],
        "edges": [],
    }


@pytest.fixture
def db_sem_credenciais_do_usuario():
    """Nenhuma credencial pedida pertence ao usuário.

    A sessão é aberta pelo próprio service (get_session_async), só quando há
    o que checar no banco (credencial, `workspace_id` ou nó SubWorkflow).
    """
    from contextlib import asynccontextmanager

    db = MagicMock()
    result = MagicMock()
    result.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    @asynccontextmanager
    async def _fake_session():
        yield db

    with patch("app.services.validate_service.get_session_async", _fake_session):
        yield


async def test_credencial_alheia_e_recusada_sem_simular(db_sem_credenciais_do_usuario):
    alheia = str(uuid4())

    with patch("flow.executor.core.WorkflowExecutor.simulate_runner", new=AsyncMock()) as sim:
        with pytest.raises(CredentialAccessDeniedError) as exc:
            await validar_definicao(_definition(alheia), user_id=USUARIO, workspace_id=None)

    assert exc.value.status_code == 403
    # A recusa acontece ANTES de qualquer conexão ao banco da credencial.
    sim.assert_not_awaited()


async def test_definition_sem_credencial_segue_simulando():
    """Caso comum não pode ser afetado pela guarda — nem abre sessão de banco."""
    from flow.executor.core import WorkflowExecutor

    payload = {
        "nodes": [{"id": "n1", "name": "ReadGeoJSON", "type": "datasource", "parameters": {}}],
        "edges": [],
    }

    chamadas = []

    async def _fake_sim(self):
        chamadas.append(True)
        self.simulated_outputs = {"n1": {"status": "ok", "schema": []}}
        return self.simulated_outputs

    with patch.object(WorkflowExecutor, "simulate_runner", _fake_sim), \
         patch("app.services.validate_service.get_session_async",
               MagicMock(side_effect=AssertionError("sessão de banco aberta"))):
        saida = await validar_definicao(payload, user_id=USUARIO, workspace_id=None)

    assert chamadas == [True]
    assert saida["n1"] == {"status": "ok", "schema": []}
