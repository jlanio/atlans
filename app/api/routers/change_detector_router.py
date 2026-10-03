# app/api/routers/change_detector_router.py
"""
Internal endpoint for the `ChangeDetector` node (executed on a remote executor)
to swap the last execution's hash stored in the server's Redis.

Why it exists: external executors run `flow/` in an environment without access
to `app.core.redis`. This router serves as an HTTP bridge to the server's Redis,
keeping the state centralized across multiple executors that may execute runs
of the same scheduled workflow.

Auth: reuses the pattern of the `/drive/executor-*` endpoints — now via an mTLS
cert validated by Traefik and propagated in `X-Forwarded-Tls-Client-Cert-Info`.
The drive_router's `_auth_agent` resolves the executor_id and its workspace_ids.

Layout of the keys in Redis:
    change_detector:wf:{workflow_hash}:{node_id}            (workflow scope)
    change_detector:ws:{workspace_id}:{shared_key}          (workspace scope)

Prefix validation: the `key` accepted by the endpoint must start with `wf:` or
`ws:`. A simple block against a compromised executor trying to manipulate other
Redis keys (e.g. idempotency, JWT blacklist, presence).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.api.routers.executor_drive_router import _auth_agent
from app.core.redis import get_redis_pool
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/internal/change-detector", tags=["internal"])

# External key regex (without the "change_detector:" prefix — added here).
# Accepted format: "wf:<scope_id>:<identifier>" or "ws:<scope_id>:<identifier>".
# Characters allowed in scope_id and identifier: alphanumerics + hyphen +
# underscore (UUIDs and human shared_keys). Maximum length 200 chars for the
# whole key — Redis handles much more, but it limits the surface.
_KEY_PATTERN = re.compile(r"^(wf|ws):[A-Za-z0-9_\-]{1,80}:[A-Za-z0-9_\-]{1,100}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_TTL_SECONDS = 31_536_000  # 1 ano


def _validate_key(key: str) -> str:
    """Valida formato externo e retorna a chave Redis qualificada com prefixo."""
    if not _KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=400,
            detail="Formato de chave inválido. Esperado 'wf:{id}:{node}' ou 'ws:{id}:{shared_key}'.",
        )
    return f"change_detector:{key}"


async def _authorize_key(key: str, executor, db: AsyncSession) -> str:
    """Validates the key's format AND scope, returning the qualified Redis key.

    SEC: format validation alone only prevented the executor from touching
    OTHER Redis keys — it did not prevent it from reading, overwriting or
    deleting the ChangeDetector state of any workflow on the platform.
    A compromised executor could freeze another tenant's scheduled executions
    (pinning the hash as "no change") or force mass reprocessing.

    Scope:
      ws:{workspace_id}:...  → the workspace must be among the executor's
      wf:{workflow_hash}:... → the workflow must belong to one of those workspaces
    """
    redis_key = _validate_key(key)
    scope, scope_id, _ = key.split(":", 2)
    allowed_ws = set(getattr(executor, "_resolved_ws_ids", None) or [])

    if scope == "ws":
        target_ws = scope_id
    else:
        from app.models.models import Workflow
        from sqlalchemy import select
        result = await db.execute(
            select(Workflow.workspace_id).where(Workflow.id_hash == scope_id)
        )
        target_ws = result.scalar_one_or_none()
        if target_ws is None:
            # Nonexistent workflow: does not reveal the difference between "does not
            # exist" and "is not yours" — same response for both cases.
            raise HTTPException(status_code=403, detail="Acesso negado a esta chave.")

    if target_ws not in allowed_ws:
        logger.warning(
            "Executor '%s' tentou acessar chave change_detector fora do seu escopo: %s (ws=%s).",
            executor.id_hash, key, target_ws,
        )
        raise HTTPException(status_code=403, detail="Acesso negado a esta chave.")

    return redis_key


class SwapHashBody(BaseModel):
    hash: str = Field(..., description="SHA-256 hex lowercase (64 chars)")
    ttl_seconds: int = Field(0, ge=0, le=_MAX_TTL_SECONDS, description="0 = sem TTL")


@router.post("/{key:path}")
async def swap_hash(
    key: str,
    body: SwapHashBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Writes the current execution's hash and returns the PREVIOUS one — one operation.

    Atomic `SET ... GET` in Redis. Replaces the old GET+PUT pair for two
    reasons: half the HTTP round-trips per node, and — the important one — no
    read→decide→write window in which two simultaneous runs of the same workflow
    read the same old hash and BOTH decided "Mudou" (changed), duplicating the
    downstream side effect.

    `previous_hash: null` = first execution (or expired TTL — Redis does not
    distinguish an expired key from a key that never existed).
    ttl_seconds=0 = no expiry.
    """
    executor = await _auth_agent(request, db)
    redis_key = await _authorize_key(key, executor, db)

    if not _HASH_PATTERN.match(body.hash):
        raise HTTPException(
            status_code=422,
            detail="Hash inválido. Esperado SHA-256 hex lowercase (64 chars).",
        )

    rc = get_redis_pool()
    try:
        previous = await rc.set(
            redis_key, body.hash,
            ex=body.ttl_seconds or None,   # 0 → no EX (persistent)
            get=True,                      # devolve o valor anterior (Redis ≥ 6.2)
        )
    except Exception as exc:
        logger.error("change_detector SWAP %s: Redis indisponível: %s", redis_key, exc)
        # The executor decides the branch according to the `on_backend_error` policy
        # configured on the node; 503 is the signal for "could neither read nor write".
        raise HTTPException(status_code=503, detail="Backend de estado indisponível.")

    if isinstance(previous, bytes):
        previous = previous.decode()
    return {"previous_hash": previous}
