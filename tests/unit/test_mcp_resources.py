# tests/unit/test_mcp_resources.py
"""
The `atlans://…` resources — reads by URI, with the same guard as the tools.

A resource is attractive precisely because it is cheap: the client attaches it
to the context and rereads it without spending a call. That is why it is the
place where a leak would go unnoticed — nobody looks twice at a URI. This file
pins down what matters:

- every registered URI actually answers (a wrong template doesn't fail at
  registration, it fails on read);
- the guide delivered by resource is BYTE FOR BYTE the same as the tool's: if
  they ever diverge, one client learns one thing and the other learns another;
- `atlans://catalog/nodes` without `type` never returns the whole catalog in one
  blob;
- the run (`atlans://runs/{id}`) comes out with the full snapshot of the nodes
  and with the error message redacted and quarantined — it is the second path
  through which a connection string would leave the server;
- insufficient scope and a workspace outside the token's reach are refused —
  here too, not only in the tools;
- and reading workspace data leaves an audit row, as the tool would: without
  it, the resource would be the only path in the server through which one reads
  a workflow without any trace.

The read goes through the in-process `Client(server)`: it is the path that
exercises the SDK's RFC 6570 template matching, which is where a badly written
`{?type}` would show up. With no HTTP request, the scope arrives via the
`ContextVar`.
"""
from __future__ import annotations

import json

import pytest
from mcp import Client

from app.mcp import guia, infra
from app.mcp.escopo import ESCOPO_ATUAL
from app.mcp.servidor import create_mcp_server
from app.mcp.tools.catalogo import get_authoring_guide
from app.models.workflow import Workflow
from tests.unit._mcp_harness import (
    FakeRedis,
    in_memory_db,
    create_run,
    create_user,
    create_workspace,
    fake_ctx,
    fake_scope,
    session_from,
)

# A definition with a cleartext secret: if some resource delivers the definition
# without redacting, this is where it shows up.
DEFINITION_WITH_SECRET = {
    "nodes": [
        {
            "id": "n1",
            "name": "DatabaseSpatialQuery",
            "type": "datasource",
            "properties": {
                "connectionString": "postgresql://usuario:senha-secreta@host/base",  # pragma: allowlist secret
                "query": "SELECT geom FROM lotes",
            },
        },
        {
            "id": "n2",
            "name": "SubWorkflowOutput",
            "type": "output",
            "properties": {"ports": ["camada"]},
        },
    ],
    "edges": [{"source": "n1", "target": "n2", "from_key": "output", "to_key": "camada"}],
}

# A run that failed with the connection string inside the message — the case
# that proves `atlans://runs/{id}` is not a side door to the secret that the
# definition no longer hands out.
DSN = "postgresql://usuario:SenhaLiteral123@db.interno:5432/geo"  # pragma: allowlist secret

NODE_STATS = {
    "n1": {
        "node_name": "Consulta espacial",
        "status": "failed",
        "duration_ms": 900,
        "error": f"falha ao conectar em {DSN}",
        "output_keys": ["gdf"],
        "output_columns": {"gdf": ["id", "geometry"]},
    },
}


async def _create_workflow(db, *, id_hash: str, workspace_id: str, name: str, definition: dict):
    wf = Workflow(
        id_hash=id_hash,
        name=name,
        description="fluxo de teste",
        workspace_id=workspace_id,
        definition=definition,
        flag_ative=True,
    )
    db.add(wf)
    await db.commit()
    return wf


@pytest.fixture
async def ambiente(monkeypatch):
    """Two users, two workspaces, one workflow in each — and the infra redirected.

    The second workspace exists to prove what the first doesn't: that a valid id
    from ANOTHER workspace is not delivered.
    """
    async with in_memory_db() as fabrica:
        async with fabrica() as db:
            await create_user(db, "usr-1", "ana")
            await create_user(db, "usr-2", "bruno")
            await create_workspace(db, "ws-1", "usr-1", "Principal")
            await create_workspace(db, "ws-2", "usr-2", "De outra pessoa")
            await _create_workflow(
                db,
                id_hash="11111111-1111-4111-8111-111111111111",
                workspace_id="ws-1",
                name="Meu fluxo",
                definition=DEFINITION_WITH_SECRET,
            )
            await _create_workflow(
                db,
                id_hash="22222222-2222-4222-8222-222222222222",
                workspace_id="ws-2",
                name="Fluxo alheio",
                definition={"nodes": [], "edges": []},
            )
            await create_run(
                db,
                task_id=MY_RUN,
                workflow_hash="11111111-1111-4111-8111-111111111111",
                workspace_id="ws-1",
                status="failed",
                error_message=f"psycopg2.OperationalError: {DSN}",
                error_category="transient",
                node_stats=NODE_STATS,
            )
            await create_run(
                db,
                task_id=OTHERS_RUN,
                workflow_hash="22222222-2222-4222-8222-222222222222",
                workspace_id="ws-2",
            )
        monkeypatch.setattr(infra, "sessao", session_from(fabrica))
        monkeypatch.setattr(infra, "redis_ou_none", lambda: FakeRedis())
        # No disabled node: the configuration lives in a table the harness's SQLite
        # doesn't create, and what this file investigates is not the overlay.
        monkeypatch.setattr(
            "app.services.node_service.disabled_names",
            _no_disabled,
        )
        yield fabrica


async def _no_disabled(_db):
    return set()


MY_ID = "11111111-1111-4111-8111-111111111111"
OTHERS_ID = "22222222-2222-4222-8222-222222222222"
MY_RUN = "run-1111"
OTHERS_RUN = "run-2222"


async def _read(uri: str, escopo=None) -> str:
    """Reads a URI as a client would, with the scope in the `ContextVar`.

    The failure is kept and re-raised AFTER closing the client: letting it
    propagate from inside the `async with` would wrap it in the session's
    exception group, and the error message — which is the contract these tests
    check — would disappear behind the exception group's "unhandled errors".
    """
    escopo = escopo or fake_scope(scopes={"workflows:read", "drive:read"})
    token = ESCOPO_ATUAL.set(escopo)
    falha: BaseException | None = None
    resultado = None
    try:
        async with Client(create_mcp_server()) as cliente:
            try:
                resultado = await cliente.read_resource(uri)
            except Exception as exc:  # noqa: BLE001 - re-raised below, intact
                falha = exc
    finally:
        ESCOPO_ATUAL.reset(token)
    if falha is not None:
        raise falha
    return "".join(getattr(c, "text", "") or "" for c in resultado.contents)


# ── Registro ──────────────────────────────────────────────────────────────────


async def test_the_seven_uris_are_registered_with_explicit_mime():
    server = create_mcp_server()
    by_uri = {t.uri_template: t for t in await server.list_resource_templates()}
    esperado = {
        "atlans://guide/authoring/{topic}": "text/markdown",
        "atlans://catalog/nodes{?type}": "application/json",
        "atlans://catalog/nodes/{name}": "application/json",
        "atlans://workspaces/{id}/workflows": "application/json",
        "atlans://workflows/{id}": "application/json",
        "atlans://workflows/{id}/contract": "application/json",
        "atlans://runs/{id}": "application/json",
    }
    assert set(esperado) <= set(by_uri)
    for uri, mime in esperado.items():
        assert by_uri[uri].mime_type == mime, f"{uri} sem o mime declarado"


@pytest.mark.parametrize(
    "uri",
    [
        "atlans://guide/authoring/overview",
        "atlans://catalog/nodes",
        "atlans://catalog/nodes?type=spatial",
        "atlans://catalog/nodes/Buffer",
        "atlans://workspaces/ws-1/workflows",
        f"atlans://workflows/{MY_ID}",
        f"atlans://workflows/{MY_ID}/contract",
        f"atlans://runs/{MY_RUN}",
    ],
)
async def test_each_uri_answers(ambiente, uri):
    conteudo = await _read(uri)
    assert conteudo.strip(), f"{uri} devolveu vazio"


# ── Guide: the resource is an alias of the tool ───────────────────────────────


@pytest.mark.parametrize("topico", guia.TOPICS)
async def test_resource_guide_is_identical_to_the_tools(ambiente, topico):
    escopo = fake_scope(scopes={"workflows:read"})
    do_resource = await _read(f"atlans://guide/authoring/{topico}", escopo)
    da_tool = (await get_authoring_guide(fake_ctx(escopo), topic=topico))["markdown"]
    assert do_resource == da_tool == guia.ler_topico(topico)


async def test_unknown_topic_is_not_delivered(ambiente):
    with pytest.raises(Exception) as exc:
        await _read("atlans://guide/authoring/nao-existe")
    assert "not_found" in str(exc.value)


# ── Catalog ───────────────────────────────────────────────────────────────────


async def test_catalog_without_type_does_not_deliver_the_whole_catalog(ambiente):
    """Without a filter, only the group map — the whole index doesn't fit in one blob."""
    corpo = json.loads(await _read("atlans://catalog/nodes"))
    assert "items" not in corpo
    assert corpo["hint"]
    assert corpo["total"] > 0
    tipos = {t["type"] for t in corpo["types"]}
    assert {"trigger", "spatial", "output"} <= tipos
    assert sum(t["count"] for t in corpo["types"]) == corpo["total"]
    # And the body really is small: the compact index alone exceeds 4 KB.
    assert len(await _read("atlans://catalog/nodes")) < 2000


async def test_catalog_with_type_carries_only_that_group(ambiente):
    corpo = json.loads(await _read("atlans://catalog/nodes?type=trigger"))
    assert corpo["type"] == "trigger"
    assert corpo["items"]
    assert {i["type"] for i in corpo["items"]} == {"trigger"}
    assert corpo["total"] == len(corpo["items"])


async def test_catalog_node_carries_the_full_card(ambiente):
    corpo = json.loads(await _read("atlans://catalog/nodes/Buffer"))
    assert corpo["name"] == "Buffer"
    assert {p["name"] for p in corpo["properties"]} >= {"distance", "distanceUnit"}


async def test_nonexistent_node_is_refused(ambiente):
    with pytest.raises(Exception) as exc:
        await _read("atlans://catalog/nodes/NaoExiste")
    assert "not_found" in str(exc.value)


# ── Workflows ─────────────────────────────────────────────────────────────────


async def test_workspace_listing_carries_the_workflow_with_the_name_quarantined(ambiente):
    corpo = json.loads(await _read("atlans://workspaces/ws-1/workflows"))
    assert corpo["total"] == 1
    item = corpo["items"][0]
    assert item["id"] == MY_ID
    assert item["workspace_id"] == "ws-1"
    # Text written by people never rises to the top of the response.
    assert item["untrusted_data"]["name"] == "Meu fluxo"
    assert "name" not in item


async def test_workflow_comes_out_with_the_definition_redacted(ambiente):
    conteudo = await _read(f"atlans://workflows/{MY_ID}")
    corpo = json.loads(conteudo)
    assert corpo["id"] == MY_ID
    definicao = corpo["untrusted_data"]["definition"]
    propriedades = definicao["nodes"][0]["properties"]
    assert propriedades["connectionString"] == "<REDACTED>"
    assert "senha-secreta" not in conteudo


async def test_contract_carries_the_declared_ports(ambiente):
    corpo = json.loads(await _read(f"atlans://workflows/{MY_ID}/contract"))
    # What the platform derives from the definition stays at the top; the NAME of each
    # port is written by whoever edits the workflow and goes down into `untrusted_data`.
    assert corpo["has_output_node"] is True
    assert [p["name"] for p in corpo["untrusted_data"]["outputs"]] == ["camada"]


# ── Runs ──────────────────────────────────────────────────────────────────────


async def test_run_carries_the_full_picture_of_the_nodes(ambiente):
    """`full`, not `summary`: whoever attaches a run is investigating.

    Each node's outputs (`output_keys`/`output_columns`) are what show where the
    chain stopped producing what the next node expected — and they are precisely
    what the summary omits.
    """
    corpo = json.loads(await _read(f"atlans://runs/{MY_RUN}"))

    assert corpo["run_id"] == MY_RUN
    assert corpo["workflow_id"] == MY_ID
    assert corpo["status"] == "failed"
    assert corpo["error_category"] == "transient"
    nos = corpo["untrusted_data"]["node_stats"]
    assert [no["node_id"] for no in nos] == ["n1"]
    assert nos[0]["output_columns"] == {"gdf": ["id", "geometry"]}


async def test_run_comes_out_with_the_error_redacted_and_off_the_top(ambiente):
    """The error message is the field through which a password leaves a run."""
    conteudo = await _read(f"atlans://runs/{MY_RUN}")
    corpo = json.loads(conteudo)

    assert "error_message" not in corpo
    assert "<REDACTED>" in corpo["untrusted_data"]["error_message"]
    # Not in the run's error, not in the node's error, nowhere in the document.
    assert "SenhaLiteral123" not in conteudo
    assert "<REDACTED>" in corpo["untrusted_data"]["node_stats"][0]["error"]


async def test_run_of_another_workspace_is_not_delivered(ambiente):
    """A valid id of a run that exists — and the response is the nonexistent id's."""
    with pytest.raises(Exception) as alheia:
        await _read(f"atlans://runs/{OTHERS_RUN}")
    with pytest.raises(Exception) as inexistente:
        await _read("atlans://runs/run-que-nunca-existiu")

    assert "not_found" in str(alheia.value)
    assert str(alheia.value) == str(inexistente.value)


# ── Guardas ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "uri",
    [
        "atlans://guide/authoring/overview",
        "atlans://catalog/nodes",
        "atlans://catalog/nodes/Buffer",
        "atlans://workspaces/ws-1/workflows",
        f"atlans://workflows/{MY_ID}",
        f"atlans://workflows/{MY_ID}/contract",
        f"atlans://runs/{MY_RUN}",
    ],
)
async def test_insufficient_scope_is_refused(ambiente, uri):
    """A Drive-only token reads nothing from workflows — not even via resource."""
    without_read = fake_scope(scopes={"drive:read"})
    with pytest.raises(Exception) as exc:
        await _read(uri, without_read)
    mensagem = str(exc.value)
    assert "forbidden_scope" in mensagem
    assert "workflows:read" in mensagem


async def test_workflow_of_another_workspace_is_not_delivered(ambiente):
    """A valid id, an existing workflow — and still nothing comes out, not even the name."""
    for uri in (f"atlans://workflows/{OTHERS_ID}", f"atlans://workflows/{OTHERS_ID}/contract"):
        with pytest.raises(Exception) as exc:
            await _read(uri)
        mensagem = str(exc.value)
        assert "Fluxo alheio" not in mensagem
        assert "forbidden" in mensagem or "not_found" in mensagem


async def test_workspace_out_of_token_reach_is_not_listed(ambiente):
    with pytest.raises(Exception) as exc:
        await _read("atlans://workspaces/ws-2/workflows")
    mensagem = str(exc.value)
    assert "Fluxo alheio" not in mensagem
    assert "forbidden" in mensagem or "not_found" in mensagem


async def test_read_without_any_identity_is_refused(ambiente):
    """Without a resolved PAT there is no scope, and a resource is not an alternative path."""
    token = ESCOPO_ATUAL.set(None)
    try:
        async with Client(create_mcp_server()) as cliente:
            with pytest.raises(Exception) as exc:
                await cliente.read_resource("atlans://catalog/nodes")
    finally:
        ESCOPO_ATUAL.reset(token)
    assert "forbidden" in str(exc.value)


# ── Auditoria ─────────────────────────────────────────────────────────────────


def _audit_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.mcp.auditoria"]


@pytest.mark.parametrize(
    "uri,guarda",
    [
        ("atlans://workspaces/ws-1/workflows", "list_workflows"),
        (f"atlans://workflows/{MY_ID}", "get_workflow"),
        (f"atlans://workflows/{MY_ID}/contract", "get_workflow_contract"),
        (f"atlans://runs/{MY_RUN}", "get_run"),
    ],
)
async def test_reading_workspace_data_leaves_an_audit_line(ambiente, caplog, uri, guarda):
    """The resource is cheap to repeat — and that is why it can't be the traceless path."""
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        await _read(uri)
    linhas = _audit_lines(caplog)
    assert len(linhas) == 1
    assert f"resource={guarda}" in linhas[0]
    assert "desfecho=ok" in linhas[0]
    # The workflow id is a client argument: it doesn't go into the row.
    assert MY_ID not in linhas[0]


async def test_resource_refusal_is_also_audited(ambiente, caplog):
    without_read = fake_scope(scopes={"drive:read"})
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        with pytest.raises(Exception):
            await _read(f"atlans://workflows/{MY_ID}", without_read)
    linhas = _audit_lines(caplog)
    assert linhas and "desfecho=recusa:forbidden_scope" in linhas[0]


async def test_catalog_and_guide_spend_no_audit_line(ambiente, caplog):
    """Fixed installation text, the same for every token: there is nobody's data in it."""
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        await _read("atlans://catalog/nodes")
        await _read("atlans://guide/authoring/overview")
    assert _audit_lines(caplog) == []


async def test_resource_does_not_consume_the_quota_bucket(ambiente, monkeypatch):
    """The exemption is a documented decision: the resource is an alias of a tool that already counts."""
    redis = FakeRedis()
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    await _read(f"atlans://workflows/{MY_ID}")
    assert not [c for c in redis.chamadas if c[0] == "incr"]
