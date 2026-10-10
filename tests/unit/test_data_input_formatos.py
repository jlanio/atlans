"""
Entrada de Dados reads back what Salvar arquivo writes.

The artifact picker offers every artifact of the workspace, and DataInput
picks the reader by the artifact's format. Before: the default CSV (';') came
back as a single column, with no error; every .xlsx failed for lack of
openpyxl, which the executor does not ship; a GeoPackage table broke on `.crs`;
and a .kmz came back as raw bytes.
"""
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from flow.nodes.datasource.data_input import _load_file
from flow.nodes.datasource.read_csv_with_coords import _read_csv_as_geodataframe
from flow.nodes.outputs.save_file import atributos_gravaveis, gravar

LON, LAT = -63.9004, -8.7608


def _obras() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"nome": ["Escola Ji-Paraná", "Posto"], "valor": [1500.5, 20.25]},
        geometry=[Point(LON, LAT), Point(-63.8312, -8.7421)],
        crs="EPSG:4326",
    )


def _gravado(tmp_path, dado, formato: str, **opcoes) -> str:
    padrao = {"camada": "obras", "campo_nome": "", "geometria": "auto", "separador": ";", "planilha": "obras"}
    return gravar(atributos_gravaveis(dado), formato, str(tmp_path), "obras", {**padrao, **opcoes})


@pytest.mark.parametrize("formato", ["gpkg", "kml", "kmz"])
def test_reads_back_a_layer(tmp_path, formato):
    lido = _load_file(_gravado(tmp_path, _obras(), formato), formato, "")

    assert isinstance(lido, gpd.GeoDataFrame)
    assert lido.crs.to_epsg() == 4326
    assert lido["nome"].tolist() == ["Escola Ji-Paraná", "Posto"]
    assert lido.geometry.iloc[0].x == pytest.approx(LON)


def test_reads_back_a_geopackage_table(tmp_path):
    tabela = pd.DataFrame({"municipio": ["Porto Velho"], "obras": [12]})

    lido = _load_file(_gravado(tmp_path, tabela, "gpkg"), "gpkg", "EPSG:4326")

    assert not isinstance(lido, gpd.GeoDataFrame)
    assert lido.to_dict("records") == [{"municipio": "Porto Velho", "obras": 12}]


def test_reads_back_xlsx_without_openpyxl(tmp_path):
    lido = _load_file(_gravado(tmp_path, _obras(), "xlsx"), "xlsx", "")

    assert list(lido.columns) == ["nome", "valor", "longitude", "latitude"]
    assert lido["valor"].tolist() == [1500.5, 20.25]

    # Only text: GDAL would take the header row as data unless told otherwise.
    so_texto = pd.DataFrame({"municipio": ["Porto Velho", "Ariquemes"], "uf": ["RO", "RO"]})
    lido = _load_file(_gravado(tmp_path, so_texto, "xlsx"), "xlsx", "")
    assert lido.to_dict("records") == [
        {"municipio": "Porto Velho", "uf": "RO"}, {"municipio": "Ariquemes", "uf": "RO"},
    ]


@pytest.mark.parametrize("separador", [";", ","])
def test_reads_back_the_csv_with_either_separator(tmp_path, separador):
    lido = _load_file(_gravado(tmp_path, _obras(), "csv", separador=separador), "csv", "")

    assert list(lido.columns) == ["nome", "valor", "longitude", "latitude"]
    assert lido["valor"].tolist() == [1500.5, 20.25]
    assert lido["longitude"].tolist() == [LON, -63.8312]


def test_a_comma_csv_reads_as_before(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text('nome,obs\n"Obra A","fase 1; fase 2"\n', encoding="utf-8")

    assert _load_file(str(caminho), "csv", "").to_dict("records") == [{"nome": "Obra A", "obs": "fase 1; fase 2"}]


def test_csv_with_coordinates_reads_the_semicolon_csv(tmp_path):
    caminho = _gravado(tmp_path, _obras(), "csv")

    lido = _read_csv_as_geodataframe(caminho, "latitude", "longitude", "EPSG:4326")

    assert lido.geometry.iloc[0].x == pytest.approx(LON)
    assert lido.geometry.iloc[0].y == pytest.approx(LAT)


def test_reads_a_kmz_made_of_several_kml(tmp_path):
    """LIBKML's own KMZ (doc.kml linking layers/*.kml) is read as it is."""
    import pyogrio

    caminho = str(tmp_path / "camadas.kmz")
    pyogrio.write_dataframe(_obras(), caminho, layer="obras", driver="LIBKML")

    lido = _load_file(caminho, "kmz", "")

    assert lido["nome"].tolist() == ["Escola Ji-Paraná", "Posto"]
