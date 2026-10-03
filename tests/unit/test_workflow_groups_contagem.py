# tests/unit/test_workflow_groups_contagem.py
"""
Workflow group counts.

`workflow_count` counted only the ACTIVE ones: a group of three workflows with
one deactivated said "2 workflows" — and the inactive one was still there in the
list. It now counts all the non-deleted ones, and `active_count` (new) says how
many are active: "3 workflows · 2 ativos" (2 active).

The three places that return a group (create, list, update) go through the
same aggregation. The tests call the route functions directly, with an
in-memory SQLite session — same mold as test_grupos_ordem.py.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.requests import Request

from app.api.routers import workflow_groups_router as rota
from app.models.models import Workflow, WorkflowGroup
from app.schemas.workflow_group import WorkflowGroupCreate, WorkflowGroupRead, WorkflowGroupUpdate

WS = "ws-1"


class _FakeUser:
    id_hash = "user-1"


def _request() -> Request:
    """`create_group` has a rate limit, and slowapi refuses anything that is not
    a real Request."""
    return Request({
        "type": "http", "method": "POST", "path": "/workflow-groups",
        "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
    })


def _editor():
    # Where `require_workspace_role` looks up the role (the comparison stays real).
    return patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value="editor"),
    )


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            WorkflowGroup.metadata.create_all,
            tables=[WorkflowGroup.__table__, Workflow.__table__],
        )
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


def _workflow(id_hash, *, group_id=None, ativo=True, deleted=False, workspace=WS):
    return Workflow(
        id_hash=id_hash, name=id_hash, definition={"nodes": [], "edges": []},
        flag_ative=ativo, workspace_id=workspace, group_id=group_id,
        deleted_at=datetime(2026, 1, 1) if deleted else None,
    )


GROUP = "grp-1"


async def _group_with_mix(db) -> str:
    """A group with two active, one inactive and one in the trash — the scenario
    that exercises both counts at once: (3 workflows, 2 active).

    Returns the id_hash, not the entity: after the commit the session expires
    the object, and reading an attribute outside an `await` triggers a
    synchronous refresh that the async driver refuses.
    """
    db.add_all([
        WorkflowGroup(id_hash=GROUP, name="Hidrologia", position=0, workspace_id=WS),
        _workflow("a", group_id=GROUP, ativo=True),
        _workflow("b", group_id=GROUP, ativo=True),
        _workflow("c", group_id=GROUP, ativo=False),
        _workflow("lixo", group_id=GROUP, ativo=False, deleted=True),
        # Outside the group: must not be counted.
        _workflow("solto", ativo=True),
    ])
    await db.commit()
    return GROUP


def _count(item: WorkflowGroupRead) -> tuple[int, int]:
    return item.workflow_count, item.active_count


# ── schema ──────────────────────────────────────────────────────────────────

def test_active_count_defaults_to_zero():
    """Grupo vazio e a listagem antiga (sem o campo) continuam valid_items."""
    assert WorkflowGroupRead.model_fields["active_count"].default == 0


# ── listagem ────────────────────────────────────────────────────────────────

class TestList:

    @pytest.mark.asyncio
    async def test_counts_inactive_and_ignores_deleted(self, db):
        await _group_with_mix(db)

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _count(item) == (3, 2)

    @pytest.mark.asyncio
    async def test_empty_group_is_zero_zero(self, db):
        db.add(WorkflowGroup(id_hash="grp-vazio", name="Rascunhos", position=0, workspace_id=WS))
        await db.commit()

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _count(item) == (0, 0)

    @pytest.mark.asyncio
    async def test_all_inactive(self, db):
        """"2 workflows · 0 ativos" (0 active) — before, it said "0 workflows", as if
        the group were empty."""
        db.add_all([
            WorkflowGroup(id_hash="grp-1", name="Parados", position=0, workspace_id=WS),
            _workflow("a", group_id="grp-1", ativo=False),
            _workflow("b", group_id="grp-1", ativo=False),
        ])
        await db.commit()

        [item] = await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])
        assert _count(item) == (2, 0)

    @pytest.mark.asyncio
    async def test_several_groups_in_a_single_query(self, db):
        db.add_all([
            WorkflowGroup(id_hash="grp-1", name="A", position=0, workspace_id=WS),
            WorkflowGroup(id_hash="grp-2", name="B", position=1, workspace_id=WS),
            WorkflowGroup(id_hash="grp-3", name="C", position=2, workspace_id=WS),
            _workflow("a1", group_id="grp-1", ativo=True),
            _workflow("a2", group_id="grp-1", ativo=False),
            _workflow("b1", group_id="grp-2", ativo=True),
        ])
        await db.commit()

        itens = {g.name: _count(g) for g in await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS])}
        assert itens == {"A": (2, 1), "B": (1, 1), "C": (0, 0)}

    @pytest.mark.asyncio
    async def test_no_groups_at_all_does_not_break(self, db):
        assert await rota.list_groups(workspace_id=WS, db=db, workspace_ids=[WS]) == []


# ── criar ───────────────────────────────────────────────────────────────────

class TestCreate:

    @pytest.mark.asyncio
    async def test_counts_the_inactive_one_that_just_joined(self, db):
        """Creating the group with an inactive one already inside returned "1 workflow"
        for two linked ones — the freshly created screen was born wrong."""
        db.add_all([_workflow("ativo", ativo=True), _workflow("inativo", ativo=False)])
        await db.commit()

        with _editor():
            novo = await rota.create_group(
                request=_request(),
                payload=WorkflowGroupCreate(name="Novo", workspace_id=WS, workflow_ids=["ativo", "inativo"]),
                db=db, current_user=_FakeUser(),
            )

        assert _count(novo) == (2, 1)

    @pytest.mark.asyncio
    async def test_no_workflows_is_zero_zero(self, db):
        with _editor():
            novo = await rota.create_group(
                request=_request(),
                payload=WorkflowGroupCreate(name="Vazio", workspace_id=WS),
                db=db, current_user=_FakeUser(),
            )
        assert _count(novo) == (0, 0)


# ── atualizar ───────────────────────────────────────────────────────────────

class TestUpdate:

    @pytest.mark.asyncio
    async def test_recount_after_swapping_the_members(self, db):
        grupo = await _group_with_mix(db)

        with _editor():
            item = await rota.update_group(
                group_id=grupo,
                payload=WorkflowGroupUpdate(workflow_ids=["c", "solto"]),
                db=db, current_user=_FakeUser(),
            )

        # "c" e inativo, "solto" e ativo: os dois contam, um ativo.
        assert _count(item) == (2, 1)

    @pytest.mark.asyncio
    async def test_renaming_without_touching_the_members_keeps_the_count(self, db):
        grupo = await _group_with_mix(db)

        with _editor():
            item = await rota.update_group(
                group_id=grupo,
                payload=WorkflowGroupUpdate(name="Outro nome"),
                db=db, current_user=_FakeUser(),
            )

        assert item.name == "Outro nome"
        assert _count(item) == (3, 2)


# ── invariante ──────────────────────────────────────────────────────────────

def test_the_three_call_sites_go_through_the_same_aggregation():
    """If one of the routes goes back to counting on its own, the divergence
    reappears only on that screen. The helper is the only place that knows how
    to count."""
    import inspect

    for nome in ("create_group", "list_groups", "update_group"):
        fonte = inspect.getsource(getattr(rota, nome))
        assert "_contagens_por_grupo" in fonte or "_ler_grupo" in fonte, nome
        assert "func.count()" not in fonte, f"{nome} conta por fora do helper"
