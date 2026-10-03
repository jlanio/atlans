# tests/unit/test_agente_fluxos_proprios.py
"""
`list_workflows` and the workflows the assistant ITSELF created.

The listing hides `origem = "assistente"` by default — the assistant's workflows
are a Home delivery vehicle, not items the owner manages. The side effect was
cruel and silent: whoever calls the tool ON THE HOME is the assistant itself, and
the `False` default blinded it to what it had itself created. In a new chat, "run
that deforestation one again" found nothing, and a duplicate workflow was born on
every recurring question.

The cut is by SCOPE (`origem_dos_fluxos == "assistente"`), not by a parameter the
model has to remember to pass: a regular PAT keeps the `False` default, and each
item's `origem` field says what belongs to whom.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp import infra
from app.mcp.tools.workflows import list_workflows
from app.models.base import Base
from app.models.workflow import Workflow
from tests.unit._mcp_harness import TABLES, create_user, create_workspace, fake_ctx, fake_scope

pytestmark = pytest.mark.asyncio

WS = "11111111-1111-4111-8111-111111111111"
DELA = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
HIS = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
async def banco(monkeypatch):
    """A workspace with TWO workflows: one from the person, one from the assistant."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _session():
        async with fabrica() as db:
            try:
                yield db
            finally:
                await db.rollback()

    monkeypatch.setattr(infra, "sessao", _session)

    async with fabrica() as db:
        await create_user(db, "usr-1", "ana")
        await create_workspace(db, WS, "usr-1", "Principal")
        db.add(Workflow(
            id_hash=DELA, name="Recorte mensal", workspace_id=WS,
            definition={"nodes": [], "edges": []}, flag_ative=True, origem="usuario",
        ))
        db.add(Workflow(
            id_hash=HIS, name="assistente: desmatamento 2024", workspace_id=WS,
            definition={"nodes": [], "edges": []}, flag_ative=True, origem="assistente",
        ))
        await db.commit()

    yield fabrica
    await engine.dispose()


def _ctx(**kw):
    campos = {"scopes": {"workflows:read"}, "workspace_ids": {WS}}
    campos.update(kw)
    return fake_ctx(fake_scope(**campos))


async def test_the_assistant_sees_its_own_workflows(banco):
    saida = await list_workflows(_ctx(origem_dos_fluxos="assistente"))

    ids = {i["id"] for i in saida["items"]}
    assert ids == {DELA, HIS}
    origens = {i["id"]: i["origem"] for i in saida["items"]}
    assert origens[HIS] == "assistente"
    assert origens[DELA] == "usuario"


async def test_regular_pat_still_does_not_see_the_assistants(banco):
    saida = await list_workflows(_ctx())

    assert {i["id"] for i in saida["items"]} == {DELA}
    assert saida["total"] == 1


async def test_pat_can_request_the_assistants_explicitly(banco):
    """The equivalent of the REST `?assistente=1`, for whoever wants the whole collection."""
    saida = await list_workflows(_ctx(), include_from_assistant=True)

    assert {i["id"] for i in saida["items"]} == {DELA, HIS}


async def test_the_assistant_can_opt_out_of_seeing_its_own(banco):
    """O parametro explicito vence o default derivado do escopo."""
    saida = await list_workflows(
        _ctx(origem_dos_fluxos="assistente"), include_from_assistant=False
    )

    assert {i["id"] for i in saida["items"]} == {DELA}
