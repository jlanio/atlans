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

from flow.executor.utils import MAX_COLUNAS, _colunas_das_saidas


def test_lista_as_colunas_de_um_dataframe():
    df = pd.DataFrame({"cod": [1], "populacao": [2]})
    assert _colunas_das_saidas({"result": df}) == {"result": ["cod", "populacao"]}


def test_uma_entrada_por_saida():
    saidas = {"a": pd.DataFrame({"x": [1]}), "b": pd.DataFrame({"y": [1]})}
    assert _colunas_das_saidas(saidas) == {"a": ["x"], "b": ["y"]}


def test_ignora_saida_que_nao_e_tabela():
    assert _colunas_das_saidas({"texto": "abc", "n": 42}) is None


def test_dict_vazio_devolve_none():
    # None and not {}: the key only exists in node_stats when there is something to say.
    assert _colunas_das_saidas({}) is None


# ── The geometry stays out ───────────────────────────────────────────────────

def test_geometria_nao_e_sugerida():
    """Suggesting the geometry is suggesting what always fails: in the Join,
    bringing it from B collides with A's; in the filter, comparing geometry to
    a value breaks too.
    """
    gdf = gpd.GeoDataFrame({"cod": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    assert _colunas_das_saidas({"output": gdf}) == {"output": ["cod"]}


def test_pergunta_ao_geodataframe_em_vez_de_adivinhar_pelo_nome():
    """The database nodes use 'geom', not 'geometry'. Excluding by a fixed name
    would let the geometry through here — and would drop an ATTRIBUTE named
    'geom' in a plain DataFrame."""
    gdf = gpd.GeoDataFrame({"cod": [1], "geom": [Point(0, 0)]}, geometry="geom")
    assert _colunas_das_saidas({"output": gdf}) == {"output": ["cod"]}


def test_atributo_chamado_geom_em_tabela_comum_continua_valendo():
    df = pd.DataFrame({"cod": [1], "geom": ["texto qualquer"]})
    assert _colunas_das_saidas({"result": df}) == {"result": ["cod", "geom"]}


# ── Truncamento ──────────────────────────────────────────────────────────────

def test_corta_no_teto():
    largo = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUNAS + 50)})
    assert len(_colunas_das_saidas({"result": largo})["result"]) == MAX_COLUNAS


def test_nao_inventa_item_na_lista_ao_cortar():
    """REGRESSION: the truncation marker ("… (+50)") went along with the columns,
    and the UI renders EACH item as a clickable suggestion — you could insert the
    marker as if it were a column name. Whoever displays it infers the
    truncation from the length."""
    largo = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUNAS + 50)})
    nomes = _colunas_das_saidas({"result": largo})["result"]

    assert all(n.startswith("c") for n in nomes), [n for n in nomes if not n.startswith("c")]
    assert nomes[-1] == f"c{MAX_COLUNAS - 1}"


@pytest.mark.parametrize("entrada", [None, {"x": None}])
def test_nao_quebra_com_entrada_estranha(entrada):
    _colunas_das_saidas(entrada)
