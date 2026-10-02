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
    Dissolve feições de um GeoDataFrame agrupando por uma coluna,
    mesclando as geometrias do grupo (union) e agregando atributos.
    Se byColumn estiver vazio, dissolve todas as feições em uma só.
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
                    # O editor oferece os nomes vistos na última execução do nó
                    # anterior — mesma dica do AttributeFilter.
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
        # aggFunc já validado contra as options pelo self.validate().
        agg_func = self.parameters['aggFunc'].strip().lower()

        # Obtém o GeoDataFrame de entrada via helper da classe base
        gdf = self.get_first_gdf(inputs)

        # Valida se byColumn existe quando não vazio
        if by_column and by_column not in gdf.columns:
            raise ValueError(
                f"Coluna '{by_column}' não encontrada no GeoDataFrame. "
                f"Colunas disponíveis: {list(gdf.columns)}."
            )

        dissolve_by = by_column if by_column else None

        # f-string com backslash não é permitido no Python < 3.12; usar variável auxiliar
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
