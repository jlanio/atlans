# tests/unit/test_limite_de_memoria_do_executor.py
"""The executor's memory limit follows the machine.

The fixed `memory: 2G` of docker-compose.executor.yml killed an executor by cgroup
OOM — on a 16 GB machine with 13 GB free —, and the job it was
running was left without an outcome. Now the installer writes EXECUTOR_MEMORIA (75% of
the memory Docker sees) into the .env that compose interpolates.

The function is EXECUTED as it is in the installer — cut out between the markers,
not copied here: a copy would stay green with the script broken.
"""
import re
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
INSTALL_SH = (RAIZ / "static" / "install.sh").read_text(encoding="utf-8")
COMPOSE = RAIZ / "docker-compose.executor.yml"

GIB = 1024 ** 3


def _funcao():
    trecho = re.search(r"# >>> limite_de_memoria.*?\n(.*?)# <<< limite_de_memoria", INSTALL_SH, re.S)
    assert trecho, "o install.sh perdeu os marcadores da função limite_de_memoria"
    return trecho.group(1)


def _bash(chamada: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + _funcao() + "\n" + chamada],
        capture_output=True, text=True, timeout=30,
    )


def _limite(total_bytes: int) -> str:
    r = _bash(f'limite_de_memoria "{total_bytes}"')
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize("total,esperado", [
    (16 * GIB, "12G"),   # the incident's machine: 12G was what the diagnosis recommended
    (8 * GIB, "6G"),
    (4 * GIB, "3G"),
    (64 * GIB, "48G"),
    (int(15.5 * GIB), "11G"),   # rounds down: never promises what isn't there
    # Floor: the fixed 2G from before. On a "2 GB" VPS (1.93 GiB) 75% would give 1G, and
    # a 1.5 GB job that used to run would start dying from OOM.
    (int(2.66 * GIB), "2G"),
    (int(1.93 * GIB), "2G"),
    (512 * 1024 ** 2, "2G"),
])
def test_limite_e_75_por_cento_da_memoria_do_docker(total, esperado):
    assert _limite(total) == esperado


@pytest.mark.parametrize("valor,aceito", [
    ("12G", True), ("1536M", True), ("512M", True), ("512m", True), ("1g", True),
    ("08G", True),                  # a leading zero does not become octal
    ("511M", False),                # below the compose reservation: Docker refuses
    ("256M", False), ("0G", False),
    ("12", False), ("12GB", False), ("1.5G", False), ("", False),
])
def test_memoria_manual_respeita_a_reserva_do_compose(valor, aceito):
    assert (_bash(f'memoria_valida "{valor}"').returncode == 0) is aceito


def test_avisa_quando_o_compose_local_nao_le_o_limite(tmp_path):
    """Compose with a local edit: `git pull --ff-only` aborts and the file keeps
    the fixed `memory: 2G` — writing the .env alone changes nothing."""
    velho = tmp_path / "docker-compose.executor.yml"
    velho.write_text("services:\n  executor:\n    deploy: {resources: {limits: {memory: 2G}}}\n")

    assert _bash(f'compose_le_o_limite "{COMPOSE}"').returncode == 0
    assert _bash(f'compose_le_o_limite "{velho}"').returncode != 0
    assert _bash(f'compose_le_o_limite "{tmp_path / "nao-existe.yml"}"').returncode != 0


def test_compose_le_o_limite_do_env_com_2g_de_padrao():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    memoria = compose["services"]["executor"]["deploy"]["resources"]["limits"]["memory"]
    assert memoria == "${EXECUTOR_MEMORIA:-2G}"


def test_o_instalador_grava_o_limite_no_env_do_projeto():
    """Compose interpolates from the .env NEXT TO it — not from executor/.env, which is the
    container's environment."""
    assert "EXECUTOR_MEMORIA=%s" in INSTALL_SH
    assert "docker info --format '{{.MemTotal}}'" in INSTALL_SH
    assert "--memoria=*)" in INSTALL_SH
