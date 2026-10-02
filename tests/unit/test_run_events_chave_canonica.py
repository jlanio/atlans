"""A chave do histórico sai do `task_id`, não do que o cliente digitou.

`get_run_detail` autoriza por DOIS identificadores — o `task_id` e o id
numérico da linha (o ramo `run_id.isdigit()`) — mas a chave do Redis é
`workflow:{id}:history`, montada com o id que se passa adiante. Quem entrava
pelo id numérico autorizava um run e lia a chave de outro.

**Não é vazamento**: as chaves são escritas com o `task_id`, que é `uuid4`, e um
id decimal nunca colide com um uuid. O que acontece é pior de diagnosticar: a
resposta vem `200` com `expired: true`, afirmando que o log expirou, enquanto
ele está inteiro no Redis sob a outra chave.

A tool do MCP já se defendia disso por fora (`test_mcp_execucao.py`, o teste do
id digitado). A REST não — e é o mesmo serviço. Estes testes cobrem o SERVIÇO,
que é por onde os dois caminhos passam.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.models import Workflow, WorkflowRun
from app.services.observability_service import ObservabilityService

# Reusa a lista do harness do MCP em vez de montar outra: `get_run_detail`
# cruza com `users` e `workspaces` para resolver autoria e nome do workspace, e
# descobrir isso tabela a tabela é tempo gasto no lugar errado.
from tests.unit._mcp_harness import TABELAS

TASK = "1f0c9a7e-0000-4a11-9c2e-000000000001"
WS = "ws-1"
WF = "wf-1"


class _RedisFalso:
    """Só o `lrange`, e ele grava as chaves pedidas — é olhando para a chave que
    se prova de qual run o log foi lido."""

    def __init__(self, itens=None):
        self.itens = itens or []
        self.chaves: list[str] = []

    async def lrange(self, chave, inicio, fim):
        self.chaves.append(chave)
        return self.itens


class _Usuario:
    id_hash = "usr-1"
    username = "quem-consulta"
    role = "user"


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABELAS)
    async with AsyncSession(eng) as sessao:
        sessao.add(Workflow(id_hash=WF, name="Fluxo", definition={}, workspace_id=WS))
        sessao.add(WorkflowRun(task_id=TASK, workflow_hash=WF, workspace_id=WS, status="success"))
        await sessao.commit()
        yield sessao
    await eng.dispose()


@pytest.fixture
def redis(monkeypatch):
    def _instalar(itens=None):
        falso = _RedisFalso(itens)
        monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: falso)
        return falso
    return _instalar


async def _numero_da_linha(db):
    from sqlalchemy import select
    return str((await db.execute(select(WorkflowRun.id).where(WorkflowRun.task_id == TASK))).scalar())


class TestChaveCanonica:

    @pytest.mark.asyncio
    async def test_entrando_pelo_id_numerico_le_a_chave_do_task_id(self, db, redis):
        """O defeito, pelo caminho da REST.

        Contra o código de hoje: a chave lida é `workflow:{numero}:history`, e a
        resposta vem vazia com `expired: true` — o log existe, mas debaixo da
        outra chave.
        """
        falso = redis(['{"node": "n1", "kind": "lifecycle"}'])
        numero = await _numero_da_linha(db)

        out = await ObservabilityService.get_run_events(db, numero, _Usuario(), [WS])

        assert falso.chaves == [f"workflow:{TASK}:history"], (
            "leu o histórico pelo id digitado, não pelo task_id que autorizou"
        )
        assert out["expired"] is False
        assert len(out["events"]) == 1
        # A resposta também se identifica pelo id canônico.
        assert out["run_id"] == TASK

    @pytest.mark.asyncio
    async def test_entrando_pelo_task_id_nada_muda(self, db, redis):
        """O caminho comum (a web manda o task_id) continua igual."""
        falso = redis(['{"node": "n1"}'])

        out = await ObservabilityService.get_run_events(db, TASK, _Usuario(), [WS])

        assert falso.chaves == [f"workflow:{TASK}:history"]
        assert out["run_id"] == TASK

    @pytest.mark.asyncio
    async def test_redis_fora_do_ar_ainda_responde_pelo_id_canonico(self, db, redis):
        """O ramo de falha também aprendeu o id certo — senão a resposta de erro
        se identificaria por um id que o cliente não reconhece."""
        class _Explode(_RedisFalso):
            async def lrange(self, chave, inicio, fim):
                self.chaves.append(chave)
                raise RuntimeError("redis fora do ar")

        import app.core.redis as mod
        falso = _Explode()
        original = mod.get_redis_pool
        mod.get_redis_pool = lambda: falso
        try:
            numero = await _numero_da_linha(db)
            out = await ObservabilityService.get_run_events(db, numero, _Usuario(), [WS])
        finally:
            mod.get_redis_pool = original

        assert out["run_id"] == TASK
        assert out["expired"] is True


class TestUmaAutorizacaoSo:

    @pytest.mark.asyncio
    async def test_a_variante_com_detalhe_autoriza_uma_vez_e_devolve_os_dois(self, db, redis):
        """A tool do MCP precisa dos eventos E do detalhe.

        Antes ela carregava o detalhe por fora e o serviço carregava de novo por
        dentro. `get_run_detail` não tem cache e faz de 3 a 6 consultas — entre
        elas um join de três tabelas e um percentil sobre janela de 90 dias —,
        então eram de 6 a 12 idas ao banco por chamada, metade desperdício.

        Mutação que este teste mata: o serviço voltar a recarregar o detalhe
        quando o chamador já o tem.
        """
        redis(['{"node": "n1"}'])
        chamadas = []
        original = ObservabilityService.get_run_detail

        async def espiao(*a, **kw):
            chamadas.append(a[1])
            return await original(*a, **kw)

        ObservabilityService.get_run_detail = staticmethod(espiao)
        try:
            eventos, detalhe = await ObservabilityService.get_run_events_com_detalhe(
                db, TASK, _Usuario(), [WS],
            )
        finally:
            ObservabilityService.get_run_detail = staticmethod(original)

        assert len(chamadas) == 1, f"o detalhe foi carregado {len(chamadas)}x"
        assert eventos["run_id"] == TASK
        assert detalhe["run_id"] == TASK
        assert detalhe["status"] == "success"


class TestRetencaoImportada:

    def test_a_tool_usa_a_constante_do_nucleo_e_nao_uma_copia(self):
        """Com o valor duplicado, mudar o TTL no núcleo fazia a tool mentir no
        `availability` e no `retention_seconds` sem nada quebrar — o pior tipo
        de divergência, a que não dá sintoma.

        Mutação: voltar a escrever `3600` à mão em `execucao.py`. Este teste
        continuaria passando pelo valor, então ele afirma a IDENTIDADE.
        """
        from app.core.constants import REDIS_TTL_1H
        from app.mcp.tools.execucao import RETENCAO_DOS_EVENTOS_S

        assert RETENCAO_DOS_EVENTOS_S is REDIS_TTL_1H
