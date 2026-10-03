# tests/integration/test_listagem_marca_subfluxo.py
"""
The project listing distinguishes a sub-workflow from a regular workflow.

A sub-workflow exists to be CALLED by another: it declares `SubWorkflowOutput`
and, in general, has no trigger of its own. In the list it was
indistinguishable — same card, same run button, which fires a run that does
not do what one expects.

The flag is an SQL expression over the `definition` column, in the same style
as the one that already exists for `has_publish_map`: no new column, no
migration, and without pulling the whole JSON into Python on every listing.

The test brings up the real table in an in-memory SQLite and runs the real
query — an assertion on the SQL text would not prove the column comes out
filled in.
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
    """A workflow that CALLS a sub-workflow is still a regular workflow in the list.

    The flag answers "this one can be called by another", not "this one uses
    others" — those are different things, and the parent has a trigger and
    runs on its own.
    """
    pai = {"nodes": [
        {"id": "t", "name": "WebhookTrigger"},
        {"id": "s", "name": "SubWorkflow", "properties": {"workflowHash": "filho"}},
    ], "edges": []}
    await _semear(db, ("pai", pai))

    assert (await _por_hash(db))["pai"].is_subworkflow is False


@pytest.mark.asyncio
async def test_definition_vazia_nao_quebra_a_listagem(db):
    # Freshly created workflow, still without any node.
    await _semear(db, ("novo", {"nodes": [], "edges": []}))

    assert (await _por_hash(db))["novo"].is_subworkflow is False


@pytest.mark.asyncio
@pytest.mark.parametrize("definition", [{}, {"edges": []}], ids=["vazia", "sem_a_chave_nodes"])
async def test_definition_sem_nodes_nao_derruba_a_resposta(db, definition):
    """REGRESSION: without the `nodes` key, `->>` returns NULL, LIKE propagates
    NULL, and Pydantic rejects None in a `bool` field.

    The damage was not the wrong row: it was all of GET /workflows/ responding
    500 — the Projects screen blank because of ONE malformed workflow. The
    column is `nullable=False`, but nothing guarantees the shape inside the JSON.

    Validation through the schema is what proves the case: reading the row's
    attribute returned None without complaint, and the error only appeared on
    serialization.
    """
    await _semear(db, ("torto", definition))

    item = WorkflowListItem.model_validate((await _por_hash(db))["torto"])
    assert item.is_subworkflow is False
    # A marca vizinha le a mesma coluna e tinha o mesmo defeito.
    assert item.has_publish_map is False


@pytest.mark.asyncio
async def test_a_marca_convive_com_has_publish_map(db):
    """Both expressions read the SAME column; one must not mask the other."""
    dos_dois = {"nodes": [
        {"id": "out", "name": "SubWorkflowOutput"},
        {"id": "m", "name": "PublishMap"},
    ], "edges": []}
    await _semear(db, ("ambos", dos_dois))

    linha = (await _por_hash(db))["ambos"]
    assert linha.is_subworkflow is True
    assert linha.has_publish_map is True
