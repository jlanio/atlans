# app/api/routers/executor_drive_router.py
"""
Drive do EXECUTOR — as rotas executor-* (mTLS/chave de API).
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

# Prefixos S3 permitidos para executores — todos têm formato `{prefix}/{workspace_id}/...`
_AGENT_S3_PREFIXES = ("drive/", "pin-cache/", "artifacts/", "webhook-responses/")
_S3_KEY_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")


def _validate_agent_s3_key(s3_key: str, agent_ws_ids: list[str]) -> None:
    """
    Bloqueia IDOR e path traversal em endpoints que aceitam s3_key arbitrário do executor.

    Garante que:
    - O valor é uma string (o payload vem de JSON do executor, que pode mandar
      número, lista ou objeto — sem esta checagem as comparações abaixo
      levantavam TypeError/AttributeError, que os callers não esperam por
      capturarem apenas HTTPException, e o erro virava 500 em vez de rejeição).
    - O s3_key não contém `..`, NUL, nem começa com `/` (sem path traversal).
    - Apenas chars S3-safe são aceitos.
    - O prefixo é um dos conhecidos (`drive/`, `pin-cache/`, `artifacts/`, `webhook-responses/`).
    - O segmento `{workspace_id}` após o prefixo pertence ao executor.
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
    Resolve os workspaces do executor autenticado via mTLS.

    Wrapper sobre get_agent_from_mtls que adiciona o atributo _resolved_ws_ids
    para retrocompat com os endpoints existentes deste router.
    """
    executor = await get_agent_from_mtls(request, db)
    from app.services.user_executor_service import get_agent_workspace_ids
    executor._resolved_ws_ids = await get_agent_workspace_ids(db, executor.id_hash, executor.is_default)
    return executor


# Alias mantido para callers internos que usavam o nome antigo.
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

    # Se o executor envia s3_key_override, valida que aponta para o workspace dele
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
    """Registra no Drive um dataset que PERMANECE no disco do executor.

    GeoSync em modo catálogo (LGPD): o executor manda só o catálogo — nome,
    tamanho e metadados espaciais. Nenhum byte do conteúdo trafega, e não há
    objeto no MinIO.

    Idempotente por (workspace, nome, executor): o GeoSync reprocessa o mesmo
    dataset a cada ciclo em que ele muda, e criar uma linha por ciclo encheria o
    Drive de duplicatas do mesmo arquivo.
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
            # Sem objeto: nao existe key a apontar. Derivar uma faria a UI
            # oferecer um download que responderia 404 no MinIO.
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

    # Corpo OPCIONAL: executor anterior a esta versao confirma sem nada. Um JSON
    # ausente ou malformado nao pode derrubar a confirmacao de um upload que ja
    # aconteceu no MinIO — o arquivo ficaria em `pending` para sempre.
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
    """Remove um arquivo do Drive por ordem do GeoSync (mTLS).

    O executor chama isto quando detecta que o arquivo saiu da pasta
    sincronizada. E o UNICO caminho de remocao que um executor tem:
    `DELETE /drive/{id}` (do usuario) exige JWT, e no host dos executores (`agents.<dominio>`)
    o Traefik so roteia `/drive/executor-*` para a API — um `/drive/{id}` cru
    nem chega ao backend, vira 404 no proprio Traefik. Era esse 404, e nao uma
    remocao pelo web, que o executor vinha tratando como "ja apagado": ele
    desistia e limpava o manifesto, mas o WorkspaceFile continuava no Drive.

    Idempotente: registro ausente responde 204 — o que ja nao existe ja esta no
    estado desejado.
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

    # Dataset catalogado pelo GeoSync: os bytes nunca sairam do disco de um
    # executor. Nao ha objeto nem URL a assinar — devolvemos a marcacao e o
    # executor reencontra o arquivo pelo PROPRIO manifesto de sync, pelo
    # id_hash. Nenhum caminho de sistema de arquivos trafega aqui.
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
    """Leitura de Artefato pelo executor (contexto Artefatos do DataInput).

    Espelha /executor-download/{id_hash}, mas resolve na tabela `artifacts`.
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

    # Artefato que nunca saiu do disco de um executor (LGPD): nao ha objeto no
    # storage e nao ha URL a assinar. Devolvemos ONDE ele esta e o executor
    # decide se o arquivo e dele — a checagem de posse fica no lado que tem o
    # disco, nao aqui, porque so ele sabe o que existe em `EXECUTOR_ARTIFACTS_DIR`.
    #
    # `local_path` foi DERIVADO pelo servidor no registro (run_result_consumer),
    # nunca aceito do executor: ele volta para o executor e um `../` aqui viraria
    # leitura de arquivo arbitrario na maquina do usuario.
    if artifact.content_location == "executor":
        return {
            "content_location": "executor",
            "executor_id": artifact.executor_id,
            "local_path": artifact.local_path,
            "original_name": artifact.filename,
            "extension": ext,
        }

    # storage.head e boto3 sincrono — sem to_thread bloquearia o event loop do
    # worker durante o round-trip ao MinIO (mesmo motivo do fix em run_result_consumer).
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
    # A8: valida que o s3_key pertence ao workspace do executor antes de gerar presign
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
