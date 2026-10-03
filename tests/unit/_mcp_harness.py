# tests/unit/_mcp_harness.py
"""
Shared tooling for the MCP server tests.

The name starts with `_` on purpose: pytest does not collect this file, which
has no tests at all — only the database, the fake Redis and the shortcuts that
the `app/mcp/` tests use.

Three decisions that apply to every test here:

- **A real database, in memory.** The PAT middleware JOINs token, user and
  workspaces; a mock of `db.execute` would only prove that the mock returns
  what it was told to. SQLite covers the tables involved (none of them uses
  JSONB, which SQLite does not compile).
- **Infra via two patches.** `app.mcp.infra.sessao` and `app.mcp.infra.redis_ou_none`
  are the MCP's only points of contact with Postgres and Redis; swapping them
  swaps the whole infrastructure without touching any other module.
- **A client that goes through the stack.** `mcp_client` talks to the real
  ASGI app (PAT middleware + streamable HTTP transport), not to the in-process
  server — it is the only way to prove that the token arrives, that `Host` is
  checked and that the scope filters the catalog.

A limitation worth knowing before writing an execution test: `FakeRedis` does
NOT have pub/sub. It covers the key commands (quotas, idempotency, replay via
`LRANGE`) and nothing else — whoever tests `run_workflow(wait)` should swap
`esperar_run` for a stub (`patch` in the module the tool imports) and describe
the outcome with `wait_result(...)`. Testing the real wait is the job
of `test_run_events_service.py`, which has `FakePubSub` for that.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.mcp.escopo import EffectiveScope
from app.models.api_token import ApiToken
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.portal_layer import PortalLayer
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.models.schedule import Schedule
from app.models.system_config import SystemConfig
from app.models.workflow_version import WorkflowVersion
from app.models.workspace import Workspace
from app.models.platform_file_settings import (
    AllowedFileExtension, PlatformFileSettings,
)
from app.models.workspace_file import WorkspaceFile
from app.models.workspace_member import WorkspaceMember
from app.services import api_token_service
from app.services.run_events_service import WaitResult

EXTENSION_TABLES = [
    tabela for tabela in Base.metadata.sorted_tables
    if any(
        mapper.local_table is tabela and mapper.class_.__module__.startswith("app.extensoes.")
        for mapper in Base.registry.mappers
    )
]

# The tables the MCP touches that compile on SQLite. `Credential` and `Executor`
# are left out: they use JSONB, which only exists in Postgres.
TABLES = [
    User.__table__,
    Workspace.__table__,
    WorkspaceMember.__table__,
    ApiToken.__table__,
    Workflow.__table__,
    WorkflowRun.__table__,
    WorkflowVersion.__table__,
    Schedule.__table__,
    Artifact.__table__,
    # The artifact listing cross-references the portal layers to mark which
    # version is published; without the table, the SELECT breaks at collection.
    PortalLayer.__table__,
    # The Drive. `PlatformFileSettings` and `AllowedFileExtension` come along
    # because `validate_upload` queries both BEFORE writing anything: the size
    # ceiling and the list of allowed extensions. Without them, the first write
    # call breaks at collection, not at the assertion.
    WorkspaceFile.__table__,
    PlatformFileSettings.__table__,
    AllowedFileExtension.__table__,
    # The system configuration (the assistant's model and, with the plans, each
    # plan's quota). Without the table the service degrades open and returns
    # the default — a test that edited the configuration would pass without
    # reading anything.
    SystemConfig.__table__,
    # The tables of the extensions present (app/extensoes): with the plans, the
    # assistant quota queries the subscription to resolve the ceiling, and
    # without them any test that exercises `conversar()` would break at
    # collection.
    *EXTENSION_TABLES,
]


@asynccontextmanager
async def in_memory_db():
    """A new SQLite engine with the tables created; returns the session factory."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@asynccontextmanager
async def executors_db():
    """A new SQLite with the `executors` table; returns the session factory.

    It stays out of `TABLES` because it uses JSONB, which SQLite does not
    compile: here goes a copy of the table with JSON instead. The code's
    queries use the real `Executor` model — only the table and column names
    matter."""
    from sqlalchemy import JSON, MetaData
    from sqlalchemy.dialects.postgresql import JSONB

    from app.models.executor import Executor

    tabela = Executor.__table__.to_metadata(MetaData())
    for coluna in tabela.columns:
        if isinstance(coluna.type, JSONB):
            coluna.type = JSON()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(tabela.create)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def session_from(fabrica):
    """Replacement for `app.mcp.infra.sessao` bound to this factory.

    Mimics the original: rollback in the `finally`, so whoever writes has to
    commit — exactly as in production.
    """

    @asynccontextmanager
    async def _session():
        async with fabrica() as sessao:
            try:
                yield sessao
            finally:
                await sessao.rollback()

    return _session


async def create_user(db, id_hash: str = "usr-1", username: str = "ana", status: str = "active") -> User:
    usuario = User(
        id_hash=id_hash,
        username=username,
        email=f"{username}@teste.local",
        hashed_password="x",
        status=status,
    )
    db.add(usuario)
    await db.commit()
    return usuario


async def create_workspace(db, id_hash: str, owner_id: str, name: str = "Principal") -> Workspace:
    workspace = Workspace(id_hash=id_hash, name=name, owner_id=owner_id)
    db.add(workspace)
    await db.commit()
    return workspace


async def create_pat(db, user_id: str, scopes, workspace_ids=None) -> str:
    """Issues a real PAT and returns the secret in plain text.

    Goes through the real service (`criar`), not a hand-written INSERT: the
    service is what decides prefix, hash and validity, and a test that
    replicated that would be validating its own copy.
    """
    usuario = SimpleNamespace(id_hash=user_id)
    _, segredo = await api_token_service.criar(
        db,
        usuario,
        name="token de teste",
        scopes=list(scopes),
        workspace_ids=None if workspace_ids is None else list(workspace_ids),
    )
    return segredo


async def create_run(
    db,
    *,
    task_id: str,
    workflow_hash: str,
    workspace_id: str,
    status: str = "success",
    **campos,
) -> WorkflowRun:
    """A `workflow_runs` row that has already finished, ready to be read.

    The times are fixed (and not from `now()`) because what the execution
    tests check is the serialization — `duration_seconds`, listing order, date
    window — and a real clock would make the assertion depend on the moment of
    the test. `node_stats` starts empty, never null: that is the shape the
    serialization expects, and null only appears in old runs. A non-terminal
    run (`running`, `pending`) starts without `end_time`, as in production —
    asking for `status="running"` and getting a row with an end time would make
    the test agree with a state the database never has.
    """
    inicio = campos.pop("start_time", datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc))
    termina = status in ("success", "failed", "cancelled")
    fim = campos.pop("end_time", inicio + timedelta(seconds=42) if termina else None)
    duracao = campos.pop("duration_seconds", None)
    if duracao is None and fim is not None:
        duracao = (fim - inicio).total_seconds()
    campos.setdefault("node_stats", {})
    run = WorkflowRun(
        task_id=task_id,
        workflow_hash=workflow_hash,
        workspace_id=workspace_id,
        status=status,
        start_time=inicio,
        end_time=fim,
        duration_seconds=duracao,
        **campos,
    )
    db.add(run)
    await db.commit()
    return run


async def create_artifact(db, *, run_id: str, workspace_id: str, **campos) -> Artifact:
    """An artifact in storage, the way the output node writes it.

    The default is the common case (`content_location="minio"` with `s3_key`),
    which is the only one that yields a signed URL; the case of content that
    stayed on the executor is written by passing
    `content_location="executor", s3_key=None`.
    """
    campos.setdefault("output_key", "saida")
    campos.setdefault("filename", "saida.geojson")
    campos.setdefault("format", "geojson")
    campos.setdefault("size_bytes", 1024)
    campos.setdefault("content_location", "minio")
    if campos["content_location"] == "minio":
        campos.setdefault("s3_key", f"artifacts/{run_id}/{campos['filename']}")
    artefato = Artifact(run_id=run_id, workspace_id=workspace_id, **campos)
    db.add(artefato)
    await db.commit()
    return artefato


def wait_result(**kw) -> WaitResult:
    """The `WaitResult` that a stubbed `esperar_run` would return.

    The default describes the happy case — finished with `success`, no
    timeout, with `__workflow_complete__` seen. Each test overrides only the
    field it investigates (`timed_out=True`, `status="failed"`,
    `redis_indisponivel=True`).
    """
    campos = {
        "status": "success",
        "run": None,
        "concluidos": 0,
        "eventos_descartados": 0,
        "timed_out": False,
        "redis_indisponivel": False,
        "viu_complete": True,
    }
    campos.update(kw)
    return WaitResult(**campos)


def fake_scope(**kw) -> EffectiveScope:
    """A ready-made `EffectiveScope`; override only the field the test investigates."""
    campos = {
        "user_id": "usr-1",
        "username": "ana",
        "token_id": "tok-1",
        "token_prefix": "atl_pat_Ab3d",
        "scopes": {"workflows:read"},
        "workspace_ids": {"ws-1"},
        "todos_os_workspaces": False,
    }
    campos.update(kw)
    campos["scopes"] = frozenset(campos["scopes"])
    campos["workspace_ids"] = frozenset(campos["workspace_ids"])
    return EffectiveScope(**campos)


def fake_ctx(escopo: EffectiveScope | None):
    """The `ctx` a tool receives — only what `escopo_da_chamada` and the progress read."""
    estado = SimpleNamespace(escopo=escopo) if escopo is not None else SimpleNamespace()
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(state=estado)),
        report_progress=AsyncMock(),
    )


def mcp_client(app_mcp, segredo: str, *, host: str = "localhost:8000", cabecalhos: dict | None = None) -> Client:
    """Modern MCP client talking to the whole ASGI app, inside the process.

    `host` has to match `MCP_ALLOWED_HOSTS` (the default covers
    `localhost:*`): the transport rejects any other with 421.
    """
    extras = {"Authorization": f"Bearer {segredo}"} if segredo else {}
    extras.update(cabecalhos or {})
    return Client(
        streamable_http_client(
            f"http://{host}/mcp",
            http_client=httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app_mcp),
                base_url=f"http://{host}",
                headers=extras,
            ),
        )
    )


class FakeRedis:
    """Fake Redis: only the commands the MCP uses, in a dictionary.

    TTL is counted as "this much was requested", not by the clock: the tests
    check that the `EXPIRE` happened and that `retry_after_seconds` comes from
    the TTL, not the passage of time. "Time passed" is written by hand, in
    `ttls[chave]`.

    It also serves the tests of the window counter (`count_in_window`), which
    is a MULTI/EXEC with `EXPIRE ... NX`: hence `pipeline()` and `nx`.
    """

    def __init__(self) -> None:
        self.dados: dict[str, object] = {}
        self.ttls: dict[str, int] = {}
        self.chamadas: list[tuple] = []

    async def get(self, chave):
        self.chamadas.append(("get", chave))
        return self.dados.get(chave)

    async def mget(self, *chaves):
        self.chamadas.append(("mget", chaves))
        return [self.dados.get(chave) for chave in chaves]

    async def set(self, chave, valor, nx: bool = False, ex: int | None = None):
        self.chamadas.append(("set", chave, nx, ex))
        if nx and chave in self.dados:
            return None
        self.dados[chave] = valor
        if ex is not None:
            self.ttls[chave] = ex
        return True

    async def setex(self, chave, segundos, valor):
        self.chamadas.append(("setex", chave, segundos))
        self.dados[chave] = valor
        self.ttls[chave] = segundos
        return True

    async def incr(self, chave):
        self.chamadas.append(("incr", chave))
        novo = int(self.dados.get(chave, 0)) + 1
        self.dados[chave] = novo
        return novo

    async def incrby(self, chave, quanto):
        self.chamadas.append(("incrby", chave, quanto))
        novo = int(self.dados.get(chave, 0)) + int(quanto)
        self.dados[chave] = novo
        return novo

    async def decr(self, chave):
        self.chamadas.append(("decr", chave))
        novo = int(self.dados.get(chave, 0)) - 1
        self.dados[chave] = novo
        return novo

    async def expire(self, chave, segundos, nx: bool = False):
        self.chamadas.append(("expire", chave, segundos))
        if nx and (chave not in self.dados or chave in self.ttls):
            # NX: only sets the expiry of a key that exists and has none.
            return False
        self.ttls[chave] = segundos
        return True

    def pipeline(self, transaction: bool = True):
        return _FakePipeline(self, transaction)

    async def ttl(self, chave):
        self.chamadas.append(("ttl", chave))
        return self.ttls.get(chave, -1)

    async def exists(self, *chaves):
        self.chamadas.append(("exists", *chaves))
        return sum(1 for chave in chaves if chave in self.dados)

    async def delete(self, *chaves):
        self.chamadas.append(("delete", *chaves))
        apagadas = 0
        for chave in chaves:
            if self.dados.pop(chave, None) is not None:
                apagadas += 1
            self.ttls.pop(chave, None)
        return apagadas

    async def lrange(self, chave, inicio, fim):
        self.chamadas.append(("lrange", chave, inicio, fim))
        lista = self.dados.get(chave) or []
        if fim == -1:
            return list(lista[inicio:])
        return list(lista[inicio : fim + 1])


class _FakePipeline:
    """`FakeRedis`'s `pipeline()`: each command enters the queue and `execute()`
    runs the whole queue in order, without yielding the loop midway — which
    is, here, the atomicity of MULTI/EXEC. Records `("exec", [comandos])` in
    `chamadas` so the test can see what went out together in the same
    transaction."""

    def __init__(self, redis: FakeRedis, transacao: bool) -> None:
        self._redis = redis
        self._transaction = transacao
        self._fila: list[tuple] = []

    def __getattr__(self, nome):
        comando = getattr(self._redis, nome)

        def _enqueue(*args, **kwargs):
            self._fila.append((nome, comando, args, kwargs))
            return self

        return _enqueue

    async def execute(self):
        fila, self._fila = self._fila, []
        self._redis.chamadas.append(
            ("exec" if self._transaction else "pipeline", [nome for nome, *_ in fila])
        )
        return [await comando(*args, **kwargs) for _, comando, args, kwargs in fila]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self._fila = []
