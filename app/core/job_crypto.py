# app/core/job_crypto.py
"""
Job encryption for Executors.

Scheme:
  - Encrypts: X25519 (ephemeral ECDH) + HKDF-SHA256 + AES-256-GCM
  - Signs:    Ed25519 (static server key)

Per-job forward secrecy: each job uses an ephemeral X25519 pair discarded after sending.
The executor can only decrypt with its X25519 private key —
compromising the executor's static key does not expose earlier jobs.

Format of the message sent to the executor:
{
  "envelope": {
    "job_id":          str (UUID4),
    "target_executor_id": str,
    "workspace_id":    str,
    "job_type":        str,
    "issued_at":       str (ISO8601),
    "expires_at":      str (ISO8601),
    "nonce":           str (32 bytes hex)
  },
  "ephemeral_public":  str (base64 — server's ephemeral X25519 pub),
  "ciphertext":        str (base64 — AES-256-GCM output: nonce_gcm || tag || ct),
  "signature":         str (base64 — Ed25519 over canonical_bytes)
}
"""
import base64
import json
from app.core.utils.logger import get_logger
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from app.core.config import EXECUTOR_SIGNING_KEY

logger = get_logger(__name__)

# Validity duration of each job
_JOB_TTL_SECONDS = int(os.getenv("EXECUTOR_JOB_TTL_SECONDS", "300"))  # 5 min default

# HKDF info — identifies the key derivation context
_HKDF_INFO = b"atlas-executor-job-v1"


# ── Server Ed25519 signing key ────────────────────────────────────────────────

# Already reconstructed keys, indexed by the raw value of the environment variable.
_chaves_assinatura: dict[str, Ed25519PrivateKey | None] = {}


def _load_signing_key() -> Ed25519PrivateKey | None:
    """Load the Ed25519 private key from EXECUTOR_SIGNING_KEY (base64).

    Memoized: without a cache, the base64 + Ed25519 key reconstruction ran for
    every job — inside the dispatch candidate loop, on the event loop. The cache
    is keyed by the variable's CONTENT (and not an argument-less `lru_cache`) so
    that changing the key, in tests or on a config reload, still takes effect.
    """
    if not EXECUTOR_SIGNING_KEY:
        return None
    if EXECUTOR_SIGNING_KEY in _chaves_assinatura:
        return _chaves_assinatura[EXECUTOR_SIGNING_KEY]
    try:
        raw = base64.b64decode(EXECUTOR_SIGNING_KEY)
        key = Ed25519PrivateKey.from_private_bytes(raw)
    except Exception as exc:
        logger.error("Falha ao carregar EXECUTOR_SIGNING_KEY: %s", exc)
        key = None
    _chaves_assinatura[EXECUTOR_SIGNING_KEY] = key
    return key


def get_server_signing_public_key_b64() -> str | None:
    """
    Return the server's Ed25519 public key in base64.
    Distributed to executors at registration time for signature verification.
    """
    key = _load_signing_key()
    if key is None:
        return None
    pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(pub).decode()


# ── X25519 key serialization helpers ─────────────────────────────────────────

def x25519_pub_from_pem(pem: str) -> X25519PublicKey:
    """Load an X25519 public key from PEM (SubjectPublicKeyInfo)."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    return load_pem_public_key(pem.encode())


# ── Cifra + assina ────────────────────────────────────────────────────────────

def build_job_message(
    executor_id: str,
    workspace_id: str,
    agent_x25519_pub_pem: str,
    job_type: str,
    payload: dict | bytes,
    job_id: str | None = None,
) -> dict:
    """
    Build, encrypt and sign a Job to send to the executor.

    Args:
        executor_id             — id_hash of the recipient executor
        workspace_id         — workspace_id for auditing on the executor
        agent_x25519_pub_pem — the executor's X25519 public key (PEM)
        job_type             — e.g. "run_workflow"
        payload              — sensitive data to be encrypted. Accepts the dict
                               or the JSON already serialized to bytes: on failover
                               the same message is rebuilt per candidate, and for
                               a large workflow each `json.dumps` costs a few
                               milliseconds of stalled event loop. Callers in a
                               loop serialize once and pass the bytes.
        job_id               — the job's UUID; generated automatically if None

    Returns the dict ready to send via WebSocket (json.dumps).
    Raises RuntimeError if EXECUTOR_SIGNING_KEY is not configured.
    """
    signing_key = _load_signing_key()
    if signing_key is None:
        raise RuntimeError(
            "EXECUTOR_SIGNING_KEY não configurada — não é possível assinar jobs. "
            "Gere uma chave Ed25519 e defina a variável de ambiente."
        )

    if job_id is None:
        job_id = str(uuid4())

    now = datetime.now(timezone.utc)
    nonce_hex = secrets.token_hex(32)  # 32 bytes = 256 bits

    # ── Envelope (unencrypted metadata, included in the signature) ────────────
    envelope = {
        "job_id":          job_id,
        "target_executor_id": executor_id,
        "workspace_id":    workspace_id,
        "job_type":        job_type,
        "issued_at":       now.isoformat(),
        "expires_at":      (now + timedelta(seconds=_JOB_TTL_SECONDS)).isoformat(),
        "nonce":           nonce_hex,
    }

    # ── Cifra o payload com X25519 + AES-256-GCM ──────────────────────────────
    agent_pub = x25519_pub_from_pem(agent_x25519_pub_pem)

    # Ephemeral pair — discarded after this function returns (forward secrecy)
    ephemeral_priv = X25519PrivateKey.generate()
    ephemeral_pub  = ephemeral_priv.public_key()
    ephemeral_pub_raw = ephemeral_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)

    # ECDH
    shared_secret = ephemeral_priv.exchange(agent_pub)

    # AES key derivation via HKDF — the nonce serves as the salt
    aes_key = HKDF(
        algorithm=SHA256(),
        length=32,
        salt=bytes.fromhex(nonce_hex),
        info=_HKDF_INFO,
    ).derive(shared_secret)

    # AES-256-GCM: nonce de 12 bytes gerado aleatoriamente
    gcm_nonce = secrets.token_bytes(12)
    aesgcm    = AESGCM(aes_key)
    plaintext = (
        payload if isinstance(payload, bytes)
        else json.dumps(payload, ensure_ascii=False).encode()
    )
    ct        = aesgcm.encrypt(gcm_nonce, plaintext, None)  # inclui tag GCM

    # Empacota: gcm_nonce (12B) || ciphertext+tag
    ciphertext_bytes = gcm_nonce + ct

    ephemeral_pub_b64 = base64.b64encode(ephemeral_pub_raw).decode()
    ciphertext_b64    = base64.b64encode(ciphertext_bytes).decode()

    # ── Assinatura Ed25519 ────────────────────────────────────────────────────
    # canonical = envelope_json (sorted keys) + "|" + ephemeral_pub_b64 + "|" + ciphertext_b64
    canonical = (
        json.dumps(envelope, sort_keys=True, ensure_ascii=False)
        + "|" + ephemeral_pub_b64
        + "|" + ciphertext_b64
    ).encode()
    signature_b64 = base64.b64encode(signing_key.sign(canonical)).decode()

    # Clear sensitive material from memory (best-effort in Python)
    del shared_secret, aes_key, plaintext

    return {
        "envelope":        envelope,
        "ephemeral_public": ephemeral_pub_b64,
        "ciphertext":       ciphertext_b64,
        "signature":        signature_b64,
    }
