import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class SimplifyNode(BaseNode):
    """
    Simplifies the topology of a GeoDataFrame's geometries using the
    Douglas-Peucker algorithm (via Shapely/GEOS).
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Simplify',
            'alias': 'Simplify',
            'description': (
                'Simplifica geometrias de um GeoDataFrame usando Douglas-Peucker. '
                'A tolerância é expressa na unidade do CRS das feições. '
                'preserveTopology evita que polígonos colapsem em geometrias degeneradas.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'tolerance',
                    'label': 'Tolerância',
                    'type': 'number',
                    'default': 1.0,
                    'description': (
                        'Tolerância de simplificação na unidade do CRS (ex.: metros em EPSG:3857). '
                        'Valores maiores produzem geometrias mais simplificadas.'
                    )
                },
                {
                    'name': 'preserveTopology',
                    'label': 'Preservar topologia',
                    'type': 'boolean',
                    'default': True,
                    'description': (
                        "Preserva topologia durante a simplificação. "
                        "Recomendado manter ativado para polígonos."
                    )
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com as geometrias simplificadas'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        tolerance = self.get_param_float('tolerance')
        preserve_topology = self.get_param_bool('preserveTopology')

        if tolerance < 0:
            raise ValueError(
                f"Tolerância deve ser não-negativa. Recebido: {tolerance}."
            )

        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        logger.info(
            f"Simplificando {len(gdf)} feições com tolerância={tolerance}, "
            f"preserveTopology={preserve_topology}."
        )

        def _simplify(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            result = df.copy()
            result[result.geometry.name] = df.geometry.simplify(
                tolerance,
                preserve_topology=preserve_topology
            )
            return result

        try:
            result = await asyncio.to_thread(_simplify, gdf)
        except Exception as e:
            logger.error(f"Erro ao simplificar geometrias: {e}")
            raise RuntimeError(f"Erro na simplificação: {e}")

        # Warns about degenerate geometries introduced
        if result.crs is None and gdf.crs is not None:
            result = result.set_crs(gdf.crs)

        n_empty = int(result.geometry.is_empty.sum())
        if n_empty > 0:
            logger.warning(
                f"{n_empty} geometrias colapsaram para vazio após simplificação. "
                "Considere reduzir a tolerância ou ativar preserveTopology."
            )

        logger.info("Simplificação finalizada.")
        return {"output": result}
