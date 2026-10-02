# app/core/storage_reconciliation.py
"""
Reconciliacao entre o estado do DB e o estado real do MinIO.

Endereca a familia de bugs onde o relatorio de uso de disco
(/admin/storage) drifa silenciosamente em relacao ao disco real:

- Bug 1: Artifact.size_bytes = NULL quando s3.head() falhou no run_result_consumer.
         Job re-tenta o head e preenche o valor.
- Bug 2: Multipart uploads abandonados e objetos orfaos no MinIO.
         Job mede o drift e (opcionalmente) limpa.
- Bug 4: WorkspaceFile com status='pending' que ficou em limbo.
         Job apaga apos TTL + aborta multipart correspondente.
- Bug 5: Artifact com workspace_id NULL (legado/orfao). Apenas conta + loga.
- Bug 8: Artifact pinned cujo workflow_hash sumiu. Apenas conta + loga.

Roda como background task no lifespan da API (em paralelo com
artifact_cleanup.run_cleanup_loop). Lock Redis (`laco_periodico`) evita
duplicacao com varios workers uvicorn.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.core.tarefas_periodicas import laco_periodico
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.artifact import Artifact
from app.models.workflow import Workflow
from app.models.workspace_file import WorkspaceFile

logger = get_logger(__name__)

_RECONCILE_INTERVAL = int(os.getenv("STORAGE_RECONCILE_INTERVAL", "3600"))
_RECONCILE_LOCK_KEY = "storage_reconcile:lock"
_PENDING_TTL_HOURS = int(os.getenv("WORKSPACE_FILE_PENDING_TTL_HOURS", "24"))
_MULTIPART_TTL_HOURS = int(os.getenv("MULTIPART_UPLOAD_TTL_HOURS", "24"))


# Janela de retry para size_bytes NULL. Passado esse prazo a causa deixa de ser
# transitoria (objeto nunca subiu ao MinIO, ou ficou no disco do executor via
# fallback local) e insistir so gasta chamada e mantem alerta permanente.
NULL_SIZE_RETRY_WINDOW_DAYS = int(os.getenv("ARTIFACT_NULL_SIZE_RETRY_DAYS", "7"))


# ── Bug 1: preencher size_bytes NULL via s3.head() retry ─────────────────────

async def fix_artifact_null_sizes(db: AsyncSession, limit: int = 500) -> dict:
    """Re-tenta s3.head() em Artifacts RECENTES com size_bytes IS NULL.

    Quando o run_result_consumer falha em obter o tamanho (MinIO transitorio,
    race com upload do executor), grava NULL — e o /admin/storage subestima.
    Este job tenta de novo, preenchendo o que conseguir.

    Janela de retry: so artefatos criados nos ultimos NULL_SIZE_RETRY_WINDOW_DAYS
    dias. Antes o filtro era apenas `size_bytes IS NULL`, entao registros
    insoluveis eram re-consultados 1x/hora para sempre — gastando chamadas ao
    MinIO e mantendo um alerta permanente no painel que nenhuma acao resolvia.
    Passada a janela, a causa nao e mais transitoria: ou o objeto nunca chegou
    ao MinIO, ou ficou no disco do executor (s3_key local). Esses ficam
    contabilizados como `unrecoverable_size_artifacts` no /admin/storage.

    Returns: dict com contadores {checked, fixed, still_null}.
    """
    from app.core import storage as _s3

    cutoff = utc_now_naive() - timedelta(days=NULL_SIZE_RETRY_WINDOW_DAYS)
    stmt = (
        select(Artifact)
        .where(Artifact.size_bytes.is_(None))
        .where(Artifact.s3_key.isnot(None))
        .where(Artifact.created_at >= cutoff)
        .limit(limit)
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    fixed = 0
    still_null = 0
    for art in candidates:
        # s3_key local de fallback do executor (sync to disk) nao tem head() no MinIO
        if art.s3_key.startswith("/"):
            still_null += 1
            continue
        try:
            obj = await _s3.head_async(art.s3_key)
        except Exception as exc:
            logger.debug("fix_null: head falhou para %s: %s", art.s3_key, exc)
            obj = None

        if obj and "size" in obj:
            art.size_bytes = obj["size"]
            fixed += 1
        else:
            still_null += 1

    if fixed > 0:
        await db.commit()

    summary = {"checked": len(candidates), "fixed": fixed, "still_null": still_null}
    if fixed > 0:
        logger.info("Reconcile/fix_null: %s", summary)
    return summary


# ── Bug 4: TTL para WorkspaceFile pending + abort multipart ──────────────────

async def cleanup_pending_workspace_files(db: AsyncSession) -> dict:
    """Remove WorkspaceFile com status='pending' mais antigos que TTL.

    Pending eterno acumula: cliente pediu presigned PUT, recebeu URL, abandonou.
    Sem confirm, o registro vive para sempre no DB e bytes podem ter ficado em
    multipart abandonado no MinIO. Aborta o multipart correspondente se existir.

    Returns: dict {deleted_pending, aborted_multipart}.
    """
    from app.core import storage as _s3

    cutoff = utc_now_naive() - timedelta(hours=_PENDING_TTL_HOURS)
    stmt = (
        select(WorkspaceFile)
        .where(WorkspaceFile.status == "pending")
        .where(WorkspaceFile.created_at < cutoff)
    )
    result = await db.execute(stmt)
    stale = result.scalars().all()

    aborted = 0
    deleted_ids: list[Any] = []
    for wf in stale:
        # Best-effort: abort multipart se existir para esta key
        try:
            for upload in await _s3.list_incomplete_multipart_uploads_async(prefix=wf.s3_key):
                if upload["key"] == wf.s3_key:
                    if await _s3.abort_multipart_upload_async(upload["key"], upload["upload_id"]):
                        aborted += 1
        except Exception as exc:
            logger.debug("Reconcile/pending: list_multipart falhou para %s: %s", wf.s3_key, exc)

        deleted_ids.append(wf.id)

    if deleted_ids:
        await db.execute(delete(WorkspaceFile).where(WorkspaceFile.id.in_(deleted_ids)))
        await db.commit()
        logger.info(
            "Reconcile/pending: removidos %d WorkspaceFile pending > %dh (multipart abortados: %d).",
            len(deleted_ids), _PENDING_TTL_HOURS, aborted,
        )

    return {"deleted_pending": len(deleted_ids), "aborted_multipart": aborted}


async def abort_stale_multipart_uploads(prefix: str = "") -> dict:
    """Aborta multipart uploads com idade > TTL, sem precisar olhar DB.

    Cobre multipart abandonados que nao tem WorkspaceFile correspondente
    (ex: presign falhou apos iniciar multipart). Roda em thread (boto3 e sync).

    Returns: dict {scanned, aborted}.
    """
    from app.core import storage as _s3

    cutoff = datetime.now(timezone.utc) - timedelta(hours=_MULTIPART_TTL_HOURS)
    scanned = 0
    aborted = 0

    def _scan_sync() -> tuple[int, int]:
        s, a = 0, 0
        for upload in _s3.list_incomplete_multipart_uploads(prefix=prefix):
            s += 1
            initiated = upload.get("initiated")
            if initiated is None:
                continue
            # initiated vem com tzinfo do boto3
            if initiated < cutoff:
                if _s3.abort_multipart_upload(upload["key"], upload["upload_id"]):
                    a += 1
        return s, a

    try:
        scanned, aborted = await asyncio.to_thread(_scan_sync)
    except Exception as exc:
        logger.warning("Reconcile/multipart: falha ao escanear: %s", exc)
        return {"scanned": 0, "aborted": 0}

    if aborted > 0:
        logger.info("Reconcile/multipart: %d abortados (de %d > %dh).",
                    aborted, scanned, _MULTIPART_TTL_HOURS)

    return {"scanned": scanned, "aborted": aborted}


# ── Bug 2: drift report DB vs MinIO ──────────────────────────────────────────

async def compute_storage_drift(db: AsyncSession, sample_prefixes: tuple[str, ...] = ("drive/", "artifacts/")) -> dict:
    """Compara SUM(size) do DB com soma real de objetos no MinIO por prefixo.

    NAO deleta nada — apenas mede e loga. Operador decide o que fazer com o
    drift via /admin/storage (que expoe esses numeros).

    Returns: dict {by_prefix: {prefix: {db_bytes, s3_bytes, s3_objects, drift_bytes}}}.
    """
    from app.core import storage as _s3

    out: dict[str, dict] = {}

    # DB totals (conta tudo, nao filtra workspace)
    drive_db = await db.execute(
        select(func.coalesce(func.sum(WorkspaceFile.size), 0)).where(WorkspaceFile.status == "confirmed")
    )
    drive_db_bytes = int(drive_db.scalar() or 0)

    artifact_db = await db.execute(
        select(func.coalesce(func.sum(Artifact.size_bytes), 0))
    )
    artifact_db_bytes = int(artifact_db.scalar() or 0)

    db_by_prefix = {"drive/": drive_db_bytes, "artifacts/": artifact_db_bytes}

    def _sum_s3_prefix(prefix: str) -> tuple[int, int]:
        total = 0
        count = 0
        for obj in _s3.list_objects(prefix=prefix):
            total += int(obj.get("size", 0))
            count += 1
        return total, count

    for prefix in sample_prefixes:
        try:
            s3_bytes, s3_objects = await asyncio.to_thread(_sum_s3_prefix, prefix)
        except Exception as exc:
            logger.warning("Reconcile/drift: falha ao listar prefixo '%s': %s", prefix, exc)
            continue
        db_bytes = db_by_prefix.get(prefix, 0)
        out[prefix] = {
            "db_bytes": db_bytes,
            "s3_bytes": s3_bytes,
            "s3_objects": s3_objects,
            "drift_bytes": s3_bytes - db_bytes,
        }

    if out:
        logger.info("Reconcile/drift: %s", out)
    return {"by_prefix": out}


# ── Bug 5 e 8: auditoria de orfaos (so conta + loga) ─────────────────────────

async def count_orphaned_workspace_artifacts(db: AsyncSession) -> int:
    """Conta Artifact cujo workspace_id nao existe mais em `workspaces`.

    A versao anterior filtrava `workspace_id IS NULL` numa coluna declarada
    NOT NULL (ver app/models/artifact.py) — logo, sempre retornava 0 e a
    auditoria nunca acusava nada, enquanto os orfaos reais apareciam no painel
    rotulados como "(sem workspace)".

    O orfao real e REFERENCIAL: o artefato aponta para um workspace que nao
    existe mais (purgado) ou que esta na lixeira. Efeito pratico: ninguem mais
    consegue acessa-los — verify_workspace_access nunca casa, porque um
    workspace soft-deletado nao entra em get_user_workspace_ids.

    Apenas auditoria — nao deleta.
    """
    from app.models.workspace import Workspace

    result = await db.execute(
        select(func.count(Artifact.id))
        .outerjoin(Workspace, Workspace.id_hash == Artifact.workspace_id)
        .where(or_(Workspace.id_hash.is_(None), Workspace.deleted_at.isnot(None)))
    )
    return int(result.scalar() or 0)


async def count_orphaned_pinned_artifacts(db: AsyncSession) -> int:
    """Conta Artifact pinned cujo workflow_hash nao existe mais.

    Artifacts pinned escapam do cleanup periodico (Artifact.is_pinned == False
    no filtro do artifact_cleanup). Se o workflow for deletado, esses pinned
    ficam orfaos consumindo disco.
    """
    valid_hashes = select(Workflow.id_hash)
    result = await db.execute(
        select(func.count(Artifact.id))
        .where(Artifact.is_pinned == True)  # noqa: E712
        .where(Artifact.workflow_hash.isnot(None))
        .where(Artifact.workflow_hash.notin_(valid_hashes))
    )
    return int(result.scalar() or 0)


# ── Orquestrador ─────────────────────────────────────────────────────────────

async def run_full_reconciliation() -> dict:
    """Roda todos os jobs de reconciliacao em sequencia. Returns summary."""
    summary: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        try:
            summary["fix_null"] = await fix_artifact_null_sizes(db)
        except Exception as exc:
            logger.error("Reconcile/fix_null falhou: %s", exc, exc_info=True)
            summary["fix_null"] = {"error": str(exc)}

        try:
            summary["cleanup_pending"] = await cleanup_pending_workspace_files(db)
        except Exception as exc:
            logger.error("Reconcile/cleanup_pending falhou: %s", exc, exc_info=True)
            summary["cleanup_pending"] = {"error": str(exc)}

        try:
            summary["multipart"] = await abort_stale_multipart_uploads()
        except Exception as exc:
            logger.error("Reconcile/multipart falhou: %s", exc, exc_info=True)
            summary["multipart"] = {"error": str(exc)}

        try:
            summary["drift"] = await compute_storage_drift(db)
        except Exception as exc:
            logger.error("Reconcile/drift falhou: %s", exc, exc_info=True)
            summary["drift"] = {"error": str(exc)}

        try:
            orphan_ws = await count_orphaned_workspace_artifacts(db)
            orphan_pin = await count_orphaned_pinned_artifacts(db)
            summary["audit"] = {
                "orphaned_workspace_artifacts": orphan_ws,
                "orphaned_pinned_artifacts": orphan_pin,
            }
            if orphan_ws > 0:
                logger.warning(
                    "Reconcile/audit: %d artifact(s) apontam para workspace inexistente "
                    "(workspace deletado) — inacessiveis e ocupando disco.", orphan_ws,
                )
            if orphan_pin > 0:
                logger.warning("Reconcile/audit: %d artifacts pinned orfaos (workflow removido).", orphan_pin)
        except Exception as exc:
            logger.error("Reconcile/audit falhou: %s", exc, exc_info=True)
            summary["audit"] = {"error": str(exc)}

    return summary


async def run_reconciliation_loop() -> None:
    """Loop infinito. Iniciado no lifespan da API; lock Redis garante 1 worker por ciclo."""
    await laco_periodico(
        "Reconciliacao de storage", _RECONCILE_INTERVAL, run_full_reconciliation, lock=_RECONCILE_LOCK_KEY
    )
