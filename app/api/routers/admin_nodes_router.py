# app/api/routers/admin_nodes_router.py
"""
Admin endpoints to enable/disable platform nodes.

- GET    /admin/nodes              -> lists ALL registry nodes with status
- PATCH  /admin/nodes/{name}       -> {enabled: bool, reason?: str}

Persistence: SystemConfig key="disabled_nodes". See
app/services/disabled_nodes_service.py for the contract.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db, require_admin
from app.services import disabled_nodes_service as svc
from flow.registry import NODE_REGISTRY

router = APIRouter(
    prefix="/admin/nodes",
    tags=["admin-nodes"],
    dependencies=[Depends(require_admin)],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class NodeAdminEntry(BaseModel):
    name: str
    alias: str
    type: str | None = None
    enabled: bool
    reason: str | None = None
    disabled_at: str | None = None
    disabled_by: str | None = None


class NodeToggleBody(BaseModel):
    enabled: bool
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def _validate_reason(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[NodeAdminEntry])
async def list_admin_nodes(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists ALL registry nodes with their current status.

    Even if disabled, the node shows up here — unlike the public /nodes,
    which filters out disabled ones so they are not shown in the drawer.
    """
    disabled = await svc.list_disabled(db)
    out: list[dict[str, Any]] = []
    for name, cls in NODE_REGISTRY.items():
        info = cls.description() or {}
        meta = disabled.get(name)
        out.append({
            "name": info.get("name", name),
            "alias": info.get("alias") or name,
            "type": info.get("type"),
            "enabled": meta is None,
            "reason": (meta or {}).get("reason"),
            "disabled_at": (meta or {}).get("disabled_at"),
            "disabled_by": (meta or {}).get("disabled_by"),
        })
    # Stable order: by type (in drawer order) and then alphabetical.
    _TYPE_ORDER = {"trigger": 0, "action": 1, "datasource": 2, "control": 3, "spatial": 4, "output": 5}
    out.sort(key=lambda e: (_TYPE_ORDER.get(e.get("type") or "", 99), (e.get("alias") or "").lower()))
    return out


@router.patch("/{name}", response_model=NodeAdminEntry)
async def patch_admin_node(
    name: str,
    body: NodeToggleBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Enables or disables a node by name.

    - Disabling requires `reason` (>=5 chars after strip).
    - Enabling (`enabled: True`) ignores `reason`.
    - The name must exist in NODE_REGISTRY (otherwise 404 — avoids garbage in
      SystemConfig from wrong names).
    """
    if name not in NODE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{name}' nao existe no registry.",
        )

    if body.enabled:
        await svc.set_enabled(db, name)
    else:
        if not body.reason or len(body.reason) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para desabilitar um node, informe 'reason' com pelo menos 5 caracteres.",
            )
        await svc.set_disabled(db, name, by=current_user.id_hash, reason=body.reason)

    # Resposta refletindo o novo estado
    cls = NODE_REGISTRY[name]
    info = cls.description() or {}
    disabled = await svc.list_disabled(db)
    meta = disabled.get(name)
    return {
        "name": info.get("name", name),
        "alias": info.get("alias") or name,
        "type": info.get("type"),
        "enabled": meta is None,
        "reason": (meta or {}).get("reason"),
        "disabled_at": (meta or {}).get("disabled_at"),
        "disabled_by": (meta or {}).get("disabled_by"),
    }
