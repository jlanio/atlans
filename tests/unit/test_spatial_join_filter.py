"""
Padronização de usabilidade + funcionalidade de SpatialJoin e SpatialFilter:
- SpatialJoin ganha a relação 'dwithin' com campo 'distance' (gated por visibleWhen).
- SpatialFilter usa entradas nomeadas layer/mask e ganha 'invert' (complemento).
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box  # noqa: E402

from flow.nodes.spatial.spatial_join import SpatialJoinNode  # noqa: E402
from flow.nodes.spatial.spatial_filter import SpatialFilterNode  # noqa: E402


def _pts(coords, crs="EPSG:3857"):
    return gpd.GeoDataFrame(
        {"id": list(range(len(coords)))},
        geometry=[Point(*c) for c in coords],
        crs=crs,
    )


# ── SpatialJoin: dwithin ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sjoin_dwithin_marca_matches_e_mantem_todos_a():
    # p0 a 5m de um ponto de B; p1 longe (100m).
    A = _pts([(0, 0), (100, 100)])
    B = _pts([(5, 0)])
    node = SpatialJoinNode("n", {"how": "left", "predicate": "dwithin", "distance": 10})
    out = (await node.execute({"layerA": A, "layerB": B}))["output"]
    assert len(out) == 2                          # how=left mantém todos de A
    assert out["index_right"].notna().sum() == 1  # só p0 casa a ≤10m


@pytest.mark.asyncio
async def test_sjoin_dwithin_sem_distancia_da_erro():
    A = _pts([(0, 0)])
    B = _pts([(5, 0)])
    node = SpatialJoinNode("n", {"how": "left", "predicate": "dwithin", "distance": 0})
    with pytest.raises(ValueError, match="dwithin"):
        await node.execute({"layerA": A, "layerB": B})


@pytest.mark.asyncio
async def test_sjoin_intersects_regressao():
    A = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 2, 2)], crs="EPSG:3857")
    B = gpd.GeoDataFrame({"b": [9]}, geometry=[box(1, 1, 3, 3)], crs="EPSG:3857")
    node = SpatialJoinNode("n", {"how": "inner", "predicate": "intersects"})
    out = (await node.execute({"layerA": A, "layerB": B}))["output"]
    assert len(out) == 1


# ── SpatialFilter: máscara + invert ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_mask_mantem_intersectantes():
    pts = _pts([(1, 1), (50, 50)])           # p0 dentro do polígono, p1 fora
    mask = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects", "invert": False})
    out = (await node.execute({"layer": pts, "mask": mask}))["output"]
    assert set(out["id"]) == {0}


@pytest.mark.asyncio
async def test_filter_mask_invert_pega_complemento():
    pts = _pts([(1, 1), (50, 50)])
    mask = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects", "invert": True})
    out = (await node.execute({"layer": pts, "mask": mask}))["output"]
    assert set(out["id"]) == {1}


@pytest.mark.asyncio
async def test_filter_mask_exige_entrada_mask():
    pts = _pts([(1, 1)])
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects"})
    with pytest.raises(ValueError, match="mask"):
        await node.execute({"layer": pts})


@pytest.mark.asyncio
async def test_filter_bbox_invert():
    pts = _pts([(1, 1), (50, 50)])
    node = SpatialFilterNode("n", {"filter_mode": "bbox", "bbox": "0,0,10,10", "invert": True})
    out = (await node.execute({"layer": pts}))["output"]
    assert set(out["id"]) == {1}  # inverte: mantém quem está FORA da bbox
