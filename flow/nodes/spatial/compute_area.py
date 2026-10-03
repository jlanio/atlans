import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import para_crs_metrico, require_crs
from flow.utils.logger import get_logger
logger = get_logger(__name__)

@register_node
class ComputeArea(BaseNode):
    """
    Node that computes the area of each feature in a GeoDataFrame and adds
    an 'area' column converted to the chosen unit.
    Supported units: 'm2' (square meters), 'ha' (hectares) and 'km2' (square kilometers).
    Only areal geometries (Polygon, MultiPolygon) are considered.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ComputeArea',
            'alias': 'Calcular Área',
            'description': (
                "Calcula a area de cada feicao Polygon/MultiPolygon e adiciona a coluna 'area'. "
                "Feicoes com outros tipos de geometria sao ignoradas. "
                "CRS geografico (ex: EPSG:4326) e automaticamente reprojetado para UTM."
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'unit',
                    'label': 'Unidade de área',
                    'type': 'select',
                    'default': 'm2',
                    'description': 'Unidade da área calculada.',
                    'options': [
                        {'value': 'm2',  'label': 'Metros quadrados (m²)'},
                        {'value': 'ha',  'label': 'Hectares (ha)'},
                        {'value': 'km2', 'label': 'Quilômetros quadrados (km²)'},
                    ],
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com a coluna "area" calculada na unidade escolhida'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        unit = self.parameters.get('unit', 'm2').strip().lower()

        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        # Checks whether the CRS is defined
        require_crs(gdf)

        # Keeps areal geometries
        valid_types = ['Polygon', 'MultiPolygon']
        gdf = gdf[gdf.geometry.geom_type.isin(valid_types)]
        if gdf.empty:
            raise ValueError("Nenhuma feição com geometria de área ('Polygon' ou 'MultiPolygon') encontrada.")

        # Reprojects to UTM if needed
        if gdf.crs.is_geographic:
            logger.info("Reprojetando GeoDataFrame geográfico para UTM antes de calcular área.")
            try:
                (gdf,) = await asyncio.to_thread(para_crs_metrico, gdf)
            except Exception as e:
                logger.error(f"Falha ao reprojetar para UTM: {e}")
                raise RuntimeError(f"Erro ao reprojetar para UTM: {e}")

        # Computes the area
        try:
            area_m2 = await asyncio.to_thread(lambda df: df.geometry.area, gdf)
        except Exception as e:
            logger.error(f"Erro ao calcular área: {e}")
            raise RuntimeError(f"Erro no cálculo de área: {e}")

        # Converte unidade
        conversion_factors = {
            'm2': 1,
            'ha': 1 / 10_000,
            'km2': 1 / 1_000_000
        }

        gdf = gdf.copy()
        gdf['area'] = area_m2 * conversion_factors[unit]

        logger.info(f"Área calculada com sucesso para {len(gdf)} feições (unidade: {unit}).")
        return {"output": gdf}
