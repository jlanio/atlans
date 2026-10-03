import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.drive_resolver import read_drive_file_as
from flow.utils.leitura_geo import ler_geodataframe
from flow.utils.logger import get_logger
from flow.utils.geo_helpers import ensure_gdf_crs
logger = get_logger(__name__)


@register_node
class ReadGeoJSONNode(BaseNode):
    """
    Reads a GeoJSON file from the Workspace Drive and returns a GeoDataFrame.
    Optionally reprojects to the specified CRS.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ReadGeoJSON',
            'alias': 'Ler GeoJSON',
            'description': 'Le um arquivo GeoJSON do Drive e retorna um GeoDataFrame.',
            'type': 'datasource',
            'dynamic_output': True,
            'properties': [
                {
                    'name': 'driveFileId', 'required': True,
                    'label': 'Arquivo do Drive',
                    'type': 'drive',
                    'default': '',
                    'description': 'Arquivo GeoJSON do Drive',
                    'drive_extensions': ['geojson'],
                },
                {
                    'name': 'crs',
                    'label': 'CRS de saída',
                    'type': 'string',
                    'default': 'EPSG:4326',
                    'description': 'CRS de saida. Se diferente do CRS do arquivo, realiza reprojecao.'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame lido do arquivo GeoJSON'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        drive_file_id = self.get_param('driveFileId', '').strip()
        crs = self.get_param('crs', 'EPSG:4326').strip()

        if not drive_file_id:
            raise ValueError("Parametro 'driveFileId' e obrigatorio.")

        gdf, original_name = await read_drive_file_as(
            drive_file_id, ler_geodataframe, label="GeoJSON"
        )
        logger.info("Lendo GeoJSON do Drive: '%s'", original_name)

        if gdf.empty:
            logger.warning("GeoDataFrame vazio lido de '%s'.", original_name)

        gdf = await asyncio.to_thread(ensure_gdf_crs, gdf, crs)

        logger.info("GeoJSON carregado com %d feicoes. CRS: %s", len(gdf), gdf.crs)
        return {"output": gdf}
