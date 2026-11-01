"""
Nodes must not change the frame they receive: the same upstream frame feeds
other branches and `$Alias` references in the same run (review of 2026-10-31).
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def _gdf(**cols):
    n = len(next(iter(cols.values()))) if cols else 2
    return gpd.GeoDataFrame(
        cols or {"a": [1, 2]},
        geometry=[Point(i, i) for i in range(n)],
        crs="EPSG:4326",
    )


def test_set_fields_leaves_its_input_untouched():
    from flow.nodes.action.field_transformer import SetFields

    entrada = _gdf(a=[1, 2])
    antes = entrada.copy()
    node = SetFields("n1", {"setFields": {"novo": "x", "a": 9}, "removeFields": {}, "renameFields": {}})
    saida = node.execute_sync({"output": entrada})["output"]

    assert saida is not entrada
    assert saida["novo"].tolist() == ["x", "x"] and saida["a"].tolist() == [9, 9]
    pd.testing.assert_frame_equal(entrada, antes)


def test_set_fields_with_expressions_leaves_its_input_untouched():
    from flow.nodes.action.field_transformer import SetFields

    entrada = _gdf(a=[1, 2])
    antes = entrada.copy()
    node = SetFields("n1", {"setFields": {"dobro": "{{ row.a * 2 }}"}, "removeFields": {}, "renameFields": {}})
    saida = node.execute_sync({"output": entrada})["output"]

    assert saida["dobro"].tolist() == [2, 4]
    pd.testing.assert_frame_equal(entrada, antes)


def test_remove_duplicates_reports_the_removed_rows_with_a_repeated_index():
    import asyncio
    from flow.nodes.action.remove_duplicates import RemoveDuplicates

    # The output of a spatial join repeats index labels.
    entrada = gpd.GeoDataFrame(
        {"cod": ["A", "A", "B"]},
        geometry=[Point(0, 0), Point(0, 0), Point(1, 1)],
        index=[7, 7, 8],
        crs="EPSG:4326",
    )
    out = asyncio.run(RemoveDuplicates("n", {"fields": ["cod"], "keep": "first"}).execute({"output": entrada}))
    assert out["removed_count"] == 1
    assert len(out["removed"]) == 1 and len(out["output"]) == 2


def test_spatial_filter_bbox_inverted_keeps_rows_outside_with_a_shared_label():
    import asyncio
    from flow.nodes.spatial.spatial_filter import SpatialFilterNode as SpatialFilter

    entrada = gpd.GeoDataFrame(
        {"n": ["dentro", "fora"]},
        geometry=[Point(0.5, 0.5), Point(5, 5)],
        index=[3, 3],
        crs="EPSG:4326",
    )
    node = SpatialFilter("n", {"filter_mode": "bbox", "bbox": "0,0,1,1", "invert": True})
    out = asyncio.run(node.execute({"layer": entrada}))["output"]
    assert out["n"].tolist() == ["fora"]
    node = SpatialFilter("n", {"filter_mode": "bbox", "bbox": "0,0,1,1", "invert": False})
    out = asyncio.run(node.execute({"layer": entrada}))["output"]
    assert out["n"].tolist() == ["dentro"]


def test_a_spilled_frame_keeps_its_index(tmp_path, monkeypatch):
    from flow.executor import spill

    monkeypatch.setattr(spill, "_SPILL_THRESHOLD_MB", 0.000001)
    monkeypatch.setattr(spill, "_SPILL_BASE_DIR", str(tmp_path))
    entrada = gpd.GeoDataFrame({"a": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], index=[10, 20], crs="EPSG:4326")
    salvo = spill._spill_to_disk("t1", "n", {"output": entrada})
    assert salvo["output"].get("__spilled__")
    restaurado = spill._load_from_disk(salvo)["output"]
    assert restaurado.index.tolist() == [10, 20]
