# tests/unit/test_conexao_do_alembic.py
"""How alembic/env.py connects to Postgres (psycopg2): the TLS of DATABASE_URL.

`?ssl=verify-ca` / `verify-full` used to be downgraded to `sslmode=require`
(encrypt without checking the certificate) and DATABASE_CA_CERT was ignored:
the API refused a server with the wrong certificate and `alembic upgrade`, with
the same URL, accepted it. The reading now matches app/core/db.py.

env.py is loaded by path with a stand-in for `alembic.context` in offline mode:
nothing connects, and the module's functions are tested directly.
"""
import contextlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ENV_PY = RAIZ / "alembic" / "env.py"


class _Config:
    config_file_name = None
    config_ini_section = "alembic"

    def get_section(self, *_a, **_k):
        return {}


@pytest.fixture
def env(monkeypatch):
    import alembic

    contexto = types.ModuleType("alembic.context")
    contexto.config = _Config()
    contexto.is_offline_mode = lambda: True
    contexto.configure = lambda **_k: None
    contexto.begin_transaction = contextlib.nullcontext
    contexto.run_migrations = lambda: None
    monkeypatch.setattr(alembic, "context", contexto, raising=False)
    monkeypatch.setitem(sys.modules, "alembic.context", contexto)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/x")  # pragma: allowlist secret
    monkeypatch.delenv("DATABASE_CA_CERT", raising=False)
    # env.py puts the repository root first in sys.path; give it back as it was.
    monkeypatch.setattr(sys, "path", list(sys.path))

    spec = importlib.util.spec_from_file_location("alembic_env_teste", ENV_PY)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


_BASE = "postgresql+psycopg2://u:p@db:5432/x"  # pragma: allowlist secret


@pytest.mark.parametrize("valor", ["verify-ca", "verify-full", "VERIFY-FULL"])
def test_verify_modes_are_kept_with_the_ca(env, monkeypatch, valor):
    monkeypatch.setenv("DATABASE_CA_CERT", "/certs/pg-ca.crt")
    url, args = env._connect_args(f"{_BASE}?ssl={valor}")
    assert url == _BASE
    assert args["sslmode"] == valor.lower()
    assert args["sslrootcert"] == "/certs/pg-ca.crt"


def test_verify_without_ca_leaves_libpq_default_root(env):
    """No sslrootcert: libpq looks for ~/.postgresql/root.crt and refuses without
    it — never a silent downgrade to `require`."""
    _, args = env._connect_args(f"{_BASE}?sslmode=verify-full")
    assert args == {"sslmode": "verify-full"}


@pytest.mark.parametrize("valor, esperado", [
    ("require", "require"), ("prefer", "require"), ("true", "require"), ("1", "require"),
    ("disable", "disable"), ("false", "disable"), ("allow", "disable"),
])
def test_other_values_keep_their_meaning(env, monkeypatch, valor, esperado):
    # The CA only goes with the verify modes: with `require`, libpq would turn a
    # present root into verify-ca — app/core/db.py does not verify there either.
    monkeypatch.setenv("DATABASE_CA_CERT", "/certs/pg-ca.crt")
    _, args = env._connect_args(f"{_BASE}?ssl={valor}")
    assert args == {"sslmode": esperado}


def test_without_the_parameter_nothing_is_forced(env):
    assert env._connect_args(_BASE) == (_BASE, {})


def test_the_other_query_parameters_survive(env):
    url, args = env._connect_args(f"{_BASE}?ssl=verify-ca&application_name=alembic")
    assert url == f"{_BASE}?application_name=alembic"
    assert args["sslmode"] == "verify-ca"
    url, _ = env._connect_args(f"{_BASE}?application_name=alembic&sslmode=verify-ca")
    assert url == f"{_BASE}?application_name=alembic"
    url, _ = env._connect_args(f"{_BASE}?application_name=alembic&ssl=require&connect_timeout=5")
    assert url == f"{_BASE}?application_name=alembic&connect_timeout=5"
