# tests/integration/test_listagem_marca_subfluxo.py
"""
A listagem de projetos distingue um sub-fluxo de um workflow comum.

Um sub-fluxo existe para ser CHAMADO por outro: declara `SubWorkflowOutput` e,
em geral, nao tem gatilho proprio. Na lista ele era indistinguivel — mesmo card,
mesmo botao de executar, que dispara um run que nao faz o que se espera.

A marca e uma expressao SQL sobre a coluna `definition`, do mesmo feitio da que
ja existe para `has_publish_map`: sem coluna nova, sem migration, e sem trazer o
JSON inteiro para o Python a cada listagem.

O teste sobe a tabela real num SQLite de memoria e roda a consulta de verdade —
uma asercao sobre o texto do SQL nao provaria que a coluna sai preenchida.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.crud.workflow_crud import WorkflowCRUD
from app.models.models import Workflow
from app.schemas.workflow import WorkflowListItem

SO_SAIDA = {
    "nodes": [
        {"id": "in", "name": "SubWorkflowInput"},
        {"id": "out", "name": "SubWorkflowOutput"},
    ],
    "edges": [],
}
COMUM = {
    "nodes": [
        {"id": "t", "name": "WebhookTrigger"},
        {"id": "p", "name": "PythonScript"},
    ],
    "edges": [],
}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Workflow.metadata.create_all, tables=[Workflow.__table__])
    async with AsyncSession(engine) as sessao:
        yield sessao
    await engine.dispose()


async def _semear(db, *pares):
    for i, (hash_, definition) in enumerate(pares):
        db.add(Workflow(
            id_hash=hash_, name=hash_, definition=definition,
            flag_ative=True, priority=i, workspace_id="ws-1",
        ))
    await db.commit()


async def _por_hash(db):
    linhas = await WorkflowCRUD(db).get_all_metadata()
    return {linha.id_hash: linha for linha in linhas}


@pytest.mark.asyncio
async def test_marca_quem_declara_saida_de_subfluxo(db):
    await _semear(db, ("filho", SO_SAIDA), ("comum", COMUM))
    linhas = await _por_hash(db)

    assert linhas["filho"].is_subworkflow is True
    assert linhas["comum"].is_subworkflow is False


@pytest.mark.asyncio
async def test_um_pai_que_apenas_chama_nao_e_marcado(db):
    """Quem CHAMA um sub-fluxo continua sendo um workflow comum na lista.

    A marca responde "este pode ser chamado por outro", e nao "este usa
    outros" — sao coisas diferentes, e o pai tem gatilho e roda sozinho.
    """
    pai = {"nodes": [
        {"id": "t", "name": "WebhookTrigger"},
        {"id": "s", "name": "SubWorkflow", "properties": {"workflowHash": "filho"}},
    ], "edges": []}
    await _semear(db, ("pai", pai))

    assert (await _por_hash(db))["pai"].is_subworkflow is False


@pytest.mark.asyncio
async def test_definition_vazia_nao_quebra_a_listagem(db):
    # Workflow recem-criado, ainda sem nenhum node.
    await _semear(db, ("novo", {"nodes": [], "edges": []}))

    assert (await _por_hash(db))["novo"].is_subworkflow is False


@pytest.mark.asyncio
@pytest.mark.parametrize("definition", [{}, {"edges": []}], ids=["vazia", "sem_a_chave_nodes"])
async def test_definition_sem_nodes_nao_derruba_a_resposta(db, definition):
    """REGRESSAO: sem a chave `nodes`, o `->>` devolve NULL, o LIKE propaga
    NULL, e o Pydantic recusa None num campo `bool`.

    O estrago nao era a linha errada: era GET /workflows/ inteiro respondendo
    500 — a tela de Projetos em branco por causa de UM workflow malformado. A
    coluna e `nullable=False`, mas nada garante o formato de dentro do JSON.

    A validacao pelo schema e o que prova o caso: ler o atributo da linha
    devolvia None sem reclamar, e o erro so aparecia ao serializar.
    """
    await _semear(db, ("torto", definition))

    item = WorkflowListItem.model_validate((await _por_hash(db))["torto"])
    assert item.is_subworkflow is False
    # A marca vizinha le a mesma coluna e tinha o mesmo defeito.
    assert item.has_publish_map is False


@pytest.mark.asyncio
async def test_a_marca_convive_com_has_publish_map(db):
    """As duas expressoes leem a MESMA coluna; uma nao pode mascarar a outra."""
    dos_dois = {"nodes": [
        {"id": "out", "name": "SubWorkflowOutput"},
        {"id": "m", "name": "PublishMap"},
    ], "edges": []}
    await _semear(db, ("ambos", dos_dois))

    linha = (await _por_hash(db))["ambos"]
    assert linha.is_subworkflow is True
    assert linha.has_publish_map is True
