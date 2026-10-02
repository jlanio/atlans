# tests/unit/test_get_first_gdf_diagnostico.py
"""A mensagem de `get_first_gdf` precisa dizer O QUE chegou.

SaveToPostGIS aceita apenas GeoDataFrame, enquanto DataInput entrega
GeoDataFrame, DataFrame, dict, list ou bytes conforme a extensao do arquivo do
Drive. Ligar um CSV no PostGIS falhava com "Nenhum GeoDataFrame encontrado nos
inputs." — sem chave, sem tipo, sem pista de onde olhar.
"""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from flow.nodes.base import BaseNode


class _Node(BaseNode):
    """BaseNode e abstrata; aqui so interessa o helper de inputs."""

    def __init__(self):
        pass

    @classmethod
    def description(cls):  # pragma: no cover - exigido pela ABC
        return {"name": "_Node", "type": "output", "properties": []}

    async def execute(self, inputs):  # pragma: no cover - nao usado
        return {}


def _gdf(vazio: bool = False) -> gpd.GeoDataFrame:
    if vazio:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, geometry="geometry", crs="EPSG:4326")


def test_retorna_o_primeiro_gdf_nao_vazio():
    alvo = _gdf()
    assert _Node().get_first_gdf({"metadata": {"a": 1}, "output": alvo}) is alvo


def test_erro_lista_chaves_e_tipos_recebidos():
    """O caso do CSV: DataInput entrega DataFrame + metadata, PostGIS quer GDF."""
    with pytest.raises(ValueError) as exc:
        _Node().get_first_gdf({"output": pd.DataFrame({"a": [1]}), "metadata": {"x": 1}})

    msg = str(exc.value)
    assert "output" in msg and "DataFrame" in msg      # chave e tipo do dado
    assert "metadata" in msg and "dict" in msg


def test_erro_sinaliza_gdf_vazio_em_vez_de_so_dizer_ausente():
    """GeoDataFrame vazio e ignorado pelo loop — sem esta pista o usuario
    procuraria erro de conexao, nao filtro que nao retornou nada."""
    with pytest.raises(ValueError) as exc:
        _Node().get_first_gdf({"output": _gdf(vazio=True)})

    msg = str(exc.value)
    assert "vazio" in msg.lower()
    assert "output" in msg


def test_inputs_vazios_nao_quebram_a_mensagem():
    with pytest.raises(ValueError, match="Nenhum GeoDataFrame"):
        _Node().get_first_gdf({})
