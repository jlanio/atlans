# app/api/routers/workspace_router.py
"""
CRUD de Workspaces — isolamento multi-tenant de workflows.
Inclui gerenciamento de membros (workspaces multi-usuário).
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
    """Retorna workspace vivo que pertence ao usuário (owner), ou lança 403/404.

    Workspace na lixeira é invisível aqui — restaurar e purgar são ações de
    admin, em /admin/workspaces.
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
    """Aceita owner OU membro com role admin — para convidar/remover membros e definir executor."""
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
    """Workspace vivo + role efetivo do usuário. 404 se não existe, 403 se não é membro.

    Devolve a entidade, e não um `WorkspaceOut`, porque quem lista membros precisa
    de `Workspace.owner_id` e `Workspace.created_at` para montar a linha do dono —
    que não existe em `workspace_members`.
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
    """Retorna workspaces criados pelo usuário + workspaces dos quais é membro."""
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
    """Move o workspace para a lixeira — a linha permanece, com `deleted_at`.

    Os workflows caem junto (soft delete + schedules desativados). Restaurar e
    descartar em definitivo são ações de admin, em /admin/workspaces — o dono
    deleta, mas não desfaz.
    """
    ws = await _get_owned_workspace(id_hash, db, current_user)
    if ws.is_default:
        raise HTTPException(status_code=403, detail="O workspace padrão não pode ser removido.")

    deleted_at = utc_now_naive()

    # ORDEM IMPORTA. `schedule_workspace_data_expiry` faz um commit interno
    # (via purge_workspace_storage), entao tudo que precisa cair junto tem de
    # estar sujo na sessao ANTES dela. Marcar o workspace por ultimo abria uma
    # janela em que os workflows ja estavam soft-deletados e o workspace ainda
    # vivo — estado que nao aparece na lixeira (o filtro e deleted_at IS NOT
    # NULL) e que, portanto, nem o dono nem o admin conseguem desfazer pela UI.
    ws.deleted_at = deleted_at

    # Desativa os workflows junto. Um workflow cujo workspace sumiu continua
    # sendo disparado pelo AsyncScheduler (que filtra so por Schedule.active) —
    # invisivel na UI, rodando no pool default em vez do executor do workspace e
    # sem a allowlist de webhook. Nenhum workflow sobrevive ao delete do seu
    # workspace.
    #
    # O timestamp e compartilhado com Workspace.deleted_at: e a marca que o
    # restore usa para saber quais workflows cairam por causa deste delete.
    from app.services.workflow_service import soft_delete_workspace_workflows
    cascaded = await soft_delete_workspace_workflows(db, id_hash, deleted_at)

    # Storage segue a politica de expiracao imediata: artefatos ganham
    # expires_at=agora (removidos na proxima passada do purge_expired_artifacts,
    # que trata MinIO, PortalLayer e retry de S3) e arquivos do Drive, que nao
    # tem coluna de expiracao, saem na hora. Um restore devolve os workflows,
    # NAO os arquivos ja purgados.
    #
    # E aqui que a transacao acima e confirmada, no commit interno do helper.
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
    """Monta a lista de membros com o dono na frente.

    O dono NAO tem linha em `workspace_members` — `create_workspace` nunca cria
    uma. Antes disso, quem criou o workspace simplesmente nao aparecia na propria
    lista de membros, e um admin convidado nao tinha como descobrir com quem falar.
    A linha do dono e sintetica: role "owner" (que nao esta em `_VALID_ROLES`, logo
    nao e atribuivel) e `joined_at` = criacao do workspace, que e literalmente
    quando ele entrou.

    Se o dono TAMBEM tiver linha em `workspace_members` — possivel em dados
    antigos, ja que ate agora nada impedia convidar o proprio dono por e-mail — a
    linha sintetica vence e a real e descartada. Sem isso ele apareceria duas
    vezes, com dois roles diferentes.
    """
    members: List[MemberOut] = []

    # `owner_id` e nullable e o usuario pode ter sido removido da plataforma;
    # nos dois casos a lista sai so com os membros, sem uma linha vazia.
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
    """O convite é pelo e-mail: ele só vale se o e-mail é de quem tem a conta.

    Com EXIGIR_EMAIL_VERIFICADO (o padrão), a conta sem e-mail verificado nem
    entra, e o convite espera a verificação. Sem a exigência, o cadastro aberto
    deixa qualquer um criar a conta com o e-mail de outra pessoa — e o convite
    entregaria o workspace a quem se cadastrou primeiro. Havendo transporte, a
    pessoa consegue verificar (o link chega), então o convite espera por isso.
    Sem transporte, nada na instalação prova o e-mail: o convite passa, e o
    aviso fica no log (o risco está descrito no .env.example).
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
    """Admin ou dono do workspace pode convidar membros."""
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)

    if payload.role not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role inválido. Opções: {sorted(_VALID_ROLES)}")

    # Busca usuário pelo e-mail
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"Usuário com e-mail '{payload.email}' não encontrado.")
    # Comparar com o dono, e nao com quem convida: um admin convidando o dono
    # criava uma linha duplicada em `workspace_members` — e a mensagem antiga
    # ("Você já é o dono deste workspace") ainda por cima acusava a pessoa errada.
    if ws.owner_id and user.id_hash == ws.owner_id:
        raise HTTPException(status_code=400, detail="Este usuário já é o dono do workspace.")
    _conferir_email_do_convidado(user, id_hash)

    # Verifica se já é membro
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

    # Extrai atributos do ORM antes de sair da sessão (evita DetachedInstanceError)
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

    # O dono agora aparece na lista de membros, entao a UI oferece a linha dele
    # como qualquer outra. Sem esta guarda o PUT cairia no 404 generico abaixo
    # ("Membro não encontrado"), que nao explica nada.
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
    """Admin/dono pode remover qualquer membro. Membros podem sair por conta própria."""
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.is_(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    # Uma guarda, dois casos: admin tentando remover o dono (que agora aparece na
    # lista) e o proprio dono tentando "sair". Nenhum dos dois pode acontecer — o
    # dono nao tem linha em `workspace_members`, entao sem isto ambos cairiam num
    # 404 que parece bug. Sair do proprio workspace nao existe: excluir, sim.
    if ws.owner_id and user_id == ws.owner_id:
        raise HTTPException(
            status_code=400,
            detail="O dono não pode sair do próprio workspace. Exclua o workspace em vez disso.",
        )

    # Próprio usuário pode sair; admin+ pode remover outros membros
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
    # Auditoria (SEG-98): as credenciais que o ex-membro compartilhou COM ESTE
    # workspace deixam de valer aqui — senão continuavam sendo resolvidas no
    # dispatch para quem ficou, mesmo sem o dono ter mais acesso ao workspace.
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


# ── Executor do workspace ────────────────────────────────────────────────────────

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
    Define qual executor será usado para executar workflows deste workspace.
    Workflows sem override específico herdarão este executor.
    """
    ws = await _get_admin_managed_workspace(id_hash, db, current_user)

    # Validar que o executor existe e está ativo
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

        # Não-admin global só pode vincular executores a que tem acesso (pool padrão,
        # atribuição direta ou executor de outro workspace seu). Impede apontar o
        # workspace para o executor dedicado de outro usuário — o que faria o job
        # (com credenciais injetadas) ser descriptografado no host alheio.
        if current_user.role != "admin":
            # Auditoria SEG-13: usa a lista de VINCULÁVEIS (dono do workspace do
            # executor), não a de exibição, para não deixar membro sem posse
            # vincular executor dedicado alheio.
            from app.services.user_executor_service import get_user_bindable_agents
            accessible = await get_user_bindable_agents(db, current_user.id_hash)
            if not any(a["id_hash"] == payload.target_executor_id for a in accessible):
                raise HTTPException(status_code=403, detail="Você não tem acesso a este executor.")

    old_agent_id = ws.target_executor_id
    ws.target_executor_id = payload.target_executor_id
    # Dual-write na política (spec §8, onda 2): o nível 1 passa a ser
    # {executor} (ou é limpo). Enquanto EXECUTOR_POLICY_ROUTING=off é este
    # ponteiro que vale; manter os dois iguais é o que faz a virada não mudar nada.
    from app.services import workspace_executor_service as politica
    await politica.replace_primary(db, ws, payload.target_executor_id, actor_id=current_user.id_hash)
    await db.commit()

    # Notificar executores afetados
    from app.core.executor_connections import executor_registry
    # Notificar executor anterior (se existia e é diferente do novo)
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
    """Retorna o executor configurado para o workspace.

    Leitura liberada a qualquer membro — quem opera o workspace precisa saber
    onde os jobs rodam. `_get_visible_workspace` é o mesmo gate de
    `list_members`: sem ele, esta rota devolvia o `target_executor_id` de
    qualquer workspace a qualquer conta autenticada, e ainda distinguia
    "não existe" (404) de "existe e não é seu" (200) — um oráculo de enumeração
    de id_hash de workspace.
    """
    _ws, _role = await _get_visible_workspace(id_hash, db, current_user)
    return {"workspace_id": id_hash, "target_executor_id": _ws.target_executor_id}


# ── Política de execução: níveis, terminal, saúde ─────────────────────────────
# docs/specs/executor-isolation-routing.md §9. O piso (isolation_floor) é do
# admin da plataforma e vive em admin_workspaces_router.

class PolicyMemberOut(BaseModel):
    id_hash: str
    name: str
    executor_type: str
    status: str
    tier: int
    online: Optional[bool] = None       # None = presença desconhecida (Redis fora / reconectando)
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
    # A UI não pode prometer uma política que o roteamento ainda não lê.
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
    """Executores a que o usuário tem acesso; None = admin da plataforma (sem restrição)."""
    if current_user.role == "admin":
        return None
    # Auditoria SEG-13: escrita de vínculo usa a lista de VINCULÁVEIS.
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


# ── Allowlist de notificações ─────────────────────────────────────────────────

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
    """Normaliza e valida padroes de hostname. Lanca 400 no que o matcher ignoraria.

    A regra mora em `app.core.utils.allowlist.validar_allowlist`, compartilhada
    com a whitelist global de webhooks do admin.
    """
    from app.core.utils.allowlist import validar_allowlist

    try:
        return validar_allowlist(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _notification_targets(db: AsyncSession, id_hash: str, allowlist: List[str]) -> List[NotificationTargetOut]:
    """Workflows do workspace que enviam webhook, marcando quais a allowlist barra.

    Usa `hostname_matches_allowlist` — a MESMA funcao que o consumer chama ao
    disparar a notificacao. Reimplementar aqui faria a tela prometer um resultado
    diferente do que acontece na execucao. Esta tela trata só da allowlist DO
    WORKSPACE; a whitelist global do admin (Configurações) também vale no
    disparo, e é mostrada e editada lá.
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
            # Lista vazia = sem politica adicional: tudo que passa no SSRF check
            # e aceito. Espelha o `if allowlist:` do consumer.
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
    """Leitura liberada a qualquer membro: saber POR QUE um webhook não chegou é
    útil para quem opera o workflow, não só para quem administra o workspace."""
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
    # Lista vazia grava NULL. O consumer trata `None` e `[]` igual (`or []` +
    # `if allowlist:`), e manter dois valores para o mesmo estado so faria a
    # coluna mentir sobre existir uma politica.
    ws.notification_url_allowlist = normalized or None
    await db.commit()

    # E configuracao de seguranca: sem este log, o warning de "webhook bloqueado"
    # no consumer aparece sem nenhuma pista de quem apertou o parafuso.
    logger.info(
        "Allowlist de notificação alterada: workspace=%s por=%s de=%s para=%s",
        id_hash, current_user.id_hash, previous, normalized,
    )

    return WorkspaceNotificationsOut(
        allowlist=normalized,
        workflows=await _notification_targets(db, id_hash, normalized),
    )


# ── Busca de usuários por e-mail (para convidar membros) ───────────────────────

@router.get("/users/search", response_model=List[UserSearchOut], summary="Buscar usuário por e-mail")
async def search_users(
    email: str = Query(..., min_length=3, max_length=254, description="E-mail completo do usuário a convidar"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resolve UM usuário ativo pelo e-mail EXATO, para convidar como membro.

    Auditoria (SEG-06): a busca por substring (ILIKE) sem escopo permitia
    coletar os e-mails de toda a base — o termo "___" já casava qualquer conta,
    e a rota não confere se quem busca administra algum workspace (todo cadastro
    cria um). Igualdade exata devolve no máximo o usuário digitado (ou nada), o
    que é o necessário para convidar e remove a enumeração em massa.
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
