# app/services/admin_user_service.py
"""Service layer for administrative user management."""

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils.busca import contem
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.user import User
from app.services import executor_service

logger = get_logger(__name__)


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[User], int]:
    """
    Lists users with filters, search, sorting and pagination.
    Returns (lista_de_usuarios, total_count).
    """
    # Query base
    query = select(User)
    count_query = select(func.count()).select_from(User)

    conditions = []

    # Search filter (username or email). The term is literal: with `%`/`_` as
    # wildcards, "___" listed any account.
    if search:
        conditions.append(or_(contem(User.username, search), contem(User.email, search)))

    # Status filter
    if status:
        conditions.append(User.status == status)

    # Role filter
    if role:
        conditions.append(User.role == role)

    # Creation date range filter
    if date_from:
        conditions.append(User.created_at >= date_from)
    if date_to:
        conditions.append(User.created_at <= date_to)

    if conditions:
        combined = and_(*conditions)
        query = query.where(combined)
        count_query = count_query.where(combined)

    # Sorting
    _sortable = {"username", "email", "created_at", "last_login_at", "status", "role"}
    col = getattr(User, sort_by) if sort_by in _sortable else User.created_at
    order_col = col.asc() if sort_order == "asc" else col.desc()
    query = query.order_by(order_col)

    # Pagination
    query = query.offset(offset).limit(limit)

    # Execution (two queries — simple and efficient)
    result = await db.execute(query)
    users = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return users, total


async def get_user(db: AsyncSession, id_hash: str) -> User | None:
    """Fetches a user by id_hash."""
    result = await db.execute(select(User).where(User.id_hash == id_hash))
    return result.scalar_one_or_none()


async def get_users_by_ids(db: AsyncSession, ids: list[str]) -> dict[str, User]:
    """Loads several users in a single query (id_hash -> User).

    Replaces the N+1 of the bulk endpoints, which did one get_user per id.
    """
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id_hash.in_(ids)))
    return {u.id_hash: u for u in result.scalars().all()}


async def _revogar_executores(db: AsyncSession, users: list[User], *, motivo: str) -> list:
    """Audit (SEG-16): each account's executors go down with it, in the caller's
    transaction — otherwise they stayed connected, receiving jobs with code and
    credentials and renewing their own cert. Status revoked, cert voided and,
    after the commit (`executor_service.concluir_revogacoes`), blacklist,
    `control: revoked` and the session dropped.

    The policy tiers stay (`desanexar=False`): the executor may be in the
    primary tier of workspaces of other owners, and emptying it would
    downgrade an Isolated workspace to the shared pool — see
    `executor_service.revogar_executores_do_usuario`."""
    revogados: list = []
    for user in users:
        revogados += await executor_service.revogar_executores_do_usuario(
            db, user, motivo=motivo, desanexar=False,
        )
    return revogados


async def bulk_suspend(
    db: AsyncSession, users: list[User], *, motivo: str | None = None, por: str | None = None,
) -> None:
    """Suspends several already-validated users, with ONE single commit."""
    if not users:
        return
    now = utc_now_naive()
    for user in users:
        user.status = "suspended"
        user.suspended_at = now
    # Cascade: a suspended account must not keep acting through an agent. Same
    # transaction (the service does NOT commit — the commit below closes both).
    from app.services.api_token_service import revogar_todos_do_usuario

    await revogar_todos_do_usuario(db, [u.id_hash for u in users], motivo="user_suspended")
    revogados = await _revogar_executores(db, users, motivo="user_suspended")
    await db.commit()
    await executor_service.concluir_revogacoes(revogados)
    logger.info(
        "%d usuario(s) suspenso(s) em lote por '%s'. Motivo: %s | alvos: %s",
        len(users), por or "?", motivo or "(nao informado)",
        ", ".join(u.username for u in users),
    )


async def bulk_reactivate(db: AsyncSession, users: list[User]) -> None:
    if not users:
        return
    for user in users:
        user.status = "active"
        user.suspended_at = None
    await db.commit()
    logger.info("%d usuario(s) reativado(s) em lote.", len(users))


async def bulk_soft_delete(db: AsyncSession, users: list[User]) -> None:
    if not users:
        return
    now = utc_now_naive()
    for user in users:
        user.status = "deleted"
        user.deleted_at = now
    from app.services.api_token_service import revogar_todos_do_usuario

    await revogar_todos_do_usuario(db, [u.id_hash for u in users], motivo="user_deleted")
    revogados = await _revogar_executores(db, users, motivo="user_deleted")
    await db.commit()
    await executor_service.concluir_revogacoes(revogados)
    logger.info("%d usuario(s) deletado(s) em lote.", len(users))


async def suspend_user(
    db: AsyncSession, user: User, *, motivo: str | None = None, por: str | None = None,
) -> User:
    """Suspends an active user.

    `motivo` came from the UI ("Motivo (opcional)", reason (optional)), was
    validated by `UserSuspendRequest` and discarded by the route: the admin
    wrote the justification, saw "Usuário suspenso" (user suspended), and the
    text vanished. Now it is recorded with the author and the target.

    DESIGN NOTE, for whoever takes this further: the natural destination for
    this is the `audit_events` table, which exists, is indexed and has a
    documented 90-day retention — but its `workspace_id` is NOT NULL, and
    suspending a user is a PLATFORM action, with no workspace. Choosing between
    widening the column or stamping a sentinel is a product decision, not a
    refactoring one; until then the record stays in the structured log, where
    the other admin actions are already tracked.
    """
    user.status = "suspended"
    user.suspended_at = utc_now_naive()
    from app.services.api_token_service import revogar_todos_do_usuario

    await revogar_todos_do_usuario(db, [user.id_hash], motivo="user_suspended")
    revogados = await _revogar_executores(db, [user], motivo="user_suspended")
    await db.commit()
    await executor_service.concluir_revogacoes(revogados)
    await db.refresh(user)
    logger.info(
        "Usuário '%s' suspenso por '%s' (executores revogados: %d). Motivo: %s",
        user.username, por or "?", len(revogados), motivo or "(nao informado)",
    )
    return user


async def reactivate_user(db: AsyncSession, user: User) -> User:
    """Reactivates a suspended user."""
    user.status = "active"
    user.suspended_at = None
    await db.commit()
    await db.refresh(user)
    logger.info("Usuário '%s' reativado.", user.username)
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> User:
    """Marks a user as deleted (soft delete)."""
    user.status = "deleted"
    user.deleted_at = utc_now_naive()
    from app.services.api_token_service import revogar_todos_do_usuario

    await revogar_todos_do_usuario(db, [user.id_hash], motivo="user_deleted")
    revogados = await _revogar_executores(db, [user], motivo="user_deleted")
    await db.commit()
    await executor_service.concluir_revogacoes(revogados)
    await db.refresh(user)
    logger.info(
        "Usuário '%s' marcado como deletado (executores revogados: %d).",
        user.username, len(revogados),
    )
    return user


async def update_role(db: AsyncSession, user: User, new_role: str) -> User:
    """Changes a user's role."""
    old_role = user.role
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    logger.info("Role do usuário '%s' alterado de '%s' para '%s'.", user.username, old_role, new_role)
    return user


async def update_agent_quota(db: AsyncSession, user: User, new_quota: int) -> User:
    """Changes the quota of dedicated executors the user can create."""
    old_quota = user.agent_quota
    user.agent_quota = new_quota
    await db.commit()
    await db.refresh(user)
    logger.info("Cota de executores do usuário '%s' alterada de %s para %s.", user.username, old_quota, new_quota)
    return user
