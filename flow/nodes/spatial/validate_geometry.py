import asyncio
import geopandas as gpd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class ValidateGeometryNode(BaseNode):
    """
    Valida as geometrias de um GeoDataFrame e, dependendo do modo,
    corrige, remove ou apenas reporta as geometrias inválidas.

    Modos:
      - fix:    Tenta corrigir geometrias inválidas aplicando buffer(0).
      - remove: Remove as linhas com geometrias inválidas.
      - report: Não modifica o GeoDataFrame; retorna um dict de estatísticas.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'ValidateGeometry',
            'alias': 'Validate Geometry',
            'description': (
                'Valida geometrias de um GeoDataFrame. No modo "fix" tenta corrigir '
                'geometrias inválidas via buffer(0). No modo "remove" descarta feições '
                'inválidas. No modo "report" retorna apenas estatísticas sem modificar os dados.'
            ),
            'type': 'spatial',
            'properties': [
                {
                    'name': 'mode',
                    'label': 'Modo de validação',
                    'type': 'select',
                    'default': 'fix',
                    'description': 'O que fazer com as geometrias inválidas.',
                    'options': [
                        {'value': 'fix',    'label': 'Corrigir (make_valid)'},
                        {'value': 'remove', 'label': 'Descartar inválidas'},
                        {'value': 'report', 'label': 'Apenas reportar estatísticas'},
                    ],
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com geometrias validadas, corrigidas ou filtradas'},
                {'name': 'stats', 'type': 'object', 'description': 'Estatísticas da validação (total, valid, invalid, null_geometry, invalid_ratio)'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # mode já validado contra as options pelo self.validate().
        mode = self.parameters['mode'].strip().lower()

        # Obtém o GeoDataFrame de entrada via helper da classe base
        gdf = self.get_first_gdf(inputs)

        logger.info(
            f"ValidateGeometry: modo='{mode}', {len(gdf)} feições."
        )

        def _validate(df: gpd.GeoDataFrame) -> Dict[str, Any]:
            valid_mask = df.geometry.notnull() & df.geometry.is_valid
            invalid_mask = ~valid_mask
            null_mask = df.geometry.isnull()

            total = len(df)
            n_valid = int(valid_mask.sum())
            n_invalid = int(invalid_mask.sum())
            n_null = int(null_mask.sum())

            stats = {
                'total': total,
                'valid': n_valid,
                'invalid': n_invalid,
                'null_geometry': n_null,
                'invalid_ratio': round(n_invalid / total, 4) if total > 0 else 0.0
            }

            if mode == 'report':
                return {'output': df.copy(), 'stats': stats}

            if mode == 'fix':
                result = df.copy()
                if n_invalid > 0:
                    logger.info(
                        f"Corrigindo {n_invalid} geometrias inválidas via buffer(0)."
                    )
                    # Aplica buffer(0) apenas em geometrias inválidas (não nulas)
                    fixable = invalid_mask & df.geometry.notnull()
                    result.loc[fixable, result.geometry.name] = (
                        result.loc[fixable, result.geometry.name].buffer(0)
                    )
                    # Após correção, verifica se ainda há inválidas
                    still_invalid = int((~result.geometry.is_valid).sum())
                    if still_invalid > 0:
                        logger.warning(
                            f"{still_invalid} geometrias permanecem inválidas após buffer(0). "
                            "Considere usar o modo 'remove'."
                        )
                return {"output": result, "stats": stats}

            if mode == 'remove':
                result = df[valid_mask].copy()
                removed = total - len(result)
                if removed > 0:
                    logger.info(
                        f"{removed} feições inválidas/nulas removidas. "
                        f"{len(result)} feições mantidas."
                    )
                return {"output": result, "stats": stats}

            # Não deve chegar aqui por causa da validação prévia
            raise RuntimeError(f"Modo inesperado: '{mode}'.")

        try:
            result_dict = await asyncio.to_thread(_validate, gdf)
        except Exception as e:
            logger.error(f"Erro ao validar geometrias: {e}")
            raise RuntimeError(f"Erro na validação de geometrias: {e}")

        logger.info("ValidateGeometry finalizado.")
        return result_dict
