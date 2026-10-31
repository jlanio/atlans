"""POST /credentials/test for databases connects from the API host
(review of 2026-10-31): internal addresses refused, port must be a number."""
import pytest

from app.api.routers import credentials_router as R
from app.core.credentials.connection_builder import build_connection_data, porta_valida
from app.services.credential_service import validation_error


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"])
async def test_internal_database_hosts_are_refused(host):
    resposta = await R._test_db_connection(
        "postgresql", {"host": host, "port": "5432", "user": "u", "password": "p", "database": "d"},
    )
    assert resposta["ok"] is False
    assert "bloqueado" in resposta["message"]


def test_the_port_is_a_number():
    assert porta_valida("5432") == 5432
    for invalida in ("5432/x?sslmode=disable", "0", "70000", "abc", True):
        assert porta_valida(invalida) is None
    erro = validation_error(
        "postgresql",
        {"host": "db.exemplo.org", "port": "5432/x?sslmode=disable", "user": "u",
         "password": "p", "database": "d"},
    )
    assert erro and "Porta" in erro
    # A stored legacy value never reaches the DSN as text.
    dsn = build_connection_data("postgresql", {"host": "h", "port": "1/x", "user": "u", "password": "p", "database": "d"})
    assert "@h:5432/" in dsn["connectionString"]


class _Engine:
    def __init__(self, falha):
        self.falha = falha

    def connect(self):
        engine = self

        class _Conn:
            def __enter__(self):
                if engine.falha:
                    raise OSError("inalcançável")
                return self

            def __exit__(self, *a):
                return False

            def execute(self, _q):
                return None

        return _Conn()

    def dispose(self):
        pass


@pytest.mark.asyncio
async def test_postgres_gets_every_validated_address_for_libpq_to_fall_back(monkeypatch):
    """Pinning only the first address broke a dual-stack or multi-address host
    whose first address is unreachable (fix review)."""
    import sqlalchemy

    monkeypatch.setattr("flow.utils.geo_helpers.validated_addresses", lambda _h: ["2001:db8::1", "203.0.113.7"])
    chamadas = []

    def _create_engine(url, connect_args=None):
        chamadas.append((str(url), connect_args))
        return _Engine(falha=False)

    monkeypatch.setattr(sqlalchemy, "create_engine", _create_engine)
    resposta = await R._test_db_connection(
        "postgresql", {"host": "db.exemplo.org", "port": "5432", "user": "u", "password": "p", "database": "d"},
    )
    assert resposta["ok"] is True
    (_url, args), = chamadas
    assert args["hostaddr"] == "2001:db8::1,203.0.113.7"
    assert args["host"] == "db.exemplo.org,db.exemplo.org"


@pytest.mark.asyncio
async def test_mysql_tries_the_addresses_in_order(monkeypatch):
    import sqlalchemy

    monkeypatch.setattr("flow.utils.geo_helpers.validated_addresses", lambda _h: ["2001:db8::1", "203.0.113.7"])
    urls = []

    def _create_engine(url, connect_args=None):
        urls.append(str(url))
        return _Engine(falha=len(urls) == 1)      # the first address is unreachable

    monkeypatch.setattr(sqlalchemy, "create_engine", _create_engine)
    resposta = await R._test_db_connection(
        "mysql", {"host": "db.exemplo.org", "port": "3306", "user": "u", "password": "p", "database": "d"},
    )
    assert resposta["ok"] is True
    assert "@[2001:db8::1]:" in urls[0] and "@203.0.113.7:" in urls[1]


def test_validated_addresses_refuses_if_any_is_internal(monkeypatch):
    import socket

    from flow.utils import geo_helpers as G

    def _resolve(_h, _p):
        return [(None, None, None, None, ("8.8.8.8", 0)), (None, None, None, None, ("10.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _resolve)
    with pytest.raises(ValueError):
        G.validated_addresses("db.exemplo.org")

    def _resolve_ok(_h, _p):
        return [(None, None, None, None, ("8.8.8.8", 0))] * 2

    monkeypatch.setattr(socket, "getaddrinfo", _resolve_ok)
    assert G.validated_addresses("db.exemplo.org") == ["8.8.8.8"]
