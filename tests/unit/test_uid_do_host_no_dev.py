"""
The development API starts when the host user has a UID other than 1000.

`docker compose --profile dev` mounts the repository at /app and runs the API
as UID 1000. With another host UID, the .env from make bootstrap (mode 600)
cannot be read in there and app.log cannot be created in the repository: both
used to raise PermissionError at import, and the API never answered. The
compose file passes the environment itself, so neither file is required.
"""
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.core.utils import logger as modulo_logger

RAIZ = Path(__file__).resolve().parents[2]


@contextmanager
def root_sem_handlers():
    """pytest attaches its own handler to root, and with one there get_logger
    only propagates: it would never reach the file. Emptied in place, inside
    the test, and put back before pytest removes its handler."""
    root = logging.getLogger()
    guardados = root.handlers[:]
    root.handlers.clear()
    try:
        yield
    finally:
        root.handlers[:] = guardados


@pytest.fixture
def sem_arquivo_de_log(monkeypatch):
    """A LOG_FILE that cannot be opened."""
    tentativas = []

    def recusa(*args, **kwargs):
        tentativas.append(args)
        raise PermissionError(13, "Permission denied", "app.log")

    monkeypatch.setattr(modulo_logger, "RotatingFileHandler", recusa)
    monkeypatch.setattr(modulo_logger, "_arquivo_de_log_falhou", False)
    nomes = []
    yield tentativas, nomes
    for nome in nomes:
        registrado = logging.getLogger(nome)
        for handler in list(registrado.handlers):
            registrado.removeHandler(handler)
            handler.close()
        registrado.propagate = True


def test_log_file_without_permission_keeps_the_console(sem_arquivo_de_log, capsys):
    tentativas, nomes = sem_arquivo_de_log
    nomes.append("teste.uid.console")

    with root_sem_handlers():
        registrado = modulo_logger.get_logger("teste.uid.console")

    assert [type(h) for h in registrado.handlers] == [logging.StreamHandler]
    assert "o log segue só no console" in capsys.readouterr().err
    assert len(tentativas) == 1


def test_log_file_failure_is_tried_and_reported_once(sem_arquivo_de_log, capsys):
    tentativas, nomes = sem_arquivo_de_log
    nomes.extend(["teste.uid.a", "teste.uid.b"])

    with root_sem_handlers():
        modulo_logger.get_logger("teste.uid.a")
        modulo_logger.get_logger("teste.uid.b")

    assert len(tentativas) == 1
    assert capsys.readouterr().err.count("indisponível") == 1


def test_unreadable_dotenv_does_not_stop_the_config_import():
    """A fresh interpreter: config runs load_dotenv() at import."""
    codigo = (
        "import dotenv\n"
        "def recusa(*a, **k):\n"
        "    raise PermissionError(13, 'Permission denied', '/app/.env')\n"
        "dotenv.load_dotenv = recusa\n"
        "import app.core.config\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env={**os.environ, "PYTHONPATH": str(RAIZ)},
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "/app/.env ilegível" in resultado.stderr
