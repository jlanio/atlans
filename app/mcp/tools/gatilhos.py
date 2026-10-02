# app/mcp/tools/gatilhos.py
"""
Gatilhos: quando um fluxo dispara sozinho.

É o domínio que faz um fluxo virar rotina. Sem ele, um agente consegue construir
e executar um workflow, mas não consegue responder à pergunta seguinte — "e
agora, como isto roda todo dia às sete?" — nem descobrir por que a rotina que
existe não está rodando.

`triggers:manage` é o escopo que a tela de tokens oferece desde a Fase 0 e que
até aqui **não gatilhava nada**: era um chip no cartão do token sem nenhuma tool
por trás. Este módulo é o que torna aquela promessa verdadeira.

Quatro decisões moldam o módulo:

- **Agendar é executar.** Um schedule de um minuto dispara o fluxo com as
  credenciais do dono, indefinidamente. Por isso as três tools de escrita pedem
  `operator`, o mesmo papel de `run_workflow` — e é a mesma régua que a rota
  REST aplica (`workflow_com_papel(ROLE_OPERATOR)` no `schedules_router`).
- **`list_schedules` lista fluxo inativo.** "Por que este fluxo parou de
  rodar?" é exatamente a pergunta que se faz sobre um fluxo inativo, então ler
  não passa pelo guardião de execução que as escritas usam
  (`ScheduleService._exigir_workflow_ativo`). A consulta é direta no
  `ScheduleCRUD`: a tool já tem o workflow em mãos pelo `carregar_workflow`.
- **`delete_schedule` exige `confirm`.** Apagar um agendamento não tem desfazer
  e o sintoma é silencioso: nada falha, a rotina só deixa de acontecer. O
  parâmetro obriga o agente a ter lido o que vai apagar.
- **Nada do cliente entra num schema por atacado.** `ScheduleBase` carrega
  `workspace_id` e não tinha `extra="forbid"`; as tools montam o objeto campo a
  campo, com lista branca.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import exigir_papel
from app.core.exceptions import AtlasBaseError
from app.core.rbac import ROLE_OPERATOR, ROLE_VIEWER
from app.crud.schedule_crud import ScheduleCRUD
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow
from app.mcp.saida import envelope, iso
from app.mcp.tools.base import anotacoes, ferramenta
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.schedule_service import (
    ScheduleService, validate_schedule_create,
)

_MENSAGEM_PAPEL_LEITURA = "Requer papel 'viewer' ou superior neste workspace."
_MENSAGEM_PAPEL_ESCRITA = (
    "Requer papel 'operator' ou superior neste workspace — agendar é executar."
)

ESTRATEGIAS = ("cron", "interval", "rrule")
UNIDADES = ("seconds", "minutes", "hours", "days")


def _resumo(sch) -> dict:
    """O que identifica e descreve um agendamento.

    Nada aqui é texto livre de pessoa: estratégia e unidade são enums, o fuso é
    um nome de zona, e as expressões são a configuração que o próprio chamador
    mandou. Por isso o item sai no topo e não em `untrusted_data`.
    """
    return {
        "job_id": sch.job_id,
        "strategy": sch.strategy,
        "active": bool(sch.active),
        "timezone": sch.timezone,
        # Só o campo da estratégia em uso: o nó `ScheduleTrigger` envia os
        # defaults de TODAS elas, e o service zera os que não pertencem — mas
        # uma linha antiga pode ter os três preenchidos, e devolver os três
        # faria o agente concluir que há três regras concorrendo.
        **({"cron_expression": sch.cron_expression} if sch.strategy == "cron" else {}),
        **({"interval": sch.interval, "unit": sch.unit}
           if sch.strategy == "interval" else {}),
        **({"rrule_expression": sch.rrule_expression}
           if sch.strategy == "rrule" else {}),
        "next_run_at": iso(sch.next_run_at),
        "last_run_at": iso(sch.last_run_at),
        "retry_count": sch.retry_count or 0,
    }


def _erro_de_config(exc: Exception):
    return erro(
        "validation",
        str(exc),
        "cron precisa de 5 campos (min hora dia mês dia-da-semana); "
        "interval precisa de interval + unit; rrule precisa de rrule_expression",
    )


# ── Leitura ──────────────────────────────────────────────────────────────────


@ferramenta
async def list_schedules(ctx: Context, workflow_id: str) -> dict:
    """Os agendamentos deste workflow — quando ele dispara sozinho.

    Responde as duas perguntas que um fluxo agendado gera: "quando roda?"
    (`next_run_at`) e "por que não rodou?". Para a segunda, olhe nesta ordem:

    1. `workflow_active: false` no topo — o agendador **ignora** agendamento de
       fluxo inativo, por mais correto que ele esteja. É a causa mais comum, e
       nada no agendamento em si a denuncia.
    2. `active: false` no item — o agendamento existe e está desligado.
    3. `next_run_at` no passado — o agendador não passou por ele ainda.

    `timezone` é o fuso em que a expressão é lida: `"0 9 * * *"` em
    `America/Sao_Paulo` dispara às 9h de lá, não às 9h UTC.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
        id_do_fluxo, ativo = wf.id_hash, bool(wf.flag_ative)

        # Direto no CRUD, sem o guardião de execução das escritas: o workflow
        # já veio do `carregar_workflow` acima, e fluxo inativo é listável.
        itens = [_resumo(s) for s in await ScheduleCRUD(db).get_by_workflow_hash(id_do_fluxo)]

    return envelope({
        "workflow_id": id_do_fluxo,
        "workflow_active": ativo,
        "items": itens,
        "total": len(itens),
        **({"hint": (
            "o workflow está inativo: o agendador ignora agendamentos de fluxo "
            "inativo, então nenhum destes vai disparar até set_workflow_active"
        )} if itens and not ativo else {}),
    })


# ── Escrita ──────────────────────────────────────────────────────────────────


@ferramenta
async def create_schedule(
    ctx: Context,
    workflow_id: str,
    strategy: str,
    cron_expression: Optional[str] = None,
    interval: Optional[int] = None,
    unit: Optional[str] = None,
    rrule_expression: Optional[str] = None,
    timezone: Optional[str] = None,
    active: bool = True,
) -> dict:
    """Cria um agendamento: faz o workflow disparar sozinho, sem ninguém pedir.

    Três estratégias, e cada uma usa campos diferentes:

    - `cron` — `cron_expression` com **5 campos** (`min hora dia mês
      dia-da-semana`). `"0 9 * * 1-5"` é 9h nos dias úteis.
    - `interval` — `interval` + `unit` (`seconds`/`minutes`/`hours`/`days`).
    - `rrule` — `rrule_expression` RFC 5545, para calendário
      (`"FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1"` = primeira segunda do mês).

    `timezone` é o fuso em que a expressão é lida; omitido, usa o padrão do
    produto. Um cron sem fuso explícito não é UTC.

    Peça confirmação antes de chamar. Um agendamento dispara o fluxo com as
    credenciais do dono, repetidamente e sem ninguém olhando — um `interval` de
    1 `minutes` num fluxo caro é uma conta que corre sozinha.

    **O workflow precisa estar ativo.** Agendar um fluxo inativo é recusado, e
    não por capricho: o agendador ignora agendamento de fluxo inativo, então a
    linha gravada seria uma promessa que nunca se cumpre. Ative primeiro com
    `set_workflow_active(active=true)`.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    if strategy not in ESTRATEGIAS:
        raise erro("validation", f"strategy deve ser uma de {list(ESTRATEGIAS)}.",
                   "cron para horário, interval para repetição, rrule para calendário")
    if unit is not None and unit not in UNIDADES:
        raise erro("validation", f"unit deve ser uma de {list(UNIDADES)}.")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash

        # A recusa também é do núcleo (`_exigir_workflow_ativo` levanta
        # `WorkflowInactiveError`). Antecipar aqui dá o código e a saída antes
        # de montar e validar a configuração inteira — e a mensagem daqui
        # explica o PORQUÊ, que a do núcleo não tem espaço para dizer.
        if not wf.flag_ative:
            raise erro(
                "workflow_inactive",
                "Este workflow está inativo, e o agendador ignora agendamento de "
                "fluxo inativo — a linha gravada nunca dispararia.",
                "ative com set_workflow_active(workflow_id, active=true) e agende depois",
            )

        # Lista branca, campo a campo. `ScheduleBase` não tem `extra="forbid"` e
        # carrega `workspace_id` — jogar um dict do cliente aqui deixaria ele
        # escolher o tenant do agendamento.
        campos: dict[str, Any] = {"strategy": strategy, "active": bool(active)}
        for nome, valor in (
            ("cron_expression", cron_expression), ("interval", interval),
            ("unit", unit), ("rrule_expression", rrule_expression),
        ):
            if valor is not None:
                campos[nome] = valor
        if timezone:
            campos["timezone"] = timezone

        try:
            config = ScheduleCreate(**campos)
            # A mesma validação que a rota usa, chamada ANTES de gravar.
            validate_schedule_create(config)
        except AtlasBaseError as exc:
            raise _erro_de_config(exc)
        except ValueError as exc:
            # Pydantic e `InvalidScheduleError` caem aqui.
            raise _erro_de_config(exc)

        criado = await ScheduleService(db).create_schedule(id_do_fluxo, config)
        # `create_schedule` não commita; a sessão do MCP faz rollback no finally.
        await db.commit()
        item = _resumo(criado)

    return envelope({"workflow_id": id_do_fluxo, **item})


@ferramenta
async def update_schedule(
    ctx: Context,
    workflow_id: str,
    job_id: str,
    strategy: Optional[str] = None,
    cron_expression: Optional[str] = None,
    interval: Optional[int] = None,
    unit: Optional[str] = None,
    rrule_expression: Optional[str] = None,
    timezone: Optional[str] = None,
    active: Optional[bool] = None,
) -> dict:
    """Altera um agendamento existente. Só os campos enviados mudam.

    Para **pausar sem perder a configuração**, mande `active=false` — é o que se
    quer quase sempre, e não apaga nada. `delete_schedule` é para quando a
    rotina deixou de existir.

    Trocar de estratégia exige mandar os campos da nova: virar `cron` sem
    `cron_expression` é recusado.

    O `job_id` vem de `list_schedules`. Um `job_id` que não pertence a este
    workflow responde `not_found`, e não `forbidden`: dizer "existe, mas não é
    seu" já entregaria que ele existe.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    if strategy is not None and strategy not in ESTRATEGIAS:
        raise erro("validation", f"strategy deve ser uma de {list(ESTRATEGIAS)}.")
    if unit is not None and unit not in UNIDADES:
        raise erro("validation", f"unit deve ser uma de {list(UNIDADES)}.")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash

        campos: dict[str, Any] = {}
        for nome, valor in (
            ("strategy", strategy), ("cron_expression", cron_expression),
            ("interval", interval), ("unit", unit),
            ("rrule_expression", rrule_expression), ("timezone", timezone),
            ("active", active),
        ):
            if valor is not None:
                campos[nome] = valor
        if not campos:
            raise erro(
                "validation", "Nenhum campo para alterar.",
                "mande ao menos um: strategy, cron_expression, interval, unit, "
                "rrule_expression, timezone ou active",
            )

        try:
            mudancas = ScheduleUpdate(**campos)
        except ValueError as exc:
            raise _erro_de_config(exc)

        try:
            atualizado = await ScheduleService(db).update_schedule(
                job_id, mudancas, owner_workflow_hash=id_do_fluxo,
            )
        except AtlasBaseError as exc:
            # `ScheduleNotFoundError` cobre tanto "não existe" quanto "é de
            # outro workflow" — de propósito, para não virar oráculo.
            raise erro(
                "not_found", str(exc),
                "use list_schedules(workflow_id) para ver os job_id deste fluxo",
            )
        await db.commit()
        item = _resumo(atualizado)

    return envelope({"workflow_id": id_do_fluxo, **item})


@ferramenta
async def delete_schedule(
    ctx: Context, workflow_id: str, job_id: str, confirm: bool = False
) -> dict:
    """Apaga um agendamento de vez. Exige `confirm=true`.

    **Antes de apagar, considere `update_schedule(active=false)`**: pausar
    preserva a expressão, o fuso e o histórico, e é reversível com uma chamada.
    Apagar não tem desfazer, e o sintoma é silencioso — nada falha, a rotina só
    deixa de acontecer, e pode levar semanas até alguém reparar.

    Sem `confirm=true` nada é apagado: a resposta descreve o que seria removido,
    para você mostrar a quem pediu antes de repetir a chamada.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "triggers:manage")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_OPERATOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash

        crud = ScheduleCRUD(db)
        alvo = await crud.get(job_id)
        # A mesma regra do service: posse confirmada pelo workflow do path, e
        # `not_found` para os dois casos.
        if alvo is None or alvo.workflow_hash != id_do_fluxo:
            raise erro(
                "not_found", f"Agendamento {job_id} não encontrado neste workflow.",
                "use list_schedules(workflow_id) para ver os job_id deste fluxo",
            )
        item = _resumo(alvo)

        if not confirm:
            return envelope({
                "workflow_id": id_do_fluxo,
                "outcome": "not_confirmed",
                "would_delete": item,
                "hint": (
                    "nada foi apagado. Repita com confirm=true para apagar, ou "
                    "use update_schedule(active=false) para só pausar"
                ),
            })

        await ScheduleService(db).delete_schedule(job_id, owner_workflow_hash=id_do_fluxo)
        await db.commit()

    return envelope({
        "workflow_id": id_do_fluxo,
        "outcome": "deleted",
        "deleted": item,
    })


def registrar(server) -> None:
    """Registra as tools deste domínio."""
    server.tool(
        name="list_schedules",
        title="Agendamentos do fluxo",
        description=(
            "Quando este workflow dispara sozinho: estratégia, expressão, fuso e a próxima "
            "execução. Traz workflow_active no topo, porque o agendador ignora agendamento "
            "de fluxo inativo e nada no agendamento em si denuncia isso."
        ),
        annotations=anotacoes("list_schedules"),
    )(list_schedules)

    server.tool(
        name="create_schedule",
        title="Criar agendamento",
        description=(
            "Faz o workflow disparar sozinho por cron, intervalo ou regra de calendário. "
            "Peça confirmação antes: o fluxo passa a rodar com as credenciais do dono, "
            "repetidamente e sem ninguém olhando."
        ),
        annotations=anotacoes("create_schedule"),
    )(create_schedule)

    server.tool(
        name="update_schedule",
        title="Alterar agendamento",
        description=(
            "Muda só os campos enviados. Para pausar sem perder a configuração, mande "
            "active=false — é o que se quer quase sempre, e é reversível."
        ),
        annotations=anotacoes("update_schedule"),
    )(update_schedule)

    server.tool(
        name="delete_schedule",
        title="Apagar agendamento",
        description=(
            "Remove o agendamento de vez; exige confirm=true. Sem ele, descreve o que seria "
            "apagado e não apaga nada. Apagar não tem desfazer e falha em silêncio: a rotina "
            "só deixa de acontecer."
        ),
        annotations=anotacoes("delete_schedule"),
    )(delete_schedule)
