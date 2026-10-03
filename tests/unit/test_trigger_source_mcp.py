# tests/unit/test_trigger_source_mcp.py
"""
`trigger_source="mcp"` (docs/specs/metrics-history.md §2; mcp-server.md §1).

The MCP server will stamp the runs it triggers with an origin of its own, so
that History can tell "an agent ran it" from "someone clicked". The column has
no CHECK — the vocabulary lives in the route's filter and in the web app. This
covers the route side: `mcp` passes; a value from outside is still a 422.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def listagem_mockada(client):
    from app.api.dependencies import get_db
    from app.api.routers import observability_router as R
    from app.main import app

    db = MagicMock()

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    with patch.object(R._svc, "list_runs", AsyncMock(return_value={"items": [], "has_more": False})) as listar:
        yield client, listar
    app.dependency_overrides.pop(get_db, None)


async def test_filtro_de_origem_aceita_mcp(listagem_mockada):
    client, listar = listagem_mockada
    resp = await client.get("/observability/runs", params={"trigger_source": "mcp"})
    assert resp.status_code == 200, resp.text
    assert listar.await_args.kwargs["trigger_source"] == "mcp"


@pytest.mark.parametrize("origem", ["manual", "retry", "webhook", "schedule"])
async def test_filtro_de_origem_continua_aceitando_as_antigas(listagem_mockada, origem):
    client, listar = listagem_mockada
    resp = await client.get("/observability/runs", params={"trigger_source": origem})
    assert resp.status_code == 200, resp.text
    assert listar.await_args.kwargs["trigger_source"] == origem


async def test_filtro_de_origem_fora_do_vocabulario_e_422(listagem_mockada):
    client, listar = listagem_mockada
    resp = await client.get("/observability/runs", params={"trigger_source": "cron"})
    assert resp.status_code == 422
    listar.assert_not_awaited()
