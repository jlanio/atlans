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

    Returns (node result, with the node's log lines under "_logs", arguments
    given to persistir_artefato, saved file).
    """
    node = SaveFileNode("n1", params)
    node._task_id = "task-1"
    node._workspace_id = "ws-1"
    logs: list = []
    node.log = logs.append
    recebido: dict = {}

    def _persistir(**kwargs):
        recebido.update(kwargs)
        destino = tmp_path / kwargs["filename"]
        destino.write_bytes(kwargs["fileobj"].read())
        return f"artifacts/ws-1/task-1/{kwargs['filename']}", {"filename": kwargs["filename"]}

    with patch("flow.nodes.outputs.save_file.persistir_artefato", side_effect=_persistir):
        resultado = await node.execute(inputs)
    resultado["_logs"] = logs
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


# ── Findings of the adversarial review ───────────────────────────────────────
# Each test below reproduces a case that broke the first version: data lost or
# changed in silence, a file that does not open, or the executor held too long.

def _kml_de(arquivo) -> str:
    if str(arquivo).endswith(".kmz"):
        with zipfile.ZipFile(arquivo) as kmz:
            return kmz.read("doc.kml").decode("utf-8")
    return arquivo.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_names_that_differ_only_in_case_keep_their_values(tmp_path):
    """The join of an IBGE layer (NM_MUN) with a Postgres table (nm_mun): the
    KML wrote nm_mun's values under NM_MUN, and the GeoPackage refused the layer."""
    camada = _obras()
    camada["NM_MUN"] = ["Porto Velho", "Ji-Paraná"]
    camada["nm_mun"] = ["PVH (sede)", "JPR (sede)"]

    resultado, _, kmz = await _salvar(tmp_path, {"label": "j", "formato": "kmz"}, {"in": camada})
    kml = _kml_de(kmz)
    assert '<SimpleData name="NM_MUN">Porto Velho</SimpleData>' in kml
    assert '<SimpleData name="nm_mun_1">PVH (sede)</SimpleData>' in kml
    assert any("'nm_mun' foi gravada como 'nm_mun_1'" in linha for linha in resultado["_logs"])

    _, _, gpkg = await _salvar(tmp_path, {"label": "j", "formato": "gpkg"}, {"in": camada})
    lido = pyogrio.read_dataframe(gpkg)
    assert lido["NM_MUN"].tolist() == ["Porto Velho", "Ji-Paraná"]
    assert lido["nm_mun_1"].tolist() == ["PVH (sede)", "JPR (sede)"]


def test_repeated_numbered_and_pivot_names_become_distinct_text():
    tabela = pd.concat([pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [2]})], axis=1)
    tabela[2024] = [3]
    tabela["2024"] = [4]
    avisos: list = []

    pronta = atributos_gravaveis(tabela, avisos)

    assert list(pronta.columns) == ["a", "a_1", "2024", "2024_1"]
    assert pronta.iloc[0].tolist() == [1, 2, 3, 4]
    assert len(avisos) == 2

    pivo = pd.DataFrame({("valor", "soma"): [1.5], ("valor", ""): [2.0]})
    assert list(atributos_gravaveis(pivo).columns) == ["valor_soma", "valor"]


def test_a_named_index_becomes_a_column():
    """The keys of a groupby live in the index, and every format dropped it."""
    resumo = pd.DataFrame({"municipio": ["PVH", "PVH", "JPR"], "obras": [1, 2, 3]})
    resumo = resumo.groupby("municipio").sum()

    pronta = atributos_gravaveis(resumo)

    assert pronta.to_dict("records") == [
        {"municipio": "JPR", "obras": 3}, {"municipio": "PVH", "obras": 3},
    ]


@pytest.mark.asyncio
async def test_excel_refuses_more_cells_than_the_executor_writes_in_time(tmp_path, monkeypatch):
    """pyogrio keeps the GIL while GDAL writes: a sheet at Excel's own limit
    froze the executor's loop past the 90 s after which the server drops it."""
    monkeypatch.setattr(save_file, "CELULAS_DO_EXCEL", 5)

    with pytest.raises(ValueError, match=r"A planilha teria 6 células \(2 linhas × 3 colunas\), acima das 5"):
        await _salvar(tmp_path, {"label": "t", "formato": "xlsx", "geometria": "wkt"}, {"in": _obras()})

    # The CSV, written by pandas, does not hold the loop: no such limit.
    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": _obras()})
    assert arquivo.exists()


def test_excel_column_limit_message():
    with pytest.raises(ValueError, match=r"teria 2\.001 colunas, e o Excel gravado aqui vai até 2\.000"):
        conferir_limites_do_excel(pd.DataFrame({f"c{i}": [1] for i in range(2001)}))


@pytest.mark.asyncio
async def test_kml_field_names_with_xml_characters_still_open(tmp_path):
    camada = _obras()
    camada['Obras & "Serviços"'] = ["a", "b"]

    resultado, _, arquivo = await _salvar(
        tmp_path, {"label": "k", "formato": "kml", "campoNome": 'Obras & "Serviços"'}, {"in": camada}
    )

    lido = pyogrio.read_dataframe(arquivo)  # not well-formed before
    assert "<name>a</name>" in arquivo.read_text(encoding="utf-8")  # the name field follows the rename
    assert len(lido) == 2
    assert any("foi gravada como 'Obras _ _Serviços_'" in linha for linha in resultado["_logs"])


@pytest.mark.asyncio
async def test_numbers_that_would_lose_digits_go_as_text(tmp_path):
    """An NF-e access key in a `numeric` came out as 3,52e+43."""
    tabela = pd.DataFrame({
        "chave_nfe": pd.Series([Decimal("35200114200166000187550010000000071000000003")], dtype=object),
        "processo": pd.Series([Decimal("70001234520238220001")], dtype=object),
        "taxa": pd.Series([Decimal("0.12345678901234567")], dtype=object),
        "valor": pd.Series([Decimal("1500.50")], dtype=object),
    })

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": tabela})

    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == [
        "chave_nfe;processo;taxa;valor",
        "35200114200166000187550010000000071000000003;70001234520238220001;0.12345678901234567;1500,5",
    ]


@pytest.mark.asyncio
async def test_excel_gets_integers_above_15_digits_as_text(tmp_path):
    """Excel keeps 15 significant digits: 1234567890123456789 would end in 800."""
    tabela = pd.DataFrame({"id": pd.array([1234567890123456789, None], dtype="Int64"), "n": [1, 2]})

    resultado, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "xlsx"}, {"in": tabela})

    lido = _ler_xlsx(arquivo)
    assert lido["id"].tolist() == ["1234567890123456789", None]
    assert lido["n"].tolist() == [1, 2]
    assert any("mais de 15 dígitos" in linha for linha in resultado["_logs"])


@pytest.mark.asyncio
async def test_csv_neutralizes_the_header_and_categorical_columns(tmp_path):
    tabela = pd.DataFrame({
        "=1+2": ["a"],
        "situacao": pd.Categorical(["=1+3"]),
        "fator": pd.Categorical([1.5]),
    })

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": tabela})

    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == ["'=1+2;situacao;fator", "a;'=1+3;1,5"]


@pytest.mark.asyncio
async def test_csv_leaves_plain_numbers_without_apostrophe(tmp_path):
    tabela = pd.DataFrame({"saldo": pd.Series([-3, "N/D", "+55", "-", "-1 days"], dtype=object)})

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": tabela})

    assert arquivo.read_text(encoding="utf-8-sig").splitlines()[1:] == ["-3", "N/D", "+55", "'-", "'-1 days"]


@pytest.mark.asyncio
async def test_excel_has_no_infinite_cell(tmp_path):
    """<v>inf</v> is not a number in the format: LibreOffice showed 0."""
    tabela = pd.DataFrame({"valor": [10.0, 5.0, 1.0], "area": [0.0, 2.0, -0.0]})
    tabela["razao"] = tabela.valor / tabela.area

    resultado, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "xlsx"}, {"in": tabela})

    with zipfile.ZipFile(arquivo) as xlsx:
        planilhas = "".join(xlsx.read(n).decode("utf-8") for n in xlsx.namelist() if n.startswith("xl/worksheets/"))
    assert "inf" not in planilhas
    razao = _ler_xlsx(arquivo)["razao"].tolist()
    assert pd.isna(razao[0]) and razao[1] == 2.5 and pd.isna(razao[2])
    assert any("2 valor(es) infinito(s) ficaram vazios" in linha for linha in resultado["_logs"])


@pytest.mark.asyncio
@pytest.mark.parametrize("formato", ["kml", "csv", "gpkg"])
async def test_a_layer_without_crs_in_utm_is_not_called_longitude_latitude(tmp_path, formato):
    """A UTM shapefile whose .prj got lost: KML at 40,9030000, CSV with longitude 400000."""
    sem_crs = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(400000, 9030000)])

    with pytest.raises(ValueError, match="não tem CRS, e as coordenadas .* não são longitude/latitude"):
        await _salvar(tmp_path, {"label": "u", "formato": formato}, {"in": sem_crs})


@pytest.mark.asyncio
async def test_a_layer_without_crs_can_be_told_its_crs(tmp_path):
    sem_crs = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(400000, 9030000)])

    _, _, arquivo = await _salvar(
        tmp_path, {"label": "u", "formato": "csv", "crs": "EPSG:31980"}, {"in": sem_crs}
    )

    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == ["id;x;y", "1;400000,0;9030000,0"]


@pytest.mark.asyncio
async def test_a_layer_without_crs_in_longitude_latitude_is_taken_as_wgs84(tmp_path):
    sem_crs = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(LON_A, LAT_A)])

    _, _, arquivo = await _salvar(tmp_path, {"label": "u", "formato": "gpkg"}, {"in": sem_crs})

    assert pyogrio.read_dataframe(arquivo).crs.to_epsg() == 4326


@pytest.mark.asyncio
async def test_dates_with_time_zone(tmp_path):
    """Excel has no zone: GDAL dropped it, and 02:30 UTC and 02:30 in Porto
    Velho came out as the same cell. The GeoPackage stores UTC (its spec)."""
    tabela = pd.DataFrame({
        "enviado_em": pd.to_datetime(["2024-03-11 02:30"]).tz_localize("UTC"),
        "aberto_em": pd.to_datetime(["2024-03-10 22:30"]).tz_localize("America/Porto_Velho"),
        "dia": pd.to_datetime(["2024-03-11"]),
    })

    resultado, _, xlsx = await _salvar(tmp_path, {"label": "t", "formato": "xlsx"}, {"in": tabela})
    lido = _ler_xlsx(xlsx)
    assert lido["enviado_em"].tolist() == ["2024-03-11 02:30:00+00:00"]
    assert lido["aberto_em"].tolist() == ["2024-03-10 22:30:00-04:00"]
    assert lido["dia"].tolist() == [pd.Timestamp("2024-03-11")]
    assert sum("fuso horário" in linha for linha in resultado["_logs"]) == 2

    _, _, gpkg = await _salvar(tmp_path, {"label": "t", "formato": "gpkg"}, {"in": tabela})
    lido = pyogrio.read_dataframe(gpkg)
    assert lido["aberto_em"].iloc[0] == pd.Timestamp("2024-03-11 02:30", tz="UTC")


@pytest.mark.asyncio
async def test_a_geodataframe_without_active_geometry_is_a_table(tmp_path):
    sem_geometria = gpd.GeoDataFrame({"municipio": ["Porto Velho"], "obras": [12]})

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv"}, {"in": sem_geometria})

    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == ["municipio;obras", "Porto Velho;12"]


@pytest.mark.asyncio
async def test_empty_geometries(tmp_path):
    """A point outside a polygon intersects as POINT EMPTY: the KML wrote
    nan,nan (read back as POINT (0 0)), and the coordinates refused an empty
    polygon among the points."""
    camada = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[Point(LON_A, LAT_A), Point(), box(0, 0, 1, 1).difference(box(0, 0, 1, 1))],
        crs="EPSG:4326",
    )

    _, _, kml = await _salvar(tmp_path, {"label": "t", "formato": "kml"}, {"in": camada})
    assert "nan" not in kml.read_text(encoding="utf-8")
    assert pyogrio.read_dataframe(kml).geometry.isna().tolist() == [False, True, True]

    _, _, csv = await _salvar(tmp_path, {"label": "t", "formato": "csv", "geometria": "xy"}, {"in": camada})
    assert csv.read_text(encoding="utf-8-sig").splitlines()[2:] == ["2;;", "3;;"]


@pytest.mark.asyncio
async def test_missing_values_are_not_written_as_text(tmp_path):
    camada = _obras()
    camada["obs"] = pd.Series(["a", pd.NA], dtype=object)
    camada["quando"] = pd.Series([pd.NaT, "b"], dtype=object)

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "gpkg"}, {"in": camada})

    lido = pyogrio.read_dataframe(arquivo)
    assert lido["obs"].tolist() == ["a", None]
    assert lido["quando"].tolist() == [None, "b"]


def test_a_second_geometry_comes_in_the_layers_crs_and_full_precision():
    camada = _obras("EPSG:31980")
    camada["original"] = camada.geometry
    camada = camada.to_crs("EPSG:4326")

    pronta = atributos_gravaveis(camada)

    assert pronta["original"].iloc[0] == f"POINT ({camada.geometry.iloc[0].x!r} {camada.geometry.iloc[0].y!r})"


@pytest.mark.asyncio
async def test_wkt_keeps_every_decimal_and_xy_keeps_z(tmp_path):
    preciso = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[box(-63.123456789, -8.1, -63.0, -8.0)], crs="EPSG:4326"
    )
    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv", "separador": ","}, {"in": preciso})
    assert "-63.123456789 " in arquivo.read_text(encoding="utf-8-sig")

    com_z = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(LON_A, LAT_A, 95.5)], crs="EPSG:4326")
    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "csv", "separador": ","}, {"in": com_z})
    assert arquivo.read_text(encoding="utf-8-sig").splitlines() == [
        "id,longitude,latitude,z", f"1,{LON_A},{LAT_A},95.5",
    ]


@pytest.mark.asyncio
async def test_kml_with_a_hyphen_in_the_name_writes_without_gdal_warning(tmp_path, capfd):
    _, _, arquivo = await _salvar(tmp_path, {"label": "Obras Guajará-Mirim", "formato": "kml"}, {"in": _obras()})

    assert "Warning" not in capfd.readouterr().err
    assert "<Folder><name>Obras_Guajara_Mirim</name>" in arquivo.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_a_postgres_boolean_with_null_stays_boolean(tmp_path):
    camada = _obras()
    camada["ativo"] = pd.Series([True, None], dtype=object)

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "gpkg"}, {"in": camada})

    assert dict(zip(*[pyogrio.read_info(arquivo)[k] for k in ("fields", "dtypes")]))["ativo"] == "bool"


@pytest.mark.asyncio
async def test_excel_message_for_long_text_outside_the_geometry(tmp_path):
    tabela = pd.DataFrame({"parecer": pd.Categorical(["x" * 40_000])})

    with pytest.raises(ValueError, match=r"coluna 'parecer' tem textos de 40\.000 .* Grave em CSV ou GeoPackage\.$"):
        await _salvar(tmp_path, {"label": "t", "formato": "xlsx"}, {"in": tabela})


@pytest.mark.asyncio
async def test_geometry_only_without_geometry_in_the_sheet(tmp_path):
    so_geometria = gpd.GeoDataFrame(geometry=[Point(LON_A, LAT_A)], crs="EPSG:4326")

    with pytest.raises(ValueError, match="Não há colunas para gravar"):
        await _salvar(tmp_path, {"label": "t", "formato": "csv", "geometria": "nenhuma"}, {"in": so_geometria})


@pytest.mark.asyncio
async def test_gpkg_layer_names_reserved_by_the_format(tmp_path):
    resultado, _, arquivo = await _salvar(tmp_path, {"label": "gpkgobras", "formato": "gpkg"}, {"in": _obras()})

    assert [nome for nome, _ in pyogrio.list_layers(arquivo)] == ["camada_gpkgobras"]
    assert any("camada_gpkgobras" in linha for linha in resultado["_logs"])


@pytest.mark.asyncio
@pytest.mark.parametrize("formato", ["gpkg", "xlsx", "csv", "kml"])
async def test_unusual_number_types_are_written(tmp_path, formato):
    import numpy as np

    camada = _obras()
    camada["grande"] = np.array([2**64 - 1, 1], dtype="uint64")
    camada["meia"] = np.array([1.5, 2.5], dtype="float16")
    camada["complexo"] = np.array([1 + 2j, 3j])

    _, recebido, arquivo = await _salvar(tmp_path, {"label": "t", "formato": formato}, {"in": camada})

    assert arquivo.stat().st_size > 0 and recebido["features"] == 2


def test_containers_become_valid_json_with_numbers():
    tabela = pd.DataFrame({"valores": pd.Series([[Decimal("1.5"), Decimal("2"), None, float("nan")], "x"], dtype=object)})

    pronta = atributos_gravaveis(tabela)

    assert pronta["valores"].tolist() == ["[1.5, 2, null, null]", "x"]


@pytest.mark.asyncio
async def test_a_nul_character_does_not_cut_the_text(tmp_path):
    camada = _obras()
    camada["obs"] = ["antes\x00depois", "ok"]

    _, _, arquivo = await _salvar(tmp_path, {"label": "t", "formato": "gpkg"}, {"in": camada})

    assert pyogrio.read_dataframe(arquivo)["obs"].tolist() == ["antesdepois", "ok"]


def test_importing_the_node_does_not_load_gdal():
    """The catalog is imported in every API worker (+27 MB each with GDAL), and
    loading GDAL before leitura_geo turned the VRT drivers back on."""
    import subprocess
    import sys
    from pathlib import Path

    codigo = "import sys, flow.nodes.outputs.save_file; print('pyogrio' in sys.modules)"
    saida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, check=True,
    )
    assert saida.stdout.strip() == "False"
