# flow/nodes/spatial/filter_by_geometry_type.py
"""Separa GeoDataFrame por tipo de geometria (Point, LineString, Polygon)."""
import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_POINT_TYPES = {"Point", "MultiPoint"}
_LINE_TYPES = {"LineString", "MultiLineString"}
_POLYGON_TYPES = {"Polygon", "MultiPolygon"}


@register_node
class FilterByGeometryType(BaseNode):

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "FilterByGeometryType",
            "alias": "Filtrar por Tipo de Geometria",
            "description": (
                "Separa um GeoDataFrame em saídas distintas por tipo de geometria: "
                "pontos, linhas, polígonos e outros."
            ),
            "type": "spatial",
            "properties": [
                {
                    "name": "include_multi",
                    "label": "Incluir Multi*",
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "Agrupa Multi* com tipo base "
                        "(ex: MultiPolygon junto com Polygon na saída 'polygons')."
                    ),
                },
            ],
            "outputs": [
                {"name": "points", "type": "geodataframe", "description": "Feições do tipo ponto", "port": True},
                {"name": "lines", "type": "geodataframe", "description": "Feições do tipo linha", "port": True},
                {"name": "polygons", "type": "geodataframe", "description": "Feições do tipo polígono", "port": True},
                {"name": "other", "type": "geodataframe", "description": "Outros tipos de geometria", "port": True},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        gdf = self.get_first_gdf(inputs)
        include_multi = self.get_param_bool("include_multi", True)

        def _split(gdf: gpd.GeoDataFrame) -> Dict[str, gpd.GeoDataFrame]:
            geom_type = gdf.geometry.geom_type

            if include_multi:
                pt_types, ln_types, pg_types = _POINT_TYPES, _LINE_TYPES, _POLYGON_TYPES
            else:
                pt_types = {"Point"}
                ln_types = {"LineString"}
                pg_types = {"Polygon"}

            points_mask   = geom_type.isin(pt_types)
            lines_mask    = geom_type.isin(ln_types)
            polygons_mask = geom_type.isin(pg_types)
            other_mask    = ~(points_mask | lines_mask | polygons_mask)

            return {
                "points":   gdf[points_mask].copy(),
                "lines":    gdf[lines_mask].copy(),
                "polygons": gdf[polygons_mask].copy(),
                "other":    gdf[other_mask].copy(),
            }

        result = await asyncio.to_thread(_split, gdf)

        counts = {k: len(v) for k, v in result.items() if len(v) > 0}
        logger.info("FilterByGeometryType: %d feições → %s", len(gdf), counts or "nenhuma saída com dados")

        return result
