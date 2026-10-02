"""Propagação de dados através dos nós de bifurcação.

Os nós de controle existem para DECIDIR por onde o fluxo segue, não para
consumir o dado. Três defeitos faziam justamente isso:

1. `branch` era a primeira chave do dict devolvido. A aresta de bifurcação
   nasce sem `from_key` (a UI grava `source_handle`/`condition` — ver
   edge-persistence.ts), então o executor espalha o dict inteiro no nó seguinte
   (core.py:599) e quem lê `next(iter(inputs.values()))` recebia o BOOLEANO no
   lugar da camada. São oito nós, entre eles ComputeBBox, Geocode, o POST do
   HttpRequest e o ResponseNode.

2. `**inputs` vinha por ÚLTIMO e sobrescrevia `branch`/`value`/`result` que o
   próprio nó acabara de calcular. Encadeando duas bifurcações, a segunda
   devolvia a decisão da PRIMEIRA — e como o executor roteia lendo
   `outputs["branch"]` (core.py:628), o fluxo seguia por um ramo que ninguém
   escolheu.

3. `result` e a chave original apontavam para o mesmo objeto, e o
   `get_first_gdf` avisava "mais de uma camada chegou" sobre uma escolha
   inexistente.
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


# ── O dado chega ao nó seguinte ─────────────────────────────────────────────

def test_o_primeiro_valor_e_o_dado_e_nao_o_booleano(camada):
    """O sintoma relatado: o nó seguinte recebia True em vez da camada."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    primeiro = next(iter(saida.values()))
    assert isinstance(primeiro, gpd.GeoDataFrame)
    assert len(primeiro) == 3


def test_a_chave_original_do_pai_sobrevive(camada):
    saida = asyncio.run(_cond().execute({"focos": camada}))
    assert "focos" in saida
    assert saida["focos"] is camada


def test_todas_as_chaves_do_pai_sobrevivem(camada):
    """O nó repassa o pacote inteiro, não só o primeiro valor."""
    saida = asyncio.run(_cond().execute({"camada": camada, "meta": {"fonte": "IBGE"}}))
    assert saida["camada"] is camada
    assert saida["meta"] == {"fonte": "IBGE"}


def test_result_continua_existindo(camada):
    """É porta escolhível no seletor da aresta (custom-edges); sumir com ela
    quebraria fluxos que já a apontam em `from_key`."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    assert saida["result"] is camada


def test_o_branch_continua_sendo_booleano(camada):
    """O executor roteia com `isinstance(outputs['branch'], bool)`
    (core.py:628) — sem isso a bifurcação deixa de bifurcar."""
    saida = asyncio.run(_cond().execute({"output": camada}))
    assert isinstance(saida["branch"], bool)
    assert saida["branch"] is True
    assert saida["value"] == 3


# ── A decisão do nó não é sobrescrita ───────────────────────────────────────

def test_a_decisao_do_no_vence_a_do_pai(camada):
    """Chave `branch` vinda do pai não pode apagar a decisão deste nó."""
    entrada = {"output": camada, "branch": True, "value": 999}
    # 3 feições > 5 é falso.
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
    """Antes: `float(True)` = 1.0 virava o `count` da segunda avaliação."""
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


# ── ChangeDetector: o `output` vem antes do `branch` ────────────────────────

def test_change_detector_devolve_o_dado_antes_do_branch():
    """Sem executar o nó (precisa de Redis): o formato do dict é o contrato."""
    import inspect
    from flow.nodes.control.change_detector import ChangeDetector

    fonte = inspect.getsource(ChangeDetector.execute)
    pos_output = fonte.index('"output":')
    pos_branch = fonte.index('"branch":', fonte.index("def _resultado"))
    assert pos_output < pos_branch, "branch como primeira chave volta a mascarar o dado"


# ── get_first_gdf não avisa sobre uma escolha que não existe ────────────────

class _NoFalso(BaseNode):
    @classmethod
    def description(cls):
        return {"name": "Falso", "type": "control", "properties": []}

    async def execute(self, inputs):
        return {}


def test_mesma_camada_em_duas_chaves_nao_gera_aviso(camada, caplog):
    """É exatamente o que a bifurcação produz: `result` e a chave do pai
    apontando para o MESMO objeto. Não há ambiguidade a avisar."""
    import logging

    no = _NoFalso(node_id="n1", parameters={})
    with caplog.at_level(logging.INFO):
        achada = no.get_first_gdf({"output": camada, "result": camada})

    assert achada is camada
    assert "Mais de uma camada" not in caplog.text


def test_camadas_distintas_continuam_avisando(camada, caplog):
    """A guarda original tem de sobreviver: duas camadas DIFERENTES são
    ambiguidade real, e o silêncio ali era o bug que ela veio corrigir."""
    import logging

    outra = camada.copy()
    no = _NoFalso(node_id="n1", parameters={})
    with caplog.at_level(logging.INFO):
        no.get_first_gdf({"a": camada, "b": outra})

    assert "Mais de uma camada" in caplog.text


# ── Simulação: o tipo anunciado ao nó seguinte ──────────────────────────────
#
# Numa aresta SEM `from_key` — que é toda aresta de bifurcação — o executor
# tipa a entrada do nó seguinte pelo PRIMEIRO campo de `outputs`. Com
# `branch` na frente, o editor anunciava `<boolean>` para quem na verdade
# recebe a camada.

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
    """O Conditional indexa `_OP_FUNCS` direto pelo operador, sem conferir:
    quem garante que ele é uma das options é o `validate()`. Então cada
    option precisa ter a sua função."""
    from flow.nodes.control.conditional import _OP_FUNCS
    props = {p["name"]: p for p in Conditional.description()["properties"]}
    assert {o["value"] for o in props["operator"]["options"]} == set(_OP_FUNCS)


# ── O dado é a primeira E a última chave ────────────────────────────────────
#
# Leitores diferentes varrem o dict em direções opostas: os oito nós que usam
# `next(iter(inputs.values()))` leem da frente, e o Merge com estratégia
# "último" usa `reversed(inputs.values())`. Com o dado só na frente, o Merge
# passava a pegar `value` — o número da métrica — no lugar da camada.

@pytest.mark.parametrize("estrategia,esperado", [("first", 0), ("last", -1)])
def test_o_dado_esta_nas_duas_pontas_do_dict(camada, estrategia, esperado):
    saida = asyncio.run(_cond().execute({"output": camada}))
    valores = list(saida.values())
    assert isinstance(valores[esperado], gpd.GeoDataFrame), (
        f"a ponta '{estrategia}' do dict devolveu {type(valores[esperado]).__name__}"
    )


def test_merge_com_estrategia_ultimo_recebe_a_camada(camada):
    """Integração real com o nó que lê de trás para frente."""
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
    """Reatribuir chave existente mantém a POSIÇÃO no dict Python. Sem remover
    as chaves de controle antes de reescrevê-las, o `result` herdado do
    JinjaBranch ficava no meio e `value` terminava como última chave."""
    jb = asyncio.run(_jinja("{{ value | length > 1 }}").execute({"output": camada}))
    saida = asyncio.run(_cond().execute(dict(jb)))

    chaves = list(saida)
    assert chaves[-1] == "result", f"última chave é '{chaves[-1]}', não 'result'"
    assert isinstance(list(saida.values())[0], gpd.GeoDataFrame)
    assert isinstance(list(saida.values())[-1], gpd.GeoDataFrame)


def test_chave_de_controle_do_pai_nao_e_repassada_em_duplicidade(camada):
    """`branch`/`value`/`result` do pai são superseded, não acumulados."""
    entrada = {"output": camada, "branch": True, "value": 99, "result": "velho"}
    saida = asyncio.run(_cond(operator=">", compareTo="5").execute(entrada))

    assert list(saida) == ["output", "branch", "value", "result"]
    assert saida["branch"] is False
    assert saida["value"] == 3
    assert saida["result"] is camada
