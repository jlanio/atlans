# flow/core/aliases.py
"""Single rule for a node's Jinja alias.

The executor registers each node's outputs in the context under an alias
(`named[alias]`, see flow/executor/core.py) and the static lint has to apply
EXACTLY the same rule to flag what the executor would silently discard.
The rule used to live as a private function of the executor, and the lint could
not import it without pulling in the whole node registry. Here it is pure code (stdlib).
"""
from __future__ import annotations

from typing import Any, Mapping

# Aliases that collide with fixed keys of the Jinja context (rendering.py).
# If the user names a node with one of these, it would be silently
# overwritten by the fixed keys and the expression {{ alias.x }} would point
# to something else.
RESERVED_ALIASES = frozenset({"inputs", "nodes", "named", "now", "uuid", "env"})


def alias_declarado(node_def: Mapping[str, Any]) -> str:
    """User-written alias: the top-level one beats `properties.alias`.

    The choice is by TRUTHINESS, not validity: a top-level alias that is filled in
    but invalid does not fall back to the `properties` one — it falls back to
    `name` (in resolve_alias). That is how the executor has always behaved;
    changing it here would change under which name an already-saved workflow
    registers its nodes.
    """
    props = node_def.get("properties")
    custom = node_def.get("alias") or (props.get("alias") if isinstance(props, dict) else None)
    return str(custom) if custom else ""


def alias_e_valido(alias: str) -> bool:
    """Python identifier (Unicode is fine — "Área" passes) and not reserved."""
    return bool(alias) and alias.isidentifier() and alias not in RESERVED_ALIASES


def resolve_alias(node_def: Mapping[str, Any]) -> str:
    """The node's Jinja-safe alias: the custom one if valid, otherwise `name`."""
    custom = alias_declarado(node_def)
    if alias_e_valido(custom):
        return custom
    return node_def["name"]
