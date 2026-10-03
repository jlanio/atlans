import operator
from typing import Any, Dict, List
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_OP_FUNCS = {
    "==":       operator.eq,
    "!=":       operator.ne,
    ">":        operator.gt,
    "<":        operator.lt,
    ">=":       operator.ge,
    "<=":       operator.le,
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "starts":   lambda a, b: str(a).lower().startswith(str(b).lower()),
    "ends":     lambda a, b: str(a).lower().endswith(str(b).lower()),
}


def _cast(value: Any, raw_cmp: str) -> Any:
    """Tries to convert raw_cmp to the same type as value."""
    try:
        if isinstance(value, (int, float)):
            return float(raw_cmp)
    except (TypeError, ValueError):
        pass  # Type conversion failed — keeps the original value
    return raw_cmp


@register_node
class Switch(BaseNode):
    """
    Routes records to N different outputs based on condition rules.

    Each rule is evaluated in order; the record goes to the first output
    whose condition is true. Records that match no rule
    go to the fallback output (output_0 by default).

    Args:
      - rules (list): list of objects in the format:
            [
              {"field": "status", "operator": "==", "value": "ativo", "output": "output_1"},
              {"field": "area",   "operator": ">",  "value": "1000",  "output": "output_2"}
            ]
        Supported operators: ==, !=, >, <, >=, <=, contains, starts, ends
      - fallback_output (string): output key for records with no match (default: "output_0")

    Dynamic outputs — each record lands in exactly one of the outputs.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "Switch",
            "alias": "Switch",
            "description": "Roteia registros para N saídas com base em condições. "
                           "Semelhante ao if/elif/else, mas com múltiplas saídas nomeadas.",
            "type": "control",
            "properties": [
                {
                    "name": "rules",
                    "label": "Regras",
                    "type": "object",
                    "default": [],
                    "description": (
                        'Lista de regras. Cada regra: {"field":"coluna","operator":"==","value":"x","output":"output_1"}. '
                        "Operadores: ==, !=, >, <, >=, <=, contains, starts, ends."
                    ),
                    # The dedicated editor (switch-rules-field) offers the names
                    # seen in the last run in each rule's field.
                    "suggest_columns": "*",
                },
                {
                    "name": "fallback_output",
                    "label": "Saída padrão",
                    "type": "string",
                    "default": "output_0",
                    "description": "Saída para registros que não casam com nenhuma regra (default: output_0).",
                },
            ],
            "dynamic_output": True,
            "outputs": [
                {"name": "output_0", "type": "any", "description": "Registros que caíram na saída padrão / fallback"},
                {"name": "output_1", "type": "any", "description": "Registros que casaram com a regra da saída 1"},
                {"name": "output_2", "type": "any", "description": "Registros que casaram com a regra da saída 2"},
                {"name": "output_3", "type": "any", "description": "Registros que casaram com a regra da saída 3"},
            ],
        }

    def _eval_rule(self, row: dict, rule: dict) -> bool:
        field = rule.get("field", "")
        op_key = rule.get("operator", "==")
        raw_cmp = rule.get("value", "")

        value = row.get(field)
        cmp_value = _cast(value, str(raw_cmp))

        op_func = _OP_FUNCS.get(op_key)
        if op_func is None:
            logger.warning("Switch: operador desconhecido '%s' — ignorando regra.", op_key)
            return False

        try:
            return bool(op_func(value, cmp_value))
        except Exception as exc:
            logger.debug("Falha ao avaliar regra de switch: %s", exc)
            return False

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        import geopandas as gpd

        rules: List[dict] = self.parameters.get("rules", [])
        if not isinstance(rules, list):
            rules = []

        fallback = self.parameters.get("fallback_output", "output_0")

        # Accepts a GeoDataFrame or a list of dicts
        data = next(iter(inputs.values()), None)
        if data is None:
            raise ValueError("Switch: nenhum dado nos inputs.")

        is_gdf = isinstance(data, gpd.GeoDataFrame)
        geo_col_name = data.geometry.name if is_gdf else "geometry"
        records = data.to_dict(orient="records") if is_gdf else list(data)

        # Each output_key → list of records
        buckets: Dict[str, list] = {}

        for record in records:
            props = record.get("properties", record) if isinstance(record, dict) else {}
            matched_output = fallback

            for rule in rules:
                if self._eval_rule(props, rule):
                    matched_output = rule.get("output", fallback)
                    break

            buckets.setdefault(matched_output, []).append(record)

        # Emits ALL possible outputs (fallback + the rules' outputs), even
        # those that received no record in this batch. Without this, an empty output
        # vanished from the dict and an edge from_key='output_N' to it didn't resolve —
        # under the old resolver it crossed in data from ANOTHER bucket (F5). With the
        # empty bucket present, the edge resolves to an empty container, which is correct.
        all_outputs = {fallback}
        for rule in rules:
            saida = rule.get("output")
            if saida:
                all_outputs.add(saida)
        all_outputs |= set(buckets.keys())

        if is_gdf:
            import pandas as pd

            def _to_gdf(rows: list):
                # gpd.GeoDataFrame.from_records is pandas' from_records (no
                # geometry kwarg) and blows up on geopandas >= 1.0. Builds via
                # DataFrame + explicit geometry, which works on every version.
                if not rows:
                    return gpd.GeoDataFrame()
                return gpd.GeoDataFrame(
                    pd.DataFrame.from_records(rows), geometry=geo_col_name, crs=data.crs
                )

            result = {key: _to_gdf(buckets.get(key, [])) for key in all_outputs}
        else:
            result = {key: buckets.get(key, []) for key in all_outputs}

        logger.info(
            "Switch: %d registros distribuídos em %d saídas (%d com dados).",
            len(records), len(result), sum(1 for v in buckets.values() if v),
        )
        return result
