# tests/unit/test_catalogo_configuracao.py
"""
O catálogo de fontes se desliga como a documentação diz, e as variáveis dele
chegam ao container.

O .env.example e docs/sources.md diziam que FONTES_CATALOGO_DIR vazia desliga a
importação, mas o `.strip() or` a devolvia ao padrão; e o compose nem repassava
as três FONTES_* ao container. Na prática, só uma pasta inexistente desligava.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("valor, esperado", [
    (None, "catalogo/geoservicos"),   # fora do .env: a pasta do repositório
    ("", ""),                          # vazia: desliga
    ("  /dados/vault  ", "/dados/vault"),
])
def test_vazia_desliga_e_ausente_vale_o_padrao(valor, esperado):
    env = {k: v for k, v in os.environ.items() if k != "FONTES_CATALOGO_DIR"}
    if valor is not None:
        env["FONTES_CATALOGO_DIR"] = valor
    r = subprocess.run(
        [sys.executable, "-c", "import app.core.config as c; print(repr(c.FONTES_CATALOGO_DIR))"],
        cwd=RAIZ, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip() == repr(esperado)


def test_o_compose_repassa_as_fontes_e_o_vazio_chega_vazio():
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    # Sem os dois-pontos: `${X-padrao}` só usa o padrão quando X não existe.
    assert "FONTES_CATALOGO_DIR: ${FONTES_CATALOGO_DIR-catalogo/geoservicos}" in compose
    for var in ("FONTES_APRENDER_DAS_EXECUCOES", "FONTES_VERIFICACAO_INTERVAL"):
        assert f"{var}: ${{{var}:-}}" in compose
