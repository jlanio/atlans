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
    Nó que calcula a área de cada feição em um GeoDataFrame e adiciona
    uma coluna 'area' convertida na unidade escolhida.
    Suporta unidades: 'm2' (metros quadrados), 'ha' (hectares) e 'km2' (quilômetros quadrados).
    Apenas geometrias de área (Polygon, MultiPolygon) são consideradas.
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

        # Obtém o GeoDataFrame de entrada via helper da classe base
        gdf = self.get_first_gdf(inputs)

        # Verifica se CRS está definido
        require_crs(gdf)

        # Filtra geometrias de área
        valid_types = ['Polygon', 'MultiPolygon']
        gdf = gdf[gdf.geometry.geom_type.isin(valid_types)]
        if gdf.empty:
            raise ValueError("Nenhuma feição com geometria de área ('Polygon' ou 'MultiPolygon') encontrada.")

        # Reprojeta para UTM se necessário
        if gdf.crs.is_geographic:
            logger.info("Reprojetando GeoDataFrame geográfico para UTM antes de calcular área.")
            try:
                (gdf,) = await asyncio.to_thread(para_crs_metrico, gdf)
            except Exception as e:
                logger.error(f"Falha ao reprojetar para UTM: {e}")
                raise RuntimeError(f"Erro ao reprojetar para UTM: {e}")

        # Calcula área
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
