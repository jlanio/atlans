# app/core/tarefas_periodicas.py
"""
Periodic loop with a Redis lock: the skeleton of the lifespan's background tasks.

Artifact cleanup, storage reconciliation, source verification and the
extensions' tasks are the same loop — sleep the interval, try the lock
for that interval and, if it got it, do the work. The lock exists because the API
runs with `--workers N` and every worker starts the same tasks: without it, each
sweep would run N times per interval.

Usage:
    from app.core.tarefas_periodicas import laco_periodico
    await laco_periodico("Cleanup de artefatos", 3600, purge_expired_artifacts,
                         lock="artifact_cleanup:lock")
"""
import asyncio
from typing import Awaitable, Callable

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


async def adquirir_lock(chave: str, ttl_s: float) -> bool:
    """`SET NX EX` lock on the global Redis pool; True = this worker does the work.

    The TTL is what holds the lock: nobody releases it, it expires (minimum of 1 s).
    Redis down (or the pool not yet initialized): proceeds WITHOUT a lock — the
    protected routines are idempotent, so the worst case is work repeated by
    more than one worker, never less work because Redis went down.
    """
    try:
        from app.core.redis import get_redis_pool

        return bool(await get_redis_pool().set(chave, "1", nx=True, ex=max(1, int(ttl_s))))
    except Exception as exc:
        logger.warning("Falha ao adquirir o lock %s no Redis — prosseguindo sem lock: %s", chave, exc)
        return True


async def soltar_lock(chave: str) -> None:
    """Release the lock before the TTL — for whoever took it and FAILED: without this,
    the next startup (the API recreation right after `alembic upgrade head`,
    for example) skipped the work for up to 10 minutes. Redis down: nothing to release."""
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
    """Call `trabalho()` every `intervalo_s` seconds, until cancelled.

    With `lock`, each round only works on the worker that takes the lock (TTL = the
    interval); the others skip that round. An error in the work is logged and the
    loop goes on. Cancellation (lifespan shutdown) ends the loop, which
    finishes normally.
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
