# tests/unit/test_validate_credential_idor.py
"""Validation must not touch someone else's credential.

`validar_definicao` accepts an ARBITRARY definition, with no persisted workflow
and no workspace. The simulation of nodes with `dynamic_output` (today the
DatabaseSpatialQuery) resolves the received credential_id and CONNECTS to the
database, inside the API process. Without the guard, any authenticated user who
knew the UUID of someone else's credential could run SQL on it.

It started as a test of `POST /workflows/validate`; the route was removed (it
had no caller), and the guard remains in the core that the MCP
`validate_workflow` tool consumes — which is why the test calls the service
directly.
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
    """None of the requested credentials belongs to the user.

    The session is opened by the service itself (get_session_async), only when
    there is something to check in the database (credential, `workspace_id` or
    SubWorkflow node).
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
    # The refusal happens BEFORE any connection to the credential's database.
    sim.assert_not_awaited()


async def test_definition_sem_credencial_segue_simulando():
    """The common case must not be affected by the guard — it does not even open a database session."""
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
