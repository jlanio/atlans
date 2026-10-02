"""
Resolucao do trust store no enrollment.

Regressao real (quickstart Ubuntu/Docker):

    [ca-bootstrap] SSL_CERT_FILE ja setado externamente: /atlans-root.crt
    Enviando CSR para https://agents.atlans.example.org/... (verify=.../certifi/cacert.pem)
    FALHA: CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate

O `_ca_bootstrap` respeita o SSL_CERT_FILE do ambiente e retorna cedo; o
`enroll` procurava o root APENAS em `cert_dir/atlans-root.crt`, nao achava (o
quickstart grava em /atlans-root.crt) e caia no bundle publico do certifi — que
nao contem a CA interna que assina agents.atlans.example.org.
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


# ── Localizacao do root cert ─────────────────────────────────────────────────

def test_encontra_root_no_cert_dir(root_cert):
    assert _find_internal_root_cert(root_cert.parent) == root_cert


def test_encontra_root_via_ssl_cert_file(tmp_path, root_cert, monkeypatch):
    """Cenario do quickstart: cert FORA do cert_dir, apontado por env."""
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
    """O cert do enrollment anterior vence o env global da maquina."""
    outro = tmp_path / "outro.crt"
    outro.write_bytes(root_cert.read_bytes())
    monkeypatch.setenv("SSL_CERT_FILE", str(outro))

    assert _find_internal_root_cert(root_cert.parent) == root_cert


def test_env_apontando_para_arquivo_inexistente_e_ignorado(tmp_path, monkeypatch):
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.setenv("SSL_CERT_FILE", "/caminho/que/nao/existe.crt")
    # A funcao le as DUAS vars; sem controlar a segunda o teste depende do
    # ambiente da maquina (ou do que outro teste deixou para tras).
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    assert _find_internal_root_cert(vazio) is None


# ── Contexto de verificacao ──────────────────────────────────────────────────

def test_com_ca_interna_devolve_contexto_combinado(tmp_path, root_cert, monkeypatch):
    """Nao basta trocar certifi pela CA interna: um servidor com cert publico
    (atlans.example.org atras do Cloudflare) precisa do trust store padrao junto."""
    vazio = tmp_path / "certs"
    vazio.mkdir()
    monkeypatch.setenv("SSL_CERT_FILE", str(root_cert))

    verify, desc = _resolve_enroll_verify(vazio)

    assert isinstance(verify, ssl.SSLContext)
    assert "CA interna" in desc
    # O contexto tem de conter a CA interna E as publicas.
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
    """Cert ilegivel degrada para o bundle publico em vez de estourar."""
    ruim = tmp_path / "atlans-root.crt"
    ruim.write_text("isto nao e um certificado")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)

    verify, desc = _resolve_enroll_verify(Path(tmp_path))

    assert not isinstance(verify, ssl.SSLContext)
    assert "certifi" in desc or "sistema" in desc
