# app/mcp/escopo.py
"""
`EscopoEfetivo` — who owns the call and how far it reaches.

The PAT middleware resolves the token ONCE per request and distills the result
into this immutable object: user, token, granted scopes and the workspaces it
actually reaches (already intersected with the user's workspaces). From then on
no tool goes back to the database to ask "can this token?" — the answer travels
along.

Two channels, because there are two consumers:
- `request.state.escopo`, read by the tools from `ctx` (it is the normal path,
  and the only one that works with several concurrent requests);
- `ESCOPO_ATUAL`, a `ContextVar`, because `list_tools()` receives no `ctx` at
  all and still needs to filter the catalog by the token's scope.

`como_usuario()` exists for a security reason: the observability services
decide what to show based on a `user` object, and some still look at
`user.role`. Handing them the raw `User` from the database would give MCP an
administrator's global reach. The substitute carries only what they read and
is always `role="user"`.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from types import SimpleNamespace

from app.core.authorization import pat
from app.mcp.erros import erro


@dataclass(frozen=True)
class EscopoEfetivo:
    """The reach of a call — frozen at authentication time."""

    user_id: str
    username: str | None
    token_id: str
    token_prefix: str
    scopes: frozenset[str]
    # Already the intersection "user's workspaces ∩ token's reach".
    workspace_ids: frozenset[str]
    # True when the token was issued with `workspace_ids = NULL` ("all,
    # including future ones"). Does not widen anything by itself: `workspace_ids`
    # remains the real list; it serves to explain the reach and for documentation.
    todos_os_workspaces: bool

    # Provenance that the workflows created by this principal receive
    # (`Workflow.origem`). "usuario" for PATs and for the editor assistant;
    # "assistente" only for the Home assistant's scope. It is an origin stamp,
    # NOT a privilege: it widens no reach, it only marks who created the workflow
    # so the listings can hide it. Default at the end of the class: the
    # existing constructors (PAT, assistant, `escopo_falso`) remain intact.
    origem_dos_fluxos: str = "usuario"

    def tem(self, escopo: str) -> bool:
        """True if the token carries this scope."""
        return escopo in self.scopes

    def como_usuario(self) -> SimpleNamespace:
        """The minimum the services ask for as `user` — NEVER the database `User`.

        Always `role="user"`: a PAT does not confer administrator privilege,
        even if the owner is one.
        """
        return SimpleNamespace(id_hash=self.user_id, username=self.username, role="user")

    def workspace_unico(self) -> str | None:
        """The workspace when there is exactly one — which makes `workspace_id` optional."""
        if len(self.workspace_ids) == 1:
            return next(iter(self.workspace_ids))
        return None


# Filled in by the middleware and reset at the end of the request. `list_tools()`
# is the consumer that has no other channel; the handler runs in a task created
# inside the request, and `create_task` copies the context, so the value gets there.
ESCOPO_ATUAL: ContextVar[EscopoEfetivo | None] = ContextVar("ESCOPO_ATUAL", default=None)


# ── Assistant ───────────────────────────────────────────────────────────────────
# The web assistant calls the same tools, but what authenticates it is the JWT
# session, not a PAT. It still needs an `EscopoEfetivo` — it is the format all of
# MCP's authorization consumes —, and the synthetic `token_id` below has two
# deliberate effects: the quota buckets (`ratelimit:mcp:assistente-editor:…`) are
# born separate from the PATs' buckets, and the audit line immediately
# distinguishes what came from the screen from what came from an external client.

PREFIXO_DO_EDITOR = "assistente-editor"

# These are NOT the PAT's six scopes. `triggers:manage` and `drive:write` were
# left out of the first version by the owner's decision: deleting a schedule or a
# Drive file destroys another workspace member's data, and a natural-language
# conversation is precisely where a misunderstanding is cheapest to commit
# ("limpa os agendamentos antigos" (clean up the old schedules) is a sentence
# someone types without thinking). Widening it here is one line — and it is a
# product decision, not an implementation one.
ESCOPOS_DO_EDITOR: frozenset[str] = frozenset(
    {
        "workflows:read",
        "workflows:write",
        "runs:execute",
        "drive:read",
    }
)


def escopo_do_editor(
    *,
    user_id: str,
    username: str | None,
    workspace_ids: frozenset[str] | set[str] | list[str],
) -> EscopoEfetivo:
    """The scope of an assistant conversation — the session's user, no PAT.

    Pure on purpose: `workspace_ids` arrives resolved by the caller (with
    `listar_workspace_ids`), and not by a query from here. This module is
    imported by `erros`, by the tools and by the middleware; a database
    dependency in it would drag the models into that whole path — and would
    make it impossible to test building the scope without starting a database.

    `todos_os_workspaces=True` because there is no token restricting anything:
    the reach is exactly the user's, today and when they join a new workspace.
    """
    return EscopoEfetivo(
        user_id=user_id,
        username=username,
        token_id=f"{PREFIXO_DO_EDITOR}:{user_id}",
        token_prefix=PREFIXO_DO_EDITOR,
        scopes=ESCOPOS_DO_EDITOR,
        workspace_ids=frozenset(workspace_ids),
        todos_os_workspaces=True,
    )


# ── Home assistant ────────────────────────────────────────────────────────────
# The Home assistant is the assistant of ANOTHER surface: same JWT session, but
# FULL reach. Unlike the editor assistant, it creates and runs its OWN workflows
# and changes what already existed — and what holds back what it can destroy is
# the CLICK CONFIRMATION verified on the server (`app/services/assistente_superficie.py`),
# not the absence of a scope. The difference in reach lives here, in the
# IDENTITY, and not in a list scattered across the loop.

PREFIXO_DO_ASSISTENTE = "assistente"

# The PAT's SIX scopes, `pat.ESCOPOS` — including `triggers:manage` and
# `drive:write`, which the editor assistant does NOT carry. They come in here
# because deleting a schedule or a Drive file is an action the assistant can
# take, as long as the person clicks to confirm; removing the scope would make
# the confirmation useless (there would be nothing to confirm).
ESCOPOS_DO_ASSISTENTE: frozenset[str] = frozenset(pat.ESCOPOS)


def escopo_do_assistente(
    *,
    user_id: str,
    username: str | None,
    workspace_ids: frozenset[str] | set[str] | list[str],
) -> EscopoEfetivo:
    """The scope of a Home assistant conversation — the session's user, full reach.

    Modeled on `escopo_do_assistente`, with three deliberate differences:

    - `token_id`/`token_prefix` "assistente:…": the quota buckets
      (`ratelimit:mcp:assistente:{user}`) and the audit line are born separate
      from the PAT's and the editor assistant's, for free — everything is keyed
      by `token_id`;
    - the SIX scopes (`ESCOPOS_DO_ASSISTENTE`), not the editor's four;
    - `origem_dos_fluxos="assistente"`: every workflow it creates is born
      marked, and the listings hide it by default. It is an origin stamp, not
      a privilege — it widens no reach.

    The model's TOKEN quota stays on the `assistente:tokens:{user}` key
    (`cotas.chave_de_tokens`), SHARED with the editor: the model is the same and
    the per-person budget is a single one.
    """
    return EscopoEfetivo(
        user_id=user_id,
        username=username,
        token_id=f"{PREFIXO_DO_ASSISTENTE}:{user_id}",
        token_prefix=PREFIXO_DO_ASSISTENTE,
        scopes=ESCOPOS_DO_ASSISTENTE,
        workspace_ids=frozenset(workspace_ids),
        todos_os_workspaces=True,
        origem_dos_fluxos="assistente",
    )


def escopo_da_chamada(ctx) -> EscopoEfetivo:
    """The scope of this call, via the tool's `ctx` or via the `ContextVar`.

    The order matters: `request.state` is per request and does not get mixed up
    between concurrent calls; the `ContextVar` is the fallback (and the only path
    in tests that call the tool function directly). With neither, the call is
    not authenticated — and then there is nothing to answer but "forbidden".
    """
    requisicao = getattr(getattr(ctx, "request_context", None), "request", None)
    escopo = getattr(getattr(requisicao, "state", None), "escopo", None)
    if isinstance(escopo, EscopoEfetivo):
        return escopo
    do_contexto = ESCOPO_ATUAL.get()
    if do_contexto is not None:
        return do_contexto
    raise erro(
        "forbidden",
        "Chamada sem identidade: nenhum token pessoal de acesso foi resolvido.",
        "conecte-se com Authorization: Bearer atl_pat_…",
    )


def exigir_escopo(escopo: EscopoEfetivo, *necessarios: str) -> None:
    """Refuses the call, naming the missing scope.

    Naming it is deliberate: the caller has no way to guess which box to tick
    on the tokens screen, and the scope name reveals nothing about the data.
    The hint says WHO ticks it: the tokens screen only opens for the system
    administrator (`web/proxy.ts` sends non-admins to `/`).
    """
    faltando = [e for e in necessarios if not escopo.tem(e)]
    if not faltando:
        return
    raise erro(
        "forbidden_scope",
        "Este token não tem o escopo necessário: " + ", ".join(faltando) + ".",
        "crie um token com esse escopo em /settings/tokens "
        "(hoje, página só de administradores do sistema)",
        missing_scope=faltando if len(faltando) > 1 else faltando[0],
    )
