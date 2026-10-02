# flow/nodes/spatial/voronoi.py
"""
Nó Voronoi — gera diagrama de Voronoi (polígonos de Thiessen) a partir de pontos.
"""
import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class VoronoiNode(BaseNode):

    @classmethod
    def description(cls):
        return {
            "name": "VoronoiNode",
            "alias": "Diagrama de Voronoi",
            "description": "Gera polígonos de Voronoi (Thiessen) a partir de uma camada de pontos.",
            "type": "spatial",
            "properties": [
                {
                    "name": "buffer_ratio",
                    "label": "Fator de expansão",
                    "type": "number",
                    "default": 0.5,
                    "description": "Fator de expansão do envelope externo (0.0 = sem expansão).",
                },
            ],
            "inputs": [{"name": "layer", "type": "geodataframe", "description": "Camada de pontos."}],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "Poligonos de Voronoi"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        from shapely.ops import voronoi_diagram
        from shapely.geometry import MultiPoint, GeometryCollection

        buffer_ratio = float(self.parameters.get("buffer_ratio", 0.5))
        gdf = self.get_first_gdf(inputs)

        def _compute(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            points = gdf.geometry.apply(lambda g: g.centroid if g.geom_type != "Point" else g)
            multi = MultiPoint(list(points))

            envelope = multi.envelope
            if buffer_ratio > 0:
                envelope = envelope.buffer((envelope.bounds[2] - envelope.bounds[0]) * buffer_ratio)

            regions: GeometryCollection = voronoi_diagram(multi, envelope=envelope)
            return gpd.GeoDataFrame(geometry=list(regions.geoms), crs=gdf.crs)

        result = await asyncio.to_thread(_compute, gdf)
        logger.info(f"Gerado Voronoi com {len(result)} polígonos.")
        return {"output": result}
