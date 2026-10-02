"""
Buffer com unidade de distância explícita (metros/graus):
- a camada é reprojetada quando o CRS usa outra unidade;
- o resultado sempre volta ao CRS de entrada.
"""
import math

import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point  # noqa: E402

from flow.nodes.spatial.buffer import BufferNode  # noqa: E402

# Brasília — bem dentro da zona UTM 23S (EPSG:32723).
LON, LAT = -47.9, -15.8
UTM_X, UTM_Y = 190_000.0, 8_252_000.0


def _pt(x, y, crs):
    return gpd.GeoDataFrame({"id": [0]}, geometry=[Point(x, y)], crs=crs)


def _area_m2(gdf):
    """Área em m² independente do CRS de saída."""
    metric = gdf if gdf.crs and not gdf.crs.is_geographic else gdf.to_crs(gdf.estimate_utm_crs())
    return float(metric.geometry.area.iloc[0])


def _expected_area(radius_m, quad_segs=8):
    """Área do polígono regular que o Shapely gera com `quad_segs` por quadrante."""
    n = quad_segs * 4
    return 0.5 * n * radius_m**2 * math.sin(2 * math.pi / n)


# ── Camada geográfica (EPSG:4326) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metros_em_camada_geografica_reprojeta_e_volta():
    gdf = _pt(LON, LAT, "EPSG:4326")
    node = BufferNode("n", {"distance": 100, "distanceUnit": "meters"})
    out = (await node.execute({"input": gdf}))["output"]

    assert out.crs.to_epsg() == 4326  # volta ao CRS de entrada
    assert _area_m2(out) == pytest.approx(_expected_area(100), rel=0.02)


@pytest.mark.asyncio
async def test_graus_em_camada_geografica_nao_reprojeta():
    gdf = _pt(LON, LAT, "EPSG:4326")
    node = BufferNode("n", {"distance": 1, "distanceUnit": "degrees"})
    out = (await node.execute({"input": gdf}))["output"]

    assert out.crs.to_epsg() == 4326
    minx, miny, maxx, maxy = out.total_bounds
    assert minx == pytest.approx(LON - 1, abs=0.01)
    assert maxx == pytest.approx(LON + 1, abs=0.01)
    assert miny == pytest.approx(LAT - 1, abs=0.01)
    assert maxy == pytest.approx(LAT + 1, abs=0.01)


# ── Camada projetada em metros (EPSG:32723) ───────────────────────────────────

@pytest.mark.asyncio
async def test_metros_em_camada_metrica_nao_reprojeta():
    gdf = _pt(UTM_X, UTM_Y, "EPSG:32723")
    node = BufferNode("n", {"distance": 100, "distanceUnit": "meters"})
    out = (await node.execute({"input": gdf}))["output"]

    assert out.crs.to_epsg() == 32723
    # Sem ida-e-volta de reprojeção, a área bate com precisão bem maior.
    assert float(out.geometry.area.iloc[0]) == pytest.approx(_expected_area(100), rel=1e-6)


@pytest.mark.asyncio
async def test_graus_em_camada_metrica_volta_ao_crs_de_entrada():
    gdf = _pt(UTM_X, UTM_Y, "EPSG:32723")
    node = BufferNode("n", {"distance": 0.001, "distanceUnit": "degrees"})
    out = (await node.execute({"input": gdf}))["output"]

    assert out.crs.to_epsg() == 32723
    # 0.001° ≈ 111 m — ordem de grandeza confirma que o buffer foi em graus.
    assert _area_m2(out) == pytest.approx(_expected_area(111), rel=0.05)


# ── Validação ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unidade_invalida_da_erro():
    gdf = _pt(LON, LAT, "EPSG:4326")
    node = BufferNode("n", {"distance": 100, "distanceUnit": "leguas"})
    with pytest.raises(ValueError, match="distanceUnit"):
        await node.execute({"input": gdf})


@pytest.mark.asyncio
async def test_camada_sem_crs_continua_dando_erro():
    gdf = gpd.GeoDataFrame({"id": [0]}, geometry=[Point(LON, LAT)])
    node = BufferNode("n", {"distance": 100, "distanceUnit": "meters"})
    with pytest.raises(ValueError, match="CRS"):
        await node.execute({"input": gdf})
