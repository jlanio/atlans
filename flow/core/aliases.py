# flow/core/aliases.py
"""Regra única do alias Jinja de um nó.

O executor registra as saídas de cada nó no contexto sob um alias
(`named[alias]`, ver flow/executor/core.py) e o lint estático precisa aplicar
EXATAMENTE a mesma regra para acusar o que o executor descartaria em silêncio.
Antes a regra vivia como função privada do executor, e o lint não podia
importá-la sem puxar o registry inteiro de nós. Aqui é código puro (stdlib).
"""
from __future__ import annotations

from typing import Any, Mapping

# Aliases que colidem com chaves fixas do contexto Jinja (rendering.py).
# Se o usuário nomear um nó com um destes, ele seria silenciosamente
# sobrescrito pelas chaves fixas e a expressão {{ alias.x }} apontaria para
# outra coisa.
RESERVED_ALIASES = frozenset({"inputs", "nodes", "named", "now", "uuid", "env"})


def alias_declarado(node_def: Mapping[str, Any]) -> str:
    """Alias escrito pelo usuário: o de topo vence `properties.alias`.

    A escolha é por VERACIDADE, não por validade: um alias de topo preenchido
    mas inválido não cai no de `properties` — cai no `name` (em resolve_alias).
    É o comportamento que o executor sempre teve; mudar isso aqui mudaria sob
    qual nome um fluxo já salvo registra seus nós.
    """
    props = node_def.get("properties")
    custom = node_def.get("alias") or (props.get("alias") if isinstance(props, dict) else None)
    return str(custom) if custom else ""


def alias_e_valido(alias: str) -> bool:
    """Identificador Python (Unicode vale — "Área" passa) e não reservado."""
    return bool(alias) and alias.isidentifier() and alias not in RESERVED_ALIASES


def resolve_alias(node_def: Mapping[str, Any]) -> str:
    """Alias Jinja-safe do nó: o customizado se válido, senão o `name`."""
    custom = alias_declarado(node_def)
    if alias_e_valido(custom):
        return custom
    return node_def["name"]
