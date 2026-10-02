# app/api/routers/admin_workspaces_router.py
"""
Lixeira de workspaces — restaurar ou descartar workspaces soft-deletados.

Admin-only por decisão de produto: o dono faz o soft delete (DELETE
/workspaces/{id}), mas só o administrador da plataforma enxerga a lixeira e
decide o destino. Por isso a listagem NÃO filtra por owner_id — o admin vê o
que qualquer usuário deletou.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_admin
from app.core.utils.logger import get_logger
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workspace import Workspace

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/workspaces",
    tags=["admin", "workspaces"],
    dependencies=[Depends(require_admin)],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class WorkspaceTrashOut(BaseModel):
    id_hash: str
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    deleted_at: str
    workflows: int = 0   # quantos workflows voltam se este workspace for restaurado


class WorkspacePolicyAdminOut(BaseModel):
    """Uma linha da tela de admin "Piso de isolamento": o que o admin precisa
    para decidir onde fixar `no_pool` — e enxergar quem ficaria sem rodar."""
    id_hash: str
    name: str
    is_default: bool = False
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
    mode: str                       # pool | isolated | dedicated_pool
    isolation_floor: str
    fallback_terminal: str
    effective_terminal: str
    primary_count: int = 0
    fallback_count: int = 0


class PurgeWorkspaceRequest(BaseModel):
    confirm: str = Field(
        ..., description="Repita o id_hash do workspace — guarda contra clique acidental.",
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_deleted_workspace(id_hash: str, db: AsyncSession) -> Workspace:
    """Workspace que está na lixeira, ou 404.

    Sem checagem de owner — este router é admin-only. Exigir `deleted_at`
    preenchido é o que impede restaurar/purgar um workspace vivo por engano.
    """
    result = await db.execute(
        select(Workspace).where(
            Workspace.id_hash == id_hash,
            Workspace.deleted_at.isnot(None),
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado na lixeira.")
    return ws


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/policies", response_model=List[WorkspacePolicyAdminOut],
            summary="[Admin] Política de execução de todos os workspaces vivos")
async def list_workspace_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Só as contagens dos níveis, não os executores: é o suficiente para o
    modo (a mesma conta de `mode_of`) e para o admin ver, antes de fixar o
    piso, quem ficaria sem executor principal."""
    from app.models.workspace_executor import WorkspaceExecutor
    from app.services import workspace_executor_service as politica

    ws_rows = (await db.execute(
        select(Workspace).where(Workspace.deleted_at.is_(None)).order_by(Workspace.name)
    )).scalars().all()

    contagem = (await db.execute(
        select(WorkspaceExecutor.workspace_id, WorkspaceExecutor.tier, sa_func.count())
        .group_by(WorkspaceExecutor.workspace_id, WorkspaceExecutor.tier)
    )).all()
    por_ws: dict[str, dict[int, int]] = {}
    for ws_id, tier, n in contagem:
        por_ws.setdefault(ws_id, {})[int(tier)] = int(n)

    owner_ids = {w.owner_id for w in ws_rows if w.owner_id}
    donos: dict[str, str] = {}
    if owner_ids:
        for id_hash, username in (await db.execute(
            select(User.id_hash, User.username).where(User.id_hash.in_(owner_ids))
        )).all():
            donos[id_hash] = username

    saida: list[WorkspacePolicyAdminOut] = []
    for w in ws_rows:
        niveis = por_ws.get(w.id_hash, {})
        principais = niveis.get(politica.TIER_PRIMARY, 0)
        floor = w.isolation_floor or politica.FLOOR_NONE
        terminal = w.fallback_terminal or politica.TERMINAL_FAIL
        saida.append(WorkspacePolicyAdminOut(
            id_hash=w.id_hash,
            name=w.name,
            is_default=bool(getattr(w, "is_default", False)),
            owner_id=w.owner_id,
            owner_username=donos.get(w.owner_id) if w.owner_id else None,
            mode=politica.mode_of(principais > 0, floor, terminal),
            isolation_floor=floor,
            fallback_terminal=terminal,
            effective_terminal=politica.effective_terminal_of(floor, terminal),
            primary_count=principais,
            fallback_count=niveis.get(politica.TIER_FALLBACK, 0),
        ))
    return saida


@router.get("/trash", response_model=List[WorkspaceTrashOut], summary="[Admin] Listar workspaces na lixeira")
async def list_deleted_workspaces(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Todos os workspaces soft-deletados da plataforma, do mais recente ao mais antigo."""
    # LEFT OUTER JOIN: owner_id e nullable e nao tem FK para users, entao um
    # INNER JOIN esconderia justamente os workspaces orfaos — os que mais
    # interessam ao admin.
    result = await db.execute(
        select(Workspace, User.username, User.email)
        .outerjoin(User, User.id_hash == Workspace.owner_id)
        .where(Workspace.deleted_at.isnot(None))
        .order_by(Workspace.deleted_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    if not rows:
        return []

    # Quantos workflows voltam no restore: só os que caíram junto com o
    # workspace, casados pelo deleted_at compartilhado. Contar todos os
    # deletados inflaria o número com workflows apagados individualmente antes,
    # que o restore não devolve.
    counts = dict((await db.execute(
        select(Workflow.workspace_id, sa_func.count(Workflow.id))
        .join(Workspace, Workspace.id_hash == Workflow.workspace_id)
        .where(
            Workflow.workspace_id.in_([ws.id_hash for ws, _, _ in rows]),
            Workflow.deleted_at == Workspace.deleted_at,
        )
        .group_by(Workflow.workspace_id)
    )).all())

    return [
        WorkspaceTrashOut(
            id_hash=ws.id_hash,
            name=ws.name,
            description=ws.description,
            owner_id=ws.owner_id,
            owner_username=username,
            owner_email=email,
            deleted_at=ws.deleted_at.isoformat(),
            workflows=int(counts.get(ws.id_hash, 0)),
        )
        for ws, username, email in rows
    ]


@router.post("/{id_hash}/restore", summary="[Admin] Restaurar workspace da lixeira")
async def restore_workspace(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tira o workspace da lixeira e devolve os workflows que caíram com ele.

    Os workflows voltam DESATIVADOS, e os agendamentos continuam desligados: o
    delete em cascata não registra quem já estava desativado antes, então
    religar em bloco reativaria justamente o que o dono tinha desligado de
    propósito. O dono reativa o que ainda fizer sentido.
    """
    ws = await _get_deleted_workspace(id_hash, db)

    from app.services.workflow_service import restore_workspace_workflows
    restored = await restore_workspace_workflows(db, id_hash, ws.deleted_at)

    ws.deleted_at = None
    await db.commit()
    logger.info(
        "Admin '%s' restaurou o workspace '%s' (dono=%s, %d workflow(s) devolvido(s))",
        current_user.username, id_hash, ws.owner_id, restored,
    )
    return {
        "workspace_id": id_hash,
        "workflows_restored": restored,
        "detail": (
            f"{restored} workflow(s) devolvido(s) ao workspace. Eles voltam "
            "desativados, assim como os agendamentos — reative manualmente."
        ),
    }


@router.post("/{id_hash}/purge", status_code=204, summary="[Admin] Remover workspace definitivamente")
async def purge_workspace(
    id_hash: str,
    payload: PurgeWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hard delete — apaga a linha de vez. Exige que o workspace esteja na lixeira.

    A exigência é proposital: purgar direto significaria perder em um clique o
    que o soft delete existe para proteger. Os membros saem por FK CASCADE.

    `confirm` repete o id_hash porque o botão fica ao lado de cada linha da
    tabela, e agora sobre workspaces de outros usuários.
    """
    if payload.confirm != id_hash:
        raise HTTPException(status_code=400, detail="Confirmação não confere com o id_hash.")

    ws = await _get_deleted_workspace(id_hash, db)

    # Os workflows continuam apontando para o id_hash apos o hard delete — sem
    # FK, nada os remove. Ja estao soft-deletados pelo delete, entao nao voltam
    # a executar; a limpeza definitiva deles fica fora deste endpoint (o
    # historico de runs e metricas ainda referencia esses hashes).
    #
    # A expiracao de storage aqui e rede de seguranca: o DELETE do workspace ja
    # rodou o mesmo helper, entao na pratica costuma ser no-op. Ela cobre o caso
    # do purge_expired_artifacts ainda nao ter passado quando a linha some — sem
    # isso os artefatos viram orfaos sem nome no /admin/storage.
    from app.services.storage_purge_service import schedule_workspace_data_expiry
    scheduled = await schedule_workspace_data_expiry(db, id_hash)

    await db.delete(ws)
    await db.commit()
    logger.warning(
        "Admin '%s' purgou definitivamente o workspace '%s' (dono=%s; agendados p/ "
        "remoção: %d artefato(s), %d arquivo(s) do Drive)",
        current_user.username, id_hash, ws.owner_id,
        scheduled["artifacts"], scheduled["drive_files"],
    )


# ── Piso de isolamento (spec §4.5, Q10) ────────────────────────────────────────

class IsolationFloorUpdate(BaseModel):
    floor: str = Field(..., pattern="^(none|no_pool)$")


@router.put("/{id_hash}/isolation-floor", summary="[Admin] Piso de isolamento do workspace")
async def set_isolation_floor(
    id_hash: str,
    payload: IsolationFloorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """`no_pool` proíbe o fallback para o pool compartilhado: o terminal é
    forçado a `fail` e o dono/admin do workspace não consegue afrouxar (a API
    recusa com 403 e o dispatch lê o piso). Só o admin da plataforma escreve —
    é o que restaura uma garantia dura onde ela é exigência externa."""
    from app.services import workspace_executor_service as politica
    from app.services.execution_alert_service import notify_floor_forced

    result = await db.execute(
        select(Workspace).where(Workspace.id_hash == id_hash, Workspace.deleted_at.is_(None))
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    forced = await politica.set_floor(db, ws, payload.floor, actor_id=current_user.id_hash)
    # Só avisa quem tem nível principal: sem dedicado, "passou a ser isolado"
    # não descreve nada que o dono reconheça.
    if forced and (await politica.load_policy(db, ws)).has_primary:
        try:
            await notify_floor_forced(db, ws)
        except Exception as exc:  # best-effort
            logger.warning("Falha ao avisar o dono do piso em '%s': %s", id_hash, exc)
    logger.info("Admin '%s' definiu piso '%s' no workspace '%s' (terminal forçado: %s).",
                current_user.username, payload.floor, id_hash, forced)
    return {
        "workspace_id": id_hash,
        "isolation_floor": ws.isolation_floor,
        "fallback_terminal": ws.fallback_terminal,
        "terminal_forced_to_fail": forced,
    }
