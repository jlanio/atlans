"""
Case-insensitive login lockout.

Regression: the user lookup uses `ident.lower()`, but the lockout key used the
raw `ident`. `Admin`, `admin` and `ADMIN` resolve to the SAME account and are
DISTINCT lockout buckets — the per-account lockout (defense against a
distributed botnet) never fires, as long as the case varies on each attempt.

We test the invariant directly: two failed attempts with different cases land
in the SAME bucket. Only two requests, deterministic, within the per-IP rate
limit of 5/min.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.unit._mcp_harness import RedisFalso


@pytest.fixture
def login_client(client):
    """The conftest's client + auth_router's get_db/get_redis overridden.

    The user is never found (scalar_one_or_none -> None), so every attempt
    falls into the failure path that calls _record_failed — exactly the point
    where the lockout key is derived.
    """
    from app.main import app
    from app.api.dependencies import get_db
    from app.api.routers.auth_router import get_redis

    fake_redis = RedisFalso()

    async def _fake_db():
        db = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=result)
        yield db

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        yield client, fake_redis
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_tentativas_com_caixas_diferentes_compartilham_o_balde(login_client):
    client, fake_redis = login_client

    await client.post("/auth/login", json={"identifier": "Admin", "password": "x"})
    await client.post("/auth/login", json={"identifier": "admin", "password": "x"})

    buckets = [k for k in fake_redis.dados if k.startswith("login_failed:")]
    assert buckets == ["login_failed:admin"], (
        f"esperado um unico balde normalizado; encontrados: {buckets}"
    )
    assert fake_redis.dados["login_failed:admin"] == 2, (
        "as duas tentativas deveriam somar no mesmo contador"
    )


@pytest.mark.asyncio
async def test_conta_bloqueada_barra_mesmo_com_caixa_diferente(login_client):
    """If the account is already locked (normalized bucket), varying the case
    doesn't get around the 429."""
    client, fake_redis = login_client
    fake_redis.dados["login_locked:admin"] = "1"
    fake_redis.ttls["login_locked:admin"] = 900

    resp = await client.post("/auth/login", json={"identifier": "ADMIN", "password": "x"})
    assert resp.status_code == 429
