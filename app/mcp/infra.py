# app/mcp/infra.py
"""
Os dois pontos de contato do MCP com a infraestrutura — e os dois pontos de
`patch` dos testes.

Sessão de banco e pool Redis são obtidos SEMPRE por aqui, nunca importando
`get_session_async`/`get_redis_pool` direto num módulo do MCP. A razão é
prática: `patch("app.mcp.infra.sessao")` e `patch("app.mcp.infra.redis_ou_none")`
trocam a infraestrutura inteira do servidor de uma vez, e nenhum teste precisa
de Postgres ou Redis de verdade. Se um módulo importasse a função original,
esse `patch` passaria ao largo dele.

Consequência para quem escreve tool: importe o MÓDULO (`from app.mcp import
infra`) e chame `infra.sessao()`; um `from app.mcp.infra import sessao` no topo
congela a referência e escapa do patch.
"""
from __future__ import annotations

from app.core.db import get_session_async
from app.core.redis import get_redis_pool, new_pubsub_client

# Sessão de banco: context manager assíncrono que faz rollback no `finally` —
# quem escreve precisa commitar por conta própria.
sessao = get_session_async

# `new_pubsub_client` (cliente Redis dedicado para uma assinatura pub/sub longa,
# como a espera de uma execução) é re-exportado daqui pelo mesmo motivo: um
# ponto só de troca nos testes.


def redis_ou_none():
    """O pool Redis, ou `None` quando ele não foi inicializado.

    `get_redis_pool()` levanta `RuntimeError` fora do lifespan (testes, scripts,
    um worker que subiu sem `init_redis`). Nada no MCP deve morrer por isso: as
    cotas degradam abertas e o carimbo de último uso simplesmente não acontece.
    Redis fora do ar é falha transitória, não modo de operação.
    """
    try:
        return get_redis_pool()
    except RuntimeError:
        return None


__all__ = ["sessao", "redis_ou_none", "new_pubsub_client"]
