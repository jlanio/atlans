# app/services/amostras_de_dados.py
"""Admin switch for the data samples of the editor's Entradas/Saídas panels.

With it on (the default), a run started from the editor asks the executor for a
sample of each node's outputs (`data_preview` in the envelope, see
docs/specs/node-data-panels.md). An installation whose data must not leave the
executor, even as a sample, turns it off here.

Stored as a `SystemConfig` row, the same pattern as `artifact_retention_days`. A
missing row means on. Read on every execute request (one lookup by primary
key), with no cache, so turning it off applies to the very next run.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig

CONFIG_KEY = "node_data_preview_enabled"


def _as_bool(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.strip().lower() not in {"false", "0", "no", "off", ""}
    return bool(valor)


async def amostras_habilitadas(db: AsyncSession) -> bool:
    """Whether the installation allows data samples. On when never configured."""
    cfg = await db.get(SystemConfig, CONFIG_KEY)
    return _as_bool(cfg.value if cfg is not None else None)


async def definir_amostras(db: AsyncSession, enabled: bool) -> bool:
    cfg = await db.get(SystemConfig, CONFIG_KEY)
    if cfg is None:
        db.add(SystemConfig(key=CONFIG_KEY, value=bool(enabled)))
    else:
        cfg.value = bool(enabled)
    await db.commit()
    return bool(enabled)
