"""Timeout for each command in the database (app/core/db.py).

Without a timeout, a stuck query — a lock waiting on another, a bad plan, a
network that vanishes without dropping the connection — held the connection
forever, and a few stuck ones exhausted the worker's pool (POOL_TIMEOUT only
limits the wait for a free connection). Here the wiring is checked; the behavior
against a real Postgres (cancellation as `QueryCanceledError`, reusable
connection, `SET LOCAL` as a per-transaction exception, lock waits counting) was
measured outside the suite, which runs without a database.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core import db

_RAIZ = Path(__file__).resolve().parents[2]


def test_os_dois_prazos_viram_connect_args_do_asyncpg():
    assert db._prazos(60, 90) == {
        "server_settings": {"statement_timeout": "60000"},   # milissegundos
        "command_timeout": 90,
    }


def test_zero_desliga_cada_prazo():
    assert db._prazos(0, 90) == {"command_timeout": 90}
    assert db._prazos(60, 0) == {"server_settings": {"statement_timeout": "60000"}}
    assert db._prazos(0, 0) == {}


def test_avisa_quando_o_asyncpg_desistiria_antes_do_postgres(caplog):
    with caplog.at_level(logging.WARNING, logger=db.logger.name):
        db._prazos(60, 60)
    assert "DB_COMMAND_TIMEOUT" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=db.logger.name):
        db._prazos(60, 90)
    assert caplog.text == ""


def _em_processo_novo(codigo: str, **env: str) -> dict:
    """The config is read at import: each scenario in a clean interpreter."""
    ambiente = {**os.environ, "PYTHONPATH": str(_RAIZ), **env}
    saida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=_RAIZ, env=ambiente,
        capture_output=True, text=True, timeout=120, check=True,
    )
    return json.loads(saida.stdout.strip().splitlines()[-1])


def test_variavel_vazia_vale_o_padrao():
    """Compose passes through `${DB_STATEMENT_TIMEOUT:-}`: empty must not bring down
    the import with `int('')`."""
    lido = _em_processo_novo(
        "import json; from app.core import config as c;"
        "print(json.dumps([c.DB_STATEMENT_TIMEOUT, c.DB_COMMAND_TIMEOUT]))",
        DB_STATEMENT_TIMEOUT="", DB_COMMAND_TIMEOUT="",
    )
    assert lido == [60, 90]


_CAPTURA_DO_CONNECT = """
import asyncio, json
import asyncpg

capturado = {}

async def _connect(*args, **kwargs):
    capturado.update(kwargs)
    raise RuntimeError("sem banco no teste")

asyncpg.connect = _connect

from app.core import db

async def main():
    try:
        async with db.async_engine.connect():
            pass
    except Exception:
        pass

asyncio.run(main())
print(json.dumps({
    "server_settings": capturado.get("server_settings"),
    "command_timeout": capturado.get("command_timeout"),
    "ssl": repr(capturado.get("ssl")),
}))
"""


def test_os_prazos_chegam_ao_asyncpg_connect_sem_perder_o_ssl():
    """What matters is what SQLAlchemy hands to asyncpg.connect, not the dict."""
    lido = _em_processo_novo(
        _CAPTURA_DO_CONNECT,
        DATABASE_URL="postgresql+asyncpg://u:p@127.0.0.1:1/x",  # pragma: allowlist secret
        DB_STATEMENT_TIMEOUT="45", DB_COMMAND_TIMEOUT="70",
    )
    assert lido == {"server_settings": {"statement_timeout": "45000"}, "command_timeout": 70, "ssl": "False"}


@pytest.mark.parametrize("bruto, esperado", [
    ("60s", 60), ("5min", 60), ("1.5", 60), ("  ", 60),   # not an integer: the default, with a warning
    ("-5", 0),                                             # negativo: desligado
    ("99999999", 2_147_483),                               # above this Postgres rejects the connection
    ("120", 120),
])
def test_valor_estranho_nao_derruba_a_importacao(bruto, esperado):
    lido = _em_processo_novo(
        "import json; from app.core import config as c; print(json.dumps(c.DB_STATEMENT_TIMEOUT))",
        DB_STATEMENT_TIMEOUT=bruto,
    )
    assert lido == esperado


_OUVINTE = """
import asyncio, json
from app.core import db
from sqlalchemy import event

chamadas = []

class _Driver:
    def terminate(self):
        chamadas.append("terminate")

class _Conexao:
    driver_connection = _Driver()

registrado = event.contains(db.async_engine.sync_engine, "invalidate", db._abortar_conexao_presa)
resultado = {}
for nome, exc in [
    ("timeout_asyncio", asyncio.TimeoutError()),
    ("timeout", TimeoutError()),
    ("cancelado", asyncio.CancelledError()),
    ("outro", ConnectionResetError()),
    ("nenhum", None),
]:
    chamadas.clear()
    db._abortar_conexao_presa(_Conexao(), None, exc)
    resultado[nome] = list(chamadas)
print(json.dumps({"registrado": registrado, **resultado}))
"""


def test_conexao_invalidada_por_prazo_ou_cancelamento_e_abortada():
    """Without this, with the network silent, asyncpg's polite close waited for the
    cancellation confirmation with no timeout: neither command_timeout nor a
    wait_for around the write returned (measured with a proxy that freezes)."""
    lido = _em_processo_novo(_OUVINTE, DATABASE_URL="postgresql+asyncpg://u:p@127.0.0.1:1/x")  # pragma: allowlist secret
    assert lido == {
        "registrado": True,
        "timeout_asyncio": ["terminate"], "timeout": ["terminate"], "cancelado": ["terminate"],
        "outro": [], "nenhum": [],
    }


def test_a_cli_de_manutencao_roda_sem_prazo():
    """migrar-nos scans whole tables: the API's 60 s would cut it off."""
    codigo = (
        "import json, app.cli; from app.core import config as c;"
        "print(json.dumps([c.DB_STATEMENT_TIMEOUT, c.DB_COMMAND_TIMEOUT]))"
    )
    assert _em_processo_novo(codigo, DB_STATEMENT_TIMEOUT="", DB_COMMAND_TIMEOUT="") == [0, 0]
    assert _em_processo_novo(codigo, DB_STATEMENT_TIMEOUT="30", DB_COMMAND_TIMEOUT="40") == [30, 40]
