# executor/enrollment.py
"""
Executor enrollment module via Bootstrap OTP + mTLS.

Flow:
  1. Operator runs `python -m executor enroll --otp=... --server=https://...`
  2. Executor generates an Ed25519 keypair (cert) + X25519 (job envelope encryption)
  3. Builds a CSR with CN=executor-pending
  4. POST /executores/enroll with Authorization: Bearer {otp}
  5. Server consumes the OTP, validates the CSR, asks step-ca to sign, returns the cert
  6. Executor validates the bundle and swaps cert.pem, chain.pem, ca.pem, key.pem and
     x25519_key.pem in CERT_DIR (0o600) via .new + os.replace —
     `_persist_bundle`, the same path as renewal (executor/renewal.py)
  7. Wipes the OTP from memory
"""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
import sys
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.x509.oid import NameOID

from executor.versao import versao_do_executor

logger = logging.getLogger(__name__)


# ── Filename constants ────────────────────────────────────────────────────────

CERT_FILE  = "cert.pem"
CHAIN_FILE = "chain.pem"
CA_FILE    = "ca.pem"
KEY_FILE   = "key.pem"          # chave privada Ed25519 (cert mTLS)
X25519_KEY_FILE = "x25519_key.pem"  # chave privada X25519 (envelope decrypt)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ws_to_http(server_url: str) -> str:
    """Converte wss://... -> https://... (e ws:// -> http://)."""
    if server_url.startswith("wss://"):
        return "https://" + server_url[len("wss://"):]
    if server_url.startswith("ws://"):
        return "http://" + server_url[len("ws://"):]
    return server_url


def _find_internal_root_cert(cert_dir: Path) -> Path | None:
    """Locates the internal CA's root cert, in the actual order of precedence.

    The quickstart/Docker writes the cert OUTSIDE cert_dir (e.g. /atlans-root.crt)
    and points SSL_CERT_FILE there; _ca_bootstrap honors that env and returns
    early. Searching only in `cert_dir` made enroll ignore exactly the cert the
    bootstrap had just honored, falling back to the public bundle — which does
    not contain the internal CA of the executors' host.
    """
    candidatos = [cert_dir / "atlans-root.crt"]
    for env in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        valor = os.environ.get(env)
        if valor:
            candidatos.append(Path(valor))

    for c in candidatos:
        try:
            if c.is_file() and c.stat().st_size > 0:
                return c
        except OSError:
            continue
    return None


def _resolve_enroll_verify(cert_dir: Path):
    """TLS context for POST /executores/enroll.

    Combines the default trust store (certifi/system) WITH the internal CA,
    instead of choosing one or the other:
      - the internal CA alone would break a server with a public cert (e.g. the
        root domain behind Cloudflare);
      - certifi alone breaks the executors' host, whose cert comes from step-ca.
    Same pattern as `executor/utils.py::build_mtls_ssl_context`, used after
    enroll.

    Returns `(verify, descricao_para_log)`. `verify` is an SSLContext when there
    is an internal CA; otherwise a path/bool accepted by httpx. Passing it
    explicitly avoids the gotcha of libraries that use truststore and ignore
    SSL_CERT_FILE.
    """
    root = _find_internal_root_cert(cert_dir)
    if root is not None:
        import ssl
        ctx = ssl.create_default_context()
        try:
            # create_default_context() honors SSL_CERT_FILE — which the quickstart
            # points to the internal CA, REPLACING the public trust store instead
            # of adding to it. We reload the public bundle explicitly so that
            # the system CAs survive (otherwise a public endpoint behind
            # Cloudflare would break in the same context).
            try:
                import certifi  # type: ignore
                ctx.load_verify_locations(cafile=certifi.where())
            except ImportError:
                ctx.load_default_certs()
            ctx.load_verify_locations(cafile=str(root))
            return ctx, f"sistema + CA interna ({root})"
        except Exception as exc:
            logger.warning("Root cert '%s' invalido (%s) — seguindo sem ele.", root, exc)

    try:
        import certifi  # type: ignore
        return certifi.where(), f"certifi ({certifi.where()})"
    except ImportError:
        return True, "trust store do sistema"


def _generate_keypairs() -> tuple[Ed25519PrivateKey, X25519PrivateKey]:
    """Generates (Ed25519 key for the mTLS cert, X25519 key for envelope encryption)."""
    return Ed25519PrivateKey.generate(), X25519PrivateKey.generate()


def _build_csr(ed_key: Ed25519PrivateKey, cn: str) -> bytes:
    """
    Builds an Ed25519 CSR in PEM. The CN must be `executor-{id}` — step-ca
    requires the CSR's CN to match the `sub` of the OTT (one-time token) that the
    backend generates with `sub=executor-{executor_id}`. Without it, step-ca
    rejects with 403.
    """
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    )
    csr = builder.sign(ed_key, algorithm=None)  # Ed25519 does not use a separate hash
    return csr.public_bytes(serialization.Encoding.PEM)


def _write_pem(path: Path, content: bytes, mode: int = 0o600) -> None:
    """Writes a PEM with restricted permissions. On Windows os.chmod() is a no-op but the NTFS ACL already restricts it."""
    path.write_bytes(content)
    try:
        os.chmod(path, mode)
    except (OSError, NotImplementedError):
        pass  # Windows


def _private_pem(chave: Ed25519PrivateKey | X25519PrivateKey) -> bytes:
    """Private key in unencrypted PKCS8 PEM — the format of key.pem and x25519_key.pem."""
    return chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _validate_bundle(bundle: dict, new_key: Ed25519PrivateKey) -> str | None:
    """
    Validates the bundle returned by /enroll or /renew-cert BEFORE touching any
    file. Returns None if OK, or the message with the reason for the refusal.

    WHY: renewal did `_write_pem(..., bundle.get("ca_pem", "").encode())`
    followed by `os.replace`. An empty `ca_pem` (the server has returned "" with
    only a WARNING when the root cert went missing) overwrote the GOOD ca.pem
    with an empty file. From then on EVERY connect blew up with
    X509 NO_CERTIFICATE_OR_CRL_FOUND — including renewal itself, which needs
    ca.pem to talk to the server. The executor stayed offline in endless
    backoff, unable to fix itself. A renewal that fails is recoverable; a
    renewal that corrupts the credentials is not. Enroll wrote directly and
    kept the same hole for longer: on a RE-enroll, the good ca.pem became the
    server's empty one.
    """
    # Required: without cert_pem there is no identity, and without ca_pem there is
    # no trust anchor — the latter is exactly the field whose emptiness caused the damage.
    #
    # chain_pem is deliberately NOT included here. The server fills it with
    # `body.get("ca") or ""` (executor_enrollment_service.sign_csr_via_stepca):
    # empty is a value it legitimately emits, and enroll has always written
    # that empty value without complaint. Requiring it here would make the
    # validator STRICTER than the emitter, and the consequence would be worse
    # than the original bug: renewal would fail on every cycle, silently, until
    # the cert expired and the executor died for good. A missing chain corrupts
    # nothing — what anchors trust is ca_pem.
    for field in ("cert_pem", "ca_pem"):
        value = bundle.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"campo '{field}' ausente ou vazio na resposta do servidor"

    chain_pem = bundle.get("chain_pem")
    if chain_pem is not None and not isinstance(chain_pem, str):
        return "campo 'chain_pem' com tipo invalido na resposta do servidor"

    try:
        cert = x509.load_pem_x509_certificate(bundle["cert_pem"].encode())
    except Exception as exc:
        return f"'cert_pem' nao e um certificado PEM valido: {exc}"

    try:
        ca_certs = x509.load_pem_x509_certificates(bundle["ca_pem"].encode())
    except Exception as exc:
        return f"'ca_pem' nao e um PEM de certificados valido: {exc}"
    if not ca_certs:
        return "'ca_pem' nao contem nenhum certificado"

    # chain_pem only needs to be PARSEABLE when it is filled in.
    if chain_pem and chain_pem.strip():
        try:
            x509.load_pem_x509_certificates(chain_pem.encode())
        except Exception as exc:
            return f"'chain_pem' nao e um PEM de certificados valido: {exc}"

    # The issued cert must be for the key we just generated — if the server
    # returned (through a bug or a cache) the old cert, the cert/key pair would
    # be inconsistent and mTLS would break with the same "endless offline" look.
    issued_pub = cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    expected_pub = new_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if issued_pub != expected_pub:
        return "'cert_pem' nao corresponde a chave privada gerada para este pedido"

    return None


def _persist_bundle(
    cert_dir: Path,
    bundle: dict,
    chave_ed: Ed25519PrivateKey,
    chave_x: X25519PrivateKey | None = None,
) -> str | None:
    """
    Validates the bundle and swaps the identity files — the single path for
    enroll and renewal. Returns None if it wrote, or the reason for the refusal;
    on refusal NO file has been touched.

    Everything first goes to `<nome>.new` and only afterwards, with all of them
    written, does each one replace the original with os.replace (atomic per
    file). A write failure midway (disk full) deletes the .new files and
    propagates the error without having swapped anything. The .new files a crash
    leaves behind are cleaned up at boot
    (executor/config.py::_cleanup_renewal_orphans).

    `chave_x` (the envelope's X25519 key) only comes on enroll: renewal swaps the
    mTLS cert, and the X25519 public key remains the one registered on the server.
    """
    problema = _validate_bundle(bundle, chave_ed)
    if problema:
        return problema

    contents = [
        (CERT_FILE, bundle["cert_pem"].encode()),
        # chain_pem is optional (see _validate_bundle): missing or null becomes empty.
        (CHAIN_FILE, (bundle.get("chain_pem") or "").encode()),
        (CA_FILE, bundle["ca_pem"].encode()),
        (KEY_FILE, _private_pem(chave_ed)),
    ]
    if chave_x is not None:
        contents.append((X25519_KEY_FILE, _private_pem(chave_x)))

    novos = [(cert_dir / (nome + ".new"), cert_dir / nome, dados) for nome, dados in contents]
    try:
        for temporario, _final, dados in novos:
            _write_pem(temporario, dados)
    except OSError:
        for temporario, _final, _data in novos:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    for temporario, final, _data in novos:
        os.replace(temporario, final)
    return None


def _pin_server_signing_key(cert_dir: Path, key_b64: str | None) -> str | None:
    """Pins the server's signing key delivered in the enroll/renew bundle.

    Does not undo the enrollment if there is a problem: the mTLS cert has already
    been issued and persisted, and reverting that would burn the OTP for nothing.
    But a MISMATCH (the pinned key is a different one) cannot become just a log
    line: `pin_key` writes a conflict marker that makes the next boot stop, and
    here we return the message so the CLI ends with a failure instead of printing
    "concluido com sucesso" (completed successfully). Before, the command exited
    with 0 and the executor came up rejecting 100% of jobs for an invalid
    signature, with nothing connecting the two facts.

    Returns the mismatch message (fatal for the CLI) or None.
    """
    from executor.server_key import ServerKeyError, ServerKeyPersistError, pin_key

    if not key_b64:
        logger.warning(
            "Servidor nao devolveu 'server_signing_public_key' no bundle "
            "(EXECUTOR_SIGNING_KEY provavelmente nao configurada no servidor). "
            "O executor tentara fixa-la no primeiro boot."
        )
        return None
    try:
        pin_key(cert_dir, key_b64, source="bundle do enrollment")
    except ServerKeyPersistError as exc:
        # Not a mismatch: it is the cert_dir that did not accept the write. The boot
        # falls back to TOFU and carries on — not worth failing the enroll over it.
        logger.error("Nao foi possivel gravar o pin da chave de assinatura: %s", exc)
        return None
    except ServerKeyError as exc:
        logger.error("Nao foi possivel fixar a chave de assinatura do servidor: %s", exc)
        return str(exc)
    return None


def _persist_agent_config_to_env(
    executor_id: str,
    server_url: str | None = None,
    env_path: Path | None = None,
) -> None:
    """
    Seeds `.env` from `.env.example` (if empty) and writes EXECUTOR_ID +
    EXECUTOR_SERVER_URL. Also removes legacy envs that confuse the executor after
    the mTLS migration.

    The seed ensures that critical variables (EXECUTOR_SERVER_URL, LOG_LEVEL, etc.)
    are populated from the first boot — without it, the executor fell back to a
    hardcoded fallback (`wss://localhost`) and the upload failed with
    `Connection refused`.

    IO errors become a WARNING — the enrollment has already persisted the cert,
    and a missing EXECUTOR_ID in .env does not stop the operator from adding it
    manually.
    """
    from executor._env_utils import (
        normalize_server_url_to_ws,
        persist_env_var,
        read_env_var,
        remove_env_var,
        seed_env_from_example,
    )

    # 1. Seeds .env from .env.example (if there is no config yet).
    seed_env_from_example(env_path=env_path)

    # 2. Cleans up legacy envs (idempotent):
    # - EXECUTOR_API_KEY: no longer used after mTLS, lingers in old .env files.
    # - EXECUTOR_PRIVATE_KEY_PATH pointing to a legacy path: made the executor
    #   generate a new key in ./agent_key.pem instead of using the enroll one in
    #   x25519_key.pem.
    remove_env_var("EXECUTOR_API_KEY", env_path)
    legacy_key_path = read_env_var("EXECUTOR_PRIVATE_KEY_PATH", env_path)
    if legacy_key_path and legacy_key_path.strip() in ("./agent_key.pem", "/data/agent_key.pem"):
        remove_env_var("EXECUTOR_PRIVATE_KEY_PATH", env_path)

    # 3. Updates EXECUTOR_ID with the enrollment value.
    persist_env_var(
        "EXECUTOR_ID",
        executor_id,
        env_path=env_path,
        file_header="# Gerado por `python -m executor enroll`\n",
    )

    # 4. Overwrites EXECUTOR_SERVER_URL if the operator passed a --server different
    # from the example's default. Allows staging/dev deploys without editing .env
    # by hand. Normalizes to wss:// because the executor opens a WebSocket — writing
    # https:// to .env breaks the connect with "scheme isn't ws or wss".
    if server_url:
        persist_env_var(
            "EXECUTOR_SERVER_URL",
            normalize_server_url_to_ws(server_url),
            env_path=env_path,
        )


# ── API publica ────────────────────────────────────────────────────────────────


def _refusal_reason(resp) -> str:
    """The reason the server gave, in the format it responds with.

    The server's handlers return `message` (not `detail`, FastAPI's raw field),
    and the validation 422 lists the rejected fields in `details`. It used to
    read only `detail`: every refusal came out with a blank reason.
    """
    try:
        corpo = resp.json()
    except Exception:
        return resp.text[:200]
    if not isinstance(corpo, dict):
        return str(corpo)[:200]
    motivo = str(corpo.get("message") or corpo.get("detail") or "")
    campos = [
        f"{'.'.join(str(p) for p in (e.get('loc') or [])[1:])}: {e.get('msg', '')}"
        for e in (corpo.get("details") or []) if isinstance(e, dict)
    ]
    if campos:
        motivo = f"{motivo} ({'; '.join(campos)})" if motivo else "; ".join(campos)
    return motivo[:300]


def enroll(
    server_url: str,
    otp: str,
    executor_id: str,
    cert_dir: str | Path,
    env_path: str | Path | None = None,
) -> dict:
    """
    Runs the full enrollment: generates keypairs, sends the CSR, receives the cert, persists.

    `executor_id` must be the executor's id_hash (provided by the admin in the UI).
    It is used as the CSR's CN — step-ca requires it to match the OTT's `sub`.

    `env_path` defines where EXECUTOR_ID and EXECUTOR_SERVER_URL are written.
    Without it, it falls back to the `_env_utils` default (the `.env` inside the
    package), which is the wrong place when the caller is the desktop app — there
    the config lives in `%APPDATA%\\AtlasExecutor\\config\\.env`.

    Raises RuntimeError if the server refuses or step-ca is unavailable.
    Returns a dict with the issued cert's metadata (serial, fingerprint, expires_at).
    """
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(cert_dir, 0o700)
    except (OSError, NotImplementedError):
        pass

    if not executor_id or not executor_id.strip():
        raise RuntimeError("executor_id e obrigatorio (recebido pelo admin no momento da criacao do executor).")

    logger.info("Gerando keypairs locais...")
    ed_key, x_key = _generate_keypairs()
    csr_pem = _build_csr(ed_key, cn=f"executor-{executor_id}").decode()

    x25519_pub_pem = x_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    body = {
        "csr_pem":        csr_pem,
        "public_key_pem": x25519_pub_pem,
        "hostname":       socket.gethostname()[:255],
        # The same as in the handshake (executor/versao.py): the build's version in the
        # Docker image, the app's version on desktop.
        "executor_version":  versao_do_executor(),
        "os":             f"{platform.system()} {platform.release()}"[:64],
    }

    http_base = _ws_to_http(server_url).rstrip("/")
    url = f"{http_base}/executores/enroll"

    # `--server=ws://...` becomes http:// and the `verify` below becomes decorative:
    # the OTP travels in clear text in the Authorization header and anyone on-path
    # can consume it to enroll as this executor. We do not block it (on-prem
    # without TLS is a deliberate operator choice), but it cannot be silent.
    if not http_base.lower().startswith("https://"):
        logger.warning(
            "Enroll indo por canal NAO CIFRADO (%s): o OTP trafega em texto claro e "
            "o certificado emitido nao tem mais garantia que a rede. Use https:// / "
            "wss:// em qualquer ambiente que nao seja um laboratorio isolado.",
            http_base,
        )

    verify_path, verify_desc = _resolve_enroll_verify(cert_dir)
    logger.info("Enviando CSR para %s (verify=%s)", url, verify_desc)
    try:
        resp = httpx.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {otp}"},
            timeout=30,
            verify=verify_path,
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Falha de rede no enrollment: {exc}") from exc
    finally:
        # Wipes the OTP from memory as soon as possible.
        otp = None  # noqa: F841

    if resp.status_code != 200 and resp.status_code != 201:
        raise RuntimeError(
            f"Servidor recusou enrollment (status {resp.status_code}): {_refusal_reason(resp)}"
        )

    bundle = resp.json()

    # Persists cert + chain + CA + private keys through the same path as
    # renewal: validates first and swaps via .new + os.replace. Writing directly,
    # as before, accepted an empty ca_pem and — on a RE-enroll — overwrote the
    # good ca.pem, leaving the executor without a trust anchor.
    problema = _persist_bundle(cert_dir, bundle, ed_key, x_key)
    if problema:
        raise RuntimeError(
            f"Servidor devolveu um bundle invalido no enrollment ({problema}). "
            "Nenhum arquivo foi alterado. O OTP ja foi consumido: depois de "
            "corrigir o servidor, gere outro."
        )

    # Pins the server's Ed25519 signing key that came in the bundle. This is the
    # right moment: the bundle has already been authenticated by the OTP, so there
    # is no "trust the first response" window. Without this the executor would
    # fall back to the boot TOFU (see executor/server_key.py), which is the gap
    # that finding S8 points out.
    signing_key_conflict = _pin_server_signing_key(
        cert_dir, bundle.get("server_signing_public_key")
    )

    # Seeds executor/.env from .env.example, writes EXECUTOR_ID and updates
    # EXECUTOR_SERVER_URL with the value the operator passed in --server. Ensures
    # that critical variables (LOG_LEVEL, EXECUTOR_SYNC_*, etc.) come populated.
    _persist_agent_config_to_env(
        executor_id, server_url=server_url,
        env_path=Path(env_path) if env_path else None,
    )

    logger.info(
        "Enrollment OK. Cert serial=%s expira=%s",
        bundle["serial"], bundle["expires_at"],
    )

    return {
        "serial":      bundle["serial"],
        "fingerprint": bundle["fingerprint"],
        "issued_at":   bundle["issued_at"],
        "expires_at":  bundle["expires_at"],
        # Present (a message) when the server's signing key diverged from the
        # pinned one. The cert is valid, but the executor will NOT come up until the
        # operator resolves the conflict — the CLI needs to say so instead of "success".
        "signing_key_conflict": signing_key_conflict,
    }


# ── CLI entry point ────────────────────────────────────────────────────────────


def _cli_main(argv: list[str]) -> int:
    """
    `python -m executor enroll` subcommand:
      python -m executor enroll --otp=<otp> --server=https://agents.<dominio> \\
          [--executor-id=<id>] [--cert-dir=./certs]

    If `--executor-id` is not passed, reads it from the EXECUTOR_ID env (loaded from
    executor/.env when running via docker compose, or exported in the shell when local).
    """
    import argparse
    parser = argparse.ArgumentParser(prog="atlans-executor enroll")
    parser.add_argument(
        "--executor-id", default=None,
        help="ID do executor (id_hash). Default: env EXECUTOR_ID (de executor/.env)",
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--otp", help="OTP fornecido pelo admin (~43 chars)")
    grupo.add_argument(
        "--otp-stdin", action="store_true",
        help="Le o OTP da primeira linha do stdin. Preferivel a --otp: a linha "
             "de comando de um processo e legivel por qualquer outro processo "
             "do mesmo usuario.",
    )
    parser.add_argument("--server", required=True, help="URL do servidor (https:// ou wss://)")
    parser.add_argument("--cert-dir", default="./certs", help="Diretorio para salvar cert + chave (default: ./certs)")
    parser.add_argument(
        "--json", action="store_true",
        help="Emite um unico objeto JSON no stdout, em vez do relatorio humano. "
             "Para quem chama o enrollment de outro programa (o app desktop).",
    )
    args = parser.parse_args(argv)

    # With --json stdout belongs to the JSON and nothing else; the log goes to stderr,
    # otherwise the first INFO logging line would break the caller's parse.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr if args.json else sys.stdout,
    )

    def _fail(mensagem: str, *, codigo: str = "erro") -> int:
        if args.json:
            json.dump({"ok": False, "codigo": codigo, "erro": mensagem}, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            print(f"FALHA: {mensagem}", file=sys.stderr)
        return 1

    otp = args.otp
    if args.otp_stdin:
        otp = sys.stdin.readline().strip()
        if not otp:
            return _fail("nenhum OTP recebido no stdin.", codigo="otp_ausente")

    # Loads executor/.env (no-op if env_file was already applied by docker compose).
    try:
        from dotenv import load_dotenv as _load_dotenv
        _env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")
        _load_dotenv(dotenv_path=_env_path, override=False)
    except ImportError:
        pass  # python-dotenv missing: relies on the shell already having the envs

    # Resolve executor_id: flag CLI > env var > erro claro.
    executor_id = (args.executor_id or os.getenv("EXECUTOR_ID") or "").strip()
    if not executor_id:
        return _fail(
            "EXECUTOR_ID nao definido. Configure no .env ou passe --executor-id=<id>.",
            codigo="executor_id_ausente",
        )

    _env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")

    try:
        info = enroll(args.server, otp, executor_id, args.cert_dir, env_path=_env_path)
    except RuntimeError as exc:
        return _fail(str(exc), codigo="enroll_recusado")

    # Cert issued, but the server's signing key does not match the pinned one:
    # the executor will not come up like this (see executor/server_key.py). Exiting
    # with 0 here sent the operator to run `docker compose up` and discover the
    # problem only through the symptom "online but nothing runs".
    if info.get("signing_key_conflict"):
        if args.json:
            json.dump({
                "ok": False, "codigo": "signing_key_conflict",
                "erro": info["signing_key_conflict"],
                "cert_dir": str(Path(args.cert_dir).resolve()),
            }, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return 1
        print(file=sys.stderr)
        print("  Cert emitido, MAS O ENROLLMENT NAO ESTA UTILIZAVEL.", file=sys.stderr)
        print(f"  Certs em: {Path(args.cert_dir).resolve()}", file=sys.stderr)
        print(file=sys.stderr)
        print(f"  {info['signing_key_conflict']}", file=sys.stderr)
        return 1

    if args.json:
        json.dump({
            "ok": True,
            "executor_id": executor_id,
            "serial": info.get("serial"),
            "fingerprint": info.get("fingerprint"),
            "expires_at": info.get("expires_at"),
            "cert_dir": str(Path(args.cert_dir).resolve()),
            "env_path": _env_path,
        }, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    print()
    print("  Enrollment concluido com sucesso.")
    print(f"  Serial:     {info['serial']}")
    print(f"  Valido ate: {info['expires_at']}")
    print(f"  Certs em:   {Path(args.cert_dir).resolve()}")
    print(f"  EXECUTOR_ID gravado em: {_env_path}")
    # No quickstart (install.sh) o bash continua e roda `docker compose up -d`
    # logo apos. Omitir o "python -m executor" evita instrucao conflitante.
    if not os.getenv("ATLANS_QUICKSTART"):
        print()
        print("  Inicie o executor com:")
        print("    python -m executor")
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main(sys.argv[1:]))
