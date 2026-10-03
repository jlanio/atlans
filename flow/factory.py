# flow/factory.py
"""
NodeFactory: simple, cohesive factory for instantiating workflow nodes.
"""
from flow.registry import NODE_REGISTRY
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

# Properties that reach the factory ALREADY with the secret in plaintext: the server
# resolves the credential and injects the decrypted value into the node's properties
# before instantiating it (see app/services/credential_resolver.py). Lowercase
# names — the comparison is case-insensitive, but by EXACT NAME: `awsSecretAccessKey`
# (old SaveToS3 field) did not match `secret` and came out in plaintext in the log,
# in the redacted read and in the lint.
_SECRET_PROPERTIES = frozenset({
    'http_auth', 's3_auth', 'connectionstring', 'token', 'password', 'senha',
    'secret', 'api_key', 'apikey', 'authorization', 'private_key',
    'awssecretaccesskey',
})


def _without_secrets(props: dict) -> dict:
    """Copy of the properties with the sensitive values replaced by a marker.

    The instantiation log printed the WHOLE properties, and they carry the
    decrypted Bearer token and the database password. At DEBUG that is enough
    for the user's secret to end up written in plain text in the log file and in
    any collector it gets shipped to — outside the database, where it is
    encrypted, and outside the control of whoever registered it.
    """
    if not isinstance(props, dict):
        return props
    return {
        chave: ('***' if str(chave).lower() in _SECRET_PROPERTIES else valor)
        for chave, valor in props.items()
    }


class NodeFactory:
    """
    Responsible for creating node instances based on JSON definitions.

    Example definition:
        {
            'id': '1',
            'name': 'MyNode',
            'properties': { 'param1': 'value' }
        }
    """
    def __init__(self):
        self.logger = get_logger(__name__)
        self.registry = NODE_REGISTRY

    def create(self, node_def: dict) -> BaseNode:
        node_id = node_def.get('id')
        name = node_def.get('name')
        props = node_def.get('properties', {})

        cls = self.registry.get(name)
        if cls is None:
            from flow.nodes.contrato import unknown_node_hint
            msg = f"Node '{name}' não encontrado para instância (id={node_id}).{unknown_node_hint(name)}"
            self.logger.error(msg)
            raise ValueError(msg)

        if not issubclass(cls, BaseNode):
            msg = f"Node '{name}' não é subclasse de BaseNode — rejeitado."
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.debug(
            "[Factory] Instanciando nó '%s' (id=%s) com props=%s",
            name, node_id, _without_secrets(props),
        )
        return cls(node_id=node_id, parameters=props)
    
    def get(self, name: str):
        """
        Returns the registered node class, without instantiating it.
        """
        return self.registry.get(name)