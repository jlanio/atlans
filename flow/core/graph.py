import logging
from collections import defaultdict, deque
from graphlib import TopologicalSorter, CycleError
from typing import Dict, List

logger = logging.getLogger(__name__)


class WorkflowGraph:
    """
    Constrói e analisa o grafo de execução do workflow.
    - Indexa arestas de entrada e saída para cada nó.
    - Calcula ordem topológica garantindo DAG.
    - Ignora nós isolados (sem arestas) opcionalmente.
    - Restringe execução aos nós alcançáveis a partir dos triggers E às
      dependências (ancestrais) desses nós, opcionalmente.
    """
    def __init__(
        self,
        node_defs: Dict[str, dict],  # mapeamento id -> definição de node
        edges: List[dict],           # lista de conexões {'source', 'target'}
        filter_isolated: bool = True,
        filter_trigger_reachable: bool = True,
    ):
        self.node_defs = node_defs
        self.edges = edges
        self.filter_isolated = filter_isolated
        self.filter_trigger_reachable = filter_trigger_reachable
        self.incoming = defaultdict(list)
        self.outgoing = defaultdict(list)
        self._index_edges()

    def _index_edges(self) -> None:
        """
        Indexa arestas por origem e destino em estruturas de fácil busca.

        Arestas ÓRFÃS — cujo `source` e/ou `target` não existe em `node_defs` —
        são descartadas (e logadas), não indexadas. Elas surgem de cruft real:
        um nó deletado no canvas deixando a aresta pendurada, expansão de
        sub-fluxo, import/edição manual do JSON. Se retidas, envenenam o run —
        `KeyError` na montagem de inputs (o run lê `self.incoming`) e na
        instanciação. `compute_order` aplica a mesma guarda na ordenação.
        """
        self.orphan_edges: List[dict] = []
        for edge in self.edges:
            src = edge['source']
            tgt = edge['target']
            if src not in self.node_defs or tgt not in self.node_defs:
                self.orphan_edges.append(edge)
                continue
            self.outgoing[src].append(edge)
            self.incoming[tgt].append(edge)
        if self.orphan_edges:
            logger.warning(
                "Ignorando %d aresta(s) órfã(s) (endpoint fora de node_defs): %s",
                len(self.orphan_edges),
                [f"{e.get('source')}->{e.get('target')}" for e in self.orphan_edges],
            )

    def compute_order(self) -> List[str]:
        """
        Retorna lista de IDs dos nós na ordem de execução (topológica),
        removendo nós isolados se filter_isolated == True.
        """
        # Cria mapa de predecessores
        predecessors = {nid: set() for nid in self.node_defs}
        for edge in self.edges:
            src = edge['source']
            tgt = edge['target']
            # Guarda contra aresta órfã (mesma cruft tratada em _index_edges):
            #  - target fora de node_defs → predecessors[tgt] daria KeyError cru
            #    (dict comum), abortando TODO o run antes de qualquer filtro;
            #  - source fora de node_defs → o id fantasma entraria como valor no
            #    set de predecessores e o TopologicalSorter o devolveria em
            #    static_order() como nó sem predecessores; os filtros abaixo só
            #    removem CHAVES, então ele vazaria para a instanciação (KeyError
            #    em node_defs[fantasma]).
            if src in self.node_defs and tgt in self.node_defs:
                predecessors[tgt].add(src)

        # Se solicitado, remove nós sem arestas de entrada ou saída.
        # O filtro só faz sentido quando o workflow tem arestas — se não há
        # arestas, todos os nós são "isolados" por definição e devem executar.
        if self.filter_isolated and self.edges:
            envolvidos = set(self.incoming.keys()) | set(self.outgoing.keys())
            for nid in list(predecessors.keys()):
                if nid not in envolvidos:
                    predecessors.pop(nid)

        # Se solicitado, restringe execução aos nós alcançáveis a partir dos
        # triggers E às dependências (ancestrais) desses nós.
        # Preserva fluxos paralelos legítimos (ex: dois triggers convergindo num Merge)
        # e elimina árvores desconectadas sem caminho até um trigger.
        # Quando não há triggers (ex: testes unitários isolados), o filtro não é aplicado.
        if self.filter_trigger_reachable:
            trigger_ids = {
                nid for nid in predecessors
                if self.node_defs.get(nid, {}).get("type") == "trigger"
            }
            if trigger_ids:
                # Frente: o run "desce" dos triggers seguindo as arestas de saída.
                reachable: set = set()
                queue: deque = deque(trigger_ids)
                while queue:
                    nid = queue.popleft()
                    if nid in reachable:
                        continue
                    reachable.add(nid)
                    for edge in self.outgoing.get(nid, []):
                        queue.append(edge["target"])
                # Trás: as DEPENDÊNCIAS (ancestrais) de cada nó que vai rodar também
                # rodam. Sem isto, uma fonte "lateral" que alimenta um nó alcançável
                # (ex.: WFS→Filtro→Caixa, com o trigger ligado só na Caixa) ficava de
                # fora, e a junção TRAVAVA: o executor conta os pais por aresta (Kahn),
                # e o pai que não entrou no run nunca decrementa esse contador — a
                # junção e o ramo inteiro nunca rodavam, só o trigger. (O predecessor
                # direto até vazava para a ORDEM como valor, mas o mesmo contador de
                # pais o segurava, então nem ele rodava.) Fechar o cone de entrada
                # resolve tudo: todo predecessor de um nó mantido também é mantido —
                # sem pai faltante travando o Kahn nem id pendurado no TopologicalSorter.
                manter: set = set(reachable)
                queue = deque(reachable)
                while queue:
                    nid = queue.popleft()
                    for src in predecessors.get(nid, ()):  # predecessors diretos
                        if src not in manter:
                            manter.add(src)
                            queue.append(src)
                for nid in list(predecessors.keys()):
                    if nid not in manter:
                        predecessors.pop(nid)

        # Topological sort
        sorter = TopologicalSorter(predecessors)
        try:
            order = list(sorter.static_order())
        except CycleError as e:
            raise ValueError(f"Ciclo detectado no grafo: {e}")

        return order

