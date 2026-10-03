#/flow/utils/query_param_formatter.py

import re
from typing import Any, Dict, List, Tuple

from flow.utils.sql_guard import strip_sql_literals

# Precompiled regex to find :name placeholders
_PLACEHOLDER_PATTERN = re.compile(r'(?<!:):(?P<key>[A-Za-z_]\w*)\b')

def prepare_query(query: str, params: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Converts :key placeholders into $1, $2, ... stably (same placeholder → same index),
    and returns (query_preparada, valores_ordenados).

    Example:
        query = "SELECT * FROM imoveis WHERE id = :id AND bairro = :bairro OR fk_id = :id"
        params = {"id": 5, "bairro": "Centro"}

    Returns:
        (
            "SELECT * FROM imoveis WHERE id = $1 AND bairro = $2 OR fk_id = $1",
            [5, "Centro"]
        )

    Only what is in CODE position counts as a placeholder. The regex used to
    scan the raw text, and `:nome` inside a literal or comment was treated
    as a parameter — with two outcomes, both silent for the author:

        WHERE obs = 'urgente:revisar'      -> "Parâmetro SQL 'revisar' não
                                              fornecido" (SQL parameter not
                                              provided), and a perfectly valid
                                              query was rejected.
        WHERE tag = 'nota:importante'      -> became `'nota$1'` if there was a
                                              parameter named `importante`: the
                                              literal's content was replaced by
                                              a bind, and the query started
                                              filtering something else.

    The position map comes from `strip_sql_literals`, which preserves the query's
    length and blanks out only what is text — the same scanner `sql_guard` uses
    so as not to mistake Portuguese for a command.
    """
    # Same length as the query: a match index here is valid there.
    mapa = strip_sql_literals(query)
    if len(mapa) != len(query):  # pragma: no cover - scanner invariant
        # If the masking stops preserving the length, the positions
        # shift and the slices below silently build a WRONG query.
        # Failing here is the only acceptable way out.
        raise RuntimeError(
            "strip_sql_literals não preservou o comprimento da query — "
            "as posições dos placeholders não são confiáveis."
        )

    index_map: Dict[str, int] = {}
    values: List[Any] = []
    pedacos: List[str] = []
    fim_anterior = 0

    for match in _PLACEHOLDER_PATTERN.finditer(mapa):
        key = match.group("key")
        if key not in params:
            raise ValueError(f"Parâmetro SQL '{key}' não fornecido.")
        if key not in index_map:
            index_map[key] = len(index_map) + 1
            values.append(params[key])
        pedacos.append(query[fim_anterior:match.start()])
        pedacos.append(f"${index_map[key]}")
        fim_anterior = match.end()

    pedacos.append(query[fim_anterior:])
    return "".join(pedacos), values


def resolver_query_params(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Decides between the `queryParams` received from the previous node and the one configured in the node.

    PRESENCE is what counts, not truthiness. The previous form was
    `inputs.get('queryParams') or parameters.get('queryParams', {})`, and the `or`
    treated `{}` as absence — but an empty dictionary coming from an edge is
    an answer, not silence: it means "there is no filter at all". The node
    ignored that answer and fell back to the static value, so a query that
    should run with no filter ran with the old filters, saved in the
    form — and the result came back plausible, just wrong.

    `inputs` is keyed by the edge's `to_key` (see executor/core.py), so the
    key being there means exactly that someone connected an edge pointing
    to `queryParams`.
    """
    veio_da_aresta = 'queryParams' in inputs
    valor = inputs['queryParams'] if veio_da_aresta else parameters.get('queryParams', {})

    if valor is None:
        valor = {}

    if not isinstance(valor, dict):
        origem = (
            "recebido do nó anterior" if veio_da_aresta
            else "configurado no campo 'Parâmetros da consulta'"
        )
        raise ValueError(
            f"'queryParams' ({origem}) deve ser um objeto JSON. "
            f"Recebido: {type(valor).__name__}."
        )
    return valor
