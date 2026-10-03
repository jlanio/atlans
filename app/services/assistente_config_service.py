# app/services/assistente_config_service.py
"""Which model the assistant uses — and who is in charge of that.

**Env as the floor, database on top.** `ASSISTENTE_MODELO` is still the default:
a new installation comes up working without anyone configuring anything. If there
is a choice saved by the admin, it wins. It is the same precedence as the plan
prices, only with the database in front — because switching models is an
operations decision, and requiring a deploy for it is what kept the operator from
switching.

There is no new table: `SystemConfig` is already the system's global
configuration keyring (`app/core/system_config.py`), with the same requirements —
one row, read a lot and written rarely.

**The cache exists because this is read on every conversation**, and the
assistant loop has no request session (it runs inside an SSE generator). The
read, the cache and the write are those of `app/core/config_em_cache.py` — Redis
with a short TTL, its own session on a miss, failing open: Redis down means
reading the database every time, never means being left without a model. Only
what belongs to the model stays here: the shape of a valid id.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ASSISTENTE_MODELO
from app.core.config_em_cache import ConfigEmCache

CHAVE = "assistente.modelo"
_CACHE = "assistente:modelo"
_TTL_S = 300

# A model id is the name in the provider's catalog: `fornecedor/nome[:variante]`
# on OpenRouter, `qwen3:14b` on Ollama. The validation is of SHAPE, not of
# existence: what exists is said by the provider's catalog, queried in the
# route. It serves to stop the obvious accident — a field pasted with a space,
# a whole URL, an empty text — before it turns into an error in every conversation.
TAMANHO_MAXIMO = 120


def formato_valido(modelo: str) -> bool:
    if not modelo or len(modelo) > TAMANHO_MAXIMO:
        return False
    if any(c.isspace() for c in modelo) or "://" in modelo:
        return False
    # A slash at the start, at the end or doubled is a bad paste.
    return all(modelo.split("/"))


def _ler(valor: Any) -> str | None:
    """The model from the saved row, if it has the shape of an id — otherwise, nothing (the default)."""
    if isinstance(valor, dict):
        valor = valor.get("modelo")
    if isinstance(valor, str) and formato_valido(valor):
        return valor
    return None


_CONFIG: ConfigEmCache[str] = ConfigEmCache(
    chave=CHAVE,
    chave_cache=_CACHE,
    ttl_s=_TTL_S,
    campo="modelo",
    ler=_ler,
    padrao=lambda: ASSISTENTE_MODELO,
    rotulo="Assistente",
)


async def modelo_em_uso(*, db: AsyncSession | None = None, redis=None) -> str:
    """The model in effect now. Never returns empty.

    Any failure — Redis, database, corrupted row — falls back to the
    environment's default. Being left without a model would mean the whole
    assistant down because of a setting; the default is always better than nothing.
    """
    return await _CONFIG.em_uso(db=db, redis=redis)


async def definir_modelo(db: AsyncSession, modelo: str | None, *, por: str | None = None,
                         redis=None) -> dict[str, Any]:
    """Saves the admin's choice. `None` goes back to the environment's default.

    Writes the who-and-when stamp together with the value and pins the new model
    in the cache right away (`ConfigEmCache.definir`).
    """
    if modelo is not None and not formato_valido(modelo):
        raise ValueError(
            "Id de modelo inválido: o nome no catálogo do provedor (ex.: `fornecedor/nome` "
            "no OpenRouter), sem espaços nem URL."
        )
    await _CONFIG.definir(db, modelo, por=por, redis=redis)
    return await situacao(db=db)


async def situacao(*, db: AsyncSession) -> dict[str, Any]:
    """What the admin screen shows: the model, where it came from, and the stamp.

    `origem` is not decoration: "from the environment" and "set here" call for
    different buttons (one offers to set, the other offers to go back to the
    default), and without the field the screen would have to guess by comparing
    strings.
    """
    carimbo = await _CONFIG.carimbo(db)
    if carimbo is not None:
        return {
            "modelo": carimbo.valor,
            "origem": "banco",
            "definido_por": carimbo.por,
            "definido_em": carimbo.em,
            "padrao_do_ambiente": ASSISTENTE_MODELO,
        }
    return {
        "modelo": ASSISTENTE_MODELO,
        "origem": "ambiente",
        "definido_por": None,
        "definido_em": None,
        "padrao_do_ambiente": ASSISTENTE_MODELO,
    }
