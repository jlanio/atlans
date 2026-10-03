# executor/server_key.py
"""
Resolution and PINNING of the server's Ed25519 public signing key.

MOTIVATION (audit finding S8):
Before, when `SERVER_SIGNING_PUBLIC_KEY` was not in `.env` (the default case —
neither enroll nor setup wrote it), the executor fetched the key from
`GET /executores/server-public-key` **on every boot**, with
`follow_redirects=True` and without persisting anything. That makes the job
signing layer decorative: whoever won the channel on any boot delivered their
own key and could then sign arbitrary jobs — which the executor then runs with
the workspace's credentials. The signature added nothing on top of TLS, and
the compromise repeated on every restart without leaving a trace.

Order of precedence now:
  1. `SERVER_SIGNING_PUBLIC_KEY` in the environment — explicit operator override.
  2. File pinned at `CERT_DIR/server_signing.pub` — written at enrollment
     (with no trust window at all: it arrives together with the cert, inside
     the same bundle authenticated by the OTP) or by the TOFU of step 3.
  3. TOFU **only once**: fetch over mTLS with the internal CA already pinned,
     with redirects off, and PERSIST. Subsequent boots use the file from step 2.

The difference that matters: in the old model every restart was a new attack
opportunity; now there is at most ONE window, and only for executors enrolled
before this change. New enrollments never have it.

A mismatch (the server key changed) is treated as an ERROR, not as a silent
update: rotating the signing key requires operator action (re-enroll or
deliberately deleting the pinned file). Accepting the new key automatically
would reopen exactly the hole that pinning closes.

And the mismatch STOPS THE BOOT, not just the enroll: `pin_key` records a
`server_signing.pub.conflict` marker and `resolve_server_signing_key` turns it
into ServerKeyError. Without that the executor started with the stale pin,
connected, requested jobs and rejected 100% of them with "Assinatura Ed25519
inválida" (invalid Ed25519 signature) — a silent failure mode, in which nothing
at boot mentions the key. Failing at boot is loud and actionable.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SERVER_SIGNING_PUB_FILE = "server_signing.pub"
SERVER_SIGNING_CONFLICT_FILE = "server_signing.pub.conflict"


class ServerKeyError(RuntimeError):
    """Failure to establish trust in the server's signing key."""


class ServerKeyPersistError(ServerKeyError):
    """Could not WRITE the pin — but the key itself is trustworthy.

    A subclass on purpose: enroll/renewal already handle ServerKeyError and keep
    logging the problem. The one that needs to tell them apart is the boot,
    which can carry on with the key in memory (it came over verified mTLS)
    instead of dying because of a read-only directory.
    """


def pinned_key_path(cert_dir: str | Path) -> Path:
    return Path(cert_dir) / SERVER_SIGNING_PUB_FILE


def conflict_marker_path(cert_dir: str | Path) -> Path:
    return Path(cert_dir) / SERVER_SIGNING_CONFLICT_FILE


def load_pinned_key(cert_dir: str | Path) -> str | None:
    """Reads the pinned key. Returns None ONLY when there is no pin at all.

    Important distinction: "file missing" and "file present but unreadable/
    empty" must NOT have the same outcome. Treating both as None would make the
    executor fall back to network TOFU — that is, anyone able to corrupt or
    truncate the file (or a disk error) would downgrade the pinned trust back
    to "accept the first response that arrives", which is exactly what
    pinning exists to prevent. A broken pin is an ERROR, not an absence.
    """
    path = pinned_key_path(cert_dir)
    if not path.exists():
        return None
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ServerKeyError(
            f"Chave de assinatura fixada em '{path}' existe mas não pôde ser lida: {exc}. "
            "Corrija a permissão do arquivo ou apague-o conscientemente para refazer o pin."
        ) from exc
    if not value:
        raise ServerKeyError(
            f"Chave de assinatura fixada em '{path}' está vazia. "
            "Apague o arquivo conscientemente para refazer o pin, ou restaure-o do backup."
        )
    return value


def _validate_key_b64(key_b64: str) -> None:
    """Confirms that the string really is an Ed25519 public key (32 raw bytes)."""
    import base64

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        raw = base64.b64decode(key_b64, validate=True)
    except Exception as exc:
        raise ServerKeyError(f"Chave de assinatura não é base64 válido: {exc}") from exc
    if len(raw) != 32:
        raise ServerKeyError(
            f"Chave de assinatura tem {len(raw)} bytes; Ed25519 exige exatamente 32."
        )
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise ServerKeyError(f"Chave de assinatura não é uma chave Ed25519 válida: {exc}") from exc


def _divergence_message(path: Path, existing: str, key_b64: str, source: str) -> str:
    return (
        "A chave de assinatura do servidor MUDOU.\n"
        f"  fixada em disco: {existing[:16]}…\n"
        f"  recebida ({source}): {key_b64[:16]}…\n"
        "Isto é ou uma rotação legítima da chave do servidor, ou um ataque. "
        "O executor NÃO aceita a troca automaticamente e NÃO sobe enquanto o "
        "conflito existir — subir com o pin antigo faria ele rejeitar todo job "
        "sem dizer por quê.\n"
        "Se a rotação for legítima, confirme a chave nova com o admin e então "
        f"apague '{path}' e '{conflict_marker_path(path.parent)}' e reinicie "
        "(ou defina SERVER_SIGNING_PUBLIC_KEY no ambiente)."
    )


def _clear_conflict_marker(cert_dir: str | Path) -> None:
    """Removes the marker when the pin is consistent again. Without this the executor
    would stay stuck forever after the operator has already resolved the case."""
    marker = conflict_marker_path(cert_dir)
    try:
        marker.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Não foi possível remover o marcador '%s': %s", marker, exc)


def pin_key(cert_dir: str | Path, key_b64: str, *, source: str) -> None:
    """Pins the key on disk.

    If there is already a DIFFERENT pinned key, writes a conflict marker and
    raises ServerKeyError instead of overwriting — the marker is what makes the
    next boot STOP (see `resolve_server_signing_key`), instead of silently
    loading the stale pin.

    A failure to WRITE (read-only dir, ENOSPC) becomes ServerKeyPersistError,
    which the boot can degrade to in-memory use — the key itself is already
    trustworthy.
    """
    key_b64 = (key_b64 or "").strip()
    if not key_b64:
        raise ServerKeyError("Servidor não forneceu chave de assinatura.")
    _validate_key_b64(key_b64)

    path = pinned_key_path(cert_dir)
    existing = load_pinned_key(cert_dir)
    if existing and existing != key_b64:
        _record_conflict(cert_dir, existing, key_b64, source)
        raise ServerKeyError(_divergence_message(path, existing, key_b64, source))
    if existing == key_b64:
        _clear_conflict_marker(cert_dir)
        return  # already pinned, nothing to do

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key_b64 + "\n", encoding="utf-8")
    except OSError as exc:
        # Symmetric to what `load_pinned_key` does on read: an IO error becomes an
        # actionable message, never a raw traceback in the middle of the boot.
        raise ServerKeyPersistError(
            f"Não foi possível fixar a chave de assinatura em '{path}': {exc}. "
            "Torne o diretório de certs gravável (o bind `:ro` do compose é a "
            "causa mais comum) ou defina SERVER_SIGNING_PUBLIC_KEY no ambiente."
        ) from exc
    try:
        os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass  # Windows: the NTFS ACL already restricts it
    _clear_conflict_marker(cert_dir)
    logger.info("Chave de assinatura do servidor fixada em '%s' (origem: %s).", path, source)


def _record_conflict(cert_dir: str | Path, existing: str, key_b64: str, source: str) -> None:
    """Persists the mismatch so the next boot can abort with context.

    Best-effort: if not even the marker can be written, the mismatch's
    ServerKeyError is still raised — losing the marker must not mask the
    conflict that was just detected.
    """
    marker = conflict_marker_path(cert_dir)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{source}\n{key_b64}\n", encoding="utf-8")
    except OSError as exc:
        logger.error(
            "Divergência de chave detectada mas o marcador '%s' não pôde ser gravado "
            "(%s) — o próximo boot NÃO vai conseguir avisar sobre o conflito.",
            marker, exc,
        )


async def resolve_server_signing_key(cert_dir: str | Path, server_url: str) -> str:
    """Returns the signing key to use, pinning it when necessary.

    Raises ServerKeyError when trust cannot be established (including the
    recorded-mismatch case) — the caller must abort the boot. Running without
    a trusted key means accepting jobs from anyone who wins the channel.

    The only failure that does NOT abort is pin persistence: the key was
    already obtained over mTLS, so it is better to carry on with it in memory
    than to bring the executor down because of a read-only volume.
    """
    # 1. Explicit operator override — it is the deliberate action that resolves
    #    even a recorded conflict, so it beats even the marker (only warns).
    env_key = (os.getenv("SERVER_SIGNING_PUBLIC_KEY") or "").strip()
    if env_key:
        _validate_key_b64(env_key)
        marker = conflict_marker_path(cert_dir)
        if marker.exists():
            logger.warning(
                "Há um conflito de chave registrado em '%s', mas SERVER_SIGNING_PUBLIC_KEY "
                "foi definida explicitamente e vence. Apague o marcador e o pin depois de "
                "confirmar a rotação com o admin.", marker,
            )
        logger.info("Chave de assinatura do servidor definida via ambiente.")
        return env_key

    # 1.5. Conflito registrado por um enroll/renewal anterior.
    _assert_no_conflict(cert_dir)

    # 2. Key already pinned (enrollment or previous TOFU).
    pinned = load_pinned_key(cert_dir)
    if pinned:
        _validate_key_b64(pinned)
        logger.info("Chave de assinatura do servidor carregada do pin local.")
        return pinned

    # 3. One-time TOFU, over mTLS, and persisted.
    logger.warning(
        "Nenhuma chave de assinatura fixada — buscando do servidor UMA VEZ e fixando "
        "em '%s'. Executores enrolados a partir de agora recebem a chave já no bundle "
        "do enroll e não passam por esta etapa.",
        pinned_key_path(cert_dir),
    )
    fetched = await _fetch_server_key(server_url)
    try:
        pin_key(cert_dir, fetched, source="GET /executores/server-public-key")
    except ServerKeyPersistError as exc:
        # The key came over mTLS with the internal CA already pinned, so it is
        # trustworthy IN THIS session. Killing the boot because of a read-only
        # directory would trade a security risk for total unavailability. The
        # price is that the TOFU window repeats on every boot — hence ERROR,
        # not WARNING.
        logger.error(
            "%s\nSeguindo com a chave APENAS EM MEMÓRIA nesta sessão: a janela de "
            "TOFU vai se repetir a cada reinício até o pin conseguir ser gravado.",
            exc,
        )
    return fetched


def _assert_no_conflict(cert_dir: str | Path) -> None:
    """Aborts the boot if a previous enroll/renewal detected a key change.

    This is the missing link: `pin_key` only runs on enroll and renewal, so
    without the marker the mismatch died in a log line and the next boot
    loaded the stale pin — rejecting every job for an invalid signature, with
    nothing at boot tying the failure to the key.
    """
    marker = conflict_marker_path(cert_dir)
    if not marker.exists():
        return
    try:
        linhas = marker.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        linhas = []
    source = linhas[0] if linhas else "origem desconhecida"
    recebida = linhas[1] if len(linhas) > 1 else "?"
    existing = "?"
    try:
        existing = load_pinned_key(cert_dir) or "?"
    except ServerKeyError:
        pass
    raise ServerKeyError(
        _divergence_message(pinned_key_path(cert_dir), existing, recebida, source)
    )


async def _fetch_server_key(server_url: str) -> str:
    """Fetches the key from `/executores/server-public-key` over mTLS.

    `follow_redirects=False` on purpose: following a redirect here would let a
    hostile proxy divert the request to a host that returns its own key.
    """
    import httpx

    from executor.utils import mtls_httpx_kwargs, ws_to_http

    base = ws_to_http(server_url)
    url = f"{base}/executores/server-public-key"
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=False, **mtls_httpx_kwargs(base)
        ) as client:
            resp = await client.get(url)
    except Exception as exc:
        raise ServerKeyError(
            f"Não foi possível buscar a chave de assinatura em {url}: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise ServerKeyError(
            f"Servidor respondeu HTTP {resp.status_code} em {url} — chave de "
            "assinatura não obtida. (Redirects não são seguidos de propósito.)"
        )
    try:
        key_b64 = resp.json()["ed25519_public_key_b64"]
    except Exception as exc:
        raise ServerKeyError(f"Resposta inesperada de {url}: {exc}") from exc
    return key_b64
