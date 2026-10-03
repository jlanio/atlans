# tests/unit/test_workspace_members_router.py
"""Workspace member list: the owner shows up and cannot be edited.

The owner never had a row in `workspace_members` — `create_workspace` does not create one.
Until now that meant whoever created the workspace did not show up in their own
member list: a workspace with only the owner displayed "Nenhum membro convidado
ainda" (no members invited yet), and an invited admin had no way to find out who to talk to.

The owner's row is now synthetic, built on read. That opens two risks that
these tests close: the owner showing up TWICE (when they also have a real row,
possible in old data) and the UI offering to edit/remove a row that does not
exist in the database — which ended in a generic 404.
"""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.routers.workspace_router import _build_member_list


CREATED_AT = datetime(2026, 1, 15, 10, 30)
JOINED_AT = datetime(2026, 3, 20, 8, 0)


def _user(id_hash, username, email):
    return SimpleNamespace(id_hash=id_hash, username=username, email=email)


def _member(user_id, role, joined_at=JOINED_AT):
    return SimpleNamespace(user_id=user_id, role=role, joined_at=joined_at)


# ── _build_member_list (puro, sem DB) ────────────────────────────────────────

def test_owner_comes_first_with_owner_role():
    dono = _user("u-dono", "dona", "dona@ex.com")
    convidado = _user("u-1", "convidado", "c@ex.com")

    resultado = _build_member_list(
        "u-dono", dono, CREATED_AT, [(_member("u-1", "editor"), convidado)],
    )

    assert [m.user_id for m in resultado] == ["u-dono", "u-1"]
    assert resultado[0].role == "owner"
    # The owner "joined" when they created the workspace — there is no other honest timestamp.
    assert resultado[0].joined_at == CREATED_AT.isoformat()
    assert resultado[1].role == "editor"


def test_owner_with_real_row_does_not_duplicate():
    """Until now nothing prevented inviting the owner themselves by email."""
    dono = _user("u-dono", "dona", "dona@ex.com")

    resultado = _build_member_list(
        "u-dono", dono, CREATED_AT, [(_member("u-dono", "admin"), dono)],
    )

    assert len(resultado) == 1
    # The synthetic row wins: "admin" cannot mask who the owner is.
    assert resultado[0].role == "owner"


def test_without_owner_id_returns_only_the_members():
    """`Workspace.owner_id` is nullable — do not make up an empty row."""
    convidado = _user("u-1", "convidado", "c@ex.com")

    resultado = _build_member_list(
        None, None, CREATED_AT, [(_member("u-1", "viewer"), convidado)],
    )

    assert [m.user_id for m in resultado] == ["u-1"]


def test_owner_removed_from_platform_produces_no_row():
    """owner_id is set but the User is gone: with no username/email, there is nothing to display."""
    resultado = _build_member_list("u-dono", None, CREATED_AT, [])
    assert resultado == []


# ── Write guards on the owner ────────────────────────────────────────────────

@pytest.fixture
def ws_client_db(client, mock_current_user, monkeypatch):
    """client + mocked db, with the authenticated user as the workspace owner.

    `get_workspace_member_role` is replaced by a stub: with a mocked db, its
    `select(Workspace.owner_id)` would return the whole entity instead of the
    id, and role resolution would give a 403 before the guard under test ran. The
    stub applies in both places that call it: the router itself (read) and
    `workflow_access`, from which `require_workspace_role` calls it (write).
    """
    from app.api.dependencies import get_db
    from app.api.routers import workspace_router
    from app.core.authorization import workflow_access
    from app.main import app

    workspace = SimpleNamespace(
        id_hash="ws-1",
        name="Workspace",
        owner_id=mock_current_user.id_hash,
        deleted_at=None,
        created_at=CREATED_AT,
    )

    db = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()

    resultado = MagicMock()
    resultado.scalar_one_or_none.return_value = workspace
    db.execute = AsyncMock(return_value=resultado)

    for modulo in (workspace_router, workflow_access):
        monkeypatch.setattr(
            modulo, "get_workspace_member_role", AsyncMock(return_value="owner"),
        )

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db
    yield client, workspace
    app.dependency_overrides.pop(get_db, None)


async def test_removing_the_owner_is_400_not_404(ws_client_db):
    """Applies both to an admin removing the owner and to the owner trying to leave."""
    client, ws = ws_client_db

    resp = await client.delete(f"/workspaces/ws-1/members/{ws.owner_id}")

    assert resp.status_code == 400
    # `http_exception_handler` remaps `detail` to `message` in the response.
    assert "dono" in resp.json()["message"].lower()


async def test_changing_the_owner_role_is_400(ws_client_db):
    client, ws = ws_client_db

    resp = await client.put(
        f"/workspaces/ws-1/members/{ws.owner_id}", json={"role": "viewer"},
    )

    assert resp.status_code == 400
    # `http_exception_handler` remaps `detail` to `message` in the response.
    assert "dono" in resp.json()["message"].lower()
