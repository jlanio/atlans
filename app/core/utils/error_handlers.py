# app/error_handlers.py
import re
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


async def atlas_domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for domain exceptions (AtlasBaseError and subclasses).
    Converts automatically to the correct HTTP response without the routers
    having to catch each exception type individually.
    """
    content = {
        "error":   exc.error_code,
        "message": exc.detail,
    }
    # 409 from the execution policy: the list of workspaces that would be emptied
    # is what lets the screen offer "remove anyway" knowingly.
    workspaces = getattr(exc, "workspaces", None)
    if workspaces:
        content["workspaces"] = workspaces
    return JSONResponse(status_code=exc.status_code, content=content)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTPException uniformly.
    """
    # The exception's headers go on to the client: without this, `Retry-After`
    # (503 from the webhook with no executor) and `WWW-Authenticate` died here.
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_exception",
            "message": exc.detail,
            "status_code": exc.status_code
        },
        headers=getattr(exc, "headers", None) or None,
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors uniformly.

    Removes `input` (and `ctx`) from each error: `exc.errors()` includes the
    raw value submitted by the client, which for a sensitive field (e.g., a
    malformed password on /auth/login) comes back in the response and can be
    captured by proxies, logs or APM. The client does not need its own value
    back — `loc`, `msg` and `type` are enough. Bonus: `ctx` sometimes carries
    non-serializable exception objects.
    """
    details = [
        {k: v for k, v in err.items() if k not in ("input", "ctx")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Validation failed",
            "details": details,
        }
    )

def _permissao_negada_no_banco(exc: Exception) -> str | None:
    """PostgreSQL's `permission denied for table X` / `must be owner of table X`:
    the API user is not the owner of (or has no GRANT on) the object.
    Returns the readable excerpt, or None if this is not the case."""
    from sqlalchemy.exc import DBAPIError

    if not isinstance(exc, DBAPIError):
        return None
    texto = str(getattr(exc, "orig", None) or exc)
    m = re.search(r"(permission denied for \w+ \S+|must be owner of \w+ \S+)", texto)
    return m.group(1) if m else None


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unexpected exceptions.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    # A database permission is not a code bug: it is environment configuration,
    # and "Unexpected error occurred" hid exactly what was missing a grant.
    permissao = _permissao_negada_no_banco(exc)
    if permissao:
        return JSONResponse(
            status_code=500,
            content={
                "error": "database_permission_denied",
                "message": (
                    f"O usuário do banco de dados da API não tem privilégio: {permissao}. "
                    "Conceda a permissão (ou a propriedade do objeto) ao usuário da API e tente de novo."
                ),
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Unexpected error occurred"
        }
    )
async def rate_limit_exceeded_global_handler(request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too Many Requests"}
    )