# tests/unit/test_policy_error_body.py
"""O 409 da política carrega a lista de workspaces que esvaziariam: é o que
permite à tela oferecer "remover mesmo assim" sabendo o que vai acontecer."""
import json
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import WorkspacePolicyConflictError, WorkspacePolicyError
from app.core.utils.error_handlers import atlas_domain_error_handler


@pytest.mark.asyncio
async def test_409_da_politica_lista_os_workspaces():
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
async def test_erros_sem_lista_nao_ganham_o_campo():
    resp = await atlas_domain_error_handler(MagicMock(), WorkspacePolicyError("x"))
    corpo = json.loads(resp.body)
    assert "workspaces" not in corpo
