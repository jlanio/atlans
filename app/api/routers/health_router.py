# app/api/routers/health_router.py
"""
Endpoints administrativos: whitelist de webhook e armazenamento (uso e purga).
Todos requerem role admin.
"""
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func as sa_func, or_ as sa_or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.logger import get_logger

logger = get_logger(__name__)

from app.api.dependencies import get_current_user, get_db, require_admin
from app.models.workspace import Workspace
from app.models.workspace_file import WorkspaceFile
from app.models.artifact import Artifact
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-health"], dependencies=[Depends(require_admin)])


# ── Helpers ────────────────────────────────────────────────────────────────────
# get_config/set_config foram movidos para app/core/system_config.py para reuso
# por outros modulos admin (disabled_nodes_service etc.). Aliases mantidos como
# wrappers para manter o resto do arquivo igual.

from app.core.system_config import get_config as _get_config  # noqa: E402
from app.core.system_config import set_config as _set_config  # noqa: E402


# ── Whitelist de webhook (/admin/health) ──────────────────────────────────────

@router.get("/health", summary="Whitelist de domínios para webhook")
async def system_health(db: AsyncSession = Depends(get_db)):
    """Só a whitelist: é o que a tela de Configurações lê.

    A lista EFETIVA, a mesma que o disparo aplica (`padroes_validos`): uma
    entrada gravada antes da validação que nunca casaria (`*`, URL com caminho)
    não aparece como restrição, e a tela avisa "sem restrição" quando é o caso.

    A rota também calculava Redis INFO, a dead-letter de resultados e as
    execuções presas (critério antigo, running > 1 h) — nada disso tinha tela.
    As presas de verdade são as do Dashboard, em /observability/metrics.
    """
    from app.core.utils.allowlist import padroes_validos

    gravada = await _get_config(db, "webhook_whitelist", default=[]) or []
    return {"webhook_whitelist": padroes_validos(gravada)}


@router.patch("/health/webhook-whitelist", summary="Atualiza whitelist de domínios para webhook")
async def update_webhook_whitelist(
    domains: List[str] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """
    Define a lista de domínios permitidos para notificação webhook dos workflows.
    Lista vazia = sem restrição (qualquer URL é aceita). Com itens, o host do
    webhook precisa estar nela (e na allowlist do workspace, quando houver) —
    aplicada no disparo, em `run_result_consumer._fire_notification_if_configured`.
    """
    from app.core.utils.allowlist import normalizar_dominio, separar_dominios, validar_allowlist

    # Uma URL colada vira o HOST (como antes: sem esquema, caminho e porta), e o
    # que o matcher ignoraria — `*`, `localhost` — é recusado com 400, a mesma
    # regra da allowlist do workspace. Agora a lista é aplicada no disparo: um
    # `*` aceito em silêncio bloquearia todos os webhooks da plataforma.
    try:
        cleaned = validar_allowlist([normalizar_dominio(x) for x in separar_dominios(domains)])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _set_config(db, "webhook_whitelist", cleaned)
    return {"webhook_whitelist": cleaned}


# ── Armazenamento (MinIO) ─────────────────────────────────────────────────────

@router.get("/storage", summary="Uso de armazenamento por workspace (Drive + Artefatos)")
async def storage_usage(db: AsyncSession = Depends(get_db)):
    """
    Retorna o consumo de armazenamento agregado por workspace,
    consultando workspace_files.size e artifacts.size_bytes.

    Inclui indicadores de saude do tracking — sem essa visibilidade o relatorio
    drifa silenciosamente quando algo escapa do caminho normal (NULL sizes,
    pending stale, falha de delete deixando orfao no S3).
    """
    # Drive: agrupa por workspace_id (apenas confirmados — pending fica em
    # bucket separado abaixo).
    drive_agg = await db.execute(
        select(
            WorkspaceFile.workspace_id,
            sa_func.coalesce(sa_func.sum(WorkspaceFile.size), 0).label("bytes"),
            sa_func.count(WorkspaceFile.id).label("files"),
        )
        .where(WorkspaceFile.status == "confirmed")
        .group_by(WorkspaceFile.workspace_id)
    )
    drive_map: dict[str, dict] = {}
    for row in drive_agg.all():
        drive_map[row.workspace_id] = {"bytes": int(row.bytes), "files": row.files}

    # Artefatos: agrupa por workspace_id
    artifact_agg = await db.execute(
        select(
            Artifact.workspace_id,
            sa_func.coalesce(sa_func.sum(Artifact.size_bytes), 0).label("bytes"),
            sa_func.count(Artifact.id).label("files"),
        )
        .group_by(Artifact.workspace_id)
    )
    artifact_map: dict[str, dict] = {}
    for row in artifact_agg.all():
        ws_id = row.workspace_id or "__none__"
        artifact_map[ws_id] = {"bytes": int(row.bytes), "files": row.files}

    # ── Indicadores de saude do tracking ─────────────────────────────────────

    # Drive pending: presigned PUT criado mas nao confirmado. Bytes ja podem
    # estar no MinIO sem aparecer em "confirmed".
    pending_drive_row = await db.execute(
        select(
            sa_func.count(WorkspaceFile.id).label("files"),
            sa_func.coalesce(sa_func.sum(WorkspaceFile.size), 0).label("bytes"),
        ).where(WorkspaceFile.status == "pending")
    )
    pending_drive = pending_drive_row.one()

    # Artefatos com size_bytes NULL: s3.head() falhou no consumer. Contribui 0
    # para o total mas o objeto pode existir no MinIO. Job
    # storage_reconciliation.fix_artifact_null_sizes preenche periodicamente.
    null_size_row = await db.execute(
        select(sa_func.count(Artifact.id)).where(Artifact.size_bytes.is_(None))
    )
    null_size_artifacts = int(null_size_row.scalar() or 0)

    # Antigos demais para o retry da reconciliação: se o objeto existisse no
    # MinIO, uma das dezenas de tentativas já teria preenchido o tamanho. Sobram
    # dois casos, ambos definitivos: o upload nunca chegou ao MinIO, ou o
    # artefato ficou no disco do executor (s3_key local, via fallback quando o
    # executor não alcança o MinIO).
    from app.core.storage_reconciliation import NULL_SIZE_RETRY_WINDOW_DAYS
    from app.core.utils.datetime_utils import utc_now_naive
    _cutoff = utc_now_naive() - timedelta(days=NULL_SIZE_RETRY_WINDOW_DAYS)
    unrecoverable_row = await db.execute(
        select(sa_func.count(Artifact.id)).where(
            Artifact.size_bytes.is_(None),
            Artifact.created_at < _cutoff,
        )
    )
    unrecoverable_size_artifacts = int(unrecoverable_row.scalar() or 0)

    # Artefatos cujo workspace foi purgado (linha inexistente) ou esta na
    # lixeira — em ambos os casos ninguem mais os acessa, porque um workspace
    # soft-deletado nao entra em get_user_workspace_ids. A versao anterior
    # filtrava `workspace_id IS NULL` numa coluna NOT NULL, entao media sempre 0
    # e nunca acusava os orfaos que apareciam na tabela como "(sem workspace)".
    orphan_ws_row = await db.execute(
        select(sa_func.count(Artifact.id))
        .outerjoin(Workspace, Workspace.id_hash == Artifact.workspace_id)
        .where(sa_or_(Workspace.id_hash.is_(None), Workspace.deleted_at.isnot(None)))
    )
    orphaned_workspace_artifacts = int(orphan_ws_row.scalar() or 0)

    # Enriquecer com nomes
    ws_result = await db.execute(select(Workspace))
    ws_by_id = {w.id_hash: w for w in ws_result.scalars().all()}

    user_result = await db.execute(select(User))
    users_by_id = {u.id_hash: u for u in user_result.scalars().all()}

    all_ws_ids = set(drive_map.keys()) | set(artifact_map.keys())

    total_drive_bytes = 0
    total_artifact_bytes = 0
    total_drive_files = 0
    total_artifact_files = 0
    by_ws = []

    for ws_id in all_ws_ids:
        d = drive_map.get(ws_id, {"bytes": 0, "files": 0})
        a = artifact_map.get(ws_id, {"bytes": 0, "files": 0})
        ws = ws_by_id.get(ws_id)
        owner = users_by_id.get(ws.owner_id) if ws else None

        total_drive_bytes += d["bytes"]
        total_artifact_bytes += a["bytes"]
        total_drive_files += d["files"]
        total_artifact_files += a["files"]

        # Tres estados, nao dois. Com soft delete a linha continua existindo,
        # entao `ws is None` (o teste antigo) deixava o workspace na lixeira sem
        # marcacao — enquanto orphaned_workspace_artifacts ja o contava. O
        # operador lia "N artefatos de workspace deletado" e nao achava a linha.
        # O rotulo antigo ("sem workspace") tambem sugeria workspace_id NULL,
        # que a coluna NOT NULL nem permite.
        if ws is None:
            ws_state, ws_name = "purged", "(workspace removido)"
        elif ws.deleted_at is not None:
            ws_state, ws_name = "trashed", ws.name
        else:
            ws_state, ws_name = "active", ws.name

        by_ws.append({
            "workspace_id": ws_id,
            "workspace_name": ws_name,
            "workspace_state": ws_state,          # active | trashed | purged
            "workspace_deleted": ws_state != "active",
            "owner_username": owner.username if owner else "?",
            "drive_bytes": d["bytes"],
            "drive_files": d["files"],
            "artifacts_bytes": a["bytes"],
            "artifact_files": a["files"],
            "total_bytes": d["bytes"] + a["bytes"],
        })

    by_ws.sort(key=lambda x: x["total_bytes"], reverse=True)

    return {
        "totals": {
            "drive_bytes": total_drive_bytes,
            "artifacts_bytes": total_artifact_bytes,
            "total_bytes": total_drive_bytes + total_artifact_bytes,
            "drive_files": total_drive_files,
            "artifact_files": total_artifact_files,
        },
        "tracking_health": {
            # Pending drive: bytes possivelmente no MinIO mas nao confirmados.
            # Reconcile/cleanup_pending_workspace_files limpa apos TTL.
            "pending_drive_files": int(pending_drive.files or 0),
            "pending_drive_bytes": int(pending_drive.bytes or 0),
            # Artefatos sem tamanho conhecido. Reconcile/fix_artifact_null_sizes
            # tenta preencher enquanto forem recentes.
            "null_size_artifacts": null_size_artifacts,
            # Subconjunto do anterior: antigos demais para o retry — o objeto
            # nao existe no MinIO (upload falhou) ou ficou no disco do executor
            # (fallback local). Nao se resolvem sozinhos.
            "unrecoverable_size_artifacts": unrecoverable_size_artifacts,
            # Artefatos cujo workspace foi deletado: inacessiveis e ocupando disco.
            "orphaned_workspace_artifacts": orphaned_workspace_artifacts,
        },
        "by_workspace": by_ws,
    }


# ── Purga de armazenamento por workspace ─────────────────────────────────────

class PurgeStorageRequest(BaseModel):
    scope: str = Field(
        "all", pattern="^(all|artifacts|drive)$",
        description="all | artifacts | drive",
    )
    confirm: str = Field(
        ..., description="Repita o workspace_id — guarda contra clique acidental.",
    )


@router.post(
    "/storage/workspaces/{workspace_id}/purge",
    summary="[Admin] Purgar Drive e/ou Artefatos de um workspace",
)
async def storage_purge(
    workspace_id: str,
    payload: PurgeStorageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove objetos do MinIO e as linhas do banco. IRREVERSÍVEL.

    Também aceita o id de um workspace já deletado — é como se limpam os
    órfãos que aparecem em /admin/storage como "(workspace deletado)".

    `confirm` precisa repetir o workspace_id: o botão fica ao lado de cada
    linha da tabela e um clique errado apagaria os dados do workspace vizinho.
    """
    if payload.confirm != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="Confirmação não confere com o workspace_id.",
        )

    from app.services.storage_purge_service import purge_workspace_storage

    result = await purge_workspace_storage(db, workspace_id, scope=payload.scope)
    logger.warning(
        "Admin '%s' purgou armazenamento do workspace '%s' (scope=%s): "
        "%d artefato(s), %d arquivo(s) do Drive.",
        current_user.username, workspace_id, payload.scope,
        result["artifacts"], result["drive_files"],
    )
    return result
