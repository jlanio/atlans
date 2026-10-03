import asyncio
import geopandas as gpd
from shapely.geometry import box
import shapely
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import reject_unsupported_geom_types
from flow.utils.logger import get_logger

logger = get_logger(__name__)

@register_node
class ComputeBoundingBox(BaseNode):
    """
    Node that computes the bounding box of a GeoDataFrame.
    Can return the overall bounding box or one per feature.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ComputeBoundingBox',
            'alias': 'Caixa Delimitadora',
            'description': 'Calcula o bounding box de um GeoDataFrame ou GeoJSON, '
                           'retornando um GeoDataFrame de poligonos.',
            'type': 'spatial',
            'properties': [
                {
                    'name': 'perFeature',
                    'label': 'Por feição',
                    'type': 'boolean',
                    'default': False,
                    'description': 'Se True, retorna um bounding box para cada feição; se False, retorna apenas o bounding box geral'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com os polígonos de bounding box'},
                {'name': 'bbox_string', 'type': 'string', 'description': 'Formato minx,miny,maxx,maxy'},
                {'name': 'minx', 'type': 'number', 'description': 'Longitude mínima (oeste)'},
                {'name': 'miny', 'type': 'number', 'description': 'Latitude mínima (sul)'},
                {'name': 'maxx', 'type': 'number', 'description': 'Longitude máxima (leste)'},
                {'name': 'maxy', 'type': 'number', 'description': 'Latitude máxima (norte)'},
            ],
        }

    @staticmethod
    def _to_gdf(data) -> gpd.GeoDataFrame:
        """Converts GeoJSON (dict or string) to a GeoDataFrame. Passthrough if it is already a GDF."""
        if isinstance(data, gpd.GeoDataFrame):
            return data
        if isinstance(data, str):
            import json
            data = json.loads(data)
        if isinstance(data, dict):
            if "features" in data:
                return gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
            if "geometry" in data:
                return gpd.GeoDataFrame.from_features([data], crs="EPSG:4326")
        raise TypeError(f"Input nao reconhecido: esperado GeoJSON ou GeoDataFrame, recebido {type(data).__name__}")

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, gpd.GeoDataFrame]:
        self.validate()

        # Auto-conversao: aceita GeoJSON (dict/string) alem de GeoDataFrame
        raw = next(iter(inputs.values()), None)
        try:
            gdf = self._to_gdf(raw)
        except (TypeError, ValueError):
            gdf = self.get_first_gdf(inputs)

        reject_unsupported_geom_types(gdf, operation="bounding box")

        per_feature = self.parameters.get('perFeature', False)

        def _compute_boxes(df: gpd.GeoDataFrame, per_feat: bool) -> gpd.GeoDataFrame:
            if per_feat:
                bounds_df = df.bounds
                # PERF: vectorized shapely.box — 1 call over numpy arrays instead
                # of one box() per feature in a Python loop (interpreted O(n)).
                geometries = shapely.box(
                    bounds_df.minx.values, bounds_df.miny.values,
                    bounds_df.maxx.values, bounds_df.maxy.values,
                )
                return gpd.GeoDataFrame(geometry=geometries, crs=df.crs)
            else:
                minx, miny, maxx, maxy = df.total_bounds
                single_box = box(minx, miny, maxx, maxy)
                return gpd.GeoDataFrame(geometry=[single_box], crs=df.crs)

        try:
            result_gdf = await asyncio.to_thread(_compute_boxes, gdf, per_feature)
        except Exception as e:
            logger.error(f"Erro ao calcular bounding box: {e}")
            raise RuntimeError(f"Erro no ComputeBoundingBox: {e}")

        # Extrai coordenadas do bbox geral (mesmo em modo per_feature)
        minx, miny, maxx, maxy = gdf.total_bounds
        bbox_str = f"{minx},{miny},{maxx},{maxy}"

        logger.info(
            f"ComputeBoundingBox: {'por feição' if per_feature else 'geral'} "
            f"calculado(s), CRS: {result_gdf.crs}, bbox: {bbox_str}"
        )

        return {
            "output": result_gdf,
            "bbox_string": bbox_str,
            "minx": float(minx),
            "miny": float(miny),
            "maxx": float(maxx),
            "maxy": float(maxy),
        }
