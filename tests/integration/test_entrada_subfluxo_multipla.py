# tests/integration/test_entrada_subfluxo_multipla.py
"""
Varios dados ENTRANDO num sub-fluxo, e o trigger escolhendo o que passa adiante.

Espelho de test_saida_subfluxo_multipla.py, no lado da ENTRADA. Dois defeitos
que apareciam ao passar mais de um argumento:

  1. Entrar com 2+ valores no node SubWorkflow (invoke): sem `to_key` por porta,
     duas arestas com o mesmo nome de chave colidem em `inputs.update()` e a
     ultima vence — depois o `inputsMapping` reclama de chave que "nao chegou".
  2. Dentro do sub-fluxo, o SubWorkflowInput (trigger) so conseguia espalhar o
     dict inteiro para cada node seguinte — nao dava para dizer, pela aresta,
     "esta leva focos, aquela leva bbox".

A correcao torna o trigger e o invoke simetricos ao SubWorkflowOutput (que ja
funcionava): portas declaradas viram pontos de conexao nomeados, e cada aresta
carrega uma chave distinta (`from_key` na saida do trigger, `to_key` na entrada
do invoke). O EXECUTOR ja roteava por nome — estes testes exercitam o grafo de
verdade e travam esse contrato.
"""
import asyncio
from unittest.mock import MagicMock

import flow.nodes  # noqa: F401  (popula o registry)


def _script(node_id, code, saida="result"):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": code, "output_vars": saida, "timeout": 20}}


def _rodar_pai(filho, edges_pai_para_sub):
    """Pai que alimenta o node `sub` com {focos: 'FOCOS', bbox: 'BBOX'} vindos de
    dois nodes distintos, pelas arestas em `edges_pai_para_sub`."""
    from flow.executor import WorkflowExecutor

    pai = {
        "nodes": [
            {"id": "t", "type": "trigger", "name": "WebhookTrigger", "properties": {}},
            _script("pf", "result = 'FOCOS'"),
            _script("pb", "result = 'BBOX'"),
            {"id": "sub", "type": "control", "name": "SubWorkflow",
             "properties": {"workflowHash": "FILHO", "inputsMapping": {},
                            "timeoutSeconds": 60}},
        ],
        "edges": [
            {"source": "t", "target": "pf"},
            {"source": "t", "target": "pb"},
            *edges_pai_para_sub,
        ],
    }
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return asyncio.run(
        WorkflowExecutor(
            pai, task_id="t", publisher=publisher, workflow_hash="PAI",
            subworkflow_definitions={"FILHO": filho},
        ).run()
    )


# Cada origem cai na SUA porta de entrada do sub (to_key distinto).
PAI_PARA_SUB = [
    {"source": "pf", "target": "sub", "from_key": "result", "to_key": "focos"},
    {"source": "pb", "target": "sub", "from_key": "result", "to_key": "bbox"},
]


def _filho_passthrough():
    return {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput", "properties": {"ports": []}},
            {"id": "out", "type": "output", "name": "SubWorkflowOutput", "properties": {"ports": []}},
        ],
        "edges": [{"source": "in", "target": "out"}],
    }


def test_invoke_recebe_duas_entradas_cada_uma_na_sua_chave():
    """Bug do relato: passar 2 valores para o sub. Com `to_key` por porta, cada
    origem cai na sua chave — sem colisao 'ultima vence'."""
    saida = _rodar_pai(_filho_passthrough(), PAI_PARA_SUB)["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "bbox": "BBOX"}


def test_trigger_escolhe_o_que_passa_adiante_por_from_key():
    """Bug do relato: no sub-fluxo, escolher pela aresta o que o trigger manda a
    cada node. Cada aresta que sai do trigger leva `from_key` = a porta, entao o
    destino recebe SO aquela chave (aqui, roteada a portas nomeadas da saida)."""
    filho = {
        "nodes": [
            {"id": "in", "type": "trigger", "name": "SubWorkflowInput",
             "properties": {"ports": ["focos", "bbox"]}},
            {"id": "out", "type": "output", "name": "SubWorkflowOutput",
             "properties": {"ports": ["a", "b"]}},
        ],
        "edges": [
            {"source": "in", "target": "out", "from_key": "focos", "to_key": "a"},
            {"source": "in", "target": "out", "from_key": "bbox", "to_key": "b"},
        ],
    }
    saida = _rodar_pai(filho, PAI_PARA_SUB)["sub"]

    # `focos` foi so para a porta `a`, `bbox` so para a porta `b`: se o trigger
    # tivesse espalhado o dict inteiro, o rename por to_key pegaria o 1o valor e
    # as duas portas ficariam iguais.
    assert saida["a"] == "FOCOS"
    assert saida["b"] == "BBOX"


def test_passthrough_sem_portas_continua_espalhando():
    """NAO-REGRESSAO: trigger sem portas declaradas segue espalhando o dict
    inteiro (aresta sem `from_key`) — os sub-fluxos que ja existem nao mudam."""
    saida = _rodar_pai(_filho_passthrough(), PAI_PARA_SUB)["sub"]

    assert saida["subWorkflowResult"] == {"focos": "FOCOS", "bbox": "BBOX"}


def test_o_defeito_que_a_regra_evita():
    """Sem `to_key`, as duas arestas pai->sub usam o `from_key` ('result') como
    nome e colidem em inputs.update() — a ultima vence. E a razao de o editor
    preencher `to_key` por porta nomeada; o fix do frontend evita este estado."""
    sem_to_key = [
        {"source": "pf", "target": "sub", "from_key": "result"},
        {"source": "pb", "target": "sub", "from_key": "result"},
    ]
    saida = _rodar_pai(_filho_passthrough(), sem_to_key)["sub"]

    publico = saida["subWorkflowResult"]
    assert list(publico) == ["result"]
    assert publico["result"] in ("FOCOS", "BBOX")


# ── O contrato do node ───────────────────────────────────────────────────────

def test_subworkflowinput_declara_saidas_por_ports():
    """`outputs_from_ports` e o que faz o editor derivar os pontos de conexao de
    SAIDA do trigger da propriedade `ports` — cada porta vira um handle de saida,
    e a aresta que sai dela leva `from_key`. Sem isso o trigger volta a ter um
    unico handle anonimo: o executor nao muda, mas no canvas nao ha como escolher
    o que passar adiante. Simetrico ao `dynamic_inputs` do SubWorkflowOutput."""
    from flow.registry import auto_discover_nodes, NODE_REGISTRY
    auto_discover_nodes()

    d = NODE_REGISTRY["SubWorkflowInput"].description()
    assert d.get("outputs_from_ports") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["default"] == [], "vazio por padrao — preserva os sub-fluxos existentes"
