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
