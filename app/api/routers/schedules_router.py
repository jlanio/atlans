from fastapi import APIRouter, Depends, Request

from app.schemas.schedule import ScheduleRead, ScheduleUpdate
from app.services.schedule_service import ScheduleService
from app.api.dependencies import (
    get_schedule_service,
    workflow_com_papel,
)
from app.core.rate_limiter import limiter
from app.core.rbac import ROLE_OPERATOR

router = APIRouter(
    prefix="/workflows/{id_hash}/schedules",
    tags=["schedules"]
)


# Papel 'operator' ou superior. Agendar é executar: um schedule com intervalo
# de 1 minuto dispara o workflow com as credenciais do dono indefinidamente.
# Estas rotas já dependeram só do pertencimento ao workspace — e um membro
# 'viewer' criava agendamentos e apagava os de produção, exatamente o que o 403
# de POST /workflows/{id}/execute existe para impedir. O rbac.py já define
# operator como quem "executa workflows e gerencia agendamentos".
#
# Hoje só resta o PUT (pausar/retomar, na Home): os agendamentos nascem do nó
# ScheduleTrigger ao salvar o workflow, e o MCP usa o ScheduleService direto.
# Listar, criar e apagar por aqui saíram — não tinham chamador.
_GERENCIAR_AGENDAMENTOS = workflow_com_papel(
    ROLE_OPERATOR, "Requer role 'operator' ou superior para gerenciar agendamentos.",
)


@router.put("/{job_id}", response_model=ScheduleRead)
@limiter.limit("20/minute")
async def update_schedule(
    request: Request,
    job_id: str,
    schedule_in: ScheduleUpdate,
    service: ScheduleService = Depends(get_schedule_service),
    wf=Depends(_GERENCIAR_AGENDAMENTOS),
):
    return await service.update_schedule(job_id, schedule_in, owner_workflow_hash=wf.id_hash)
