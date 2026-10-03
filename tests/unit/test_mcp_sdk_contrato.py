# tests/unit/test_mcp_sdk_contrato.py
"""
Contract of the `mcp` SDK pinned in requirements.txt (docs/specs/mcp-server.md).

The MCP server spec was written against identifiers of a fast-changing package.
This test is the check it requires: the names Phase 1 will import exist IN THIS
version, and the streamable HTTP transport behaves as the spec assumes — a Host
outside the list is 421, a browser Origin is 403, and `initialize` answers with
the server's name.

Note for Phase 1: the Host/Origin validation happens INSIDE the transport,
after any external middleware. With PAT authentication in front, a request
without a token gets 401 before any 421.
"""
from __future__ import annotations

import inspect

import httpx
import pytest

# The identifiers the spec cites — the import failing ALREADY is the test.
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

_JSON = {
    "Content-Type": "application/json",
    # Without both types in Accept the transport answers 406 before looking at the rest.
    "Accept": "application/json, text/event-stream",
}

_INITIALIZE = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "cliente-de-teste", "version": "0"},
    },
}


def _servidor():
    server = MCPServer("teste")

    @server.tool()
    def soma(a: int, b: int) -> int:
        """Soma dois inteiros."""
        return a + b

    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        # JSON instead of SSE only in the test: what is checked is Host/Origin and the
        # identifiers, not the streaming.
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=["atlans.example.org", "atlans.example.org:*", "localhost:*", "127.0.0.1:*"],
            allowed_origins=[],
        ),
    )
    return server, app


def test_identificadores_da_spec_existem():
    assert inspect.isclass(Context)
    assert issubclass(ToolError, Exception)
    assert callable(getattr(MCPServer, "tool"))
    assert callable(getattr(MCPServer, "streamable_http_app"))
    params = inspect.signature(MCPServer.streamable_http_app).parameters
    for nome in ("streamable_http_path", "stateless_http", "json_response", "transport_security"):
        assert nome in params, nome


@pytest.mark.asyncio
async def test_transporte_recusa_host_e_origin_fora_da_lista_e_responde_initialize():
    server, app = _servidor()
    async with server.session_manager.run():
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://atlans.example.org") as c:
            # Unknown Host: DNS rebinding — 421 before any JSON-RPC.
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Host": "evil.example"})
            assert r.status_code == 421, r.text

            # A browser (Origin present) is not a client of this server: 403.
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Origin": "https://x.example"})
            assert r.status_code == 403, r.text

            # Allowed Host, no Origin: the handshake answers with the server's name.
            r = await c.post("/mcp", json=_INITIALIZE, headers=_JSON)
            assert r.status_code == 200, r.text
            corpo = r.json()
            assert corpo["result"]["serverInfo"]["name"] == "teste"

            # Stateless: `tools/list` answers without a prior session and lists the registered tool.
            r = await c.post(
                "/mcp", headers=_JSON,
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            assert r.status_code == 200, r.text
            assert [t["name"] for t in r.json()["result"]["tools"]] == ["soma"]
