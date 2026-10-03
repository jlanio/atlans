"""Output equivalence of the nodes optimized in the performance batch.

The refactors (spatial index in PartitionNode, single template compilation in
SetFields) change the HOW, not the WHAT: these tests pin the expected result for
a known input, so that any behavior regression shows up.
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box  # noqa: E402

from flow.nodes.spatial.partition import PartitionNode  # noqa: E402
from flow.nodes.spatial.spatial_filter import SpatialFilterNode  # noqa: E402
from flow.nodes.action.field_transformer import SetFields  # noqa: E402


async def test_indexed_partition_keeps_all_features():
    """2x2 grid over 4 points, one per quadrant: 4 non-empty tiles, 1 feature
    each, no feature lost or duplicated. Proves the spatial index returns the
    same set as the old elementwise scan (intersects predicate)."""
    pts = gpd.GeoDataFrame(
        {"id": [1, 2, 3, 4]},
        geometry=[Point(1, 1), Point(9, 1), Point(1, 9), Point(9, 9)],
        crs="EPSG:3857",
    )
    node = PartitionNode("n", {"nPartitions": 4})  # ceil(sqrt(4)) = 2 → grade 2x2
    tiles = (await node.execute({"input": pts}))["output"]

    assert len(tiles) == 4                      # one per quadrant, all non-empty
    assert all(len(t) == 1 for t in tiles)      # one feature per tile
    ids = sorted(int(t.iloc[0]["id"]) for t in tiles)
    assert ids == [1, 2, 3, 4]                  # none lost, none duplicated


async def test_partition_empty_tile_is_omitted():
    """A single point in a 2x2 grid: only the tile that contains it enters the result."""
    pts = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:3857",
    )
    # degenerate bbox (a point) → the node returns the whole copy in a single tile.
    tiles = (await PartitionNode("n", {"nPartitions": 4}).execute({"input": pts}))["output"]
    assert len(tiles) == 1
    assert len(tiles[0]) == 1


async def test_setfields_compiles_once_renders_per_row():
    """Per-row expression, fixed value and numeric coercion: the per-row result
    is the same with the single template compilation."""
    gdf = gpd.GeoDataFrame(
        {"area": [1_000_000, 2_000_000, 3_000_000]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:3857",
    )
    node = SetFields("n", {"setFields": {
        "area_km2": "{{ row.area / 1000000 }}",   # expression → float per row
        "dobro":    "{{ row.area * 2 }}",          # expression → int per row
        "status":   "ativo",                        # valor fixo
    }})
    out = (await node.execute({"input": gdf}))["output"]

    assert list(out["area_km2"]) == [1.0, 2.0, 3.0]
    assert list(out["dobro"]) == [2_000_000, 4_000_000, 6_000_000]
    assert list(out["status"]) == ["ativo", "ativo", "ativo"]


async def test_setfields_without_expression_uses_vectorized_path():
    """Fixed values only: direct assignment, unchanged result."""
    gdf = gpd.GeoDataFrame(
        {"a": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:3857",
    )
    out = (await SetFields("n", {"setFields": {"flag": "x"}}).execute({"input": gdf}))["output"]
    assert list(out["flag"]) == ["x", "x"]


async def test_setfields_fixed_list_value_is_replicated_per_row():
    """Regression: a NON-scalar fixed value (list) in a field mixed with an expression.
    Without care, `gdf[col] = ["x","y"]` would assign element by element; the
    expected result (like the old behavior) is the SAME list in every cell."""
    gdf = gpd.GeoDataFrame(
        {"a": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:3857",
    )
    node = SetFields("n", {"setFields": {
        "e": "{{ row.a }}",       # forces the row-by-row path
        "tags": ["x", "y"],       # non-scalar fixed value
    }})
    out = (await node.execute({"input": gdf}))["output"]
    assert list(out["tags"]) == [["x", "y"], ["x", "y"]]
    assert list(out["e"]) == [1, 2]


async def test_spatial_filter_intersects_non_unique_index():
    """Regression: a duplicate index must not over-select. b(0) is OUTSIDE the
    mask and must not get in just because it shares label 0 with a(0)."""
    layer = gpd.GeoDataFrame(
        {"id": ["a", "b", "c"]},
        geometry=[Point(1, 1), Point(100, 100), Point(2, 2)],
        crs="EPSG:3857",
        index=[0, 0, 1],
    )
    mask = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects", "invert": False})
    out = (await node.execute({"layer": layer, "mask": mask}))["output"]
    assert sorted(out["id"]) == ["a", "c"]


async def test_spatial_filter_intersects_with_index_right_column():
    """Regression: a pre-existing 'index_right' column (e.g. output of an earlier
    SpatialJoin) must not make sjoin raise ValueError."""
    layer = gpd.GeoDataFrame(
        {"id": ["a"], "index_right": [99]},
        geometry=[Point(1, 1)], crs="EPSG:3857",
    )
    mask = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects", "invert": False})
    out = (await node.execute({"layer": layer, "mask": mask}))["output"]
    assert list(out["id"]) == ["a"]
