# tests/integration/test_grupos_ordem.py
"""
Order of workflow groups.

`GET /workflow-groups/` had no `order_by` at all: the order came undefined
from the database and could change between two loads of the same page. There
was not even a stable order, let alone one chosen by the user.

The tests call the route functions directly, with an in-memory SQLite
session — what matters here is the query and the write, not the HTTP layer.
"""
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.requests import Request

from app.api.routers import workflow_groups_router as rota
from app.models.models import Workflow, WorkflowGroup
from app.schemas.workflow_group import WorkflowGroupCreate, WorkflowGroupReorder

WS = "ws-1"


class _FakeUser:
    id_hash = "user-1"


def _request() -> Request:
    """Minimal Request: `create_group` has a rate limit, and slowapi rejects
    anything that is not a real Request."""
    return Request({
        "type": "http", "method": "POST", "path": "/workflow-groups",
        "headers": [], "client": ("127.0.0.1", 0), "query_string": b"",
    })


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


async def _groups(db, *names_and_positions, workspace=WS):
    for nome, pos in names_and_positions:
        db.add(WorkflowGroup(name=nome, position=pos, workspace_id=workspace))
    await db.commit()
    resultado = {}
    for g in (await rota.list_groups(workspace_id=None, db=db, workspace_ids=[workspace])):
        resultado[g.name] = g
    return resultado


async def _names_in_order(db, workspace_ids=(WS,)):
    saida = await rota.list_groups(
        workspace_id=None, db=db, workspace_ids=list(workspace_ids)
    )
    return [g.name for g in saida]


# Where `require_workspace_role` looks up the role: swapping it here keeps
# the real comparison running, just without the members table.
_ROLE = "app.core.authorization.workflow_access.get_workspace_member_role"


def _editor():
    """Editor role in the workspace, without needing the members table."""
    return patch(_ROLE, new=AsyncMock(return_value="editor"))


# ── listagem ────────────────────────────────────────────────────────────────

class TestListingOrder:

    @pytest.mark.asyncio
    async def test_sorts_by_position_not_by_name(self, db):
        await _groups(db, ("Zebra", 0), ("Abacate", 1))
        assert await _names_in_order(db) == ["Zebra", "Abacate"]

    @pytest.mark.asyncio
    async def test_name_breaks_ties_between_equal_positions(self, db):
        # Groups created before the column existed, or an interrupted
        # reordering: without the tiebreaker the order becomes undefined again.
        await _groups(db, ("Beta", 0), ("Alfa", 0), ("Gama", 0))
        assert await _names_in_order(db) == ["Alfa", "Beta", "Gama"]


# ── reordenacao ─────────────────────────────────────────────────────────────

class TestReorder:

    @pytest.mark.asyncio
    async def test_saves_the_received_order(self, db):
        criados = await _groups(db, ("A", 0), ("B", 1), ("C", 2))
        nova = [criados["C"].id_hash, criados["A"].id_hash, criados["B"].id_hash]

        with _editor():
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=nova),
                db=db, current_user=_FakeUser(),
            )

        assert await _names_in_order(db) == ["C", "A", "B"]

    @pytest.mark.asyncio
    async def test_unknown_id_is_rejected(self, db):
        """Silently ignoring it would leave the database and the screen with
        different lists — and the next reordering would write over the
        divergence."""
        criados = await _groups(db, ("A", 0))

        with _editor(), pytest.raises(HTTPException) as exc:
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=[criados["A"].id_hash, "nao-existe"]),
                db=db, current_user=_FakeUser(),
            )
        assert exc.value.status_code == 404
        assert "nao-existe" in exc.value.detail

    @pytest.mark.asyncio
    async def test_refuses_to_mix_workspaces(self, db):
        aqui = await _groups(db, ("A", 0))
        outro = await _groups(db, ("X", 0), workspace="ws-2")

        with _editor(), pytest.raises(HTTPException) as exc:
            await rota.reorder_groups(
                payload=WorkflowGroupReorder(group_ids=[aqui["A"].id_hash, outro["X"].id_hash]),
                db=db, current_user=_FakeUser(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_requires_editor_role(self, db):
        criados = await _groups(db, ("A", 0))

        with patch(_ROLE, new=AsyncMock(return_value="viewer")):
            with pytest.raises(HTTPException) as exc:
                await rota.reorder_groups(
                    payload=WorkflowGroupReorder(group_ids=[criados["A"].id_hash]),
                    db=db, current_user=_FakeUser(),
                )
        assert exc.value.status_code == 403


# ── route registration ──────────────────────────────────────────────────────

def test_reorder_is_registered_before_the_variable_path():
    """`PUT /reorder` must come BEFORE `PUT /{group_id}`.

    FastAPI matches routes in registration order: with the variable path
    first, "reorder" would arrive as if it were a group id, and the response
    would be a nonexistent-group 404 — an error that in no way hints at the
    real cause.
    """
    caminhos = [r.path for r in rota.router.routes if "PUT" in (r.methods or set())]
    assert caminhos.index("/workflow-groups/reorder") < caminhos.index(
        "/workflow-groups/{group_id}"
    )


# ── criacao ─────────────────────────────────────────────────────────────────

class TestNewGroupGoesToTheEnd:

    @pytest.mark.asyncio
    async def test_is_not_created_tied_at_zero(self, db):
        """With a fixed `position=0`, every new group ties with the existing ones and
        the order among them goes back to depending on the name tiebreaker."""
        await _groups(db, ("A", 0), ("B", 1))

        with _editor():
            novo = await rota.create_group(
                request=_request(),
                payload=WorkflowGroupCreate(name="Aaa", workspace_id=WS),
                db=db, current_user=_FakeUser(),
            )

        assert novo.position == 2
        # The name would come first alphabetically; the position is what decides.
        assert await _names_in_order(db) == ["A", "B", "Aaa"]

    @pytest.mark.asyncio
    async def test_first_group_of_the_workspace(self, db):
        with _editor():
            novo = await rota.create_group(
                request=_request(),
                payload=WorkflowGroupCreate(name="Primeiro", workspace_id=WS),
                db=db, current_user=_FakeUser(),
            )
        assert novo.position == 1
