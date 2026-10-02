# app/core/utils/workflow_nodes.py
"""Leitura das propriedades de um nó da definition.

Mora em `core/utils` — e não dentro de um service — porque três caminhos
independentes precisam concordar na extração: o dispatch (que valida e injeta
credenciais), o relatório de impacto do move e qualquer coletor futuro. Enquanto
a função era privada de `workflow_execution_service`, o relatório a importava
com underscore, atando um service ao interior de outro.
"""


def node_props(node: dict) -> dict:
    """Extrai o dict de propriedades efetivo do nó.

    Usa a mesma cadeia de fallback do frontend/worker: `data.properties` tem
    precedência sobre `properties`. Centralizado para que coletor e validador
    concordem em qual campo do nó contém `credential_id` — evita que um atacante
    contorne a validação forjando um `data.properties` sem `credential_id` ao
    lado de um `properties.credential_id` real.
    """
    return node.get("data", {}).get("properties") or node.get("properties") or {}
