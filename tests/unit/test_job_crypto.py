# tests/unit/test_job_crypto.py
"""Testes unitários para app/core/job_crypto.py — criptografia de jobs para executores."""
import base64
import copy
import json
import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ed25519_key_b64() -> str:
    """Gera chave privada Ed25519 real em base64 (formato de EXECUTOR_SIGNING_KEY)."""
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    return base64.b64encode(raw).decode()


def _make_x25519_pub_pem() -> str:
    """Gera chave pública X25519 em PEM SubjectPublicKeyInfo."""
    priv = X25519PrivateKey.generate()
    return priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode()


def _verify_job_signature(message: dict, server_ed25519_pub_b64: str) -> bool:
    """A verificação que o executor faz (`executor.crypto.verify_signature`),
    refeita aqui para conferir a assinatura de `build_job_message`: o servidor
    só assina. O par real servidor↔executor é exercido em
    test_contrato_app_executor_cripto.py."""
    try:
        pub_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(server_ed25519_pub_b64))
        canonical = (
            json.dumps(message["envelope"], sort_keys=True, ensure_ascii=False)
            + "|" + message["ephemeral_public"]
            + "|" + message["ciphertext"]
        ).encode()
        pub_key.verify(base64.b64decode(message["signature"]), canonical)
        return True
    except Exception:
        return False


# ── Fixtures de escopo de módulo (geração de chave é barata mas desnecessariamente repetida) ──

@pytest.fixture(scope="module")
def ed25519_signing_key_b64() -> str:
    """Chave Ed25519 gerada uma vez por módulo."""
    return _make_ed25519_key_b64()


@pytest.fixture(scope="module")
def x25519_agent_pub_pem() -> str:
    """Chave pública X25519 do executor gerada uma vez por módulo."""
    return _make_x25519_pub_pem()


@pytest.fixture
def with_signing_key(ed25519_signing_key_b64, monkeypatch):
    """Patcha EXECUTOR_SIGNING_KEY no módulo job_crypto para uma chave válida."""
    monkeypatch.setattr("app.core.job_crypto.EXECUTOR_SIGNING_KEY", ed25519_signing_key_b64)
    monkeypatch.setattr("app.core.config.EXECUTOR_SIGNING_KEY", ed25519_signing_key_b64)


@pytest.fixture
def without_signing_key(monkeypatch):
    """Patcha EXECUTOR_SIGNING_KEY para None (chave ausente)."""
    monkeypatch.setattr("app.core.job_crypto.EXECUTOR_SIGNING_KEY", None)
    monkeypatch.setattr("app.core.config.EXECUTOR_SIGNING_KEY", None)


# ── Testes ────────────────────────────────────────────────────────────────────

class TestBuildJobMessage:

    def test_sem_signing_key_lanca_runtime_error(self, without_signing_key, x25519_agent_pub_pem):
        """Sem EXECUTOR_SIGNING_KEY configurada deve lançar RuntimeError."""
        from app.core.job_crypto import build_job_message

        with pytest.raises(RuntimeError, match="EXECUTOR_SIGNING_KEY"):
            build_job_message(
                executor_id="executor-001",
                workspace_id="ws-001",
                agent_x25519_pub_pem=x25519_agent_pub_pem,
                job_type="run_workflow",
                payload={"test": True},
            )

    def test_estrutura_resultado_completa(self, with_signing_key, x25519_agent_pub_pem):
        """Resultado deve conter exatamente as chaves: envelope, ephemeral_public, ciphertext, signature."""
        from app.core.job_crypto import build_job_message

        msg = build_job_message(
            executor_id="executor-001",
            workspace_id="ws-001",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload={"key": "value"},
        )

        assert set(msg.keys()) == {"envelope", "ephemeral_public", "ciphertext", "signature"}

    def test_campos_envelope(self, with_signing_key, x25519_agent_pub_pem):
        """Envelope deve conter todos os campos obrigatórios com valores corretos."""
        from app.core.job_crypto import build_job_message

        msg = build_job_message(
            executor_id="executor-abc",
            workspace_id="ws-xyz",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload={},
            job_id="custom-job-id",
        )

        env = msg["envelope"]
        assert env["job_id"] == "custom-job-id"
        assert env["target_executor_id"] == "executor-abc"
        assert env["workspace_id"] == "ws-xyz"
        assert env["job_type"] == "run_workflow"
        assert "issued_at" in env
        assert "expires_at" in env
        # nonce deve ser 32 bytes em hex = 64 caracteres
        assert len(env["nonce"]) == 64
        assert all(c in "0123456789abcdef" for c in env["nonce"])

    def test_job_id_gerado_automaticamente_se_none(self, with_signing_key, x25519_agent_pub_pem):
        """Sem job_id explícito, deve gerar um UUID4."""
        from app.core.job_crypto import build_job_message
        import re

        msg = build_job_message(
            executor_id="executor-001",
            workspace_id="ws-001",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload={},
        )

        job_id = msg["envelope"]["job_id"]
        uuid4_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        assert uuid4_pattern.match(job_id), f"job_id não é UUID4: {job_id}"

    def test_job_id_customizado_preservado(self, with_signing_key, x25519_agent_pub_pem):
        """job_id fornecido deve ser preservado no envelope."""
        from app.core.job_crypto import build_job_message

        msg = build_job_message(
            executor_id="executor-001",
            workspace_id="ws-001",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload={},
            job_id="my-deterministic-id",
        )

        assert msg["envelope"]["job_id"] == "my-deterministic-id"

    def test_ephemeral_public_e_ciphertext_sao_base64_valido(self, with_signing_key, x25519_agent_pub_pem):
        """ephemeral_public e ciphertext devem ser strings base64 decodificáveis."""
        from app.core.job_crypto import build_job_message

        msg = build_job_message(
            executor_id="executor-001",
            workspace_id="ws-001",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload={"data": "test"},
        )

        # Não deve lançar exceção
        ephemeral_raw = base64.b64decode(msg["ephemeral_public"])
        ciphertext_raw = base64.b64decode(msg["ciphertext"])

        # ephemeral_public X25519 = 32 bytes em raw
        assert len(ephemeral_raw) == 32
        # ciphertext inclui GCM nonce (12B) + dados cifrados + tag (16B)
        assert len(ciphertext_raw) >= 12 + 16

    def test_dois_jobs_geram_ephemeral_keys_diferentes(self, with_signing_key, x25519_agent_pub_pem):
        """Cada chamada deve gerar um par efêmero X25519 distinto (forward secrecy)."""
        from app.core.job_crypto import build_job_message

        msg1 = build_job_message("a", "ws", x25519_agent_pub_pem, "run_workflow", {})
        msg2 = build_job_message("a", "ws", x25519_agent_pub_pem, "run_workflow", {})

        assert msg1["ephemeral_public"] != msg2["ephemeral_public"]


class TestVerifyJobSignature:

    def test_assinatura_valida_retorna_true(
        self, with_signing_key, x25519_agent_pub_pem, ed25519_signing_key_b64
    ):
        """Mensagem não adulterada deve ter assinatura válida."""
        from app.core.job_crypto import build_job_message, get_server_signing_public_key_b64

        msg = build_job_message("executor-1", "ws-1", x25519_agent_pub_pem, "run_workflow", {})
        pub_b64 = get_server_signing_public_key_b64()

        assert _verify_job_signature(msg, pub_b64) is True

    def test_envelope_adulterado_retorna_false(
        self, with_signing_key, x25519_agent_pub_pem
    ):
        """Modificar o envelope após assinar deve invalidar a assinatura."""
        from app.core.job_crypto import build_job_message, get_server_signing_public_key_b64

        msg = build_job_message("executor-1", "ws-1", x25519_agent_pub_pem, "run_workflow", {})
        pub_b64 = get_server_signing_public_key_b64()

        # Adultera campo do envelope
        tampered = copy.deepcopy(msg)
        tampered["envelope"]["job_id"] = "attacker-injected-id"

        assert _verify_job_signature(tampered, pub_b64) is False

    def test_ciphertext_adulterado_retorna_false(
        self, with_signing_key, x25519_agent_pub_pem
    ):
        """Modificar o ciphertext deve invalidar a assinatura."""
        from app.core.job_crypto import build_job_message, get_server_signing_public_key_b64

        msg = build_job_message("executor-1", "ws-1", x25519_agent_pub_pem, "run_workflow", {})
        pub_b64 = get_server_signing_public_key_b64()

        tampered = copy.deepcopy(msg)
        # Modifica um byte no ciphertext via base64
        raw = bytearray(base64.b64decode(tampered["ciphertext"]))
        raw[0] ^= 0xFF  # bit flip
        tampered["ciphertext"] = base64.b64encode(bytes(raw)).decode()

        assert _verify_job_signature(tampered, pub_b64) is False

    def test_chave_ed25519_incorreta_retorna_false(
        self, with_signing_key, x25519_agent_pub_pem
    ):
        """Verificar com chave pública incorreta deve retornar False."""
        from app.core.job_crypto import build_job_message

        msg = build_job_message("executor-1", "ws-1", x25519_agent_pub_pem, "run_workflow", {})

        # Gera uma chave Ed25519 completamente diferente
        wrong_key = Ed25519PrivateKey.generate()
        wrong_pub_raw = wrong_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        wrong_pub_b64 = base64.b64encode(wrong_pub_raw).decode()

        assert _verify_job_signature(msg, wrong_pub_b64) is False

    def test_ephemeral_public_adulterado_retorna_false(
        self, with_signing_key, x25519_agent_pub_pem
    ):
        """Modificar ephemeral_public deve invalidar a assinatura."""
        from app.core.job_crypto import build_job_message, get_server_signing_public_key_b64

        msg = build_job_message("executor-1", "ws-1", x25519_agent_pub_pem, "run_workflow", {})
        pub_b64 = get_server_signing_public_key_b64()

        tampered = copy.deepcopy(msg)
        # Substitui ephemeral_public por outra chave X25519 gerada
        new_priv = X25519PrivateKey.generate()
        new_pub_raw = new_priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        tampered["ephemeral_public"] = base64.b64encode(new_pub_raw).decode()

        assert _verify_job_signature(tampered, pub_b64) is False


class TestRoundTrip:

    def test_build_e_verify_retorna_true(self, with_signing_key, x25519_agent_pub_pem):
        """Round-trip completo: build + verify deve retornar True."""
        from app.core.job_crypto import (
            build_job_message,
            get_server_signing_public_key_b64,
        )

        payload = {
            "workflow_definition": {"nodes": [], "edges": []},
            "run_id": "run-001",
            "params": {"input": "value"},
        }

        msg = build_job_message(
            executor_id="executor-round-trip",
            workspace_id="ws-round-trip",
            agent_x25519_pub_pem=x25519_agent_pub_pem,
            job_type="run_workflow",
            payload=payload,
            job_id="round-trip-job",
        )

        pub_b64 = get_server_signing_public_key_b64()
        assert _verify_job_signature(msg, pub_b64) is True


class TestGetServerSigningPublicKeyB64:

    def test_sem_chave_retorna_none(self, without_signing_key):
        """Sem EXECUTOR_SIGNING_KEY, deve retornar None."""
        from app.core.job_crypto import get_server_signing_public_key_b64

        result = get_server_signing_public_key_b64()

        assert result is None

    def test_com_chave_retorna_base64_valido(self, with_signing_key):
        """Com EXECUTOR_SIGNING_KEY válida, deve retornar base64 de 32 bytes (Ed25519 pub raw)."""
        from app.core.job_crypto import get_server_signing_public_key_b64

        result = get_server_signing_public_key_b64()

        assert result is not None
        pub_raw = base64.b64decode(result)
        # Chave pública Ed25519 raw = 32 bytes
        assert len(pub_raw) == 32
