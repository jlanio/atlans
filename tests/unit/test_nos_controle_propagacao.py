"""Data propagation through the branching nodes.

Control nodes exist to DECIDE where the workflow goes next, not to consume
the data. Three defects did exactly that:

1. `branch` was the first key of the returned dict. The branching edge is
   born without `from_key` (the UI saves `source_handle`/`condition` — see
   edge-persistence.ts), so the executor spreads the whole dict into the next
   node (core.py:599) and whoever reads `next(iter(inputs.values()))` received
   the BOOLEAN instead of the layer. There are eight such nodes, among them
   ComputeBBox, Geocode, HttpRequest's POST and ResponseNode.

2. `**inputs` came LAST and overwrote the `branch`/`value`/`result` the node
   itself had just computed. Chaining two branches, the second returned the
   FIRST one's decision — and since the executor routes by reading
   `outputs["branch"]` (core.py:628), the workflow went down a branch nobody
   chose.

3. `result` and the original key pointed to the same object, and
   `get_first_gdf` warned "more than one layer arrived" about a nonexistent
   choice.
"""
import asyncio

import geopandas as gpd
import pytest
from shapely.geometry import Point

from flow.nodes.base import BaseNode
from flow.nodes.control.conditional import Conditional
from flow.nodes.control.jinja_branch import JinjaBranchNode


@pytest.fixture
def camada():
    return gpd.GeoDataFrame(
        {"n": list("abc")},
        geometry=[Point(i, i) for i in range(3)],
        crs="EPSG:4326",
    )


def _cond(**props):
    base = {"metric": "count", "operator": ">", "compareTo": "1"}
    return Conditional(node_id="c", parameters={**base, **props})


# ── The data reaches the next node ──────────────────────────────────────────

def test_o_primeiro_valor_e_o_dado_e_nao_o_booleano(camada):
    """The reported symptom: the next node received True instead of the layer."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    primeiro = next(iter(saida.values()))
    assert isinstance(primeiro, gpd.GeoDataFrame)
    assert len(primeiro) == 3


def test_a_chave_original_do_pai_sobrevive(camada):
    saida = asyncio.run(_cond().execute({"focos": camada}))
    assert "focos" in saida
    assert saida["focos"] is camada


def test_todas_as_chaves_do_pai_sobrevivem(camada):
    """The node passes along the whole package, not just the first value."""
    saida = asyncio.run(_cond().execute({"camada": camada, "meta": {"fonte": "IBGE"}}))
    assert saida["camada"] is camada
    assert saida["meta"] == {"fonte": "IBGE"}


def test_result_continua_existindo(camada):
    """It is a selectable port in the edge selector (custom-edges); removing it
    would break workflows that already point to it in `from_key`."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    assert saida["result"] is camada


def test_o_branch_continua_sendo_booleano(camada):
    """The executor routes with `isinstance(outputs['branch'], bool)`
    (core.py:628) — without this the branch stops branching."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    assert isinstance(saida["branch"], bool)
    assert saida["branch"] is True
    assert saida["value"] == 3


# ── The node's decision is not overwritten ──────────────────────────────────

def test_a_decisao_do_no_vence_a_do_pai(camada):
    """A `branch` key coming from the parent must not erase this node's decision."""
    entrada = {"output": camada, "branch": True, "value": 999}
    # 3 features > 5 is false.
    saida = asyncio.run(_cond(operator=">", compareTo="5").execute(entrada))
    assert saida["branch"] is False
    assert saida["value"] == 3


def test_duas_bifurcacoes_decidem_de_forma_independente(camada):
    """O defeito mais grave, e silencioso: a segunda repetia a primeira."""
    s1 = asyncio.run(_cond(operator=">", compareTo="1").execute({"output": camada}))
    assert s1["branch"] is True

    # A segunda recebe o espalhamento da primeira e avalia a MESMA camada.
    s2 = asyncio.run(_cond(operator=">", compareTo="5").execute(dict(s1)))
    assert s2["branch"] is False, "a 2a bifurcação devolveu a decisão da 1a"
    assert s2["value"] == 3, "a 2a avaliou o booleano da 1a em vez da camada"


def test_a_segunda_bifurcacao_avalia_a_camada_e_nao_o_booleano(camada):
    """Before: `float(True)` = 1.0 became the second evaluation's `count`."""
    s1 = asyncio.run(_cond().execute({"output": camada}))
    s2 = asyncio.run(_cond().execute(dict(s1)))
    assert s2["value"] == 3


# ── JinjaBranch: mesmo contrato ─────────────────────────────────────────────

def _jinja(expr):
    return JinjaBranchNode(node_id="j", parameters={"expression": expr})


def test_jinja_branch_repassa_o_dado_primeiro(camada):
    saida = asyncio.run(_jinja("{{ value | length > 1 }}").execute({"output": camada}))
    assert isinstance(next(iter(saida.values())), gpd.GeoDataFrame)
    assert saida["branch"] is True


def test_jinja_branch_nao_e_sobrescrito_pelo_pai(camada):
    entrada = {"output": camada, "branch": True}
    saida = asyncio.run(_jinja("{{ false }}").execute(entrada))
    assert saida["branch"] is False


# ── ChangeDetector: `output` comes before `branch` ──────────────────────────

def test_change_detector_devolve_o_dado_antes_do_branch():
    """Without executing the node (it needs Redis): the dict's shape is the contract."""
    import inspect
    from flow.nodes.control.change_detector import ChangeDetector

    fonte = inspect.getsource(ChangeDetector.execute)
    pos_output = fonte.index('"output":')
    pos_branch = fonte.index('"branch":', fonte.index("def _resultado"))
    assert pos_output < pos_branch, "branch como primeira chave volta a mascarar o dado"


# ── get_first_gdf doesn't warn about a choice that doesn't exist ────────────

class _NoFalso(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "Falso", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {}


def test_mesma_camada_em_duas_chaves_nao_gera_aviso(camada, caplog):
    """It is exactly what the branch produces: `result` and the parent's key
    pointing to the SAME object. There is no ambiguity to warn about."""
    import logging

    no = _NoFalso(node_id="n1", parameters={})
    with caplog.at_level(logging.INFO):
        achada = no.get_first_gdf({"output": camada, "result": camada})

    assert achada is camada
    assert "Mais de uma camada" not in caplog.text


def test_camadas_distintas_continuam_avisando(camada, caplog):
    """The original guard has to survive: two DIFFERENT layers are real
    ambiguity, and silence there was the bug it came to fix."""
    import logging

    outra = camada.copy()
    no = _NoFalso(node_id="n1", parameters={})
    with caplog.at_level(logging.INFO):
        no.get_first_gdf({"a": camada, "b": outra})

    assert "Mais de uma camada" in caplog.text


# ── Simulation: the type announced to the next node ─────────────────────────
#
# On an edge WITHOUT `from_key` — which is every branching edge — the executor
# types the next node's input by the FIRST field of `outputs`. With
# `branch` in front, the editor announced `<boolean>` for a node that actually
# receives the layer.

@pytest.mark.parametrize("cls", [Conditional, JinjaBranchNode],
                         ids=lambda c: c.__name__)
def test_o_primeiro_campo_do_schema_e_o_dado(cls):
    campos = cls.description()["outputs"]
    assert campos[0]["name"] == "result", (
        f"{cls.__name__}: com '{campos[0]['name']}' na frente, a simulação "
        f"anuncia o tipo errado para o nó seguinte"
    )


def test_change_detector_ja_anuncia_o_dado_primeiro():
    from flow.nodes.control.change_detector import ChangeDetector
    campos = ChangeDetector.description()["outputs"]
    assert campos[0]["name"] == "output"


def test_todo_operador_do_select_tem_funcao():
    """Conditional indexes `_OP_FUNCS` directly by the operator, without checking:
    what guarantees it is one of the options is `validate()`. So every
    option needs its own function."""
    from flow.nodes.control.conditional import _OP_FUNCS
    props = {p["name"]: p for p in Conditional.description()["properties"]}
    assert {o["value"] for o in props["operator"]["options"]} == set(_OP_FUNCS)


# ── The data is the first AND the last key ──────────────────────────────────
#
# Different readers scan the dict in opposite directions: the eight nodes that use
# `next(iter(inputs.values()))` read from the front, and Merge with the "último"
# (last) strategy uses `reversed(inputs.values())`. With the data only in front,
# Merge started picking `value` — the metric's number — instead of the layer.

@pytest.mark.parametrize("estrategia,esperado", [("first", 0), ("last", -1)])
def test_o_dado_esta_nas_duas_pontas_do_dict(camada, estrategia, esperado):
    saida = asyncio.run(_cond().execute({"output": camada}))
    valores = list(saida.values())
    assert isinstance(valores[esperado], gpd.GeoDataFrame), (
        f"a ponta '{estrategia}' do dict devolveu {type(valores[esperado]).__name__}"
    )


def test_merge_com_estrategia_ultimo_recebe_a_camada(camada):
    """Real integration with the node that reads back to front."""
    from flow.nodes.control.merge import MergeNode

    saida_cond = asyncio.run(_cond().execute({"output": camada}))
    merge = MergeNode(node_id="m", parameters={"strategy": "last"})
    saida_merge = asyncio.run(merge.execute(dict(saida_cond)))

    assert isinstance(saida_merge["output"], gpd.GeoDataFrame)
    assert len(saida_merge["output"]) == 3


def test_merge_com_estrategia_primeiro_recebe_a_camada(camada):
    from flow.nodes.control.merge import MergeNode

    saida_cond = asyncio.run(_cond().execute({"output": camada}))
    merge = MergeNode(node_id="m", parameters={"strategy": "first"})
    saida_merge = asyncio.run(merge.execute(dict(saida_cond)))

    assert isinstance(saida_merge["output"], gpd.GeoDataFrame)


def test_a_ordem_e_estavel_encadeando_nos_diferentes(camada):
    """Reassigning an existing key keeps its POSITION in a Python dict. Without
    removing the control keys before rewriting them, the `result` inherited
    from JinjaBranch stayed in the middle and `value` ended up as the last key."""
    jb = asyncio.run(_jinja("{{ value | length > 1 }}").execute({"output": camada}))
    saida = asyncio.run(_cond().execute(dict(jb)))

    chaves = list(saida)
    assert chaves[-1] == "result", f"última chave é '{chaves[-1]}', não 'result'"
    assert isinstance(list(saida.values())[0], gpd.GeoDataFrame)
    assert isinstance(list(saida.values())[-1], gpd.GeoDataFrame)


def test_chave_de_controle_do_pai_nao_e_repassada_em_duplicidade(camada):
    """The parent's `branch`/`value`/`result` are superseded, not accumulated."""
    entrada = {"output": camada, "branch": True, "value": 99, "result": "velho"}
    saida = asyncio.run(_cond(operator=">", compareTo="5").execute(entrada))

    assert list(saida) == ["output", "branch", "value", "result"]
    assert saida["branch"] is False
    assert saida["value"] == 3
    assert saida["result"] is camada
