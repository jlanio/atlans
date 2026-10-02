"""Versão real do executor Docker no painel.

O executor declarava `EXECUTOR_VERSION` (padrão "1.0.0"), e o executor/.env
de todo executor Docker trazia o `EXECUTOR_VERSION=1.0.0` do .env.example:
a frota inteira aparecia como "v1.0.0", e não dava para saber quais máquinas
ainda não tinham uma correção. Agora o build da imagem grava a versão do
produto (a mesma do app desktop) mais o commit do checkout — lido do próprio
.git, sem depender de quem builda —, fora da árvore do código, e ela vence o
.env; o desktop segue declarando a dele por EXECUTOR_VERSION.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from app.api.routers.executor_ws.protocolo import _sanitize_executor_version
from executor import versao as V

RAIZ = Path(__file__).resolve().parents[2]
SHA = "3f02f442d1c0ffee0123456789abcdef01234567"  # pragma: allowlist secret
OUTRO_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


# ── Qual versão vale ─────────────────────────────────────────────────────────

def test_a_gravada_na_imagem_vence_o_env(tmp_path):
    arquivo = tmp_path / "VERSAO"
    arquivo.write_text("2.15.0+3f02f44\n")
    assert V.versao_do_executor({"EXECUTOR_VERSION": "1.0.0"}, arquivo) == "2.15.0+3f02f44"


@pytest.mark.parametrize("conteudo", [None, "", "  \n"])
def test_sem_a_gravada_vale_o_env_como_no_desktop(tmp_path, conteudo):
    arquivo = tmp_path / "VERSAO"
    if conteudo is not None:
        arquivo.write_text(conteudo)
    assert V.versao_do_executor({"EXECUTOR_VERSION": " 2.15.1 "}, arquivo) == "2.15.1"
    assert V.versao_do_executor({}, arquivo) == "1.0.0"
    assert V.versao_do_executor({"EXECUTOR_VERSION": ""}, arquivo) == "1.0.0"


@pytest.mark.parametrize("conteudo", [
    b"\xff\xfe\x00lixo",                 # não é UTF-8: derrubava a importação do config
    ("2.15.0+" + "a" * 30).encode(),     # grande demais: o servidor descartaria
    b"2.15\x00.0",                       # não imprimível
])
def test_arquivo_estragado_nao_derruba_o_executor(tmp_path, conteudo):
    arquivo = tmp_path / "VERSAO"
    arquivo.write_bytes(conteudo)
    assert V.versao_do_executor({"EXECUTOR_VERSION": "2.15.1"}, arquivo) == "2.15.1"


def test_a_gravada_mora_fora_da_arvore_do_codigo():
    """No checkout ela venceria o EXECUTOR_VERSION do desktop e da CLI — e um
    build local a deixaria para trás sem o git avisar."""
    assert not V.ARQUIVO_DA_IMAGEM.is_relative_to(RAIZ)
    assert V.ARQUIVO_DA_IMAGEM.is_absolute()


def test_a_config_do_executor_usa_a_resolucao():
    from executor import config

    assert config.EXECUTOR_VERSION == V.versao_do_executor()


def test_o_enroll_declara_a_mesma_versao_do_handshake(tmp_path, monkeypatch):
    """O enroll lia `executor.__version__`, que não existe, e caía sempre no
    "1.0.0" — qualquer que fosse a versão da imagem ou do app desktop."""
    import httpx

    from executor import enrollment

    monkeypatch.setattr(V, "ARQUIVO_DA_IMAGEM", tmp_path / "sem-imagem")
    monkeypatch.setenv("EXECUTOR_VERSION", "2.15.1")
    enviado = {}

    def _post(url, **kw):
        enviado.update(kw["json"])
        return httpx.Response(403, json={"detail": "OTP inválido"})

    monkeypatch.setattr(enrollment.httpx, "post", _post)
    with pytest.raises(RuntimeError, match="recusou"):
        enrollment.enroll("https://srv.invalid", "otp", "exec-1", tmp_path / "certs")

    assert enviado["executor_version"] == "2.15.1"


@pytest.mark.parametrize("no_env, esperada", [
    ("2.16.0-beta.1+3f02f44", "2.16.0-beta.1+3f02f4"),   # 21: o commit encurta, como no build
    ("2.16.0-release-candidate.12", "1.0.0"),             # sem commit para encurtar: o padrão
    ("2.15\x00.0", "1.0.0"),                              # não imprimível
])
def test_env_fora_da_regua_nao_vai_cru_ao_enroll(tmp_path, no_env, esperada):
    """O enroll valida `executor_version` (até 20 caracteres) e recusava com
    422 o `EXECUTOR_VERSION` cru de um build local — o re-enroll também."""
    from app.schemas.executor_enrollment import EnrollRequest

    versao = V.versao_do_executor({"EXECUTOR_VERSION": no_env}, tmp_path / "sem-imagem")
    assert versao == esperada
    EnrollRequest(csr_pem="x", public_key_pem="x", hostname="h", executor_version=versao, os="Linux")
    assert _sanitize_executor_version("ex-1", versao) == versao


@pytest.mark.parametrize("status, corpo, motivo", [
    # O formato dos handlers do servidor: `message`, e não `detail`.
    (401, {"error": "http_exception", "message": "OTP invalido, expirado ou ja utilizado."},
     "OTP invalido, expirado ou ja utilizado."),
    (422, {"error": "validation_error", "message": "Validation failed",
           "details": [{"loc": ["body", "executor_version"], "msg": "String should have at most 20 characters"}]},
     "Validation failed (executor_version: String should have at most 20 characters)"),
    (403, {"detail": "OTP inválido"}, "OTP inválido"),
])
def test_a_recusa_do_enroll_diz_o_motivo(tmp_path, monkeypatch, status, corpo, motivo):
    """Só o `detail` era lido, e o servidor responde `message`: a recusa saía
    como "Servidor recusou enrollment (status 401): " — sem motivo."""
    import httpx

    from executor import enrollment

    monkeypatch.setattr(V, "ARQUIVO_DA_IMAGEM", tmp_path / "sem-imagem")
    monkeypatch.setattr(enrollment.httpx, "post", lambda url, **kw: httpx.Response(status, json=corpo))
    with pytest.raises(RuntimeError) as exc:
        enrollment.enroll("https://srv.invalid", "otp", "exec-1", tmp_path / "certs")
    assert str(exc.value) == f"Servidor recusou enrollment (status {status}): {motivo}"


# ── Como a versão é composta no build ────────────────────────────────────────

@pytest.mark.parametrize("base, commit, esperada", [
    ("2.15.0", SHA, "2.15.0+3f02f44"),                   # o sha inteiro vira curto
    ("2.15.0", "3f02f44", "2.15.0+3f02f44"),
    ("2.15.0", "", "2.15.0"),                            # tarball sem .git
    ("2.15.0", None, "2.15.0"),
    ("2.15.0", "3f0;2 f\n44", "2.15.0+3f02f44"),         # só alfanumérico
    ("2.16.0-beta.1", SHA, "2.16.0-beta.1+3f02f4"),      # o hash encurta antes de sair
    ("2.16.0-beta.123", SHA, "2.16.0-beta.123+3f02"),
    ("2.16.0-beta.1234", SHA, "2.16.0-beta.1234"),       # nem 4 cabem: só a do produto
    ("2.16.0-release-candidate.12", SHA, "3f02f44"),     # nem a do produto cabe: o commit
    ("2.16.0-release-candidate.12", None, ""),           # nada aceitável: não grava
    ("", SHA, "3f02f44"),
])
def test_compor(base, commit, esperada):
    versao = V.compor(base, commit)
    assert versao == esperada
    assert len(versao) <= V.TAMANHO_MAXIMO


def test_o_servidor_aceita_a_versao_composta():
    """Acima de 20 caracteres o servidor descarta e o painel fica sem versão."""
    versao = V.compor("2.15.0", SHA)
    assert _sanitize_executor_version("ex-1", versao) == versao


# ── O commit sai do próprio checkout ─────────────────────────────────────────

def _pasta_do_build(tmp_path, head, *, soltas=None, empacotadas=None, versao="2.15.0"):
    """O layout do COPY do Dockerfile: package.json, HEAD e packed-refs na raiz,
    o CONTEÚDO de .git/refs (heads/, tags/) ao lado."""
    pasta = tmp_path / "versao"
    pasta.mkdir()
    (pasta / "package.json").write_text(json.dumps({"version": versao}))
    if head is not None:
        (pasta / "HEAD").write_text(head + "\n")
    for ref, sha in (soltas or {}).items():
        caminho = pasta / ref[len("refs/"):]
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(sha + "\n")
    if empacotadas:
        linhas = ["# pack-refs with: peeled fully-peeled sorted"]
        linhas += [f"{sha} {ref}" for ref, sha in empacotadas.items()]
        (pasta / "packed-refs").write_text("\n".join(linhas) + "\n")
    return pasta


def test_commit_da_ref_solta(tmp_path):
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/trabalho/ramo", soltas={"refs/heads/trabalho/ramo": SHA})
    assert V.commit_do_git(pasta) == SHA


def test_a_ref_solta_vence_a_empacotada(tmp_path):
    """O clone raso do install.sh empacota as refs; o `git pull` seguinte
    atualiza só a solta. Ler a empacotada daria o commit de antes do pull."""
    pasta = _pasta_do_build(
        tmp_path, "ref: refs/heads/main",
        soltas={"refs/heads/main": SHA}, empacotadas={"refs/heads/main": OUTRO_SHA},
    )
    assert V.commit_do_git(pasta) == SHA


def test_commit_da_ref_empacotada(tmp_path):
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/main", empacotadas={"refs/heads/main": SHA})
    assert V.commit_do_git(pasta) == SHA


def test_head_destacado(tmp_path):
    """O checkout do Actions num tag deixa o HEAD destacado."""
    assert V.commit_do_git(_pasta_do_build(tmp_path, SHA)) == SHA


@pytest.mark.parametrize("head", [None, "ref: refs/heads/sumiu", "lixo", "ref: ../../etc/passwd", "ref: refs/../../etc/passwd"])
def test_sem_como_saber_o_commit(tmp_path, head):
    assert V.commit_do_git(_pasta_do_build(tmp_path, head)) is None


def test_gravar_com_o_commit_do_checkout(tmp_path):
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/main", soltas={"refs/heads/main": SHA})
    destino = tmp_path / "share" / "VERSAO"
    assert V.gravar(pasta, destino) == "2.15.0+3f02f44"
    assert destino.read_text() == "2.15.0+3f02f44"


def test_os_argumentos_do_release_valem_mais(tmp_path):
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/main", soltas={"refs/heads/main": OUTRO_SHA})
    destino = tmp_path / "VERSAO"
    assert V.gravar(pasta, destino, commit=SHA, base="v1.4.2") == "1.4.2+3f02f44"   # sem o "v" da tag


def test_gravar_sem_versao_aceitavel_nao_derruba_o_build(tmp_path, capsys):
    pasta = _pasta_do_build(tmp_path, None, versao="2.16.0-release-candidate.12")
    destino = tmp_path / "VERSAO"
    assert V.gravar(pasta, destino) is None
    assert not destino.exists()
    assert "aviso" in capsys.readouterr().err


def test_o_comando_do_dockerfile_grava_no_destino(tmp_path):
    """O mesmo comando do Dockerfile.executor, numa cópia do pacote e com a
    versão real do desktop/package.json."""
    (tmp_path / "executor").mkdir()
    (tmp_path / "executor" / "__init__.py").write_text("")
    shutil.copy(RAIZ / "executor" / "versao.py", tmp_path / "executor" / "versao.py")
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/main", soltas={"refs/heads/main": SHA})
    shutil.copy(RAIZ / "desktop" / "package.json", pasta / "package.json")
    destino = tmp_path / "usr" / "share" / "VERSAO"

    subprocess.run(
        [sys.executable, "-m", "executor.versao", str(pasta), str(destino)],
        cwd=tmp_path, env={"PATH": ""}, check=True, capture_output=True, text=True, timeout=60,
    )

    produto = json.loads((RAIZ / "desktop" / "package.json").read_text())["version"]
    assert destino.read_text() == V.compor(produto, SHA)


# ── Os caminhos de build ─────────────────────────────────────────────────────

def test_dockerfile_le_o_commit_do_checkout_e_grava_fora_da_arvore():
    texto = (RAIZ / "Dockerfile.executor").read_text()
    copia = re.search(r"^COPY desktop/package\.json (.+) /tmp/versao/$", texto, re.M)
    assert copia, "o COPY da versão sumiu"
    # Curingas: sem .git (tarball) o COPY não pode falhar.
    assert copia.group(1).split() == [".gi[t]/HEA[D]", ".gi[t]/packed-ref[s]", ".gi[t]/ref[s]"]
    assert "ARG EXECUTOR_COMMIT" in texto and "ARG EXECUTOR_BASE" in texto
    assert f"python -m executor.versao /tmp/versao {V.ARQUIVO_DA_IMAGEM}" in texto
    assert texto.index("COPY executor/ ./executor/") < texto.index("RUN python -m executor.versao")


def test_dockerignore_deixa_entrar_so_a_ref_do_git():
    linhas = [l.strip() for l in (RAIZ / ".dockerignore").read_text().splitlines()]
    assert ".git" in linhas
    assert {"!.git/HEAD", "!.git/packed-refs", "!.git/refs"} <= set(linhas)
    assert not any(l.startswith("!.git/") and l not in {"!.git/HEAD", "!.git/packed-refs", "!.git/refs"} for l in linhas)
    assert "**/.env" in linhas       # o executor/.env de quem builda não entra na imagem


def test_compose_do_executor_ainda_aceita_forcar_o_commit():
    compose = yaml.safe_load((RAIZ / "docker-compose.executor.yml").read_text())
    assert compose["services"]["executor"]["build"]["args"]["EXECUTOR_COMMIT"] == "${EXECUTOR_COMMIT:-}"


def test_release_passa_a_versao_da_tag():
    fluxo = yaml.safe_load((RAIZ / ".github" / "workflows" / "executor-docker.yml").read_text())
    passos = fluxo["jobs"]["build"]["steps"]
    nomes = [p.get("name") for p in passos]
    assert nomes.index("Extract version from tag") < nomes.index("Build executor image")
    build = passos[nomes.index("Build executor image")]
    assert "EXECUTOR_BASE=${{ steps.version.outputs.VERSION }}" in build["with"]["build-args"]


def test_env_example_do_executor_nao_fixa_a_versao():
    texto = (RAIZ / "executor" / ".env.example").read_text()
    assert not re.search(r"^\s*EXECUTOR_VERSION\s*=", texto, re.M)


_AVISO_NO_BOOT = """
import json, sys
from pathlib import Path
import executor.versao as V
V.ARQUIVO_DA_IMAGEM = Path(sys.argv[1])
from executor import _ambiente, config
print(json.dumps([config.EXECUTOR_VERSION, [m % a for m, a in _ambiente._AVISOS_ADIADOS if "EXECUTOR_VERSION" in m]]))
"""


@pytest.mark.parametrize("no_env, avisa", [
    ("2.14.0", True),      # escolha explícita que a imagem ignora: o operador fica sabendo
    ("1.0.0", False),      # o do .env.example de toda instalação antiga: não é escolha
    ("", False),
])
def test_aviso_quando_a_imagem_ignora_uma_versao_escolhida(tmp_path, no_env, avisa):
    import os

    arquivo = tmp_path / "VERSAO"
    arquivo.write_text("2.15.0+3f02f44")
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ), "EXECUTOR_VERSION": no_env}
    saida = subprocess.run(
        [sys.executable, "-c", _AVISO_NO_BOOT, str(arquivo)], cwd=RAIZ, env=ambiente,
        capture_output=True, text=True, timeout=60, check=True,
    )
    versao, avisos = json.loads(saida.stdout.strip().splitlines()[-1])
    assert versao == "2.15.0+3f02f44"
    assert bool(avisos) is avisa
