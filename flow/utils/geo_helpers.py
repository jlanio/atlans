"""Funções auxiliares reutilizáveis para nós de saída e credenciais."""

import ipaddress
import os
import pathlib
import socket
from urllib.parse import urlparse


# ── Validação de caminhos de arquivo (Path Traversal) ─────────────────────────

# Diretórios base permitidos para leitura/escrita de arquivos.
# Configure via ALLOWED_FILE_DIRS (separado por vírgula). Default: /data, /tmp
_ALLOWED_DIRS_RAW = os.getenv("ALLOWED_FILE_DIRS", "/data,/tmp")
ALLOWED_FILE_DIRS = [pathlib.Path(d.strip()).resolve() for d in _ALLOWED_DIRS_RAW.split(",") if d.strip()]


def validate_file_path(file_path: str, *, write: bool = False) -> pathlib.Path:
    """
    Valida que o caminho de arquivo está dentro dos diretórios permitidos.
    Previne path traversal (../../etc/passwd) e acesso a diretórios não autorizados.

    Args:
        file_path: Caminho informado pelo usuário.
        write: Se True, cria o diretório pai se necessário (dentro do diretório permitido).

    Returns:
        pathlib.Path resolvido e validado.

    Raises:
        ValueError: Se o caminho não está dentro dos diretórios permitidos.
    """
    if not file_path or not file_path.strip():
        raise ValueError("Caminho de arquivo não pode ser vazio.")

    resolved = pathlib.Path(file_path).resolve()

    # Verifica se está DENTRO de algum diretório permitido, comparando a
    # hierarquia de caminho — não o prefixo textual.
    #
    # `str(resolved).startswith(str(allowed_dir))` deixava passar qualquer
    # diretório IRMÃO cujo nome começasse igual: com `/data` permitido,
    # `/data-secreto/x.shp` e `/datax/y.shp` eram aceitos, porque a comparação
    # era de string e não de caminho. `is_relative_to` exige que o diretório
    # permitido seja de fato um ancestral.
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
    """Extrai o endpoint base de uma URL OWS (WFS/WMS/WMTS).

    Servidores geoespaciais (GeoServer, MapServer, etc) expoem operacoes em um
    endpoint e diferenciam a operacao por query params (`service=WFS`,
    `request=GetCapabilities`, `version=2.0.0`). O codigo cliente (owslib,
    httpx) precisa receber so o endpoint base e adicionar seus proprios params
    — duplicar gera conflito (ex: `version=1.3.0` no input + `version=2.0.0`
    do cliente quebra a negociacao).

    Exemplos:
        https://host/geoserver/PGGM/ows?service=wms&version=1.3.0&request=GetCapabilities
            -> https://host/geoserver/PGGM/ows
        https://host/geoserver/wfs/  -> https://host/geoserver/wfs
        https://host:8080/path?x=1#frag -> https://host:8080/path
        ""          -> ""    (deixa validacao downstream falhar)
        "naourl"    -> "naourl"  (sem scheme; validate_url_ssrf rejeita)
    """
    if not url or not isinstance(url, str):
        return url or ""
    url = url.strip()
    parsed = urlparse(url)
    # Sem scheme/netloc nao temos uma URL parseavel — devolve original para
    # a validacao downstream produzir mensagem clara.
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path.rstrip("/") or ""
    return f"{parsed.scheme}://{parsed.netloc}{path}"


# ── Erros de verificação TLS ─────────────────────────────────────────────────

_TLS_VERIFY_MARKERS = ("CERTIFICATE_VERIFY_FAILED", "SSLCertVerificationError")


def is_tls_verify_error(exc: BaseException | None) -> bool:
    """True se `exc` — ou alguma causa dela — é falha de validação de cadeia TLS.

    Nós que falam HTTPS com servidor de terceiro recebem esse erro embrulhado
    várias vezes (`requests.exceptions.SSLError` → `urllib3.MaxRetryError` →
    `ssl.SSLCertVerificationError`), e as camadas intermediárias não preservam o
    tipo original — por isso checamos tipo E texto, mesmo padrão já usado em
    `executor/connection.py` para cert expirado.

    Distinguir importa porque cadeia inválida não é falha transiente: retentar
    só multiplica a espera antes do mesmo erro.
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
    """Mensagem acionável para falha de validação de certificado num nó."""
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
    """Faz request HTTP com IP pinning para prevenir DNS rebinding.

    Fluxo:
      1. validate_url_ssrf: resolve hostname → IP, rejeita IPs internos.
      2. Reescreve URL trocando hostname por IP literal — httpx conecta no IP
         resolvido independente do DNS no momento do request.
      3. Header Host: hostname original (para virtualhost no servidor).
      4. SNI hostname original via extensions (HTTPS valida cert pelo nome).

    Sem isso, o atacante com DNS TTL=0 podia:
      - validate_url_ssrf resolve evil.com → 1.2.3.4 (publico) PASS
      - httpx.get(url) resolve evil.com → 169.254.169.254 (metadata) FAIL

    Bloqueia redirects por default (follow_redirects=False): se servidor
    responde 302 para URL interna, sem reavaliacao SSRF, viramos proxy.
    Caller que precisa de redirect deve revalidar manualmente.

    max_response_bytes: limita corpo lido (defesa contra resposta gigante).
    """
    import httpx as _httpx
    import asyncio as _asyncio

    parsed = urlparse(url)
    resolved_ip, hostname = await _asyncio.to_thread(validate_url_ssrf, url)

    # Reescreve URL: troca hostname por IP, preserva porta + path + query.
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # IPv6 precisa de colchetes na URL.
    ip_in_url = f"[{resolved_ip}]" if ":" in resolved_ip else resolved_ip
    new_netloc = f"{ip_in_url}:{port}"
    pinned_url = parsed._replace(netloc=new_netloc).geturl()

    # Host header com nome original (servidor pode hospedar varios virtualhosts).
    req_headers = dict(headers or {})
    req_headers["Host"] = hostname if not parsed.port else f"{hostname}:{port}"

    # Extensions: sni_hostname garante que TLS handshake apresente o nome
    # correto para validacao de cert do servidor.
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
            # Cadeia TLS invalida chega como httpx.ConnectError carregando a
            # mensagem crua do OpenSSL. Traduzir aqui cobre de uma vez todo no
            # que fala HTTPS por este helper (HttpRequest, WFS,
            # webhook) em vez de repetir o tratamento em cada um. Usa `url`, nao
            # `pinned_url`: a mensagem tem de citar o hostname que o usuario
            # digitou, nao o IP em que fizemos o pin.
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


# CGNAT (RFC 6598) não é marcada como `is_private` em todas as versões de Python;
# de dentro de uma nuvem, 100.64/10 alcança serviços internos do provedor.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _endereco_perigoso(ip) -> bool:
    """True para IP que não deve ser alvo de request de saída (SSRF)."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:169.254.169.254 → o IPv4 embutido
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT)
    )


def validate_url_ssrf(url: str) -> tuple[str, str]:
    """
    Bloqueia URLs com scheme inválido ou que resolvam para endereços internos/privados.
    Retorna (resolved_ip, hostname) para uso direto no request (previne DNS rebinding).
    Lança ValueError se a URL for considerada insegura (SSRF).
    Função síncrona — use asyncio.to_thread() em contextos async.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme '{parsed.scheme}' não permitido. Use http ou https.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sem hostname válido.")

    # Bloqueia hostnames que já são IP interno. Auditoria (SEG-81): antes, o
    # `raise` deste bloco caía no `except ValueError` logo abaixo (o mesmo tipo
    # usado para "não é um IP literal") e era ENGOLIDO — a checagem direta virava
    # letra morta. Agora usa `_endereco_perigoso`, sem try/except em volta do
    # raise.
    try:
        direct_ip = ipaddress.ip_address(hostname)
    except ValueError:
        direct_ip = None  # hostname não é um IP literal — ok, vamos resolver
    if direct_ip is not None and _endereco_perigoso(direct_ip):
        raise ValueError(
            f"Requisições para endereços internos/privados não são permitidas ({hostname})."
        )

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Não foi possível resolver o hostname '{hostname}'.")

    # Confere TODOS os endereços resolvidos, não só o primeiro: um servidor DNS
    # malicioso devolve um IP público seguido de 169.254.169.254/10.x — checar
    # só o [0] deixava o segundo passar (DNS rebinding / multi-registro).
    resolved_ip = infos[0][4][0]
    for info in infos:
        candidato = info[4][0]
        if _endereco_perigoso(ipaddress.ip_address(candidato)):
            raise ValueError(
                f"Requisições para endereços internos/privados não são permitidas ({candidato})."
            )

    return resolved_ip, hostname


def ensure_extension(path: str, ext: str) -> str:
    """Garante que `path` termine com a extensão `ext` (ex: '.shp', '.parquet')."""
    if not ext.startswith("."):
        ext = f".{ext}"
    if not path.lower().endswith(ext.lower()):
        return path + ext
    return path


# ── Helpers GeoDataFrame ─────────────────────────────────────────────────────

def ensure_gdf_crs(gdf, target_crs: str):
    """Garante que o GeoDataFrame esteja no CRS alvo.

    - Se o GDF já tem CRS diferente do alvo, reprojeta.
    - Se o GDF não tem CRS, atribui o alvo.
    - Se target_crs é vazio/None, retorna sem alteração.

    Retorna o GeoDataFrame (pode ser novo objeto após reprojeção).
    Função síncrona — use asyncio.to_thread() em contextos async.
    """
    if not target_crs:
        return gdf
    if gdf.crs is not None and str(gdf.crs) != target_crs:
        return gdf.to_crs(target_crs)
    if gdf.crs is None:
        return gdf.set_crs(target_crs)
    return gdf


def gdf_para_geojson(gdf, crs: str | None = None, *, nat_como_nulo: bool = False) -> str:
    """Serializa um GeoDataFrame como texto GeoJSON — o ponto único de todo nó
    que grava ou envia GeoJSON.

    - `crs`: reprojeta antes, com a regra do `ensure_gdf_crs` (sem CRS, o de
      destino é atribuído). Vazio/None serializa no CRS em que o GDF está.
    - Colunas datetime viram texto (`astype(str)`), porque `to_json` não as
      serializa ("Object of type Timestamp is not JSON serializable").
    - `nat_como_nulo`: a data ausente (NaT) sai `null` em vez de "NaT". Os nós
      que serializavam com o `to_json` cru (SaveToS3, SendWebhook, HttpRequest,
      o fallback do pin) já entregavam `null` numa coluna de data toda vazia —
      um `dt_cancelamento` sem valor em nenhuma feição —, e é o que continuam
      entregando. Os que passavam por `astype(str)` (SaveGeoJSON, DataOutput,
      PublishMap, SendEmail) sempre gravaram "NaT", e seguem igual.

    A conversão é feita numa CÓPIA, e só quando há coluna datetime. O GDF que
    chega é o output do nó anterior (`get_first_gdf` devolve o do pai, e
    `ensure_gdf_crs` devolve o mesmo objeto quando o CRS já bate), que irmãos do
    mesmo batch — rodando em paralelo, em threads — e expressões `$Alias`
    continuam lendo. Converter in-place fazia todos eles verem as datas como
    string.

    Função síncrona — use asyncio.to_thread() em contextos async.
    """
    gdf = ensure_gdf_crs(gdf, crs)
    colunas_data = gdf.select_dtypes(include=["datetime", "datetimetz"]).columns
    if len(colunas_data):
        gdf = gdf.copy()
        for col in colunas_data:
            texto = gdf[col].astype(str)
            if nat_como_nulo:
                texto = texto.where(gdf[col].notna(), None)
            gdf[col] = texto
    return gdf.to_json()


def slugify_label(label: str) -> str:
    """Gera nome de arquivo seguro a partir de um label.

    Transliterar acentos é obrigatório, não cosmético: `str.isalnum()` devolve
    True para 'Á', então a versão anterior produzia 'Áreas_Urbanas' — que não
    casa com o charset exigido pelo validador de s3_key ([A-Za-z0-9_-./]). Num
    produto pt-BR isso é o caso comum, e o efeito era o upload do artefato ser
    recusado com 400 e o run terminar "com sucesso" sem artefato nenhum.

    NFKD separa o caractere base do diacrítico; descartar os combinantes
    (categoria Mn) deixa o ASCII equivalente. O que ainda sobrar fora do
    conjunto seguro vira '_'.
    """
    import unicodedata

    decomposto = unicodedata.normalize("NFKD", label or "")
    ascii_only = "".join(c for c in decomposto if not unicodedata.combining(c))
    slug = "".join(
        c if (c.isascii() and c.isalnum()) or c in "-_" else "_"
        for c in ascii_only
    )
    # Nome vazio geraria uma key terminando em '/', que o validador recusa.
    return slug or "arquivo"


# ── Validações geométricas compartilhadas pelos nós spatial ───────────────────
# Antes reimplementadas inline em ~12 nós (intersection, union, difference, etc.).
# Nos nós binários (A, B), quem as aplica é `BaseNode.get_pair`.

_UNSUPPORTED_GEOM_TYPES = {"GeometryCollection", "None"}


def require_crs(gdf, *, name: str = "camada") -> None:
    """Levanta ValueError se o GeoDataFrame não tem CRS definido."""
    if gdf.crs is None:
        raise ValueError(
            f"A {name} de entrada não possui CRS definido. "
            "Adicione um nó de reprojeção antes desta operação."
        )


def require_same_crs(gdf_a, gdf_b, *, operation: str = "operação") -> None:
    """Levanta ValueError se as duas camadas têm CRS diferentes."""
    if gdf_a.crs != gdf_b.crs:
        raise ValueError(
            "As camadas possuem CRS diferentes. Adicione um nó de reprojeção "
            f"para padronizar antes da {operation}."
        )


def reject_unsupported_geom_types(*gdfs, operation: str = "operação") -> None:
    """Levanta TypeError se alguma camada contém GeometryCollection/geometria nula."""
    present: set[str] = set()
    for gdf in gdfs:
        present |= set(gdf.geometry.geom_type.unique())
    if present & _UNSUPPORTED_GEOM_TYPES:
        raise TypeError(
            f"Geometria incompatível para {operation}: {present}. "
            "Use apenas ponto, linha ou polígono."
        )


def align_crs(target, other):
    """Reprojeta `other` para o CRS de `target` se diferirem; retorna `other`."""
    if target.crs is not None and other.crs is not None and target.crs != other.crs:
        return other.to_crs(target.crs)
    return other


# ── Unidade de distância vs unidade do CRS ───────────────────────────────────

_METRE_UNIT_NAMES = {"metre", "meter", "metres", "meters", "m"}


def crs_is_metric(crs) -> bool:
    """True se o CRS é projetado e sua unidade linear é o metro."""
    if crs is None or crs.is_geographic:
        return False
    try:
        return (crs.axis_info[0].unit_name or "").lower() in _METRE_UNIT_NAMES
    except (IndexError, AttributeError):
        return False


def working_crs_for_unit(gdf, unit: str):
    """CRS no qual uma distância expressa em `unit` é válida.

    - unit='meters'  → CRS projetado em metros (UTM estimado, se o atual não serve)
    - unit='degrees' → CRS geográfico (o geodetic_crs do atual, ou EPSG:4326)

    Retorna None quando o CRS atual já atende (nenhuma reprojeção necessária).
    Função síncrona — use asyncio.to_thread() em contextos async, pois
    estimate_utm_crs() percorre total_bounds.
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


def para_crs_metrico(*gdfs):
    """Leva as camadas para UM CRS projetado comum, onde área faz sentido.

    O CRS comum vem da primeira camada com CRS: é o dela, quando já é projetado
    (na unidade dele — nada é reprojetado à toa), ou a UTM estimada pela
    extensão DELA, quando é geográfico. As demais camadas vão para esse CRS.
    Estimar a UTM de cada camada em separado punha A e B em zonas diferentes
    quando os centros caíam em lados opostos de um meridiano de zona — e o
    overlay entre CRSs diferentes só AVISA: o percentual de sobreposição saía
    errado, sem erro.

    A UTM sai só da primeira camada, e não da extensão conjunta: é a mesma que
    ela sempre teve (ComputeArea e Bifurcação medem igual; no
    OverlapPercentage a saída continua no CRS de A, e uma camada B já projetada
    na zona certa não troca de zona), e uma B sem geometria válida não atrapalha
    a estimativa. A sem geometria válida levanta o ValueError do
    `estimate_utm_crs` ("NaN or None values are not allowed."), como antes.

    Camada sem CRS volta como está (não há de onde reprojetar).

    Devolve uma tupla na ordem recebida. Função síncrona — use
    asyncio.to_thread() em contextos async (estimate_utm_crs percorre
    total_bounds e to_crs é O(n)).
    """
    com_crs = [gdf for gdf in gdfs if gdf.crs is not None]
    if not com_crs:
        return gdfs
    alvo = com_crs[0].crs
    if alvo.is_geographic:
        alvo = com_crs[0].estimate_utm_crs()
    return tuple(
        gdf.to_crs(alvo) if gdf.crs is not None and gdf.crs != alvo else gdf
        for gdf in gdfs
    )
