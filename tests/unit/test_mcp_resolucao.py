# tests/unit/test_mcp_resolucao.py
"""
Resolving a name or id to a resource — without handing over what the token can't reach.

Accepting names is what makes the tools usable by someone chatting ("run the
Recorte mensal"), and it is also where a careless server leaks information: a
"not found" different from a "forbidden" already says whether the resource
exists on the other side of the wall, and picking "the first" of two namesakes
makes the tool act on something nobody pointed at.

What this file pins down:

- a repeated name becomes `ambiguous` with the candidates' ids — never a guess;
- a nonexistent workflow, a deleted workflow and ANOTHER account's workflow
  answer the same `not_found`, with the same sentence: the difference between
  "doesn't exist" and "exists and you can't reach it" is precisely what a client
  with a loop over ids would use to map what is on the other side;
- the TOKEN's reach cuts before the user's role: a token restricted to one
  workspace doesn't see the neighbor's workflow even when the owner owns both;
- with a single workspace in reach, `workspace_id` is optional.

In-memory SQLite database, because what is tested here ARE the queries.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.core.utils.datetime_utils import utc_now_naive
from app.mcp.resolucao import carregar_workflow, e_uuid, resolve_workspace
from app.models.workflow import Workflow
from app.models.workspace_member import WorkspaceMember
from tests.unit._mcp_harness import (
    in_memory_db,
    create_user,
    create_workspace,
    fake_scope,
)

ID_A = "11111111-1111-4111-8111-111111111111"
ID_B = "22222222-2222-4222-8222-222222222222"


def corpo(exc: ToolError) -> dict:
    """The JSON that travels inside the `ToolError`."""
    return json.loads(str(exc))


async def create_workflow_row(db, *, id_hash: str, nome: str, workspace_id: str, apagado=False) -> Workflow:
    wf = Workflow(
        id_hash=id_hash,
        name=nome,
        workspace_id=workspace_id,
        definition={"nodes": [], "edges": []},
        deleted_at=utc_now_naive() if apagado else None,
    )
    db.add(wf)
    await db.commit()
    return wf


async def make_member(db, workspace_id: str, user_id: str, papel: str = "viewer") -> None:
    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=papel))
    await db.commit()


@pytest.fixture
async def banco():
    """Two workspaces of the same owner, for the ambiguity and reach cases."""
    async with in_memory_db() as fabrica:
        async with fabrica() as db:
            await create_user(db, "usr-1", "ana")
            await create_workspace(db, "ws-1", "usr-1", "Principal")
            await create_workspace(db, "ws-2", "usr-1", "Secundário")
        yield fabrica


# ── e_uuid ────────────────────────────────────────────────────────────────────


def test_is_uuid_separates_identifier_from_name():
    assert e_uuid(ID_A) is True
    assert e_uuid("Recorte mensal") is False
    assert e_uuid("") is False
    assert e_uuid(None) is False


# ── resolve_workspace ────────────────────────────────────────────────────────


async def test_single_workspace_makes_the_parameter_optional(banco):
    async with banco() as db:
        assert await resolve_workspace(db, fake_scope(workspace_ids={"ws-1"}), None) == "ws-1"


async def test_with_two_workspaces_omission_becomes_ambiguous_with_the_candidates(banco):
    escopo = fake_scope(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolve_workspace(db, escopo, None)
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}
    assert {c["name"] for c in detalhe["candidates"]} == {"Principal", "Secundário"}


async def test_workspace_by_name_within_scope(banco):
    escopo = fake_scope(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        assert await resolve_workspace(db, escopo, "Secundário") == "ws-2"


async def test_name_repeated_in_two_workspaces_becomes_ambiguous(banco):
    async with banco() as db:
        await create_workspace(db, "ws-3", "usr-1", "Principal")
    escopo = fake_scope(workspace_ids={"ws-1", "ws-3"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolve_workspace(db, escopo, "Principal")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-3"}


async def test_workspace_id_out_of_scope_is_forbidden(banco):
    """It exists, the user is the owner — but the token can't reach it.

    The reference is id-shaped (it is a UUID, like every `id_hash` in Atlans),
    and the refusal is `forbidden` without querying the database: no query
    means no chance of the response revealing whether that id exists.
    """
    async with banco() as db:
        await create_workspace(db, ID_B, "usr-1", "Terceiro")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolve_workspace(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"


async def test_unknown_workspace_name_is_not_found(banco):
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolve_workspace(db, escopo, "Inexistente")
    assert corpo(exc.value)["code"] == "not_found"


async def test_token_without_any_workspace_is_forbidden(banco):
    escopo = fake_scope(workspace_ids=set())
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolve_workspace(db, escopo, None)
    assert corpo(exc.value)["code"] == "forbidden"


# ── carregar_workflow ─────────────────────────────────────────────────────────


async def test_loads_by_id_and_returns_the_role(banco):
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
    # Workspace owner: the highest role, above admin.
    assert papel == "owner"


async def test_loads_by_name(banco):
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_A, nome="Recorte mensal", workspace_id="ws-1")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, "Recorte mensal")
    assert wf.id_hash == ID_A


async def test_name_repeated_in_two_workspaces_lists_the_ids(banco):
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
        await create_workflow_row(db, id_hash=ID_B, nome="Recorte", workspace_id="ws-2")
    escopo = fake_scope(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Recorte")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {ID_A, ID_B}
    assert {c["workspace_id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}


async def test_deleted_workflow_answers_not_found(banco):
    """The trash is not a 403: for the caller, the workflow no longer exists."""
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_A, nome="Antigo", workspace_id="ws-1", apagado=True)
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_A)
    assert corpo(exc.value)["code"] == "not_found"
    # And the same through the name lookup.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Antigo")
    assert corpo(exc.value)["code"] == "not_found"


async def test_nonexistent_id_is_not_found_before_any_403(banco):
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "33333333-3333-4333-8333-333333333333")
    assert corpo(exc.value)["code"] == "not_found"


async def test_id_of_another_account_answers_byte_for_byte_like_nonexistent_id(banco):
    """The cross-account existence oracle, closed in the text and in the code.

    The workflow exists, in a workspace of another account, and the user is not
    a member. The core answers 403 (and keeps answering it — REST depends on
    that); here the response is the SAME as for an id that never existed, byte
    for byte. If any difference remained — the `code`, a word in the sentence,
    the `hint` —, whoever had a read token could sweep identifiers and find out
    which ones exist on the other side of the wall.
    """
    async with banco() as db:
        await create_user(db, "usr-2", "bruno")
        await create_workspace(db, "ws-9", "usr-2", "De outro")
        await create_workflow_row(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = fake_scope(workspace_ids={"ws-1"})

    async with banco() as db:
        with pytest.raises(ToolError) as alheio:
            await carregar_workflow(db, escopo, ID_B)
    async with banco() as db:
        with pytest.raises(ToolError) as inexistente:
            await carregar_workflow(db, escopo, "33333333-3333-4333-8333-333333333333")

    assert corpo(alheio.value)["code"] == "not_found"
    assert str(alheio.value) == str(inexistente.value)
    # And the received reference doesn't come back in the message: echoing the id
    # would be the same oracle through another door (the sentence would tell the
    # two calls apart).
    assert ID_B not in str(alheio.value)


async def test_workflow_name_out_of_scope_does_not_reveal_existence(banco):
    """By name the answer is `not_found`: the scope filter goes into the query."""
    async with banco() as db:
        await create_user(db, "usr-2", "bruno")
        await create_workspace(db, "ws-9", "usr-2", "De outro")
        await create_workflow_row(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Alheio")
    assert corpo(exc.value)["code"] == "not_found"


async def test_restricted_token_does_not_see_its_own_owners_workspace(banco):
    """The owner reaches both workspaces; the token, only one. The token wins.

    It is the case that separates "what the user can do" from "what this token
    can do" — and what keeps a read token issued for one project from serving
    as a key to all the others.

    Here the refusal is `forbidden`, and not the cross-account case's
    `not_found`, on purpose: the resource belongs to the very account that
    issued the token, which already sees it in the interface and with any other
    token of its own. There is no existence to hide from its owner — there is a
    reach to explain, and saying "this token doesn't get here" is what saves
    half an hour looking for a workflow that didn't vanish.
    """
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_B, nome="Do outro projeto", workspace_id="ws-2")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"
    # By name, it doesn't even show up as existing.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Do outro projeto")
    assert corpo(exc.value)["code"] == "not_found"


async def test_regular_member_loads_with_the_member_role(banco):
    async with banco() as db:
        await create_user(db, "usr-2", "bruno")
        await make_member(db, "ws-1", "usr-2", "editor")
        await create_workflow_row(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = fake_scope(user_id="usr-2", workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert (wf.id_hash, papel) == (ID_A, "editor")


async def test_load_by_id_does_not_decrypt_by_default(banco, monkeypatch):
    """`decifrar=False` is the default: no cleartext definition in the session."""
    from app.services import workflow_service

    async def _should_not_be_called(*args, **kwargs):  # pragma: no cover - the test fails first
        raise AssertionError("o caminho que decifra não pode ser usado pelo MCP")

    monkeypatch.setattr(
        workflow_service.WorkflowService, "get_workflow_by_hash", _should_not_be_called, raising=True
    )
    async with banco() as db:
        await create_workflow_row(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = fake_scope(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
