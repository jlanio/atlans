"""Regression of the credential guard when saving a workflow (audit SEG-12).

The guard lives in `WorkflowService`: REST checked at the edge, but MCP saved
without it with `validate_first=False`, when duplicating and when restoring a
version. Here the function is proven and, through MCP, that the four writes
inherit it.
"""
from __future__ import annotations

import inspect
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import CredentialAccessDeniedError
from app.core.utils.encryption import encrypt_workflow_connections
from app.mcp import infra
from app.mcp.tools.acervo import duplicate_workflow, restore_workflow_version
from app.mcp.tools.construcao import create_workflow, update_workflow
from app.models.base import Base
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.schemas.workflow import WorkflowUpdate
from app.services.workflow_service import WorkflowService, assert_definition_credentials
from tests.unit._mcp_harness import (
    TABLES,
    create_user,
    create_workspace,
    fake_ctx,
    fake_scope,
)

_TARGET = "app.services.workflow_service.assert_credentials_accessible"

WS_1 = "11111111-1111-4111-8111-111111111111"
WF_1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
FOREIGN_CRED = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

_DEF = {"nodes": [{"name": "HttpRequest", "properties": {"credential_id": "cred-1", "url": "https://x"}}]}


def _definition_with_credential(url: str = "https://atacante.exemplo/coleta") -> dict:
    return {
        "nodes": [{
            "id": "n1", "name": "HttpRequest", "type": "integration",
            "properties": {"credential_id": FOREIGN_CRED, "url": url},
        }],
        "edges": [],
    }


def _definition_without_credential() -> dict:
    return {"nodes": [{"id": "n1", "name": "SetFields", "type": "transform", "properties": {}}], "edges": []}


# ── The function ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refuses_inaccessible_credential_with_domain_error_403():
    with patch(_TARGET, new=AsyncMock(side_effect=CredentialAccessDeniedError("nao"))):
        with pytest.raises(CredentialAccessDeniedError) as ei:
            await assert_definition_credentials(
                AsyncMock(), _DEF, user_id="u1", workspace_id="ws1",
            )
    assert ei.value.status_code == 403
    assert "credencial que você não pode usar" in ei.value.detail


@pytest.mark.asyncio
async def test_passes_when_credential_is_accessible():
    with patch(_TARGET, new=AsyncMock(return_value=None)) as chk:
        await assert_definition_credentials(
            AsyncMock(), _DEF, user_id="u1", workspace_id="ws1",
        )
    chk.assert_awaited_once()
    _, ids, user_id = chk.await_args.args
    assert ids == ["cred-1"] and user_id == "u1"
    assert chk.await_args.kwargs == {"shared_workspace_id": "ws1"}


@pytest.mark.asyncio
async def test_without_credential_in_definition_checks_nothing():
    with patch(_TARGET, new=AsyncMock()) as chk:
        await assert_definition_credentials(
            AsyncMock(), {"nodes": [{"name": "Buffer", "properties": {}}]},
            user_id="u1", workspace_id="ws1",
        )
    chk.assert_not_awaited()


# ── The MCP writes inherit the guard ────────────────────────────────────────


def ctx():
    return fake_ctx(fake_scope(
        scopes={"workflows:read", "workflows:write"}, workspace_ids={WS_1},
    ))


def corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


@pytest.fixture
async def banco(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=TABLES)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def _session():
        async with fabrica() as db:
            try:
                yield db
            finally:
                await db.rollback()

    monkeypatch.setattr(infra, "sessao", _session)
    async with fabrica() as db:
        await create_user(db, "usr-1", "ana")
        await create_workspace(db, WS_1, "usr-1", "Principal")
    try:
        yield fabrica
    finally:
        await engine.dispose()


@pytest.fixture
def foreign_credential():
    """`assert_credentials_accessible` refusing: the credential is another member's private one."""
    with patch(_TARGET, new=AsyncMock(side_effect=CredentialAccessDeniedError("privada"))) as chk:
        yield chk


async def _workflows(fabrica) -> list[Workflow]:
    async with fabrica() as db:
        return list((await db.execute(select(Workflow))).scalars().all())


async def _insert(fabrica, definition: dict) -> None:
    async with fabrica() as db:
        db.add(Workflow(id_hash=WF_1, name="Compartilhado", workspace_id=WS_1,
                        definition=encrypt_workflow_connections(definition), flag_ative=True))
        await db.commit()


async def test_create_without_validating_does_not_skip_the_guard(banco, foreign_credential):
    """`validate_first=False` skipped the check, which existed only in validation."""
    with pytest.raises(ToolError) as exc:
        await create_workflow(
            ctx(), name="Plantado", definition=_definition_with_credential(), validate_first=False,
        )
    assert corpo(exc.value)["code"] == "forbidden"
    assert await _workflows(banco) == []
    foreign_credential.assert_awaited_once()
    assert foreign_credential.await_args.args[2] == "usr-1"
    assert foreign_credential.await_args.kwargs == {"shared_workspace_id": WS_1}


async def test_create_with_accessible_credential_stores(banco):
    with patch(_TARGET, new=AsyncMock(return_value=None)) as chk:
        await create_workflow(
            ctx(), name="Meu", definition=_definition_with_credential("https://api.exemplo"),
            validate_first=False,
        )
    chk.assert_awaited_once()
    assert [w.name for w in await _workflows(banco)] == ["Meu"]


async def test_update_without_validating_does_not_skip_the_guard(banco, foreign_credential):
    await _insert(banco, _definition_without_credential())
    with pytest.raises(ToolError) as exc:
        await update_workflow(
            ctx(), WF_1, definition=_definition_with_credential(), validate_first=False,
        )
    assert corpo(exc.value)["code"] == "forbidden"
    (wf,) = await _workflows(banco)
    assert wf.definition["nodes"][0]["name"] == "SetFields"


async def test_name_only_update_does_not_query_credential(banco, foreign_credential):
    """The guard is about the definition: renaming a workflow that already has
    someone else's credential (saved by someone who can reach it) must not be
    blocked by it."""
    await _insert(banco, _definition_with_credential())
    await update_workflow(ctx(), WF_1, name="Renomeado")
    foreign_credential.assert_not_awaited()
    (wf,) = await _workflows(banco)
    assert wf.name == "Renomeado"


async def test_duplicate_does_not_copy_credential_the_duplicator_cannot_reach(banco, foreign_credential):
    await _insert(banco, _definition_with_credential())
    with pytest.raises(ToolError) as exc:
        await duplicate_workflow(ctx(), WF_1)
    assert corpo(exc.value)["code"] == "forbidden"
    assert len(await _workflows(banco)) == 1


async def test_restore_does_not_reintroduce_unreachable_credential(banco, foreign_credential):
    await _insert(banco, _definition_without_credential())
    async with banco() as db:
        db.add(WorkflowVersion(
            workflow_hash=WF_1, version_number=1,
            definition=encrypt_workflow_connections(_definition_with_credential()),
            change_note="antiga",
        ))
        await db.commit()

    with pytest.raises(ToolError) as exc:
        await restore_workflow_version(ctx(), WF_1, 1)
    assert corpo(exc.value)["code"] == "forbidden"
    (wf,) = await _workflows(banco)
    assert wf.definition["nodes"][0]["name"] == "SetFields"
    async with banco() as db:
        versoes = (await db.execute(select(WorkflowVersion))).scalars().all()
    assert len(versoes) == 1  # not even the auto-snapshot was saved


async def test_restore_missing_version_stays_not_found(banco, foreign_credential):
    await _insert(banco, _definition_without_credential())
    with pytest.raises(ToolError) as exc:
        await restore_workflow_version(ctx(), WF_1, 7)
    assert corpo(exc.value)["code"] == "not_found"


# ── params_schema: sibling column, goes raw to the database ─────────────────


_SCHEMA_WITH_SECRET = {"token": "tok_vivo_nao_pode_entrar_123456"}  # pragma: allowlist secret


async def test_create_refuses_secret_in_params_schema(banco):
    with pytest.raises(ToolError) as exc:
        await create_workflow(
            ctx(), name="X", definition=_definition_without_credential(),
            params_schema=_SCHEMA_WITH_SECRET, validate_first=False,
        )
    assert corpo(exc.value)["code"] == "secret_in_definition"
    assert "tok_vivo" not in str(exc.value)
    assert await _workflows(banco) == []


async def test_update_refuses_secret_in_params_schema(banco):
    await _insert(banco, _definition_without_credential())
    with pytest.raises(ToolError) as exc:
        await update_workflow(ctx(), WF_1, params_schema=_SCHEMA_WITH_SECRET)
    assert corpo(exc.value)["code"] == "secret_in_definition"
    (wf,) = await _workflows(banco)
    assert not wf.params_schema


# ── params_schema: only what it stores as a VALUE ───────────────────────────


def test_merely_declared_token_parameter_is_not_a_secret():
    """The lint itself suggests `{"token": {"type": "string", "required": true}}`:
    refusing it prevented saving the validation's own suggestion."""
    from app.core.utils.redacao import params_schema_contains_secret

    assert params_schema_contains_secret({"token": {"type": "string", "required": True}}) == []
    assert params_schema_contains_secret({"password": {"type": "string", "label": "Senha do banco"}}) == []


def test_value_stored_in_the_schema_stays_refused():
    from app.core.utils.redacao import params_schema_contains_secret

    assert params_schema_contains_secret(
        {"token": {"type": "string", "default": "tok_vivo_123456"}}  # pragma: allowlist secret
    ) == ["params_schema.token.default"]
    assert params_schema_contains_secret(
        {"banco": {"type": "string", "default": "postgresql://u:SenhaForte9@h/db"}}  # pragma: allowlist secret
    ) == ["params_schema.banco.default"]
    assert params_schema_contains_secret({"x": {"type": "string", "description": "<REDACTED>"}}) == [
        "params_schema.x.description",
    ]
    assert params_schema_contains_secret("não é objeto") == []


async def test_create_accepts_the_schema_validation_suggests(banco):
    await create_workflow(
        ctx(), name="Com token", definition=_definition_without_credential(),
        params_schema={"token": {"type": "string", "required": True}}, validate_first=False,
    )
    (wf,) = await _workflows(banco)
    assert wf.params_schema == {"token": {"type": "string", "required": True}}


# ── REST: the service's refusal comes out as 403, never as 400/500 ─────────
# The routes call the service inside `try`s that translate other errors; if
# the translation swallows `CredentialAccessDeniedError`, the guard becomes
# "Não foi possível atualizar" (could not update) (400) and the user does not
# know why.


class _StubService:
    def __init__(self):
        self.erro = CredentialAccessDeniedError("A definição referencia credencial que você não pode usar.")

    async def update_workflow(self, *a, **kw):
        raise self.erro

    async def create_workflow(self, *a, **kw):
        raise self.erro

    async def duplicate_workflow(self, *a, **kw):
        raise self.erro

    async def restore_version(self, *a, **kw):
        raise self.erro


class _Wf:
    id_hash = WF_1
    workspace_id = WS_1
    name = "Compartilhado"
    definition = {"nodes": [], "edges": []}


class _FakeUser:
    id_hash = "usr-1"


@pytest.fixture
def rota_rest(monkeypatch):
    from app.api.routers import workflows_router as WR

    # The role comes from the route's dependency (`workflow_com_papel`), which the
    # direct call does not go through; here only the limiter gets in the way.
    monkeypatch.setattr(WR.limiter, "enabled", False)

    async def _no_errors(*a, **kw):
        return []

    monkeypatch.setattr(
        "flow.utils.workflow_contract.validate_subworkflow_references_against_db", _no_errors,
    )
    return WR


async def test_update_rest_lets_the_403_through(rota_rest):
    from app.schemas.workflow import WorkflowUpdate

    with pytest.raises(CredentialAccessDeniedError) as exc:
        await rota_rest.update_workflow(
            request=None, workflow_in=WorkflowUpdate(definition=_definition_with_credential()),
            service=_StubService(), wf=_Wf(), db=None, current_user=_FakeUser(),
        )
    assert exc.value.status_code == 403


async def test_duplicate_and_restore_rest_let_the_403_through(rota_rest):
    with pytest.raises(CredentialAccessDeniedError):
        await rota_rest.duplicate_workflow(
            request=None, payload=None, service=_StubService(), wf=_Wf(),
            db=None, current_user=_FakeUser(),
        )
    with pytest.raises(CredentialAccessDeniedError):
        await rota_rest.restore_version(
            request=None, version_number=1, service=_StubService(), wf=_Wf(),
            current_user=_FakeUser(),
        )


async def test_restore_version_that_no_longer_decrypts_proceeds_if_the_credential_is_accessible(banco):
    """The check reads the raw version: `credential_id` is not encrypted, and
    opening the blob made a `connectionString` that no longer decrypts (rotated
    key) turn into an "unexpected error" — the restore itself only copies the
    blob."""
    await _insert(banco, _definition_without_credential())
    antiga = {"nodes": [{"id": "n1", "name": "DatabaseQuery", "type": "database", "properties": {
        "credential_id": FOREIGN_CRED, "connectionString": "gAAAAA-cifrado-com-chave-antiga",
    }}], "edges": []}
    async with banco() as db:
        db.add(WorkflowVersion(workflow_hash=WF_1, version_number=1, definition=antiga, change_note="antiga"))
        await db.commit()

    with patch(_TARGET, new=AsyncMock(return_value=None)) as chk:
        out = await restore_workflow_version(ctx(), WF_1, 1)
    chk.assert_awaited_once()
    assert out["restored_from_version"] == 1


# ── No write saves without an author ────────────────────────────────────────
# The guard checks the definition against WHO is saving, and only ran when the
# caller passed the author — which was optional. Every production caller
# passed it; a new caller that forgot it would silently skip the guard.
# These tests fail if any of the four writes starts accepting that again.

_WRITES = [
    ("create_workflow", "created_by_id", ("Fluxo", {"nodes": []})),
    ("update_workflow", "updated_by_id", (WF_1, WorkflowUpdate(name="Outro"))),
    ("duplicate_workflow", "duplicated_by", (WF_1,)),
    ("restore_version", "restored_by", (WF_1, 1)),
]
_IDS = [escrita[0] for escrita in _WRITES]


class _UntouchableCrud:
    """Any use fails the test: the refusal has to come before the service touches the database."""

    def __getattr__(self, nome):
        raise AssertionError(f"escrita sem autor chegou ao CRUD ({nome})")


def _service_without_db() -> WorkflowService:
    servico = WorkflowService.__new__(WorkflowService)
    servico.crud = _UntouchableCrud()
    return servico


@pytest.mark.parametrize("metodo, autor, _args", _WRITES, ids=_IDS)
def test_the_author_is_required_and_keyword_only(metodo, autor, _args):
    parametro = inspect.signature(getattr(WorkflowService, metodo)).parameters.get(autor)
    assert parametro is not None, f"{metodo} perdeu o parâmetro {autor}"
    assert parametro.kind is inspect.Parameter.KEYWORD_ONLY, f"{autor} tem de ser keyword-only"
    assert parametro.default is inspect.Parameter.empty, f"{metodo}: {autor} voltou a ter default"


@pytest.mark.parametrize("metodo, _autor, args", _WRITES, ids=_IDS)
def test_write_without_author_does_not_even_start(metodo, _autor, args):
    try:
        corrotina = getattr(_service_without_db(), metodo)(*args)
    except TypeError:
        return
    corrotina.close()
    pytest.fail(f"{metodo} aceitou ser chamada sem autor")


@pytest.mark.parametrize("vazio", [None, ""])
@pytest.mark.parametrize("metodo, autor, args", _WRITES, ids=_IDS)
async def test_empty_author_is_also_refused(metodo, autor, args, vazio):
    """An explicit `None` — a careless `getattr(user, "id_hash", None)` — would
    skip the guard just like the forgotten argument."""
    with pytest.raises(TypeError, match="autor"):
        await getattr(_service_without_db(), metodo)(*args, **{autor: vazio})
