# tests/unit/test_padroes_do_executor.py
"""
Os padroes do executor escritos fora de executor/config.py tem de bater com ele.

Os mesmos numeros aparecem no `.env.example` (a semente de toda instalacao nova:
static/install.sh, `python -m executor enroll` e o app desktop), no README e na
tela de Ajustes do desktop (desktop/src/shared/limites.ts, com o teste do lado
de la). As copias ja tinham divergido: o `.env.example` semeava
EXECUTOR_MAX_QUEUE_SIZE=40 com o padrao em 50, e a tela de Ajustes mostrava a
fila da instalacao nova como "alterada".
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

_PADROES = """
import json
from executor import config
print(json.dumps({
    "EXECUTOR_MAX_CONCURRENT": config.MAX_CONCURRENT,
    "EXECUTOR_MAX_QUEUE_SIZE": config.MAX_QUEUE_SIZE,
    "EXECUTOR_JOB_TIMEOUT": config.JOB_TIMEOUT,
    "EXECUTOR_SYNC_INTERVAL": config.SYNC_INTERVAL,
    "EXECUTOR_SYNC_MODE": config.SYNC_MODE,
    "EXECUTOR_SYNC_CONFLICT_STRATEGY": config.SYNC_CONFLICT_STRATEGY,
}))
"""


@pytest.fixture(scope="module")
def padroes(tmp_path_factory) -> dict:
    """O que o executor usa quando a variavel NAO esta no ambiente nem no .env."""
    vazio = tmp_path_factory.mktemp("env") / ".env"
    vazio.write_text("", encoding="utf-8")
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith("EXECUTOR_")}
    ambiente.update(PYTHONPATH=str(RAIZ), EXECUTOR_ENV_PATH=str(vazio))
    saida = subprocess.run(
        [sys.executable, "-c", _PADROES], cwd=RAIZ, env=ambiente,
        capture_output=True, text=True, timeout=60, check=True,
    )
    return json.loads(saida.stdout.strip().splitlines()[-1])


def _env_example() -> dict[str, str]:
    valores = {}
    for linha in (RAIZ / "executor" / ".env.example").read_text(encoding="utf-8").splitlines():
        if linha.strip() and not linha.lstrip().startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            valores[chave.strip()] = valor.strip()
    return valores


@pytest.mark.parametrize("variavel", [
    "EXECUTOR_MAX_CONCURRENT", "EXECUTOR_MAX_QUEUE_SIZE", "EXECUTOR_JOB_TIMEOUT",
])
def test_env_example_semeia_os_padroes_de_execucao(padroes, variavel):
    """A tela de Ajustes marca como "alterado" o que difere do padrao: a semente
    nao pode nascer diferente dele."""
    semeado = _env_example().get(variavel)
    assert semeado is None or int(semeado) == padroes[variavel], (
        f"{variavel}={semeado} no .env.example, mas o padrao do executor e {padroes[variavel]}"
    )


def test_env_example_so_semeia_valor_que_o_executor_aceita():
    """A semente do GeoSync difere do padrao DE PROPOSITO (ver o .env.example),
    mas tem de ser um valor que o executor usa — senao ele cai no padrao calado."""
    semente = _env_example()
    assert semente["EXECUTOR_SYNC_MODE"] in ("upload", "download", "bidirectional", "catalog")
    assert int(semente["EXECUTOR_SYNC_INTERVAL"]) >= 1
    assert semente["EXECUTOR_SYNC_CONFLICT_STRATEGY"] in ("local-wins", "remote-wins", "keep-both")


@pytest.mark.parametrize("variavel", [
    "EXECUTOR_MAX_CONCURRENT", "EXECUTOR_MAX_QUEUE_SIZE", "EXECUTOR_JOB_TIMEOUT",
    "EXECUTOR_SYNC_INTERVAL", "EXECUTOR_SYNC_MODE", "EXECUTOR_SYNC_CONFLICT_STRATEGY",
])
def test_readme_do_executor_documenta_o_padrao_real(padroes, variavel):
    texto = (RAIZ / "executor" / "README.md").read_text(encoding="utf-8")
    linha = re.search(rf"^\| `{variavel}` \| `([^`]+)` \|", texto, re.M)
    assert linha, f"{variavel} sumiu da tabela do README"
    assert linha.group(1) == str(padroes[variavel])
