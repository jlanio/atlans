# app/core/utils/encryption.py
from cryptography.fernet import Fernet, MultiFernet
from app.core.config import FERNET_KEYS

if not FERNET_KEYS:
    raise RuntimeError("❌ Nenhuma chave Fernet definida (FERNET_KEY/FERNET_KEYS).")

# MultiFernet: encrypt() uses the FIRST key; decrypt() tries all of them in order.
# With a single key it is indistinguishable from the former Fernet(key) — the
# rotation path (F4) is additive and changes nothing when FERNET_KEYS is not used.
# An invalid key makes Fernet(...) raise right at import: fail early, as before.
fernet = MultiFernet([Fernet(k.encode()) for k in FERNET_KEYS])


def encrypt_string(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


def decrypt_string(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()


def encrypt_workflow_connections(definition: dict) -> dict:
    for node in definition.get("nodes", []):
        props = node.get("properties", {})
        conn_str = props.get("connectionString")
        if conn_str and not conn_str.startswith("gAAAA"):
            props["connectionString"] = encrypt_string(conn_str)
    return definition


def decrypt_credential_data(raw_data: dict) -> dict:
    """Decrypts values with the 'gAAAA' prefix in a credentials dictionary.

    Runs only on the server: credentials are decrypted before they go into
    the job's encrypted envelope, so the executor receives the values in
    the clear and never needs the FERNET_KEY.
    """
    return {
        k: (decrypt_string(v) if isinstance(v, str) and v.startswith("gAAAA") else v)
        for k, v in raw_data.items()
    }


def decrypt_workflow_connections(definition: dict) -> dict:
    for node in definition.get("nodes", []):
        props = node.get("properties", {})
        conn_str = props.get("connectionString")
        if conn_str and conn_str.startswith("gAAAA"):
            try:
                props["connectionString"] = decrypt_string(conn_str)
            except Exception:
                raise ValueError("❌ Falha ao descriptografar a connection string.")
    return definition
