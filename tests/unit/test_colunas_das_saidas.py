"""
Columns recorded per run, which become suggestions in the editor.

The list feeds fields that ask for an ATTRIBUTE COLUMN NAME (the Join key,
the filter column, the columns to bring in). Whatever goes into it becomes a
clickable button in the interface — so an item that does not work as a column
name is not harmless noise, it is a path to configuring the node wrong.
"""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from flow.executor.utils import MAX_COLUMNS, _output_columns


def test_lists_the_columns_of_a_dataframe():
    df = pd.DataFrame({"cod": [1], "populacao": [2]})
    assert _output_columns({"result": df}) == {"result": ["cod", "populacao"]}


def test_one_entry_per_output():
    saidas = {"a": pd.DataFrame({"x": [1]}), "b": pd.DataFrame({"y": [1]})}
    assert _output_columns(saidas) == {"a": ["x"], "b": ["y"]}


def test_ignores_output_that_is_not_a_table():
    assert _output_columns({"texto": "abc", "n": 42}) is None


def test_empty_dict_returns_none():
    # None and not {}: the key only exists in node_stats when there is something to say.
    assert _output_columns({}) is None


# ── The geometry stays out ───────────────────────────────────────────────────

def test_geometry_is_not_suggested():
    """Suggesting the geometry is suggesting what always fails: in the Join,
    bringing it from B collides with A's; in the filter, comparing geometry to
    a value breaks too.
    """
    gdf = gpd.GeoDataFrame({"cod": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    assert _output_columns({"output": gdf}) == {"output": ["cod"]}


def test_asks_the_geodataframe_instead_of_guessing_by_name():
    """The database nodes use 'geom', not 'geometry'. Excluding by a fixed name
    would let the geometry through here — and would drop an ATTRIBUTE named
    'geom' in a plain DataFrame."""
    gdf = gpd.GeoDataFrame({"cod": [1], "geom": [Point(0, 0)]}, geometry="geom")
    assert _output_columns({"output": gdf}) == {"output": ["cod"]}


def test_attribute_named_geom_in_plain_table_still_counts():
    df = pd.DataFrame({"cod": [1], "geom": ["texto qualquer"]})
    assert _output_columns({"result": df}) == {"result": ["cod", "geom"]}


# ── Truncamento ──────────────────────────────────────────────────────────────

def test_truncates_at_the_ceiling():
    wide = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUMNS + 50)})
    assert len(_output_columns({"result": wide})["result"]) == MAX_COLUMNS


def test_does_not_invent_list_item_when_truncating():
    """REGRESSION: the truncation marker ("… (+50)") went along with the columns,
    and the UI renders EACH item as a clickable suggestion — you could insert the
    marker as if it were a column name. Whoever displays it infers the
    truncation from the length."""
    wide = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUMNS + 50)})
    nomes = _output_columns({"result": wide})["result"]

    assert all(n.startswith("c") for n in nomes), [n for n in nomes if not n.startswith("c")]
    assert nomes[-1] == f"c{MAX_COLUMNS - 1}"


@pytest.mark.parametrize("entrada", [None, {"x": None}])
def test_does_not_break_on_odd_input(entrada):
    _output_columns(entrada)
