# app/core/rbac.py
"""
Granular RBAC (Role-Based Access Control) for Atlas Studio.

Role hierarchy (lowest to highest):
  viewer   → read workflows, observability, runs
  editor   → viewer + create/edit/delete workflows and credentials
  operator → editor + execute workflows and manage schedules
  admin    → operator + workers, node templates, users, settings

Usage in routers:
    from app.core.rbac import require_role, Role

    @router.post("/execute")
    async def execute(user=Depends(require_role(Role.OPERATOR))):
        ...
"""
from enum import IntEnum
from fastapi import Depends, HTTPException


class Role(IntEnum):
    VIEWER   = 1
    EDITOR   = 2
    OPERATOR = 3
    ADMIN    = 4


# Role constants as strings — use for _has_min_workspace_role and manual guards
ROLE_VIEWER   = "viewer"
ROLE_EDITOR   = "editor"
ROLE_OPERATOR = "operator"
ROLE_ADMIN    = "admin"
ROLE_OWNER    = "owner"

# String → numeric level mapping
ROLE_LEVELS: dict[str, Role] = {
    ROLE_VIEWER:   Role.VIEWER,
    ROLE_EDITOR:   Role.EDITOR,
    ROLE_OPERATOR: Role.OPERATOR,
    ROLE_ADMIN:    Role.ADMIN,
}


def require_role(minimum: Role):
    """
    FastAPI dependency factory.
    Ensures the authenticated user has at least the specified role.

    Example:
        async def my_endpoint(user=Depends(require_role(Role.EDITOR))):
    """
    from app.api.dependencies import get_current_user  # lazy — evita import circular

    async def _check(current_user=Depends(get_current_user)):
        user_role_str = getattr(current_user, "role", "viewer") or "viewer"
        user_level    = ROLE_LEVELS.get(user_role_str, Role.VIEWER)
        if user_level < minimum:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Permissão insuficiente. "
                    f"Requer role '{minimum.name.lower()}' ou superior "
                    f"(seu role: '{user_role_str}')."
                ),
            )
        return current_user
    return _check
