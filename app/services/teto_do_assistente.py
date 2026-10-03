# app/services/teto_do_assistente.py
"""A person's assistant plan and token ceiling.

The core knows no plan at all. Without an extension that brings them, nobody has
a plan, and the ceiling is the same for everyone: the installation's
(`ASSISTENTE_TETO_DE_TOKENS_POR_DIA`, in `app/mcp/cotas.py`). With a plans
extension (`app/extensoes`), it is the extension that answers — and the conversation quota, the
two `/estado` endpoints and the screen's donut all go through here, so that the same ceiling
comes from the same place.
"""
from __future__ import annotations

from app.extensoes import registro
from app.mcp import cotas


async def plano_e_teto(
    user_id: str, *, db=None, redis=None,
) -> tuple[str | None, int]:
    """This person's plan (or `None`, with no plans) and 24 h window ceiling."""
    resolver = registro().plano_e_teto
    if resolver is None:
        # Read from the module on each call, not imported: the tests swap the
        # value in `cotas`, and the plans extension starts from the same number.
        return None, cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    return await resolver(user_id, db=db, redis=redis)


async def teto_de(user_id: str, *, db=None, redis=None) -> int:
    """Only the ceiling — what the conversation loop checks before each turn."""
    _, teto = await plano_e_teto(user_id, db=db, redis=redis)
    return teto


def assinaturas_ativas() -> bool:
    """Whether the installation sells plans: that is what decides whether the screen offers them
    when the quota runs out."""
    return registro().assinaturas_ativas()
