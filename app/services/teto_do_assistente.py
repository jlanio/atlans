# app/services/teto_do_assistente.py
"""O plano e o teto de tokens do assistente de uma pessoa.

O núcleo não conhece plano nenhum. Sem extensão que os traga, ninguém tem
plano, e o teto é o mesmo para todos: o da instalação
(`ASSISTENTE_TETO_DE_TOKENS_POR_DIA`, em `app/mcp/cotas.py`). Com uma extensão
de planos (`app/extensoes`), quem responde é ela — e a cota da conversa, os
dois `/estado` e o donut da tela passam todos por aqui, para que o mesmo teto
saia do mesmo lugar.
"""
from __future__ import annotations

from app.extensoes import registro
from app.mcp import cotas


async def plano_e_teto(
    user_id: str, *, db=None, redis=None,
) -> tuple[str | None, int]:
    """O plano (ou `None`, sem planos) e o teto da janela de 24 h desta pessoa."""
    resolver = registro().plano_e_teto
    if resolver is None:
        # Lido do módulo a cada chamada, e não importado: os testes trocam o
        # valor em `cotas`, e a extensão de planos parte do mesmo número.
        return None, cotas.TETO_DE_TOKENS_DO_ASSISTENTE_POR_DIA
    return await resolver(user_id, db=db, redis=redis)


async def teto_de(user_id: str, *, db=None, redis=None) -> int:
    """Só o teto — o que o laço da conversa confere antes de cada turno."""
    _, teto = await plano_e_teto(user_id, db=db, redis=redis)
    return teto


def assinaturas_ativas() -> bool:
    """Se a instalação vende planos: é o que decide se a tela os oferece
    quando a cota estoura."""
    return registro().assinaturas_ativas()
