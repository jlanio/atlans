# app/services/executor_enrollment_service.py
"""
Servico de enrollment de executores via Bootstrap OTP + mTLS.

Responsabilidades:
  - Geracao e consumo atomico de OTPs single-use (HMAC com pepper).
  - Validacao de CSR Ed25519 enviado pelo executor.
  - Assinatura de CSR via step-ca interna (HTTP API JWK provisioner).
  - Revogacao de cert via Redis blacklist (fail-closed) + CRL step-ca.

A revogacao Redis serve como blacklist rapida; CRL/OCSP step-ca e camada
de defesa em profundidade quando integrarmos com Traefik.
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
# se o cert ja estiver perto de expirar. Idealmente, revoke_cert recebe a data
# de expiracao do cert e usa max(remaining, floor). Sem isso, cert valido por
# ate 90 dias (EXECUTOR_CERT_TTL_DAYS) podia continuar aceito pelo Traefik apos o
# Redis liberar a chave em 7 dias.


# ── OTP lifecycle ────────────────────────────────────────────────────────────


async def create_enrollment_otp(
    db: AsyncSession,
    executor_id: str,
    created_by: str,
) -> tuple[str, datetime]:
    """
    Gera um OTP de uso unico, persiste o HMAC e retorna o plaintext.

    O plaintext aparece apenas uma vez (no retorno) — admin entrega ao
    operador via canal seguro. Subsequentemente so o HMAC fica no banco.
    """
    otp_plaintext = secrets.token_urlsafe(32)  # ~43 chars, 256 bits de entropia
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EXECUTOR_OTP_TTL_HOURS)

    # Invalida OTPs anteriores ainda não consumidos deste executor — garante que
    # no máximo um OTP fique válido por vez (evita acúmulo de credenciais vivas).
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
        expires_at=expires_at.replace(tzinfo=None),  # tabela usa naive datetime
        created_by=created_by,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("OTP de enrollment criado para executor '%s' (expira em %s).", executor_id, expires_at.isoformat())
    return otp_plaintext, expires_at


async def consume_otp(db: AsyncSession, otp_plaintext: str, from_ip: str) -> str:
    """
    Consome um OTP atomicamente e retorna o executor_id vinculado.

    Race-safe: UPDATE...WHERE consumed_at IS NULL...RETURNING garante que
    apenas uma transacao concorrente tera sucesso.

    Lanca ValueError se OTP invalido, expirado ou ja consumido — mensagem
    generica para nao revelar qual condicao falhou.
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


# ── Validacao de CSR ─────────────────────────────────────────────────────────


def parse_and_validate_csr(csr_pem: str, expected_cn_prefix: str = "executor-") -> x509.CertificateSigningRequest:
    """
    Carrega o CSR e valida:
      - PEM bem formado
      - Assinatura interna OK
      - CN comeca com `executor-`
      - Chave publica Ed25519 (rejeita RSA/ECDSA para reduzir matriz de algoritmos)

    Lanca ValueError com mensagem generica em caso de qualquer falha.
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
    Decifra um JWE compacto no formato PBES2-HS256+A128KW + A256GCM (usado
    pela step-ca para cifrar a chave privada do provisioner JWK no ca.json).

    Implementacao manual com `cryptography` porque jwcrypto impoe limite
    MAX_P2C arbitrario e step-ca usa iterations alto (600k+).

    Estrutura do JWE compact: protected_b64.encrypted_key_b64.iv_b64.cipher_b64.tag_b64
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

    # AES Key Wrap (RFC 3394) → CEK de 256 bits (para A256GCM)
    cek = aes_key_unwrap(kek, _b64u_decode(enc_key_b64))

    # A256GCM decrypt. AAD = ASCII do protected header b64.
    aesgcm = AESGCM(cek)
    ciphertext_with_tag = _b64u_decode(ciphertext_b64) + _b64u_decode(tag_b64)
    plaintext = aesgcm.decrypt(_b64u_decode(iv_b64), ciphertext_with_tag, protected_b64.encode("ascii"))
    return plaintext


def _jwk_ec_to_pem(jwk: dict) -> bytes:
    """
    Converte JWK EC (P-256 / ES256) com componente privada `d` para PEM PKCS8
    sem cifragem. Aceita apenas EC P-256 (kty=EC, crv=P-256).
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
    Le ca.json da step-ca, decifra `encryptedKey` do provisioner com a senha
    e retorna (JWK privada como dict, chave privada em PEM PKCS8).
    Cacheia em memoria — PBKDF2 com 600k iterations e caro (~50-200ms).

    Lanca RuntimeError se:
      - STEPCA_PROVISIONER_PASSWORD vazio.
      - ca.json nao encontrado (volume step-ca-data:/etc/step-ca:ro nao montado).
      - Provisioner com nome STEPCA_PROVISIONER_NAME nao existe.
      - Decifragem falha (senha errada ou JWE mal formado).
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
        # Preserva o kid do provisioner (a chave PUBLICA tem kid; a privada
        # decifrada nao tem, mas precisamos pro header do JWT).
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
    Gera OTT (one-time token) assinado com ES256 usando a chave privada do
    provisioner JWK da step-ca. Step-ca valida com a chave publica embutida
    no provisioner e autoriza a assinatura do CSR.

    Claims exigidos pela step-ca:
      sub:  identidade do cert (CN/SAN principal)
      sans: lista de SANs adicionais
      iss:  nome do provisioner
      aud:  endpoint /1.0/sign
      iat/nbf/exp: validade curta (5 min)
      jti:  ID unico do token (step-ca rastreia para impedir reuso)
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
    Pede a step-ca para assinar o CSR.

    Retorna dict com:
      cert_pem, chain_pem, ca_pem, serial, fingerprint, issued_at, expires_at

    Lanca RuntimeError se step-ca indisponivel ou rejeitar.
    """
    ttl = ttl_days or EXECUTOR_CERT_TTL_DAYS
    # _build_stepca_token faz PBKDF2 (600k iter, ~50-200ms) + leituras de arquivo
    # em _load_provisioner_jwk. O JWK e cacheado em modulo (1x por processo), mas
    # a assinatura ES256 e o custo do 1o token nao devem prender o event loop que
    # atende os WebSockets dos executores.
    token = await asyncio.to_thread(_build_stepca_token, executor_id, ttl)

    payload = {
        "csr":     csr_pem,
        "ott":     token,
        "notAfter": f"{ttl * 24}h",
    }

    # NAO usar safe_httpx_request aqui: STEPCA_URL vem de ENV var (admin,
    # nao user-controlled), entao nao ha vetor SSRF. safe_httpx_request faria
    # pin de IP — desnecessario para um host interno conhecido e configurado.
    #
    # SEG: este e o canal que EMITE os certs mTLS de todos os executores — e a
    # raiz de confianca do sistema inteiro. Com verify=False, quem estivesse na
    # rede interna podia se passar pela step-ca e devolver certs proprios.
    # Validamos contra o root cert da CA (mesmo volume ja usado por /ca-bundle).
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

    # ca_pem do response deve conter o ROOT cert (trust anchor que o executor vai
    # usar para validar a chain completa). step-ca nao devolve o root no /1.0/sign,
    # entao lemos diretamente do volume step-ca-data montado em /etc/step-ca/certs.
    #
    # FALHAR AQUI E OBRIGATORIO. Antes esta funcao devolvia ca_pem="" com um mero
    # WARNING; o executor gravava esse vazio por cima do ca.pem bom e ficava
    # permanentemente offline — sem trust anchor ele nao consegue nem chamar
    # /renew-cert para se autocorrigir. Recusar o enroll/renewal deixa o executor
    # com o bundle antigo (que ainda funciona ate expirar) e da ao operador uma
    # mensagem acionavel; entregar um bundle mutilado nao tem volta.
    try:
        # Leitura de arquivo em thread: acontece a CADA enroll/renewal e bloquearia
        # o event loop no disco. read_text abre/le/fecha; OSError propaga do worker.
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

    # Conteudo vazio/truncado tem o mesmo efeito destrutivo de arquivo ausente.
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


# ── Persistencia do cert no executor ────────────────────────────────────────────


async def attach_cert_to_agent(db: AsyncSession, executor_id: str, cert_data: dict) -> Executor:
    """
    Enrollment: atualiza o executor com os metadados do novo cert e marca
    status='active'. A renovacao NAO passa por aqui — ver
    `renovar_cert_do_executor`.

    Limpa o flag de revogacao Redis caso houvesse um anterior (reuso de
    executor_id apos revogacao + re-enrollment).
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

    # Limpa revocation flag se existia.
    try:
        from app.core.redis import get_redis_pool
        rc = get_redis_pool()
        await rc.delete(_cert_revoked_key(cert_data["serial"]))
    except Exception as exc:
        logger.warning("Nao foi possivel limpar flag de revogacao Redis: %s", exc)

    return ag


async def renovar_cert_do_executor(
    db: AsyncSession, executor_id: str, serial_apresentado: str | None, cert_data: dict,
) -> bool:
    """
    Renovacao: grava o cert novo SO se o executor continua como estava quando
    apresentou o antigo — ativo e com aquele serial. Condicao e escrita sao um
    UPDATE so.

    A renovacao autentica no inicio do request e espera a assinatura do step-ca
    antes de gravar. Uma revogacao nessa janela (a do cert zera `cert_serial`,
    a do executor muda `status`) era desfeita: a gravacao incondicional punha um
    serial novo e valido no banco, e o executor revogado voltava a conectar.

    Nao mexe em `status` (renovar nao reativa) nem em `last_seen_at` (a
    renovacao acontece com o executor conectado, e o `last_seen_at` de quem
    esta online e o inicio da sessao — o "no ar desde" da tela de executores).

    Devolve False quando o executor mudou no meio: quem chama descarta o cert
    recem-emitido.
    """
    if not serial_apresentado:
        return False
    resultado = await db.execute(
        update(Executor)
        .where(
            Executor.id_hash == executor_id,
            Executor.cert_serial == serial_apresentado,
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
    """Garante que o PEM enviado no enrollment e mesmo uma chave publica X25519.

    Sem esta checagem, um PEM RSA/Ed25519 era persistido como se fosse valido e
    so estourava no dispatch: `build_job_message` chamava `exchange()` e
    levantava TypeError, que o `_dispatch_job` nao captura (so trata
    RuntimeError) — todo despacho para aquele executor virava HTTP 500.
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
    """Persiste a chave publica X25519 do executor (envelope encryption de jobs)."""
    validate_x25519_public_key(public_key_pem)
    result = await db.execute(select(Executor).where(Executor.id_hash == executor_id))
    ag = result.scalar_one_or_none()
    if ag is None:
        return
    ag.public_key = public_key_pem
    await db.commit()


# ── Revogacao ────────────────────────────────────────────────────────────────


async def revoke_cert(serial: str, cert_expires_at: datetime | None = None) -> None:
    """
    Marca o serial como revogado no Redis. TTL = max(remaining_lifetime, 7d).

    Antes era fixo em 7 dias, mas certs tem ate 90 dias de validade. Apos o
    Redis liberar a chave, Traefik aceitava o cert revogado pelo restante da
    validade (potencialmente ~83 dias). Agora o TTL acompanha a validade real.

    cert_expires_at: datetime de expiracao do cert (UTC). Se omitido (callers
    legados), usa o piso de 7 dias — comportamento anterior, mantido por
    compatibilidade durante migracao.
    """
    from app.core.redis import get_redis_pool
    rc = get_redis_pool()

    ttl = _REVOCATION_TTL_FLOOR_SECONDS
    if cert_expires_at is not None:
        now = datetime.now(timezone.utc)
        # Aceita datetime naive ou aware; normaliza para UTC.
        exp = cert_expires_at if cert_expires_at.tzinfo else cert_expires_at.replace(tzinfo=timezone.utc)
        remaining = int((exp - now).total_seconds())
        ttl = max(remaining, _REVOCATION_TTL_FLOOR_SECONDS)

    await rc.setex(_cert_revoked_key(serial), ttl, "1")
    logger.info(
        "Cert serial '%s' marcado como revogado (TTL=%ds).", serial, ttl,
    )


async def is_cert_revoked(serial: str) -> bool:
    """Fail-closed: qualquer falha do Redis trata o cert como revogado."""
    from app.core.redis import get_redis_pool
    try:
        rc = get_redis_pool()
        return (await rc.get(_cert_revoked_key(serial))) is not None
    except Exception as exc:
        logger.error("Redis indisponivel ao checar revogacao do cert '%s': %s — tratando como revogado.", serial, exc)
        return True
