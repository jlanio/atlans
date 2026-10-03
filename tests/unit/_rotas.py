# tests/unit/_rotas.py
"""
The effective routes of a FastAPI app, for the tests that check what exists.

The name starts with `_` on purpose: pytest does not collect this file.

Up to FastAPI 0.140, `include_router` copied the included router's routes into
`app.routes`, already with the prefix: the list was flat, and each item had
`path` and `endpoint`. Since 0.141 `app.routes` holds one node per included
router (`_IncludedRouter`), with neither `path` nor `endpoint`. Code that scans
`app.routes` directly no longer sees any route from the routers: a test that
looks for a route fails, and one that looks for a *forbidden* route passes
without checking anything. `iter_route_contexts` (new in 0.141) returns each
route with its effective path, and it is what FastAPI itself uses to build the
OpenAPI.
"""
from __future__ import annotations


def effective_routes(app) -> list:
    """Every route of the app with `path` and `endpoint`, including those of included routers."""
    try:
        from fastapi.routing import iter_route_contexts
    except ImportError:  # FastAPI < 0.141: app.routes is already the flat list
        rotas = list(app.routes)
    else:
        # WebSocket route of an included router: the context returns path "", and the
        # effective path is on the route FastAPI builds to match the connection.
        rotas = [
            getattr(contexto, "starlette_route", None) or contexto
            for contexto in iter_route_contexts(app.routes)
        ]
    # Without this, a future format change would silently empty the paths again,
    # and an `assert "/x" not in caminhos` would pass without checking anything.
    without_path = [rota for rota in rotas if not getattr(rota, "path", None)]
    assert not without_path, f"rota sem caminho no app (o FastAPI mudou o app.routes?): {without_path[:3]}"
    return rotas
