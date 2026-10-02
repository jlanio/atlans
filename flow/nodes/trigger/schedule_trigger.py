# flow/nodes/trigger/schedule_trigger.py
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.fuso import fuso_padrao_do_agendamento

@register_node
class ScheduleTrigger(BaseNode):
    """
    Nó de gatilho baseado em agendamento (cron ou intervalo).
    Este nó não dispara diretamente — ele serve como base para que a API agende
    execuções futuras com base nos parâmetros definidos.
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
                    # No servidor, o MESMO valor que ele usa para agendar
                    # (`app.core.constants.FUSO_PADRAO_DO_AGENDAMENTO`), lido
                    # do ambiente em `flow/utils/fuso.py`. Não pode ser um
                    # import de `app/`: os módulos de `flow/` só importam de
                    # `app/` DENTRO de funções, porque o executor empacota
                    # `flow/` sem `app/`, e `description()` roda no import.
                    #
                    # Quem garante que servidor e nó não divirjam é
                    # `test_mcp_gatilhos.py`: divergir faz o próximo save de
                    # CADA workflow agendado recriar o schedule, zerando o
                    # `next_run_at` e pulando a ocorrência do dia.
                    #
                    # No EXECUTOR, que não tem AGENDAMENTO_FUSO_PADRAO, este
                    # default seria UTC — por isso o servidor preenche o
                    # `timezone` ao despachar (app/services/fuso_do_agendamento.py),
                    # e aqui ele só vale para quem monta o nó no próprio servidor.
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
        # Este nó não executa diretamente — apenas serve como metadado para agendamento.
        return {"status": "scheduled", "info": self.parameters}
