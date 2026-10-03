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
    Spatial node that splits a GeoDataFrame into spatial partitions (grid tiles)
    for map-reduce processing. Computes the total bbox, creates an NxN grid and
    clips the GeoDataFrame to each cell, returning only the non-empty partitions.

    Properties:
      - nPartitions:  number of divisions (N for an NxN grid, e.g. 2 = 4 tiles, 3 = 9 tiles)
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
        # 1) Validation and parameter extraction
        # -------------------------------------------------------
        self.validate()

        n_partitions = self.get_param_int('nPartitions')
        if n_partitions <= 0:
            raise ValueError("nPartitions deve ser maior que zero.")

        # Determina o N do grid: ceil(sqrt(nPartitions))
        n = math.ceil(math.sqrt(n_partitions))

        # -------------------------------------------------------
        # 2) Validates and gets the input GeoDataFrame
        # -------------------------------------------------------
        gdf = self.get_first_gdf(inputs)

        require_crs(gdf)

        logger.info(
            f"PartitionNode: dividindo {len(gdf)} feições em grade {n}x{n} "
            f"({n * n} tiles potenciais, nPartitions={n_partitions})."
        )

        # -------------------------------------------------------
        # 3) Creates the spatial partitions (in a separate thread)
        # -------------------------------------------------------
        def _partition(df: gpd.GeoDataFrame, grid_n: int) -> List[gpd.GeoDataFrame]:
            # Computes the total bbox of the GeoDataFrame
            total_bounds = df.total_bounds  # (minx, miny, maxx, maxy)
            minx, miny, maxx, maxy = total_bounds

            # Avoids division by zero if the bbox is degenerate
            if minx == maxx or miny == maxy:
                return [df.copy()]

            # Computes the step of each cell
            x_step = (maxx - minx) / grid_n
            y_step = (maxy - miny) / grid_n

            # Spatial index built ONCE. Before, `df.geometry.intersects(cell)`
            # per cell was an elementwise scan over ALL features — cost
            # O(features × tiles). With the STRtree, each cell queries only the
            # candidates touching its bbox and then refines with intersects. The
            # bbox+refine form is equivalent to the old result and does not depend
            # on the geopandas/shapely version (it does not use the predicate= kwarg).
            sindex = df.sindex

            partitions = []
            for i in range(grid_n):
                for j in range(grid_n):
                    cell_minx = minx + i * x_step
                    cell_maxx = minx + (i + 1) * x_step
                    cell_miny = miny + j * y_step
                    cell_maxy = miny + (j + 1) * y_step

                    # Creates the cell geometry and clips the GDF
                    cell_geom = box(cell_minx, cell_miny, cell_maxx, cell_maxy)
                    try:
                        cand_pos = sindex.query(cell_geom)  # candidates by bbox
                        if len(cand_pos) == 0:
                            continue
                        cand = df.iloc[cand_pos]
                        clipped = cand[cand.geometry.intersects(cell_geom)].copy()
                        clipped = clipped.reset_index(drop=True)
                    except Exception:
                        clipped = gpd.GeoDataFrame(columns=df.columns, crs=df.crs)

                    # Includes only non-empty partitions
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
