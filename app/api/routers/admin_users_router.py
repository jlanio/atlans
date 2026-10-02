# app/api/routers/admin_users_router.py
"""Endpoints administrativos para gestão de usuários."""

import csv
import io
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.core.rate_limiter import limiter
from app.schemas.admin_users import (
    UserAdminOut,
    UserListResponse,
    UserSuspendRequest,
    UserBulkActionRequest,
    UserBulkActionResponse,
    UserUpdateRoleRequest,
    UserUpdateAgentQuotaRequest,
    UserExecutorStatsResponse,
    RevokeAllAgentsResponse,
)
from app.services import admin_user_service as svc
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/users",
    tags=["admin", "users"],
    dependencies=[Depends(require_admin)],
)


# ── V04: cross-workspace privilege guard ─────────────────────────────────────


async def _ensure_admin_can_modify_target(
    db: AsyncSession, admin_user, target_user_id_hash: str,
) -> None:
    """Guard de jurisdicao admin sobre o target.

    Modelo atual: um unico nivel de admin — `role=admin` = admin global,
    opera sobre qualquer usuario da instalacao. Sem hierarquia
    workspace_admin/global_admin ainda (previsto em V04). Guard fica como
    no-op enquanto isso.

    Reativar quando a hierarquia existir:
      - global_admin: pula esta checagem (return direto)
      - workspace_admin: exige que admin e alvo compartilhem ao menos um
        workspace vivo (dono ou membro). Um helper pronto para essa conta,
        `_admin_shares_workspace_with`, existiu sem nunca ser chamado e saiu;
        esta no historico do git.

    Auto-acao (admin == target) tambem seria liberada — outros guards
    do endpoint cuidam disso (ex: nao se auto-suspender).
    """
    _ = (db, admin_user, target_user_id_hash)  # noqa: F841 — assinatura preservada
    return


# ── Rotas sem path params (ANTES das rotas com {id_hash}) ────────────────────


@router.get("", response_model=UserListResponse, summary="Listar usuários com paginação e filtros")
async def list_users(
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    users, total = await svc.list_users(
        db,
        search=search,
        status=status,
        role=role,
        sort_by=sort_by,
        sort_order=sort_order,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return UserListResponse(
        items=[UserAdminOut.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/export/csv", summary="Exportar usuários em CSV")
async def export_users_csv(
    search: str | None = None,
    status: str | None = None,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Gera CSV com todos os usuários que atendem aos filtros (sem paginação)."""
    users, _ = await svc.list_users(
        db, search=search, status=status, role=role, limit=10_000, offset=0,
    )

    def _neutralizar(valor):
        """Neutraliza injeção de fórmula no CSV (auditoria SEG-121).

        Um username/e-mail começando com `=`, `+`, `-`, `@` (ou TAB/CR) é
        executado como fórmula ao abrir no Excel/Sheets. Prefixar com `'`
        (apóstrofo) faz a planilha tratar a célula como texto.
        """
        if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + valor
        return valor

    def _generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id_hash", "username", "email", "status", "role", "last_login_at", "created_at"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for u in users:
            writer.writerow([_neutralizar(c) for c in (
                u.id_hash, u.username, u.email, u.status, u.role,
                str(u.last_login_at) if u.last_login_at else "",
                str(u.created_at),
            )])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


# ── Bulk actions ─────────────────────────────────────────────────────────────


async def _triar(
    db: AsyncSession,
    current_user,
    user_ids: list[str],
    *,
    elegivel: Callable[[object], str | None],
    erro_auto: str | None,
) -> tuple[list, list[dict]]:
    """Triagem comum de `bulk/suspend`, `bulk/reactivate` e `bulk/delete`.

    As três repetiam o mesmo laço com ~90% do corpo igual, e a diferença entre
    elas era só o predicado de elegibilidade e a mensagem de auto-ação. O
    problema de manter as cópias não é o tamanho: as seis rotas *single*
    chamavam `_ensure_admin_can_modify_target` e as três bulk **não**. Hoje isso
    é inócuo (o guard é no-op enquanto a hierarquia de admin do V04 não existe),
    mas no dia em que ele passar a valer, quem quisesse contornar a jurisdição
    usaria a rota bulk com um id só.

    `elegivel(user)` devolve None quando a ação pode ser aplicada, ou a mensagem
    de erro. `erro_auto` é a mensagem quando o admin é o próprio alvo; None
    libera a auto-ação (é o caso de `reactivate`).

    Devolve (elegíveis, erros).
    """
    errors: list[dict] = []
    eligible: list = []
    users_by_id = await svc.get_users_by_ids(db, user_ids)

    for uid in user_ids:
        if erro_auto and uid == current_user.id_hash:
            errors.append({"user_id": uid, "error": erro_auto})
            continue

        user = users_by_id.get(uid)
        if not user:
            errors.append({"user_id": uid, "error": "Usuário não encontrado."})
            continue

        # O guard que faltava. Traduzido para a semântica de lote: uma recusa
        # vira erro DAQUELE usuário, não uma exceção que derruba o lote inteiro
        # — nas rotas single ele levanta, e ali derrubar é o certo.
        try:
            await _ensure_admin_can_modify_target(db, current_user, uid)
        except HTTPException as exc:
            errors.append({"user_id": uid, "error": exc.detail})
            continue

        motivo = elegivel(user)
        if motivo:
            errors.append({"user_id": uid, "error": motivo})
            continue

        eligible.append(user)

    return eligible, errors


@router.post("/bulk/suspend", response_model=UserBulkActionResponse, summary="Suspender múltiplos usuários")
async def bulk_suspend(
    payload: UserBulkActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    eligible, errors = await _triar(
        db, current_user, payload.user_ids,
        elegivel=lambda u: (
            None if u.status == "active"
            else f"Usuário com status '{u.status}' não pode ser suspenso."
        ),
        erro_auto="Não é possível suspender a si mesmo.",
    )
    await svc.bulk_suspend(
        db, eligible,
        motivo=getattr(payload, "reason", None),
        por=current_user.username,
    )
    return UserBulkActionResponse(processed=len(eligible), errors=errors)


@router.post("/bulk/reactivate", response_model=UserBulkActionResponse, summary="Reativar múltiplos usuários")
async def bulk_reactivate(
    payload: UserBulkActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    eligible, errors = await _triar(
        db, current_user, payload.user_ids,
        elegivel=lambda u: (
            None if u.status == "suspended"
            else f"Usuário com status '{u.status}' não pode ser reativado."
        ),
        # Reativar a si mesmo é inofensivo: um admin suspenso não consegue
        # autenticar para chegar aqui.
        erro_auto=None,
    )
    await svc.bulk_reactivate(db, eligible)
    return UserBulkActionResponse(processed=len(eligible), errors=errors)


@router.post("/bulk/delete", response_model=UserBulkActionResponse, summary="Soft-delete múltiplos usuários")
async def bulk_delete(
    payload: UserBulkActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    eligible, errors = await _triar(
        db, current_user, payload.user_ids,
        elegivel=lambda u: None if u.status != "deleted" else "Usuário já está excluído.",
        erro_auto="Não é possível excluir a si mesmo.",
    )
    await svc.bulk_soft_delete(db, eligible)
    return UserBulkActionResponse(processed=len(eligible), errors=errors)


# ── Rotas com {id_hash} ─────────────────────────────────────────────────────


@router.post("/{id_hash}/suspend", response_model=UserAdminOut, summary="Suspender usuário")
async def suspend_user(
    id_hash: str,
    payload: UserSuspendRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    if id_hash == current_user.id_hash:
        raise HTTPException(status_code=400, detail="Não é possível suspender a si mesmo.")
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.status != "active":
        raise HTTPException(status_code=400, detail=f"Usuário com status '{user.status}' não pode ser suspenso.")
    return await svc.suspend_user(
        db, user,
        motivo=(payload.reason if payload else None),
        por=current_user.username,
    )


@router.post("/{id_hash}/reactivate", response_model=UserAdminOut, summary="Reativar usuário")
async def reactivate_user(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.status != "suspended":
        raise HTTPException(status_code=400, detail=f"Usuário com status '{user.status}' não pode ser reativado.")
    return await svc.reactivate_user(db, user)


@router.post("/{id_hash}/delete", response_model=UserAdminOut, summary="Soft-delete de usuário")
async def delete_user(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    if id_hash == current_user.id_hash:
        raise HTTPException(status_code=400, detail="Não é possível excluir a si mesmo.")
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.status == "deleted":
        raise HTTPException(status_code=400, detail="Usuário já está excluído.")
    return await svc.soft_delete_user(db, user)


@router.put("/{id_hash}/role", response_model=UserAdminOut, summary="Alterar role do usuário")
async def update_user_role(
    id_hash: str,
    payload: UserUpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    if id_hash == current_user.id_hash:
        raise HTTPException(status_code=400, detail="Não é possível alterar seu próprio role.")
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.status == "deleted":
        raise HTTPException(status_code=400, detail="Não é possível alterar o role de um usuário excluído.")
    if user.role == payload.role:
        raise HTTPException(status_code=400, detail=f"Usuário já possui o role '{payload.role}'.")
    return await svc.update_role(db, user, payload.role)


@router.put("/{id_hash}/executor-quota", response_model=UserAdminOut, summary="Definir cota de executores dedicados do usuário")
async def update_user_agent_quota(
    id_hash: str,
    payload: UserUpdateAgentQuotaRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if user.status == "deleted":
        raise HTTPException(status_code=400, detail="Não é possível alterar a cota de um usuário excluído.")
    return await svc.update_agent_quota(db, user, payload.agent_quota)


@router.get("/{id_hash}/executor-stats", response_model=UserExecutorStatsResponse,
            summary="Estatísticas de executores do usuário (cota, criados, acessíveis)")
async def get_user_agent_stats(
    id_hash: str,
    db: AsyncSession = Depends(get_db),
):
    """Usado pelo dialog de cota para avisar quando a redução afeta executores
    existentes. Leve — 2 SELECTs por chamada, sem efeito colateral."""
    from app.services import executor_service, user_executor_service

    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    created = await executor_service.count_user_created_executors(db, user.id_hash)
    accessible = len(await user_executor_service.get_user_accessible_agents(db, user.id_hash))

    return UserExecutorStatsResponse(
        user_id=user.id_hash,
        agent_quota=user.agent_quota,
        created=created,
        accessible=accessible,
    )


@router.post("/{id_hash}/revoke-all-executores", response_model=RevokeAllAgentsResponse,
             summary="Revoga TODOS os executores criados pelo usuário (ação destrutiva)")
@limiter.limit("3/hour")
async def revoke_all_user_agents(
    request: Request,
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Ação destrutiva: revoga cada executor com created_by == user.id_hash que
    ainda não está revogado — a mesma revogação do DELETE /executores/{id}
    (`executor_service.revogar_executor`): sai de todos os níveis da política
    (força — é uma ação de admin sobre a conta inteira), status=revoked, cert
    anulado e na blacklist, donos dos workspaces cujo nível principal esvaziou
    avisados por e-mail, `control: revoked` e WS fechado com 4403. Idempotente:
    executores já revogados são ignorados.

    Workflows em execução nos executores continuam até terminar; jobs enfileirados
    locais são descartados.
    """
    # V04: bloqueia admin de outro tenant revogando executores alheios.
    await _ensure_admin_can_modify_target(db, current_user, id_hash)
    from app.services import executor_service
    from app.services import workspace_executor_service as politica

    user = await svc.get_user(db, id_hash)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    revogacoes = await executor_service.revogar_executores_do_usuario(
        db, user, motivo="operator_revoked", desanexar=True, actor_id=current_user.id_hash,
    )
    # Workspaces impactados (para o toast/log): os dos níveis de que cada
    # executor acabou de sair ∪ os que apontam para ele pelo ponteiro legado.
    impactados: set[str] = set()
    for r in revogacoes:
        impactados |= {d["workspace_id"] for d in r.afetados}
        impactados |= await politica.workspace_ids_for_executor(db, r.executor_id)
    affected_workspaces = len(impactados)
    await db.commit()
    await executor_service.concluir_revogacoes(revogacoes)
    revoked = [r.executor_id for r in revogacoes]

    logger.info(
        "Admin '%s' executou revoke-all-executores para '%s': %d revogados, %d workspaces afetados.",
        current_user.username, user.username, len(revoked), affected_workspaces,
    )
    return RevokeAllAgentsResponse(
        user_id=id_hash,
        revoked_count=len(revoked),
        agent_ids=revoked,
        affected_workspaces=affected_workspaces,
    )
