# tests/unit/test_workspace_service.py
"""
`listar_workspaces_do_usuario` — a listagem que saiu de `workspace_router.py`.

O router só chama; quem garante o contrato agora é esta função, e o servidor
MCP vai depender dela sem passar pela rota. Cada teste fixa uma decisão que a
listagem já tomava e que uma reescrita "equivalente" poderia trocar:

- dono que também consta como membro aparece UMA vez, como "owner" (o papel
  de membro não rebaixa o dono);
- workspace na lixeira (`deleted_at`) fica de fora — seja do dono, seja do
  membro;
- a ordem é a de sempre: primeiro os próprios (por nome), depois os
  compartilhados (por nome) — não uma ordenação global;
- `is_default` é ecoado e `my_role` é o papel do membro nos compartilhados.

Banco de verdade (SQLite em memória): a função é consulta, e um mock de
`db.execute` só provaria que o mock devolve o que se mandou.
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
    """Dois usuários, seis workspaces.

    u-dono  é dono de "Zeta" (e TAMBÉM membro "viewer" nele), de "Beta"
            (is_default) e de "Lixo" (na lixeira); é editor em "Alfa" e
            operator em "Lixo compartilhado" (na lixeira, de u-outro).
    u-outro é dono de "Alfa", "Lixo compartilhado" e "Ômega" (onde u-dono
            não está).
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
    assert zetas[0].my_role == "owner"          # a linha "viewer" em WorkspaceMember não rebaixa


async def test_lixeira_fica_de_fora_para_dono_e_para_membro(db):
    ids = {w.id_hash for w in await listar_workspaces_do_usuario(db, "u-dono")}
    assert "ws-lixo" not in ids                 # dele, na lixeira
    assert "ws-lixo-comp" not in ids            # é operator, mas o workspace foi apagado
    assert "ws-omega" not in ids                # nem dono nem membro


async def test_ordem_proprios_por_nome_depois_compartilhados_por_nome(db):
    """Não é uma ordenação global: "Alfa" (compartilhado) vem DEPOIS de "Zeta" (próprio)."""
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
    """`GET /workspaces` é uma casca: o corpo é a lista do service, sem retoques.

    A rota é exercida de verdade (a app real, pelo `client` do conftest) e o
    service é dublado: se o handler passar a filtrar, reordenar ou remontar a
    lista, o corpo deixa de bater.
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
    # E o service foi chamado com a sessão injetada e o usuário autenticado.
    assert duble.await_args.args[1] == "usr-test-001"
