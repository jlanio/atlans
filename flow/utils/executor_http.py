# flow/utils/executor_http.py
"""
Shared utility for configuring executor -> server HTTP requests.

After the migration to mTLS, calls from flow nodes (publish_map, send_email,
response_node, change_detector) are authenticated by the mTLS cert persisted in
the EXECUTOR_CERT_DIR directory (created during enrollment). No fallback to
X-Api-Key.

Returns (base_url, headers, verify) where:
  - base_url: the server's HTTP URL
  - headers:  empty dict (no header auth — mTLS resolves the identity in TLS)
  - verify:   SSLContext with the executor's cert + key + pinned CA
              or False on localhost (no TLS).
"""
import logging
import os
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})


def is_local_server(url: str) -> bool:
    """Detects whether the URL points to a local server (dev/Docker).

    SEC: compares the exact HOSTNAME. A substring match (`"localhost" in url`)
    treated `wss://localhost.evil.tld` — or any URL with "localhost" in the
    query string — as local, turning off TLS and mTLS entirely
    (`verify=False` / `ssl_ctx=None`). Single implementation: the executor
    re-exports it from `executor.utils`.
    """
    try:
        host = urlparse(url).hostname
    except ValueError:
        return False
    return (host or "").lower() in _LOCAL_HOSTS


def get_agent_http_config(
    server_url: str | None = None,
) -> tuple[str, dict, "str | bool | object"]:
    """
    Returns (base_url, headers, verify) ready for use with httpx.

    - Converts wss:// -> https:// and ws:// -> http://
    - On localhost: verify=False (no local TLS).
    - In prod: verify=SSLContext with the mTLS cert (cert-based authentication).
    """
    if server_url is None:
        # No default, like executor/config.py:SERVER_URL: a default would send the
        # upload to an installation nobody chose. It used to be
        # 'wss://localhost', which broke silently (Connection refused on the
        # presign upload); now the failure says what to do.
        server_url = os.getenv("EXECUTOR_SERVER_URL", "").strip()
        if not server_url:
            raise RuntimeError(
                "EXECUTOR_SERVER_URL nao definida: o executor nao sabe com que "
                "servidor falar. O enrollment (`python -m executor enroll "
                "--server=...`) grava o valor no .env."
            )

    base_url = server_url.replace("wss://", "https://").replace("ws://", "http://")
    # Identity comes from the mTLS cert — we no longer need auth headers.
    headers: dict = {}

    if is_local_server(base_url):
        verify: "str | bool | object" = False
    else:
        try:
            # The canonical implementation lives in executor.utils — lazy import so
            # EXECUTOR_CERT_DIR is not read on local calls (verify=False).
            from executor.utils import build_mtls_ssl_context
            verify = build_mtls_ssl_context()
        except Exception as exc:
            # Explicit diagnostics: silencing here leads to "CERTIFICATE_VERIFY_FAILED"
            # later with no clue about the real reason (wrong path, key format, etc).
            _logger.warning(
                "Falha ao montar SSLContext mTLS de EXECUTOR_CERT_DIR=%s — fallback "
                "para verify=True (provavel SSL: CERTIFICATE_VERIFY_FAILED contra "
                "a CA interna). Erro: %s: %s",
                os.getenv("EXECUTOR_CERT_DIR", "./certs"),
                type(exc).__name__, exc,
            )
            verify = True

    return base_url, headers, verify


def slugify(text: str) -> str:
    """Safe lowercase slug for a file name/S3 key.

    Lowercase variant of flow.utils.geo_helpers.slugify_label (the single
    implementation). Kept for the callers that depend on lower-case (data_output,
    publish_map, send_email → S3 keys)."""
    from flow.utils.geo_helpers import slugify_label
    return slugify_label(text).lower()
