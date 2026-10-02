import hmac
from app.core.utils.logger import get_logger
from typing import Callable, Dict
from fastapi import Request, HTTPException

logger = get_logger(__name__)

# ── Registry de validadores por tipo de credencial ─────────────────────────────
# Para adicionar um novo tipo: basta decorar a função com @register_validator("tipo")
_VALIDATOR_REGISTRY: Dict[str, Callable] = {}

# Validadores que AUTENTICAM QUEM CHAMOU, em vez de conferir a credencial.
#
# A distinção existe porque só um deles olha o `request`: o do token de webhook,
# que compara o header `Authorization` com o token guardado. Os outros apenas
# verificam se a credencial está completa (tem connectionString, tem chave de
# acesso) e valem em qualquer caminho.
#
# Sem separar os dois, o botão "Executar" do editor caía no validador de
# webhook: o header existe, mas leva o JWT de sessão do usuário, e a comparação
# devolvia "Token inválido" — exigindo o token de uma chamada externa de quem já
# estava autenticado por sessão e com papel de operator.
_AUTENTICAM_A_REQUISICAO: set = set()


def register_validator(*ctypes: str, autentica_requisicao: bool = False):
    """Registra uma função de validação para um ou mais tipos de credencial.

    `autentica_requisicao=True` marca o validador como autenticação de ENTRADA:
    ele só faz sentido no endpoint que recebe a chamada externa.
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
    """Valida a credencial delegando para o validador registrado pelo tipo.

    `autenticar_entrada=False` pula os validadores que autenticam quem chamou —
    usado nos disparos já autenticados por outro meio (botão Executar, cron).
    Os demais validadores continuam rodando: credencial incompleta é problema
    em qualquer caminho.
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

    # A MESMA regra da resolução (`validade_da_credencial`): antes esta cópia
    # comparava um `now` com fuso a um `expires_at` gravado sem fuso e dava
    # TypeError (500) em vez de 403.
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
