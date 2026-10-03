import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import align_crs
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class ClipNode(BaseNode):
    """
    Clips a GeoDataFrame (layerA = features) by the outline of another (layerB = mask).
    Automatically reprojects the mask to the features' CRS if needed.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Clip',
            'alias': 'Clip',
            'description': (
                'Recorta as feições de um GeoDataFrame (layerA) pelo contorno de outro GeoDataFrame '
                '(layerB = máscara). A máscara é reprojetada automaticamente para o CRS das feições.'
            ),
            'type': 'spatial',
            'properties': [],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'GeoDataFrame com as feições a recortar.'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'GeoDataFrame da máscara de recorte.'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com as feições recortadas pela máscara'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        # Gets the layers via the base class helper; requires a CRS on both (the
        # mask is aligned to the features' CRS inside the thread, in _clip).
        gdf, mask_gdf = self.get_pair(
            inputs, crs="alinhar", nomes=("camada 'layerA'", "máscara 'layerB'"),
        )

        logger.info(
            f"Iniciando clip: {len(gdf)} feições em 'layerA' "
            f"com máscara de {len(mask_gdf)} feições em 'layerB'."
        )

        def _clip(
            features: gpd.GeoDataFrame,
            mask: gpd.GeoDataFrame
        ) -> gpd.GeoDataFrame:
            # Reprojects the mask to the features' CRS if they differ
            if features.crs != mask.crs:
                logger.info(f"Reprojetando máscara de {mask.crs} para {features.crs}.")
            mask = align_crs(features, mask)

            clipped = features.clip(mask)
            return clipped

        try:
            result = await asyncio.to_thread(_clip, gdf, mask_gdf)
        except Exception as e:
            logger.error(f"Erro ao realizar clip: {e}")
            raise RuntimeError(f"Erro no clip: {e}")

        logger.info(
            f"Clip finalizado. {len(result)} feições resultantes "
            f"(de {len(gdf)} originais)."
        )
        return {"output": result}
