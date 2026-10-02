from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkflowGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    workflow_ids: List[str] = Field(default_factory=list)


class WorkflowGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    workflow_ids: Optional[List[str]] = None


class WorkflowGroupReorder(BaseModel):
    """Nova ordem dos grupos, da primeira posicao para a ultima.

    A posicao vem do INDICE da lista, e nao de um numero enviado pelo cliente:
    assim nao existe estado intermediario com duas posicoes iguais, nem sobra
    para o cliente inventar a numeracao.
    """
    group_ids: List[str] = Field(..., min_length=1)


class WorkflowGroupRead(BaseModel):
    id: int
    id_hash: str
    name: str
    description: Optional[str]
    workspace_id: Optional[str]
    position: int = 0
    # Todos os workflows nao excluidos do grupo (inativos inclusive) — e o que
    # a tela de Projetos mostra, e um inativo continua na lista. Contar so os
    # ativos fazia "3 workflows" virar "2" quando um era desativado.
    workflow_count: int = 0
    # So os com `flag_ative`; a tela mostra "3 workflows · 2 ativos".
    active_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
