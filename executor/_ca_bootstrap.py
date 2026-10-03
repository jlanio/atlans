"""
Auto-bootstrap of the atlans internal CA root cert.

Running `python -m executor` in a fresh environment (no `SSL_CERT_FILE` set
and no local `atlans-root.crt`) currently breaks with CERTIFICATE_VERIFY_FAILED
— the executors' host cert (`agents.<dominio>`) is issued by the internal step-ca, which
is not in the system trust store. The Docker flow's `install.sh` solves
this automatically; this module does the same in the native Python flow.

The trust store published in the env vars is a COMBINED bundle — public CAs
(certifi) PLUS the internal CA —, never the internal CA alone: SSL_CERT_FILE
replaces the process trust store instead of adding to it, and pointing it only
at the internal CA broke every HTTPS access to public servers made by workflow
nodes (WFS, WMS, APIs) with `unable to get local issuer certificate`.

Idempotent: if the cert already exists at `<EXECUTOR_CERT_DIR>/atlans-root.crt`,
it only rebuilds the bundle and sets the env vars. If `SSL_CERT_FILE` is already set
externally, it is respected and left alone. Download failures persist NOTHING:
the bootstrap aborts with manual installation instructions and the executor keeps
its pre-existing behavior (which will probably fail with
CERTIFICATE_VERIFY_FAILED, telling the operator exactly what is missing).

SECURITY: the material downloaded here becomes the host's TRUST ANCHOR —
it covers the enroll OTP, the mTLS cert's Ed25519 key and every future job.
That is why the download only happens over verified TLS. The only escape
for environments with a corporate SSL inspector is explicit pinning by
fingerprint (`ATLANS_CA_SHA256`), which validates the material AFTER the download.
There is never a "trust anything" path: an `http://` URL
(coming from `--server=ws://...` or from EXECUTOR_PUBLIC_SERVER_URL) is also
refused, because there is no chain at all to verify there — only the fingerprint
pin unlocks that case.

Zero transitive dependencies: uses only the stdlib. Does NOT import
`executor.config` (which requires `EXECUTOR_ID` — it would break on the 1st boot before
enroll) nor `executor.utils.logger` (which loads the custom formatter
before the env is ready).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

_logger = logging.getLogger("executor.ca_bootstrap")


def _emit(level: str, msg: str) -> None:
    """Writes to stderr directly — the root logger may not have a handler yet
    when the bootstrap runs (before executor.main is imported)."""
    print(f"[ca-bootstrap] {level}: {msg}", file=sys.stderr, flush=True)
    if level == "ERROR":
        _logger.error(msg)
    elif level == "WARNING":
        _logger.warning(msg)
    elif level == "INFO":
        _logger.info(msg)
    else:
        _logger.debug(msg)

_CERT_FILENAME = "atlans-root.crt"
# Effective trust store of the process: public CAs + internal CA. Derived, never
# edited by hand — rewritten on each boot when it changes. See _ensure_combined_bundle.
_BUNDLE_FILENAME = "atlans-ca-bundle.crt"
_CA_BUNDLE_PATH = "/executores/ca-bundle"
_DOWNLOAD_TIMEOUT_SEC = 15

# Optional pinning: SHA-256 (hex) of the expected root cert, as output by
# `openssl x509 -in atlans-root.crt -noout -fingerprint -sha256`. Accepted with
# or without the `:`. When set, the downloaded material is validated against it — and
# only in that case can the TLS chain verification be skipped (the operator
# has already proven they know what to expect). Without it, verified TLS is the only way.
_PIN_ENV = "ATLANS_CA_SHA256"

# The executors' host (agents.<dominio>) uses a cert from the internal step-ca — the
# download of the CA bundle from it would itself break with CERT_VERIFY_FAILED
# (circular). install.sh works around this by downloading from the root domain (public cert).
# We replicate it here: if the server starts with `agents.`, we use `<dominio>` for the
# download. EXECUTOR_PUBLIC_SERVER_URL allows a manual override when the
# convention does not apply.
_MTLS_SUBDOMAIN_PREFIX = "agents."


def bootstrap_ca() -> None:
    """Ensures a trust store that covers the internal CA AND the public CAs.

    Called as the FIRST line of `executor/__main__.main()`. At that
    point no executor module has been imported besides the stdlib of
    __main__ — setting env here is seen by every httpx.SSLContext
    created in the subcommands (default/enroll/status).
    """
    # 1) An explicit operator override wins — leave it alone.
    if os.environ.get("SSL_CERT_FILE"):
        _emit(
            "INFO",
            f"SSL_CERT_FILE ja setado externamente: {os.environ['SSL_CERT_FILE']} "
            "— o bootstrap nao toca. Esse arquivo SUBSTITUI o trust store do processo: "
            "se ele contiver so a CA interna, os nos de workflow falham ao acessar "
            "qualquer servidor HTTPS publico.",
        )
        return

    cert_dir = Path(os.getenv("EXECUTOR_CERT_DIR") or "./certs")
    cert_path = cert_dir / _CERT_FILENAME

    # 2) Cert already exists (Docker with install.sh, or a subsequent boot) — reuse it.
    if cert_path.is_file() and cert_path.stat().st_size > 0:
        # If the operator configured a pin, it applies HERE TOO, and not only on
        # download. The file lives in a volume: replacing `atlans-root.crt` with
        # another one and restarting the container installed the attacker's CA as a
        # trust anchor, silently — the pin was checked exactly once,
        # on the first boot that downloaded the bundle, and never again.
        #
        # Fail CLOSED: whoever configured the pin opted into it. A rotated CA
        # with an old pin in .env stops the boot, and the message says what to do — which
        # is the right outcome for a trust control.
        try:
            pins = _expected_pins()
        except ValueError as exc:
            _emit("ERROR", str(exc))
            raise
        if pins:
            # A single read, and the combined bundle is built from THESE
            # bytes. Reading the file here and letting `_set_env` read it again would open
            # a window to swap the content between the check and the use —
            # against exactly the attacker this check exists to stop.
            material = cert_path.read_bytes()
            try:
                _assert_pinned(material, pins)
            except Exception as exc:
                _emit(
                    "ERROR",
                    f"Root cert existente em {cert_path.resolve()} NAO casa com "
                    f"{_PIN_ENV}: {exc} "
                    "Se a CA foi rotacionada, acrescente o novo fingerprint a "
                    f"{_PIN_ENV} (aceita varios, separados por virgula) ou apague "
                    "o arquivo para baixar de novo.",
                )
                raise
            _emit("INFO", f"Root cert reutilizado e conferido contra {_PIN_ENV}.")
            _set_env(cert_path, material=material)
            return
        _emit("INFO", f"Root cert reutilizado: {cert_path.resolve()}")
        _set_env(cert_path)
        return

    # 3) Cert ausente — tenta baixar.
    server_url = _resolve_server_url()
    if not server_url:
        # Without a server there is nowhere to download from: no default pointing at an
        # installation nobody chose. Enroll brings the --server.
        _emit(
            "WARNING",
            "Root cert da CA interna ausente e nenhum servidor configurado "
            "(EXECUTOR_SERVER_URL, --server ou EXECUTOR_PUBLIC_SERVER_URL): "
            "nada foi baixado.",
        )
        return
    bundle_url = server_url.rstrip("/") + _CA_BUNDLE_PATH

    try:
        cert_dir.mkdir(parents=True, exist_ok=True)
        _download_atomic(bundle_url, cert_path)
    except Exception as exc:
        # ABORTS without persisting anything. There is no unverified fallback: the
        # file would become the host's permanent trust anchor, and an on-path
        # attacker would only need to corrupt the handshake to force the downgrade.
        _emit(
            "WARNING",
            f"Nao foi possivel baixar root cert de {bundle_url}: "
            f"{type(exc).__name__}: {exc}. "
            f"Nada foi gravado — instale o root cert manualmente:\n"
            f"    curl -o {cert_path} {bundle_url}\n"
            f"  (basta o arquivo no lugar; no proximo boot o bootstrap monta o trust\n"
            f"   store combinado. NAO exporte SSL_CERT_FILE apontando so para ele —\n"
            f"   isso substitui as CAs publicas e quebra os nos que acessam HTTPS.)\n"
            f"  Confira o fingerprint com o admin do Atlans:\n"
            f"    openssl x509 -in {cert_path} -noout -fingerprint -sha256\n"
            f"  Em rede com inspetor SSL corporativo, exporte {_PIN_ENV}=<sha256 esperado> "
            f"e rode de novo — o download e validado contra o fingerprint.",
        )
        return

    _set_env(cert_path)
    _emit("INFO", f"Root cert baixado em {cert_path}")


# ── Helpers ─────────────────────────────────────────────────────────────

def _set_env(cert_path: Path, material: bytes | None = None) -> None:
    """Points the trust store env vars at the COMBINED bundle (public CAs
    + internal CA) — never at the internal root cert alone.

    Setting SSL_CERT_FILE REPLACES the process trust store, it does not add. Pointing
    only at the internal CA, all outbound HTTPS to public servers broke with
    `unable to get local issuer certificate` — including inside workflow
    nodes (WFS/WMS via owslib+requests, GDAL/pyogrio, boto3). The executor
    worked around it case by case in its own code (`utils.build_mtls_ssl_context`,
    `enrollment._resolve_enroll_verify`), but third-party libraries read the env var
    directly and cannot be worked around; the fix has to be here.

    The three env vars cover different stacks: SSL_CERT_FILE (stdlib ssl, httpx),
    REQUESTS_CA_BUNDLE (requests/urllib3) and CURL_CA_BUNDLE (libcurl — GDAL,
    pyogrio and the /vsicurl drivers ignore the other two).
    """
    p = str(_ensure_combined_bundle(cert_path, material=material))
    os.environ["SSL_CERT_FILE"] = p
    os.environ["REQUESTS_CA_BUNDLE"] = p
    os.environ["CURL_CA_BUNDLE"] = p


def _public_ca_pem() -> tuple[bytes | None, str]:
    """PEM of the public CAs: certifi (an executor dependency), otherwise the OS cafile.

    `ssl.get_default_verify_paths()` honors SSL_CERT_FILE, but here it has not yet
    been set by us — `bootstrap_ca` returns early when the operator already set it —
    so the cafile read really is the system one, with no risk of self-reference.
    """
    try:
        import certifi  # type: ignore
        return Path(certifi.where()).read_bytes(), "certifi"
    except Exception:
        pass

    paths = ssl.get_default_verify_paths()
    for candidate in (paths.cafile, paths.openssl_cafile):
        if candidate and os.path.isfile(candidate):
            try:
                return Path(candidate).read_bytes(), candidate
            except OSError:
                continue
    return None, "none"


def _ensure_combined_bundle(root_cert: Path, material: bytes | None = None) -> Path:
    """Writes (idempotently) `<dir>/atlans-ca-bundle.crt` = public CAs + internal CA.

    Returns the bundle path. On any failure it returns `root_cert` itself:
    the executor keeps talking to the executors' host (which is what makes it
    usable), and the WARNING explains why public HTTPS will fail.

    The certs directory may be mounted read-only (the compose offers
    `./executor-certs:/data/certs:ro`), hence the fallback to the tmpdir — the
    bundle is derived and only needs to survive the process.
    """
    if material is not None:
        # Bytes ALREADY verified against the pin by the caller. Re-reading the file here
        # would open a window between the check and the use.
        internal_pem = material.strip()
    else:
        try:
            internal_pem = root_cert.read_bytes().strip()
        except OSError as exc:
            _emit("WARNING", f"Nao foi possivel ler o root cert {root_cert}: {exc}")
            return root_cert.resolve()

    public_pem, source = _public_ca_pem()
    if public_pem is None:
        _emit(
            "WARNING",
            "Nenhum bundle de CAs publicas encontrado (certifi ausente e sistema sem "
            "cafile). O trust store fica so com a CA interna, e toda conexao HTTPS para "
            "servidor publico vai falhar com 'unable to get local issuer certificate' — "
            "incluindo nos de workflow (WFS, WMS, APIs). Instale: pip install certifi",
        )
        return root_cert.resolve()

    payload = public_pem.rstrip() + b"\n" + internal_pem + b"\n"

    last_exc: OSError | None = None
    for target_dir in (root_cert.parent, Path(tempfile.gettempdir())):
        bundle = target_dir / _BUNDLE_FILENAME
        try:
            # Rewrites only when the content changes (root cert renewed, certifi
            # updated in a new image) — a normal boot does not touch the disk.
            if not (bundle.is_file() and bundle.read_bytes() == payload):
                tmp = bundle.with_suffix(bundle.suffix + ".tmp")
                tmp.write_bytes(payload)
                os.replace(tmp, bundle)
                _emit("INFO", f"Trust store combinado ({source} + CA interna): {bundle}")
            return bundle.resolve()
        except OSError as exc:
            last_exc = exc

    _emit(
        "WARNING",
        f"Nao foi possivel gravar o trust store combinado ({last_exc}). Usando so a CA "
        "interna — HTTPS para servidores publicos vai falhar com 'unable to get local "
        "issuer certificate'.",
    )
    return root_cert.resolve()


def _do_env_do_executor(nome: str) -> str:
    """The value in `executor/.env` (`_env_utils.read_env_var`, pure stdlib), without
    the quotes dotenv would strip; empty if there is none."""
    from executor._env_utils import read_env_var

    try:
        valor = (read_env_var(nome) or "").strip()
    except Exception:
        return ""
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1]
    return valor


def _resolve_server_url() -> str:
    """
    Resolves the URL for downloading the CA bundle.

    Priority order:
      1. EXECUTOR_PUBLIC_SERVER_URL from the env — explicit override when the
         agents.<dominio> convention does not apply.
      2. --server=<X> or --server <X> in argv (preferred for enroll),
         converted: agents.<dominio> -> <dominio>.
      3. EXECUTOR_SERVER_URL from the environment or, failing that, from `executor/.env`,
         same conversion. The `.env` for the reason given in `_expected_pins`: this
         bootstrap runs before the `load_dotenv()` in `executor/config.py`, and in the
         native executor (systemd, terminal) the server only exists in the file.
      4. None of the three: empty, and nothing is downloaded.

    Then converts wss:// -> https:// and ws:// -> http://. Done inline
    (without importing `executor.utils.ws_to_http`) so as not to load config.

    The conversion PRESERVES the `http://` of a `--server=ws://...` on purpose:
    the one that decides what to do with it is `_download_atomic`, which refuses to
    download the trust anchor over an unverified channel (unless ATLANS_CA_SHA256
    is set). Rewriting to https here would hide the problem behind a
    confusing connection error.
    """
    public_override = os.getenv("EXECUTOR_PUBLIC_SERVER_URL")
    if public_override:
        return public_override.replace("wss://", "https://").replace("ws://", "http://")

    from_argv = _parse_server_from_argv(sys.argv[1:])
    server = (from_argv or os.getenv("EXECUTOR_SERVER_URL") or _do_env_do_executor("EXECUTOR_SERVER_URL")).strip()
    if not server:
        return ""
    server = server.replace("wss://", "https://").replace("ws://", "http://")
    return _strip_mtls_subdomain(server)


def _strip_mtls_subdomain(url: str) -> str:
    """`https://agents.<dominio>` -> `https://<dominio>`. If the host does not
    start with `agents.`, returns it unchanged. Preserves scheme, path, port."""
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    host = parts.hostname or ""
    if not host.startswith(_MTLS_SUBDOMAIN_PREFIX):
        return url
    new_host = host[len(_MTLS_SUBDOMAIN_PREFIX):]
    # Preserve the port if there is one
    netloc = new_host if not parts.port else f"{new_host}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _parse_server_from_argv(argv: list[str]) -> str | None:
    """Defensive parse — does not touch argv, does not use argparse (which
    would consume known args and break the __main__ dispatcher).
    Accepts the two common forms: `--server=URL` and `--server URL`.
    """
    for i, arg in enumerate(argv):
        if arg.startswith("--server="):
            return arg[len("--server="):]
        if arg == "--server" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _expected_pins() -> frozenset[str]:
    """Accepted SHA-256 fingerprints for the root cert, normalized.

    Sources, in this order: `ATLANS_CA_SHA256` in the environment, then in
    `executor/.env`. The `.env` matters because `bootstrap_ca()` is the FIRST line
    of `executor/__main__.main()` and runs BEFORE the `load_dotenv()` in
    `executor/config.py`: in compose the variable arrives through `env_file`, but in
    the native and desktop flows the pin written by the installer only exists in the file.

    The read uses `_env_utils.read_env_var`, the `.env` parser the executor already
    has (pure stdlib, used by enrollment). Having a second parser here was a
    mistake: the two diverged on the first review.

    Accepts SEVERAL comma-separated fingerprints. Without this, strict pinning
    made a CA rotation with overlap impossible — the period in which the
    bundle legitimately carries the old root AND the new one —, and the executor would
    not boot until someone turned pinning off, which is the opposite of the desired outcome.

    Returns an empty frozenset when no pin is configured.
    """
    from executor._env_utils import read_env_var

    # `or`, and not `is None`: an env var defined as EMPTY (common in compose,
    # `ATLANS_CA_SHA256=` with no value) shadowed the pin written in .env and turned
    # pinning off without any warning.
    bruto = os.environ.get(_PIN_ENV) or ""
    if not bruto.strip():
        try:
            bruto = read_env_var(_PIN_ENV) or ""
        except Exception:
            bruto = ""
    if not bruto.strip():
        return frozenset()

    # `export KEY=v` and inline comments are forms the operator writes by hand
    # and the shared parser does not handle; normalizing here avoids diverging from it.
    bruto = bruto.split("#", 1)[0]
    if bruto.lstrip().startswith("export "):
        bruto = bruto.lstrip()[len("export "):]

    pins = set()
    for parte in bruto.replace(";", ",").split(","):
        raw = parte.strip().strip('"').strip("'").replace(":", "").lower()
        if not raw:
            continue
        if len(raw) != 64 or any(c not in "0123456789abcdef" for c in raw):
            raise ValueError(
                f"{_PIN_ENV} invalido: esperado SHA-256 em hex (64 chars, `:` "
                f"opcional, varios separados por virgula), recebido {len(raw)} chars."
            )
        pins.add(raw)
    return frozenset(pins)


# `CERTIFICATE` is not the only label OpenSSL loads as an anchor:
# `TRUSTED CERTIFICATE` and `X509 CERTIFICATE` also go into
# `load_verify_locations`. Recognizing only the first let the
# addition check be bypassed by a block with another label.
_PEM_CERT_RE = re.compile(
    rb"-----BEGIN (?:TRUSTED |X509 )?CERTIFICATE-----"
    rb".*?"
    rb"-----END (?:TRUSTED |X509 )?CERTIFICATE-----",
    re.DOTALL,
)


def _pem_fingerprints(payload: bytes) -> list[str]:
    """SHA-256 (hex) of the DER of each cert in the downloaded PEM bundle.

    The fingerprint is computed over the DER, not over the raw bytes of the file —
    that is how `openssl x509 -fingerprint -sha256` computes it, so the operator
    compares against the value the admin passed, and differences in whitespace/CRLF or
    in the order of the certs in the bundle do not invalidate the comparison.
    """
    fps: list[str] = []
    for block in _PEM_CERT_RE.findall(payload):
        # `PEM_cert_to_DER_cert` only accepts the canonical label. A
        # `TRUSTED CERTIFICATE` block raised and fell into the `continue` — that is, it
        # was NOT counted, which is the opposite of what the addition check needs: the
        # OpenSSL loads that block as a trust anchor all the same.
        texto = (block.decode("ascii", errors="replace")
                 .replace("BEGIN TRUSTED CERTIFICATE", "BEGIN CERTIFICATE")
                 .replace("END TRUSTED CERTIFICATE", "END CERTIFICATE")
                 .replace("BEGIN X509 CERTIFICATE", "BEGIN CERTIFICATE")
                 .replace("END X509 CERTIFICATE", "END CERTIFICATE"))
        try:
            der = ssl.PEM_cert_to_DER_cert(texto)
        except Exception:
            # Unreadable block: there is no way to prove it is the pinned cert, so
            # it counts as an intruder instead of vanishing from the check.
            fps.append("<bloco-pem-ilegivel>")
            continue
        fps.append(hashlib.sha256(der).hexdigest())
    return fps


def _assert_pinned(payload: bytes, pins: frozenset[str]) -> None:
    """Aborts if the bundle contains ANY cert outside the pinned set.

    Requiring "all match", and not "some match", is what closes the attack by
    ADDITION. The whole file is concatenated to the public CAs by
    `_ensure_combined_bundle` and the result becomes the process trust store
    (SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE): EVERY cert in it
    becomes a trust anchor, not only the one that matches the pin. With the loose
    check, a bundle with [legitimate_root, attacker_ca] passed — the pin matched
    the first — and the second entered the trust store silently.

    The set (and not a single value) is what keeps CA rotation with overlap
    viable: during the switch, the legitimate bundle carries both roots.

    Applies to both paths (download and reuse of the file already on disk), because
    both end up feeding the same combined bundle.
    """
    found = _pem_fingerprints(payload)
    if not found:
        raise ValueError(
            f"Nenhum cert PEM valido no material a conferir contra {_PIN_ENV}."
        )
    intrusos = sorted(set(found) - pins)
    if intrusos:
        raise ValueError(
            f"Root cert NAO casa com {_PIN_ENV}. Aceitos: {sorted(pins)}; "
            f"o material contem tambem {intrusos}. Possivel interceptacao, "
            "substituicao ou acrescimo de CA — nada foi gravado."
        )


def _build_download_context() -> tuple[ssl.SSLContext | None, str]:
    """Verified SSLContext for the download, in this order:
      1. `certifi` (the lib ships a bundle of public CAs and is already an
         executor dependency). Solves the Windows gotcha where the default urllib
         has no trust store at all and falls into CERTIFICATE_VERIFY_FAILED.
      2. System default (`ssl.create_default_context()`). Works
         on Linux/macOS where the OS maintains a trust store.
    """
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where()), "certifi"
    except ImportError:
        pass
    try:
        return ssl.create_default_context(), "system"
    except Exception:
        return None, "none"


def _fetch(req: urllib.request.Request, ctx: ssl.SSLContext | None) -> bytes:
    """Simple GET with timeout. `ctx=None` uses the urllib default."""
    open_kwargs: dict = {"timeout": _DOWNLOAD_TIMEOUT_SEC}
    if ctx is not None:
        open_kwargs["context"] = ctx
    with urllib.request.urlopen(req, **open_kwargs) as resp:
        if resp.status != 200:
            raise urllib.error.HTTPError(
                req.full_url, resp.status, f"HTTP {resp.status}", resp.headers, None,
            )
        payload = resp.read()
    if not payload.strip():
        raise ValueError("Endpoint retornou payload vazio.")
    return payload


def _download_atomic(url: str, dest: Path) -> None:
    """Downloads `url` to `dest.tmp` and does an atomic rename — avoids a corrupted
    cert if the process is interrupted in the middle of the download.

    Only writes over VERIFIED TLS. There is no unverified fallback: the
    resulting file is the host's trust anchor, so a downgrade
    triggerable by any handshake error would give an on-path attacker
    persistent compromise (enroll OTP, mTLS cert key, jobs).

    That includes the SCHEME: `http://` is not a TLS that failed, it is a TLS that never
    existed — the SSLContext built below would simply be ignored by
    urllib and the payload would arrive in cleartext. Without a pin, abort.

    The only escape for a corporate SSL inspector (or for the on-prem `http://`):
    `ATLANS_CA_SHA256`. With the fingerprint pinned the chain may not validate, but the
    downloaded material is checked against the pin BEFORE any write —
    a mismatch aborts.
    """
    from urllib.parse import urlsplit

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "atlans-executor-bootstrap/1.0"},
    )

    pins = _expected_pins()

    scheme = (urlsplit(url).scheme or "").lower()
    if scheme != "https" and not pins:
        raise ValueError(
            f"Recusando baixar a ancora de confianca por '{scheme}://' ({url}). "
            "O root cert baixado vira trust store de TODA conexao TLS de saida "
            "deste host (SSL_CERT_FILE/REQUESTS_CA_BUNDLE), entao um atacante "
            "on-path so precisaria responder este GET para se tornar CA confiavel. "
            f"Use https:// no --server/EXECUTOR_PUBLIC_SERVER_URL, ou exporte "
            f"{_PIN_ENV}=<sha256 esperado> — com o pin, a integridade nao depende "
            "do canal."
        )

    ctx, ctx_source = _build_download_context()

    attempts: list[tuple[ssl.SSLContext | None, str]] = [(ctx, ctx_source)]
    if pins:
        attempts.append((ssl._create_unverified_context(), "pinned-sha256"))

    last_exc: Exception | None = None
    payload: bytes | None = None
    used_source = ctx_source
    for attempt_ctx, source in attempts:
        if source == "pinned-sha256":
            _emit(
                "WARNING",
                f"TLS verificado falhou ({type(last_exc).__name__}: {last_exc}). "
                f"Tentando de novo sem validar a cadeia porque {_PIN_ENV} esta "
                "setado — o cert baixado sera aceito somente se casar com o "
                "fingerprint pinado.",
            )
        try:
            payload = _fetch(req, attempt_ctx)
            used_source = source
            break
        except urllib.error.HTTPError:
            # Server response (404, 500...): switching TLS context does not help.
            raise
        except urllib.error.URLError as exc:
            # urllib wraps the handshake SSLError in URLError.reason — the
            # earlier `except ssl.SSLError` never matched and the second attempt
            # only happened by accident.
            if not isinstance(exc.reason, ssl.SSLError):
                raise  # DNS, connection refused, timeout: not a chain problem
            last_exc = exc
            continue
        except ssl.SSLError as exc:
            last_exc = exc
            continue

    if payload is None:
        raise last_exc or RuntimeError("Download do root cert falhou sem excecao registrada.")

    # Validation BEFORE writing: nothing touches the disk if the pin mismatches.
    if pins:
        _assert_pinned(payload, pins)

    tmp.write_bytes(payload)
    os.replace(tmp, dest)
    if used_source != "certifi":
        _emit("INFO", f"Root cert baixado usando SSL source={used_source}")
