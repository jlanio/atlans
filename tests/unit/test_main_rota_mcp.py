# tests/unit/test_main_rota_mcp.py
"""
How `/mcp` fits into the app: exact routes, no JWT and no redirect.

Four things a well-meaning refactor would silently break:

- **`add_route`, never `app.mount`.** A mount would consume the prefix and hand
  the SDK's app an empty path, which does not match its internal route.
- **Both spellings respond.** `/mcp` and `/mcp/` point to the same ASGI app.
  Without the second route, the router answers 307 for the first, and the `Location`
  of that hop is built with the scheme the app sees — behind Traefik, without
  `--proxy-headers`, that is `http://`. A client following the hop would send
  the personal token outside TLS. Neither of the two may redirect.
- **No JWT dependency.** The route is mounted outside `include_router`, so it does
  not inherit the app's global dependencies; the authentication here is the PAT. If
  someone started registering it as an API route, a client with a valid token would
  get a JWT 401 before the MCP middleware saw the Bearer.
- **Out of OpenAPI.** The contract of `/mcp` is the MCP protocol, not the REST schema.
"""
from __future__ import annotations

import pytest
from starlette.routing import Route

from app.main import app


def _rota_do_mcp() -> Route:
    rotas = [r for r in app.router.routes if getattr(r, "path", None) == "/mcp"]
    assert len(rotas) == 1, f"esperava uma rota /mcp, achei {len(rotas)}"
    return rotas[0]


def _trailing_slash_route() -> Route:
    rotas = [r for r in app.router.routes if getattr(r, "path", None) == "/mcp/"]
    assert len(rotas) == 1, f"esperava uma rota /mcp/, achei {len(rotas)}"
    return rotas[0]


def test_route_is_exact_not_a_mount():
    rota = _rota_do_mcp()
    assert isinstance(rota, Route)
    assert rota.path == "/mcp"
    # `Mount` casaria qualquer caminho sob o prefixo e exigiria a barra final.
    from starlette.routing import Mount

    assert not isinstance(rota, Mount)


def test_route_accepts_any_protocol_method():
    # `methods=None` means "all": streamable HTTP uses POST, GET (SSE) and
    # DELETE (end session).
    assert _rota_do_mcp().methods is None


def test_route_carries_no_jwt_dependency():
    rota = _rota_do_mcp()
    from fastapi.routing import APIRoute

    assert not isinstance(rota, APIRoute)
    assert not getattr(rota, "dependencies", None)


def test_route_stays_out_of_openapi():
    assert "/mcp" not in app.openapi().get("paths", {})


def test_server_instance_lives_in_app_state():
    from app.mcp.servidor import AtlansServer

    assert isinstance(app.state.mcp_server, AtlansServer)
    # It is the same instance the lifespan uses to open the session manager.
    assert app.state.mcp_server.session_manager is not None


@pytest.mark.usefixtures("mock_redis")
async def test_post_without_pat_gets_401_from_real_app(client):
    """Through the whole-app fixture: middlewares, CORS and security headers."""
    r = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="atlans-mcp"'
    assert r.json()["error"] == "unauthorized"


async def test_mcp_without_slash_does_not_redirect(client):
    """No 307: the canonical URL responds on the first hop."""
    r = await client.post("/mcp", json={})
    assert r.status_code != 307


async def test_mcp_with_slash_also_responds_without_redirect(client):
    """`/mcp/` is a route of its own, not a 307 to `/mcp`.

    The redirect that used to exist here sent the client back through a `Location`
    built with the scheme seen by the app — `http://` behind a proxy that does not
    forward `X-Forwarded-Proto`. Repeating the request means repeating the
    `Authorization` header, and the personal token would go out in the clear. Without a hop, it can't.
    """
    r = await client.post("/mcp/", json={})
    assert r.status_code != 307
    assert "location" not in r.headers
    # And it reaches the same place: the PAT middleware, not the API router.
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == 'Bearer realm="atlans-mcp"'


def test_both_spellings_are_the_same_app():
    """Same transport and same `session_manager` — not a second mount.

    Two transport instances would mean two session managers, and the
    `lifespan` only starts the one of the instance that existed when it came up: the other
    would answer with a session error on every call.
    """
    from app.main import _NoTrailingSlashPath

    with_slash = _trailing_slash_route().endpoint
    assert isinstance(with_slash, _NoTrailingSlashPath)
    assert with_slash._app is _rota_do_mcp().endpoint
