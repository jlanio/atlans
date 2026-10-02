# tests/unit/test_workflow_duplicate.py
"""Duplicacao de workflow.

A copia fica no MESMO workspace de proposito: `credential_id` na definition so
resolve para quem tem acesso ao workspace (ver credential_loader) e
sub-workflows referenciados precisam viver nele — copiar para outro workspace
produziria um workflow que parece integro e falha ao executar.

O agendamento acompanha DESLIGADO. Duplicar costuma preceder uma edicao, e uma
copia que nasce disparando sozinha dobra a carga e a escrita no Drive sem que
ninguem tenha pedido. O desligamento e feito na propria definition — nao so no
banco — porque `apply_schedule_if_needed` le o `active` do no: mexer so no banco
deixaria o canvas dizendo "ativo" e o schedule desligado.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import WorkflowNameConflictError
from app.services.workflow_service import WorkflowService


WS = "ws-1"
# Quem duplica. O autor é obrigatório: é contra ele que o serviço confere as
# credenciais da cópia (SEG-12).
QUEM = "usr-1"


def _definition(com_schedule=True, conn=None):
    nodes = [{"id": "n1", "name": "WFS", "type": "datasource",
              "properties": {"credential_id": "cred-1", **({"connectionString": conn} if conn else {})}}]
    if com_schedule:
        nodes.insert(0, {
            "id": "t1", "name": "ScheduleTrigger", "type": "trigger",
            "properties": {"strategy": "cron", "cron_expression": "0 6 * * *",
                           "timezone": "America/Cuiaba", "active": True},
        })
    return {"nodes": nodes, "edges": [{"source": "t1", "target": "n1"}]}


def _servico(original, nomes_no_workspace=()):
    """Serviço com o CRUD dublado; `create` devolve o que recebeu."""
    svc = WorkflowService(MagicMock())
    svc.crud = MagicMock()
    svc.crud.get_by_hash = AsyncMock(return_value=original)

    async def _create(name, definition, **kwargs):
        # `name` e argumento reservado do MagicMock (nomeia o proprio mock),
        # entao precisa ser atribuido depois.
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)

    resultado = MagicMock()
    resultado.all.return_value = [(n,) for n in nomes_no_workspace]
    svc.crud.db = MagicMock(execute=AsyncMock(return_value=resultado), rollback=AsyncMock())
    return svc


def _original(definition=None, **kw):
    base = {"id_hash": "wf-1", "workspace_id": WS,
            "definition": definition if definition is not None else _definition()}
    base.update(kw)
    m = MagicMock(**base)
    m.name = "Edificações"      # reservado no construtor do MagicMock
    return m


@pytest.fixture(autouse=True)
def _sem_schedule_real():
    """`apply_schedule_if_needed` toca o banco; o alvo aqui é a definition."""
    with patch("app.services.workflow_service.apply_schedule_if_needed",
               new=AsyncMock()) as m:
        yield m


@pytest.fixture(autouse=True)
def credenciais_de_quem_duplica():
    """A guarda de credenciais (SEG-12) aceitando: o alvo aqui é a cópia, e a
    recusa é provada em test_workflow_credencial_guard.py. A consulta toca a
    tabela de credenciais, que o CRUD dublado não tem."""
    with patch("app.services.workflow_service.assert_credentials_accessible",
               new=AsyncMock(return_value=None)) as m:
        yield m


# ── Nome ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nome_derivado_do_original():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações"


@pytest.mark.asyncio
async def test_desambigua_quando_a_copia_ja_existe():
    """Há UniqueConstraint(name, workspace_id): sem isto, duplicar duas vezes
    devolvia 409 antes de o usuário ver a cópia."""
    svc = _servico(_original(), nomes_no_workspace=["Edificações", "Cópia de Edificações"])

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_desambigua_repetidamente():
    svc = _servico(_original(), nomes_no_workspace=[
        "Cópia de Edificações", "Cópia de Edificações (2)", "Cópia de Edificações (3)",
    ])

    assert (await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)).name == "Cópia de Edificações (4)"


@pytest.mark.asyncio
async def test_nome_explicito_prevalece():
    copia = await _servico(_original()).duplicate_workflow("wf-1", "Teste 2026", duplicated_by=QUEM)

    assert copia.name == "Teste 2026"


@pytest.mark.asyncio
async def test_nome_em_branco_cai_no_derivado():
    copia = await _servico(_original()).duplicate_workflow("wf-1", "   ", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações"


# ── Colisao no INSERT ────────────────────────────────────────────────────────
#
# `_nome_de_copia` LE os nomes ocupados e o INSERT vem depois: entre os dois ha
# uma janela. Duas duplicacoes simultaneas leem o mesmo conjunto e propoem o
# mesmo nome; a segunda bate na restricao. Nenhum teste fazia `crud.create`
# falhar, entao esse caminho ficou descoberto ate virar 409 na tela do usuario.
#
# O `move` ja tratava a mesma corrida (workflow_move_service._aplicar); estes
# testes fixam o tratamento equivalente na duplicacao.


def _conflito(nome: str) -> WorkflowNameConflictError:
    return WorkflowNameConflictError(f"Já existe um workflow chamado '{nome}' neste workspace.")


def _servico_que_falha(original, falhas: int, nomes_no_workspace=()):
    """Como `_servico`, mas `crud.create` levanta conflito nas `falhas` primeiras.

    Os nomes ja tentados entram em `nomes_no_workspace` a cada falha — e o que o
    banco real faria: a proxima leitura enxerga quem causou a colisao.
    """
    svc = _servico(original, nomes_no_workspace=nomes_no_workspace)
    ocupados = list(nomes_no_workspace)
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) <= falhas:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            raise _conflito(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)
    svc.tentativas = tentativas
    return svc


@pytest.mark.asyncio
async def test_colisao_no_insert_e_resolvida_recalculando_o_nome():
    """Primeira aposta e recalcular: "(2)" e melhor nome que um hex aleatorio."""
    svc = _servico_que_falha(_original(), falhas=1)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.tentativas == ["Cópia de Edificações", "Cópia de Edificações (2)"]
    assert copia.name == "Cópia de Edificações (2)"


@pytest.mark.asyncio
async def test_colisao_persistente_cai_no_sufixo_unico():
    """Colidir duas vezes indica corrida real — o hex nao disputa com ninguem."""
    svc = _servico_que_falha(_original(), falhas=2)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert len(svc.tentativas) == 3
    assert copia.name.startswith("Cópia de Edificações (")
    # Sufixo aleatorio, nao o contador: 6 hex entre parenteses.
    sufixo = copia.name.rsplit("(", 1)[1].rstrip(")")
    assert len(sufixo) == 6 and all(c in "0123456789abcdef" for c in sufixo)


@pytest.mark.asyncio
async def test_colisao_nas_tres_tentativas_vira_erro_legivel():
    """Melhor 409 com mensagem propria que IntegrityError cru virando 500."""
    svc = _servico_que_falha(_original(), falhas=99)

    with pytest.raises(WorkflowNameConflictError, match="nome livre para a cópia"):
        await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert len(svc.tentativas) == 3


@pytest.mark.asyncio
async def test_nome_explicito_nao_e_renomeado_na_colisao():
    """Quem digitou o nome merece saber que colidiu.

    Renomear por conta propria criaria "Meu Fluxo (2)" para quem pediu
    "Meu Fluxo" — a colisao aqui e resposta, nao acidente nosso.
    """
    svc = _servico_que_falha(_original(), falhas=1)

    with pytest.raises(WorkflowNameConflictError):
        await svc.duplicate_workflow("wf-1", "Meu Fluxo", duplicated_by=QUEM)

    assert svc.tentativas == ["Meu Fluxo"]


class _OriginalQueExpira:
    """Dublê com a semântica de expiração do SQLAlchemy.

    `MagicMock` responde a qualquer atributo para sempre, então nenhum teste
    baseado nele enxerga o problema real desta retentativa: `create_workflow`
    chama `rollback()` na colisão, e o rollback expira TODO objeto da sessão —
    inclusive o `original`, que nem participou da escrita. Numa AsyncSession,
    ler um atributo expirado não é um SELECT a mais, é `MissingGreenlet`: a
    retentativa devolveria 500 no lugar do 409 que ela existe para evitar.
    """

    def __init__(self, **campos):
        object.__setattr__(self, "_campos", campos)
        object.__setattr__(self, "_expirado", False)

    def expirar(self):
        object.__setattr__(self, "_expirado", True)

    def __getattr__(self, nome):
        if nome.startswith("_"):
            raise AttributeError(nome)
        if object.__getattribute__(self, "_expirado"):
            raise RuntimeError(
                f"leitura de '{nome}' com a sessão expirada — em AsyncSession isto é "
                "MissingGreenlet. Capture os campos do original ANTES da primeira escrita."
            )
        return object.__getattribute__(self, "_campos")[nome]


@pytest.mark.asyncio
async def test_retentativa_nao_le_o_original_depois_do_rollback():
    """Regressão: o retry lia `original.name` e `original.workspace_id` de novo."""
    original = _OriginalQueExpira(
        id_hash="wf-1", workspace_id=WS, name="Edificações", definition=_definition(),
        description="d", params_schema={}, group_id=None, priority=0, notification_url=None,
        # A cópia herda a proveniência do original — lida ANTES da primeira
        # escrita (no bloco de captura), como todos os campos aqui.
        origem="usuario",
    )

    svc = _servico(original)
    ocupados: list[str] = []
    tentativas: list[str] = []

    async def _create(name, definition, **kwargs):
        tentativas.append(name)
        if len(tentativas) == 1:
            ocupados.append(name)
            svc.crud.db.execute.return_value.all.return_value = [(n,) for n in ocupados]
            original.expirar()          # é o que o rollback do SQLAlchemy faz
            raise _conflito(name)
        m = MagicMock(id_hash="novo", definition=definition,
                      workspace_id=kwargs.get("workspace_id"))
        m.name = name
        return m

    svc.crud.create = AsyncMock(side_effect=_create)

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.name == "Cópia de Edificações (2)"
    assert copia.workspace_id == WS      # o workspace sobreviveu à expiração


@pytest.mark.asyncio
async def test_erro_de_outra_natureza_nao_e_engolido_pelo_retry():
    """O retry existe para colisao de NOME; o resto tem de subir intacto."""
    svc = _servico(_original())
    svc.crud.create = AsyncMock(side_effect=RuntimeError("conexão caiu"))

    with pytest.raises(RuntimeError, match="conexão caiu"):
        await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.crud.create.await_count == 1


# ── Autoria ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_copia_e_de_quem_copiou_e_as_credenciais_sao_conferidas_contra_ele(
    credenciais_de_quem_duplica,
):
    svc = _servico(_original())

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    kw = svc.crud.create.await_args.kwargs
    assert (kw["created_by_id"], kw["updated_by_id"]) == (QUEM, QUEM)
    _db, ids, usuario = credenciais_de_quem_duplica.await_args.args
    assert (ids, usuario) == (["cred-1"], QUEM)
    assert credenciais_de_quem_duplica.await_args.kwargs == {"shared_workspace_id": WS}


# ── Workspace ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_copia_fica_no_mesmo_workspace():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert copia.workspace_id == WS


# ── Agendamento ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agendamento_acompanha_desligado():
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    trigger = next(n for n in copia.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is False
    # O resto da configuração fica: o usuário liga sem reconfigurar cron e fuso.
    assert trigger["properties"]["cron_expression"] == "0 6 * * *"
    assert trigger["properties"]["timezone"] == "America/Cuiaba"


@pytest.mark.asyncio
async def test_original_continua_agendado():
    """Regressão: a definition do ORM é observada pelo SQLAlchemy — mutá-la
    marcaria o workflow de ORIGEM como sujo e desligaria o agendamento dele."""
    original = _original()

    await _servico(original).duplicate_workflow("wf-1", duplicated_by=QUEM)

    trigger = next(n for n in original.definition["nodes"] if n["name"] == "ScheduleTrigger")
    assert trigger["properties"]["active"] is True


@pytest.mark.asyncio
async def test_workflow_sem_agendamento_duplica_normalmente():
    svc = _servico(_original(definition=_definition(com_schedule=False)))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert [n["name"] for n in copia.definition["nodes"]] == ["WFS"]


# ── Conteúdo copiado ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_definition_e_copiada_com_as_credenciais():
    """No mesmo workspace o credential_id continua resolvendo."""
    copia = await _servico(_original()).duplicate_workflow("wf-1", duplicated_by=QUEM)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["credential_id"] == "cred-1"


@pytest.mark.asyncio
async def test_connection_string_chega_cifrada_na_copia():
    """O ciclo é decrypt no get, encrypt no create.

    `get_workflow_by_hash` devolve a definition EM CLARO (descriptografa a
    connectionString), e `create_workflow` recifra. A cópia não pode guardar a
    string de conexão em claro no banco.
    """
    from app.core.utils.encryption import encrypt_string

    svc = _servico(_original(definition=_definition(conn=encrypt_string("host=db user=x"))))

    copia = await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    no = next(n for n in copia.definition["nodes"] if n["name"] == "WFS")
    assert no["properties"]["connectionString"].startswith("gAAAA")


@pytest.mark.asyncio
async def test_params_schema_acompanha():
    """Regressão: `create_workflow` só recebia nome/definition/workspace.

    É o params_schema que faz a tela pedir os parâmetros antes de executar
    (handleRunClick no front). Sem ele, a cópia dispara direto e calada, com
    schema vazio — comportamento silenciosamente diferente do original.
    """
    esquema = {"ano": {"type": "number", "required": True}}
    svc = _servico(_original(params_schema=esquema))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    assert svc.crud.create.await_args.kwargs["params_schema"] == esquema


@pytest.mark.asyncio
async def test_configuracao_do_workflow_acompanha():
    svc = _servico(_original(
        description="Valida edificações", group_id="grp-1",
        priority=5, notification_url="https://hook",
    ))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    kw = svc.crud.create.await_args.kwargs
    assert kw["description"] == "Valida edificações"
    assert kw["group_id"] == "grp-1"
    assert kw["priority"] == 5
    assert kw["notification_url"] == "https://hook"


@pytest.mark.asyncio
async def test_pins_e_portal_nao_acompanham():
    """`create_workflow` recebe só nome e definition — pins apontam para runs do
    original e portal publicado não pode se propagar sem alguém pedir."""
    svc = _servico(_original(pinned_outputs={"n1": "art-1"}, portal_access="public"))

    await svc.duplicate_workflow("wf-1", duplicated_by=QUEM)

    _nome, _definition = svc.crud.create.await_args.args[:2]
    assert "pinned_outputs" not in svc.crud.create.await_args.kwargs
    assert "portal_access" not in svc.crud.create.await_args.kwargs
