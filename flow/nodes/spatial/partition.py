import asyncio
import math
import geopandas as gpd
from typing import Any, Dict, List
from shapely.geometry import box
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import require_crs
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class PartitionNode(BaseNode):
    """
    Nó espacial que divide um GeoDataFrame em partições espaciais (tiles de grade)
    para processamento map-reduce. Computa a bbox total, cria uma grade NxN e
    recorta o GeoDataFrame em cada célula, retornando apenas as partições não-vazias.

    Propriedades:
      - nPartitions:  número de divisões (N para NxN grid, ex: 2 = 4 tiles, 3 = 9 tiles)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Partition',
            'alias': 'Particionamento Espacial',
            'description': (
                'Divide um GeoDataFrame em partições espaciais de grade NxN '
                'para processamento map-reduce. Retorna apenas partições não-vazias.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'nPartitions',
                    'label': 'Nº de partições',
                    'type': 'integer',
                    'default': 4,
                    'description': (
                        'Número de divisões N para criar uma grade NxN. '
                        'Ex: 2 cria 4 tiles (2x2), 3 cria 9 tiles (3x3). '
                        'O valor N é extraído como ceil(sqrt(nPartitions)).'
                    )
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'list', 'description': 'Lista de GeoDataFrames (um por tile nao-vazio)'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Validação e extração de parâmetros
        # -------------------------------------------------------
        self.validate()

        n_partitions = self.get_param_int('nPartitions')
        if n_partitions <= 0:
            raise ValueError("nPartitions deve ser maior que zero.")

        # Determina o N do grid: ceil(sqrt(nPartitions))
        n = math.ceil(math.sqrt(n_partitions))

        # -------------------------------------------------------
        # 2) Valida e obtém o GeoDataFrame de entrada
        # -------------------------------------------------------
        gdf = self.get_first_gdf(inputs)

        require_crs(gdf)

        logger.info(
            f"PartitionNode: dividindo {len(gdf)} feições em grade {n}x{n} "
            f"({n * n} tiles potenciais, nPartitions={n_partitions})."
        )

        # -------------------------------------------------------
        # 3) Cria partições espaciais (em thread separada)
        # -------------------------------------------------------
        def _partition(df: gpd.GeoDataFrame, grid_n: int) -> List[gpd.GeoDataFrame]:
            # Calcula bbox total do GeoDataFrame
            total_bounds = df.total_bounds  # (minx, miny, maxx, maxy)
            minx, miny, maxx, maxy = total_bounds

            # Evita divisão por zero se bbox for degenerada
            if minx == maxx or miny == maxy:
                return [df.copy()]

            # Calcula passo de cada célula
            x_step = (maxx - minx) / grid_n
            y_step = (maxy - miny) / grid_n

            # Índice espacial construído UMA vez. Antes, `df.geometry.intersects(cell)`
            # por célula era um scan elementwise sobre TODAS as feições — custo
            # O(feições × tiles). Com o STRtree, cada célula consulta só os
            # candidatos que tocam seu bbox e depois refina com intersects. A
            # forma bbox+refino é equivalente ao resultado antigo e independe da
            # versão do geopandas/shapely (não usa o kwarg predicate=).
            sindex = df.sindex

            partitions = []
            for i in range(grid_n):
                for j in range(grid_n):
                    cell_minx = minx + i * x_step
                    cell_maxx = minx + (i + 1) * x_step
                    cell_miny = miny + j * y_step
                    cell_maxy = miny + (j + 1) * y_step

                    # Cria geometria da célula e recorta o GDF
                    cell_geom = box(cell_minx, cell_miny, cell_maxx, cell_maxy)
                    try:
                        cand_pos = sindex.query(cell_geom)  # candidatos por bbox
                        if len(cand_pos) == 0:
                            continue
                        cand = df.iloc[cand_pos]
                        clipped = cand[cand.geometry.intersects(cell_geom)].copy()
                        clipped = clipped.reset_index(drop=True)
                    except Exception:
                        clipped = gpd.GeoDataFrame(columns=df.columns, crs=df.crs)

                    # Inclui apenas partições não-vazias
                    if not clipped.empty:
                        partitions.append(clipped)

            return partitions

        try:
            partitions = await asyncio.to_thread(_partition, gdf, n)
        except Exception as e:
            logger.error(f"Erro ao criar partições espaciais: {e}")
            raise RuntimeError(f"Erro no PartitionNode: {e}") from e

        logger.info(
            f"PartitionNode: {len(gdf)} feições particionadas em "
            f"{len(partitions)} tiles não-vazios (grade {n}x{n})."
        )

        return {"output": partitions}
