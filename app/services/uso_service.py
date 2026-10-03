# app/services/uso_service.py
"""Recording what each assistant round consumed.

**This module exists because the data was already arriving and being thrown away.** The provider
returns, with each response, how many tokens went in, how many came out and how much
it cost; the loop added it all up, wrote a log line and discarded it.
No money question — how much each person costs, whether what is charged pays
for itself, what a model switch would do to the bill — has an answer without this.

Two rules that make this recording safe to add to the loop:

1. **It never raises.** A failure to record cannot bring down a conversation that
   has already happened and that the platform has already paid for. It is the same reasoning as
   `cotas.cobrar_tokens_do_assistente`: the right side to err on is losing the
   note, never the work.
2. **Its own session.** The assistant loop has no request session (it runs
   inside an SSE generator, see `assistente_editor_router.py`), so the session is opened
   here and closed here.
"""
from __future__ import annotations

from decimal import Decimal

from app.core.utils.logger import get_logger
from app.mcp import infra
from app.models.uso_do_assistente import AssistantUsage

logger = get_logger(__name__)


async def registrar_volta(
    *,
    user_id: str,
    modelo: str,
    superficie: str | None,
    entrada: int,
    saida: int,
    cache_leitura: int = 0,
    raciocinio: int = 0,
    custo_usd: float = 0.0,
) -> None:
    """One row per round. Silent on success, silent on failure.

    A round with no tokens at all does not become a row: it exists when the provider
    answered without consuming anything (immediate refusal, error before generating), and a
    row of zeros would only skew the median downward.
    """
    if not user_id or not modelo or (entrada <= 0 and saida <= 0):
        return
    try:
        async with infra.sessao() as db:
            db.add(AssistantUsage(
                user_id=user_id,
                modelo=modelo,
                superficie=superficie,
                entrada=int(entrada),
                saida=int(saida),
                cache_leitura=int(cache_leitura),
                raciocinio=int(raciocinio),
                # Via string: `Decimal(float)` drags the float's binary error
                # into the decimal, which is exactly what the NUMERIC
                # column exists to avoid.
                custo_usd=Decimal(str(round(float(custo_usd or 0.0), 6))),
            ))
            await db.commit()
    except Exception as exc:  # pragma: no cover - depends on the database
        logger.warning(
            "Uso: falha ao registrar a volta do usuário %s (%s). A conversa segue.",
            user_id, exc.__class__.__name__,
        )
