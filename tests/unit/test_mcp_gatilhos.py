# tests/unit/test_mcp_gatilhos.py
"""
As quatro tools de gatilho, e o fuso padrão que elas herdam.

O arquivo tem duas metades com propósitos diferentes:

- **O fuso** — a invariante de que a mudança no fallback do agendador NÃO
  recria schedule nenhum. É dela que a decisão do dono depende: recriar zera o
  `next_run_at` e pula a ocorrência do dia, e isso aconteceria em cada workflow
  agendado no primeiro save depois do deploy.
- **As tools** — as portas (escopo, papel, workspace), o que a descrição promete
  e o formato da resposta.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO
from app.core.utils.encryption import encrypt_workflow_connections
from app.mcp import infra
from app.mcp.tools.gatilhos import (
    create_schedule, delete_schedule, list_schedules, update_schedule,
)
from app.models.base import Base
from app.models.models import Schedule, Workflow
from app.models.workspace_member import WorkspaceMember
from app.schemas.schedule import ScheduleBase
from tests.unit._mcp_harness import (
    TABELAS, criar_usuario, criar_workspace, ctx_falso, escopo_falso,
)

WS_1 = "11111111-1111-4111-8111-111111111111"
WS_2 = "22222222-2222-4222-8222-222222222222"
WF_1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
WF_2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
WF_INATIVO = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


def ctx(**kw):
    """`ctx` com leitura e gestão de gatilhos sobre o workspace 1."""
    campos = {
        "scopes": {"workflows:read", "triggers:manage"},
        "workspace_ids": {WS_1},
    }
    campos.update(kw)
    return ctx_falso(escopo_falso(**campos))


def _definicao() -> dict:
    return {
        "nodes": [{"id": "n1", "type": "action", "name": "Buffer", "properties": {}}],
        "edges": [],
    }


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _sessao():
        async with fabrica() as db:
            try:
                yield db
            finally:
                await db.rollback()

    monkeypatch.setattr(infra, "sessao", _sessao)

    async with fabrica() as db:
        await criar_usuario(db, "usr-1", "ana")
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, WS_1, "usr-1", "Principal")
        await criar_workspace(db, WS_2, "usr-2", "De outra conta")
        db.add_all([
            Workflow(id_hash=WF_1, name="Recorte", workspace_id=WS_1,
                     definition=encrypt_workflow_connections(_definicao()), flag_ative=True),
            Workflow(id_hash=WF_2, name="Alheio", workspace_id=WS_2,
                     definition=encrypt_workflow_connections(_definicao()), flag_ative=True),
            Workflow(id_hash=WF_INATIVO, name="Parado", workspace_id=WS_1,
                     definition=encrypt_workflow_connections(_definicao()), flag_ative=False),
        ])
        await db.commit()
    try:
        yield fabrica
    finally:
        await engine.dispose()


async def _semear(fabrica, workflow_hash, job_id="job-semeado", **campos):
    """Um schedule gravado direto, sem passar pelas tools.

    Necessário em dois casos que as tools recusam de propósito: fluxo inativo
    (`create_schedule` responde `workflow_inactive`) e fluxo de outra conta
    (inalcançável pelo escopo do teste).
    """
    campos.setdefault("strategy", "cron")
    campos.setdefault("cron_expression", "0 9 * * *")
    campos.setdefault("timezone", FUSO_PADRAO_DO_AGENDAMENTO)
    campos.setdefault("active", True)
    campos.setdefault("retry_count", 0)
    async with fabrica() as db:
        db.add(Schedule(id_hash=job_id, workflow_hash=workflow_hash,
                        job_id=job_id, **campos))
        await db.commit()
    return job_id


async def _job_ids(fabrica, workflow_hash=WF_1):
    async with fabrica() as db:
        linhas = (await db.execute(
            select(Schedule).where(Schedule.workflow_hash == workflow_hash)
        )).scalars().all()
        return [s.job_id for s in linhas]


# ── O fuso: a invariante de que nada é recriado ──────────────────────────────


def test_o_no_e_a_constante_dizem_o_MESMO_fuso():
    """É a invariante de que a decisão do dono depende, e ela é frágil.

    O nó não pode importar a constante — `flow/` só importa de `app/` dentro de
    funções, porque o executor empacota `flow/` sem `app/`, e `description()`
    roda no import. Então o valor está escrito duas vezes, e só este teste
    impede que divirjam.

    Divergir não dá erro: faz o PRÓXIMO SAVE de cada workflow agendado ver
    `timezone` diferente em `_mesma_configuracao`, recriar o schedule, zerar o
    `next_run_at` e **pular a ocorrência do dia**. Silenciosamente, em todos.
    """
    from flow.registry import NODE_REGISTRY

    propriedades = NODE_REGISTRY["ScheduleTrigger"].description()["properties"]
    do_no = next(p for p in propriedades if p["name"] == "timezone")["default"]

    assert do_no == FUSO_PADRAO_DO_AGENDAMENTO


def test_o_schema_herda_a_mesma_constante():
    """Era `America/Cuiaba` — mesmo offset, nome diferente. Dois nomes para a
    mesma intenção foi como o terceiro valor (UTC) passou despercebido."""
    assert ScheduleBase.model_fields["timezone"].default == FUSO_PADRAO_DO_AGENDAMENTO


def test_mudar_o_fallback_nao_recria_nenhum_schedule():
    """A prova direta da decisão: `_mesma_configuracao` continua concordando.

    O levantamento em produção (2026-09-15) mediu 10 agendamentos ativos, TODOS
    com o fuso padrão de então gravado e NENHUM com a coluna nula — então o
    fallback novo não move disparo nenhum hoje. Este teste é o que garante que
    continue assim quando alguém mexer na constante.
    """
    from app.core.scheduling.hooks import _mesma_configuracao

    gravado = SimpleNamespace(
        strategy="cron", timezone=FUSO_PADRAO_DO_AGENDAMENTO,
        cron_expression="0 9 * * *", interval=None, unit=None,
        rrule_expression=None,
    )
    # O que o nó envia ao salvar o workflow.
    desejado = ScheduleBase(
        strategy="cron", cron_expression="0 9 * * *",
        interval=60, unit="minutes",
    )

    assert _mesma_configuracao(gravado, desejado) is True


@pytest.mark.parametrize("valor", [None, "", "   ", "Fuso/Inexistente"])
def test_o_agendador_nao_cai_mais_em_UTC(valor):
    """Quatro horas de diferença entre o que a tela diz e a hora do disparo.

    A pergunta que `_tz_of` responde é uma só — "não sei o fuso deste
    agendamento, qual uso?" — e as duas saídas dela (coluna vazia, valor
    ilegível) davam em UTC, que é o default do `datetime` e não uma escolha.
    """
    from app.core.async_scheduler import AsyncScheduler

    tz = AsyncScheduler()._tz_of(SimpleNamespace(timezone=valor, job_id="j1"))

    assert str(tz) == FUSO_PADRAO_DO_AGENDAMENTO


def test_fuso_valido_e_respeitado():
    """O fallback não pode ter virado um "sempre o padrão"."""
    from app.core.async_scheduler import AsyncScheduler

    tz = AsyncScheduler()._tz_of(SimpleNamespace(timezone="Europe/Lisbon", job_id="j1"))

    assert str(tz) == "Europe/Lisbon"


# ── list_schedules ───────────────────────────────────────────────────────────


async def test_sem_agendamento_a_lista_vem_vazia(banco):
    saida = await list_schedules(ctx(), WF_1)

    assert saida["total"] == 0
    assert saida["workflow_active"] is True
    assert "hint" not in saida


async def test_o_fluxo_inativo_e_LISTAVEL_e_nao_um_erro(banco):
    """Fluxo inativo é exatamente onde alguém pergunta "por que isto parou de
    rodar". Se a leitura passar pelo guardião de execução das escritas
    (`ScheduleService._exigir_workflow_ativo`), este teste cai com
    `WorkflowInactiveError`.

    O schedule é semeado direto no banco porque `create_schedule` recusa fluxo
    inativo — e é justamente essa assimetria que o par de testes prende: LER o
    agendamento de um fluxo parado tem de funcionar; CRIAR, não.
    """
    await _semear(banco, WF_INATIVO)

    saida = await list_schedules(ctx(), WF_INATIVO)

    assert saida["total"] == 1
    assert saida["workflow_active"] is False
    # E diz POR QUE não vai disparar — a causa mais comum, invisível no item.
    assert "inativo" in saida["hint"]


async def test_so_o_campo_da_estrategia_em_uso_sai_na_resposta(banco):
    """Uma linha antiga pode ter os três preenchidos; devolver os três faria o
    agente concluir que há três regras concorrendo."""
    await create_schedule(ctx(), WF_1, "interval", interval=30, unit="minutes")

    item = (await list_schedules(ctx(), WF_1))["items"][0]

    assert item["interval"] == 30 and item["unit"] == "minutes"
    assert "cron_expression" not in item
    assert "rrule_expression" not in item


# ── create_schedule ──────────────────────────────────────────────────────────


async def test_criar_cron_grava_e_devolve_o_job_id(banco):
    saida = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * 1-5")

    assert saida["strategy"] == "cron"
    assert saida["cron_expression"] == "0 9 * * 1-5"
    assert saida["job_id"] in await _job_ids(banco)


async def test_o_fuso_omitido_vira_o_padrao_do_produto(banco):
    """Um cron sem fuso explícito não é UTC — é o que a descrição promete."""
    saida = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    assert saida["timezone"] == FUSO_PADRAO_DO_AGENDAMENTO


@pytest.mark.parametrize("kwargs, esperado, motivo", [
    ({"strategy": "cron"}, "5 campos", "cron sem expressão"),
    ({"strategy": "cron", "cron_expression": "0 9 * *"}, "5 campos", "cron com 4 campos"),
    ({"strategy": "cron", "cron_expression": ""}, "5 campos", "cron com expressão vazia"),
    ({"strategy": "interval", "interval": 5}, "interval + unit", "interval sem unit"),
    ({"strategy": "rrule"}, "rrule_expression", "rrule sem expressão"),
    # Estas duas têm receita PRÓPRIA: a tool lista os valores aceitos, coisa
    # que o núcleo não faz — `InvalidScheduleError` diz "Strategy inválida:
    # xyz" e para por aí, deixando o agente tentar de novo no escuro.
    ({"strategy": "nao_existe"}, "'cron', 'interval', 'rrule'", "estratégia desconhecida"),
    ({"strategy": "interval", "interval": 5, "unit": "luas"},
     "'seconds', 'minutes', 'hours', 'days'", "unidade inválida"),
])
async def test_config_invalida_vira_validation_COM_a_receita(banco, kwargs, esperado, motivo):
    """O código sozinho não é o ponto — a MENSAGEM é.

    Medido por mutação: apagar a guarda de estratégia e a chamada explícita de
    `validate_schedule_create` NÃO derrubava este teste, porque o núcleo valida
    de novo lá dentro e o `@ferramenta` mapeia o `InvalidScheduleError` para
    `validation` do mesmo jeito. Ou seja, as guardas da tool são redundantes
    quanto a RECUSAR.

    O que só elas fazem é dizer o que é válido: `InvalidScheduleError` responde
    "Strategy inválida: xyz" e para por aí, sem listar as três. Um agente lendo
    isso tenta de novo no escuro. Por isso a asserção é sobre o `hint`.
    """
    with pytest.raises(ToolError) as exc:
        await create_schedule(ctx(), WF_1, **kwargs)

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "validation", motivo
    # A asserção é sobre o CORPO inteiro (mensagem + dica): é ali que mora o
    # que a tool acrescenta ao núcleo, e é isso que a mutação apaga.
    assert esperado in json.dumps(detalhe, ensure_ascii=False), motivo


async def test_nada_e_gravado_quando_a_config_e_invalida(banco):
    """A validação roda ANTES do insert — senão sobra linha pela metade."""
    with pytest.raises(ToolError):
        await create_schedule(ctx(), WF_1, "cron", cron_expression="invalido")

    assert await _job_ids(banco) == []


async def test_criar_em_fluxo_inativo_e_recusado_com_a_saida(banco):
    """O núcleo já recusava, mas a rota REST convertia num 400 genérico
    ("Não foi possível criar o agendamento") que não diz o que fazer.

    A tool antecipa a recusa e nomeia a saída — o agente precisa saber que o
    caminho é `set_workflow_active`, não tentar outra expressão.
    """
    with pytest.raises(ToolError) as exc:
        await create_schedule(ctx(), WF_INATIVO, "cron", cron_expression="0 9 * * *")

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "workflow_inactive"
    assert "set_workflow_active" in detalhe["hint"]
    assert await _job_ids(banco, WF_INATIVO) == []


async def test_o_cliente_nao_escolhe_o_workspace_do_agendamento(banco):
    """`ScheduleBase` carrega `workspace_id` e não tinha `extra="forbid"`.

    A tool monta o objeto campo a campo, então não há por onde passar. O teste
    afirma a ausência do parâmetro: acrescentá-lo à assinatura quebra aqui.
    """
    import inspect

    assinatura = inspect.signature(create_schedule)
    assert "workspace_id" not in assinatura.parameters


# ── update_schedule ──────────────────────────────────────────────────────────


async def test_pausar_preserva_a_configuracao(banco):
    """`active=false` é o que se quer quase sempre, e o oposto de apagar."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await update_schedule(ctx(), WF_1, criado["job_id"], active=False)

    assert saida["active"] is False
    assert saida["cron_expression"] == "0 9 * * *"


async def test_religar_pelo_tool_zera_next_run_at(banco):
    """A mesma correção do PUT REST vale pela tool: religar um agendamento
    pausado com `next_run_at` no passado zera o horário — senão o agendador o
    dispararia na hora de virar o interruptor. Semeado direto porque o schedule
    precisa nascer pausado e com uma próxima parada no passado."""
    from datetime import datetime

    job = await _semear(
        banco, WF_1, job_id="j-religar", active=False,
        next_run_at=datetime(2020, 1, 1, 9, 0),
    )

    saida = await update_schedule(ctx(), WF_1, job, active=True)
    assert saida["active"] is True

    async with banco() as db:
        sch = (await db.execute(
            select(Schedule).where(Schedule.job_id == job)
        )).scalars().one()
        assert sch.next_run_at is None


async def test_so_os_campos_enviados_mudam(banco):
    criado = await create_schedule(
        ctx(), WF_1, "cron", cron_expression="0 9 * * *", timezone="Europe/Lisbon",
    )

    saida = await update_schedule(ctx(), WF_1, criado["job_id"], cron_expression="30 7 * * *")

    assert saida["cron_expression"] == "30 7 * * *"
    assert saida["timezone"] == "Europe/Lisbon"


async def test_update_sem_nenhum_campo_e_recusado(banco):
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    with pytest.raises(ToolError) as exc:
        await update_schedule(ctx(), WF_1, criado["job_id"])

    assert corpo(exc.value)["code"] == "validation"


async def test_job_id_de_outro_workflow_responde_not_found(banco):
    """`not_found` e não `forbidden`: dizer "existe, mas não é seu" já entrega
    que ele existe. É a mesma regra do service, herdada do conserto de IDOR."""
    doutro = await _semear(banco, WF_2, job_id="job-do-vizinho")

    with pytest.raises(ToolError) as exc:
        await update_schedule(ctx(), WF_1, doutro, active=False)

    assert corpo(exc.value)["code"] == "not_found"


# ── delete_schedule ──────────────────────────────────────────────────────────


async def test_sem_confirm_nada_e_apagado_e_a_resposta_descreve_o_alvo(banco):
    """Apagar não tem desfazer e o sintoma é silencioso: nada falha, a rotina
    só deixa de acontecer."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await delete_schedule(ctx(), WF_1, criado["job_id"])

    assert saida["outcome"] == "not_confirmed"
    assert saida["would_delete"]["cron_expression"] == "0 9 * * *"
    assert await _job_ids(banco) == [criado["job_id"]]


async def test_com_confirm_apaga(banco):
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")

    saida = await delete_schedule(ctx(), WF_1, criado["job_id"], confirm=True)

    assert saida["outcome"] == "deleted"
    assert await _job_ids(banco) == []


async def test_apagar_o_que_nao_existe_responde_not_found(banco):
    with pytest.raises(ToolError) as exc:
        await delete_schedule(ctx(), WF_1, "nao-existe", confirm=True)

    assert corpo(exc.value)["code"] == "not_found"


async def test_o_confirm_nao_pode_vazar_agendamento_alheio(banco):
    """A posse é conferida ANTES do `confirm`, senão o ramo de descrição vira
    um oráculo: sem apagar nada, ele contaria a configuração do vizinho."""
    doutro = await _semear(banco, WF_2, job_id="job-do-vizinho")

    with pytest.raises(ToolError) as exc:
        await delete_schedule(ctx(), WF_1, doutro)

    assert corpo(exc.value)["code"] == "not_found"


# ── As portas ────────────────────────────────────────────────────────────────


async def test_ler_agendamento_nao_exige_escopo_de_gestao(banco):
    """Paridade com `get_run`: quem só acompanha não precisa de poder para
    mexer. A rota REST também só pede pertencimento para listar."""
    so_leitura = ctx(scopes={"workflows:read"})

    assert (await list_schedules(so_leitura, WF_1))["total"] == 0


@pytest.mark.parametrize("nome", ["create_schedule", "update_schedule", "delete_schedule"])
async def test_escrever_exige_triggers_manage(banco, nome):
    from app.mcp.tools import gatilhos as modulo

    magro = ctx(scopes={"workflows:read", "workflows:write"})
    chamadas = {
        "create_schedule": lambda: modulo.create_schedule(magro, WF_1, "cron",
                                                          cron_expression="0 9 * * *"),
        "update_schedule": lambda: modulo.update_schedule(magro, WF_1, "j", active=False),
        "delete_schedule": lambda: modulo.delete_schedule(magro, WF_1, "j", confirm=True),
    }
    with pytest.raises(ToolError) as exc:
        await chamadas[nome]()

    detalhe = corpo(exc.value)
    assert detalhe["code"] == "forbidden_scope"
    assert "triggers:manage" in json.dumps(detalhe)


async def test_operator_e_o_piso_para_agendar_e_nao_editor(banco):
    """AGENDAR É EXECUTAR: um schedule de um minuto dispara o fluxo com as
    credenciais do dono, indefinidamente. `editor` não basta — é a mesma régua
    de `run_workflow`, e a mesma que a rota REST aplica."""
    async with banco() as db:
        db.add(WorkspaceMember(workspace_id=WS_1, user_id="usr-2", role="editor"))
        await db.commit()

    editor = ctx_falso(escopo_falso(
        user_id="usr-2", username="bruno",
        scopes={"workflows:read", "triggers:manage"}, workspace_ids={WS_1},
    ))

    # Ler, pode.
    assert (await list_schedules(editor, WF_1))["total"] == 0
    # Agendar, não.
    with pytest.raises(ToolError) as exc:
        await create_schedule(editor, WF_1, "cron", cron_expression="0 9 * * *")
    assert corpo(exc.value)["code"] == "forbidden"


@pytest.mark.parametrize("nome", [
    "list_schedules", "create_schedule", "update_schedule", "delete_schedule",
])
async def test_fluxo_de_outra_conta_e_inalcancavel(banco, nome):
    from app.mcp.tools import gatilhos as modulo

    chamadas = {
        "list_schedules": lambda: modulo.list_schedules(ctx(), WF_2),
        "create_schedule": lambda: modulo.create_schedule(ctx(), WF_2, "cron",
                                                          cron_expression="0 9 * * *"),
        "update_schedule": lambda: modulo.update_schedule(ctx(), WF_2, "j", active=False),
        "delete_schedule": lambda: modulo.delete_schedule(ctx(), WF_2, "j", confirm=True),
    }
    with pytest.raises(ToolError) as exc:
        await chamadas[nome]()

    assert corpo(exc.value)["code"] in ("not_found", "forbidden")


async def test_nenhuma_resposta_carrega_a_definition_nem_a_credencial(banco):
    """As quatro carregam o workflow; `decifrar=False` é o que impede o blob
    cifrado de chegar até aqui."""
    criado = await create_schedule(ctx(), WF_1, "cron", cron_expression="0 9 * * *")
    respostas = [
        json.dumps(criado),
        json.dumps(await list_schedules(ctx(), WF_1)),
        json.dumps(await update_schedule(ctx(), WF_1, criado["job_id"], active=False)),
        json.dumps(await delete_schedule(ctx(), WF_1, criado["job_id"], confirm=True)),
    ]

    for resposta in respostas:
        assert "gAAAA" not in resposta
        assert "definition" not in resposta
