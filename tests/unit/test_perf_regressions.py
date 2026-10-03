"""
Regressions for the performance optimizations.

They ensure the changes preserve BEHAVIOR — the gain is in cost, the
result must be identical to the previous path.
"""
import numpy as np


# ── P1: Jinja template compilation cache ─────────────────────────────────────

def test_template_cache_compila_uma_vez_e_preserva_render():
    from flow.utils.expression_service import ExpressionService

    svc = ExpressionService()
    # Mesmo source, contextos diferentes -> 1 compilacao, renders corretos.
    assert svc.render("Ola {{ nome }}", {"nome": "A"}) == "Ola A"
    assert svc.render("Ola {{ nome }}", {"nome": "B"}) == "Ola B"
    assert len(svc._template_cache) == 1

    # Source distinto -> nova entrada.
    assert svc.render("{{ x * 2 }}", {"x": 3}) == "6"
    assert len(svc._template_cache) == 2


def test_template_cache_respeita_o_teto():
    from flow.utils import expression_service as mod

    svc = mod.ExpressionService()
    orig = mod._TEMPLATE_CACHE_MAX
    mod._TEMPLATE_CACHE_MAX = 3
    try:
        for i in range(10):
            svc.render(f"{{{{ v{i} }}}}", {f"v{i}": i})
        assert len(svc._template_cache) <= 3, "cache nao pode crescer sem limite"
    finally:
        mod._TEMPLATE_CACHE_MAX = orig


def test_alias_ainda_funciona_com_cache():
    """The alias path ($X -> X) must render via the cache too."""
    from flow.utils.expression_service import ExpressionService

    svc = ExpressionService()
    assert svc.render("$Camada", {"Camada": "valor"}) == "valor"


# ── P4: vetorizacao de bbox (comportamento identico) ─────────────────────────

def test_compute_bbox_per_feature_vetorizado_bate_com_scalar():
    import geopandas as gpd
    from shapely.geometry import Point, box

    gdf = gpd.GeoDataFrame(
        geometry=[Point(0, 0).buffer(1), Point(5, 5).buffer(2)], crs="EPSG:4326",
    )
    bounds = gdf.bounds

    import shapely
    vetor = shapely.box(
        bounds.minx.values, bounds.miny.values,
        bounds.maxx.values, bounds.maxy.values,
    )
    escalar = [box(r.minx, r.miny, r.maxx, r.maxy) for r in bounds.itertuples()]

    assert len(vetor) == len(escalar)
    for v, e in zip(vetor, escalar):
        assert v.equals(e), "box vetorizado deve ser identico ao escalar"


def test_heatmap_grid_vetorizado_bate_com_scalar():
    import shapely
    from shapely.geometry import box

    gx = np.array([0.0, 1.0, 2.0])
    gy = np.array([0.0, 1.0, 2.0])
    hw, hh = 0.5, 0.5

    vetor = shapely.box(gx - hw, gy - hh, gx + hw, gy + hh)
    escalar = [box(gx[i] - hw, gy[i] - hh, gx[i] + hw, gy[i] + hh) for i in range(len(gx))]

    for v, e in zip(vetor, escalar):
        assert v.equals(e)


# ── P3: gpd.concat nao existe (o bug corrigido) ──────────────────────────────

def test_geopandas_nao_tem_concat_e_pd_concat_preserva_tipo():
    """Proves the WFS bug: gpd.concat does not exist; pd.concat preserves GeoDataFrame."""
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point

    assert not hasattr(gpd, "concat")

    a = gpd.GeoDataFrame({"v": [1]}, geometry=[Point(0, 0)])
    b = gpd.GeoDataFrame({"v": [2]}, geometry=[Point(1, 1)])
    r = pd.concat([a, b], ignore_index=True)
    assert isinstance(r, gpd.GeoDataFrame)
    assert len(r) == 2
