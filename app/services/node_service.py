# app/services/node_service.py
from functools import lru_cache
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from flow.registry import NODE_REGISTRY
from app.schemas.node import NodeDefinition, NodeProperty, NodePort, NodeOutputField
from app.services.disabled_nodes_service import disabled_names


@lru_cache(maxsize=1)
def _catalogo_completo() -> List[tuple]:
    """Catalogo montado UMA vez a partir do NODE_REGISTRY.

    `cls.description()` e literal/pura (ja chamada no import, em flow/registry.py)
    e o NODE_REGISTRY nao muda em runtime — remontar os ~64 NodeDefinition e os
    objetos Pydantic a CADA GET /nodes era trabalho repetido. O overlay de nos
    desabilitados continua por request (em list_nodes); so o catalogo base, que
    e o que custa, e cacheado.

    Devolve pares (nome_no_registry, NodeDefinition): a chave e o nome do REGISTRY
    — o mesmo que o filtro de desabilitados usa —, nao o `name` da description.
    Testes que mexem no NODE_REGISTRY limpam este cache com
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

        # Campos de saída — a fonte única e tipada do contrato (A13): lista
        # plana com `type` e, quando o campo tem ponto de conexão próprio no
        # canvas, `port=True`. Chaves internas do protocolo (__response__,
        # __artifact__) não são saídas que uma aresta possa consumir: o
        # executor as remove do que o nó entrega (core.py::_actual_keys).
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
    Serviço para listar nodes registrados,
    lendo suas properties da description().

    Nodes desabilitados pelo admin (via /admin/nodes) sao filtrados aqui —
    drawer do canvas nao os vê. A entidade canonica continua sendo
    NODE_REGISTRY; o filtro e overlay via SystemConfig.disabled_nodes.

    O catalogo base e montado uma vez (`_catalogo_completo`, cacheado); aqui
    so aplicamos o overlay de desabilitados, que e leitura barata (ja cacheada
    em disabled_nodes_service).
    """
    async def list_nodes(self, db: AsyncSession) -> List[NodeDefinition]:
        disabled = await disabled_names(db)
        return [defn for name, defn in _catalogo_completo() if name not in disabled]
