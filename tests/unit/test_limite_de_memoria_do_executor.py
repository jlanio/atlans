# tests/unit/test_limite_de_memoria_do_executor.py
"""O limite de memória do executor acompanha a máquina.

O `memory: 2G` fixo do docker-compose.executor.yml matou um executor por OOM do
cgroup — numa máquina de 16 GB com 13 GB livres —, e o job que ele
rodava ficou sem desfecho. Agora o instalador grava EXECUTOR_MEMORIA (75% da
memória que o Docker enxerga) no .env que o compose interpola.

A função é EXECUTADA como está no instalador — recortada entre os marcadores,
não copiada para cá: uma cópia continuaria verde com o script quebrado.
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
    (16 * GIB, "12G"),   # a máquina do incidente: 12G era o que o diagnóstico recomendou
    (8 * GIB, "6G"),
    (4 * GIB, "3G"),
    (64 * GIB, "48G"),
    (int(15.5 * GIB), "11G"),   # arredonda para baixo: nunca promete o que não há
    # Piso: os 2G fixos de antes. Numa VPS de "2 GB" (1,93 GiB) 75% daria 1G, e
    # um job de 1,5 GB que rodava passaria a morrer por OOM.
    (int(2.66 * GIB), "2G"),
    (int(1.93 * GIB), "2G"),
    (512 * 1024 ** 2, "2G"),
])
def test_limite_e_75_por_cento_da_memoria_do_docker(total, esperado):
    assert _limite(total) == esperado


@pytest.mark.parametrize("valor,aceito", [
    ("12G", True), ("1536M", True), ("512M", True), ("512m", True), ("1g", True),
    ("08G", True),                  # zero à esquerda não vira octal
    ("511M", False),                # abaixo da reserva do compose: o Docker recusa
    ("256M", False), ("0G", False),
    ("12", False), ("12GB", False), ("1.5G", False), ("", False),
])
def test_memoria_manual_respeita_a_reserva_do_compose(valor, aceito):
    assert (_bash(f'memoria_valida "{valor}"').returncode == 0) is aceito


def test_avisa_quando_o_compose_local_nao_le_o_limite(tmp_path):
    """Compose com edição local: o `git pull --ff-only` aborta e o arquivo segue
    com o `memory: 2G` fixo — gravar o .env sozinho não muda nada."""
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
    """O compose interpola do .env AO LADO dele — não do executor/.env, que é o
    ambiente do container."""
    assert "EXECUTOR_MEMORIA=%s" in INSTALL_SH
    assert "docker info --format '{{.MemTotal}}'" in INSTALL_SH
    assert "--memoria=*)" in INSTALL_SH
