# executor/crypto.py
"""
Operações criptográficas do executor:
  - Carga da chave privada X25519 gerada no enrollment
  - Descriptografia de jobs (X25519 ECDH + HKDF + AES-256-GCM)
  - Verificação de assinatura Ed25519 do servidor

A GERAÇÃO da chave X25519 NÃO mora aqui: ela acontece uma única vez em
`executor/enrollment.py::enroll`, junto com o envio da pública ao servidor.
Ver `PrivateKeyMissingError` para o porquê.
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


# ── Carga da chave X25519 ─────────────────────────────────────────────────────

class PrivateKeyMissingError(RuntimeError):
    """
    Chave privada X25519 ausente ou ilegível.

    Levantada em vez de gerar uma chave nova. Gerar era o comportamento antigo e
    era SEMPRE errado depois do enrollment: a pública registrada no servidor
    passava a não casar com a privada local, o executor subia e aparecia
    "online", e 100% dos jobs morriam em `decrypt_job_payload` com uma mensagem
    que sugeria "ciphertext corrompido" — mandando o operador investigar rede /
    servidor quando o problema era a chave local. Falhar alto aqui troca um bug
    silencioso e enganoso por uma instrução clara: refazer o enrollment.
    """


def load_private_key(key_b64: str | None, key_path: str) -> X25519PrivateKey:
    """
    Carrega a chave privada X25519 do executor. NUNCA gera uma chave nova.

    Ordem:
      1. EXECUTOR_PRIVATE_KEY (base64 dos 32 bytes raw), se fornecida
      2. Arquivo PEM (PKCS8) em `key_path`, gravado pelo enroll

    Levanta PrivateKeyMissingError se nenhuma das duas existir ou se o material
    for inválido.
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


# ── Verificação de assinatura Ed25519 ────────────────────────────────────────

def verify_signature(message: dict, server_pub_b64: str) -> bool:
    """
    Verifica a assinatura Ed25519 do envelope do job.
    Retorna True se válida. Não lança exceção.

    Canonical bytes = json(envelope, sort_keys) + "|" + ephemeral_public + "|" + ciphertext
    """
    try:
        pub_raw = base64.b64decode(server_pub_b64)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_raw)

        # Junta os pedacos JA CODIFICADOS em vez de concatenar strings e codificar
        # o resultado: a versao anterior criava uma str do tamanho total (o
        # ciphertext em base64 de um workflow grande tem alguns MB) e logo em
        # seguida um bytes do mesmo tamanho. Os bytes finais sao identicos —
        # UTF-8 de uma concatenacao e a concatenacao dos UTF-8, e o separador
        # '|' e ASCII —, entao a assinatura do servidor continua batendo.
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


# ── Descriptografia do payload ────────────────────────────────────────────────

def decrypt_job_payload(message: dict, agent_priv: X25519PrivateKey) -> dict:
    """
    Descriptografa o payload cifrado de um job.

    Fluxo:
      1. Extrai a chave pública efêmera do servidor (X25519)
      2. ECDH: shared_secret = X25519(agent_priv, ephemeral_pub)
      3. HKDF-SHA256(shared_secret, salt=nonce_hex, info=_HKDF_INFO) → aes_key
      4. AES-256-GCM decrypt (gcm_nonce nos primeiros 12 bytes do ciphertext)
      5. json.loads → dict em memória

    Lança ValueError se descriptografia falhar (ciphertext corrompido / chave errada).
    """
    try:
        envelope = message["envelope"]
        nonce_hex = envelope["nonce"]

        # Chave pública efêmera do servidor
        ephemeral_pub_raw = base64.b64decode(message["ephemeral_public"])
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey as _X
        ephemeral_pub = _X.from_public_bytes(ephemeral_pub_raw)

        # ECDH
        shared_secret = agent_priv.exchange(ephemeral_pub)

        # Derivação de chave AES
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
        # Best-effort: apaga variáveis sensíveis da memória
        try:
            del shared_secret, aes_key, plaintext  # type: ignore[name-defined]
        except Exception as exc:
            logger.debug("Falha ao limpar variáveis sensíveis da memória: %s", exc)
