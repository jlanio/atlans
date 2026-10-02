"""
Monta strings de conexão e estruturas de autenticação a partir dos campos
individuais fornecidos pelo usuário. Chamado durante create/update de credencial.
"""

from typing import Optional
from urllib.parse import quote_plus


def build_connection_data(cred_type: str, data: dict) -> dict:
    """
    Dado o tipo de credencial e os campos brutos, retorna o dict enriquecido
    com connectionString (para tipos de banco) ou outros campos derivados.
    Não modifica o dict original — retorna uma cópia.
    """
    result = dict(data)

    if cred_type == "postgresql":
        result["connectionString"] = _build_postgres_dsn(result)

    elif cred_type == "mysql":
        result["connectionString"] = _build_mysql_dsn(result)

    return result


def _build_postgres_dsn(data: dict) -> str:
    host = quote_plus(data.get("host", "localhost"))
    port = data.get("port", "5432") or "5432"
    database = quote_plus(data.get("database", ""))
    user = quote_plus(data.get("user", ""))
    password = quote_plus(data.get("password", ""))
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def _build_mysql_dsn(data: dict) -> str:
    host = quote_plus(data.get("host", "localhost"))
    port = data.get("port", "3306") or "3306"
    database = quote_plus(data.get("database", ""))
    user = quote_plus(data.get("user", ""))
    password = quote_plus(data.get("password", ""))
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def validate_required_fields(cred_type: str, data: dict) -> Optional[str]:
    """
    Valida que todos os campos obrigatórios do schema estejam presentes e não-vazios.
    Retorna mensagem de erro ou None se OK.
    """
    from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS

    schema = CREDENTIAL_TYPE_SCHEMAS.get(cred_type)
    if schema is None:
        return None  # tipo livre — sem validação de schema

    # `str(... or "")`: a validação também roda sobre o `data` já gravado
    # (troca de tipo sem `data` no pedido), e um valor legado que não é string
    # (uma porta numérica) não pode virar um 500.
    missing = [
        f.label
        for f in schema.fields
        if f.required and not str(data.get(f.key) or "").strip()
    ]
    if missing:
        return f"Campos obrigatórios ausentes: {', '.join(missing)}"
    return None
