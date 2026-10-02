# flow/utils/carta.py
"""
A matematica da carta imagem — pura, sem matplotlib nem Pillow.

Vive fora do no (flow/nodes/outputs/carta_imagem.py) para ser testavel sem
renderizar nada: o CRS da carta, a extensao, o zoom e os tiles do fundo, a
escala grafica, os rotulos da grade e os creditos. Nada aqui toca rede, disco
ou figura. Quem importa matplotlib e o no, e so na hora de desenhar.
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Mapping

# ── Constantes do contrato ───────────────────────────────────────────────────

# Oito cores categoricas legiveis sobre branco E sobre imagem de satelite; a
# primeira e a terracota da marca.
PALETA = (
    "#e7723b", "#2f80ed", "#27ae60", "#f2c94c",
    "#9b51e0", "#eb5757", "#56ccf2", "#8d6e63",
)

# Polegadas (largura, altura) — ISO 216. A paisagem e o padrao porque uma carta
# com legenda ao lado do mapa cabe melhor deitada.
TAMANHOS: dict[str, tuple[float, float]] = {
    "a4-paisagem": (11.69, 8.27),
    "a4-retrato":  (8.27, 11.69),
    "a3-paisagem": (16.54, 11.69),
    "a3-retrato":  (11.69, 16.54),
}
DPI_MIN, DPI_MAX = 72, 300
# A3 a 300 dpi = 4961 x 3508 = 17,4 Mpx: passa. O teto existe porque o render
# roda em `asyncio.to_thread`, que nao e cancelavel — um buffer de centenas de
# megabytes ignoraria o cancel e a memoria do executor e compartilhada entre
# EXECUTOR_MAX_CONCURRENT runs.
TETO_DE_PIXELS = 30_000_000

FORMATOS: dict[str, tuple[str, str]] = {
    "png": ("image/png", "png"),
    "jpg": ("image/jpeg", "jpg"),
    "pdf": ("application/pdf", "pdf"),
}

# Os fundos com nome e as variaveis que os configuram — as mesmas do mapa web
# (web/lib/fundos-do-mapa.ts). A URL de cada um e da INSTALACAO, e nao do
# codigo: o servidor a injeta no no ao despachar (`fundo_da_instalacao`, de
# MAPA_*_URL no ambiente da API) e, sem ela, vale o ambiente do proprio
# executor. So "ruas" tem padrao: o OpenStreetMap.
FUNDOS_COM_NOME: dict[str, tuple[str, str]] = {
    "hibrido":  ("MAPA_HIBRIDO_URL",  "MAPA_HIBRIDO_CREDITO"),
    "satelite": ("MAPA_SATELITE_URL", "MAPA_SATELITE_CREDITO"),
    "ruas":     ("MAPA_RUAS_URL",     "MAPA_RUAS_CREDITO"),
}
# A atribuicao do OpenStreetMap e obrigatoria (ODbL). Entra sozinha nos
# creditos quando o fundo e usado, como a de qualquer fundo configurado.
RUAS_PADRAO: tuple[str, str] = (
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "© OpenStreetMap contributors",
)
TETO_DE_TILES = 256
ZOOM_MAXIMO = 19          # o OSM serve ate 19
TAMANHO_DO_TILE = 256
RAIO_DA_TERRA = 6378137.0  # esfera do Web Mercator (EPSG:3857)
LATITUDE_MAXIMA = 85.0511  # limite do Web Mercator
MERCATOR_MAX = math.pi * RAIO_DA_TERRA

COR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ESCALAS_BONITAS = (1.0, 2.0, 5.0)


# ── Parametros ───────────────────────────────────────────────────────────────

def cor_valida(cor: Any) -> bool:
    """`#RRGGBB` e so isso — o matplotlib aceitaria nomes, mas a paleta da carta
    fala em hex e o campo do editor tambem."""
    return isinstance(cor, str) and bool(COR_HEX.match(cor.strip()))


def parse_mapa(raw: Any) -> dict[str, str]:
    """Le um campo `keyvalue` (porta → valor).

    O campo do editor grava um objeto, mas um fluxo salvo (ou um executor
    antigo) pode trazer JSON em string — e `validate_node_parameters` nao toca
    `keyvalue`. Chaves e valores viram texto sem espacos nas pontas; entradas
    vazias sao descartadas.
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
    """O rotulo da legenda: o que a pessoa escreveu em `rotulos`, senao o nome
    da porta com `_` virando espaco (o nome da porta tem de ser identificador)."""
    return rotulos.get(porta) or porta.replace("_", " ")


def escurecer(cor_hex: str, fator: float = 0.6) -> str:
    """A borda de um poligono: a mesma cor, mais escura."""
    cor = cor_hex.lstrip("#")
    r, g, b = (int(cor[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(
        int(r * fator), int(g * fator), int(b * fator),
    )


def dimensoes_da_pagina(tamanho: str, dpi: int) -> tuple[float, float, int, int]:
    """(largura_pol, altura_pol, largura_px, altura_px) — ou ValueError.

    `validate_node_parameters` coage tipos mas nao aplica minimo/maximo; e aqui
    que o dpi e o tamanho sao conferidos de verdade.
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
    """O CRS em que a carta e desenhada, e um aviso opcional para o log.

    - com fundo de mapa: sempre EPSG:3857 — os tiles sao Web Mercator e
      reprojetar o raster nao entra nesta versao;
    - `auto`: o UTM local estimado pelo CENTRO da extensao (`estimate_utm_crs`);
      extensoes largas ganham aviso (a borda distorce), e onde nao ha zona UTM
      (regioes polares) cai em 3857 com aviso;
    - senao, o CRS que a pessoa escreveu (`EPSG:31980`, WKT...) — lixo e ValueError.
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
    """(x0, y0, x1, y1) com 5 % de folga em cada lado.

    Uma extensao degenerada (um ponto so, ou uma linha reta) ganha um tamanho
    minimo — 500 m em CRS projetado, 0,01 grau em geografico — senao o mapa
    teria area zero.
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


# ── O quadro do mapa na pagina ───────────────────────────────────────────────

def quadro_do_mapa(legenda: bool) -> tuple[float, float, float, float]:
    """(esquerda, base, largura, altura) do eixo do mapa, em fracao da figura.

    A coluna da direita so existe com legenda; sem ela o mapa toma a pagina.
    O topo fica logo abaixo do subtitulo e a base acima da faixa de creditos.
    """
    return (0.04, 0.10, 0.70 if legenda else 0.92, 0.785)


def extensao_no_quadro(extensao: tuple[float, float, float, float],
                       proporcao: float) -> tuple[float, float, float, float]:
    """Alarga a extensao (nunca corta) ate ter a proporcao largura/altura do
    quadro, centrada — assim o mapa PREENCHE o quadro em vez de o eixo
    encolher e deixar a pagina em branco. E o que uma carta faz: a moldura e
    fixa, a extensao cresce para caber nela."""
    x0, y0, x1, y1 = extensao
    dx, dy = x1 - x0, y1 - y0
    if dx <= 0 or dy <= 0 or proporcao <= 0:
        return extensao
    if dx / dy < proporcao:      # mais alta que o quadro: alarga
        novo_dx = dy * proporcao
        cx = (x0 + x1) / 2
        return cx - novo_dx / 2, y0, cx + novo_dx / 2, y1
    novo_dy = dx / proporcao     # mais larga que o quadro: cresce para cima e para baixo
    cy = (y0 + y1) / 2
    return x0, cy - novo_dy / 2, x1, cy + novo_dy / 2


# ── Escala grafica ───────────────────────────────────────────────────────────

def fator_de_escala_3857(latitude: float) -> float:
    """Quanto o Web Mercator estica as distancias nesta latitude: 1 m no chao
    mede 1/cos(lat) unidades de mapa. Corrige a escala grafica em 3857."""
    return math.cos(math.radians(latitude))


def comprimento_da_escala(largura_real_m: float) -> float:
    """A barra da escala: cerca de um quinto da largura do mapa, arredondada
    para baixo a 1, 2 ou 5 vezes uma potencia de dez (em metros)."""
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
    """O menor zoom em que a largura do mapa, em pixels de tile, alcanca a
    largura de saida — o fundo nao fica borrado nem e baixado alem do que a
    pagina consegue mostrar."""
    x0, _, x1, _ = extensao_3857
    largura_m = max(x1 - x0, 1e-9)
    n_necessario = largura_px * 2 * MERCATOR_MAX / (largura_m * TAMANHO_DO_TILE)
    z = math.ceil(math.log2(max(n_necessario, 1.0)))
    return max(0, min(ZOOM_MAXIMO, z))


def tiles_da_extensao(extensao_3857: tuple[float, float, float, float], z: int,
                      teto: int = TETO_DE_TILES) -> tuple[int, int, int, int, int]:
    """(z, x_min, x_max, y_min, y_max) dos tiles que cobrem a extensao.

    Acima do teto o zoom desce ate caber: a carta nunca falha por tamanho de
    fundo, so perde nitidez.
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
    """(xmin, xmax, ymin, ymax) em EPSG:3857 do mosaico — e o `extent` do imshow."""
    n = 2 ** z
    tamanho = 2 * MERCATOR_MAX / n
    xmin = x_min * tamanho - MERCATOR_MAX
    xmax = (x_max + 1) * tamanho - MERCATOR_MAX
    ymax = MERCATOR_MAX - y_min * tamanho
    ymin = MERCATOR_MAX - (y_max + 1) * tamanho
    return xmin, xmax, ymin, ymax


# ── Grade de coordenadas ─────────────────────────────────────────────────────

def passo_bonito(vao: float, alvo: int = 5) -> float:
    """Um passo 1/2/5 x 10^n que divide o vao em cerca de `alvo` partes."""
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
    """Os multiplos de `passo` dentro de [inicio, fim]."""
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
    """O texto de uma marca da grade.

    - EPSG:3857: a marca e convertida para longitude/latitude (em 3857 x so
      depende de lon e y so de lat, entao a conversao e exata);
    - outro CRS projetado (UTM): metros, com separador de milhar;
    - geografico: graus.
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
    """As posicoes das linhas da grade nos dois eixos, em unidades do mapa.

    Em 3857 as linhas sao de longitude/latitude redondas (convertidas para
    metros de mapa); nos demais CRS, multiplos redondos da propria unidade.
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
    """Os creditos escritos pela pessoa mais a atribuicao do fundo, quando ha."""
    partes = [(creditos or "").strip(), (atribuicao or "").strip()]
    return " · ".join(p for p in partes if p)


def fundo_configurado(
    fundo: str, injetado: Any = None, ambiente: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    """(template, atribuicao) de um fundo com nome, ou None se a instalacao nao o tem.

    Nesta ordem: o que o servidor injetou no no (`fundo_da_instalacao`), o
    ambiente do executor (MAPA_*_URL e MAPA_*_CREDITO) e, so para "ruas", o
    OpenStreetMap. Sem o hibrido, o satelite, como no servidor e no web.
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
    """O servidor que despachou mandou o fundo da instalacao? Um servidor
    desta versao sempre manda a chave `url` (vazia quando nao ha o fundo); sem
    ela, o despacho veio de um servidor anterior."""
    return isinstance(injetado, dict) and "url" in injetado
