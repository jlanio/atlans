# flow/utils/safe_env.py
# Expoe apenas variaveis de ambiente seguras para templates Jinja2.
# Impede vazamento de segredos (DATABASE_URL, FERNET_KEY, etc.).

import os

# Variaveis seguras por padrao — nenhuma contem credenciais
_DEFAULT_SAFE_KEYS = {
    "TZ", "NODE_ENV", "ALLOWED_FILE_DIRS", "LANG", "LC_ALL",
}

# Administrador pode estender via EXPOSED_ENV_VARS="VAR1,VAR2"
_extra = os.getenv("EXPOSED_ENV_VARS", "")
if _extra:
    _DEFAULT_SAFE_KEYS.update(k.strip() for k in _extra.split(",") if k.strip())


def safe_env() -> dict:
    """Retorna dict com apenas as variaveis de ambiente permitidas."""
    return {k: os.environ[k] for k in _DEFAULT_SAFE_KEYS if k in os.environ}
