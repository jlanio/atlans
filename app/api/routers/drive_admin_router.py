# app/api/routers/drive_admin_router.py
"""
Drive — configuração global (admin): tamanho máximo e extensões permitidas.
"""
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.dependencies import (
    require_admin,
)
from app.schemas.drive import (
    PlatformFileSettingsOut, PlatformFileSettingsUpdate,
    AllowedExtensionOut, AllowedExtensionCreate,
)
from app.services.drive_service import DriveService

from app.api.routers.drive_router import get_drive_service

router = APIRouter(
    prefix="/admin/drive",
    tags=["admin", "drive"],
    dependencies=[Depends(require_admin)],
)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/settings", response_model=PlatformFileSettingsOut)
async def get_settings(svc: DriveService = Depends(get_drive_service)):
    return PlatformFileSettingsOut.model_validate(await svc.get_settings())


@router.put("/settings", response_model=PlatformFileSettingsOut)
async def update_settings(
    payload: PlatformFileSettingsUpdate,
    svc: DriveService = Depends(get_drive_service),
):
    settings = await svc.update_settings(payload.max_size_mb)
    return PlatformFileSettingsOut.model_validate(settings)


@router.get("/extensions", response_model=List[AllowedExtensionOut])
async def list_extensions(svc: DriveService = Depends(get_drive_service)):
    exts = await svc.list_extensions()
    return [AllowedExtensionOut.model_validate(e) for e in exts]


@router.post("/extensions", response_model=AllowedExtensionOut, status_code=201)
async def add_extension(
    payload: AllowedExtensionCreate,
    svc: DriveService = Depends(get_drive_service),
):
    new_ext = await svc.add_extension(payload.extension)
    return AllowedExtensionOut.model_validate(new_ext)


@router.delete("/extensions/{ext}", status_code=204)
async def remove_extension(ext: str, svc: DriveService = Depends(get_drive_service)):
    await svc.remove_extension(ext)
    return Response(status_code=204)
