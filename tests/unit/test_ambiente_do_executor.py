# tests/unit/test_ambiente_do_executor.py
"""
Reading numbers from the executor's environment — the single point in executor/_ambiente.py.

There were two copies of the tolerant reader (`_env_int` in executor/config.py
and in executor/sync/sync_config.py, with different contracts) and five raw
`int(os.getenv(...))` calls in job_validator.py and renewal.py. The raw ones
brought down the IMPORT with ValueError over a typo in .env: with
`EXECUTOR_CLOCK_SKEW_SECONDS=abc` the executor did not even start — exactly
what config's `_env_int` claimed to have fixed.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# Imports in the real executor's order (executor/main.py): config first, then
# the flush that configure_logging() does, and only then the module — which
# main imports with logging already up. The collector sits on root from the start.
_IMPORT_SCRIPT = """
import importlib, json, logging, sys
avisos = []
class _Coletor(logging.Handler):
    def emit(self, record):
        avisos.append(record.getMessage())
logging.getLogger().addHandler(_Coletor())
from executor import config
config.flush_startup_warnings()
modulo = importlib.import_module(sys.argv[1])
print(json.dumps({"valor": getattr(modulo, sys.argv[2]), "avisos": avisos}))
"""


@pytest.mark.parametrize("modulo, variavel, atributo, padrao, bruto", [
    ("executor.job_validator", "EXECUTOR_CLOCK_SKEW_SECONDS", "_CLOCK_SKEW_TOLERANCE_SECONDS", 300, "abc"),
    ("executor.job_validator", "EXECUTOR_MAX_JOB_EXPIRY_SECONDS", "_MAX_EXPIRY_HORIZON_SECONDS", 900, "15m"),
    ("executor.job_validator", "EXECUTOR_MAX_CLOCK_SKEW_SECONDS", "_MAX_CLOCK_SKEW_SECONDS", 900, "9.5"),
    ("executor.renewal", "EXECUTOR_CERT_RENEW_BEFORE_DAYS", "RENEW_BEFORE_DAYS", 7, "sete"),
    ("executor.renewal", "EXECUTOR_CERT_RENEW_CHECK_SECONDS", "RENEW_CHECK_INTERVAL_SECONDS", 3600, "1h"),
    # A valid number, but meaningless: a negative slack would reject an envelope
    # before it expired; a negative renewal interval breaks asyncio.sleep.
    ("executor.job_validator", "EXECUTOR_CLOCK_SKEW_SECONDS", "_CLOCK_SKEW_TOLERANCE_SECONDS", 300, "-60"),
    ("executor.renewal", "EXECUTOR_CERT_RENEW_CHECK_SECONDS", "RENEW_CHECK_INTERVAL_SECONDS", 3600, "-1"),
])
def test_invalid_env_value_does_not_break_the_import(modulo, variavel, atributo, padrao, bruto):
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ), variavel: bruto}
    saida = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT, modulo, atributo], cwd=RAIZ, env=ambiente,
        capture_output=True, text=True, timeout=60,
    )
    assert saida.returncode == 0, f"import de {modulo} caiu:\n{saida.stderr[-1500:]}"

    resultado = json.loads(saida.stdout.strip().splitlines()[-1])
    assert resultado["valor"] == padrao
    # The warning says WHICH variable and WHICH value — otherwise the operator only sees the effect.
    assert any(variavel in a and bruto in a for a in resultado["avisos"]), resultado["avisos"]


def test_read_int_validates_the_range(monkeypatch):
    """MAX_CONCURRENT=0 left the executor online, with capacity 0 (preferred by
    the least-loaded scheduler), accepting jobs that would never run."""
    from executor._ambiente import ler_int

    for bruto, esperado in (
        ("0", 4), ("nao-e-numero", 4), ("8x", 4), ("999999", 4), (" 8 ", 8), ("", 4),
    ):
        monkeypatch.setenv("_TESTE_INT", bruto)
        assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == esperado, bruto

    monkeypatch.delenv("_TESTE_INT")
    assert ler_int("_TESTE_INT", 4) == 4

    # The minimum can be zero where zero is a legitimate choice (e.g. SYNC_MIN_CYCLE).
    monkeypatch.setenv("_TESTE_INT", "0")
    assert ler_int("_TESTE_INT", 5, minimo=0, maximo=3600) == 0


def test_read_float_rejects_what_is_not_a_finite_number(monkeypatch):
    from executor._ambiente import read_float

    for bruto, esperado in (("0.5", 0.5), ("0.1", 1.0), ("abc", 1.0), ("nan", 1.0), ("inf", 1.0)):
        monkeypatch.setenv("_TESTE_FLOAT", bruto)
        assert read_float("_TESTE_FLOAT", 1.0, minimo=0.25) == esperado, bruto


def test_warning_is_held_until_logging_starts_and_goes_straight_out_after(monkeypatch, caplog):
    """config.py is imported before any handler exists: its warning waits for the
    flush. But job_validator, renewal and sync_config are imported AFTER the
    flush — if their warning were also held back, nobody would deliver it."""
    from executor import _ambiente

    monkeypatch.setattr(_ambiente, "_AVISOS_ADIADOS", [])
    monkeypatch.setattr(_ambiente, "_logging_pronto", False)
    monkeypatch.setenv("_TESTE_INT", "abc")

    with caplog.at_level(logging.WARNING):
        assert _ambiente.ler_int("_TESTE_INT", 7) == 7
        assert not caplog.records

        _ambiente.emit_deferred_warnings()
        assert "_TESTE_INT='abc'" in caplog.text

        caplog.clear()
        assert _ambiente.ler_int("_TESTE_INT", 7) == 7
        assert "_TESTE_INT='abc'" in caplog.text

    assert _ambiente._AVISOS_ADIADOS == []


def test_no_copy_of_the_reader_is_left():
    """The copies diverged once; the guard keeps them from coming back."""
    for arquivo in ("config.py", "sync/sync_config.py", "job_validator.py", "renewal.py"):
        texto = (RAIZ / "executor" / arquivo).read_text(encoding="utf-8")
        assert "def _env_int" not in texto, arquivo
        assert "def _env_float" not in texto, arquivo
        assert "int(os.getenv(" not in texto, arquivo
