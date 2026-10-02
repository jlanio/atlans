from typing import Any, Dict
from jinja2 import StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.exceptions import SecurityError
from flow.utils.jinja_seguro import criar_ambiente_sandbox
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)

# SandboxedEnvironment, nao Environment: a expressao vem do usuario que edita o
# workflow, e num Environment comum os globais default (`cycler`, `joiner`,
# `namespace`, `lipsum`) abrem a cadeia `__init__.__globals__` ate o modulo `os`
# — execucao de comandos no processo do executor, onde ficam o cert mTLS da
# maquina e as connection strings ja descriptografadas.
#
# Mesmo ambiente usado por flow/utils/expression_service.py e
# flow/nodes/action/field_transformer.py para exatamente esta classe de entrada;
# este no era o unico desvio.
#
# Instanciado uma vez no modulo: o env e stateless entre renders (o contexto so
# entra no .render()) e recria-lo por execucao so custava CPU.
_JINJA_ENV = criar_ambiente_sandbox(undefined=StrictUndefined)

# Conjuntos de valores reconhecidos como truthy/falsy para o resultado da expressão Jinja2.
# Evita falsos negativos com variações de casing ("TRUE", "Yes", "False", etc.).
_TRUTHY = frozenset({'true', '1', 'yes', 'on'})
_FALSY  = frozenset({'false', '0', 'no', 'off', 'none', '', 'null'})


@register_node
class JinjaBranchNode(BaseNode):
    """
    Nó de controle que avalia uma expressão Jinja2 e roteia o fluxo de acordo com
    o resultado booleano. Mais flexível que o Conditional pois permite expressões
    arbitrárias com acesso completo ao contexto de inputs.

    Propriedades:
      - expression: expressão Jinja2 a avaliar, ex: '{{ inputs.count > 10 }}'
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
            # `result` primeiro: aresta de bifurcação nasce sem `from_key`, e a
            # simulação tipa a entrada do nó seguinte pelo primeiro campo daqui
            # (core.py:805). Ver o comentário em conditional.py.
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # -------------------------------------------------------
        # 1) Validação e extração de parâmetros
        # -------------------------------------------------------
        self.validate()

        expression = self.parameters.get('expression', '').strip()

        if not expression:
            raise ValueError("Parâmetro 'expression' é obrigatório e não pode ser vazio.")

        # -------------------------------------------------------
        # 2) Monta o contexto para a expressão Jinja2
        # -------------------------------------------------------
        # Expõe o primeiro valor dos inputs como 'value' para conveniência
        value = next(iter(inputs.values()), None) if inputs else None

        context: Dict[str, Any] = {
            'inputs': inputs,
            'value': value,
        }

        # -------------------------------------------------------
        # 3) Avalia a expressão Jinja2
        # -------------------------------------------------------
        try:
            rendered = _JINJA_ENV.from_string(expression).render(context)
        except SecurityError as e:
            # A sandbox barrou acesso a atributo/operação insegura. Erro próprio
            # (e não o RuntimeError genérico abaixo) para que o autor do workflow
            # entenda que foi bloqueio de segurança, não falha de sintaxe.
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
        # 4) Converte o resultado renderizado para booleano
        # -------------------------------------------------------
        # Conversão robusta: reconhece variações de casing e valores numéricos.
        # Antes: só checava ('True', 'true', '1', 'yes') — ignorava 'TRUE', 'Yes', etc.
        raw = rendered.strip().lower()
        if raw in _TRUTHY:
            result_bool = True
        elif raw in _FALSY:
            result_bool = False
        else:
            # Tenta interpretar como número (0 = falsy, qualquer outro = truthy)
            try:
                result_bool = bool(float(raw))
            except ValueError:
                # String não reconhecida e não-vazia → truthy (consistente com Python)
                result_bool = bool(raw)

        logger.info(
            "JinjaBranch: expressão '%s' renderizada como '%s' -> branch=%s",
            expression, rendered.strip(), result_bool,
        )

        # -------------------------------------------------------
        # 5) Retorna resultado com o branch sinalizado
        # -------------------------------------------------------
        # Mesma ordem do Conditional, e pelo mesmo motivo: `**inputs` por
        # último sobrescrevia o `branch` recém-calculado (duas bifurcações em
        # sequência faziam a segunda repetir a decisão da primeira), e `branch`
        # como primeira chave fazia todo nó que lê `next(iter(inputs.values()))`
        # receber o booleano no lugar do dado. Ver o comentário em
        # conditional.py para o caminho completo.
        # Mesma reconstrução do Conditional: reatribuir chave existente mantém
        # a posição dela no dict, e o `result` precisa terminar no fim para o
        # Merge "último" achar o dado. Ver o comentário em conditional.py.
        saida = {k: v for k, v in inputs.items()
                 if k not in ('branch', 'result')}
        saida['branch'] = result_bool
        saida['result'] = value
        return saida
