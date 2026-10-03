"""Workspace with no owner (null `owner_id`: old or hand-edited data) with members.

`get_workspace_member_role` returns early with no owner, and the `/workflows/{id}`
routes all went through it with the single guard (`workflow_com_papel`). The three read
routes ("belonging is enough": the workflow, the contract and the versions) previously used
the membership from `listar_workspace_ids`, owner OR member, and a member of a
workspace with no owner could read them. They still can; and every route with a minimum role
refuses them with the same 403 as before.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from tests.unit._mcp_harness import TABELAS

LEITURAS = ("/workflows/wf-n", "/workflows/wf-n/contract", "/workflows/wf-n/versions")


@pytest.fixture
async def api_sem_dono(client, monkeypatch):
    from app.api.dependencies import get_current_user, get_db, get_user_workspace_ids
    from app.core.rate_limiter import limiter
    from app.main import app
    from app.models.base import Base
    from app.models.user import User
    from app.models.workflow import Workflow
    from app.models.workflow_group import WorkflowGroup
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[*TABELAS, WorkflowGroup.__table__])
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        db.add_all([
            User(id_hash=u, username=u, email=f"{u}@t", hashed_password="x")
            for u in ("u-viewer", "u-admin", "u-fora")
        ])
        db.add(Workspace(id_hash="ws-n", name="Sem dono", owner_id=None))
        db.add(WorkspaceMember(workspace_id="ws-n", user_id="u-viewer", role="viewer"))
        db.add(WorkspaceMember(workspace_id="ws-n", user_id="u-admin", role="admin"))
        db.add(Workflow(
            id_hash="wf-n", name="F", workspace_id="ws-n",
            definition={"nodes": [], "edges": []}, flag_ative=True,
        ))
        await db.commit()

    async def _db():
        async with fabrica() as sessao:
            yield sessao

    async def _quem(request: Request):
        uid = request.headers["x-usuario"]
        return SimpleNamespace(id_hash=uid, username=uid, email=f"{uid}@t", role="user", is_active=True)

    anteriores = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _quem
    # The real membership (`listar_workspace_ids`), not the conftest's fixed list.
    app.dependency_overrides.pop(get_user_workspace_ids, None)
    monkeypatch.setattr(limiter, "enabled", False)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)
        await engine.dispose()


@pytest.mark.parametrize("usuario", ["u-viewer", "u-admin"])
async def test_membro_de_workspace_sem_dono_le_o_workflow(api_sem_dono, usuario):
    lista = await api_sem_dono.get("/workflows?workspace_id=ws-n", headers={"x-usuario": usuario})
    assert lista.status_code == 200
    for url in LEITURAS:
        resposta = await api_sem_dono.get(url, headers={"x-usuario": usuario})
        assert resposta.status_code == 200, (url, resposta.text)


async def test_membro_de_workspace_sem_dono_nao_age_nem_como_admin(api_sem_dono):
    """With no role, no route with a minimum passes, with the 403 for someone not in the
    workspace: the same response as before the single guard."""
    cabecalho = {"x-usuario": "u-admin"}
    pins = await api_sem_dono.get("/workflows/wf-n/pins", headers=cabecalho)
    renomear = await api_sem_dono.put("/workflows/wf-n", json={"name": "G"}, headers=cabecalho)
    for resposta in (pins, renomear):
        assert resposta.status_code == 403
        assert resposta.json()["message"] == "Acesso negado a este recurso."


async def test_quem_nao_e_membro_segue_sem_ler(api_sem_dono):
    for url in LEITURAS:
        resposta = await api_sem_dono.get(url, headers={"x-usuario": "u-fora"})
        assert resposta.status_code == 403, url
        assert resposta.json()["message"] == "Acesso negado a este recurso."
