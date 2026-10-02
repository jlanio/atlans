# app/services/schedule_service.py
# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.schedule_crud import ScheduleCRUD
from app.schemas.schedule import ScheduleCreate
from app.models.models import Schedule, Workflow
from app.core.exceptions import (  # noqa: F401 — ScheduleNotFoundError re-exportado para compatibilidade
    ScheduleNotFoundError,
    InvalidScheduleError,
    WorkflowNotFoundError,
    WorkflowInactiveError,
)


def campos_de_ativacao(ativar: bool) -> dict:
    """Campos a gravar no Schedule ao ligar/desligar o agendamento.

    Religar zera `next_run_at` de propósito. Enquanto o agendamento esteve
    desligado, o scheduler não o processou e o horário ficou parado no passado —
    religar sem zerar faria `_process_schedule` ver `now >= next_run_at` e
    disparar o workflow na hora, como efeito colateral invisível de mexer num
    switch. Com NULL ele recalcula a próxima ocorrência FUTURA e só então
    dispara.

    Fonte canônica dos dois caminhos que ligam/desligam sem passar pela
    definition: o hook (`core/scheduling/hooks.py`, que importa daqui) e o
    `update_schedule` abaixo (a rota REST e a tool MCP).
    """
    return {"active": True, "next_run_at": None} if ativar else {"active": False}


_CAMPOS_DE_HORARIO = ("strategy", "cron_expression", "interval", "unit", "rrule_expression", "timezone")


def _horario_mudou(updates: dict, sch: Schedule) -> bool:
    """True se algum campo de temporização PRESENTE em `updates` difere do valor
    gravado no `sch`.

    Compara só os campos que o caller de fato enviou (o dict vem de
    `ScheduleUpdate.dict(exclude_unset=True)`), então re-salvar o mesmo horário —
    ou editar um campo não-temporal — não conta como mudança.
    """
    return any(
        campo in updates and updates[campo] != getattr(sch, campo)
        for campo in _CAMPOS_DE_HORARIO
    )


def _como_utc(valor: Optional[datetime]) -> Optional[datetime]:
    """`next_run_at`/`last_run_at` são gravados UTC-NAIVE (ver `_to_utc_naive` no
    agendador). Sem o tzinfo o Pydantic serializa sem offset e a web lê a hora
    como local. Mesma normalização de `workflow_service._como_utc` — duplicada de
    propósito: importá-la de lá fecharia um ciclo (workflow_service já importa
    deste módulo)."""
    if valor is None or valor.tzinfo is not None:
        return valor
    return valor.replace(tzinfo=timezone.utc)


async def listar_agendamentos_de(
    db: AsyncSession, workspace_ids: List[str], *, limit: int = 200, offset: int = 0
) -> List[dict]:
    """Todos os agendamentos dos workspaces do usuário, um por linha (não um por
    fluxo, como o resumo de Projetos). Para o painel "Meu → Agendamentos" da Home.

    NÃO filtra `Workflow.origem`, ao contrário das listagens de Projetos — e a
    divergência é deliberada. Um fluxo do assistente que está AGENDADO dispara
    execução sozinho, gasta cota e custa dinheiro; escondê-lo aqui também o
    deixaria sem nenhuma tela onde possa ser visto ou pausado. Por isso ele
    aparece com o selo de origem (a web o desenha) em vez de sumir. O lado que
    falta alinhar é o de Projetos, que tem o parâmetro `assistente` na rota mas
    ainda não tem o interruptor na tela.

    SELECT de COLUNAS, nunca do objeto `Schedule`: `Schedule.workflow` é
    `lazy='raise'`, e trazer o objeto arriscaria um acesso ao relacionamento que
    levantaria. O JOIN com `Workflow` traz nome e `flag_ative` na mesma query
    (o `active` do schedule e o `flag_ative` do fluxo são as DUAS causas de
    "pausado" que a web distingue). Filtra por `Workflow.workspace_id` — nunca
    por `Schedule.workspace_id`, que o `create` não escreve.

    Ordem: ativos primeiro, depois por próxima execução (nulos por último — um
    agendamento recém-criado sem `next_run_at` ainda não some do topo dos ativos).
    """
    if not workspace_ids:
        return []
    stmt = (
        select(
            Schedule.job_id, Schedule.id_hash, Schedule.active, Schedule.strategy,
            Schedule.cron_expression, Schedule.interval, Schedule.unit,
            Schedule.rrule_expression, Schedule.timezone,
            Schedule.next_run_at, Schedule.last_run_at, Schedule.retry_count,
            Schedule.workflow_hash,
            Workflow.name.label("workflow_name"),
            Workflow.flag_ative, Workflow.workspace_id, Workflow.origem,
        )
        .join(Workflow, Workflow.id_hash == Schedule.workflow_hash)
        .where(
            Workflow.deleted_at.is_(None),
            Workflow.workspace_id.in_(workspace_ids),
        )
        .order_by(
            Schedule.active.desc(),
            Schedule.next_run_at.asc().nulls_last(),
            # Terceiro critério de desempate: sem ele, dois agendamentos com o
            # mesmo `active`/`next_run_at` podem trocar de página entre requests.
            Schedule.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    linhas = (await db.execute(stmt)).mappings().all()
    return [
        {
            "job_id": r["job_id"],
            "id_hash": r["id_hash"],
            "active": bool(r["active"]),
            "strategy": r["strategy"],
            "cron_expression": r["cron_expression"],
            "interval": r["interval"],
            "unit": r["unit"],
            "rrule_expression": r["rrule_expression"],
            "timezone": r["timezone"],
            "next_run_at": _como_utc(r["next_run_at"]),
            "last_run_at": _como_utc(r["last_run_at"]),
            "retry_count": r["retry_count"],
            "workflow_id": r["workflow_hash"],
            "workflow_name": r["workflow_name"],
            "flag_ative": bool(r["flag_ative"]),
            "workspace_id": r["workspace_id"],
            "origem": r["origem"],
        }
        for r in linhas
    ]


def validate_schedule_create(schedule_in: ScheduleCreate) -> None:
    """Valida uma config de agendamento SEM efeitos colaterais (raise se inválida).

    Espelha exatamente as checagens de `create_schedule` (profundidade rasa: só
    presença dos campos e 5 campos no cron — a validade sintática fina fica com
    croniter/dateutil no scheduler, que já trata erro sem derrubar o schedule).

    Existe separada para que `apply_schedule_if_needed` possa recusar uma config
    inválida ANTES de apagar o schedule atual. Antes, a validação só acontecia
    dentro de `create_schedule` — depois do delete dos existentes —, então uma
    expressão inválida apagava o agendamento e o deixava sem substituto (a
    exceção é engolida pelo chamador: o usuário via "salvo" e o cron sumia).
    """
    if schedule_in.strategy not in ("cron", "interval", "rrule"):
        raise InvalidScheduleError(f"Strategy inválida: {schedule_in.strategy}")

    if schedule_in.strategy == "cron":
        if not schedule_in.cron_expression:
            raise InvalidScheduleError("cron_expression é obrigatório para strategy='cron'")
        if len(schedule_in.cron_expression.strip().split()) != 5:
            raise InvalidScheduleError("cron_expression deve ter 5 campos: min hour day month dow")
    elif schedule_in.strategy == "interval":
        if schedule_in.interval is None or schedule_in.unit is None:
            raise InvalidScheduleError("Interval strategy requer interval e unit")
    elif schedule_in.strategy == "rrule":
        if not schedule_in.rrule_expression:
            raise InvalidScheduleError("rrule_expression é obrigatório para strategy='rrule'")


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.schedule_crud = ScheduleCRUD(db)

    async def _buscar_workflow(self, id_hash: str) -> Workflow:
        """O workflow, exista ele ativo ou não. NÃO autoriza nada.

        Quem autoriza é o chamador — as rotas passam por
        `workflow_com_papel(ROLE_OPERATOR)` antes de chegar aqui. Esta consulta
        é a segunda leitura, feita só para ter o objeto em mãos.
        """
        stmt = select(Workflow).where(Workflow.id_hash == id_hash)
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow '{id_hash}' não encontrado.")
        return workflow

    async def _exigir_workflow_ativo(self, id_hash: str) -> Workflow:
        """Idem, mas recusa fluxo desativado — para quem vai ESCREVER.

        `WorkflowInactiveError` (409), e não `ValueError`: o `ValueError` cru
        não tem handler (`app/main.py` registra `AtlasBaseError` e um
        `Exception` genérico), então ele virava **500** com mensagem de erro
        interno para uma recusa que é de domínio.
        """
        workflow = await self._buscar_workflow(id_hash)
        if not workflow.flag_ative:
            raise WorkflowInactiveError(
                f"Workflow '{id_hash}' está desativado. Ative-o para gerenciar agendamentos."
            )
        return workflow

    async def create_schedule(self, id_hash: str, schedule_in: ScheduleCreate) -> Schedule:
        workflow = await self._exigir_workflow_ativo(id_hash)

        # Fonte única da validação (também usada por apply_schedule_if_needed
        # ANTES de apagar o schedule anterior).
        validate_schedule_create(schedule_in)

        # Zera os campos que não pertencem à estratégia escolhida — o nó
        # ScheduleTrigger envia os defaults de todas elas.
        if schedule_in.strategy == "cron":
            schedule_in.interval = None
            schedule_in.unit = None
            schedule_in.rrule_expression = None
        elif schedule_in.strategy == "interval":
            schedule_in.cron_expression = None
            schedule_in.rrule_expression = None
        elif schedule_in.strategy == "rrule":
            schedule_in.cron_expression = None
            schedule_in.interval = None
            schedule_in.unit = None

        job_id = str(uuid4())
        sch = await self.schedule_crud.create(
            id_hash=workflow.id_hash,
            workflow_hash=workflow.id_hash,
            strategy=schedule_in.strategy,
            interval=schedule_in.interval,
            unit=schedule_in.unit,
            cron_expression=schedule_in.cron_expression,
            rrule_expression=getattr(schedule_in, "rrule_expression", None),
            timezone=schedule_in.timezone,
            active=schedule_in.active,
            job_id=job_id,
        )
        # O AsyncScheduler recarrega os schedules do banco no proprio loop —
        # nao ha registro em processo a fazer aqui.
        return sch

    async def update_schedule(
        self, job_id: str, schedule_in: ScheduleCreate, owner_workflow_hash: str,
    ) -> Schedule:
        sch = await self.schedule_crud.get(job_id)
        # SEG (IDOR): schedules sao resolvidos por job_id global. A rota so
        # autoriza o workflow do path — sem confirmar que o schedule pertence a
        # ele, um usuario apontava DELETE/PUT de um workflow proprio para o
        # job_id de outro tenant. 404 (nao 403) para nao revelar existencia.
        #
        # `owner_workflow_hash` era opcional, e com `None` a confirmacao acima
        # era PULADA — a defesa descrita neste comentario ficava desligada por
        # omissao. Ninguem usava o atalho (as duas rotas sempre passaram o dono),
        # e agora esquece-lo quebra na chamada em vez de abrir o IDOR de volta.
        if not sch or sch.workflow_hash != owner_workflow_hash:
            raise ScheduleNotFoundError(f"Schedule {job_id} não encontrado.")

        updates = schedule_in.dict(exclude_unset=True)
        # Religar (pausado -> ativo) zera `next_run_at`: sem isto, o horário
        # parado no passado faria o agendador disparar na hora de virar o
        # interruptor. Cobre a rota REST (PUT .../schedules/{job}) e a tool MCP
        # `update_schedule`, que chamam ambas este método. Só quando de fato há
        # transição para ativo — reeditar um schedule já ativo não deve zerar.
        if updates.get("active") is True and not sch.active:
            updates.update(campos_de_ativacao(True))
        # Mudar o HORÁRIO (strategy/cron/interval/unit/rrule/timezone) também zera
        # `next_run_at`, mesmo num schedule que segue ativo: o valor gravado foi
        # calculado da expressão ANTIGA, então mantê-lo faria a próxima ocorrência
        # sair no horário velho uma vez, e uma troca de frequência ficaria atrasada
        # até o horário antigo passar. `None` NÃO dispara na hora — igual à
        # ativação, `_process_schedule` recomputa a próxima ocorrência FUTURA e só
        # então dispara. Editar um campo não-temporal (ou re-salvar o mesmo
        # horário) não mexe em `next_run_at`.
        elif _horario_mudou(updates, sch):
            updates["next_run_at"] = None
        return await self.schedule_crud.update_by_id(job_id, updates)

    async def delete_schedule(self, job_id: str, owner_workflow_hash: str) -> None:
        # Mesma regra e mesmo motivo do `update_schedule` acima.
        sch = await self.schedule_crud.get(job_id)
        if not sch or sch.workflow_hash != owner_workflow_hash:
            raise ScheduleNotFoundError(f"Schedule {job_id} não encontrado.")

        await self.schedule_crud.delete(job_id)

    async def delete_all_schedules_for_workflow(self, id_hash: str) -> None:
        """
        Remove todos os agendamentos do workflow com id_hash informado.
        """
        schedules = await self.schedule_crud.get_by_workflow_hash(id_hash)
        for sch in schedules:
            await self.schedule_crud.delete(sch.job_id)

   