# app/mcp/tools/base.py
"""
The tools' shared base: the error-translation decorator, the timed guard
(scope + quota + audit) and the annotations derived from the table.

The module lives here, and not in `servidor.py`, because the THREE consumers of
the guard — `AtlansServer.call_tool`, the resource handlers and the tools
themselves — already depend on this file and none of them can import
`servidor.py` without a cycle (`servidor` imports `tools` and `resources` to
register them).

── The decorator every tool wears ──

It translates the core's exception into the MCP error. Why inside the tool and
not in the server: the SDK's tool manager wraps any exception that is not a
`ToolError` into a generic error BEFORE the call returns to `call_tool`.
Whoever wants to turn a `WorkflowInactiveError` into a readable `{"code":
"workflow_inactive"}` has to do it INSIDE the tool — afterwards it is too late,
and the client receives "unexpected error".

What goes up intact, and why:
- `ToolError` passes through: whoever raised it (a guard, `resolve_workspace`,
  the tool itself) knew more about the case than the generic table;
- `AtlasBaseError` and `HTTPException` become `to_tool_error(exc)` — they are
  the exceptions Atlans services use to say "404", "403", "422";
- anything else GOES UP. A `KeyError` is a defect of ours, not a refusal: the
  SDK records the failure and the client receives a generic message, with no
  library `str(exc)` — which is precisely where a URL with a password tends to
  show up.

`functools.wraps` is not cosmetic: the SDK builds the tool's `inputSchema` by
introspecting the function, and without it every tool would reach the client as
`(*args, **kwargs)`. It also leaves `__wrapped__` on the wrapper, which is the
thread through which `inspect.signature` and `typing.get_type_hints` reach the
original function — and therefore the module where `Context` and the other
names actually exist (with `from __future__ import annotations` the annotations
are STRINGS, evaluated against the globals of whoever defined them, never of
this file).

The already-resolved annotations are copied over as a second line of defense:
that way the tool's schema — and the recognition of the `ctx` parameter, which
the server injects and the client never fills in — does not depend on that
unwrapping detail continuing to hold.
"""
from __future__ import annotations

import functools
import time
import typing
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

from fastapi import HTTPException
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from app.core.exceptions import AtlasBaseError
from app.core.utils.logger import get_logger
from app.mcp import cotas, infra
from app.mcp.erros import codigo_do_erro, to_tool_error
from app.mcp.escopo import EffectiveScope, exigir_escopo
from app.mcp.guardas import GUARDAS

auditoria = get_logger("app.mcp.auditoria")


def _resolved_annotations(fn: Callable[..., Any]) -> dict:
    """The annotations of `fn` already evaluated (objects, not strings).

    Failing here must not bring down the tool's registration: without the
    resolved annotations the SDK still builds a schema from the original
    signature.
    """
    try:
        return dict(typing.get_type_hints(fn, include_extras=True))
    except Exception:  # pragma: no cover - exotic annotation or circular import
        return dict(getattr(fn, "__annotations__", {}) or {})


def ferramenta(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wraps a tool's coroutine, translating the core's exceptions."""

    @functools.wraps(fn)
    async def _wrapper(*args: Any, **kwargs: Any):
        try:
            return await fn(*args, **kwargs)
        except ToolError:
            raise
        except (AtlasBaseError, HTTPException) as exc:
            raise to_tool_error(exc) from exc

    _wrapper.__annotations__ = _resolved_annotations(fn)
    return _wrapper


@asynccontextmanager
async def call_guard(
    nome: str,
    escopo: EffectiveScope,
    *,
    charge_quota: bool = True,
    origem: str = "tool",
) -> AsyncIterator[None]:
    """Scope → quota → body → audit line, with the real outcome.

    The order matters in two ways. Scope and quota are checked INSIDE the timed
    block so that the refusal also leaves a trace: a call blocked for lack of
    scope or by a quota ceiling is precisely the one most worth recording, and
    while the guards sat before the `try` it went out with no line at all. The
    refusal gets its own outcome (`recusa:<code>`) so it is not confused with a
    tool that ran and failed (`tool_error:<code>`).

    `escopo` arrives ready: the caller has already resolved it with
    `escopo_da_chamada`, and it is on purpose that this resolution stays
    OUTSIDE of here — when it fails there is no identity to name in the audit
    line.

    `charge_quota=False` is the case of resources, which are read aliases of a
    tool and have no bucket of their own: charging twice for the same work
    measures nothing, and the tool's general bucket already holds back the
    loop. Auditing still applies.

    The line never carries the call's arguments — they carry user data (file
    name, workflow id, search text).
    """
    guarda = GUARDAS.get(nome)
    inicio = time.perf_counter()
    desfecho = "ok"
    try:
        try:
            if guarda is not None and guarda.escopo:
                exigir_escopo(escopo, guarda.escopo)
            if charge_quota:
                await cotas.verificar(
                    infra.redis_ou_none(), escopo.token_id, guarda.cota if guarda else None
                )
        except ToolError as exc:
            desfecho = f"recusa:{codigo_do_erro(exc)}"
            raise
        yield
    except ToolError as exc:
        if desfecho == "ok":
            desfecho = f"tool_error:{codigo_do_erro(exc)}"
        raise
    except BaseException:
        if desfecho == "ok":
            desfecho = "erro"
        raise
    finally:
        # Token prefix (never the secret), user, duration and outcome.
        auditoria.info(
            "mcp %s=%s token=%s user=%s ms=%d desfecho=%s",
            origem,
            nome,
            escopo.token_prefix,
            escopo.user_id,
            int((time.perf_counter() - inicio) * 1000),
            desfecho,
        )


def anotacoes(nome: str) -> ToolAnnotations:
    """The tool's `ToolAnnotations`, derived from its row in `GUARDAS`.

    Writing the hints by hand in each domain module is the shortcut to the doc
    and the table silently diverging — the table says `idempotente=False` and
    the published annotation keeps saying `true`. Here there is a single place.

    `destructive_hint` is always False by design decision, not by omission: the
    Atlans MCP deletes nothing. `open_world_hint` comes from the table: False
    for everything except the tools that probe a WFS (see the note in
    `app/mcp/guardas.py`).
    """
    guarda = GUARDAS[nome]
    return ToolAnnotations(
        read_only_hint=guarda.read_only,
        destructive_hint=False,
        idempotent_hint=guarda.idempotente,
        open_world_hint=guarda.open_world,
    )
