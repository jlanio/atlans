from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class Sort(BaseNode):
    """
    Ordena os registros de um GeoDataFrame por um ou mais campos.

    Parâmetros:
      - sort_by (list): lista de objetos no formato:
            [
              {"field": "nome_coluna", "direction": "asc"},
              {"field": "area",        "direction": "desc"}
            ]
        direction: "asc" (crescente, padrão) ou "desc" (decrescente).

    Exemplo:
        sort_by = [{"field": "area", "direction": "desc"}, {"field": "nome", "direction": "asc"}]
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "Sort",
            "alias": "Ordenar",
            "description": "Ordena os registros do GeoDataFrame por um ou mais campos.",
            "type": "action",
            "properties": [
                {
                    "name": "sort_by",
                    "label": "Ordenar Por",
                    "type": "object",
                    "default": [],
                    "description": (
                        'Lista de campos para ordenação. '
                        'Ex: [{"field": "area", "direction": "desc"}, {"field": "nome", "direction": "asc"}]'
                    ),
                    # O editor dedicado (sort-by-field) oferece os nomes vistos
                    # na última execução no campo de cada critério.
                    "suggest_columns": "*",
                }
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "GeoDataFrame ordenado pelos campos especificados"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        import asyncio

        gdf = self.get_first_gdf(inputs)

        sort_by: List[dict] = self.parameters.get("sort_by", [])
        if not isinstance(sort_by, list) or not sort_by:
            logger.warning("Sort: parâmetro 'sort_by' vazio ou inválido — retornando sem ordenar.")
            return {"output": gdf}

        # Separa colunas e direções
        columns = []
        ascending_flags = []

        for entry in sort_by:
            field = entry.get("field", "")
            direction = entry.get("direction", "asc").lower()

            if not field:
                logger.warning("Sort: entrada sem 'field' — ignorada.")
                continue

            if field not in gdf.columns:
                logger.warning("Sort: campo '%s' não existe no GeoDataFrame — ignorado.", field)
                continue

            columns.append(field)
            ascending_flags.append(direction != "desc")

        if not columns:
            logger.warning("Sort: nenhuma coluna válida encontrada para ordenar.")
            return {"output": gdf}

        sorted_gdf = await asyncio.to_thread(
            lambda: gdf.sort_values(by=columns, ascending=ascending_flags, ignore_index=True)
        )

        logger.info(
            "Sort: %d registros ordenados por %s.",
            len(sorted_gdf),
            ", ".join(f"{c} {'↑' if a else '↓'}" for c, a in zip(columns, ascending_flags)),
        )
        return {"output": sorted_gdf}
