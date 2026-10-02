import asyncio
import geopandas as gpd
import numpy as np
import shapely
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class HeatmapNode(BaseNode):
    """
    Gera um grid de heatmap (estimativa de densidade via KDE) como um
    GeoDataFrame de polígonos retangulares, cada um com um valor de
    densidade relativa calculado a partir dos centroides das feições de entrada.

    O KDE é calculado com numpy (kernel gaussiano).
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Heatmap',
            'alias': 'Heatmap',
            'description': (
                'Gera um grid de heatmap (KDE) como GeoDataFrame de polígonos com '
                'coluna "density". '
                'resolution define o número de células por lado do grid.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'resolution',
                    'label': 'Resolução',
                    'type': 'integer',
                    'default': 50,
                    'description': (
                        'Número de células por lado do grid (ex.: 50 → grid 50×50). '
                        'Valores maiores produzem heatmaps mais detalhados mas mais lentos.'
                    )
                },
                {
                    'name': 'bandwidth',
                    'label': 'Largura de banda',
                    'type': 'number',
                    'default': 1.0,
                    'description': (
                        'Largura de banda do KDE como fração da extensão do dado (0 < bandwidth). '
                        'Valores maiores suavizam mais o heatmap.'
                    )
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame de grid com a coluna "density" representando a densidade relativa'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        resolution = self.get_param_int('resolution')
        bandwidth = self.get_param_float('bandwidth')

        if resolution < 2:
            raise ValueError(
                f"resolution deve ser >= 2. Recebido: {resolution}."
            )
        if bandwidth <= 0:
            raise ValueError(f"bandwidth deve ser positivo. Recebido: {bandwidth}.")

        # Obtém o GeoDataFrame de entrada via helper da classe base
        gdf = self.get_first_gdf(inputs)

        # Filtra geometrias válidas
        valid_gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
        if valid_gdf.empty:
            raise ValueError(
                "Nenhuma geometria válida encontrada para gerar heatmap."
            )

        n_dropped = len(gdf) - len(valid_gdf)
        if n_dropped > 0:
            logger.warning(
                f"{n_dropped} feições com geometria nula/vazia foram ignoradas."
            )

        logger.info(
            f"Gerando heatmap: {len(valid_gdf)} feições, "
            f"resolution={resolution}, bandwidth={bandwidth}."
        )

        source_crs = valid_gdf.crs

        def _heatmap(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            # Extrai coordenadas dos centroides
            centroids = df.geometry.centroid
            cx = centroids.x.values.astype(np.float64)
            cy = centroids.y.values.astype(np.float64)

            # Calcula bounding box
            xmin, xmax = cx.min(), cx.max()
            ymin, ymax = cy.min(), cy.max()

            x_range = xmax - xmin
            y_range = ymax - ymin

            # Evita bbox degenerada (todos os pontos iguais)
            if x_range == 0:
                x_range = 1.0
                xmin -= 0.5
                xmax += 0.5
            if y_range == 0:
                y_range = 1.0
                ymin -= 0.5
                ymax += 0.5

            # Cria centros das células do grid
            xs = np.linspace(xmin, xmax, resolution)
            ys = np.linspace(ymin, ymax, resolution)
            xx, yy = np.meshgrid(xs, ys)
            grid_points = np.vstack([xx.ravel(), yy.ravel()])  # shape (2, N)

            # Avalia o KDE gaussiano nos centros do grid
            bw_h = bandwidth * 0.5 * (
                np.std(cx) + np.std(cy)
            )
            if bw_h == 0:
                bw_h = bandwidth * 0.5 * (x_range + y_range) / 2.0
            if bw_h == 0:
                bw_h = 1.0

            data = np.vstack([cx, cy])  # (2, P)
            diff = (
                grid_points[:, :, np.newaxis] - data[:, np.newaxis, :]
            )  # (2, G, P)
            sq_dist = np.sum(diff ** 2, axis=0)  # (G, P)
            kernels = np.exp(-0.5 * sq_dist / (bw_h ** 2))  # (G, P)
            density_values = kernels.sum(axis=1)  # (G,)

            # Normaliza para [0, 1]
            d_max = density_values.max()
            if d_max > 0:
                density_values = density_values / d_max

            # Constrói GeoDataFrame de células do grid
            cell_width = x_range / resolution
            cell_height = y_range / resolution

            half_w = cell_width / 2.0
            half_h = cell_height / 2.0

            gx = grid_points[0]  # (G,)
            gy = grid_points[1]  # (G,)

            # PERF: shapely.box vetorizado sobre os arrays da grade — evita
            # resolution² chamadas box() em loop Python.
            polygons = shapely.box(gx - half_w, gy - half_h, gx + half_w, gy + half_h)

            result = gpd.GeoDataFrame(
                {'density': density_values},
                geometry=polygons,
                crs=source_crs
            )
            return result

        try:
            result = await asyncio.to_thread(_heatmap, valid_gdf)
        except Exception as e:
            logger.error(f"Erro ao gerar heatmap: {e}")
            raise RuntimeError(f"Erro na geração do heatmap: {e}")

        logger.info(
            f"Heatmap finalizado. Grid {resolution}×{resolution} "
            f"({len(result)} células)."
        )
        return {"output": result}
