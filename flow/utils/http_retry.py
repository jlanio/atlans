# flow/utils/http_retry.py
"""
Retry with exponential backoff for transient executor -> server HTTP calls.

Two entrypoints:
  - async_request_with_retry: 1 async httpx request, retries transient 5xx and
    transport errors. Used by ChangeDetector.
  - retry_sync: wraps an arbitrary synchronous block (e.g. presign + upload in
    pin.py, where the pre-signed URL must be re-obtained on every attempt).

Policy: status 502/503/504 and connection/timeout errors are transient.
4xx (incl. 404) and generic 500 are not retried — they propagate immediately.

How long to wait between attempts is NOT decided here: it comes from
`flow/utils/backoff.py`, which is where the growth, ceiling and jitter policy
now lives. What this module decides is only what is HTTP-specific —
which statuses and which exceptions count as transient.
"""
import asyncio
import time
from typing import Any, Callable, Iterable, TypeVar

import httpx

from flow.utils.backoff import espera_exponencial
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_RETRYABLE_STATUS = frozenset({502, 503, 504})
_TRANSPORT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.WriteError,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)

T = TypeVar("T")


async def async_request_with_retry(
    method: str,
    url: str,
    *,
    client_kwargs: dict | None = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_status: Iterable[int] = _DEFAULT_RETRYABLE_STATUS,
    label: str = "",
    **request_kwargs: Any,
) -> httpx.Response:
    """Executes 1 async httpx request with exponential retry.

    - Transport errors (connect/read/timeout): retries; propagates the last one when exhausted.
    - Status in retryable_status (502/503/504 by default): retries; returns the last
      Response when exhausted (the caller decides raise_for_status).
    - Other statuses (200/4xx/500): returns immediately, no retry.
    """
    retryable = frozenset(retryable_status)
    last_exc: Exception | None = None
    tag = label or f"{method} {url}"

    for attempt in range(1, max_attempts + 1):
        # The wait that FOLLOWS this attempt. Computed before sleeping because
        # it goes into the log — the reader needs to know how much time will pass.
        espera = espera_exponencial(attempt - 1, inicial=base_delay, teto=max_delay)
        try:
            async with httpx.AsyncClient(**(client_kwargs or {})) as client:
                resp = await client.request(method, url, **request_kwargs)
            if resp.status_code in retryable and attempt < max_attempts:
                logger.warning(
                    "HTTP %s retornou %d (tentativa %d/%d) — retentando em %.1fs.",
                    tag, resp.status_code, attempt, max_attempts, espera,
                )
                await asyncio.sleep(espera)
                continue
            return resp
        except _TRANSPORT_ERRORS as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning(
                    "HTTP %s falhou no transporte (tentativa %d/%d): %s — retentando em %.1fs.",
                    tag, attempt, max_attempts, exc, espera,
                )
                await asyncio.sleep(espera)
            else:
                logger.error("HTTP %s falhou apos %d tentativas: %s", tag, max_attempts, exc)
                raise
    # Unreachable in practice, but satisfies the type checker.
    if last_exc:
        raise last_exc
    raise RuntimeError(f"HTTP {tag}: retry esgotado sem resposta nem excecao.")


# "Broad" transients for best-effort uploads: includes the network builtins
# besides httpx's transport errors.
_SYNC_DEFAULT_RETRYABLE: tuple[type[BaseException], ...] = _TRANSPORT_ERRORS + (
    ConnectionError, TimeoutError, OSError,
)


def retry_sync(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exc: tuple[type[BaseException], ...] = _SYNC_DEFAULT_RETRYABLE,
    label: str = "",
) -> T:
    """Executes a synchronous block `fn` with exponential retry.

    Useful when the retry spans more than one request (e.g. re-obtaining a pre-signed
    URL and retrying the upload). Retries exceptions in `retryable_exc` (default: network/
    transport errors). For best-effort uploads, pass `retryable_exc=(Exception,)`
    to retry any failure. Other exceptions propagate immediately.
    """
    for attempt in range(1, max_attempts + 1):
        espera = espera_exponencial(attempt - 1, inicial=base_delay, teto=max_delay)
        try:
            return fn()
        except retryable_exc as exc:
            if attempt >= max_attempts:
                logger.error("%s falhou apos %d tentativas: %s", label or "retry_sync", max_attempts, exc)
                raise
            logger.warning(
                "%s falhou (tentativa %d/%d): %s — retentando em %.1fs.",
                label or "retry_sync", attempt, max_attempts, exc, espera,
            )
            time.sleep(espera)
    raise RuntimeError(f"{label or 'retry_sync'}: retry esgotado.")
