# tests/unit/test_versao_nao_vaza_connection_string.py
"""Version history stores the connection string ENCRYPTED — in both directions.

Read: `get_version` did `v.definition = decrypt_workflow_connections(v.definition)`
on a LIVE session row. The assignment marks the row as dirty: any later commit
in the same request wrote the connection string in PLAIN TEXT to the
`workflow_versions` table — encryption at rest undone by a GET, in a history
that nobody ever rewrites.

Write: `update_workflow` decrypts the current definition to compare it with the
new one, and `decrypt_workflow_connections` MUTATES the dict it receives. The
snapshot on the next line — what the code comment calls an "encrypted
snapshot" — went out in plain text through the same reference. It was the same
leak through the opposite door, and no test saw it: this file covered only the
read, and the service test mocks precisely the function that mutates.

The tests run against real SQLite and real Fernet: what matters here is what
remains stored after the commit.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.utils.encryption import encrypt_workflow_connections
from app.crud.workflow_crud import WorkflowCRUD
from app.models.models import Schedule, Workflow, WorkflowGroup, WorkflowVersion
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_service import WorkflowService
from app.services.workflow_version_service import get_version, restore_version

# Fictitious credential: it needs the shape of a real connection string for the
# test to prove anything, and that is exactly what BasicAuthDetector flags.
SEGREDO = "postgresql://usuario:senha-secretissima@host:5432/base"  # pragma: allowlist secret


def _definition(conn: str = SEGREDO) -> dict:
    return {
        "nodes": [
            {
                "id": "n1",
                "type": "action",
                "name": "PostgresQuery",
                "properties": {"connectionString": conn},
            }
        ]
    }


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[
                WorkflowGroup.__table__,
                Workflow.__table__,
                WorkflowVersion.__table__,
                # `update_workflow` syncs the schedule at the end; without the table the
                # error would be swallowed by the try/except there and the test
                # would end up exercising a path different from production's.
                Schedule.__table__,
            ],
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    async with AsyncSession(engine) as sessao:
        sessao.add(Workflow(id_hash="wf-1", name="wf", workspace_id="ws-1", definition={}))
        sessao.add(WorkflowVersion(
            workflow_hash="wf-1",
            version_number=1,
            definition=encrypt_workflow_connections(_definition()),
        ))
        await sessao.commit()
        yield sessao


async def _definition_no_banco(engine) -> dict:
    """Reads the row in a NEW session — the other one's identity map is no proof."""
    async with AsyncSession(engine) as outra:
        v = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.version_number == 1)
        )).scalar_one()
        return v.definition


async def test_get_version_devolve_a_definition_redigida(db):
    """The route that consumes this requires no role: it handed the credential to a viewer.

    Reading the history is legitimate for someone who only reads; knowing the
    production database password is not. And restoring does not need it
    either — `restore` copies the encrypted blob without opening it.
    """
    v = await get_version(WorkflowCRUD(db), "wf-1", 1)

    assert v.definition["nodes"][0]["properties"]["connectionString"] == "<REDACTED>"
    assert SEGREDO not in str(v.definition)
    # The shape stays whole: what is lost is the secret, not the version.
    assert v.definition["nodes"][0]["id"] == "n1"
    assert v.definition["nodes"][0]["name"] == "PostgresQuery"


async def test_commit_depois_do_get_version_nao_grava_o_segredo_em_claro(db, engine):
    """The regression. Before, this commit persisted the readable connection string."""
    await get_version(WorkflowCRUD(db), "wf-1", 1)
    await db.commit()

    gravado = (await _definition_no_banco(engine))["nodes"][0]["properties"]["connectionString"]
    assert gravado != SEGREDO
    assert gravado.startswith("gAAAA")


async def test_get_version_nao_suja_a_sessao(db):
    """There is not even a pending UPDATE for someone else's commit to carry along."""
    await get_version(WorkflowCRUD(db), "wf-1", 1)

    assert not db.dirty


async def test_update_workflow_grava_o_snapshot_ainda_cifrado(db, engine):
    """The regression on the other side: WRITING the version.

    `update_workflow` fetches `wf` via `get_by_hash` (no decrypt) precisely to
    avoid dirtying the session — and the code comment says so. On the next line
    it called `decrypt_workflow_connections(wf.definition)`, which MUTATES the
    dict and returns the same object: from then on `wf.definition` was in
    plain text, and the snapshot's `definition=wf.definition` wrote the
    readable credential to `workflow_versions`.
    """
    db.add(Workflow(
        id_hash="wf-2",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    await db.commit()

    # Change the set of node ids: that is what `_has_substantial_changes` requires
    # to create a version. Without it there is no snapshot and the test proves nothing.
    nova = {"nodes": [{"id": "n2", "type": "action", "name": "Outro", "properties": {}}]}
    await WorkflowService(db).update_workflow("wf-2", WorkflowUpdate(definition=nova), updated_by_id="u-1")

    async with AsyncSession(engine) as outra:
        versao = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.workflow_hash == "wf-2")
        )).scalar_one()

    gravado = versao.definition["nodes"][0]["properties"]["connectionString"]
    assert SEGREDO not in str(versao.definition)
    assert gravado.startswith("gAAAA")


async def test_snapshot_cifrado_mesmo_com_a_sessao_ja_decifrada(db, engine):
    """The case the test above did NOT cover — and it is the real route's case.

    `update_workflow` fetches with `get_by_hash` (no decrypt) and the code
    comment said that was enough. It is not: the route's dependency
    (`get_accessible_workflow_with_role`) has already called
    `get_workflow_by_hash`, which does
    `wf.definition = decrypt_workflow_connections(...)` — an in-place mutation
    on the LIVE row. Being the same session, `get_by_hash` returns the SAME
    Python object, already in plain text, and copying it only duplicates the
    plain text.

    Calling `get_workflow_by_hash` first reproduces exactly the state the
    dependency leaves. The reference must be kept: the identity map is weak,
    and with nobody holding the object the next SELECT brings the encrypted
    row from the database — that is how the defect went unnoticed.
    """
    svc = WorkflowService(db)
    db.add(Workflow(
        id_hash="wf-3",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    await db.commit()

    vivo = await svc.get_workflow_by_hash("wf-3")          # what the dependency does
    assert vivo.definition["nodes"][0]["properties"]["connectionString"] == SEGREDO

    nova = {"nodes": [{"id": "n2", "type": "action", "name": "Outro", "properties": {}}]}
    await svc.update_workflow("wf-3", WorkflowUpdate(definition=nova), updated_by_id="u-1")

    async with AsyncSession(engine) as outra:
        versao = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.workflow_hash == "wf-3")
        )).scalar_one()

    assert SEGREDO not in str(versao.definition)
    assert versao.definition["nodes"][0]["properties"]["connectionString"].startswith("gAAAA")


async def test_restore_version_tambem_guarda_o_auto_snapshot_cifrado(db, engine):
    """The same leak at the second call site of `create_version`.

    `restore_version` takes an auto-snapshot of the current state before
    restoring, through the same route and with the same dependency. Closing only
    `update_workflow` would let a restore put the readable credential back into
    the history.
    """
    svc = WorkflowService(db)
    db.add(Workflow(
        id_hash="wf-4",
        name="fluxo",
        workspace_id="ws-1",
        definition=encrypt_workflow_connections(_definition()),
    ))
    db.add(WorkflowVersion(
        workflow_hash="wf-4",
        version_number=1,
        definition=encrypt_workflow_connections(_definition("postgresql://a:b@c:5432/d")),
    ))
    await db.commit()

    vivo = await svc.get_workflow_by_hash("wf-4")          # the dependency again
    assert vivo.definition["nodes"][0]["properties"]["connectionString"] == SEGREDO

    await restore_version(WorkflowCRUD(db), "wf-4", 1)

    async with AsyncSession(engine) as outra:
        auto = (await outra.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_hash == "wf-4")
            .where(WorkflowVersion.version_number != 1)
        )).scalar_one()

    assert SEGREDO not in str(auto.definition)
    assert auto.definition["nodes"][0]["properties"]["connectionString"].startswith("gAAAA")


async def test_restore_depois_de_get_version_nao_grava_redacted(db, engine):
    """The redaction must not turn into destruction of the credential.

    `set_committed_value` writes to the instance; without detaching it, a
    `restore_version` in the SAME session would get the same row via the
    identity map and write `"<REDACTED>"` into the workflow's definition —
    irreversible loss of the encrypted token. REST does not reach this (one
    request, one session), but the MCP server tools chain operations in a single
    session.
    """
    v = await get_version(WorkflowCRUD(db), "wf-1", 1)
    assert v.definition["nodes"][0]["properties"]["connectionString"] == "<REDACTED>"

    await restore_version(WorkflowCRUD(db), "wf-1", 1)

    async with AsyncSession(engine) as outra:
        wf = (await outra.execute(
            select(Workflow).where(Workflow.id_hash == "wf-1")
        )).scalar_one()

    gravado = wf.definition["nodes"][0]["properties"]["connectionString"]
    assert gravado != "<REDACTED>"
    assert gravado.startswith("gAAAA")


async def test_definition_indecifravel_vira_erro_explicito(db, engine):
    """A corrupted token must not slip through as if it were normal text."""
    async with AsyncSession(engine) as outra:
        v = (await outra.execute(
            select(WorkflowVersion).where(WorkflowVersion.version_number == 1)
        )).scalar_one()
        v.definition = _definition("gAAAAlixo-que-nao-decifra")
        await outra.commit()

    with pytest.raises(ValueError, match="descriptografar"):
        await get_version(WorkflowCRUD(db), "wf-1", 1)
