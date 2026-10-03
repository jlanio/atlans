import asyncio
import geopandas as gpd
import pandas as pd
from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class AggregateNode(BaseNode):
    """
    Spatial node that aggregates a list of GeoDataFrames (coming from PartitionNode
    or LoopNode) into a single GeoDataFrame.

    Supported operations:
      - 'concat':        concatenates all GDFs with pd.concat and reset_index
      - 'union':         applies unary_union to the geometry column, returns a 1-row GDF
      - 'intersect_all': iterative intersection of all GDFs

    Properties:
      - operation: aggregation operation ('concat', 'union', 'intersect_all')
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Aggregate',
            'alias': 'Agregação Espacial',
            'description': (
                'Agrega uma lista de GeoDataFrames em um único GeoDataFrame. '
                "Operações: 'concat' (concatenar), 'union' (união geométrica), "
                "'intersect_all' (interseção iterativa)."
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'operation',
                    'label': 'Operação de agregação',
                    'type': 'select',
                    'default': 'concat',
                    'description': 'Como agregar os GeoDataFrames de entrada.',
                    'options': [
                        {'value': 'concat',        'label': 'Concatenar (empilhar)'},
                        {'value': 'union',         'label': 'União geométrica'},
                        {'value': 'intersect_all', 'label': 'Interseção de todos'},
                    ],
                }
            ],
            'inputs': [{'name': 'output', 'type': 'geodataframe', 'description': 'Lista de GeoDataFrames (ex: saida do Partition ou Loop).'}],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame resultante da agregação das camadas de entrada'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Validation and parameter extraction
        # -------------------------------------------------------
        self.validate()

        # operation already validated against the options by self.validate().
        operation = self.parameters.get('operation', 'concat')

        # -------------------------------------------------------
        # 2) Gets the list of GeoDataFrames from the inputs
        # -------------------------------------------------------
        # Supports both a list value directly and multiple GDFs in the inputs
        gdf_list_raw = None
        for v in inputs.values():
            if isinstance(v, list):
                gdf_list_raw = v
                break

        if gdf_list_raw is None:
            # Fallback: uses all GDFs found in the inputs as the list
            gdf_list_raw = [v for v in inputs.values() if isinstance(v, gpd.GeoDataFrame)]

        if not gdf_list_raw:
            raise ValueError("Nenhuma lista de GeoDataFrames encontrada nos inputs.")

        # Keeps only valid, non-empty GeoDataFrames
        valid_gdfs: List[gpd.GeoDataFrame] = []
        for idx, item in enumerate(gdf_list_raw):
            if not isinstance(item, gpd.GeoDataFrame):
                logger.warning(
                    f"AggregateNode: item #{idx} na lista não é um GeoDataFrame "
                    f"(tipo: {type(item).__name__}). Ignorando."
                )
                continue
            if item.empty:
                logger.warning(f"AggregateNode: GeoDataFrame #{idx} está vazio. Ignorando.")
                continue
            valid_gdfs.append(item)

        if not valid_gdfs:
            logger.warning(
                "AggregateNode: nenhum GeoDataFrame válido encontrado nos inputs."
            )
            return {"output": gpd.GeoDataFrame()}

        logger.info(
            f"AggregateNode: agregando {len(valid_gdfs)} GeoDataFrames "
            f"com operação '{operation}'."
        )

        # -------------------------------------------------------
        # 3) Runs the aggregation operation in a separate thread
        # -------------------------------------------------------
        if operation == 'concat':
            result = await asyncio.to_thread(self._concat, valid_gdfs)

        elif operation == 'union':
            result = await asyncio.to_thread(self._union, valid_gdfs)

        elif operation == 'intersect_all':
            result = await asyncio.to_thread(self._intersect_all, valid_gdfs)

        logger.info(
            f"AggregateNode: agregação '{operation}' concluída. "
            f"Resultado: {len(result)} feições."
        )

        return {"output": result}

    # -------------------------------------------------------
    # Aggregation methods (synchronous, for use in a thread)
    # -------------------------------------------------------

    @staticmethod
    def _concat(gdfs: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Concatenates all GeoDataFrames and resets the index."""
        try:
            result = pd.concat(gdfs, ignore_index=True)
            result = gpd.GeoDataFrame(result, geometry=result.geometry.name)
            # Preserva o CRS do primeiro GDF
            if gdfs[0].crs is not None:
                result = result.set_crs(gdfs[0].crs)
            return result.reset_index(drop=True)
        except Exception as e:
            raise RuntimeError(f"Erro ao concatenar GeoDataFrames: {e}") from e

    @staticmethod
    def _union(gdfs: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Applies unary_union to all GDFs and returns a single-row GDF."""
        try:
            # Concatenates first to get all geometries
            combined = pd.concat(gdfs, ignore_index=True)
            combined_gdf = gpd.GeoDataFrame(combined, geometry=combined.geometry.name)
            if gdfs[0].crs is not None:
                combined_gdf = combined_gdf.set_crs(gdfs[0].crs)

            # Aplica unary_union
            union_geom = combined_gdf.geometry.union_all()

            # Builds a one-row GDF with the resulting geometry
            result = gpd.GeoDataFrame(
                [{'geometry': union_geom}],
                geometry='geometry',
                crs=gdfs[0].crs
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Erro ao calcular union de GeoDataFrames: {e}") from e

    @staticmethod
    def _intersect_all(gdfs: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Computes the iterative intersection of all GeoDataFrames."""
        try:
            if len(gdfs) == 1:
                return gdfs[0].copy()

            result = gdfs[0].copy()
            crs = gdfs[0].crs

            for i, next_gdf in enumerate(gdfs[1:], start=1):
                # Aligns the CRS if needed
                if next_gdf.crs is not None and crs is not None and next_gdf.crs != crs:
                    next_gdf = next_gdf.to_crs(crs)

                try:
                    result = gpd.overlay(result, next_gdf, how='intersection')
                except Exception as e:
                    raise RuntimeError(
                        f"Erro ao calcular interseção com GeoDataFrame #{i}: {e}"
                    ) from e

                if result.empty:
                    logger.warning(
                        f"AggregateNode (intersect_all): resultado vazio após "
                        f"interseção com GeoDataFrame #{i}."
                    )
                    break

            return result.reset_index(drop=True)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Erro na operação intersect_all: {e}") from e
