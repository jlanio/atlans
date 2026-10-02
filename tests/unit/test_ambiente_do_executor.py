# tests/unit/test_ambiente_do_executor.py
"""
Leitura de numeros do ambiente do executor — o ponto unico em executor/_ambiente.py.

Havia duas copias do leitor tolerante (`_env_int` em executor/config.py e em
executor/sync/sync_config.py, com contratos diferentes) e cinco
`int(os.getenv(...))` crus em job_validator.py e renewal.py. Os crus derrubavam o
IMPORT com ValueError por um erro de digitacao no .env: com
`EXECUTOR_CLOCK_SKEW_SECONDS=abc` o executor nem subia — exatamente o que o
`_env_int` do config dizia ter corrigido.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# Importa na ordem do executor de verdade (executor/main.py): config primeiro,
# depois o flush que configure_logging() faz, e so entao o modulo — que o main
# importa com o logging ja no ar. O coletor fica no root desde o inicio.
_IMPORTAR = """
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
    # Numero valido, mas sem sentido: folga negativa recusaria envelope antes
    # de vencer; intervalo negativo do renewal quebra o asyncio.sleep.
    ("executor.job_validator", "EXECUTOR_CLOCK_SKEW_SECONDS", "_CLOCK_SKEW_TOLERANCE_SECONDS", 300, "-60"),
    ("executor.renewal", "EXECUTOR_CERT_RENEW_CHECK_SECONDS", "RENEW_CHECK_INTERVAL_SECONDS", 3600, "-1"),
])
def test_valor_invalido_no_ambiente_nao_derruba_o_import(modulo, variavel, atributo, padrao, bruto):
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ), variavel: bruto}
    saida = subprocess.run(
        [sys.executable, "-c", _IMPORTAR, modulo, atributo], cwd=RAIZ, env=ambiente,
        capture_output=True, text=True, timeout=60,
    )
    assert saida.returncode == 0, f"import de {modulo} caiu:\n{saida.stderr[-1500:]}"

    resultado = json.loads(saida.stdout.strip().splitlines()[-1])
    assert resultado["valor"] == padrao
    # O aviso diz QUAL variavel e QUAL valor — senao o operador so ve o efeito.
    assert any(variavel in a and bruto in a for a in resultado["avisos"]), resultado["avisos"]


def test_ler_int_valida_a_faixa(monkeypatch):
    """MAX_CONCURRENT=0 deixava o executor online, com capacity 0 (preferido pelo
    scheduler least-loaded), aceitando jobs que nunca executariam."""
    from executor._ambiente import ler_int

    for bruto, esperado in (
        ("0", 4), ("nao-e-numero", 4), ("8x", 4), ("999999", 4), (" 8 ", 8), ("", 4),
    ):
        monkeypatch.setenv("_TESTE_INT", bruto)
        assert ler_int("_TESTE_INT", 4, minimo=1, maximo=256) == esperado, bruto

    monkeypatch.delenv("_TESTE_INT")
    assert ler_int("_TESTE_INT", 4) == 4

    # O minimo pode ser zero onde zero e escolha legitima (ex.: SYNC_MIN_CYCLE).
    monkeypatch.setenv("_TESTE_INT", "0")
    assert ler_int("_TESTE_INT", 5, minimo=0, maximo=3600) == 0


def test_ler_float_recusa_o_que_nao_e_numero_finito(monkeypatch):
    from executor._ambiente import ler_float

    for bruto, esperado in (("0.5", 0.5), ("0.1", 1.0), ("abc", 1.0), ("nan", 1.0), ("inf", 1.0)):
        monkeypatch.setenv("_TESTE_FLOAT", bruto)
        assert ler_float("_TESTE_FLOAT", 1.0, minimo=0.25) == esperado, bruto


def test_aviso_fica_retido_ate_o_logging_subir_e_sai_direto_depois(monkeypatch, caplog):
    """config.py e importado antes de existir handler: o aviso espera o flush.
    Mas job_validator, renewal e sync_config sao importados DEPOIS do flush —
    se o aviso deles tambem ficasse retido, ninguem mais o entregaria."""
    from executor import _ambiente

    monkeypatch.setattr(_ambiente, "_AVISOS_ADIADOS", [])
    monkeypatch.setattr(_ambiente, "_logging_pronto", False)
    monkeypatch.setenv("_TESTE_INT", "abc")

    with caplog.at_level(logging.WARNING):
        assert _ambiente.ler_int("_TESTE_INT", 7) == 7
        assert not caplog.records

        _ambiente.emitir_avisos_adiados()
        assert "_TESTE_INT='abc'" in caplog.text

        caplog.clear()
        assert _ambiente.ler_int("_TESTE_INT", 7) == 7
        assert "_TESTE_INT='abc'" in caplog.text

    assert _ambiente._AVISOS_ADIADOS == []


def test_nenhuma_copia_do_leitor_sobrou():
    """As copias divergiram uma vez; a guarda impede que voltem."""
    for arquivo in ("config.py", "sync/sync_config.py", "job_validator.py", "renewal.py"):
        texto = (RAIZ / "executor" / arquivo).read_text(encoding="utf-8")
        assert "def _env_int" not in texto, arquivo
        assert "def _env_float" not in texto, arquivo
        assert "int(os.getenv(" not in texto, arquivo
