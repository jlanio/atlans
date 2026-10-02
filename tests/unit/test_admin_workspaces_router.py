# tests/unit/test_admin_workspaces_router.py
"""Autorizacao da lixeira de workspaces (/admin/workspaces/*).

A lixeira lista, restaura e descarta workspaces de QUALQUER usuario da
plataforma. A garantia vem do router (`dependencies=[Depends(require_admin)]`),
nao de codigo nos handlers — e por isso e fragil: basta alguem mover um endpoint
para outro router, ou criar um router novo sem a dependency, para abrir tudo.
Estes testes falham no instante em que isso acontecer.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Negado para usuario comum ────────────────────────────────────────────────

async def test_trash_negado_para_usuario_comum(client):
    """client autentica com role='user' (ver conftest)."""
    resp = await client.get("/admin/workspaces/trash")
    assert resp.status_code == 403


async def test_restore_negado_para_usuario_comum(client):
    resp = await client.post("/admin/workspaces/ws-test-001/restore")
    assert resp.status_code == 403


async def test_purge_negado_para_usuario_comum(client):
    resp = await client.post(
        "/admin/workspaces/ws-test-001/purge",
        json={"confirm": "ws-test-001"},
    )
    assert resp.status_code == 403


# ── Guardas do purge (com admin autenticado) ─────────────────────────────────

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


async def test_purge_exige_confirm_igual_ao_id(admin_client_db):
    """Guarda contra clique na linha errada da tabela — checada no servidor."""
    ac, _ = admin_client_db
    resp = await ac.post(
        "/admin/workspaces/ws-test-001/purge",
        json={"confirm": "ws-outro-999"},
    )
    assert resp.status_code == 400


async def test_purge_404_para_workspace_fora_da_lixeira(admin_client_db):
    """Só workspace com deleted_at preenchido pode ser purgado."""
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


async def test_restore_404_para_workspace_fora_da_lixeira(admin_client_db):
    ac, db = admin_client_db
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    resp = await ac.post("/admin/workspaces/ws-test-001/restore")
    assert resp.status_code == 404
    db.commit.assert_not_awaited()
