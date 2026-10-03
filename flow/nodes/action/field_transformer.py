from jinja2 import Undefined
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.jinja_seguro import create_sandbox_environment
from flow.utils.safe_env import safe_env

_JINJA_ENV = create_sandbox_environment(undefined=Undefined)


def _has_expression(v: Any) -> bool:
    """True if the value is a string with Jinja syntax ({{ }} or {% %})."""
    return isinstance(v, str) and ("{{" in v or "{%" in v)


def _coerce_num(rendered: str) -> Any:
    """Converts the rendered text to int/float when possible.

    E.g.: "{{ row.area * 1.1 }}" → float; "ativo" → "ativo".
    """
    try:
        return int(rendered)
    except ValueError:
        pass
    try:
        return float(rendered)
    except ValueError:
        pass
    return rendered


@register_node
class SetFields(BaseNode):
    """
    Adds, updates, removes or renames fields in a GeoDataFrame.

    Parameters:
      - setFields (dict): fields and values to add or overwrite.
        Supports per-field Jinja expressions using {{ row.<coluna> }} and
        workflow context variables (e.g. {{ env.NOME_VAR }}).
        E.g.: {"area_km2": "{{ row.area / 1e6 }}", "status": "ativo"}

      - removeFields (dict): object with a 'fields' key containing the list of columns to remove.
        E.g.: {"fields": ["temp", "flag"]}

      - renameFields (dict): mapping old_name → new_name.
        E.g.: {"old_coluna": "nova_coluna"}
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SetFields',
            'alias': 'Definir Campos',
            'description': 'Adiciona, remove ou renomeia colunas de um GeoDataFrame. '
                           'Suporta expressões Jinja nos valores ({{ row.<campo> }}).',
            'type': 'action',
            'properties': [
                {
                    'name': 'setFields',
                    'label': 'Definir campos',
                    'type': 'object',
                    # The type stays "object" (a dedicated web helper consumes
                    # these fields); the marker only turns on the suggestions block.
                    'suggest_columns': '*',
                    'default': {},
                    'description': (
                        'Campos e valores a definir ou sobrescrever. '
                        'Aceita valores fixos ou expressões Jinja. '
                        'Ex: {"area_km2": "{{ row.area / 1e6 }}", "status": "ativo"}'
                    )
                },
                {
                    'name': 'removeFields',
                    'label': 'Remover campos',
                    'type': 'object',
                    'suggest_columns': '*',
                    'default': {},
                    'description': 'Objeto com lista de colunas a remover. Ex: {"fields": ["temp", "flag_aux"]}'
                },
                {
                    'name': 'renameFields',
                    'label': 'Renomear campos',
                    'type': 'object',
                    'suggest_columns': '*',
                    'default': {},
                    'description': 'Mapeamento de renomeação de colunas. Ex: {"antigo_nome": "novo_nome"}'
                }
            ],
            'outputs': [
                {'name': 'output', 'type': 'geodataframe', 'description': 'GeoDataFrame com os campos adicionados, removidos ou renomeados'},
            ],
        }

    # Pure CPU-bound work (row-by-row Jinja over the whole GeoDataFrame): runs
    # on a pool thread, not on the event loop serving the executor's WebSocket.
    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        gdf = self.get_first_gdf(inputs)

        # Context available in Jinja expressions — only safe vars
        jinja_context: dict = {"env": safe_env()}

        # SET FIELDS — supports fixed values and per-row Jinja expressions
        set_fields: Dict[str, Any] = self.parameters.get('setFields', {})
        if set_fields:
            # Checks whether any value uses Jinja to decide whether it needs to iterate row by row
            has_expressions = any(_has_expression(v) for v in set_fields.values())

            if has_expressions:
                # `to_dict(orient='records')` materializes the WHOLE GeoDataFrame
                # into Python dicts. It sat inside the list comprehension, that is,
                # it was redone once PER FIELD: with 5 fields over 100k rows
                # that was 500k dicts built to render 500k values. Once only,
                # outside the loop.
                registros = gdf.to_dict(orient="records")
                for field, raw_value in set_fields.items():
                    if not _has_expression(raw_value):
                        # Fixed value amid fields with expressions. Scalar →
                        # pandas broadcast. Container (list/tuple/dict/set) →
                        # replicated per row, preserving the old behavior
                        # (_render_value returned the raw value per row); without this
                        # pandas would try to assign the elements column by column.
                        if isinstance(raw_value, (list, tuple, dict, set)):
                            gdf[field] = [raw_value] * len(gdf)
                        else:
                            gdf[field] = raw_value
                        continue
                    # Compiles the template ONCE per field — compiling
                    # (source→AST→bytecode) is orders of magnitude more expensive than
                    # rendering. It used to recompile on every row × field: 100k
                    # rows × 3 fields = 300k compilations of the SAME template.
                    tpl = _JINJA_ENV.from_string(raw_value)
                    gdf[field] = [
                        _coerce_num(tpl.render(row=row, **jinja_context))
                        for row in registros
                    ]
            else:
                # Fast path without Jinja — direct vectorized assignment
                for field, value in set_fields.items():
                    gdf[field] = value

        # REMOVE FIELDS
        remove_fields_obj = self.parameters.get("removeFields", {})
        fields_to_remove = (
            remove_fields_obj.get("fields", [])
            if isinstance(remove_fields_obj, dict)
            else []
        )
        if fields_to_remove:
            gdf = gdf.drop(columns=[col for col in fields_to_remove if col in gdf.columns], errors='ignore')

        # RENAME FIELDS
        rename_fields: Dict[str, str] = self.parameters.get('renameFields', {})
        if rename_fields:
            gdf = gdf.rename(columns=rename_fields)

        return {"output": gdf}
