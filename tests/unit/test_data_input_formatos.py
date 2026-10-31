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


def test_a_semicolon_csv_with_decimal_points(tmp_path):
    """QGIS (ogr2ogr SEPARATOR=SEMICOLON) and pandas write ';' with '.' decimals:
    every number came back as text."""
    caminho = tmp_path / "x.csv"
    caminho.write_text("nome;lat;lon;valor\nA;-8.7608;-63.9004;1500.5\n", encoding="utf-8")

    lido = _load_file(str(caminho), "csv", "")

    assert lido.iloc[0].tolist() == ["A", -8.7608, -63.9004, 1500.5]


def test_a_semicolon_csv_mixing_integers_and_decimal_commas(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text("valor;codigo\n12;A1\n1.500,5;B2\n", encoding="utf-8")

    lido = _load_file(str(caminho), "csv", "")

    assert lido["valor"].tolist() == [12.0, 1500.5]
    assert lido["codigo"].tolist() == ["A1", "B2"]


def test_the_csv_excel_in_portuguese_saves(tmp_path):
    """'CSV (separado por vírgulas)' in Excel in Portuguese is Windows-1252."""
    caminho = tmp_path / "x.csv"
    caminho.write_bytes("Município;Valor\nJi-Paraná;1500,5\n".encode("cp1252"))

    assert _load_file(str(caminho), "csv", "").to_dict("records") == [{"Município": "Ji-Paraná", "Valor": 1500.5}]


def test_a_semicolon_csv_keeps_dotted_codes_as_text(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text("processo;valor\n12.345.678;1,5\n98.765.432;2,5\n", encoding="utf-8")

    lido = _load_file(str(caminho), "csv", "")

    assert lido["processo"].tolist() == ["12.345.678", "98.765.432"]
    assert lido["valor"].tolist() == [1.5, 2.5]


# ── Review of the URL origin (PR #38) ─────────────────────────────────────────

def _zip(tmp_path, entradas, nome="dados.zip") -> str:
    import zipfile

    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, conteudo in entradas:
            zf.writestr(arcname, conteudo)
    return str(caminho)


def _gdal_proibido(monkeypatch):
    def proibido(*_a, **_k):
        raise AssertionError("GDAL opened the ZIP before the refusal")

    monkeypatch.setattr("flow.utils.leitura_geo.list_layers", proibido)
    monkeypatch.setattr("flow.utils.leitura_geo.read_geodataframe", proibido)


def test_a_kmz_whose_kml_is_a_bomb_is_refused(tmp_path, monkeypatch):
    from flow.utils import leitura_zip

    monkeypatch.setattr(leitura_zip, "_PISO_RAZAO_BYTES", 1024)
    monkeypatch.setattr(leitura_zip, "_RAZAO_MAXIMA", 100)
    _gdal_proibido(monkeypatch)
    caminho = _zip(tmp_path, [("doc.kml", b"<kml>" + b" " * 5_000_000 + b"</kml>")], "mapa.kmz")

    with pytest.raises(leitura_zip.ZipInvalidoError, match="zip bomb"):
        _load_file(caminho, "kmz", "")


def test_the_whole_zip_read_refuses_a_bomb_before_gdal(tmp_path, monkeypatch):
    # 'Arquivo dentro do ZIP' empty: the ZIP went straight to GDAL, which
    # inflates the layer it reads, with no zip-bomb check at all.
    from flow.utils import leitura_zip

    monkeypatch.setattr(leitura_zip, "_PISO_RAZAO_BYTES", 1024)
    monkeypatch.setattr(leitura_zip, "_RAZAO_MAXIMA", 100)
    _gdal_proibido(monkeypatch)
    caminho = _zip(tmp_path, [("municipios.dbf", b"0" * 5_000_000), ("municipios.shp", b"x")])

    with pytest.raises(leitura_zip.ZipInvalidoError, match="zip bomb"):
        _load_file(caminho, "zip", "")


def test_a_zip_of_one_shapefile_is_opened_once_by_gdal(tmp_path, monkeypatch):
    from flow.utils import leitura_geo

    pasta = tmp_path / "shp"
    pasta.mkdir()
    _obras().to_file(pasta / "obras.shp")
    caminho = _zip(tmp_path, [(p.name, p.read_bytes()) for p in sorted(pasta.iterdir())])

    listagens = []
    original = leitura_geo.list_layers
    monkeypatch.setattr(leitura_geo, "list_layers", lambda f: listagens.append(f) or original(f))
    leitura_geo._zip_tem_vrt.cache_clear()
    analises = []
    original_vrt = leitura_geo._zip_has_vrt
    monkeypatch.setattr(leitura_geo, "_zip_has_vrt", lambda f: analises.append(f) or original_vrt(f))

    lido = _load_file(caminho, "zip", "")

    assert lido["nome"].tolist() == ["Escola Ji-Paraná", "Posto"]
    assert listagens == []          # one layer: no listing before the read
    assert len(analises) == 1       # the .vrt check parsed the ZIP once


def test_a_zip_with_two_shapefiles_still_names_the_one_read(tmp_path, monkeypatch, caplog):
    pasta = tmp_path / "shp"
    pasta.mkdir()
    _obras().to_file(pasta / "a_obras.shp")
    _obras().to_file(pasta / "b_postos.shp")
    caminho = _zip(tmp_path, [(p.name, p.read_bytes()) for p in sorted(pasta.iterdir())])

    with caplog.at_level("WARNING"):
        lido = _load_file(caminho, "zip", "")

    assert len(lido) == 2
    assert "o ZIP tem 2 camadas" in caplog.text


def test_a_json_with_a_bom_is_read(tmp_path):
    # The format check skips the BOM IIS/.NET portals write; the read refused it.
    caminho = tmp_path / "dados.json"
    caminho.write_bytes(b'\xef\xbb\xbf[{"municipio": "Porto Velho"}]')

    assert _load_file(str(caminho), "json", "") == [{"municipio": "Porto Velho"}]


def test_csv_with_coordinates_shares_the_data_input_conversion(tmp_path):
    caminho = tmp_path / "x.csv"
    caminho.write_text('nome,lat,lon\nA,"-8,7608","-63,9004"\nB,,\n', encoding="utf-8")

    lido = _read_csv_as_geodataframe(str(caminho), "lat", "lon", "EPSG:4326")

    assert lido.geometry.iloc[0].x == pytest.approx(LON)
    assert lido.geometry.iloc[0].y == pytest.approx(LAT)
    assert lido.geometry.iloc[1] is None  # not POINT (NaN NaN)


def test_the_format_fields_keep_older_editors_working():
    # An editor from before `any` reads `field`/`in` only: it must show the
    # field on every origin instead of breaking the form on `r.in`.
    from flow.nodes.datasource.data_input import DataInput

    campos = {p["name"]: p for p in DataInput.description()["properties"]}
    for nome in ("zipMember", "skipRows", "latColumn", "lonColumn"):
        regra = campos[nome]["visibleWhen"]
        assert "any" in regra
        assert regra["field"] == "context"
        assert sorted(regra["in"]) == ["artifacts", "drive", "url"]
