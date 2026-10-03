import hmac
from app.core.utils.logger import get_logger
from typing import Callable, Dict
from fastapi import Request, HTTPException

logger = get_logger(__name__)

# ── Registry of validators per credential type ─────────────────────────────────
# To add a new type: just decorate the function with @register_validator("tipo")
_VALIDATOR_REGISTRY: Dict[str, Callable] = {}

# Validators that AUTHENTICATE THE CALLER, instead of checking the credential.
#
# The distinction exists because only one of them looks at the `request`: the webhook
# token one, which compares the `Authorization` header with the stored token. The others only
# check whether the credential is complete (has a connectionString, has an access
# key) and apply on any path.
#
# Without separating the two, the editor's "Executar" (Run) button fell into the webhook
# validator: the header exists, but it carries the user's session JWT, and the comparison
# returned "Token inválido" (invalid token) — demanding an external call's token from someone
# already authenticated by session and holding the operator role.
_AUTENTICAM_A_REQUISICAO: set = set()


def register_validator(*ctypes: str, autentica_requisicao: bool = False):
    """Registers a validation function for one or more credential types.

    `autentica_requisicao=True` marks the validator as INBOUND authentication:
    it only makes sense on the endpoint that receives the external call.
    """
    def decorator(fn: Callable):
        for ctype in ctypes:
            _VALIDATOR_REGISTRY[ctype] = fn
            if autentica_requisicao:
                _AUTENTICAM_A_REQUISICAO.add(ctype)
        return fn
    return decorator


async def validate_credential_by_type(
    cred: dict, request: Request = None, autenticar_entrada: bool = True,
) -> None:
    """Validates the credential by delegating to the validator registered for its type.

    `autenticar_entrada=False` skips the validators that authenticate the caller —
    used for triggers already authenticated by other means (Run button, cron).
    The remaining validators still run: an incomplete credential is a problem
    on any path.
    """
    ctype = cred.get("type")
    validator = _VALIDATOR_REGISTRY.get(ctype)
    if not validator:
        logger.debug("Tipo de credencial '%s' sem validação específica.", ctype)
        return

    if not autenticar_entrada and ctype in _AUTENTICAM_A_REQUISICAO:
        logger.debug(
            "Credencial '%s' autentica a requisição — pulada em disparo já autenticado.",
            ctype,
        )
        return

    validator(cred, request)


# ── Validadores ────────────────────────────────────────────────────────────────

@register_validator("webhook_token", "WebhookAuthToken", autentica_requisicao=True)
def _validate_webhook_token(cred: dict, request: Request) -> None:
    if not request:
        raise HTTPException(status_code=401, detail="Request HTTP é necessário para autenticação via token.")

    expected_token = cred.get("token")
    token_provided = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    expires_at_str = cred.get("expires_at")

    if not expected_token:
        raise HTTPException(status_code=500, detail="Token ausente na credencial")

    if not token_provided:
        raise HTTPException(status_code=401, detail="Token não fornecido no header Authorization")

    if not hmac.compare_digest(token_provided, expected_token):
        raise HTTPException(status_code=403, detail="Token inválido")

    # The SAME rule as resolution (`validade_da_credencial`): before, this copy
    # compared a timezone-aware `now` to an `expires_at` stored without timezone and raised
    # TypeError (500) instead of 403.
    from app.core.authorization.credential_loader import validade_da_credencial

    validade = validade_da_credencial(expires_at_str)
    if validade == "expirada":
        raise HTTPException(status_code=403, detail="Token expirado")
    if validade == "invalida":
        raise HTTPException(status_code=500, detail="Formato inválido de expires_at")


@register_validator("postgresql", "mysql", "db")
def _validate_db_credential(cred: dict, _request=None) -> None:
    if "connectionString" not in cred:
        raise HTTPException(
            status_code=500,
            detail="Credencial de banco incompleta: connectionString ausente",
        )


@register_validator("s3")
def _validate_s3_credential(cred: dict, _request=None) -> None:
    missing = [k for k in ("access_key_id", "secret_access_key", "region") if not cred.get(k)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Credencial S3 incompleta. Campos ausentes: {', '.join(missing)}",
        )


@register_validator("http_bearer")
def _validate_http_bearer(cred: dict, _request=None) -> None:
    if not cred.get("token"):
        raise HTTPException(status_code=500, detail="Credencial HTTP Bearer sem token definido")


@register_validator("http_basic")
def _validate_http_basic(cred: dict, _request=None) -> None:
    missing = [k for k in ("username", "password") if not cred.get(k)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Credencial HTTP Basic incompleta. Campos ausentes: {', '.join(missing)}",
        )


@register_validator("smtp")
def _validate_smtp_credential(cred: dict, _request=None) -> None:
    missing = [k for k in ("host", "username", "password") if not cred.get(k)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Credencial SMTP incompleta. Campos ausentes: {', '.join(missing)}",
        )
