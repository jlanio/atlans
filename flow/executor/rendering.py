# flow/executor/rendering.py
"""Node parameter rendering via Jinja2 with an aliases system."""
from typing import Any, Dict
from flow.utils.expression_service import ExpressionService
from flow.utils.logger import get_logger

logger = get_logger(__name__)

expr_svc = ExpressionService()

# Nesting ceiling when descending through dicts/lists. A form parameter does not
# come close to this; the limit exists only so a pathological structure does not
# turn into infinite recursion.
_PROFUNDIDADE_MAX = 12

# What the SERVER injects from the saved credential (see
# app/services/credential_resolver.py): a secret, never a template. Rendering
# would silently alter a password with `{{`, `{%` or `$Alias.campo` inside — and
# the rendering failure would repeat the secret in the error message, which goes
# to the screen, the database and the log (the DEBUG here would also write it raw).
_INJETADOS_PELO_SERVIDOR = frozenset({"connectionString", "http_auth", "s3_auth"})


def _tem_expressao(raw: str, named: Dict[str, Any]) -> bool:
    """Does the string call for rendering?

    `{% %}` statements count as Jinja just as much as `{{ }}` expressions.
    The gate used to require `{{` AND `}}`, so a parameter containing only
    `{% ... %}` was not rendered here and went RAW to the node — which could
    evaluate it in its own environment. Going through expr_svc (sandboxed),
    statements and expressions get the same treatment.
    """
    has_jinja = ("{{" in raw and "}}" in raw) or ("{%" in raw and "%}" in raw)
    m_alias = expr_svc.find_alias(raw)
    has_valid_alias = bool(m_alias and m_alias.group("alias").split(".")[0] in named)
    return has_jinja or has_valid_alias


def _renderizar(
    valor: Any,
    *,
    node_id: str,
    caminho: str,
    named: Dict[str, Any],
    context: Dict[str, Any],
    profundidade: int = 0,
) -> Any:
    """Renders a parameter value, descending through dicts and lists.

    The previous version stopped at the first line (`if not isinstance(raw, str):
    continue`) and only rendered top-level string parameters. Those who suffered
    from that were precisely the fields that exist to receive a dynamic value:

      - `queryParams` of DatabaseQuery/DatabaseSpatialQuery — the values of the
        `:placeholders`, which is WHERE the filter's variable value should go.
        The UI even instructs, right above the field, to use `{{ $Alias }}`.
      - `headers` and `params` of HttpRequest.

    And the failure mode was worse than "does not work": the dict went raw to the
    node, the template went as TEXT to the database (`WHERE bairro = '{{ ... }}'`),
    the query ran, came back empty and the workflow carried on. No error
    anywhere.

    The dict key is not rendered — only the value. In `queryParams` the
    key is the name of the `:placeholder` and must match the SQL; in `headers` it
    is the header name. There is no use case, and a template producing an empty
    or repeated key would silently break the dict.
    """
    if isinstance(valor, str):
        if not _tem_expressao(valor, named):
            return valor
        logger.debug("[%s] Param raw (%s): %s", node_id, caminho, valor)
        try:
            # Inside a dict/list, the type is preserved when the value is
            # a single expression: `{{ $Filtro.limite }}` with 50 returns the integer
            # 50, not `'50'`. That is what `queryParams` needs — there the value becomes
            # a SQL bind, and the type decides how Postgres compares it to the column.
            #
            # At the top level (depth 0) it stays `render`, which returns text. There
            # nodes have long depended on the existing behavior, and changing it
            # at the same time would mix a fix with a breakage: a node that does
            # `.strip()` on a parameter would start receiving an int. Native
            # handling comes in only where nothing was rendered before.
            renderizado = (
                expr_svc.render_native(valor, context) if profundidade > 0
                else expr_svc.render(valor, context)
            )
        except Exception as e:
            msg = (
                f"[Node {node_id} | param '{caminho}']\n"
                f"  Falha ao renderizar a expressão: {valor!r}\n"
                f"  Erro: {e}\n"
                f"  Aliases disponíveis: {sorted(named.keys())}\n"
            )
            logger.error(msg)
            raise ValueError(msg) from e
        logger.debug("[%s] Param rendered (%s): %s", node_id, caminho, renderizado)
        return renderizado

    if profundidade >= _PROFUNDIDADE_MAX:
        return valor

    if isinstance(valor, dict):
        return {
            chave: _renderizar(
                item, node_id=node_id, caminho=f"{caminho}.{chave}",
                named=named, context=context, profundidade=profundidade + 1,
            )
            for chave, item in valor.items()
        }

    if isinstance(valor, list):
        return [
            _renderizar(
                item, node_id=node_id, caminho=f"{caminho}[{i}]",
                named=named, context=context, profundidade=profundidade + 1,
            )
            for i, item in enumerate(valor)
        ]

    # Number, boolean, None, pinned GeoDataFrame — nothing to render.
    return valor


def render_node_parameters(
    node,
    node_id: str,
    named: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Renders the node's parameters using Jinja2.

    Returns a copy of the parameters with the expressions rendered.
    Does not modify node.parameters directly — the caller must assign the result.
    """
    context.update(named)
    return {
        chave: valor if chave in _INJETADOS_PELO_SERVIDOR else _renderizar(
            valor, node_id=node_id, caminho=chave,
            named=named, context=context,
        )
        for chave, valor in node.parameters.items()
    }
