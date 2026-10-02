# executor/renewal.py
"""
Renovacao automatica do cert mTLS do executor.

Loop periodico que checa o vencimento do cert atual e, se faltar menos
que RENEW_BEFORE_DAYS, gera novo keypair, envia CSR autenticado pelo
cert atual (mTLS) e troca os arquivos atomicamente — validacao e escrita
sao as do enroll (executor/enrollment.py::_persistir_bundle).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from executor._ambiente import ler_int
from executor.enrollment import CERT_FILE, _build_csr, _persistir_bundle, _ws_to_http

logger = logging.getLogger(__name__)


# ── Config ─────────────────────────────────────────────────────────────────────
# Leitura tolerante (executor/_ambiente.py): um `sete` no .env vira o padrao com
# aviso, em vez de ValueError no import. Minimo 1 dia porque, com zero, o
# renewal so tentaria com o cert ja vencido — e o /renew-cert se autentica
# justamente por ele.

RENEW_BEFORE_DAYS = ler_int("EXECUTOR_CERT_RENEW_BEFORE_DAYS", 7, minimo=1)
RENEW_CHECK_INTERVAL_SECONDS = ler_int("EXECUTOR_CERT_RENEW_CHECK_SECONDS", 3600, minimo=1)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _cert_expires_at(cert_path: Path) -> datetime | None:
    """Le cert.pem e retorna not_valid_after_utc. None se nao existir/falhar."""
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        return cert.not_valid_after_utc
    except Exception as exc:
        logger.error("Erro ao ler cert.pem: %s", exc)
        return None


def _cert_common_name(cert_path: Path) -> str | None:
    """Le o CN do cert atual (usado para preservar identidade no renewal)."""
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


# ── API publica ────────────────────────────────────────────────────────────────


async def maybe_renew(server_url: str, cert_dir: str | Path) -> bool:
    """
    Checa o cert atual e renova se faltar menos que RENEW_BEFORE_DAYS.
    Retorna True se renovou, False caso contrario.
    """
    cert_dir = Path(cert_dir)
    days_left = _days_until_expiry(cert_dir / CERT_FILE)
    if days_left is None:
        logger.error("Sem cert atual valido — renovacao impossivel. Rode `enroll` novamente.")
        return False
    if days_left > RENEW_BEFORE_DAYS:
        logger.debug("Cert ainda valido por %.1f dias — sem renewal necessario.", days_left)
        return False

    logger.info("Cert vence em %.1f dias — iniciando renewal...", days_left)

    # Preserva o CN do cert atual no novo CSR — step-ca exige match com o
    # sub do OTT que o backend gera com base no executor_id.
    cn = _cert_common_name(cert_dir / CERT_FILE)
    if not cn:
        logger.error("Nao foi possivel extrair CN do cert atual — renewal abortado.")
        return False

    # Gera nova chave + CSR.
    new_ed = Ed25519PrivateKey.generate()
    csr_pem = _build_csr(new_ed, cn=cn).decode()

    http_base = _ws_to_http(server_url).rstrip("/")
    url = f"{http_base}/executores/renew-cert"

    from executor.utils import build_mtls_ssl_context
    ssl_ctx = build_mtls_ssl_context()

    try:
        from flow.utils.http_retry import async_request_with_retry
        # Renovacao de cert e critica (falha repetida = executor expira e cai).
        # Retry de transitorios (502/503/504/connect/read) recupera de blips sem
        # esperar o proximo ciclo do renewal_loop. 5xx de gateway = request nao
        # processado pelo backend → reenvio seguro.
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
        return False

    try:
        bundle = resp.json()
    except Exception as exc:
        logger.error("Resposta do renewal nao e JSON valido: %s", exc)
        return False

    # Valida TUDO antes de escrever e troca via .new + os.replace — o mesmo
    # caminho do enroll (enrollment._persistir_bundle). Um bundle parcial que
    # sobrescreve as credenciais boas deixa o executor offline sem chance de
    # autocorrecao.
    problema = _persistir_bundle(cert_dir, bundle, new_ed)
    if problema:
        logger.error(
            "Renewal abortado — bundle invalido (%s). Nenhum arquivo foi alterado; "
            "o cert atual continua em uso e o proximo ciclo tentara de novo.",
            problema,
        )
        return False

    # Fixa a chave de assinatura do servidor se ainda nao houver pin. O renewal e
    # autenticado por mTLS, entao o bundle e uma fonte confiavel — e para um
    # executor enrolado ANTES do pinning existir, este e o caminho que fecha a
    # janela de TOFU sem exigir re-enroll.
    #
    # DIVERGENCIA nao interrompe o renewal (o cert novo ja esta em disco e e
    # valido) nem derruba o processo em execucao, que segue com a chave que
    # carregou no boot. Mas `pin_key` grava um marcador de conflito, e o PROXIMO
    # boot para com mensagem clara em vez de subir com o pin obsoleto rejeitando
    # todo job. `pin_key` recusa a troca automatica de proposito.
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

    # .get: metadados so servem para log — nao vale estourar KeyError depois do
    # swap ja ter dado certo.
    logger.info("Renewal concluido — serial novo %s expira %s",
                bundle.get("serial", "?"), bundle.get("expires_at", "?"))
    return True


async def renewal_loop(server_url: str, cert_dir: str | Path) -> None:
    """
    Loop infinito chamado pelo executor main: checa renewal a cada
    RENEW_CHECK_INTERVAL_SECONDS (default 1h). Resiliente a erros — apenas
    logga e tenta de novo no proximo tick.
    """
    while True:
        try:
            await maybe_renew(server_url, cert_dir)
        except Exception as exc:
            logger.exception("Erro inesperado no renewal_loop: %s", exc)
        await asyncio.sleep(RENEW_CHECK_INTERVAL_SECONDS)
