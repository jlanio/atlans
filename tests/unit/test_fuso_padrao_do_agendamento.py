# tests/unit/test_fuso_padrao_do_agendamento.py
"""
The default schedule time zone comes from the environment, and is UTC without it.

Before, it was a fixed time zone (UTC-4) in the server, the node and the screen: every
installation scheduled, without saying so, in the time zone of whoever wrote the code. Now
the installation defines it in AGENDAMENTO_FUSO_PADRAO (read in `flow/utils/fuso.py`), and
the server, the node and the schema read the SAME value — diverging would recreate the
schedules on the next save.

(The tests run with `America/La_Paz` set in the conftest, on purpose:
see there. Here each case sets or deletes the variable.)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from flow.utils import fuso

RAIZ = Path(__file__).resolve().parents[2]


def test_without_the_variable_it_is_utc(monkeypatch):
    monkeypatch.delenv("AGENDAMENTO_FUSO_PADRAO", raising=False)
    assert fuso.default_schedule_timezone() == "UTC"
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", "   ")
    assert fuso.default_schedule_timezone() == "UTC"


def test_an_iana_timezone_is_valid(monkeypatch):
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", " Europe/Lisbon ")
    assert fuso.default_schedule_timezone() == "Europe/Lisbon"


@pytest.mark.parametrize("valor", [
    "Marte/Olympus", "../etc/passwd", "UTC-3",
    # Review findings: a folder in the database opened a directory (raw IsADirectoryError),
    # and files that are not time zones were accepted — the browser does not know them.
    "America", "localtime", "posixrules", "Factory",
])
def test_a_non_timezone_value_stops_startup(monkeypatch, valor):
    """Silently falling back to UTC, a typo would shift the schedules."""
    monkeypatch.setenv("AGENDAMENTO_FUSO_PADRAO", valor)
    with pytest.raises(ValueError, match="AGENDAMENTO_FUSO_PADRAO"):
        fuso.default_schedule_timezone()


def test_the_api_does_not_start_with_an_invalid_timezone():
    env = {**os.environ, "AGENDAMENTO_FUSO_PADRAO": "Amrica/Sao_Paulo"}
    r = subprocess.run([sys.executable, "-c", "import app.core.constants"], cwd=RAIZ, env=env,
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "AGENDAMENTO_FUSO_PADRAO='Amrica/Sao_Paulo'" in r.stderr


@pytest.mark.parametrize("valor, esperado", [
    (None, "UTC"),
    ("Europe/Lisbon", "Europe/Lisbon"),
])
def test_server_node_and_schema_state_the_same_timezone(valor, esperado):
    """The value is read at import: each case runs in its own process."""
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
