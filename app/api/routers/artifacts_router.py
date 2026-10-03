# app/api/routers/artifacts_router.py

import hmac as _hmac
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db, get_current_user, get_user_workspace_ids, require_admin,
    require_workspace_role, verify_workspace_access,
)
from app.models.artifact import Artifact
from app.models.credential import Credential
from app.models.system_config import SystemConfig
from app.core.utils.encryption import decrypt_string
from app.core.rbac import ROLE_EDITOR
from app.core.utils.logger import get_logger
from app.core.rate_limiter import limiter
from app.services.artifact_service import listar_artefatos
from app.services.remocao_de_artefatos import remove_artifacts

logger = get_logger(__name__)

# ── JWT-protected router (listing, deletion and config) ───────────────────────
router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(get_current_user)],
)

# ── Public router (download by id_hash) ───────────────────────────────────────
public_router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _artifact_or_404(artifact: Artifact | None) -> Artifact:
    if not artifact:
        raise HTTPException(status_code=404, detail="Artefato não encontrado.")
    return artifact


def _recusar_se_local(artifact: Artifact) -> None:
    """Blocks the download of an artifact that lives on the executor's disk.

    Serving this file would require the server to fetch the content from the executor
    — exactly what the `keepLocal` flag forbids. No proxy could preserve the
    guarantee: the data would pass through the server on the way.

    409 (conflict with the resource state) instead of 404: the artifact EXISTS and the
    user has permission; what does not exist is the possibility of downloading it.
    Returning 404 would send support looking for a lost file instead of
    explaining a policy.
    """
    if getattr(artifact, "content_location", "minio") != "executor":
        return
    onde = artifact.executor_id or "desconhecido"
    raise HTTPException(
        status_code=409,
        detail=(
            "Este arquivo foi marcado para permanecer no executor e não pode ser "
            f"baixado pela plataforma (executor {onde}). Ele continua disponível "
            "para workflows que rodem nesse mesmo executor."
        ),
    )


async def _jwt_has_workspace_access(token: str, workspace_id: str, db: AsyncSession) -> bool:
    """
    Returns True if the token is a valid JWT and the user has access to the artifact's workspace.
    Used to let logged-in users download protected artifacts without the artifact token.
    """
    from app.api.dependencies import resolve_access_token
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    # decode + audience + type + blacklist + active user, at the single point.
    user = await resolve_access_token(token, db)
    if user is None:
        return False

    # A workspace in the trash grants access to nobody — not the owner, not the
    # members (WorkspaceMember survives the soft delete, it only goes away on purge).
    alive = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.id_hash == workspace_id,
            Workspace.deleted_at.is_(None),
        )
    )
    if alive.scalar_one_or_none() is None:
        return False

    owned = await db.execute(
        select(Workspace.id_hash).where(
            Workspace.id_hash == workspace_id,
            Workspace.owner_id == user.id_hash,
        )
    )
    if owned.scalar_one_or_none():
        return True

    member = await db.execute(
        select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id_hash,
        )
    )
    return member.scalar_one_or_none() is not None


async def _resolve_bearer_credential(
    credential_id: str, db: AsyncSession
) -> tuple[str | None, str | None]:
    """Returns (decrypted token, ISO expires_at) of the credential.

    Returns (None, None) on any failure. `expires_at` comes in clear text from the database:
    `Credential.encrypt_and_store` encrypts every string field **except** this one.
    """
    from uuid import UUID as _UUID
    try:
        # CredentialField stores credential.id (UUID primary key), not id_hash
        result = await db.execute(
            select(Credential).where(Credential.id == _UUID(credential_id))
        )
        cred = result.scalar_one_or_none()
        if not cred:
            return None, None
        # Credencial do tipo webhook_token guarda o token em data["token"]
        data = cred.data or {}
        raw = data.get("token")
        if not raw:
            return None, None
        return decrypt_string(raw), data.get("expires_at")
    except Exception as exc:
        logger.warning("Falha ao resolver credencial %s: %s", credential_id, exc)
        return None, None


def _reject_if_token_expired(expires_at_str: str | None) -> None:
    """Denies access when the credential's `expires_at` has already passed.

    Same semantics as `_validate_webhook_token`
    (app/core/authorization/credential_validators.py): 403 when expired,
    500 when the format is invalid, and allowed when the field is empty.
    """
    if not expires_at_str:
        return
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=500, detail="Formato inválido de expires_at")
    # A naive expires_at is interpreted as UTC — comparing naive with
    # aware would raise TypeError and become a 500 on an authorization path.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(tz=timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Token expirado")


async def _autorizar_download(artifact: Artifact, request: Request, db: AsyncSession) -> None:
    """Authorizes the download of an artifact, if it is protected by a credential.

    Single point of authorization for the public download. The block was once
    replicated in two endpoints (the other one, by task_id, was removed for having no
    client), and the divergence between the copies is what let the download
    with an expired token through.

    The order matters and cannot be swapped: a user JWT with access to the
    workspace first, the credential's Bearer token second.
    """
    if not artifact.credential_id:
        return  # public artifact

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação não informado.")
    provided_token = auth_header.removeprefix("Bearer ").strip()

    # An authenticated user's JWT takes priority
    if await _jwt_has_workspace_access(provided_token, artifact.workspace_id, db):
        return  # acesso concedido via JWT

    expected_token, expires_at = await _resolve_bearer_credential(artifact.credential_id, db)
    if not expected_token or not _hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Token inválido.")
    _reject_if_token_expired(expires_at)


async def _url_de_download(artifact: Artifact) -> dict:
    """Resolves the pre-signed download URL of an already authorized artifact."""
    _recusar_se_local(artifact)

    if not artifact.s3_key:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado no storage.")

    # Detect an s3_key with an absolute local path (old executor fallback)
    # and rebuild the correct s3_key
    s3_key = artifact.s3_key
    if s3_key.startswith("/") or s3_key.startswith("\\"):
        safe_name = os.path.basename(artifact.filename).replace("..", "_")
        s3_key = f"artifacts/{artifact.workspace_id}/{artifact.run_id}/{safe_name}"

    from app.core import storage as _s3
    # Check whether the object exists in MinIO
    if not await _s3.head_async(s3_key):
        raise HTTPException(
            status_code=404,
            detail="Arquivo armazenado no executor local e nao disponivel para download remoto.",
        )

    url = await _s3.presigned_get_async(s3_key, filename=artifact.filename)
    return {"download_url": url, "filename": artifact.filename}


# ── GET /artifacts/ ───────────────────────────────────────────────────────────

@router.get("", status_code=status.HTTP_200_OK)
async def list_artifacts(
    workflow_id: Optional[str] = None,
    run_id: Optional[str]      = None,
    fmt: Optional[str]         = None,
    workspace_id: Optional[str] = None,
    search: Optional[str]      = None,
    kind: Optional[str]        = Query(
        None, pattern="^(execution|publication)$",
        description="Recorte das abas: 'publication' = camadas publicadas no portal",
    ),
    include_pinned: bool       = False,
    limit: int                 = Query(50, ge=1, le=200),
    offset: int                = Query(0, ge=0),
    db: AsyncSession           = Depends(get_db),
    workspace_ids: List[str]   = Depends(get_user_workspace_ids),
):
    """Lists artifacts of the workspaces accessible to the user, paginated.

    This route used to return the user's workspaces' ENTIRE table: no
    LIMIT, no OFFSET, and with `total = len(items)` — that is, there was no
    concept of a page. `artifacts` grows with every output node of every run
    and only leaves via `expires_at`, so the response grew monotonically until the
    tab froze rendering everything at once.

    Filtering and search are also done by the SERVER now: filtering on the client
    required downloading everything, which is exactly what we want to avoid.

    The query itself lives in `app/services/artifact_service.py` since it
    gained a second caller — the MCP server, which goes through no request
    at all. What remains here is the door: who is asking (`get_current_user`) and
    with what reach (`get_user_workspace_ids`). The response shape did not change.
    """
    return await listar_artefatos(
        db,
        workspace_ids,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        run_id=run_id,
        fmt=fmt,
        search=search,
        kind=kind,
        include_pinned=include_pinned,
        limit=limit,
        offset=offset,
    )


# ── DELETE /artifacts/{id_hash} ───────────────────────────────────────────────

_DELETE_ARTIFACTS = "Requer role 'editor' ou superior para excluir artefatos."


@router.delete("/{id_hash}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    id_hash: str,
    db: AsyncSession          = Depends(get_db),
    current_user              = Depends(get_current_user),
    workspace_ids: List[str]  = Depends(get_user_workspace_ids),
):
    """Remove um artefato (arquivo + registro). Apenas owners/admins do workspace."""
    result = await db.execute(select(Artifact).where(Artifact.id_hash == id_hash))
    artifact = _artifact_or_404(result.scalar_one_or_none())

    verify_workspace_access(artifact.workspace_id, workspace_ids)
    await require_workspace_role(
        db, artifact.workspace_id, current_user.id_hash, ROLE_EDITOR, _DELETE_ARTIFACTS,
    )

    # Content on an executor's disk, object in MinIO, portal layer: the
    # rule is that of every removal (`remove_artifacts`); here only the response.
    remocao = await remove_artifacts(db, [artifact], schedule_pending=True)
    if remocao.falhas_s3:
        # MinIO failed (other than "already gone") and the record stayed: the object
        # remains reachable by reconciliation, and repeating the request solves it.
        logger.error(
            "Delete cancelado para artefato %s: S3 falhou. "
            "Registro preservado; reconcile/cleanup tentara de novo.",
            artifact.s3_key,
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao remover do storage; tente novamente em alguns segundos.",
        )
    # Commit even with nothing deleted: persists the pending ones' `expires_at`.
    await db.commit()
    if remocao.pendentes_local or remocao.sem_rastro:
        # 202 with a body, not HTTPException: it is not an error. The request was accepted
        # and will complete on its own — using the exception path would make the UI
        # paint a normal outcome red.
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "pendente",
                "detail": (
                    "Remocao agendada. O arquivo esta no disco do executor, "
                    "que nao esta conectado agora — sera apagado assim que "
                    "ele voltar."
                ),
            },
        )


# ── POST /artifacts/batch-delete ──────────────────────────────────────────────

@router.post("/batch-delete", status_code=status.HTTP_200_OK)
async def batch_delete_artifacts(
    request: Request,
    db: AsyncSession          = Depends(get_db),
    current_user              = Depends(get_current_user),
    workspace_ids: List[str]  = Depends(get_user_workspace_ids),
):
    """Removes multiple artifacts at once. Workspace owners/admins only."""
    body = await request.json()
    id_hashes: List[str] = body.get("id_hashes", [])
    if not id_hashes:
        raise HTTPException(status_code=400, detail="Lista de id_hashes vazia.")

    result = await db.execute(
        select(Artifact).where(Artifact.id_hash.in_(id_hashes))
    )
    artifacts = list(result.scalars().all())

    if not artifacts:
        raise HTTPException(status_code=404, detail="Nenhum artefato encontrado.")

    # Check permission: all must belong to the user's workspaces with role editor+
    for a in artifacts:
        if a.workspace_id not in workspace_ids:
            raise HTTPException(status_code=403, detail=f"Acesso negado ao artefato {a.id_hash}.")

    # One role per WORKSPACE involved, not per artifact (avoids N+1). The
    # message is the same whichever workspace blocks, so the order in which
    # they are checked does not show in the response.
    for ws_id in sorted({a.workspace_id for a in artifacts}):
        await require_workspace_role(
            db, ws_id, current_user.id_hash, ROLE_EDITOR, _DELETE_ARTIFACTS,
        )

    # The rule is that of every removal (`remove_artifacts`): local ones become ONE
    # order per executor, MinIO goes first and its failure preserves the row
    # (reconciliation tries again), the portal layer goes along.
    remocao = await remove_artifacts(db, artifacts, schedule_pending=True)
    if remocao.falhas_s3:
        logger.error(
            "Batch-delete: %d artefato(s) pulado(s) por falha no S3. Reconcile tentara depois.",
            len(remocao.falhas_s3),
        )
    # Pending ones do NOT go into `skipped`: there it means "failed, try again",
    # and these will happen on their own. Counting them in both would make the UI add
    # up the same artifact as an error AND as pending.
    pendentes = len(remocao.pendentes_local) + len(remocao.sem_rastro)

    # The commit also runs when there are only pending ones. With all artifacts
    # local and the executor offline — the common case on this path — nothing is
    # deleted, and a commit conditioned on what was deleted discarded the
    # `expires_at` just set on the ORM objects: the API answered
    # "remoção pendente" (removal pending) and nothing was scheduled.
    if remocao.apagados or pendentes:
        await db.commit()

    return {
        "deleted": len(remocao.apagados),
        "skipped": len(remocao.falhas_s3),
        # Distinguishes "failed, try again" from "will happen on its own" — without
        # it the UI would show both as errors.
        "pendentes_no_executor": pendentes,
    }


# ── GET /artifacts/{id_hash}/download (public) ────────────────────────────────

@public_router.get("/{id_hash}/download")
@limiter.limit("10/minute")
async def download_artifact(
    id_hash: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Downloads an artifact.
    - Without credential_id → public (no authentication).
    - With credential_id → accepts an authenticated user's JWT OR a Bearer artifact token.
    """
    result = await db.execute(select(Artifact).where(Artifact.id_hash == id_hash))
    artifact = result.scalar_one_or_none()

    # Fallback: look it up in portal_layers (GeoJSON stored in the database)
    if not artifact:
        from app.models.portal_layer import PortalLayer
        from app.models.workflow import Workflow
        from app.api.routers.portal_router import enforce_portal_access
        from fastapi.responses import JSONResponse
        pl_result = await db.execute(select(PortalLayer).where(PortalLayer.id_hash == id_hash))
        pl = pl_result.scalar_one_or_none()
        if pl:
            # SEC: same gate as the twin route /artifacts/portal/layers/{id}/download.
            # This path is the one the portal UI actually calls, and it served the
            # whole GeoJSON with no check at all: whoever had the layer's UUID
            # (returned publicly by GET /artifacts/portal/{workflow_hash})
            # kept downloading the geometries even after the owner marked the
            # portal as private/disabled or deactivated the workflow.
            wf_result = await db.execute(
                select(Workflow).where(Workflow.id_hash == pl.workflow_hash)
            )
            await enforce_portal_access(wf_result.scalar_one_or_none(), request)
            return JSONResponse(
                content=pl.geojson_data,
                headers={"Content-Disposition": f'attachment; filename="{pl.layer_key}.geojson"'},
            )
        raise HTTPException(status_code=404, detail="Artefato não encontrado.")

    # Token validation when the artifact is protected
    await _autorizar_download(artifact, request, db)

    return await _url_de_download(artifact)


# ── GET/PUT /artifacts/admin/settings (retention config) ─────────────────────

@router.get("/admin/settings", dependencies=[Depends(require_admin)])
async def get_artifact_settings(db: AsyncSession = Depends(get_db)):
    """Returns the global artifact retention configuration."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "artifact_retention_days")
    )
    cfg = result.scalar_one_or_none()
    retention_days = int(cfg.value) if cfg and cfg.value is not None else None
    return {"artifact_retention_days": retention_days}


@router.put("/admin/settings", dependencies=[Depends(require_admin)])
async def update_artifact_settings(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the global retention configuration.
    Body: { "artifact_retention_days": <int|null> }
    null = no automatic expiration.
    """
    days = body.get("artifact_retention_days")
    if days is not None and (not isinstance(days, int) or days < 1):
        raise HTTPException(status_code=422, detail="artifact_retention_days deve ser um inteiro >= 1.")

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "artifact_retention_days")
    )
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = days
    else:
        db.add(SystemConfig(key="artifact_retention_days", value=days))

    await db.commit()
    return {"artifact_retention_days": days}

# Portal endpoints (publish, tiles, portal data) movidos para portal_router.py
