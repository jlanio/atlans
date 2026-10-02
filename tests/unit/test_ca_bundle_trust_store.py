# tests/unit/test_ca_bundle_trust_store.py
"""
Trust store do executor: CAs publicas + CA interna, nunca a interna sozinha.

Regressao do bug em que `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` apontavam so para
`atlans-root.crt`. Como essas env vars SUBSTITUEM o trust store do processo (nao
somam), todo HTTPS de saida para servidor publico quebrava dentro dos nos de
workflow com `unable to get local issuer certificate` — reportado no no WFS
contra geoportal.example.org, cujo cert Let's Encrypt e valido.

Cobre tambem o lado do no: cadeia TLS invalida nao e falha transiente, entao
nao pode consumir o ciclo de retries nem vazar a mensagem crua do urllib3.
"""
import datetime
import os
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cert_pem(cn: str) -> bytes:
    """Root CA autoassinada. `basicConstraints CA:TRUE` nao e detalhe cosmetico:
    OpenSSL so contabiliza em `x509_ca` o que esta marcado como CA, e sem isso o
    bundle carregaria mas nao serviria como ancora de confianca."""
    key = Ed25519PrivateKey.generate()
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(minutes=5))
        .not_valid_after(agora + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, algorithm=None)
    )
    return cert.public_bytes(serialization.Encoding.PEM)


@pytest.fixture
def root_cert(tmp_path):
    """CA interna ja gravada, como o bootstrap a encontra num boot subsequente."""
    p = tmp_path / "certs" / "atlans-root.crt"
    p.parent.mkdir(parents=True)
    p.write_bytes(_cert_pem("Atlans Internal Root CA"))
    return p


@pytest.fixture
def fake_certifi(monkeypatch, tmp_path):
    """certifi.where() apontando para um bundle publico sintetico."""
    import sys
    import types

    bundle = tmp_path / "certifi-cacert.pem"
    bundle.write_bytes(_cert_pem("Public CA A") + _cert_pem("Public CA B"))

    mod = types.ModuleType("certifi")
    mod.where = lambda: str(bundle)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "certifi", mod)
    return bundle


_TRUST_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")


@pytest.fixture(autouse=True)
def _clean_trust_env():
    """Isola as env vars de trust store, na entrada E na saida.

    monkeypatch nao basta: `_set_env` escreve em os.environ direto, e uma var que
    nao existia no inicio do teste nao fica registrada para restauracao — ela
    vazaria para os testes seguintes (test_enrollment_tls le REQUESTS_CA_BUNDLE).
    """
    antes = {v: os.environ.get(v) for v in _TRUST_VARS}
    for v in _TRUST_VARS:
        os.environ.pop(v, None)
    yield
    for v, valor in antes.items():
        if valor is None:
            os.environ.pop(v, None)
        else:
            os.environ[v] = valor


def _count_certs(payload: bytes) -> int:
    return payload.count(b"-----BEGIN CERTIFICATE-----")


# ══════════════════════════════════════════════════════════════════════════════
# Bundle combinado
# ══════════════════════════════════════════════════════════════════════════════


def test_bundle_combina_publicas_e_interna(root_cert, fake_certifi):
    """O arquivo publicado no env tem as CAs publicas E a interna."""
    from executor import _ca_bootstrap

    bundle = _ca_bootstrap._ensure_combined_bundle(root_cert)
    payload = bundle.read_bytes()

    assert bundle != root_cert, "apontar para a CA interna sozinha e o bug"
    assert _count_certs(payload) == 3, "2 publicas + 1 interna"
    assert root_cert.read_bytes().strip() in payload
    assert fake_certifi.read_bytes().strip() in payload
    # Precisa ser parseavel como trust store de verdade, nao so texto concatenado.
    # SSLContext cru em vez de create_default_context(): este ja carrega o trust
    # store do SO e a contagem viraria "3 + o que a maquina tiver".
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations(cafile=str(bundle))
    assert ctx.cert_store_stats()["x509_ca"] == 3


def test_set_env_publica_as_tres_variaveis(root_cert, fake_certifi):
    """stdlib/httpx, requests/urllib3 e libcurl (GDAL/pyogrio) leem vars distintas."""
    from executor import _ca_bootstrap

    _ca_bootstrap._set_env(root_cert)

    valores = {
        os.environ["SSL_CERT_FILE"],
        os.environ["REQUESTS_CA_BUNDLE"],
        os.environ["CURL_CA_BUNDLE"],
    }
    assert len(valores) == 1, "as tres devem apontar para o mesmo bundle"
    publicado = valores.pop()
    assert publicado != str(root_cert.resolve())
    assert _count_certs(open(publicado, "rb").read()) == 3


def test_bundle_regravado_quando_root_cert_muda(root_cert, fake_certifi):
    """Renovacao da CA interna precisa refletir no bundle derivado."""
    from executor import _ca_bootstrap

    bundle = _ca_bootstrap._ensure_combined_bundle(root_cert)
    antes = bundle.read_bytes()

    novo = _cert_pem("Atlans Internal Root CA v2")
    root_cert.write_bytes(novo)
    _ca_bootstrap._ensure_combined_bundle(root_cert)

    depois = bundle.read_bytes()
    assert depois != antes
    assert novo.strip() in depois


def test_bundle_nao_reescreve_sem_mudanca(root_cert, fake_certifi):
    """Boot normal nao toca o disco (mtime estavel)."""
    from executor import _ca_bootstrap

    bundle = _ca_bootstrap._ensure_combined_bundle(root_cert)
    mtime = bundle.stat().st_mtime_ns

    _ca_bootstrap._ensure_combined_bundle(root_cert)

    assert bundle.stat().st_mtime_ns == mtime


def test_cert_dir_read_only_cai_para_tmpdir(root_cert, fake_certifi, monkeypatch, tmp_path):
    """O compose oferece montar ./executor-certs:/data/certs:ro — o bundle e
    derivado, entao gravar no tmpdir e suficiente e melhor que degradar."""
    from executor import _ca_bootstrap

    tmpdir = tmp_path / "tmpdir"
    tmpdir.mkdir()
    monkeypatch.setattr(_ca_bootstrap.tempfile, "gettempdir", lambda: str(tmpdir))

    real_write = _ca_bootstrap.Path.write_bytes

    def write_bytes_negando_certdir(self, data):
        if self.parent == root_cert.parent:
            raise OSError(30, "Read-only file system")
        return real_write(self, data)

    monkeypatch.setattr(_ca_bootstrap.Path, "write_bytes", write_bytes_negando_certdir)

    bundle = _ca_bootstrap._ensure_combined_bundle(root_cert)

    assert bundle.parent == tmpdir.resolve()
    assert _count_certs(bundle.read_bytes()) == 3


def test_sem_certifi_usa_cafile_do_sistema(root_cert, monkeypatch, tmp_path):
    """Sem certifi instalado, o trust store do SO ainda precisa entrar no bundle."""
    import builtins

    from executor import _ca_bootstrap

    sistema = tmp_path / "system-ca.pem"
    sistema.write_bytes(_cert_pem("System CA"))

    real_import = builtins.__import__

    def sem_certifi(name, *args, **kwargs):
        if name == "certifi":
            raise ImportError("no certifi")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sem_certifi)
    monkeypatch.setattr(
        _ca_bootstrap.ssl, "get_default_verify_paths",
        lambda: ssl.DefaultVerifyPaths(str(sistema), None, "", str(sistema), "", ""),
    )

    bundle = _ca_bootstrap._ensure_combined_bundle(root_cert)

    assert _count_certs(bundle.read_bytes()) == 2
    assert sistema.read_bytes().strip() in bundle.read_bytes()


def test_sem_ca_publica_nenhuma_degrada_para_root(root_cert, monkeypatch):
    """Sem material publico o executor ainda fala com agents.atlans.example.org; o
    WARNING e que precisa explicar por que HTTPS publico vai falhar."""
    from executor import _ca_bootstrap

    monkeypatch.setattr(_ca_bootstrap, "_public_ca_pem", lambda: (None, "none"))
    avisos = []
    monkeypatch.setattr(
        _ca_bootstrap, "_emit", lambda nivel, msg: avisos.append((nivel, msg))
    )

    assert _ca_bootstrap._ensure_combined_bundle(root_cert) == root_cert.resolve()
    assert any(n == "WARNING" and "certifi" in m for n, m in avisos)


def test_ssl_cert_file_externo_nao_e_sobrescrito(root_cert, fake_certifi, monkeypatch):
    """Override do operador continua vencendo — regra documentada do modulo."""
    from executor import _ca_bootstrap

    monkeypatch.setenv("SSL_CERT_FILE", "/opt/corp/ca.pem")
    _ca_bootstrap.bootstrap_ca()

    assert os.environ["SSL_CERT_FILE"] == "/opt/corp/ca.pem"


def test_bootstrap_reusa_cert_existente_e_publica_bundle(root_cert, fake_certifi, monkeypatch):
    """Caminho real do container: cert ja em EXECUTOR_CERT_DIR, sem download."""
    from executor import _ca_bootstrap

    monkeypatch.setenv("EXECUTOR_CERT_DIR", str(root_cert.parent))
    monkeypatch.setattr(
        _ca_bootstrap, "_download_atomic",
        lambda *a, **k: pytest.fail("nao deve baixar com o cert presente"),
    )

    _ca_bootstrap.bootstrap_ca()

    assert _count_certs(open(os.environ["SSL_CERT_FILE"], "rb").read()) == 3


# ══════════════════════════════════════════════════════════════════════════════
# Lado do no: cadeia invalida nao e falha transiente
# ══════════════════════════════════════════════════════════════════════════════


def test_detecta_erro_de_cadeia_embrulhado():
    """requests embrulha o SSLCertVerificationError e perde o tipo original."""
    from flow.utils.geo_helpers import is_tls_verify_error

    raiz = ssl.SSLCertVerificationError(
        1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
           "unable to get local issuer certificate (_ssl.c:1010)"
    )
    try:
        try:
            raise raiz
        except ssl.SSLCertVerificationError as exc:
            raise ConnectionError("Max retries exceeded with url: /geoserver/ows") from exc
    except ConnectionError as embrulhado:
        assert is_tls_verify_error(embrulhado)

    # Texto sem tipo (o caso do urllib3, que stringifica a causa).
    assert is_tls_verify_error(
        RuntimeError("Caused by SSLError(SSLCertVerificationError(1, '[SSL: "
                     "CERTIFICATE_VERIFY_FAILED] ...'))")
    )


def test_nao_confunde_falha_transiente():
    from flow.utils.geo_helpers import is_tls_verify_error

    assert not is_tls_verify_error(TimeoutError("read timeout"))
    assert not is_tls_verify_error(ConnectionResetError("connection reset by peer"))
    assert not is_tls_verify_error(None)


def test_ciclo_de_causas_nao_trava():
    """__context__ circular nao pode virar loop infinito no meio de um run."""
    from flow.utils.geo_helpers import is_tls_verify_error

    a, b = RuntimeError("a"), RuntimeError("b")
    a.__cause__ = b
    b.__cause__ = a

    assert is_tls_verify_error(a) is False


def test_wfs_nao_retenta_erro_de_certificado(monkeypatch):
    """3 tentativas com backoff so fazem o usuario esperar pelo mesmo erro."""
    import flow.nodes.datasource.wfs as wfs

    chamadas = []

    def falha_tls(*_a, **_k):
        chamadas.append(1)
        raise ConnectionError(
            "HTTPSConnectionPool(host='geoportal.example.org', port=443): "
            "Max retries exceeded (Caused by SSLError(SSLCertVerificationError(1, "
            "'[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "unable to get local issuer certificate (_ssl.c:1010)')))"
        )

    monkeypatch.setattr(wfs, "_fetch_wfs_features", falha_tls)
    monkeypatch.setattr(wfs.time if hasattr(wfs, "time") else __import__("time"),
                        "sleep", lambda _s: pytest.fail("nao deve dormir em backoff"))

    with pytest.raises(RuntimeError) as ei:
        wfs._fetch_with_retry(
            "https://geoportal.example.org/geoserver/ows", "camada",
            1000, None, None, None, 60, retries=2, retry_delay=3,
        )

    assert len(chamadas) == 1, "erro de cadeia TLS nao deve consumir retries"
    msg = str(ei.value)
    assert "geoportal.example.org" in msg
    assert "cadeia incompleta" in msg
    assert "tentativa(s)" not in msg, "nao deve virar a mensagem generica de retry"


async def test_safe_httpx_request_traduz_erro_de_certificado(monkeypatch):
    """Os nos HTTP (GET/POST/Request) e o webhook passam todos por aqui: a
    traducao fica no helper para nao ser reimplementada em cada no."""
    import httpx

    import flow.utils.geo_helpers as gh

    monkeypatch.setattr(gh, "validate_url_ssrf", lambda _u: ("203.0.113.10", "geoportal.example.org"))

    async def send_falhando(self, request, **_k):
        raise httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "unable to get local issuer certificate (_ssl.c:1010)"
        )

    monkeypatch.setattr(httpx.AsyncClient, "send", send_falhando)

    with pytest.raises(RuntimeError) as ei:
        await gh.safe_httpx_request("GET", "https://geoportal.example.org/geoserver/ows")

    msg = str(ei.value)
    assert "geoportal.example.org" in msg, "cita o host digitado, nao o IP do pin"
    assert "203.0.113.10" not in msg
    assert "cadeia incompleta" in msg


async def test_safe_httpx_request_nao_mascara_outros_erros(monkeypatch):
    """Timeout continua sendo timeout — o caller distingue transiente de fatal."""
    import httpx

    import flow.utils.geo_helpers as gh

    monkeypatch.setattr(gh, "validate_url_ssrf", lambda _u: ("93.184.216.34", "exemplo.gov.br"))

    async def send_timeout(self, request, **_k):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx.AsyncClient, "send", send_timeout)

    with pytest.raises(httpx.ConnectTimeout):
        await gh.safe_httpx_request("GET", "https://exemplo.gov.br/api")


def test_wfs_ainda_retenta_falha_transiente(monkeypatch):
    """A correcao nao pode desligar o retry legitimo."""
    import flow.nodes.datasource.wfs as wfs

    chamadas = []

    def falha_transiente(*_a, **_k):
        chamadas.append(1)
        raise TimeoutError("read timeout")

    monkeypatch.setattr(wfs, "_fetch_wfs_features", falha_transiente)
    monkeypatch.setattr(__import__("time"), "sleep", lambda _s: None)

    with pytest.raises(RuntimeError, match="tentativa"):
        wfs._fetch_with_retry(
            "https://exemplo.gov.br/geoserver/ows", "camada",
            1000, None, None, None, 60, retries=2, retry_delay=0,
        )

    assert len(chamadas) == 3
