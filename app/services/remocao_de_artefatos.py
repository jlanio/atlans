# app/services/remocao_de_artefatos.py
"""
Artifact removal: a single algorithm for the five paths that delete.

DELETE /artifacts/{id}, POST /artifacts/batch-delete, retention
(`artifact_cleanup.purge_expired_artifacts`), the resend to a reconnecting
executor (`artifact_cleanup.purgar_pendentes_do_executor`) and the workspace
purge (`storage_purge_service.purge_workspace_storage`) each had their
own copy of the loop, and the copies diverged: only the purge deleted the portal
layer of a delivered LOCAL artifact — on the other paths the row vanished and the
PortalLayer stayed up. The caller chooses WHICH artifacts (the query) and
translates the outcome (204/202/502, counters, log); the rule lives here:

- Content on an executor's disk (`content_location='executor'`): the removal
  order goes to the executor (`_ordenar_remocao_local`, one per machine) and the
  row only drops once it has been DELIVERED. Deleting before that would leave the file
  orphaned on the user's disk and the server with no record of it at all — for personal
  data, worse than not having deleted. Without `executor_id`/`local_path` there is no one
  to send it to: the row stays, so as not to lose track of the file.
- Object in MinIO: goes FIRST. If S3 fails for any reason other than "not
  found", the row stays — the object does not become an invisible orphan, and the next
  pass (or the reconciliation) tries again. An `s3_key` starting with "/" is the
  executor's old local fallback: it does not exist in MinIO, only the row goes.
- The portal layer (and the features, by cascade) goes along with the row of every
  deleted published artifact, of any location.

Does NOT commit: the caller decides when to persist.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.portal_layer import PortalLayer

logger = get_logger(__name__)


@dataclass
class Remocao:
    """The outcome, artifact by artifact. Only `apagados` left the database."""

    apagados: list = field(default_factory=list)
    # Object MinIO did not delete: the row stays, and retrying fixes it.
    falhas_s3: list = field(default_factory=list)
    # Local whose order was not delivered (executor offline): the row stays, and the
    # order is resent when it reconnects.
    pendentes_local: list = field(default_factory=list)
    # Local without executor_id/local_path: there is no one to send the order to.
    sem_rastro: list = field(default_factory=list)

    @property
    def bytes(self) -> int:
        return sum(int(a.size_bytes or 0) for a in self.apagados)


async def remover_artefatos(
    db: AsyncSession, artefatos, *, agendar_pendentes: bool,
) -> Remocao:
    """Removes `artefatos` (objects from the `db` session) — see the semantics above.

    `agendar_pendentes`: those left on an executor's disk (order not
    delivered, or no trace) are marked as expired, unpinned, for
    retention to finish on its own — that is what the user asked for in the delete routes.
    The pin MUST drop along with it: retention ignores pinned artifacts, and a pinned one
    marked as expired would vanish from the screen as "removing" and never be
    removed. In retention and in the purge they are already within reach of the next
    pass, and nothing is marked.
    """
    # From retention: it is the one that signs, sends and returns only the DELIVERED ids.
    from app.core.artifact_cleanup import _ordenar_remocao_local
    from app.core import storage as s3

    remocao = Remocao()

    por_executor: dict[str, list[dict]] = {}
    locais: list = []
    for a in artefatos:
        if a.content_location != "executor":
            continue
        if not a.executor_id or not a.local_path:
            logger.warning(
                "Remoção: artefato local %s sem executor_id/local_path — mantido no banco "
                "para não perder o rastro do arquivo.", a.id_hash,
            )
            remocao.sem_rastro.append(a)
            continue
        por_executor.setdefault(a.executor_id, []).append(
            {"id_hash": a.id_hash, "local_path": a.local_path, "_id": a.id}
        )
        locais.append(a)
    if por_executor:
        entregues = set(await _ordenar_remocao_local(por_executor))
        for a in locais:
            (remocao.apagados if a.id in entregues else remocao.pendentes_local).append(a)

    for a in artefatos:
        if a.content_location == "executor":
            continue
        if a.s3_key and not a.s3_key.startswith("/"):
            try:
                await s3.delete_strict_async(a.s3_key, allow_missing=True)
            except Exception as exc:
                logger.warning("Remoção: mantendo artefato %s no banco (S3 falhou: %s).", a.s3_key, exc)
                remocao.falhas_s3.append(a)
                continue
        remocao.apagados.append(a)

    for a in remocao.apagados:
        await _apagar_camada_do_portal(db, a)
    if remocao.apagados:
        await db.execute(delete(Artifact).where(Artifact.id.in_([a.id for a in remocao.apagados])))

    if agendar_pendentes:
        agora = utc_now_naive()
        for a in (*remocao.pendentes_local, *remocao.sem_rastro):
            a.expires_at = agora
            a.is_pinned = False
    return remocao


async def _apagar_camada_do_portal(db: AsyncSession, artefato) -> None:
    """The artifact's published layer (the features drop by cascade)."""
    if artefato.is_published and artefato.workflow_hash:
        await db.execute(
            delete(PortalLayer).where(
                PortalLayer.workflow_hash == artefato.workflow_hash,
                PortalLayer.layer_key == artefato.output_key,
            )
        )
