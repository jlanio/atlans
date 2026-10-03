# app/services/executor_enrollment_service.py
"""
Executor enrollment service via Bootstrap OTP + mTLS.

Responsibilities:
  - Generation and atomic consumption of single-use OTPs (HMAC with pepper).
  - Validation of the Ed25519 CSR sent by the executor.
  - CSR signing via the internal step-ca (HTTP API JWK provisioner).
  - Cert revocation via Redis blacklist (fail-closed) + step-ca CRL.

The Redis revocation serves as a fast blacklist; step-ca CRL/OCSP is a
defense-in-depth layer for when we integrate with Traefik.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import jwt as _jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    EXECUTOR_CERT_TTL_DAYS,
    EXECUTOR_OTP_TTL_HOURS,
    OTP_PEPPER,
    STEPCA_CA_CONFIG_PATH,
    STEPCA_PROVISIONER_NAME,
    STEPCA_PROVISIONER_PASSWORD,
    STEPCA_ROOT_CERT_PATH,
    STEPCA_URL,
)
from app.core.utils.datetime_utils import utc_now_naive
from app.core.utils.logger import get_logger
from app.models.executor import Executor
from app.models.executor_enrollment_otp import ExecutorEnrollmentOTP

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _hash_otp(otp_plaintext: str) -> str:
    """HMAC-SHA256(otp, OTP_PEPPER) -> hex (64 chars). Pepper ausente = erro fail-closed."""
    if not OTP_PEPPER:
        raise RuntimeError("OTP_PEPPER nao configurado — fluxo de enrollment desabilitado.")
    return hmac.new(OTP_PEPPER.encode(), otp_plaintext.encode(), hashlib.sha256).hexdigest()


def _cert_revoked_key(serial: str) -> str:
    return f"agent_cert_revoked:{serial}"


_REVOCATION_TTL_FLOOR_SECONDS = 7 * 24 * 60 * 60  # 7 dias — piso minimo, mesmo
# if the cert is already close to expiring. Ideally, revoke_cert receives the
# cert's expiration date and uses max(remaining, floor). Without that, a cert valid
# for up to 90 days (EXECUTOR_CERT_TTL_DAYS) could keep being accepted by Traefik
# after Redis released the key at 7 days.


# ── OTP lifecycle ────────────────────────────────────────────────────────────


async def create_enrollment_otp(
    db: AsyncSession,
    executor_id: str,
    created_by: str,
) -> tuple[str, datetime]:
    """
    Generates a single-use OTP, persists the HMAC and returns the plaintext.

    The plaintext appears only once (in the return value) — the admin hands it
    to the operator over a secure channel. From then on only the HMAC stays in the database.
    """
    otp_plaintext = secrets.token_urlsafe(32)  # ~43 chars, 256 bits of entropy
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EXECUTOR_OTP_TTL_HOURS)

    # Invalidates this executor's earlier OTPs not yet consumed — ensures that
    # at most one OTP is valid at a time (avoids piling up live credentials).
    await db.execute(
        update(ExecutorEnrollmentOTP)
        .where(
            ExecutorEnrollmentOTP.executor_id == executor_id,
            ExecutorEnrollmentOTP.consumed_at.is_(None),
        )
        .values(consumed_at=utc_now_naive())
    )

    record = ExecutorEnrollmentOTP(
        executor_id=executor_id,
        otp_hash=_hash_otp(otp_plaintext),
        expires_at=expires_at.replace(tzinfo=None),  # table uses naive datetime
        created_by=created_by,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("OTP de enrollment criado para executor '%s' (expira em %s).", executor_id, expires_at.isoformat())
    return otp_plaintext, expires_at


async def consume_otp(db: AsyncSession, otp_plaintext: str, from_ip: str) -> str:
    """
    Consumes an OTP atomically and returns the linked executor_id.

    Race-safe: UPDATE...WHERE consumed_at IS NULL...RETURNING guarantees that
    only one concurrent transaction succeeds.

    Raises ValueError if the OTP is invalid, expired or already consumed — a
    generic message so as not to reveal which condition failed.
    """
    h = _hash_otp(otp_plaintext)
    now = utc_now_naive()

    stmt = (
        update(ExecutorEnrollmentOTP)
        .where(
            ExecutorEnrollmentOTP.otp_hash == h,
            ExecutorEnrollmentOTP.consumed_at.is_(None),
            ExecutorEnrollmentOTP.expires_at > now,
        )
        .values(consumed_at=now, consumed_from_ip=from_ip)
        .returning(ExecutorEnrollmentOTP.executor_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    await db.commit()

    if row is None:
        logger.warning("Tentativa de consumir OTP invalido/expirado/ja usado de %s.", from_ip)
        raise ValueError("OTP invalido, expirado ou ja utilizado.")

    return row[0]


# ── CSR validation ───────────────────────────────────────────────────────────


def parse_and_validate_csr(csr_pem: str, expected_cn_prefix: str = "executor-") -> x509.CertificateSigningRequest:
    """
    Loads the CSR and validates:
      - well-formed PEM
      - internal signature OK
      - CN starts with `executor-`
      - Ed25519 public key (rejects RSA/ECDSA to shrink the algorithm matrix)

    Raises ValueError with a generic message on any failure.
    """
    try:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
    except Exception as exc:
        raise ValueError(f"CSR mal formado: {exc}") from exc

    if not csr.is_signature_valid:
        raise ValueError("Assinatura do CSR invalida.")

    cn_attrs = csr.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if not cn_attrs:
        raise ValueError("CSR sem CommonName.")
    cn = cn_attrs[0].value
    if not isinstance(cn, str) or not cn.startswith(expected_cn_prefix):
        raise ValueError(f"CommonName do CSR fora do padrao esperado ({expected_cn_prefix}*).")

    pub = csr.public_key()
    if not isinstance(pub, Ed25519PublicKey):
        raise ValueError("Algoritmo da chave do CSR nao suportado — use Ed25519.")

    return csr


# ── step-ca client ───────────────────────────────────────────────────────────


_provisioner_jwk_cache: dict | None = None
_provisioner_pem_cache: bytes | None = None


def _b64u_decode(s: str) -> bytes:
    """Base64url decode com padding tolerante."""
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + ("=" * pad))


def _decrypt_jwe_pbes2(jwe_compact: str, password: str) -> bytes:
    """
    Decrypts a compact JWE in the PBES2-HS256+A128KW + A256GCM format (used
    by step-ca to encrypt the JWK provisioner's private key in ca.json).

    Manual implementation with `cryptography` because jwcrypto imposes an
    arbitrary MAX_P2C limit and step-ca uses a high iteration count (600k+).

    JWE compact structure: protected_b64.encrypted_key_b64.iv_b64.cipher_b64.tag_b64
    """
    parts = jwe_compact.split(".")
    if len(parts) != 5:
        raise ValueError(f"JWE compact deve ter 5 partes, tem {len(parts)}.")
    protected_b64, enc_key_b64, iv_b64, ciphertext_b64, tag_b64 = parts

    header = json.loads(_b64u_decode(protected_b64))
    alg = header.get("alg")
    enc = header.get("enc")
    if alg != "PBES2-HS256+A128KW" or enc != "A256GCM":
        raise ValueError(f"Algoritmo JWE nao suportado: alg={alg!r} enc={enc!r}")

    p2s = _b64u_decode(header["p2s"])
    p2c = int(header["p2c"])

    # Salt do PBES2: UTF8(alg) || 0x00 || p2s_bytes (RFC 7518 §4.8.1.1)
    salt = alg.encode("utf-8") + b"\x00" + p2s

    # PBKDF2 → 128-bit Key Encryption Key (A128KW)
    kek = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        iterations=p2c,
    ).derive(password.encode("utf-8"))

    # AES Key Wrap (RFC 3394) → 256-bit CEK (for A256GCM)
    cek = aes_key_unwrap(kek, _b64u_decode(enc_key_b64))

    # A256GCM decrypt. AAD = ASCII do protected header b64.
    aesgcm = AESGCM(cek)
    ciphertext_with_tag = _b64u_decode(ciphertext_b64) + _b64u_decode(tag_b64)
    plaintext = aesgcm.decrypt(_b64u_decode(iv_b64), ciphertext_with_tag, protected_b64.encode("ascii"))
    return plaintext


def _jwk_ec_to_pem(jwk: dict) -> bytes:
    """
    Converts an EC JWK (P-256 / ES256) with private component `d` to unencrypted
    PKCS8 PEM. Accepts only EC P-256 (kty=EC, crv=P-256).
    """
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError(f"JWK nao suportado: kty={jwk.get('kty')} crv={jwk.get('crv')}. Esperado EC P-256.")
    if "d" not in jwk:
        raise ValueError("JWK sem componente privada `d`.")

    x = int.from_bytes(_b64u_decode(jwk["x"]), "big")
    y = int.from_bytes(_b64u_decode(jwk["y"]), "big")
    d = int.from_bytes(_b64u_decode(jwk["d"]), "big")

    pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
    priv = ec.EllipticCurvePrivateNumbers(d, pub).private_key()
    return priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _load_provisioner_jwk() -> tuple[dict, bytes]:
    """
    Reads step-ca's ca.json, decrypts the provisioner's `encryptedKey` with the
    password and returns (private JWK as a dict, private key as PKCS8 PEM).
    Caches in memory — PBKDF2 with 600k iterations is expensive (~50-200ms).

    Raises RuntimeError if:
      - STEPCA_PROVISIONER_PASSWORD is empty.
      - ca.json is not found (volume step-ca-data:/etc/step-ca:ro not mounted).
      - No provisioner named STEPCA_PROVISIONER_NAME exists.
      - Decryption fails (wrong password or malformed JWE).
    """
    global _provisioner_jwk_cache, _provisioner_pem_cache
    if _provisioner_jwk_cache is not None and _provisioner_pem_cache is not None:
        return _provisioner_jwk_cache, _provisioner_pem_cache

    if not STEPCA_PROVISIONER_PASSWORD:
        raise RuntimeError("STEPCA_PROVISIONER_PASSWORD nao configurado.")

    try:
        with open(STEPCA_CA_CONFIG_PATH, "r") as f:
            ca_config = json.load(f)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ca.json da step-ca nao encontrado em {STEPCA_CA_CONFIG_PATH}. "
            "O volume step-ca-data:/etc/step-ca:ro precisa estar montado no api-prod."
        ) from exc
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Falha ao ler ca.json da step-ca: {exc}") from exc

    provisioners = ca_config.get("authority", {}).get("provisioners", [])
    provisioner = next(
        (p for p in provisioners if p.get("name") == STEPCA_PROVISIONER_NAME and p.get("type") == "JWK"),
        None,
    )
    if provisioner is None:
        raise RuntimeError(
            f"Provisioner JWK '{STEPCA_PROVISIONER_NAME}' nao encontrado no ca.json. "
            f"Provisioners disponiveis: {[p.get('name') for p in provisioners]}"
        )

    encrypted_key = provisioner.get("encryptedKey")
    if not encrypted_key:
        raise RuntimeError(f"Provisioner '{STEPCA_PROVISIONER_NAME}' nao tem encryptedKey.")

    try:
        plaintext = _decrypt_jwe_pbes2(encrypted_key, STEPCA_PROVISIONER_PASSWORD)
        private_jwk = json.loads(plaintext.decode("utf-8"))
        # Preserves the provisioner's kid (the PUBLIC key has a kid; the decrypted
        # private key does not, but we need it for the JWT header).
        if "kid" not in private_jwk and "kid" in provisioner.get("key", {}):
            private_jwk["kid"] = provisioner["key"]["kid"]
        pem = _jwk_ec_to_pem(private_jwk)
    except Exception as exc:
        raise RuntimeError(
            f"Falha ao decifrar chave do provisioner JWK: {exc}. "
            "Verifique se STEPCA_PROVISIONER_PASSWORD bate com a senha usada no init da step-ca."
        ) from exc

    _provisioner_jwk_cache = private_jwk
    _provisioner_pem_cache = pem
    logger.info(
        "Chave do provisioner JWK '%s' (kid=%s) decifrada e cacheada.",
        STEPCA_PROVISIONER_NAME, private_jwk.get("kid", "<sem-kid>"),
    )
    return private_jwk, pem


def _build_stepca_token(executor_id: str, ttl_days: int) -> str:
    """
    Generates an OTT (one-time token) signed with ES256 using the private key of
    step-ca's JWK provisioner. step-ca validates it with the public key embedded
    in the provisioner and authorizes the CSR signing.

    Claims required by step-ca:
      sub:  cert identity (primary CN/SAN)
      sans: list of additional SANs
      iss:  provisioner name
      aud:  /1.0/sign endpoint
      iat/nbf/exp: short validity (5 min)
      jti:  unique token ID (step-ca tracks it to prevent reuse)
    """
    private_jwk, priv_pem = _load_provisioner_jwk()

    now = datetime.now(timezone.utc)
    claims = {
        "sub":  f"executor-{executor_id}",
        "sans": [f"executor-{executor_id}"],
        "iss":  STEPCA_PROVISIONER_NAME,
        "aud":  f"{STEPCA_URL}/1.0/sign",
        "iat":  int(now.timestamp()),
        "nbf":  int(now.timestamp()),
        "exp":  int((now + timedelta(minutes=5)).timestamp()),
        "jti":  secrets.token_hex(16),
    }
    # Header `kid` permite a step-ca localizar a chave publica do provisioner.
    headers = {"kid": private_jwk.get("kid"), "alg": "ES256"}
    return _jwt.encode(claims, priv_pem, algorithm="ES256", headers=headers)


async def sign_csr_via_stepca(csr_pem: str, executor_id: str, ttl_days: int | None = None) -> dict:
    """
    Asks step-ca to sign the CSR.

    Returns a dict with:
      cert_pem, chain_pem, ca_pem, serial, fingerprint, issued_at, expires_at

    Raises RuntimeError if step-ca is unavailable or rejects it.
    """
    ttl = ttl_days or EXECUTOR_CERT_TTL_DAYS
    # _build_stepca_token does PBKDF2 (600k iter, ~50-200ms) + file reads
    # in _load_provisioner_jwk. The JWK is cached at module level (once per process),
    # but the ES256 signature and the cost of the 1st token must not hold the event
    # loop that serves the executors' WebSockets.
    token = await asyncio.to_thread(_build_stepca_token, executor_id, ttl)

    payload = {
        "csr":     csr_pem,
        "ott":     token,
        "notAfter": f"{ttl * 24}h",
    }

    # Do NOT use safe_httpx_request here: STEPCA_URL comes from an ENV var (admin,
    # not user-controlled), so there is no SSRF vector. safe_httpx_request would
    # pin the IP — unnecessary for a known, configured internal host.
    #
    # SEC: this is the channel that ISSUES the mTLS certs of every executor — it is
    # the root of trust of the whole system. With verify=False, anyone on the
    # internal network could impersonate step-ca and hand back their own certs.
    # We validate against the CA's root cert (same volume already used by /ca-bundle).
    verify: str | bool = False
    if os.path.exists(STEPCA_ROOT_CERT_PATH):
        verify = STEPCA_ROOT_CERT_PATH
    else:
        logger.error(
            "Root cert da CA nao encontrado em %s — chamada a step-ca seguira SEM "
            "verificacao de TLS. Monte o volume step-ca-data para fechar esta brecha.",
            STEPCA_ROOT_CERT_PATH,
        )
    async with httpx.AsyncClient(verify=verify, timeout=15.0) as client:
        try:
            resp = await client.post(f"{STEPCA_URL}/1.0/sign", json=payload)
        except httpx.HTTPError as exc:
            logger.error("step-ca indisponivel: %s", exc)
            raise RuntimeError("CA interna indisponivel.") from exc

    if resp.status_code not in (200, 201):
        # step-ca devolve 201 Created em sucesso. 200 e fallback.
        logger.error("step-ca recusou CSR: status=%s body=%s", resp.status_code, resp.text[:500])
        raise RuntimeError(f"CA interna recusou CSR (status {resp.status_code}).")

    body = resp.json()
    cert_pem = body.get("crt")
    chain_pem = body.get("ca") or ""  # step-ca devolve o intermediate em 'ca'
    if not cert_pem:
        raise RuntimeError("Resposta da CA sem cert.")

    # Carrega o cert para extrair metadata (serial, fingerprint, expires_at).
    try:
        cert_obj = x509.load_pem_x509_certificate(cert_pem.encode())
    except Exception as exc:
        raise RuntimeError("CA retornou cert mal formado.") from exc

    fingerprint_bytes = cert_obj.fingerprint(hashes.SHA256())
    serial_hex = format(cert_obj.serial_number, "x")

    # The response's ca_pem must contain the ROOT cert (the trust anchor the executor
    # will use to validate the full chain). step-ca does not return the root on
    # /1.0/sign, so we read it directly from the step-ca-data volume mounted at
    # /etc/step-ca/certs.
    #
    # FAILING HERE IS MANDATORY. This function used to return ca_pem="" with a mere
    # WARNING; the executor wrote that empty value over the good ca.pem and went
    # permanently offline — without a trust anchor it cannot even call
    # /renew-cert to fix itself. Refusing the enroll/renewal leaves the executor
    # with the old bundle (which still works until it expires) and gives the operator
    # an actionable message; handing out a mangled bundle cannot be undone.
    try:
        # File read in a thread: it happens on EVERY enroll/renewal and would block
        # the event loop on disk. read_text opens/reads/closes; OSError propagates from the worker.
        root_pem = await asyncio.to_thread(Path(STEPCA_ROOT_CERT_PATH).read_text)
    except OSError as exc:
        logger.error(
            "Root cert nao legivel em %s (%s) — enroll/renewal abortado para nao "
            "entregar um ca.pem vazio ao executor. Monte o volume step-ca-data.",
            STEPCA_ROOT_CERT_PATH, exc,
        )
        raise RuntimeError(
            "Root cert da CA interna indisponivel no servidor — bundle nao emitido."
        ) from exc

    # Empty/truncated content has the same destructive effect as a missing file.
    try:
        x509.load_pem_x509_certificate(root_pem.encode())
    except Exception as exc:
        logger.error(
            "Root cert em %s nao e um PEM valido (%s) — enroll/renewal abortado.",
            STEPCA_ROOT_CERT_PATH, exc,
        )
        raise RuntimeError(
            "Root cert da CA interna invalido no servidor — bundle nao emitido."
        ) from exc

    return {
        "cert_pem":    cert_pem,
        "chain_pem":   chain_pem,
        "ca_pem":      root_pem,
        "serial":      serial_hex,
        "fingerprint": fingerprint_bytes.hex(),
        "issued_at":   cert_obj.not_valid_before_utc,
        "expires_at":  cert_obj.not_valid_after_utc,
    }


# ── Persisting the cert on the executor ─────────────────────────────────────────


async def attach_cert_to_agent(db: AsyncSession, executor_id: str, cert_data: dict) -> Executor:
    """
    Enrollment: updates the executor with the new cert's metadata and sets
    status='active'. Renewal does NOT go through here — see
    `renovar_cert_do_executor`.

    Clears the Redis revocation flag if there was an earlier one (reuse of an
    executor_id after revocation + re-enrollment).
    """
    result = await db.execute(select(Executor).where(Executor.id_hash == executor_id))
    ag = result.scalar_one_or_none()
    if ag is None:
        raise ValueError(f"Executor '{executor_id}' nao encontrado.")

    ag.cert_serial             = cert_data["serial"]
    ag.cert_fingerprint_sha256 = cert_data["fingerprint"]
    ag.cert_issued_at          = cert_data["issued_at"].replace(tzinfo=None)
    ag.cert_expires_at         = cert_data["expires_at"].replace(tzinfo=None)
    ag.status                  = "active"
    ag.last_seen_at            = utc_now_naive()

    await db.commit()
    await db.refresh(ag)

    # Clears the revocation flag if it existed.
    try:
        from app.core.redis import get_redis_pool
        rc = get_redis_pool()
        await rc.delete(_cert_revoked_key(cert_data["serial"]))
    except Exception as exc:
        logger.warning("Nao foi possivel limpar flag de revogacao Redis: %s", exc)

    return ag


async def renovar_cert_do_executor(
    db: AsyncSession, executor_id: str, presented_serial: str | None, cert_data: dict,
) -> bool:
    """
    Renewal: writes the new cert ONLY if the executor is still as it was when it
    presented the old one — active and with that serial. Condition and write are a
    single UPDATE.

    Renewal authenticates at the start of the request and waits for step-ca's
    signature before writing. A revocation in that window (the cert's zeroes
    `cert_serial`, the executor's changes `status`) used to be undone: the
    unconditional write put a new, valid serial in the database, and the revoked
    executor could connect again.

    Does not touch `status` (renewing does not reactivate) nor `last_seen_at` (the
    renewal happens with the executor connected, and the `last_seen_at` of one
    that is online is the session start — the "no ar desde" (online since) of the executors screen).

    Returns False when the executor changed midway: the caller discards the
    freshly issued cert.
    """
    if not presented_serial:
        return False
    resultado = await db.execute(
        update(Executor)
        .where(
            Executor.id_hash == executor_id,
            Executor.cert_serial == presented_serial,
            Executor.status == "active",
        )
        .values(
            cert_serial=cert_data["serial"],
            cert_fingerprint_sha256=cert_data["fingerprint"],
            cert_issued_at=cert_data["issued_at"].replace(tzinfo=None),
            cert_expires_at=cert_data["expires_at"].replace(tzinfo=None),
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return resultado.rowcount == 1


def validate_x25519_public_key(public_key_pem: str) -> None:
    """Ensures the PEM sent at enrollment really is an X25519 public key.

    Without this check, an RSA/Ed25519 PEM was persisted as if it were valid and
    only blew up at dispatch: `build_job_message` called `exchange()` and
    raised TypeError, which `_dispatch_job` does not catch (it only handles
    RuntimeError) — every dispatch to that executor became an HTTP 500.
    """
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    try:
        key = load_pem_public_key(public_key_pem.encode())
    except Exception as exc:
        raise ValueError(f"public_key_pem mal formada: {exc}") from exc
    if not isinstance(key, X25519PublicKey):
        raise ValueError("public_key_pem deve ser uma chave publica X25519.")


async def attach_public_key_to_agent(db: AsyncSession, executor_id: str, public_key_pem: str) -> None:
    """Persists the executor's X25519 public key (envelope encryption of jobs)."""
    validate_x25519_public_key(public_key_pem)
    result = await db.execute(select(Executor).where(Executor.id_hash == executor_id))
    ag = result.scalar_one_or_none()
    if ag is None:
        return
    ag.public_key = public_key_pem
    await db.commit()


# ── Revocation ────────────────────────────────────────────────────────────────


async def revoke_cert(serial: str, cert_expires_at: datetime | None = None) -> None:
    """
    Marks the serial as revoked in Redis. TTL = max(remaining_lifetime, 7d).

    It used to be fixed at 7 days, but certs are valid for up to 90 days. After
    Redis released the key, Traefik accepted the revoked cert for the rest of its
    validity (potentially ~83 days). Now the TTL follows the actual validity.

    cert_expires_at: the cert's expiration datetime (UTC). If omitted (legacy
    callers), uses the 7-day floor — the previous behavior, kept for
    compatibility during the migration.
    """
    from app.core.redis import get_redis_pool
    rc = get_redis_pool()

    ttl = _REVOCATION_TTL_FLOOR_SECONDS
    if cert_expires_at is not None:
        now = datetime.now(timezone.utc)
        # Accepts naive or aware datetime; normalizes to UTC.
        exp = cert_expires_at if cert_expires_at.tzinfo else cert_expires_at.replace(tzinfo=timezone.utc)
        remaining = int((exp - now).total_seconds())
        ttl = max(remaining, _REVOCATION_TTL_FLOOR_SECONDS)

    await rc.setex(_cert_revoked_key(serial), ttl, "1")
    logger.info(
        "Cert serial '%s' marcado como revogado (TTL=%ds).", serial, ttl,
    )


async def is_cert_revoked(serial: str) -> bool:
    """Fail-closed: any Redis failure treats the cert as revoked."""
    from app.core.redis import get_redis_pool
    try:
        rc = get_redis_pool()
        return (await rc.get(_cert_revoked_key(serial))) is not None
    except Exception as exc:
        logger.error("Redis indisponivel ao checar revogacao do cert '%s': %s — tratando como revogado.", serial, exc)
        return True
