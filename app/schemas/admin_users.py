# app/schemas/admin_users.py
"""Schemas Pydantic para o módulo administrativo de gestão de usuários."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class UserAdminOut(BaseModel):
    """Representação completa de um usuário no painel admin."""
    id_hash: str
    username: str
    email: str
    status: str
    role: str
    agent_quota: int = 0
    workspace_id: Optional[str] = None
    last_login_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Resposta paginada de listagem de usuários."""
    items: list[UserAdminOut]
    total: int
    limit: int
    offset: int


class UserSuspendRequest(BaseModel):
    """Payload opcional para suspensão com motivo."""
    reason: Optional[str] = Field(None, max_length=500)


class UserBulkActionRequest(BaseModel):
    """Payload para ações em massa (suspender, reativar, deletar)."""
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    reason: Optional[str] = Field(None, max_length=500)


class UserBulkActionResponse(BaseModel):
    """Resposta de ações em massa com contagem e erros individuais."""
    processed: int
    errors: list[dict]


class UserUpdateRoleRequest(BaseModel):
    """Payload para alteração de role."""
    role: str = Field(..., pattern=r"^(admin|user)$")


class UserUpdateAgentQuotaRequest(BaseModel):
    """Payload para alteração da cota de executores dedicados do usuário."""
    agent_quota: int = Field(..., ge=0, le=100)


class UserExecutorStatsResponse(BaseModel):
    """Estatística de executores do usuário — usada pelo dialog de cota no admin."""
    user_id:     str
    agent_quota: int
    created:     int  # criados pelo user e ainda ativos (não revogados, não soft-deletados)
    accessible:  int  # acessíveis (pool + workspace + atribuição direta)


class RevokeAllAgentsResponse(BaseModel):
    """Resultado da ação destrutiva de revogar todos os executores criados pelo user."""
    user_id:       str
    revoked_count: int
    agent_ids:     list[str]
    affected_workspaces: int  # workspaces com target_executor_id apontando aos revogados
