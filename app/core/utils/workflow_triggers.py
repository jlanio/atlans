"""Utilitarios para detectar tipos de trigger em definicoes de workflow.

A funcao `trigger_workflow_inline` foi removida junto com o node
TriggerWorkflow — sub-fluxos agora sao executados exclusivamente pelo
SubWorkflow (categoria control), que tem resolver injetado pelo executor
e nao depende de `app.*` em runtime.
"""


def has_webhook_trigger(definition: dict) -> bool:
    """True se a definição contém pelo menos um node WebhookTrigger.

    Usado por endpoints que só devem executar workflows configurados para
    esse tipo de gatilho (ex: POST /webhook/execute/{id_hash}).

    Segue o mesmo padrão de `extract_schedule_node` em app.core.scheduling.hooks
    (checa type + name).
    """
    for node in definition.get("nodes", []):
        if node.get("type") == "trigger" and node.get("name") == "WebhookTrigger":
            return True
    return False
