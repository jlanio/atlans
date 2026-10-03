# flow/utils/safe_env.py
# Exposes only safe environment variables to Jinja2 templates.
# Prevents leaking secrets (DATABASE_URL, FERNET_KEY, etc.).

import os

# Variables safe by default — none contains credentials
_DEFAULT_SAFE_KEYS = {
    "TZ", "NODE_ENV", "ALLOWED_FILE_DIRS", "LANG", "LC_ALL",
}

# Administrador pode estender via EXPOSED_ENV_VARS="VAR1,VAR2"
_extra = os.getenv("EXPOSED_ENV_VARS", "")
if _extra:
    _DEFAULT_SAFE_KEYS.update(k.strip() for k in _extra.split(",") if k.strip())


def safe_env() -> dict:
    """Returns a dict with only the allowed environment variables."""
    return {k: os.environ[k] for k in _DEFAULT_SAFE_KEYS if k in os.environ}
