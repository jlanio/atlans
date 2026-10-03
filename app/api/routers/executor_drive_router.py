# app/api/routers/executor_drive_router.py
"""
The EXECUTOR's Drive — the executor-* routes (mTLS/API key).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db, get_agent_from_mtls,
)
from app.schemas.drive import (
    ExecutorRegisterRequest, ExecutorUploadUrlRequest, ExecutorPresignUploadRequest, ExecutorPresignDownloadRequest,
    ExecutorTriggerWorkflowRequest,
)
from app.services.drive_service import DriveService

from app.api.routers.drive_router import get_drive_service

# S3 prefixes allowed for executors — all have the format `{prefix}/{workspace_id}/...`
_AGENT_S3_PREFIXES = ("drive/", "pin-cache/", "artifacts/", "webhook-responses/")
_S3_KEY_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")


def _validate_agent_s3_key(s3_key: str, agent_ws_ids: list[str]) -> None:
    """
    Blocks IDOR and path traversal on endpoints that accept an arbitrary s3_key from the executor.

    Ensures that:
    - The value is a string (the payload comes from the executor's JSON, which may
      send a number, list or object — without this check the comparisons below
      raised TypeError/AttributeError, which the callers do not expect since they
      only catch HTTPException, and the error became a 500 instead of a rejection).
    - The s3_key does not contain `..`, NUL, nor start with `/` (no path traversal).
    - Only S3-safe chars are accepted.
    - The prefix is one of the known ones (`drive/`, `pin-cache/`, `artifacts/`, `webhook-responses/`).
    - The `{workspace_id}` segment after the prefix belongs to the executor.
    """
    if not isinstance(s3_key, str):
        raise HTTPException(status_code=400, detail="s3_key invalido.")
    if not s3_key or ".." in s3_key or "\x00" in s3_key or s3_key.startswith("/"):
        raise HTTPException(status_code=400, detail="s3_key invalido.")
    if not _S3_KEY_RE.match(s3_key):
        raise HTTPException(status_code=400, detail="s3_key contem caracteres invalidos.")
    if not s3_key.startswith(_AGENT_S3_PREFIXES):
        raise HTTPException(status_code=403, detail="s3_key fora dos prefixos permitidos.")
    parts = s3_key.split("/")
    if len(parts) < 3 or not parts[1]:
        raise HTTPException(status_code=400, detail="s3_key mal formado.")
    if parts[1] not in agent_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado ao workspace do s3_key.")


async def _resolve_agent_workspaces(request: Request, db: AsyncSession):
    """
    Resolves the workspaces of the executor authenticated via mTLS.

    Wrapper over get_agent_from_mtls that adds the _resolved_ws_ids attribute
    for backward compat with this router's existing endpoints.
    """
    executor = await get_agent_from_mtls(request, db)
    from app.services.user_executor_service import get_agent_workspace_ids
    executor._resolved_ws_ids = await get_agent_workspace_ids(db, executor.id_hash, executor.is_default)
    return executor


# Alias kept for internal callers that used the old name.
_auth_agent = _resolve_agent_workspaces


router = APIRouter(
    prefix="/drive",
    tags=["drive", "executor"],
)



# ══════════════════════════════════════════════════════════════════════════════
# AGENT ENDPOINTS (API Key)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/executor-upload-url", status_code=201)
async def agent_get_upload_url(
    request: Request,
    payload: ExecutorUploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)
    ws_id = payload.workspace_id or (executor._resolved_ws_ids[0] if executor._resolved_ws_ids else None)
    if not ws_id:
        raise HTTPException(status_code=400, detail="Nenhum workspace disponível para este executor.")
    if ws_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado ao workspace.")

    # If the executor sends s3_key_override, validates that it points to its own workspace
    if payload.s3_key_override:
        _validate_agent_s3_key(payload.s3_key_override, executor._resolved_ws_ids)

    return await svc.create_agent_upload_url(
        workspace_id=ws_id,
        filename=payload.filename,
        size=payload.size,
        uploaded_by=executor.id_hash,
        s3_key_override=payload.s3_key_override,
        content_type_override=payload.content_type,
        overwrite=payload.overwrite,
    )


@router.post("/executor-register", status_code=201)
async def agent_register_local_dataset(
    request: Request,
    payload: ExecutorRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Registers in the Drive a dataset that STAYS on the executor's disk.

    GeoSync in catalog mode (LGPD): the executor sends only the catalog — name,
    size and spatial metadata. No byte of the content travels, and there is no
    object in MinIO.

    Idempotent per (workspace, name, executor): GeoSync reprocesses the same
    dataset on every cycle in which it changes, and creating one row per cycle
    would fill the Drive with duplicates of the same file.
    """
    from sqlalchemy import select

    from app.core.utils.datetime_utils import utc_now_naive
    from app.models.workspace_file import WorkspaceFile

    executor = await _auth_agent(request, db)
    ws_id = payload.workspace_id or (executor._resolved_ws_ids[0] if executor._resolved_ws_ids else None)
    if not ws_id:
        raise HTTPException(status_code=400, detail="Nenhum workspace disponível para este executor.")
    if ws_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado ao workspace.")

    nome = payload.filename.replace("\\", "/").split("/")[-1].strip()
    if not nome or nome in (".", ".."):
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")
    ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""

    existente = await db.execute(
        select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == ws_id,
            WorkspaceFile.original_name == nome,
            WorkspaceFile.content_location == "executor",
            WorkspaceFile.content_executor_id == executor.id_hash,
        ).limit(1)
    )
    wf = existente.scalar_one_or_none()

    if wf is None:
        wf = WorkspaceFile(
            workspace_id=ws_id,
            # No object: there is no key to point to. Deriving one would make the UI
            # offer a download that would answer 404 in MinIO.
            s3_key=None,
            original_name=nome,
            extension=ext,
            uploaded_by=executor.id_hash,
            status="confirmed",
            content_location="executor",
            content_executor_id=executor.id_hash,
        )
        db.add(wf)

    wf.size = payload.size
    wf.spatial_metadata = payload.spatial_metadata or None
    wf.content_written_at = utc_now_naive()

    await db.commit()
    await db.refresh(wf)

    return {
        "id_hash": wf.id_hash,
        "original_name": wf.original_name,
        "content_location": wf.content_location,
    }


@router.post("/executor-confirm-upload/{id_hash}")
async def agent_confirm_upload(
    request: Request,
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)

    wf = await svc.get_file(id_hash)
    if wf.workspace_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # OPTIONAL body: an executor older than this version confirms with nothing.
    # A missing or malformed JSON must not bring down the confirmation of an
    # upload that already happened in MinIO — the file would stay `pending` forever.
    spatial_metadata = None
    try:
        corpo = await request.json()
        if isinstance(corpo, dict):
            bruto = corpo.get("spatial_metadata")
            if isinstance(bruto, dict):
                spatial_metadata = bruto
    except Exception:
        pass

    wf = await svc.confirm_upload(
        id_hash, exclude_agent_id=executor.id_hash, spatial_metadata=spatial_metadata,
    )
    return {
        "id_hash": wf.id_hash, "original_name": wf.original_name,
        "extension": wf.extension, "size": wf.size, "content_md5": wf.content_md5,
    }


@router.delete("/executor-file/{id_hash}", status_code=204)
async def agent_delete_file(
    request: Request,
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    """Removes a file from the Drive on GeoSync's order (mTLS).

    The executor calls this when it detects that the file left the synced
    folder. It is the ONLY removal path an executor has:
    `DELETE /drive/{id}` (the user's) requires a JWT, and on the executors' host
    (`agents.<dominio>`) Traefik only routes `/drive/executor-*` to the API — a
    bare `/drive/{id}` does not even reach the backend, it becomes a 404 in
    Traefik itself. It was that 404, and not a removal through the web, that the
    executor had been treating as "already deleted": it gave up and cleared the
    manifest, but the WorkspaceFile remained in the Drive.

    Idempotent: a missing record answers 204 — what no longer exists is already
    in the desired state.
    """
    executor = await _auth_agent(request, db)
    try:
        wf = await svc.get_file(id_hash)
    except FileNotFoundError:
        return Response(status_code=204)
    if wf.workspace_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado ao workspace.")
    await svc.delete_agent_file(wf, executor.id_hash)
    return Response(status_code=204)


@router.get("/executor-list")
async def agent_list_files(
    request: Request,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)
    if workspace_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    files = await svc.list_files_for_agent(workspace_id)
    return {"files": files}


@router.get("/executor-download/{id_hash}")
async def agent_download_file(
    request: Request,
    id_hash: str,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)
    wf = await svc.get_file(id_hash)
    if wf.workspace_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # Dataset cataloged by GeoSync: the bytes never left an executor's disk.
    # There is no object nor URL to sign — we return the marker and the
    # executor finds the file again through its OWN sync manifest, by
    # id_hash. No filesystem path travels here.
    if wf.content_location == "executor":
        return {
            "content_location": "executor",
            "executor_id": wf.content_executor_id,
            "original_name": wf.original_name,
            "extension": wf.extension,
        }

    download_url = await svc.generate_download_url(wf)
    return {
        "content_location": "minio",
        "download_url": download_url["download_url"],
        "original_name": wf.original_name,
        "extension": wf.extension,
    }


@router.get("/executor-download-artifact/{id_hash}")
async def agent_download_artifact(
    request: Request,
    id_hash: str,
    db: AsyncSession = Depends(get_db),
):
    """Artifact read by the executor (DataInput's Artifacts context).

    Mirrors /executor-download/{id_hash}, but resolves in the `artifacts` table.
    """
    import asyncio
    from sqlalchemy import select
    from app.models.artifact import Artifact
    from app.core import storage as _s3

    executor = await _auth_agent(request, db)

    result = await db.execute(select(Artifact).where(Artifact.id_hash == id_hash))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artefato não encontrado.")
    if artifact.workspace_id not in executor._resolved_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    ext = (artifact.format or "").lower()
    if not ext and "." in (artifact.filename or ""):
        ext = artifact.filename.rsplit(".", 1)[-1].lower()

    # Artifact that never left an executor's disk (LGPD): there is no object in
    # storage and no URL to sign. We return WHERE it is and the executor decides
    # whether the file is its own — the ownership check stays on the side that
    # has the disk, not here, because only it knows what exists in
    # `EXECUTOR_ARTIFACTS_DIR`.
    #
    # `local_path` was DERIVED by the server at registration (run_result_consumer),
    # never accepted from the executor: it goes back to the executor and a `../`
    # here would become an arbitrary file read on the user's machine.
    if artifact.content_location == "executor":
        return {
            "content_location": "executor",
            "executor_id": artifact.executor_id,
            "local_path": artifact.local_path,
            "original_name": artifact.filename,
            "extension": ext,
        }

    # storage.head is synchronous boto3 — without to_thread it would block the
    # worker's event loop during the round-trip to MinIO (same reason as the fix
    # in run_result_consumer).
    head_ok = await asyncio.to_thread(_s3.head, artifact.s3_key) if artifact.s3_key else None
    if not head_ok:
        raise HTTPException(status_code=404, detail="Arquivo do artefato não disponível no storage.")

    return {
        "content_location": "minio",
        "download_url": await _s3.presigned_get_async(artifact.s3_key, filename=artifact.filename),
        "original_name": artifact.filename,
        "extension": ext,
    }


@router.post("/executor-presign-upload")
async def agent_presign_upload(
    request: Request,
    payload: ExecutorPresignUploadRequest,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)
    # A8: validates that the s3_key belongs to the executor's workspace before generating a presign
    _validate_agent_s3_key(payload.s3_key, executor._resolved_ws_ids)
    return await svc.presign_upload(payload.s3_key, content_type=payload.content_type)


@router.post("/executor-presign-download")
async def agent_presign_download(
    request: Request,
    payload: ExecutorPresignDownloadRequest,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)
    return await svc.presign_download(payload.s3_key, executor._resolved_ws_ids)


@router.post("/executor-trigger-workflow", status_code=202)
async def agent_trigger_workflow(
    request: Request,
    payload: ExecutorTriggerWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    svc: DriveService = Depends(get_drive_service),
):
    executor = await _auth_agent(request, db)

    return await svc.trigger_workflow(
        workflow_id_hash=payload.workflow_id_hash,
        agent_ws_ids=executor._resolved_ws_ids,
        inputs=payload.inputs,
    )
