# flow/nodes/spatial/sobreposicao_binaria.py
"""
Base for the nodes that are a `gpd.overlay` of A with B and differ only in `how`.

Difference (A - B) and Symmetric Difference (A △ B) were the same node copied,
changing the `how` and the texts. Each subclass declares the four below and its
own `description()`; node name, descriptor, parameters and messages are the same
as before, so a saved workflow does not notice the change.

It is not registered: without `@register_node` and without `description()`, it
does not become a node.
"""
import asyncio
from typing import Any, Dict

import geopandas as gpd

from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


class SobreposicaoBinaria(BaseNode):
    """Binary overlay that rejects differing CRSs and unsupported geometry."""

    HOW: str            # gpd.overlay's `how`
    OPERACAO: str       # the operation in the rejection messages (CRS, geometry type)
    ROTULO: str         # "Erro na operação de <ROTULO>: ..."
    DESCRICAO_LOG: str  # "Executando <DESCRICAO_LOG> entre N e M feições."

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()
        gdf1, gdf2 = self.get_pair(inputs, operacao=self.OPERACAO, tipos_suportados=True)

        logger.info(f"Executando {self.DESCRICAO_LOG} entre {len(gdf1)} e {len(gdf2)} feições.")

        try:
            result = await asyncio.to_thread(gpd.overlay, gdf1, gdf2, how=self.HOW)
        except Exception as e:
            raise RuntimeError(f"Erro na operação de {self.ROTULO}: {e}") from e

        return {"output": result}
