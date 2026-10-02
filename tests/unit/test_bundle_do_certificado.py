# tests/unit/test_bundle_do_certificado.py
"""
Persistencia do bundle mTLS — um caminho so para o enroll e o renewal.

O renewal validava o bundle e trocava os arquivos com `.new` + os.replace desde
que um `ca_pem` vazio sobrescreveu o ca.pem BOM e deixou o executor offline sem
chance de autocorrecao. O enroll ficou para tras: gravava direto, aceitando o
mesmo `ca_pem` vazio — num RE-enroll, o ca.pem bom virava um arquivo vazio.
"""
import datetime
import os
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from executor import enrollment

RAIZ = Path(__file__).resolve().parents[2]

_IDENTIDADE = {
    "cert.pem": b"CERT-BOM",
    "chain.pem": b"CHAIN-BOM",
    "ca.pem": b"CA-BOM",
    "key.pem": b"KEY-BOM",
    "x25519_key.pem": b"X25519-BOM",
}


def _pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


class _CA:
    """CA de teste que assina o CSR recebido, como a step-ca atras do servidor."""

    def __init__(self):
        self.chave = Ed25519PrivateKey.generate()
        self.cert = self._emitir(self.chave.public_key(), "Atlans Test Root")

    def _emitir(self, publica, cn: str) -> x509.Certificate:
        agora = datetime.datetime.now(datetime.timezone.utc)
        return (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
            .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Atlans Test Root")]))
            .public_key(publica)
            .serial_number(x509.random_serial_number())
            .not_valid_before(agora - datetime.timedelta(minutes=5))
            .not_valid_after(agora + datetime.timedelta(days=1))
            .sign(self.chave, algorithm=None)
        )

    def bundle(self, csr_pem: str, **sobrescrever) -> dict:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        cn = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        return {
            "cert_pem": _pem(self._emitir(csr.public_key(), cn)),
            # O servidor preenche chain com `body.get("ca") or ""`: vazio e legitimo.
            "chain_pem": "",
            "ca_pem": _pem(self.cert),
            "serial": "1", "fingerprint": "ab:cd",
            "issued_at": "2026-01-01T00:00:00Z", "expires_at": "2026-01-02T00:00:00Z",
            **sobrescrever,
        }


def _cert_dir_enrolado(tmp_path: Path) -> Path:
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()
    for nome, conteudo in _IDENTIDADE.items():
        (cert_dir / nome).write_bytes(conteudo)
    return cert_dir


def _servidor_de_enroll(monkeypatch, ca: _CA, **sobrescrever) -> dict:
    enviado: dict = {}

    def _post(url, **kw):
        enviado.update(kw["json"])
        return httpx.Response(200, json=ca.bundle(kw["json"]["csr_pem"], **sobrescrever))

    monkeypatch.setattr(enrollment.httpx, "post", _post)
    return enviado


def _enroll(cert_dir: Path, tmp_path: Path) -> dict:
    # env_path explicito: sem ele o enroll gravaria no executor/.env do checkout.
    return enrollment.enroll(
        "https://srv.invalid", "otp", "exec-1", cert_dir, env_path=tmp_path / ".env",
    )


def test_reenroll_com_ca_pem_vazio_nao_sobrescreve_o_ca_bom(tmp_path, monkeypatch):
    """O bug: o enroll gravava `bundle.get("ca_pem", "")` direto no ca.pem."""
    cert_dir = _cert_dir_enrolado(tmp_path)
    _servidor_de_enroll(monkeypatch, _CA(), ca_pem="")

    try:
        _enroll(cert_dir, tmp_path)
    except RuntimeError as exc:
        erro = str(exc)
    else:
        erro = None

    assert (cert_dir / "ca.pem").read_bytes() == b"CA-BOM", "o ca.pem bom virou o ca_pem vazio"
    for nome, conteudo in _IDENTIDADE.items():
        assert (cert_dir / nome).read_bytes() == conteudo, f"{nome} foi sobrescrito"
    assert erro is not None and "ca_pem" in erro, "o enroll tem de falhar dizendo o porque"
    assert not list(cert_dir.glob("*.new"))


def test_enroll_com_cert_de_outra_chave_nao_grava_nada(tmp_path, monkeypatch):
    """Mesma validacao do renewal: cert que nao e da chave gerada = par quebrado."""
    cert_dir = _cert_dir_enrolado(tmp_path)
    ca = _CA()
    alheio = ca.bundle(enrollment._build_csr(Ed25519PrivateKey.generate(), "executor-x").decode())
    _servidor_de_enroll(monkeypatch, ca, cert_pem=alheio["cert_pem"])

    with pytest.raises(RuntimeError, match="nao corresponde"):
        _enroll(cert_dir, tmp_path)
    assert (cert_dir / "cert.pem").read_bytes() == b"CERT-BOM"


def test_enroll_valido_troca_toda_a_identidade(tmp_path, monkeypatch):
    cert_dir = _cert_dir_enrolado(tmp_path)
    ca = _CA()
    enviado = _servidor_de_enroll(monkeypatch, ca)

    info = _enroll(cert_dir, tmp_path)

    assert info["serial"] == "1"
    assert (cert_dir / "ca.pem").read_text() == _pem(ca.cert)
    assert (cert_dir / "chain.pem").read_bytes() == b""
    cert = x509.load_pem_x509_certificate((cert_dir / "cert.pem").read_bytes())
    chave = serialization.load_pem_private_key((cert_dir / "key.pem").read_bytes(), None)
    assert cert.public_key() == chave.public_key(), "cert.pem e key.pem sao um par"
    chave_x = serialization.load_pem_private_key((cert_dir / "x25519_key.pem").read_bytes(), None)
    publica_x = chave_x.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    assert publica_x == enviado["public_key_pem"], "x25519_key.pem e a chave registrada"
    assert not list(cert_dir.glob("*.new"))
    if os.name == "posix":
        for nome in _IDENTIDADE:
            assert (cert_dir / nome).stat().st_mode & 0o777 == 0o600, nome


def test_falha_de_escrita_no_meio_nao_troca_arquivo_nenhum(tmp_path, monkeypatch):
    """Tudo vai para .new antes do primeiro os.replace: disco cheio na metade
    nao deixa metade das credenciais nova e metade velha."""
    cert_dir = _cert_dir_enrolado(tmp_path)
    ca = _CA()
    chave = Ed25519PrivateKey.generate()
    bundle = ca.bundle(enrollment._build_csr(chave, "executor-abc").decode())

    escrever = enrollment._write_pem

    def _write_pem(caminho, conteudo, mode=0o600):
        if caminho.name == "ca.pem.new":
            raise OSError(28, "No space left on device")
        escrever(caminho, conteudo, mode)

    monkeypatch.setattr(enrollment, "_write_pem", _write_pem)
    with pytest.raises(OSError):
        enrollment._persistir_bundle(cert_dir, bundle, chave)

    for nome, conteudo in _IDENTIDADE.items():
        assert (cert_dir / nome).read_bytes() == conteudo, nome
    assert not list(cert_dir.glob("*.new")), "os .new da tentativa nao podem sobrar"


@pytest.mark.asyncio
async def test_renewal_valido_passa_pelo_mesmo_caminho(tmp_path, monkeypatch):
    from executor import renewal

    cert_dir = _cert_dir_enrolado(tmp_path)
    ca = _CA()
    monkeypatch.setattr(renewal, "_days_until_expiry", lambda _p: 1.0)
    monkeypatch.setattr(renewal, "_cert_common_name", lambda _p: "executor-abc")
    monkeypatch.setattr("executor.utils.build_mtls_ssl_context", lambda: None)

    async def _post(*_a, json, **_kw):
        bundle = ca.bundle(json["csr_pem"])
        return SimpleNamespace(status_code=200, json=lambda: bundle, text="")

    monkeypatch.setattr("flow.utils.http_retry.async_request_with_retry", _post)

    assert await renewal.maybe_renew("wss://x", cert_dir) is True
    assert (cert_dir / "ca.pem").read_text() == _pem(ca.cert)
    cert = x509.load_pem_x509_certificate((cert_dir / "cert.pem").read_bytes())
    chave = serialization.load_pem_private_key((cert_dir / "key.pem").read_bytes(), None)
    assert cert.public_key() == chave.public_key()
    # A chave de envelope nao e do cert mTLS: o renewal nao a toca.
    assert (cert_dir / "x25519_key.pem").read_bytes() == b"X25519-BOM"
    assert not list(cert_dir.glob("*.new"))


def test_renewal_nao_grava_arquivo_por_conta_propria():
    """A escrita das credenciais tem um lugar so; a segunda copia foi a que divergiu."""
    texto = (RAIZ / "executor" / "renewal.py").read_text(encoding="utf-8")
    assert "_write_pem(" not in texto
    assert "os.replace(" not in texto
    assert "PrivateFormat.PKCS8" not in texto
