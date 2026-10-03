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
    Node that computes the overlap percentage between two polygon layers (layerA and layerB).
    Returns a GeoDataFrame containing only the intersection geometries, with percentage fields.

    Example output:
    - percentA: % of the intersection relative to the total area of A
    - percentB: % of the intersection relative to the total area of B
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
        # Validates parameters
        self.validate()

        ref = self.parameters.get("reference", "A").upper()

        # Gets the layers via the base class helper (CRS is handled below)
        gdfA, gdfB = self.get_pair(inputs, crs=None)

        # Reprojection to ONE metric CRS shared by both layers. Estimating the UTM of
        # each one separately put them in different zones when the centers
        # fell on opposite sides of a zone meridian, and the overlay between different
        # CRSs only warns — the percentage came out wrong, with no error.
        try:
            gdfA, gdfB = await asyncio.to_thread(para_crs_metrico, gdfA, gdfB)
        except Exception as e:
            logger.warning(f"Falha ao reprojetar as camadas para um CRS métrico comum: {e}")

        # Computes intersection
        try:
            intersection = await asyncio.to_thread(gpd.overlay, gdfA, gdfB, how="intersection")
        except Exception as e:
            logger.error(f"Erro ao calcular interseção: {e}")
            raise RuntimeError(f"Erro no overlay: {e}")

        # Computes areas
        areaA = await asyncio.to_thread(lambda df: df.geometry.area.sum(), gdfA)
        areaB = await asyncio.to_thread(lambda df: df.geometry.area.sum(), gdfB)
        areaI = await asyncio.to_thread(lambda df: df.geometry.area.sum(), intersection)

        # Computes percentage and adds it as a column in the GeoDataFrame
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
