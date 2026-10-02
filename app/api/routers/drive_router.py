# app/api/routers/drive_router.py
"""
Drive Router — gerencia arquivos do workspace via MinIO (pre-signed URLs).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db, get_current_user, get_user_workspace_ids, exigir_papel_no_workspace, verify_workspace_access,
)
from app.schemas.drive import (
    WorkspaceFileOut, WorkspaceFileList,
)
from app.core.rbac import ROLE_EDITOR
from app.services.drive_service import DriveService


# Tamanho do bloco na leitura do upload — grande o bastante para não penalizar
# arquivos legítimos, pequeno o bastante para o corte por tamanho acontecer
# antes de acumular memória demais.
_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB

# ── Dependency ────────────────────────────────────────────────────────────────

async def get_drive_service(db: AsyncSession = Depends(get_db)) -> DriveService:
    return DriveService(db)


router = APIRouter(
    prefix="/drive",
    tags=["drive"],
    dependencies=[Depends(get_current_user)],
)


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS (JWT)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=WorkspaceFileList)
async def list_files(
    workspace_id:  str          = Query(...),
    search:        Optional[str] = None,
    ext:           Optional[str] = None,
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(50, ge=1, le=200),
    workspace_ids: List[str]     = Depends(get_user_workspace_ids),
    svc:           DriveService  = Depends(get_drive_service),
):
    verify_workspace_access(workspace_id, workspace_ids)

    items, total = await svc.list_files(workspace_id, search=search, ext=ext, page=page, page_size=page_size)
    return WorkspaceFileList(
        items=[WorkspaceFileOut.model_validate(i) for i in items],
        total=total,
    )


@router.post("/upload", response_model=WorkspaceFileOut, status_code=201)
async def upload_file(
    request:       Request,
    workspace_id:  str          = Query(...),
    file:          UploadFile   = File(...),
    db:            AsyncSession = Depends(get_db),
    current_user                = Depends(get_current_user),
    workspace_ids: List[str]    = Depends(get_user_workspace_ids),
    svc:           DriveService = Depends(get_drive_service),
):
    verify_workspace_access(workspace_id, workspace_ids)
    await exigir_papel_no_workspace(db, workspace_id, current_user.id_hash, ROLE_EDITOR)

    original_name = file.filename or "arquivo"

    # O teto vinha sendo aplicado só dentro de `svc.upload_file`, DEPOIS de
    # `await file.read()` sem argumento — que materializa o arquivo inteiro num
    # único bytes na memória do worker. Qualquer editor de workspace derrubava a
    # API mandando um arquivo grande o suficiente. Aqui o limite passa a valer
    # ANTES de acumular: rejeita cedo pelo Content-Length e, como esse header é
    # do cliente e portanto não confiável, corta também durante a leitura.
    settings = await svc.get_settings()
    max_bytes = settings.max_size_mb * 1024 * 1024

    def _too_large() -> HTTPException:
        return HTTPException(
            status_code=413,
            detail=f"Arquivo excede {settings.max_size_mb}MB.",
        )

    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise _too_large()

    chunks: List[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise _too_large()
        chunks.append(chunk)
    content = b"".join(chunks)

    wf = await svc.upload_file(workspace_id, original_name, content, uploaded_by=current_user.id_hash)
    return WorkspaceFileOut.model_validate(wf)


@router.get("/{id_hash}/download")
async def download_file(
    id_hash: str,
    workspace_ids: List[str]    = Depends(get_user_workspace_ids),
    svc:           DriveService = Depends(get_drive_service),
):
    wf = await svc.get_file(id_hash)
    verify_workspace_access(wf.workspace_id, workspace_ids)
    return await svc.generate_download_url(wf)


@router.delete("/{id_hash}", status_code=204)
async def delete_file(
    id_hash: str,
    db:            AsyncSession = Depends(get_db),
    current_user                = Depends(get_current_user),
    workspace_ids: List[str]    = Depends(get_user_workspace_ids),
    svc:           DriveService = Depends(get_drive_service),
):
    wf = await svc.get_file(id_hash)
    verify_workspace_access(wf.workspace_id, workspace_ids)
    await exigir_papel_no_workspace(db, wf.workspace_id, current_user.id_hash, ROLE_EDITOR)

    await svc.delete_file(wf)
    return Response(status_code=204)


@router.post("/batch-delete", status_code=200)
async def batch_delete_files(
    request:       Request,
    current_user                = Depends(get_current_user),
    workspace_ids: List[str]    = Depends(get_user_workspace_ids),
    svc:           DriveService = Depends(get_drive_service),
):
    body = await request.json()
    id_hashes: List[str] = body.get("id_hashes", [])
    deleted, no_executor = await svc.batch_delete_files(
        id_hashes, workspace_ids, current_user.id_hash
    )
    return {"deleted": deleted, "no_executor": no_executor}


