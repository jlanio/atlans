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
MEMBRO = "user-membro"
ESTRANHO = "user-de-outro-workspace"


def _cred(owner_id: str, cid=None) -> MagicMock:
    c = MagicMock()
    c.id = cid or uuid4()
    c.owner_id = owner_id
    c.type = "postgresql"
    c.data = {"connectionString": "postgres://x"}
    return c


def _session_com(credenciais: list) -> MagicMock:
    """Session that returns only what the query's WHERE would let through.

    The real filter is SQL; here the test inspects the statement to make sure
    owner_id went into it — see test_query_filtra_por_owner_id.
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


def _db_com_linhas(linhas: list) -> MagicMock:
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

async def test_sem_escopo_levanta_em_vez_de_resolver():
    """Fail-closed: call site novo que esquecer o escopo quebra em teste."""
    with pytest.raises(CredentialScopeMissing):
        await resolve_credentials_from_ids([str(uuid4())])


async def test_escopo_vazio_nao_resolve_nada():
    """A workflow without a workspace lands here — it must not become open resolution."""
    with _patch_session(_session_com([])):
        assert await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids=set()) == {}


async def test_contextvar_serve_de_escopo():
    """Simulation path: `simulate()` does not receive context parameters."""
    cred = _cred(DONO)
    with _patch_session(_session_com([cred])), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out


async def test_contextvar_carrega_shared_workspace_id():
    """/validate with a workspace: `simulate()` receives no parameters, so the
    ContextVar has to carry BOTH dimensions — owner AND shared workspace.
    Otherwise the guard would accept the shared credential and the simulation
    would not resolve it."""
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())])

    where = _where(session)
    assert "owner_id IN" in where and DONO in where
    assert "workspace_id" in where and "ws-1" in where
    assert " OR " in where


async def test_kwargs_explicitos_nao_se_misturam_com_o_contextvar():
    """Explicit kwargs are the ENTIRE scope: the ContextVar never fills in the
    missing dimension. Otherwise a call site passing only `allowed_owner_ids`
    inside a `credential_scope(..., shared_workspace_id=...)` would inherit the
    workspace without knowing — and vice versa."""
    # Explicit owner inside a ctx with owner AND workspace: only the explicit one applies.
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={MEMBRO})

    where = _where(session)
    assert MEMBRO in where
    assert DONO not in where
    assert "ws-1" not in where

    # Explicit workspace alone: no owner clause, even with an active ctx.
    session = _session_com([])
    with _patch_session(session), credential_scope({DONO}, shared_workspace_id="ws-1"):
        await resolve_credentials_from_ids([str(uuid4())], shared_workspace_id="ws-2")

    where = _where(session)
    assert "owner_id IN" not in where
    assert "ws-2" in where
    assert DONO not in where
    assert "ws-1" not in where


# ── Filter by owner ──────────────────────────────────────────────────────────

async def test_query_filtra_por_owner_id():
    """The fence has to be in the SQL, not just in the caller.

    Checks the WHERE specifically: `select(Credential)` already lists owner_id
    among the selected columns, so searching the whole statement would pass
    even with no filter at all.
    """
    session = _session_com([])
    with _patch_session(session):
        await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO, MEMBRO})

    stmt = str(session.execute.await_args_list[0].args[0].compile(
        compile_kwargs={"literal_binds": True},
    ))
    where = stmt.split("WHERE", 1)[1]
    assert "owner_id" in where
    assert DONO in where


async def test_credencial_de_membro_do_workspace_resolve():
    """B runs A's workflow: A's credential still applies."""
    cred = _cred(DONO)
    with _patch_session(_session_com([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={DONO, MEMBRO},
        )

    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_credencial_sem_dono_nao_resolve():
    """A NULL owner_id never matches IN — that is the desired behavior.

    Today those credentials are readable by ANY authenticated user,
    including the secrets via GET /credentials/{id}/data.
    """
    session = _session_com([])   # the database WHERE would not return it
    with _patch_session(session):
        out = await resolve_credentials_from_ids([str(uuid4())], allowed_owner_ids={DONO})

    assert out == {}


# ── Scope D: owner (who triggered) OR shared with the workspace ──────────────

async def test_escopo_d_no_sql_e_dono_ou_workspace_sem_orfa():
    """The clause is (owner IS NOT NULL) AND (owner IN allowed OR workspace_id == ws)."""
    session = _session_com([])
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


async def test_escopo_d_sem_usuario_so_compartilhadas_no_sql():
    """triggered_by=None (cron/webhook): no owner clause, only the workspace one."""
    session = _session_com([])
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


async def test_credencial_compartilhada_resolve_mesmo_nao_sendo_de_quem_disparou():
    """Shared with the workspace resolves for whoever triggered, even when it
    belongs to another owner (the database returns it via the workspace_id clause)."""
    cred = _cred("outro-dono")
    with _patch_session(_session_com([cred])):
        out = await resolve_credentials_from_ids(
            [str(cred.id)], allowed_owner_ids={MEMBRO}, shared_workspace_id="ws-1",
        )
    assert out[str(cred.id)]["connectionString"] == "postgres://x"


async def test_credencial_privada_de_outro_nao_resolve():
    """Not shared and not belonging to whoever triggered, the database does not
    return it — the WHERE excludes it. We simulate this with the session that
    only delivers what the filter would allow."""
    with _patch_session(_session_com([])):    # the WHERE (owner/ws) would not return it
        out = await resolve_credentials_from_ids(
            [str(uuid4())], allowed_owner_ids={MEMBRO}, shared_workspace_id="ws-1",
        )
    assert out == {}


# ── last_used_at (F6): carimbo best-effort ───────────────────────────────────

def _statements(session):
    """SQL statements that went through session.execute, as objects."""
    return [c.args[0] for c in session.execute.await_args_list]


async def test_last_used_carimbado_e_commitado_na_sessao_propria():
    """Own session (simulate): issues an UPDATE on last_used_at and COMMITS.

    get_session_async rolls back on exit — without an explicit commit the stamp
    would not persist.
    """
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    with _patch_session(session), credential_scope({DONO}):
        out = await resolve_credentials_from_ids([str(cred.id)])

    assert str(cred.id) in out
    updates = [s for s in _statements(session) if isinstance(s, Update)]
    assert len(updates) == 1, "esperado exatamente um UPDATE de last_used_at"
    session.commit.assert_awaited_once()


async def test_last_used_grava_horario_utc_sem_fuso():
    """`Credential.last_used_at` is a `DateTime` without a time zone: asyncpg
    rejects a time-zone-AWARE datetime ("can't subtract offset-naive and
    offset-aware datetimes"), and the stamp's savepoint swallowed the error — on
    Postgres last_used_at was never written. The mocks here have no driver, so
    the guarantee is the value that goes into the UPDATE: naive and in UTC."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    await resolve_credentials_from_ids([str(cred.id)], allowed_owner_ids={DONO}, db=session)

    (update,) = [s for s in _statements(session) if isinstance(s, Update)]
    carimbo = update.compile().params["last_used_at"]
    assert carimbo.tzinfo is None
    agora_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs(agora_utc - carimbo) < timedelta(seconds=5)


async def test_last_used_nao_commita_na_sessao_do_request():
    """Request session (db=): issues the UPDATE but does NOT commit — the caller
    commits, so as not to accidentally write its pending work."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
    out = await resolve_credentials_from_ids(
        [str(cred.id)], allowed_owner_ids={DONO}, db=session,
    )

    assert str(cred.id) in out
    assert any(isinstance(s, Update) for s in _statements(session))
    session.commit.assert_not_awaited()


async def test_last_used_falha_nao_derruba_resolucao():
    """If the audit UPDATE fails, the resolution still delivers the credentials."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
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


async def test_last_used_falha_na_sessao_do_request_nao_faz_rollback():
    """In the request's SHARED session, the stamp failure must not call
    rollback — that would discard the caller's pending work. The SAVEPOINT has
    already reverted what was ours; the resolution still delivers the
    credentials and the caller remains free to commit (avoids the 500 on
    dispatch)."""
    from sqlalchemy.sql.dml import Update

    cred = _cred(DONO)
    session = _session_com([cred])
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

async def test_workspace_credential_owners_une_dono_e_membros():
    """Owner and members come from a single query (outerjoin), not two SELECTs."""
    db = MagicMock()
    res = MagicMock()
    # One row per member; the owner repeats in all of them.
    res.all.return_value = [(DONO, MEMBRO), (DONO, None)]
    db.execute = AsyncMock(return_value=res)

    assert await workspace_credential_owners(db, "ws-1") == {DONO, MEMBRO}
    assert db.execute.await_count == 1


async def test_workspace_credential_owners_sem_workspace():
    """Legacy workflow without a workspace: empty scope, without going to the database."""
    db = MagicMock(execute=AsyncMock())

    assert await workspace_credential_owners(db, None) == set()
    db.execute.assert_not_awaited()


# ── Validation credential guard (assert_credentials_accessible) ─────────────

async def test_assert_recusa_credencial_alheia():
    """IDOR: the definition comes from the body and simulate() connects to the database."""
    alheia = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = []            # none belongs to the user
    db.execute = AsyncMock(return_value=res)

    with pytest.raises(CredentialAccessDeniedError, match=str(alheia)):
        await assert_credentials_accessible(db, [str(alheia)], MEMBRO)


async def test_assert_aceita_credencial_propria():
    minha = uuid4()
    db = MagicMock()
    res = MagicMock()
    res.all.return_value = [(minha,)]
    db.execute = AsyncMock(return_value=res)

    await assert_credentials_accessible(db, [str(minha)], MEMBRO)


async def test_assert_recusa_uuid_invalido():
    db = MagicMock(execute=AsyncMock())

    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, ["nao-e-uuid"], MEMBRO)


# ── Validation guard with a workspace: same clause as the dispatch ──────────
#
# Validate with a workspace has to accept EXACTLY what Executar would resolve:
# (owner IS NOT NULL) AND (owner == user OR workspace_id == ws). Never the member
# list — otherwise one member would validate (and simulate() would CONNECT) with
# another member's PRIVATE credential.

async def test_assert_accessible_sql_e_dono_ou_workspace_sem_orfa_e_sem_membros():
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(
            db, [str(uuid4())], MEMBRO, shared_workspace_id="ws-1",
        )

    where = _where(db)
    assert "owner_id IS NOT NULL" in where             # a shared orphan does not pass
    assert MEMBRO in where                             # o proprio usuario
    assert "workspace_id" in where and "ws-1" in where  # or shared with the ws
    assert " OR " in where
    assert "workspace_members" not in _sql(db)         # members do not get in, not even via join


async def test_assert_accessible_sem_workspace_so_dono():
    """Without a workspace the clause does not even enter the SQL — it does not
    become `workspace_id = NULL` (would never match) nor `IS NULL` (would match
    any owner's private one)."""
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError):
        await assert_credentials_accessible(db, [str(uuid4())], MEMBRO)

    where = _where(db)
    assert MEMBRO in where
    assert "owner_id IS NOT NULL" in where
    assert "workspace_id" not in where


async def test_assert_accessible_aceita_o_que_o_banco_devolve():
    """The decision belongs to the SQL: if the WHERE returned all the ids (own or
    shared), it passes silently, with no second check in Python."""
    minha, compartilhada = uuid4(), uuid4()
    db = _db_com_linhas([(minha,), (compartilhada,)])

    await assert_credentials_accessible(
        db, [str(minha), str(compartilhada)], MEMBRO, shared_workspace_id="ws-1",
    )


async def test_assert_accessible_mensagem_cita_o_workspace_e_o_uuid():
    """Whoever gets the 403 needs to know WHAT was rejected (the UUID, to find the
    node) and that sharing with the workspace was already considered — the way
    out is to share the credential, not to ask the owner for the password."""
    alheia = uuid4()
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(
            db, [str(alheia)], MEMBRO, shared_workspace_id="ws-1",
        )

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" in msg


async def test_assert_accessible_sem_workspace_nao_cita_workspace():
    """Without a workspace the guard is "owner only": the workspace dimension
    appears neither in the SQL nor in the rejection message."""
    alheia = uuid4()
    db = _db_com_linhas([])
    with pytest.raises(CredentialAccessDeniedError) as exc:
        await assert_credentials_accessible(db, [str(alheia)], MEMBRO)

    msg = str(exc.value)
    assert str(alheia) in msg
    assert "workspace" not in msg
    assert "workspace_id" not in _where(db)


# ── Integration: start_analysis builds the scope (option D) ──────────────────
#
# Execution scope = {who triggered (triggered_by)} + credentials shared with
# the workflow's workspace. Being a MEMBER of the workspace is not enough.

def _svc_com_workflow(workspace_id):
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


async def test_start_analysis_escopo_e_quem_disparou_mais_compartilhadas():
    """Option D: scope = {who triggered} + the workflow's shared_workspace_id —
    NOT the set of workspace members."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow("ws-1")
    capturado = {}

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):
        capturado["allowed"] = set(allowed_owner_ids or [])
        capturado["shared_ws"] = shared_workspace_id
        capturado["db"] = db
        return {}

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        await svc.start_analysis("wf-1", triggered_by=MEMBRO)

    # Only whoever triggered enters as owner; DONO (another member) does NOT.
    assert capturado["allowed"] == {MEMBRO}
    assert DONO not in capturado["allowed"]
    assert capturado["shared_ws"] == "ws-1"
    # The request session goes along: without it the resolver opened a second
    # connection from the same pool without releasing the first.
    assert capturado["db"] is svc.crud.db


async def test_start_analysis_cron_sem_usuario_so_alcanca_compartilhadas():
    """Trigger without a user (triggered_by=None): empty owner, only the
    credentials shared with the workspace resolve."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow("ws-1")
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


async def test_start_analysis_recusa_workflow_sem_workspace():
    """Without a workspace there is no one to trust — fails instead of resolving openly."""
    from contextlib import ExitStack

    svc, wf = _svc_com_workflow(None)

    async def _resolve(ids, *, allowed_owner_ids=None, shared_workspace_id=None, db=None):  # pragma: no cover
        raise AssertionError("não deveria resolver credencial sem workspace")

    with ExitStack() as stack:
        for p in _patches_do_dispatch(wf, _resolve):
            stack.enter_context(p)
        with pytest.raises(CredentialAccessDeniedError):
            await svc.start_analysis("wf-1", triggered_by=MEMBRO)
