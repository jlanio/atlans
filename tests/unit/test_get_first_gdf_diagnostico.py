# tests/unit/test_get_first_gdf_diagnostico.py
"""The `get_first_gdf` message must say WHAT arrived.

SaveToPostGIS only accepts a GeoDataFrame, while DataInput delivers a
GeoDataFrame, DataFrame, dict, list or bytes depending on the Drive file's
extension. Connecting a CSV to PostGIS failed with "Nenhum GeoDataFrame encontrado nos
inputs." (no GeoDataFrame found in the inputs) — no key, no type, no clue where to look.
"""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from flow.nodes.base import BaseNode


class _Node(BaseNode):
    """BaseNode is abstract; here only the inputs helper matters."""

    def __init__(self):
        pass

    @classmethod
    def description(cls):  # pragma: no cover - required by the ABC
        return {"name": "_Node", "type": "output", "properties": []}

    async def execute(self, inputs):  # pragma: no cover - unused
        return {}


def _gdf(vazio: bool = False) -> gpd.GeoDataFrame:
    if vazio:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, geometry="geometry", crs="EPSG:4326")


def test_returns_the_first_non_empty_gdf():
    alvo = _gdf()
    assert _Node().get_first_gdf({"metadata": {"a": 1}, "output": alvo}) is alvo


def test_error_lists_received_keys_and_types():
    """O caso do CSV: DataInput entrega DataFrame + metadata, PostGIS quer GDF."""
    with pytest.raises(ValueError) as exc:
        _Node().get_first_gdf({"output": pd.DataFrame({"a": [1]}), "metadata": {"x": 1}})

    msg = str(exc.value)
    assert "output" in msg and "DataFrame" in msg      # the data's key and type
    assert "metadata" in msg and "dict" in msg


def test_error_flags_empty_gdf_instead_of_just_saying_missing():
    """An empty GeoDataFrame is ignored by the loop — without this clue the user
    would look for a connection error, not a filter that returned nothing."""
    with pytest.raises(ValueError) as exc:
        _Node().get_first_gdf({"output": _gdf(vazio=True)})

    msg = str(exc.value)
    assert "vazio" in msg.lower()
    assert "output" in msg


def test_empty_inputs_do_not_break_the_message():
    with pytest.raises(ValueError, match="Nenhum GeoDataFrame"):
        _Node().get_first_gdf({})
