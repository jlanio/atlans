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
class ReadShapefileNode(BaseNode):
    """
    Le um Shapefile ESRI do Drive do Workspace e retorna um GeoDataFrame.
    Suporta arquivos .shp e .zip contendo shapefile.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ReadShapefile',
            'alias': 'Ler Shapefile',
            'description': 'Le um Shapefile do Drive e retorna um GeoDataFrame.',
            'type': 'datasource',
            'dynamic_output': True,
            'properties': [
                {
                    'name': 'driveFileId', 'required': True,
                    'label': 'Arquivo do Drive',
                    'type': 'drive',
                    'default': '',
                    'description': 'Arquivo Shapefile do Drive',
                    'drive_extensions': ['shp', 'zip'],
                },
                {
                    'name': 'crs',
                    'label': 'CRS de saída',
                    'type': 'string',
                    'default': '',
                    'description': 'CRS de saida. Se informado e diferente do CRS do arquivo, realiza reprojecao.'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame lido do arquivo Shapefile'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        drive_file_id = self.get_param('driveFileId', '').strip()
        crs = self.get_param('crs', '').strip()

        if not drive_file_id:
            raise ValueError("Parametro 'driveFileId' e obrigatorio.")

        gdf, original_name = await read_drive_file_as(
            drive_file_id, ler_geodataframe, label="Shapefile"
        )
        logger.info("Lendo Shapefile do Drive: '%s'", original_name)

        if gdf.empty:
            logger.warning("GeoDataFrame vazio lido de '%s'.", original_name)

        gdf = await asyncio.to_thread(ensure_gdf_crs, gdf, crs)

        logger.info("Shapefile carregado com %d feicoes. CRS: %s", len(gdf), gdf.crs)
        return {"output": gdf}
