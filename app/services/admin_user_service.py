# app/services/admin_user_service.py
"""Camada de serviço para gestão administrativa de usuários."""

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
    Lista usuários com filtros, busca, ordenação e paginação.
    Retorna (lista_de_usuarios, total_count).
    """
    # Query base
    query = select(User)
    count_query = select(func.count()).select_from(User)

    conditions = []

    # Filtro de busca (username ou email). O termo é literal: com `%`/`_` como
    # curinga, "___" listava qualquer conta.
    if search:
        conditions.append(or_(contem(User.username, search), contem(User.email, search)))

    # Filtro de status
    if status:
        conditions.append(User.status == status)

    # Filtro de role
    if role:
        conditions.append(User.role == role)

    # Filtro de intervalo de data de criação
    if date_from:
        conditions.append(User.created_at >= date_from)
    if date_to:
        conditions.append(User.created_at <= date_to)

    if conditions:
        combined = and_(*conditions)
        query = query.where(combined)
        count_query = count_query.where(combined)

    # Ordenação
    _sortable = {"username", "email", "created_at", "last_login_at", "status", "role"}
    col = getattr(User, sort_by) if sort_by in _sortable else User.created_at
    order_col = col.asc() if sort_order == "asc" else col.desc()
    query = query.order_by(order_col)

    # Paginação
    query = query.offset(offset).limit(limit)

    # Execução (duas queries — simples e eficiente)
    result = await db.execute(query)
    users = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return users, total


async def get_user(db: AsyncSession, id_hash: str) -> User | None:
    """Busca um usuário pelo id_hash."""
    result = await db.execute(select(User).where(User.id_hash == id_hash))
    return result.scalar_one_or_none()


async def get_users_by_ids(db: AsyncSession, ids: list[str]) -> dict[str, User]:
    """Carrega vários usuários numa unica query (id_hash -> User).

    Substitui o N+1 dos endpoints bulk, que faziam um get_user por id.
    """
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id_hash.in_(ids)))
    return {u.id_hash: u for u in result.scalars().all()}


async def _revogar_executores(db: AsyncSession, users: list[User], *, motivo: str) -> list:
    """Auditoria (SEG-16): os executores de cada conta caem junto, na transação
    de quem chama — senão seguiam conectados, recebendo jobs com código e
    credenciais e renovando o próprio cert. Status revogado, cert anulado e,
    depois do commit (`executor_service.concluir_revogacoes`), blacklist,
    `control: revoked` e a sessão derrubada.

    Os níveis da política ficam (`desanexar=False`): o executor pode estar no
    nível principal de workspaces de outros donos, e esvaziá-lo rebaixaria um
    workspace Isolado para o pool compartilhado — ver
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
    """Suspende varios usuarios ja validados, com UM unico commit."""
    if not users:
        return
    now = utc_now_naive()
    for user in users:
        user.status = "suspended"
        user.suspended_at = now
    # Cascata: conta suspensa não pode seguir agindo por um agente. Mesma
    # transação (o service NÃO commita — este commit abaixo fecha as duas).
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
    """Suspende um usuário ativo.

    `motivo` vinha da UI ("Motivo (opcional)"), era validado por
    `UserSuspendRequest` e descartado pela rota: o admin escrevia a
    justificativa, via "Usuário suspenso", e o texto sumia. Agora ele é
    registrado com o autor e o alvo.

    NOTA DE DESIGN, para quem for adiante: o destino natural disto é a tabela
    `audit_events`, que existe, está indexada e tem retenção de 90 dias
    documentada — mas o `workspace_id` dela é NOT NULL, e suspender um usuário é
    ação de PLATAFORMA, sem workspace. Escolher entre alargar a coluna ou
    carimbar um sentinela é decisão de produto, não de refatoração; até lá o
    registro fica no log estruturado, onde as demais ações de admin já são
    rastreadas.
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
    """Reativa um usuário suspenso."""
    user.status = "active"
    user.suspended_at = None
    await db.commit()
    await db.refresh(user)
    logger.info("Usuário '%s' reativado.", user.username)
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> User:
    """Marca um usuário como deletado (soft delete)."""
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
    """Altera o role de um usuário."""
    old_role = user.role
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    logger.info("Role do usuário '%s' alterado de '%s' para '%s'.", user.username, old_role, new_role)
    return user


async def update_agent_quota(db: AsyncSession, user: User, new_quota: int) -> User:
    """Altera a cota de executores dedicados que o usuário pode criar."""
    old_quota = user.agent_quota
    user.agent_quota = new_quota
    await db.commit()
    await db.refresh(user)
    logger.info("Cota de executores do usuário '%s' alterada de %s para %s.", user.username, old_quota, new_quota)
    return user
