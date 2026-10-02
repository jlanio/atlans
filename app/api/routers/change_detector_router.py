# app/api/routers/change_detector_router.py
"""
Endpoint interno para o node `ChangeDetector` (executado em executor remoto)
trocar o hash da última execução armazenado no Redis do servidor.

Por que existe: executores externos rodam `flow/` em ambiente sem acesso a
`app.core.redis`. Este router serve como bridge HTTP ao Redis do servidor,
mantendo o estado centralizado entre múltiplos executores que podem executar
runs do mesmo workflow agendado.

Auth: reusa o padrao dos endpoints `/drive/executor-*` — agora via cert mTLS
validado por Traefik e propagado em `X-Forwarded-Tls-Client-Cert-Info`.
`_auth_agent` do drive_router resolve o executor_id e seus workspace_ids.

Layout das chaves no Redis:
    change_detector:wf:{workflow_hash}:{node_id}            (escopo workflow)
    change_detector:ws:{workspace_id}:{shared_key}          (escopo workspace)

Validação de prefixo: o `key` aceito pelo endpoint deve começar com
`wf:` ou `ws:`. Bloqueio simples contra um executor comprometido tentar
manipular outras chaves Redis (ex: idempotency, JWT blacklist, presence).
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

# Regex de chave externa (sem o prefixo "change_detector:" — adicionado aqui).
# Formato aceito: "wf:<scope_id>:<identifier>" ou "ws:<scope_id>:<identifier>".
# Caracteres permitidos em scope_id e identifier: alfanuméricos + hífen +
# underscore (UUIDs e shared_keys humanas). Comprimento máximo 200 chars
# para a chave inteira — Redis aguenta muito mais, mas limita superfície.
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
    """Valida o formato E o escopo da chave, devolvendo a chave Redis qualificada.

    SEG: a validação de formato sozinha impedia apenas que o executor tocasse
    OUTRAS chaves do Redis — não impedia que ele lesse, sobrescrevesse ou
    apagasse o estado de ChangeDetector de qualquer workflow da plataforma.
    Um executor comprometido podia congelar execuções agendadas de outro tenant
    (fixando o hash como "sem mudança") ou forçar reprocessamento em massa.

    Escopo:
      ws:{workspace_id}:...  → workspace tem de estar entre os do executor
      wf:{workflow_hash}:... → workflow tem de pertencer a um desses workspaces
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
            # Workflow inexistente: não revela a diferença entre "não existe" e
            # "não é seu" — mesma resposta dos dois casos.
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
    """Grava o hash da execução atual e devolve o ANTERIOR — uma operação.

    `SET ... GET` atômico no Redis. Substitui o antigo par GET+PUT por duas
    razões: metade dos round-trips HTTP por nó, e — a importante — sem a
    janela ler→decidir→gravar em que duas runs simultâneas do mesmo workflow
    liam o mesmo hash antigo e AMBAS decidiam "Mudou", duplicando o efeito
    colateral a jusante.

    `previous_hash: null` = primeira execução (ou TTL vencido — o Redis não
    distingue chave expirada de chave que nunca existiu).
    ttl_seconds=0 = sem expiração.
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
            ex=body.ttl_seconds or None,   # 0 → sem EX (persistente)
            get=True,                      # devolve o valor anterior (Redis ≥ 6.2)
        )
    except Exception as exc:
        logger.error("change_detector SWAP %s: Redis indisponível: %s", redis_key, exc)
        # O executor decide o branch conforme a política `on_backend_error`
        # configurada no nó; 503 é o sinal de "não consegui nem ler nem gravar".
        raise HTTPException(status_code=503, detail="Backend de estado indisponível.")

    if isinstance(previous, bytes):
        previous = previous.decode()
    return {"previous_hash": previous}
