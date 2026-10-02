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
    Handler para exceções de domínio (AtlasBaseError e subclasses).
    Converte automaticamente para a resposta HTTP correta sem que os routers
    precisem capturar cada tipo de exceção individualmente.
    """
    content = {
        "error":   exc.error_code,
        "message": exc.detail,
    }
    # 409 da política de execução: a lista de workspaces que esvaziariam é o
    # que permite à tela oferecer "remover mesmo assim" com conhecimento.
    workspaces = getattr(exc, "workspaces", None)
    if workspaces:
        content["workspaces"] = workspaces
    return JSONResponse(status_code=exc.status_code, content=content)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTPException uniformly.
    """
    # Os headers da exceção seguem para o cliente: sem isto, `Retry-After`
    # (503 do webhook sem executor) e `WWW-Authenticate` morriam aqui.
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

    Remove `input` (e `ctx`) de cada erro: `exc.errors()` inclui o valor cru
    submetido pelo cliente, que num campo sensível (ex.: senha malformada em
    /auth/login) volta na resposta e pode ser capturado por proxies, logs ou
    APM. O cliente não precisa do próprio valor de volta — `loc`, `msg` e `type`
    bastam. Bônus: `ctx` às vezes carrega objetos de exceção não serializáveis.
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
    """`permission denied for table X` / `must be owner of table X` do
    PostgreSQL: o usuário da API não é dono (ou não tem GRANT) do objeto.
    Devolve o trecho legível, ou None se não é esse caso."""
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
    # Permissão no banco não é um bug de código: é configuração do ambiente, e
    # "Unexpected error occurred" escondia exatamente o que faltava conceder.
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