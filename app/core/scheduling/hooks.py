# app/core/scheduling/hooks.py
"""
Hook de agendamento: cria/atualiza schedules ao salvar um workflow.
Fonte canônica — importar daqui diretamente.
"""
from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.core.exceptions import InvalidScheduleError
from app.core.utils.logger import get_logger
from app.models.models import Schedule, Workflow
from app.services.schedule_service import ScheduleService, validate_schedule_create, campos_de_ativacao
from app.schemas.schedule import ScheduleCreate, ScheduleNotice

logger = get_logger(__name__)


def extract_schedule_node(definition: dict) -> dict | None:
    """Retorna o primeiro nó ScheduleTrigger encontrado na definição, ou None."""
    for node in definition.get("nodes", []):
        if node.get("type") == "trigger" and node.get("name") == "ScheduleTrigger":
            return node
    return None


def disable_schedule_node(definition: dict) -> bool:
    """Desliga o ScheduleTrigger na própria definition. Devolve se havia um.

    Regra comum a duplicar e a mover: o workflow derivado nasce desligado, para
    não disparar sozinho antes de o usuário revisá-lo. Desligar na definition (e
    não só na tabela) mantém canvas e schedule coerentes — `apply_schedule_if_needed`
    lê o `active` do nó, então o que o usuário vê no canvas é o que vale.
    """
    node = extract_schedule_node(definition)
    if node is None:
        return False
    node.setdefault("properties", {})["active"] = False
    return True


def _update_de_active(ativar: bool) -> dict:
    """Campos a gravar no Schedule ao ligar/desligar o agendamento.

    Alias fino de `campos_de_ativacao` (a fonte canônica mora em
    `schedule_service`, junto do `update_schedule` que a rota REST e a tool MCP
    usam). Mantido pelo nome antigo para não tocar os chamadores deste módulo.
    Religar zera `next_run_at` de propósito — ver a docstring da função canônica.
    """
    return campos_de_ativacao(ativar)


async def sync_schedules_with_workflow_state(workflow: Workflow, db_session) -> None:
    """Alinha `Schedule.active` ao `flag_ative` do workflow.

    Chamada por todo caminho que liga/desliga o workflow SEM passar pela
    definition: o switch "Ativado/Inativo" da lista de projetos (`PUT
    /workflows/{id}` só com `flag_ative`) e o override do admin. Nenhum dos dois
    tocava em schedules, então desativar um workflow deixava o Schedule ativo no
    banco e o AsyncScheduler seguia tentando disparar a cada ocorrência do cron,
    colhendo `WorkflowInactiveError` num loop que só existia no log de erro.

    Na reativação quem manda é o `active` do nó ScheduleTrigger — o que o
    usuário vê no canvas, e a mesma fonte que `apply_schedule_if_needed` usa.
    Religar tudo às cegas ressuscitaria o agendamento que o dono tinha desligado
    no editor antes de desativar o workflow. Sem nó na definition não há
    agendamento legítimo: o que sobrou no banco fica desligado.

    Lê `properties.active` direto de `workflow.definition`, sem descriptografar:
    a criptografia cobre `connectionString`, e `decrypt_workflow_connections`
    grava no dict recebido — chamá-la aqui marcaria a definition como suja na
    sessão e o commit seguinte salvaria o texto claro no banco.
    """
    crud = ScheduleService(db_session).schedule_crud
    existentes = await crud.get_by_workflow_hash(workflow.id_hash)
    if not existentes:
        return

    if workflow.flag_ative:
        node = extract_schedule_node(workflow.definition or {})
        desejado = bool(node.get("properties", {}).get("active", True)) if node else False
    else:
        desejado = False

    for sch in existentes:
        if bool(sch.active) != desejado:
            await crud.update(sch, _update_de_active(desejado))


def _campo_cron_norm(campo: str) -> str:
    """Normaliza um campo do cron para comparação: "09" -> "9", "4,2" -> "2,4".

    Só toca em campos que são lista de inteiros puros — curingas, faixas e
    passos ("*", "1-5", "*/15") ficam intactos (comparados literalmente).
    """
    partes = campo.split(",")
    if partes and all(p.isdigit() for p in partes):
        return ",".join(str(n) for n in sorted({int(p) for p in partes}))
    return campo


def _cron_normalizado(expr: str | None) -> str | None:
    """Forma canônica de um cron para o comparador de configuração."""
    if not expr:
        return None
    campos = expr.strip().split()
    if len(campos) != 5:
        return expr.strip()   # não é um cron de 5 campos: compara literal
    return " ".join(_campo_cron_norm(c) for c in campos)


def _mesma_configuracao(atual: Schedule, desejado: ScheduleCreate) -> bool:
    """Compara só o que define QUANDO o agendamento dispara.

    `active` fica de fora de propósito — mudar de ativo para inativo não deve
    recriar o schedule, só alternar a flag. E cada estratégia olha apenas os
    seus campos: o nó ScheduleTrigger sempre envia os defaults de todas elas
    (interval=60, unit="minutes"), enquanto `create_schedule` zera os que não
    pertencem à estratégia escolhida. Comparar tudo daria diferente sempre.

    O cron é comparado NORMALIZADO ("00 09 * * *" == "0 9 * * *", "... 4,2" ==
    "... 2,4"): croniter trata as duas formas de modo idêntico, então tê-las
    como "diferentes" recriaria o schedule à toa — o que zera `next_run_at` e
    faz a ocorrência do dia ser pulada.
    """
    if atual.strategy != desejado.strategy:
        return False
    if (atual.timezone or None) != (desejado.timezone or None):
        return False

    if desejado.strategy == "cron":
        return _cron_normalizado(atual.cron_expression) == _cron_normalizado(desejado.cron_expression)
    if desejado.strategy == "interval":
        return atual.interval == desejado.interval and (atual.unit or None) == (desejado.unit or None)
    if desejado.strategy == "rrule":
        return (atual.rrule_expression or None) == (desejado.rrule_expression or None)
    return False


async def apply_schedule_if_needed(
    workflow: Workflow, definition: dict, db_session,
) -> list[ScheduleNotice]:
    """
    Sincroniza os agendamentos do workflow com sua definição atual.

    - Sem ScheduleTrigger na definição: remove os agendamentos existentes. Sem
      isso, remover o nó do canvas deixava o async_scheduler disparando pelo
      Schedule antigo — o "scheduler zumbi".
    - Com ScheduleTrigger e configuração INALTERADA: não mexe. Recriar zeraria
      `next_run_at`, que é recalculado para a próxima ocorrência FUTURA — então
      salvar o workflow depois do horário do cron fazia o disparo daquele dia
      ser pulado silenciosamente.
    - Com ScheduleTrigger e configuração alterada: substitui.

    Devolve avisos (`ScheduleNotice`) sobre o que NÃO foi aplicado — workflow
    inativo, expressão inválida. Antes esses casos só viravam log e o usuário
    via "salvo com sucesso" sem saber que o agendamento tinha sido preservado
    (ou, no caso inválido, destruído). O chamador expõe os avisos na resposta
    do save para virarem toast.
    """
    notices: list[ScheduleNotice] = []
    scheduler = ScheduleService(db_session)
    node = extract_schedule_node(definition)

    if not node:
        await scheduler.delete_all_schedules_for_workflow(workflow.id_hash)
        return notices

    props = node.get("properties", {})
    desejado = ScheduleCreate(
        strategy=props.get("strategy", "cron"),
        cron_expression=props.get("cron_expression") or None,
        interval=props.get("interval"),
        unit=props.get("unit") or None,
        rrule_expression=props.get("rrule_expression") or None,
        timezone=props.get("timezone", FUSO_PADRAO_DO_AGENDAMENTO),
        active=bool(props.get("active", True)),
    )

    existentes = await scheduler.schedule_crud.get_by_workflow_hash(workflow.id_hash)

    if len(existentes) == 1 and _mesma_configuracao(existentes[0], desejado):
        atual = existentes[0]
        if bool(atual.active) != bool(desejado.active):
            await scheduler.schedule_crud.update(atual, _update_de_active(bool(desejado.active)))
        return notices

    # Daqui para baixo o schedule precisaria ser substituído. Duas guardas
    # ANTES de apagar qualquer coisa — apagar e só então descobrir que não dá
    # para recriar deixava o workflow sem agendamento nenhum, com a falha
    # engolida pelo chamador (o usuário via "salvo" e o cron morria).

    # 1) `create_schedule` recusa workflow desativado. Preserva o schedule atual
    #    e avisa: a config nova só entra quando o workflow for reativado e salvo.
    if not workflow.flag_ative:
        logger.warning(
            "Workflow '%s' está desativado: agendamento preservado como está, "
            "a nova configuração NÃO foi aplicada. Reative o workflow e salve "
            "de novo para atualizar o agendamento.",
            workflow.id_hash,
        )
        notices.append(ScheduleNotice(
            code="workflow_inactive",
            severity="warning",
            message=(
                "O workflow está inativo, então a nova configuração de "
                "agendamento não foi aplicada. Reative o workflow e salve de "
                "novo para atualizar o agendamento."
            ),
        ))
        return notices

    # 2) Config inválida não pode destruir um agendamento válido anterior.
    #    (O ScheduleTrigger no front já valida; isto é defesa em profundidade
    #    para payloads legados/de API que cheguem inválidos.)
    try:
        validate_schedule_create(desejado)
    except InvalidScheduleError as exc:
        logger.warning(
            "Workflow '%s': configuração de agendamento inválida (%s) — "
            "agendamento anterior preservado.",
            workflow.id_hash, exc,
        )
        notices.append(ScheduleNotice(
            code="invalid_schedule",
            severity="warning",
            message=f"Configuração de agendamento inválida: {exc}. O agendamento anterior foi mantido.",
        ))
        return notices

    for sch in existentes:
        await scheduler.schedule_crud.delete(sch.job_id)

    await scheduler.create_schedule(workflow.id_hash, desejado)
    return notices
