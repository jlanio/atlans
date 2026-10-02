"""
Registry de nós e decorator para registro automático via descrição.
Importa recursivamente todos os submódulos em 'nodes/' para disparar decorators.
"""
import logging
import pkgutil
import importlib
from flow import nodes
from flow.nodes.base import BaseNode
from flow.nodes.contrato import validar_description
from flow.utils.logger import get_logger

logger = get_logger(__name__)
NODE_REGISTRY = {}

def register_node(cls):
    """
    Decora uma classe de nó, registrando-a pelo campo 'name' de sua description().

    O description inteiro é validado aqui, na importação (`validar_description`):
    categoria, tipos de propriedade, campos de saída e chaves conhecidas. Um nó
    malformado morre no CI com a causa exata — não na tela, como campo sem
    editor ou porta sem tipo.
    """
    if not issubclass(cls, BaseNode):
        raise ValueError(f"{cls.__name__} não herda de BaseNode")
    desc = cls.description()
    try:
        validar_description(desc)
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
    Descobre e importa todos os submódulos dentro de 'nodes/' para registrar nós automaticamente.

    Falha ALTO: engolir o erro fazia um nó com description inválido (ou import
    quebrado) simplesmente sumir do catálogo — a paleta, o MCP e o validate
    seguiam no ar sem ele, e ninguém descobria o porquê.
    """
    for finder, module_name, ispkg in pkgutil.walk_packages(nodes.__path__, prefix=nodes.__name__ + '.'):
        try:
            importlib.import_module(module_name)
        except Exception as e:
            raise RuntimeError(f"Falha ao importar o módulo de nós '{module_name}': {e}") from e

def show_registered_nodes():
    """
    Exibe os nós registrados, agrupados por tipo (action, trigger, etc).
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

# Executa a descoberta automática ao carregar
auto_discover_nodes()
show_registered_nodes()

__all__ = ['register_node', 'NODE_REGISTRY']
