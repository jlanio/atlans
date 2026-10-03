# tests/unit/test_credential_authorization.py
"""Authorization in credential resolution.

Before, the lookup was `WHERE id IN (...)`, with no owner and no workspace. Since
the credential_id sits in plain text in the definition and is readable by any
member who opens the workflow, it was enough to copy it into a workflow in
ANOTHER workspace — created by the attacker themselves — to use someone else's
credential indefinitely.

These tests fail the moment the owner filter leaves the query.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.authorization.credential_loader import (
    CredentialScopeMissing,
    assert_credentials_accessible,
    credential_scope,
    resolve_credentials_from_ids,
    workspace_credential_owners,
)
from app.core.exceptions import CredentialAccessDeniedError

DONO = "user-dono"
MEMBER = "user-membro"
OUTSIDER = "user-de-outro-workspace"


def _cred(owner_id: str, cid=None) -> MagicMock:
    c = MagicMock()
    c.id = cid or uuid4()
    c.owner_id = owner_id
    c.type = "postgresql"
    c.data = {"connectionString": "postgres://x"}
    return c


def _session_with(credenciais: list) -> MagicMock:
    """Session that returns only what the query's WHERE would let through.

    The real filter is SQL; here the test inspects the statement to make sure
    owner_id went into it — see test_query_filters_by_owner_id.
    """
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = credenciais
    result.all.return_value = []          # _explain_missing
    session.execute = AsyncMock(return_value=result)
    # async commit/rollback: the resolver commits the last_used_at stamp when it
    # opens its own session. Without these AsyncMocks, `await session.commit()`
    # would fall into the best-effort branch and the test would not exercise
    # the success path.
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    # begin_nested: the last_used_at stamp runs inside a SAVEPOINT so as not to
    # poison the caller's transaction. The mock returns a no-op async CM (it
    # does not suppress exceptions — __aexit__ → False), like the real savepoint.
    session.begin_nested = MagicMock(side_effect=lambda: _AsyncNoop())
    return session


class _AsyncNoop:
    """No-op async context manager to simulate session.begin_nested()."""
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False   # does not suppress the exception — same as the real savepoint


def _patch_session(session):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake():
        yield session

    return patch("app.core.authorization.credential_loader.get_session_async", _fake)


def _sql(session) -> str:
    """First statement that went through session.execute, compiled with literals.

    Compiling is the only way to check the filter: the session is fake, so the
    real WHERE never runs — and it is precisely what this file protects.
    """
    return str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    ))


def _where(session) -> str:
    """Only the WHERE clause — `select(Credential)` lists owner_id/workspace_id
    among the columns, so searching the whole statement would pass with no filter."""
    return _sql(session).split("WHERE", 1)[1]


def _db_with_rows(linhas: list) -> MagicMock:
    """Request session for the /validate guards: `.all()` returns `linhas`,
    that is, only the ids the WHERE would let through."""
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = linhas
    db.execute = AsyncMock(return_value=res)
    return db


@pytest.fixture(autouse=True)
def _decrypt():
    with patch(
        "app.core.authorization.credential_loader.decrypt_credential_data",
        side_effect=lambda d: dict(d),
    ):
        yield


# ── Escopo obrigatorio ───────────────────────────────────────────────────────

async def test_without_scope_raises_instead_of_resolving():
    """Fail-closed: call site novo que esquecer o escopo quebra em teste."""
    with pytest.raises(CredentialScopeMissing):
        await resolve_credentials_from_ids([str(uuid4())])


async def test_empty_scope_resolves_nothing():
    """A workflow without a workspace lands here — it must not become open resolution."""
    with _patch_session(_session_with([])):
        assert await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids=set()) == {}


async def test_contextvar_serves_as_scope():
    """Simulation path: `simulate()` does not receive context parameters."""
    cred = _cred(DONO)
    with _patch_session(_session_with([cred])), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out


async def test_contextvar_carries_shared_workspace_id():
    """/validate with a workspace: `simulate()` receives no parameters, so the
    ContextVar has to carry BOTH dimensions — owner AND shared workspace.
    Otherwise the guard would accept the shared credential and the simulation
    would not resolve it."""
    session = _session_with([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())])

    where = _where(session)
    assert "owner_id IN" in where and DONO in where
    assert "workspace_id" in where and "ws-1" in where
    assert " OR " in where


async def test_explicit_kwargs_do_not_mix_with_the_contextvar():
    """Explicit kwargs are the ENTIRE scope: the ContextVar never fills in the
    missing dimension. Otherwise a call site passing only `allowed_owner_ids`
    inside a `credential_scope(..., shared_workspace_id=...)` would inherit the
    workspace without knowing — and vice versa."""
    # Explicit owner inside a ctx with owner AND workspace: only the explicit one applies.
    session = _session_with([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={MEMBER})

    where = _where(session)
    assert MEMBER in where
    assert DONO not in where
    assert "ws-1" not in where

    # Explicit workspace alone: no owner clause, even with an active ctx.
    session = _session_with([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], shared_workspace_id="ws-2")

    where = _where(session)
    assert "owner_id IN" not in where
    assert "ws-2" in where
    assert DONO not in where
    assert "ws-1" not in where


# ── Filter by owner ──────────────────────────────────────────────────────────

async def test_query_filters_by_owner_id():
    """The fence has to be in the SQL, not just in the caller.

    Checks the WHERE specifically: `select(Credential)` already lists owner_id
    among the selected columns, so searching the whole statement would pass
    even with no filter at all.
    """
    session = _session_with([])
    with _patch_session(session):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO, MEMBER})

    stmt = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    ))
    where = stmt.split("WHERE", 1)[1]
    assert "owner_id" in where
    assert DONO in where


async def test_workspace_member_credential_resolves():
    """B runs A's workflow: A's credential still applies."""
    cred = _cred(DONO)
    with _patch_session(_session_with([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={DONO, MEMBER},
        )

    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_ownerless_credential_does_not_resolve():
    """A NULL owner_id never matches IN — that is the desired behavior.

    Today those credentials are readable by ANY authenticated user,
    including the secrets via GET /credentials/{id}/data.
    """
    session = _session_with([])   # the database WHERE would not return it
    with _patch_session(session):
        out = await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO})

    assert out == {}


# ── Scope D: owner (who triggered) OR shared with the workspace ──────────────

async def test_scope_d_in_sql_is_owner_or_workspace_without_orphan():
    """The clause is (owner IS NOT NULL) AND (owner IN allowed OR workspace_id == ws)."""
    session = _session_with([])
    with _patch_session(session):
        await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids={DONO}, shared_workspace_id="ws-1",
        )
    where = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    )).split("WHERE", 1)[1]
    assert "owner_id IS NOT NULL" in where          # an orphan never resolves
    assert "owner_id IN" in where and DONO in where  # belongs to who triggered
    assert "workspace_id" in where and "ws-1" in where  # compartilhada
    assert " OR " in where


async def test_scope_d_without_user_only_shared_in_sql():
    """triggered_by=None (cron/webhook): no owner clause, only the workspace one."""
    session = _session_with([])
    with _patch_session(session):
        await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids=set(), shared_workspace_id="ws-1",
        )
    where = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    )).split("WHERE", 1)[1]
    assert "workspace_id" in where and "ws-1" in where
    assert "owner_id IN" not in where               # no user → no owner clause
    assert "owner_id IS NOT NULL" in where           # but an orphan is still blocked


async def test_shared_credential_resolves_even_if_not_the_triggerers():
    """Shared with the workspace resolves for whoever triggered, even when it
    belongs to another owner (the database returns it via the workspace_id clause)."""
    cred = _cred("outro-dono")
    with _patch_session(_session_with([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={MEMBER}, shared_workspace_id="ws-1",
        )
    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_someone_elses_private_credential_does_not_resolve():
    """Not shared and not belonging to whoever triggered, the database does not
    return it — the WHERE excludes it. We simulate this with the session that
    only delivers what the filter would allow."""
    with _patch_session(_session_with([])):    # the WHERE (owner/ws) would not return it
        out = await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids={MEMBER}, shared_workspace_id="ws-1",
        )
    assert out == {}


# ── last_used_at (F6): carimbo best-effort ───────────────────────────────────

def _statements(session):
    """SQL statements that went through session.execute, as objects."""
    return [c.args[0] for c in session.execute.await_args_list]


async def test_last_used_stamped_and_committed_in_own_session():
    """Own session (simulate): issues an UPDATE on last_used_at and COMMITS.

    get_session_async rolls back on exit — without an explicit commit the stamp
    would not persist.
    """
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_with([cred])
    with _patch_session(session), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out
    updates = [s for s in _statements(session) if isinstance(s, Update)]
    assert len(updates) == 1, "esperado exatamente um UPDATE de last_used_at"
    session.commit.assert_awaited_once()


async def test_last_used_writes_naive_utc_time():
    """`Credential.last_used_at` is a `DateTime` without a time zone: asyncpg
    rejects a time-zone-AWARE datetime ("can't subtract offset-naive and
    offset-aware datetimes"), and the stamp's savepoint swallowed the error — on
    Postgres last_used_at was never written. The mocks here have no driver, so
    the guarantee is the value that goes into the UPDATE: naive and in UTC."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_with([cred])
    await resolve_credentials_from_ids([str(cred.id)], allowed_owner_ids={DONO}, db=session)

    (update,) = [s for s in _statements(session) if isinstance(s, Update)]
    carimbo = update.compile().params["last_used_at"]
    assert carimbo.tzinfo is None
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(now_utc - carimbo) < timedelta(seconds=5)


async def test_last_used_does_not_commit_in_the_request_session():
    """Request session (db=): issues the UPDATE but does NOT commit — the caller
    commits, so as not to accidentally write its pending work."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_with([cred])
    out = await resolve_credentials_from_ids(
        [str(cred.id)], allowed_owner_ids={DONO}, db=session,
    )

    assert str(cred.id) in out
    assert any(isinstance(s, Update) for s in _statements(session))
    session.commit.assert_not_awaited()


async def test_last_used_failure_does_not_break_resolution():
    """If the audit UPDATE fails, the resolution still delivers the credentials."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_with([cred])
    result = session.execute.return_value

    async def _execute(stmt, *a, **k):
        if isinstance(stmt, Update):
            raise RuntimeError("banco indisponivel para o carimbo")
        return result

    session.execute = AsyncMock(side_effect=_execute)
    with _patch_session(session), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    # The secret was resolved despite the best-effort failure on the stamp.
    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_last_used_failure_does_not_roll_back_the_request_session():
    """In the request's SHARED session, the stamp failure must not call
    rollback — that would discard the caller's pending work. The SAVEPOINT has
    already reverted what was ours; the resolution still delivers the
    credentials and the caller remains free to commit (avoids the 500 on
    dispatch)."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_with([cred])
    result = session.execute.return_value

    async def _execute(stmt, *a, **k):
        if isinstance(stmt, Update):
            raise RuntimeError("deadlock no carimbo")
        return result

    session.execute = AsyncMock(side_effect=_execute)
    out = await resolve_credentials_from_ids(
        [str(cred.id)], allowed_owner_ids={DONO}, db=session,
    )

    assert str(cred.id) in out
    session.rollback.assert_not_awaited()   # caller's transaction untouched


# ── Workspace scope helper ───────────────────────────────────────────────────

async def test_workspace_credential_owners_unites_owner_and_members():
    """Owner and members come from a single query (outerjoin), not two SELECTs."""
    db = MagicMock()
    res = MagicMock()
    # One row per member; the owner repeats in all of them.
    res.all.return_value = [(DONO, MEMBER), (DONO, None)]
    db.execute = AsyncMock(return_value=res)

    assert await workspace_credential_owners(db, "ws-1") == {DONO, MEMBER}
    assert db.execute.await_count == 1


async def test_workspace_credential_owners_without_workspace():
    """Legacy workflow without a workspace: empty scope, without going to the database."""
    db = MagicMock(execute=AsyncMock())

    assert await workspace_credential_owners(db, None) == set()
    db.execute.assert_not_awaited()


# ── Validation credential guard (assert_credentials_accessible) ─────────────

async def test_assert_rejects_foreign_credential():
    """IDOR: the definition comes from the body and simulate() connects to the database."""
    alheia = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = []            # none belongs to the user
    db.execute = AsyncMock(return_value=res)

    with pytest.raises(CredentialAccessDeniedError, match=str(alheia)):
        await assert_credentials_accessible(db, [str(alheia)], MEMBER)


async def test_assert_accepts_own_credential():
    minha = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = [(minha,)]
    db.execute = AsyncMock(return_value=res)

    await assert_credentials_accessible(db, [str(minha)], MEMBER)


async def test_assert_rejects_invalid_uuid():
    db = MagicMock(execute=AsyncMock())

    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, ["nao-e-uuid"], MEMBER)


# ── Validation guard with a workspace: same clause as the dispatch ──────────
#
# Validate with a workspace has to accept EXACTLY what Executar would resolve:
# (owner IS NOT NULL) AND (owner == user OR workspace_id == ws). Never the member
# list — otherwise one member would validate (and simulate() would CONNECT) with
# another member's PRIVATE credential.

async def test_assert_accessible_sql_is_owner_or_workspace_without_orphan_or_members():
    db = _db_with_rows([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(
            db, [str(uuid4())], MEMBER, shared_workspace_id="ws-1",
        )

    where = _where(db)
    assert "owner_id IS NOT NULL" in where             # a shared orphan does not pass
    assert MEMBER in where                             # o proprio usuario
    assert "workspace_id" in where and "ws-1" in where  # or shared with the ws
    assert " OR " in where
    assert "workspace_members" not in _sql(db)         # members do not get in, not even via join


async def test_assert_accessible_without_workspace_owner_only():
    """Without a workspace the clause does not even enter the SQL — it does not
    become `workspace_id = NULL` (would never match) nor `IS NULL` (would match
    any owner's private one)."""
    db = _db_with_rows([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, [str(uuid4())], MEMBER)

    where = _where(db)
    assert MEMBER in where
    assert "owner_id IS NOT NULL" in where
    assert "workspace_id" not in where


async def test_assert_accessible_accepts_what_the_db_returns():
    """The decision belongs to the SQL: if the WHERE returned all the ids (own or
    shared), it passes silently, with no second check in Python."""
    minha, compartilhada = uuid4(), uuid4()
    db = _db_with_rows([(minha,), (compartilhada,)])

    await assert_credentials_accessible(
        db, [str(minha), str(compartilhada)], MEMBER, shared_workspace_id="ws-1",
    )


async def test_assert_accessible_message_cites_the_workspace_and_the_uuid():
    """Whoever gets the 403 needs to know WHAT was rejected (the UUID, to find the
    node) and that sharing with the workspace was already considered — the way
    out is to share the credential, not to ask the owner for the password."""
    alheia = uuid4()
    db = _db_with_rows([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(
            db, [str(alheia)], MEMBER, shared_workspace_id="ws-1",
        )

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" in msg


async def test_assert_accessible_without_workspace_does_not_cite_workspace():
    """Without a workspace the guard is "owner only": the workspace dimension
    appears neither in the SQL nor in the rejection message."""
    alheia = uuid4()
    db = _db_with_rows([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(db, [str(alheia)], MEMBER)

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" not in msg
    assert "workspace_id" not in _where(db)


# ── Integration: start_analysis builds the scope (option D) ──────────────────
#
# Execution scope = {who triggered (triggered_by)} + credentials shared with
# the workflow's workspace. Being a MEMBER of the workspace is not enough.

def _svc_with_workflow(workspace_id):
    from app.services.workflow_service import WorkflowService

    wf = MagicMock(id_hash="wf-1", workspace_id=workspace_id, flag_ative=True)
    svc = WorkflowService(MagicMock())
    return svc, wf


def _patches_do_dispatch(wf, resolve_fn):
    """Silences everything start_analysis touches before and after the credential block."""
    return [
        patch("app.services.workflow_service._load_workflow",
              new=AsyncMock(return_value=(wf, {"nodes": [], "edges": []}))),
        patch("app.services.workflow_service._validate_trigger_inputs"),
        patch("app.services.workflow_service._collect_credential_ids", return_value=["cred-1"]),
        patch("app.services.workflow_service.resolve_credentials_from_ids", new=resolve_fn),
        patch("app.services.workflow_service._validate_trigger_credentials_only", new=AsyncMock()),
        patch("app.services.disabled_nodes_service.disabled_names",
              new=AsyncMock(return_value=set())),
        patch("app.services.workflow_execution_service._validate_no_disabled_nodes"),
        patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive",
              new=AsyncMock(return_value={})),
        patch("app.services.workflow_service.WorkflowService._resolve_candidates",
              new=AsyncMock(return_value=[MagicMock()])),
        patch("app.services.workflow_service.WorkflowService._dispatch_job",
              new=AsyncMock(return_value=MagicMock(id="run-1"))),
    ]


async def test_start_analysis_scope_is_triggerer_plus_shared():
    """Option D: scope = {who triggered} + the workflow's shared_workspace_id —
    NOT the set of workspace members."""
    from contextlib import ExitStack

    svc, wf = _svc_with_workflow("ws-1")
    capturado = {}

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        capturado["allowed"] = set(allowed_owner_ids or [])
        capturado["shared_ws"] = shared_workspace_id
        capturado["db"] = db
        return {}

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        await svc.start_analysis("wf-1", triggered_by=MEMBER)

    # Only whoever triggered enters as owner; DONO (another member) does NOT.
    assert capturado["allowed"] == {MEMBER}
    assert DONO not in capturado["allowed"]
    assert capturado["shared_ws"] == "ws-1"
    # The request session goes along: without it the resolver opened a second
    # connection from the same pool without releasing the first.
    assert capturado["db"] is svc.crud.db


async def test_start_analysis_cron_without_user_only_reaches_shared():
    """Trigger without a user (triggered_by=None): empty owner, only the
    credentials shared with the workspace resolve."""
    from contextlib import ExitStack

    svc, wf = _svc_with_workflow("ws-1")
    capturado = {}

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        capturado["allowed"] = set(allowed_owner_ids or [])
        capturado["shared_ws"] = shared_workspace_id
        return {}

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        await svc.start_analysis("wf-1")   # no triggered_by

    assert capturado["allowed"] == set()
    assert capturado["shared_ws"] == "ws-1"


async def test_start_analysis_rejects_workflow_without_workspace():
    """Without a workspace there is no one to trust — fails instead of resolving openly."""
    from contextlib import ExitStack

    svc, wf = _svc_with_workflow(None)

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):  # pragma: no cover
        raise AssertionError("não deveria resolver credencial sem workspace")

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        with pytest.raises(CredentialAccessDeniedError):
            await svc.start_analysis("wf-1", triggered_by=MEMBER)
