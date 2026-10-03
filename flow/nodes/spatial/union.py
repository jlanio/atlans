import asyncio
import geopandas as gpd
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)

@register_node
class UnionNode(BaseNode):
    """
    Computes the spatial union between two layers (GeoDataFrames).
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'UnionNode',
            'alias': 'União Espacial',
            'description': 'Realiza a operação de união entre duas camadas vetoriais.',
            'type': 'spatial',
            'properties': [],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'Primeira camada (GeoDataFrame).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'Segunda camada (GeoDataFrame).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da união espacial entre as camadas'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()
        # Gets and validates the layers via the base class helper (rejects differing CRSs)
        gdf1, gdf2 = self.get_pair(inputs, operacao="união", tipos_suportados=True)

        logger.info(f"Executando união entre {len(gdf1)} e {len(gdf2)} feições...")

        # Uses concat if the columns are compatible
        if set(gdf1.columns) == set(gdf2.columns):
            logger.info("Colunas compatíveis. Aplicando concatenação direta (merge).")
            result = await asyncio.to_thread(lambda: gpd.GeoDataFrame(
                pd.concat([gdf1, gdf2], ignore_index=True),
                crs=gdf1.crs
            ))
        else:
            logger.info("Colunas incompatíveis. Aplicando união via overlay.")
            try:
                result = await asyncio.to_thread(gpd.overlay, gdf1, gdf2, how='union')
            except Exception as e:
                logger.error(f"Erro na união espacial: {e}")
                raise RuntimeError(f"Erro na operação de união: {e}") from e

        return {"output": result}
