"""Equivalência de saída dos nós otimizados no batch de desempenho.

Os refactors (índice espacial no PartitionNode, compilação única do template no
SetFields) mudam o COMO, não o QUE: estes testes fixam o resultado esperado para
uma entrada conhecida, de modo que qualquer regressão de comportamento apareça.
"""
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box  # noqa: E402

from flow.nodes.spatial.partition import PartitionNode  # noqa: E402
from flow.nodes.spatial.spatial_filter import SpatialFilterNode  # noqa: E402
from flow.nodes.action.field_transformer import SetFields  # noqa: E402


async def test_partition_indexado_mantem_todas_as_feicoes():
    """Grade 2x2 sobre 4 pontos, um por quadrante: 4 tiles não-vazios, 1 feição
    cada, nenhuma feição perdida ou duplicada. Prova que o índice espacial
    devolve o mesmo conjunto que o scan elementwise antigo (predicado intersects)."""
    pts = gpd.GeoDataFrame(
        {"id": [1, 2, 3, 4]},
        geometry=[Point(1, 1), Point(9, 1), Point(1, 9), Point(9, 9)],
        crs="EPSG:3857",
    )
    node = PartitionNode("n", {"nPartitions": 4})  # ceil(sqrt(4)) = 2 → grade 2x2
    tiles = (await node.execute({"input": pts}))["output"]

    assert len(tiles) == 4                      # um por quadrante, todos não-vazios
    assert all(len(t) == 1 for t in tiles)      # uma feição por tile
    ids = sorted(int(t.iloc[0]["id"]) for t in tiles)
    assert ids == [1, 2, 3, 4]                  # nenhuma perdida, nenhuma duplicada


async def test_partition_tile_vazio_e_omitido():
    """Um ponto só numa grade 2x2: só o tile que o contém entra no resultado."""
    pts = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:3857",
    )
    # bbox degenerada (um ponto) → o nó devolve a cópia inteira num tile só.
    tiles = (await PartitionNode("n", {"nPartitions": 4}).execute({"input": pts}))["output"]
    assert len(tiles) == 1
    assert len(tiles[0]) == 1


async def test_setfields_compila_uma_vez_rende_por_linha():
    """Expressão por linha, valor fixo e coerção numérica: o resultado por linha
    é o mesmo com a compilação única do template."""
    gdf = gpd.GeoDataFrame(
        {"area": [1_000_000, 2_000_000, 3_000_000]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:3857",
    )
    node = SetFields("n", {"setFields": {
        "area_km2": "{{ row.area / 1000000 }}",   # expressão → float por linha
        "dobro":    "{{ row.area * 2 }}",          # expressão → int por linha
        "status":   "ativo",                        # valor fixo
    }})
    out = (await node.execute({"input": gdf}))["output"]

    assert list(out["area_km2"]) == [1.0, 2.0, 3.0]
    assert list(out["dobro"]) == [2_000_000, 4_000_000, 6_000_000]
    assert list(out["status"]) == ["ativo", "ativo", "ativo"]


async def test_setfields_sem_expressao_usa_caminho_vetorial():
    """Só valores fixos: atribuição direta, resultado inalterado."""
    gdf = gpd.GeoDataFrame(
        {"a": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:3857",
    )
    out = (await SetFields("n", {"setFields": {"flag": "x"}}).execute({"input": gdf}))["output"]
    assert list(out["flag"]) == ["x", "x"]


async def test_setfields_valor_fixo_lista_e_replicado_por_linha():
    """Regressão: valor fixo NÃO-escalar (lista) num campo misto com expressão.
    Sem o cuidado, `gdf[col] = ["x","y"]` atribuiria elemento a elemento; o
    esperado (como o comportamento antigo) é a MESMA lista em cada célula."""
    gdf = gpd.GeoDataFrame(
        {"a": [1, 2]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:3857",
    )
    node = SetFields("n", {"setFields": {
        "e": "{{ row.a }}",       # força o caminho linha-a-linha
        "tags": ["x", "y"],       # valor fixo não-escalar
    }})
    out = (await node.execute({"input": gdf}))["output"]
    assert list(out["tags"]) == [["x", "y"], ["x", "y"]]
    assert list(out["e"]) == [1, 2]


async def test_spatial_filter_intersects_indice_nao_unico():
    """Regressão: índice duplicado não pode super-selecionar. b(0) está FORA da
    máscara e não pode entrar só por compartilhar o rótulo 0 com a(0)."""
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


async def test_spatial_filter_intersects_com_coluna_index_right():
    """Regressão: uma coluna 'index_right' pré-existente (ex.: saída de um
    SpatialJoin anterior) não pode fazer o sjoin levantar ValueError."""
    layer = gpd.GeoDataFrame(
        {"id": ["a"], "index_right": [99]},
        geometry=[Point(1, 1)], crs="EPSG:3857",
    )
    mask = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:3857")
    node = SpatialFilterNode("n", {"filter_mode": "mask", "predicate": "intersects", "invert": False})
    out = (await node.execute({"layer": layer, "mask": mask}))["output"]
    assert list(out["id"]) == ["a"]
