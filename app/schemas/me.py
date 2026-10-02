# app/schemas/me.py
"""Schemas do escopo "Meu" — recortes por PESSOA, entre todos os workspaces
dela. Hoje só os agendamentos (painel "Meu → Agendamentos" da Home)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgendamentoMeu(BaseModel):
    """Um agendamento na lista da pessoa. Um por linha (não um por fluxo, como o
    resumo de Projetos): a mesma rotina pode ter mais de um.

    `next_run_at` nulo tem dois sentidos que a web distingue por `active`:
    pausado (o agendador não calcula próxima para inativo) ou recém-criado (o
    agendador preenche em até 30 s). "Pausado" também tem duas causas — `active`
    do próprio agendamento ou `flag_ative` do workflow desligado —, por isso os
    dois campos vêm juntos.
    """
    job_id: str
    id_hash: str
    active: bool
    strategy: str
    cron_expression: Optional[str] = None
    interval: Optional[int] = None
    unit: Optional[str] = None
    rrule_expression: Optional[str] = None
    timezone: Optional[str] = None
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    retry_count: int = 0
    workflow_id: str
    workflow_name: str
    flag_ative: bool
    workspace_id: Optional[str] = None
    # Proveniência do fluxo (usuario|assistente), para o selo "assistente" no
    # painel da Home. Vem do JOIN com Workflow (coluna do PR da origem); default
    # "usuario" porque todo campo novo do schema tem default.
    origem: str = "usuario"
