# tests/unit/test_mcp_sdk_contrato.py
"""
Contrato do SDK `mcp` pinado em requirements.txt (docs/specs/mcp-server.md).

A spec do servidor MCP foi escrita contra identificadores de um pacote que
muda rápido. Este teste é a verificação que ela exige: os nomes que a Fase 1
vai importar existem NESTA versão, e o transporte streamable HTTP se comporta
como a spec assume — Host fora da lista é 421, Origin de navegador é 403, e
`initialize` responde com o nome do servidor.

Nota para a Fase 1: a validação de Host/Origin acontece DENTRO do transporte,
depois de qualquer middleware externo. Com a autenticação por PAT na frente,
um request sem token recebe 401 antes de qualquer 421.
"""
from __future__ import annotations

import inspect

import httpx
import pytest

# Os identificadores que a spec cita — o import falhar JÁ é o teste.
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

_JSON = {
    "Content-Type": "application/json",
    # Sem os dois tipos no Accept o transporte responde 406 antes de olhar o resto.
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
        # JSON em vez de SSE só no teste: o que se verifica é Host/Origin e os
        # identificadores, não o streaming.
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
            # Host estranho: DNS rebinding — 421 antes de qualquer JSON-RPC.
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Host": "evil.example"})
            assert r.status_code == 421, r.text

            # Navegador (Origin presente) não é cliente deste servidor: 403.
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Origin": "https://x.example"})
            assert r.status_code == 403, r.text

            # Host permitido, sem Origin: o handshake responde com o nome do servidor.
            r = await c.post("/mcp", json=_INITIALIZE, headers=_JSON)
            assert r.status_code == 200, r.text
            corpo = r.json()
            assert corpo["result"]["serverInfo"]["name"] == "teste"

            # Stateless: `tools/list` responde sem sessão prévia e lista a tool registrada.
            r = await c.post(
                "/mcp", headers=_JSON,
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            assert r.status_code == 200, r.text
            assert [t["name"] for t in r.json()["result"]["tools"]] == ["soma"]
