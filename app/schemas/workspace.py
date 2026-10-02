# app/schemas/workspace.py
"""
Schemas de Workspace compartilhados entre a REST e os services.

`WorkspaceOut` nasceu dentro de `workspace_router.py`. Saiu de lá porque a
listagem de workspaces do usuário virou service (`workspace_service.py`) e um
service não pode importar um router — a direção de dependência é router →
service, nunca o inverso (e o router puxa `app.api.dependencies`, que puxa
meio mundo). O router continua re-exportando o nome, então quem importava
`WorkspaceOut` dali segue funcionando.
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
