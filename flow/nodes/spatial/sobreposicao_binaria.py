# flow/nodes/spatial/sobreposicao_binaria.py
"""
Base dos nós que são um `gpd.overlay` de A com B e só diferem no `how`.

Diferença (A - B) e Diferença Simétrica (A △ B) eram o mesmo nó copiado,
mudando o `how` e os textos. Cada subclasse declara os quatro abaixo e a sua
`description()`; nome do nó, descriptor, parâmetros e mensagens continuam os de
antes, então um workflow salvo não percebe a troca.

Não é registrada: sem `@register_node` e sem `description()`, não vira nó.
"""
import asyncio
from typing import Any, Dict

import geopandas as gpd

from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


class SobreposicaoBinaria(BaseNode):
    """Overlay binário que recusa CRS diferentes e geometria não suportada."""

    HOW: str            # `how` do gpd.overlay
    OPERACAO: str       # a operação nas mensagens de recusa (CRS, tipo de geometria)
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
