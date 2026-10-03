# app/schemas/workspace.py
"""
Workspace schemas shared between REST and the services.

`WorkspaceOut` was born inside `workspace_router.py`. It moved out because the
user's workspace listing became a service (`workspace_service.py`) and a
service cannot import a router — the dependency direction is router →
service, never the reverse (and the router pulls in `app.api.dependencies`,
which pulls in half the world). The router keeps re-exporting the name, so
whoever imported `WorkspaceOut` from there keeps working.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_hash: str
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    is_default: bool = False
    my_role: Optional[str] = None  # "owner" | "viewer" | "editor" | "operator" | "admin"
