# app/core/utils/encryption.py
from cryptography.fernet import Fernet, MultiFernet
from app.core.config import FERNET_KEYS

if not FERNET_KEYS:
    raise RuntimeError("❌ Nenhuma chave Fernet definida (FERNET_KEY/FERNET_KEYS).")

# MultiFernet: encrypt() usa a PRIMEIRA chave; decrypt() tenta todas na ordem.
# Com uma única chave é indistinguível do Fernet(chave) de antes — o caminho de
# rotação (F4) é aditivo e não muda nada quando FERNET_KEYS não é usado.
# Uma chave inválida faz Fernet(...) levantar já no import: falha cedo, como antes.
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
    """Descriptografa valores com prefixo 'gAAAA' em um dicionário de credenciais.

    Roda apenas no servidor: as credenciais sao descriptografadas antes de
    entrarem no envelope cifrado do job, entao o executor recebe os valores
    em claro e nunca precisa da FERNET_KEY.
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
