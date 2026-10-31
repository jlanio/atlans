# executor/renewal.py
"""
Automatic renewal of the executor's mTLS cert.

Periodic loop that checks the current cert's expiry and, if less than
RENEW_BEFORE_DAYS remain, generates a new keypair, sends a CSR authenticated
by the current cert (mTLS) and swaps the files atomically — validation and
writing are the same as enroll's (executor/enrollment.py::_persist_bundle).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from executor._ambiente import ler_int
from executor.enrollment import (
    CERT_FILE,
    RENEWAL_PENDING_FILE,
    _build_csr,
    _persist_bundle,
    _ws_to_http,
    drop_pending_renewal,
    load_pending_renewal,
    save_pending_renewal,
)

logger = logging.getLogger(__name__)


# ── Config ─────────────────────────────────────────────────────────────────────
# Tolerant parsing (executor/_ambiente.py): a `sete` in .env becomes the default
# with a warning, instead of a ValueError on import. Minimum 1 day because, with
# zero, renewal would only be attempted with the cert already expired — and
# /renew-cert authenticates precisely with that cert.

RENEW_BEFORE_DAYS = ler_int("EXECUTOR_CERT_RENEW_BEFORE_DAYS", 7, minimo=1)
RENEW_CHECK_INTERVAL_SECONDS = ler_int("EXECUTOR_CERT_RENEW_CHECK_SECONDS", 3600, minimo=1)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _cert_expires_at(cert_path: Path) -> datetime | None:
    """Reads cert.pem and returns not_valid_after_utc. None if missing/failed."""
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        return cert.not_valid_after_utc
    except Exception as exc:
        logger.error("Erro ao ler cert.pem: %s", exc)
        return None


def _cert_common_name(cert_path: Path) -> str | None:
    """Reads the current cert's CN (used to preserve identity on renewal)."""
    try:
        from cryptography.x509.oid import NameOID
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return attrs[0].value if attrs else None
    except Exception as exc:
        logger.error("Erro ao ler CN do cert: %s", exc)
        return None


def _days_until_expiry(cert_path: Path) -> float | None:
    expires_at = _cert_expires_at(cert_path)
    if expires_at is None:
        return None
    return (expires_at - datetime.now(timezone.utc)).total_seconds() / 86400.0


# ── Interrupted renewal ────────────────────────────────────────────────────────
# The server revokes the current serial and commits the new one BEFORE it
# answers. A lost answer (read timeout, proxy reset) left this executor with a
# serial the server had already revoked: every later renewal was refused, and
# the next reconnect ended the process until a new OTP. The key and CSR of a
# renewal in progress are kept on disk until its bundle is persisted; resending
# the SAME CSR within the server's replay window gives back the same bundle.

PENDING_FILE = RENEWAL_PENDING_FILE
# Shorter than the server's replay window (app/api/routers/executores_router.py,
# _JANELA_DE_REPETICAO_S = 30 min), so a resumed request always finds it.
_PENDING_MAX_AGE_S = 25 * 60


def _load_pending(cert_dir: Path) -> "tuple[Ed25519PrivateKey, str] | None":
    import time

    try:
        dados = load_pending_renewal(cert_dir)
    except Exception as exc:
        logger.warning("Renovacao pendente ilegivel — descartada: %s", exc)
        _drop_pending(cert_dir)
        return None
    if dados is None:
        return None
    if time.time() - dados["criado_em"] > _PENDING_MAX_AGE_S:
        _drop_pending(cert_dir)
        return None
    return dados["key"], dados["csr_pem"]


def _save_pending(cert_dir: Path, key: Ed25519PrivateKey, csr_pem: str) -> None:
    import time

    save_pending_renewal(cert_dir, key, csr_pem, time.time())


def _drop_pending(cert_dir: Path) -> None:
    try:
        drop_pending_renewal(cert_dir)
    except OSError as exc:
        logger.warning("Nao foi possivel apagar a renovacao pendente: %s", exc)


def has_pending_renewal(cert_dir: str | Path) -> bool:
    """Whether a renewal was interrupted before its bundle was persisted."""
    return _load_pending(Path(cert_dir)) is not None


# ── API publica ────────────────────────────────────────────────────────────────


async def maybe_renew(server_url: str, cert_dir: str | Path) -> bool:
    """
    Checks the current cert and renews it if less than RENEW_BEFORE_DAYS remain.
    Returns True if it renewed, False otherwise.
    """
    cert_dir = Path(cert_dir)
    days_left = _days_until_expiry(cert_dir / CERT_FILE)
    if days_left is None:
        logger.error("Sem cert atual valido — renovacao impossivel. Rode `enroll` novamente.")
        return False

    pendente = _load_pending(cert_dir)
    if pendente is not None:
        # Resumes an interrupted renewal with the SAME key and CSR, whatever the
        # remaining validity: the server may already have revoked this serial.
        new_ed, csr_pem = pendente
        logger.warning("Retomando renovacao interrompida (a resposta anterior nao chegou).")
    else:
        if days_left > RENEW_BEFORE_DAYS:
            logger.debug("Cert ainda valido por %.1f dias — sem renewal necessario.", days_left)
            return False

        logger.info("Cert vence em %.1f dias — iniciando renewal...", days_left)

        # Preserves the current cert's CN in the new CSR — step-ca requires it to
        # match the sub of the OTT that the backend generates from the executor_id.
        cn = _cert_common_name(cert_dir / CERT_FILE)
        if not cn:
            logger.error("Nao foi possivel extrair CN do cert atual — renewal abortado.")
            return False

        # Gera nova chave + CSR.
        new_ed = Ed25519PrivateKey.generate()
        csr_pem = _build_csr(new_ed, cn=cn).decode()
        try:
            _save_pending(cert_dir, new_ed, csr_pem)
        except OSError as exc:
            # Without the record the renewal still works; it only loses the
            # recovery from a lost answer.
            logger.warning("Nao foi possivel registrar a renovacao em andamento: %s", exc)

    http_base = _ws_to_http(server_url).rstrip("/")
    url = f"{http_base}/executores/renew-cert"

    from executor.utils import build_mtls_ssl_context
    ssl_ctx = build_mtls_ssl_context()

    try:
        from flow.utils.http_retry import async_request_with_retry
        # Cert renewal is critical (repeated failure = executor expires and drops).
        # Retrying transient errors (502/503/504/connect/read) recovers from
        # blips without waiting for the next renewal_loop cycle. Gateway 5xx =
        # request not processed by the backend → safe to resend.
        resp = await async_request_with_retry(
            "POST", url,
            client_kwargs={"verify": ssl_ctx, "timeout": 30.0},
            json={"csr_pem": csr_pem},
            label="cert renewal",
        )
    except Exception as exc:
        logger.error("Falha de rede no renewal: %s", exc)
        return False

    if resp.status_code not in (200, 201):
        logger.error("Servidor recusou renewal (status %s): %s", resp.status_code, resp.text[:200])
        if resp.status_code in (400, 409, 422):
            # A definitive refusal of THIS request (invalid CSR, executor changed
            # during the signature): retrying the same CSR cannot succeed.
            _drop_pending(cert_dir)
        elif resp.status_code in (401, 403):
            logger.error(
                "O servidor nao aceita mais o certificado atual. Se a renovacao "
                "anterior nao for retomada nos proximos minutos, refaca o enrollment."
            )
        return False

    try:
        bundle = resp.json()
    except Exception as exc:
        logger.error("Resposta do renewal nao e JSON valido: %s", exc)
        return False

    # Validates EVERYTHING before writing and swaps via .new + os.replace — the
    # same path as enroll (enrollment._persist_bundle). A partial bundle that
    # overwrites the good credentials leaves the executor offline with no
    # chance of self-correction.
    problema = _persist_bundle(cert_dir, bundle, new_ed)
    if not problema:
        _drop_pending(cert_dir)
    if problema:
        logger.error(
            "Renewal abortado — bundle invalido (%s). Nenhum arquivo foi alterado; "
            "o cert atual continua em uso e o proximo ciclo tentara de novo.",
            problema,
        )
        return False

    # Pins the server's signing key if there is no pin yet. Renewal is
    # authenticated by mTLS, so the bundle is a trusted source — and for an
    # executor enrolled BEFORE pinning existed, this is the path that closes the
    # TOFU window without requiring a re-enroll.
    #
    # A MISMATCH does not interrupt the renewal (the new cert is already on disk
    # and is valid) nor kill the running process, which carries on with the key
    # it loaded at boot. But `pin_key` writes a conflict marker, and the NEXT
    # boot stops with a clear message instead of starting with the stale pin and
    # rejecting every job. `pin_key` refuses the automatic swap on purpose.
    _pin_key = bundle.get("server_signing_public_key")
    if _pin_key:
        from executor.server_key import ServerKeyError, ServerKeyPersistError, pin_key
        try:
            pin_key(cert_dir, _pin_key, source="bundle do renewal")
        except ServerKeyPersistError as exc:
            logger.warning("Pin da chave de assinatura nao pode ser gravado: %s", exc)
        except ServerKeyError as exc:
            logger.error(
                "Chave de assinatura do servidor DIVERGENTE no renewal — o proximo "
                "boot deste executor vai abortar ate o operador agir: %s", exc,
            )

    # .get: the metadata is only for logging — not worth raising KeyError after
    # the swap has already succeeded.
    logger.info("Renewal concluido — serial novo %s expira %s",
                bundle.get("serial", "?"), bundle.get("expires_at", "?"))
    return True


async def renewal_loop(server_url: str, cert_dir: str | Path) -> None:
    """
    Infinite loop called by the executor main: checks renewal every
    RENEW_CHECK_INTERVAL_SECONDS (default 1h). Resilient to errors — it just
    logs and tries again on the next tick.
    """
    while True:
        try:
            await maybe_renew(server_url, cert_dir)
        except Exception as exc:
            logger.exception("Erro inesperado no renewal_loop: %s", exc)
        await asyncio.sleep(RENEW_CHECK_INTERVAL_SECONDS)
