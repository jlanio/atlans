# tests/integration/test_saida_subfluxo_multipla.py
"""
Varias origens alimentando a saida publica de um sub-fluxo.

O `SubWorkflowOutput` aceitava UMA aresta chegando. Para devolver dois valores
ao pai era preciso um no-funil (SetFields/PythonScript) so para montar o dict —
um no que nao faz nada alem de existir por causa da restricao.

A restricao tinha causa real: com um unico ponto de conexao anonimo, duas
arestas espalham os dois dicts nas MESMAS chaves e a ultima vence. A saida
depende da ordem das arestas, e o contrato anuncia uma coisa entregando outra.

O que mudou: `ports` passou a declarar tambem os pontos de conexao (o mesmo
mecanismo do PythonScript). A partir de DUAS portas o editor preenche o `to_key`
de cada aresta com o nome da porta, e cada origem cai na sua propria chave.

Estes testes exercitam o EXECUTOR de verdade: o defeito e a correcao estao na
montagem dos inputs entre nos, que so aparece rodando o grafo.
"""
import asyncio
from unittest.mock import MagicMock

import flow.nodes  # noqa: F401  (popula o registry)


def _script(node_id, code, saida="result"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _filho(portas, edges_para_saida):
    return {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": []}},
            _script("a", "result = 'FOCOS'"),
            _script("b", "result = 'MAPA'"),
            {"id": "out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": portas}},
        ],
        "edges": [
            {"source": "in", "target": "a"},
            {"source": "in", "target": "b"},
            *edges_para_saida,
        ],
    }


def _rodar_pai(filho):
    from flow.executor import WorkflowExecutor

    pai = {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            {"id": "sub", "type": "control", "name": "SubWorkflow",
             "properties": {"workflowHash": "FILHO", "inputsMapping": {},
                            "timeoutSeconds": 60}},
        ],
        "edges": [{"source": "t", "target": "sub"}],
    }
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor(
            pai, task_id="t", publisher=publisher, workflow_hash="PAI",
            subworkflow_definitions={"FILHO": filho},
        ).run()
    )


COM_PORTAS = [
    {"source": "a", "target": "out", "from_key": "result", "to_key": "focos"},
    {"source": "b", "target": "out", "from_key": "result", "to_key": "mapa"},
]


def test_duas_origens_chegam_cada_uma_na_sua_chave():
    saida = _rodar_pai(_filho(["focos", "mapa"], COM_PORTAS))["sub"]

    assert saida["focos"] == "FOCOS"
    assert saida["mapa"] == "MAPA"
    # O involucro carrega o mesmo conjunto — e por ele que o pai referencia
    # tudo de uma vez em Jinja (`{{ Alias.subWorkflowResult }}`).
    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "mapa": "MAPA"}


def test_o_defeito_que_a_regra_evita():
    """Sem `to_key`, as duas arestas usam o `from_key` como nome.

    Nao e bug do executor a corrigir — e a razao de o editor so liberar varias
    conexoes quando o node declara duas ou mais portas.
    """
    sem_to_key = [
        {"source": "a", "target": "out", "from_key": "result"},
        {"source": "b", "target": "out", "from_key": "result"},
    ]
    saida = _rodar_pai(_filho([], sem_to_key))["sub"]

    # Uma unica chave, com o valor de UMA das duas origens: a outra sumiu.
    publico = saida["subWorkflowResult"]
    assert list(publico) == ["result"]
    assert publico["result"] in ("FOCOS", "MAPA")


def test_a_allowlist_continua_valendo_sobre_as_portas():
    """`ports` e ponto de conexao E contrato: o que nao esta na lista nao volta.

    Aqui a aresta entrega `mapa`, que nao foi declarada — o valor e descartado
    (com aviso no log) em vez de vazar para o pai.
    """
    saida = _rodar_pai(_filho(["focos"], COM_PORTAS))["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS"}
    assert "mapa" not in saida


def test_passthrough_sem_portas_continua_devolvendo_tudo():
    """Sub-fluxo de uso unico: uma aresta, nenhuma porta declarada."""
    uma_aresta = [{"source": "a", "target": "out", "from_key": "result"}]
    saida = _rodar_pai(_filho([], uma_aresta))["sub"]

    assert saida["subWorkflowResult"] == {"result": "FOCOS"}


# ── O contrato do node ───────────────────────────────────────────────────────

def test_subworkflowoutput_declara_entradas_dinamicas():
    """`dynamic_inputs` e o que faz o editor derivar os pontos de conexao da
    propriedade `ports`. Sem isso o node volta a ter um handle anonimo: os
    testes acima continuam passando (o executor nao muda), mas no canvas nao ha
    como ligar cada origem a sua chave — o `to_key` deixa de ser preenchido."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["SubWorkflowOutput"].description()
    assert d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["default"] == [], "vazio por padrao — preserva os sub-fluxos existentes"
