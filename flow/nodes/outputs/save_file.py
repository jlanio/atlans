"""
"Salvar arquivo": the layer, or a table, in the formats people open outside a
GIS — GeoPackage, KMZ/KML (Google Earth), Excel and CSV.

Everything is written with what the executor already ships: GDAL through
pyogrio (GeoPackage, KML, Excel) and pandas (CSV, for the decimal comma that
GDAL's CSV driver does not offer). The storage is the one of the other
"Salvar em…" nodes: a run artifact, the data locality (LGPD) and the optional
download credential.

Left out on purpose, tried with the bundled GDAL 3.12: GPX and File
Geodatabase refuse a layer with mixed geometry types, and DXF drops the
attributes.
"""
import asyncio
import json
import numbers
import os
import tempfile
import zipfile
from decimal import Decimal
from typing import Any, Dict, Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from geopandas.array import GeometryDtype

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import ensure_gdf_crs, slugify_label
from flow.utils.artifact_helpers import (
    EXECUTOR,
    describe_locality,
    locality_property,
    persistir_artefato,
    resolve_locality,
)
# format -> (extension, content type, needs a geometry)
FORMATOS: Dict[str, tuple[str, str, bool]] = {
    "gpkg": (".gpkg", "application/geopackage+sqlite3", False),
    "kmz": (".kmz", "application/vnd.google-earth.kmz", True),
    "kml": (".kml", "application/vnd.google-earth.kml+xml", True),
    "xlsx": (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", False),
    "csv": (".csv", "text/csv", False),
}

# KML only knows longitude/latitude in WGS 84 (OGC KML 2.2).
CRS_DO_KML = "EPSG:4326"

# Excel's own limits: rows per sheet (the header takes one) and characters per
# cell. Above the second, Excel cuts the text — a WKT cut in half is a broken
# geometry that nobody notices.
LINHAS_DO_EXCEL = 1_048_575
CARACTERES_POR_CELULA = 32_767

# A CSV cell starting with one of these is a formula for Excel and LibreOffice
# (OWASP, "CSV Injection"): an attribute that came from an external WFS would
# run when the auditor opens the file. Same rule as the users' CSV export
# (SEG-121). In .xlsx GDAL writes text as text, and the problem does not exist.
_INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")

_MENOR_INT64, _MAIOR_INT64 = -(2**63), 2**63 - 1


def _milhar(n: int) -> str:
    """1048575 -> '1.048.575'."""
    return f"{n:,}".replace(",", ".")


def _nome_livre(colunas: Iterable[Any], base: str) -> str:
    """`base`, or `base_1`, `base_2`... when one of `colunas` already has it.

    Compared without case: SQLite, under the GeoPackage, takes `FID` and `fid`
    as the same column.
    """
    usados = {str(c).lower() for c in colunas}
    nome, n = base, 1
    while nome.lower() in usados:
        nome = f"{base}_{n}"
        n += 1
    return nome


def _como_texto(valor: Any) -> Any:
    """A cell of a mixed column as text: containers as JSON, not Python repr,
    and bytes in hex, the way PostGIS shows a WKB."""
    if isinstance(valor, np.ndarray):
        valor = valor.tolist()
    if isinstance(valor, (dict, list, tuple, set)):
        conteudo = list(valor) if isinstance(valor, set) else valor
        return json.dumps(conteudo, ensure_ascii=False, default=str)
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return bytes(valor).hex()
    if pd.isna(valor):
        return None
    return str(valor)


def _como_numero(valores: pd.Series) -> pd.Series | None:
    """Decimal (Postgres `numeric`), maybe mixed with int and float, as numbers.

    When no Decimal has decimal places (`numeric(14,0)`, a CNPJ) the column
    stays integer: as float it would come out as 12345678000195.0. None when
    the column is not all numbers.
    """
    presentes = valores.dropna()
    if not all(
        isinstance(v, (Decimal, numbers.Real)) and not isinstance(v, (bool, np.bool_))
        for v in presentes
    ):
        return None
    inteiros = all(
        isinstance(v, numbers.Integral)
        or (isinstance(v, Decimal) and v.is_finite() and v.as_tuple().exponent >= 0)
        for v in presentes
    )
    if inteiros and all(_MENOR_INT64 <= int(v) <= _MAIOR_INT64 for v in presentes):
        return valores.map(lambda v: None if pd.isna(v) else int(v)).astype("Int64")
    return pd.to_numeric(valores.map(lambda v: float(v) if isinstance(v, Decimal) else v))


def atributos_gravaveis(df: pd.DataFrame) -> pd.DataFrame:
    """The columns the same way in every format.

    What GDAL writes each its own way, or refuses: a Postgres query brings
    `numeric` as Decimal, an API brings dicts and lists, a spreadsheet mixes 1
    and "a" in the same column, a pivot names columns with numbers, and a node
    that swaps the geometry can leave the old one behind as a second geometry
    column ("Multiple geometry columns are not supported"). Here numbers stay
    numbers, any other mixed column becomes text (containers as JSON), a second
    geometry becomes WKT and a duration becomes text.
    """
    df = df.rename(columns=lambda c: c if isinstance(c, str) else str(c))
    geometria = df.geometry.name if isinstance(df, gpd.GeoDataFrame) else None
    for coluna in df.columns:
        if coluna == geometria:
            continue
        serie = df[coluna]
        if isinstance(serie.dtype, GeometryDtype):
            df[coluna] = gpd.GeoSeries(serie).to_wkt()
        elif serie.dtype.kind == "m":
            df[coluna] = serie.map(_como_texto)
        elif serie.dtype == object:
            presentes = serie.dropna()
            if presentes.empty or all(isinstance(v, str) for v in presentes):
                continue
            numeros = _como_numero(serie)
            df[coluna] = numeros if numeros is not None else serie.map(_como_texto)
    return df


def geometria_em_colunas(df: pd.DataFrame, modo: str) -> pd.DataFrame:
    """The table of a spreadsheet: the geometry, if any, as columns.

    `auto`: points become two coordinate columns and any other geometry becomes
    WKT. The coordinate columns are longitude/latitude in a geographic CRS and
    x/y in a projected one.
    """
    if not isinstance(df, gpd.GeoDataFrame):
        return pd.DataFrame(df)
    geom = df.geometry
    tabela = pd.DataFrame(df.drop(columns=geom.name))
    if modo == "nenhuma":
        return tabela

    presentes = geom[~(geom.isna() | geom.is_empty)]
    so_pontos = not presentes.empty and bool((presentes.geom_type == "Point").all())
    if modo == "auto":
        modo = "xy" if so_pontos else "wkt"

    if modo == "xy":
        if not presentes.empty and not so_pontos:
            tipos = ", ".join(sorted(set(presentes.geom_type)))
            raise ValueError(
                f"A geometria 'xy' só vale para pontos, e a camada tem {tipos}. "
                "Use 'wkt', ou o nó Centróide antes, para gravar um ponto por feição."
            )
        geografico = df.crs is None or df.crs.is_geographic
        base_x, base_y = ("longitude", "latitude") if geografico else ("x", "y")
        tabela[_nome_livre(tabela.columns, base_x)] = geom.x
        tabela[_nome_livre(tabela.columns, base_y)] = geom.y
        return tabela

    tabela[_nome_livre(tabela.columns, "wkt")] = geom.to_wkt()
    return tabela


def conferir_limites_do_excel(tabela: pd.DataFrame) -> None:
    """Refuses what Excel would cut instead of letting it cut in silence."""
    if len(tabela) > LINHAS_DO_EXCEL:
        raise ValueError(
            f"O Excel comporta até {_milhar(LINHAS_DO_EXCEL)} linhas por planilha, e a "
            f"tabela tem {_milhar(len(tabela))}. Grave em CSV ou GeoPackage."
        )
    for coluna in tabela.select_dtypes(include=["object", "string"]).columns:
        tamanhos = tabela[coluna].dropna().map(lambda v: len(v) if isinstance(v, str) else 0)
        maior = int(tamanhos.max()) if not tamanhos.empty else 0
        if maior > CARACTERES_POR_CELULA:
            raise ValueError(
                f"A coluna '{coluna}' tem textos de {_milhar(maior)} caracteres, acima do "
                f"limite de {_milhar(CARACTERES_POR_CELULA)} por célula do Excel (é comum no "
                "WKT de polígonos grandes). Use a geometria 'xy' ou 'nenhuma', ou grave em "
                "GeoPackage."
            )


def sem_formulas(tabela: pd.DataFrame) -> pd.DataFrame:
    """Text that Excel would run as a formula gets an apostrophe in front (OWASP)."""
    tabela = tabela.copy()
    for coluna in tabela.select_dtypes(include=["object", "string"]).columns:
        tabela[coluna] = tabela[coluna].map(
            lambda v: "'" + v if isinstance(v, str) and v.startswith(_INICIO_DE_FORMULA) else v
        )
    return tabela


def _colunas_do_gpkg(dado: pd.DataFrame) -> Dict[str, str]:
    """Names for the two columns GDAL creates in a GeoPackage, the key (`fid`)
    and the geometry (`geom`), away from the attributes.

    An attribute with either name makes GDAL refuse the layer ("Error adding
    field 'fid'"), and a table made in QGIS or read from another GeoPackage
    brings `fid`. The attribute keeps its name and values; GDAL's column takes
    another name.
    """
    if not isinstance(dado, gpd.GeoDataFrame):
        return {"FID": _nome_livre(dado.columns, "fid")}
    atributos = [c for c in dado.columns if c != dado.geometry.name]
    return {"FID": _nome_livre(atributos, "fid"), "GEOMETRY_NAME": _nome_livre(atributos, "geom")}


def gravar(dado: pd.DataFrame, formato: str, pasta: str, nome: str, opcoes: Dict[str, Any]) -> str:
    """Writes `dado` into `pasta` and returns the file's path. Blocking."""
    extensao = FORMATOS[formato][0]
    caminho = os.path.join(pasta, f"{nome}{extensao}")

    if formato == "gpkg":
        pyogrio.write_dataframe(
            dado, caminho, layer=opcoes["camada"], driver="GPKG",
            layer_options=_colunas_do_gpkg(dado),
        )
        return caminho

    if formato in ("kml", "kmz"):
        campo = opcoes.get("campo_nome") or ""
        destino_kml = caminho if formato == "kml" else os.path.join(pasta, "doc.kml")
        # The layer is the folder Google Earth shows. The slug, because GDAL
        # turns anything but letters, digits, '_' and '.' into '_' (the name is
        # also an XML id) and warns about it on every run.
        pyogrio.write_dataframe(
            dado, destino_kml, layer=nome, driver="KML",
            dataset_options={"NameField": campo} if campo else None,
        )
        if formato == "kmz":
            # A KMZ is a zip whose main document is doc.kml (Google's KMZ spec).
            with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.write(destino_kml, "doc.kml")
        return caminho

    tabela = geometria_em_colunas(dado, opcoes["geometria"])
    if formato == "xlsx":
        conferir_limites_do_excel(tabela)
        pyogrio.write_dataframe(tabela, caminho, layer=opcoes["planilha"], driver="XLSX")
        return caminho

    # CSV: ';' goes with the decimal comma, which is how Excel in Portuguese
    # opens it with a double click; the BOM makes it read the accents as UTF-8.
    separador = opcoes["separador"]
    sem_formulas(tabela).to_csv(
        caminho, sep=separador, decimal="," if separador == ";" else ".",
        index=False, encoding="utf-8-sig",
    )
    return caminho


@register_node
class SaveFileNode(BaseNode):
    """Saves a layer or a table as GeoPackage, KMZ/KML, Excel or CSV."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "SaveFile",
            "alias": "Salvar arquivo",
            "description": (
                "Salva a camada (ou uma tabela) como GeoPackage, KMZ/KML para o Google "
                "Earth, Excel ou CSV, no armazenamento da plataforma ou apenas no disco do "
                "executor, conforme a localidade dos dados. Em Excel e CSV a geometria vira "
                "colunas: coordenadas para pontos, WKT para as demais."
            ),
            "type": "output",
            "dynamic_output": False,
            "outputs": [
                {"name": "artifact_filename", "type": "string", "description": "Nome do arquivo salvo"},
                {"name": "artifact_s3_key", "type": "string", "description": "Chave S3 do artefato no MinIO, ou o caminho local quando o conteúdo fica no executor"},
                {"name": "artifact_format", "type": "string", "description": "Formato: gpkg, kmz, kml, xlsx ou csv"},
                {"name": "features", "type": "number", "description": "Número de linhas gravadas"},
            ],
            "properties": [
                {
                    "name": "formato",
                    "label": "Formato",
                    "type": "select",
                    "default": "gpkg",
                    "description": "Formato do arquivo.",
                    "options": [
                        {"value": "gpkg", "label": "GeoPackage (.gpkg)"},
                        {"value": "kmz", "label": "Google Earth (.kmz)"},
                        {"value": "kml", "label": "KML (.kml)"},
                        {"value": "xlsx", "label": "Excel (.xlsx)"},
                        {"value": "csv", "label": "CSV (.csv)"},
                    ],
                },
                {
                    "name": "label",
                    "required": True,
                    "label": "Nome do arquivo",
                    "type": "string",
                    "default": "",
                    "description": "Nome do arquivo, sem extensão. Ex: 'obras_para_vistoria'.",
                },
                {
                    "name": "crs",
                    "label": "CRS de destino",
                    "type": "string",
                    "default": "EPSG:4326",
                    "description": (
                        "Reprojeta a camada antes de gravar; vazio mantém o CRS dela. No KML "
                        "e no KMZ é sempre EPSG:4326, exigência do formato."
                    ),
                    "visibleWhen": {"field": "formato", "in": ["gpkg", "xlsx", "csv"]},
                },
                {
                    "name": "camada",
                    "label": "Nome da camada",
                    "type": "string",
                    "default": "",
                    "description": "Nome da camada dentro do GeoPackage. Vazio = o nome do arquivo.",
                    "visibleWhen": {"field": "formato", "in": ["gpkg"]},
                },
                {
                    "name": "campoNome",
                    "label": "Campo do nome",
                    "type": "string",
                    "default": "",
                    "description": "Coluna mostrada como nome de cada marcador no Google Earth.",
                    "suggest_columns": "*",
                    "visibleWhen": {"field": "formato", "in": ["kmz", "kml"]},
                },
                {
                    "name": "geometria",
                    "label": "Geometria na planilha",
                    "type": "select",
                    "default": "auto",
                    "description": (
                        "Como a geometria vira colunas. Automático: pontos viram longitude/"
                        "latitude (x/y em CRS projetado) e as demais geometrias viram WKT."
                    ),
                    "options": [
                        {"value": "auto", "label": "Automático"},
                        {"value": "xy", "label": "Coordenadas (só pontos)"},
                        {"value": "wkt", "label": "WKT"},
                        {"value": "nenhuma", "label": "Sem geometria"},
                    ],
                    "visibleWhen": {"field": "formato", "in": ["xlsx", "csv"]},
                },
                {
                    "name": "separador",
                    "label": "Separador",
                    "type": "select",
                    "default": ";",
                    "description": (
                        "Ponto e vírgula grava números com vírgula decimal, como o Excel em "
                        "português abre direto; vírgula grava com ponto decimal."
                    ),
                    "options": [
                        {"value": ";", "label": "Ponto e vírgula (;)"},
                        {"value": ",", "label": "Vírgula (,)"},
                    ],
                    "visibleWhen": {"field": "formato", "in": ["csv"]},
                },
                {
                    "name": "credential_id",
                    "type": "credential",
                    "default": "",
                    "description": "Token Bearer para proteger o download. Sem credencial, o artefato é público.",
                    "credential_types": ["webhook_token"],
                    # There is no download to protect on an artifact that stays on the executor.
                    "visibleWhen": {"field": "localidade", "in": ["herdar"]},
                },
                locality_property(),
            ],
        }

    def _entrada(self, inputs: Dict[str, Any]) -> pd.DataFrame:
        """The layer (GeoDataFrame) or, when there is none, a table (DataFrame)."""
        if any(isinstance(v, gpd.GeoDataFrame) and not v.empty for v in inputs.values()):
            return self.get_first_gdf(inputs)
        tabelas = [
            k for k, v in inputs.items()
            if isinstance(v, pd.DataFrame) and not isinstance(v, gpd.GeoDataFrame) and not v.empty
        ]
        if tabelas:
            if len({id(inputs[k]) for k in tabelas}) > 1:
                self.log(
                    f"Mais de uma tabela chegou a este nó ({tabelas}); usando '{tabelas[0]}' "
                    "e ignorando as demais."
                )
            return inputs[tabelas[0]]
        recebido = {k: type(v).__name__ for k, v in inputs.items()}
        vazias = [k for k, v in inputs.items() if isinstance(v, pd.DataFrame) and v.empty]
        detalhe = f" Chegaram vazias: {vazias}." if vazias else ""
        raise ValueError(
            f"Nenhuma camada ou tabela com dados chegou ao nó. Recebido: {recebido}.{detalhe}"
        )

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        formato = self.get_param("formato", "gpkg")
        label = self.get_param("label", "").strip()
        if not label:
            raise ValueError("Informe o nome do arquivo (parâmetro 'label') no nó Salvar arquivo.")
        credential_id = self.get_param("credential_id", "") or None
        localidade, quem = resolve_locality(self.get_param("localidade", None))
        if localidade == EXECUTOR:
            # There is no download to protect on an artifact that stays on the executor.
            credential_id = None

        workspace_id, task_id = self.require_execution_context()
        extensao, content_type, exige_geometria = FORMATOS[formato]
        safe_label = slugify_label(label)

        dado = self._entrada(inputs)
        tem_geometria = isinstance(dado, gpd.GeoDataFrame)
        if exige_geometria and not tem_geometria:
            raise ValueError(
                f"O formato {formato.upper()} precisa de geometria, e chegou uma tabela. "
                "Para tabelas, use Excel, CSV ou GeoPackage."
            )

        if tem_geometria:
            destino = CRS_DO_KML if formato in ("kml", "kmz") else self.get_param("crs", "EPSG:4326").strip()
            dado = await asyncio.to_thread(ensure_gdf_crs, dado, destino)
        dado = await asyncio.to_thread(atributos_gravaveis, dado)

        campo_nome = self.get_param("campoNome", "").strip()
        if formato in ("kml", "kmz") and campo_nome and campo_nome not in dado.columns:
            colunas = [c for c in dado.columns if c != dado.geometry.name]
            raise ValueError(f"O campo '{campo_nome}' não existe na camada. Campos: {colunas}.")

        opcoes = {
            "camada": self.get_param("camada", "").strip() or safe_label,
            "campo_nome": campo_nome,
            "geometria": self.get_param("geometria", "auto"),
            "separador": self.get_param("separador", ";"),
            # Excel limits a sheet's name to 31 characters; the slug has no forbidden ones.
            "planilha": safe_label[:31],
        }
        features = len(dado)
        filename = f"{safe_label}{extensao}"

        with tempfile.TemporaryDirectory() as pasta:
            caminho = await asyncio.to_thread(gravar, dado, formato, pasta, safe_label, opcoes)
            with open(caminho, "rb") as arquivo:
                s3_key, artifact_meta = await asyncio.to_thread(
                    persistir_artefato,
                    localidade=localidade,
                    fileobj=arquivo,
                    filename=filename,
                    content_type=content_type,
                    workspace_id=workspace_id,
                    task_id=task_id,
                    label=label,
                    fmt=formato,
                    features=features,
                    credential_id=credential_id,
                )

        self.log(describe_locality(localidade, quem))
        onde = "neste executor" if localidade == EXECUTOR else "no MinIO"
        self.log(f"Arquivo salvo {onde}: {s3_key} ({formato}, {features} linhas)")

        return {
            "output": {
                "artifact_filename": filename,
                "artifact_s3_key": s3_key,
                "artifact_format": formato,
                "features": features,
            },
            "__artifact__": artifact_meta,
        }
