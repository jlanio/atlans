"""Session lifecycle and login hardening (full-project review, auth block).

What dies if any of these fails:

- A password reset that leaves the old browser sessions alive: whoever had the
  password keeps renewing the cookie forever (`session_revoked` in the access
  path and in /auth/refresh, `fam_iat` kept across refreshes).
- The per-ACCOUNT lockout: username and email were separate buckets, 2 x 5
  guesses per window.
- The bcrypt that ran only for known identifiers (~1 ms vs ~250 ms tells which
  accounts exist).
- /auth/logout refusing an expired access token, leaving the refresh family
  alive after "Sair".
- Single-use links read with GET then DEL (two concurrent uses both pass).
"""
import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import APP_SECRET
from app.core.utils import jwt_utils
from app.core.utils.jwt_utils import (
    AUDIENCE_ACCESS,
    AUDIENCE_REFRESH,
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_user_sessions,
    session_revoked,
)
from tests.unit._mcp_harness import FakeRedis

USUARIO = "user-sessao-1"
MARCA = f"sessions_revoked_at:{USUARIO}"


# ── session_revoked: the rule ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_without_a_revocation_every_session_is_valid():
    r = FakeRedis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert await session_revoked({"sub": USUARIO, "fam_iat": 1}) is False
        assert await session_revoked({"sub": USUARIO}) is False


@pytest.mark.asyncio
async def test_the_reset_ends_sessions_opened_before_it_and_spares_the_later_ones():
    r = FakeRedis()
    with patch("app.core.redis.get_redis_pool", return_value=r):
        antes = jwt_utils.session_opened_at() - 1
        await revoke_user_sessions(USUARIO)
        depois = int(r.dados[MARCA]) + 1
        assert await session_revoked({"sub": USUARIO, "fam_iat": antes}) is True
        assert await session_revoked({"sub": USUARIO, "fam_iat": depois}) is False
        # A token from before the claim existed is older than any mark.
        assert await session_revoked({"sub": USUARIO}) is True
        # Another user's sessions are not touched.
        assert await session_revoked({"sub": "outro", "fam_iat": antes}) is False
    # The mark outlives the longest token issued before it (a refresh token).
    assert r.ttls[MARCA] >= jwt_utils._REFRESH_FAMILY_TTL


@pytest.mark.asyncio
async def test_without_redis_the_answer_is_503_not_a_valid_session():
    quebrado = MagicMock()
    quebrado.get = AsyncMock(side_effect=ConnectionError("redis fora"))
    with patch("app.core.redis.get_redis_pool", return_value=quebrado):
        with pytest.raises(HTTPException) as erro:
            await session_revoked({"sub": USUARIO, "fam_iat": 1})
    assert erro.value.status_code == 503


@pytest.mark.asyncio
async def test_the_access_path_refuses_a_token_of_a_revoked_session():
    from app.api.dependencies import validate_access_token_claims

    r = FakeRedis()
    token = create_access_token({"sub": USUARIO, "username": "u", "family": "f", "fam_iat": 1})
    with patch("app.core.redis.get_redis_pool", return_value=r):
        assert (await validate_access_token_claims(token))["sub"] == USUARIO
        await revoke_user_sessions(USUARIO)
        assert await validate_access_token_claims(token) is None


# ── /auth/refresh ────────────────────────────────────────────────────────────


def _refresh(fam_iat=None, family="fam-1"):
    dados = {"sub": USUARIO, "username": "u", "family": family, "jti": "jti-1"}
    if fam_iat is not None:
        dados["fam_iat"] = fam_iat
    return create_refresh_token(dados)


@pytest.fixture
def api_refresh(client):
    from app.main import app
    from app.api.dependencies import get_db

    usuario = SimpleNamespace(id_hash=USUARIO, username="u", is_active=True)

    async def _db():
        db = MagicMock()
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=usuario)
        db.execute = AsyncMock(return_value=res)
        yield db

    r = FakeRedis()
    app.dependency_overrides[get_db] = _db
    try:
        with patch("app.core.redis.get_redis_pool", return_value=r):
            yield client, r
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_refresh_of_a_session_opened_before_the_reset_is_401_and_kills_the_family(api_refresh):
    client, r = api_refresh
    r.dados["refresh_family:fam-1"] = "jti-1"
    await revoke_user_sessions(USUARIO)
    rotacao = AsyncMock(return_value=("ok", "jti-2"))
    with patch("app.api.routers.auth_router.rotate_refresh_family", rotacao):
        resp = await client.post("/auth/refresh", json={"refresh_token": _refresh(fam_iat=1)})
    assert resp.status_code == 401
    rotacao.assert_not_awaited()
    assert "refresh_family:fam-1" not in r.dados


@pytest.mark.asyncio
async def test_refresh_keeps_the_moment_the_session_was_opened(api_refresh):
    client, _r = api_refresh
    aberta = jwt_utils.session_opened_at()
    with patch("app.api.routers.auth_router.rotate_refresh_family", AsyncMock(return_value=("ok", "jti-2"))):
        resp = await client.post("/auth/refresh", json={"refresh_token": _refresh(fam_iat=aberta)})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    acesso = jwt.decode(corpo["access_token"], APP_SECRET, algorithms=["HS256"], audience=AUDIENCE_ACCESS)
    renovado = jwt.decode(corpo["refresh_token"], APP_SECRET, algorithms=["HS256"], audience=AUDIENCE_REFRESH)
    # Renewing must not make the session "newer" than a later reset.
    assert acesso["fam_iat"] == renovado["fam_iat"] == aberta
    assert renovado["jti"] == "jti-2"


@pytest.mark.asyncio
async def test_refresh_of_a_token_without_the_claim_gets_the_oldest_moment(api_refresh):
    client, _r = api_refresh
    with patch("app.api.routers.auth_router.rotate_refresh_family", AsyncMock(return_value=("ok", "jti-2"))):
        resp = await client.post("/auth/refresh", json={"refresh_token": _refresh()})
    assert resp.status_code == 200, resp.text
    acesso = jwt.decode(resp.json()["access_token"], APP_SECRET, algorithms=["HS256"], audience=AUDIENCE_ACCESS)
    assert acesso["fam_iat"] == 0


# ── /auth/login ──────────────────────────────────────────────────────────────

SENHA = "SenhaCorreta!123"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def hash_da_senha():
    return hash_password(SENHA)


@pytest.fixture
def api_login(client, hash_da_senha):
    from app.main import app
    from app.api.dependencies import get_db
    from app.api.routers.auth_router import get_redis

    estado = {"usuario": SimpleNamespace(
        id_hash=USUARIO, username="ana", email="ana@exemplo.org",
        hashed_password=hash_da_senha, status="active", email_verified=True,
        last_login_at=None,
    )}
    r = FakeRedis()

    async def _db():
        db = MagicMock()
        res = MagicMock()
        res.scalar_one_or_none = MagicMock(side_effect=lambda: estado["usuario"])
        db.execute = AsyncMock(return_value=res)
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = lambda: r
    try:
        with patch("app.core.redis.get_redis_pool", return_value=r):
            yield client, r, estado
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_username_and_email_share_the_account_lockout(api_login):
    client, r, _estado = api_login
    respostas = []
    for ident in ["ana", "ana@exemplo.org", "ana", "ana@exemplo.org", "ana"]:
        resp = await client.post("/auth/login", json={"identifier": ident, "password": "errada"})  # pragma: allowlist secret
        respostas.append(resp.status_code)
    # Five wrong guesses at the account, whichever identifier: locked.
    assert respostas == [401, 401, 401, 401, 429]
    assert f"login_locked:account:{USUARIO}" in r.dados
    # ...and the email does not open a fresh bucket of guesses — not even with
    # the right password.
    resp = await client.post("/auth/login", json={"identifier": "ana@exemplo.org", "password": SENHA})
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_a_successful_login_clears_the_account_bucket_and_opens_a_dated_session(api_login):
    client, r, _estado = api_login
    await client.post("/auth/login", json={"identifier": "ana", "password": "errada"})  # pragma: allowlist secret
    assert r.dados.get(f"login_failed:account:{USUARIO}") == 1

    antes = jwt_utils.session_opened_at()
    resp = await client.post("/auth/login", json={"identifier": "ana@exemplo.org", "password": SENHA})
    assert resp.status_code == 200, resp.text
    assert f"login_failed:account:{USUARIO}" not in r.dados
    corpo = resp.json()
    for token, aud in ((corpo["access_token"], AUDIENCE_ACCESS), (corpo["refresh_token"], AUDIENCE_REFRESH)):
        claims = jwt.decode(token, APP_SECRET, algorithms=["HS256"], audience=aud)
        assert claims["fam_iat"] >= antes


@pytest.mark.asyncio
async def test_an_unknown_identifier_still_pays_the_bcrypt(api_login):
    client, _r, estado = api_login
    estado["usuario"] = None
    chamadas = []

    def _verificar(senha, hashed):
        chamadas.append(hashed)
        return False

    with patch("app.api.routers.auth_router.verify_password", _verificar):
        resp = await client.post("/auth/login", json={"identifier": "ninguem", "password": "x"})
    assert resp.status_code == 401
    assert len(chamadas) == 1 and chamadas[0].startswith("$bcrypt-sha256$")


@pytest.mark.asyncio
async def test_the_dummy_hash_never_logs_anyone_in(api_login):
    """Even if verify_password said yes for the dummy hash, no user means 401."""
    client, _r, estado = api_login
    estado["usuario"] = None
    with patch("app.api.routers.auth_router.verify_password", lambda *_a: True):
        resp = await client.post("/auth/login", json={"identifier": "ninguem", "password": "x"})
    assert resp.status_code == 401


# ── /auth/logout ─────────────────────────────────────────────────────────────


def _acesso(expira_em: timedelta, family="fam-9", **extra):
    return jwt_utils._encode(
        {"sub": USUARIO, "username": "u", "family": family, "type": "access", **extra},
        expira_em, AUDIENCE_ACCESS,
    )


@pytest.mark.asyncio
async def test_logout_with_an_expired_token_still_revokes_the_family(api_refresh):
    client, r = api_refresh
    r.dados["refresh_family:fam-9"] = "jti"
    token = _acesso(timedelta(minutes=-5))
    resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert "refresh_family:fam-9" not in r.dados
    assert any(k.startswith("token_blacklist:") for k in r.dados)


@pytest.mark.asyncio
@pytest.mark.parametrize("cabecalho", [
    None,
    "Bearer nao-e-um-jwt",
    # signed with another key
    "Bearer " + jwt.encode(
        {"sub": USUARIO, "type": "access", "aud": AUDIENCE_ACCESS, "exp": 4102444800, "family": "fam-9"},
        "outra-chave-com-tamanho-suficiente-para-hs256", algorithm="HS256",
    ),
    # ours, but a refresh token
    "Bearer " + jwt_utils._encode(
        {"sub": USUARIO, "type": "refresh", "family": "fam-9"}, timedelta(days=1), AUDIENCE_REFRESH,
    ),
])
async def test_logout_refuses_what_is_not_our_access_token(api_refresh, cabecalho):
    client, r = api_refresh
    r.dados["refresh_family:fam-9"] = "jti"
    headers = {"Authorization": cabecalho} if cabecalho else {}
    resp = await client.post("/auth/logout", headers=headers)
    assert resp.status_code == 401
    assert "refresh_family:fam-9" in r.dados


# ── single-use links ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_reset_link_is_consumed_once_even_by_concurrent_requests():
    from app.services import token_service

    r = FakeRedis()
    with patch("app.services.token_service.get_redis_pool", return_value=r):
        token = await token_service.create_password_reset_token(USUARIO)
        resultados = await asyncio.gather(
            token_service.verify_password_reset_token(token),
            token_service.verify_password_reset_token(token),
        )
    assert sorted(resultados, key=str) == [None, USUARIO]
    assert f"pwd_reset_user:{USUARIO}" not in r.dados


@pytest.mark.asyncio
async def test_an_email_link_is_consumed_once():
    from app.services import token_service

    r = FakeRedis()
    with patch("app.services.token_service.get_redis_pool", return_value=r):
        token = await token_service.create_email_verification_token(USUARIO)
        assert await token_service.verify_email_token(token) == USUARIO
        assert await token_service.verify_email_token(token) is None


@pytest.mark.asyncio
async def test_a_password_reset_clears_the_account_lockout(api_login):
    """Locking the account by its username must not outlast a password reset:
    the owner proved they hold the e-mail and gets the login back."""
    client, r, estado = api_login
    for _ in range(5):
        await client.post("/auth/login", json={"identifier": "ana", "password": "errada"})  # pragma: allowlist secret
    assert f"login_locked:account:{USUARIO}" in r.dados

    estado["usuario"].email = "ana@exemplo.org"
    with patch("app.api.routers.auth_router.verify_password_reset_token", AsyncMock(return_value=USUARIO)), \
         patch("app.services.api_token_service.revoke_all_for_user", AsyncMock()):
        resp = await client.post(
            "/auth/reset-password",
            json={"token": "t", "password": "NovaSenha!12345", "password_confirm": "NovaSenha!12345"},  # pragma: allowlist secret
        )
    assert resp.status_code == 200, resp.text
    assert not [k for k in r.dados if k.startswith("login_locked:") or k.startswith("login_failed:")]
