"""
Trust store resolution during enrollment.

Real regression (Ubuntu/Docker quickstart):

    [ca-bootstrap] SSL_CERT_FILE ja setado externamente: /atlans-root.crt
    Enviando CSR para https://agents.atlans.example.org/... (verify=.../certifi/cacert.pem)
    FALHA: CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate

`_ca_bootstrap` honors the environment's SSL_CERT_FILE and returns early;
`enroll` looked for the root ONLY in `cert_dir/atlans-root.crt`, did not find it
(the quickstart writes it to /atlans-root.crt) and fell back to certifi's public
bundle — which does not contain the internal CA that signs
agents.atlans.example.org.
"""
import ssl
from pathlib import Path

import pytest

from executor.enrollment import _find_internal_root_cert, _resolve_enroll_verify


@pytest.fixture
def root_cert(tmp_path):
    """Root cert minimo, valido o suficiente para load_verify_locations."""
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Atlans Test CA")])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(days=1))
        .not_valid_after(agora + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    p = tmp_path / "atlans-root.crt"
    p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return p


# ── Locating the root cert ───────────────────────────────────────────────────

def test_encontra_root_no_cert_dir(root_cert):
    assert _find_internal_root_cert(root_cert.parent) == root_cert


def test_encontra_root_via_ssl_cert_file(tmp_path, root_cert, monkeypatch):
    """Quickstart scenario: cert OUTSIDE cert_dir, pointed to by env."""
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.setenv("SSL_CERT_FILE", str(root_cert))

    assert _find_internal_root_cert(vazio) == root_cert


def test_encontra_root_via_requests_ca_bundle(tmp_path, root_cert, monkeypatch):
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(root_cert))

    assert _find_internal_root_cert(vazio) == root_cert


def test_cert_dir_tem_precedencia_sobre_env(tmp_path, root_cert, monkeypatch):
    """The cert from the previous enrollment wins over the machine's global env."""
    outro = tmp_path / "outro.crt"
    outro.write_bytes(root_cert.read_bytes())
    monkeypatch.setenv("SSL_CERT_FILE", str(outro))

    assert _find_internal_root_cert(root_cert.parent) == root_cert


def test_env_apontando_para_arquivo_inexistente_e_ignorado(tmp_path, monkeypatch):
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.setenv("SSL_CERT_FILE", "/caminho/que/nao/existe.crt")
    # The function reads BOTH vars; without controlling the second, the test
    # depends on the machine's environment (or on what another test left behind).
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    assert _find_internal_root_cert(vazio) is None


# ── Verification context ─────────────────────────────────────────────────────

def test_com_ca_interna_devolve_contexto_combinado(tmp_path, root_cert, monkeypatch):
    """Swapping certifi for the internal CA is not enough: a server with a public
    cert (atlans.example.org behind Cloudflare) needs the default trust store too."""
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.setenv("SSL_CERT_FILE", str(root_cert))

    verify, desc = _resolve_enroll_verify(vazio)

    assert isinstance(verify, ssl.SSLContext)
    assert "CA interna" in desc
    # The context must contain the internal CA AND the public ones.
    assuntos = {c["subject"][0][0][1] for c in verify.get_ca_certs()}
    assert "Atlans Test CA" in assuntos
    assert len(assuntos) > 1, "trust store padrao foi perdido"


def test_sem_ca_interna_cai_para_certifi(tmp_path, monkeypatch):
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    verify, desc = _resolve_enroll_verify(vazio)

    assert isinstance(verify, str) and verify.endswith(".pem")
    assert "certifi" in desc


def test_root_corrompido_nao_derruba_o_enroll(tmp_path, monkeypatch):
    """An unreadable cert degrades to the public bundle instead of blowing up."""
    ruim = tmp_path / "atlans-root.crt"
    ruim.write_text("isto nao e um certificado")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    verify, desc = _resolve_enroll_verify(Path(tmp_path))

    assert not isinstance(verify, ssl.SSLContext)
    assert "certifi" in desc or "sistema" in desc
