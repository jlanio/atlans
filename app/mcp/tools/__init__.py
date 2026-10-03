# app/mcp/tools/__init__.py
"""
Registration of the server's tools — one module per domain.

`registrar_tools` is the only point the factory knows; each domain module
exposes `registrar(server)` and decides on its own which tools it declares. That
way a workstream adds a domain without touching the factory or the other
modules.
"""
from __future__ import annotations

from app.mcp.tools import (
    acervo,
    catalogo,
    construcao,
    credenciais,
    drive,
    drive_escrita,
    execucao,
    fontes,
    gatilhos,
    pins,
    workflows,
    workspaces,
)


def registrar_tools(server) -> None:
    """Registers all tools on the given instance."""
    workspaces.registrar(server)
    workflows.registrar(server)
    catalogo.registrar(server)
    credenciais.registrar(server)
    drive.registrar(server)
    construcao.registrar(server)
    execucao.registrar(server)
    acervo.registrar(server)
    pins.registrar(server)
    gatilhos.registrar(server)
    drive_escrita.registrar(server)
    fontes.registrar(server)
