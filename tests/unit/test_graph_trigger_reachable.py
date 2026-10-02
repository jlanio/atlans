# tests/unit/test_graph_trigger_reachable.py
"""
Alcance por trigger + fechamento por DEPENDÊNCIAS (ancestrais).

O run é definido pelos triggers: executa o que "desce" deles. Mas uma FONTE
lateral — um `datasource` que alimenta um nó alcançável sem estar no caminho do
trigger (ex.: WFS→Filtro→Caixa, com o trigger ligado só na Caixa) — também tem
de rodar, senão o nó de junção roda sem o input.

Antes, o filtro só olhava para frente (alcançáveis do trigger) e podava a fonte.
A poda removia só as CHAVES dos inalcançáveis, então o predecessor DIRETO da
junção vazava como valor no TopologicalSorter e entrava na ORDEM — mas o
executor conta os pais por aresta (Kahn), e o pai que ficou fora do run nunca
decrementava esse contador: a junção e o ramo inteiro TRAVAVAM e não rodavam (só
o trigger). Agora o filtro fecha o cone de entrada: alcançáveis-do-trigger ∪
ancestrais deles.
"""
import pytest

from flow.core.graph import WorkflowGraph


def nd(**tipos):
    """node_defs a partir de id=tipo, ex.: nd(trig="trigger", wfs="datasource")."""
    return {i: {"id": i, "type": t} for i, t in tipos.items()}


def e(source, target):
    return {"source": source, "target": target}


def ordem(node_defs, edges):
    return WorkflowGraph(node_defs, edges).compute_order()


# ── Fonte lateral (o caso reportado) ────────────────────────────────────────────

def test_fonte_lateral_roda_o_ramo_inteiro():
    """WFS→Filtro→Caixa com o trigger ligado só na Caixa: o ramo inteiro roda."""
    o = ordem(
        nd(trig="trigger", wfs="datasource", filtro="action", caixa="spatial"),
        [e("wfs", "filtro"), e("filtro", "caixa"), e("trig", "caixa")],
    )
    assert set(o) == {"trig", "wfs", "filtro", "caixa"}
    # Ordem topológica: a fonte antes de quem a consome; a junção por último.
    assert o.index("wfs") < o.index("filtro") < o.index("caixa")
    assert o.index("trig") < o.index("caixa")


def test_fonte_lateral_dois_niveis():
    """Cadeia lateral mais funda (WFS→f1→f2→Caixa) também entra inteira."""
    o = ordem(
        nd(trig="trigger", wfs="datasource", f1="action", f2="action", caixa="spatial"),
        [e("wfs", "f1"), e("f1", "f2"), e("f2", "caixa"), e("trig", "caixa")],
    )
    assert set(o) == {"trig", "wfs", "f1", "f2", "caixa"}
    assert o.index("wfs") < o.index("f1") < o.index("f2") < o.index("caixa")


def test_todo_predecessor_de_um_no_mantido_tambem_e_mantido():
    """Regressão do vazamento: todo predecessor de um nó mantido também é mantido.

    Antes, `filtro` saía na ORDEM sem `wfs`; como o executor conta os pais por
    aresta (Kahn), a junção travava e o ramo inteiro não rodava. Aqui garantimos a
    invariante que evita isso: nenhum nó fica na ordem com uma dependência de fora.
    """
    node_defs = nd(trig="trigger", wfs="datasource", filtro="action", caixa="spatial")
    edges = [e("wfs", "filtro"), e("filtro", "caixa"), e("trig", "caixa")]
    o = set(ordem(node_defs, edges))
    # Para cada aresta cujo destino roda, a origem também roda.
    for aresta in edges:
        if aresta["target"] in o:
            assert aresta["source"] in o, (
                f"{aresta['target']} roda mas sua fonte {aresta['source']} ficou de fora"
            )


# ── O que NÃO muda ───────────────────────────────────────────────────────────────

def test_arvore_totalmente_solta_e_descartada():
    """Sem caminho ao trigger nem alimentando quem roda: continua podada."""
    o = ordem(
        nd(trig="trigger", a="action", b="datasource", c="action"),
        [e("trig", "a"), e("b", "c")],  # b→c é uma ilha
    )
    assert set(o) == {"trig", "a"}
    assert "b" not in o and "c" not in o


def test_dois_gatilhos_convergindo_num_merge():
    o = ordem(
        nd(t1="trigger", t2="trigger", m="action"),
        [e("t1", "m"), e("t2", "m")],
    )
    assert set(o) == {"t1", "t2", "m"}
    assert o.index("t1") < o.index("m") and o.index("t2") < o.index("m")


def test_ciclo_levanta_valueerror():
    with pytest.raises(ValueError, match="[Cc]iclo"):
        ordem(
            nd(trig="trigger", a="action", b="action"),
            [e("trig", "a"), e("a", "b"), e("b", "a")],
        )


def test_sem_trigger_nao_aplica_o_filtro():
    """Sem nenhum trigger (ex.: teste unitário isolado), tudo que tem aresta roda."""
    o = ordem(
        nd(a="datasource", b="action"),
        [e("a", "b")],
    )
    assert set(o) == {"a", "b"}
    assert o.index("a") < o.index("b")


def test_no_isolado_continua_descartado_mesmo_com_trigger():
    """O filtro de isolados (sem nenhuma aresta) segue valendo junto do novo fechamento."""
    o = ordem(
        nd(trig="trigger", caixa="spatial", solto="datasource"),
        [e("trig", "caixa")],  # `solto` não tem aresta nenhuma
    )
    assert set(o) == {"trig", "caixa"}
    assert "solto" not in o
