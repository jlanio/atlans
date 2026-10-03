# app/core/authorization/credential_loader.py
"""
Credential resolution for execution — with a mandatory authorization scope.

Before, the lookup was by bare ID (`WHERE id IN (...)`), without looking at owner or
workspace. Since the `credential_id` sits in plain text in the definition and is readable
by any member who opens the workflow, it was enough to copy it into a workflow in
another workspace — created by the attacker themselves — to use someone else's credential
indefinitely. The same hole applied to `POST /workflows/validate`, which
accepts an arbitrary definition and even CONNECTS to the database through `simulate()`.

The scope has two dimensions (one match is enough): the authorized `owner_id`s and the
sharing workspace. In EXECUTION, a credential is resolved if it belongs
to WHOEVER TRIGGERED (`triggered_by`) OR is EXPLICITLY shared with the
workflow's workspace (`workspace_id`). Merely being a member of the workspace is not
enough — otherwise a member would use another's PRIVATE credential just by copying the
`credential_id` from the definition. Triggers without a user (cron/webhook) reach
only the shared credentials. In SIMULATION/validation, the scope is the
authenticated user and, when the validation provides a workspace, the credentials
shared with it — the SAME clause, applied before connecting
(`assert_credentials_accessible`) and during `simulate()` (`credential_scope`).
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Collection, Iterable, List
from uuid import UUID

from sqlalchemy.future import select

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger

from app.models.credential import Credential
from app.core.db import get_session_async
from app.core.utils.encryption import decrypt_credential_data

logger = get_logger(__name__)


class CredentialScopeMissing(RuntimeError):
    """Resolution attempted without an authorization scope.

    A programming error, not a data error: it flags a new call site that did not
    declare whose credentials may be used. Failing loudly here is what prevents
    a silent regression to the old behavior.
    """


@dataclass(frozen=True)
class CredentialScope:
    """What a `credential_scope` delimits: authorized owners and, optionally,
    the workspace whose shared credentials also count.

    These are the SAME two dimensions as the kwargs of `resolve_credentials_from_ids`.
    The ContextVar carried only the owner one, and validation with a workspace was
    inconsistent: the guard (`assert_credentials_accessible`) accepted the shared
    credential, but `simulate()` — which takes no parameters — did not
    resolve it, because the implicit scope did not know about the workspace.
    """
    owner_ids: frozenset[str]
    shared_workspace_id: str | None = None


# Implicit scope for code that takes no parameters — today only the nodes'
# `simulate()`, invoked generically by `simulate_runner`.
_scope: ContextVar[CredentialScope | None] = ContextVar("credential_scope", default=None)


@contextmanager
def credential_scope(owner_ids: Iterable[str], shared_workspace_id: str | None = None):
    """Delimits whose credentials may be resolved within the block.

    `shared_workspace_id` extends the scope to the credentials EXPLICITLY
    shared with that workspace (the same rule as the dispatch). Only pass it
    when the caller has already verified that the user belongs to the workspace — the
    resolver trusts what it receives here.
    """
    token = _scope.set(CredentialScope(frozenset(owner_ids), shared_workspace_id))
    try:
        yield
    finally:
        _scope.reset(token)


async def workspace_credential_owners(db, workspace_id: str | None) -> set[str]:
    """Users with access to the workspace: the owner plus the members.

    Serves MEMBERSHIP checks — today, the workspace change report, which warns
    which credential owners no longer reach the destination.
    It is NOT a credential scope: passing it as `allowed_owner_ids` (or using it
    in a guard) would hand each member's PRIVATE credential to any other
    member who copied the `credential_id` from the definition. The resolution scope is
    {whoever triggered} + `shared_workspace_id` — see `resolve_credentials_from_ids`
    and `assert_credentials_accessible`.

    A nonexistent/deleted workspace returns an empty set, and the caller
    decides whether that is an error.
    """
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    if not workspace_id:
        return set()

    # Owner and members in a single query. They were two sequential SELECTs in the
    # hot path of POST /execute — and the second did not even filter the workspace by
    # `deleted_at`, so a workspace in the trash kept authorizing
    # its credentials through the member list. The outerjoin starts from Workspace,
    # so a nonexistent or deleted workspace returns no row at all.
    rows = (await db.execute(
        select(Workspace.owner_id, WorkspaceMember.user_id)
        .outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id_hash)
        .where(
            Workspace.id_hash == workspace_id,
            Workspace.deleted_at.is_(None),
        )
    )).all()

    return {uid for row in rows for uid in row if uid}


async def assert_credentials_accessible(
    db, credential_ids: Iterable[str], owner_id: str, shared_workspace_id: str | None = None,
) -> None:
    """Refuses if any id neither belongs to `owner_id` nor is shared with the workspace.

    Guard for validation (`validate_service`), which accepts an arbitrary
    definition: the `simulate()` of dynamic nodes even CONNECTS to the database,
    so someone else's credential_id there meant running SQL on
    another user's infrastructure. Blocking here gives a clear 403 before
    any connection. The `WorkflowService` writes use the same guard.

    The clause is the SAME as the dispatch's (`_resolve_in_session`): (requested id) AND
    (owner_id IS NOT NULL) AND (owner_id == user OR workspace_id ==
    shared_workspace_id). Keeping the two identical ensures validate accepts
    exactly what Run would resolve — no more (it would connect to a
    credential the execution would refuse) and no less (a 403 on a credential the
    execution uses). `owner_id IS NOT NULL` is fail-closed: a shared orphan
    does not pass. The workspace clause only applies when `shared_workspace_id` is
    provided; without it the guard is "owner only".

    Never swap the workspace for `workspace_credential_owners`: being a member of the
    workspace grants no right to another member's PRIVATE credential.
    """
    from sqlalchemy import or_

    from app.core.exceptions import CredentialAccessDeniedError

    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception:
            raise CredentialAccessDeniedError(f"credential_id inválido: {cid!r}")
    if not uuid_ids:
        return

    escopo = [Credential.owner_id == owner_id]
    if shared_workspace_id:
        escopo.append(Credential.workspace_id == shared_workspace_id)

    acessiveis = {
        str(cid) for (cid,) in (await db.execute(
            select(Credential.id).where(
                Credential.id.in_(uuid_ids),
                Credential.owner_id.isnot(None),
                or_(*escopo),
            )
        )).all()
    }

    recusadas = sorted(str(uid) for uid in uuid_ids if str(uid) not in acessiveis)
    if recusadas:
        logger.warning(
            "Usuário '%s' referenciou credencial(is) fora do seu escopo "
            "(dono, ou compartilhada com o workspace %r): %s",
            owner_id, shared_workspace_id, recusadas,
        )
        raise CredentialAccessDeniedError(
            "A definição referencia credenciais que não pertencem a você"
            + (" nem estão compartilhadas com o workspace informado" if shared_workspace_id else "")
            + f": {', '.join(recusadas)}."
        )


def credential_validity(expires_at_raw) -> str:
    """What the `expires_at` stored in the credential's `data` says about it:
    `"valida"` (still valid, or has no expiry), `"expirada"` (expired) or
    `"invalida"` (not a date — ignored for safety during resolution).

    It is the resolution rule (`_resolve_in_session`); validation uses it to
    warn BEFORE Run that the node's credential will not be resolved.
    """
    if not expires_at_raw:
        return "valida"
    try:
        expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
    except ValueError:
        return "invalida"
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return "expirada" if expires_at < datetime.now(timezone.utc) else "valida"


async def tipos_e_validades(db, credential_ids: Iterable[str]) -> dict:
    """`{id: (tipo, validade, expires_at)}` (type, validity) of the requested credentials — only the
    type and validity, never the decrypted `data`.

    So validation can say what resolution would do silently: leave out
    an expired credential, or one of a type the node does not accept. Call AFTER
    `assert_credentials_accessible` — there is no scope here.
    """
    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception:
            continue
    if not uuid_ids:
        return {}
    rows = (await db.execute(
        select(Credential.id, Credential.type, Credential.data).where(Credential.id.in_(uuid_ids))
    )).all()
    saida = {}
    for cid, tipo, data in rows:
        expires_at_raw = (data or {}).get("expires_at") if isinstance(data, dict) else None
        saida[str(cid)] = (tipo, credential_validity(expires_at_raw), expires_at_raw)
    return saida


async def _explain_missing(session, uuid_ids: List[UUID], resolvidos: set[str],
                           allowed: Collection[str],
                           shared_workspace_id: str | None = None) -> None:
    """Logs why each requested credential was not resolved.

    Without this the symptom reaches the operator as "the workflow stopped working".
    Queries only id/owner_id/workspace_id — never touches `data`.
    """
    faltando = [uid for uid in uuid_ids if str(uid) not in resolvidos]
    if not faltando:
        return

    rows = (await session.execute(
        select(Credential.id, Credential.owner_id, Credential.workspace_id)
        .where(Credential.id.in_(faltando))
    )).all()
    encontrados = {str(cid): (owner, ws) for cid, owner, ws in rows}

    for uid in faltando:
        cid = str(uid)
        if cid not in encontrados:
            logger.warning("Credencial %s não existe (ou foi removida).", cid)
            continue
        owner, ws = encontrados[cid]
        if owner is None:
            logger.warning(
                "Credencial %s não tem dono (owner_id nulo) e por isso não é resolvida. "
                "Atribua um dono: UPDATE credentials SET owner_id = '<user_id_hash>' WHERE id = '%s';",
                cid, cid,
            )
        elif owner not in allowed and not (shared_workspace_id and ws == shared_workspace_id):
            # Scope D: it does not belong to whoever triggered and is not shared with the
            # workflow's workspace. The way out is for the owner to share the credential
            # with the workspace (or for its owner to trigger).
            logger.warning(
                "Credencial %s pertence a '%s' e não está compartilhada com o workspace "
                "deste workflow — não resolvida. Compartilhe-a com o workspace ou execute "
                "como o dono dela.",
                cid, owner,
            )
        # Remainder: exists, in scope, but expired — already logged in the main loop.


async def resolve_credentials_from_ids(
    credential_ids: list[str],
    *,
    allowed_owner_ids: Collection[str] | None = None,
    shared_workspace_id: str | None = None,
    db=None,
) -> dict:
    """Resolves and decrypts credentials, restricted to the authorization scope.

    A credential is resolved when (requested id) AND (owner NOT null) AND
    (`owner_id ∈ allowed_owner_ids` OR `workspace_id == shared_workspace_id`):

    - `allowed_owner_ids` — authorized owners. In execution it is {whoever triggered}
      (see workflow_service); in simulation/validation, the user themselves.
    - `shared_workspace_id` — the workspace of the workflow being executed (or the one
      the validation provided). Matches credentials EXPLICITLY shared
      with it (workspace_id set), from any owner. It is what lets a
      trigger without a user (cron/webhook) reach the workspace's shared
      credentials.

    The two kwargs are the ENTIRE scope as soon as either of them is passed.
    Only in the absence of BOTH does the active `credential_scope` apply — which carries the
    same two dimensions (`CredentialScope`). There is no mixing: an explicit
    kwarg is never completed by the ContextVar, so that a call
    site's scope is always what is written in it.

    With NEITHER scope (no kwargs, no credential_scope) it raises
    `CredentialScopeMissing` — it never resolves "open". A null owner (orphan) never
    resolves, even if shared: fail-closed.

    `db` is the caller's session, when it already has one. Without this parameter this
    function opened ITS OWN session even when running inside the request — a
    nested wait for a connection from the SAME pool (8 + 5 per worker), with the first
    connection held while the second was awaited. From ~7 simultaneous
    triggers on the same worker the Run button hung on the
    30 s `pool_timeout`. Callers without a session (simulate/credential_scope)
    still fall back to `get_session_async()`.
    """
    if allowed_owner_ids is None and shared_workspace_id is None:
        # Only with NO scope kwarg at all does the ContextVar come in — and it comes in with
        # both dimensions at once.
        escopo = _scope.get()
        if escopo is None:
            raise CredentialScopeMissing(
                "resolve_credentials_from_ids exige allowed_owner_ids, shared_workspace_id "
                "ou um credential_scope ativo."
            )
        allowed = escopo.owner_ids
        shared_workspace_id = escopo.shared_workspace_id
    else:
        # Explicit kwargs are the ENTIRE scope: the ContextVar never completes the
        # missing dimension. Otherwise an `allowed_owner_ids` passed inside a
        # `credential_scope(..., shared_workspace_id=...)` would inherit the workspace
        # without the caller knowing — and vice versa.
        allowed = allowed_owner_ids

    # Converts strings to UUID objects — asyncpg does not auto-cast for UUID columns
    uuid_ids: List[UUID] = []
    for cid in credential_ids:
        try:
            uuid_ids.append(UUID(str(cid)))
        except Exception as exc:
            logger.warning("Falha ao converter credential_id '%s' para UUID: %s", cid, exc)
    if not uuid_ids:
        return {}

    allowed = list(allowed) if allowed is not None else []
    if not allowed and not shared_workspace_id:
        logger.warning(
            "Escopo de credenciais vazio — %d credencial(is) não serão resolvidas.",
            len(uuid_ids),
        )
        return {}

    if db is not None:
        # Request session: the caller is the one who commits. We don't commit here so we
        # don't accidentally write its pending work.
        return await _resolve_in_session(
            db, uuid_ids, allowed, shared_workspace_id=shared_workspace_id, own_session=False
        )

    async with get_session_async() as session:
        # Own session (simulate): get_session_async rolls back on exit,
        # so the last_used_at stamp only persists if we commit here.
        return await _resolve_in_session(
            session, uuid_ids, allowed, shared_workspace_id=shared_workspace_id, own_session=True
        )


async def _mark_last_used(session, usados: List[UUID], now, *, own_session: bool) -> None:
    """Stamps last_used_at on the credentials actually resolved — best-effort.

    Runs on the HOTTEST path (POST /execute). Safety rules:
    - Uses the SAME session already in hand (never opens a new connection — pool
      exhaustion is the reason the `db` parameter exists).
    - Never fatal: any failure here is swallowed and logged; the workflow
      execution must not fail because an audit stamp failed.
    - Only commits when the session is OURS; in the request's, the caller commits.
    """
    if not usados:
        return
    from sqlalchemy import update
    try:
        # SAVEPOINT (begin_nested) isolates the stamp's failure. Without it, an error in the
        # UPDATE (lock, statement_timeout, deadlock between two dispatches on the same
        # credential) would leave the request's SHARED transaction in
        # PendingRollback — and the following WorkflowRun commit would blow up,
        # bringing the dispatch down with a 500. Exactly the "never brings down the execution"
        # that this block promises. With the savepoint, the failure reverts only the nested
        # point; the caller's transaction stays intact and it commits normally.
        async with session.begin_nested():
            await session.execute(
                update(Credential).where(Credential.id.in_(usados)).values(last_used_at=now)
            )
        if own_session:
            await session.commit()
    except Exception as exc:  # best-effort — never brings down the execution
        logger.warning("Falha best-effort ao marcar last_used_at (%d cred): %s", len(usados), exc)
        # On the request path we do NOT touch the caller's transaction: the savepoint
        # already reverted what was ours. In our own session, we undo what we opened.
        if own_session:
            try:
                await session.rollback()
            except Exception:
                pass


async def _resolve_in_session(
    session, uuid_ids: List[UUID], allowed: list,
    *, shared_workspace_id: str | None = None, own_session: bool = False,
) -> dict:
    """Body of the resolution, with a session already in hand (own or the request's)."""
    from sqlalchemy import or_

    # Naive, in UTC: `Credential.last_used_at` is a `DateTime` WITHOUT timezone, and
    # asyncpg rejects a timezone-aware datetime for that column ("can't subtract
    # offset-naive and offset-aware datetimes"). The stamp's savepoint swallowed
    # the error, and on Postgres last_used_at was never written. Same helper as the
    # API token stamp (api_token_service).
    now = utc_now_naive()

    # Scope: authorized owner (whoever triggered) OR shared with the workflow's
    # workspace. `owner_id IS NOT NULL` is fail-closed: an orphan credential
    # never resolves, even if it matched through the workspace clause — the same
    # behavior the old `owner_id.in_(...)` had as a side effect (IN
    # never matches NULL), now explicit because the workspace clause could
    # reach a shared orphan.
    escopo = []
    if allowed:
        escopo.append(Credential.owner_id.in_(allowed))
    if shared_workspace_id:
        escopo.append(Credential.workspace_id == shared_workspace_id)
    if not escopo:
        # Guarded by the callers, but defensive: without a scope, resolves nothing.
        return {}

    result = await session.execute(
        select(Credential).where(
            Credential.id.in_(uuid_ids),
            Credential.owner_id.isnot(None),
            or_(*escopo),
        )
    )
    credentials = result.scalars().all()

    auth = {}
    usados: List[UUID] = []
    for cred in credentials:
        # Ignores expired credentials (expires_at is inside the JSONB data, not a column)
        expires_at_raw = (cred.data or {}).get("expires_at")
        validade = credential_validity(expires_at_raw)
        if validade == "expirada":
            logger.warning("Credencial %s expirada em %s — ignorada.", cred.id, expires_at_raw)
            continue
        if validade == "invalida":
            logger.warning(
                "Credencial %s com expires_at inválido: %r — ignorada por segurança.",
                cred.id, expires_at_raw,
            )
            continue
        # `decrypt_credential_data` returns a NEW dict: nothing is assigned
        # back to the ORM object, so running in the request session does not make the
        # next commit write a decrypted credential to the database.
        decrypted = decrypt_credential_data(cred.data)
        decrypted["type"] = cred.type
        auth[str(cred.id)] = decrypted
        usados.append(cred.id)

    await _explain_missing(session, uuid_ids, set(auth), allowed, shared_workspace_id)
    await _mark_last_used(session, usados, now, own_session=own_session)

    return auth
