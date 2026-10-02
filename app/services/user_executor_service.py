# app/services/user_executor_service.py
"""
Operações de negócio para vinculação de executores a usuários/workspaces.

Regras de acesso:
  - Executor default: acessível a todos automaticamente
  - Executor dedicated: acessível via workspace (Workspace.target_executor_id)
    ou via atribuição direta pelo admin (user_agent_assignments)
"""
from uuid import uuid4

from sqlalchemy import delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.executor import Executor
from app.models.user_executor_assignment import UserExecutorAssignment


async def get_default_agents(db: AsyncSession) -> list[Executor]:
    """Retorna todos os executores do pool padrão (is_default=true, status=active)."""
    result = await db.execute(
        select(Executor).where(
            Executor.is_default == True,  # noqa: E712
            Executor.status == "active",
            Executor.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def get_default_agent(db: AsyncSession) -> Executor | None:
    """Wrapper de compatibilidade — retorna o primeiro executor default ou None."""
    executores = await get_default_agents(db)
    return executores[0] if executores else None


async def get_user_accessible_agents(db: AsyncSession, user_id: str) -> list[dict]:
    """
    Retorna executores acessíveis ao usuário:
    1. Executor default (disponível para todos)
    2. Executores atribuídos a workspaces dos quais o usuário é owner ou membro
    """
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    # Executores do pool default
    default_agents = await get_default_agents(db)

    # Executores dos workspaces do usuário (owner + membro)
    ws_result = await db.execute(
        select(Workspace.target_executor_id).where(
            Workspace.target_executor_id.isnot(None),
            Workspace.deleted_at.is_(None),
            or_(
                Workspace.owner_id == user_id,
                Workspace.id_hash.in_(
                    select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
                ),
            ),
        )
    )
    ws_agent_ids = set(ws_result.scalars().all())

    # Membros de NÍVEL da política dos mesmos workspaces: quem entrou pelo
    # editor da política precisa aparecer aqui, senão o dono não vê nem
    # consegue remover um executor que roda os workflows dele.
    from app.services.workspace_executor_service import executor_ids_for_workspaces
    meus_ws = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.deleted_at.is_(None),
            or_(
                Workspace.owner_id == user_id,
                Workspace.id_hash.in_(
                    select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
                ),
            ),
        )
    )
    ws_agent_ids |= await executor_ids_for_workspaces(db, list(meus_ws.scalars().all()))

    # Buscar executores dos workspaces
    ws_agents: list[Executor] = []
    if ws_agent_ids:
        ag_result = await db.execute(
            select(Executor).where(
                Executor.id_hash.in_(ws_agent_ids),
                Executor.deleted_at.is_(None),
            )
        )
        ws_agents = list(ag_result.scalars().all())

    executores = []
    seen_ids: set[str] = set()

    for dag in default_agents:
        executores.append(_agent_to_dict(dag))
        seen_ids.add(dag.id_hash)

    for ag in ws_agents:
        if ag.id_hash not in seen_ids:
            executores.append(_agent_to_dict(ag))
            seen_ids.add(ag.id_hash)

    # Executores atribuídos diretamente ao usuário pelo admin
    from app.models.user_executor_assignment import UserExecutorAssignment

    assign_result = await db.execute(
        select(UserExecutorAssignment.executor_id).where(UserExecutorAssignment.user_id == user_id)
    )
    assigned_ids = set(assign_result.scalars().all()) - seen_ids
    if assigned_ids:
        ag_result = await db.execute(
            select(Executor).where(
                Executor.id_hash.in_(assigned_ids),
                Executor.deleted_at.is_(None),
            )
        )
        for ag in ag_result.scalars().all():
            executores.append(_agent_to_dict(ag))
            seen_ids.add(ag.id_hash)

    return executores


async def get_user_bindable_agents(db: AsyncSession, user_id: str) -> list[dict]:
    """Executores que o usuário pode VINCULAR a um workspace que administra.

    Diferente de `get_user_accessible_agents` (usada só para EXIBIR), esta é o
    critério de escrita e é mais estrita (auditoria SEG-13): um executor
    dedicado só entra se o usuário for DONO do workspace ao qual ele já está
    ligado — não basta ser admin por membresia. Sem isso, um viewer convidado a
    um workspace B (com executor dedicado X) via X aparecer como "acessível" e o
    vinculava ao próprio workspace A, rodando código na máquina de B.

    Inclui: pool padrão; executores criados pelo usuário; atribuídos a ele
    (UserExecutorAssignment); e executores de workspaces cujo `owner_id` é ele.
    """
    from app.models.workspace import Workspace
    from app.models.user_executor_assignment import UserExecutorAssignment
    from app.services.workspace_executor_service import executor_ids_for_workspaces

    default_agents = await get_default_agents(db)
    seen: set[str] = set()
    executores: list[dict] = []
    for dag in default_agents:
        executores.append(_agent_to_dict(dag))
        seen.add(dag.id_hash)

    ids: set[str] = set()
    # Criados pelo usuário.
    criados = await db.execute(
        select(Executor.id_hash).where(
            Executor.created_by == user_id, Executor.deleted_at.is_(None)
        )
    )
    ids |= set(criados.scalars().all())
    # Atribuídos diretamente pelo admin.
    atrib = await db.execute(
        select(UserExecutorAssignment.executor_id).where(UserExecutorAssignment.user_id == user_id)
    )
    ids |= set(atrib.scalars().all())
    # Executores de workspaces DE QUE O USUÁRIO É DONO (ponteiro legado + política).
    meus_ws = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.owner_id == user_id, Workspace.deleted_at.is_(None)
        )
    )
    meus_ws_ids = list(meus_ws.scalars().all())
    ptr = await db.execute(
        select(Workspace.target_executor_id).where(
            Workspace.owner_id == user_id,
            Workspace.deleted_at.is_(None),
            Workspace.target_executor_id.isnot(None),
        )
    )
    ids |= set(ptr.scalars().all())
    ids |= await executor_ids_for_workspaces(db, meus_ws_ids)

    ids -= seen
    if ids:
        ag_result = await db.execute(
            select(Executor).where(Executor.id_hash.in_(ids), Executor.deleted_at.is_(None))
        )
        for ag in ag_result.scalars().all():
            if ag.id_hash not in seen:
                executores.append(_agent_to_dict(ag))
                seen.add(ag.id_hash)
    return executores


async def set_default_agent(
    db: AsyncSession, executor_id: str, *, force: bool = False, actor_id: str | None = None,
) -> Executor:
    """Adiciona um executor ao pool padrão da plataforma.

    Operação inversa do Q3 da política de execução: um executor do pool não
    pode estar num nível dedicado, então ele é RETIRADO de todos os níveis —
    bloqueando (409) se isso esvaziaria o nível principal de algum workspace e
    `force` não foi pedido.
    """
    from app.services import workspace_executor_service as politica

    result = await db.execute(
        select(Executor).where(Executor.id_hash == executor_id, Executor.deleted_at.is_(None))
    )
    ag = result.scalar_one_or_none()
    if ag is None:
        raise ValueError("Executor não encontrado.")

    await politica.detach_executor(
        db, executor_id, force=force, actor_id=actor_id, reason="promoted_to_default",
    )
    ag.is_default = True
    ag.executor_type = "default"
    await db.commit()
    await db.refresh(ag)
    return ag


async def unset_default_agent(db: AsyncSession, executor_id: str) -> Executor:
    """Remove um executor do pool padrão, tornando-o dedicado."""
    result = await db.execute(
        select(Executor).where(Executor.id_hash == executor_id, Executor.deleted_at.is_(None))
    )
    ag = result.scalar_one_or_none()
    if ag is None:
        raise ValueError("Executor não encontrado.")

    ag.is_default = False
    ag.executor_type = "dedicated"
    await db.commit()
    await db.refresh(ag)
    return ag


async def get_agent_workspace_ids(db: AsyncSession, agent_id_hash: str, is_default: bool) -> list[str]:
    """
    Retorna workspace_ids que este executor pode acessar.
    - Default: todos os workspaces
    - Dedicated: workspaces que o apontam (ponteiro legado) OU que o têm em
      algum nível da política de execução — é para esses que o dispatch
      manda jobs, e o job precisa do Drive/artefatos do workspace.
    """
    from app.models.workspace import Workspace
    from app.services.workspace_executor_service import workspace_ids_for_executor

    if is_default:
        result = await db.execute(
            select(Workspace.id_hash).where(Workspace.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    return sorted(await workspace_ids_for_executor(db, agent_id_hash))


# ── CRUD de atribuições diretas (admin) ───────────────────────────────────────

async def list_agent_users(db: AsyncSession, executor_id: str) -> list[dict]:
    """Retorna usuários atribuídos diretamente ao executor pelo admin."""
    from app.models.user import User

    result = await db.execute(
        select(UserExecutorAssignment, User)
        .join(User, User.id_hash == UserExecutorAssignment.user_id)
        .where(UserExecutorAssignment.executor_id == executor_id)
        .order_by(UserExecutorAssignment.assigned_at)
    )
    return [
        {
            "user_id":     assignment.user_id,
            "username":    user.username,
            "email":       user.email,
            "assigned_at": assignment.assigned_at.isoformat(),
            "assigned_by": assignment.assigned_by,
        }
        for assignment, user in result.all()
    ]


async def assign_user_to_agent(
    db: AsyncSession,
    executor_id: str,
    user_id: str,
    assigned_by: str,
) -> UserExecutorAssignment:
    """
    Cria atribuição direta de executor a usuário.
    Lança ValueError se o executor não estiver ativo ou se a atribuição já existir.
    """
    from app.models.user import User

    ag = await db.execute(
        select(Executor).where(Executor.id_hash == executor_id, Executor.deleted_at.is_(None))
    )
    ag = ag.scalar_one_or_none()
    if ag is None:
        raise ValueError("Executor não encontrado.")
    if ag.status != "active":
        raise ValueError(f"Executor '{ag.name}' não está ativo (status: {ag.status}).")

    user_result = await db.execute(
        select(User).where(User.id_hash == user_id, User.deleted_at.is_(None))
    )
    if user_result.scalar_one_or_none() is None:
        raise ValueError("Usuário não encontrado.")

    existing = await db.execute(
        select(UserExecutorAssignment).where(
            UserExecutorAssignment.user_id == user_id,
            UserExecutorAssignment.executor_id == executor_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Executor já está atribuído a este usuário.")

    assignment = UserExecutorAssignment(
        id_hash=str(uuid4()),
        user_id=user_id,
        executor_id=executor_id,
        assigned_by=assigned_by,
    )
    db.add(assignment)
    await db.commit()
    return assignment


async def remove_user_from_agent(db: AsyncSession, executor_id: str, user_id: str) -> None:
    """
    Remove atribuição direta de executor a usuário.
    Lança ValueError se a atribuição não existir.
    """
    result = await db.execute(
        select(UserExecutorAssignment).where(
            UserExecutorAssignment.executor_id == executor_id,
            UserExecutorAssignment.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise ValueError("Atribuição não encontrada.")

    await db.execute(
        delete(UserExecutorAssignment).where(
            UserExecutorAssignment.executor_id == executor_id,
            UserExecutorAssignment.user_id == user_id,
        )
    )
    await db.commit()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _agent_to_dict(ag: Executor) -> dict:
    """Serializa Executor para resposta."""
    return {
        "id_hash": ag.id_hash,
        "name": ag.name,
        "description": ag.description,
        "status": ag.status,
        "executor_type": ag.executor_type,
        "is_default": ag.is_default,
        "capabilities": ag.capabilities or [],
        "max_concurrent_jobs": ag.max_concurrent_jobs,
        "max_queue_size": ag.max_queue_size,
        "executor_version": ag.executor_version,
        "last_seen_at": ag.last_seen_at.isoformat() if ag.last_seen_at else None,
        "created_at": ag.created_at.isoformat(),
        "created_by": ag.created_by,
    }
