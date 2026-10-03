from typing import Any, Dict
from jinja2 import StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.exceptions import SecurityError
from flow.utils.jinja_seguro import create_sandbox_environment
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# SandboxedEnvironment, not Environment: the expression comes from the user who
# edits the workflow, and in a plain Environment the default globals (`cycler`,
# `joiner`, `namespace`, `lipsum`) open the `__init__.__globals__` chain up to the
# `os` module — command execution in the executor's process, where the machine's
# mTLS cert and the already-decrypted connection strings live.
#
# Same environment used by flow/utils/expression_service.py and
# flow/nodes/action/field_transformer.py for exactly this class of input;
# this node was the only deviation.
#
# Instantiated once at module level: the env is stateless between renders (the
# context only enters in .render()) and recreating it per run only cost CPU.
_JINJA_ENV = create_sandbox_environment(undefined=StrictUndefined)

# Sets of values recognized as truthy/falsy for the result of the Jinja2 expression.
# Avoids false negatives with casing variations ("TRUE", "Yes", "False", etc.).
_TRUTHY = frozenset({'true', '1', 'yes', 'on'})
_FALSY  = frozenset({'false', '0', 'no', 'off', 'none', '', 'null'})


@register_node
class JinjaBranchNode(BaseNode):
    """
    Control node that evaluates a Jinja2 expression and routes the workflow according
    to the boolean result. More flexible than Conditional, since it allows arbitrary
    expressions with full access to the inputs context.

    Properties:
      - expression: Jinja2 expression to evaluate, e.g.: '{{ inputs.count > 10 }}'
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'JinjaBranch',
            'alias': 'Bifurcação Jinja',
            'description': (
                'Avalia uma expressão Jinja2 arbitrária e roteia o fluxo com base '
                'no resultado booleano (True/False).'
            ),
            'type': 'control',
            'properties': [
                {
                    'name': 'expression', 'required': True,
                    'label': 'Condição',
                    'type': 'string',
                    'default': '',
                    'description': (
                        "Expressão Jinja2 a avaliar. "
                        "Ex: '{{ inputs.count > 10 }}' ou '{{ value is not none }}'."
                    )
                }
            ],
            'outputs': [
                {'name': 'result', 'type': 'any', 'description': 'Primeiro valor recebido na entrada, repassado adiante'},
                {'name': 'branch', 'type': 'boolean', 'description': 'Resultado booleano da expressão Jinja2'},
            ],
            'branches': True,
            # `result` first: a fork edge is created without `from_key`, and the
            # simulation types the next node's input by the first field here
            # (core.py:805). See the comment in conditional.py.
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Parameter validation and extraction
        # -------------------------------------------------------
        self.validate()

        expression = self.parameters.get('expression', '').strip()

        if not expression:
            raise ValueError("Parâmetro 'expression' é obrigatório e não pode ser vazio.")

        # -------------------------------------------------------
        # 2) Builds the context for the Jinja2 expression
        # -------------------------------------------------------
        # Exposes the first value of the inputs as 'value' for convenience
        value = next(iter(inputs.values()), None) if inputs else None

        context: Dict[str, Any] = {
            'inputs': inputs,
            'value': value,
        }

        # -------------------------------------------------------
        # 3) Evaluates the Jinja2 expression
        # -------------------------------------------------------
        try:
            rendered = _JINJA_ENV.from_string(expression).render(context)
        except SecurityError as e:
            # The sandbox blocked access to an unsafe attribute/operation. A dedicated error
            # (and not the generic RuntimeError below) so the workflow author
            # understands it was a security block, not a syntax failure.
            raise ValueError(
                f"Operação não permitida por segurança na expressão Jinja2 '{expression}': {e}"
            ) from e
        except TemplateSyntaxError as e:
            raise ValueError(
                f"Erro de sintaxe Jinja2 na expressão '{expression}': {e}"
            ) from e
        except UndefinedError as e:
            raise ValueError(
                f"Variável indefinida na expressão Jinja2 '{expression}': {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Erro inesperado ao avaliar a expressão Jinja2 '{expression}': {e}"
            ) from e

        # -------------------------------------------------------
        # 4) Converts the rendered result to a boolean
        # -------------------------------------------------------
        # Robust conversion: recognizes casing variations and numeric values.
        # Before: only checked ('True', 'true', '1', 'yes') — ignored 'TRUE', 'Yes', etc.
        raw = rendered.strip().lower()
        if raw in _TRUTHY:
            result_bool = True
        elif raw in _FALSY:
            result_bool = False
        else:
            # Tries to interpret it as a number (0 = falsy, anything else = truthy)
            try:
                result_bool = bool(float(raw))
            except ValueError:
                # Unrecognized non-empty string → truthy (consistent with Python)
                result_bool = bool(raw)

        logger.info(
            "JinjaBranch: expressão '%s' renderizada como '%s' -> branch=%s",
            expression, rendered.strip(), result_bool,
        )

        # -------------------------------------------------------
        # 5) Returns the result with the signaled branch
        # -------------------------------------------------------
        # Same order as Conditional, and for the same reason: `**inputs`
        # last overwrote the freshly computed `branch` (two forks in
        # sequence made the second repeat the first's decision), and `branch`
        # as the first key made every node that reads `next(iter(inputs.values()))`
        # receive the boolean in place of the data. See the comment in
        # conditional.py for the full path.
        # Same rebuild as Conditional: reassigning an existing key keeps
        # its position in the dict, and `result` needs to end up at the end for
        # the "último" Merge to find the data. See the comment in conditional.py.
        saida = {k: v for k, v in inputs.items()
                 if k not in ('branch', 'result')}
        saida['branch'] = result_bool
        saida['result'] = value
        return saida
