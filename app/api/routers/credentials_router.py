# routers/credentials_router.py

from app.core.utils.logger import get_logger
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialOut,
    CredentialOutWithData,
    CredentialTestRequest,
)
from app.services.credential_service import (
    create_credential,
    validation_error,
    get_credential_metadata,
    list_credential_metadata,
    delete_credential,
    update_credential,
)
from app.api.dependencies import (
    get_db,
    get_current_user,
    get_user_workspace_ids,
    verify_workspace_access,
)
from app.core.rate_limiter import limiter
from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS, CredentialTypeSchema

logger = get_logger(__name__)

router = APIRouter(
    prefix="/credentials",
    tags=["Credentials"]
)


@router.get(
    "/types",
    response_model=List[CredentialTypeSchema],
    summary="Listar tipos de credencial disponíveis com seus campos",
)
async def list_credential_types(_user=Depends(get_current_user)):
    """
    Returns the schemas of the supported credential types.
    The frontend uses this data to render guided forms.
    """
    return list(CREDENTIAL_TYPE_SCHEMAS.values())


@router.get(
    "/usage",
    summary="Contagem de uso por credencial nos workflows do workspace",
)
async def credential_usage(
    workspace_id: Optional[str] = Query(default=None, description="Filtra por workspace específico"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """
    For each credential referenced in a workflow of the user's workspace(s),
    returns {node_count, workflow_count}. Decrypts nothing — it only reads
    `properties.credential_id` from the definition (plain text).

    The count is done in Postgres. Previously this route materialized the
    `definition` of ALL the workspace's workflows (the CRUD layer estimates
    ~10 KB each) and iterated node by node in Python: the worker's event loop
    was busy deserializing JSON while every other request on that worker
    waited — and the whole scan repeated every time a credential modal was
    closed. Same path already used by `workflow_crud._has_node`.
    """
    from sqlalchemy import bindparam, text

    # The `OR workspace_id IS NULL` that existed in both branches handed the usage
    # count of the credentials of every legacy workflow without a workspace to
    # any authenticated user. The column is NOT NULL since 20260828_0001.
    if workspace_id:
        verify_workspace_access(workspace_id, workspace_ids)
        escopo = [workspace_id]
    else:
        escopo = workspace_ids

    if not escopo:
        return {}

    # `json_array_elements` blows up if `definition->'nodes'` is not an array
    # (empty definition, old format) — hence the CASE, evaluated before the
    # WHERE in the LATERAL.
    stmt = text("""
        SELECT
            node -> 'properties' ->> 'credential_id' AS credential_id,
            count(*)                    AS node_count,
            count(DISTINCT w.id_hash)   AS workflow_count
        FROM workflows w
        CROSS JOIN LATERAL json_array_elements(
            CASE WHEN json_typeof(w.definition -> 'nodes') = 'array'
                 THEN w.definition -> 'nodes'
                 ELSE '[]'::json END
        ) AS node
        WHERE w.deleted_at IS NULL
          AND w.workspace_id IN :workspace_ids
          AND node -> 'properties' ->> 'credential_id' IS NOT NULL
        GROUP BY 1
    """).bindparams(bindparam("workspace_ids", expanding=True))

    result = await db.execute(stmt, {"workspace_ids": list(escopo)})
    return {
        row.credential_id: {
            "node_count": row.node_count,
            "workflow_count": row.workflow_count,
        }
        for row in result
    }


@router.post(
    "/test",
    summary="Testar credencial antes de salvar",
)
@limiter.limit("10/minute")
async def test_credential(
    request: Request,
    data: CredentialTestRequest,
    _user=Depends(get_current_user),
):
    """
    Validates the required fields (and, for WFS ones, the node's rules — the
    same as on save) and, when possible, tests the real connectivity.
    Persists nothing — it only serves as immediate feedback to the user.
    """
    error = validation_error(data.type, data.data)
    if error:
        raise HTTPException(status_code=422, detail=error)

    result = await _test_connectivity(data.type, data.data)
    return result


async def _test_connectivity(cred_type: str, data: dict) -> dict:
    if cred_type in ("postgresql", "mysql"):
        return await _test_db_connection(cred_type, data)
    if cred_type == "s3":
        return await _test_s3_connection(data)
    return {"ok": True, "message": "Campos validados com sucesso."}


async def _test_db_connection(cred_type: str, data: dict) -> dict:
    from app.core.credentials.connection_builder import build_connection_data
    import asyncio

    built = build_connection_data(cred_type, data)
    conn_str = built.get("connectionString", "")

    def _try_connect():
        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine(conn_str, connect_args={"connect_timeout": 5})
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            engine.dispose()
            return {"ok": True, "message": "Conexão estabelecida com sucesso!"}
        except Exception as exc:
            logger.warning("Falha no teste de conexão DB: %s", exc)
            return {"ok": False, "message": "Falha na conexão com o banco de dados. Verifique as credenciais e o endereço do servidor."}

    try:
        return await asyncio.wait_for(asyncio.to_thread(_try_connect), timeout=10)
    except asyncio.TimeoutError:
        return {"ok": False, "message": "Tempo limite excedido ao tentar conectar (10s)."}
    except Exception as exc:
        logger.warning("Erro inesperado no teste de conexão DB: %s", exc)
        return {"ok": False, "message": "Erro inesperado ao testar a conexão."}


async def _test_s3_connection(data: dict) -> dict:
    import asyncio
    from urllib.parse import urlparse

    endpoint = data.get("endpoint_url", "").strip()
    if endpoint:
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {"ok": False, "message": "endpoint_url inválido: use http:// ou https://."}

        # SSRF: bloquear endpoint apontando para hosts internos/cloud metadata
        # (ex: http://169.254.169.254 — AWS metadata). validate_url_ssrf
        # resolve DNS e rejeita IPs privados/loopback/link-local.
        from flow.utils.geo_helpers import validate_url_ssrf
        try:
            await asyncio.to_thread(validate_url_ssrf, endpoint)
        except ValueError as exc:
            return {"ok": False, "message": f"endpoint_url bloqueado por segurança: {exc}"}

    def _try_s3():
        try:
            # The same client that the SaveToS3 node builds with the resolved
            # credential: the test approves exactly what the execution will use.
            from flow.utils.s3_cliente import s3_client
            s3_client(data).list_buckets()
            return {"ok": True, "message": "Credenciais S3 válidas!"}
        except ImportError:
            return {"ok": True, "message": "Campos validados (boto3 não instalado para teste real)."}
        except Exception as exc:
            logger.warning("Falha no teste de conexão S3: %s", exc)
            return {"ok": False, "message": "Falha na autenticação S3. Verifique as credenciais e o endpoint."}

    try:
        return await asyncio.wait_for(asyncio.to_thread(_try_s3), timeout=10)
    except asyncio.TimeoutError:
        return {"ok": False, "message": "Tempo limite excedido ao tentar conectar (10s)."}
    except Exception as exc:
        logger.warning("Erro inesperado no teste de conexão S3: %s", exc)
        return {"ok": False, "message": "Erro inesperado ao testar a conexão."}


@router.post("", response_model=CredentialOut, summary="Criar uma nova credencial")
@limiter.limit("20/minute")
async def create_credential_route(
    request: Request,
    data: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    # It is only possible to SHARE with a workspace the user belongs to —
    # otherwise guessing an id_hash would be enough to inject a credential into
    # another tenant's members screen.
    if data.workspace_id:
        verify_workspace_access(data.workspace_id, workspace_ids)
    credential = await create_credential(data, db, owner_id=current_user.id_hash)
    logger.info("Credencial criada: tipo=%s owner=%s", data.type, current_user.id_hash)
    return credential


@router.get("", response_model=List[CredentialOut], summary="Listar credenciais")
async def list_credentials(
    type: Optional[str] = Query(default=None, description="Filtrar pelo tipo de credencial"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    # Returns the user's credentials UNION those shared with their workspaces
    # (workspace_id filled in). The scope is never opened up: owner_id always
    # enters the clause.
    return await list_credential_metadata(
        db, owner_id=current_user.id_hash, type=type, workspace_ids=workspace_ids,
    )


@router.get("/{cred_id}/data", response_model=CredentialOutWithData, summary="Obter credencial com dados descriptografados")
async def get_credential_data(
    cred_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Returns the credential's decrypted data to pre-fill the edit form.
    Only the credential's owner can access this endpoint.
    """
    from app.core.utils.encryption import decrypt_credential_data
    cred = await get_credential_metadata(db, cred_id, owner_id=current_user.id_hash)
    decrypted = decrypt_credential_data(cred.data or {})
    # model_validate brings metadata + expires_at (property) and the new columns;
    # the next line REPLACES the encrypted data with the decrypted one. The order
    # matters: without the overwrite, the secret would go out encrypted (and
    # useless) in the body.
    out = CredentialOutWithData.model_validate(cred)
    out.data = decrypted
    return out


@router.put("/{cred_id}", response_model=CredentialOut, summary="Atualizar credencial por ID")
@limiter.limit("20/minute")
async def update_credential_route(
    request: Request,
    cred_id: UUID,
    data: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    if data.workspace_id:
        verify_workspace_access(data.workspace_id, workspace_ids)
    credential = await update_credential(cred_id, data, db, owner_id=current_user.id_hash)
    logger.info("Credencial atualizada: id=%s owner=%s", cred_id, current_user.id_hash)
    return credential


@router.delete("/{cred_id}", status_code=204, summary="Deletar credencial por ID")
@limiter.limit("20/minute")
async def delete_credential_route(
    request: Request,
    cred_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_credential(db, cred_id, owner_id=current_user.id_hash)
    logger.info("Credencial deletada: id=%s owner=%s", cred_id, current_user.id_hash)
    return
