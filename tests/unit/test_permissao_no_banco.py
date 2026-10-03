# tests/unit/test_permissao_no_banco.py
"""Permission denied in PostgreSQL becomes a message that says what to grant —
"Unexpected error occurred" hid the cause (that is what happened with
`audit_events` in the first week of the execution policy)."""
import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import ProgrammingError

from app.core.utils.error_handlers import generic_exception_handler


@pytest.mark.asyncio
async def test_permission_denied_vira_mensagem_acionavel():
    orig = Exception("<class 'asyncpg.exceptions.InsufficientPrivilegeError'>: permission denied for table audit_events")
    exc = ProgrammingError("INSERT INTO audit_events ...", {}, orig)
    resp = await generic_exception_handler(MagicMock(), exc)
    corpo = json.loads(resp.body)
    assert resp.status_code == 500
    assert corpo["error"] == "database_permission_denied"
    assert "permission denied for table audit_events" in corpo["message"]


@pytest.mark.asyncio
async def test_must_be_owner_tambem_e_reconhecido():
    orig = Exception("must be owner of table workspaces")
    exc = ProgrammingError("ALTER TABLE workspaces ...", {}, orig)
    corpo = json.loads((await generic_exception_handler(MagicMock(), exc)).body)
    assert corpo["error"] == "database_permission_denied"
    assert "must be owner of table workspaces" in corpo["message"]


@pytest.mark.asyncio
async def test_outros_erros_continuam_genericos():
    corpo = json.loads((await generic_exception_handler(MagicMock(), RuntimeError("x"))).body)
    assert corpo["error"] == "internal_server_error"
