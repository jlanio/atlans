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
    """Tenta converter raw_cmp para o mesmo tipo de value."""
    try:
        if isinstance(value, (int, float)):
            return float(raw_cmp)
    except (TypeError, ValueError):
        pass  # Conversão de tipo falhou — mantém valor original
    return raw_cmp


@register_node
class Switch(BaseNode):
    """
    Roteia registros para N saídas diferentes com base em regras de condição.

    Cada regra é avaliada em ordem; o registro vai para a primeira saída
    cuja condição for verdadeira. Registros que não casam com nenhuma regra
    vão para a saída de fallback (output_0 por padrão).

    Parâmetros:
      - rules (list): lista de objetos no formato:
            [
              {"field": "status", "operator": "==", "value": "ativo", "output": "output_1"},
              {"field": "area",   "operator": ">",  "value": "1000",  "output": "output_2"}
            ]
        Operadores suportados: ==, !=, >, <, >=, <=, contains, starts, ends
      - fallback_output (string): chave de saída para registros sem match (default: "output_0")

    Outputs dinâmicos — cada registro cai em exatamente uma das saídas.
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
                    # O editor dedicado (switch-rules-field) oferece os nomes
                    # vistos na última execução no campo de cada regra.
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

        # Aceita GeoDataFrame ou lista de dicts
        data = next(iter(inputs.values()), None)
        if data is None:
            raise ValueError("Switch: nenhum dado nos inputs.")

        is_gdf = isinstance(data, gpd.GeoDataFrame)
        geo_col_name = data.geometry.name if is_gdf else "geometry"
        records = data.to_dict(orient="records") if is_gdf else list(data)

        # Cada output_key → lista de registros
        buckets: Dict[str, list] = {}

        for record in records:
            props = record.get("properties", record) if isinstance(record, dict) else {}
            matched_output = fallback

            for rule in rules:
                if self._eval_rule(props, rule):
                    matched_output = rule.get("output", fallback)
                    break

            buckets.setdefault(matched_output, []).append(record)

        # Emite TODAS as saídas possíveis (fallback + saídas das regras), mesmo
        # as que não receberam registro neste lote. Sem isso, uma saída vazia
        # sumia do dict e uma aresta from_key='output_N' para ela não resolvia —
        # sob o resolvedor antigo cruzava dados de OUTRO balde (F5). Com o balde
        # vazio presente, a aresta resolve para um container vazio, correto.
        todas_saidas = {fallback}
        for rule in rules:
            saida = rule.get("output")
            if saida:
                todas_saidas.add(saida)
        todas_saidas |= set(buckets.keys())

        if is_gdf:
            import pandas as pd

            def _to_gdf(rows: list):
                # gpd.GeoDataFrame.from_records é o from_records do pandas (sem
                # kwarg geometry) e estoura em geopandas >= 1.0. Constrói via
                # DataFrame + geometria explícita, que funciona em toda versão.
                if not rows:
                    return gpd.GeoDataFrame()
                return gpd.GeoDataFrame(
                    pd.DataFrame.from_records(rows), geometry=geo_col_name, crs=data.crs
                )

            result = {key: _to_gdf(buckets.get(key, [])) for key in todas_saidas}
        else:
            result = {key: buckets.get(key, []) for key in todas_saidas}

        logger.info(
            "Switch: %d registros distribuídos em %d saídas (%d com dados).",
            len(records), len(result), sum(1 for v in buckets.values() if v),
        )
        return result
