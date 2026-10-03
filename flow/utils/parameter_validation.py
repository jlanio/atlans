# Em flow/utils/parameter_validation.py

import json
from typing import Any, Dict, List
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _coerce_structured(key: str, value: Any) -> Any:
    """Normalizes "object" type parameters arriving serialized from the canvas.

    The node editor can only save primitives — `setNodeField` has the
    signature (field, value: string | number | boolean) — so the helpers
    serialize structures with JSON.stringify. They arrived here as str and the
    `isinstance(value, dict)` check rejected them with
    "O parametro 'X' deve ser um objeto (dict)", breaking at runtime something
    the UI had saved correctly (e.g. the SubWorkflow's inputsMapping).

    "object" in the catalog's vocabulary means "JSON structure", not
    strictly dict: `ports` declares type "object" with default [] (a list).
    That is why dict and list are both accepted.
    """
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        texto = value.strip()
        if not texto:
            return {}
        try:
            decodificado = json.loads(texto)
        except (ValueError, TypeError):
            raise ValueError(
                f"O parâmetro '{key}' deve ser um objeto (dict) ou JSON válido. "
                f"Recebido: {value[:80]!r}"
            )
        if isinstance(decodificado, (dict, list)):
            return decodificado
    raise ValueError(
        f"O parâmetro '{key}' deve ser um objeto (dict). "
        f"Tipo recebido: {type(value).__name__}"
    )


def requested_columns(bruto: Any) -> List[str]:
    """List of columns from a chips field, whether it comes as a list,
    JSON, or comma-separated text.

    The chips field saves JSON (`ChipsField` does JSON.stringify), but already
    saved definitions hold an actual list (object editor) or the old format —
    comma-separated text —, which is still the natural way to PASTE several
    columns at once into the new field.

    A tolerant parser here avoids a data migration over the definition of every
    workflow that uses one of these nodes. It was born as `_requested_columns` in
    AttributeJoin and moved up here when other nodes gained the same field.

    Returns list[str] with no empty entries and no leading/trailing spaces.
    """
    if isinstance(bruto, (list, tuple)):
        return [str(c).strip() for c in bruto if str(c).strip()]

    texto = str(bruto or "").strip()
    if not texto:
        return []

    if texto.startswith("["):
        try:
            carregado = json.loads(texto)
        except json.JSONDecodeError:
            carregado = None
        if isinstance(carregado, list):
            return [str(c).strip() for c in carregado if str(c).strip()]

    return [c.strip() for c in texto.split(",") if c.strip()]

# Keys that live in `properties` without being node parameters, and therefore
# must not trigger a discard warning: the label saved by the configuration modal
# and the retry controls the executor reads directly from `parameters` before
# execute (core.py::get_retry_params).
#
# The legacy outputKey*/inputKey* prefixes left this list: auto_map_edges was
# retired (see core.py and docs/specs/edge-data-contract.md §5), so these
# params no longer have any effect and MUST show up as discarded until they are
# fixed by hand.
_PLATFORM_KEYS = frozenset({"alias", "retry_count", "retry_delay_s"})


def _is_platform_key(chave: str) -> bool:
    return chave in _PLATFORM_KEYS


def validate_node_parameters(
    params: Dict[str, Any],
    props: List[Dict[str, Any]],
    node_name: str = "",
) -> Dict[str, Any]:
    """
    New version that accepts:
      params:      The parameter dictionary (e.g. self.parameters)
      props:       The property list (e.g. description().get("properties"))
      node_name:   Node name, only to identify the discarded-parameter warning

    Returns the validated parameters (with defaults applied).

    WARNING: the return value is built from `props`, so **every key in
    `params` that is not declared is discarded**. That is what keeps the node
    immune to garbage in the definition, but it also makes an outdated executor
    indistinguishable from a logic bug: the server publishes the node catalog, the
    UI shows the new field and saves the value, and the executor — with an older
    `flow/`, whose descriptor does not yet declare the property — throws the value
    away without any error. That is how DataOutput's "Sobrescrever se já existir"
    (overwrite if it already exists) option had no effect. The warning below exists
    so that this shows up in a log line instead of becoming an investigation.
    """
    final_params = {}
    for prop in props:
        key = prop["name"]
        expected_type = prop.get("type")
        default_value = prop.get("default")

        if key in params:
            value = params[key]
            # A numeric/boolean field CLEARED in the UI arrives as "" (the text
            # input saves an empty string, it does not remove the key). For a
            # parameter with a declared default this means "not filled in", not a
            # value: without this detour, clearing an optional field brought down
            # the run with "deve ser inteiro. Recebido: ''" (must be an integer).
            if value in ("", None) and expected_type in ("integer", "number", "boolean") \
                    and default_value is not None:
                value = default_value
        elif default_value is not None:
            value = default_value
            # optional: to log the default used, add verbose here
        else:
            raise ValueError(f"❌ Parâmetro obrigatório '{key}' ausente.")

        # type validation
        if expected_type:
            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"O parâmetro '{key}' deve ser uma string.")
            if expected_type == "object":
                value = _coerce_structured(key, value)
            if expected_type == "number":
                # Coerces numeric strings (the text field UI used to save "5"); only
                # rejects what is not actually a number.
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(f"O parâmetro '{key}' deve ser numérico. Recebido: '{value}'.")
                elif isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"O parâmetro '{key}' deve ser numérico.")
            if expected_type == "integer":
                if isinstance(value, bool):
                    raise ValueError(f"O parâmetro '{key}' deve ser inteiro.")
                if isinstance(value, str):
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(f"O parâmetro '{key}' deve ser inteiro. Recebido: '{value}'.")
                elif not isinstance(value, int):
                    # aceita float inteiro (5.0 -> 5); rejeita 5.5
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                    else:
                        raise ValueError(f"O parâmetro '{key}' deve ser inteiro.")
            if expected_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"O parâmetro '{key}' deve ser booleano.")
            if expected_type == "select":
                if not isinstance(value, str):
                    raise ValueError(f"O parâmetro '{key}' deve ser uma string (select).")
                options = prop.get("options", [])
                valid_values = [o["value"] if isinstance(o, dict) else o for o in options]
                if valid_values and value not in valid_values:
                    # Tolerates whitespace/case (as nodes did with .strip().lower()/.upper()
                    # before migrating to select) and canonicalizes to the option's value.
                    stripped = value.strip()
                    match = next((v for v in valid_values if v.lower() == stripped.lower()), None)
                    if match is None:
                        raise ValueError(
                            f"O parâmetro '{key}' deve ser um dos valores: {valid_values}. Recebido: '{value}'."
                        )
                    value = match

        final_params[key] = value

    descartados = sorted(
        k for k in params
        if k not in final_params and not _is_platform_key(k)
    )
    if descartados:
        logger.warning(
            "%sparâmetro(s) %s presentes na definição mas ausentes do schema do nó — "
            "descartados. Duas causas: parâmetro obsoleto de um workflow antigo "
            "(inofensivo), ou executor com `flow/` anterior ao que publicou o campo — "
            "aí a opção foi configurada na interface e não surte efeito. Declarados: %s",
            f"[{node_name}] " if node_name else "",
            descartados,
            sorted(p["name"] for p in props),
        )

    return final_params
