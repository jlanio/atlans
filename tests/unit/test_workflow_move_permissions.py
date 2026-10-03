# tests/unit/test_workflow_move_permissions.py
"""Authorization of the route that moves a workflow between workspaces.

Moving crosses the tenant boundary: it takes the definition — which carries
`credential_id` in plain text and Drive file ids — into another workspace, and
starts producing data there. That is why it requires admin/owner on BOTH
sides, and not the `editor` that suffices to create and duplicate inside one's
own workspace.

It is the gap that `app/schemas/workflow.py` describes when refusing
`workspace_id` in the PUT: there, authorization would be resolved against the
workspace from BEFORE the change.

Both guards are the real ones, without starting the application: the SOURCE
one is the `workflow_com_papel` dependency declared on the route itself (read
from the router), and the DESTINATION one runs in `_move`, with the role coming
from `get_workspace_member_role`.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routers import workflows_router as WR
from app.schemas.workflow import WorkflowMove, WorkflowUpdate

_SOURCE = "Requer role 'admin' ou 'owner' no workspace de origem para mover workflows."
_TARGET = "Requer role 'admin' ou 'owner' no workspace de destino para mover workflows."

_MOVE_ROUTES = ["/workflows/{id_hash}/move", "/workflows/{id_hash}/move/preview"]


def _source_guard(caminho: str):
    """The role dependency the route declares — the one that runs in production."""
    (rota,) = [r for r in WR.router.routes if r.path == caminho]
    (guarda,) = [d.call for d in rota.dependant.dependencies if hasattr(d.call, "papel_minimo")]
    return guarda


async def _origin(papel, caminho=_MOVE_ROUTES[0]):
    wf = SimpleNamespace(id_hash="wf-1", workspace_id="ws-origem")
    return await _source_guard(caminho)((wf, papel))


async def _mover(role_in_target):
    """`_move` with the destination role decided by the test; returns the service."""
    service = SimpleNamespace(move_workflow=AsyncMock(return_value={
        "id": "wf-1", "name": "Fluxo", "renamed": False, "from_workspace_id": "ws-origem",
        "to_workspace_id": "ws-destino", "dry_run": True, "warnings": [],
    }))
    with patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value=role_in_target),
    ):
        await WR._move(
            WorkflowMove(target_workspace_id="ws-destino"), service,
            SimpleNamespace(id_hash="wf-1"), db=None,
            current_user=SimpleNamespace(id_hash="u-1"), dry_run=True,
        )
    return service


# ── Casos negados ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("caminho", _MOVE_ROUTES)
@pytest.mark.parametrize("origem", ["viewer", "editor", "operator"])
async def test_403_when_the_source_role_is_insufficient(origem, caminho):
    """Move and preview declare the SAME guard: a preview without it would become
    an oracle about the contents of other people's workspaces."""
    with pytest.raises(HTTPException) as exc:
        await _origin(origem, caminho)

    assert exc.value.status_code == 403
    assert exc.value.detail == _SOURCE


@pytest.mark.parametrize("destino", ["viewer", "editor", "operator"])
async def test_403_when_the_target_role_is_insufficient(destino):
    with pytest.raises(HTTPException) as exc:
        await _mover(destino)

    assert exc.value.status_code == 403
    assert exc.value.detail == _TARGET


async def test_403_when_admin_only_in_source():
    await _origin("admin")                      # a origem passa...
    with pytest.raises(HTTPException) as exc:   # ...e o destino barra
        await _mover(None)
    assert exc.value.status_code == 403


async def test_403_when_admin_only_in_target():
    with pytest.raises(HTTPException) as exc:
        await _origin(None)
    assert exc.value.status_code == 403


async def test_non_member_and_nonexistent_workspace_give_the_same_response():
    """`get_workspace_member_role` returns None for a non-member, a nonexistent
    workspace and a workspace in the trash. Distinguishing them would allow
    enumerating other people's workspaces by guessing ids."""
    with pytest.raises(HTTPException) as non_member:
        await _mover(None)

    assert non_member.value.status_code == 403
    assert non_member.value.detail == _TARGET


async def test_insufficient_target_does_not_reach_the_service():
    service = SimpleNamespace(move_workflow=AsyncMock())
    with patch(
        "app.core.authorization.workflow_access.get_workspace_member_role",
        new=AsyncMock(return_value="editor"),
    ), pytest.raises(HTTPException):
        await WR._move(
            WorkflowMove(target_workspace_id="ws-destino"), service,
            SimpleNamespace(id_hash="wf-1"), db=None,
            current_user=SimpleNamespace(id_hash="u-1"), dry_run=False,
        )
    service.move_workflow.assert_not_awaited()


# ── Casos permitidos ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("origem", ["admin", "owner"])
@pytest.mark.parametrize("destino", ["admin", "owner"])
async def test_admin_or_owner_on_both_sides_passes(origem, destino):
    """`owner` ranks above `admin` in WORKSPACE_ROLE_ORDER, so the minimum check
    already covers it — there is no special branch for the owner."""
    await _origin(origem)
    service = await _mover(destino)
    service.move_workflow.assert_awaited_once()


# ── Regression: the PUT still cannot change tenant ───────────────────────────

def test_workspace_id_still_forbidden_on_update():
    """This route exists precisely so that the PUT does not need to accept the
    field. If `extra="forbid"` goes away, the IDOR hole comes back through the
    old door."""
    with pytest.raises(ValidationError):
        WorkflowUpdate(name="x", workspace_id="ws-alheio")
