# flow/utils/coordenadas.py
"""A table with latitude/longitude columns as a GeoDataFrame of points.

Shared by DataInput (any origin) and ReadCSVWithCoords, so the same CSV gives
the same geometry whichever node reads it. The columns are taken in the `crs`
the node is given — the rule both nodes document.
"""
from typing import Any

from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _coordenada(serie, coluna: str):
    import pandas as pd
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")
    # A ',' CSV can still quote a decimal comma ("-23,55"); XLSX keeps text as typed.
    texto = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    numeros = pd.to_numeric(texto, errors="coerce")
    invalidos = texto.notna() & (texto != "") & numeros.isna()
    if invalidos.any():
        exemplo = serie[invalidos].iloc[0]
        raise ValueError(f"A coluna '{coluna}' tem valor que não é número: {exemplo!r}.")
    return numeros


def pontos_de_colunas(dados: Any, lat_col: str, lon_col: str, crs: str) -> Any:
    """`dados` as points from its latitude/longitude columns, in `crs`.

    A row without both coordinates stays without geometry: a point at
    (NaN, NaN) is not "no position", and it breaks a spatial join downstream.
    """
    import geopandas as gpd
    import pandas as pd

    if isinstance(dados, gpd.GeoDataFrame):
        logger.info("Colunas de latitude/longitude ignoradas — o arquivo já tem geometria.")
        return dados
    if not isinstance(dados, pd.DataFrame):
        raise ValueError(
            "As colunas de latitude e longitude valem para tabelas (CSV, XLSX); "
            "este arquivo não foi lido como tabela."
        )
    for coluna, papel in ((lat_col, "latitude"), (lon_col, "longitude")):
        if coluna not in dados.columns:
            raise ValueError(
                f"Coluna de {papel} '{coluna}' não encontrada. "
                f"Colunas disponíveis: {list(dados.columns)}"
            )
    lat = _coordenada(dados[lat_col], lat_col)
    lon = _coordenada(dados[lon_col], lon_col)
    pontos = gpd.points_from_xy(lon, lat)
    vazias = (lat.isna() | lon.isna()).to_numpy()
    if vazias.any():
        pontos[vazias] = None
        logger.warning("%d linha(s) sem coordenada ficaram sem geometria.", int(vazias.sum()))
    return gpd.GeoDataFrame(dados, geometry=pontos, crs=crs)
