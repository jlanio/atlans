# tests/unit/test_email_transporte.py
"""
E-mail over any transport: Resend, SMTP or just the log.

Before, there was only Resend: without the key, no e-mail went out — and login,
which requires a verified e-mail, only let in the admin created by the CLI.

  CHOICE      EMAIL_BACKEND, or whatever is configured; a wrong value stops the API
  SMTP        STARTTLS, SSL or no TLS; header without injection
  RECIPIENTS  one address per item: the SendEmail recipient ceiling holds
  PATHS       the server's e-mails and the SendEmail node's use the transport
  LOGIN       EXIGIR_EMAIL_VERIFICADO=false lets people in without verifying
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import config
from app.services import email_transporte as T


@pytest.fixture
def no_transport(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "")
    monkeypatch.setattr(config, "RESEND_API_KEY", "")
    monkeypatch.setattr(config, "SMTP_HOST", "")
    monkeypatch.setattr(config, "EMAIL_FROM", "Atlans <noreply@atlans.example.org>")


# ── ESCOLHA ──────────────────────────────────────────────────────────────────

def test_with_nothing_configured_it_is_the_log(no_transport):
    assert T.backend() == "log"
    assert not T.ativo()


def test_with_the_resend_key_it_is_resend(no_transport, monkeypatch):
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_x")
    assert T.backend() == "resend"


def test_with_the_smtp_host_it_is_smtp(no_transport, monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.org")
    assert T.backend() == "smtp"


def test_explicit_choice_wins(no_transport, monkeypatch):
    monkeypatch.setattr(config, "RESEND_API_KEY", "re_x")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    assert T.backend() == "smtp"
    monkeypatch.setattr(config, "EMAIL_BACKEND", "log")
    assert not T.ativo()


def _startup_with(ambiente: dict[str, str]):
    """The config is read at import: each combination runs in its own process."""
    import os
    import subprocess
    import sys

    nomes = ("EMAIL_BACKEND", "SMTP_HOST", "SMTP_PORT", "SMTP_SEGURANCA", "SMTP_USERNAME", "RESEND_API_KEY",
             "MINIO_ROOT_PASSWORD", "REDIS_PASSWORD")
    env = {k: v for k, v in os.environ.items() if k not in nomes}
    env.update(ambiente)
    return subprocess.run(
        [sys.executable, "-c", "import app.core.config"], env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("ambiente, pedaco", [
    # Before, a wrong name fell back to the configured transport, with just a log.
    ({"EMAIL_BACKEND": "sendgrid", "SMTP_HOST": "smtp.example.org"}, "EMAIL_BACKEND='sendgrid'"),
    # Before, an unknown TLS mode silently became STARTTLS.
    ({"SMTP_HOST": "smtp.example.org", "SMTP_SEGURANCA": "tls"}, "SMTP_SEGURANCA='tls'"),
    # Before, every send failed with "please run connect() first".
    ({"EMAIL_BACKEND": "smtp"}, "sem SMTP_HOST"),
    ({"EMAIL_BACKEND": "resend"}, "sem RESEND_API_KEY"),
    # Before, it was the only e-mail error that got through: plaintext LOGIN on port 25.
    ({"SMTP_HOST": "smtp.example.org", "SMTP_SEGURANCA": "nenhuma", "SMTP_USERNAME": "fulana"}, "em claro"),
    # The example password from .env.example brought up a published MinIO with it.
    ({"MINIO_ROOT_PASSWORD": "change-me-strong-password"}, "MINIO_ROOT_PASSWORD"),  # pragma: allowlist secret
    ({"REDIS_PASSWORD": "troque-me-por-uma-senha-forte"}, "REDIS_PASSWORD"),  # pragma: allowlist secret
])
def test_wrong_config_prevents_the_api_from_starting(ambiente, pedaco):
    r = _startup_with(ambiente)
    assert r.returncode != 0
    assert pedaco in r.stderr


def test_correct_config_starts():
    for ambiente in ({}, {"EMAIL_BACKEND": "log"}, {"EMAIL_BACKEND": "smtp", "SMTP_HOST": "smtp.example.org",
                                                  "SMTP_SEGURANCA": "SSL"},
                     # Local relay without authentication: the case `nenhuma` exists for.
                     {"SMTP_HOST": "127.0.0.1", "SMTP_SEGURANCA": "nenhuma"}):
        r = _startup_with(ambiente)
        assert r.returncode == 0, r.stderr[-1500:]


def test_send_without_transport_raises(no_transport):
    with pytest.raises(RuntimeError):
        T.enviar(["a@example.org"], "Oi", "<p>oi</p>")


# ── SMTP ─────────────────────────────────────────────────────────────────────

class _SMTPFalso:
    """Records what the transport does with the connection."""

    instancias: list["_SMTPFalso"] = []

    def __init__(self, host, porta, **kw):
        self.host, self.porta, self.kw = host, porta, kw
        self.passos: list[str] = []
        self.mensagem = None
        _SMTPFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.passos.append("quit")

    def starttls(self, context=None):
        self.passos.append("starttls")

    def login(self, usuario, senha):
        self.passos.append(f"login:{usuario}")

    def send_message(self, mensagem, to_addrs=None):
        self.passos.append("send")
        self.mensagem = mensagem
        self.destinos = to_addrs


@pytest.fixture
def fake_smtp(no_transport, monkeypatch):
    _SMTPFalso.instancias = []
    monkeypatch.setattr(T.smtplib, "SMTP", _SMTPFalso)
    monkeypatch.setattr(T.smtplib, "SMTP_SSL", _SMTPFalso)
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(config, "SMTP_USERNAME", "")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "")
    return _SMTPFalso.instancias


def test_smtp_starttls_with_login(fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SEGURANCA", "starttls")
    monkeypatch.setattr(config, "SMTP_PORT", 587)
    monkeypatch.setattr(config, "SMTP_USERNAME", "atlans")
    monkeypatch.setattr(config, "SMTP_PASSWORD", "segredo")

    id_ = T.enviar(["a@example.org", "b@example.org"], "Relatório pronto", "<p>Olá</p>")

    (conexao,) = fake_smtp
    assert (conexao.host, conexao.porta) == ("smtp.example.org", 587)
    assert conexao.kw["timeout"] == T.SMTP_TIMEOUT_S
    assert conexao.passos == ["starttls", "login:atlans", "send", "quit"]
    # The recipients go explicitly: smtplib does not re-read them from the header.
    assert conexao.destinos == ["a@example.org", "b@example.org"]
    m = conexao.mensagem
    assert m["From"] == "Atlans <noreply@atlans.example.org>"
    assert m["To"] == "a@example.org, b@example.org"
    assert m["Subject"] == "Relatório pronto"
    assert m.get_content_type() == "text/html"
    assert "<p>Olá</p>" in m.get_content()
    assert id_ == m["Message-ID"] and id_.endswith("@atlans.example.org>")


def test_smtp_ssl_is_without_tls(fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SEGURANCA", "ssl")
    monkeypatch.setattr(config, "SMTP_PORT", 465)
    T.enviar(["a@example.org"], "x", "<p>x</p>")
    assert fake_smtp[-1].passos == ["send", "quit"]
    assert "context" in fake_smtp[-1].kw

    monkeypatch.setattr(config, "SMTP_SEGURANCA", "nenhuma")
    monkeypatch.setattr(config, "SMTP_PORT", 25)
    T.enviar(["a@example.org"], "x", "<p>x</p>")
    assert fake_smtp[-1].passos == ["send", "quit"]


def test_subject_with_line_break_does_not_inject_header(fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SEGURANCA", "nenhuma")
    with pytest.raises(ValueError):
        T.enviar(["a@example.org"], "Oi\r\nBcc: vitima@example.org", "<p>x</p>")
    assert not fake_smtp or fake_smtp[-1].mensagem is None


def test_default_port_follows_the_mode():
    import os
    import subprocess
    import sys

    codigo = (
        "import app.core.config as c\n"
        "print(c.SMTP_SEGURANCA, c.SMTP_PORT)\n"
    )
    vistos = []
    for modo in ("", "ssl", "nenhuma"):
        env = {k: v for k, v in os.environ.items() if k not in ("SMTP_PORT", "SMTP_SEGURANCA")}
        if modo:
            env["SMTP_SEGURANCA"] = modo
        r = subprocess.run([sys.executable, "-c", codigo], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-1500:]
        vistos.append(r.stdout.strip())
    assert vistos == ["starttls 587", "ssl 465", "nenhuma 25"]


def test_smtp_timeout_fits_within_the_sendemail_node_timeout():
    """The node waits 30 s for the whole response. With 30 s per operation, a
    slow server blew the node's deadline with the e-mail still going out — and
    the node failed with the e-mail sent."""
    assert T.SMTP_TIMEOUT_S * 2 < 30


# ── DESTINOS ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("item, puro", [
    ("ana@example.org", "ana@example.org"),
    ("  ana@example.org ", "ana@example.org"),
    ("Ana Souza <ana@example.org>", "ana@example.org"),
])
def test_one_address_per_item(item, puro):
    assert T.endereco(item) == puro


@pytest.mark.parametrize("item", [
    "a@example.org, b@example.org",          # comma: two recipients
    "lista: a@example.org, b@example.org;",  # grupo
    "lista: a@example.org",                  # unclosed group
    "a@example.org; b@example.org",
    "a@example.org\r\nBcc: c@example.org",   # header injection
    "a b@example.org", "a@", "@example.org", "<>", "", "   ",
    "a@example.org <b@example.org>",
])
def test_item_that_is_not_an_address_is_rejected(item):
    with pytest.raises(ValueError, match="Destinatário inválido"):
        T.endereco(item)


def test_smtp_does_not_multiply_recipients(fake_smtp, monkeypatch):
    """The review's attack: an item with 120 addresses got past the ceiling of 50
    (it counted as one) and became 120 `RCPT TO` — smtplib took the recipients
    from the `To` header."""
    monkeypatch.setattr(config, "SMTP_SEGURANCA", "nenhuma")
    lote = ", ".join(f"v{i}@example.org" for i in range(120))
    with pytest.raises(ValueError):
        T.enviar([lote], "x", "<p>x</p>")
    assert not fake_smtp


def test_resend_also_rejects(no_transport, monkeypatch):
    import resend

    monkeypatch.setattr(config, "RESEND_API_KEY", "re_x")
    with patch.object(resend.Emails, "send") as envio, pytest.raises(ValueError):
        T.enviar(["a@example.org, b@example.org"], "Oi", "<p>oi</p>")
    envio.assert_not_called()


def test_sendemail_node_rejects_item_with_commas():
    from pydantic import ValidationError

    from app.api.routers.internal_email_router import SendEmailRequest

    lote = ", ".join(f"v{i}@example.org" for i in range(120))
    with pytest.raises(ValidationError, match="Destinatário inválido"):
        SendEmailRequest(to=[lote], subject="x", html="<p>x</p>")
    pedido = SendEmailRequest(to=["a@example.org", "Bia <b@example.org>"], subject="x", html="<p>x</p>")
    assert pedido.to == ["a@example.org", "Bia <b@example.org>"]


# ── Resend ───────────────────────────────────────────────────────────────────

def test_resend_uses_the_single_sender(no_transport, monkeypatch):
    import resend

    monkeypatch.setattr(config, "RESEND_API_KEY", "re_x")
    with patch.object(resend.Emails, "send", return_value={"id": "msg-1"}) as envio:
        assert T.enviar(["a@example.org"], "Oi", "<p>oi</p>") == "msg-1"
    assert envio.call_args.args[0] == {
        "from": "Atlans <noreply@atlans.example.org>",
        "to": ["a@example.org"],
        "subject": "Oi",
        "html": "<p>oi</p>",
    }


# ── CAMINHOS ─────────────────────────────────────────────────────────────────

async def test_server_email_goes_out_through_the_transport(fake_smtp, monkeypatch):
    from app.services import email_service

    monkeypatch.setattr(config, "SMTP_SEGURANCA", "nenhuma")
    await email_service.send_email(
        "a@example.org", "Verifique seu e-mail", "verify_email.html",
        {"username": "ana", "verify_url": "https://atlans.example.org/verify-email?token=t"},
    )
    (conexao,) = fake_smtp
    assert conexao.mensagem["To"] == "a@example.org"
    assert "verify-email?token=t" in conexao.mensagem.get_content()


async def test_without_transport_server_email_only_goes_to_the_log(no_transport, caplog):
    from app.services import email_service

    with patch.object(T, "enviar") as enviar:
        await email_service.send_email(
            "a@example.org", "Oi", "verify_email.html", {"username": "ana", "verify_url": "x"},
        )
    enviar.assert_not_called()


def _email_request():
    from app.api.routers.internal_email_router import SendEmailRequest

    return SendEmailRequest(
        to=["a@example.org"], subject="Resultado", html="<p>ok</p>",
        workspace_id="ws-1", task_id="task-1",
    )


@pytest.fixture
def no_send_email(monkeypatch):
    from app.api.routers import internal_email_router as R

    monkeypatch.setattr(R, "_auth_agent", AsyncMock(return_value=MagicMock(id_hash="exe-1")))
    monkeypatch.setattr(R, "_assert_envio_vinculado_a_run", AsyncMock())
    monkeypatch.setattr(R, "_enforce_agent_quota", AsyncMock())
    return R


async def test_sendemail_node_without_transport_responds_503(no_send_email, no_transport):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as erro:
        await no_send_email.send_email(_email_request(), MagicMock(), MagicMock())
    assert erro.value.status_code == 503


async def test_sendemail_node_goes_out_through_smtp(no_send_email, fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SEGURANCA", "nenhuma")
    resposta = await no_send_email.send_email(_email_request(), MagicMock(), MagicMock())
    (conexao,) = fake_smtp
    assert resposta.sent and resposta.recipients == 1
    assert resposta.resend_id == conexao.mensagem["Message-ID"]


# ── LOGIN ────────────────────────────────────────────────────────────────────

SENHA = "senha-certa-123"  # pragma: allowlist secret


@pytest.fixture
def unverified_user_login(client):
    from app.api.dependencies import get_db
    from app.api.routers import auth_router
    from app.api.routers.auth_router import get_redis
    from app.core.utils.jwt_utils import hash_password
    from app.main import app
    from tests.unit._mcp_harness import FakeRedis

    usuario = MagicMock(
        id_hash="usr-1", username="ana", status="active", email_verified=False,
        hashed_password=hash_password(SENHA),
    )

    async def _db():
        db = MagicMock()
        resultado = MagicMock()
        resultado.scalar_one_or_none = MagicMock(return_value=usuario)
        db.execute = AsyncMock(return_value=resultado)
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = lambda: FakeRedis()
    with patch.object(auth_router, "register_refresh_family", AsyncMock()):
        yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_redis, None)


async def test_by_default_login_requires_verified_email(unverified_user_login, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_EMAIL_VERIFICADO", True)
    r = await unverified_user_login.post(
        "/auth/login", json={"identifier": "ana", "password": SENHA},
    )
    assert r.status_code == 403
    assert r.headers.get("X-Error-Code") == "email_not_verified"


async def test_without_the_requirement_login_succeeds_unverified(unverified_user_login, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_EMAIL_VERIFICADO", False)
    r = await unverified_user_login.post(
        "/auth/login", json={"identifier": "ana", "password": SENHA},
    )
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


# ── INVITATION ───────────────────────────────────────────────────────────────
#
# Without the verified e-mail requirement, open sign-up does not prove the
# e-mail belongs to whoever created the account. The invitation is by e-mail:
# without care, it handed the workspace to whoever signed up first with someone
# else's address.

@pytest.fixture
def convite(client, mock_current_user, monkeypatch):
    from types import SimpleNamespace

    from app.api.dependencies import get_db
    from app.api.routers import workspace_router
    from app.main import app

    ws = SimpleNamespace(id_hash="ws-1", name="Equipe", owner_id="u-dono")
    monkeypatch.setattr(workspace_router, "_get_admin_managed_workspace", AsyncMock(return_value=ws))
    monkeypatch.setattr("app.services.email_service.send_email_background", MagicMock())
    estado = {"convidado": None}

    async def _db():
        db = MagicMock()
        achou = MagicMock()
        achou.scalar_one_or_none = MagicMock(side_effect=lambda: estado["convidado"])
        nenhum = MagicMock()
        nenhum.scalar_one_or_none = MagicMock(return_value=None)
        # 1st query: the person by e-mail; 2nd: whether they are already a member.
        db.execute = AsyncMock(side_effect=[achou, nenhum])
        db.add = MagicMock()
        db.commit = AsyncMock()

        async def _refresh(membro):
            from datetime import datetime

            membro.joined_at = datetime(2026, 1, 15, 10, 30)

        db.refresh = AsyncMock(side_effect=_refresh)
        yield db

    app.dependency_overrides[get_db] = _db

    async def convidar(verificado: bool):
        estado["convidado"] = SimpleNamespace(
            id_hash="u-ana", email="ana@example.org", username="ana", email_verified=verificado,
        )
        return await client.post("/workspaces/ws-1/members", json={"email": "ana@example.org", "role": "editor"})

    yield convidar
    app.dependency_overrides.pop(get_db, None)


async def test_without_requirement_and_with_transport_the_invite_awaits_verification(convite, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_EMAIL_VERIFICADO", False)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.org")
    r = await convite(verificado=False)
    assert r.status_code == 409
    assert "confirmou o e-mail" in r.json()["message"]


async def test_without_requirement_or_transport_the_invite_passes_with_warning(convite, monkeypatch, caplog):
    """Without a transport, nothing in the installation proves the e-mail: rejecting
    would make invitations impossible. It passes, and the warning goes to the log."""
    monkeypatch.setattr(config, "EXIGIR_EMAIL_VERIFICADO", False)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "log")
    with caplog.at_level("WARNING"):
        r = await convite(verificado=False)
    assert r.status_code == 201, r.text
    assert "sem e-mail verificado" in caplog.text


@pytest.mark.parametrize("exigir, verificado", [(True, False), (True, True), (False, True)])
async def test_in_other_cases_the_invite_behaves_as_before(convite, monkeypatch, exigir, verificado):
    """With the requirement on (the default), the unverified account cannot even
    log in; the invitation waits for it, as it always did."""
    monkeypatch.setattr(config, "EXIGIR_EMAIL_VERIFICADO", exigir)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example.org")
    r = await convite(verificado=verificado)
    assert r.status_code == 201, r.text
