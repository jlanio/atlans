"""Suspending or deleting the account drops its executors — without touching the
tiers of the workspaces' policy.

Executor revocation was written in four places, and the account's only did the
status UPDATE and the cert blacklist: the open session stayed until the
revocation watcher came by. Now the account uses the same revocation as the
executor DELETE (status, cert, blacklist, `control: revoked` and close 4403
after the commit).

What the account does NOT do is remove the executor from the tiers: it may be in
the primary tier of workspaces of other owners, and forcibly emptying it deleted
the fallback and the terminal — the Isolated workspace became a shared pool and
the owner's configuration was lost, even if the account was reactivated later.
It stays in the tier, as the spec says (executor-isolation-routing §4.4), and
dispatch skips it. Removing from the tiers belongs to the executor DELETE and to
the operator's "revoke all".

Real database (SQLite): what matters is what remains stored — the tier, the
status, the audit.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import JSON, MetaData, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.api_token import ApiToken
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.executor import Executor
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_executor import WorkspaceExecutor
from app.services import admin_user_service, execution_alert_service, executor_enrollment_service
from app.services import executor_service


@asynccontextmanager
async def _from_db():
    """SQLite with what the revocation touches. `executors` uses JSONB, which SQLite
    does not compile: a copy of the table with JSON is used (see `executors_db`)."""
    executores = Executor.__table__.to_metadata(MetaData())
    for coluna in executores.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(executores.create)
        await conn.run_sync(Base.metadata.create_all, tables=[
            User.__table__, ApiToken.__table__, Workspace.__table__,
            WorkspaceExecutor.__table__, AuditEvent.__table__,
        ])
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def _seed(SessionMaker):
    """Ana's account has her machine, which is the ONLY executor in the primary
    tier of ws-1 (Bia's) and shares the one of ws-2 with another executor."""
    async with SessionMaker() as db:
        db.add_all([
            User(id_hash="u-ana", username="ana", email="ana@x.test", hashed_password="x"),
            User(id_hash="u-bia", username="bia", email="bia@x.test", hashed_password="x"),
            Executor(id_hash="ex-ana", name="maquina-da-ana", status="active", cert_serial="S1",
                     public_key="pem", created_by="u-ana"),
            Executor(id_hash="ex-outro", name="outro", status="active", cert_serial="S9",
                     public_key="pem", created_by="u-bia"),
            Workspace(id_hash="ws-1", name="Bacia", owner_id="u-bia"),
            Workspace(id_hash="ws-2", name="Cadastro", owner_id="u-bia"),
            WorkspaceExecutor(workspace_id="ws-1", executor_id="ex-ana", tier=1),
            WorkspaceExecutor(workspace_id="ws-2", executor_id="ex-ana", tier=1),
            WorkspaceExecutor(workspace_id="ws-2", executor_id="ex-outro", tier=1),
        ])
        await db.commit()


@pytest.fixture
def effects(monkeypatch):
    """What leaves the database: blacklist, e-mail to the owners and the WebSocket."""
    registro = MagicMock()
    registro.send_json = AsyncMock(return_value=True)
    registro.disconnect_executor = AsyncMock(return_value=True)
    monkeypatch.setattr(executor_service, "executor_registry", registro, raising=False)
    blacklist = AsyncMock()
    monkeypatch.setattr(executor_enrollment_service, "revoke_cert", blacklist)
    aviso = MagicMock()
    monkeypatch.setattr(execution_alert_service, "notify_primary_emptied_background", aviso)
    return {"registro": registro, "blacklist": blacklist, "aviso": aviso}


async def _suspend(db, ana):
    await admin_user_service.suspend_user(db, ana, motivo="teste", por="adm")


async def _delete_account(db, ana):
    await admin_user_service.soft_delete_user(db, ana)


async def _suspend_in_batch(db, ana):
    await admin_user_service.bulk_suspend(db, [ana], motivo="teste", por="adm")


async def _batch_delete(db, ana):
    await admin_user_service.bulk_soft_delete(db, [ana])


ACTIONS = [
    pytest.param(_suspend, "user_suspended", id="suspender"),
    pytest.param(_delete_account, "user_deleted", id="excluir"),
    pytest.param(_suspend_in_batch, "user_suspended", id="suspender-em-lote"),
    pytest.param(_batch_delete, "user_deleted", id="excluir-em-lote"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("acao, motivo", ACTIONS)
async def test_revoked_account_drops_the_executor_and_keeps_the_tiers(effects, acao, motivo):
    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        async with SessionMaker() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await acao(db, ana)

        async with SessionMaker() as db:
            status, serial = (await db.execute(
                select(Executor.status, Executor.cert_serial).where(Executor.id_hash == "ex-ana")
            )).one()
            tiers = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()
            auditoria = (await db.execute(
                select(AuditEvent.workspace_id)
                .where(AuditEvent.action == "workspace.executor_policy.member_detached")
            )).all()

    assert (status, serial) == ("revoked", None)
    # The tiers of ws-1 and ws-2 (Bia's) stay: dispatch skips the revoked executor
    # and follows the chain; no detach and no emptied-tier notice.
    assert sorted(tiers) == ["ws-1", "ws-2"]
    assert auditoria == []
    assert all(c.args[0] == [] for c in effects["aviso"].call_args_list)

    # The open session drops right away, as in the executor DELETE.
    registro = effects["registro"]
    registro.send_json.assert_awaited_once()
    destino, mensagem = registro.send_json.await_args.args
    assert destino == "ex-ana"
    assert (mensagem["type"], mensagem["action"]) == ("control", "revoked")
    registro.disconnect_executor.assert_awaited_once_with("ex-ana", code=4403, reason="Operador revogado.")
    effects["blacklist"].assert_awaited_once()
    assert effects["blacklist"].await_args.args == ("S1",)


@pytest.mark.asyncio
@pytest.mark.parametrize("acao, motivo", ACTIONS)
async def test_suspending_the_account_does_not_downgrade_another_owners_isolated_workspace(effects, acao, motivo):
    """ws-1 (Bia's) is Isolated: primary [ex-ana], fallback [ex-outro], terminal
    `fail`. With the account's forced detach, the primary was emptied, the fallback
    and the terminal were deleted and the workspace started sending jobs to the
    shared pool."""
    from app.services import workspace_executor_service as politica

    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        async with SessionMaker() as db:
            db.add(WorkspaceExecutor(workspace_id="ws-1", executor_id="ex-outro", tier=2))
            await db.commit()
        async with SessionMaker() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await acao(db, ana)

        async with SessionMaker() as db:
            tiers = sorted((await db.execute(
                select(WorkspaceExecutor.executor_id, WorkspaceExecutor.tier)
                .where(WorkspaceExecutor.workspace_id == "ws-1")
            )).all())
            policy_ws1 = await politica.load_policy_by_id(db, "ws-1")

    assert tiers == [("ex-ana", 1), ("ex-outro", 2)]
    assert policy_ws1.mode == politica.MODE_ISOLATED


@pytest.mark.asyncio
async def test_revoke_all_of_operator_removes_from_tiers_and_notifies_the_owners(effects, monkeypatch):
    """The "revoke all" is an explicit action on the executors: like the forced
    DELETE, it leaves the tiers and the owner of the emptied primary tier is notified."""
    from types import SimpleNamespace

    from app.api.routers import admin_users_router as R
    from app.core.rate_limiter import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    admin = SimpleNamespace(role="admin", id_hash="u-adm", username="adm")
    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        async with SessionMaker() as db:
            await R.revoke_all_user_agents(request=None, id_hash="u-ana", db=db, current_user=admin)

        async with SessionMaker() as db:
            tiers = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()

    assert tiers == []
    [chamada] = effects["aviso"].call_args_list
    assert [d["workspace_id"] for d in chamada.args[0] if d["would_empty_primary"]] == ["ws-1"]
    effects["registro"].disconnect_executor.assert_awaited_once_with("ex-ana", code=4403, reason="Operador revogado.")


@pytest.mark.asyncio
async def test_nothing_leaves_the_db_if_the_commit_fails(effects):
    """Blacklist, e-mail and close 4403 (terminal for the executor) only after the
    commit: a rollback must not leave the executor dropped yet active in the database."""
    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        async with SessionMaker() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            db.commit = AsyncMock(side_effect=RuntimeError("banco fora"))
            with pytest.raises(RuntimeError):
                await _suspend(db, ana)

    effects["registro"].send_json.assert_not_awaited()
    effects["registro"].disconnect_executor.assert_not_awaited()
    effects["blacklist"].assert_not_awaited()
    effects["aviso"].assert_not_called()


# ── The executor DELETE goes through the same revocation ─────────────────────

async def _revoke_via_route(SessionMaker, *, force):
    from types import SimpleNamespace

    from app.api.routers import executores_router as R

    admin = SimpleNamespace(role="admin", id_hash="u-adm", username="adm")
    async with SessionMaker() as db:
        ag = (await db.execute(select(Executor).where(Executor.id_hash == "ex-ana"))).scalar_one()
        await R.revoke_executor("ex-ana", force=force, db=db, current_user=admin, ag=ag)


@pytest.mark.asyncio
async def test_executor_delete_revokes_like_the_account(effects):
    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        await _revoke_via_route(SessionMaker, force=True)

        async with SessionMaker() as db:
            status, serial = (await db.execute(
                select(Executor.status, Executor.cert_serial).where(Executor.id_hash == "ex-ana")
            )).one()
            tiers = (await db.execute(
                select(WorkspaceExecutor.workspace_id).where(WorkspaceExecutor.executor_id == "ex-ana")
            )).scalars().all()

    assert (status, serial, tiers) == ("revoked", None, [])
    [chamada] = effects["aviso"].call_args_list
    assert chamada.kwargs["executor_name"] == "maquina-da-ana"
    effects["registro"].disconnect_executor.assert_awaited_once_with(
        "ex-ana", code=4403, reason="Executor revogado.",
    )
    assert effects["registro"].send_json.await_args.args[1]["reason"] == "Executor revogado pelo administrador."


@pytest.mark.asyncio
async def test_delete_without_force_does_not_empty_the_main_tier(effects):
    from app.core.exceptions import WorkspacePolicyConflictError

    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        with pytest.raises(WorkspacePolicyConflictError):
            await _revoke_via_route(SessionMaker, force=False)

        async with SessionMaker() as db:
            status = (await db.execute(
                select(Executor.status).where(Executor.id_hash == "ex-ana")
            )).scalar_one()

    assert status == "active"
    effects["registro"].disconnect_executor.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_of_another_account_is_not_touched(effects):
    async with _from_db() as SessionMaker:
        await _seed(SessionMaker)
        async with SessionMaker() as db:
            ana = (await db.execute(select(User).where(User.id_hash == "u-ana"))).scalar_one()
            await _suspend(db, ana)

        async with SessionMaker() as db:
            outro = (await db.execute(select(Executor).where(Executor.id_hash == "ex-outro"))).scalar_one()
            nivel = (await db.execute(
                select(WorkspaceExecutor.tier).where(WorkspaceExecutor.executor_id == "ex-outro")
            )).scalars().all()

    assert (outro.status, outro.cert_serial) == ("active", "S9")
    assert nivel == [1]
    assert [c.args[0] for c in effects["registro"].disconnect_executor.await_args_list] == ["ex-ana"]
