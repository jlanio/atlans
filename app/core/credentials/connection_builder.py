"""
Builds connection strings and authentication structures from the individual
fields provided by the user. Called during credential create/update.
"""

from typing import Optional
from urllib.parse import quote_plus


def build_connection_data(cred_type: str, data: dict) -> dict:
    """
    Given the credential type and the raw fields, returns the dict enriched
    with connectionString (for database types) or other derived fields.
    Does not modify the original dict — returns a copy.
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
    Validates that all required fields of the schema are present and non-empty.
    Returns an error message, or None if OK.
    """
    from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS

    schema = CREDENTIAL_TYPE_SCHEMAS.get(cred_type)
    if schema is None:
        return None  # free-form type — no schema validation

    # `str(... or "")`: validation also runs on the already-stored `data`
    # (a type change without `data` in the request), and a legacy value that is not a string
    # (a numeric port) must not become a 500.
    missing = [
        f.label
        for f in schema.fields
        if f.required and not str(data.get(f.key) or "").strip()
    ]
    if missing:
        return f"Campos obrigatórios ausentes: {', '.join(missing)}"
    return None
