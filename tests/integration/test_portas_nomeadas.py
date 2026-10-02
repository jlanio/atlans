# tests/integration/test_portas_nomeadas.py
"""
Duas entradas distintas chegando ao mesmo no.

O nome da variavel que o script recebe vem do `to_key` da aresta. O editor so
preenche `to_key` quando o no de destino DECLARA mais de uma porta; sem ele o
executor cai no `from_key` (core.py) — que e "output" em praticamente todo no.
Duas arestas escrevem na mesma chave e a segunda sobrescreve a primeira.

O sintoma nao denuncia a causa: o script reclama de uma variavel indefinida, sem
nada dizendo que a outra entrada foi perdida. Foi assim que o `PythonScript`
passou a existir sem conseguir combinar duas fontes.

Estes testes exercitam o EXECUTOR de verdade, e nao o no isolado: o defeito
estava na montagem dos inputs entre nos, que so aparece rodando o grafo.
"""
import asyncio
from unittest.mock import MagicMock

import pytest


def _script(node_id, code, saida="r"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _rodar(nodes, edges):
    from flow.executor import WorkflowExecutor

    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor({"nodes": nodes, "edges": edges},
                         task_id="t", publisher=publisher).run()
    )


# ── O defeito ────────────────────────────────────────────────────────────────

def test_sem_to_key_a_segunda_aresta_SOBRESCREVE_a_primeira():
    """Documenta o comportamento herdado: sem `to_key`, as duas arestas usam o
    `from_key` como nome e uma delas se perde.

    Nao e um bug a corrigir no executor — e o motivo pelo qual o no precisa
    DECLARAR portas. Se um dia isto passar a acumular em vez de sobrescrever,
    este teste avisa que o contrato mudou.
    """
    with pytest.raises(Exception) as e:
        _rodar(
            [_script("a", "r = 'A'"), _script("b", "r = 'B'"),
             _script("c", "r = f'{A}+{B}'")],
            [{"source": "a", "target": "c", "from_key": "r"},
             {"source": "b", "target": "c", "from_key": "r"}],
        )
    msg = str(e.value)
    assert "not defined" in msg
    assert "['r']" in msg, "so uma entrada chegou, com o nome do from_key"


# ── O conserto ───────────────────────────────────────────────────────────────

def test_com_to_key_as_duas_entradas_chegam_pelo_nome():
    resultado = _rodar(
        [_script("a", "r = 'A'"), _script("b", "r = 'B'"),
         _script("c", "r = f'{entrada_1}+{entrada_2}'")],
        [{"source": "a", "target": "c", "from_key": "r", "to_key": "entrada_1"},
         {"source": "b", "target": "c", "from_key": "r", "to_key": "entrada_2"}],
    )
    assert resultado["c"]["r"] == "A+B"


def test_to_key_nomeia_mesmo_com_from_key_diferente():
    """`to_key` vence: e o nome de CHEGADA, independente de como o pai chamava."""
    resultado = _rodar(
        [_script("a", "saida_do_a = 'A'", saida="saida_do_a"),
         _script("c", "r = pontos")],
        [{"source": "a", "target": "c", "from_key": "saida_do_a", "to_key": "pontos"}],
    )
    assert resultado["c"]["r"] == "A"


def test_uma_entrada_sem_to_key_continua_funcionando():
    """Nao pode quebrar fluxo existente: sem portas declaradas o `ports` fica
    vazio, o no segue com um ponto de conexao anonimo e a variavel continua
    vindo pelo `from_key`."""
    resultado = _rodar(
        [_script("a", "r = 'A'"), _script("c", "r = r + '!'")],
        [{"source": "a", "target": "c", "from_key": "r"}],
    )
    assert resultado["c"]["r"] == "A!"


# ── O contrato do no ─────────────────────────────────────────────────────────

def test_pythonscript_declara_entradas_dinamicas():
    """`dynamic_inputs` e o que faz o editor derivar os pontos de conexao da
    propriedade `ports` em vez da lista fixa do catalogo."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["PythonScript"].description()
    assert d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["type"] == "ports"
    assert ports["default"] == [], "vazio por padrao — e o que preserva os fluxos existentes"
