# tests/unit/test_carta_helpers.py
"""
The image map math (flow/utils/carta.py), without rendering anything.

Each expected number was computed by hand from the Web Mercator formulas and the
contract rules — not from the code — so that the test pins the behavior and not
the implementation.
"""
import math

import pytest

from flow.utils import carta
from flow.utils.carta import (
    MERCATOR_MAX,
    TETO_DE_PIXELS,
    scale_length,
    valid_color,
    credits_with_basemap,
    image_map_crs,
    page_dimensions,
    darken,
    extent_with_margin,
    tiles_extent,
    extent_in_frame,
    scale_factor_3857,
    badges,
    grid_ticks,
    parse_map,
    nice_step,
    map_frame,
    scale_label,
    port_label,
    coordinate_label,
    tiles_for_extent,
    url_do_tile,
    validate_template,
    zoom_para,
)

# A box ~690 km wide in UTM zone 20 South (EPSG:32720).
BBOX_UTM20S_4326 = (-66.0, -13.0, -59.8, -8.0)
# A mesma caixa em EPSG:3857 (x = R*rad(lon)).
BBOX_UTM20S_3857 = (
    math.radians(-66.0) * carta.EARTH_RADIUS, -1459732.0,
    math.radians(-59.8) * carta.EARTH_RADIUS, -893464.0,
)


# ── Parametros ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cor,ok", [
    ("#e7723b", True), ("#E7723B", True), (" #e7723b ", True),
    ("laranja", False), ("#fff", False), ("e7723b", False), (None, False), (7, False),
])
def test_valid_color(cor, ok):
    assert valid_color(cor) is ok


def test_parse_map_accepts_object_and_json_and_drops_empties():
    assert parse_map({"focos": " #eb5757 ", "vazio": "", "nulo": None}) == {"focos": "#eb5757"}
    assert parse_map('{"a": "x"}') == {"a": "x"}
    assert parse_map("lixo") == {}
    assert parse_map(None) == {}
    assert parse_map(["lista"]) == {}


def test_port_label_replaces_underscore_with_space_unless_own_label():
    assert port_label("focos_de_calor", {}) == "focos de calor"
    assert port_label("focos_de_calor", {"focos_de_calor": "Focos de calor"}) == "Focos de calor"


def test_darken():
    assert darken("#ffffff", 0.5) == "#7f7f7f"
    assert darken("#000000") == "#000000"


def test_page_dimensions_a4_landscape_at_150_dpi():
    assert page_dimensions("a4-paisagem", 150) == (11.69, 8.27, 1754, 1240)


def test_page_dimensions_a3_at_300_dpi_fit_under_ceiling():
    _, _, largura, altura = page_dimensions("a3-paisagem", 300)
    assert largura * altura <= TETO_DE_PIXELS


@pytest.mark.parametrize("tamanho,dpi", [("a4-paisagem", 600), ("a4-paisagem", 50), ("a5", 150)])
def test_page_dimensions_refuse_out_of_bounds(tamanho, dpi):
    with pytest.raises(ValueError):
        page_dimensions(tamanho, dpi)


def test_page_dimensions_respect_the_pixel_ceiling(monkeypatch):
    monkeypatch.setattr(carta, "TETO_DE_PIXELS", 1_000_000)
    with pytest.raises(ValueError, match="Mpx"):
        page_dimensions("a4-paisagem", 150)


# ── CRS ──────────────────────────────────────────────────────────────────────

def test_auto_crs_in_an_area_of_zone_20_south_is_utm_20_south():
    assert image_map_crs((-64.0, -11.0, -62.0, -9.0), "auto", "nenhum") == ("EPSG:32720", None)


def test_basemap_forces_3857_even_with_requested_crs():
    assert image_map_crs(BBOX_UTM20S_4326, "EPSG:31980", "ruas") == ("EPSG:3857", None)
    assert image_map_crs(BBOX_UTM20S_4326, "auto", "hibrido")[0] == "EPSG:3857"


def test_explicit_crs_is_honored_and_garbage_is_error():
    assert image_map_crs(BBOX_UTM20S_4326, "EPSG:31980", None) == ("EPSG:31980", None)
    with pytest.raises(ValueError, match="invalido"):
        image_map_crs(BBOX_UTM20S_4326, "nao-e-um-crs", "nenhum")


def test_wide_extent_warns_about_distortion():
    crs, aviso = image_map_crs((-70.0, -11.0, -40.0, -9.0), "auto", "nenhum")
    assert crs.startswith("EPSG:327")
    assert aviso and "longitude" in aviso


def test_without_utm_zone_falls_back_to_3857_with_warning():
    crs, aviso = image_map_crs((-10.0, 87.0, 10.0, 89.0), "auto", "nenhum")
    assert crs == "EPSG:3857"
    assert aviso and "UTM" in aviso


def test_extent_with_margin_and_minimum():
    assert extent_with_margin((0.0, 0.0, 10_000.0, 10_000.0), True) == (-500.0, -500.0, 10_500.0, 10_500.0)
    # A single point: 500 m per side in a projected CRS, plus the 5 % on each side.
    assert extent_with_margin((0.0, 0.0, 0.0, 0.0), True) == (-275.0, -275.0, 275.0, 275.0)
    x0, y0, x1, y1 = extent_with_margin((-63.0, -10.0, -63.0, -10.0), False)
    assert (x1 - x0) == pytest.approx(0.011) and (y1 - y0) == pytest.approx(0.011)


def test_extent_in_frame_widens_and_never_clips():
    # Wider than a square frame: grows up and down.
    assert extent_in_frame((0.0, 0.0, 100.0, 50.0), 1.0) == (0.0, -25.0, 100.0, 75.0)
    # Taller than a 4:1 frame: widens, centered.
    assert extent_in_frame((0.0, 0.0, 100.0, 50.0), 4.0) == (-50.0, 0.0, 150.0, 50.0)
    # Already in proportion: untouched.
    assert extent_in_frame((0.0, 0.0, 200.0, 100.0), 2.0) == (0.0, 0.0, 200.0, 100.0)


def test_map_frame_reserves_the_legend_column():
    com = map_frame(True)
    sem = map_frame(False)
    assert com[2] < sem[2]
    assert com[0] == sem[0] and com[1] == sem[1] and com[3] == sem[3]


# ── Escala grafica ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("largura_m,esperado", [
    (10_000, 2_000), (370, 50), (123_000, 20_000), (5_000, 1_000), (0, 0),
])
def test_scale_length_rounds_to_1_2_5(largura_m, esperado):
    assert scale_length(largura_m) == esperado


def test_scale_label():
    assert scale_label(2000) == "2 km"
    assert scale_label(2500) == "2,5 km"
    assert scale_label(500) == "500 m"


def test_3857_scale_factor_is_the_cosine_of_latitude():
    assert scale_factor_3857(-10) == pytest.approx(math.cos(math.radians(10)))
    assert scale_factor_3857(60) == pytest.approx(0.5)


# ── Tiles ────────────────────────────────────────────────────────────────────

def test_zoom_for_is_the_smallest_covering_the_pixel_width():
    # A ~690 km box on a 1754 px page: at zoom 8 the map would have ~1128 px
    # of tiles, at 9 ~2257 — the smallest that reaches 1754 is 9.
    assert zoom_para(BBOX_UTM20S_3857, 1754) == 9
    # A 1 km neighborhood asks for zoom 19 — the OSM ceiling.
    assert zoom_para((0.0, 0.0, 1000.0, 1000.0), 1754) == 19
    # The whole world on a 500 px page: two tiles are enough.
    assert zoom_para((-MERCATOR_MAX, -MERCATOR_MAX, MERCATOR_MAX, MERCATOR_MAX), 500) == 1


def test_extent_tiles_count_correctly_and_respect_the_ceiling():
    z, x0, x1, y0, y1 = tiles_for_extent(BBOX_UTM20S_3857, 9)
    assert z == 9
    assert (x0, x1) == (162, 170) and (y0, y1) == (267, 274)
    assert (x1 - x0 + 1) * (y1 - y0 + 1) == 72

    z, x0, x1, y0, y1 = tiles_for_extent(BBOX_UTM20S_3857, 9, teto=4)
    assert z == 6
    assert (x1 - x0 + 1) * (y1 - y0 + 1) <= 4


def test_tiles_extent_covers_the_requested_extent():
    z, x0, x1, y0, y1 = tiles_for_extent(BBOX_UTM20S_3857, 9)
    xmin, xmax, ymin, ymax = tiles_extent(x0, x1, y0, y1, z)
    assert xmin <= BBOX_UTM20S_3857[0] and xmax >= BBOX_UTM20S_3857[2]
    assert ymin <= BBOX_UTM20S_3857[1] and ymax >= BBOX_UTM20S_3857[3]
    # O tile unico do zoom 0 e o mundo inteiro.
    assert tiles_extent(0, 0, 0, 0, 0) == (-MERCATOR_MAX, MERCATOR_MAX, -MERCATOR_MAX, MERCATOR_MAX)


def test_template_needs_the_three_placeholders():
    assert validate_template(" https://t.exemplo.org/{z}/{x}/{y}.png ") == "https://t.exemplo.org/{z}/{x}/{y}.png"
    with pytest.raises(ValueError, match="marcadores"):
        validate_template("https://t.exemplo.org/{z}/{x}.png")
    assert url_do_tile("https://t/{z}/{x}/{y}.png", 9, 162, 267) == "https://t/9/162/267.png"


# ── Grade ────────────────────────────────────────────────────────────────────

def test_nice_step_and_ticks():
    assert nice_step(6.2) == 2
    assert badges(-66.0, -59.8, 2) == [-66.0, -64.0, -62.0, -60.0]
    assert badges(0, 0, 1) == []


def test_coordinate_label_by_crs():
    assert coordinate_label(-7_000_000, "x", "EPSG:3857") == "62,88°O"
    assert coordinate_label(-1_000_000, "y", "EPSG:3857") == "8,95°S"
    assert coordinate_label(512_000, "x", "EPSG:32720") == "512 000 m"
    assert coordinate_label(-63.0, "x", "EPSG:4326") == "63°O"
    assert coordinate_label(-10.5, "y", "EPSG:4326") == "10,5°S"


def test_grid_ticks_in_3857_are_round_degrees_within_the_extent():
    xs, ys = grid_ticks(BBOX_UTM20S_3857, "EPSG:3857")
    assert xs and ys
    lons = [math.degrees(x / carta.EARTH_RADIUS) for x in xs]
    assert all(-66.0 <= lon <= -59.8 for lon in lons)
    assert all(round(lon, 6) == round(lon) for lon in lons)  # graus inteiros (passo 2)
    assert all(BBOX_UTM20S_3857[1] <= y <= BBOX_UTM20S_3857[3] for y in ys)


# ── Creditos ─────────────────────────────────────────────────────────────────

def test_credits_with_basemap():
    assert credits_with_basemap("Fonte: INPE", "© OpenStreetMap contributors") == "Fonte: INPE · © OpenStreetMap contributors"
    assert credits_with_basemap("", "© Provedor") == "© Provedor"
    assert credits_with_basemap("Fonte: INPE", None) == "Fonte: INPE"
    assert credits_with_basemap("", "  ") == ""
