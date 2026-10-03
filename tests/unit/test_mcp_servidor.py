# tests/unit/test_mcp_servidor.py
"""
The whole `/mcp` server: factory, catalog filter, scope guard and edge.

This file exercises the real stack — PAT middleware + streamable HTTP transport
+ `AtlansServer` — because the composition is what goes wrong: a filter that
works on the object and doesn't work over HTTP protects nobody.

The points pinned down here:

- `create_mcp_server()` is a factory. `session_manager.run()` can only be
  entered ONCE per instance; a module singleton would make the second test (or a
  reload in production) find the manager already consumed;
- `initialize` answers on both paths clients use: the legacy one, which pins
  `protocolVersion` and speaks raw JSON-RPC, and the SDK's modern one;
- `tools/list` hides what the token can't reach — on both paths, because the
  scope reaches `list_tools` through a `ContextVar` and it has to be proven that
  it survives the task the transport creates;
- hiding is a convenience; the guarantee is `call_tool`, which refuses naming
  the missing scope even when the client calls a name it never saw in the list;
- the default is to REFUSE: a tool with no row in `GUARDAS` doesn't appear in
  the catalog and doesn't run. It is the case that would fail OPEN if the
  default were to delegate to the SDK — a new tool would run without scope,
  without quota and without role;
- every call leaves ONE audit row, including the one refused by the guard, and
  none of them carries the arguments;
- a `Host` outside the list is 421 and a present `Origin` is 403 — but without
  a PAT the 401 comes FIRST, because the middleware is outside the transport.

Since the domain tools don't exist yet, the tests register their own tools on
the test instance, with the names the guard table knows.
"""
from __future__ import annotations

import json

import httpx
import pytest
from mcp.server.mcpserver import Context

from app.mcp import cotas, infra
from app.mcp.escopo import ESCOPO_ATUAL
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCTIONS
from app.mcp.servidor import (
    MCP_VERSION,
    AtlansServer,
    create_mcp_server,
    criar_app_mcp,
    hosts_permitidos,
)
from tests.unit._mcp_harness import (
    FakeRedis,
    in_memory_db,
    mcp_client,
    create_pat,
    create_user,
    create_workspace,
    fake_ctx,
    fake_scope,
    session_from,
)

_JSON = {
    "Content-Type": "application/json",
    # Without both types in Accept the transport answers 406 before looking at the rest.
    "Accept": "application/json, text/event-stream",
}

_INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "cliente-de-teste", "version": "0"},
    },
}


def test_server():
    """A server without the real tools, with two fake ones — one per scope in the table.

    What is exercised here is the COMPOSITION (catalog filter, scope guard,
    quota, audit), not the body of any tool. That is why the instance is built
    by hand instead of coming from `create_mcp_server()`: with the real tools
    registered, a second registration with the same name would be ignored by the
    SDK and the tests would be measuring the production tool by accident. The
    names are still two from the guard table, which is what gives meaning to
    the scope filter.
    """
    server = AtlansServer(
        name="atlans",
        title="Atlans",
        instructions=INSTRUCTIONS,
        version=MCP_VERSION,
    )

    @server.tool(name="list_workspaces", description="Lista workspaces (tool de teste).")
    async def _workspaces() -> dict:
        return {"items": []}

    @server.tool(name="list_drive_files", description="Lista arquivos do Drive (tool de teste).")
    async def _drive() -> dict:
        return {"items": []}

    return server


def _jsonrpc_response(r: httpx.Response) -> dict:
    """The JSON-RPC body, whether it comes as JSON or inside an SSE event."""
    if r.headers.get("content-type", "").startswith("application/json"):
        return r.json()
    for linha in r.text.splitlines():
        if linha.startswith("data: "):
            return json.loads(linha[len("data: ") :])
    raise AssertionError(f"sem payload JSON-RPC em: {r.text!r}")


@pytest.fixture
async def ambiente(monkeypatch):
    """In-memory database with one user and one workspace; MCP infra redirected."""
    async with in_memory_db() as fabrica:
        async with fabrica() as db:
            await create_user(db, "usr-1", "ana")
            await create_workspace(db, "ws-1", "usr-1", "Principal")
        redis = FakeRedis()
        monkeypatch.setattr(infra, "sessao", session_from(fabrica))
        monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
        yield fabrica


async def _pat(fabrica, escopos) -> str:
    async with fabrica() as db:
        return await create_pat(db, "usr-1", escopos, None)


# ── Factory ───────────────────────────────────────────────────────────────────


def test_the_factory_returns_independent_instances():
    a, b = create_mcp_server(), create_mcp_server()
    assert a is not b
    # Each instance has its own session manager — that is what allows one
    # server per test without "cannot be used twice".
    criar_app_mcp(a)
    criar_app_mcp(b)
    assert a.session_manager is not b.session_manager


def test_creating_mcp_app_twice_returns_the_same_app():
    """Two calls would swap the `session_manager` silently.

    `streamable_http_app()` creates a new manager on every call, and what
    enters the manager is `app.main`'s `lifespan`, only once: a second app
    would leave the served one with a manager nobody started.
    """
    server = create_mcp_server()
    primeiro = criar_app_mcp(server)
    gerenciador = server.session_manager
    assert criar_app_mcp(server) is primeiro
    assert server.session_manager is gerenciador


def test_the_factory_carries_identity_and_instructions():
    """The version is pinned on purpose: changing it has to be deliberate.

    It is the only discriminator a client has to know WHICH contract is live —
    it is what was missing when checking the previous delivery, when the stuck
    `1.0.0` made it impossible to tell, via `initialize`, the new server from
    the old one. A new tool bumps the minor; a removed tool stays one minor
    version marked as deprecated before disappearing.
    """
    server = create_mcp_server()
    assert server.name == "atlans"
    assert server.instructions == INSTRUCTIONS
    assert MCP_VERSION == "1.5.0"


def test_allowed_hosts_come_from_the_configuration(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config, "MCP_ALLOWED_HOSTS", ["atlans.example.org", "localhost:*"])
    assert hosts_permitidos() == ["atlans.example.org", "localhost:*"]


def test_default_hosts_cover_the_site_and_development():
    """Without MCP_ALLOWED_HOSTS, the FRONTEND_URL host and local dev apply."""
    from app.core import config

    assert config.default_mcp_hosts("https://atlans.example.org")[:2] == [
        "atlans.example.org", "atlans.example.org:*",
    ]
    assert "localhost:*" in config.MCP_ALLOWED_HOSTS


# ── Paridade tools × guardas ──────────────────────────────────────────────────


async def test_every_registered_tool_has_a_guard():
    """No registered tool is left without a row in the guard table.

    A second line of defense, on purpose: in production a tool without a guard
    is already hidden and refused, but that makes it silently USELESS. This
    test is what warns in CI — and that is why it reads the SDK's RAW catalog
    (`MCPServer.list_tools`), without the `AtlansServer` filter, otherwise the
    forgotten tool would vanish from the list and the test would pass without
    seeing anything.
    """
    from mcp.server.mcpserver import MCPServer

    server = create_mcp_server()
    nomes = {t.name for t in await MCPServer.list_tools(server)}
    assert nomes, "o catálogo não pode estar vazio"
    assert nomes <= set(GUARDAS)


async def test_the_raw_and_filtered_catalogs_match_on_the_real_server():
    """With the table up to date, hiding takes nothing away from whoever has full scope."""
    from mcp.server.mcpserver import MCPServer

    server = create_mcp_server()
    crus = {t.name for t in await MCPServer.list_tools(server)}
    # Full scope = the union of what the table requires; that way the list doesn't
    # go stale when a new tool brings a scope nobody used.
    ficha = ESCOPO_ATUAL.set(
        fake_scope(scopes={g.escopo for g in GUARDAS.values()})
    )
    try:
        filtered = {t.name for t in await server.list_tools()}
    finally:
        ESCOPO_ATUAL.reset(ficha)
    assert filtered == crus


# The read tools, separated from the rest because they are the ones the
# promises of "changes nothing and spends no extra bucket" apply to.
READ_TOOLS = {
    "list_workspaces",
    "list_workflows",
    "get_workflow",
    "get_workflow_contract",
    "search_nodes",
    "describe_node",
    "list_credentials",
    "list_drive_files",
    "get_drive_download_url",
    "get_portal_info",
    "get_authoring_guide",
    "get_run",
    "list_runs",
    "get_run_artifacts",
    # Phase 2: reading a run's log is a read like the rest of
    # observability — it neither interrupts nor dispatches anything.
    "get_run_events",
    # Phase 2, collection: the history and what the runs produced. Reading an
    # old version changes nothing; `list_artifacts` signs a URL, which makes it
    # non-idempotent, but it is still a read.
    "list_workflow_versions",
    "get_workflow_version",
    "list_artifacts",
    # Phase 2, pins: knowing WHICH outputs are frozen is a read — and it is the
    # only way to find out that a result came from cache.
    "list_pins",
    # Phase 2, triggers: seeing WHEN a workflow fires on its own is a read, and
    # requires `workflows:read` and not `triggers:manage` — for the same reason
    # as `get_run`: whoever only follows along doesn't need the power to change things.
    "list_schedules",
    # Sources: search and describe are table reads, with no network.
    "search_sources",
    "describe_source",
}


def test_the_guard_table_has_exactly_the_registered_tools():
    """The list is written by hand on purpose.

    Deriving it from `GUARDAS` would make the test tautological: it would start
    asserting that the table equals itself, and a new tool would get in without
    anyone deciding whether it reads or writes. Keeping both lists and
    comparing them is what forces that decision to be made by a person.
    """
    assert set(GUARDAS) == READ_TOOLS | {
        "validate_workflow",
        "create_workflow",
        "update_workflow",
        "set_workflow_active",
        "set_portal_access",
        "run_workflow",
        # Phase 2 — they touch what is running.
        "cancel_run",
        "retry_run",
        # Phase 2 — collection: the two that write.
        "restore_workflow_version",
        "duplicate_workflow",
        # Phase 2 — pins: both change the workflow's column.
        "pin_node_output",
        "unpin_node_output",
        # Phase 2 — triggers: all three change when the workflow fires on its own.
        "create_schedule",
        "update_schedule",
        "delete_schedule",
        # Phase 2 — Drive writes: all three touch the workspace's collection.
        "create_drive_upload_url",
        "confirm_drive_upload",
        "delete_drive_file",
        # Sources: `probe_source` talks to the internet, updates the state of an
        # already cataloged source and spends bucket — it is not a read, just as
        # `validate_workflow` isn't; `register_source` probes AND saves.
        "probe_source",
        "register_source",
    }


def test_every_read_guard_is_read_only_and_spends_no_quota():
    for nome in READ_TOOLS:
        guarda = GUARDAS[nome]
        assert guarda.read_only is True, nome
        assert guarda.cota is None, nome
    # The presigned URL is the only one that changes on every call (new signature) —
    # both the Drive one and those of a run's artifacts.
    assert GUARDAS["get_drive_download_url"].idempotente is False
    assert GUARDAS["get_run_artifacts"].idempotente is False


def test_reading_run_does_not_require_trigger_scope():
    """Following a run is a read; dispatching is something else.

    Parity with REST, where `/observability` only requires being a member of
    the workspace. If `get_run` started requiring `runs:execute`, whoever only
    wanted to follow along would need a token capable of DISPATCHING — a scope
    larger than the task, which is the opposite of what this table exists to
    guarantee.
    """
    for nome in ("get_run", "list_runs", "get_run_artifacts"):
        assert GUARDAS[nome].escopo == "workflows:read", nome
        assert GUARDAS[nome].papel == "viewer", nome
    assert GUARDAS["run_workflow"].escopo == "runs:execute"
    assert GUARDAS["run_workflow"].papel == "operator"


def test_every_write_guard_is_not_read_only():
    """Writing can never announce `readOnlyHint` — the client trusts it.

    The annotation is what makes a client decide whether to ask for confirmation
    before calling. A tool that writes while announcing itself as a read runs
    without anyone asking anything.
    """
    for nome, guarda in GUARDAS.items():
        if nome in READ_TOOLS:
            continue
        assert guarda.read_only is False, nome
        assert guarda.escopo in (
            "workflows:write", "runs:execute", "triggers:manage", "drive:write",
        ), nome
        assert guarda.papel in ("editor", "operator"), nome


# The two extra buckets, written by hand for the same reason as the read list:
# deriving them from the table would make the test agree with whatever value
# was there. `run` is for whoever reserves an executor; `validate` is for whoever
# runs the definition's simulation — which `create` and `update` do before saving.
DISPATCHING_TOOLS = {"run_workflow", "retry_run"}
SIMULATING_TOOLS = {"validate_workflow", "create_workflow", "update_workflow"}
# The ones that PROBE a third-party WFS (GetCapabilities/DescribeFeatureType):
# outbound I/O, with its own bucket, tighter than the validation one.
PROBING_TOOLS = {"probe_source", "register_source"}


def test_each_quota_bucket_covers_exactly_who_spends_the_resource():
    """Without this, `retry_run` could lose its quota and keep passing.

    The `run` quota is what keeps a looping agent from filling the run queue —
    and `retry_run` dispatches one run per call, like `run_workflow`. The other
    guard tests check `read_only`, `escopo` and `papel`, and none looked at
    `cota`: deleting `"run"` from `retry_run`'s row passed entirely.
    """
    for nome, guarda in GUARDAS.items():
        if nome in DISPATCHING_TOOLS:
            esperado = "run"
        elif nome in SIMULATING_TOOLS:
            esperado = "validate"
        elif nome in PROBING_TOOLS:
            esperado = "probe"
        else:
            esperado = None
        assert guarda.cota == esperado, f"{nome}: cota {guarda.cota!r}, esperado {esperado!r}"


def test_each_tool_idempotency_hint_is_a_recorded_decision():
    """`idempotentHint` is published to the client, and it acts on it.

    A tool announced as idempotent authorizes the agent to repeat the call
    after a network error. In `retry_run` each repetition is a NEW run, with an
    executor reserved — that is why it is the only one of the three execution
    tools marked as non-idempotent, and why the value needs to be pinned here:
    no other guard test looked at this field.
    """
    non_idempotent = {
        # Assinam URL nova a cada chamada.
        "get_drive_download_url", "get_run_artifacts",
        "list_artifacts",
        # They save or dispatch something different on every call.
        "create_workflow", "update_workflow", "run_workflow", "retry_run",
        # Restoring saves a new auto-snapshot on every call; duplicating creates
        # a new workflow with a new id.
        "restore_workflow_version", "duplicate_workflow",
        # Each call creates a new `job_id`: repeating after a network error
        # would leave TWO schedules firing the same workflow.
        "create_schedule",
        # Each call creates a pending row and signs a new URL.
        "create_drive_upload_url",
    }
    # The pins are NOT included: `pin_node_output` rewrites the same entry and
    # `unpin_node_output` removing it twice changes nothing. They are the only
    # write tools in the server that can be safely repeated, and making that
    # explicit here is what keeps someone from "fixing" their row in `GUARDAS`
    # by analogy with the other writes.
    assert not ({"pin_node_output", "unpin_node_output"} & non_idempotent)
    for nome, guarda in GUARDAS.items():
        esperado = nome not in non_idempotent
        assert guarda.idempotente is esperado, (
            f"{nome}: idempotente={guarda.idempotente}, esperado {esperado}"
        )


# ── list_tools filtrado ───────────────────────────────────────────────────────


async def test_without_scope_in_context_the_list_comes_out_whole():
    """This is the in-process client's case, which doesn't go through the middleware."""
    server = test_server()
    assert ESCOPO_ATUAL.get() is None
    assert {t.name for t in await server.list_tools()} == {"list_workspaces", "list_drive_files"}


async def test_filtered_list_on_the_modern_path(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {"list_workspaces"}


async def test_filtered_list_on_the_legacy_path(ambiente):
    segredo = await _pat(ambiente, ["drive:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    cabecalhos = {**_JSON, "Authorization": f"Bearer {segredo}"}
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post("/mcp", json=_INITIALIZE, headers=cabecalhos)
            assert r.status_code == 200, r.text
            corpo = _jsonrpc_response(r)
            assert corpo["result"]["serverInfo"]["name"] == "atlans"

            r = await c.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                headers=cabecalhos,
            )
            assert r.status_code == 200, r.text
            nomes = {t["name"] for t in _jsonrpc_response(r)["result"]["tools"]}
    assert nomes == {"list_drive_files"}


async def test_token_with_both_scopes_sees_both_tools(ambiente):
    segredo = await _pat(ambiente, ["workflows:read", "drive:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            nomes = {t.name for t in (await cliente.list_tools()).tools}
    assert nomes == {"list_workspaces", "list_drive_files"}


# ── call_tool ─────────────────────────────────────────────────────────────────


async def test_tool_with_the_right_scope_runs(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is False


async def test_calling_hidden_tool_is_refused_naming_the_missing_scope(ambiente):
    """Filtering the list is a convenience; the guarantee is this refusal."""
    segredo = await _pat(ambiente, ["drive:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    corpo = json.loads(resultado.content[0].text)
    assert corpo["code"] == "forbidden_scope"
    assert corpo["missing_scope"] == "workflows:read"


async def test_call_without_any_identity_is_forbidden():
    """In-process client: no middleware, no scope — the tool doesn't run."""
    server = test_server()
    from mcp import Client

    async with Client(server) as cliente:
        resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "forbidden"


async def test_exceeded_quota_refuses_the_call_before_running_the_tool(ambiente, monkeypatch):
    segredo = await _pat(ambiente, ["workflows:read"])
    redis = FakeRedis()
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    # This token's general bucket is already at the ceiling.
    redis.dados[f"ratelimit:mcp:{await _token_id(ambiente)}:geral"] = cotas.OVERALL_LIMIT

    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "rate_limited"


async def _token_id(fabrica) -> str:
    from sqlalchemy import select

    from app.models.api_token import ApiToken

    async with fabrica() as db:
        return (await db.execute(select(ApiToken.id_hash))).scalars().first()


# ── Tool without a guard: the default is to refuse ────────────────────────────


def _server_with_unguarded_tool(nome: str = "tool_sem_guarda"):
    """A server with a single tool that has NO row in the guard table.

    It is the oversight we want to cover: someone registers the tool and doesn't
    declare the guard. Before, the server delegated to the SDK and the tool ran
    without scope, without quota and without role — exactly the opposite of
    what the table exists to do.
    """
    server = AtlansServer(
        name="atlans", title="Atlans", instructions=INSTRUCTIONS, version=MCP_VERSION,
    )
    rastro = {"rodou": False}

    @server.tool(name=nome, description="Tool sem linha em GUARDAS (teste).")
    async def _sem_guarda() -> dict:
        rastro["rodou"] = True
        return {"segredo_da_casa": "nunca deveria sair"}

    return server, rastro


async def test_tool_without_guard_does_not_appear_in_the_catalog():
    server, _ = _server_with_unguarded_tool()
    assert await server.list_tools() == []


async def test_tool_without_guard_is_refused_without_running_the_body():
    """The inverted default: with no declared guard, the call doesn't happen."""
    from mcp import Client

    server, rastro = _server_with_unguarded_tool()
    ficha = ESCOPO_ATUAL.set(fake_scope(scopes={"workflows:read", "drive:read"}))
    try:
        async with Client(server) as cliente:
            resultado = await cliente.call_tool("tool_sem_guarda", {})
    finally:
        ESCOPO_ATUAL.reset(ficha)

    assert resultado.is_error is True
    assert rastro["rodou"] is False
    corpo = json.loads(resultado.content[0].text)
    assert corpo["code"] == "not_found"
    # The refusal doesn't tell the client whether the name exists and was left
    # without a guard or never existed — and carries nothing from inside the tool.
    assert "GUARDAS" not in json.dumps(corpo)
    assert "segredo_da_casa" not in json.dumps(corpo)


async def test_name_that_never_existed_gets_the_same_refusal():
    from mcp import Client

    server = test_server()
    ficha = ESCOPO_ATUAL.set(fake_scope(scopes={"workflows:read"}))
    try:
        async with Client(server) as cliente:
            resultado = await cliente.call_tool("delete_tudo", {})
    finally:
        ESCOPO_ATUAL.reset(ficha)
    assert resultado.is_error is True
    assert json.loads(resultado.content[0].text)["code"] == "not_found"


# ── Auditoria ─────────────────────────────────────────────────────────────────


def _audit_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.mcp.auditoria"]


async def _call_in_process(server, nome: str, argumentos: dict, escopo):
    """Calls a tool through the in-process client, with the scope in the `ContextVar`."""
    from mcp import Client

    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        async with Client(server) as cliente:
            return await cliente.call_tool(nome, argumentos)
    finally:
        ESCOPO_ATUAL.reset(ficha)


async def test_successful_call_leaves_an_audit_line(caplog):
    server = test_server()
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _call_in_process(
            server, "list_workspaces", {}, fake_scope(scopes={"workflows:read"})
        )
    assert resultado.is_error is False
    linhas = _audit_lines(caplog)
    assert len(linhas) == 1
    assert "tool=list_workspaces" in linhas[0]
    assert "desfecho=ok" in linhas[0]
    # O prefixo identifica o token; o segredo nunca aparece.
    assert "token=atl_pat_Ab3d" in linhas[0]


async def test_missing_scope_refusal_is_also_audited(caplog):
    """The blocked call is precisely the one most worth recording."""
    server = test_server()
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _call_in_process(
            server, "list_workspaces", {}, fake_scope(scopes={"drive:read"})
        )
    assert resultado.is_error is True
    linhas = _audit_lines(caplog)
    assert len(linhas) == 1
    assert "desfecho=recusa:forbidden_scope" in linhas[0]


async def test_quota_refusal_is_also_audited(caplog, monkeypatch):
    server = test_server()
    redis = FakeRedis()
    redis.dados["ratelimit:mcp:tok-1:geral"] = cotas.OVERALL_LIMIT
    monkeypatch.setattr(infra, "redis_ou_none", lambda: redis)
    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _call_in_process(
            server, "list_workspaces", {}, fake_scope(scopes={"workflows:read"})
        )
    assert resultado.is_error is True
    assert "desfecho=recusa:rate_limited" in _audit_lines(caplog)[0]


async def test_the_audit_never_logs_the_call_arguments(caplog):
    """Without this test, a mutant that added `arguments=%s` would pass.

    The argument is user data: a file name, search text, a workflow id. The
    audit row says WHO called WHAT and how it ended — never with what.
    """
    sentinel = "SENTINELA-9f3c-nome-do-no"
    server = AtlansServer(
        name="atlans", title="Atlans", instructions=INSTRUCTIONS, version=MCP_VERSION,
    )

    @server.tool(name="describe_node", description="Devolve o nome recebido (teste).")
    async def _descrever(name: str) -> dict:
        return {"name": name}

    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _call_in_process(
            server, "describe_node", {"name": sentinel}, fake_scope(scopes={"workflows:read"})
        )

    assert resultado.is_error is False
    linhas = _audit_lines(caplog)
    assert len(linhas) == 1
    assert "tool=describe_node" in linhas[0]
    assert sentinel not in linhas[0]


async def test_failing_tool_logs_the_error_code(caplog):
    """A tool failure and a guard refusal have different outcomes on purpose."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.erros import erro as build_error

    server = AtlansServer(
        name="atlans", title="Atlans", instructions=INSTRUCTIONS, version=MCP_VERSION,
    )

    @server.tool(name="get_workflow", description="Sempre falha (teste).")
    async def _falha() -> dict:
        raise build_error("not_found", "Não achei o fluxo.")

    with caplog.at_level("INFO", logger="app.mcp.auditoria"):
        resultado = await _call_in_process(
            server, "get_workflow", {}, fake_scope(scopes={"workflows:read"})
        )

    assert resultado.is_error is True
    assert isinstance(ToolError("x"), Exception)
    assert "desfecho=tool_error:not_found" in _audit_lines(caplog)[0]
    # The prefix the SDK puts in front of the JSON is removed before going out.
    assert json.loads(resultado.content[0].text)["code"] == "not_found"


# ── Borda: Host, Origin e a ordem das recusas ─────────────────────────────────


async def test_host_outside_the_list_is_421_even_with_valid_pat(ambiente):
    segredo = await _pat(ambiente, ["workflows:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post(
                "/mcp",
                json=_INITIALIZE,
                headers={**_JSON, "Host": "evil.example", "Authorization": f"Bearer {segredo}"},
            )
    assert r.status_code == 421


async def test_present_origin_is_403_even_with_valid_pat(ambiente):
    """Browser clients only in the OAuth phase — any `Origin` is refused."""
    segredo = await _pat(ambiente, ["workflows:read"])
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post(
                "/mcp",
                json=_INITIALIZE,
                headers={**_JSON, "Origin": "https://x.example", "Authorization": f"Bearer {segredo}"},
            )
    assert r.status_code == 403


async def test_without_pat_the_401_comes_before_the_421(ambiente):
    """The middleware is outside the transport: whoever doesn't identify never even gets there."""
    server = test_server()
    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_mcp), base_url="http://localhost:8000"
        ) as c:
            r = await c.post("/mcp", json=_INITIALIZE, headers={**_JSON, "Host": "evil.example"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Bearer")


# ── EffectiveScope ─────────────────────────────────────────────────────────────


def test_as_user_never_carries_admin_role():
    """The observability services decide what to show by looking at `user.role`.

    Handing them the database `User` would give a PAT an administrator's
    global reach — the substitute is always `role="user"`.
    """
    escopo = fake_scope(user_id="usr-admin", username="raiz")
    usuario = escopo.as_user()
    assert usuario.role == "user"
    assert usuario.id_hash == "usr-admin"
    assert usuario.username == "raiz"
    assert not hasattr(usuario, "status")


def test_single_workspace_only_exists_when_there_is_exactly_one():
    assert fake_scope(workspace_ids={"ws-1"}).single_workspace() == "ws-1"
    assert fake_scope(workspace_ids={"ws-1", "ws-2"}).single_workspace() is None
    assert fake_scope(workspace_ids=set()).single_workspace() is None


def test_call_scope_prefers_the_request_state():
    """With concurrent calls, `request.state` is the channel that doesn't get mixed up."""
    from app.mcp.escopo import escopo_da_chamada

    da_request = fake_scope(token_id="tok-request")
    ficha = ESCOPO_ATUAL.set(fake_scope(token_id="tok-contextvar"))
    try:
        assert escopo_da_chamada(fake_ctx(da_request)).token_id == "tok-request"
    finally:
        ESCOPO_ATUAL.reset(ficha)


def test_call_scope_falls_back_to_the_contextvar():
    from app.mcp.escopo import escopo_da_chamada

    ficha = ESCOPO_ATUAL.set(fake_scope(token_id="tok-contextvar"))
    try:
        assert escopo_da_chamada(fake_ctx(None)).token_id == "tok-contextvar"
    finally:
        ESCOPO_ATUAL.reset(ficha)


def test_call_scope_without_identity_raises_forbidden():
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import escopo_da_chamada

    with pytest.raises(ToolError) as exc:
        escopo_da_chamada(fake_ctx(None))
    assert json.loads(str(exc.value))["code"] == "forbidden"


def test_require_scope_lists_all_missing_ones():
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo

    escopo = fake_scope(scopes={"workflows:read"})
    exigir_escopo(escopo, "workflows:read")  # doesn't raise
    with pytest.raises(ToolError) as exc:
        exigir_escopo(escopo, "workflows:write", "runs:execute")
    corpo = json.loads(str(exc.value))
    assert corpo["code"] == "forbidden_scope"
    assert corpo["missing_scope"] == ["workflows:write", "runs:execute"]


def test_the_scope_hint_says_who_can_reach_the_tokens_page():
    """The tokens page only opens for the system administrator
    (`web/proxy.ts`), and the token is personal: the hint can't tell the user to
    ask the admin for a token (it would be HIS token, acting on his behalf)."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo

    with pytest.raises(ToolError) as exc:
        exigir_escopo(fake_scope(scopes=set()), "drive:write")
    hint = json.loads(str(exc.value))["hint"]
    assert "/settings/tokens" in hint
    assert "administradores" in hint
    assert "peça" not in hint


async def test_the_scope_reaches_the_tool_via_the_request_state(ambiente):
    """Proves the primary channel end to end, without the `ContextVar` fallback.

    The tool reads `ctx.request_context.request.state.escopo` directly: it is
    what `escopo_da_chamada` checks first, and the only channel that doesn't
    get mixed up between concurrent calls.
    """
    segredo = await _pat(ambiente, ["workflows:read"])
    # Instance without the real tools: the body here only returns the identity
    # that arrived through the request state (see `test_server`).
    server = AtlansServer(
        name="atlans", title="Atlans", instructions=INSTRUCTIONS, version=MCP_VERSION,
    )

    @server.tool(name="list_workspaces", description="Devolve a identidade da chamada (teste).")
    async def _quem_sou(ctx: Context) -> dict:
        # The `Context` annotation is what makes the SDK inject the context instead
        # of requiring an argument from the client.
        from starlette.requests import Request

        requisicao = ctx.request_context.request
        assert isinstance(requisicao, Request)
        escopo = requisicao.state.escopo
        return {"user_id": escopo.user_id, "token_prefix": escopo.token_prefix}

    app_mcp = criar_app_mcp(server)
    async with server.session_manager.run():
        async with mcp_client(app_mcp, segredo) as cliente:
            resultado = await cliente.call_tool("list_workspaces", {})
    assert resultado.is_error is False, resultado.content
    assert json.loads(resultado.content[0].text)["user_id"] == "usr-1"
