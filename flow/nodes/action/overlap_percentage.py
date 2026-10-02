import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import para_crs_metrico
from flow.utils.logger import get_logger
logger = get_logger(__name__)

@register_node
class OverlapPercentage(BaseNode):
    """
    Nó que calcula a porcentagem de sobreposição entre duas camadas poligonais (layerA e layerB).
    Retorna um GeoDataFrame contendo apenas as geometrias de interseção, com campos de percentual.

    Exemplo de saída:
    - percentA: % da interseção em relação à área total de A
    - percentB: % da interseção em relação à área total de B
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "OverlapPercentage",
            "alias": "Percentual Sobreposição",
            "description": "Calcula a porcentagem de área onde A e B se sobrepõem. Retorna geometrias de interseção com campo de percentual.",
            "type": "action",
            "properties": [
                {
                    "name": "reference",
                    "label": "Camada de Referência",
                    "type": "string",
                    "default": "A",
                    "description": "Para qual camada calcular o %: 'A', 'B' ou 'both'."
                }
            ],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'Primeira camada poligonal (GeoDataFrame).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'Segunda camada poligonal (GeoDataFrame).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame de interseção com colunas de percentual de sobreposição'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Valida parâmetros
        self.validate()

        ref = self.parameters.get("reference", "A").upper()

        # Obtém as camadas via helper da classe base (o CRS é tratado abaixo)
        gdfA, gdfB = self.get_pair(inputs, crs=None)

        # Reprojeção para UM CRS métrico comum às duas camadas. Estimar a UTM de
        # cada uma em separado as punha em zonas diferentes quando os centros
        # caíam em lados opostos de um meridiano de zona, e o overlay entre CRSs
        # diferentes só avisa — o percentual saía errado, sem erro.
        try:
            gdfA, gdfB = await asyncio.to_thread(para_crs_metrico, gdfA, gdfB)
        except Exception as e:
            logger.warning(f"Falha ao reprojetar as camadas para um CRS métrico comum: {e}")

        # Calcula interseção
        try:
            intersection = await asyncio.to_thread(gpd.overlay, gdfA, gdfB, how="intersection")
        except Exception as e:
            logger.error(f"Erro ao calcular interseção: {e}")
            raise RuntimeError(f"Erro no overlay: {e}")

        # Calcula áreas
        areaA = await asyncio.to_thread(lambda df: df.geometry.area.sum(), gdfA)
        areaB = await asyncio.to_thread(lambda df: df.geometry.area.sum(), gdfB)
        areaI = await asyncio.to_thread(lambda df: df.geometry.area.sum(), intersection)

        # Calcula percentual e adiciona como coluna no GeoDataFrame
        if ref == "A":
            pctA = 0.0 if areaA == 0 else float(areaI / areaA) * 100
            intersection["percentA"] = pctA
        elif ref == "B":
            pctB = 0.0 if areaB == 0 else float(areaI / areaB) * 100
            intersection["percentB"] = pctB
        elif ref == "BOTH":
            pctA = 0.0 if areaA == 0 else float(areaI / areaA) * 100
            pctB = 0.0 if areaB == 0 else float(areaI / areaB) * 100
            intersection["percentA"] = pctA
            intersection["percentB"] = pctB
        else:
            raise ValueError("Parâmetro 'reference' inválido. Use 'A', 'B' ou 'both'.")

        return {"output": intersection}
