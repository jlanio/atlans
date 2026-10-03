import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import require_crs
from flow.utils.logger import get_logger

logger = get_logger(__name__)

@register_node
class CentroidNode(BaseNode):
    """
    Computes the centroid of each feature of a vector layer (GeoDataFrame).
    Ignores features with invalid or null geometry.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'CentroidNode',
            'alias': 'Centróide',
            'description': 'Calcula o centróide de cada feição de uma camada vetorial.',
            'type': 'spatial',
            'properties': [],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com os centróides das feições'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()
        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        require_crs(gdf)

        # Removes features without geometry
        gdf_valid = gdf[gdf.geometry.notnull()]
        if len(gdf_valid) < len(gdf):
            logger.warning(f"{len(gdf) - len(gdf_valid)} feições removidas por não possuírem geometria válida.")

        if gdf_valid.empty:
            raise ValueError("Nenhuma feição válida encontrada para cálculo de centróide.")

        logger.info(f"Camada válida com {len(gdf_valid)} feições. Calculando centróides...")

        try:
            centroids = await asyncio.to_thread(lambda: gdf_valid.geometry.centroid)
        except Exception as e:
            logger.error(f"Erro ao calcular centróides: {e}")
            raise RuntimeError(f"Erro no cálculo de centróides: {e}")

        result = gdf_valid.copy()
        result["geometry"] = centroids
        result.set_geometry("geometry", inplace=True)
        result.set_crs(gdf.crs, inplace=True)

        logger.info("Cálculo de centróides concluído com sucesso.")
        return {"output": result}
