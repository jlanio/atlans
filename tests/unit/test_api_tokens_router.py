"""
/auth/tokens — as rotas do token pessoal de acesso.

Banco real (SQLite) por trás da app real: o que se afirma aqui é o contrato
HTTP — 201 com o segredo uma vez, lista sem segredo, revogação idempotente,
404 para token alheio, 409 no teto, 422 de validação no formato do repo, 401
sem sessão — e que o reset de senha derruba os tokens.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.authorization import pat
from app.core.rate_limiter import limiter
from app.core.utils.datetime_utils import utc_now_naive
from app.models.api_token import ApiToken
from app.models.base import Base
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

TABELAS = [User.__table__, Workspace.__table__, WorkspaceMember.__table__, ApiToken.__table__]
USUARIO = "usr-test-001"  # o id_hash do mock_current_user do conftest


@pytest_asyncio.fixture
async def sessao():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as s:
        s.add_all([
            User(id_hash=USUARIO, username="teste", email="t@x.test", hashed_password="x"),
            # A outra pessoa existe de verdade: `api_tokens.user_id` tem FK para
            # `users`, e o SQLite só não a impõe por padrão.
            User(id_hash="u-outro", username="outro", email="o@x.test", hashed_password="x"),
            Workspace(id_hash="ws-test-001", name="Meu", owner_id=USUARIO),
            Workspace(id_hash="ws-outro", name="Alheio", owner_id="u-outro"),
        ])
        await s.commit()
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def api(client, sessao, monkeypatch):
    """Cliente autenticado (conftest) com o banco SQLite no lugar do get_db."""
    from app.api.dependencies import get_db
    from app.main import app

    async def _db():
        yield sessao

    app.dependency_overrides[get_db] = _db
    # O `10/hour` é real e conta por IP entre testes do mesmo processo.
    monkeypatch.setattr(limiter, "enabled", False)
    yield client
    app.dependency_overrides.pop(get_db, None)


def _payload(**extra):
    base = {"name": "Claude Code", "scopes": ["workflows:read", "runs:execute"], "expires_in_days": 90}
    base.update(extra)
    return base


# ── contrato HTTP ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_cria_e_mostra_o_segredo_uma_unica_vez(api, sessao):
    resp = await api.post("/auth/tokens", json=_payload(workspace_ids=["ws-test-001"]))

    assert resp.status_code == 201, resp.text
    corpo = resp.json()
    assert pat.e_segredo_pat(corpo["token"])
    assert corpo["token_prefix"] == corpo["token"][:12]
    assert corpo["status"] == "active" and corpo["revoked_at"] is None and corpo["last_used_at"] is None
    assert corpo["scopes"] == ["workflows:read", "runs:execute"]
    assert corpo["workspace_ids"] == ["ws-test-001"]
    assert set(corpo) == {
        "id", "name", "token_prefix", "scopes", "workspace_ids", "expires_at",
        "last_used_at", "revoked_at", "created_at", "status", "token",
    }

    # No banco só o hash; a listagem nunca devolve o segredo.
    linha = (await sessao.execute(select(ApiToken).where(ApiToken.id_hash == corpo["id"]))).scalar_one()
    assert linha.token_hash == pat.hash_segredo(corpo["token"])
    lista = (await api.get("/auth/tokens")).json()
    assert [t["id"] for t in lista] == [corpo["id"]]
    assert "token" not in lista[0]


@pytest.mark.asyncio
async def test_post_valida_o_corpo_no_formato_do_repo(api):
    r = await api.post("/auth/tokens", json=_payload(scopes=["admin"]))
    assert r.status_code == 422
    assert "Escopo desconhecido" in r.text

    r = await api.post("/auth/tokens", json=_payload(scopes=[]))
    assert r.status_code == 422

    r = await api.post("/auth/tokens", json=_payload(expires_in_days=400))
    assert r.status_code == 422

    r = await api.post("/auth/tokens", json=_payload(workspace_ids=[]))
    assert r.status_code == 422

    r = await api.post("/auth/tokens", json=_payload(extra="nao"))
    assert r.status_code == 422  # extra="forbid"


@pytest.mark.asyncio
async def test_post_recusa_workspace_de_que_o_usuario_nao_participa(api):
    r = await api.post("/auth/tokens", json=_payload(workspace_ids=["ws-test-001", "ws-outro"]))
    assert r.status_code == 422
    assert r.json()["error"] == "api_token_invalid"


@pytest.mark.asyncio
async def test_teto_de_tokens_ativos_da_409(api, sessao):
    sessao.add_all([
        ApiToken(
            user_id=USUARIO, name=f"t{i}", token_prefix="atl_pat_xxxx",
            token_hash=pat.hash_segredo(f"seed-{i}"), scopes=["workflows:read"],
            expires_at=utc_now_naive() + timedelta(days=5),
        )
        for i in range(pat.MAX_TOKENS_ATIVOS_POR_USUARIO)
    ])
    await sessao.commit()

    r = await api.post("/auth/tokens", json=_payload())
    assert r.status_code == 409
    assert r.json()["error"] == "api_token_limit"


@pytest.mark.asyncio
async def test_delete_revoga_sem_apagar_e_e_idempotente(api):
    criado = (await api.post("/auth/tokens", json=_payload())).json()

    r1 = await api.delete(f"/auth/tokens/{criado['id']}")
    assert r1.status_code == 200
    assert r1.json()["status"] == "revoked" and r1.json()["revoked_at"] is not None
    assert "token" not in r1.json()

    r2 = await api.delete(f"/auth/tokens/{criado['id']}")
    assert r2.status_code == 200
    assert r2.json()["revoked_at"] == r1.json()["revoked_at"]

    lista = (await api.get("/auth/tokens")).json()
    assert lista[0]["status"] == "revoked"  # continua na lista, marcado


@pytest.mark.asyncio
async def test_delete_de_token_alheio_ou_inexistente_da_404(api, sessao):
    sessao.add(ApiToken(
        id_hash="tok-da-outra", user_id="u-outro", name="dela", token_prefix="atl_pat_xxxx",
        token_hash=pat.hash_segredo("seed-outra"), scopes=["workflows:read"],
        expires_at=utc_now_naive() + timedelta(days=5),
    ))
    await sessao.commit()

    r = await api.delete("/auth/tokens/tok-da-outra")
    assert r.status_code == 404
    assert r.json()["error"] == "api_token_not_found"
    assert (await api.delete("/auth/tokens/nao-existe")).status_code == 404


@pytest.mark.asyncio
async def test_sem_sessao_e_401(api):
    from app.api.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)  # o conftest limpa o resto ao fim
    assert (await api.get("/auth/tokens")).status_code == 401
    assert (await api.post("/auth/tokens", json=_payload())).status_code == 401


def test_criacao_tem_rate_limit_de_10_por_hora():
    """Pelo registro do slowapi, não pelo texto-fonte: é o que a request usa."""
    from app.api.routers import api_tokens_router  # noqa: F401 — importar registra a rota no limiter

    limites = limiter._route_limits["app.api.routers.api_tokens_router.criar_token"]
    assert [str(l.limit) for l in limites] == ["10 per 1 hour"]


# ── cascata no reset de senha ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_de_senha_revoga_os_tokens_do_usuario(api, sessao):
    criado = (await api.post("/auth/tokens", json=_payload())).json()

    with patch("app.api.routers.auth_router.verify_password_reset_token", AsyncMock(return_value=USUARIO)), \
         patch("app.api.routers.auth_router.hash_password", lambda senha: "hash-novo"):
        r = await api.post(
            "/auth/reset-password",
            json={"token": "t", "password": "NovaSenha!123", "password_confirm": "NovaSenha!123"},  # pragma: allowlist secret
        )
    assert r.status_code == 200, r.text

    linha = (await sessao.execute(select(ApiToken).where(ApiToken.id_hash == criado["id"]))).scalar_one()
    await sessao.refresh(linha)
    assert linha.revoked_reason == "password_reset"
