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


def test_verify_full_trusts_the_system_roots_and_the_ca(env, monkeypatch, tmp_path):
    """verify-full checks the host name: the system's roots plus the private CA,
    the same roots the API trusts."""
    sistema = tmp_path / "sistema.pem"
    sistema.write_text("SISTEMA\n")
    ca = tmp_path / "pg-ca.crt"
    ca.write_text("PRIVADA\n")
    monkeypatch.setattr(env, "_bundle_do_sistema", lambda: str(sistema))
    monkeypatch.setenv("DATABASE_CA_CERT", str(ca))
    for valor in ("verify-full", "VERIFY-FULL"):
        url, args = env._connect_args(f"{_BASE}?ssl={valor}")
        assert url == _BASE
        assert args["sslmode"] == "verify-full"
        assert Path(args["sslrootcert"]).read_text() == "SISTEMA\nPRIVADA\n"


def test_verify_ca_trusts_the_private_ca_alone(env, monkeypatch, tmp_path):
    """verify-ca checks the chain WITHOUT the host name: with public roots too,
    any publicly issued certificate let a MITM into the migration (round-2
    review). A missing CA file is passed as is — libpq fails naming it."""
    monkeypatch.setattr(env, "_bundle_do_sistema", lambda: "/etc/ssl/certs/ca-certificates.crt")
    ca = tmp_path / "pg-ca.crt"
    ca.write_text("PRIVADA\n")
    monkeypatch.setenv("DATABASE_CA_CERT", str(ca))
    _, args = env._connect_args(f"{_BASE}?ssl=verify-ca")
    assert args == {"sslmode": "verify-ca", "sslrootcert": str(ca)}

    monkeypatch.setenv("DATABASE_CA_CERT", "/nao/existe/pg-ca.crt")
    _, args = env._connect_args(f"{_BASE}?ssl=verify-ca")
    assert args["sslrootcert"] == "/nao/existe/pg-ca.crt"


def test_verify_ca_without_a_ca_lets_libpq_refuse_the_public_roots(env, monkeypatch):
    """libpq refuses verify-ca with sslrootcert=system, saying why: the
    migration fails closed instead of trusting any public certificate."""
    monkeypatch.delenv("DATABASE_CA_CERT", raising=False)
    _, args = env._connect_args(f"{_BASE}?ssl=verify-ca")
    assert args == {"sslmode": "verify-ca", "sslrootcert": "system"}


@pytest.mark.parametrize("ca", [None, "/nao/existe/pg-ca.crt"])
def test_verify_full_without_a_ca_file_uses_the_system_roots(env, monkeypatch, tmp_path, ca):
    """The host name is checked, so the system's roots are safe — and the API,
    with the same URL, trusts them: the migration connects where the API does."""
    sistema = tmp_path / "sistema.pem"
    sistema.write_text("SISTEMA\n")
    monkeypatch.setattr(env, "_bundle_do_sistema", lambda: str(sistema))
    if ca:
        monkeypatch.setenv("DATABASE_CA_CERT", ca)
    _, args = env._connect_args(f"{_BASE}?sslmode=verify-full")
    assert args == {"sslmode": "verify-full", "sslrootcert": str(sistema)}


def test_without_any_system_bundle_libpq_reads_its_own_store(env, monkeypatch):
    monkeypatch.setattr(env, "_bundle_do_sistema", lambda: None)
    _, args = env._connect_args(f"{_BASE}?sslmode=verify-full")
    assert args["sslrootcert"] == "system"


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


def test_the_migration_session_is_utc(env):
    """Like the API's (app/core/db.py): `now()` into a TIMESTAMP column is UTC."""
    assert env._session_options(_BASE) == "-c timezone=UTC"


def test_the_url_options_are_kept_next_to_the_time_zone(env):
    """connect_args replaces the URL's `options`: they have to be carried over."""
    url = f"{_BASE}?options=-c%20search_path%3Dpublic"
    assert env._session_options(url) == "-c search_path=public -c timezone=UTC"


def test_the_other_query_parameters_survive(env):
    url, args = env._connect_args(f"{_BASE}?ssl=verify-ca&application_name=alembic")
    assert url == f"{_BASE}?application_name=alembic"
    assert args["sslmode"] == "verify-ca"
    url, _ = env._connect_args(f"{_BASE}?application_name=alembic&sslmode=verify-ca")
    assert url == f"{_BASE}?application_name=alembic"
    url, _ = env._connect_args(f"{_BASE}?application_name=alembic&ssl=require&connect_timeout=5")
    assert url == f"{_BASE}?application_name=alembic&connect_timeout=5"
