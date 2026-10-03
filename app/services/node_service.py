# app/services/node_service.py
from functools import lru_cache
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from flow.registry import NODE_REGISTRY
from app.schemas.node import NodeDefinition, NodeProperty, NodePort, NodeOutputField
from app.services.disabled_nodes_service import disabled_names


@lru_cache(maxsize=1)
def _catalogo_completo() -> List[tuple]:
    """Catalog built ONCE from NODE_REGISTRY.

    `cls.description()` is literal/pure (already called at import, in flow/registry.py)
    and NODE_REGISTRY does not change at runtime — rebuilding the ~64 NodeDefinitions and
    the Pydantic objects on EVERY GET /nodes was repeated work. The overlay of disabled
    nodes is still per request (in list_nodes); only the base catalog, which
    is what costs, is cached.

    Returns (registry_name, NodeDefinition) pairs: the key is the REGISTRY name
    — the same one the disabled filter uses —, not the description's `name`.
    Tests that touch NODE_REGISTRY clear this cache with
    `_catalogo_completo.cache_clear()`.
    """
    catalogo: List[tuple] = []
    for name, cls in NODE_REGISTRY.items():
        info: Dict[str, Any] = cls.description() or {}
        node_name = info.get('name', name)
        node_alias = info.get('alias', name)
        node_type = info.get('type')
        desc = info.get('description')
        raw_props = info.get('properties', [])

        props: List[NodeProperty] = []
        for p in raw_props:
            props.append(NodeProperty(
                name=p.get('name'),
                label=p.get('label'),
                type=p.get('type'),
                default=p.get('default'),
                description=p.get('description'),
                credential_types=p.get('credential_types'),
                suggest_columns=p.get('suggest_columns'),
                drive_extensions=p.get('drive_extensions'),
                options=p.get('options'),
                visibleWhen=p.get('visibleWhen'),
                required=bool(p.get('required', False)),
                placeholder=p.get('placeholder'),
            ))

        raw_inputs  = info.get('inputs',  []) or []
        inputs  = [NodePort(name=p['name'], type=p.get('type'), description=p.get('description')) for p in raw_inputs]

        # Output fields — the single, typed source of the contract (A13): a flat
        # list with `type` and, when the field has its own connection point on the
        # canvas, `port=True`. Internal protocol keys (__response__,
        # __artifact__) are not outputs an edge can consume: the
        # executor removes them from what the node delivers (core.py::_actual_keys).
        outputs = [
            NodeOutputField(
                name=f['name'],
                type=f.get('type'),
                description=f.get('description'),
                port=bool(f.get('port')),
            )
            for f in (info.get('outputs') or [])
            if isinstance(f, dict) and f.get('name') and not f['name'].startswith('__')
        ]

        catalogo.append((name, NodeDefinition(
            name=node_name,
            alias=node_alias,
            type=node_type,
            description=desc,
            properties=props,
            outputs=outputs or None,
            inputs=inputs  or None,
            dynamic_inputs=bool(info.get('dynamic_inputs', False)),
            dynamic_output=bool(info.get('dynamic_output', False)),
            outputs_from_ports=bool(info.get('outputs_from_ports', False)),
            requires_credential=bool(info.get('requires_credential', False)),
            source_kind=info.get('source_kind') or None,
            branches=bool(info.get('branches', False)),
        )))
    return catalogo


class NodeService:
    """
    Service to list registered nodes,
    reading their properties from description().

    Nodes disabled by the admin (via /admin/nodes) are filtered out here —
    the canvas drawer does not see them. The canonical entity is still
    NODE_REGISTRY; the filter is an overlay via SystemConfig.disabled_nodes.

    The base catalog is built once (`_catalogo_completo`, cached); here
    we only apply the disabled overlay, which is a cheap read (already cached
    in disabled_nodes_service).
    """
    async def list_nodes(self, db: AsyncSession) -> List[NodeDefinition]:
        disabled = await disabled_names(db)
        return [defn for name, defn in _catalogo_completo() if name not in disabled]
