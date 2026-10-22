# flow/utils/download_seguro.py
"""Downloads a URL to a temporary file — the origin "URL" of DataInput.

`safe_httpx_request` answers with the body in memory, which is right for an API
and wrong for a file: a municipal grid or a year of weather stations is hundreds
of MB. Here the body goes to disk chunk by chunk and the download stops as soon
as it passes the limit, with the same defenses as the other outbound nodes:

  - SSRF with IP pinning (`pin_request_target`), redone on EVERY hop and every
    attempt — a 3xx pointing to an internal address is refused like the
    address typed;
  - redirects followed here, never by httpx, up to `MAX_REDIRECTS`;
  - credential headers dropped when a hop changes origin;
  - per-host circuit breaker, shared with HttpRequest (same key);
  - retry only on what is transient (network, 429, 5xx) — a GET can be repeated.

The caller removes the returned file.
"""
import asyncio
import os
import re
import tempfile
from dataclasses import dataclass, field
from email.message import Message
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

import httpx

from flow.utils.autenticacao_http import same_origin, without_credentials
from flow.utils.backoff import espera_exponencial
from flow.utils.circuit_breaker import CircuitOpenError, get_circuit_breaker
from flow.utils.geo_helpers import (
    is_tls_verify_error,
    pin_request_target,
    tls_verify_error_message,
)
from flow.utils.identidade import user_agent
from flow.utils.logger import get_logger

logger = get_logger(__name__)

# How many 3xx a download follows. A storage behind a portal is usually one or
# two hops (portal → signed URL); five leaves room without letting a loop of
# redirects hold the run.
MAX_REDIRECTS = 5

# The same transient set as HttpRequest: the server said "overloaded" or "try
# again". Other 4xx are request errors — repeating gives the same answer.
_STATUS_REPETIVEIS = frozenset({429, 500, 502, 503, 504})
_WAIT_CEILING_S = 30.0

# Chunk written to disk at a time. Large enough that the thread hop per write
# costs nothing next to the network, small enough to keep memory flat.
_CHUNK = 1024 * 1024

# What is kept of the start of the file for the format detection (magic bytes,
# HTML page, GeoJSON) — the caller should not have to reopen the file.
_INICIO = 8192

# Query parameters whose value is a secret or a temporary signature (S3, Azure,
# GeoServer's authkey). They are masked wherever the URL is shown: run log,
# error message and the node's `metadata`, which is stored with the run.
_PARAM_SECRETO = re.compile(
    r"(?i)(token|key|secret|senha|password|passwd|signature|^sig$|auth|credential)"
)


@dataclass
class Download:
    """A finished download. `caminho` is a temporary file the caller removes."""
    caminho: str
    url_final: str
    status: int
    headers: dict = field(default_factory=dict)
    tamanho: int = 0
    inicio: bytes = b""


@dataclass
class _Redirecionamento:
    location: str
    status: int


@dataclass
class _Falha:
    """An HTTP answer that is neither success nor redirect."""
    status: int
    trecho: str


@dataclass
class _Recusa:
    """Our own policy refused (size limit). Kept apart from an exception raised
    inside the circuit breaker, which would count it as a failure of the HOST:
    five oversized files would open the circuit for every workflow that talks
    to it."""
    erro: Exception


class _LimiteExcedido(Exception):
    pass


def para_registro(url: str) -> str:
    """The URL as it can be shown: without user/password and with the value of
    secret-looking query parameters replaced by `***`."""
    try:
        partes = urlsplit(url)
        host = partes.hostname or ""
        porta = partes.port
    except ValueError:
        return url
    if ":" in host:  # IPv6 goes in brackets in the URL
        host = f"[{host}]"
    netloc = f"{host}:{porta}" if porta else host
    pares = parse_qsl(partes.query, keep_blank_values=True)
    query = urlencode(
        [(k, "***" if _PARAM_SECRETO.search(k) else v) for k, v in pares], safe="*/:",
    )
    return urlunsplit((partes.scheme, netloc, partes.path, query, ""))


def nome_sugerido(headers) -> str:
    """The file name the server suggests in `Content-Disposition`, or "".

    `email.message` already decodes the RFC 2231/5987 form
    (`filename*=UTF-8''munic%C3%ADpios.zip`), which is what portals send for a
    name with accents. Only the last path component is kept: the name serves
    to detect the format and to tell the user what came, never as a path.
    """
    valor = headers.get("content-disposition") if headers else None
    if not valor:
        return ""
    mensagem = Message()
    mensagem["content-disposition"] = valor
    try:
        nome = mensagem.get_filename() or ""
    except (ValueError, LookupError):
        return ""
    return re.split(r"[\\/]", nome.strip())[-1].strip()


def _grande_demais(limite: int, declarado: int | None = None) -> ValueError:
    mb = limite / (1024 * 1024)
    detalhe = f" (o servidor anunciou {declarado / (1024 * 1024):.1f} MB)" if declarado else ""
    return ValueError(
        f"O arquivo passa do tamanho máximo do download, {mb:.0f} MB{detalhe}. "
        "Aumente 'Tamanho máximo do download (MB)' no nó, ou use 0 para tirar o limite."
    )


async def _ler_trecho(response: httpx.Response, limite: int) -> str:
    """First bytes of an error body, for the message — a portal's 404 page or an
    API's JSON error says more than the status code alone."""
    lido = bytearray()
    try:
        async for parte in response.aiter_bytes():
            lido.extend(parte)
            if len(lido) >= limite:
                break
    except httpx.HTTPError:
        pass
    texto = bytes(lido[:limite]).decode("utf-8", errors="replace")
    return " ".join(texto.split())[:200]


async def _tentar(
    pinned_url: str, req_headers: dict, extensions: dict | None,
    url: str, timeout: float, max_bytes: int | None,
):
    """One GET. Returns Download, _Redirecionamento, _Falha or _Recusa; raises
    only what the circuit breaker must count (network, TLS)."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        request = client.build_request("GET", pinned_url, headers=req_headers)
        if extensions:
            request.extensions.update(extensions)
        try:
            response = await client.send(request, stream=True)
        except Exception as exc:
            # The message cites the hostname typed, not the pinned IP.
            if is_tls_verify_error(exc):
                raise RuntimeError(tls_verify_error_message(url, exc)) from exc
            raise

        try:
            if response.is_redirect:
                return _Redirecionamento(response.headers["location"], response.status_code)
            if not response.is_success:
                return _Falha(response.status_code, await _ler_trecho(response, 2048))

            declarado = response.headers.get("content-length", "")
            if max_bytes and declarado.isdigit() and int(declarado) > max_bytes:
                return _Recusa(_grande_demais(max_bytes, int(declarado)))

            fd, caminho = tempfile.mkstemp(prefix="atlans-download-")
            total = 0
            inicio = bytearray()
            try:
                with os.fdopen(fd, "wb") as destino:
                    async for parte in response.aiter_bytes(_CHUNK):
                        total += len(parte)
                        # Counts DECODED bytes — what goes to disk —, so a gzip
                        # transfer that inflates is also caught.
                        if max_bytes and total > max_bytes:
                            raise _LimiteExcedido()
                        if len(inicio) < _INICIO:
                            inicio.extend(parte[: _INICIO - len(inicio)])
                        await asyncio.to_thread(destino.write, parte)
            except _LimiteExcedido:
                _remover(caminho)
                return _Recusa(_grande_demais(max_bytes))
            except BaseException:
                _remover(caminho)
                raise

            return Download(
                caminho=caminho,
                url_final=url,
                status=response.status_code,
                headers=dict(response.headers),
                tamanho=total,
                inicio=bytes(inicio),
            )
        finally:
            await response.aclose()


def _remover(caminho: str) -> None:
    try:
        os.unlink(caminho)
    except OSError:
        pass


def _mensagem_de_falha(url: str, falha: _Falha) -> str:
    dica = ""
    if falha.status in (401, 403):
        dica = (" O servidor exige autenticação ou recusou a que foi enviada: "
                "confira a credencial do nó.")
    elif falha.status == 404:
        dica = " Confira o endereço: o arquivo pode ter mudado de lugar ou de nome."
    trecho = f" Resposta: {falha.trecho}" if falha.trecho else ""
    return f"O servidor respondeu HTTP {falha.status} para {para_registro(url)}.{dica}{trecho}"


async def _com_tentativas(
    url: str, cabecalhos: dict, timeout: float, max_bytes: int | None, tentativas: int,
):
    """One hop (one URL), repeated on transient failure. Returns Download or
    _Redirecionamento."""
    breaker = get_circuit_breaker(f"http:{urlparse(url).netloc or url}")
    total = max(0, tentativas) + 1
    for tentativa in range(total):
        ultima = tentativa == total - 1
        # Validated and pinned again on every attempt: the IP of the previous
        # attempt may no longer be what the name resolves to. An SSRF refusal
        # (ValueError) is not retried and does not reach the circuit breaker.
        pinned_url, req_headers, extensions = await pin_request_target(url, cabecalhos)
        try:
            resultado = await breaker.call(
                _tentar, pinned_url, req_headers, extensions, url, timeout, max_bytes,
            )
        except CircuitOpenError as e:
            raise RuntimeError(str(e)) from e
        except httpx.TransportError as e:
            if ultima:
                raise RuntimeError(
                    f"Erro de rede no download de {para_registro(url)}: {e}"
                ) from e
            logger.warning(
                "Tentativa %d/%d do download falhou (%s) — repetindo.",
                tentativa + 1, total, e,
            )
        else:
            if isinstance(resultado, _Recusa):
                raise resultado.erro
            if not isinstance(resultado, _Falha):
                return resultado
            if ultima or resultado.status not in _STATUS_REPETIVEIS:
                raise RuntimeError(_mensagem_de_falha(url, resultado))
            logger.warning(
                "Tentativa %d/%d do download devolveu HTTP %s — repetindo.",
                tentativa + 1, total, resultado.status,
            )

        await asyncio.sleep(
            espera_exponencial(tentativa, inicial=0.5, teto=_WAIT_CEILING_S)
        )
    raise AssertionError("inalcançável")  # pragma: no cover


async def baixar_para_arquivo(
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = 60.0,
    max_bytes: int | None = None,
    tentativas: int = 2,
    max_redirects: int = MAX_REDIRECTS,
) -> Download:
    """GET `url` to a temporary file, following redirects with the defenses in
    the module docstring.

    `timeout` is per operation (connecting, each read), not for the whole
    download: a 800 MB file takes minutes and is fine while bytes keep coming;
    what it catches is a server that stopped answering. `max_bytes` None or 0
    removes the limit.
    """
    cabecalhos = dict(headers or {})
    if not any(k.lower() == "user-agent" for k in cabecalhos):
        # httpx's default (`python-httpx/x.y`) is blocked by some portals'
        # firewalls; this one says who is asking (flow/utils/identidade.py).
        cabecalhos["User-Agent"] = user_agent("entrada-de-dados")

    atual = url
    for salto in range(max_redirects + 1):
        resultado = await _com_tentativas(atual, cabecalhos, timeout, max_bytes, tentativas)
        if isinstance(resultado, Download):
            return resultado

        if salto == max_redirects:
            raise RuntimeError(
                f"Limite de {max_redirects} redirecionamentos atingido sem chegar ao "
                f"arquivo (último endereço: {para_registro(atual)})."
            )
        destino = str(httpx.URL(atual).join(resultado.location))
        # SEC: the destination of a 3xx is chosen by the remote server, not by the
        # user. On another origin the token would go to a host the other side
        # pointed to; on the same origin (`/dados` → `/dados/`) it goes along.
        if not same_origin(atual, destino):
            cabecalhos = without_credentials(cabecalhos)
        logger.info(
            "Redirecionamento %d (HTTP %s): %s → %s",
            salto + 1, resultado.status, para_registro(atual), para_registro(destino),
        )
        atual = destino

    raise AssertionError("inalcançável")  # pragma: no cover
