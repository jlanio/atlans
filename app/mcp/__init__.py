# app/mcp/__init__.py
"""Atlans MCP server — a facade over the API and the permission model that already exist."""
from __future__ import annotations

from app.mcp.servidor import create_mcp_server, criar_app_mcp

__all__ = ["create_mcp_server", "criar_app_mcp"]
