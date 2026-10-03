"""
Node registry and decorator for automatic registration via description.
Recursively imports all submodules in 'nodes/' to trigger the decorators.
"""
import logging
import pkgutil
import importlib
from flow import nodes
from flow.nodes.base import BaseNode
from flow.nodes.contrato import validate_description
from flow.utils.logger import get_logger

logger = get_logger(__name__)
NODE_REGISTRY = {}

def register_node(cls):
    """
    Decorates a node class, registering it by the 'name' field of its description().

    The whole description is validated here, at import (`validate_description`):
    category, property types, output fields and known keys. A malformed
    node dies in CI with the exact cause — not on screen, as a field without
    an editor or a port without a type.
    """
    if not issubclass(cls, BaseNode):
        raise ValueError(f"{cls.__name__} não herda de BaseNode")
    desc = cls.description()
    try:
        validate_description(desc)
    except ValueError as exc:
        raise ValueError(f"{cls.__name__}: {exc}") from None
    name = desc['name']
    if name in NODE_REGISTRY:
        raise ValueError(f"Node duplicado registrado: {name}")
    NODE_REGISTRY[name] = cls
    logger.info(f"Node registrado: {name}")
    return cls

def auto_discover_nodes():
    """
    Discovers and imports all submodules inside 'nodes/' to register nodes automatically.

    Fails LOUDLY: swallowing the error made a node with an invalid description (or a
    broken import) simply vanish from the catalog — the palette, the MCP and validate
    stayed up without it, and nobody found out why.
    """
    for finder, module_name, ispkg in pkgutil.walk_packages(nodes.__path__, prefix=nodes.__name__ + '.'):
        try:
            importlib.import_module(module_name)
        except Exception as e:
            raise RuntimeError(f"Falha ao importar o módulo de nós '{module_name}': {e}") from e

def show_registered_nodes():
    """
    Displays the registered nodes, grouped by type (action, trigger, etc).
    """
    grouped = {}
    for node in NODE_REGISTRY.values():
        info = node.description()
        node_type = info.get('type', 'unknown').lower()
        grouped.setdefault(node_type, []).append(info.get('name', node.__name__))

    total = sum(len(v) for v in grouped.values())
    summary = ", ".join(f"{t}={len(n)}" for t, n in sorted(grouped.items()))
    logger.info(f"Nós registrados: {total} ({summary})")

    if logger.isEnabledFor(logging.DEBUG):
        lines = ["\nNÓS REGISTRADOS:"]
        for node_type, names in sorted(grouped.items()):
            lines.append(f"  [{node_type.upper()}]")
            lines.extend(f"    - {n}" for n in sorted(names))
        logger.debug("\n".join(lines))

# Runs automatic discovery on load
auto_discover_nodes()
show_registered_nodes()

__all__ = ['register_node', 'NODE_REGISTRY']
