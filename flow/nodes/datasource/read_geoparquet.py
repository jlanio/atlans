import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.drive_resolver import read_drive_file_as
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class ReadGeoParquetNode(BaseNode):
    """
    Reads a GeoParquet file from the Workspace Drive and returns a GeoDataFrame.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ReadGeoParquet',
            'alias': 'Ler GeoParquet',
            'description': 'Le um arquivo GeoParquet do Drive e retorna um GeoDataFrame.',
            'type': 'datasource',
            'dynamic_output': True,
            'properties': [
                {
                    'name': 'driveFileId', 'required': True,
                    'label': 'Arquivo do Drive',
                    'type': 'drive',
                    'default': '',
                    'description': 'Arquivo GeoParquet do Drive',
                    'drive_extensions': ['parquet', 'geoparquet'],
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame lido do arquivo GeoParquet'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        drive_file_id = self.get_param('driveFileId', '').strip()

        if not drive_file_id:
            raise ValueError("Parametro 'driveFileId' e obrigatorio.")

        gdf, original_name = await read_drive_file_as(
            drive_file_id, gpd.read_parquet, label="GeoParquet"
        )
        logger.info("Lendo GeoParquet do Drive: '%s'", original_name)

        if gdf.empty:
            logger.warning("GeoDataFrame vazio lido de '%s'.", original_name)

        logger.info("GeoParquet carregado com %d feicoes. CRS: %s", len(gdf), gdf.crs)
        return {"output": gdf}
