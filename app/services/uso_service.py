# app/services/uso_service.py
"""Gravar o que cada volta do assistente consumiu.

**Este módulo existe porque o dado já chegava e era jogado fora.** O provedor
devolve, a cada resposta, quantos tokens entraram, quantos saíram e quanto
aquilo custou; o laço somava tudo, escrevia uma linha de log e descartava.
Nenhuma pergunta de dinheiro — quanto custa cada pessoa, se o que se cobra se
paga, o que a troca de modelo faria com a conta — tem resposta sem isto.

Duas regras que fazem esta gravação ser segura de acrescentar ao laço:

1. **Nunca levanta.** Uma falha ao registrar não pode derrubar uma conversa que
   já aconteceu e que a plataforma já pagou. É o mesmo raciocínio de
   `cotas.cobrar_tokens_do_assistente`: o lado certo para errar é perder a
   anotação, nunca o trabalho.
2. **Sessão própria.** O laço do assistente não tem sessão de request (ele roda
   dentro de um gerador SSE, ver `assistente_editor_router.py`), então a sessão é aberta
   aqui e fechada aqui.
"""
from __future__ import annotations

from decimal import Decimal

from app.core.utils.logger import get_logger
from app.mcp import infra
from app.models.uso_do_assistente import UsoDoAssistente

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
    """Uma linha por volta. Silencioso no sucesso, silencioso na falha.

    Volta sem token nenhum não vira linha: ela existe quando o provedor
    respondeu sem consumir nada (recusa imediata, erro antes de gerar), e uma
    linha de zeros só distorceria a mediana para baixo.
    """
    if not user_id or not modelo or (entrada <= 0 and saida <= 0):
        return
    try:
        async with infra.sessao() as db:
            db.add(UsoDoAssistente(
                user_id=user_id,
                modelo=modelo,
                superficie=superficie,
                entrada=int(entrada),
                saida=int(saida),
                cache_leitura=int(cache_leitura),
                raciocinio=int(raciocinio),
                # Por string: `Decimal(float)` arrasta o erro binário do float
                # para dentro do decimal, que é justamente o que a coluna
                # NUMERIC existe para não ter.
                custo_usd=Decimal(str(round(float(custo_usd or 0.0), 6))),
            ))
            await db.commit()
    except Exception as exc:  # pragma: no cover - depende do banco
        logger.warning(
            "Uso: falha ao registrar a volta do usuário %s (%s). A conversa segue.",
            user_id, exc.__class__.__name__,
        )
