# flow/utils/carta.py
"""
The math of the image map — pure, without matplotlib or Pillow.

Lives outside the node (flow/nodes/outputs/carta_imagem.py) so it can be tested
without rendering anything: the map's CRS, the extent, the zoom and the basemap
tiles, the scale bar, the grid labels and the credits. Nothing here touches the
network, disk or a figure. The node is what imports matplotlib, and only when it
is time to draw.
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Mapping

# ── Contract constants ────────────────────────────────────────────────────────

# Eight categorical colors readable on white AND on satellite imagery; the
# first is the brand's terracotta.
PALETA = (
    "#e7723b", "#2f80ed", "#27ae60", "#f2c94c",
    "#9b51e0", "#eb5757", "#56ccf2", "#8d6e63",
)

# Inches (width, height) — ISO 216. Landscape is the default because an image
# map with the legend beside the map fits better lying down.
TAMANHOS: dict[str, tuple[float, float]] = {
    "a4-paisagem": (11.69, 8.27),
    "a4-retrato":  (8.27, 11.69),
    "a3-paisagem": (16.54, 11.69),
    "a3-retrato":  (11.69, 16.54),
}
DPI_MIN, DPI_MAX = 72, 300
# A3 at 300 dpi = 4961 x 3508 = 17.4 Mpx: passes. The ceiling exists because the
# render runs in `asyncio.to_thread`, which is not cancellable — a buffer of
# hundreds of megabytes would ignore the cancel, and the executor's memory is
# shared among EXECUTOR_MAX_CONCURRENT runs.
TETO_DE_PIXELS = 30_000_000

FORMATOS: dict[str, tuple[str, str]] = {
    "png": ("image/png", "png"),
    "jpg": ("image/jpeg", "jpg"),
    "pdf": ("application/pdf", "pdf"),
}

# The named basemaps and the variables that configure them — the same as the web
# map's (web/lib/fundos-do-mapa.ts). Each one's URL belongs to the INSTALLATION,
# not the code: the server injects it into the node at dispatch
# (`fundo_da_instalacao`, from MAPA_*_URL in the API's environment) and, without
# it, the executor's own environment applies. Only "ruas" has a default:
# OpenStreetMap.
FUNDOS_COM_NOME: dict[str, tuple[str, str]] = {
    "hibrido":  ("MAPA_HIBRIDO_URL",  "MAPA_HIBRIDO_CREDITO"),
    "satelite": ("MAPA_SATELITE_URL", "MAPA_SATELITE_CREDITO"),
    "ruas":     ("MAPA_RUAS_URL",     "MAPA_RUAS_CREDITO"),
}
# The OpenStreetMap attribution is mandatory (ODbL). It is added to the credits
# automatically when the basemap is used, like that of any configured basemap.
RUAS_PADRAO: tuple[str, str] = (
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "© OpenStreetMap contributors",
)
TETO_DE_TILES = 256
ZOOM_MAXIMO = 19          # o OSM serve ate 19
TAMANHO_DO_TILE = 256
RAIO_DA_TERRA = 6378137.0  # Web Mercator sphere (EPSG:3857)
LATITUDE_MAXIMA = 85.0511  # Web Mercator limit
MERCATOR_MAX = math.pi * RAIO_DA_TERRA

COR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ESCALAS_BONITAS = (1.0, 2.0, 5.0)


# ── Parametros ───────────────────────────────────────────────────────────────

def cor_valida(cor: Any) -> bool:
    """`#RRGGBB` and nothing else — matplotlib would accept names, but the map's
    palette speaks hex and so does the editor field."""
    return isinstance(cor, str) and bool(COR_HEX.match(cor.strip()))


def parse_mapa(raw: Any) -> dict[str, str]:
    """Reads a `keyvalue` field (port → value).

    The editor field writes an object, but a saved workflow (or an old
    executor) may bring JSON as a string — and `validate_node_parameters` does
    not touch `keyvalue`. Keys and values become text with no surrounding
    whitespace; empty entries are dropped.
    """
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return {}
    if not isinstance(raw, dict):
        return {}
    saida: dict[str, str] = {}
    for chave, valor in raw.items():
        k = str(chave).strip()
        v = "" if valor is None else str(valor).strip()
        if k and v:
            saida[k] = v
    return saida


def rotulo_da_porta(porta: str, rotulos: dict[str, str]) -> str:
    """The legend label: what the person wrote in `rotulos`, otherwise the port
    name with `_` turned into a space (the port name must be an identifier)."""
    return rotulos.get(porta) or porta.replace("_", " ")


def escurecer(cor_hex: str, fator: float = 0.6) -> str:
    """A polygon's outline: the same color, darker."""
    cor = cor_hex.lstrip("#")
    r, g, b = (int(cor[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(
        int(r * fator), int(g * fator), int(b * fator),
    )


def dimensoes_da_pagina(tamanho: str, dpi: int) -> tuple[float, float, int, int]:
    """(largura_pol, altura_pol, largura_px, altura_px) — or ValueError.

    `validate_node_parameters` coerces types but does not apply min/max; this is
    where the dpi and the size are actually checked.
    """
    if tamanho not in TAMANHOS:
        raise ValueError(
            f"Tamanho de pagina '{tamanho}' desconhecido. Use um de: {', '.join(TAMANHOS)}."
        )
    if not isinstance(dpi, int) or isinstance(dpi, bool) or not (DPI_MIN <= dpi <= DPI_MAX):
        raise ValueError(f"dpi deve ficar entre {DPI_MIN} e {DPI_MAX} (recebido: {dpi!r}).")
    largura_pol, altura_pol = TAMANHOS[tamanho]
    largura_px = int(round(largura_pol * dpi))
    altura_px = int(round(altura_pol * dpi))
    if largura_px * altura_px > TETO_DE_PIXELS:
        raise ValueError(
            f"{tamanho} a {dpi} dpi daria {largura_px}x{altura_px} px, acima do teto de "
            f"{TETO_DE_PIXELS // 1_000_000} Mpx. Reduza o dpi ou o tamanho."
        )
    return largura_pol, altura_pol, largura_px, altura_px


# ── CRS e extensao ───────────────────────────────────────────────────────────

def crs_da_carta(caixa_4326: tuple[float, float, float, float],
                 crs_param: str | None, fundo: str | None) -> tuple[str, str | None]:
    """The CRS the image map is drawn in, and an optional warning for the log.

    - with a basemap: always EPSG:3857 — the tiles are Web Mercator and
      reprojecting the raster is not part of this version;
    - `auto`: the local UTM estimated from the CENTER of the extent
      (`estimate_utm_crs`); wide extents get a warning (the edge distorts), and
      where there is no UTM zone (polar regions) it falls back to 3857 with a warning;
    - otherwise, the CRS the person wrote (`EPSG:31980`, WKT...) — garbage is a ValueError.
    """
    fundo = (fundo or "nenhum").strip().lower()
    if fundo and fundo != "nenhum":
        return "EPSG:3857", None

    pedido = (crs_param or "auto").strip()
    if pedido.lower() == "auto":
        import geopandas as gpd
        from shapely.geometry import box

        x0, y0, x1, y1 = caixa_4326
        aviso = None
        if (x1 - x0) > 6:
            aviso = (
                f"A extensao das camadas cobre {x1 - x0:.1f} graus de longitude: o UTM "
                "estimado pelo centro distorce nas bordas. Um EPSG proprio pode servir melhor."
            )
        try:
            crs = gpd.GeoSeries([box(x0, y0, x1, y1)], crs="EPSG:4326").estimate_utm_crs()
        except Exception:  # sem zona UTM (polos): a estimativa levanta RuntimeError
            return "EPSG:3857", (
                "Nao ha zona UTM para esta extensao; a carta sai em EPSG:3857 "
                "(Web Mercator). Informe um EPSG em 'crs' para escolher outro."
            )
        return crs.to_string(), aviso

    from pyproj import CRS
    from pyproj.exceptions import CRSError

    try:
        crs = CRS.from_user_input(pedido)
    except CRSError as exc:
        raise ValueError(f"CRS '{pedido}' invalido: {exc}") from exc
    return crs.to_string(), None


def crs_e_projetado(crs_texto: str) -> bool:
    from pyproj import CRS
    return bool(CRS.from_user_input(crs_texto).is_projected)


def extensao_com_margem(caixa: tuple[float, float, float, float], projetado: bool,
                        fracao: float = 0.05) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) with 5 % padding on each side.

    A degenerate extent (a single point, or a straight line) gets a minimum
    size — 500 m in a projected CRS, 0.01 degree in a geographic one — otherwise
    the map would have zero area.
    """
    x0, y0, x1, y1 = caixa
    minimo = 500.0 if projetado else 0.01
    if (x1 - x0) < minimo:
        cx = (x0 + x1) / 2
        x0, x1 = cx - minimo / 2, cx + minimo / 2
    if (y1 - y0) < minimo:
        cy = (y0 + y1) / 2
        y0, y1 = cy - minimo / 2, cy + minimo / 2
    dx, dy = (x1 - x0) * fracao, (y1 - y0) * fracao
    return x0 - dx, y0 - dy, x1 + dx, y1 + dy


# ── The map frame on the page ─────────────────────────────────────────────────

def quadro_do_mapa(legenda: bool) -> tuple[float, float, float, float]:
    """(left, bottom, width, height) of the map axis, as a fraction of the figure.

    The right column only exists with a legend; without it the map takes the page.
    The top sits just below the subtitle and the bottom above the credits strip.
    """
    return (0.04, 0.10, 0.70 if legenda else 0.92, 0.785)


def extensao_no_quadro(extensao: tuple[float, float, float, float],
                       proporcao: float) -> tuple[float, float, float, float]:
    """Widens the extent (never cuts) until it has the frame's width/height
    ratio, centered — so the map FILLS the frame instead of the axis
    shrinking and leaving the page blank. It is what an image map does: the
    frame is fixed, the extent grows to fit it."""
    x0, y0, x1, y1 = extensao
    dx, dy = x1 - x0, y1 - y0
    if dx <= 0 or dy <= 0 or proporcao <= 0:
        return extensao
    if dx / dy < proporcao:      # taller than the frame: widen
        novo_dx = dy * proporcao
        cx = (x0 + x1) / 2
        return cx - novo_dx / 2, y0, cx + novo_dx / 2, y1
    novo_dy = dx / proporcao     # wider than the frame: grow up and down
    cy = (y0 + y1) / 2
    return x0, cy - novo_dy / 2, x1, cy + novo_dy / 2


# ── Escala grafica ───────────────────────────────────────────────────────────

def fator_de_escala_3857(latitude: float) -> float:
    """How much Web Mercator stretches distances at this latitude: 1 m on the
    ground measures 1/cos(lat) map units. Corrects the scale bar in 3857."""
    return math.cos(math.radians(latitude))


def comprimento_da_escala(largura_real_m: float) -> float:
    """The scale bar: about one fifth of the map's width, rounded down to
    1, 2 or 5 times a power of ten (in meters)."""
    alvo = largura_real_m / 5.0
    if alvo <= 0:
        return 0.0
    expoente = math.floor(math.log10(alvo))
    base = 10.0 ** expoente
    melhor = base
    for m in ESCALAS_BONITAS:
        if m * base <= alvo:
            melhor = m * base
    return melhor


def rotulo_da_escala(metros: float) -> str:
    if metros >= 1000:
        km = metros / 1000
        return f"{km:g} km".replace(".", ",")
    return f"{metros:g} m".replace(".", ",")


# ── Tiles (Web Mercator) ─────────────────────────────────────────────────────

def validar_template(template: str) -> str:
    t = (template or "").strip()
    for marcador in ("{z}", "{x}", "{y}"):
        if marcador not in t:
            raise ValueError(
                "A URL personalizada do fundo precisa dos marcadores {z}, {x} e {y} "
                "(ex.: https://tiles.exemplo.org/{z}/{x}/{y}.png)."
            )
    return t


def url_do_tile(template: str, z: int, x: int, y: int) -> str:
    return template.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))


def lon_lat_de_3857(x: float, y: float) -> tuple[float, float]:
    lon = math.degrees(x / RAIO_DA_TERRA)
    lat = math.degrees(math.atan(math.sinh(y / RAIO_DA_TERRA)))
    return lon, lat


def _tile_de_lon_lat(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    lat = max(-LATITUDE_MAXIMA, min(LATITUDE_MAXIMA, lat))
    phi = math.radians(lat)
    x = int(math.floor((lon + 180.0) / 360.0 * n))
    y = int(math.floor((1.0 - math.log(math.tan(phi) + 1.0 / math.cos(phi)) / math.pi) / 2.0 * n))
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def zoom_para(extensao_3857: tuple[float, float, float, float], largura_px: int) -> int:
    """The smallest zoom at which the map's width, in tile pixels, reaches the
    output width — the basemap is neither blurry nor downloaded beyond what the
    page can show."""
    x0, _, x1, _ = extensao_3857
    largura_m = max(x1 - x0, 1e-9)
    n_necessario = largura_px * 2 * MERCATOR_MAX / (largura_m * TAMANHO_DO_TILE)
    z = math.ceil(math.log2(max(n_necessario, 1.0)))
    return max(0, min(ZOOM_MAXIMO, z))


def tiles_da_extensao(extensao_3857: tuple[float, float, float, float], z: int,
                      teto: int = TETO_DE_TILES) -> tuple[int, int, int, int, int]:
    """(z, x_min, x_max, y_min, y_max) of the tiles covering the extent.

    Above the ceiling the zoom steps down until it fits: the image map never
    fails because of basemap size, it only loses sharpness.
    """
    x0, y0, x1, y1 = extensao_3857
    lon0, lat0 = lon_lat_de_3857(x0, y0)
    lon1, lat1 = lon_lat_de_3857(x1, y1)
    z = max(0, min(ZOOM_MAXIMO, int(z)))
    while True:
        tx0, ty1 = _tile_de_lon_lat(lon0, lat0, z)  # canto inferior esquerdo -> y maior
        tx1, ty0 = _tile_de_lon_lat(lon1, lat1, z)  # canto superior direito  -> y menor
        quantidade = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
        if quantidade <= teto or z == 0:
            return z, tx0, tx1, ty0, ty1
        z -= 1


def extensao_dos_tiles(x_min: int, x_max: int, y_min: int, y_max: int, z: int
                       ) -> tuple[float, float, float, float]:
    """(xmin, xmax, ymin, ymax) of the mosaic in EPSG:3857 — it is the imshow `extent`."""
    n = 2 ** z
    tamanho = 2 * MERCATOR_MAX / n
    xmin = x_min * tamanho - MERCATOR_MAX
    xmax = (x_max + 1) * tamanho - MERCATOR_MAX
    ymax = MERCATOR_MAX - y_min * tamanho
    ymin = MERCATOR_MAX - (y_max + 1) * tamanho
    return xmin, xmax, ymin, ymax


# ── Coordinate grid ───────────────────────────────────────────────────────────

def passo_bonito(vao: float, alvo: int = 5) -> float:
    """A 1/2/5 x 10^n step that divides the span into about `alvo` parts."""
    if vao <= 0:
        return 1.0
    bruto = vao / alvo
    expoente = math.floor(math.log10(bruto))
    base = 10.0 ** expoente
    for m in ESCALAS_BONITAS:
        if m * base >= bruto:
            return m * base
    return 10.0 * base


def marcas(inicio: float, fim: float, passo: float) -> list[float]:
    """The multiples of `passo` within [inicio, fim]."""
    if passo <= 0 or fim <= inicio:
        return []
    primeiro = math.ceil(inicio / passo)
    ultimo = math.floor(fim / passo)
    return [round(k * passo, 10) for k in range(primeiro, ultimo + 1)]


def _graus(valor: float, positivo: str, negativo: str) -> str:
    lado = positivo if valor >= 0 else negativo
    texto = f"{abs(valor):.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto}°{lado}"


def rotulo_de_coordenada(valor: float, eixo: str, crs_texto: str) -> str:
    """The text of a grid tick.

    - EPSG:3857: the tick is converted to longitude/latitude (in 3857 x only
      depends on lon and y only on lat, so the conversion is exact);
    - another projected CRS (UTM): meters, with a thousands separator;
    - geographic: degrees.
    """
    from pyproj import CRS

    crs = CRS.from_user_input(crs_texto)
    if crs.to_epsg() == 3857:
        if eixo == "x":
            return _graus(math.degrees(valor / RAIO_DA_TERRA), "L", "O")
        return _graus(math.degrees(math.atan(math.sinh(valor / RAIO_DA_TERRA))), "N", "S")
    if crs.is_projected:
        inteiro = int(round(valor))
        return f"{inteiro:,}".replace(",", " ") + " m"
    return _graus(valor, "L", "O") if eixo == "x" else _graus(valor, "N", "S")


def marcas_da_grade(extensao: tuple[float, float, float, float], crs_texto: str
                    ) -> tuple[list[float], list[float]]:
    """The positions of the grid lines on both axes, in map units.

    In 3857 the lines are at round longitudes/latitudes (converted to map
    meters); in the other CRSs, round multiples of the unit itself.
    """
    from pyproj import CRS

    x0, y0, x1, y1 = extensao
    crs = CRS.from_user_input(crs_texto)
    if crs.to_epsg() == 3857:
        lon0, lat0 = lon_lat_de_3857(x0, y0)
        lon1, lat1 = lon_lat_de_3857(x1, y1)
        p_lon = passo_bonito(lon1 - lon0)
        p_lat = passo_bonito(lat1 - lat0)
        xs = [math.radians(lon) * RAIO_DA_TERRA for lon in marcas(lon0, lon1, p_lon)]
        ys = [
            RAIO_DA_TERRA * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
            for lat in marcas(lat0, lat1, p_lat)
            if -LATITUDE_MAXIMA < lat < LATITUDE_MAXIMA
        ]
        return xs, ys
    return marcas(x0, x1, passo_bonito(x1 - x0)), marcas(y0, y1, passo_bonito(y1 - y0))


# ── Creditos ─────────────────────────────────────────────────────────────────

def creditos_com_fundo(creditos: str | None, atribuicao: str | None) -> str:
    """The credits written by the person plus the basemap's attribution, when there is one."""
    partes = [(creditos or "").strip(), (atribuicao or "").strip()]
    return " · ".join(p for p in partes if p)


def fundo_configurado(
    fundo: str, injetado: Any = None, ambiente: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    """(template, attribution) of a named basemap, or None if the installation does not have it.

    In this order: what the server injected into the node (`fundo_da_instalacao`),
    the executor's environment (MAPA_*_URL and MAPA_*_CREDITO) and, only for
    "ruas", OpenStreetMap. Without hybrid or satellite, as on the server and the web.
    """
    var_url, var_credito = FUNDOS_COM_NOME[fundo]
    if isinstance(injetado, dict) and str(injetado.get("url") or "").strip():
        url, credito = str(injetado["url"]), str(injetado.get("credito") or "")
    else:
        ambiente = os.environ if ambiente is None else ambiente
        url, credito = ambiente.get(var_url) or "", ambiente.get(var_credito) or ""
        if fundo == "hibrido" and not url.strip():
            var_url, var_credito = FUNDOS_COM_NOME["satelite"]
            url, credito = ambiente.get(var_url) or "", ambiente.get(var_credito) or ""
    if url.strip():
        try:
            return validar_template(url), credito.strip()
        except ValueError as exc:
            raise ValueError(f"O fundo '{fundo}' da instalacao ({var_url}) nao e um template de tiles: {exc}") from exc
    return RUAS_PADRAO if fundo == "ruas" else None


def servidor_injetou(injetado: Any) -> bool:
    """Did the dispatching server send the installation's basemap? A server of
    this version always sends the `url` key (empty when there is no such
    basemap); without it, the dispatch came from an earlier server."""
    return isinstance(injetado, dict) and "url" in injetado
