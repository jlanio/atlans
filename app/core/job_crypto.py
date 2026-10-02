# app/core/job_crypto.py
"""
Criptografia de Jobs para Executores.

Esquema:
  - Cifra:   X25519 (ECDH efêmero) + HKDF-SHA256 + AES-256-GCM
  - Assina:  Ed25519 (chave estática do servidor)

Forward secrecy por job: cada job usa um par efêmero X25519 descartado após envio.
O executor só consegue descriptografar com sua chave privada X25519 —
comprometer a chave estática do executor não expõe jobs anteriores.

Formato da mensagem enviada ao executor:
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
  "ephemeral_public":  str (base64 — X25519 pub efêmero do servidor),
  "ciphertext":        str (base64 — AES-256-GCM output: nonce_gcm || tag || ct),
  "signature":         str (base64 — Ed25519 sobre canonical_bytes)
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

# Duração de validade de cada job
_JOB_TTL_SECONDS = int(os.getenv("EXECUTOR_JOB_TTL_SECONDS", "300"))  # 5 min padrão

# HKDF info — identifica o contexto da derivação de chave
_HKDF_INFO = b"atlas-executor-job-v1"


# ── Chave de assinatura Ed25519 do servidor ───────────────────────────────────

# Chaves ja reconstruidas, indexadas pelo valor bruto da variavel de ambiente.
_chaves_assinatura: dict[str, Ed25519PrivateKey | None] = {}


def _load_signing_key() -> Ed25519PrivateKey | None:
    """Carrega a chave privada Ed25519 a partir de EXECUTOR_SIGNING_KEY (base64).

    Memoizada: sem cache, o base64 + a reconstrucao da chave Ed25519 rodavam a
    cada job — dentro do laco de candidatos do dispatch, no event loop. O cache
    e por CONTEUDO da variavel (e nao um `lru_cache` sem argumentos) para que
    trocar a chave, nos testes ou num reload de config, continue valendo.
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
    Retorna a chave pública Ed25519 do servidor em base64.
    Distribuída aos executores no momento do registro para verificação de assinaturas.
    """
    key = _load_signing_key()
    if key is None:
        return None
    pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(pub).decode()


# ── Helpers de serialização de chave X25519 ──────────────────────────────────

def x25519_pub_from_pem(pem: str) -> X25519PublicKey:
    """Carrega chave pública X25519 de PEM (SubjectPublicKeyInfo)."""
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
    Monta, cifra e assina um Job para envio ao executor.

    Parâmetros:
        executor_id             — id_hash do executor destinatário
        workspace_id         — workspace_id para auditoria no executor
        agent_x25519_pub_pem — chave pública X25519 do executor (PEM)
        job_type             — ex: "run_workflow"
        payload              — dados sensíveis a serem cifrados. Aceita o dict
                               ou o JSON já serializado em bytes: no failover a
                               mesma mensagem é remontada por candidato, e para
                               um workflow grande cada `json.dumps` custa alguns
                               milissegundos de event loop parado. Quem chama em
                               laço serializa uma vez e passa os bytes.
        job_id               — UUID do job; gerado automaticamente se None

    Retorna o dict pronto para enviar via WebSocket (json.dumps).
    Lança RuntimeError se EXECUTOR_SIGNING_KEY não estiver configurada.
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

    # ── Envelope (metadados não-cifrados, incluídos na assinatura) ────────────
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

    # Par efêmero — descartado após esta função retornar (forward secrecy)
    ephemeral_priv = X25519PrivateKey.generate()
    ephemeral_pub  = ephemeral_priv.public_key()
    ephemeral_pub_raw = ephemeral_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)

    # ECDH
    shared_secret = ephemeral_priv.exchange(agent_pub)

    # Derivação de chave AES via HKDF — o nonce serve como salt
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

    # Limpa material sensível da memória (best-effort em Python)
    del shared_secret, aes_key, plaintext

    return {
        "envelope":        envelope,
        "ephemeral_public": ephemeral_pub_b64,
        "ciphertext":       ciphertext_b64,
        "signature":        signature_b64,
    }
