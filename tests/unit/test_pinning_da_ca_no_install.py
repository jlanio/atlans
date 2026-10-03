# tests/unit/test_pinning_da_ca_no_install.py
"""
Pinning of the CA root cert in the served install.sh.

`STEPCA_ROOT_FINGERPRINT` was read in `app/core/config.py` and never used
anywhere in the backend, while `docs/mtls-bootstrap.md:77` claimed the backend
used it "when building install.sh". The executor always supported pinning
(`ATLANS_CA_SHA256`, in executor/_ca_bootstrap.py) — what was missing was
someone publishing the value.

The effect of the gap: the installer's `curl .../ca-bundle` was pure TOFU.
Anyone able to answer in place of the server delivered their own CA, and the
executor would start trusting certs signed by it.

Three test levels, because each one catches a different class of error:

  INJECTION    the server actually replaces the script line.
  DEGRADATION  empty or invalid config must not break the installer.
  EXECUTION    the generated shell really accepts the right cert and rejects the wrong one.
"""
from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from app.api.routers.executores_router import (
    _CA_PIN_LINE, _inject_ca_fingerprint, _normalize_fingerprint,
)

RAIZ = Path(__file__).resolve().parents[2]
INSTALL_SH = RAIZ / "static" / "install.sh"

FP = "a" * 64


# ── INJECAO ──────────────────────────────────────────────────────────────────

def test_the_pinning_line_exists_in_the_script():
    """Ancora o acoplamento: o servidor substitui esta string exata."""
    assert _CA_PIN_LINE in INSTALL_SH.read_text(encoding="utf-8"), (
        "static/install.sh perdeu a linha que o servidor substitui — o "
        "fingerprint deixaria de ser publicado, em silencio"
    )


def test_configured_fingerprint_becomes_script_default(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _inject_ca_fingerprint(INSTALL_SH.read_text(encoding="utf-8"))

    assert f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{FP}}}"' in saida
    assert _CA_PIN_LINE not in saida


def test_the_environment_still_takes_precedence_over_the_injected(monkeypatch):
    """`${ATLANS_CA_SHA256:-<fp>}` preserva o override do operador."""
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _inject_ca_fingerprint(INSTALL_SH.read_text(encoding="utf-8"))
    assert "${ATLANS_CA_SHA256:-" in saida


@pytest.mark.parametrize("bruto,esperado", [
    ("AB:CD:" + "EF" * 29 + ":01", "abcd" + "ef" * 29 + "01"),
    ("  " + "A" * 64 + "\n", "a" * 64),
])
def test_normalization_accepts_both_tool_formats(bruto, esperado):
    """`step certificate fingerprint` gives plain hex; `openssl` gives it with ':'."""
    assert _normalize_fingerprint(bruto) == esperado


# ── DEGRADACAO ───────────────────────────────────────────────────────────────

def test_without_configuration_the_script_is_untouched(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", "")
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _inject_ca_fingerprint(original) == original


@pytest.mark.parametrize("invalido", ["abc", "z" * 64, "a" * 63])
def test_invalid_fingerprint_is_not_injected(monkeypatch, invalido):
    """Injecting garbage would make EVERY installer abort on an impossible comparison."""
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", invalido)
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _inject_ca_fingerprint(original) == original


def test_script_without_the_expected_line_does_not_break(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    assert _inject_ca_fingerprint("#!/bin/bash\necho oi\n") == "#!/bin/bash\necho oi\n"


def test_the_script_stays_syntactically_valid_after_injection(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _inject_ca_fingerprint(INSTALL_SH.read_text(encoding="utf-8"))

    proc = subprocess.run(["bash", "-n"], input=saida, text=True, capture_output=True)
    assert proc.returncode == 0, f"install.sh injetado nao e bash valido:\n{proc.stderr}"


# ── EXECUTION ────────────────────────────────────────────────────────────────
#
# Cuts the verification block out of install.sh and actually runs it, against a
# cert generated on the spot. Without this, a normalization error (leftover ':',
# uppercase hex, `cut` on the wrong field) would pass every test above and
# break every enrollment in production.

_BLOCO = """
set -euo pipefail
err()  { printf "ERR %s\\n" "$*" >&2; }
warn() { printf "WARN %s\\n" "$*"; }
ok()   { printf "OK %s\\n" "$*"; }
die()  { err "$*"; exit 1; }
CA_SHA256_PIN="${PIN}"
if [[ -n "$CA_SHA256_PIN" ]]; then
    _esperados=$(printf '%s' "$CA_SHA256_PIN" | tr 'A-Z' 'a-z' | tr -d ': ' | tr ',;' '\\n\\n')
    _tmp_split=$(mktemp -d)
    awk -v d="$_tmp_split" '
        /-----BEGIN( TRUSTED| X509)? CERTIFICATE-----/ { n++; f = sprintf("%s/c%03d.pem", d, n) }
        n { print > f }
    ' "$CERT"
    _blocos=$(find "$_tmp_split" -name 'c*.pem' | wc -l | tr -d '[:space:]')
    if [[ "$_blocos" -eq 0 ]]; then
        rm -rf "$_tmp_split"; die "sem cert"
    fi
    _intrusos=""
    for _bloco in "$_tmp_split"/c*.pem; do
        sed -e 's/TRUSTED CERTIFICATE/CERTIFICATE/g; s/X509 CERTIFICATE/CERTIFICATE/g' \\
            "$_bloco" > "$_bloco.norm"
        _fp=$(openssl x509 -in "$_bloco.norm" -noout -fingerprint -sha256 2>/dev/null \\
            | cut -d= -f2 | tr 'A-Z' 'a-z' | tr -d ': ' || true)
        if [[ -z "$_fp" ]] || ! printf '%s\\n' "$_esperados" | grep -qx "$_fp"; then
            _intrusos="$_intrusos ${_fp:-<bloco-ilegivel>}"
        fi
    done
    rm -rf "$_tmp_split"
    if [[ -n "$_intrusos" ]]; then
        die "MISMATCH intrusos=$_intrusos"
    fi
    ok "conferido $_blocos"
else
    warn "sem pin"
fi
"""


@pytest.fixture
def cert(tmp_path):
    """Gera um self-signed e devolve (caminho, fingerprint sha256 hex)."""
    if not shutil.which("openssl"):
        pytest.skip("openssl ausente")
    caminho = tmp_path / "root.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "k.pem"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=teste"],
        check=True, capture_output=True,
    )
    saida = subprocess.run(
        ["openssl", "x509", "-in", str(caminho), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout
    fp = saida.split("=", 1)[1].strip().replace(":", "").lower()
    return caminho, fp


def _run(cert_path, pin):
    return subprocess.run(
        ["bash", "-c", textwrap.dedent(_BLOCO)],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "CERT": str(cert_path), "PIN": pin},
        capture_output=True, text=True, timeout=60,
    )


def test_correct_cert_passes_verification(cert):
    caminho, fp = cert
    r = _run(caminho, fp)
    assert r.returncode == 0, r.stderr
    assert "OK conferido" in r.stdout


def test_fingerprint_with_colons_and_uppercase_also_passes(cert):
    """O operador cola o que a ferramenta dele imprimiu."""
    caminho, fp = cert
    with_colons = ":".join(fp[i:i + 2] for i in range(0, len(fp), 2)).upper()
    assert _run(caminho, with_colons).returncode == 0


def test_wrong_cert_aborts_the_install(cert):
    """A propriedade central: CA trocada nao passa."""
    caminho, _ = cert
    r = _run(caminho, "b" * 64)
    assert r.returncode != 0
    assert "MISMATCH" in r.stderr


def test_without_pin_the_installer_warns_and_proceeds(cert):
    """Old behavior preserved for a server without the variable."""
    caminho, _ = cert
    r = _run(caminho, "")
    assert r.returncode == 0
    assert "WARN sem pin" in r.stdout


# ── PERSISTENCE ──────────────────────────────────────────────────────────────
#
# Where the pin actually takes effect on every boot.
#
# `_ca_bootstrap.bootstrap_ca()` returns early when `SSL_CERT_FILE` is already
# set — and the enrollment container sets it, pointing at the cert the shell
# already verified. So the `-e ATLANS_CA_SHA256` of that command is inert, and
# the "on every boot" verification only exists if the value reaches the
# long-running service, which does NOT set SSL_CERT_FILE. The path for that is
# `executor/.env`.

def _persistence_block() -> str:
    """The install.sh snippet that writes the pin to executor/.env.

    Delimited by stable markers instead of slicing by offset: the previous
    version took the 600 characters before a string and broke as soon as a
    comment was added above it.
    """
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    inicio = fonte.index("Persists the fingerprint in the executor's .env")
    fim = fonte.index("chmod 660 executor/.env", inicio)
    return fonte[inicio:fim]


def test_the_installer_writes_the_pin_to_the_executor_env():
    bloco = _persistence_block()
    assert "ATLANS_CA_SHA256=" in bloco, (
        "o instalador nao persiste o pin em executor/.env — sem isso o servico "
        "de longa duracao nunca reconfere a CA"
    )
    # The write must be conditional: with no published pin, nothing to write.
    assert 'if [[ -n "$CA_SHA256_PIN" ]]' in bloco, (
        "a gravacao no .env precisa ser condicional ao pin existir"
    )


def test_the_stored_pin_is_normalized():
    """The .env is read by `_expected_pins()`, which expects lowercase hex."""
    bloco = _persistence_block()
    assert "tr 'A-Z' 'a-z'" in bloco and "tr -d ': '" in bloco, (
        "o valor gravado no .env precisa da mesma normalizacao da comparacao"
    )


def test_writing_twice_does_not_duplicate_the_key():
    """Running the installer again (--force) must not leave two lines."""
    bloco = _persistence_block()
    assert "grep -qE '^[[:space:]]*(export[[:space:]]+)?ATLANS_CA_SHA256='" in bloco, (
        "sem checar a existencia (inclusive com `export`), um segundo run "
        "acrescenta uma linha duplicada"
    )


def test_the_doc_does_not_promise_verification_in_the_enrollment_container():
    """The docs once claimed a layer that does not run; they must not claim it again."""
    doc = (RAIZ / "docs" / "mtls-bootstrap.md").read_text(encoding="utf-8")
    assert "SSL_CERT_FILE" in doc, (
        "a doc precisa explicar por que o container de enrollment nao reverifica"
    )
    assert "bootstrap_ca()" in doc


# ── REUSE ────────────────────────────────────────────────────────────────────
#
# The pin must hold on the REUSE path, not only on download.
#
# `bootstrap_ca()` reuses `atlans-root.crt` when it already exists in cert_dir —
# which is a volume. The pin was only checked inside `_download_atomic`, so the
# verification happened ONCE, on the first boot that downloaded the bundle.
# Swapping the file in the volume and restarting installed the attacker's CA as
# a trust anchor, without any warning.

_TRUST_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "ATLANS_CA_SHA256")


@pytest.fixture(autouse=True)
def _clean_trust_env():
    """Isolates the trust store env vars, on entry AND on exit.

    monkeypatch is not enough: `_set_env` writes to os.environ directly, and
    `monkeypatch.delenv(..., raising=False)` records nothing when the key is
    absent — the three vars would leak into the following tests pointing at a
    bundle in an already deleted tmp_path. Same reason (and same shape) as the
    autouse fixture in tests/unit/test_ca_bundle_trust_store.py.
    """
    import os as _os
    antes = {v: _os.environ.get(v) for v in _TRUST_VARS}
    for v in _TRUST_VARS:
        _os.environ.pop(v, None)
    yield
    for v, valor in antes.items():
        if valor is None:
            _os.environ.pop(v, None)
        else:
            _os.environ[v] = valor


@pytest.fixture
def cert_dir(tmp_path, monkeypatch):
    """Simulates the executor's volume, with a root cert already installed."""
    if not shutil.which("openssl"):
        pytest.skip("openssl ausente")
    d = tmp_path / "certs"
    d.mkdir()
    caminho = d / "atlans-root.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "k.pem"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=atlans-teste"],
        check=True, capture_output=True,
    )
    saida = subprocess.run(
        ["openssl", "x509", "-in", str(caminho), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout
    fp = saida.split("=", 1)[1].strip().replace(":", "").lower()

    monkeypatch.setenv("EXECUTOR_CERT_DIR", str(d))
    # `_expected_pin` falls back to `.env` when the env var does not exist; point it
    # at an empty file so the test controls both sources.
    (tmp_path / "vazio.env").write_text("", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(tmp_path / "vazio.env"))
    return caminho, fp


def test_reuse_with_correct_pin_proceeds_normally(cert_dir, monkeypatch):
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    _ca_bootstrap.bootstrap_ca()

    import os
    assert os.environ.get("SSL_CERT_FILE"), "o trust store deveria ter sido montado"


def test_cert_SWAPPED_in_the_volume_stops_the_boot(cert_dir, monkeypatch):
    """The security regression: file swap + restart must not get through."""
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    # O pin continua sendo o do cert legitimo...
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)
    # ...but someone swapped the file in the volume.
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "atacante.key"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )

    with pytest.raises(Exception) as exc:
        _ca_bootstrap.bootstrap_ca()
    assert "ATLANS_CA_SHA256" in str(exc.value) or "casa" in str(exc.value).lower()


def test_without_pin_reuse_works_as_before(cert_dir, monkeypatch):
    """Whoever has not configured pinning must not have their boot broken by this."""
    from executor import _ca_bootstrap

    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    _ca_bootstrap.bootstrap_ca()

    import os
    assert os.environ.get("SSL_CERT_FILE")


def test_APPENDING_a_CA_to_the_bundle_is_also_blocked(cert_dir, monkeypatch):
    """The hole that "some cert matches" let through.

    `_set_env` concatenates the whole file with the public CAs and publishes the
    result in SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE — EVERY cert in it
    becomes a trust anchor. With the loose check, an attacker did not need to
    REPLACE the root: it was enough to APPEND their own CA to the file. The pin
    matched the legitimate cert, the verification passed, and the extra CA got
    into the trust store silently.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    # Legitimate root PRESERVED; the attacker's CA comes after, in the same file.
    intruso = caminho.parent / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "intruso.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    caminho.write_bytes(caminho.read_bytes() + b"\n" + intruso.read_bytes())

    with pytest.raises(Exception) as exc:
        _ca_bootstrap.bootstrap_ca()
    assert "acrescimo" in str(exc.value).lower() or "encontrado" in str(exc.value).lower()


def test_pin_from_the_env_file_is_honored(cert_dir, monkeypatch, tmp_path):
    """`bootstrap_ca` runs BEFORE the load_dotenv of executor/config.py.

    In compose the variable arrives through the container's `env_file` and this
    does not show; in the native and desktop flows, the pin the installer writes
    to `executor/.env` was invisible — the bootstrap fell into the "no pin" branch
    and checked nothing, contrary to what the docs promise.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    env = tmp_path / "com-pin.env"
    env.write_text(f"# comentario\nOUTRA=coisa\nATLANS_CA_SHA256={fp}\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})

    # And the pin from .env actually blocks a swapped cert.
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "outro.key"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=outro"],
        check=True, capture_output=True,
    )
    with pytest.raises(Exception):
        _ca_bootstrap.bootstrap_ca()


def test_environment_takes_precedence_over_the_env_file(cert_dir, monkeypatch, tmp_path):
    from executor import _ca_bootstrap

    env = tmp_path / "com-pin.env"
    env.write_text("ATLANS_CA_SHA256=" + "b" * 64 + "\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))
    monkeypatch.setenv("ATLANS_CA_SHA256", "a" * 64)

    assert _ca_bootstrap._expected_pins() == frozenset({"a" * 64})


def test_ERROR_emit_reaches_the_logger(caplog):
    """The pin-mismatch message fell into `debug` and vanished from the persisted log."""
    import logging
    from executor import _ca_bootstrap

    with caplog.at_level(logging.ERROR, logger="executor.ca_bootstrap"):
        _ca_bootstrap._emit("ERROR", "pin divergente de teste")

    assert any(r.levelno == logging.ERROR for r in caplog.records), (
        "_emit('ERROR') precisa chegar ao logger como ERROR"
    )


def test_multiple_pins_allow_overlapping_rotation(cert_dir, monkeypatch, tmp_path):
    """The strict pin must not prevent a CA rotation.

    During rotation the bundle legitimately carries the old root AND the new one.
    With a single pin and the "all match" check, the executor would not boot until
    someone TURNED OFF pinning — the opposite of the intended outcome.
    """
    from executor import _ca_bootstrap

    caminho, old_fp = cert_dir

    novo = caminho.parent / "novo.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "novo.key"), "-out", str(novo),
         "-days", "1", "-subj", "/CN=atlans-novo"],
        check=True, capture_output=True,
    )
    new_fp = subprocess.run(
        ["openssl", "x509", "-in", str(novo), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout.split("=", 1)[1].strip().replace(":", "").lower()

    # Overlap bundle: both roots.
    caminho.write_bytes(caminho.read_bytes() + b"\n" + novo.read_bytes())
    monkeypatch.setenv("ATLANS_CA_SHA256", f"{old_fp},{new_fp}")

    _ca_bootstrap.bootstrap_ca()  # does not raise

    import os
    assert os.environ.get("SSL_CERT_FILE")


def test_TRUSTED_CERTIFICATE_label_is_also_counted(cert_dir, monkeypatch):
    """`CERTIFICATE` is not the only label OpenSSL loads as an anchor.

    Recognizing only that one let the append check be bypassed by changing the
    label of the intruding block.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    intruso = caminho.parent / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "i.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    disguised = intruso.read_bytes() \
        .replace(b"BEGIN CERTIFICATE", b"BEGIN TRUSTED CERTIFICATE") \
        .replace(b"END CERTIFICATE", b"END TRUSTED CERTIFICATE")
    caminho.write_bytes(caminho.read_bytes() + b"\n" + disguised)

    with pytest.raises(Exception):
        _ca_bootstrap.bootstrap_ca()


def test_pin_with_inline_comment_does_not_break_the_boot(cert_dir, monkeypatch, tmp_path):
    """`.env` escrito a mao costuma ter comentario na mesma linha."""
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    env = tmp_path / "com-comentario.env"
    env.write_text(f"export ATLANS_CA_SHA256={fp}  # root de producao\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})


def test_the_isolation_fixture_does_not_wipe_the_developer_env(monkeypatch):
    """Fixture order regression.

    Requested by `cert_dir`, `_clean_trust_env` was created AFTER monkeypatch and
    restored BEFORE its teardown — and monkeypatch, which had recorded "absent"
    for a var the fixture had already removed, then deleted the real value.
    Autouse inverts the order.
    """
    import os
    assert os.environ.get("SSL_CERT_FILE") is None, (
        "a fixture autouse deveria ter limpado a var para este teste"
    )


def test_installer_rejects_bundle_with_APPENDED_CA(cert, tmp_path):
    """The same hole on the executor side, now in the shell.

    `openssl x509 -in <arquivo>` reads only the FIRST PEM block. The whole file
    becomes the trust store, so [root_legitimo, ca_do_atacante] passed the
    installation check — and became the SSL_CERT_FILE of the enrollment
    container, which carries the OTP and generates the mTLS cert's key.
    """
    caminho, fp = cert
    intruso = tmp_path / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "i.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + intruso.read_bytes())

    r = _run(juntos, fp)
    assert r.returncode != 0, "bundle com CA acrescentada nao pode passar"
    assert "MISMATCH" in r.stderr


def test_installer_accepts_rotation_bundle_with_two_pins(cert, tmp_path):
    caminho, fp = cert
    novo = tmp_path / "novo.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "n.key"), "-out", str(novo),
         "-days", "1", "-subj", "/CN=atlans-novo"],
        check=True, capture_output=True,
    )
    new_fp = subprocess.run(
        ["openssl", "x509", "-in", str(novo), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout.split("=", 1)[1].strip().replace(":", "").lower()

    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + novo.read_bytes())

    r = _run(juntos, f"{fp},{new_fp}")
    assert r.returncode == 0, r.stderr
    assert "OK conferido 2" in r.stdout


def test_installer_counts_block_with_TRUSTED_label(cert, tmp_path):
    caminho, fp = cert
    intruso = tmp_path / "i.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "i2.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    disguised = intruso.read_bytes() \
        .replace(b"BEGIN CERTIFICATE", b"BEGIN TRUSTED CERTIFICATE") \
        .replace(b"END CERTIFICATE", b"END TRUSTED CERTIFICATE")
    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + disguised)

    assert _run(juntos, fp).returncode != 0


# ── Edge cases found in the fifth review ─────────────────────────────────────

def test_unreadable_block_counts_as_intruder_and_does_not_kill_the_script(cert, tmp_path):
    """Under `set -euo pipefail`, a failing openssl aborted the script HERE.

    The intruder branch — and with it the bundle's `rm -f` — never ran: the
    attacker's file stayed on disk and the installer died with "Falha na etapa:
    cabundle", without saying why.
    """
    caminho, fp = cert
    quebrado = tmp_path / "quebrado.crt"
    quebrado.write_bytes(
        caminho.read_bytes()
        + b"\n-----BEGIN CERTIFICATE-----\nnao-e-base64-valido\n-----END CERTIFICATE-----\n"
    )

    r = _run(quebrado, fp)
    assert r.returncode != 0
    assert "MISMATCH" in r.stderr, (
        f"esperado o ramo de intruso, veio: {r.stderr[:200]!r}"
    )


def test_block_count_without_padding():
    """BSD/macOS `wc -l` pads with spaces — the installer already targets macOS.

    Running the real block tests nothing here: Linux's GNU `wc` does not pad, so
    the assertion would pass with or without the `tr` it claims to protect. The
    test simulates the BSD output (`       2`) and checks that the normalization
    cleans it.
    """
    r = subprocess.run(
        ["bash", "-c", "_b=$(printf '       2\n' | tr -d '[:space:]'); printf 'conferido %s' \"$_b\""],
        capture_output=True, text=True, timeout=30,
    )
    assert r.stdout == "conferido 2", repr(r.stdout)

    # And the delivered install.sh actually uses the normalization.
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    assert "wc -l | tr -d '[:space:]'" in fonte


def test_server_injects_multi_pin_value(monkeypatch):
    """The docs prescribe `<fp_antigo>,<new_fp>` during rotation.

    The length validation rejected the whole value (129 chars) and the script
    exited WITHOUT pinning — pure TOFU exactly in the window when the CA is changing.
    """
    dois = f"{'a' * 64},{'b' * 64}"
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", dois)
    saida = _inject_ca_fingerprint(INSTALL_SH.read_text(encoding="utf-8"))
    assert f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{dois}}}"' in saida


def test_multi_pin_with_one_invalid_entry_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.STEPCA_ROOT_FINGERPRINT", f"{'a' * 64},nao-e-hex",
    )
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _inject_ca_fingerprint(original) == original


def test_multi_pin_normalization():
    assert _normalize_fingerprint(f"AB:{'CD' * 31}:EF, {'a' * 64}") == \
        f"ab{'cd' * 31}ef,{'a' * 64}"


def test_EMPTY_env_var_does_not_shadow_the_env_file_pin(cert_dir, monkeypatch, tmp_path):
    """`ATLANS_CA_SHA256=` with no value is common in compose.

    With `if bruto is None`, it shadowed the pin from .env and turned off
    pinning without any warning.
    """
    from executor import _ca_bootstrap

    _, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", "")
    env = tmp_path / "com-pin.env"
    env.write_text(f"ATLANS_CA_SHA256={fp}\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})


def test_remove_env_var_matches_the_SAME_line_as_read_env_var(tmp_path):
    """The tolerance for `export` had been added only to the read.

    `remove_env_var` stopped matching the line the read reported, and the legacy
    variable migration (enrollment.py) became a silent no-op.
    """
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export LEGADO=valor\nOUTRA=x\n", encoding="utf-8")

    assert _env_utils.read_env_var("LEGADO", env) == "valor"
    assert _env_utils.remove_env_var("LEGADO", env) is True
    assert _env_utils.read_env_var("LEGADO", env) is None


def test_persist_env_var_updates_line_with_export(tmp_path):
    """Without this, persist APPENDED a second line, and the read (first
    occurrence wins) kept returning the old value."""
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export CHAVE=antigo\n", encoding="utf-8")

    _env_utils.persist_env_var("CHAVE", "novo", env)

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.count("CHAVE") == 1, f"linha duplicada: {conteudo!r}"
    assert _env_utils.read_env_var("CHAVE", env) == "novo"


def test_the_test_executable_block_has_not_diverged_from_install_sh():
    """`_BLOCO` is a COPY of the install.sh verification snippet.

    The copy exists so the real shell can be run against real certs — which
    has already caught three bugs no string test would catch. The price is
    keeping them in sync, and that has already broken once: the `|| true` went
    into install.sh and not into the copy, and the unreadable-block test started
    exercising the old version.

    This test locks the points that matter. It does not compare character by
    character: `_BLOCO` is deliberately reduced (no `rm -f`, no long messages).
    """
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    for marca in (
        "|| true",                                   # bloco ilegivel nao mata o script
        "tr -d '[:space:]'",                         # BSD wc -l
        "tr ',;' '\\n\\n'",                          # multi-pin
        "BEGIN( TRUSTED| X509)? CERTIFICATE",        # alternative labels in awk
        "s/TRUSTED CERTIFICATE/CERTIFICATE/g",       # normalization before openssl
        "grep -qx",                                  # exact fingerprint match
    ):
        assert marca in fonte, f"install.sh perdeu: {marca!r}"
        assert marca in _BLOCO, (
            f"_BLOCO divergiu do install.sh — falta {marca!r}. "
            "O teste passaria exercitando um shell que nao e o entregue."
        )


def test_installer_UPDATES_line_with_export_instead_of_duplicating(tmp_path):
    """CA rotation started refusing the boot right after the installer ran.

    install.sh's .env writer only matched `^ATLANS_CA_SHA256=`. With a line
    `export ATLANS_CA_SHA256=<antigo>`, it APPENDED the new value instead of
    replacing it — and `read_env_var` returns the FIRST occurrence, so the
    executor kept pinning the old CA.
    """
    env = tmp_path / ".env"
    env.write_text("export ATLANS_CA_SHA256=" + "a" * 64 + "\nOUTRA=x\n", encoding="utf-8")
    novo = "b" * 64

    trecho = r'''
set -euo pipefail
_pin_normalizado="$NOVO"
cd "$DIR"
if grep -qE '^[[:space:]]*(export[[:space:]]+)?ATLANS_CA_SHA256=' .env 2>/dev/null; then
    sed -i.bak -E "s|^([[:space:]]*(export[[:space:]]+)?)ATLANS_CA_SHA256=.*|\1ATLANS_CA_SHA256=${_pin_normalizado}|" .env
    rm -f .env.bak
else
    printf 'ATLANS_CA_SHA256=%s\n' "$_pin_normalizado" >> .env
fi
'''
    r = subprocess.run(
        ["bash", "-c", trecho],
        env={"PATH": "/usr/bin:/bin", "DIR": str(tmp_path), "NOVO": novo},
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.count("ATLANS_CA_SHA256") == 1, f"linha duplicada: {conteudo!r}"
    assert "export ATLANS_CA_SHA256=" + novo in conteudo, (
        f"o `export` tem de ser preservado: {conteudo!r}"
    )

    from executor import _env_utils
    assert _env_utils.read_env_var("ATLANS_CA_SHA256", env) == novo


def test_persist_env_var_preserves_the_export(tmp_path):
    """In a `source`d .env, losing the `export` makes the variable stop reaching
    child processes."""
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export CHAVE=antigo\n", encoding="utf-8")

    _env_utils.persist_env_var("CHAVE", "novo", env)

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.strip() == "export CHAVE=novo", repr(conteudo)
