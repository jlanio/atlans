"""The `version_number` race in `create_version`.

The version number is read-modify-write — it reads the max and adds 1 — and the
UNIQUE `uq_workflow_version` is the only arbiter. Two simultaneous saves of the
same workflow read the same max and the second INSERT violates it; before this
fix the violation surfaced as an unexpected error and the saver's work turned
into a 500.

Why these tests do NOT use `asyncio.gather`: the in-memory SQLite is a
`StaticPool` (the aiosqlite dialect returns StaticPool for any URL that is not a
file, even without an explicit `poolclass=`), so all sessions share ONE
connection and two "concurrent" coroutines are serialized. The
`SELECT max / SELECT max / INSERT / INSERT` interleaving does not happen, and
such a test would pass by construction without proving anything.

What is done instead: the colliding row is actually planted in the database,
and the FIRST read of the max returns a stale value — which is exactly what the
losing session sees in the window between its SELECT and the winner's INSERT.
The constraint that fires is the real one, not a fabricated error.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.crud.workflow_crud import WorkflowCRUD, _e_colisao_de_versao
from app.core.exceptions import WorkflowVersionConflictError
from app.models.models import Workflow, WorkflowGroup, WorkflowVersion

HASH = "wf-corrida"


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(
            Workflow.metadata.create_all,
            tables=[WorkflowGroup.__table__, Workflow.__table__, WorkflowVersion.__table__],
        )
    async with AsyncSession(eng) as sessao:
        yield sessao
    await eng.dispose()


async def _plantar(db, *numeros):
    """The versions the WINNING session has already written."""
    for n in numeros:
        db.add(WorkflowVersion(workflow_hash=HASH, version_number=n, definition={"n": n}))
    await db.commit()


class _MaximoVelho:
    """Makes the first N reads of the max return a stale value.

    That is what the losing session actually sees: it read before the winner
    committed. Only the read is faked — the INSERT goes to the real database and
    violates the real constraint.
    """

    def __init__(self, db, valor=0, vezes=1):
        self.db, self.valor, self.restam = db, valor, vezes
        self.original = db.execute
        self.leituras = 0

    def __enter__(self):
        async def execute(stmt, *a, **kw):
            if "max" in str(stmt).lower():
                self.leituras += 1
                if self.restam > 0:
                    self.restam -= 1
                    return _Resultado(self.valor)
            return await self.original(stmt, *a, **kw)

        self.db.execute = execute
        return self

    def __exit__(self, *_):
        self.db.execute = self.original
        return False


class _Resultado:
    def __init__(self, valor):
        self._valor = valor

    def scalar(self):
        return self._valor


class TestReconvergencia:

    @pytest.mark.asyncio
    async def test_colisao_de_numero_reconverge_em_vez_de_levantar(self, db):
        """The loser of the race rereads the max and takes the next number.

        Against today's code: the IntegrityError escapes `create_version` and
        goes up to the global handler, which responds 500 — and the save is lost.
        """
        await _plantar(db, 1)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=1):
            versao = await crud.create_version(HASH, {"x": 1}, "nota")

        assert versao.version_number == 2
        await db.commit()

        numeros = (await db.execute(
            select(WorkflowVersion.version_number).where(WorkflowVersion.workflow_hash == HASH)
        )).scalars().all()
        assert sorted(numeros) == [1, 2], "nenhuma versão pode ter sido perdida"

    @pytest.mark.asyncio
    async def test_o_retry_rele_o_maximo_em_vez_de_incrementar_o_que_falhou(self, db):
        """Incrementing the number that failed would collide with the neighbor again.

        With 1..5 planted and a stale max of 0: by rereading, the second attempt
        sees 5 and writes 6. By incrementing, it would try 2, then 3, and
        exhaust the three attempts without writing anything. The final number
        is what tells the two implementations apart — and that is why this test
        plants five rows and not one.
        """
        await _plantar(db, 1, 2, 3, 4, 5)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=1):
            versao = await crud.create_version(HASH, {"x": 9})

        assert versao.version_number == 6

    @pytest.mark.asyncio
    async def test_a_violacao_nao_escapa_do_savepoint(self, db):
        """The CALLER's transaction survives the collision and still commits.

        It is the difference between fixing and masking. In PostgreSQL a
        violation poisons the whole transaction, and this one runs inside
        someone else's transaction — which will still commit unrelated work.
        Without the SAVEPOINT, catching the error only swaps the 500 for a
        `PendingRollbackError` on the next commit.

        Mutation this test kills: replacing `async with db.begin_nested()` with
        a bare `try` around `flush()`.
        """
        await _plantar(db, 1)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=1):
            await crud.create_version(HASH, {"x": 1})

        # The work the caller would do afterwards — in move, the UPDATE on
        # `schedules` and the DELETE on `artifacts`; here, any row.
        db.add(Workflow(id_hash="outro", name="depois da colisao", definition={}, workspace_id="ws"))
        await db.commit()

        assert (await db.execute(
            select(Workflow.id_hash).where(Workflow.id_hash == "outro")
        )).scalar() == "outro"

    @pytest.mark.asyncio
    async def test_tentativas_esgotadas_viram_conflito_de_dominio(self, db):
        """Three collisions in a row stop being bad luck — and 409 is honest, 500 is not.

        The stale max is always returned, so every attempt recomputes the same
        number and collides. The client gets something actionable instead of
        "Unexpected error occurred".
        """
        await _plantar(db, 1)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=99) as espiao:
            with pytest.raises(WorkflowVersionConflictError) as exc:
                await crud.create_version(HASH, {"x": 1})

        assert espiao.leituras == 3, "três tentativas, três leituras do máximo"
        assert exc.value.status_code == 409
        assert exc.value.error_code == "workflow_version_conflict"

    @pytest.mark.asyncio
    async def test_integrityerror_de_outra_constraint_nao_e_engolida(self, db):
        """Only the version collision reconverges; everything else surfaces.

        Without the filter, a broken FK (or any other violation) would turn into
        a loop of three identical attempts ending in a 409 that lies about the
        cause.
        """
        crud = WorkflowCRUD(db)
        original = db.flush

        async def flush_que_quebra(*a, **kw):
            raise IntegrityError(
                "INSERT ...",
                {},
                Exception('violates foreign key constraint "workflow_versions_workflow_hash_fkey"'),
            )

        db.flush = flush_que_quebra
        try:
            with pytest.raises(IntegrityError):
                await crud.create_version("fantasma", {"x": 1})
        finally:
            db.flush = original


class TestReconhecimentoDaViolacao:
    """The filter has to recognize BOTH messages — that is what makes the fix hold
    in tests and in production at the same time."""

    def _erro(self, texto):
        return IntegrityError("INSERT ...", {}, Exception(texto))

    def test_mensagem_do_postgres_nomeia_a_constraint(self):
        assert _e_colisao_de_versao(self._erro(
            'duplicate key value violates unique constraint "uq_workflow_version"'
        ))

    def test_mensagem_do_sqlite_nomeia_as_colunas(self):
        assert _e_colisao_de_versao(self._erro(
            "UNIQUE constraint failed: workflow_versions.workflow_hash, "
            "workflow_versions.version_number"
        ))

    def test_violacao_de_outra_constraint_nao_casa(self):
        assert not _e_colisao_de_versao(self._erro(
            'duplicate key value violates unique constraint "uq_workflow_name_workspace"'
        ))
        assert not _e_colisao_de_versao(self._erro(
            "UNIQUE constraint failed: workflows.name, workflows.workspace_id"
        ))
