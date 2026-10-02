"""A corrida de `version_number` em `create_version`.

O número da versão é read-modify-write — lê o máximo e soma 1 — e a UNIQUE
`uq_workflow_version` é a única árbitra. Dois saves simultâneos do mesmo
workflow leem o mesmo máximo e o segundo INSERT viola; antes deste conserto a
violação subia como erro inesperado e o trabalho de quem salvou virava um 500.

Por que estes testes NÃO usam `asyncio.gather`: o SQLite em memória é
`StaticPool` (o dialeto aiosqlite devolve StaticPool para qualquer URL que não
seja arquivo, mesmo sem `poolclass=` explícito), então todas as sessões
compartilham UMA conexão e duas corrotinas "concorrentes" são serializadas. A
intercalação `SELECT max / SELECT max / INSERT / INSERT` não acontece, e um
teste desses passaria por construção sem provar nada.

O que se faz em lugar disso: a linha colidente é plantada de verdade no banco, e
a PRIMEIRA leitura do máximo devolve um valor velho — que é exatamente o que a
sessão perdedora enxerga na janela entre o seu SELECT e o INSERT da vencedora. A
constraint que dispara é a real, não um erro fabricado.
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
    """As versões que a sessão VENCEDORA já gravou."""
    for n in numeros:
        db.add(WorkflowVersion(workflow_hash=HASH, version_number=n, definition={"n": n}))
    await db.commit()


class _MaximoVelho:
    """Faz as N primeiras leituras do máximo devolverem um valor defasado.

    É o que a sessão perdedora de fato enxerga: ela leu antes de a vencedora
    commitar. Só a leitura é falsificada — o INSERT vai ao banco real e viola a
    constraint real.
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
        """O perdedor da corrida relê o máximo e leva o número seguinte.

        Contra o código de hoje: a IntegrityError escapa de `create_version` e
        sobe até o handler global, que responde 500 — e o save some.
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
        """Incrementar o número que falhou colidiria de novo com o vizinho.

        Com 1..5 plantadas e um máximo velho de 0: relendo, a segunda tentativa
        vê 5 e grava 6. Incrementando, ela tentaria 2, depois 3, e esgotaria as
        três tentativas sem gravar nada. O número final é o que distingue as
        duas implementações — e é por isso que este teste planta cinco linhas e
        não uma.
        """
        await _plantar(db, 1, 2, 3, 4, 5)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=1):
            versao = await crud.create_version(HASH, {"x": 9})

        assert versao.version_number == 6

    @pytest.mark.asyncio
    async def test_a_violacao_nao_escapa_do_savepoint(self, db):
        """A transação do CHAMADOR sobrevive à colisão e ainda commita.

        É a diferença entre consertar e mascarar. No PostgreSQL uma violação
        envenena a transação inteira, e esta roda dentro da transação de outra
        pessoa — que ainda vai commitar trabalho não relacionado. Sem o
        SAVEPOINT, capturar o erro só troca o 500 por um `PendingRollbackError`
        no commit seguinte.

        Mutação que este teste mata: trocar `async with db.begin_nested()` por
        um `try` solto em volta do `flush()`.
        """
        await _plantar(db, 1)
        crud = WorkflowCRUD(db)

        with _MaximoVelho(db, valor=0, vezes=1):
            await crud.create_version(HASH, {"x": 1})

        # O trabalho que o chamador faria depois — no move, o UPDATE em
        # `schedules` e o DELETE em `artifacts`; aqui, uma linha qualquer.
        db.add(Workflow(id_hash="outro", name="depois da colisao", definition={}, workspace_id="ws"))
        await db.commit()

        assert (await db.execute(
            select(Workflow.id_hash).where(Workflow.id_hash == "outro")
        )).scalar() == "outro"

    @pytest.mark.asyncio
    async def test_tentativas_esgotadas_viram_conflito_de_dominio(self, db):
        """Três colisões seguidas param de ser azar — e 409 é honesto, 500 não.

        O máximo velho é devolvido sempre, então toda tentativa recalcula o
        mesmo número e colide. O cliente recebe algo acionável em vez de
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
        """Só a colisão de versão reconverge; o resto sobe.

        Sem o filtro, uma FK quebrada (ou qualquer outra violação) viraria um
        laço de três tentativas idênticas terminando num 409 que mente sobre a
        causa.
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
    """O filtro tem de reconhecer as DUAS mensagens — é o que faz o conserto
    valer nos testes e em produção ao mesmo tempo."""

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
