# app/api/routers/admin_workflows_router.py
"""
Endpoints administrativos para gerenciamento de workflows.

Escopo: admin global tem override — pode ler/mutar workflow de qualquer
workspace mesmo sem membership. Isso permite ao admin:

  - Desativar workflows mal configurados (schedule quebrado, webhook
    apontando pra nada, loop infinito), impedindo dispatch, schedule
    e webhook sem precisar deletar o workflow ou pedir ao dono.

Auditoria: cada alteracao gera `logger.info` estruturado (quem, o
que, workflow, dono). Nao ha coluna persistida — historia fica no
stdout/Loki. Se compliance exigir trilha auditavel, extensao futura
adiciona tabela `audit_events`.

Trade-off consciente: o dono pode reativar via `PUT /workflows/{id}`
(update do proprio workflow em `/projects`), sobrescrevendo a acao
do admin. Comportamento aceito — se virar problema real, migrar para
coluna dedicada `admin_disabled_at` em iteracao futura.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.core.scheduling.hooks import sync_schedules_with_workflow_state
from app.core.utils.logger import get_logger
from app.crud.workflow_crud import WorkflowCRUD

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin/workflows",
    tags=["admin", "workflows"],
    dependencies=[Depends(require_admin)],
)


class SetWorkflowStatusBody(BaseModel):
    flag_ative: bool


@router.put(
    "/{id_hash}/status",
    summary="[Admin] Alterar flag_ative de um workflow (bypassa membership de workspace)",
)
async def set_workflow_status(
    id_hash: str,
    payload: SetWorkflowStatusBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Alterna `Workflow.flag_ative`. Diferente do `PUT /workflows/{id}`
    do usuario dono, este endpoint NAO checa `_has_min_workspace_role`
    — admin global tem override em qualquer workspace.
    """
    wf = await WorkflowCRUD(db).get_by_hash(id_hash)
    if wf is None or wf.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Workflow não encontrado.")

    old_value = bool(wf.flag_ative)
    wf.flag_ative = payload.flag_ative
    await db.commit()

    if old_value != payload.flag_ative:
        # Desativar o workflow sem desligar seus agendamentos deixava o
        # AsyncScheduler disparando em loop contra um workflow que recusa
        # executar. Best-effort: falhar aqui nao desfaz a decisao do admin, que
        # ja esta commitada — e o proprio scheduler ignora schedule de workflow
        # inativo desde o JOIN em `_tick`.
        try:
            await sync_schedules_with_workflow_state(wf, db)
        except Exception as exc:
            logger.warning(
                "Falha ao sincronizar agendamentos do workflow '%s' apos mudanca de flag_ative: %s",
                wf.id_hash, exc,
            )

        logger.info(
            "Admin '%s' alterou flag_ative de workflow '%s' (dono='%s') de %s para %s",
            current_user.username,
            wf.id_hash,
            wf.created_by_id,
            old_value,
            payload.flag_ative,
        )

    return {"id_hash": wf.id_hash, "flag_ative": bool(wf.flag_ative)}
