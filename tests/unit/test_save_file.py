"""
"Salvar arquivo" (SaveFile): each format written and read back.

What is checked is what the person opens on the other side: the columns and
rows, the CRS (KML is always WGS 84), the geometry turned into columns in a
spreadsheet, the CSV that Excel in Portuguese opens with a double click, and
the refusals that keep Excel from cutting data in silence.
"""
import re
import zipfile
from decimal import Decimal
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pyogrio
import pytest
from shapely.geometry import Point, box

from flow.nodes.outputs import save_file
from flow.nodes.outputs.save_file import (
    SaveFileNode,
    atributos_gravaveis,
    conferir_limites_do_excel,
)

# Two works in Porto Velho, in WGS 84.
LON_A, LAT_A = -63.9004, -8.7608
LON_B, LAT_B = -63.8312, -8.7421


@pytest.fixture(autouse=True)
def _maquina_sem_politica(monkeypatch):
    """The machine's locality policy comes from the environment; without this,
    a developer with GeoSync in "catalog" mode would see other results."""
    monkeypatch.delenv("EXECUTOR_SYNC_MODE", raising=False)


def _obras(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        {"nome": ["Escola Ji-Paraná", "Posto de saúde"], "valor": [1500.5, 20.25]},
        geometry=[Point(LON_A, LAT_A), Point(LON_B, LAT_B)],
        crs="EPSG:4326",
    )
    return gdf if crs == "EPSG:4326" else gdf.to_crs(crs)


def _lotes() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"lote": [1, 2]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:31980",
    )


async def _salvar(tmp_path, params: dict, inputs: dict):
    """Runs the node with the persistence replaced by a copy into `tmp_path`.

    Returns (node result, arguments given to persistir_artefato, saved file).
    """
    node = SaveFileNode("n1", params)
    node._task_id = "task-1"
    node._workspace_id = "ws-1"
    recebido: dict = {}

    def _persistir(**kwargs):
        recebido.update(kwargs)
        destino = tmp_path / kwargs["filename"]
        destino.write_bytes(kwargs["fileobj"].read())
        return f"artifacts/ws-1/task-1/{kwargs['filename']}", {"filename": kwargs["filename"]}

    with patch("flow.nodes.outputs.save_file.persistir_artefato", side_effect=_persistir):
        resultado = await node.execute(inputs)
    return resultado, recebido, tmp_path / recebido["filename"]


def _ler_xlsx(caminho) -> pd.DataFrame:
    # HEADERS=FORCE: GDAL only guesses the header when a data row has a number.
    return pyogrio.read_dataframe(caminho, HEADERS="FORCE")


# ── GeoPackage ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gpkg_comes_back_with_the_columns_rows_and_crs(tmp_path):
    resultado, recebido, arquivo = await _salvar(
        tmp_path, {"label": "Obras", "formato": "gpkg"}, {"in": _obras("EPSG:31980")}
    )

    lido = pyogrio.read_dataframe(arquivo)
    assert list(lido.columns) == ["nome", "valor", "geometry"]
    assert lido["nome"].tolist() == ["Escola Ji-Paraná", "Posto de saúde"]
    assert lido.crs.to_epsg() == 4326  # reprojected to the default destination
    assert lido.geometry.iloc[0].x == pytest.approx(LON_A)
    assert lido.geometry.iloc[0].y == pytest.approx(LAT_A)
    assert [nome for nome, _ in pyogrio.list_layers(arquivo)] == ["Obras"]

    assert recebido["filename"] == "Obras.gpkg"
    assert recebido["content_type"] == "application/geopackage+sqlite3"
    assert recebido["fmt"] == "gpkg"
    assert recebido["features"] == 2
    assert resultado["output"] == {
        "artifact_filename": "Obras.gpkg",
        "artifact_s3_key": "artifacts/ws-1/task-1/Obras.gpkg",
        "artifact_format": "gpkg",
        "features": 2,
    }
    assert resultado["__artifact__"] == {"filename": "Obras.gpkg"}


@pytest.mark.asyncio
async def test_gpkg_layer_name_and_crs_kept_when_empty(tmp_path):
    _, _, arquivo = await _salvar(
        tmp_path,
        {"label": "obras", "formato": "gpkg", "camada": "Obras 2024", "crs": ""},
        {"in": _obras("EPSG:31980")},
    )

    assert [nome for nome, _ in pyogrio.list_layers(arquivo)] == ["Obras 2024"]
    assert pyogrio.read_dataframe(arquivo).crs.to_epsg() == 31980


@pytest.mark.asyncio
async def test_gpkg_keeps_attributes_named_fid_and_geom(tmp_path):
    """GDAL refused both ("Error adding field 'fid'"): they are the names of
    its own key and geometry columns. A table made in QGIS brings `fid`."""
    camada = _obras()
    camada["fid"] = ["obra.1", "obra.1"]  # text and repeated: never a key
    camada["GEOM"] = ["texto", "outro"]

    _, _, arquivo = await _salvar(tmp_path, {"label": "obras"}, {"in": camada})

    lido = pyogrio.read_dataframe(arquivo)
    assert lido["fid"].tolist() == ["obra.1", "obra.1"]
    assert lido["GEOM"].tolist() == ["texto", "outro"]
    assert lido.geometry.iloc[1].x == pytest.approx(LON_B)


@pytest.mark.asyncio
async def test_gpkg_takes_a_table_without_geometry(tmp_path):
    tabela = pd.DataFrame({"municipio": ["Porto Velho", "Ariquemes"], "geom": ["a", "b"]})

    _, recebido, arquivo = await _salvar(tmp_path, {"label": "municipios"}, {"in": tabela})

    lido = pyogrio.read_dataframe(arquivo)
    assert pyogrio.read_info(arquivo)["geometry_type"] is None
    assert lido["municipio"].tolist() == ["Porto Velho", "Ariquemes"]
    assert lido["geom"].tolist() == ["a", "b"]
    assert recebido["features"] == 2


@pytest.mark.asyncio
async def test_gpkg_takes_a_second_geometry_column_as_wkt(tmp_path):
    """A node that swaps the geometry can leave the old one behind, and OGR
    writes a single geometry per layer."""
    camada = _lotes()
    camada["original"] = camada.geometry
    camada = camada.set_geometry(camada.centroid)

    _, _, arquivo = await _salvar(tmp_path, {"label": "lotes", "crs": ""}, {"in": camada})

    lido = pyogrio.read_dataframe(arquivo)
    assert lido["original"].iloc[0] == "POLYGON ((1 0, 1 1, 0 1, 0 0, 1 0))"
    assert lido.geom_type.tolist() == ["Point", "Point"]


# ── KMZ / KML ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kmz_is_a_zip_with_doc_kml_in_wgs84(tmp_path):
    _, recebido, arquivo = await _salvar(
        tmp_path, {"label": "obras", "formato": "kmz", "crs": "EPSG:31980"},
        {"in": _obras("EPSG:31980")},
    )

    with zipfile.ZipFile(arquivo) as kmz:
        assert kmz.namelist() == ["doc.kml"]
    lido = pyogrio.read_dataframe(f"/vsizip/{arquivo}/doc.kml")
    # The `crs` parameter does not apply: KML only knows longitude/latitude.
    assert lido.geometry.iloc[0].x == pytest.approx(LON_A, abs=1e-6)
    assert lido.geometry.iloc[0].y == pytest.approx(LAT_A, abs=1e-6)
    assert lido["nome"].tolist() == ["Escola Ji-Paraná", "Posto de saúde"]
    assert recebido["content_type"] == "application/vnd.google-earth.kmz"
    assert recebido["filename"] == "obras.kmz"


@pytest.mark.asyncio
async def test_kml_names_the_placemarks_with_the_chosen_field(tmp_path):
    _, recebido, arquivo = await _salvar(
        tmp_path, {"label": "Obras em vistoria", "formato": "kml", "campoNome": "nome"},
        {"in": _obras()},
    )

    texto = arquivo.read_text(encoding="utf-8")
    assert "<name>Escola Ji-Paraná</name>" in texto
    assert "<Folder><name>Obras_em_vistoria</name>" in texto  # the folder, as the file
    assert recebido["content_type"] == "application/vnd.google-earth.kml+xml"


@pytest.mark.asyncio
async def test_kml_refuses_a_table(tmp_path):
    with pytest.raises(ValueError, match="KML precisa de geometria"):
        await _salvar(tmp_path, {"label": "t", "formato": "kml"}, {"in": pd.DataFrame({"a": [1]})})


@pytest.mark.asyncio
async def test_kml_refuses_a_name_field_that_does_not_exist(tmp_path):
    with pytest.raises(ValueError, match=r"'Nome' não existe na camada\. Campos: \['nome', 'valor'\]"):
        await _salvar(
            tmp_path, {"label": "t", "formato": "kmz", "campoNome": "Nome"}, {"in": _obras()}
        )


# ── Excel ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_xlsx_points_become_longitude_and_latitude(tmp_path):
    _, recebido, arquivo = await _salvar(
        tmp_path, {"label": "obras", "formato": "xlsx"}, {"in": _obras()}
    )

    lido = _ler_xlsx(arquivo)
    assert list(lido.columns) == ["nome", "valor", "longitude", "latitude"]
    assert lido["longitude"].tolist() == pytest.approx([LON_A, LON_B])
    assert lido["latitude"].tolist() == pytest.approx([LAT_A, LAT_B])
    assert lido["valor"].tolist() == pytest.approx([1500.5, 20.25])
    assert recebido["content_type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@pytest.mark.asyncio
async def test_xlsx_projected_points_become_x_and_y(tmp_path):
    _, _, arquivo = await _salvar(
        tmp_path, {"label": "obras", "formato": "xlsx", "crs": "EPSG:31980"}, {"in": _obras()}
    )

    assert list(_ler_xlsx(arquivo).columns) == ["nome", "valor", "x", "y"]


@pytest.mark.asyncio
async def test_xlsx_polygons_become_wkt(tmp_path):
    _, _, arquivo = await _salvar(
        tmp_path, {"label": "lotes", "formato": "xlsx", "crs": ""}, {"in": _lotes()}
    )

    lido = _ler_xlsx(arquivo)
    assert list(lido.columns) == ["lote", "wkt"]
    assert lido["wkt"].iloc[0].startswith("POLYGON ((")


@pytest.mark.asyncio
async def test_xlsx_without_geometry_and_sheet_name_within_31_characters(tmp_path):
    rotulo = "levantamento_das_obras_paralisadas_2024"
    _, _, arquivo = await _salvar(
        tmp_path, {"label": rotulo, "formato": "xlsx", "geometria": "nenhuma"}, {"in": _obras()}
    )

    assert list(_ler_xlsx(arquivo).columns) == ["nome", "valor"]
    assert [nome for nome, _ in pyogrio.list_layers(arquivo)] == [rotulo[:31]]


@pytest.mark.asyncio
async def test_xy_refuses_polygons(tmp_path):
    with pytest.raises(ValueError, match="'xy' só vale para pontos, e a camada tem Polygon"):
        await _salvar(
            tmp_path, {"label": "lotes", "formato": "xlsx", "geometria": "xy"}, {"in": _lotes()}
        )


@pytest.mark.asyncio
async def test_xlsx_writes_a_formula_as_text(tmp_path):
    """Unlike the CSV, the spreadsheet needs no apostrophe: GDAL writes the
    cell as a string, never as a formula."""
    camada = _obras()
    camada["obs"] = ["=1+1", "ok"]

    _, _, arquivo = await _salvar(tmp_path, {"label": "obras", "formato": "xlsx"}, {"in": camada})

    with zipfile.ZipFile(arquivo) as xlsx:
        planilhas = [n for n in xlsx.namelist() if n.startswith("xl/worksheets/")]
        conteudo = "".join(xlsx.read(n).decode("utf-8") for n in xlsx.namelist() if n.endswith(".xml"))
        assert planilhas and all("<f>" not in xlsx.read(n).decode("utf-8") for n in planilhas)
    assert "=1+1" in conteudo
    assert _ler_xlsx(arquivo)["obs"].tolist() == ["=1+1", "ok"]


@pytest.mark.asyncio
async def test_xlsx_refuses_a_cell_above_excels_limit(tmp_path):
    """Excel cuts the text at 32,767 characters: a broken WKT nobody notices."""
    detalhado = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(0, 0).buffer(1, quad_segs=1000)], crs="EPSG:31980"
    )

    with pytest.raises(ValueError, match=r"coluna 'wkt' tem textos de .* acima do limite de 32\.767"):
        await _salvar(tmp_path, {"label": "t", "formato": "xlsx", "crs": ""}, {"in": detalhado})

    # The same layer fits in a CSV, which has no such limit.
    _, _, arquivo = await _salvar(
        tmp_path, {"label": "t", "formato": "csv", "crs": ""}, {"in": detalhado}
    )
    assert arquivo.stat().st_size > save_file.CARACTERES_POR_CELULA


def test_excel_row_limit_message(monkeypatch):
    tabela = pd.DataFrame({"a": range(3)})
    monkeypatch.setattr(save_file, "LINHAS_DO_EXCEL", 2)

    with pytest.raises(ValueError) as erro:
        conferir_limites_do_excel(tabela)
    assert str(erro.value) == (
        "O Excel comporta até 2 linhas por planilha, e a tabela tem 3. "
        "Grave em CSV ou GeoPackage."
    )


def test_thousands_use_a_dot():
    assert save_file._milhar(1_048_575) == "1.048.575"


# ── CSV ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_csv_opens_in_portuguese_excel(tmp_path):
    """';' with the decimal comma, and the BOM so Excel reads UTF-8 accents."""
    _, recebido, arquivo = await _salvar(tmp_path, {"label": "obras", "formato": "csv"}, {"in": _obras()})

    bruto = arquivo.read_bytes()
    assert bruto.startswith(b"\xef\xbb\xbf")
    linhas = bruto.decode("utf-8-sig").splitlines()
    assert linhas[0] == "nome;valor;longitude;latitude"
    assert linhas[1] == f"Escola Ji-Paraná;1500,5;{str(LON_A).replace('.', ',')};{str(LAT_A).replace('.', ',')}"
    assert recebido["content_type"] == "text/csv"
    assert recebido["filename"] == "obras.csv"


@pytest.mark.asyncio
async def test_csv_with_comma_uses_a_decimal_point(tmp_path):
    _, _, arquivo = await _salvar(
        tmp_path, {"label": "obras", "formato": "csv", "separador": ","}, {"in": _obras()}
    )

    linhas = arquivo.read_text(encoding="utf-8-sig").splitlines()
    assert linhas[0] == "nome,valor,longitude,latitude"
    assert linhas[1] == f"Escola Ji-Paraná,1500.5,{LON_A},{LAT_A}"


@pytest.mark.asyncio
async def test_csv_neutralizes_formulas_but_not_negative_numbers(tmp_path):
    tabela = pd.DataFrame({
        "texto": ['=HYPERLINK("http://x")', "+55 69", "-", "@SOMA(A1)", "\tx", "normal"],
        "saldo": [-3.5, 1.0, 2.0, 3.0, 4.0, 5.0],
    })

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": tabela})

    lido = pd.read_csv(arquivo, sep=";", decimal=",", encoding="utf-8-sig", keep_default_na=False)
    assert lido["texto"].tolist() == [
        "'=HYPERLINK(\"http://x\")", "'+55 69", "'-", "'@SOMA(A1)", "'\tx", "normal",
    ]
    assert lido["saldo"].tolist() == [-3.5, 1.0, 2.0, 3.0, 4.0, 5.0]


@pytest.mark.asyncio
async def test_csv_polygons_go_as_wkt(tmp_path):
    _, _, arquivo = await _salvar(
        tmp_path, {"label": "lotes", "formato": "csv", "crs": ""}, {"in": _lotes()}
    )

    lido = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")
    assert list(lido.columns) == ["lote", "wkt"]
    assert lido["wkt"].iloc[1] == "POLYGON ((2 0, 2 1, 1 1, 1 0, 2 0))"


# ── Columns written the same way in every format ─────────────────────────────

def test_numbers_stay_numbers_and_the_rest_becomes_text():
    tabela = pd.DataFrame({
        "valor": pd.Series([Decimal("10.50"), None, Decimal("3")], dtype=object),
        "cnpj": pd.Series([Decimal("12345678000195"), Decimal("4"), None], dtype=object),
        "misto": pd.Series([1, "a", None], dtype=object),
        "dados": pd.Series([{"bairro": "Centro"}, [1, 2], b"\x01\xff"], dtype=object),
        "prazo": pd.to_timedelta(["1 day", None, "2 hours"]),
        2024: [1, 2, 3],
    })

    pronta = atributos_gravaveis(tabela)

    assert pronta["valor"].dtype == "float64"
    assert pronta["valor"].iloc[0] == 10.5
    # A numeric(14,0): as float it would be written 12345678000195.0.
    assert str(pronta["cnpj"].dtype) == "Int64"
    assert pronta["cnpj"].iloc[0] == 12345678000195
    assert pronta["misto"].tolist() == ["1", "a", None]
    assert pronta["dados"].tolist() == ['{"bairro": "Centro"}', "[1, 2]", "01ff"]
    assert pronta["prazo"].tolist() == ["1 days 00:00:00", None, "0 days 02:00:00"]
    assert "2024" in pronta.columns
    # The input is not changed.
    assert tabela["valor"].iloc[0] == Decimal("10.50")


@pytest.mark.asyncio
@pytest.mark.parametrize("formato", ["gpkg", "kmz", "xlsx", "csv"])
async def test_every_format_takes_decimal_and_numbered_columns(tmp_path, formato):
    camada = _obras()
    camada["valor"] = pd.Series([Decimal("1500.50"), Decimal("20.25")], dtype=object)
    camada[2024] = [1, 2]

    _, recebido, arquivo = await _salvar(tmp_path, {"label": "obras", "formato": formato}, {"in": camada})

    assert arquivo.stat().st_size > 0
    assert recebido["features"] == 2


@pytest.mark.asyncio
async def test_a_cnpj_in_the_csv_has_no_decimal_part(tmp_path):
    tabela = pd.DataFrame({"cnpj": pd.Series([Decimal("12345678000195")], dtype=object)})

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": tabela})

    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == ["cnpj", "12345678000195"]


# ── Input, parameters and storage ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_table_goes_to_spreadsheet_formats(tmp_path):
    tabela = pd.DataFrame({"municipio": ["Porto Velho"], "obras": [12]})

    _, _, arquivo = await _salvar(tmp_path, {"label": "resumo", "formato": "xlsx"}, {"in": tabela})

    assert _ler_xlsx(arquivo).to_dict("records") == [{"municipio": "Porto Velho", "obras": 12}]


@pytest.mark.asyncio
async def test_the_layer_wins_over_a_table(tmp_path):
    _, recebido, _ = await _salvar(
        tmp_path, {"label": "obras", "formato": "kml"},
        {"tabela": pd.DataFrame({"a": [1, 2, 3]}), "camada": _obras()},
    )

    assert recebido["features"] == 2


@pytest.mark.asyncio
async def test_nothing_to_save_says_what_arrived(tmp_path):
    with pytest.raises(ValueError, match=r"Nenhuma camada ou tabela com dados.*Chegaram vazias: \['in'\]"):
        await _salvar(tmp_path, {"label": "t"}, {"in": _obras().iloc[0:0], "msg": "ok"})


@pytest.mark.asyncio
async def test_the_file_name_is_required(tmp_path):
    with pytest.raises(ValueError, match="Informe o nome do arquivo"):
        await _salvar(tmp_path, {"label": "  "}, {"in": _obras()})


@pytest.mark.asyncio
async def test_the_file_name_fits_the_s3_key(tmp_path):
    """Accents and spaces would make the server refuse the upload (400)."""
    _, recebido, _ = await _salvar(
        tmp_path, {"label": "Obras – Ji-Paraná 2024", "formato": "csv"}, {"in": _obras()}
    )

    assert re.fullmatch(r"[A-Za-z0-9_.-]+\.csv", recebido["filename"])
    assert recebido["label"] == "Obras – Ji-Paraná 2024"


@pytest.mark.asyncio
async def test_format_is_validated_and_canonicalized(tmp_path):
    _, recebido, _ = await _salvar(tmp_path, {"label": "t", "formato": "XLSX"}, {"in": _obras()})
    assert recebido["fmt"] == "xlsx"

    with pytest.raises(ValueError, match="deve ser um dos valores"):
        await _salvar(tmp_path, {"label": "t", "formato": "pdf"}, {"in": _obras()})


@pytest.mark.asyncio
async def test_credential_protects_the_download(tmp_path):
    _, recebido, _ = await _salvar(
        tmp_path, {"label": "t", "credential_id": "cred-1"}, {"in": _obras()}
    )

    assert recebido["localidade"] == "servidor"
    assert recebido["credential_id"] == "cred-1"


@pytest.mark.asyncio
async def test_kept_on_the_executor_without_credential(tmp_path):
    """There is no download to protect on an artifact that stays on the executor."""
    _, recebido, _ = await _salvar(
        tmp_path, {"label": "t", "credential_id": "cred-1", "localidade": "executor"},
        {"in": _obras()},
    )

    assert recebido["localidade"] == "executor"
    assert recebido["credential_id"] is None


@pytest.mark.asyncio
async def test_the_machines_policy_keeps_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")

    _, recebido, _ = await _salvar(tmp_path, {"label": "t"}, {"in": _obras()})

    assert recebido["localidade"] == "executor"


def test_registered_with_the_declared_outputs():
    from flow.nodes.contrato import validate_description
    from flow.registry import NODE_REGISTRY

    desc = SaveFileNode.description()
    validate_description(desc)
    assert NODE_REGISTRY["SaveFile"] is SaveFileNode
    assert [o["name"] for o in desc["outputs"]] == [
        "artifact_filename", "artifact_s3_key", "artifact_format", "features",
    ]
    assert [o["value"] for o in desc["properties"][0]["options"]] == list(save_file.FORMATOS)
