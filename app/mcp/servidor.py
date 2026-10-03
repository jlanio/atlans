# app/mcp/servidor.py
"""
The Atlans MCP server: factory, guards at the edge of calls, and the ASGI app.

Two structural decisions live here.

1. `ServidorAtlans` overrides `list_tools` and `call_tool`, which the SDK exposes
   as public methods and calls through `self`. `list_tools` filters the catalog
   by the token's scope — a convenience, so the client does not spend a call
   trying a tool it cannot use. `call_tool` is the real guarantee: no tool runs
   without going through scope and quota, even if the client calls a name it
   never saw in the list.

   The default is to REFUSE. A tool without a row in `GUARDAS` is not callable
   and does not even appear in the catalog: a new tool that its author forgot
   to declare would fail CLOSED (nobody uses it and the defect shows up in the
   log) instead of running without scope, without quota and without role. The
   parity test still exists as a second line of defense — it warns in CI, this
   rule protects in production.

2. `create_mcp_server()` is a FACTORY, not a module singleton. `session_manager`
   is a context that can only be entered once per instance; with a singleton,
   the second test (or a second `lifespan` on a reload) would find the manager
   already consumed. Each process and each test creates its own instance.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

from app.core.utils.logger import get_logger
from app.mcp.auth import AutenticacaoPAT
from app.mcp.erros import erro, sem_prefixo_do_sdk
from app.mcp.escopo import ESCOPO_ATUAL, escopo_da_chamada
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCOES
from app.mcp.prompts import registrar_prompts
from app.mcp.resources import registrar_resources
from app.mcp.tools import registrar_tools
from app.mcp.tools.base import guarda_da_chamada

# Version of the server's CONTRACT (tools, resources, output format), not of
# Atlans. A removed tool stays marked as deprecated for at least one minor
# version before disappearing — see docs/mcp.md.
VERSAO_MCP = "1.5.0"

logger = get_logger("app.mcp.servidor")

# Where the ASGI app is kept on the server instance — see `criar_app_mcp`.
_ATRIBUTO_DO_APP = "_app_do_atlans"

# Names already reported by `list_tools`: the warning is about a programming
# defect (a tool registered without a guard), and repeating it on every
# `tools/list` would flood the log.
_SEM_GUARDA_AVISADAS: set[str] = set()


class ServidorAtlans(MCPServer):
    """`MCPServer` with scope, quota and auditing on every tool call."""

    async def list_tools(self):
        """The catalog filtered by the request token's scope.

        With no scope in the `ContextVar` the list comes out with everything
        that IS callable: that is the case of the in-process client
        (`Client(server)`), which does not go through the middleware. There is
        no loss of security — what decides whether the call happens is
        `call_tool`.

        A tool without a declared guard is ALWAYS left out of the list, with or
        without scope: `call_tool` refuses it, and advertising what cannot be
        called would only make the client spend a call to find that out.
        """
        escopo = ESCOPO_ATUAL.get()
        visiveis = []
        for tool in await super().list_tools():
            guarda = GUARDAS.get(tool.name)
            if guarda is None:
                if tool.name not in _SEM_GUARDA_AVISADAS:
                    _SEM_GUARDA_AVISADAS.add(tool.name)
                    logger.error(
                        "Tool %s registrada sem linha em GUARDAS: escondida do catálogo "
                        "e recusada em call_tool.",
                        tool.name,
                    )
                continue
            if escopo is None or guarda.escopo is None or escopo.tem(guarda.escopo):
                visiveis.append(tool)
        return visiveis

    async def call_tool(self, name, arguments, context=None):
        """Scope → quota → tool → audit.

        The mapping from domain exception to `ToolError` does NOT happen here:
        the SDK's tool manager has already wrapped any exception before the
        call comes back here. It lives in each tool's decorator.
        """
        if name not in GUARDAS:
            # Without a declared guard there is no scope to require, quota to
            # charge or role to check — so there is no call.
            #
            # `not_found` and not `forbidden` (which would promise that the tool
            # exists and permission is missing) nor `internal_error` (which
            # would blame a defect of ours for a simple client typo): from the
            # outside, a tool that does not appear in tools/list and does not
            # run simply does not exist. And it is the SAME code in both cases
            # — a name that never existed and a tool registered without its
            # table row —, so the refusal does not become an oracle of which
            # tools the installation has hidden.
            #
            # Only the beginning of the name goes into the log: it comes from
            # the client, and a giant name repeated in a loop would fill the
            # log for free.
            logger.warning("Chamada recusada: %s não tem guarda declarada.", str(name)[:60])
            raise erro(
                "not_found",
                "Ferramenta indisponível neste servidor.",
                "use tools/list para ver o que este token alcança",
            )

        # Outside the timed block on purpose: when the identity does not
        # resolve there is no token or user to name in the audit line.
        escopo = escopo_da_chamada(context)

        async with guarda_da_chamada(name, escopo):
            try:
                return await super().call_tool(name, arguments, context)
            except ToolError as exc:
                # The SDK prefixes the text with "Error executing tool <nome>: " when
                # re-raising the error from inside the tool. Without stripping
                # the prefix, the client would receive two formats: plain JSON
                # when the guard refuses, and JSON preceded by prose when the
                # tool fails.
                limpa = sem_prefixo_do_sdk(str(exc))
                if limpa != str(exc):
                    raise ToolError(limpa) from exc.__cause__
                raise


def hosts_permitidos() -> list[str]:
    """The `Host` values accepted by the transport (defense against DNS rebinding).

    Read on every call, not at import, so that an environment change (or a
    test) takes effect without reloading the module.
    """
    from app.core import config

    return list(config.MCP_ALLOWED_HOSTS)


def create_mcp_server() -> ServidorAtlans:
    """A new server instance, with tools, resources and prompts registered."""
    server = ServidorAtlans(
        name="atlans",
        title="Atlans",
        instructions=INSTRUCOES,
        version=VERSAO_MCP,
    )
    registrar_tools(server)
    registrar_resources(server)
    registrar_prompts(server)
    return server


def criar_app_mcp(server: ServidorAtlans):
    """The `/mcp` ASGI app: streamable HTTP transport behind the PAT middleware.

    - `streamable_http_path="/mcp"` matches the exact route mounted in
      `app.main`, with no redirect on the canonical URL;
    - `stateless_http=True` so that several uvicorn workers can serve the same
      client without session affinity;
    - `json_response=False` is mandatory: a run's progress only reaches the
      client through the request's own SSE;
    - `allowed_origins=[]` refuses any `Origin`. Non-browser MCP clients do not
      send that header; a browser only comes in at the OAuth phase.

    An instance has ONE app. `streamable_http_app()` swaps the server's
    `session_manager` on every call, and the `lifespan` of `app.main` enters
    the manager that existed when it started: a second call would leave the
    app served with a manager nobody started — every request would answer with
    a session error. That is why the created app is kept on the instance itself
    and returned again, instead of a second one being built silently.
    """
    existente = getattr(server, _ATRIBUTO_DO_APP, None)
    if existente is not None:
        return existente
    app = AutenticacaoPAT(
        server.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=False,
            transport_security=TransportSecuritySettings(
                allowed_hosts=hosts_permitidos(),
                allowed_origins=[],
            ),
        )
    )
    setattr(server, _ATRIBUTO_DO_APP, app)
    return app
