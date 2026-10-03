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
CONTROL_TIMEOUT = 30.0

# READ/WRITE timeout for transfers (PUT/GET of bytes to/from MinIO).
TRANSFER_TIMEOUT = 300.0


class HTTPClient:
    """Holds a reusable `httpx.AsyncClient`, created on demand.

    Lazy because the sync components are built OUTSIDE the event loop
    (main.py assembles the SyncManagers before calling `run()`): an AsyncClient
    created there would be born bound to the wrong loop.

    The default timeout already covers the transfer; the control calls pass
    `timeout=CONTROL_TIMEOUT` per request.
    """

    def __init__(self, httpx_kwargs: dict):
        self._kwargs = httpx_kwargs
        self._client: httpx.AsyncClient | None = None

    def __call__(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    CONTROL_TIMEOUT,
                    read=TRANSFER_TIMEOUT,
                    write=TRANSFER_TIMEOUT,
                ),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
                **self._kwargs,
            )
        return self._client

    async def aclose(self) -> None:
        """Closes the client. A shared pool needs an explicit close at
        shutdown, otherwise the sockets leak until the process dies."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
