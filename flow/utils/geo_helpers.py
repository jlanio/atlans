"""Reusable helper functions for output nodes and credentials."""

import ipaddress
import os
import pathlib
import socket
from urllib.parse import urlparse


# ── File path validation (Path Traversal) ─────────────────────────────────────

# Base directories allowed for reading/writing files.
# Configure via ALLOWED_FILE_DIRS (comma-separated). Default: /data, /tmp
_ALLOWED_DIRS_RAW = os.getenv("ALLOWED_FILE_DIRS", "/data,/tmp")
ALLOWED_FILE_DIRS = [pathlib.Path(d.strip()).resolve() for d in _ALLOWED_DIRS_RAW.split(",") if d.strip()]


def validate_file_path(file_path: str, *, write: bool = False) -> pathlib.Path:
    """
    Validates that the file path is inside the allowed directories.
    Prevents path traversal (../../etc/passwd) and access to unauthorized directories.

    Args:
        file_path: Path provided by the user.
        write: If True, creates the parent directory if needed (inside the allowed directory).

    Returns:
        Resolved and validated pathlib.Path.

    Raises:
        ValueError: If the path is not inside the allowed directories.
    """
    if not file_path or not file_path.strip():
        raise ValueError("Caminho de arquivo não pode ser vazio.")

    resolved = pathlib.Path(file_path).resolve()

    # Checks whether it is INSIDE some allowed directory, comparing the
    # path hierarchy — not the textual prefix.
    #
    # `str(resolved).startswith(str(allowed_dir))` let through any SIBLING
    # directory whose name started the same: with `/data` allowed,
    # `/data-secreto/x.shp` and `/datax/y.shp` were accepted, because the
    # comparison was on strings, not paths. `is_relative_to` requires the
    # allowed directory to actually be an ancestor.
    is_allowed = any(
        resolved.is_relative_to(allowed_dir)
        for allowed_dir in ALLOWED_FILE_DIRS
    )
    if not is_allowed:
        raise ValueError(
            f"Acesso negado: o caminho '{file_path}' está fora dos diretórios permitidos "
            f"({', '.join(str(d) for d in ALLOWED_FILE_DIRS)}). "
            "Configure ALLOWED_FILE_DIRS para adicionar diretórios."
        )

    if write:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


def normalize_ows_endpoint_url(url: str) -> str:
    """Extracts the base endpoint of an OWS URL (WFS/WMS/WMTS).

    Geospatial servers (GeoServer, MapServer, etc) expose operations on one
    endpoint and distinguish the operation by query params (`service=WFS`,
    `request=GetCapabilities`, `version=2.0.0`). Client code (owslib,
    httpx) must receive only the base endpoint and add its own params
    — duplicating them causes conflicts (e.g. `version=1.3.0` in the input +
    `version=2.0.0` from the client breaks the negotiation).

    Examples:
        https://host/geoserver/PGGM/ows?service=wms&version=1.3.0&request=GetCapabilities
            -> https://host/geoserver/PGGM/ows
        https://host/geoserver/wfs/  -> https://host/geoserver/wfs
        https://host:8080/path?x=1#frag -> https://host:8080/path
        ""          -> ""    (lets downstream validation fail)
        "naourl"    -> "naourl"  (no scheme; validate_url_ssrf rejects it)
    """
    if not url or not isinstance(url, str):
        return url or ""
    url = url.strip()
    parsed = urlparse(url)
    # Without scheme/netloc we don't have a parseable URL — return the original so
    # downstream validation produces a clear message.
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path.rstrip("/") or ""
    return f"{parsed.scheme}://{parsed.netloc}{path}"


# ── TLS verification errors ───────────────────────────────────────────────────

_TLS_VERIFY_MARKERS = ("CERTIFICATE_VERIFY_FAILED", "SSLCertVerificationError")


def is_tls_verify_error(exc: BaseException | None) -> bool:
    """True if `exc` — or one of its causes — is a TLS chain validation failure.

    Nodes that talk HTTPS to a third-party server receive this error wrapped
    several times (`requests.exceptions.SSLError` → `urllib3.MaxRetryError` →
    `ssl.SSLCertVerificationError`), and the intermediate layers do not preserve
    the original type — so we check type AND text, the same pattern already used in
    `executor/connection.py` for an expired cert.

    The distinction matters because an invalid chain is not a transient failure:
    retrying only multiplies the wait before the same error.
    """
    import ssl

    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, ssl.SSLCertVerificationError):
            return True
        if any(marker in str(exc) for marker in _TLS_VERIFY_MARKERS):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def tls_verify_error_message(url: str, exc: BaseException) -> str:
    """Actionable message for a certificate validation failure in a node."""
    host = urlparse(url).hostname or url
    return (
        f"Não foi possível validar o certificado TLS de '{host}'. "
        "Isso não é falha temporária — as causas prováveis são o servidor enviar "
        "uma cadeia incompleta (falta o certificado intermediário) ou o trust "
        "store do executor não incluir as CAs públicas. "
        "Confira o certificado do servidor em https://www.ssllabs.com/ssltest/ e, "
        "se estiver íntegro, verifique SSL_CERT_FILE/REQUESTS_CA_BUNDLE no "
        f"executor. Detalhe: {exc}"
    )


async def safe_httpx_request(
    method: str,
    url: str,
    *,
    timeout: float = 15.0,
    follow_redirects: bool = False,
    headers: dict | None = None,
    content: bytes | None = None,
    json: dict | None = None,
    params: dict | None = None,
    max_response_bytes: int | None = None,
):
    """Makes an HTTP request with IP pinning to prevent DNS rebinding.

    Flow:
      1. validate_url_ssrf: resolves hostname → IP, rejects internal IPs.
      2. Rewrites the URL replacing the hostname with the literal IP — httpx connects
         to the resolved IP regardless of DNS at request time.
      3. Host header: original hostname (for virtual hosts on the server).
      4. SNI original hostname via extensions (HTTPS validates the cert by name).

    Without this, an attacker with DNS TTL=0 could:
      - validate_url_ssrf resolves evil.com → 1.2.3.4 (public) PASS
      - httpx.get(url) resolves evil.com → 169.254.169.254 (metadata) FAIL

    Blocks redirects by default (follow_redirects=False): if the server
    answers 302 to an internal URL, without SSRF re-evaluation we become a proxy.
    A caller that needs redirects must revalidate manually.

    max_response_bytes: limits the body read (defense against a huge response).
    """
    import httpx as _httpx
    import asyncio as _asyncio

    parsed = urlparse(url)
    resolved_ip, hostname = await _asyncio.to_thread(validate_url_ssrf, url)

    # Reescreve URL: troca hostname por IP, preserva porta + path + query.
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # IPv6 needs brackets in the URL.
    ip_in_url = f"[{resolved_ip}]" if ":" in resolved_ip else resolved_ip
    new_netloc = f"{ip_in_url}:{port}"
    pinned_url = parsed._replace(netloc=new_netloc).geturl()

    # Host header with the original name (the server may host several virtual hosts).
    req_headers = dict(headers or {})
    req_headers["Host"] = hostname if not parsed.port else f"{hostname}:{port}"

    # Extensions: sni_hostname ensures the TLS handshake presents the correct
    # name for validating the server's cert.
    extensions = {"sni_hostname": hostname} if parsed.scheme == "https" else None

    async with _httpx.AsyncClient(
        timeout=timeout, follow_redirects=follow_redirects,
    ) as client:
        request = client.build_request(
            method, pinned_url, headers=req_headers,
            content=content, json=json, params=params,
        )
        if extensions:
            request.extensions.update(extensions)
        try:
            response = await client.send(request)
        except Exception as exc:
            # An invalid TLS chain arrives as httpx.ConnectError carrying the raw
            # OpenSSL message. Translating it here covers at once every node
            # that talks HTTPS through this helper (HttpRequest, WFS,
            # webhook) instead of repeating the handling in each. Uses `url`, not
            # `pinned_url`: the message must cite the hostname the user
            # typed, not the IP we pinned.
            if is_tls_verify_error(exc):
                raise RuntimeError(tls_verify_error_message(url, exc)) from exc
            raise

        if max_response_bytes is not None:
            # Le no max N bytes; truncar protege memoria.
            await response.aread()
            if len(response.content) > max_response_bytes:
                raise ValueError(
                    f"Resposta excedeu o limite de {max_response_bytes} bytes."
                )

        return response


# CGNAT (RFC 6598) is not flagged as `is_private` in every Python version;
# from inside a cloud, 100.64/10 reaches the provider's internal services.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _dangerous_address(ip) -> bool:
    """True for an IP that must not be the target of an outbound request (SSRF)."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:169.254.169.254 → o IPv4 embutido
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT)
    )


def validate_url_ssrf(url: str) -> tuple[str, str]:
    """
    Blocks URLs with an invalid scheme or that resolve to internal/private addresses.
    Returns (resolved_ip, hostname) for direct use in the request (prevents DNS rebinding).
    Raises ValueError if the URL is considered unsafe (SSRF).
    Synchronous function — use asyncio.to_thread() in async contexts.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme '{parsed.scheme}' não permitido. Use http ou https.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sem hostname válido.")

    # Blocks hostnames that are already an internal IP. Audit (SEG-81): before, the
    # `raise` in this block fell into the `except ValueError` just below (the same
    # type used for "not a literal IP") and was SWALLOWED — the direct check became
    # a dead letter. Now it uses `_dangerous_address`, with no try/except around
    # the raise.
    try:
        direct_ip = ipaddress.ip_address(hostname)
    except ValueError:
        direct_ip = None  # hostname is not a literal IP — ok, let's resolve it
    if direct_ip is not None and _dangerous_address(direct_ip):
        raise ValueError(
            f"Requisições para endereços internos/privados não são permitidas ({hostname})."
        )

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Não foi possível resolver o hostname '{hostname}'.")

    # Checks ALL resolved addresses, not just the first: a malicious DNS server
    # returns a public IP followed by 169.254.169.254/10.x — checking
    # only [0] let the second one through (DNS rebinding / multi-record).
    resolved_ip = infos[0][4][0]
    for info in infos:
        candidato = info[4][0]
        if _dangerous_address(ipaddress.ip_address(candidato)):
            raise ValueError(
                f"Requisições para endereços internos/privados não são permitidas ({candidato})."
            )

    return resolved_ip, hostname


def ensure_extension(path: str, ext: str) -> str:
    """Ensures `path` ends with the extension `ext` (e.g. '.shp', '.parquet')."""
    if not ext.startswith("."):
        ext = f".{ext}"
    if not path.lower().endswith(ext.lower()):
        return path + ext
    return path


# ── Helpers GeoDataFrame ─────────────────────────────────────────────────────

def ensure_gdf_crs(gdf, target_crs: str):
    """Ensures the GeoDataFrame is in the target CRS.

    - If the GDF already has a CRS different from the target, reprojects.
    - If the GDF has no CRS, assigns the target.
    - If target_crs is empty/None, returns unchanged.

    Returns the GeoDataFrame (may be a new object after reprojection).
    Synchronous function — use asyncio.to_thread() in async contexts.
    """
    if not target_crs:
        return gdf
    if gdf.crs is not None and str(gdf.crs) != target_crs:
        return gdf.to_crs(target_crs)
    if gdf.crs is None:
        return gdf.set_crs(target_crs)
    return gdf


def gdf_para_geojson(gdf, crs: str | None = None, *, nat_as_null: bool = False) -> str:
    """Serializes a GeoDataFrame as GeoJSON text — the single entry point for every
    node that writes or sends GeoJSON.

    - `crs`: reprojects first, with the `ensure_gdf_crs` rule (without a CRS, the
      target one is assigned). Empty/None serializes in the CRS the GDF is in.
    - Datetime columns become text (`astype(str)`), because `to_json` does not
      serialize them ("Object of type Timestamp is not JSON serializable").
    - `nat_as_null`: a missing date (NaT) comes out as `null` instead of "NaT". The
      nodes that serialized with raw `to_json` (SaveToS3, SendWebhook, HttpRequest,
      the pin fallback) already delivered `null` in an all-empty date column —
      a `dt_cancelamento` with no value in any feature —, and that is what they keep
      delivering. Those that went through `astype(str)` (SaveGeoJSON, DataOutput,
      PublishMap, SendEmail) always wrote "NaT", and stay the same.

    The conversion is done on a COPY, and only when there is a datetime column. The
    incoming GDF is the previous node's output (`get_first_gdf` returns the
    parent's, and `ensure_gdf_crs` returns the same object when the CRS already
    matches), which siblings in the same batch — running in parallel, in threads —
    and `$Alias` expressions keep reading. Converting in place made all of them see
    the dates as strings.

    Synchronous function — use asyncio.to_thread() in async contexts.
    """
    gdf = ensure_gdf_crs(gdf, crs)
    date_columns = gdf.select_dtypes(include=["datetime", "datetimetz"]).columns
    if len(date_columns):
        gdf = gdf.copy()
        for col in date_columns:
            texto = gdf[col].astype(str)
            if nat_as_null:
                texto = texto.where(gdf[col].notna(), None)
            gdf[col] = texto
    return gdf.to_json()


def slugify_label(label: str) -> str:
    """Generates a safe file name from a label.

    Transliterating accents is mandatory, not cosmetic: `str.isalnum()` returns
    True for 'Á', so the previous version produced 'Áreas_Urbanas' — which does
    not match the charset required by the s3_key validator ([A-Za-z0-9_-./]). In a
    pt-BR product that is the common case, and the effect was the artifact upload
    being rejected with 400 and the run finishing "successfully" with no artifact.

    NFKD separates the base character from the diacritic; discarding the combining
    marks (category Mn) leaves the ASCII equivalent. Whatever is still outside
    the safe set becomes '_'.
    """
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", label or "")
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = "".join(
        c if (c.isascii() and c.isalnum()) or c in "-_" else "_"
        for c in ascii_only
    )
    # An empty name would generate a key ending in '/', which the validator rejects.
    return slug or "arquivo"


# ── Geometric validations shared by the spatial nodes ─────────────────────────
# Previously reimplemented inline in ~12 nodes (intersection, union, difference, etc.).
# In binary nodes (A, B), `BaseNode.get_pair` is what applies them.

_UNSUPPORTED_GEOM_TYPES = {"GeometryCollection", "None"}


def require_crs(gdf, *, name: str = "camada") -> None:
    """Raises ValueError if the GeoDataFrame has no CRS defined."""
    if gdf.crs is None:
        raise ValueError(
            f"A {name} de entrada não possui CRS definido. "
            "Adicione um nó de reprojeção antes desta operação."
        )


def require_same_crs(gdf_a, gdf_b, *, operation: str = "operação") -> None:
    """Raises ValueError if the two layers have different CRSs."""
    if gdf_a.crs != gdf_b.crs:
        raise ValueError(
            "As camadas possuem CRS diferentes. Adicione um nó de reprojeção "
            f"para padronizar antes da {operation}."
        )


def reject_unsupported_geom_types(*gdfs, operation: str = "operação") -> None:
    """Raises TypeError if any layer contains a GeometryCollection/null geometry."""
    present: set[str] = set()
    for gdf in gdfs:
        present |= set(gdf.geometry.geom_type.unique())
    if present & _UNSUPPORTED_GEOM_TYPES:
        raise TypeError(
            f"Geometria incompatível para {operation}: {present}. "
            "Use apenas ponto, linha ou polígono."
        )


def align_crs(target, other):
    """Reprojects `other` to the CRS of `target` if they differ; returns `other`."""
    if target.crs is not None and other.crs is not None and target.crs != other.crs:
        return other.to_crs(target.crs)
    return other


# ── Distance unit vs CRS unit ─────────────────────────────────────────────────

_METRE_UNIT_NAMES = {"metre", "meter", "metres", "meters", "m"}


def crs_is_metric(crs) -> bool:
    """True if the CRS is projected and its linear unit is the meter."""
    if crs is None or crs.is_geographic:
        return False
    try:
        return (crs.axis_info[0].unit_name or "").lower() in _METRE_UNIT_NAMES
    except (IndexError, AttributeError):
        return False


def working_crs_for_unit(gdf, unit: str):
    """CRS in which a distance expressed in `unit` is valid.

    - unit='meters'  → projected CRS in meters (estimated UTM, if the current one doesn't fit)
    - unit='degrees' → geographic CRS (the current one's geodetic_crs, or EPSG:4326)

    Returns None when the current CRS already fits (no reprojection needed).
    Synchronous function — use asyncio.to_thread() in async contexts, since
    estimate_utm_crs() walks total_bounds.
    """
    crs = gdf.crs
    if unit == "meters":
        if crs_is_metric(crs):
            return None
        return gdf.estimate_utm_crs()
    if unit == "degrees":
        if crs.is_geographic:
            return None
        return crs.geodetic_crs or "EPSG:4326"
    raise ValueError(f"Unidade de distância não suportada: '{unit}'.")


def to_metric_crs(*gdfs):
    """Brings the layers to ONE common projected CRS, where area makes sense.

    The common CRS comes from the first layer with a CRS: its own, when already
    projected (in its unit — nothing is reprojected needlessly), or the UTM
    estimated from ITS extent, when geographic. The other layers go to that CRS.
    Estimating the UTM of each layer separately put A and B in different zones
    when their centers fell on opposite sides of a zone meridian — and an
    overlay between different CRSs only WARNS: the overlap percentage came out
    wrong, with no error.

    The UTM comes only from the first layer, not from the combined extent: it is
    the same one it always had (ComputeArea and Bifurcação measure the same; in
    OverlapPercentage the output stays in A's CRS, and a B layer already projected
    in the right zone does not change zone), and a B with no valid geometry does
    not disturb the estimate. An A with no valid geometry raises the ValueError from
    `estimate_utm_crs` ("NaN or None values are not allowed."), as before.

    A layer without a CRS comes back as is (there is nothing to reproject from).

    Returns a tuple in the order received. Synchronous function — use
    asyncio.to_thread() in async contexts (estimate_utm_crs walks
    total_bounds and to_crs is O(n)).
    """
    with_crs = [gdf for gdf in gdfs if gdf.crs is not None]
    if not with_crs:
        return gdfs
    alvo = with_crs[0].crs
    if alvo.is_geographic:
        alvo = with_crs[0].estimate_utm_crs()
    return tuple(
        gdf.to_crs(alvo) if gdf.crs is not None and gdf.crs != alvo else gdf
        for gdf in gdfs
    )
