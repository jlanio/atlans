# flow/factory.py
"""
NodeFactory: fábrica simples e coesa para instanciar nós do workflow.
"""
from flow.registry import NODE_REGISTRY
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

# Propriedades que chegam à fábrica JÁ com o segredo em claro: o servidor
# resolve a credencial e injeta o valor decifrado nas properties do nó antes de
# instanciá-lo (ver app/services/credential_resolver.py). Nomes em minúsculas —
# a comparação é feita sem caixa, mas é por NOME EXATO: `awsSecretAccessKey`
# (campo antigo do SaveToS3) não casava com `secret` e saía em claro no log, na
# leitura redigida e no lint.
_PROPRIEDADES_SECRETAS = frozenset({
    'http_auth', 's3_auth', 'connectionstring', 'token', 'password', 'senha',
    'secret', 'api_key', 'apikey', 'authorization', 'private_key',
    'awssecretaccesskey',
})


def _sem_segredos(props: dict) -> dict:
    """Cópia das propriedades com os valores sensíveis trocados por marcador.

    O log de instanciação imprimia as properties INTEIRAS, e nelas vai o token
    Bearer decifrado e a senha do banco. Em DEBUG isso é o bastante para o
    segredo do usuário ficar gravado em texto puro no arquivo de log e em
    qualquer coletor para onde ele seja enviado — fora do banco, onde está
    cifrado, e fora do controle de quem o cadastrou.
    """
    if not isinstance(props, dict):
        return props
    return {
        chave: ('***' if str(chave).lower() in _PROPRIEDADES_SECRETAS else valor)
        for chave, valor in props.items()
    }


class NodeFactory:
    """
    Responsável por criar instâncias de nós com base em definições JSON.

    Exemplo de definição:
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
            from flow.nodes.contrato import dica_de_no_desconhecido
            msg = f"Node '{name}' não encontrado para instância (id={node_id}).{dica_de_no_desconhecido(name)}"
            self.logger.error(msg)
            raise ValueError(msg)

        if not issubclass(cls, BaseNode):
            msg = f"Node '{name}' não é subclasse de BaseNode — rejeitado."
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.debug(
            "[Factory] Instanciando nó '%s' (id=%s) com props=%s",
            name, node_id, _sem_segredos(props),
        )
        return cls(node_id=node_id, parameters=props)
    
    def get(self, name: str):
        """
        Retorna a classe do nó registrada, sem instanciá-la.
        """
        return self.registry.get(name)