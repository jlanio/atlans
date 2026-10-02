"""
Lockout de login insensivel a caixa.

Regressao: a busca do usuario usa `ident.lower()`, mas a chave de lockout usava
o `ident` cru. `Admin`, `admin` e `ADMIN` resolvem a MESMA conta e sao baldes de
lockout DISTINTOS — o bloqueio por conta (defesa contra botnet distribuido)
nunca dispara, bastando variar a caixa a cada tentativa.

Testamos o invariante direto: duas tentativas falhas com caixas diferentes
caem no MESMO balde. Duas requisicoes so, deterministico, dentro do rate-limit
por IP de 5/min.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.unit._mcp_harness import RedisFalso


@pytest.fixture
def login_client(client):
    """client do conftest + get_db/get_redis do auth_router sobrescritos.

    O usuario nunca e encontrado (scalar_one_or_none -> None), entao toda
    tentativa cai no caminho de falha que chama _record_failed — exatamente o
    ponto onde a chave de lockout e derivada.
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
    """Se a conta ja esta bloqueada (balde normalizado), variar a caixa nao
    contorna o 429."""
    client, fake_redis = login_client
    fake_redis.dados["login_locked:admin"] = "1"
    fake_redis.ttls["login_locked:admin"] = 900

    resp = await client.post("/auth/login", json={"identifier": "ADMIN", "password": "x"})
    assert resp.status_code == 429
