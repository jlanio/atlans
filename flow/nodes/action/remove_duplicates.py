from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.parameter_validation import requested_columns

logger = get_logger(__name__)


@register_node
class RemoveDuplicates(BaseNode):
    """
    Removes duplicate records from a GeoDataFrame based on key fields.

    If no field is specified, considers all columns (except geometry)
    to determine uniqueness.

    Args:
      - fields (list): list of field names that define uniqueness.
            E.g.: ["id_municipio"] or ["nome", "estado"]
            If empty, uses all non-geometry columns.
      - keep (string): which record to keep in case of a duplicate:
            "first" (default) — keeps the first occurrence
            "last"            — keeps the last occurrence
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "RemoveDuplicates",
            "alias": "Remover Duplicatas",
            "description": "Remove registros duplicados do GeoDataFrame com base em campos-chave.",
            "type": "action",
            "properties": [
                {
                    "name": "fields",
                    "label": "Campos-chave",
                    "type": "chips",
                    # Single-input node: '*' and the port would amount to the same thing.
                    "suggest_columns": "*",
                    "default": [],
                    "description": (
                        'Campos que definem unicidade. '
                        'Se vazio, usa todas as colunas não-geométricas. '
                        'Colar vários nomes separados por vírgula adiciona todos.'
                    ),
                },
                {
                    "name": "keep",
                    "label": "Registro a Manter",
                    "type": "select",
                    "default": "first",
                    "description": "Qual ocorrência manter em caso de duplicata.",
                    "options": [
                        {"value": "first", "label": "Primeira"},
                        {"value": "last",  "label": "Última"},
                    ],
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "GeoDataFrame sem registros duplicados", "port": True},
                {"name": "removed", "type": "geodataframe", "description": "GeoDataFrame com os registros que foram removidos", "port": True},
                {"name": "removed_count", "type": "number", "description": "Quantidade de registros removidos", "port": True},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        import asyncio

        gdf = self.get_first_gdf(inputs)

        # Chips field: accepts a list, a JSON string (what the screen writes) and the
        # comma-separated text of old definitions.
        fields: List[str] = requested_columns(self.parameters.get("fields", []))

        # keep already validated against the options by self.validate().
        keep = self.parameters.get("keep", "first")

        # Determines subset columns
        geo_col = gdf.geometry.name
        if fields:
            # Filters only columns that exist in the GDF
            subset = [f for f in fields if f in gdf.columns]
            if not subset:
                logger.warning(
                    "RemoveDuplicates: nenhuma coluna de '%s' existe no GeoDataFrame. "
                    "Usando todas as colunas não-geométricas.",
                    fields,
                )
                subset = None
        else:
            subset = None  # pandas uses all columns

        original_count = len(gdf)

        # Runs drop_duplicates in a thread (blocking operation)
        # Doesn't use ignore_index, to preserve the original indexes and be able
        # to identify removed records by index comparison.
        if subset:
            deduped = await asyncio.to_thread(
                lambda: gdf.drop_duplicates(subset=subset, keep=keep)
            )
        else:
            non_geo_cols = [c for c in gdf.columns if c != geo_col]
            deduped = await asyncio.to_thread(
                lambda: gdf.drop_duplicates(subset=non_geo_cols or None, keep=keep)
            )

        removed_count = original_count - len(deduped)
        removed_gdf = gdf[~gdf.index.isin(deduped.index)] if removed_count > 0 else gdf.iloc[0:0]
        deduped = deduped.reset_index(drop=True)

        logger.info(
            "RemoveDuplicates: %d → %d registros (%d removidos).",
            original_count, len(deduped), removed_count,
        )

        return {
            "output": deduped,
            "removed": removed_gdf,
            "removed_count": removed_count,
        }
