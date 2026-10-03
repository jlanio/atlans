# tests/unit/test_padroes_do_executor.py
"""
The executor defaults written outside executor/config.py must match it.

The same numbers appear in `.env.example` (the seed of every new installation:
static/install.sh, `python -m executor enroll` and the desktop app), in the README
and in the desktop Settings screen (desktop/src/shared/limites.ts, with the test
on that side). The copies had already diverged: `.env.example` seeded
EXECUTOR_MAX_QUEUE_SIZE=40 with the default at 50, and the Settings screen showed
the new installation's queue as "alterada" (changed).
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
    """What the executor uses when the variable is NOT in the environment nor in .env."""
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
    """The Settings screen marks as "alterado" (changed) whatever differs from the
    default: the seed cannot be born different from it."""
    semeado = _env_example().get(variavel)
    assert semeado is None or int(semeado) == padroes[variavel], (
        f"{variavel}={semeado} no .env.example, mas o padrao do executor e {padroes[variavel]}"
    )


def test_env_example_so_semeia_valor_que_o_executor_aceita():
    """The GeoSync seed differs from the default ON PURPOSE (see .env.example),
    but it has to be a value the executor uses — otherwise it silently falls back to the default."""
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
