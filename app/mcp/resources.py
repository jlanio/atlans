# app/mcp/resources.py
"""
Server resources (`atlans://…`) — cacheable reads, no side effects.

Each resource is an **alias of a read tool**, and alias here is literal: the
handler calls the same function the tool calls, and returns what it returned.
There is no second query, second redaction or second output format to keep in
sync — the only difference is the packaging (text or JSON) and the fact that
the client can attach a resource to the context and reuse it, instead of
spending a call.

Three rules hold for every handler here:

1. **Same guard as the tools.** Scope is checked inside the tool's function,
   which is what calls `escopo_da_chamada` + `exigir_escopo`. A resource is not
   a back door: no scope, no read. What this module adds is the translation of
   the error and, in the handlers that read workspace data, the SAME timed
   guard as `call_tool` (`call_guard`) — without it, reading by URI
   would be the only path in the server that leaves no audit line, and it is
   precisely the path the client repeats without thinking.

   Quota is waived for resources, and that is a decision, not an oversight: a
   resource is an alias of a tool that already has a bucket, and charging again
   for the same work measures nothing. What holds back the loop is the token's
   general bucket.

   Catalog and guide do not go through the guard: they are fixed text of the
   installation, the same for every token, and there is nobody's data to
   record — their scope check still happens inside the tool.

2. **An anticipated error becomes `ResourceError`.** The SDK only preserves the
   message of a `ResourceError` (or `ResourceNotFoundError`); a `ToolError`
   escaping from a resource counts as a crash, and the client would receive a
   generic text with the URI. Since the Atlans error format is the JSON
   `{code, message, hint}`, the translation only swaps the class, keeping the
   body.

3. **Nothing decrypted.** Comes for free from (1): the tools load the workflow
   with `decifrar=False` and redact the definition before handing it over.
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError

from app.mcp import guia
from app.mcp.erros import codigo_do_erro, to_tool_error
from app.mcp.escopo import escopo_da_chamada
from app.mcp.tools.base import call_guard
from app.mcp.tools.catalogo import describe_node, get_authoring_guide, search_nodes
from app.mcp.tools.execucao import get_run
from app.mcp.tools.workflows import get_workflow, get_workflow_contract, list_workflows

# Without `type`, the catalog comes out only as a map of groups. The whole index
# exceeds 10 KB and the full sheet of the 64 nodes, 70 KB: delivering that as a
# single blob in a `resources/read` spends the reader's context budget before
# the conversation begins. The hint says how to get to what matters.
CATALOG_HINT = (
    "Leia atlans://catalog/nodes?type=<tipo> para o índice de um grupo, ou "
    "atlans://catalog/nodes/<Nome> para a ficha completa de um nó."
)


def _json(dados: Any) -> str:
    """JSON readable by humans and machines — without escaping accents."""
    return json.dumps(dados, ensure_ascii=False, default=str)


def _as_resource_error(exc: Exception) -> ResourceError:
    """Translates an exception into the resource error, without losing the `code`.

    `to_tool_error` remains the MCP's only translation table (an
    already-formatted `ToolError` passes through it intact); here only the
    class is swapped, because the SDK handles the two families through
    different paths.

    Only `Exception`, never `BaseException`: a `CancelledError` (the client
    gave up, the server is shutting down) is not a resource error, and
    converting it into `ResourceError` would swallow the cancellation — the
    task would stay alive and the response would go out as if the resource
    had failed.
    """
    convertido = to_tool_error(exc)
    corpo = str(convertido)
    if codigo_do_erro(convertido) == "not_found":
        return ResourceNotFoundError(corpo)
    return ResourceError(corpo)


def registrar_resources(server) -> None:
    """Registers the resources on the given instance.

    A function, and not decorators at module top level, because
    `create_mcp_server` is a factory: each instance needs its own
    registrations.
    """

    @server.resource(
        "atlans://guide/authoring/{topic}",
        name="guia_de_autoria",
        title="Guia de autoria de workflows",
        description=(
            "O guia de autoria, por tópico: "
            + ", ".join(guia.TOPICS)
            + ". Mesmo texto da ferramenta get_authoring_guide."
        ),
        mime_type="text/markdown",
    )
    async def guia_de_autoria(topic: str, ctx: Context) -> str:
        """Alias of `get_authoring_guide`: one file, two delivery paths.

        Returns the plain markdown, not the tool's envelope: the resource
        declares `text/markdown`, so the body is the document.
        """
        try:
            return (await get_authoring_guide(ctx, topic=topic))["markdown"]
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://catalog/nodes{?type}",
        name="catalogo_de_nos",
        title="Catálogo de nós",
        description=(
            "Sem 'type', os grupos de nós e quantos há em cada um. Com 'type', o índice "
            "compacto daquele grupo (nome, tipo, uma linha, se exige credencial)."
        ),
        mime_type="application/json",
    )
    async def catalogo_de_nos(ctx: Context, type: str | None = None) -> str:
        """The catalog in two layers — never all 64 nodes in a single blob.

        The parameter is called `type` because that is the variable's name in
        the URI, and the SDK matches the two by name.
        """
        try:
            resultado = await search_nodes(ctx, type=type)
            if not type:
                # Without a filter, only the map of groups: `items` is built by the
                # tool and discarded here on purpose. Going through it anyway
                # is what guarantees the scope guard runs on BOTH paths.
                return _json({
                    "types": resultado["types"],
                    "total": resultado["total"],
                    "hint": CATALOG_HINT,
                })
            return _json({
                "type": type,
                "total": resultado["total"],
                "items": resultado["items"],
            })
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://catalog/nodes/{name}",
        name="no_do_catalogo",
        title="Nó do catálogo",
        description="A ficha completa de um nó: propriedades, entradas, saídas e dicas.",
        mime_type="application/json",
    )
    async def no_do_catalogo(name: str, ctx: Context) -> str:
        """A whole node — the same as `describe_node(brief=false)`.

        An unknown name becomes 404, and a node disabled in the installation
        answers the same as a nonexistent one: the tool already treats both as
        `not_found`.
        """
        try:
            return _json(await describe_node(ctx, name=name, brief=False))
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://workspaces/{id}/workflows",
        name="workflows_do_workspace",
        title="Workflows de um workspace",
        description="A mesma listagem leve de list_workflows, fixada num workspace.",
        mime_type="application/json",
    )
    async def workflows_do_workspace(id: str, ctx: Context) -> str:
        """Lightweight listing — no definition, no params_schema, no secret."""
        try:
            escopo = escopo_da_chamada(ctx)
            async with call_guard(
                "list_workflows", escopo, charge_quota=False, origem="resource"
            ):
                return _json(await list_workflows(ctx, workspace_id=id))
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://workflows/{id}",
        name="workflow",
        title="Workflow",
        description="Um workflow e a sua definition REDIGIDA (segredo vira <REDACTED>).",
        mime_type="application/json",
    )
    async def workflow(id: str, ctx: Context) -> str:
        """The workflow as a reference: you can read the wiring, never the credential.

        `include_definition=True` because that is what a resource lives on —
        whoever only wants the header calls the tool with the default.
        """
        try:
            escopo = escopo_da_chamada(ctx)
            async with call_guard(
                "get_workflow", escopo, charge_quota=False, origem="resource"
            ):
                return _json(
                    await get_workflow(ctx, workflow_id=id, include_definition=True)
                )
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://workflows/{id}/contract",
        name="contrato_do_workflow",
        title="Contrato de sub-fluxo",
        description="Portas de entrada e saída declaradas para uso como sub-fluxo.",
        mime_type="application/json",
    )
    async def contrato_do_workflow(id: str, ctx: Context) -> str:
        """What the workflow accepts and returns when called by another one."""
        try:
            escopo = escopo_da_chamada(ctx)
            async with call_guard(
                "get_workflow_contract", escopo, charge_quota=False, origem="resource"
            ):
                return _json(await get_workflow_contract(ctx, workflow_id=id))
        except Exception as exc:
            raise _as_resource_error(exc) from exc

    @server.resource(
        "atlans://runs/{id}",
        name="execucao",
        title="Execução",
        description=(
            "O desfecho de uma execução com o retrato COMPLETO de cada nó: status, "
            "duração, erro e saídas. Mesmo conteúdo de get_run(node_stats='full')."
        ),
        mime_type="application/json",
    )
    async def execucao(id: str, ctx: Context) -> str:
        """The whole run — and `full`, not `summary`, on purpose.

        Whoever attaches a run to the context is investigating a failure, and
        it is precisely `output_keys`/`output_columns` that show where the
        chain stopped producing what the next node expected. The tool still
        offers the summary to whoever only wants the status.

        The run's error message and each node's go down sanitized into
        `untrusted_data` (that is what `run_summary` does): they are the fields
        most likely to carry a secret or a command sentence from a run.
        """
        try:
            escopo = escopo_da_chamada(ctx)
            async with call_guard(
                "get_run", escopo, charge_quota=False, origem="resource"
            ):
                return _json(await get_run(ctx, run_id=id, node_stats="full"))
        except Exception as exc:
            raise _as_resource_error(exc) from exc
