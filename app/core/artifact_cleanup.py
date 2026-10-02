# app/core/artifact_cleanup.py
"""
Loop periódico de limpeza de artefatos expirados.

Roda como background task no lifespan da API.
Intervalo: ARTIFACT_CLEANUP_INTERVAL segundos (padrão: 3600 = 1h).

Lock distribuído Redis (`laco_periodico`, com TTL = o intervalo) — garante que
apenas um worker uvicorn execute o cleanup por intervalo, evitando queries
redundantes com --workers N.
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
    """Manda cada executor apagar os artefatos locais expirados que ele guarda.

    Devolve os ids de banco cuja ordem foi ENTREGUE — só esses podem ter a linha
    removida. Executor offline significa arquivo ainda em disco: manter a linha
    faz o próximo ciclo tentar de novo, e é a diferença entre retenção cumprida
    e arquivo esquecido no computador do usuário.

    A mensagem vai pelo mesmo canal `control` de `revoked`/`shutdown`, que o
    executor exige assinado com Ed25519 (`_SIGNED_SERVER_MESSAGES`). Uma ordem
    de apagar arquivo sem assinatura seria um canal de destruição de dados para
    quem vencesse a conexão.
    """
    from app.core.executor_connections import executor_registry

    entregues: list = []
    for executor_id, itens in por_executor.items():
        try:
            # ⚠️ O RETORNO importa. `send_json` devolve False — sem levantar —
            # quando o executor está offline, quando o relay Redis não tem
            # ouvinte, e quando a assinatura Ed25519 falha. Um `try/except` só
            # pega o caso raro (exceção) e deixa passar o caso COMUM: executor
            # desligado. Ignorar o booleano fazia a linha ser considerada
            # entregue e apagada do banco, deixando o arquivo órfão no disco do
            # usuário — dado pessoal retido indefinidamente e sem nada que o
            # registre, que é exatamente o desfecho que esta função existe para
            # evitar.
            entregue = await executor_registry.send_json(executor_id, {
                "type": "control",
                "action": "purge_artifacts",
                "reason": "Retenção expirada.",
                # `local_path` vai junto por conveniência de log, mas o executor
                # NÃO deve confiar nele para montar caminho — ver o handler em
                # executor/connection.py, que resolve a partir da própria raiz.
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
    """Reenvia a UM executor as ordens de remoção que ficaram pendentes.

    Chamada quando ele conecta. Sem isto, um artefato expirado enquanto a
    máquina estava desligada esperaria o próximo ciclo do loop — até
    ARTIFACT_CLEANUP_INTERVAL (1 h por padrão) com dado pessoal vencido no
    disco do usuário. Reconectar é justamente o instante em que a ordem
    finalmente pode ser entregue.

    Devolve quantos artefatos tiveram a remoção confirmada.
    """
    now = utc_now_naive()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Artifact).where(
                Artifact.content_location == "executor",
                Artifact.executor_id == executor_id,
                Artifact.expires_at.isnot(None),
                Artifact.expires_at <= now,
                Artifact.is_pinned == False,  # noqa: E712 — pin cache não segue retenção
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
    Remove artefatos cujo expires_at já passou.

    Remove artefatos expirados do MinIO e do banco.
    Retorna o numero de artefatos removidos.
    """
    now = utc_now_naive()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Artifact).where(
                Artifact.expires_at.isnot(None),
                Artifact.expires_at <= now,
                Artifact.is_pinned == False,  # Artefatos de pin cache nao seguem retencao global
            )
        )
        expired = result.scalars().all()

        if not expired:
            return 0

        # MinIO primeiro, falha preserva a linha (próximo ciclo tenta de novo);
        # conteúdo local só sai com a ordem ENTREGUE ao executor — com ele
        # offline, apagar a linha deixaria o arquivo para sempre no disco do
        # usuário, sem nada que o registre: retenção que não acontece.
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
    Loop infinito que chama purge_expired_artifacts() a cada _CLEANUP_INTERVAL segundos.
    Iniciado como background task no lifespan da API.

    Lock Redis garante que apenas um worker uvicorn execute o cleanup por intervalo.
    """
    await laco_periodico(
        "Cleanup de artefatos", _CLEANUP_INTERVAL, purge_expired_artifacts, lock=_CLEANUP_LOCK_KEY
    )
