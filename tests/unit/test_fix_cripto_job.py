# tests/unit/test_fix_cripto_job.py
"""
Fixes for the executor's crypto/job group.

Covers:
  S1  — _ca_bootstrap no longer downloads the root cert without TLS verification
  B7  — renewal validates the whole bundle before overwriting the credentials
  B12 — the X25519 key is never generated silently post-enrollment
  S9  — anti-replay: expires_at ceiling, bound TTL, O(expired) purge
  B9  — failing jobs produce partial stats + __metrics__ with the real status
  S11 — build_mtls_ssl_context adds the public bundle (certifi) to ca.pem
"""
import asyncio
import datetime
import hashlib
import ssl
import urllib.error
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.x509.oid import NameOID


# ── Helpers ───────────────────────────────────────────────────────────────────


def _self_signed(key: Ed25519PrivateKey, cn: str = "Atlans Test CA") -> x509.Certificate:
    """Self-signed Ed25519 cert — cheap to generate and enough for parse/fingerprint."""
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    agora = datetime.datetime.now(datetime.timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(minutes=5))
        .not_valid_after(agora + datetime.timedelta(days=1))
        .sign(key, algorithm=None)
    )


def _pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


# ══════════════════════════════════════════════════════════════════════════════
# S1 — CA bootstrap without an unverified fallback
# ══════════════════════════════════════════════════════════════════════════════


class _FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.status = 200
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return self._payload


@pytest.fixture
def ca_pem_bytes():
    return _pem(_self_signed(Ed25519PrivateKey.generate())).encode()


def _fingerprint(pem_bytes: bytes) -> str:
    der = ssl.PEM_cert_to_DER_cert(pem_bytes.decode())
    return hashlib.sha256(der).hexdigest()


def _patch_urlopen(monkeypatch, behavior):
    """Substitui urllib.request.urlopen e registra os contextos usados."""
    from executor import _ca_bootstrap

    usados = []

    def fake_urlopen(req, **kwargs):
        usados.append(kwargs.get("context"))
        return behavior(req, kwargs)

    monkeypatch.setattr(_ca_bootstrap.urllib.request, "urlopen", fake_urlopen)
    return usados


def test_without_pin_there_is_no_unverified_fallback(monkeypatch, tmp_path):
    """A failing TLS handshake must NOT turn into an insecure download (the old TOFU)."""
    from executor import _ca_bootstrap

    monkeypatch.delenv(_ca_bootstrap._PIN_ENV, raising=False)

    def always_fail_tls(req, kwargs):
        raise urllib.error.URLError(ssl.SSLError("CERTIFICATE_VERIFY_FAILED"))

    usados = _patch_urlopen(monkeypatch, always_fail_tls)
    dest = tmp_path / "atlans-root.crt"

    with pytest.raises(urllib.error.URLError):
        _ca_bootstrap._download_atomic("https://atlans.example.org/executores/ca-bundle", dest)

    assert not dest.exists(), "nada pode ser persistido quando o TLS nao verifica"
    assert len(usados) == 1, "so pode existir a tentativa verificada"
    assert usados[0] is not None and usados[0].verify_mode == ssl.CERT_REQUIRED


def test_plain_http_aborts_without_touching_the_network(monkeypatch, tmp_path):
    """`--server=ws://...` became `http://` and the SSLContext was ignored by urllib:
    the CA arrived in cleartext and became the trust store of the whole host."""
    from executor import _ca_bootstrap

    monkeypatch.delenv(_ca_bootstrap._PIN_ENV, raising=False)
    usados = _patch_urlopen(monkeypatch, lambda req, kwargs: _FakeResp(b"x"))
    dest = tmp_path / "atlans-root.crt"

    with pytest.raises(ValueError, match="http"):
        _ca_bootstrap._download_atomic("http://atlans.interno:8000/executores/ca-bundle", dest)

    assert usados == [], "nem chega a abrir a conexao"
    assert not dest.exists()


def test_plain_http_is_allowed_with_pinned_fingerprint(monkeypatch, tmp_path, ca_pem_bytes):
    """With the pin, integrity does not depend on the channel — on-prem over http stays viable."""
    from executor import _ca_bootstrap

    monkeypatch.setenv(_ca_bootstrap._PIN_ENV, _fingerprint(ca_pem_bytes))
    _patch_urlopen(monkeypatch, lambda req, kwargs: _FakeResp(ca_pem_bytes))
    dest = tmp_path / "atlans-root.crt"

    _ca_bootstrap._download_atomic("http://atlans.interno:8000/x", dest)
    assert dest.read_bytes() == ca_pem_bytes


def test_non_tls_error_does_not_retry(monkeypatch, tmp_path):
    """A URLError from DNS/connection propagates directly — switching TLS context would not help."""
    from executor import _ca_bootstrap

    monkeypatch.setenv(_ca_bootstrap._PIN_ENV, "ab" * 32)

    def broken_dns(req, kwargs):
        raise urllib.error.URLError(OSError("Name or service not known"))

    usados = _patch_urlopen(monkeypatch, broken_dns)

    with pytest.raises(urllib.error.URLError):
        _ca_bootstrap._download_atomic("https://atlans.example.org/x", tmp_path / "ca.crt")
    assert len(usados) == 1


def test_pin_allows_unvalidated_chain_but_checks_fingerprint(
    monkeypatch, tmp_path, ca_pem_bytes
):
    """With a correct ATLANS_CA_SHA256, the download goes through even without a valid chain."""
    from executor import _ca_bootstrap

    monkeypatch.setenv(_ca_bootstrap._PIN_ENV, _fingerprint(ca_pem_bytes).upper())

    estado = {"n": 0}

    def fail_the_first(req, kwargs):
        estado["n"] += 1
        if estado["n"] == 1:
            raise urllib.error.URLError(ssl.SSLError("self signed certificate in chain"))
        return _FakeResp(ca_pem_bytes)

    usados = _patch_urlopen(monkeypatch, fail_the_first)
    dest = tmp_path / "atlans-root.crt"

    _ca_bootstrap._download_atomic("https://atlans.example.org/x", dest)

    assert dest.read_bytes() == ca_pem_bytes
    assert usados[1].verify_mode == ssl.CERT_NONE, "2a tentativa e a pinada"


def test_mismatched_pin_aborts_without_writing(monkeypatch, tmp_path, ca_pem_bytes):
    """Fingerprint diferente = possivel interceptacao: nada toca o disco."""
    from executor import _ca_bootstrap

    monkeypatch.setenv(_ca_bootstrap._PIN_ENV, "cd" * 32)
    _patch_urlopen(monkeypatch, lambda req, kwargs: _FakeResp(ca_pem_bytes))
    dest = tmp_path / "atlans-root.crt"

    with pytest.raises(ValueError, match="NAO casa"):
        _ca_bootstrap._download_atomic("https://atlans.example.org/x", dest)
    assert not dest.exists()
    assert not (tmp_path / "atlans-root.crt.tmp").exists()


# ══════════════════════════════════════════════════════════════════════════════
# B7 — renewal validates the bundle before overwriting
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def valid_bundle():
    key = Ed25519PrivateKey.generate()
    ca = _self_signed(Ed25519PrivateKey.generate(), cn="Atlans Root")
    cert = _self_signed(key, cn="executor-abc")
    return key, {
        "cert_pem": _pem(cert),
        "chain_pem": _pem(ca),
        "ca_pem": _pem(ca),
        "serial": "1",
        "expires_at": "2030-01-01T00:00:00Z",
    }


def test_valid_bundle_passes(valid_bundle):
    from executor.enrollment import _validate_bundle

    key, bundle = valid_bundle
    assert _validate_bundle(bundle, key) is None


@pytest.mark.parametrize("campo", ["cert_pem", "ca_pem"])
def test_bundle_with_empty_required_field_is_refused(valid_bundle, campo):
    """ca_pem vazio sobrescrevia o ca.pem bom e deixava o executor offline eterno."""
    from executor.enrollment import _validate_bundle

    key, bundle = valid_bundle
    bundle[campo] = ""
    motivo = _validate_bundle(bundle, key)
    assert motivo and campo in motivo


@pytest.mark.parametrize("valor", ["", None])
def test_empty_chain_pem_is_accepted(valid_bundle, valor):
    """An empty chain_pem is LEGITIMATELY issued by the server — it must not block renewal.

    `sign_csr_via_stepca` builds `chain_pem = body.get("ca") or ""`, and `enroll`
    stores that empty value without complaint. A validator stricter than the issuer
    would make every renewal cycle fail silently until the cert expired and the
    executor died for good — worse than the bug the validator came to fix. What
    anchors trust is ca_pem, not the chain.
    """
    from executor.enrollment import _validate_bundle

    key, bundle = valid_bundle
    if valor is None:
        bundle.pop("chain_pem", None)
    else:
        bundle["chain_pem"] = valor
    assert _validate_bundle(bundle, key) is None


def test_bundle_with_invalid_pem_is_refused(valid_bundle):
    from executor.enrollment import _validate_bundle

    key, bundle = valid_bundle
    bundle["ca_pem"] = "-----BEGIN CERTIFICATE-----\nlixo\n-----END CERTIFICATE-----\n"
    assert _validate_bundle(bundle, key) is not None


def test_cert_for_another_key_is_refused(valid_bundle):
    from executor.enrollment import _validate_bundle

    _key, bundle = valid_bundle
    assert "nao corresponde" in _validate_bundle(bundle, Ed25519PrivateKey.generate())


@pytest.mark.asyncio
async def test_maybe_renew_does_not_write_with_empty_ca_pem(monkeypatch, tmp_path, valid_bundle):
    """Ponta a ponta: servidor devolve ca_pem="" e os arquivos originais sobrevivem."""
    from executor import enrollment, renewal

    key, bundle = valid_bundle
    bundle["ca_pem"] = ""

    for nome, conteudo in (
        (enrollment.CERT_FILE, b"CERT-BOM"),
        (enrollment.CHAIN_FILE, b"CHAIN-BOM"),
        (enrollment.CA_FILE, b"CA-BOM"),
        (enrollment.KEY_FILE, b"KEY-BOM"),
    ):
        (tmp_path / nome).write_bytes(conteudo)

    monkeypatch.setattr(renewal, "_days_until_expiry", lambda _p: 1.0)
    monkeypatch.setattr(renewal, "_cert_common_name", lambda _p: "executor-abc")
    monkeypatch.setattr(renewal, "_build_csr", lambda _k, cn: b"csr")
    monkeypatch.setattr("executor.utils.build_mtls_ssl_context", lambda: None)

    async def fake_request(*_a, **_kw):
        return SimpleNamespace(status_code=200, json=lambda: bundle, text="")

    monkeypatch.setattr("flow.utils.http_retry.async_request_with_retry", fake_request)

    assert await renewal.maybe_renew("wss://x", tmp_path) is False
    assert (tmp_path / enrollment.CA_FILE).read_bytes() == b"CA-BOM"
    assert (tmp_path / enrollment.CERT_FILE).read_bytes() == b"CERT-BOM"


# ══════════════════════════════════════════════════════════════════════════════
# B12 — chave X25519 nunca e gerada silenciosamente
# ══════════════════════════════════════════════════════════════════════════════


def test_missing_key_fails_loudly_instead_of_generating(tmp_path):
    from executor.crypto import PrivateKeyMissingError, load_private_key

    caminho = tmp_path / "x25519_key.pem"
    with pytest.raises(PrivateKeyMissingError, match="enroll"):
        load_private_key(None, str(caminho))
    assert not caminho.exists(), "nao pode criar chave nova"


def test_existing_key_is_loaded(tmp_path):
    from executor.crypto import load_private_key

    priv = X25519PrivateKey.generate()
    caminho = tmp_path / "x25519_key.pem"
    caminho.write_bytes(priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))

    carregada = load_private_key(None, str(caminho))
    assert carregada.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ) == priv.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def test_file_with_wrong_key_is_refused(tmp_path):
    """Point EXECUTOR_PRIVATE_KEY_PATH at the mTLS key.pem (Ed25519)."""
    from executor.crypto import PrivateKeyMissingError, load_private_key

    caminho = tmp_path / "key.pem"
    caminho.write_bytes(Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    with pytest.raises(PrivateKeyMissingError, match="X25519"):
        load_private_key(None, str(caminho))


def test_crypto_no_longer_exposes_generation():
    """Generation lives only in the enrollment flow."""
    from executor import crypto

    assert not hasattr(crypto, "load_or_generate_private_key")


# ══════════════════════════════════════════════════════════════════════════════
# S9 — anti-replay
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def clean_validator(monkeypatch):
    from executor import job_validator

    job_validator._nonce_cache.clear()
    # The skew warning is throttled by a global — resetting it to None ("never
    # warned") keeps test order from deciding whether the WARNING fires or not.
    # Zeroing did not work: 0.0 means "warned at monotonic instant zero", and on a
    # host with uptime < 300s (a CI runner) the reset itself suppressed the warning.
    monkeypatch.setattr(job_validator, "_last_skew_warn_monotonic", None)
    # The signature is already covered by test_job_crypto — here we care about the rest.
    monkeypatch.setattr(job_validator, "verify_signature", lambda *_a, **_kw: True)
    yield job_validator
    job_validator._nonce_cache.clear()


def _message(
    expires_delta_seconds: float,
    nonce: str = "nonce-1",
    *,
    skew_seconds: float = 0.0,
) -> dict:
    """Envelope as the server issues it: `issued_at` = the SERVER's clock,
    `expires_at` = issued_at + TTL. `skew_seconds` simulates the server clock
    running ahead of the executor's (equivalent to the executor running behind)."""
    from executor import config

    issued = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=skew_seconds
    )
    expires = issued + datetime.timedelta(seconds=expires_delta_seconds)
    return {
        "envelope": {
            "target_executor_id": config.EXECUTOR_ID,
            "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
            "nonce": nonce,
            "job_id": "job-1",
            "job_type": "run_workflow",
            "workspace_id": "ws-1",
        },
    }


def test_envelope_within_the_horizon_passes(clean_validator):
    clean_validator.validate_job(_message(120))


def test_envelope_with_absurd_validity_is_rejected(clean_validator):
    """An expires_at 10 years out was valid forever — now it hits the ceiling."""
    with pytest.raises(clean_validator.JobValidationError, match="teto"):
        clean_validator.validate_job(_message(10 * 365 * 86400, nonce="nonce-longo"))


def test_envelope_without_issued_at_is_rejected(clean_validator):
    """Without issued_at there is no way to measure the declared duration — and the only
    alternative would be to anchor the ceiling on the local clock again, which is the skew bug."""
    msg = _message(120, nonce="sem-issued")
    del msg["envelope"]["issued_at"]
    with pytest.raises(clean_validator.JobValidationError, match="issued_at"):
        clean_validator.validate_job(msg)


def test_lagging_clock_does_not_reject_legitimate_job(clean_validator, caplog):
    """REGRESSION: the 1st version of the ceiling compared expires_at with the LOCAL clock.
    An executor 10 min behind rejected 100% of jobs — total unavailability
    from broken NTP. By measuring the declared duration, skew stops mattering
    up to the HARD CEILING (900s), which is tested right below."""
    with caplog.at_level("WARNING"):
        clean_validator.validate_job(_message(300, nonce="skew", skew_seconds=600))
    assert "Relógio local diverge" in caplog.text, "o operador precisa saber que e o NTP"


# ── Hard skew ceiling: fail LOUDLY instead of staying replayable ──────────────

def test_first_skew_warning_is_emitted_on_freshly_started_host(clean_validator, caplog, monkeypatch):
    """REGRESSION: the throttle anchored at 0.0 and `time.monotonic()` is the machine's
    uptime on Linux. On a host only a few seconds old — a container starting
    on a new VM, which is exactly when NTP tends to be off — the first
    warning was swallowed, and the operator only saw the rejection talking about replay."""
    monkeypatch.setattr(clean_validator.time, "monotonic", lambda: 12.0)

    with caplog.at_level("WARNING"):
        clean_validator.validate_job(_message(300, nonce="uptime-baixo", skew_seconds=600))

    assert "Relógio local diverge" in caplog.text


def test_skew_warnings_stay_throttled(clean_validator, caplog, monkeypatch):
    """The warning is per host, not per job: without a throttle, a full queue with NTP
    off becomes one WARNING per job."""
    momento = {"t": 12.0}
    monkeypatch.setattr(clean_validator.time, "monotonic", lambda: momento["t"])

    with caplog.at_level("WARNING"):
        clean_validator.validate_job(_message(300, nonce="skew-1", skew_seconds=600))
        momento["t"] += 30.0  # within the 300s interval
        caplog.clear()
        clean_validator.validate_job(_message(300, nonce="skew-2", skew_seconds=600))
    assert "Relógio local diverge" not in caplog.text

    with caplog.at_level("WARNING"):
        momento["t"] += 400.0  # passou o intervalo
        clean_validator.validate_job(_message(300, nonce="skew-3", skew_seconds=600))
    assert "Relógio local diverge" in caplog.text


def test_clock_far_behind_is_rejected_pointing_to_ntp(clean_validator):
    """The case that silently opened up replay.

    With the local clock behind the server, `agora_local` never reaches
    `expires_at`, so the expiration check NEVER fires and the envelope stays
    acceptable for (lag + duration) local seconds — longer than the nonce
    cache TTL. Once the TTL passes, the same signed envelope is accepted again.
    The hard ceiling trades that silent exposure for a refusal that says what to do.
    """
    teto = clean_validator._MAX_CLOCK_SKEW_SECONDS
    msg = _message(300, nonce="atrasado-demais", skew_seconds=teto + 120)
    with pytest.raises(clean_validator.JobValidationError) as exc:
        clean_validator.validate_job(msg)
    texto = str(exc.value)
    assert "NTP" in texto
    assert "atrasado" in texto, "a direcao da deriva precisa estar correta na mensagem"
    assert "replay" not in texto.split("NÃO é replay")[0], "nao pode acusar replay"


def test_clock_far_ahead_is_rejected_pointing_to_ntp(clean_validator):
    """The ceiling is symmetric — a clock running ahead also stops, with the right direction."""
    teto = clean_validator._MAX_CLOCK_SKEW_SECONDS
    msg = _message(300, nonce="adiantado-demais", skew_seconds=-(teto + 120))
    with pytest.raises(clean_validator.JobValidationError) as exc:
        clean_validator.validate_job(msg)
    assert "adiantado" in str(exc.value)


def test_nonce_ttl_covers_the_maximum_acceptance_window(clean_validator):
    """Anti-replay INVARIANT, verified instead of trusted.

    A nonce may only be forgotten after the corresponding envelope is no longer
    acceptable. The acceptance window measured on the LOCAL clock (which is what
    the cache uses) is max_duration + expiration_slack + max_tolerated_drift.
    If someone lowers the TTL or raises the skew ceiling without rebalancing the two,
    this test breaks — which is exactly when the hole would reappear.
    """
    janela = (
        clean_validator._MAX_EXPIRY_HORIZON_SECONDS
        + clean_validator._CLOCK_SKEW_TOLERANCE_SECONDS
        + clean_validator._MAX_CLOCK_SKEW_SECONDS
    )
    assert clean_validator._nonce_ttl_seconds() >= janela


def test_envelope_already_expired_beyond_tolerance_is_rejected(clean_validator):
    """Local clock AHEAD beyond the slack: rejects, but pointing at the clock."""
    msg = _message(300, nonce="velho", skew_seconds=-(300 + 300 + 60))
    with pytest.raises(clean_validator.JobValidationError, match="NTP"):
        clean_validator.validate_job(msg)


def test_replay_of_same_nonce_is_rejected(clean_validator):
    clean_validator.validate_job(_message(120, nonce="repetido"))
    with pytest.raises(clean_validator.JobValidationError, match="replay"):
        clean_validator.validate_job(_message(120, nonce="repetido"))


def test_cache_ttl_covers_the_maximum_horizon(clean_validator, monkeypatch):
    """A nonce must not be forgotten while the envelope is still valid."""
    from executor import config

    monkeypatch.setattr(config, "NONCE_CACHE_TTL", 5)
    assert clean_validator._nonce_ttl_seconds() >= clean_validator._MAX_EXPIRY_HORIZON_SECONDS


def test_purge_removes_only_the_expired(clean_validator, monkeypatch):
    import time

    agora = time.monotonic()
    ttl = clean_validator._nonce_ttl_seconds()
    clean_validator._nonce_cache["velho"] = agora - ttl - 10
    clean_validator._nonce_cache["novo"] = agora

    assert clean_validator._nonce_seen("outro") is False
    assert "velho" not in clean_validator._nonce_cache
    assert "novo" in clean_validator._nonce_cache


def test_valid_nonce_drop_is_logged_at_error(clean_validator, monkeypatch, caplog):
    """The old hole was the SILENT discarding of entries that were still valid."""
    monkeypatch.setattr(clean_validator, "_NONCE_CACHE_MAX", 2)
    clean_validator._nonce_seen("a")
    clean_validator._nonce_seen("b")

    with caplog.at_level("ERROR"):
        clean_validator._nonce_seen("c")

    assert "a" not in clean_validator._nonce_cache
    assert any(r.levelname == "ERROR" and "anti-replay" in r.message for r in caplog.records)


# ══════════════════════════════════════════════════════════════════════════════
# B9 — stats/__metrics__ on the error path
# ══════════════════════════════════════════════════════════════════════════════


class _FakeMetricsCollector:
    def build_metrics(self):
        return {"run": {"nodes_executed": 1}, "nodes": {}}


def _fake_executor():
    return SimpleNamespace(
        node_stats={"no-1": {"status": "success"}},
        final_outputs={},
        pinned_outputs={},
        metrics_collector=_FakeMetricsCollector(),
    )


def test_collect_stats_includes_the_collector_metrics():
    from executor.job_executor import _collect_stats

    ex = _fake_executor()
    stats = _collect_stats(ex, status="timeout")

    assert stats["no-1"] == {"status": "success"}
    assert stats["__metrics__"] == {"run": {"nodes_executed": 1}, "nodes": {}}


def test_error_result_always_has_stats():
    from executor.job_executor import _error_result

    assert _error_result("j", "r", "boom", "runtime")["stats"] == {}


@pytest.mark.asyncio
async def test_workflow_failure_returns_partial_stats(monkeypatch):
    """node_stats of the nodes already executed must not become {} on the server."""
    from executor import job_executor

    ex = _fake_executor()

    async def fake_dispatch(job_type, payload, envelope, event_queue=None, stats_holder=None):
        stats_holder["executor"] = ex
        stats_holder["run_id"] = "run-1"
        raise RuntimeError("no explodiu")

    monkeypatch.setattr(job_executor, "validate_job", lambda _m: None)
    monkeypatch.setattr(job_executor, "decrypt_job_payload", lambda _m, _k: {"run_id": "run-1"})
    monkeypatch.setattr(job_executor, "_agent_private_key", object())
    monkeypatch.setattr(job_executor, "_dispatch", fake_dispatch)

    result = await job_executor.execute_job({"envelope": {"job_id": "j1", "job_type": "run_workflow"}})

    assert result["status"] == "error"
    assert result["stats"]["no-1"] == {"status": "success"}
    assert result["stats"]["__metrics__"]["run"]["nodes_executed"] == 1


@pytest.mark.asyncio
async def test_timeout_also_returns_partial_stats(monkeypatch):
    """The deadline cancels the coroutine — the stats come through the holder, not the return value."""
    from executor import config, job_executor

    ex = _fake_executor()

    async def fake_dispatch(job_type, payload, envelope, event_queue=None, stats_holder=None):
        stats_holder["executor"] = ex
        await asyncio.sleep(30)

    monkeypatch.setattr(config, "JOB_TIMEOUT", 0.05)
    monkeypatch.setattr(job_executor, "validate_job", lambda _m: None)
    monkeypatch.setattr(job_executor, "decrypt_job_payload", lambda _m, _k: {"run_id": "run-1"})
    monkeypatch.setattr(job_executor, "_agent_private_key", object())
    monkeypatch.setattr(job_executor, "_dispatch", fake_dispatch)

    result = await job_executor.execute_job({"envelope": {"job_id": "j1", "job_type": "run_workflow"}})

    assert result["error_category"] == "timeout"
    assert result["stats"]["__metrics__"]["run"]["nodes_executed"] == 1


@pytest.mark.asyncio
async def test_node_timeout_does_not_become_job_timeout(monkeypatch):
    """From 3.11 on, `asyncio.TimeoutError` IS the built-in TimeoutError. The
    PythonScript raises the built-in one when the script exceeds ITS OWN deadline; with
    the job's `except asyncio.TimeoutError`, the run came out as "Job expirou após
    3600s" (job expired after 3600s) instead of the node's message. Only the job's
    deadline, when it expires, is the job's."""
    from executor import config, job_executor

    ex = _fake_executor()

    async def fake_dispatch(job_type, payload, envelope, event_queue=None, stats_holder=None):
        stats_holder["executor"] = ex
        raise TimeoutError("Execução do script excedeu o limite de 1 segundos.")

    monkeypatch.setattr(config, "JOB_TIMEOUT", 3600)
    monkeypatch.setattr(job_executor, "validate_job", lambda _m: None)
    monkeypatch.setattr(job_executor, "decrypt_job_payload", lambda _m, _k: {"run_id": "run-1"})
    monkeypatch.setattr(job_executor, "_agent_private_key", object())
    monkeypatch.setattr(job_executor, "_dispatch", fake_dispatch)

    result = await job_executor.execute_job({"envelope": {"job_id": "j1", "job_type": "run_workflow"}})

    assert result["error"] == "Execução do script excedeu o limite de 1 segundos."
    assert "Job expirou" not in result["error"]
    # The category is still "timeout" (classify_error), but the path is the error
    # path — the job did not expire — and the partial stats arrive all the same.
    assert result["error_category"] == "timeout"
    assert result["stats"]["no-1"] == {"status": "success"}


@pytest.mark.asyncio
async def test_expired_job_deadline_is_still_the_job_deadline(monkeypatch):
    from executor import config, job_executor

    async def fake_dispatch(job_type, payload, envelope, event_queue=None, stats_holder=None):
        await asyncio.sleep(30)

    monkeypatch.setattr(config, "JOB_TIMEOUT", 0.05)
    monkeypatch.setattr(job_executor, "validate_job", lambda _m: None)
    monkeypatch.setattr(job_executor, "decrypt_job_payload", lambda _m, _k: {"run_id": "run-1"})
    monkeypatch.setattr(job_executor, "_agent_private_key", object())
    monkeypatch.setattr(job_executor, "_dispatch", fake_dispatch)

    result = await job_executor.execute_job({"envelope": {"job_id": "j1", "job_type": "run_workflow"}})

    assert result["error"] == "Job expirou após 0.05s."
    assert result["error_category"] == "timeout"


@pytest.mark.asyncio
async def test_validation_failure_does_not_invent_stats(monkeypatch):
    from executor import job_executor
    from executor.job_validator import JobValidationError

    def recusa(_m):
        raise JobValidationError("assinatura invalida")

    monkeypatch.setattr(job_executor, "validate_job", recusa)
    result = await job_executor.execute_job({"envelope": {"job_id": "j1"}})

    assert result["error_category"] == "validation"
    assert result["stats"] == {}


# ══════════════════════════════════════════════════════════════════════════════
# S11 — contexto mTLS mantem o trust store publico
# ══════════════════════════════════════════════════════════════════════════════


def test_mtls_context_loads_certifi_besides_the_internal_ca(monkeypatch):
    """The bootstrap's SSL_CERT_FILE replaces the trust store — certifi has to come back."""
    import certifi

    from executor import config, utils

    carregados = []

    class _CtxFake:
        def load_verify_locations(self, cafile=None, **_kw):
            carregados.append(cafile)

        def load_default_certs(self):
            carregados.append("default")

        def load_cert_chain(self, certfile, keyfile):
            carregados.append(("chain", certfile, keyfile))

    monkeypatch.setattr(ssl, "create_default_context", lambda *a, **kw: _CtxFake())
    monkeypatch.setattr(config, "EXECUTOR_CA_PATH", "/tmp/ca.pem")
    monkeypatch.setattr(config, "EXECUTOR_CERT_PATH", "/tmp/cert.pem")
    monkeypatch.setattr(config, "EXECUTOR_KEY_PATH", "/tmp/key.pem")

    utils.build_mtls_ssl_context()

    assert certifi.where() in carregados
    assert "/tmp/ca.pem" in carregados
    # The internal CA must go in AFTER the public bundle (adds to it, does not replace it).
    assert carregados.index(certifi.where()) < carregados.index("/tmp/ca.pem")
