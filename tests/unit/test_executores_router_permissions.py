# tests/unit/test_agents_router_permissions.py
"""Tests for the owner-or-admin check on executor lifecycle actions."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routers.executores_router import _assert_executor_owner_or_admin, _assert_pode_gerenciar_executor


def _user(role: str, uid: str):
    u = MagicMock()
    u.role = role
    u.id_hash = uid
    return u


def _agent(created_by: str | None, is_default: bool = False):
    ag = MagicMock()
    ag.created_by = created_by
    ag.id_hash = str(uuid4())
    ag.is_default = is_default
    return ag


def test_admin_sempre_autorizado():
    _assert_executor_owner_or_admin(_user("admin", "admin-1"), _agent(created_by="alguem"))


def test_dono_autorizado():
    _assert_executor_owner_or_admin(_user("user", "user-1"), _agent(created_by="user-1"))


def test_terceiro_recebe_403():
    with pytest.raises(HTTPException) as exc:
        _assert_executor_owner_or_admin(_user("user", "user-1"), _agent(created_by="user-2"))
    assert exc.value.status_code == 403


def test_dono_nao_gerencia_executor_do_pool():
    """Audit SEG-94: promoted to the pool (is_default), only an admin manages it."""
    with pytest.raises(HTTPException) as ei:
        _assert_pode_gerenciar_executor(_user("user", "user-1"), _agent(created_by="user-1", is_default=True))
    assert ei.value.status_code == 403


def test_admin_gerencia_executor_do_pool():
    _assert_pode_gerenciar_executor(_user("admin", "adm"), _agent(created_by="outro", is_default=True))
