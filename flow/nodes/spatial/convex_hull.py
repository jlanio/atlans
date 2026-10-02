# flow/nodes/spatial/convex_hull.py
"""
Nó Convex Hull — calcula o casco convexo (convex hull) de uma camada vetorial.
"""
import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class ConvexHullNode(BaseNode):

    @classmethod
    def description(cls):
        return {
            "name": "ConvexHullNode",
            "alias": "Casco Convexo",
            "description": "Calcula o casco convexo (convex hull) de todas as feições de entrada.",
            "type": "spatial",
            "properties": [
                {
                    "name": "per_feature",
                    "label": "Por feição",
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Se ligado, calcula o casco convexo individualmente por feição. "
                        "Se desligado, calcula o casco convexo da camada inteira."
                    ),
                },
            ],
            "inputs": [{"name": "layer", "type": "geodataframe", "description": "Camada de feições."}],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "Casco convexo"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        per_feature = bool(self.parameters.get("per_feature", False))
        gdf = self.get_first_gdf(inputs)

        def _compute(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            if per_feature:
                result = gdf.copy()
                result["geometry"] = result.geometry.convex_hull
                return result
            else:
                from shapely.ops import unary_union
                hull = unary_union(gdf.geometry).convex_hull
                return gpd.GeoDataFrame(geometry=[hull], crs=gdf.crs)

        result = await asyncio.to_thread(_compute, gdf)
        logger.info(f"Casco convexo calculado — {len(result)} polígono(s).")
        return {"output": result}
