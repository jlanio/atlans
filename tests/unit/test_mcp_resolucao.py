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
from app.mcp.resolucao import carregar_workflow, e_uuid, resolver_workspace
from app.models.workflow import Workflow
from app.models.workspace_member import WorkspaceMember
from tests.unit._mcp_harness import (
    banco_em_memoria,
    criar_usuario,
    criar_workspace,
    escopo_falso,
)

ID_A = "11111111-1111-4111-8111-111111111111"
ID_B = "22222222-2222-4222-8222-222222222222"


def corpo(exc: ToolError) -> dict:
    """The JSON that travels inside the `ToolError`."""
    return json.loads(str(exc))


async def criar_workflow(db, *, id_hash: str, nome: str, workspace_id: str, apagado=False) -> Workflow:
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


async def tornar_membro(db, workspace_id: str, user_id: str, papel: str = "viewer") -> None:
    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=papel))
    await db.commit()


@pytest.fixture
async def banco():
    """Two workspaces of the same owner, for the ambiguity and reach cases."""
    async with banco_em_memoria() as fabrica:
        async with fabrica() as db:
            await criar_usuario(db, "usr-1", "ana")
            await criar_workspace(db, "ws-1", "usr-1", "Principal")
            await criar_workspace(db, "ws-2", "usr-1", "Secundário")
        yield fabrica


# ── e_uuid ────────────────────────────────────────────────────────────────────


def test_e_uuid_separa_identificador_de_nome():
    assert e_uuid(ID_A) is True
    assert e_uuid("Recorte mensal") is False
    assert e_uuid("") is False
    assert e_uuid(None) is False


# ── resolver_workspace ────────────────────────────────────────────────────────


async def test_workspace_unico_dispensa_o_parametro(banco):
    async with banco() as db:
        assert await resolver_workspace(db, escopo_falso(workspace_ids={"ws-1"}), None) == "ws-1"


async def test_com_dois_workspaces_a_omissao_vira_ambiguous_com_os_candidatos(banco):
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, None)
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}
    assert {c["name"] for c in detalhe["candidates"]} == {"Principal", "Secundário"}


async def test_workspace_por_nome_dentro_do_escopo(banco):
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        assert await resolver_workspace(db, escopo, "Secundário") == "ws-2"


async def test_nome_repetido_em_dois_workspaces_vira_ambiguous(banco):
    async with banco() as db:
        await criar_workspace(db, "ws-3", "usr-1", "Principal")
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-3"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, "Principal")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {"ws-1", "ws-3"}


async def test_id_de_workspace_fora_do_escopo_e_proibido(banco):
    """It exists, the user is the owner — but the token can't reach it.

    The reference is id-shaped (it is a UUID, like every `id_hash` in Atlans),
    and the refusal is `forbidden` without querying the database: no query
    means no chance of the response revealing whether that id exists.
    """
    async with banco() as db:
        await criar_workspace(db, ID_B, "usr-1", "Terceiro")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"


async def test_nome_de_workspace_desconhecido_e_not_found(banco):
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, "Inexistente")
    assert corpo(exc.value)["code"] == "not_found"


async def test_token_sem_workspace_nenhum_e_proibido(banco):
    escopo = escopo_falso(workspace_ids=set())
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await resolver_workspace(db, escopo, None)
    assert corpo(exc.value)["code"] == "forbidden"


# ── carregar_workflow ─────────────────────────────────────────────────────────


async def test_carrega_por_id_e_devolve_o_papel(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
    # Workspace owner: the highest role, above admin.
    assert papel == "owner"


async def test_carrega_por_nome(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte mensal", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, "Recorte mensal")
    assert wf.id_hash == ID_A


async def test_nome_repetido_em_dois_workspaces_lista_os_ids(banco):
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
        await criar_workflow(db, id_hash=ID_B, nome="Recorte", workspace_id="ws-2")
    escopo = escopo_falso(workspace_ids={"ws-1", "ws-2"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Recorte")
    detalhe = corpo(exc.value)
    assert detalhe["code"] == "ambiguous"
    assert {c["id"] for c in detalhe["candidates"]} == {ID_A, ID_B}
    assert {c["workspace_id"] for c in detalhe["candidates"]} == {"ws-1", "ws-2"}


async def test_workflow_apagado_responde_not_found(banco):
    """The trash is not a 403: for the caller, the workflow no longer exists."""
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Antigo", workspace_id="ws-1", apagado=True)
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_A)
    assert corpo(exc.value)["code"] == "not_found"
    # And the same through the name lookup.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Antigo")
    assert corpo(exc.value)["code"] == "not_found"


async def test_id_inexistente_e_not_found_antes_de_qualquer_403(banco):
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "33333333-3333-4333-8333-333333333333")
    assert corpo(exc.value)["code"] == "not_found"


async def test_id_de_outra_conta_responde_byte_a_byte_como_id_inexistente(banco):
    """The cross-account existence oracle, closed in the text and in the code.

    The workflow exists, in a workspace of another account, and the user is not
    a member. The core answers 403 (and keeps answering it — REST depends on
    that); here the response is the SAME as for an id that never existed, byte
    for byte. If any difference remained — the `code`, a word in the sentence,
    the `hint` —, whoever had a read token could sweep identifiers and find out
    which ones exist on the other side of the wall.
    """
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, "ws-9", "usr-2", "De outro")
        await criar_workflow(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = escopo_falso(workspace_ids={"ws-1"})

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


async def test_nome_de_workflow_fora_do_escopo_nao_revela_existencia(banco):
    """By name the answer is `not_found`: the scope filter goes into the query."""
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await criar_workspace(db, "ws-9", "usr-2", "De outro")
        await criar_workflow(db, id_hash=ID_B, nome="Alheio", workspace_id="ws-9")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Alheio")
    assert corpo(exc.value)["code"] == "not_found"


async def test_token_restrito_nao_ve_workspace_do_proprio_dono(banco):
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
        await criar_workflow(db, id_hash=ID_B, nome="Do outro projeto", workspace_id="ws-2")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, ID_B)
    assert corpo(exc.value)["code"] == "forbidden"
    # By name, it doesn't even show up as existing.
    async with banco() as db:
        with pytest.raises(ToolError) as exc:
            await carregar_workflow(db, escopo, "Do outro projeto")
    assert corpo(exc.value)["code"] == "not_found"


async def test_membro_comum_carrega_com_o_papel_de_membro(banco):
    async with banco() as db:
        await criar_usuario(db, "usr-2", "bruno")
        await tornar_membro(db, "ws-1", "usr-2", "editor")
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(user_id="usr-2", workspace_ids={"ws-1"})
    async with banco() as db:
        wf, papel = await carregar_workflow(db, escopo, ID_A)
    assert (wf.id_hash, papel) == (ID_A, "editor")


async def test_carregar_por_id_nao_decifra_por_padrao(banco, monkeypatch):
    """`decifrar=False` is the default: no cleartext definition in the session."""
    from app.services import workflow_service

    async def _nao_deveria(*args, **kwargs):  # pragma: no cover - the test fails first
        raise AssertionError("o caminho que decifra não pode ser usado pelo MCP")

    monkeypatch.setattr(
        workflow_service.WorkflowService, "get_workflow_by_hash", _nao_deveria, raising=True
    )
    async with banco() as db:
        await criar_workflow(db, id_hash=ID_A, nome="Recorte", workspace_id="ws-1")
    escopo = escopo_falso(workspace_ids={"ws-1"})
    async with banco() as db:
        wf, _ = await carregar_workflow(db, escopo, ID_A)
    assert wf.id_hash == ID_A
