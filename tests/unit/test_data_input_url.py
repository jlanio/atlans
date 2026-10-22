"""
Entrada de Dados with the URL origin, and the ZIP read through one member.

The ZIP cases are the ones that failed with the Drive too (geopandas 1.1.4,
pyogrio 0.13.0): shapefile in a subfolder, two shapefiles, CSV in cp1252,
INMET's CSVs with metadata above the header.
"""
import io
import zipfile

import geopandas as gpd
import httpx
import pandas as pd
import pytest
from shapely.geometry import Point

from flow.nodes.datasource.data_input import DataInput, _load_file
from tests.unit._rede_falsa import RedeFalsa

BASE = "https://dados.exemplo.gov.br"

CSV_EXCEL = "codigo;nome;valor;lat;lon\n1;São Paulo;1500,5;-23,55;-46,63\n2;Manaus;12,25;-3,10;-60,02\n".encode("cp1252")

INMET = (
    "REGIAO:;CO\nUF:;DF\nESTACAO:;BRASILIA\nCODIGO (WMO):;A001\nLATITUDE:;-15,78\n"
    "LONGITUDE:;-47,92\nALTITUDE:;1160,96\nDATA DE FUNDACAO:;07/05/00\n"
    "Data;Hora UTC;PRECIPITACAO TOTAL, HORARIO (mm);TEMPERATURA DO AR - BULBO SECO, HORARIA (C)\n"
    "2024/01/01;0000 UTC;0;21,4\n2024/01/01;0100 UTC;0,2;20,9\n"
).encode("latin-1")


@pytest.fixture
def rede(monkeypatch):
    return RedeFalsa().instalar(monkeypatch)


def _no(**props):
    parametros = {"context": "url", "url": f"{BASE}/arquivo", "expectedFormat": "csv", **props}
    return DataInput(node_id="n1", parameters=parametros)


def _shapefile(tmp_path, nome, n):
    pasta = tmp_path / nome
    pasta.mkdir()
    gpd.GeoDataFrame(
        {"nome": [f"{nome}{i}" for i in range(n)]},
        geometry=[Point(-50 + i, -10 + i) for i in range(n)],
        crs="EPSG:4674",
    ).to_file(pasta / f"{nome}.shp")
    return {p.name: p.read_bytes() for p in pasta.iterdir()}


def _zip(entradas) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in entradas:
            zf.writestr(nome, conteudo)
    return buffer.getvalue()


# ── CSV ─────────────────────────────────────────────────────────────────────

async def test_an_excel_csv_becomes_points(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=CSV_EXCEL, headers={
        "Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="capitais.csv"',
        "ETag": '"abc"', "Last-Modified": "Wed, 21 Oct 2026 10:00:00 GMT",
    }))

    saida = await _no(latColumn="lat", lonColumn="lon").execute({})

    gdf = saida["output"]
    assert isinstance(gdf, gpd.GeoDataFrame) and gdf.crs.to_epsg() == 4326
    assert gdf["valor"].tolist() == [1500.5, 12.25]
    assert gdf.geometry.iloc[0].x == pytest.approx(-46.63)
    assert gdf.geometry.iloc[0].y == pytest.approx(-23.55)
    meta = saida["metadata"]
    assert meta["context"] == "url" and meta["file_id"] is None
    assert meta["original_name"] == "capitais.csv" and meta["extension"] == "csv"
    assert meta["final_url"] == f"{BASE}/arquivo"
    assert meta["etag"] == '"abc"' and meta["last_modified"].startswith("Wed")
    assert meta["size_bytes"] == len(CSV_EXCEL) and meta["zip_member"] is None


async def test_a_row_without_coordinates_has_no_geometry(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=b"nome,lat,lon\nA,-1.5,-2.5\nB,,\n"))

    gdf = (await _no(latColumn="lat", lonColumn="lon").execute({}))["output"]

    assert gdf.geometry.iloc[0] == Point(-2.5, -1.5)
    assert gdf.geometry.iloc[1] is None


async def test_a_coordinate_that_is_not_a_number_is_named(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=b"nome,lat,lon\nA,norte,-2\n"))

    with pytest.raises(ValueError, match="'lat' tem valor que não é número: 'norte'"):
        await _no(latColumn="lat", lonColumn="lon").execute({})


async def test_only_one_coordinate_column_is_refused():
    with pytest.raises(ValueError, match="as duas colunas"):
        await _no(latColumn="lat").execute({})


async def test_skips_the_lines_above_the_header(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=INMET, headers={"Content-Type": "text/csv"}))

    tabela = (await _no(skipRows=8).execute({}))["output"]

    assert list(tabela.columns)[:2] == ["Data", "Hora UTC"]
    assert tabela["TEMPERATURA DO AR - BULBO SECO, HORARIA (C)"].tolist() == [21.4, 20.9]


# ── Expected format ───────────────────────────────────────────────────────────

async def test_the_format_must_be_chosen_before_downloading(rede):
    with pytest.raises(ValueError, match="Escolha o 'Formato esperado'"):
        await _no(expectedFormat="escolher").execute({})
    assert rede.pedidos == []


async def test_geojson_served_as_json(rede):
    corpo = gpd.GeoDataFrame({"n": [1]}, geometry=[Point(-47, -15)], crs="EPSG:4326").to_json()
    rede.rota(f"{BASE}/api/limites.json", httpx.Response(200, text=corpo, headers={"Content-Type": "application/json"}))

    saida = await _no(url=f"{BASE}/api/limites.json", expectedFormat="geojson").execute({})

    assert isinstance(saida["output"], gpd.GeoDataFrame)
    assert saida["metadata"]["extension"] == "geojson"


async def test_json_chosen_for_a_geojson_stays_json(rede):
    corpo = gpd.GeoDataFrame({"n": [1]}, geometry=[Point(-47, -15)], crs="EPSG:4326").to_json()
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, text=corpo))

    saida = await _no(expectedFormat="json").execute({})

    assert saida["output"]["type"] == "FeatureCollection"


async def test_a_zip_without_an_extension_in_the_url(rede, tmp_path):
    rede.rota(f"{BASE}/download.php", httpx.Response(200, content=_zip(_shapefile(tmp_path, "municipios", 3).items())))

    saida = await _no(url=f"{BASE}/download.php?id=123", expectedFormat="zip").execute({})

    assert saida["output"]["nome"].tolist() == ["municipios0", "municipios1", "municipios2"]
    assert saida["metadata"]["extension"] == "zip"


async def test_an_html_page_instead_of_the_file(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, text="<!DOCTYPE html><html><body>Entrar</body></html>"))

    with pytest.raises(ValueError, match="Esperava CSV, mas o servidor devolveu uma página HTML") as erro:
        await _no().execute({})
    assert "tela de login" in str(erro.value)


async def test_a_json_error_instead_of_the_zip(rede):
    rede.rota(f"{BASE}/municipios.zip", httpx.Response(200, json={"erro": "cota excedida"}))

    with pytest.raises(ValueError, match="Esperava ZIP, mas o servidor devolveu um JSON") as erro:
        await _no(url=f"{BASE}/municipios.zip", expectedFormat="zip").execute({})
    assert "cota excedida" in str(erro.value)
    assert "escolha 'JSON' em 'Formato esperado'" in str(erro.value)


async def test_a_zip_where_a_csv_was_expected_names_the_option(rede, tmp_path):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip([("a.csv", b"x\n")])))

    with pytest.raises(ValueError, match="Esperava CSV, mas o servidor devolveu um ZIP") as erro:
        await _no().execute({})
    assert "escolha 'ZIP (shapefile ou outros arquivos dentro)'" in str(erro.value)


async def test_a_spreadsheet_is_not_taken_for_a_zip(rede):
    planilha = _zip([("[Content_Types].xml", b"<Types/>"), ("xl/workbook.xml", b"<workbook/>")])
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=planilha))

    with pytest.raises(ValueError, match="devolveu uma planilha XLSX") as erro:
        await _no(expectedFormat="zip").execute({})
    assert "escolha 'XLSX (Excel)'" in str(erro.value)


async def test_gzip_is_named(rede):
    rede.rota(f"{BASE}/focos.csv.gz", httpx.Response(200, content=b"\x1f\x8b\x08\x00" + b"\x00" * 20))

    with pytest.raises(ValueError, match=r"gzip \(\.gz\)") as erro:
        await _no(url=f"{BASE}/focos.csv.gz").execute({})
    assert "versão .zip ou sem compressão" in str(erro.value)


async def test_an_empty_file(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=b""))

    with pytest.raises(ValueError, match="vazio"):
        await _no().execute({})


def test_format_fields_follow_the_choice_only_on_the_url():
    """On the URL origin a field shows for the formats it serves; on the Drive
    and in Artifacts the file's format is only known at run time, so it always
    shows (node-config-form evaluates `any` as an OR)."""
    props = {p["name"]: p for p in DataInput.description()["properties"]}
    na_origem_armazenada = {"field": "context", "in": ["drive", "artifacts"]}

    assert props["expectedFormat"]["visibleWhen"] == {"field": "context", "in": ["url"]}
    assert props["zipMember"]["visibleWhen"] == {
        "any": [na_origem_armazenada, {"field": "expectedFormat", "in": ["zip"]}]}
    assert props["skipRows"]["visibleWhen"]["any"][1]["in"] == ["csv", "zip"]
    assert props["latColumn"]["visibleWhen"]["any"][1]["in"] == ["csv", "xlsx", "zip"]
    assert props["lonColumn"]["visibleWhen"] == props["latColumn"]["visibleWhen"]


# ── Credential ────────────────────────────────────────────────────────────────

async def test_the_credential_goes_in_the_header(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=b"a,b\n1,2\n"))

    await _no(http_auth={"type": "http_bearer", "token": "segredo"}).execute({})

    assert rede.pedidos[0].headers["authorization"] == "Bearer segredo"


async def test_an_unresolved_credential_does_not_go_out_anonymous(rede):
    with pytest.raises(ValueError, match="não pôde ser resolvida"):
        await _no(credential_id="cred-1").execute({})
    assert rede.pedidos == []


# ── ZIP ───────────────────────────────────────────────────────────────────────

async def test_a_shapefile_in_a_subfolder(rede, tmp_path):
    entradas = [(f"dados/{n}", c) for n, c in _shapefile(tmp_path, "municipios", 2).items()]
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip(entradas)))

    saida = await _no(expectedFormat="zip").execute({})

    assert saida["output"]["nome"].tolist() == ["municipios0", "municipios1"]
    assert saida["output"].crs.to_epsg() == 4326  # reprojected from 4674, as always
    assert saida["metadata"]["zip_member"] == "dados/municipios.shp"


async def test_two_shapefiles_choose_by_pattern(rede, tmp_path):
    entradas = list(_shapefile(tmp_path, "municipios", 3).items()) + list(_shapefile(tmp_path, "estados", 2).items())
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip(entradas)))

    saida = await _no(expectedFormat="zip", zipMember="estados*").execute({})

    assert saida["output"]["nome"].tolist() == ["estados0", "estados1"]
    assert saida["metadata"]["zip_member"] == "estados.shp"


async def test_two_shapefiles_without_a_pattern_read_as_before_and_say_so(rede, tmp_path, caplog):
    entradas = list(_shapefile(tmp_path, "municipios", 3).items()) + list(_shapefile(tmp_path, "estados", 2).items())
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip(entradas)))

    with caplog.at_level("WARNING", logger="flow.nodes.datasource.data_input"):
        saida = await _no(expectedFormat="zip").execute({})

    assert len(saida["output"]) == 3
    assert "o ZIP tem 2 camadas" in caplog.text and "Arquivo dentro do ZIP" in caplog.text


async def test_an_excel_csv_inside_a_zip(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip([("capitais.csv", CSV_EXCEL)])))

    tabela = (await _no(expectedFormat="zip").execute({}))["output"]

    assert tabela["nome"].tolist() == ["São Paulo", "Manaus"]
    assert tabela["valor"].tolist() == [1500.5, 12.25]


async def test_inmet_station_from_a_zip_of_stations(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip([
        ("INMET_CO_DF_A001_BRASILIA.CSV", INMET), ("INMET_CO_GO_A002_GOIANIA.CSV", INMET),
    ])))

    saida = await _no(expectedFormat="zip", zipMember="*A001*", skipRows=8).execute({})

    assert list(saida["output"].columns)[:2] == ["Data", "Hora UTC"]
    assert saida["metadata"]["zip_member"] == "INMET_CO_DF_A001_BRASILIA.CSV"


def test_a_trailing_separator_adds_no_empty_column(tmp_path):
    caminho = tmp_path / "estacao.csv"
    caminho.write_bytes(b"Data;Chuva (mm);\n2024/01/01;0,2;\n2024/01/02;;\n")

    tabela = _load_file(str(caminho), "csv", "")

    assert list(tabela.columns) == ["Data", "Chuva (mm)"]
    assert tabela["Chuva (mm)"].tolist()[0] == 0.2


def test_a_headerless_column_with_data_stays(tmp_path):
    caminho = tmp_path / "tabela.csv"
    caminho.write_bytes(b"a,,c\n1,2,3\n")

    assert list(_load_file(str(caminho), "csv", "").columns) == ["a", "Unnamed: 1", "c"]


async def test_skip_rows_with_several_files_asks_which(rede):
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip([("a.csv", b"x\n"), ("b.csv", b"y\n")])))

    with pytest.raises(ValueError, match="Diga qual em 'Arquivo dentro do ZIP'"):
        await _no(expectedFormat="zip", skipRows=1).execute({})


async def test_two_shapefiles_in_a_subfolder_ask_which_first(rede, tmp_path):
    entradas = [(f"BR/{n}", c) for n, c in _shapefile(tmp_path, "municipios", 1).items()]
    entradas += [(f"BR/{n}", c) for n, c in _shapefile(tmp_path, "estados", 1).items()]
    rede.rota(f"{BASE}/arquivo", httpx.Response(200, content=_zip(entradas)))

    with pytest.raises(RuntimeError) as erro:
        await _no(expectedFormat="zip").execute({})
    mensagem = str(erro.value)
    assert mensagem.startswith("O ZIP tem 2 arquivos que o nó lê: BR/municipios.shp, BR/estados.shp.")
    assert "Lido como está, o ZIP deu erro no GDAL" in mensagem


# ── Drive: what existed keeps working ─────────────────────────────────────────

def test_a_drive_zip_with_one_shapefile_reads_as_before(tmp_path):
    caminho = tmp_path / "municipios.zip"
    caminho.write_bytes(_zip(_shapefile(tmp_path, "municipios", 2).items()))
    info = {}

    lido = _load_file(str(caminho), "zip", "", info=info)

    assert isinstance(lido, gpd.GeoDataFrame) and lido.crs.to_epsg() == 4674
    assert lido["nome"].tolist() == ["municipios0", "municipios1"]
    assert info == {}
    assert not caminho.exists()


def test_points_also_work_for_a_table_from_the_drive(tmp_path):
    from flow.nodes.datasource.data_input import _pontos_de_colunas

    tabela = pd.DataFrame({"y": [-10.0], "x": [-50.0]})
    gdf = _pontos_de_colunas(tabela, "y", "x", "EPSG:4674")

    assert gdf.crs.to_epsg() == 4674 and gdf.geometry.iloc[0] == Point(-50, -10)
