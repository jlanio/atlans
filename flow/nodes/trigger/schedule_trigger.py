# flow/nodes/trigger/schedule_trigger.py
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.fuso import fuso_padrao_do_agendamento

@register_node
class ScheduleTrigger(BaseNode):
    """
    Schedule-based trigger node (cron or interval).
    This node does not fire directly — it serves as the basis for the API to schedule
    future runs according to the defined parameters.
    """

    @classmethod
    def description(cls) -> dict:
        return {
            "name": "ScheduleTrigger",
            "alias": "Disparador Agendado",
            "description": "Gatilho que agenda a execução do workflow em intervalos definidos (cron ou interval).",
            "type": "trigger",
            "properties": [
                {
                    "name": "strategy",
                    "label": "Estratégia de Agendamento",
                    "type": "string",
                    "default": "cron",
                    "description": "Estratégia de agendamento: 'cron' ou 'interval'"
                },
                {
                    "name": "cron_expression",
                    "label": "Agendamento (cron)",
                    "type": "string",
                    "default": "0 9 * * *",
                    "description": "Expressão cron (se strategy = cron). Exemplo: '0 9 * * *' para 9h todos os dias."
                },
                {
                    "name": "interval",
                    "label": "Intervalo",
                    "type": "integer",
                    "default": 60,
                    "description": "Intervalo de tempo (em segundos, minutos, etc) — usado se strategy = 'interval'"
                },
                {
                    "name": "unit",
                    "label": "Unidade do Intervalo",
                    "type": "string",
                    "default": "minutes",
                    "description": "Unidade do intervalo: 'seconds', 'minutes', 'hours', 'days'"
                },
                {
                    "name": "timezone",
                    "label": "Fuso horário",
                    "type": "string",
                    # On the server, the SAME value it uses for scheduling
                    # (`app.core.constants.FUSO_PADRAO_DO_AGENDAMENTO`), read
                    # from the environment in `flow/utils/fuso.py`. It cannot be an
                    # import from `app/`: the `flow/` modules only import from
                    # `app/` INSIDE functions, because the executor packages
                    # `flow/` without `app/`, and `description()` runs at import.
                    #
                    # What guarantees that server and node do not diverge is
                    # `test_mcp_gatilhos.py`: diverging makes the next save of
                    # EVERY scheduled workflow recreate the schedule, resetting
                    # `next_run_at` and skipping that day's occurrence.
                    #
                    # On the EXECUTOR, which has no AGENDAMENTO_FUSO_PADRAO, this
                    # default would be UTC — that is why the server fills in
                    # `timezone` at dispatch (app/services/fuso_do_agendamento.py),
                    # and here it only applies to whoever builds the node on the server itself.
                    "default": fuso_padrao_do_agendamento(),
                    "description": "Fuso horário de referência para execução"
                },
                {
                    "name": "active",
                    "label": "Ativo",
                    "type": "boolean",
                    "default": True,
                    "description": "Se o agendamento já deve ser criado como ativo"
                },
                {
                    "name": "rrule_expression",
                    "label": "Regra de Recorrência (RRule)",
                    "type": "string",
                    "default": "",
                    "description": "Expressão RRule (RFC 5545) — usada se strategy = 'rrule'. Exemplo: 'FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9'"
                }
            ],
            'outputs': [
                {'name': 'status', 'type': 'string', 'description': 'Status do agendamento'},
                {'name': 'info', 'type': 'object', 'description': 'Parâmetros de configuração do agendamento'},
            ],
        }

    async def execute(self, inputs):
        self.validate()
        # This node does not execute directly — it only serves as metadata for scheduling.
        return {"status": "scheduled", "info": self.parameters}
