# tests/unit/test_carta_helpers.py
"""
A matematica da carta imagem (flow/utils/carta.py), sem renderizar nada.

Cada numero esperado foi calculado a mao a partir das formulas do Web Mercator
e das regras do contrato — nao a partir do codigo — para que o teste prenda o
comportamento e nao a implementacao.
"""
import math

import pytest

from flow.utils import carta
from flow.utils.carta import (
    MERCATOR_MAX,
    TETO_DE_PIXELS,
    comprimento_da_escala,
    cor_valida,
    creditos_com_fundo,
    crs_da_carta,
    dimensoes_da_pagina,
    escurecer,
    extensao_com_margem,
    extensao_dos_tiles,
    extensao_no_quadro,
    fator_de_escala_3857,
    marcas,
    marcas_da_grade,
    parse_mapa,
    passo_bonito,
    quadro_do_mapa,
    rotulo_da_escala,
    rotulo_da_porta,
    rotulo_de_coordenada,
    tiles_da_extensao,
    url_do_tile,
    validar_template,
    zoom_para,
)

# Uma caixa de ~690 km de largura no fuso UTM 20 Sul (EPSG:32720).
BBOX_UTM20S_4326 = (-66.0, -13.0, -59.8, -8.0)
# A mesma caixa em EPSG:3857 (x = R*rad(lon)).
BBOX_UTM20S_3857 = (
    math.radians(-66.0) * carta.RAIO_DA_TERRA, -1459732.0,
    math.radians(-59.8) * carta.RAIO_DA_TERRA, -893464.0,
)


# ── Parametros ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cor,ok", [
    ("#e7723b", True), ("#E7723B", True), (" #e7723b ", True),
    ("laranja", False), ("#fff", False), ("e7723b", False), (None, False), (7, False),
])
def test_cor_valida(cor, ok):
    assert cor_valida(cor) is ok


def test_parse_mapa_aceita_objeto_e_json_e_descarta_vazios():
    assert parse_mapa({"focos": " #eb5757 ", "vazio": "", "nulo": None}) == {"focos": "#eb5757"}
    assert parse_mapa('{"a": "x"}') == {"a": "x"}
    assert parse_mapa("lixo") == {}
    assert parse_mapa(None) == {}
    assert parse_mapa(["lista"]) == {}


def test_rotulo_da_porta_troca_sublinhado_por_espaco_salvo_rotulo_proprio():
    assert rotulo_da_porta("focos_de_calor", {}) == "focos de calor"
    assert rotulo_da_porta("focos_de_calor", {"focos_de_calor": "Focos de calor"}) == "Focos de calor"


def test_escurecer():
    assert escurecer("#ffffff", 0.5) == "#7f7f7f"
    assert escurecer("#000000") == "#000000"


def test_dimensoes_da_pagina_a4_paisagem_a_150_dpi():
    assert dimensoes_da_pagina("a4-paisagem", 150) == (11.69, 8.27, 1754, 1240)


def test_dimensoes_da_pagina_a3_a_300_dpi_cabe_no_teto():
    _, _, largura, altura = dimensoes_da_pagina("a3-paisagem", 300)
    assert largura * altura <= TETO_DE_PIXELS


@pytest.mark.parametrize("tamanho,dpi", [("a4-paisagem", 600), ("a4-paisagem", 50), ("a5", 150)])
def test_dimensoes_da_pagina_recusa_fora_dos_limites(tamanho, dpi):
    with pytest.raises(ValueError):
        dimensoes_da_pagina(tamanho, dpi)


def test_dimensoes_da_pagina_respeita_o_teto_de_pixels(monkeypatch):
    monkeypatch.setattr(carta, "TETO_DE_PIXELS", 1_000_000)
    with pytest.raises(ValueError, match="Mpx"):
        dimensoes_da_pagina("a4-paisagem", 150)


# ── CRS ──────────────────────────────────────────────────────────────────────

def test_crs_auto_numa_area_do_fuso_20_sul_e_o_utm_20_sul():
    assert crs_da_carta((-64.0, -11.0, -62.0, -9.0), "auto", "nenhum") == ("EPSG:32720", None)


def test_fundo_de_mapa_forca_3857_mesmo_com_crs_pedido():
    assert crs_da_carta(BBOX_UTM20S_4326, "EPSG:31980", "ruas") == ("EPSG:3857", None)
    assert crs_da_carta(BBOX_UTM20S_4326, "auto", "hibrido")[0] == "EPSG:3857"


def test_crs_explicito_e_respeitado_e_lixo_e_erro():
    assert crs_da_carta(BBOX_UTM20S_4326, "EPSG:31980", None) == ("EPSG:31980", None)
    with pytest.raises(ValueError, match="invalido"):
        crs_da_carta(BBOX_UTM20S_4326, "nao-e-um-crs", "nenhum")


def test_extensao_larga_avisa_da_distorcao():
    crs, aviso = crs_da_carta((-70.0, -11.0, -40.0, -9.0), "auto", "nenhum")
    assert crs.startswith("EPSG:327")
    assert aviso and "longitude" in aviso


def test_sem_zona_utm_cai_em_3857_com_aviso():
    crs, aviso = crs_da_carta((-10.0, 87.0, 10.0, 89.0), "auto", "nenhum")
    assert crs == "EPSG:3857"
    assert aviso and "UTM" in aviso


def test_extensao_com_margem_e_minimo():
    assert extensao_com_margem((0.0, 0.0, 10_000.0, 10_000.0), True) == (-500.0, -500.0, 10_500.0, 10_500.0)
    # Um ponto so: 500 m de lado em CRS projetado, mais os 5 % de cada lado.
    assert extensao_com_margem((0.0, 0.0, 0.0, 0.0), True) == (-275.0, -275.0, 275.0, 275.0)
    x0, y0, x1, y1 = extensao_com_margem((-63.0, -10.0, -63.0, -10.0), False)
    assert (x1 - x0) == pytest.approx(0.011) and (y1 - y0) == pytest.approx(0.011)


def test_extensao_no_quadro_alarga_e_nunca_corta():
    # Mais larga que um quadro quadrado: cresce para cima e para baixo.
    assert extensao_no_quadro((0.0, 0.0, 100.0, 50.0), 1.0) == (0.0, -25.0, 100.0, 75.0)
    # Mais alta que um quadro 4:1: alarga, centrada.
    assert extensao_no_quadro((0.0, 0.0, 100.0, 50.0), 4.0) == (-50.0, 0.0, 150.0, 50.0)
    # Ja na proporcao: intacta.
    assert extensao_no_quadro((0.0, 0.0, 200.0, 100.0), 2.0) == (0.0, 0.0, 200.0, 100.0)


def test_quadro_do_mapa_reserva_a_coluna_da_legenda():
    com = quadro_do_mapa(True)
    sem = quadro_do_mapa(False)
    assert com[2] < sem[2]
    assert com[0] == sem[0] and com[1] == sem[1] and com[3] == sem[3]


# ── Escala grafica ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("largura_m,esperado", [
    (10_000, 2_000), (370, 50), (123_000, 20_000), (5_000, 1_000), (0, 0),
])
def test_comprimento_da_escala_arredonda_a_1_2_5(largura_m, esperado):
    assert comprimento_da_escala(largura_m) == esperado


def test_rotulo_da_escala():
    assert rotulo_da_escala(2000) == "2 km"
    assert rotulo_da_escala(2500) == "2,5 km"
    assert rotulo_da_escala(500) == "500 m"


def test_fator_de_escala_3857_e_o_cosseno_da_latitude():
    assert fator_de_escala_3857(-10) == pytest.approx(math.cos(math.radians(10)))
    assert fator_de_escala_3857(60) == pytest.approx(0.5)


# ── Tiles ────────────────────────────────────────────────────────────────────

def test_zoom_para_e_o_menor_que_cobre_a_largura_em_pixels():
    # Uma caixa de ~690 km numa pagina de 1754 px: no zoom 8 o mapa teria ~1128 px
    # de tiles, no 9 ~2257 — o menor que alcanca 1754 e o 9.
    assert zoom_para(BBOX_UTM20S_3857, 1754) == 9
    # Um bairro de 1 km pede zoom 19 — o teto do OSM.
    assert zoom_para((0.0, 0.0, 1000.0, 1000.0), 1754) == 19
    # O mundo inteiro numa pagina de 500 px: dois tiles bastam.
    assert zoom_para((-MERCATOR_MAX, -MERCATOR_MAX, MERCATOR_MAX, MERCATOR_MAX), 500) == 1


def test_tiles_da_extensao_conta_certo_e_respeita_o_teto():
    z, x0, x1, y0, y1 = tiles_da_extensao(BBOX_UTM20S_3857, 9)
    assert z == 9
    assert (x0, x1) == (162, 170) and (y0, y1) == (267, 274)
    assert (x1 - x0 + 1) * (y1 - y0 + 1) == 72

    z, x0, x1, y0, y1 = tiles_da_extensao(BBOX_UTM20S_3857, 9, teto=4)
    assert z == 6
    assert (x1 - x0 + 1) * (y1 - y0 + 1) <= 4


def test_extensao_dos_tiles_cobre_a_extensao_pedida():
    z, x0, x1, y0, y1 = tiles_da_extensao(BBOX_UTM20S_3857, 9)
    xmin, xmax, ymin, ymax = extensao_dos_tiles(x0, x1, y0, y1, z)
    assert xmin <= BBOX_UTM20S_3857[0] and xmax >= BBOX_UTM20S_3857[2]
    assert ymin <= BBOX_UTM20S_3857[1] and ymax >= BBOX_UTM20S_3857[3]
    # O tile unico do zoom 0 e o mundo inteiro.
    assert extensao_dos_tiles(0, 0, 0, 0, 0) == (-MERCATOR_MAX, MERCATOR_MAX, -MERCATOR_MAX, MERCATOR_MAX)


def test_template_precisa_dos_tres_marcadores():
    assert validar_template(" https://t.exemplo.org/{z}/{x}/{y}.png ") == "https://t.exemplo.org/{z}/{x}/{y}.png"
    with pytest.raises(ValueError, match="marcadores"):
        validar_template("https://t.exemplo.org/{z}/{x}.png")
    assert url_do_tile("https://t/{z}/{x}/{y}.png", 9, 162, 267) == "https://t/9/162/267.png"


# ── Grade ────────────────────────────────────────────────────────────────────

def test_passo_bonito_e_marcas():
    assert passo_bonito(6.2) == 2
    assert marcas(-66.0, -59.8, 2) == [-66.0, -64.0, -62.0, -60.0]
    assert marcas(0, 0, 1) == []


def test_rotulo_de_coordenada_por_crs():
    assert rotulo_de_coordenada(-7_000_000, "x", "EPSG:3857") == "62,88°O"
    assert rotulo_de_coordenada(-1_000_000, "y", "EPSG:3857") == "8,95°S"
    assert rotulo_de_coordenada(512_000, "x", "EPSG:32720") == "512 000 m"
    assert rotulo_de_coordenada(-63.0, "x", "EPSG:4326") == "63°O"
    assert rotulo_de_coordenada(-10.5, "y", "EPSG:4326") == "10,5°S"


def test_marcas_da_grade_em_3857_sao_graus_redondos_dentro_da_extensao():
    xs, ys = marcas_da_grade(BBOX_UTM20S_3857, "EPSG:3857")
    assert xs and ys
    lons = [math.degrees(x / carta.RAIO_DA_TERRA) for x in xs]
    assert all(-66.0 <= lon <= -59.8 for lon in lons)
    assert all(round(lon, 6) == round(lon) for lon in lons)  # graus inteiros (passo 2)
    assert all(BBOX_UTM20S_3857[1] <= y <= BBOX_UTM20S_3857[3] for y in ys)


# ── Creditos ─────────────────────────────────────────────────────────────────

def test_creditos_com_fundo():
    assert creditos_com_fundo("Fonte: INPE", "© OpenStreetMap contributors") == "Fonte: INPE · © OpenStreetMap contributors"
    assert creditos_com_fundo("", "© Provedor") == "© Provedor"
    assert creditos_com_fundo("Fonte: INPE", None) == "Fonte: INPE"
    assert creditos_com_fundo("", "  ") == ""
