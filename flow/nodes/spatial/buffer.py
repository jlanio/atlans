import asyncio
import warnings
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import require_crs, working_crs_for_unit
from flow.utils.logger import get_logger
logger = get_logger(__name__)

@register_node
class BufferNode(BaseNode):
    """
    Applies a buffer to the geometries of a GeoDataFrame.
    The distance can be given in meters or in decimal degrees: if the layer's
    CRS uses another unit, the layer is reprojected for the computation and the
    result goes back to the input CRS.
    Supports cap and join styles, and validates geometric inputs.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Buffer',
            'alias': 'Buffer',
            'description': 'Aplica um buffer em cada feição de um GeoDataFrame, '
                           'filtrando geometrias inválidas ou vazias. A distância pode ser '
                           'em metros ou graus: quando o CRS da camada usa outra unidade, '
                           'ela é reprojetada automaticamente e o resultado volta ao CRS de entrada.',
            'type': 'spatial',
            'properties': [
                {
                    'name': 'distance',
                    'label': 'Distância',
                    'type': 'number',
                    'default': 0,
                    'description': 'Distância do buffer, na unidade escolhida abaixo.'
                },
                {
                    'name': 'distanceUnit',
                    'label': 'Unidade da distância',
                    'type': 'select',
                    'default': 'meters',
                    'description': 'Unidade em que a distância é interpretada. Se o CRS da camada '
                                   'usar outra unidade, ela é reprojetada automaticamente para o '
                                   'cálculo e o resultado volta ao CRS de entrada.',
                    'options': [
                        {'value': 'meters',  'label': 'Metros (m)'},
                        {'value': 'degrees', 'label': 'Graus decimais (°)'},
                    ],
                },
                {
                    'name': 'capStyle',
                    'label': 'Estilo da extremidade',
                    'type': 'select',
                    'default': 'round',
                    'description': 'Estilo das extremidades do buffer.',
                    'options': [
                        {'value': 'round',  'label': 'Arredondado'},
                        {'value': 'flat',   'label': 'Reto'},
                        {'value': 'square', 'label': 'Quadrado'},
                    ],
                },
                {
                    'name': 'joinStyle',
                    'label': 'Estilo da junção',
                    'type': 'select',
                    'default': 'round',
                    'description': 'Estilo das junções do buffer.',
                    'options': [
                        {'value': 'round', 'label': 'Arredondado'},
                        {'value': 'mitre', 'label': 'Angular (mitre)'},
                        {'value': 'bevel', 'label': 'Chanfrado (bevel)'},
                    ],
                },
                {
                    'name': 'quadSegs',
                    'label': 'Segmentos por curva',
                    'type': 'number',
                    'default': 8,
                    'description': 'Segmentos por curva (resolução).'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com as geometrias após aplicação do buffer'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        distance = self.get_param_float('distance')
        unit = self.parameters['distanceUnit']
        cap_style = self.parameters['capStyle']
        join_style = self.parameters['joinStyle']
        quad_segs = self.get_param_int('quadSegs')

        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        require_crs(gdf)

        # capStyle/joinStyle/distanceUnit already validated against the options by self.validate().

        if unit == 'degrees' and abs(distance) > 10:
            logger.warning(
                f"Buffer de {distance} graus (~{abs(distance) * 111:.0f} km). "
                "Confirme se a unidade escolhida é a desejada."
            )

        # Filters out invalid geometries
        # `is_valid` does one GEOS check per geometry — an O(n) that ran on the
        # event loop BEFORE any to_thread (the rest of the heavy work already
        # went there). It goes to a thread too.
        gdf_valid = await asyncio.to_thread(
            lambda: gdf[gdf.geometry.notnull() & gdf.geometry.is_valid & ~gdf.geometry.is_empty]
        )
        if gdf_valid.empty:
            raise ValueError("Nenhuma geometria válida encontrada para aplicar buffer.")

        if len(gdf_valid) < len(gdf):
            logger.warning(f"{len(gdf) - len(gdf_valid)} feições inválidas foram descartadas.")

        # Reprojects if the chosen unit is not the one of the layer's CRS
        original_crs = gdf.crs
        try:
            work_crs = await asyncio.to_thread(working_crs_for_unit, gdf_valid, unit)
        except Exception as e:
            logger.error(f"Falha ao determinar o CRS de trabalho para a unidade '{unit}': {e}")
            raise RuntimeError(
                f"Não foi possível determinar um CRS adequado para uma distância em '{unit}': {e}"
            )

        if work_crs is not None:
            logger.info(f"Reprojetando de {original_crs.to_string()} para {work_crs} "
                        f"para aplicar o buffer em {unit}.")
            try:
                gdf_valid = await asyncio.to_thread(lambda df: df.to_crs(work_crs), gdf_valid)
            except Exception as e:
                logger.error(f"Falha ao reprojetar para {work_crs}: {e}")
                raise RuntimeError(f"Erro ao reprojetar para {work_crs}: {e}")

        logger.info(f"Aplicando buffer de {distance} {unit} em {len(gdf_valid)} feições...")

        # Buffer em thread separada
        try:
            def _buffer(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
                with warnings.catch_warnings():
                    # A buffer in a geographic CRS is an explicit user choice
                    # when the unit is 'degrees' — the GeoPandas warning does not apply.
                    if unit == 'degrees':
                        warnings.filterwarnings(
                            "ignore", message=".*Geometry is in a geographic CRS.*"
                        )
                    return df.copy().set_geometry(
                        df.geometry.buffer(
                            distance,
                            cap_style=cap_style,
                            join_style=join_style,
                            resolution=quad_segs
                        )
                    )

            result = await asyncio.to_thread(_buffer, gdf_valid)
        except Exception as e:
            logger.error(f"Erro ao aplicar buffer: {e}")
            raise RuntimeError(f"Erro no buffer: {e}")

        # Back to the input CRS so the node is transparent in the pipeline
        if work_crs is not None:
            try:
                result = await asyncio.to_thread(lambda df: df.to_crs(original_crs), result)
            except Exception as e:
                logger.error(f"Falha ao reprojetar o resultado de volta para {original_crs}: {e}")
                raise RuntimeError(f"Erro ao reprojetar o resultado para {original_crs}: {e}")

        logger.info("Buffer finalizado.")
        return {"output": result}
