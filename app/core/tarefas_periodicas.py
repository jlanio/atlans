# app/core/tarefas_periodicas.py
"""
Laço periódico com lock no Redis: o esqueleto das tarefas de fundo do lifespan.

A limpeza de artefatos, a reconciliação do storage, a verificação das fontes e as
tarefas das extensões são o mesmo laço — dorme o intervalo, tenta o
lock daquele intervalo e, se pegou, trabalha. O lock existe porque a API roda com
`--workers N` e cada worker sobe as mesmas tarefas: sem ele, cada varredura
rodaria N vezes por intervalo.

Uso:
    from app.core.tarefas_periodicas import laco_periodico
    await laco_periodico("Cleanup de artefatos", 3600, purge_expired_artifacts,
                         lock="artifact_cleanup:lock")
"""
import asyncio
from typing import Awaitable, Callable

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


async def adquirir_lock(chave: str, ttl_s: float) -> bool:
    """Lock `SET NX EX` no pool Redis global; True = este worker faz o trabalho.

    O TTL é o que segura o lock: ninguém o solta, ele vence (mínimo de 1 s).
    Redis fora (ou o pool ainda não inicializado): prossegue SEM lock — as
    rotinas protegidas são idempotentes, então o pior caso é trabalho repetido
    por mais de um worker, nunca trabalho a menos porque o Redis caiu.
    """
    try:
        from app.core.redis import get_redis_pool

        return bool(await get_redis_pool().set(chave, "1", nx=True, ex=max(1, int(ttl_s))))
    except Exception as exc:
        logger.warning("Falha ao adquirir o lock %s no Redis — prosseguindo sem lock: %s", chave, exc)
        return True


async def soltar_lock(chave: str) -> None:
    """Devolve o lock antes do TTL — para quem o pegou e FALHOU: sem isto, a
    próxima subida (a recriação da API logo depois do `alembic upgrade head`,
    por exemplo) pulava o trabalho por até 10 minutos. Redis fora: nada a soltar."""
    try:
        from app.core.redis import get_redis_pool

        await get_redis_pool().delete(chave)
    except Exception as exc:
        logger.debug("Falha ao soltar o lock %s no Redis: %s", chave, exc)


async def laco_periodico(
    nome: str,
    intervalo_s: float,
    trabalho: Callable[[], Awaitable[object]],
    *,
    lock: str | None = None,
) -> None:
    """Chama `trabalho()` a cada `intervalo_s` segundos, até ser cancelado.

    Com `lock`, cada volta só trabalha no worker que pegar o lock (TTL = o
    intervalo); os outros pulam aquela volta. Um erro no trabalho é logado e o
    laço segue. O cancelamento (shutdown do lifespan) encerra o laço, que
    termina normalmente.
    """
    logger.info("%s: iniciado (intervalo=%ss).", nome, intervalo_s)
    while True:
        try:
            await asyncio.sleep(intervalo_s)
            if lock is None or await adquirir_lock(lock, intervalo_s):
                await trabalho()
            else:
                logger.debug("%s: outro worker pegou o lock deste intervalo — pulando.", nome)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("%s: erro no ciclo: %s", nome, exc, exc_info=True)
    logger.info("%s: encerrado.", nome)
