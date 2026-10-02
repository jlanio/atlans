# tests/unit/test_agent_enrollment_service.py
"""
Testes unitarios do servico de enrollment via Bootstrap OTP.

Cobertura:
  - create_enrollment_otp: gera OTP plaintext + persiste HMAC.
  - consume_otp: atomico, lanca em invalidos/expirados/duplicados.
  - parse_and_validate_csr: aceita Ed25519, rejeita RSA/sem CN/CN errado.
  - revoke_cert / is_cert_revoked: blacklist Redis fail-closed.

step-ca client (sign_csr_via_stepca) nao e testado aqui — requer
container step-ca rodando. Testes de integracao cobrem isso.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key as gen_rsa
from cryptography.x509.oid import NameOID


# ── Helpers ──────────────────────────────────────────────────────────────────


def _csr_pem(cn: str = "executor-abc", use_ed25519: bool = True) -> str:
    """Gera um CSR para testes. Default: Ed25519, CN=executor-abc."""
    if use_ed25519:
        priv = Ed25519PrivateKey.generate()
        builder = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
        )
        csr = builder.sign(priv, algorithm=None)
    else:
        priv = gen_rsa(public_exponent=65537, key_size=2048)
        builder = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
        )
        csr = builder.sign(priv, hashes.SHA256())
    return csr.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


# ── TestCreateEnrollmentOTP ──────────────────────────────────────────────────


class TestCreateEnrollmentOTP:

    @pytest.mark.asyncio
    async def test_gera_otp_urlsafe_de_alta_entropia(self, mock_db):
        from app.services.executor_enrollment_service import create_enrollment_otp

        with patch("app.services.executor_enrollment_service.OTP_PEPPER", "pepper-de-teste-256-bits-base64xxxx"):
            otp, expires_at = await create_enrollment_otp(
                mock_db, executor_id="executor-123", created_by="admin-1",
            )

        # secrets.token_urlsafe(32) -> ~43 chars
        assert isinstance(otp, str)
        assert len(otp) >= 40
        assert expires_at > datetime.now(timezone.utc)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_sem_pepper_lanca_runtime_error(self, mock_db):
        from app.services.executor_enrollment_service import create_enrollment_otp

        with patch("app.services.executor_enrollment_service.OTP_PEPPER", ""):
            with pytest.raises(RuntimeError, match="OTP_PEPPER"):
                await create_enrollment_otp(mock_db, executor_id="x", created_by="y")


# ── TestConsumeOTP ───────────────────────────────────────────────────────────


class TestConsumeOTP:

    @pytest.mark.asyncio
    async def test_invalido_ou_expirado_lanca_value_error(self, mock_db):
        from app.services.executor_enrollment_service import consume_otp

        result = MagicMock()
        result.first.return_value = None  # nenhuma linha retornada -> invalido
        mock_db.execute.return_value = result

        with patch("app.services.executor_enrollment_service.OTP_PEPPER", "p" * 32):
            with pytest.raises(ValueError, match="invalido|expirado|utilizado"):
                await consume_otp(mock_db, "otp-fake-xyz", from_ip="127.0.0.1")

    @pytest.mark.asyncio
    async def test_sucesso_retorna_agent_id(self, mock_db):
        from app.services.executor_enrollment_service import consume_otp

        result = MagicMock()
        result.first.return_value = ("executor-xyz",)
        mock_db.execute.return_value = result

        with patch("app.services.executor_enrollment_service.OTP_PEPPER", "p" * 32):
            executor_id = await consume_otp(mock_db, "ok-otp", from_ip="10.0.0.1")

        assert executor_id == "executor-xyz"
        mock_db.commit.assert_awaited()


# ── TestParseAndValidateCSR ──────────────────────────────────────────────────


class TestParseAndValidateCSR:

    def test_aceita_csr_ed25519_com_cn_valido(self):
        from app.services.executor_enrollment_service import parse_and_validate_csr

        csr_pem = _csr_pem(cn="executor-abc")
        result = parse_and_validate_csr(csr_pem)
        assert isinstance(result, x509.CertificateSigningRequest)

    def test_rejeita_csr_rsa(self):
        from app.services.executor_enrollment_service import parse_and_validate_csr

        csr_pem = _csr_pem(cn="executor-abc", use_ed25519=False)
        with pytest.raises(ValueError, match="Ed25519"):
            parse_and_validate_csr(csr_pem)

    def test_rejeita_csr_com_cn_invalido(self):
        from app.services.executor_enrollment_service import parse_and_validate_csr

        csr_pem = _csr_pem(cn="random-cn-without-prefix")
        with pytest.raises(ValueError, match="CommonName"):
            parse_and_validate_csr(csr_pem)

    def test_rejeita_csr_mal_formado(self):
        from app.services.executor_enrollment_service import parse_and_validate_csr

        with pytest.raises(ValueError, match="CSR"):
            parse_and_validate_csr("isso nao eh um PEM valido")


# ── TestRevokeCert ───────────────────────────────────────────────────────────


class TestRevokeCert:

    @pytest.mark.asyncio
    async def test_marca_serial_no_redis(self):
        from app.services.executor_enrollment_service import revoke_cert

        fake_redis = AsyncMock()
        fake_redis.setex = AsyncMock()

        with patch("app.core.redis.get_redis_pool", return_value=fake_redis):
            await revoke_cert("serial-abc")

        fake_redis.setex.assert_awaited_once()
        call_args = fake_redis.setex.await_args
        # Key deve conter o serial
        assert "serial-abc" in str(call_args)

    @pytest.mark.asyncio
    async def test_is_cert_revoked_true_quando_marcado(self):
        from app.services.executor_enrollment_service import is_cert_revoked

        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value=b"1")

        with patch("app.core.redis.get_redis_pool", return_value=fake_redis):
            revoked = await is_cert_revoked("serial-abc")

        assert revoked is True

    @pytest.mark.asyncio
    async def test_is_cert_revoked_false_quando_ausente(self):
        from app.services.executor_enrollment_service import is_cert_revoked

        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value=None)

        with patch("app.core.redis.get_redis_pool", return_value=fake_redis):
            revoked = await is_cert_revoked("serial-novo")

        assert revoked is False

    @pytest.mark.asyncio
    async def test_is_cert_revoked_fail_closed_em_redis_down(self):
        """Fail-closed: Redis indisponivel = trata cert como revogado."""
        from app.services.executor_enrollment_service import is_cert_revoked

        broken = AsyncMock()
        broken.get = AsyncMock(side_effect=ConnectionError("redis down"))

        with patch("app.core.redis.get_redis_pool", return_value=broken):
            revoked = await is_cert_revoked("any-serial")

        assert revoked is True
