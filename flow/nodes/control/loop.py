import asyncio
import geopandas as gpd
from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class LoopNode(BaseNode):
    """
    Control node that acts as a batch processor:
    splits a GeoDataFrame into fixed-size chunks and returns them as a list.
    Useful for processing large datasets in sequential partitions.

    Properties:
      - chunkSize: number of rows per chunk (default 100)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Loop',
            'alias': 'Loop em Lote',
            'description': (
                'Divide um GeoDataFrame em chunks de tamanho fixo e retorna '
                'uma lista de GeoDataFrames para processamento em lote.'
            ),
            'type': 'control',
            'properties': [
                {
                    'name': 'chunkSize',
                    'label': 'Tamanho do chunk',
                    'type': 'integer',
                    'default': 100,
                    'description': 'Número de linhas por chunk (partição). Default: 100.'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'list', 'description': 'Lista de GeoDataFrames particionados em chunks'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Parameter validation and extraction
        # -------------------------------------------------------
        self.validate()

        chunk_size = self.get_param_int('chunkSize')
        if chunk_size <= 0:
            raise ValueError("chunkSize deve ser maior que zero.")

        # -------------------------------------------------------
        # 2) Gets the input GeoDataFrame via the base class helper
        # -------------------------------------------------------
        gdf = self.get_first_gdf(inputs)

        logger.info(
            f"LoopNode: dividindo {len(gdf)} feições em chunks de {chunk_size} linhas."
        )

        # -------------------------------------------------------
        # 3) Splits the GeoDataFrame into chunks (in a separate thread)
        # -------------------------------------------------------
        # Safety limit to avoid memory exhaustion
        MAX_CHUNKS = 1000
        expected_chunks = (len(gdf) + chunk_size - 1) // chunk_size
        if expected_chunks > MAX_CHUNKS:
            raise ValueError(
                f"A combinacao de {len(gdf)} feicoes com chunkSize={chunk_size} "
                f"geraria {expected_chunks} chunks, excedendo o limite de {MAX_CHUNKS}. "
                f"Aumente o chunkSize para no minimo {(len(gdf) + MAX_CHUNKS - 1) // MAX_CHUNKS}."
            )

        def _split_into_chunks(df: gpd.GeoDataFrame, size: int) -> List[gpd.GeoDataFrame]:
            chunks = []
            for start in range(0, len(df), size):
                chunk = df.iloc[start:start + size].copy().reset_index(drop=True)
                chunks.append(chunk)
            return chunks

        try:
            chunks = await asyncio.to_thread(_split_into_chunks, gdf, chunk_size)
        except Exception as e:
            logger.error(f"Erro ao dividir GeoDataFrame em chunks: {e}")
            raise RuntimeError(f"Erro no LoopNode ao dividir dados: {e}") from e

        logger.info(
            f"LoopNode: {len(gdf)} feições divididas em {len(chunks)} chunks "
            f"de até {chunk_size} linhas cada."
        )

        return {"output": chunks}
