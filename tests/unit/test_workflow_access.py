# tests/unit/test_workflow_access.py
"""
`app/core/authorization/workflow_access.py` — the home of the access guards.

The rules moved out of `app/api/dependencies.py` into a module without
`Depends`, because the MCP server (docs/specs/mcp-server.md §1) needs the SAME
rules without a FastAPI request. Each test here pins down a decision the
dependencies already made — and that a "refactor" could change without breaking
any route:

- 404 BEFORE 403: a workflow that does not exist or is in the trash does not
  reveal whether the id exists in another workspace;
- a resource without a workspace is 403 (not 404);
- a run is authorized by the run's OWN workspace, not the workflow's current one;
- `owner` ranks above `admin`, and the owner is the owner even if also a member;
- a workspace in the trash grants no role and is not listed, for owner or member.

Real database (in-memory SQLite, only the tables involved): the guards are
queries, and a mock of `db.execute` would only prove that the mock returns what
it was told to return.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.authorization import workflow_access as wa
from app.core.exceptions import WorkflowNotFoundError
from app.models.workflow import Workflow


# ── Harness ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def db():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.models.base import Base
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[User.__table__, Workspace.__table__, WorkspaceMember.__table__],
        )
    async with async_sessionmaker(engine, expire_on_commit=False)() as sessao:
        await _seed(sessao)
        yield sessao
    await engine.dispose()


async def _seed(sessao) -> None:
    """Three workspaces, five people.

    ws-a    owner u-dono (who ALSO appears as a "viewer" member — the owner wins);
            u-editor is an editor, u-viewer is a viewer.
    ws-b    owner u-outro; u-dono is only a viewer here.
    ws-lixo owner u-dono, in the trash; u-editor is admin — nobody has a role in it.
    u-fora  is nowhere.
    """
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember

    def _user(id_hash: str) -> User:
        return User(id_hash=id_hash, username=id_hash, email=f"{id_hash}@teste", hashed_password="x")

    sessao.add_all([_user(u) for u in ("u-dono", "u-editor", "u-viewer", "u-outro", "u-fora")])
    sessao.add_all([
        Workspace(id_hash="ws-a", name="A", owner_id="u-dono"),
        Workspace(id_hash="ws-b", name="B", owner_id="u-outro"),
        Workspace(id_hash="ws-lixo", name="Lixo", owner_id="u-dono", deleted_at=datetime(2026, 9, 1)),
    ])
    sessao.add_all([
        WorkspaceMember(workspace_id="ws-a", user_id="u-dono", role="viewer"),
        WorkspaceMember(workspace_id="ws-a", user_id="u-editor", role="editor"),
        WorkspaceMember(workspace_id="ws-a", user_id="u-viewer", role="viewer"),
        WorkspaceMember(workspace_id="ws-b", user_id="u-dono", role="viewer"),
        WorkspaceMember(workspace_id="ws-lixo", user_id="u-editor", role="admin"),
    ])
    await sessao.commit()


def _workflow(id_hash: str, workspace_id: str, apagado: bool = False) -> Workflow:
    wf = Workflow(id_hash=id_hash, name=id_hash, workspace_id=workspace_id, definition={"nodes": []}, flag_ative=True)
    wf.deleted_at = datetime(2026, 9, 2) if apagado else None
    return wf


class _FakeCrud:
    """`crud.get_by_hash` like the real one: returns the raw ORM object or None, never raises."""

    def __init__(self, by_hash: dict):
        self._by_hash = by_hash
        self.chamadas: list[str] = []

    async def get_by_hash(self, id_hash: str) -> Workflow | None:
        self.chamadas.append(id_hash)
        return self._by_hash.get(id_hash)


class _FakeService:
    """Only what `load_accessible_workflow` uses: `get_workflow_by_hash` and `crud.get_by_hash`.

    `decifrado` marks the definition as the real service would (assigning to
    `wf.definition`), so the test can tell the two paths apart.
    """

    def __init__(self, *workflows: Workflow):
        self._by_hash = {w.id_hash: w for w in workflows}
        self.crud = _FakeCrud(self._by_hash)
        self.decrypted: list[str] = []

    async def get_workflow_by_hash(self, id_hash: str) -> Workflow:
        try:
            wf = self._by_hash[id_hash]
        except KeyError:
            raise WorkflowNotFoundError(f"Workflow '{id_hash}' não encontrado")
        self.decrypted.append(id_hash)
        wf.definition = {**(wf.definition or {}), "decifrado": True}
        return wf


def _status(exc: pytest.ExceptionInfo) -> int:
    return exc.value.status_code


# ══════════════════════════════════════════════════════════════════════════════
# Roles
# ══════════════════════════════════════════════════════════════════════════════

def test_hierarchy_owner_above_admin():
    assert wa.WORKSPACE_ROLE_ORDER == ["viewer", "editor", "operator", "admin", "owner"]
    assert wa.has_minimum_role("owner", "admin")
    assert not wa.has_minimum_role("admin", "owner")
    assert wa.has_minimum_role("editor", "editor")
    assert not wa.has_minimum_role("viewer", "editor")


def test_null_or_unknown_role_never_reaches_minimum():
    assert not wa.has_minimum_role(None, "viewer")
    assert not wa.has_minimum_role("superuser", "viewer")
    # a minimum outside the list is also a "no" — never an exception
    assert not wa.has_minimum_role("owner", "deus")


def test_require_role_403_with_the_default_or_route_message():
    wa.exigir_papel("owner", "admin")          # does not raise
    with pytest.raises(HTTPException) as exc:
        wa.exigir_papel("viewer", "editor")
    assert _status(exc) == 403
    assert exc.value.detail == "Requer role 'editor' ou superior."

    with pytest.raises(HTTPException) as exc:
        wa.exigir_papel(None, "operator", "Só operadores cancelam execuções.")
    assert exc.value.detail == "Só operadores cancelam execuções."


# ══════════════════════════════════════════════════════════════════════════════
# Pertencimento
# ══════════════════════════════════════════════════════════════════════════════

def test_verify_workspace_access_resource_without_workspace_is_403_not_404():
    with pytest.raises(HTTPException) as exc:
        wa.verify_workspace_access(None, ["ws-a"])
    assert _status(exc) == 403
    assert "sem workspace" in exc.value.detail


def test_verify_workspace_access_outside_and_inside():
    with pytest.raises(HTTPException) as exc:
        wa.verify_workspace_access("ws-b", ["ws-a"])
    assert _status(exc) == 403
    assert exc.value.detail == "Acesso negado a este recurso."
    assert wa.verify_workspace_access("ws-a", ["ws-a", "ws-b"]) is None


@pytest.mark.asyncio
async def test_list_workspace_ids_owner_or_member_never_trash(db):
    assert set(await wa.listar_workspace_ids(db, "u-dono")) == {"ws-a", "ws-b"}     # ws-lixo is theirs, and it is not included
    assert set(await wa.listar_workspace_ids(db, "u-editor")) == {"ws-a"}           # admin of ws-lixo, and it is not included
    assert await wa.listar_workspace_ids(db, "u-fora") == []


@pytest.mark.asyncio
async def test_list_workspace_ids_does_not_duplicate_owner_who_is_also_member(db):
    ids = await wa.listar_workspace_ids(db, "u-dono")
    assert ids.count("ws-a") == 1


@pytest.mark.asyncio
async def test_workspace_role_owner_beats_member_and_trash_has_no_role(db):
    assert await wa.get_workspace_member_role(db, "ws-a", "u-dono") == "owner"      # also a "viewer" in the table
    assert await wa.get_workspace_member_role(db, "ws-a", "u-editor") == "editor"
    assert await wa.get_workspace_member_role(db, "ws-b", "u-dono") == "viewer"     # owner of A is only a viewer in B
    assert await wa.get_workspace_member_role(db, "ws-a", "u-fora") is None
    assert await wa.get_workspace_member_role(db, "ws-lixo", "u-dono") is None
    assert await wa.get_workspace_member_role(db, "ws-lixo", "u-editor") is None
    assert await wa.get_workspace_member_role(db, "ws-nao-existe", "u-dono") is None


# ══════════════════════════════════════════════════════════════════════════════
# Workflows and runs
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_load_workflow_returns_workflow_and_role(db):
    servico = _FakeService(_workflow("wf-1", "ws-a"))
    wf, papel = await wa.load_accessible_workflow(servico, db, "wf-1", "u-dono")
    assert wf.id_hash == "wf-1" and papel == "owner"
    _, papel = await wa.load_accessible_workflow(servico, db, "wf-1", "u-editor")
    assert papel == "editor"


@pytest.mark.asyncio
async def test_load_missing_workflow_is_404(db):
    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(_FakeService(), db, "wf-x", "u-dono")
    assert _status(exc) == 404
    assert exc.value.detail == "Workflow 'wf-x' não encontrado"


@pytest.mark.asyncio
async def test_load_workflow_outside_the_workspace_is_403(db):
    servico = _FakeService(_workflow("wf-1", "ws-a"))
    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(servico, db, "wf-1", "u-fora")
    assert _status(exc) == 403
    assert exc.value.detail == "Acesso negado a este recurso."


@pytest.mark.asyncio
async def test_trashed_workflow_is_404_even_for_the_owner_and_before_the_403(db):
    """404 before 403: someone outside the workspace gets the SAME response as
    the owner — the deleted id does not reveal which workspace it lived in."""
    servico = _FakeService(_workflow("wf-apagado", "ws-a", apagado=True))
    for usuario in ("u-dono", "u-fora"):
        with pytest.raises(HTTPException) as exc:
            await wa.load_accessible_workflow(servico, db, "wf-apagado", usuario)
        assert _status(exc) == 404, usuario


@pytest.mark.asyncio
async def test_workflow_of_trashed_workspace_is_403(db):
    """The workflow exists and was not deleted, but the workspace was: no role, 403."""
    servico = _FakeService(_workflow("wf-lixo", "ws-lixo"))
    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(servico, db, "wf-lixo", "u-dono")
    assert _status(exc) == 403


@pytest.mark.asyncio
async def test_load_workflow_without_decrypting_comes_raw_from_crud_with_the_same_rules(db):
    """`decifrar=False` (the MCP path) does not go through `get_workflow_by_hash`:
    the definition stays as it is in the database — encrypted — and nothing is
    dirty in the session. The access rules are the same: 404 for
    nonexistent/deleted, 403 outside."""
    cifrada = {"nodes": [{"properties": {"connectionString": "enc:abc"}}]}
    wf_ok = _workflow("wf-1", "ws-a")
    wf_ok.definition = cifrada
    servico = _FakeService(wf_ok, _workflow("wf-apagado", "ws-a", apagado=True))

    wf, papel = await wa.load_accessible_workflow(servico, db, "wf-1", "u-editor", decifrar=False)
    assert (wf.id_hash, papel) == ("wf-1", "editor")
    assert wf.definition == cifrada                     # not even touched
    assert servico.decrypted == []                     # get_workflow_by_hash was not called
    assert servico.crud.chamadas == ["wf-1"]

    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(servico, db, "wf-x", "u-dono", decifrar=False)
    assert _status(exc) == 404
    assert exc.value.detail == "Workflow 'wf-x' não encontrado"
    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(servico, db, "wf-apagado", "u-dono", decifrar=False)
    assert _status(exc) == 404
    with pytest.raises(HTTPException) as exc:
        await wa.load_accessible_workflow(servico, db, "wf-1", "u-fora", decifrar=False)
    assert _status(exc) == 403
    assert servico.decrypted == []

    # O default continua sendo o da REST: decifra e atribui em `wf.definition`.
    wf, _ = await wa.load_accessible_workflow(servico, db, "wf-1", "u-editor")
    assert servico.decrypted == ["wf-1"]
    assert wf.definition["decifrado"] is True


@pytest.mark.asyncio
async def test_run_role_comes_from_the_run_workspace_not_the_workflow(db):
    """Workflow moved from ws-b to ws-a: ws-b's history still belongs to ws-b."""
    run = SimpleNamespace(workspace_id="ws-b", workflow_hash="wf-1")
    assert await wa.role_in_run_workspace(db, run, "u-editor") is None     # editor em A, nada em B
    assert await wa.role_in_run_workspace(db, run, "u-dono") == "viewer"   # dono de A, viewer em B
    assert await wa.role_in_run_workspace(db, run, "u-outro") == "owner"


# ══════════════════════════════════════════════════════════════════════════════
# A single implementation: dependencies.py re-exports, does not copy
# ══════════════════════════════════════════════════════════════════════════════

def test_dependencies_reexports_the_same_functions():
    from app.api import dependencies as deps

    assert deps.verify_workspace_access is wa.verify_workspace_access
    assert deps.get_workspace_member_role is wa.get_workspace_member_role
    assert deps._has_min_workspace_role is wa._has_min_workspace_role
    assert deps.exigir_papel is wa.exigir_papel
    assert deps.require_workspace_role is wa.require_workspace_role


# ══════════════════════════════════════════════════════════════════════════════
# Minimum role: `require_workspace_role` and the `workflow_com_papel` dependency
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_require_workspace_role_returns_the_role_or_403(db):
    assert await wa.require_workspace_role(db, "ws-a", "u-dono", "admin") == "owner"
    assert await wa.require_workspace_role(db, "ws-a", "u-editor", "editor") == "editor"

    with pytest.raises(HTTPException) as exc:
        await wa.require_workspace_role(db, "ws-a", "u-viewer", "editor")
    assert (_status(exc), exc.value.detail) == (403, "Requer role 'editor' ou superior.")

    with pytest.raises(HTTPException) as exc:
        await wa.require_workspace_role(db, "ws-a", "u-editor", "admin", "Só admin mexe aqui.")
    assert exc.value.detail == "Só admin mexe aqui."


@pytest.mark.asyncio
async def test_require_workspace_role_does_not_distinguish_outside_missing_and_trash(db):
    """All three give the SAME 403: telling them apart would allow enumerating other people's workspaces."""
    respostas = set()
    for ws, usuario in (("ws-a", "u-fora"), ("ws-nao-existe", "u-dono"), ("ws-lixo", "u-editor")):
        with pytest.raises(HTTPException) as exc:
            await wa.require_workspace_role(db, ws, usuario, "viewer", "Sem acesso.")
        respostas.add((_status(exc), exc.value.detail))
    assert respostas == {(403, "Sem acesso.")}


@pytest.mark.asyncio
async def test_workflow_with_role_declares_the_minimum_and_checks_after_access(db):
    """The dependency of the `/workflows/{id_hash}` routes: the access 404 and 403
    come from `load_accessible_workflow` (in that order), and only then the role."""
    from app.api import dependencies as deps

    requires_editor = deps.workflow_com_papel("editor", "Só editor.")
    assert (requires_editor.papel_minimo, requires_editor.mensagem) == ("editor", "Só editor.")

    servico = _FakeService(_workflow("wf-1", "ws-a"), _workflow("wf-apagado", "ws-a", apagado=True))

    async def _resolver(dependency, id_hash, usuario):
        wf_with_role = await deps.get_accessible_workflow_with_role(
            id_hash, servico, db, SimpleNamespace(id_hash=usuario),
        )
        return await dependency(wf_with_role)

    assert (await _resolver(requires_editor, "wf-1", "u-editor")).id_hash == "wf-1"
    with pytest.raises(HTTPException) as exc:
        await _resolver(requires_editor, "wf-1", "u-viewer")
    assert (_status(exc), exc.value.detail) == (403, "Só editor.")
    with pytest.raises(HTTPException) as exc:
        await _resolver(requires_editor, "wf-apagado", "u-viewer")    # 404 before the role
    assert _status(exc) == 404

    membership_only = deps.workflow_com_papel(None)
    assert membership_only.papel_minimo is None
    assert (await _resolver(membership_only, "wf-1", "u-viewer")).id_hash == "wf-1"


@pytest.mark.asyncio
async def test_dependencies_delegate_to_the_module(db):
    """The FastAPI dependencies are wrappers: same result, called without `Depends`."""
    from app.api import dependencies as deps

    usuario = SimpleNamespace(id_hash="u-dono")
    assert set(await deps.get_user_workspace_ids(db, usuario)) == {"ws-a", "ws-b"}

    servico = _FakeService(_workflow("wf-1", "ws-a"))
    wf, papel = await deps.get_accessible_workflow_with_role("wf-1", servico, db, usuario)
    assert (wf.id_hash, papel) == ("wf-1", "owner")
    with pytest.raises(HTTPException) as exc:
        await deps.get_accessible_workflow_with_role("wf-1", servico, db, SimpleNamespace(id_hash="u-fora"))
    assert _status(exc) == 403
