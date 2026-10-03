"""
Admin user bulk operations without N+1.

Regression: bulk_suspend/reactivate/delete did a get_user (SELECT) + a
commit + a refresh PER user — 3N round-trips. Now: one get_users_by_ids
(1 SELECT with IN) + one commit per batch.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import admin_user_service as svc

import pytest as _pytest_seg16
from unittest.mock import AsyncMock as _AsyncMock_seg16


@_pytest_seg16.fixture(autouse=True)
def _patch_revoga_executores(monkeypatch):
    """SEG-16: isolates these tests (token/commit) from executor revocation,
    which makes its own database queries."""
    monkeypatch.setattr(
        "app.services.executor_service.revogar_executores_do_usuario",
        _AsyncMock_seg16(return_value=[]),
    )



def _user(id_hash, status="active"):
    return MagicMock(id_hash=id_hash, status=status, username=id_hash,
                     suspended_at=None, deleted_at=None)


# ── get_users_by_ids: uma query, dict indexado ───────────────────────────────

@pytest.mark.asyncio
async def test_get_users_by_ids_uma_query():
    db = MagicMock()
    res = MagicMock()
    res.scalars.return_value.all.return_value = [_user("a"), _user("b")]
    db.execute = AsyncMock(return_value=res)

    out = await svc.get_users_by_ids(db, ["a", "b", "c"])

    assert set(out) == {"a", "b"}
    db.execute.assert_awaited_once()  # NOT one per id
    sql = str(db.execute.await_args[0][0]).lower()
    assert "in (" in sql or "in(" in sql, "deve usar IN, nao N selects"


@pytest.mark.asyncio
async def test_get_users_by_ids_lista_vazia_nao_consulta():
    db = MagicMock()
    db.execute = AsyncMock()
    assert await svc.get_users_by_ids(db, []) == {}
    db.execute.assert_not_awaited()


# ── bulk mutators: um commit por lote ────────────────────────────────────────

@pytest.mark.asyncio
async def test_bulk_suspend_um_commit_para_muitos():
    db = MagicMock()
    db.commit = AsyncMock()
    # The access token revocation cascade runs an UPDATE in the same
    # session (without its own commit) — that is why `execute` must be awaitable.
    db.execute = AsyncMock()
    users = [_user("a"), _user("b"), _user("c")]

    await svc.bulk_suspend(db, users)

    assert all(u.status == "suspended" for u in users)
    assert all(u.suspended_at is not None for u in users)
    db.commit.assert_awaited_once()  # ONE commit, not three


@pytest.mark.asyncio
async def test_bulk_reactivate_limpa_suspended_at():
    db = MagicMock()
    db.commit = AsyncMock()
    users = [_user("a", status="suspended")]
    users[0].suspended_at = "2026-01-01"

    await svc.bulk_reactivate(db, users)

    assert users[0].status == "active"
    assert users[0].suspended_at is None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_soft_delete_marca_deleted():
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()  # token revocation cascade (without its own commit)
    users = [_user("a"), _user("b")]

    await svc.bulk_soft_delete(db, users)

    assert all(u.status == "deleted" for u in users)
    assert all(u.deleted_at is not None for u in users)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_lista_vazia_nao_commita():
    db = MagicMock()
    db.commit = AsyncMock()

    await svc.bulk_suspend(db, [])

    db.commit.assert_not_awaited()


# ── Endpoint: uma unica carga, ineligiveis viram erro ────────────────────────

@pytest.mark.asyncio
async def test_bulk_suspend_endpoint_carrega_uma_vez(client, mock_current_user):
    from app.main import app
    from app.api.dependencies import get_db, require_admin

    mock_current_user.role = "admin"
    mock_current_user.id_hash = "admin-1"

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[require_admin] = lambda: mock_current_user

    # Um ativo (suspende), um ja suspenso (erro), um inexistente (erro).
    users = {"u-ativo": _user("u-ativo", "active"),
             "u-susp": _user("u-susp", "suspended")}
    calls = {"get_by_ids": 0, "suspend": 0}

    async def _get_by_ids(db, ids):
        calls["get_by_ids"] += 1
        return {k: v for k, v in users.items() if k in ids}

    async def _bulk_suspend(db, elig, **kwargs):
        calls["suspend"] += 1
        assert [u.id_hash for u in elig] == ["u-ativo"]
        # `motivo`/`por`: the route passes the UI's reason along instead of discarding it.
        assert "motivo" in kwargs and "por" in kwargs

    import app.api.routers.admin_users_router as mod
    orig_g, orig_s = mod.svc.get_users_by_ids, mod.svc.bulk_suspend
    mod.svc.get_users_by_ids = _get_by_ids
    mod.svc.bulk_suspend = _bulk_suspend
    try:
        resp = await client.post("/admin/users/bulk/suspend",
                                 json={"user_ids": ["u-ativo", "u-susp", "u-inexistente"]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["processed"] == 1
        assert len(body["errors"]) == 2
        assert calls["get_by_ids"] == 1, "deve carregar todos numa unica chamada"
        assert calls["suspend"] == 1
    finally:
        mod.svc.get_users_by_ids, mod.svc.bulk_suspend = orig_g, orig_s
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_admin, None)
