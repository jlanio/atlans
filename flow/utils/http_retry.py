# flow/utils/http_retry.py
"""
Retry com backoff exponencial para chamadas HTTP transitorias executor -> servidor.

Dois entrypoints:
  - async_request_with_retry: 1 request httpx async, retenta 5xx transitorio e
    erros de transporte. Usado pelo ChangeDetector.
  - retry_sync: envolve um bloco sincrono arbitrario (ex: presign + upload do
    pin.py, onde a pre-signed URL precisa ser re-obtida a cada tentativa).

Politica: status 502/503/504 e erros de conexao/timeout sao transitorios.
4xx (incl. 404) e 500 generico nao sao retentados — propagam imediato.

Quanto esperar entre as tentativas NAO se decide aqui: vem de
`flow/utils/backoff.py`, que e onde a politica de crescimento, teto e jitter
passou a morar. O que este modulo decide e so o que e especifico de HTTP —
quais status e quais excecoes contam como transitorios.
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
    """Executa 1 request httpx async com retry exponencial.

    - Erros de transporte (connect/read/timeout): retenta; propaga o ultimo se esgotar.
    - Status em retryable_status (502/503/504 default): retenta; retorna o ultimo
      Response se esgotar (caller decide raise_for_status).
    - Demais status (200/4xx/500): retorna imediato, sem retry.
    """
    retryable = frozenset(retryable_status)
    last_exc: Exception | None = None
    tag = label or f"{method} {url}"

    for attempt in range(1, max_attempts + 1):
        # A espera que SEGUE esta tentativa. Calculada antes de dormir porque
        # entra no log — quem lê precisa saber quanto tempo vai passar.
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
    # Inalcancavel na pratica, mas satisfaz o type checker.
    if last_exc:
        raise last_exc
    raise RuntimeError(f"HTTP {tag}: retry esgotado sem resposta nem excecao.")


# Transitórios "amplos" para uploads best-effort: inclui os builtins de rede
# além dos erros de transporte do httpx.
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
    """Executa um bloco sincrono `fn` com retry exponencial.

    Util quando o retry abrange mais de um request (ex: re-obter pre-signed URL
    e re-tentar upload). Retenta exceções em `retryable_exc` (default: erros de
    rede/transporte). Para uploads best-effort, passe `retryable_exc=(Exception,)`
    para retentar qualquer falha. Demais exceções propagam imediato.
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
