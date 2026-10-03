import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class DissolveNode(BaseNode):
    """
    Dissolves the features of a GeoDataFrame grouping by a column,
    merging each group's geometries (union) and aggregating attributes.
    If byColumn is empty, dissolves all features into a single one.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'Dissolve',
            'alias': 'Dissolve',
            'description': (
                'Dissolve feições de um GeoDataFrame agrupando por uma coluna (byColumn). '
                'As geometrias do grupo são unidas e os atributos são agregados pela função '
                'aggFunc. Deixe byColumn vazio para dissolver todas as feições em uma única.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'byColumn',
                    'label': 'Agrupar por',
                    'type': 'string',
                    'default': '',
                    # The editor offers the names seen in the previous node's last
                    # run — the same hint as AttributeFilter.
                    'suggest_columns': '*',
                    'description': (
                        'Nome da coluna usada para agrupar as feições. '
                        'Deixe vazio para dissolver tudo em uma única feição.'
                    )
                },
                {
                    'name': 'aggFunc',
                    'label': 'Função de agregação',
                    'type': 'select',
                    'default': 'first',
                    'description': "Como agregar os atributos não-geométricos de cada grupo.",
                    'options': [
                        {'value': 'first',  'label': 'Primeiro'},
                        {'value': 'last',   'label': 'Último'},
                        {'value': 'sum',    'label': 'Soma'},
                        {'value': 'mean',   'label': 'Média'},
                        {'value': 'median', 'label': 'Mediana'},
                        {'value': 'min',    'label': 'Mínimo'},
                        {'value': 'max',    'label': 'Máximo'},
                        {'value': 'count',  'label': 'Contagem'},
                    ],
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com as feições dissolvidas e atributos agregados'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        by_column = self.parameters['byColumn'].strip()
        # aggFunc already validated against the options by self.validate().
        agg_func = self.parameters['aggFunc'].strip().lower()

        # Gets the input GeoDataFrame via the base class helper
        gdf = self.get_first_gdf(inputs)

        # Validates that byColumn exists when not empty
        if by_column and by_column not in gdf.columns:
            raise ValueError(
                f"Coluna '{by_column}' não encontrada no GeoDataFrame. "
                f"Colunas disponíveis: {list(gdf.columns)}."
            )

        dissolve_by = by_column if by_column else None

        # An f-string with a backslash is not allowed in Python < 3.12; use a helper variable
        col_info = f"por coluna '{by_column}'" if dissolve_by else "(dissolve total)"
        logger.info(
            f"Dissolvendo {len(gdf)} feições {col_info} com aggFunc='{agg_func}'."
        )

        def _dissolve(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            result = df.dissolve(by=dissolve_by, aggfunc=agg_func)
            result = result.reset_index()
            return result

        try:
            result = await asyncio.to_thread(_dissolve, gdf)
        except Exception as e:
            logger.error(f"Erro ao dissolver feições: {e}")
            raise RuntimeError(f"Erro no dissolve: {e}")

        logger.info(
            f"Dissolve finalizado. {len(result)} feições resultantes "
            f"(de {len(gdf)} originais)."
        )
        return {"output": result}
