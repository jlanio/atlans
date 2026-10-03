"""The real version of the Docker executor in the dashboard.

The executor declared `EXECUTOR_VERSION` (default "1.0.0"), and the executor/.env
of every Docker executor carried the `EXECUTOR_VERSION=1.0.0` from .env.example:
the whole fleet showed up as "v1.0.0", and there was no way to know which
machines still lacked a fix. Now the image build records the product version
(the same as the desktop app's) plus the checkout's commit — read from the .git
itself, without depending on who builds —, outside the code tree, and it beats
the .env; the desktop keeps declaring its own via EXECUTOR_VERSION.
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


# ── Which version wins ───────────────────────────────────────────────────────

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
    b"\xff\xfe\x00lixo",                 # not UTF-8: it brought down the config import
    ("2.15.0+" + "a" * 30).encode(),     # grande demais: o servidor descartaria
    b"2.15\x00.0",                       # not printable
])
def test_arquivo_estragado_nao_derruba_o_executor(tmp_path, conteudo):
    arquivo = tmp_path / "VERSAO"
    arquivo.write_bytes(conteudo)
    assert V.versao_do_executor({"EXECUTOR_VERSION": "2.15.1"}, arquivo) == "2.15.1"


def test_a_gravada_mora_fora_da_arvore_do_codigo():
    """In the checkout it would beat the EXECUTOR_VERSION of the desktop and the
    CLI — and a local build would leave it behind without git warning."""
    assert not V.ARQUIVO_DA_IMAGEM.is_relative_to(RAIZ)
    assert V.ARQUIVO_DA_IMAGEM.is_absolute()


def test_a_config_do_executor_usa_a_resolucao():
    from executor import config

    assert config.EXECUTOR_VERSION == V.versao_do_executor()


def test_o_enroll_declara_a_mesma_versao_do_handshake(tmp_path, monkeypatch):
    """The enroll read `executor.__version__`, which does not exist, and always
    fell back to "1.0.0" — whatever the version of the image or the desktop app."""
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
    ("2.16.0-beta.1+3f02f44", "2.16.0-beta.1+3f02f4"),   # 21: the commit gets shortened, as in the build
    ("2.16.0-release-candidate.12", "1.0.0"),             # no commit to shorten: the default
    ("2.15\x00.0", "1.0.0"),                              # not printable
])
def test_env_fora_da_regua_nao_vai_cru_ao_enroll(tmp_path, no_env, esperada):
    """The enroll validates `executor_version` (up to 20 characters) and refused
    with 422 the raw `EXECUTOR_VERSION` of a local build — the re-enroll too."""
    from app.schemas.executor_enrollment import EnrollRequest

    versao = V.versao_do_executor({"EXECUTOR_VERSION": no_env}, tmp_path / "sem-imagem")
    assert versao == esperada
    EnrollRequest(csr_pem="x", public_key_pem="x", hostname="h", executor_version=versao, os="Linux")
    assert _sanitize_executor_version("ex-1", versao) == versao


@pytest.mark.parametrize("status, corpo, motivo", [
    # The format of the server's handlers: `message`, not `detail`.
    (401, {"error": "http_exception", "message": "OTP invalido, expirado ou ja utilizado."},
     "OTP invalido, expirado ou ja utilizado."),
    (422, {"error": "validation_error", "message": "Validation failed",
           "details": [{"loc": ["body", "executor_version"], "msg": "String should have at most 20 characters"}]},
     "Validation failed (executor_version: String should have at most 20 characters)"),
    (403, {"detail": "OTP inválido"}, "OTP inválido"),
])
def test_a_recusa_do_enroll_diz_o_motivo(tmp_path, monkeypatch, status, corpo, motivo):
    """Only `detail` was read, and the server responds with `message`: the refusal
    came out as "Servidor recusou enrollment (status 401): " — with no reason."""
    import httpx

    from executor import enrollment

    monkeypatch.setattr(V, "ARQUIVO_DA_IMAGEM", tmp_path / "sem-imagem")
    monkeypatch.setattr(enrollment.httpx, "post", lambda url, **kw: httpx.Response(status, json=corpo))
    with pytest.raises(RuntimeError) as exc:
        enrollment.enroll("https://srv.invalid", "otp", "exec-1", tmp_path / "certs")
    assert str(exc.value) == f"Servidor recusou enrollment (status {status}): {motivo}"


# ── How the version is composed in the build ─────────────────────────────────

@pytest.mark.parametrize("base, commit, esperada", [
    ("2.15.0", SHA, "2.15.0+3f02f44"),                   # o sha inteiro vira curto
    ("2.15.0", "3f02f44", "2.15.0+3f02f44"),
    ("2.15.0", "", "2.15.0"),                            # tarball without .git
    ("2.15.0", None, "2.15.0"),
    ("2.15.0", "3f0;2 f\n44", "2.15.0+3f02f44"),         # alphanumeric only
    ("2.16.0-beta.1", SHA, "2.16.0-beta.1+3f02f4"),      # the hash gets shortened before going out
    ("2.16.0-beta.123", SHA, "2.16.0-beta.123+3f02"),
    ("2.16.0-beta.1234", SHA, "2.16.0-beta.1234"),       # not even 4 fit: only the product's
    ("2.16.0-release-candidate.12", SHA, "3f02f44"),     # not even the product's fits: the commit
    ("2.16.0-release-candidate.12", None, ""),           # nothing acceptable: nothing is written
    ("", SHA, "3f02f44"),
])
def test_compor(base, commit, esperada):
    versao = V.compor(base, commit)
    assert versao == esperada
    assert len(versao) <= V.TAMANHO_MAXIMO


def test_o_servidor_aceita_a_versao_composta():
    """Above 20 characters the server discards it and the dashboard has no version."""
    versao = V.compor("2.15.0", SHA)
    assert _sanitize_executor_version("ex-1", versao) == versao


# ── The commit comes from the checkout itself ────────────────────────────────

def _pasta_do_build(tmp_path, head, *, soltas=None, empacotadas=None, versao="2.15.0"):
    """The layout of the Dockerfile's COPY: package.json, HEAD and packed-refs at
    the root, the CONTENTS of .git/refs (heads/, tags/) alongside."""
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
    """install.sh's shallow clone packs the refs; the following `git pull`
    updates only the loose one. Reading the packed one would give the commit
    from before the pull."""
    pasta = _pasta_do_build(
        tmp_path, "ref: refs/heads/main",
        soltas={"refs/heads/main": SHA}, empacotadas={"refs/heads/main": OUTRO_SHA},
    )
    assert V.commit_do_git(pasta) == SHA


def test_commit_da_ref_empacotada(tmp_path):
    pasta = _pasta_do_build(tmp_path, "ref: refs/heads/main", empacotadas={"refs/heads/main": SHA})
    assert V.commit_do_git(pasta) == SHA


def test_head_destacado(tmp_path):
    """The Actions checkout of a tag leaves HEAD detached."""
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
    assert V.gravar(pasta, destino, commit=SHA, base="v1.4.2") == "1.4.2+3f02f44"   # without the tag's "v"


def test_gravar_sem_versao_aceitavel_nao_derruba_o_build(tmp_path, capsys):
    pasta = _pasta_do_build(tmp_path, None, versao="2.16.0-release-candidate.12")
    destino = tmp_path / "VERSAO"
    assert V.gravar(pasta, destino) is None
    assert not destino.exists()
    assert "aviso" in capsys.readouterr().err


def test_o_comando_do_dockerfile_grava_no_destino(tmp_path):
    """The same command as Dockerfile.executor, on a copy of the package and with
    the real version from desktop/package.json."""
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


# ── The build paths ──────────────────────────────────────────────────────────

def test_dockerfile_le_o_commit_do_checkout_e_grava_fora_da_arvore():
    texto = (RAIZ / "Dockerfile.executor").read_text()
    copia = re.search(r"^COPY desktop/package\.json (.+) /tmp/versao/$", texto, re.M)
    assert copia, "o COPY da versão sumiu"
    # Wildcards: without .git (tarball) the COPY must not fail.
    assert copia.group(1).split() == [".gi[t]/HEA[D]", ".gi[t]/packed-ref[s]", ".gi[t]/ref[s]"]
    assert "ARG EXECUTOR_COMMIT" in texto and "ARG EXECUTOR_BASE" in texto
    assert f"python -m executor.versao /tmp/versao {V.ARQUIVO_DA_IMAGEM}" in texto
    assert texto.index("COPY executor/ ./executor/") < texto.index("RUN python -m executor.versao")


def test_dockerignore_deixa_entrar_so_a_ref_do_git():
    linhas = [l.strip() for l in (RAIZ / ".dockerignore").read_text().splitlines()]
    assert ".git" in linhas
    assert {"!.git/HEAD", "!.git/packed-refs", "!.git/refs"} <= set(linhas)
    assert not any(l.startswith("!.git/") and l not in {"!.git/HEAD", "!.git/packed-refs", "!.git/refs"} for l in linhas)
    assert "**/.env" in linhas       # the builder's executor/.env does not go into the image


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
    ("2.14.0", True),      # an explicit choice that the image ignores: the operator gets told
    ("1.0.0", False),      # the one from every old installation's .env.example: not a choice
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
