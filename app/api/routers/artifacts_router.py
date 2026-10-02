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
    exigir_papel_no_workspace, verify_workspace_access,
)
from app.models.artifact import Artifact
from app.models.credential import Credential
from app.models.system_config import SystemConfig
from app.core.utils.encryption import decrypt_string
from app.core.rbac import ROLE_EDITOR
from app.core.utils.logger import get_logger
from app.core.rate_limiter import limiter
from app.services.artifact_service import listar_artefatos
from app.services.remocao_de_artefatos import remover_artefatos

logger = get_logger(__name__)

# ── Router protegido por JWT (listagem, exclusão e config) ────────────────────
router = APIRouter(
    prefix="/artifacts",
    tags=["artifacts"],
    dependencies=[Depends(get_current_user)],
)

# ── Router público (download por id_hash) ─────────────────────────────────────
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
    """Barra o download de artefato que mora no disco do executor.

    Servir este arquivo exigiria que o servidor buscasse o conteudo no executor
    — exatamente o que a marcacao `keepLocal` proibe. Nao ha proxy possivel que
    preserve a garantia: o dado passaria pelo servidor no caminho.

    409 (conflito com o estado do recurso) em vez de 404: o artefato EXISTE e o
    usuario tem permissao; o que nao existe e a possibilidade de baixa-lo.
    Devolver 404 mandaria o suporte procurar um arquivo perdido em vez de
    explicar uma politica.
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
    Retorna True se o token for um JWT válido e o usuário tiver acesso ao workspace do artefato.
    Usado para permitir que usuários logados baixem artefatos protegidos sem o token de artefato.
    """
    from app.api.dependencies import resolve_access_token
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    # decode + audience + type + blacklist + user ativo, no ponto único.
    user = await resolve_access_token(token, db)
    if user is None:
        return False

    # Workspace na lixeira nao concede acesso a ninguem — nem ao dono, nem aos
    # membros (WorkspaceMember sobrevive ao soft delete, so cai no purge).
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
    """Retorna (token descriptografado, expires_at ISO) da credencial.

    Devolve (None, None) em qualquer falha. `expires_at` vem em claro do banco:
    `Credential.encrypt_and_store` cifra todos os campos string **exceto** este.
    """
    from uuid import UUID as _UUID
    try:
        # CredentialField armazena credential.id (UUID primary key), não id_hash
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


def _recusar_se_token_expirado(expires_at_str: str | None) -> None:
    """Recusa o acesso quando o `expires_at` da credencial já passou.

    Mesma semântica de `_validate_webhook_token`
    (app/core/authorization/credential_validators.py): 403 quando expirado,
    500 quando o formato é inválido, e liberado quando o campo está vazio.
    """
    if not expires_at_str:
        return
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=500, detail="Formato inválido de expires_at")
    # Um expires_at ingênuo é interpretado como UTC — comparar ingênuo com
    # ciente levantaria TypeError e viraria 500 num caminho de autorização.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(tz=timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Token expirado")


async def _autorizar_download(artifact: Artifact, request: Request, db: AsyncSession) -> None:
    """Autoriza o download de um artefato, se ele for protegido por credencial.

    Ponto único da autorização do download público. O bloco chegou a ser
    replicado em dois endpoints (o outro, por task_id, saiu por não ter
    cliente), e a divergência entre as cópias foi o que deixou passar o
    download com token expirado.

    A ordem é significativa e não pode ser trocada: JWT de usuário com acesso ao
    workspace primeiro, token Bearer da credencial depois.
    """
    if not artifact.credential_id:
        return  # artefato público

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação não informado.")
    provided_token = auth_header.removeprefix("Bearer ").strip()

    # JWT de usuário autenticado tem prioridade
    if await _jwt_has_workspace_access(provided_token, artifact.workspace_id, db):
        return  # acesso concedido via JWT

    expected_token, expires_at = await _resolve_bearer_credential(artifact.credential_id, db)
    if not expected_token or not _hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="Token inválido.")
    _recusar_se_token_expirado(expires_at)


async def _url_de_download(artifact: Artifact) -> dict:
    """Resolve a URL pré-assinada de download de um artefato já autorizado."""
    _recusar_se_local(artifact)

    if not artifact.s3_key:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado no storage.")

    # Detecta s3_key com path local absoluto (fallback antigo de executor)
    # e reconstroi o s3_key correto
    s3_key = artifact.s3_key
    if s3_key.startswith("/") or s3_key.startswith("\\"):
        safe_name = os.path.basename(artifact.filename).replace("..", "_")
        s3_key = f"artifacts/{artifact.workspace_id}/{artifact.run_id}/{safe_name}"

    from app.core import storage as _s3
    # Verifica se o objeto existe no MinIO
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
    """Lista artefatos dos workspaces acessíveis ao usuário, paginada.

    Antes esta rota devolvia a tabela INTEIRA dos workspaces do usuário: sem
    LIMIT, sem OFFSET, e com `total = len(items)` — ou seja, não existia
    conceito de página. `artifacts` cresce a cada nó de saída de cada execução
    e só sai por `expires_at`, então a resposta crescia monotonicamente até a
    aba congelar renderizando tudo de uma vez.

    Filtro e busca também são do SERVIDOR agora: filtrar no cliente exigia
    baixar tudo, que é exatamente o que se quer evitar.

    A consulta em si mora em `app/services/artifact_service.py` desde que
    ganhou um segundo chamador — o servidor MCP, que não passa por request
    nenhuma. O que sobra aqui é a porta: quem pergunta (`get_current_user`) e
    com que alcance (`get_user_workspace_ids`). A forma da resposta não mudou.
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

_EXCLUIR_ARTEFATOS = "Requer role 'editor' ou superior para excluir artefatos."


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
    await exigir_papel_no_workspace(
        db, artifact.workspace_id, current_user.id_hash, ROLE_EDITOR, _EXCLUIR_ARTEFATOS,
    )

    # Conteudo no disco de um executor, objeto no MinIO, camada do portal: a
    # regra e a de toda remocao (`remover_artefatos`); aqui so a resposta.
    remocao = await remover_artefatos(db, [artifact], agendar_pendentes=True)
    if remocao.falhas_s3:
        # O MinIO falhou (fora "ja nao existe") e o registro ficou: o objeto
        # segue alcancavel pela reconciliacao, e repetir o pedido resolve.
        logger.error(
            "Delete cancelado para artefato %s: S3 falhou. "
            "Registro preservado; reconcile/cleanup tentara de novo.",
            artifact.s3_key,
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao remover do storage; tente novamente em alguns segundos.",
        )
    # Commit tambem sem nada apagado: persiste o `expires_at` dos pendentes.
    await db.commit()
    if remocao.pendentes_local or remocao.sem_rastro:
        # 202 com corpo, e nao HTTPException: nao e erro. O pedido foi aceito
        # e vai se concluir sozinho — usar o caminho de excecao faria a UI
        # pintar de vermelho um desfecho normal.
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
    """Remove multiplos artefatos de uma vez. Apenas owners/admins do workspace."""
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

    # Verifica permissao: todos devem pertencer a workspaces do usuario com role editor+
    for a in artifacts:
        if a.workspace_id not in workspace_ids:
            raise HTTPException(status_code=403, detail=f"Acesso negado ao artefato {a.id_hash}.")

    # Um papel por WORKSPACE envolvido, não por artefato (evita N+1). A
    # mensagem é a mesma qualquer que seja o workspace que barra, então a ordem
    # em que eles são conferidos não aparece na resposta.
    for ws_id in sorted({a.workspace_id for a in artifacts}):
        await exigir_papel_no_workspace(
            db, ws_id, current_user.id_hash, ROLE_EDITOR, _EXCLUIR_ARTEFATOS,
        )

    # A regra e a de toda remocao (`remover_artefatos`): os locais viram UMA
    # ordem por executor, o MinIO sai primeiro e a falha dele preserva a linha
    # (a reconciliacao tenta de novo), a camada do portal cai junto.
    remocao = await remover_artefatos(db, artifacts, agendar_pendentes=True)
    if remocao.falhas_s3:
        logger.error(
            "Batch-delete: %d artefato(s) pulado(s) por falha no S3. Reconcile tentara depois.",
            len(remocao.falhas_s3),
        )
    # Pendentes NAO entram em `skipped`: ali significa "falhou, tente de novo",
    # e estes vao acontecer sozinhos. Contar nos dois faria a UI somar o mesmo
    # artefato como erro E como pendente.
    pendentes = len(remocao.pendentes_local) + len(remocao.sem_rastro)

    # O commit roda tambem quando so ha pendentes. Com todos os artefatos
    # locais e o executor offline — o caso comum deste caminho — nada e
    # apagado, e um commit condicionado ao que foi apagado descartava o
    # `expires_at` que acabara de ser posto nos objetos ORM: a API respondia
    # "remocao pendente" e nada era agendado.
    if remocao.apagados or pendentes:
        await db.commit()

    return {
        "deleted": len(remocao.apagados),
        "skipped": len(remocao.falhas_s3),
        # Distingue "falhou, tente de novo" de "vai acontecer sozinho" — sem
        # isso a UI mostraria os dois como erro.
        "pendentes_no_executor": pendentes,
    }


# ── GET /artifacts/{id_hash}/download (público) ───────────────────────────────

@public_router.get("/{id_hash}/download")
@limiter.limit("10/minute")
async def download_artifact(
    id_hash: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Faz download de um artefato.
    - Sem credential_id → público (sem autenticação).
    - Com credential_id → aceita JWT de usuário autenticado OU token de artefato Bearer.
    """
    result = await db.execute(select(Artifact).where(Artifact.id_hash == id_hash))
    artifact = result.scalar_one_or_none()

    # Fallback: busca na portal_layers (GeoJSON armazenado no banco)
    if not artifact:
        from app.models.portal_layer import PortalLayer
        from app.models.workflow import Workflow
        from app.api.routers.portal_router import enforce_portal_access
        from fastapi.responses import JSONResponse
        pl_result = await db.execute(select(PortalLayer).where(PortalLayer.id_hash == id_hash))
        pl = pl_result.scalar_one_or_none()
        if pl:
            # SEG: mesmo gate da rota gemea /artifacts/portal/layers/{id}/download.
            # Este caminho e o que a UI do portal realmente chama, e servia o
            # GeoJSON inteiro sem checagem nenhuma: quem tivesse o UUID da camada
            # (devolvido publicamente por GET /artifacts/portal/{workflow_hash})
            # continuava baixando as geometrias mesmo depois de o dono marcar o
            # portal como privado/desabilitado ou desativar o workflow.
            wf_result = await db.execute(
                select(Workflow).where(Workflow.id_hash == pl.workflow_hash)
            )
            await enforce_portal_access(wf_result.scalar_one_or_none(), request)
            return JSONResponse(
                content=pl.geojson_data,
                headers={"Content-Disposition": f'attachment; filename="{pl.layer_key}.geojson"'},
            )
        raise HTTPException(status_code=404, detail="Artefato não encontrado.")

    # Validação de token quando artefato é protegido
    await _autorizar_download(artifact, request, db)

    return await _url_de_download(artifact)


# ── GET/PUT /artifacts/admin/settings (config de retenção) ───────────────────

@router.get("/admin/settings", dependencies=[Depends(require_admin)])
async def get_artifact_settings(db: AsyncSession = Depends(get_db)):
    """Retorna configuração global de retenção de artefatos."""
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
    Atualiza configuração global de retenção.
    Body: { "artifact_retention_days": <int|null> }
    null = sem expiração automática.
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
