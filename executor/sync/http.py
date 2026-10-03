# executor/sync/http.py
"""
Long-lived HTTP client for the GeoSync components.

Each uploader/downloader method opened an `async with httpx.AsyncClient(...)`
and closed it on leaving the block. Since `mtls_httpx_kwargs` injects the
client certificate, that meant a FULL mTLS handshake per request — and a
single `_upload_file` opened three (request URL, PUT to MinIO, confirm). On a
field network with 150ms of latency, a 3 KB .geojson cost the same protocol
time as a 2 GB raster.
"""
import httpx

# Timeout for CONTROL requests (request URL, confirm, list). Kept short on
# purpose: they are small calls and a failure needs to surface fast.
TIMEOUT_CONTROLE = 30.0

# READ/WRITE timeout for transfers (PUT/GET of bytes to/from MinIO).
TIMEOUT_TRANSFERENCIA = 300.0


class ClienteHTTP:
    """Holds a reusable `httpx.AsyncClient`, created on demand.

    Lazy because the sync components are built OUTSIDE the event loop
    (main.py assembles the SyncManagers before calling `run()`): an AsyncClient
    created there would be born bound to the wrong loop.

    The default timeout already covers the transfer; the control calls pass
    `timeout=TIMEOUT_CONTROLE` per request.
    """

    def __init__(self, httpx_kwargs: dict):
        self._kwargs = httpx_kwargs
        self._cliente: httpx.AsyncClient | None = None

    def __call__(self) -> httpx.AsyncClient:
        if self._cliente is None or self._cliente.is_closed:
            self._cliente = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    TIMEOUT_CONTROLE,
                    read=TIMEOUT_TRANSFERENCIA,
                    write=TIMEOUT_TRANSFERENCIA,
                ),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
                **self._kwargs,
            )
        return self._cliente

    async def aclose(self) -> None:
        """Closes the client. A shared pool needs an explicit close at
        shutdown, otherwise the sockets leak until the process dies."""
        if self._cliente is not None and not self._cliente.is_closed:
            await self._cliente.aclose()
        self._cliente = None
