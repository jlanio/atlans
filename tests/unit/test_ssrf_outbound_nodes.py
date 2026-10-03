"""
SSRF / DNS rebinding in the HTTP output nodes.

Regression: http_request and send_webhook called validate_url_ssrf and
DISCARDED the return value, letting httpx re-resolve DNS at request time
(TOCTOU). With DNS TTL=0, the attacker resolved to public at validation and to
internal (169.254.169.254 / 10.x) at request time. Now both go through
safe_httpx_request, which validates AND pins the resolved IP.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flow.utils.geo_helpers import safe_httpx_request


# ── O boundary: safe_httpx_request ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_ip_interno_e_recusado():
    """A host that resolves to metadata/internal must not go out."""
    with patch("flow.utils.geo_helpers.socket.getaddrinfo",
               return_value=[(None, None, None, None, ("169.254.169.254", 0))]):
        with pytest.raises(ValueError, match="internos/privados"):
            await safe_httpx_request("GET", "http://metadata.evil.com/latest/meta-data/")


@pytest.mark.asyncio
async def test_conecta_no_ip_fixado_nao_no_hostname():
    """The central defense: the request goes out to the IP resolved at validation,
    not to the hostname (which DNS could re-resolve to an internal target)."""
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

    # URL connects to the pinned IP; hostname goes in the Host header for the virtualhost.
    assert "93.184.216.34" in captured["url"]
    assert "example.com" not in captured["url"]
    assert captured["host_header"] == "example.com"
    assert "q=1" in captured["url"], "query string deve ser preservada"


@pytest.mark.asyncio
async def test_params_dict_preservado():
    """http_request uses a params dict — the new passthrough must not lose it."""
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


# ── Delegation: the nodes use the safe path, not raw httpx ───────────────────

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
