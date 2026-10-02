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
    Nó espacial que agrega uma lista de GeoDataFrames (proveniente de PartitionNode
    ou LoopNode) em um único GeoDataFrame.

    Operações suportadas:
      - 'concat':        concatena todos os GDFs com pd.concat e reset_index
      - 'union':         aplica unary_union na coluna de geometria, retorna GDF de 1 linha
      - 'intersect_all': interseção iterativa de todos os GDFs

    Propriedades:
      - operation: operação de agregação ('concat', 'union', 'intersect_all')
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
        # 1) Validação e extração de parâmetros
        # -------------------------------------------------------
        self.validate()

        # operation já validado contra as options pelo self.validate().
        operation = self.parameters.get('operation', 'concat')

        # -------------------------------------------------------
        # 2) Obtém a lista de GeoDataFrames dos inputs
        # -------------------------------------------------------
        # Suporta tanto um valor de lista diretamente quanto múltiplos GDFs nos inputs
        gdf_list_raw = None
        for v in inputs.values():
            if isinstance(v, list):
                gdf_list_raw = v
                break

        if gdf_list_raw is None:
            # Fallback: usa todos os GDFs encontrados nos inputs como lista
            gdf_list_raw = [v for v in inputs.values() if isinstance(v, gpd.GeoDataFrame)]

        if not gdf_list_raw:
            raise ValueError("Nenhuma lista de GeoDataFrames encontrada nos inputs.")

        # Filtra apenas GeoDataFrames válidos e não-vazios
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
        # 3) Executa a operação de agregação em thread separada
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
    # Métodos de agregação (síncronos, para uso em thread)
    # -------------------------------------------------------

    @staticmethod
    def _concat(gdfs: List[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """Concatena todos os GeoDataFrames e reseta o índice."""
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
        """Aplica unary_union em todos os GDFs e retorna um GDF de linha única."""
        try:
            # Concatena primeiro para obter todas as geometrias
            combined = pd.concat(gdfs, ignore_index=True)
            combined_gdf = gpd.GeoDataFrame(combined, geometry=combined.geometry.name)
            if gdfs[0].crs is not None:
                combined_gdf = combined_gdf.set_crs(gdfs[0].crs)

            # Aplica unary_union
            union_geom = combined_gdf.geometry.union_all()

            # Constrói GDF de uma linha com a geometria resultante
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
        """Calcula a interseção iterativa de todos os GeoDataFrames."""
        try:
            if len(gdfs) == 1:
                return gdfs[0].copy()

            result = gdfs[0].copy()
            crs = gdfs[0].crs

            for i, next_gdf in enumerate(gdfs[1:], start=1):
                # Alinha CRS se necessário
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
