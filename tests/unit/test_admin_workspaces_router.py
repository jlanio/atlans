# tests/unit/test_admin_workspaces_router.py
"""Authorization of the workspace trash (/admin/workspaces/*).

The trash lists, restores and discards workspaces of ANY user on the
platform. The guarantee comes from the router
(`dependencies=[Depends(require_admin)]`), not from code in the handlers — and
that is why it is fragile: someone only has to move an endpoint to another
router, or create a new router without the dependency, to open everything up.
These tests fail the moment that happens.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Denied for a regular user ────────────────────────────────────────────────

async def test_trash_denied_for_regular_user(client):
    """client authenticates with role='user' (see conftest)."""
    resp = await client.get("/admin/workspaces/trash")
    assert resp.status_code == 403


async def test_restore_denied_for_regular_user(client):
    resp = await client.post("/admin/workspaces/ws-test-001/restore")
    assert resp.status_code == 403


async def test_purge_denied_for_regular_user(client):
    resp = await client.post(
        "/admin/workspaces/ws-test-001/purge",
        json={"confirm": "ws-test-001"},
    )
    assert resp.status_code == 403


# ── Purge guards (with an authenticated admin) ───────────────────────────────

@pytest.fixture
def admin_client_db(client, mock_current_user):
    """Promove o usuario do client a admin e devolve um db mockado injetavel."""
    from app.api.dependencies import get_db
    from app.main import app

    mock_current_user.role = "admin"
    mock_current_user.username = "admin-test"

    db = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()

    async def _fake_db():
        yield db

    app.dependency_overrides[get_db] = _fake_db
    yield client, db
    app.dependency_overrides.pop(get_db, None)


async def test_purge_requires_confirm_equal_to_id(admin_client_db):
    """Guard against a click on the wrong row of the table — checked on the server."""
    ac, _ = admin_client_db
    resp = await ac.post(
        "/admin/workspaces/ws-test-001/purge",
        json={"confirm": "ws-outro-999"},
    )
    assert resp.status_code == 400


async def test_purge_404_for_workspace_not_in_trash(admin_client_db):
    """Only a workspace with deleted_at set can be purged."""
    ac, db = admin_client_db
    result = MagicMock()
    result.scalar_one_or_none.return_value = None   # nada casa deleted_at IS NOT NULL
    db.execute = AsyncMock(return_value=result)

    resp = await ac.post(
        "/admin/workspaces/ws-test-001/purge",
        json={"confirm": "ws-test-001"},
    )
    assert resp.status_code == 404
    db.delete.assert_not_awaited()


async def test_restore_404_for_workspace_not_in_trash(admin_client_db):
    ac, db = admin_client_db
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    resp = await ac.post("/admin/workspaces/ws-test-001/restore")
    assert resp.status_code == 404
    db.commit.assert_not_awaited()
