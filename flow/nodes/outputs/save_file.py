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
import datetime
import json
import math
import numbers
import os
import re
import tempfile
import zipfile
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from geopandas.array import GeometryDtype
from pandas.api.types import infer_dtype
from pyproj import CRS

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
# geometry that nobody notices. GDAL's XLSX writer stops at 2,000 columns.
LINHAS_DO_EXCEL = 1_048_575
COLUNAS_DO_EXCEL = 2_000
CARACTERES_POR_CELULA = 32_767

# pyogrio keeps the GIL while GDAL writes, so even inside asyncio.to_thread the
# executor's event loop (heartbeat, cancel, the other jobs' events) stands
# still for the whole write. The XLSX writer is the slow one, about 3.5 µs per
# cell: 2 million cells froze the loop for 6 s, and a sheet at Excel's limit
# would go past the 90 s after which the server drops the executor. This budget
# keeps the freeze around 20 s.
CELULAS_DO_EXCEL = 5_000_000

# The same for the KML writer, which costs about 3.3 µs per vertex and 2.2 µs
# per attribute value (30 thousand 65-vertex polygons froze the loop for 6 s):
# a state's rural properties (CAR) would go past the 90 s. Around 20 s here,
# and a KML that big is already slow to open in Google Earth.
ELEMENTOS_DO_KML = 6_000_000

# Longitude/latitude, with room for rounding; longitudes up to 360 are the
# 0–360 convention of some datasets. A UTM coordinate goes far past both.
_LONGITUDES, _LATITUDES = (-180.000001, 360.000001), (-90.000001, 90.000001)

# Excel keeps 15 significant digits: a longer number (an NF-e access key, a
# process number) loses its last digits, so it goes as text.
DIGITOS_DO_EXCEL = 15

# A CSV cell starting with one of these is a formula for Excel and LibreOffice
# (OWASP, "CSV Injection"): an attribute that came from an external WFS would
# run when the auditor opens the file. Same rule as the users' CSV export
# (SEG-121). In .xlsx GDAL writes text as text, and the problem does not exist.
_INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")
# "-3" or "+55" is a number for Excel, not a formula: it needs no apostrophe.
_NUMERO_SIMPLES = re.compile(r"[+-]?\d+(?:[.,]\d+)?")

# The KML driver writes the field names into XML attributes without escaping:
# one of these makes the file unreadable ("not well-formed"), Google Earth too.
_FORA_DO_XML = re.compile(r'[&<>"]')

_MENOR_INT64, _MAIOR_INT64 = -(2**63), 2**63 - 1


def _milhar(n: int) -> str:
    """1048575 -> '1.048.575'."""
    return f"{n:,}".replace(",", ".")


def _nome_livre(colunas: Iterable[Any], base: str) -> str:
    """`base`, or `base_1`, `base_2`... when one of `colunas` already has it.

    Compared without case, as GDAL compares field names (and SQLite, under the
    GeoPackage, takes `FID` and `fid` as the same column).
    """
    usados = {str(c).lower() for c in colunas}
    nome, n = base, 1
    while nome.lower() in usados:
        nome = f"{base}_{n}"
        n += 1
    return nome


def _para_json(valor: Any) -> Any:
    """A container ready for json.dumps: numbers as numbers (not "1.5") and NaN
    as null — json.dumps writes NaN, which is not JSON."""
    if isinstance(valor, dict):
        return {str(k): _para_json(v) for k, v in valor.items()}
    if isinstance(valor, np.ndarray):
        valor = valor.tolist()
    if isinstance(valor, set):
        # Sorted: a set's order changes from one process to another
        # (PYTHONHASHSEED), and the same data would come out as another file.
        itens = [_para_json(v) for v in valor]
        return sorted(itens, key=lambda v: json.dumps(v, sort_keys=True, default=str))
    if isinstance(valor, (list, tuple)):
        return [_para_json(v) for v in valor]
    if isinstance(valor, np.generic):
        valor = valor.item()
    if valor is None or valor is pd.NA or valor is pd.NaT:
        return None
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            return None
        if valor.as_tuple().exponent >= 0:
            return int(valor)
        return float(valor) if len(valor.as_tuple().digits) <= DIGITOS_DO_EXCEL else str(valor)
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    return valor


def _como_texto(valor: Any) -> Any:
    """A cell of a mixed column as text: containers as JSON, not Python repr,
    bytes in hex (the way PostGIS shows a WKB), and no NUL, where GDAL would
    cut the text."""
    if isinstance(valor, (dict, list, tuple, set, np.ndarray)):
        return json.dumps(_para_json(valor), ensure_ascii=False, default=str)
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return bytes(valor).hex()
    if pd.isna(valor):
        return None
    return str(valor).replace("\x00", "")


def _como_numero(valores: pd.Series) -> Optional[pd.Series]:
    """Decimal (Postgres `numeric`), maybe mixed with int and float, as numbers.

    When no Decimal has decimal places (`numeric(14,0)`, a CNPJ) the column
    stays integer: as float it would come out as 12345678000195.0. None when
    the column is not all numbers, or when a number would lose digits — an
    integer beyond int64 (an NF-e access key) or a Decimal with more than 15
    significant digits: those go as text, with every digit.
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
    if inteiros:
        if all(_MENOR_INT64 <= int(v) <= _MAIOR_INT64 for v in presentes):
            return valores.map(lambda v: None if pd.isna(v) else int(v)).astype("Int64")
        return None
    if any(
        isinstance(v, Decimal) and v.is_finite() and len(v.as_tuple().digits) > DIGITOS_DO_EXCEL
        for v in presentes
    ):
        return None
    return pd.to_numeric(valores.map(lambda v: None if pd.isna(v) else float(v)))


def _coluna_gravavel(serie: pd.Series, crs: Any) -> pd.Series:
    """One column the way every format takes it (see `atributos_gravaveis`)."""
    if isinstance(serie.dtype, GeometryDtype):
        # A second geometry: WKT, in the layer's CRS, with every decimal.
        geometrias = gpd.GeoSeries(serie)
        if crs is not None and geometrias.crs is not None and geometrias.crs != crs:
            geometrias = geometrias.to_crs(crs)
        return geometrias.to_wkt(rounding_precision=-1)
    if isinstance(serie.dtype, pd.CategoricalDtype):
        # Its values, so the decimal comma, the Excel limits and the formula
        # escaping see them.
        serie = serie.astype(object)
    if serie.dtype.kind in "mc":
        # Durations and complex numbers: GDAL takes neither.
        return serie.map(_como_texto)
    if serie.dtype == np.float16:
        return serie.astype("float32")
    if serie.dtype.kind == "u":
        maior = serie.max()
        if not pd.isna(maior) and int(maior) > _MAIOR_INT64:
            return serie.astype(object).map(_como_texto)
    if isinstance(serie.dtype, pd.StringDtype):
        return _sem_nul(serie)
    if serie.dtype != object:
        return serie

    # pd.NA and NaT went out as the texts "<NA>" and "NaT".
    serie = serie.where(serie.notna(), None)
    # One pass in C says what the column holds; the per-value work below only
    # runs for the kind that needs it.
    tipo = infer_dtype(serie, skipna=True)
    if tipo == "empty":
        return serie
    if tipo == "string":
        return _sem_nul(serie)
    if tipo == "boolean":
        # A Postgres boolean with NULL comes as an object column: without this
        # it became the text "True", while the same column without NULL is a boolean.
        return serie.astype("boolean")
    if tipo == "date" and all(type(v) is datetime.date for v in serie.dropna()):
        # A Postgres `date` comes as datetime.date objects, and was written as
        # text: no date filter or sort in QGIS and Excel. In seconds, because
        # 9999-12-31, the "no end date" of many public databases, does not fit
        # in nanoseconds.
        return serie.astype("datetime64[s]")
    numeros = _como_numero(serie)
    return numeros if numeros is not None else serie.map(_como_texto)


def _sem_nul(serie: pd.Series) -> pd.Series:
    """Text without NUL: GDAL cuts the text there, and the CSV carried the byte."""
    if serie.map(lambda v: isinstance(v, str) and "\x00" in v).any():
        # What is not text here is a missing value: None, not the pd.NA of a
        # `string` column, which GDAL writes as the text "<NA>".
        return serie.map(lambda v: v.replace("\x00", "") if isinstance(v, str) else None)
    return serie


def _nomes_unicos(df: pd.DataFrame, avisos: List[str], renomeadas: Dict[str, str]) -> List[Any]:
    """The column names as distinct text, compared without case.

    GDAL compares field names without case: `NM_MUN` and `nm_mun` (the join of
    an IBGE layer with a Postgres table) made the GeoPackage refuse the layer,
    and the KML wrote the second column's values under the first one's name, in
    silence. A pivot's columns (tuples) are joined with '_'. A repeated name
    takes a suffix that no other column has (for `a`, `A`, `a_1` the `A`
    becomes `A_2`, and `a_1` stays), the log says so, and `renomeadas` keeps
    the change for whoever chose a column by its old name.
    """
    geometria = df.active_geometry_name if isinstance(df, gpd.GeoDataFrame) else None
    originais = [
        coluna if geometria is not None and coluna == geometria
        else "_".join(str(p) for p in coluna if str(p) != "") if isinstance(coluna, tuple)
        else str(coluna)
        for coluna in df.columns
    ]
    reservados = {str(nome).lower() for nome in originais}
    nomes: List[Any] = []
    usados: set = set()
    for coluna, nome in zip(df.columns, originais):
        if geometria is not None and coluna == geometria:
            nomes.append(coluna)
            continue
        if nome.lower() in usados:
            novo = _nome_livre(usados | reservados, nome)
            avisos.append(
                f"A coluna '{nome}' foi gravada como '{novo}': outra coluna já tem esse "
                "nome, sem contar maiúsculas e minúsculas."
            )
            renomeadas.setdefault(nome, novo)
            nome = novo
        usados.add(nome.lower())
        nomes.append(nome)
    return nomes


def atributos_gravaveis(
    df: pd.DataFrame, avisos: Optional[List[str]] = None,
    renomeadas: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """The columns the same way in every format. Never changes `df`.

    What GDAL writes each its own way, or refuses: a Postgres query brings
    `numeric` as Decimal, `date` as datetime.date and booleans with NULL as
    objects, an API brings dicts
    and lists, a spreadsheet mixes 1 and "a" in the same column, a pivot names
    columns with numbers or tuples, a join brings two names that differ only in
    case, a groupby keeps the keys in the index, and a node that swaps the
    geometry can leave the old one behind as a second geometry column
    ("Multiple geometry columns are not supported"). Here numbers stay numbers
    (as text when they would lose digits), any other mixed column becomes text
    (containers as JSON), a second geometry becomes WKT, the names become
    distinct text and a named index becomes columns. What changes a name goes
    into `avisos`, and into `renomeadas` (old name -> new one).
    """
    avisos = [] if avisos is None else avisos
    renomeadas = {} if renomeadas is None else renomeadas
    if any(nome is not None for nome in df.index.names):
        # A named index is data (the keys of a groupby): every format dropped it.
        nomes_do_indice: List[str] = []
        for i, nome in enumerate(df.index.names):
            base = str(nome) if nome is not None else f"indice_{i}"
            nomes_do_indice.append(_nome_livre(list(df.columns) + nomes_do_indice, base))
        df = df.reset_index(names=nomes_do_indice)
    else:
        df = df.copy()
    df.columns = _nomes_unicos(df, avisos, renomeadas)

    geometria = df.active_geometry_name if isinstance(df, gpd.GeoDataFrame) else None
    crs = df.crs if geometria is not None else None
    for coluna in df.columns:
        if coluna != geometria:
            df[coluna] = _coluna_gravavel(df[coluna], crs)
    return df


def no_crs_de_destino(gdf: gpd.GeoDataFrame, destino: str, formato: str) -> gpd.GeoDataFrame:
    """`ensure_gdf_crs`, refusing to call longitude/latitude what is not.

    A UTM shapefile whose .prj got lost passes for longitude/latitude in two
    ways: without a CRS, `ensure_gdf_crs` takes the destination one (EPSG:4326
    by default); or the reader already stamped its own default on it (Entrada
    de Dados: EPSG:4326). Either way that wrote a KML at 40,9030000 (GDAL only
    complained on stderr) and a CSV with longitude 400000.
    """
    if gdf.crs is not None:
        geografico = gdf.crs.is_geographic
    else:
        geografico = bool(destino) and CRS.from_user_input(destino).is_geographic
    if not geografico:
        return ensure_gdf_crs(gdf, destino)

    minx, miny, maxx, maxy = gdf.total_bounds
    dentro = np.isnan(minx) or (
        _LONGITUDES[0] <= minx and maxx <= _LONGITUDES[1]
        and _LATITUDES[0] <= miny and maxy <= _LATITUDES[1]
    )
    if dentro:
        return ensure_gdf_crs(gdf, destino)

    coordenadas = f"(x de {minx:.0f} a {maxx:.0f}, y de {miny:.0f} a {maxy:.0f})"
    if gdf.crs is not None:
        raise ValueError(
            f"A camada está marcada como {gdf.crs.to_string()}, longitude/latitude, mas as "
            f"coordenadas {coordenadas} não são: o CRS dela está errado, como num "
            "shapefile sem o .prj lido com o CRS padrão. Informe o CRS certo no nó que lê "
            "a camada (campo CRS)."
        )
    if formato in ("kml", "kmz"):
        dica = (
            "O KML precisa saber o CRS de origem para converter: informe-o no nó que lê "
            "a camada (campo CRS)."
        )
    else:
        dica = (
            "Informe no campo 'CRS de destino' o CRS em que ela está (ex.: EPSG:31980) "
            "para gravar sem reprojetar."
        )
    raise ValueError(
        f"A camada não tem CRS, e as coordenadas {coordenadas} não são "
        f"longitude/latitude. {dica}"
    )


def geometria_em_colunas(df: pd.DataFrame, modo: str) -> tuple[pd.DataFrame, Optional[str]]:
    """The table of a spreadsheet: the geometry, if any, as columns.

    `auto`: points become two coordinate columns (three with Z) and any other
    geometry becomes WKT. The coordinate columns are longitude/latitude in a
    geographic CRS and x/y in a projected or unknown one. Returns the table
    and the name of the WKT column, when there is one.
    """
    if not isinstance(df, gpd.GeoDataFrame):
        return df.copy(), None
    geom = df.geometry
    tabela = pd.DataFrame(df.drop(columns=geom.name))
    if modo == "nenhuma":
        return tabela, None

    vazias = geom.isna() | geom.is_empty
    presentes = geom[~vazias]
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
        # An empty geometry of another type (POLYGON EMPTY among the points)
        # has no x either.
        pontos = geom.where(~vazias, None)
        geografico = df.crs is not None and df.crs.is_geographic
        base_x, base_y = ("longitude", "latitude") if geografico else ("x", "y")
        tabela[_nome_livre(tabela.columns, base_x)] = pontos.x
        tabela[_nome_livre(tabela.columns, base_y)] = pontos.y
        if bool(presentes.has_z.any()):
            tabela[_nome_livre(tabela.columns, "z")] = pontos.z
        return tabela, None

    nome_wkt = _nome_livre(tabela.columns, "wkt")
    tabela[nome_wkt] = geom.to_wkt(rounding_precision=-1)
    return tabela, nome_wkt


def conferir_limites_do_excel(tabela: pd.DataFrame, coluna_wkt: Optional[str] = None) -> None:
    """Refuses what Excel would cut, or what would hold the executor too long,
    instead of letting it happen in silence."""
    linhas, colunas = tabela.shape
    if linhas > LINHAS_DO_EXCEL:
        raise ValueError(
            f"O Excel comporta até {_milhar(LINHAS_DO_EXCEL)} linhas por planilha, e a "
            f"tabela tem {_milhar(linhas)}. Grave em CSV ou GeoPackage."
        )
    if colunas > COLUNAS_DO_EXCEL:
        raise ValueError(
            f"A planilha teria {_milhar(colunas)} colunas, e o Excel gravado aqui vai até "
            f"{_milhar(COLUNAS_DO_EXCEL)}. Grave em CSV ou GeoPackage."
        )
    if linhas * colunas > CELULAS_DO_EXCEL:
        raise ValueError(
            f"A planilha teria {_milhar(linhas * colunas)} células ({_milhar(linhas)} linhas "
            f"× {_milhar(colunas)} colunas), acima das {_milhar(CELULAS_DO_EXCEL)} que o "
            "executor grava em Excel sem ficar parado tempo demais. Grave em CSV ou "
            "GeoPackage, ou leve menos colunas."
        )
    for coluna in tabela.select_dtypes(include=["object", "string"]).columns:
        tamanhos = tabela[coluna].dropna().map(lambda v: len(v) if isinstance(v, str) else 0)
        maior = int(tamanhos.max()) if not tamanhos.empty else 0
        if maior > CARACTERES_POR_CELULA:
            dica = (
                "Use a geometria 'Sem geometria', ou grave em GeoPackage ou CSV."
                if coluna == coluna_wkt else "Grave em CSV ou GeoPackage."
            )
            raise ValueError(
                f"A coluna '{coluna}' tem textos de {_milhar(maior)} caracteres, acima do "
                f"limite de {_milhar(CARACTERES_POR_CELULA)} por célula do Excel (é comum no "
                f"WKT de polígonos grandes). {dica}"
            )


def _para_excel(tabela: pd.DataFrame, avisos: List[str]) -> pd.DataFrame:
    """What an XLSX cell cannot hold as it is. Changes `tabela`, which is a copy.

    - ±inf: GDAL wrote <v>inf</v>, which is not a number in the format
      (LibreOffice showed 0). It becomes an empty cell.
    - A date with a time zone: GDAL dropped the zone (02:30 UTC and 02:30 in
      Porto Velho came out as the same cell). It goes as text with the
      offset, as in the CSV.
    - An integer of more than 15 digits: see DIGITOS_DO_EXCEL.
    """
    for coluna in tabela.columns:
        serie = tabela[coluna]
        if isinstance(serie.dtype, pd.DatetimeTZDtype):
            tabela[coluna] = serie.map(lambda v: None if pd.isna(v) else v.isoformat(sep=" "))
            avisos.append(
                f"Coluna '{coluna}': datas com fuso horário gravadas como texto, com o "
                "fuso (o Excel não guarda fuso)."
            )
        elif serie.dtype.kind == "f":
            infinitos = np.isinf(serie.to_numpy(dtype=float, na_value=np.nan))
            if infinitos.any():
                tabela[coluna] = serie.mask(infinitos)
                avisos.append(
                    f"Coluna '{coluna}': {_milhar(int(infinitos.sum()))} valor(es) infinito(s) "
                    "ficaram vazios (o Excel não tem infinito)."
                )
        elif serie.dtype.kind in "iu":
            presentes = serie.dropna()
            limite = 10**DIGITOS_DO_EXCEL
            if not presentes.empty and bool(((presentes >= limite) | (presentes <= -limite)).any()):
                # astype(object) first: map on a nullable Int64 goes through float
                # and would round the very digits this keeps.
                tabela[coluna] = serie.astype(object).map(lambda v: None if pd.isna(v) else str(int(v)))
                avisos.append(
                    f"Coluna '{coluna}': números de mais de {DIGITOS_DO_EXCEL} dígitos gravados "
                    "como texto, para o Excel não arredondar."
                )
    return tabela


def _neutralizar(valor: Any) -> Any:
    if (
        isinstance(valor, str)
        and valor.startswith(_INICIO_DE_FORMULA)
        and not _NUMERO_SIMPLES.fullmatch(valor)
    ):
        return "'" + valor
    return valor


def sem_formulas(tabela: pd.DataFrame) -> pd.DataFrame:
    """Text that Excel would run as a formula gets an apostrophe in front
    (OWASP) — the header too, since column names come from uploaded files and
    APIs."""
    tabela = tabela.copy()
    tabela.columns = [_neutralizar(c) for c in tabela.columns]
    for coluna in tabela.select_dtypes(include=["object", "string"]).columns:
        tabela[coluna] = tabela[coluna].map(_neutralizar)
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


def _para_gpkg(dado: pd.DataFrame) -> pd.DataFrame:
    """The GeoPackage stores dates in UTC (its spec); another offset makes GDAL
    warn "Non-conformant content" when reading the file."""
    com_fuso = [c for c in dado.columns if isinstance(dado[c].dtype, pd.DatetimeTZDtype)]
    if not com_fuso:
        return dado
    dado = dado.copy()
    for coluna in com_fuso:
        dado[coluna] = dado[coluna].dt.tz_convert("UTC")
    return dado


def conferir_tamanho_do_kml(dado: gpd.GeoDataFrame) -> None:
    """Refuses a KML that would hold the executor too long (ELEMENTOS_DO_KML)."""
    vertices = int(dado.geometry.count_coordinates().sum())
    valores = len(dado) * (len(dado.columns) - 1)
    if vertices + valores > ELEMENTOS_DO_KML:
        raise ValueError(
            f"O KML teria {_milhar(vertices)} vértices e {_milhar(valores)} valores de "
            f"atributos, acima dos {_milhar(ELEMENTOS_DO_KML)} que o executor grava sem "
            "ficar parado tempo demais (e pesado para o Google Earth abrir). Simplifique "
            "a geometria (nó Simplify), leve menos colunas ou grave em GeoPackage."
        )


def _para_kml(dado: gpd.GeoDataFrame, campo: str, avisos: List[str]) -> tuple[gpd.GeoDataFrame, str]:
    """What the KML driver writes wrong. Returns the layer and the name field,
    renamed along with its column.

    - A field name with & < > or ": see _FORA_DO_XML. The character becomes '_'.
    - With a name field chosen, GDAL declares it as `Name`, and the values of
      another column called name (any case) went out under `Name` too. That
      column takes a suffix.
    - An empty geometry (POINT EMPTY, what intersecting a point with a polygon
      it is not in returns) became <coordinates>nan,nan</coordinates>, read back
      as POINT (0 0). It goes without geometry.
    """
    geometria = dado.geometry.name
    reservados = ["name"] if campo else []
    nomes: List[str] = []
    renomeados: Dict[str, str] = {}
    for coluna in dado.columns:
        nome, motivo = coluna, None
        if coluna != geometria and _FORA_DO_XML.search(coluna):
            nome, motivo = _FORA_DO_XML.sub("_", coluna), "o KML não aceita & < > \" no nome de um campo"
        elif coluna != geometria and campo and coluna != campo and coluna.lower() == "name":
            motivo = f"o KML chama de Name o campo do nome ('{campo}')"
        if motivo:
            outros = [c for c in dado.columns if c != coluna] + nomes + reservados
            nome = _nome_livre(outros, nome)
            renomeados[coluna] = nome
            avisos.append(f"A coluna '{coluna}' foi gravada como '{nome}': {motivo}.")
        nomes.append(nome)
    campo = renomeados.get(campo, campo)
    vazias = dado.geometry.is_empty
    if not renomeados and not vazias.any():
        return dado, campo
    dado = dado.copy()
    dado.columns = nomes
    if vazias.any():
        dado[geometria] = dado.geometry.where(~vazias, None)
    return dado, campo


def gravar(
    dado: pd.DataFrame, formato: str, pasta: str, nome: str, opcoes: Dict[str, Any],
    avisos: Optional[List[str]] = None,
) -> str:
    """Writes `dado` into `pasta` and returns the file's path. Blocking."""
    # Loaded here, not at the top of the module: importing the node catalog (in
    # every API worker) does not load GDAL. leitura_geo first, because it turns
    # the VRT drivers off (GDAL_SKIP) before GDAL registers them, should this
    # be the first use of GDAL in the process.
    import flow.utils.leitura_geo  # noqa: F401
    import pyogrio

    avisos = [] if avisos is None else avisos
    extensao = FORMATOS[formato][0]
    caminho = os.path.join(pasta, f"{nome}{extensao}")

    if formato == "gpkg":
        pyogrio.write_dataframe(
            _para_gpkg(dado), caminho, layer=opcoes["camada"], driver="GPKG",
            layer_options=_colunas_do_gpkg(dado),
        )
        return caminho

    if formato in ("kml", "kmz"):
        conferir_tamanho_do_kml(dado)
        dado, campo = _para_kml(dado, opcoes.get("campo_nome") or "", avisos)
        destino_kml = caminho if formato == "kml" else os.path.join(pasta, "doc.kml")
        # The layer is the folder Google Earth shows, and its name is also an
        # XML id: GDAL turns the slug's '-' into '_', warning on every run.
        pyogrio.write_dataframe(
            dado, destino_kml, layer=nome.replace("-", "_"), driver="KML",
            dataset_options={"NameField": campo} if campo else None,
        )
        if formato == "kmz":
            # A KMZ is a zip whose main document is doc.kml (Google's KMZ spec).
            with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.write(destino_kml, "doc.kml")
        return caminho

    tabela, coluna_wkt = geometria_em_colunas(dado, opcoes["geometria"])
    if tabela.shape[1] == 0:
        raise ValueError(
            "Não há colunas para gravar: a camada só tem a geometria, e a geometria na "
            "planilha está como 'Sem geometria'."
        )
    if formato == "xlsx":
        conferir_limites_do_excel(tabela, coluna_wkt)
        pyogrio.write_dataframe(
            _para_excel(tabela, avisos), caminho, layer=opcoes["planilha"], driver="XLSX",
        )
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
                        "português abre direto; vírgula grava com ponto decimal, o padrão "
                        "da maioria dos sistemas."
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
        # A GeoDataFrame without an active geometry (a node dropped it) is a table.
        como_tabela: Dict[int, pd.DataFrame] = {}
        entradas = {}
        for chave, valor in inputs.items():
            if isinstance(valor, gpd.GeoDataFrame) and valor.active_geometry_name is None:
                valor = como_tabela.setdefault(id(valor), pd.DataFrame(valor))
            entradas[chave] = valor

        camadas = [k for k, v in entradas.items() if isinstance(v, gpd.GeoDataFrame)]
        if any(not entradas[k].empty for k in camadas):
            return self.get_first_gdf(entradas)
        tabelas = [
            k for k, v in entradas.items()
            if isinstance(v, pd.DataFrame) and not isinstance(v, gpd.GeoDataFrame) and not v.empty
        ]
        if camadas and tabelas:
            # The layer is what was wired to be saved: writing the table that came
            # along under its name would hand over other data, with no error.
            raise ValueError(
                f"A camada chegou vazia ({camadas}), e a tabela que veio junto ({tabelas}) "
                "não é gravada no lugar dela."
            )
        if tabelas:
            if len({id(entradas[k]) for k in tabelas}) > 1:
                self.log(
                    f"Mais de uma tabela chegou a este nó ({tabelas}); usando '{tabelas[0]}' "
                    "e ignorando as demais."
                )
            return entradas[tabelas[0]]
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

        avisos: List[str] = []
        if tem_geometria:
            destino = CRS_DO_KML if formato in ("kml", "kmz") else self.get_param("crs", "EPSG:4326").strip()
            dado = await asyncio.to_thread(no_crs_de_destino, dado, destino, formato)
        renomeadas: Dict[str, str] = {}
        dado = await asyncio.to_thread(atributos_gravaveis, dado, avisos, renomeadas)

        campo_nome = self.get_param("campoNome", "").strip()
        if campo_nome not in dado.columns:
            # The editor offers the names as they arrive; a repeated one took a suffix.
            campo_nome = renomeadas.get(campo_nome, campo_nome)
        if formato in ("kml", "kmz") and campo_nome and campo_nome not in dado.columns:
            colunas = [c for c in dado.columns if c != dado.geometry.name]
            raise ValueError(f"O campo '{campo_nome}' não existe na camada. Campos: {colunas}.")

        camada = self.get_param("camada", "").strip() or safe_label
        if formato == "gpkg" and camada.lower().startswith(("gpkg", "sqlite")):
            # Prefixes the GeoPackage and SQLite keep for their own tables.
            camada = f"camada_{camada}"
            avisos.append(
                f"A camada foi gravada como '{camada}': o GeoPackage reserva os nomes "
                "começados por gpkg e sqlite."
            )
        opcoes = {
            "camada": camada,
            "campo_nome": campo_nome,
            "geometria": self.get_param("geometria", "auto"),
            "separador": self.get_param("separador", ";"),
            # Excel limits a sheet's name to 31 characters; the slug has no forbidden ones.
            "planilha": safe_label[:31],
        }
        features = len(dado)
        filename = f"{safe_label}{extensao}"

        with tempfile.TemporaryDirectory() as pasta:
            caminho = await asyncio.to_thread(gravar, dado, formato, pasta, safe_label, opcoes, avisos)
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

        for aviso in avisos:
            self.log(aviso)
        self.log(describe_locality(localidade, quem))
        onde = "neste executor" if localidade == EXECUTOR else "no MinIO"
        self.log(f"Arquivo salvo {onde}: {s3_key} ({formato}, {features} linhas)")

        # The declared outputs at the top, as the executor compares them: nested
        # under "output" they showed as schema drift on every run, and an edge
        # taking `artifact_s3_key` delivered nothing to the next node.
        return {
            "artifact_filename": filename,
            "artifact_s3_key": s3_key,
            "artifact_format": formato,
            "features": features,
            "__artifact__": artifact_meta,
        }
