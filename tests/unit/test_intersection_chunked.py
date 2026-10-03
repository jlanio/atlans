"""
Intersection with bounded peak memory: adaptive chunks sized by the
estimated fanout + geometry hygiene. Guarantees equivalence with the direct
overlay and the behavior of clean/empty layers.
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import box  # noqa: E402

from flow.nodes.spatial import intersection as _mod  # noqa: E402


def _grid(n, size=1.0, crs="EPSG:3857"):
    """n size×size squares side by side on the x axis (projected CRS for correct area)."""
    return gpd.GeoDataFrame(
        {"id": list(range(n))},
        geometry=[box(i, 0, i + size, size) for i in range(n)],
        crs=crs,
    )


def test_bounded_igual_ao_overlay_direto(monkeypatch):
    srcA = _grid(6)
    srcB = gpd.GeoDataFrame({"tag": ["b"]}, geometry=[box(0.5, 0.0, 5.5, 0.5)], crs="EPSG:3857")

    direto = gpd.overlay(srcA, srcB, how="intersection")

    # A tiny pairs/chunk target forces adaptive slicing into several chunks.
    monkeypatch.setattr(_mod, "_TARGET_PAIRS_PER_CHUNK", 1)
    bounded = _mod._overlay_intersection_bounded(srcA, srcB)

    assert len(bounded) == len(direto)
    assert bounded.geometry.area.sum() == pytest.approx(direto.geometry.area.sum())
    assert set(bounded["id"]) == set(direto["id"])
    assert str(bounded.crs) == str(srcA.crs)


def test_extents_disjuntos_resultado_vazio_com_crs(monkeypatch):
    srcA = _grid(4)
    srcB = gpd.GeoDataFrame(geometry=[box(100, 100, 101, 101)], crs="EPSG:3857")
    monkeypatch.setattr(_mod, "_TARGET_PAIRS_PER_CHUNK", 1)
    out = _mod._overlay_intersection_bounded(srcA, srcB)
    assert out.empty
    assert str(out.crs) == "EPSG:3857"


def test_estimativa_de_fanout():
    # A: 5 squares; B: a rectangle covering all of them → fanout ~1 per feature of A.
    srcA = _grid(5)
    srcB = gpd.GeoDataFrame(geometry=[box(0, 0, 5, 1)], crs="EPSG:3857")
    avg = _mod._estimate_avg_fanout(srcA, srcB)
    assert avg >= 1.0


def test_clean_layer_remove_vazias_e_preserva_validas():
    from shapely.geometry import Polygon
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[box(0, 0, 1, 1), Polygon(), box(2, 0, 3, 1)],  # 2nd is empty
        crs="EPSG:3857",
    )
    cleaned = _mod._clean_layer(gdf, "A")
    assert len(cleaned) == 2
    assert set(cleaned["id"]) == {1, 3}


@pytest.mark.asyncio
async def test_execute_com_geometria_vazia_nao_quebra(monkeypatch):
    from shapely.geometry import Polygon
    node = _mod.IntersectionNode("n1", {})
    srcA = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[box(0, 0, 2, 2), Polygon()], crs="EPSG:3857")
    srcB = gpd.GeoDataFrame({"t": ["x"]}, geometry=[box(1, 1, 3, 3)], crs="EPSG:3857")
    out = await node.execute({"layerA": srcA, "layerB": srcB})
    # The empty feature is discarded; the valid one intersects B.
    assert not out["output"].empty
