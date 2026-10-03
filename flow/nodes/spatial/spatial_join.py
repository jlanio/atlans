import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import align_crs
from flow.utils.logger import get_logger
logger = get_logger(__name__)



@register_node
class SpatialJoinNode(BaseNode):
    """
    Performs a spatial join between two GeoDataFrames using gpd.sjoin.
    The right GeoDataFrame (layerB) is reprojected to the left one's CRS (layerA) if needed.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SpatialJoin',
            'alias': 'Spatial Join',
            'description': (
                'Realiza um join espacial entre dois GeoDataFrames (layerA = esquerda, layerB = direita) '
                'usando um predicado geométrico. O GeoDataFrame direito é reprojetado '
                'automaticamente para o CRS do esquerdo quando necessário.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'how',
                    'label': 'Tipo de junção',
                    'type': 'select',
                    'default': 'left',
                    'description': 'Como as feições dos dois lados são combinadas.',
                    'options': [
                        {'value': 'left',  'label': 'Left — mantém todas de A'},
                        {'value': 'inner', 'label': 'Inner — só com correspondência'},
                        {'value': 'right', 'label': 'Right — mantém todas de B'},
                    ],
                },
                {
                    'name': 'predicate',
                    'label': 'Relação espacial',
                    'type': 'select',
                    'default': 'intersects',
                    'description': 'Relação geométrica usada para casar as feições de A e B.',
                    'options': [
                        {'value': 'intersects', 'label': 'Intersecta'},
                        {'value': 'within',     'label': 'Está contida em (A dentro de B)'},
                        {'value': 'contains',   'label': 'Contém (A contém B)'},
                        {'value': 'crosses',    'label': 'Cruza'},
                        {'value': 'dwithin',    'label': 'A uma distância de (dwithin)'},
                    ],
                },
                {
                    'name': 'distance',
                    'label': 'Distância',
                    'type': 'number',
                    'default': 0,
                    'description': (
                        "Distância máxima entre as feições, nas unidades do CRS "
                        "(use um CRS métrico, ex.: UTM, para valores em metros). "
                        "Só se aplica à relação 'A uma distância de'."
                    ),
                    'visibleWhen': {'field': 'predicate', 'in': ['dwithin']},
                },
            ],
            'inputs': [
                {'name': 'layerA', 'type': 'geodataframe', 'description': 'GeoDataFrame da esquerda (base do join).'},
                {'name': 'layerB', 'type': 'geodataframe', 'description': 'GeoDataFrame da direita (a ser juntado).'}
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante do join espacial entre as camadas'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # how/predicate already validated against the options by self.validate().
        how = self.parameters['how']
        predicate = self.parameters['predicate']

        # 'dwithin' requires a distance (in CRS units).
        distance = None
        if predicate == 'dwithin':
            try:
                distance = float(self.parameters.get('distance', 0) or 0)
            except (TypeError, ValueError):
                distance = 0.0
            if distance <= 0:
                raise ValueError(
                    "Para a relação 'A uma distância de' (dwithin), informe uma 'Distância' > 0 "
                    "nas unidades do CRS (use um CRS métrico para valores em metros)."
                )

        # Gets the layers via the base class helper; requires a CRS on both (the
        # right one is aligned to the left one's CRS inside the thread, in _sjoin).
        left_gdf, right_gdf = self.get_pair(inputs, crs="alinhar")

        logger.info(
            f"SpatialJoin: how='{how}', predicate='{predicate}', "
            f"left={len(left_gdf)} feições, right={len(right_gdf)} feições."
        )

        def _sjoin(
            left: gpd.GeoDataFrame,
            right: gpd.GeoDataFrame
        ) -> gpd.GeoDataFrame:
            # Reprojects the right GDF to the left one's CRS if they differ
            if left.crs != right.crs:
                logger.info(f"Reprojetando GeoDataFrame direito de {right.crs} para {left.crs}.")
            right = align_crs(left, right)

            kwargs = {"distance": distance} if predicate == "dwithin" else {}
            result = gpd.sjoin(left, right, how=how, predicate=predicate, **kwargs)
            return result

        try:
            result = await asyncio.to_thread(_sjoin, left_gdf, right_gdf)
        except Exception as e:
            logger.error(f"Erro ao realizar spatial join: {e}")
            raise RuntimeError(f"Erro no spatial join: {e}")

        logger.info(
            f"SpatialJoin finalizado. {len(result)} feições resultantes."
        )
        return {"output": result}
