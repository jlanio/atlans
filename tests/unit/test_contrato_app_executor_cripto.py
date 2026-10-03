# tests/unit/test_contrato_app_executor_cripto.py
"""
REAL round trip of the job crypto between server and executor.

`app/core/job_crypto.py` and `executor/crypto.py` are protocol pairs: one
encrypts/signs, the other decrypts/verifies. They must not be unified —
`executor/` does not import `app.*` in any file, and that boundary is deliberate
(the executor runs on-premise, on the customer's machine). The right remedy for
a pair like this is a contract test, not a shared abstraction.

Except the contract was not exercised. The only test that imported both sides
monkeypatched precisely `verify_signature` and `decrypt_job_payload`, and the
`verify_job_signature` the server kept was only used by tests (it left the
app) — that is, each side was tested against its OWN copy of the rules. A divergence in the
canonical bytes, in the HKDF, in the salt or in the separator would stay green
in both suites and break 100% of jobs in production, all at once, with no red
test.

Here nothing is monkeypatched: the server builds the message for real and the
executor opens it for real.
"""
from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)


@pytest.fixture
def chaves(monkeypatch):
    """Server's Ed25519 pair + executor's X25519 pair, as in production.

    Patches the module ATTRIBUTE, without `importlib.reload`. `job_crypto` does
    `from app.core.config import EXECUTOR_SIGNING_KEY`, so reloading it would
    reimport the value that `config` read at its own import — the test's new
    key would be ignored and the tests would end up signing with the key of
    whoever ran first. It is the same pattern as `tests/unit/test_job_crypto.py`.
    """
    servidor = Ed25519PrivateKey.generate()
    servidor_priv_b64 = base64.b64encode(
        servidor.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode()
    servidor_pub_b64 = base64.b64encode(
        servidor.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    executor = X25519PrivateKey.generate()
    executor_pub_pem = executor.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ).decode()

    import app.core.job_crypto as jc
    monkeypatch.setattr(jc, "EXECUTOR_SIGNING_KEY", servidor_priv_b64)
    monkeypatch.setattr("app.core.config.EXECUTOR_SIGNING_KEY", servidor_priv_b64)

    return {
        "jc": jc,
        "servidor_pub_b64": servidor_pub_b64,
        "executor_priv": executor,
        "executor_pub_pem": executor_pub_pem,
    }


def _montar(chaves, payload=None, job_type="run_workflow"):
    return chaves["jc"].build_job_message(
        executor_id="exec-1",
        workspace_id="ws-1",
        agent_x25519_pub_pem=chaves["executor_pub_pem"],
        job_type=job_type,
        payload=payload if payload is not None else {"definition": {"nodes": []}},
    )


# ── O round-trip ─────────────────────────────────────────────────────────────

def test_o_executor_verifica_a_assinatura_que_o_servidor_produz(chaves):
    """If the canonical bytes diverge between the sides, this breaks."""
    from executor import crypto as ec

    msg = _montar(chaves)
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is True


def test_o_executor_decifra_o_payload_que_o_servidor_cifrou(chaves):
    """Covers ECDH, HKDF (algorithm, length, salt and info) and AES-GCM at once."""
    from executor import crypto as ec

    original = {"definition": {"nodes": [{"id": "1", "name": "DataInput"}]}, "n": 42}
    msg = _montar(chaves, payload=original)

    assert ec.decrypt_job_payload(msg, chaves["executor_priv"]) == original


def test_payload_em_bytes_produz_o_mesmo_resultado_que_o_dict(chaves):
    """build_job_message accepts already-serialized JSON on the failover path."""
    from executor import crypto as ec

    original = {"definition": {"nodes": []}, "x": "acentuação"}
    msg = _montar(chaves, payload=json.dumps(original).encode())

    assert ec.decrypt_job_payload(msg, chaves["executor_priv"]) == original


# ── The contract also has to REJECT ──────────────────────────────────────────

def test_envelope_adulterado_invalida_a_assinatura(chaves):
    from executor import crypto as ec

    msg = _montar(chaves)
    msg["envelope"]["workspace_id"] = "ws-do-atacante"
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is False


def test_ciphertext_adulterado_invalida_a_assinatura(chaves):
    from executor import crypto as ec

    msg = _montar(chaves)
    msg["ciphertext"] = base64.b64encode(b"lixo").decode()
    assert ec.verify_signature(msg, chaves["servidor_pub_b64"]) is False


def test_assinatura_de_outro_servidor_e_recusada(chaves):
    from executor import crypto as ec

    outro = Ed25519PrivateKey.generate()
    outro_pub_b64 = base64.b64encode(
        outro.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()

    msg = _montar(chaves)
    assert ec.verify_signature(msg, outro_pub_b64) is False


def test_chave_de_executor_errada_nao_decifra(chaves):
    """A job addressed to one executor cannot be opened by another."""
    from executor import crypto as ec

    msg = _montar(chaves)
    intruso = X25519PrivateKey.generate()

    with pytest.raises(ValueError):
        ec.decrypt_job_payload(msg, intruso)
