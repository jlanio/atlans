# tests/unit/test_workspace_service.py
"""
`listar_workspaces_do_usuario` — the listing that moved out of `workspace_router.py`.

The router only calls it; what guarantees the contract now is this function, and the MCP
server will depend on it without going through the route. Each test pins a decision the
listing already made and that an "equivalent" rewrite could change:

- an owner who is also listed as a member shows up ONCE, as "owner" (the member
  role does not demote the owner);
- a workspace in the trash (`deleted_at`) is left out — whether the owner's or the
  member's;
- the order is the usual one: first one's own (by name), then the
  shared ones (by name) — not a global ordering;
- `is_default` is echoed and `my_role` is the member's role in the shared ones.

Real database (in-memory SQLite): the function is a query, and a mock of
`db.execute` would only prove that the mock returns what it was told to.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workspace_service import listar_workspaces_do_usuario


@pytest.fixture
async def db():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[User.__table__, Workspace.__table__, WorkspaceMember.__table__],
        )
    async with async_sessionmaker(engine, expire_on_commit=False)() as sessao:
        await _semear(sessao)
        yield sessao
    await engine.dispose()


async def _semear(sessao) -> None:
    """Two users, six workspaces.

    u-dono  owns "Zeta" (and is ALSO a "viewer" member of it), "Beta"
            (is_default) and "Lixo" (in the trash); is editor in "Alfa" and
            operator in "Lixo compartilhado" (in the trash, owned by u-outro).
    u-outro owns "Alfa", "Lixo compartilhado" and "Ômega" (where u-dono
            is not).
    """
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    def _usuario(id_hash: str) -> User:
        return User(id_hash=id_hash, username=id_hash, email=f"{id_hash}@teste", hashed_password="x")

    sessao.add_all([_usuario("u-dono"), _usuario("u-outro")])
    sessao.add_all([
        Workspace(id_hash="ws-zeta", name="Zeta", owner_id="u-dono", description="o principal"),
        Workspace(id_hash="ws-beta", name="Beta", owner_id="u-dono", is_default=True),
        Workspace(id_hash="ws-lixo", name="Lixo", owner_id="u-dono", deleted_at=datetime(2026, 9, 1)),
        Workspace(id_hash="ws-alfa", name="Alfa", owner_id="u-outro"),
        Workspace(id_hash="ws-lixo-comp", name="Lixo compartilhado", owner_id="u-outro", deleted_at=datetime(2026, 9, 1)),
        Workspace(id_hash="ws-omega", name="Ômega", owner_id="u-outro"),
    ])
    sessao.add_all([
        WorkspaceMember(workspace_id="ws-zeta", user_id="u-dono", role="viewer"),
        WorkspaceMember(workspace_id="ws-alfa", user_id="u-dono", role="editor"),
        WorkspaceMember(workspace_id="ws-lixo-comp", user_id="u-dono", role="operator"),
    ])
    await sessao.commit()


async def test_dono_vence_membro_na_dedup(db):
    lista = await listar_workspaces_do_usuario(db, "u-dono")
    zetas = [w for w in lista if w.id_hash == "ws-zeta"]
    assert len(zetas) == 1
    assert zetas[0].my_role == "owner"          # the "viewer" row in WorkspaceMember does not demote


async def test_lixeira_fica_de_fora_para_dono_e_para_membro(db):
    ids = {w.id_hash for w in await listar_workspaces_do_usuario(db, "u-dono")}
    assert "ws-lixo" not in ids                 # theirs, in the trash
    assert "ws-lixo-comp" not in ids            # is operator, but the workspace was deleted
    assert "ws-omega" not in ids                # neither owner nor member


async def test_ordem_proprios_por_nome_depois_compartilhados_por_nome(db):
    """Not a global ordering: "Alfa" (shared) comes AFTER "Zeta" (own)."""
    nomes = [w.name for w in await listar_workspaces_do_usuario(db, "u-dono")]
    assert nomes == ["Beta", "Zeta", "Alfa"]


async def test_my_role_is_default_e_campos_ecoados(db):
    por_id = {w.id_hash: w for w in await listar_workspaces_do_usuario(db, "u-dono")}
    assert por_id["ws-alfa"].my_role == "editor"
    assert por_id["ws-alfa"].owner_id == "u-outro"
    assert por_id["ws-beta"].is_default is True
    assert por_id["ws-zeta"].is_default is False
    assert por_id["ws-zeta"].description == "o principal"


async def test_usuario_sem_workspaces_recebe_lista_vazia(db):
    assert await listar_workspaces_do_usuario(db, "u-ninguem") == []


async def test_rota_de_listagem_ecoa_o_que_o_service_devolve(client):
    """`GET /workspaces` is a shell: the body is the service's list, untouched.

    The route is really exercised (the real app, through the conftest's `client`) and the
    service is doubled: if the handler starts filtering, reordering or rebuilding the
    list, the body stops matching.
    """
    from app.api.dependencies import get_db
    from app.api.routers import workspace_router
    from app.main import app

    async def _db():
        yield MagicMock()

    devolvido = [
        SimpleNamespace(
            id_hash="ws-alfa", name="Alfa", description="compartilhado",
            owner_id="u-outro", is_default=False, my_role="editor",
        ),
        SimpleNamespace(
            id_hash="ws-beta", name="Beta", description=None,
            owner_id="u-dono", is_default=True, my_role="owner",
        ),
    ]
    duble = AsyncMock(return_value=devolvido)

    app.dependency_overrides[get_db] = _db
    try:
        with patch.object(workspace_router, "listar_workspaces_do_usuario", duble):
            resposta = await client.get("/workspaces")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resposta.status_code == 200
    assert resposta.json() == [
        {"id_hash": "ws-alfa", "name": "Alfa", "description": "compartilhado",
         "owner_id": "u-outro", "is_default": False, "my_role": "editor"},
        {"id_hash": "ws-beta", "name": "Beta", "description": None,
         "owner_id": "u-dono", "is_default": True, "my_role": "owner"},
    ]
    # And the service was called with the injected session and the authenticated user.
    assert duble.await_args.args[1] == "usr-test-001"
