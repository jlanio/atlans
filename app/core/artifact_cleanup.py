# app/core/artifact_cleanup.py
"""
Periodic cleanup loop for expired artifacts.

Runs as a background task in the API lifespan.
Interval: ARTIFACT_CLEANUP_INTERVAL seconds (default: 3600 = 1h).

Distributed Redis lock (`laco_periodico`, with TTL = the interval) — ensures that
only one uvicorn worker runs the cleanup per interval, avoiding redundant
queries with --workers N.
"""
from app.core.utils.logger import get_logger
import os

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.tarefas_periodicas import laco_periodico
from app.core.utils.datetime_utils import utc_now_naive
from app.models.artifact import Artifact
from app.services.remocao_de_artefatos import remover_artefatos

logger = get_logger(__name__)

_CLEANUP_INTERVAL = int(os.getenv("ARTIFACT_CLEANUP_INTERVAL", "3600"))
_CLEANUP_LOCK_KEY = "artifact_cleanup:lock"


async def _ordenar_remocao_local(por_executor: dict[str, list[dict]]) -> list:
    """Tells each executor to delete the expired local artifacts it holds.

    Returns the database ids whose order was DELIVERED — only those can have their
    row removed. An offline executor means the file is still on disk: keeping the row
    makes the next cycle try again, and it is the difference between retention fulfilled
    and a file forgotten on the user's computer.

    The message goes over the same `control` channel as `revoked`/`shutdown`, which the
    executor requires to be signed with Ed25519 (`_SIGNED_SERVER_MESSAGES`). An unsigned
    order to delete files would be a data destruction channel for whoever
    won the connection.
    """
    from app.core.executor_connections import executor_registry

    entregues: list = []
    for executor_id, itens in por_executor.items():
        try:
            # ⚠️ The RETURN VALUE matters. `send_json` returns False — without raising —
            # when the executor is offline, when the Redis relay has no
            # listener, and when the Ed25519 signature fails. A `try/except` only
            # catches the rare case (exception) and lets the COMMON case through: executor
            # turned off. Ignoring the boolean made the row be considered
            # delivered and deleted from the database, leaving the file orphaned on the
            # user's disk — personal data retained indefinitely with nothing to
            # record it, which is exactly the outcome this function exists to
            # avoid.
            entregue = await executor_registry.send_json(executor_id, {
                "type": "control",
                "action": "purge_artifacts",
                "reason": "Retenção expirada.",
                # `local_path` goes along for logging convenience, but the executor
                # must NOT rely on it to build a path — see the handler in
                # executor/connection.py, which resolves from its own root.
                "artifacts": [
                    {"id_hash": i["id_hash"], "local_path": i["local_path"]} for i in itens
                ],
            })
        except Exception as exc:
            entregue = False
            logger.warning(
                "Cleanup: erro ao enviar a ordem de remoção ao executor '%s' (%s).",
                executor_id, exc,
            )

        if not entregue:
            logger.info(
                "Cleanup: executor '%s' não recebeu a ordem de remoção de %d "
                "artefato(s) local(is) — provavelmente offline. As linhas ficam "
                "no banco e a ordem é reenviada quando ele reconectar.",
                executor_id, len(itens),
            )
            continue

        entregues.extend(i["_id"] for i in itens)
        logger.info(
            "Cleanup: %d artefato(s) local(is) marcados para remoção no executor '%s'.",
            len(itens), executor_id,
        )
    return entregues


async def purgar_pendentes_do_executor(executor_id: str) -> int:
    """Resends to ONE executor the removal orders left pending.

    Called when it connects. Without this, an artifact that expired while the
    machine was off would wait for the next cycle of the loop — up to
    ARTIFACT_CLEANUP_INTERVAL (1 h by default) with expired personal data on the
    user's disk. Reconnecting is precisely the moment when the order
    can finally be delivered.

    Returns how many artifacts had their removal confirmed.
    """
    now = utc_now_naive()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Artifact).where(
                Artifact.content_location == "executor",
                Artifact.executor_id == executor_id,
                Artifact.expires_at.isnot(None),
                Artifact.expires_at <= now,
                Artifact.is_pinned == False,  # noqa: E712 — pin cache does not follow retention
                Artifact.local_path.isnot(None),
            )
        )
        pendentes = result.scalars().all()
        if not pendentes:
            return 0

        remocao = await remover_artefatos(db, pendentes, agendar_pendentes=False)
        if remocao.apagados:
            await db.commit()
        return len(remocao.apagados)


async def purge_expired_artifacts() -> int:
    """
    Removes artifacts whose expires_at has already passed.

    Removes expired artifacts from MinIO and the database.
    Returns the number of artifacts removed.
    """
    now = utc_now_naive()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Artifact).where(
                Artifact.expires_at.isnot(None),
                Artifact.expires_at <= now,
                Artifact.is_pinned == False,  # Pin cache artifacts do not follow global retention
            )
        )
        expired = result.scalars().all()

        if not expired:
            return 0

        # MinIO first, a failure preserves the row (the next cycle tries again);
        # local content only goes once the order is DELIVERED to the executor — with it
        # offline, deleting the row would leave the file forever on the user's
        # disk, with nothing to record it: retention that does not happen.
        remocao = await remover_artefatos(db, expired, agendar_pendentes=False)
        if remocao.apagados:
            await db.commit()
        if remocao.falhas_s3:
            logger.info("Cleanup: %d artefatos pulados por falha no S3.", len(remocao.falhas_s3))

    removed = len(remocao.apagados)
    logger.info("Limpeza de artefatos: %d expirado(s) removido(s).", removed)
    return removed


async def run_cleanup_loop() -> None:
    """
    Infinite loop that calls purge_expired_artifacts() every _CLEANUP_INTERVAL seconds.
    Started as a background task in the API lifespan.

    A Redis lock ensures that only one uvicorn worker runs the cleanup per interval.
    """
    await laco_periodico(
        "Cleanup de artefatos", _CLEANUP_INTERVAL, purge_expired_artifacts, lock=_CLEANUP_LOCK_KEY
    )
