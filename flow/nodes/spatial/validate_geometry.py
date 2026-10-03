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
    Validates the geometries of a GeoDataFrame and, depending on the mode,
    fixes, removes or only reports the invalid geometries.

    Modes:
      - fix:    Tries to fix invalid geometries by applying buffer(0).
      - remove: Removes the rows with invalid geometries.
      - report: Does not modify the GeoDataFrame; returns a dict of statistics.
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

        # mode already validated against the options by self.validate().
        mode = self.parameters['mode'].strip().lower()

        # Gets the input GeoDataFrame via the base class helper
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
                    # Applies buffer(0) only to invalid (non-null) geometries
                    fixable = invalid_mask & df.geometry.notnull()
                    result.loc[fixable, result.geometry.name] = (
                        result.loc[fixable, result.geometry.name].buffer(0)
                    )
                    # After fixing, checks whether there are still invalid ones
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

            # Should not get here because of the prior validation
            raise RuntimeError(f"Modo inesperado: '{mode}'.")

        try:
            result_dict = await asyncio.to_thread(_validate, gdf)
        except Exception as e:
            logger.error(f"Erro ao validar geometrias: {e}")
            raise RuntimeError(f"Erro na validação de geometrias: {e}")

        logger.info("ValidateGeometry finalizado.")
        return result_dict
