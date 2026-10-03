# app/core/system_config.py
"""
Shared helpers to read and write global settings in
SystemConfig (JSON key/value persisted in the DB).

Extracted from health_router.py for reuse by disabled_nodes_service and
any other module that needs to persist admin config.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig


async def get_config(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Read the key's JSON value. Returns `default` if it does not exist."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def set_config(db: AsyncSession, key: str, value: Any) -> None:
    """Upsert into SystemConfig. Commits at the end."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))
    await db.commit()
