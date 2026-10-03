# executor/utils.py
"""Utility functions shared by the executor."""
import logging
import os

# `is_local_server` lives in flow/ (present in both the API and executor images):
# the nodes' `get_agent_http_config` needs the SAME rule and cannot import
# the executor in the API image. Re-exported here for the executor's callers.
from flow.utils.executor_http import is_local_server

logger = logging.getLogger(__name__)


def ocultar_no_windows(caminho) -> None:
    """Marks a file/folder as HIDDEN on Windows (FILE_ATTRIBUTE_HIDDEN).

    The executor's internal files are already born with a leading dot in the name
    (`.atlans-sync.json`, `.executor_results.sqlite`, `.atlans-trash/`), which is
    enough to hide them on Linux and macOS. Windows Explorer, however, IGNORES
    that convention: there these files show up like any other, in the middle of
    the user's data, inviting accidental deletion. And deleting is not
    harmless — losing the manifest re-syncs the whole folder, and losing the
    SQLite outbox throws away job results not yet confirmed by the server.
    The NTFS hidden attribute is what actually gets these files out of the way
    on the only OS where the dot does not do it.

    No-op outside Windows (the dot already takes care of it) and fully best-effort:
    any failure — file just removed, volume without attribute support,
    permissions — is swallowed. Hiding is a convenience; it must never bring down
    the flow that just wrote the file.

    Accepts str or os.PathLike.
    """
    # TODO(windows): the behavior of this function and of the places that depend on
    # it was verified through Win32 DOCUMENTATION/analysis, not on a real Windows —
    # CI runs only on Linux, where everything here is a no-op. Three premises are
    # left without an end-to-end test:
    #   1. os.replace (MoveFileEx) does NOT fail when overwriting a hidden target,
    #      so the manifest (sync/manifest.py) keeps persisting after the 1st
    #      hide. Only CreateFile CREATE_ALWAYS is blocked by a hidden file, and the
    #      .tmp + os.replace flow works around it.
    #   2. SQLite reopens a hidden .sqlite (result_store.py) via OPEN_EXISTING/
    #      OPEN_ALWAYS, without ACCESS_DENIED.
    #   3. SetFileAttributesW really hides it in Explorer (and paths > MAX_PATH
    #      without long-path enabled fall into the silent bail — see the debug log).
    # Closing the gap: a smoke test marked @pytest.mark.skipif(sys.platform !=
    # 'win32') that creates, hides and rewrites manifest+outbox on a Windows runner.
    if os.name != "nt":
        return
    try:
        import ctypes

        FILE_ATTRIBUTE_HIDDEN = 0x02
        # GetFileAttributesW returns 0xFFFFFFFF on error; with ctypes' default
        # restype (c_int) that arrives as -1. We handle both forms.
        INVALID = (-1, 0xFFFFFFFF)

        alvo = str(caminho)
        # ctypes converts `str` to wchar_t* automatically in the `...W` functions.
        atuais = ctypes.windll.kernel32.GetFileAttributesW(alvo)
        if atuais in INVALID:
            # Nonexistent file, no access, or a path beyond MAX_PATH without
            # long-path enabled. Stays best-effort; we only log at debug
            # because, without it, this failure mode is impossible to diagnose.
            logger.debug("ocultar_no_windows: GetFileAttributesW invalido para %s (err=%s)",
                         alvo, ctypes.windll.kernel32.GetLastError())
            return
        # OR with the current attributes so as not to clear a READONLY/SYSTEM that was
        # already there. If the hidden bit is already set, the file is not touched.
        if not (atuais & FILE_ATTRIBUTE_HIDDEN):
            if not ctypes.windll.kernel32.SetFileAttributesW(alvo, atuais | FILE_ATTRIBUTE_HIDDEN):
                logger.debug("ocultar_no_windows: SetFileAttributesW falhou para %s (err=%s)",
                             alvo, ctypes.windll.kernel32.GetLastError())
    except Exception:
        # Best-effort by contract: see the docstring.
        pass


def ws_to_http(ws_url: str) -> str:
    """Converte URL WebSocket para HTTP/HTTPS. Ex: wss://agents.<dominio> -> https://agents.<dominio>"""
    return ws_url.replace("wss://", "https://").replace("ws://", "http://")


def build_mtls_ssl_context():
    """
    Builds an SSLContext with the executor's cert + key (mTLS) and the internal CA
    ADDED to the system's default trust store.

    It used to be `create_default_context(cafile=ca.pem)`, which REPLACES the system
    trust store with ca.pem — the executor only trusted the internal CA and
    broke when talking to public endpoints (e.g. public S3 behind a CDN)
    on the same SSLContext, with the error `unable to get local issuer certificate`.

    Now: default trust store (public CAs via certifi/system) + ca.pem
    as an additional CA. The same context works for:
      - the executors host (signed by the internal CA)
      - public S3 / any endpoint with a public cert (CDN/LE)
      - sending the executor's mTLS cert when the server asks for it (Traefik)

    GOTCHA: `create_default_context()` honors SSL_CERT_FILE, which REPLACES the
    default trust store instead of adding to it. Today _ca_bootstrap already exports
    a combined bundle (certifi + internal CA), but an operator may point the variable
    at a file with only the internal CA — and then the same context used as
    `verify` in httpx.put for MinIO/Drive/external APIs would break with "unable
    to get local issuer certificate". Loading certifi explicitly before
    ca.pem makes this context independent of whatever came in the environment — the
    same treatment as `executor/enrollment.py::_resolve_enroll_verify`.

    Raises FileNotFoundError if the executor has not been enrolled.
    """
    import ssl
    from executor import config as _agent_config
    ctx = ssl.create_default_context()
    try:
        import certifi  # type: ignore
        ctx.load_verify_locations(cafile=certifi.where())
    except ImportError:
        # Without certifi, falls back to the OS trust store (which the bootstrap's
        # SSL_CERT_FILE also masks, but load_default_certs reads from the system).
        ctx.load_default_certs()
    ctx.load_verify_locations(cafile=_agent_config.EXECUTOR_CA_PATH)
    ctx.load_cert_chain(
        certfile=_agent_config.EXECUTOR_CERT_PATH,
        keyfile=_agent_config.EXECUTOR_KEY_PATH,
    )
    return ctx


def mtls_httpx_kwargs(url: str) -> dict:
    """
    Returns kwargs for httpx.AsyncClient/Client (verify=..., cert=...) that
    apply mTLS when appropriate. Useful for sync/uploader, sync/downloader, etc.
    """
    if is_local_server(url):
        return {"verify": False}
    return {"verify": build_mtls_ssl_context()}


def classify_dataset_type(dataset_type: str) -> str:
    """Classifies the dataset type: raster, tabular or vector."""
    if dataset_type in ("raster", "tiff", "tif"):
        return "raster"
    if dataset_type in ("csv", "xlsx", "tabular"):
        return "tabular"
    return "vector"
