# app/mcp/tools/__init__.py
"""
Registro das tools do servidor — um módulo por domínio.

`registrar_tools` é o único ponto que a fábrica conhece; cada módulo de domínio
expõe `registrar(server)` e decide sozinho quais tools declara. Assim uma frente
de trabalho acrescenta um domínio sem tocar na fábrica nem nos outros módulos.
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
    """Registra todas as tools na instância recebida."""
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
