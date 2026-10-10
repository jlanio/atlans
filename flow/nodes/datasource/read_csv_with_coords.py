import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.drive_resolver import read_drive_file_as
from flow.utils.leitura_csv import ler_csv
from flow.utils.logger import get_logger
logger = get_logger(__name__)


def _read_csv_as_geodataframe(file_path: str, lat_col: str, lon_col: str, crs: str) -> gpd.GeoDataFrame:
    """Helper bloqueante: le CSV e converte colunas lat/lon em geometria de pontos."""
    df = ler_csv(file_path)

    if lat_col not in df.columns:
        raise ValueError(f"Coluna de latitude '{lat_col}' nao encontrada no CSV. Colunas disponiveis: {list(df.columns)}")
    if lon_col not in df.columns:
        raise ValueError(f"Coluna de longitude '{lon_col}' nao encontrada no CSV. Colunas disponiveis: {list(df.columns)}")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=crs
    )
    return gdf


@register_node
class ReadCSVWithCoordsNode(BaseNode):
    """
    Reads a CSV file from the Workspace Drive with latitude and longitude columns
    and converts it into a GeoDataFrame with point geometry.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ReadCSVWithCoords',
            'alias': 'Ler CSV com Coordenadas',
            'description': 'Le um CSV do Drive com colunas lat/lon e retorna um GeoDataFrame de pontos.',
            'type': 'datasource',
            'dynamic_output': True,
            'properties': [
                {
                    'name': 'driveFileId', 'required': True,
                    'label': 'Arquivo do Drive',
                    'type': 'drive',
                    'default': '',
                    'description': 'Arquivo CSV do Drive',
                    'drive_extensions': ['csv'],
                },
                {
                    'name': 'latColumn',
                    'label': 'Coluna de latitude',
                    'type': 'string',
                    'default': 'lat',
                    'description': 'Nome da coluna de latitude no CSV.'
                },
                {
                    'name': 'lonColumn',
                    'label': 'Coluna de longitude',
                    'type': 'string',
                    'default': 'lon',
                    'description': 'Nome da coluna de longitude no CSV.'
                },
                {
                    'name': 'crs',
                    'label': 'CRS de saída',
                    'type': 'string',
                    'default': 'EPSG:4326',
                    'description': 'CRS a ser atribuido ao GeoDataFrame resultante.'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame de pontos gerado a partir do CSV'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        drive_file_id = self.get_param('driveFileId', '').strip()
        lat_col = self.get_param('latColumn', 'lat').strip()
        lon_col = self.get_param('lonColumn', 'lon').strip()
        crs = self.get_param('crs', 'EPSG:4326').strip()

        if not drive_file_id:
            raise ValueError("Parametro 'driveFileId' e obrigatorio.")
        if not lat_col:
            raise ValueError("Parametro 'latColumn' nao pode ser vazio.")
        if not lon_col:
            raise ValueError("Parametro 'lonColumn' nao pode ser vazio.")

        gdf, original_name = await read_drive_file_as(
            drive_file_id,
            lambda p: _read_csv_as_geodataframe(p, lat_col, lon_col, crs),
            label="CSV", reraise=(ValueError,),
        )
        logger.info("Lendo CSV com coordenadas do Drive: '%s' (lat=%s, lon=%s)", original_name, lat_col, lon_col)

        if gdf.empty:
            logger.warning("GeoDataFrame vazio gerado de '%s'.", original_name)

        logger.info("CSV carregado com %d feicoes. CRS: %s", len(gdf), gdf.crs)
        return {"output": gdf}
