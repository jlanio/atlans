# flow/nodes/spatial/transform_crs.py

import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import require_crs
from flow.utils.logger import get_logger
logger = get_logger(__name__)

@register_node
class TransformCRS(BaseNode):
    """
    Reprojeta um GeoDataFrame para o CRS especificado (ex: 'EPSG:3857', 'EPSG:4326').
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "TransformCRS",
            "alias": "Transformar CRS",
            "description": "Reprojeta um GeoDataFrame para o CRS alvo especificado.",
            "type": "spatial",
            "properties": [
                {
                    "name": "targetCrs", "required": True,
                    "label": "CRS de destino",
                    "type": "string",
                    "default": "",
                    "description": "CRS de destino (ex: 'EPSG:4326')."
                }
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "GeoDataFrame reprojetado para o CRS de destino"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()

        target_crs = self.parameters.get("targetCrs", "").strip()

        if not target_crs:
            raise ValueError("Parâmetro obrigatório ausente: 'targetCrs'.")

        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        require_crs(gdf)

        logger.info(f"Reprojetando de {gdf.crs} para {target_crs} ({len(gdf)} feições).")

        try:
            reprojected = await asyncio.to_thread(lambda: gdf.to_crs(target_crs))
        except Exception as e:
            logger.error(f"Erro ao reprojetar para {target_crs}: {e}")
            raise RuntimeError(f"Falha ao transformar o CRS para '{target_crs}'. Verifique se é um código válido como 'EPSG:4326'.")

        logger.info(f"Reprojeção bem-sucedida. Novo CRS: {reprojected.crs}")
        return {"output": reprojected}
