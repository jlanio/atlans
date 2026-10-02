# app/core/system_config.py
"""
Helpers compartilhados para ler e escrever configuracoes globais no
SystemConfig (chave/valor JSON persistido no DB).

Extraido de health_router.py para reuso por disabled_nodes_service e
qualquer outro modulo que precise persistir config admin.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig


async def get_config(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Le o valor JSON da chave. Retorna `default` se nao existir."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def set_config(db: AsyncSession, key: str, value: Any) -> None:
    """Upsert no SystemConfig. Faz commit ao final."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))
    await db.commit()
