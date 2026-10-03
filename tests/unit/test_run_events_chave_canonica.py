"""The history key comes from the `task_id`, not from what the client typed.

`get_run_detail` authorizes by TWO identifiers — the `task_id` and the row's
numeric id (the `run_id.isdigit()` branch) — but the Redis key is
`workflow:{id}:history`, built with the id that is passed along. Whoever came in
through the numeric id authorized one run and read the key of another.

**It is not a leak**: the keys are written with the `task_id`, which is a `uuid4`,
and a decimal id never collides with a uuid. What happens is harder to diagnose:
the response comes back `200` with `expired: true`, claiming the log expired,
while it is intact in Redis under the other key.

The MCP tool already defended itself against this from the outside
(`test_mcp_execucao.py`, the typed-id test). The REST API did not — and it is the
same service. These tests cover the SERVICE, which is where both paths go through.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.models import Workflow, WorkflowRun
from app.services.observability_service import ObservabilityService

# Reuses the MCP harness's list instead of building another: `get_run_detail`
# joins `users` and `workspaces` to resolve authorship and the workspace name, and
# discovering that table by table is time spent in the wrong place.
from tests.unit._mcp_harness import TABLES

TASK = "1f0c9a7e-0000-4a11-9c2e-000000000001"
WS = "ws-1"
WF = "wf-1"


class _FakeRedis:
    """Only `lrange`, and it records the requested keys — looking at the key is
    how one proves which run the log was read from."""

    def __init__(self, itens=None):
        self.itens = itens or []
        self.chaves: list[str] = []

    async def lrange(self, chave, inicio, fim):
        self.chaves.append(chave)
        return self.itens


class _FakeUser:
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
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    async with AsyncSession(eng) as sessao:
        sessao.add(Workflow(id_hash=WF, name="Fluxo", definition={}, workspace_id=WS))
        sessao.add(WorkflowRun(task_id=TASK, workflow_hash=WF, workspace_id=WS, status="success"))
        await sessao.commit()
        yield sessao
    await eng.dispose()


@pytest.fixture
def redis(monkeypatch):
    def _install(itens=None):
        falso = _FakeRedis(itens)
        monkeypatch.setattr("app.core.redis.get_redis_pool", lambda: falso)
        return falso
    return _install


async def _row_number(db):
    from sqlalchemy import select
    return str((await db.execute(select(WorkflowRun.id).where(WorkflowRun.task_id == TASK))).scalar())


class TestCanonicalKey:

    @pytest.mark.asyncio
    async def test_entering_by_numeric_id_reads_the_task_id_key(self, db, redis):
        """The defect, through the REST path.

        Against today's code: the key read is `workflow:{numero}:history`, and the
        response comes back empty with `expired: true` — the log exists, but under
        the other key.
        """
        falso = redis(['{"node": "n1", "kind": "lifecycle"}'])
        numero = await _row_number(db)

        out = await ObservabilityService.get_run_events(db, numero, _FakeUser(), [WS])

        assert falso.chaves == [f"workflow:{TASK}:history"], (
            "leu o histórico pelo id digitado, não pelo task_id que autorizou"
        )
        assert out["expired"] is False
        assert len(out["events"]) == 1
        # The response also identifies itself by the canonical id.
        assert out["run_id"] == TASK

    @pytest.mark.asyncio
    async def test_entering_by_task_id_nothing_changes(self, db, redis):
        """O caminho comum (a web manda o task_id) continua igual."""
        falso = redis(['{"node": "n1"}'])

        out = await ObservabilityService.get_run_events(db, TASK, _FakeUser(), [WS])

        assert falso.chaves == [f"workflow:{TASK}:history"]
        assert out["run_id"] == TASK

    @pytest.mark.asyncio
    async def test_redis_down_still_answers_by_the_canonical_id(self, db, redis):
        """The failure branch also learned the right id — otherwise the error response
        would identify itself by an id the client does not recognize."""
        class _Explode(_FakeRedis):
            async def lrange(self, chave, inicio, fim):
                self.chaves.append(chave)
                raise RuntimeError("redis fora do ar")

        import app.core.redis as mod
        falso = _Explode()
        original = mod.get_redis_pool
        mod.get_redis_pool = lambda: falso
        try:
            numero = await _row_number(db)
            out = await ObservabilityService.get_run_events(db, numero, _FakeUser(), [WS])
        finally:
            mod.get_redis_pool = original

        assert out["run_id"] == TASK
        assert out["expired"] is True


class TestSingleAuthorization:

    @pytest.mark.asyncio
    async def test_the_detail_variant_authorizes_once_and_returns_both(self, db, redis):
        """The MCP tool needs the events AND the detail.

        Before, it loaded the detail from the outside and the service loaded it
        again on the inside. `get_run_detail` has no cache and makes 3 to 6
        queries — among them a three-table join and a percentile over a 90-day
        window —, so it was 6 to 12 database round trips per call, half of them waste.

        Mutation this test kills: the service going back to reloading the detail
        when the caller already has it.
        """
        redis(['{"node": "n1"}'])
        chamadas = []
        original = ObservabilityService.get_run_detail

        async def espiao(*a, **kw):
            chamadas.append(a[1])
            return await original(*a, **kw)

        ObservabilityService.get_run_detail = staticmethod(espiao)
        try:
            eventos, detalhe = await ObservabilityService.get_run_events_with_detail(
                db, TASK, _FakeUser(), [WS],
            )
        finally:
            ObservabilityService.get_run_detail = staticmethod(original)

        assert len(chamadas) == 1, f"o detalhe foi carregado {len(chamadas)}x"
        assert eventos["run_id"] == TASK
        assert detalhe["run_id"] == TASK
        assert detalhe["status"] == "success"


class TestImportedRetention:

    def test_the_tool_uses_the_core_constant_not_a_copy(self):
        """With the value duplicated, changing the TTL in the core made the tool lie in
        `availability` and in `retention_seconds` without anything breaking — the
        worst kind of divergence, the one with no symptom.

        Mutation: going back to writing `3600` by hand in `execucao.py`. This test
        would keep passing by value, so it asserts IDENTITY.
        """
        from app.core.constants import REDIS_TTL_1H
        from app.mcp.tools.execucao import EVENTS_RETENTION_S

        assert EVENTS_RETENTION_S is REDIS_TTL_1H
