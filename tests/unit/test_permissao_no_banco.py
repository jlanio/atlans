# tests/unit/test_permissao_no_banco.py
"""Permissão negada no PostgreSQL vira uma mensagem que diz o que conceder —
"Unexpected error occurred" escondia a causa (foi o que aconteceu com
`audit_events` na primeira semana da política de execução)."""
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
