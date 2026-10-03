# app/services/executor_service.py
"""
Business operations for Executors:
  - Creation (admin) — only records metadata; the credential comes via enrollment OTP + mTLS cert.
  - Basic CRUD + revocation (`revogar_executor` + `complete_revocations`, the
    single version for every path that revokes).

Executor authentication is now done entirely via mTLS — the static API key
was removed and the intermediate WebSocket JWT eliminated. See
app/services/executor_enrollment_service.py for the bootstrap flow and
app/api/routers/executor_ws_router.py for WS auth by cert.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.executor_connections import executor_registry
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.crud.executor_crud import ExecutorCRUD
from app.models.executor import Executor
from app.models.user_executor_assignment import UserExecutorAssignment
from app.services import workspace_executor_service as politica

logger = get_logger(__name__)


class ExecutorQuotaError(Exception):
    """User without permission or who has reached their dedicated executor quota."""

    def __init__(self, message: str, *, status_code: int):
        super().__init__(message)
        self.status_code = status_code


# ── Service operations ────────────────────────────────────────────────────────


async def create_executor(
    db: AsyncSession,
    name: str,
    created_by: str,
    description: str | None = None,
    capabilities: list[str] | None = None,
    max_concurrent_jobs: int = 4,
    max_queue_size: int = 50,
    executor_type: str = "dedicated",
    is_default: bool = False,
    commit: bool = True,
) -> Executor:
    """
    Creates a new executor in 'pending' status.

    After creation, the admin needs to generate an enrollment OTP (see
    executor_enrollment_service.create_enrollment_otp) and hand it to the operator.
    The executor exchanges the OTP for an mTLS cert via POST /executores/enroll.

    commit=False leaves the transaction open (only a flush to populate id_hash),
    letting the caller group related inserts into a single commit.
    """
    if executor_type not in ("default", "dedicated"):
        raise ValueError("executor_type deve ser 'default' ou 'dedicated'.")

    if is_default or executor_type == "default":
        is_default = True
        executor_type = "default"

    ag = Executor(
        name=name,
        description=description,
        created_by=created_by,
        capabilities=capabilities or [],
        max_concurrent_jobs=max_concurrent_jobs,
        max_queue_size=max_queue_size,
        executor_type=executor_type,
        is_default=is_default,
        status="pending",
    )
    db.add(ag)
    if commit:
        await db.commit()
        await db.refresh(ag)
    else:
        await db.flush()  # popula id_hash e demais defaults sem encerrar a transacao
    return ag


async def count_user_created_executors(db: AsyncSession, user_id: str) -> int:
    """
    Counts the user's executors (created_by) that still occupy a quota slot.

    Ignores revoked and soft-deleted ones — executors in those states are "dead
    for all purposes" and must not block the user from creating a new one
    when the admin restores the quota.
    """
    result = await db.execute(
        select(func.count())
        .select_from(Executor)
        .where(
            Executor.created_by == user_id,
            Executor.deleted_at.is_(None),
            Executor.status != "revoked",
        )
    )
    return int(result.scalar_one())


async def create_dedicated_for_user(
    db: AsyncSession,
    user,
    name: str,
    description: str | None = None,
    capabilities: list[str] | None = None,
    max_concurrent_jobs: int = 4,
    max_queue_size: int = 50,
) -> Executor:
    """
    Creates a dedicated executor on behalf of a regular user (self-service).

    Validates the individual quota (User.agent_quota) — 0 blocks, and the number of
    the user's own non-deleted executors cannot reach the quota. Forces the dedicated
    type and creates the direct assignment (UserExecutorAssignment) to give the
    creator visibility in /executores/my. Raises ExecutorQuotaError (403/409) when blocked.
    """
    quota = user.agent_quota or 0
    if quota <= 0:
        raise ExecutorQuotaError(
            "Você não tem permissão para criar executores.", status_code=403
        )

    current = await count_user_created_executors(db, user.id_hash)
    if current >= quota:
        raise ExecutorQuotaError(
            f"Limite de executores atingido ({current}/{quota}).", status_code=409
        )

    # commit=False: executor + assignment go into a single commit (atomic creation).
    # Without this, a failure writing the assignment would leave an orphan executor using quota.
    ag = await create_executor(
        db,
        name=name,
        created_by=user.id_hash,
        description=description,
        capabilities=capabilities,
        max_concurrent_jobs=max_concurrent_jobs,
        max_queue_size=max_queue_size,
        executor_type="dedicated",
        is_default=False,
        commit=False,
    )

    db.add(UserExecutorAssignment(
        user_id=user.id_hash,
        executor_id=ag.id_hash,
        assigned_by=user.id_hash,
    ))
    await db.commit()
    await db.refresh(ag)
    return ag


async def update_agent(db: AsyncSession, executor_id: str, data: dict) -> Executor:
    """
    Updates an executor's name and/or description.
    Raises ValueError if the executor is not found, deleted or revoked.
    """
    ag = await get_agent(db, executor_id)
    if ag is None:
        raise ValueError(f"Executor '{executor_id}' nao encontrado.")
    if ag.status == "revoked":
        raise ValueError("Executor revogado nao pode ser editado.")
    for field in ("name", "description"):
        if field in data and data[field] is not None:
            setattr(ag, field, data[field])
    await db.commit()
    await db.refresh(ag)
    return ag


async def get_agent(db: AsyncSession, executor_id: str, include_deleted: bool = False) -> Executor | None:
    """Fetches an executor by id_hash. By default, ignores deleted executors."""
    return await ExecutorCRUD(db).get(executor_id, include_deleted=include_deleted)


async def list_agents(db: AsyncSession) -> list[Executor]:
    """Lists active (non-deleted) executors."""
    return await ExecutorCRUD(db).list()


async def delete_agent(db: AsyncSession, executor_id: str) -> Executor:
    """
    Soft-delete of an executor — only allowed when status='revoked'.

    Fills deleted_at with the current date/time; the executor stops appearing
    in listings but stays in the database to preserve the execution history.
    """
    ag = await ExecutorCRUD(db).get_any(executor_id)
    if ag is None:
        raise ValueError(f"Executor '{executor_id}' nao encontrado.")
    if ag.status != "revoked":
        raise ValueError("Apenas executores revogados podem ser removidos.")
    ag.deleted_at = utc_now_naive()
    await db.commit()
    await db.refresh(ag)
    return ag


# ── Revocation ────────────────────────────────────────────────────────────────
#
# A single one, for the four paths that revoke: the executor DELETE, the operator's
# "revoke all", account suspension/deletion and (cert only) the certificate
# revocation. Each one copied the steps by hand, and the copies diverged: the
# suspension did not take the executor out of the policy tiers nor drop the open
# session, and "revoke all" notified the owners with the id instead of the name.


@dataclass
class Revocation:
    """An executor revoked in the caller's session, with what can only leave the
    database after the commit — see `complete_revocations`."""

    executor_id: str
    nome: str
    # The cert that was just voided, for the blacklist.
    serial: str | None
    serial_expira_em: datetime | None
    # What the executor hears: the reason in the `control` and in the WS close.
    aviso: str
    fechamento: str
    # Workspaces that had the executor in a tier (the return of `detach_executor`).
    afetados: Sequence[dict] = ()


async def revogar_executor(
    db: AsyncSession,
    ag: Executor,
    *,
    force: bool,
    actor_id: str | None,
    motivo: str,
    aviso: str,
    fechamento: str,
    desanexar: bool = True,
) -> Revocation:
    """Revokes `ag` in the caller's transaction — does NOT commit.

    1. With `desanexar` (the executor DELETE and the operator's "revoke all"),
       takes the executor out of every policy tier, with the audit
       (`detach_executor`; `WorkspacePolicyConflictError` if it would empty
       someone's primary tier and `force` was not requested; when forced, the
       owners are notified). Without `desanexar` (account suspension and deletion — see
       `revogar_executores_do_usuario`), the executor stays in the tiers.
    2. Status `revoked` and cert voided — if it comes back, only with a new enrollment.

    Blacklist, owner notification and the WebSocket close are not database work and
    only apply after the commit: the caller runs `complete_revocations` with what this
    function returns. Notifying earlier would act on a revocation that a rollback
    can still undo — and the 4403 close is terminal for the executor.
    """
    afetados = await politica.detach_executor(
        db, ag.id_hash, force=force, actor_id=actor_id, reason=motivo,
    ) if desanexar else []
    revogacao = Revocation(
        executor_id=ag.id_hash, nome=ag.name, serial=ag.cert_serial,
        serial_expira_em=ag.cert_expires_at, aviso=aviso, fechamento=fechamento,
        afetados=afetados,
    )
    ag.status = "revoked"
    ag.cert_serial = None
    return revogacao


async def revogar_executores_do_usuario(
    db: AsyncSession, usuario, *, motivo: str, desanexar: bool,
    actor_id: str | None = None,
) -> list[Revocation]:
    """Revokes every executor created by `usuario` that is not yet
    revoked — the operator's "revoke all" and account suspension/deletion
    (audit SEG-16: without this the executor of a suspended account stayed
    connected, receiving jobs with code and credentials in the clear and renewing
    its own cert).

    Pending ones are included: a suspended account does not leave an executor waiting
    for enrollment (whoever has the OTP would still enroll it). Does NOT commit, like
    `revogar_executor`.

    `desanexar` is the caller's choice, and both choices are deliberate:

    - "revoke all" (`True`, forced): an explicit operator action on the
      executors, the same as the DELETE — leaves the tiers, and an emptied
      primary tier becomes a notice to the owner.
    - account suspension/deletion (`False`): the executor STAYS in the tiers of the
      workspaces — often other owners' —, as the spec requires
      (docs/specs/executor-isolation-routing.md §4.4: an out-of-service executor
      stays in the tier and merely stops being eligible). Dispatch skips it and follows
      the chain (fallback or fail closed). Removing it by force emptied the primary
      tier: the Isolated workspace became a shared pool (jobs with
      credentials going to the common fleet) and the owner's configuration was lost
      for good, even with the account reactivated later.
    """
    result = await db.execute(
        select(Executor).where(
            Executor.created_by == usuario.id_hash,
            Executor.deleted_at.is_(None),
            Executor.status != "revoked",
        )
    )
    return [
        await revogar_executor(
            db, ag, force=True, actor_id=actor_id, motivo=motivo,
            aviso=f"Acesso do operador '{usuario.username}' revogado pelo admin.",
            fechamento="Operador revogado.", desanexar=desanexar,
        )
        for ag in result.scalars().all()
    ]


def notify_owners_of_emptied_tiers(afetados: Sequence[dict], *, executor_name: str) -> None:
    """A removal that emptied someone's primary tier: email to the owner
    (best-effort, in the background, with its own session — the request's closes
    along with the response). Without this the workspace would find out from the 503."""
    from app.services.execution_alert_service import notify_primary_emptied_background

    emptied = [d for d in afetados if d.get("would_empty_primary")]
    notify_primary_emptied_background(emptied, executor_name=executor_name)


async def complete_revocations(revocations: Iterable[Revocation]) -> None:
    """What revocation does outside the database, AFTER the caller's commit.

    All best-effort and isolated per executor — the revocation already holds in the
    database, and the session watcher (`_watch_revocation`) drops the WebSocket even
    if the close from here gets lost:

    - cert blacklist in Redis (defense in depth beyond the CRL);
    - email to the owners of workspaces whose primary tier was emptied;
    - `control: revoked` (the reason, for the operator to read) and close 4403 — it is
      the close that makes the executor stop, even one that ignores the control. Both
      are relayed through Redis when the WebSocket is on another worker: without the
      relay, an admin who landed on a worker without the WS revoked only the database.
    """
    from app.services import executor_enrollment_service

    for r in revocations:
        if r.serial:
            try:
                await executor_enrollment_service.revoke_cert(r.serial, cert_expires_at=r.serial_expira_em)
            except Exception as exc:
                logger.warning(
                    "Falha ao marcar cert '%s' (executor %s) como revogado no Redis: %s",
                    r.serial, r.executor_id, exc,
                )
        notify_owners_of_emptied_tiers(r.afetados, executor_name=r.nome)
        try:
            await executor_registry.send_json(r.executor_id, {
                "type": "control", "action": "revoked", "reason": r.aviso,
            })
        except Exception as exc:
            logger.warning("Falha ao notificar executor '%s' sobre a revogação: %s", r.executor_id, exc)
        try:
            await executor_registry.disconnect_executor(r.executor_id, code=4403, reason=r.fechamento)
        except Exception as exc:
            logger.warning("Falha ao desconectar executor '%s' revogado: %s", r.executor_id, exc)


async def update_agent_last_seen(db: AsyncSession, executor_id: str):
    """Updates last_seen_at — called at the start of each WebSocket session."""
    await ExecutorCRUD(db).touch_last_seen(executor_id)


async def motivo_da_revogacao(db: AsyncSession, executor_id: str) -> str | None:
    """Why an already-open WebSocket session stopped being valid; None if it is valid.

    Mirrors what mTLS requires on connection (`validate_executor_mtls`): an
    existing executor, not removed, active and with a cert. Cert revocation zeroes
    `cert_serial`; executor revocation (and the operator's, which revokes their
    executors) changes the status. Renewal swaps the serial without zeroing it — it
    does not drop the session that performed it."""
    linha = (await db.execute(
        select(Executor.status, Executor.cert_serial, Executor.deleted_at)
        .where(Executor.id_hash == executor_id)
    )).one_or_none()
    if linha is None or linha.deleted_at is not None:
        return "Executor removido."
    if linha.status != "active":
        return "Executor revogado."
    if not linha.cert_serial:
        return "Cert revogado."
    return None


async def registrar_fim_da_sessao(db: AsyncSession, executor_id: str, seen_at) -> None:
    """End of a WebSocket session: `last_seen_at` becomes its last contact —
    if later than what is in the database. The end of a replaced session
    arrives after the new one's handshake (seconds, up to ~100 s when the
    takeover notice gets lost) and, written unconditionally, erased the start of
    the new one: the "no ar desde" (online since) that the other workers read from here."""
    await ExecutorCRUD(db).touch_last_seen_if_later(executor_id, seen_at)
