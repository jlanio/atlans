# app/mcp/auth.py
"""
`PATAuthentication` — the edge of `/mcp`.

Pure ASGI middleware (not `BaseHTTPMiddleware`) in front of the SDK app. Pure
because the streamable HTTP transport returns long-lived SSE, and Starlette's
`BaseHTTPMiddleware` wraps the response in a task with a queue — the path by
which a run's progress would reach the client late or not at all. Here the
only thing that happens is: validate, decorate the `scope`, pass it on.

What this module guarantees (and it is the only line between a token and the data):
- token NEVER in the query string — URLs leak in proxy logs, history and Referer.
  If the client sends it, the response is 401 without even looking at the value;
- only `Authorization: Bearer atl_pat_…`. A session JWT does not count here:
  `/mcp` stays outside the global dependencies on purpose, and accepting a JWT
  would give a client the browser's whole session;
- every refusal returns the SAME message. Distinguishing "does not exist" from
  "expired" from "revoked" would turn the endpoint into an oracle of valid tokens;
- the resolved scope goes to two places: `scope["state"]["escopo"]` (what the
  tools read via `ctx`) and the `ContextVar` (the only channel that reaches
  `list_tools`, which does not receive `ctx`), with a guaranteed reset in `finally`;
- `GET /mcp` is refused with 405 before any trip to the database. With
  `stateless_http=True` there is no server stream to deliver: the GET would
  open an SSE that never sends anything and never closes, and a read-only token
  would hold a worker connection per call. The 405 with `Allow: POST` is the
  response the transport specification itself provides for a server that does
  not offer the server→client channel, and every MCP client knows how to read it.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs

from app.core.authorization.pat import is_pat_secret
from app.core.authorization.workflow_access import listar_workspace_ids
from app.core.utils.logger import get_logger
from app.mcp import infra
from app.mcp.escopo import ESCOPO_ATUAL, EffectiveScope
from app.services import api_token_service

logger = get_logger("app.mcp.auth")

REALM = "atlans-mcp"

# A single sentence, for any refusal reason — see the module note.
#
# The token is PERSONAL: each account creates, lists and revokes only its own
# (`api_token_service`), and it acts on behalf of whoever created it. And
# `/settings/tokens`, like every page outside Home, sends non-admins to `/`
# (`web/proxy.ts`): today only the system administrator can create a token. The
# message says so, without telling anyone to "ask the admin for a token" — the
# admin only creates tokens for their own account, and handing one over would
# let someone else act on their behalf.
REFUSAL_MESSAGE = (
    "Token pessoal de acesso ausente ou inválido. Use "
    "Authorization: Bearer atl_pat_… (cada pessoa cria o próprio token em "
    "/settings/tokens, hoje página só de administradores do sistema)."
)

# Names careless clients use to pass the token in the URL.
TOKEN_PARAMETERS = ("access_token", "token")


class PATAuthentication:
    """Wraps the MCP ASGI app, requiring a valid PAT."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        tipo = scope.get("type")
        if tipo == "lifespan":
            # The transport's lifecycle does NOT pass through here inward. What
            # enters `session_manager.run()` is `app.main`'s `lifespan`, once per
            # process; passing the event on to the SDK app would do a second
            # `run()` on the same manager — which is a single-use context — and
            # the failure would only show up on the first request. We answer the
            # protocol and warn, so that a refactor that swaps the route for a
            # mount is noticed in the log instead of in the middle of the night.
            logger.warning(
                "O app do MCP recebeu lifespan: o gerenciador de sessões é iniciado "
                "por app.main, não aqui."
            )
            await _serve_lifespan(receive, send)
            return

        if tipo != "http":
            # `websocket`: MCP exposes none, and there is nothing to authenticate.
            await self.app(scope, receive, send)
            return

        if scope.get("method") == "GET":
            # Before the database on purpose — see the module note.
            await _refuse_method(send)
            return

        if _has_token_in_query(scope.get("query_string", b"")):
            logger.warning("Tentativa de autenticar no MCP com token na query string — recusada.")
            await _refuse(send)
            return

        segredo = _secret_from_header(scope.get("headers") or [])
        if not is_pat_secret(segredo):
            await _refuse(send)
            return

        async with infra.sessao() as db:
            par = await api_token_service.resolver(db, segredo)
            if par is None:
                # Right format, token does not resolve: RFC 6750's `error="invalid_token"`
                # helps the client know it needs ANOTHER token, and not one more
                # header.
                await _refuse(send, invalido=True)
                return
            token, usuario = par
            user_workspaces = set(await listar_workspace_ids(db, usuario.id_hash))
            # `workspace_ids` NULL = "all of the user's workspaces, including
            # the ones they join later". Treating NULL as an empty list would take
            # away from the token precisely the reach the owner chose on the screen.
            token_reach = token.workspace_ids
            todos = token_reach is None
            alcance = user_workspaces if todos else user_workspaces & set(token_reach)
            escopo = EffectiveScope(
                user_id=usuario.id_hash,
                username=getattr(usuario, "username", None),
                token_id=token.id_hash,
                token_prefix=token.token_prefix,
                scopes=frozenset(token.scopes or ()),
                workspace_ids=frozenset(alcance),
                todos_os_workspaces=todos,
            )
            redis = infra.redis_ou_none()
            if redis is not None:
                # Best-effort with a 60 s throttle in the service itself; never
                # raises, and without Redis it simply does not stamp.
                await api_token_service.mark_used(db, redis, token)

        scope.setdefault("state", {})["escopo"] = escopo
        ficha = ESCOPO_ATUAL.set(escopo)
        try:
            await self.app(scope, receive, send)
        finally:
            ESCOPO_ATUAL.reset(ficha)


async def _serve_lifespan(receive, send) -> None:
    """Answers the lifecycle protocol without passing it on to the SDK app."""
    while True:
        mensagem = await receive()
        tipo = mensagem.get("type")
        if tipo == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif tipo == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return
        else:  # pragma: no cover - the protocol only defines the two events above
            return


def _has_token_in_query(query_string: bytes) -> bool:
    """True if the URL carries `access_token=`/`token=` — refuses before reading the value."""
    if not query_string:
        return False
    try:
        parametros = parse_qs(query_string.decode("latin-1"))
    except Exception:  # pragma: no cover - an unreadable query string is enough to refuse
        return True
    return any(nome in parametros for nome in TOKEN_PARAMETERS)


def _secret_from_header(headers) -> str | None:
    """The secret from `Authorization: Bearer …`, or None if the header is unusable."""
    for nome, valor in headers:
        if nome.lower() != b"authorization":
            continue
        try:
            texto = valor.decode("latin-1").strip()
        except Exception:  # pragma: no cover - unreadable header
            return None
        esquema, _, resto = texto.partition(" ")
        if esquema.lower() != "bearer":
            return None
        return resto.strip() or None
    return None


async def _refuse_method(send) -> None:
    """405 with `Allow: POST` — the method is not served, whatever the token."""
    corpo = json.dumps(
        {
            "error": "method_not_allowed",
            "message": (
                "O /mcp aceita apenas POST. Este servidor não abre stream de "
                "servidor→cliente: o progresso viaja no SSE da própria chamada."
            ),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 405,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(corpo)).encode("ascii")),
                (b"allow", b"POST"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": corpo})


async def _refuse(send, *, invalido: bool = False) -> None:
    """401 in JSON, with the challenge MCP clients know how to read."""
    corpo = json.dumps(
        {"error": "unauthorized", "message": REFUSAL_MESSAGE}, ensure_ascii=False
    ).encode("utf-8")
    challenge = f'Bearer realm="{REALM}"'
    if invalido:
        challenge += ', error="invalid_token"'
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(corpo)).encode("ascii")),
                (b"www-authenticate", challenge.encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": corpo})
