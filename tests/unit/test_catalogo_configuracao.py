# tests/unit/test_catalogo_configuracao.py
"""
The source catalog turns off the way the documentation says, and its variables
reach the container.

.env.example and docs/sources.md said an empty FONTES_CATALOGO_DIR turns off the
import, but the `.strip() or` sent it back to the default; and the compose file
didn't even pass the three FONTES_* to the container. In practice, only a
nonexistent folder turned it off.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("valor, esperado", [
    (None, "catalogo/geoservicos"),   # outside .env: the repository folder
    ("", ""),                          # vazia: desliga
    ("  /dados/vault  ", "/dados/vault"),
])
def test_empty_disables_and_absent_uses_the_default(valor, esperado):
    env = {k: v for k, v in os.environ.items() if k != "FONTES_CATALOGO_DIR"}
    if valor is not None:
        env["FONTES_CATALOGO_DIR"] = valor
    r = subprocess.run(
        [sys.executable, "-c", "import app.core.config as c; print(repr(c.FONTES_CATALOGO_DIR))"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip() == repr(esperado)


def test_compose_passes_the_sources_and_empty_arrives_empty():
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    # Without the colon: `${X-padrao}` only uses the default when X doesn't exist.
    assert "FONTES_CATALOGO_DIR: ${FONTES_CATALOGO_DIR-catalogo/geoservicos}" in compose
    for var in ("FONTES_APRENDER_DAS_EXECUCOES", "FONTES_VERIFICACAO_INTERVAL"):
        assert f"{var}: ${{{var}:-}}" in compose
