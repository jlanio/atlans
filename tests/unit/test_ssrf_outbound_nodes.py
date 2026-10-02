"""
SSRF / DNS-rebinding nos nodes de saida HTTP.

Regressao: http_request e send_webhook chamavam validate_url_ssrf e
DESCARTAVAM o retorno, deixando o httpx re-resolver o DNS na hora do request
(TOCTOU). Com DNS TTL=0, o atacante resolvia publico na validacao e interno
(169.254.169.254 / 10.x) no request. Agora ambos passam por
safe_httpx_request, que valida E fixa o IP resolvido.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flow.utils.geo_helpers import safe_httpx_request


# ── O boundary: safe_httpx_request ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_ip_interno_e_recusado():
    """Host que resolve para metadata/interno nao pode sair."""
    with patch("flow.utils.geo_helpers.socket.getaddrinfo",
               return_value=[(None, None, None, None, ("169.254.169.254", 0))]):
        with pytest.raises(ValueError, match="internos/privados"):
            await safe_httpx_request("GET", "http://metadata.evil.com/latest/meta-data/")


@pytest.mark.asyncio
async def test_conecta_no_ip_fixado_nao_no_hostname():
    """A defesa central: a request sai para o IP resolvido na validacao, nao
    para o hostname (que o DNS poderia re-resolver para um alvo interno)."""
    captured = {}

    async def _fake_send(self, request, **kwargs):
        captured["url"] = str(request.url)
        captured["host_header"] = request.headers.get("host")
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("flow.utils.geo_helpers.socket.getaddrinfo",
               return_value=[(None, None, None, None, ("93.184.216.34", 0))]), \
            patch("httpx.AsyncClient.send", _fake_send):
        await safe_httpx_request("GET", "http://example.com/path?q=1")

    # URL conecta no IP fixado; hostname vai no Host header para o virtualhost.
    assert "93.184.216.34" in captured["url"]
    assert "example.com" not in captured["url"]
    assert captured["host_header"] == "example.com"
    assert "q=1" in captured["url"], "query string deve ser preservada"


@pytest.mark.asyncio
async def test_params_dict_preservado():
    """http_request usa params dict — o passthrough novo nao pode perde-lo."""
    captured = {}

    async def _fake_send(self, request, **kwargs):
        captured["url"] = str(request.url)
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("flow.utils.geo_helpers.socket.getaddrinfo",
               return_value=[(None, None, None, None, ("93.184.216.34", 0))]), \
            patch("httpx.AsyncClient.send", _fake_send):
        await safe_httpx_request("GET", "http://example.com/api", params={"bbox": "1,2,3,4"})

    assert "bbox=1" in captured["url"]


# ── Delegacao: os nodes usam o caminho seguro, nao httpx cru ──────────────────

@pytest.mark.asyncio
async def test_http_request_node_delega_para_safe_httpx():
    from flow.nodes.action.http_request import HttpRequestNode

    node = HttpRequestNode("n1", {"url": "http://example.com", "method": "GET"})

    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"ok": True})
    resp.headers = {}

    with patch("flow.nodes.action.http_request.safe_httpx_request",
               new=AsyncMock(return_value=resp)) as safe_mock:
        out = await node.execute({})

    safe_mock.assert_awaited_once()
    assert out["status_code"] == 200


@pytest.mark.asyncio
async def test_send_webhook_node_delega_para_safe_httpx():
    from flow.nodes.outputs.send_webhook import SendWebhookNode

    node = SendWebhookNode("n1", {"url": "http://hook.example.com", "method": "POST"})

    resp = MagicMock()
    resp.status_code = 200
    resp.text = "ok"

    with patch("flow.nodes.outputs.send_webhook.safe_httpx_request",
               new=AsyncMock(return_value=resp)) as safe_mock:
        await node.execute({})

    safe_mock.assert_awaited_once()
