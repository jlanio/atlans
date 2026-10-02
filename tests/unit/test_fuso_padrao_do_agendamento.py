# tests/unit/test_fuso_padrao_do_agendamento.py
"""
O fuso padrão dos agendamentos vem do ambiente, e é UTC sem ele.

Antes era um fuso fixo (UTC-4) no servidor, no nó e na tela: toda instalação
agendava, sem dizer, no fuso de quem escreveu o código. Agora a instalação o define
em AGENDAMENTO_FUSO_PADRAO (lido em `flow/utils/fuso.py`), e o servidor, o nó e
o schema leem o MESMO valor — divergir recriaria os agendamentos no próximo save.

(Os testes rodam com `America/La_Paz` definido no conftest, de propósito:
ver lá. Aqui cada caso define ou apaga a variável.)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from flow.utils import fuso

RAIZ = Path(__file__).resolve().parents[2]


def test_sem_a_variavel_e_utc(monkeypatch):
    monkeypatch.delenv("AGENDAMENTO_FUSO_PADRAO", raising=False)
    assert fuso.fuso_padrao_do_agendamento() == "UTC"
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", "   ")
    assert fuso.fuso_padrao_do_agendamento() == "UTC"


def test_um_fuso_iana_vale(monkeypatch):
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", " Europe/Lisbon ")
    assert fuso.fuso_padrao_do_agendamento() == "Europe/Lisbon"


@pytest.mark.parametrize("valor", [
    "Marte/Olympus", "../etc/passwd", "UTC-3",
    # Achados da revisão: uma pasta da base abria um diretório (IsADirectoryError
    # cru), e arquivos que não são fuso eram aceitos — o navegador não os conhece.
    "America", "localtime", "posixrules", "Factory",
])
def test_um_valor_que_nao_e_fuso_para_o_arranque(monkeypatch, valor):
    """Valendo UTC em silêncio, um erro de digitação deslocaria os agendamentos."""
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", valor)
    with pytest.raises(ValueError, match="AGENDAMENTO_FUSO_PADRAO"):
        fuso.fuso_padrao_do_agendamento()


def test_a_api_nao_sobe_com_um_fuso_invalido():
    env = {**os.environ, "AGENDAMENTO_FUSO_PADRAO": "Amrica/Sao_Paulo"}
    r = subprocess.run([sys.executable, "-c", "import app.core.constants"], cwd=RAIZ, env=env,
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "AGENDAMENTO_FUSO_PADRAO='Amrica/Sao_Paulo'" in r.stderr


@pytest.mark.parametrize("valor, esperado", [
    (None, "UTC"),
    ("Europe/Lisbon", "Europe/Lisbon"),
])
def test_servidor_no_e_schema_dizem_o_mesmo_fuso(valor, esperado):
    """O valor é lido no import: cada caso roda num processo próprio."""
    codigo = (
        "from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO as c\n"
        "from app.schemas.schedule import ScheduleBase\n"
        "from flow.nodes.trigger.schedule_trigger import ScheduleTrigger\n"
        "no = next(p for p in ScheduleTrigger.description()['properties'] if p['name'] == 'timezone')['default']\n"
        "print(c, ScheduleBase.model_fields['timezone'].default, no)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "AGENDAMENTO_FUSO_PADRAO"}
    if valor is not None:
        env["AGENDAMENTO_FUSO_PADRAO"] = valor
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.split() == [esperado] * 3
