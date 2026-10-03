# app/api/routers/workspace_router.py
"""
Workspace CRUD — multi-tenant isolation of workflows.
Includes member management (multi-user workspaces).
"""
from app.core.utils.logger import get_logger
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db, get_current_user,
    get_workspace_member_role, exigir_papel_no_workspace,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.core import config
from app.core.rbac import ROLE_ADMIN
from app.core.utils.datetime_utils import utc_now_naive
from app.schemas.workspace import WorkspaceOut  # noqa: F401 — re-exportado: o schema mora em app/schemas
from app.services import email_transporte
from app.services.workspace_service import listar_workspaces_do_usuario

logger = get_logger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    owner_id: Optional[str] = None


class MemberOut(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    joined_at: str

    class Config:
        from_attributes = True


class MemberInvite(BaseModel):
    email: str = Field(..., description="E-mail do usuário a convidar")
    role: str  = Field("editor", description="viewer | editor | operator | admin")


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., description="viewer | editor | operator | admin")


class UserSearchOut(BaseModel):
    id_hash: str
    username: str
    email: str

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────────────────────

_VALID_ROLES = {"viewer", "editor", "operator", "admin"}


async def _get_owned_workspace(id_hash: str, db: AsyncSession, current_user: User) -> Workspace:
    """Returns a live workspace owned by the user (owner), or raises 403/404.

    A workspace in the trash is invisible here — restoring and purging are admin
    actions, in /admin/workspaces.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")
    if ws.owner_id != current_user.id_hash:
        raise HTTPException(status_code=403, detail="Apenas o dono pode gerenciar este workspace.")
    return ws


async def _get_admin_managed_workspace(id_hash: str, db: AsyncSession, current_user: User) -> Workspace:
    """Accepts the owner OR a member with the admin role — to invite/remove members and set the executor."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")
    await exigir_papel_no_workspace(
        db, id_hash, current_user.id_hash, ROLE_ADMIN,
        "Requer role 'admin' ou superior neste workspace.",
    )
    return ws


async def _get_visible_workspace(
    id_hash: str, db: AsyncSession, current_user: User,
) -> tuple[Workspace, str]:
    """Live workspace + the user's effective role. 404 if it does not exist, 403 if not a member.

    Returns the entity, and not a `WorkspaceOut`, because whoever lists members needs
    `Workspace.owner_id` and `Workspace.created_at` to build the owner's row —
    which does not exist in `workspace_members`.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    role = await get_workspace_member_role(db, id_hash, current_user.id_hash)
    if role is None:
        raise HTTPException(status_code=403, detail="Acesso negado a este workspace.")
    return ws, role


# ── Workspace CRUD ─────────────────────────────────────────────────────────────

@router.post("", response_model=WorkspaceOut, status_code=201, summary="Criar workspace")
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = Workspace(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id_hash,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    logger.info("Workspace criado: id=%s name=%s owner=%s", ws.id_hash, ws.name, current_user.id_hash)
    return ws


@router.get("", response_model=List[WorkspaceOut], summary="Listar workspaces do usuário autenticado")
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns workspaces created by the user + workspaces they are a member of."""
    return await listar_workspaces_do_usuario(db, current_user.id_hash)


@router.put("/{id_hash}", response_model=WorkspaceOut, summary="Atualizar workspace")
async def update_workspace(
    id_hash: str,
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_owned_workspace(id_hash, db, current_user)
    ws.name = payload.name
    if payload.description is not None:
        ws.description = payload.description
    await db.commit()
    await db.refresh(ws)
    return ws


@router.delete("/{id_hash}", status_code=204, summary="Remover workspace (soft delete)")
async def delete_workspace(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Moves the workspace to the trash — the row remains, with `deleted_at`.

    The workflows go down with it (soft delete + schedules deactivated). Restoring and
    discarding permanently are admin actions, in /admin/workspaces — the owner
    deletes, but does not undo.
    """
    ws = await _get_owned_workspace(id_hash, db, current_user)
    if ws.is_default:
        raise HTTPException(status_code=403, detail="O workspace padrão não pode ser removido.")

    deleted_at = utc_now_naive()

    # ORDER MATTERS. `schedule_workspace_data_expiry` does an internal commit
    # (via purge_workspace_storage), so everything that has to go down together must
    # be dirty in the session BEFORE it. Marking the workspace last opened a
    # window in which the workflows were already soft-deleted and the workspace still
    # alive — a state that does not show up in the trash (the filter is deleted_at IS NOT
    # NULL) and that, therefore, neither the owner nor the admin can undo through the UI.
    ws.deleted_at = deleted_at

    # Deactivates the workflows along with it. A workflow whose workspace vanished keeps
    # being triggered by the AsyncScheduler (which filters only by Schedule.active) —
    # invisible in the UI, running on the default pool instead of the workspace's executor and
    # without the webhook allowlist. No workflow survives the deletion of its
    # workspace.
    #
    # The timestamp is shared with Workspace.deleted_at: it is the mark the
    # restore uses to know which workflows went down because of this delete.
    from app.services.workflow_service import soft_delete_workspace_workflows
    cascaded = await soft_delete_workspace_workflows(db, id_hash, deleted_at)

    # Storage follows the immediate-expiration policy: artifacts get
    # expires_at=now (removed on the next pass of purge_expired_artifacts,
    # which handles MinIO, PortalLayer and S3 retry) and Drive files, which have
    # no expiration column, go right away. A restore brings back the workflows,
    # NOT the files already purged.
    #
    # It is here that the transaction above is committed, in the helper's internal commit.
    from app.services.storage_purge_service import schedule_workspace_data_expiry
    scheduled = await schedule_workspace_data_expiry(db, id_hash)

    await db.commit()
    logger.info(
        "Workspace movido para a lixeira: id=%s owner=%s (desativados: %d workflow(s), "
        "%d schedule(s); agendados p/ remoção: %d artefato(s), %d arquivo(s) do Drive)",
        id_hash, current_user.id_hash, cascaded["workflows"], cascaded["schedules"],
        scheduled["artifacts"], scheduled["drive_files"],
    )


# ── Membros ────────────────────────────────────────────────────────────────────

def _build_member_list(
    owner_id: Optional[str],
    owner_user: Optional[User],
    ws_created_at,
    member_rows: List[tuple],
) -> List[MemberOut]:
    """Builds the member list with the owner first.

    The owner does NOT have a row in `workspace_members` — `create_workspace` never
    creates one. Before this, whoever created the workspace simply did not appear in
    their own member list, and an invited admin had no way to find out whom to talk to.
    The owner's row is synthetic: role "owner" (which is not in `_VALID_ROLES`, so
    it is not assignable) and `joined_at` = the workspace's creation, which is literally
    when they joined.

    If the owner ALSO has a row in `workspace_members` — possible in old
    data, since until now nothing prevented inviting the owner themselves by e-mail — the
    synthetic row wins and the real one is discarded. Without this they would appear twice,
    with two different roles.
    """
    members: List[MemberOut] = []

    # `owner_id` is nullable and the user may have been removed from the platform;
    # in both cases the list comes out with only the members, without an empty row.
    if owner_id and owner_user is not None:
        members.append(MemberOut(
            user_id=owner_id,
            username=owner_user.username,
            email=owner_user.email,
            role="owner",
            joined_at=ws_created_at.isoformat(),
        ))

    for member, user in member_rows:
        if owner_id and member.user_id == owner_id:
            continue
        members.append(MemberOut(
            user_id=member.user_id,
            username=user.username,
            email=user.email,
            role=member.role,
            joined_at=member.joined_at.isoformat(),
        ))

    return members


@router.get("/{id_hash}/members", response_model=List[MemberOut], summary="Listar membros do workspace")
async def list_members(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws, _ = await _get_visible_workspace(id_hash, db, current_user)

    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id_hash == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == id_hash)
        .order_by(WorkspaceMember.joined_at)
    )
    rows = result.all()

    owner_user = None
    if ws.owner_id:
        owner_result = await db.execute(select(User).where(User.id_hash == ws.owner_id))
        owner_user = owner_result.scalar_one_or_none()

    return _build_member_list(ws.owner_id, owner_user, ws.created_at, rows)


def _conferir_email_do_convidado(user: User, workspace_id: str) -> None:
    """The invitation is by e-mail: it is only valid if the e-mail belongs to the account holder.

    With EXIGIR_EMAIL_VERIFICADO (the default), an account without a verified e-mail does
    not even get in, and the invitation waits for verification. Without the requirement,
    open sign-up lets anyone create an account with another person's e-mail — and the
    invitation would hand the workspace to whoever signed up first. If there is a transport,
    the person can verify (the link arrives), so the invitation waits for that.
    Without a transport, nothing in the installation proves the e-mail: the invitation goes
    through, and the warning stays in the log (the risk is described in .env.example).
    """
    if user.email_verified or config.EXIGIR_EMAIL_VERIFICADO:
        return
    if email_transporte.ativo():
        raise HTTPException(
            status_code=409,
            detail=(
                "Essa conta ainda não confirmou o e-mail. Convide de novo depois que a "
                "pessoa confirmar (o link de verificação pode ser reenviado no login)."
            ),
        )
    logger.warning(
        "Convite para conta sem e-mail verificado numa instalação sem transporte de "
        "e-mail: workspace=%s user=%s. Confira com a pessoa se a conta é dela.",
        workspace_id, user.id_hash,
    )


@router.post("/{id_hash}/members", response_model=MemberOut, status_code=201, summary="Convidar membro por e-mail")
async def invite_member(
    id_hash: str,
    payload: MemberInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The workspace admin or owner can invite members."""
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)

    if payload.role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role inválido. Opções: {sorted(_VALID_ROLES)}")

    # Look up the user by e-mail
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário com e-mail '{payload.email}' não encontrado.")
    # Compare against the owner, not against the inviter: an admin inviting the owner
    # created a duplicate row in `workspace_members` — and the old message
    # ("Você já é o dono deste workspace") on top of that accused the wrong person.
    if ws.owner_id and user.id_hash == ws.owner_id:
        raise HTTPException(status_code=400, detail="Este usuário já é o dono do workspace.")
    _conferir_email_do_convidado(user, id_hash)

    # Check whether already a member
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == id_hash,
            WorkspaceMember.user_id == user.id_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Usuário já é membro deste workspace.")

    member = WorkspaceMember(
        workspace_id=id_hash,
        user_id=user.id_hash,
        role=payload.role,
        invited_by=current_user.id_hash,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    logger.info("Membro adicionado ao workspace: workspace=%s user=%s role=%s", id_hash, user.id_hash, payload.role)

    # Extract attributes from the ORM before leaving the session (avoids DetachedInstanceError)
    invited_email = user.email
    invited_username = user.username
    ws_name = ws.name
    inviter_name = current_user.username

    # Notifica o convidado por email (fire-and-forget)
    from app.services.email_service import send_email_background
    from app.core.config import FRONTEND_URL
    send_email_background(
        to=invited_email,
        subject=f"Você foi adicionado ao workspace {ws_name}",
        template="workspace_invite.html",
        context={
            "username": invited_username,
            "workspace_name": ws_name,
            "role": payload.role,
            "invited_by": inviter_name,
            "app_url": FRONTEND_URL,
        },
    )

    return MemberOut(
        user_id=user.id_hash,
        username=user.username,
        email=user.email,
        role=member.role,
        joined_at=member.joined_at.isoformat(),
    )


@router.put("/{id_hash}/members/{user_id}", response_model=MemberOut, summary="Alterar role de um membro")
async def update_member_role(
    id_hash: str,
    user_id: str,
    payload: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)

    if payload.role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role inválido. Opções: {sorted(_VALID_ROLES)}")

    # The owner now appears in the member list, so the UI offers their row
    # like any other. Without this guard the PUT would fall into the generic 404 below
    # ("Membro não encontrado"), which explains nothing.
    if ws.owner_id and user_id == ws.owner_id:
        raise HTTPException(status_code=400, detail="O role do dono não pode ser alterado.")

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == id_hash,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado neste workspace.")

    member.role = payload.role
    await db.commit()
    await db.refresh(member)

    user_result = await db.execute(select(User).where(User.id_hash == user_id))
    user = user_result.scalar_one_or_none()

    return MemberOut(
        user_id=user.id_hash,
        username=user.username,
        email=user.email,
        role=member.role,
        joined_at=member.joined_at.isoformat(),
    )


@router.delete("/{id_hash}/members/{user_id}", status_code=204, summary="Remover membro do workspace")
async def remove_member(
    id_hash: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/owner can remove any member. Members can leave on their own."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    # One guard, two cases: an admin trying to remove the owner (who now appears in the
    # list) and the owner themselves trying to "leave". Neither can happen — the
    # owner has no row in `workspace_members`, so without this both would fall into a
    # 404 that looks like a bug. Leaving one's own workspace does not exist: deleting it does.
    if ws.owner_id and user_id == ws.owner_id:
        raise HTTPException(
            status_code=400,
            detail="O dono não pode sair do próprio workspace. Exclua o workspace em vez disso.",
        )

    # The user can leave on their own; admin+ can remove other members
    if user_id != current_user.id_hash:
        await exigir_papel_no_workspace(
            db, id_hash, current_user.id_hash, ROLE_ADMIN,
            "Requer role 'admin' ou superior para remover membros.",
        )

    member_result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == id_hash,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")

    await db.delete(member)
    # Audit (SEG-98): the credentials the former member shared WITH THIS
    # workspace stop being valid here — otherwise they kept being resolved at
    # dispatch for those who stayed, even though their owner no longer had access to the workspace.
    from app.models.credential import Credential
    from sqlalchemy import update as _sa_update
    desvinc = await db.execute(
        _sa_update(Credential)
        .where(Credential.owner_id == user_id, Credential.workspace_id == id_hash)
        .values(workspace_id=None)
    )
    await db.commit()
    logger.info(
        "Membro removido do workspace: workspace=%s user=%s credenciais_desvinculadas=%s",
        id_hash, user_id, getattr(desvinc, "rowcount", "?"),
    )


# ── Workspace executor ───────────────────────────────────────────────────────────

class WorkspaceAgentUpdate(BaseModel):
    target_executor_id: str | None = Field(None, description="id_hash do executor (null para usar o default)")


@router.put("/{id_hash}/executor", summary="Definir executor do workspace")
async def set_workspace_agent(
    id_hash: str,
    payload: WorkspaceAgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sets which executor will be used to run this workspace's workflows.
    Workflows without a specific override will inherit this executor.
    """
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)

    # Validate that the executor exists and is active
    if payload.target_executor_id:
        from app.models.executor import Executor
        ag_result = await db.execute(
            select(Executor).where(
                Executor.id_hash == payload.target_executor_id,
                Executor.deleted_at.is_(None),
            )
        )
        ag = ag_result.scalar_one_or_none()
        if ag is None:
            raise HTTPException(status_code=404, detail="Executor não encontrado.")
        if ag.status != "active":
            raise HTTPException(status_code=400, detail=f"Executor '{ag.name}' não está ativo (status: {ag.status}).")

        # A non-global-admin can only link executors they have access to (default pool,
        # direct assignment or an executor of another of their workspaces). Prevents pointing the
        # workspace at another user's dedicated executor — which would make the job
        # (with injected credentials) be decrypted on someone else's host.
        if current_user.role != "admin":
            # Audit SEG-13: uses the LINKABLE list (owner of the executor's
            # workspace), not the display one, so as not to let a member without ownership
            # link someone else's dedicated executor.
            from app.services.user_executor_service import get_user_bindable_agents
            accessible = await get_user_bindable_agents(db, current_user.id_hash)
            if not any(a["id_hash"] == payload.target_executor_id for a in accessible):
                raise HTTPException(status_code=403, detail="Você não tem acesso a este executor.")

    old_agent_id = ws.target_executor_id
    ws.target_executor_id = payload.target_executor_id
    # Dual-write to the policy (spec §8, wave 2): tier 1 becomes
    # {executor} (or is cleared). While EXECUTOR_POLICY_ROUTING=off it is this
    # pointer that counts; keeping both equal is what makes the switchover change nothing.
    from app.services import workspace_executor_service as politica
    await politica.replace_primary(db, ws, payload.target_executor_id, actor_id=current_user.id_hash)
    await db.commit()

    # Notificar executores afetados
    from app.core.executor_connections import executor_registry
    # Notify the previous executor (if there was one and it differs from the new one)
    if old_agent_id and old_agent_id != payload.target_executor_id:
        try:
            await executor_registry.send_json(old_agent_id, {
                "type": "control", "action": "config_changed",
                "reason": "Workspace removeu este executor."
            })
        except Exception as exc:
            logger.warning("Falha ao notificar executor antigo '%s' sobre remoção: %s", old_agent_id, exc)
    # Notificar novo executor
    if payload.target_executor_id:
        try:
            await executor_registry.send_json(payload.target_executor_id, {
                "type": "control", "action": "config_changed",
                "reason": "Workspace atribuiu este executor."
            })
        except Exception as exc:
            logger.warning("Falha ao notificar novo executor '%s' sobre atribuição: %s", payload.target_executor_id, exc)

    logger.info("Usuário '%s' definiu executor '%s' no workspace '%s'.", current_user.username, payload.target_executor_id, id_hash)
    return {"workspace_id": id_hash, "target_executor_id": payload.target_executor_id}


@router.get("/{id_hash}/executor", summary="Obter executor do workspace")
async def get_workspace_agent(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the executor configured for the workspace.

    Read open to any member — whoever operates the workspace needs to know
    where the jobs run. `_get_visible_workspace` is the same gate as
    `list_members`: without it, this route returned the `target_executor_id` of
    any workspace to any authenticated account, and also distinguished
    "does not exist" (404) from "exists and is not yours" (200) — an enumeration
    oracle for workspace id_hash.
    """
    _ws, _role = await _get_visible_workspace(id_hash, db, current_user)
    return {"workspace_id": id_hash, "target_executor_id": _ws.target_executor_id}


# ── Execution policy: tiers, terminal, health ─────────────────────────────────
# docs/specs/executor-isolation-routing.md §9. The floor (isolation_floor) belongs to
# the platform admin and lives in admin_workspaces_router.

class PolicyMemberOut(BaseModel):
    id_hash: str
    name: str
    executor_type: str
    status: str
    tier: int
    online: Optional[bool] = None       # None = unknown presence (Redis down / reconnecting)
    capacity: Optional[dict] = None


class PoolHealthOut(BaseModel):
    total: int
    available: int


class WorkspacePolicyOut(BaseModel):
    workspace_id: str
    mode: str                           # pool | isolated | dedicated_pool
    primary: List[PolicyMemberOut]
    fallback: List[PolicyMemberOut]
    fallback_terminal: str
    effective_terminal: str
    isolation_floor: str
    available_primary: int
    available_fallback: int
    pool: Optional[PoolHealthOut] = None
    # The UI cannot promise a policy that routing does not read yet.
    policy_routing_enabled: bool
    target_executor_id: Optional[str] = None


class FallbackUpdate(BaseModel):
    terminal: str = Field(..., pattern="^(fail|pool)$")


async def _policy_out(db: AsyncSession, ws: Workspace) -> WorkspacePolicyOut:
    import asyncio
    from app.core.config import policy_routing_enabled
    from app.core.executor_connections import executor_registry
    from app.services import workspace_executor_service as politica
    from app.services.user_executor_service import get_default_agents

    policy = await politica.load_policy(db, ws)

    async def _membro(ag, tier: int) -> PolicyMemberOut:
        online = await executor_registry.presence_or_unknown(ag.id_hash)
        capacity = await executor_registry.read_capacity(ag.id_hash) if online else None
        return PolicyMemberOut(
            id_hash=ag.id_hash, name=ag.name, executor_type=ag.executor_type,
            status=ag.status, tier=tier, online=online, capacity=capacity,
        )

    primary = list(await asyncio.gather(*[_membro(a, 1) for a in policy.primary]))
    fallback = list(await asyncio.gather(*[_membro(a, 2) for a in policy.fallback]))

    pool = None
    if policy.allows_pool:
        defaults = [d for d in await get_default_agents(db) if d.public_key]
        flags = await asyncio.gather(*[executor_registry.presence_or_unknown(d.id_hash) for d in defaults]) if defaults else []
        pool = PoolHealthOut(total=len(defaults), available=sum(1 for f in flags if f is True))

    return WorkspacePolicyOut(
        workspace_id=ws.id_hash,
        mode=policy.mode,
        primary=primary,
        fallback=fallback,
        fallback_terminal=policy.terminal_configured,
        effective_terminal=policy.terminal_effective,
        isolation_floor=policy.floor,
        available_primary=sum(1 for m in primary if m.online is True),
        available_fallback=sum(1 for m in fallback if m.online is True),
        pool=pool,
        policy_routing_enabled=policy_routing_enabled(),
        target_executor_id=ws.target_executor_id,
    )


async def _accessible_ids_for(db: AsyncSession, current_user: User) -> set[str] | None:
    """Executors the user has access to; None = platform admin (no restriction)."""
    if current_user.role == "admin":
        return None
    # Audit SEG-13: writing a link uses the LINKABLE list.
    from app.services.user_executor_service import get_user_bindable_agents
    return {a["id_hash"] for a in await get_user_bindable_agents(db, current_user.id_hash)}


@router.get("/{id_hash}/executors", response_model=WorkspacePolicyOut,
            summary="Política de execução do workspace (níveis, terminal, saúde)")
async def get_workspace_policy(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws, _role = await _get_visible_workspace(id_hash, db, current_user)
    return await _policy_out(db, ws)


@router.post("/{id_hash}/executors/{executor_id}", response_model=WorkspacePolicyOut,
             summary="Incluir executor dedicado num nível da política")
async def add_workspace_policy_member(
    id_hash: str,
    executor_id: str,
    tier: int = Query(1, ge=1, le=2, description="1 = principal, 2 = fallback"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)
    from app.services import workspace_executor_service as politica
    await politica.add_member(
        db, ws, executor_id, tier,
        actor_id=current_user.id_hash,
        accessible_ids=await _accessible_ids_for(db, current_user),
    )
    logger.info("Usuário '%s' incluiu executor '%s' no nível %d do workspace '%s'.",
                current_user.username, executor_id, tier, id_hash)
    return await _policy_out(db, ws)


@router.delete("/{id_hash}/executors/{executor_id}", status_code=204,
               summary="Remover executor de um nível da política")
async def remove_workspace_policy_member(
    id_hash: str,
    executor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)
    from app.services import workspace_executor_service as politica
    await politica.remove_member(db, ws, executor_id, actor_id=current_user.id_hash)
    logger.info("Usuário '%s' removeu executor '%s' da política do workspace '%s'.",
                current_user.username, executor_id, id_hash)


@router.put("/{id_hash}/fallback", response_model=WorkspacePolicyOut,
            summary="Definir o terminal da política: falhar ou usar o pool")
async def set_workspace_fallback(
    id_hash: str,
    payload: FallbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)
    from app.services import workspace_executor_service as politica
    await politica.set_terminal(db, ws, payload.terminal, actor_id=current_user.id_hash)
    logger.info("Usuário '%s' definiu terminal '%s' no workspace '%s'.",
                current_user.username, payload.terminal, id_hash)
    return await _policy_out(db, ws)


# ── Notification allowlist ────────────────────────────────────────────────────

class NotificationAllowlistUpdate(BaseModel):
    allowlist: List[str] = Field(default_factory=list)


class NotificationTargetOut(BaseModel):
    id_hash: str
    name: str
    notification_url: str
    host: str
    allowed: bool


class WorkspaceNotificationsOut(BaseModel):
    allowlist: List[str]
    workflows: List[NotificationTargetOut]


def _normalize_allowlist(raw: List[str]) -> List[str]:
    """Normalizes and validates hostname patterns. Raises 400 on what the matcher would ignore.

    The rule lives in `app.core.utils.allowlist.validar_allowlist`, shared
    with the admin's global webhook whitelist.
    """
    from app.core.utils.allowlist import validar_allowlist

    try:
        return validar_allowlist(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _notification_targets(db: AsyncSession, id_hash: str, allowlist: List[str]) -> List[NotificationTargetOut]:
    """The workspace's workflows that send webhooks, marking which ones the allowlist blocks.

    Uses `hostname_matches_allowlist` — the SAME function the consumer calls when
    firing the notification. Reimplementing it here would make the screen promise a result
    different from what happens at run time. This screen covers only the WORKSPACE
    allowlist; the admin's global whitelist (Settings) also applies at
    trigger time, and is shown and edited there.
    """
    from urllib.parse import urlparse
    from app.core.utils.allowlist import hostname_matches_allowlist
    from app.models.workflow import Workflow

    result = await db.execute(
        select(Workflow.id_hash, Workflow.name, Workflow.notification_url)
        .where(
            Workflow.workspace_id == id_hash,
            Workflow.deleted_at.is_(None),
            Workflow.notification_url.isnot(None),
            Workflow.notification_url != "",
        )
        .order_by(Workflow.name)
    )

    targets: List[NotificationTargetOut] = []
    for wf_id, name, url in result.all():
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            host = ""
        targets.append(NotificationTargetOut(
            id_hash=wf_id,
            name=name,
            notification_url=url,
            host=host,
            # Empty list = no additional policy: everything that passes the SSRF check
            # is accepted. Mirrors the consumer's `if allowlist:`.
            allowed=True if not allowlist else hostname_matches_allowlist(host, allowlist),
        ))
    return targets


@router.get(
    "/{id_hash}/notifications",
    response_model=WorkspaceNotificationsOut,
    summary="Allowlist de notificações do workspace e seu impacto",
)
async def get_workspace_notifications(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read open to any member: knowing WHY a webhook did not arrive is
    useful for whoever operates the workflow, not only for whoever administers the workspace."""
    ws, _ = await _get_visible_workspace(id_hash, db, current_user)
    allowlist = ws.notification_url_allowlist or []
    return WorkspaceNotificationsOut(
        allowlist=allowlist,
        workflows=await _notification_targets(db, id_hash, allowlist),
    )


@router.put(
    "/{id_hash}/notifications",
    response_model=WorkspaceNotificationsOut,
    summary="Definir allowlist de notificações do workspace",
)
async def update_workspace_notifications(
    id_hash: str,
    payload: NotificationAllowlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)
    normalized = _normalize_allowlist(payload.allowlist)

    previous = ws.notification_url_allowlist or []
    # An empty list is saved as NULL. The consumer treats `None` and `[]` the same (`or []` +
    # `if allowlist:`), and keeping two values for the same state would only make the
    # column lie about a policy existing.
    ws.notification_url_allowlist = normalized or None
    await db.commit()

    # This is security configuration: without this log, the "webhook blocked" warning
    # in the consumer shows up with no clue as to who tightened the screw.
    logger.info(
        "Allowlist de notificação alterada: workspace=%s por=%s de=%s para=%s",
        id_hash, current_user.id_hash, previous, normalized,
    )

    return WorkspaceNotificationsOut(
        allowlist=normalized,
        workflows=await _notification_targets(db, id_hash, normalized),
    )


# ── User search by e-mail (to invite members) ─────────────────────────────────

@router.get("/users/search", response_model=List[UserSearchOut], summary="Buscar usuário por e-mail")
async def search_users(
    email: str = Query(..., min_length=3, max_length=254, description="E-mail completo do usuário a convidar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resolves ONE active user by EXACT e-mail, to invite as a member.

    Audit (SEG-06): the unscoped substring search (ILIKE) allowed
    harvesting the e-mails of the entire user base — the term "___" already matched any
    account, and the route does not check whether the searcher administers any workspace
    (every sign-up creates one). Exact equality returns at most the typed user (or nothing),
    which is what is needed to invite and removes mass enumeration.
    """
    alvo = email.strip().lower()
    result = await db.execute(
        select(User)
        .where(
            sa_func.lower(User.email) == alvo,
            User.status == "active",
            User.id_hash != current_user.id_hash,
        )
        .limit(1)
    )
    return result.scalars().all()
