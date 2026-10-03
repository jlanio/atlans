# tests/unit/test_policy_error_body.py
"""The policy's 409 carries the list of workspaces that would be left empty: that
is what lets the screen offer "remover mesmo assim" (remove anyway) knowing what
will happen."""
import json
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import WorkspacePolicyConflictError, WorkspacePolicyError
from app.core.utils.error_handlers import atlas_domain_error_handler


@pytest.mark.asyncio
async def test_policy_409_lists_the_workspaces():
    exc = WorkspacePolicyConflictError(
        "Remover este executor esvaziaria o nível principal de: Bacia.",
        workspaces=[{"workspace_id": "ws-1", "workspace_name": "Bacia", "would_empty_primary": True}],
    )
    resp = await atlas_domain_error_handler(MagicMock(), exc)
    corpo = json.loads(resp.body)
    assert resp.status_code == 409
    assert corpo["error"] == "workspace_policy_conflict"
    assert corpo["workspaces"][0]["workspace_name"] == "Bacia"


@pytest.mark.asyncio
async def test_errors_without_list_do_not_get_the_field():
    resp = await atlas_domain_error_handler(MagicMock(), WorkspacePolicyError("x"))
    corpo = json.loads(resp.body)
    assert "workspaces" not in corpo
