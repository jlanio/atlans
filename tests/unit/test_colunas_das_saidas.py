"""
Colunas gravadas por execucao, que viram sugestao no editor.

A lista alimenta campos que pedem NOME DE COLUNA DE ATRIBUTO (a chave do Join,
a coluna do filtro, as colunas a trazer). O que entra nela vira botao clicavel
na interface — entao um item que nao serve como nome de coluna nao e ruido
inofensivo, e um caminho para configurar o no errado.
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
    # None e nao {}: a chave so existe no node_stats quando ha o que dizer.
    assert _colunas_das_saidas({}) is None


# ── A geometria fica de fora ─────────────────────────────────────────────────

def test_geometria_nao_e_sugerida():
    """Sugerir a geometria e sugerir o que sempre falha: no Join, traze-la de B
    colide com a de A; no filtro, comparar geometria com um valor tambem quebra.
    """
    gdf = gpd.GeoDataFrame({"cod": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
    assert _colunas_das_saidas({"output": gdf}) == {"output": ["cod"]}


def test_pergunta_ao_geodataframe_em_vez_de_adivinhar_pelo_nome():
    """Os nos de banco usam 'geom', nao 'geometry'. Excluir por nome fixo
    deixaria a geometria passar aqui — e sumiria com um ATRIBUTO chamado 'geom'
    num DataFrame comum."""
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
    """REGRESSAO: o marcador de corte ("… (+50)") ia junto das colunas, e a UI
    renderiza CADA item como sugestao clicavel — dava para inserir o marcador
    como se fosse nome de coluna. Quem exibe deduz o corte pelo tamanho."""
    largo = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUNAS + 50)})
    nomes = _colunas_das_saidas({"result": largo})["result"]

    assert all(n.startswith("c") for n in nomes), [n for n in nomes if not n.startswith("c")]
    assert nomes[-1] == f"c{MAX_COLUNAS - 1}"


@pytest.mark.parametrize("entrada", [None, {"x": None}])
def test_nao_quebra_com_entrada_estranha(entrada):
    _colunas_das_saidas(entrada)
