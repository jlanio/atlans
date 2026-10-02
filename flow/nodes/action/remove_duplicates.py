from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.parameter_validation import colunas_pedidas

logger = get_logger(__name__)


@register_node
class RemoveDuplicates(BaseNode):
    """
    Remove registros duplicados de um GeoDataFrame com base em campos-chave.

    Se nenhum campo for especificado, considera todas as colunas (exceto geometry)
    para determinar unicidade.

    Parâmetros:
      - fields (list): lista de nomes de campos que definem unicidade.
            Ex: ["id_municipio"] ou ["nome", "estado"]
            Se vazio, usa todas as colunas não-geométricas.
      - keep (string): qual registro manter em caso de duplicata:
            "first" (padrão) — mantém a primeira ocorrência
            "last"           — mantém a última ocorrência
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
                    # Nó de entrada única: '*' e a porta dariam no mesmo.
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

        # Campo de fichas: aceita lista, JSON-string (o que a tela grava) e o
        # texto com vírgulas das definitions antigas.
        fields: List[str] = colunas_pedidas(self.parameters.get("fields", []))

        # keep já validado contra as options pelo self.validate().
        keep = self.parameters.get("keep", "first")

        # Determina colunas de subset
        geo_col = gdf.geometry.name
        if fields:
            # Filtra apenas colunas que existem no GDF
            subset = [f for f in fields if f in gdf.columns]
            if not subset:
                logger.warning(
                    "RemoveDuplicates: nenhuma coluna de '%s' existe no GeoDataFrame. "
                    "Usando todas as colunas não-geométricas.",
                    fields,
                )
                subset = None
        else:
            subset = None  # pandas usa todas as colunas

        original_count = len(gdf)

        # Executa drop_duplicates em thread (operação blocking)
        # Nao usa ignore_index para preservar indices originais e poder
        # identificar registros removidos por comparacao de indice.
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
