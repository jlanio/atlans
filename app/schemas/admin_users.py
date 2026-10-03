# app/schemas/admin_users.py
"""Pydantic schemas for the user management admin module."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class UserAdminOut(BaseModel):
    """Full representation of a user in the admin panel."""
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
    """Paginated user listing response."""
    items: list[UserAdminOut]
    total: int
    limit: int
    offset: int


class UserSuspendRequest(BaseModel):
    """Optional payload for suspension with a reason."""
    reason: Optional[str] = Field(None, max_length=500)


class UserBulkActionRequest(BaseModel):
    """Payload for bulk actions (suspend, reactivate, delete)."""
    user_ids: list[str] = Field(..., min_length=1, max_length=50)
    reason: Optional[str] = Field(None, max_length=500)


class UserBulkActionResponse(BaseModel):
    """Bulk action response with a count and individual errors."""
    processed: int
    errors: list[dict]


class UserUpdateRoleRequest(BaseModel):
    """Payload for changing the role."""
    role: str = Field(..., pattern=r"^(admin|user)$")


class UserUpdateAgentQuotaRequest(BaseModel):
    """Payload for changing the user's dedicated executor quota."""
    agent_quota: int = Field(..., ge=0, le=100)


class UserExecutorStatsResponse(BaseModel):
    """The user's executor statistics — used by the quota dialog in the admin."""
    user_id:     str
    agent_quota: int
    created:     int  # created by the user and still active (not revoked, not soft-deleted)
    accessible:  int  # accessible (pool + workspace + direct assignment)


class RevokeAllAgentsResponse(BaseModel):
    """Result of the destructive action of revoking all executors created by the user."""
    user_id:       str
    revoked_count: int
    agent_ids:     list[str]
    affected_workspaces: int  # workspaces with target_executor_id pointing to the revoked ones
