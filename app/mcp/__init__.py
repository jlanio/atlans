# app/mcp/__init__.py
"""Servidor MCP do Atlans — fachada sobre a API e o modelo de permissão que já existem."""
from __future__ import annotations

from app.mcp.servidor import create_mcp_server, criar_app_mcp

__all__ = ["create_mcp_server", "criar_app_mcp"]
