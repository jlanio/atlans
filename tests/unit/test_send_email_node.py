"""
Testes do node SendEmail focados nos fixes do bug 502.

Bug original: operador configurava SendEmail com body vazio + attachMode='link'
sem artefato disponivel; executor enviava html="" pro servidor; Resend rejeitava
com "Missing html or text field"; servidor convertia em 502 e o operador via
apenas "Bad Gateway" sem pista da causa.
"""
from __future__ import annotations

import json

import pytest


try:
    from flow.nodes.outputs.send_email import SendEmailNode
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

pytestmark = pytest.mark.skipif(not _AVAILABLE, reason="flow.nodes.outputs.send_email indisponivel")


def _make_node(parameters: dict) -> SendEmailNode:
    node = SendEmailNode(node_id="t1", parameters=parameters)
    node._task_id = "task-test"
    node._workspace_id = "ws-test"
    return node


@pytest.mark.asyncio
async def test_empty_body_rejected_with_clear_error():
    """Camada 1: body vazio falha antes de chamar servidor, com mensagem util."""
    node = _make_node({
        "body": "",
        "subject": "Assunto teste",
        "toAddresses": "a@b.com",
        "attachMode": "none",
    })
    with pytest.raises(ValueError, match=r"(?i)body"):
        await node.execute({"output": {}})


@pytest.mark.asyncio
async def test_whitespace_body_rejected():
    """Body com apenas espacos/newlines tambem e rejeitado (body.strip() == '')."""
    node = _make_node({
        "body": "   \n\t  ",
        "subject": "x",
        "toAddresses": "a@b.com",
        "attachMode": "none",
    })
    with pytest.raises(ValueError, match=r"(?i)body"):
        await node.execute({"output": {}})


@pytest.mark.asyncio
async def test_link_mode_empty_body_no_artifact_rejected():
    """attachMode=link sem artefato + body vazio: falha cedo, nao chama servidor.

    Cenario exato do bug 502 reportado.
    """
    node = _make_node({
        "body": "",
        "subject": "x",
        "toAddresses": "a@b.com",
        "attachMode": "link",
    })
    with pytest.raises(ValueError, match=r"(?i)body"):
        await node.execute({"output": {}})


@pytest.mark.asyncio
async def test_dynamic_email_body_input_satisfies_validation(monkeypatch):
    """Body vazio via property mas presente via input dinamico 'email_body' passa
    da validacao inicial. Confirma que a mensagem chegou intacta ao endpoint
    de envio (sem regressao no _resolve_field)."""
    # Mock do endpoint HTTP — precisa mockar em nivel de modulo porque a
    # funcao e importada no topo. Sem isso, sem env vars, get_agent_http_config
    # faria fallback pra wss://agents.atlans.example.org e o teste bateria em prod.
    captured: dict = {}
    def _fake_call(to, subject, html, workspace_id=None, task_id=None):
        captured.update({"to": to, "subject": subject, "html": html,
                         "workspace_id": workspace_id, "task_id": task_id})
        return {"ok": True}
    monkeypatch.setattr(
        "flow.nodes.outputs.send_email._call_send_email_endpoint",
        _fake_call,
    )

    node = _make_node({
        "body": "",
        "subject": "x",
        "toAddresses": "a@b.com",
        "attachMode": "none",
    })
    inputs_with_body = {"output": {"email_body": "<p>Mensagem dinamica</p>"}}

    result = await node.execute(inputs_with_body)

    # Body dinamico substituiu o vazio e chegou ao endpoint
    assert captured["html"] == "<p>Mensagem dinamica</p>"
    assert captured["to"] == ["a@b.com"]
    assert result.get("output", {}).get("sent") is True


# ── Camada 2: erro do servidor com detail ──────────────────────────────────

class _FakeResponse:
    """Mock minimo de httpx.Response."""

    def __init__(self, status_code: int, body: dict | str | None = None):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body) if isinstance(body, dict) else (body or "")

    def json(self):
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("not json")


def test_call_send_email_endpoint_502_surfaces_detail(monkeypatch):
    """Camada 2: 502 com detail JSON vira RuntimeError com a mensagem real."""
    from flow.nodes.outputs import send_email as mod

    def fake_post(*args, **kwargs):
        return _FakeResponse(
            502,
            {"detail": "Erro ao enviar via Resend: Missing `html` or `text` field."},
        )

    # httpx e get_agent_http_config sao importados DENTRO de _call_send_email_endpoint,
    # entao monkeypatch direto no modulo importado.
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    import flow.utils.executor_http as _executor_http
    monkeypatch.setattr(
        _executor_http, "get_agent_http_config",
        lambda *a, **kw: ("https://server", {}, True),
    )

    with pytest.raises(RuntimeError) as exc_info:
        mod._call_send_email_endpoint(
            ["a@b.com"], "x", "<p>body</p>",
        )

    msg = str(exc_info.value)
    # Detalhe extraido do JSON aparece na mensagem (antes era so "Bad Gateway")
    assert "Missing" in msg
    assert "502" in msg


def test_call_send_email_endpoint_502_without_json_falls_back_to_text(monkeypatch):
    """Quando servidor retorna 502 com body texto, usa o texto como detail."""
    from flow.nodes.outputs import send_email as mod

    def fake_post(*args, **kwargs):
        return _FakeResponse(502, "Bad Gateway HTML page from Traefik")

    # httpx e get_agent_http_config sao importados DENTRO de _call_send_email_endpoint,
    # entao monkeypatch direto no modulo importado.
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    import flow.utils.executor_http as _executor_http
    monkeypatch.setattr(
        _executor_http, "get_agent_http_config",
        lambda *a, **kw: ("https://server", {}, True),
    )

    with pytest.raises(RuntimeError) as exc_info:
        mod._call_send_email_endpoint(
            ["a@b.com"], "x", "<p>body</p>",
        )

    assert "Bad Gateway" in str(exc_info.value)
    assert "502" in str(exc_info.value)


def test_call_send_email_endpoint_200_returns_json(monkeypatch):
    """Caminho feliz: 200 retorna JSON parseado."""
    from flow.nodes.outputs import send_email as mod

    def fake_post(*args, **kwargs):
        return _FakeResponse(200, {"sent": True, "recipients": 1, "resend_id": "rs_123"})

    # httpx e get_agent_http_config sao importados DENTRO de _call_send_email_endpoint,
    # entao monkeypatch direto no modulo importado.
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    import flow.utils.executor_http as _executor_http
    monkeypatch.setattr(
        _executor_http, "get_agent_http_config",
        lambda *a, **kw: ("https://server", {}, True),
    )

    result = mod._call_send_email_endpoint(
        ["a@b.com"], "x", "<p>body</p>",
    )

    assert result == {"sent": True, "recipients": 1, "resend_id": "rs_123"}


# ── Camada 3: validator no servidor (testa o schema diretamente) ──────────

def test_server_rejects_empty_html_at_pydantic_layer():
    """Camada 3: SendEmailRequest rejeita html vazio sem chegar ao Resend."""
    try:
        from app.api.routers.internal_email_router import SendEmailRequest
    except ImportError:
        pytest.skip("app.api.routers.internal_email_router indisponivel (dev sem servidor)")

    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        SendEmailRequest(to=["a@b.com"], subject="x", html="")

    errs = exc_info.value.errors()
    # Algum erro deve mencionar html
    assert any("html" in str(e).lower() for e in errs)


def test_server_rejects_whitespace_only_html():
    try:
        from app.api.routers.internal_email_router import SendEmailRequest
    except ImportError:
        pytest.skip("app.api.routers.internal_email_router indisponivel")

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SendEmailRequest(to=["a@b.com"], subject="x", html="   \n   ")


def test_server_rejects_html_emptied_by_sanitize():
    """Body com APENAS tags perigosas vira vazio apos sanitize e e rejeitado."""
    try:
        from app.api.routers.internal_email_router import SendEmailRequest
    except ImportError:
        pytest.skip("app.api.routers.internal_email_router indisponivel")

    from pydantic import ValidationError

    # Conteudo so com <script> — sanitize remove tudo, sobra ""
    with pytest.raises(ValidationError):
        SendEmailRequest(to=["a@b.com"], subject="x", html="<script>alert(1)</script>")


def test_server_accepts_valid_html():
    """Caminho feliz: html valido passa pelo schema."""
    try:
        from app.api.routers.internal_email_router import SendEmailRequest
    except ImportError:
        pytest.skip("app.api.routers.internal_email_router indisponivel")

    req = SendEmailRequest(to=["a@b.com"], subject="x", html="<p>Conteudo OK</p>")
    assert "<p>" in req.html
