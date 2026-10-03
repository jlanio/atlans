# executor/crypto.py
"""
Executor cryptographic operations:
  - Loading of the X25519 private key generated at enrollment
  - Decryption of jobs (X25519 ECDH + HKDF + AES-256-GCM)
  - Verification of the server's Ed25519 signature

The GENERATION of the X25519 key does NOT live here: it happens exactly once in
`executor/enrollment.py::enroll`, together with sending the public key to the server.
See `PrivateKeyMissingError` for why.
"""
import base64
import json
import logging
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = logging.getLogger(__name__)

_HKDF_INFO = b"atlas-executor-job-v1"


# ── Loading the X25519 key ────────────────────────────────────────────────────

class PrivateKeyMissingError(RuntimeError):
    """
    X25519 private key missing or unreadable.

    Raised instead of generating a new key. Generating was the old behavior and
    was ALWAYS wrong after enrollment: the public key registered on the server
    no longer matched the local private key, the executor came up and showed as
    "online", and 100% of jobs died in `decrypt_job_payload` with a message
    that suggested "corrupted ciphertext" — sending the operator to investigate network /
    server when the problem was the local key. Failing loudly here trades a silent,
    misleading bug for a clear instruction: redo the enrollment.
    """


def load_private_key(key_b64: str | None, key_path: str) -> X25519PrivateKey:
    """
    Loads the executor's X25519 private key. NEVER generates a new key.

    Order:
      1. EXECUTOR_PRIVATE_KEY (base64 of the 32 raw bytes), if provided
      2. PEM file (PKCS8) at `key_path`, written by enroll

    Raises PrivateKeyMissingError if neither exists or if the material
    is invalid.
    """
    if key_b64:
        try:
            raw = base64.b64decode(key_b64, validate=True)
            return X25519PrivateKey.from_private_bytes(raw)
        except Exception as exc:
            raise PrivateKeyMissingError(
                "EXECUTOR_PRIVATE_KEY está definida mas é inválida "
                f"(esperado base64 de 32 bytes raw X25519): {exc}. "
                "Remova a variável para usar a chave do enrollment em "
                f"'{key_path}', ou refaça o enrollment."
            ) from exc

    if not (os.path.exists(key_path) and os.path.getsize(key_path) > 0):
        raise PrivateKeyMissingError(
            f"Chave privada X25519 não encontrada em '{key_path}'. "
            "Ela é gerada uma única vez no enrollment e a pública correspondente "
            "fica registrada no servidor — sem ela nenhum job pode ser "
            "descriptografado. Refaça o enrollment: "
            "`python -m executor enroll --otp=<OTP> --server=<URL>`."
        )

    try:
        with open(key_path, "rb") as f:
            key = load_pem_private_key(f.read(), password=None)
    except Exception as exc:
        raise PrivateKeyMissingError(
            f"Chave privada X25519 em '{key_path}' é ilegível: {exc}. "
            "Refaça o enrollment para gerar um novo par."
        ) from exc

    if not isinstance(key, X25519PrivateKey):
        raise PrivateKeyMissingError(
            f"Arquivo '{key_path}' contém uma chave {type(key).__name__}, não X25519. "
            "Provavelmente aponta para a chave Ed25519 do cert mTLS (key.pem). "
            "Corrija EXECUTOR_PRIVATE_KEY_PATH ou refaça o enrollment."
        )
    return key


# ── Ed25519 signature verification ───────────────────────────────────────────

def verify_signature(message: dict, server_pub_b64: str) -> bool:
    """
    Verifies the Ed25519 signature of the job envelope.
    Returns True if valid. Does not raise.

    Canonical bytes = json(envelope, sort_keys) + "|" + ephemeral_public + "|" + ciphertext
    """
    try:
        pub_raw = base64.b64decode(server_pub_b64)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_raw)

        # Joins the ALREADY ENCODED pieces instead of concatenating strings and encoding
        # the result: the previous version created a str of the total size (the
        # base64 ciphertext of a large workflow is a few MB) and right
        # after a bytes of the same size. The final bytes are identical —
        # the UTF-8 of a concatenation is the concatenation of the UTF-8s, and the
        # '|' separator is ASCII —, so the server's signature still matches.
        canonical = b"|".join((
            json.dumps(message["envelope"], sort_keys=True, ensure_ascii=False).encode(),
            message["ephemeral_public"].encode(),
            message["ciphertext"].encode(),
        ))

        pub_key.verify(base64.b64decode(message["signature"]), canonical)
        return True
    except Exception as exc:
        logger.error("Falha na verificação de assinatura: %s", exc)
        return False


# ── Payload decryption ────────────────────────────────────────────────────────

def decrypt_job_payload(message: dict, agent_priv: X25519PrivateKey) -> dict:
    """
    Decrypts the encrypted payload of a job.

    Flow:
      1. Extracts the server's ephemeral public key (X25519)
      2. ECDH: shared_secret = X25519(agent_priv, ephemeral_pub)
      3. HKDF-SHA256(shared_secret, salt=nonce_hex, info=_HKDF_INFO) → aes_key
      4. AES-256-GCM decrypt (gcm_nonce in the first 12 bytes of the ciphertext)
      5. json.loads → in-memory dict

    Raises ValueError if decryption fails (corrupted ciphertext / wrong key).
    """
    try:
        envelope = message["envelope"]
        nonce_hex = envelope["nonce"]

        # Server's ephemeral public key
        ephemeral_pub_raw = base64.b64decode(message["ephemeral_public"])
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey as _X
        ephemeral_pub = _X.from_public_bytes(ephemeral_pub_raw)

        # ECDH
        shared_secret = agent_priv.exchange(ephemeral_pub)

        # AES key derivation
        aes_key = HKDF(
            algorithm=SHA256(),
            length=32,
            salt=bytes.fromhex(nonce_hex),
            info=_HKDF_INFO,
        ).derive(shared_secret)

        # Descriptografa AES-256-GCM
        ciphertext_bytes = base64.b64decode(message["ciphertext"])
        gcm_nonce = ciphertext_bytes[:12]
        ct_and_tag = ciphertext_bytes[12:]

        aesgcm    = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(gcm_nonce, ct_and_tag, None)

        payload = json.loads(plaintext.decode())
        return payload

    except Exception as exc:
        raise ValueError(f"Falha ao descriptografar payload do job: {exc}") from exc
    finally:
        # Best-effort: wipes sensitive variables from memory
        try:
            del shared_secret, aes_key, plaintext  # type: ignore[name-defined]
        except Exception as exc:
            logger.debug("Falha ao limpar variáveis sensíveis da memória: %s", exc)
