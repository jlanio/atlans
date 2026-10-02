"""
Escopo de execucao, contrato simetrico e isolamento de pool em sub-workflows.

Tres regressoes cobertas aqui:

1. O filho era instanciado como `WorkflowExecutor(definition)` puro — sem
   task_id, workspace_id, publisher nem debug. Todo node que chama
   `require_scope()` (DataOutput, PublishMap, SaveToS3, SaveToShapefile,
   SaveToGeoparquet, SendEmail) falhava com "workspace_id nao injetado".

2. `ports` filtrava so na saida. Na entrada o contrato valia no save e era
   ignorado em runtime, entao o filho recebia o namespace inteiro do pai.

3. O cache de pools asyncpg era chaveado so pela connection string, apoiado na
   premissa de "um event loop por processo" — que sub-workflows quebravam.
"""
from unittest.mock import MagicMock, patch

import pytest

from flow.nodes.control.sub_workflow import SubWorkflowNode, _SubWorkflowEventPublisher


def _child_definition():
    return {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


def _child_final_outputs(public):
    return {"out": {"__subworkflow_output__": public}}


def _async_run(returns):
    async def _run(**kwargs):
        return returns
    return _run


def _node_with_scope(**scope):
    node = SubWorkflowNode("sub-1", {"workflowHash": "CHILD", "timeoutSeconds": 30})
    node.context = {"_subworkflow_definitions": {"CHILD": _child_definition()}}
    node._task_id = scope.get("task_id", "run-abc")
    node._workspace_id = scope.get("workspace_id", "ws-1")
    node._debug_mode = scope.get("debug_mode", False)
    node._workflow_hash = scope.get("workflow_hash", "PARENT")
    node._publisher = scope.get("publisher")
    return node


# ── 1. Propagacao de escopo ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filho_herda_task_id_e_workspace_id():
    """Sem isto, qualquer node de saida dentro do sub-fluxo quebra."""
    node = _node_with_scope(task_id="run-abc", workspace_id="ws-1")

    with patch("flow.executor.WorkflowExecutor") as cls:
        inst = MagicMock()
        inst.context = {}
        inst.run = _async_run(_child_final_outputs({"ok": True}))
        cls.return_value = inst

        await node.execute({})

    kwargs = cls.call_args.kwargs
    assert kwargs["task_id"] == "run-abc"
    assert kwargs["workspace_id"] == "ws-1"


@pytest.mark.asyncio
async def test_workflow_hash_do_filho_e_do_filho_nao_do_pai():
    """Artefatos e metricas do sub-fluxo pertencem a ele, nao ao chamador."""
    node = _node_with_scope(workflow_hash="PARENT")

    with patch("flow.executor.WorkflowExecutor") as cls:
        inst = MagicMock()
        inst.context = {}
        inst.run = _async_run(_child_final_outputs({"ok": True}))
        cls.return_value = inst

        await node.execute({})

    assert cls.call_args.kwargs["workflow_hash"] == "CHILD"


@pytest.mark.asyncio
async def test_sem_publisher_no_pai_nao_cria_wrapper():
    node = _node_with_scope(publisher=None)

    with patch("flow.executor.WorkflowExecutor") as cls:
        inst = MagicMock()
        inst.context = {}
        inst.run = _async_run(_child_final_outputs({"ok": True}))
        cls.return_value = inst

        await node.execute({})

    assert cls.call_args.kwargs["publisher"] is None


# ── 2. Namespacing de eventos ────────────────────────────────────────────────

def test_evento_do_filho_recebe_prefixo_do_node_pai():
    """node_ids do filho nao existem no canvas do pai — sem prefixo o frontend
    recebe eventos de nos desconhecidos."""
    parent = MagicMock()
    pub = _SubWorkflowEventPublisher(parent, "sub-1")

    pub.publish_event(run_id="r1", node="node-do-filho", status="completed")

    kwargs = parent.publish_event.call_args.kwargs
    assert kwargs["node"] == "sub-1::node-do-filho"
    assert kwargs["extra"]["subworkflow_parent_node"] == "sub-1"


def test_workflow_complete_do_filho_nao_e_repassado():
    """Encerraria o run do pai no frontend."""
    parent = MagicMock()
    pub = _SubWorkflowEventPublisher(parent, "sub-1")

    pub.publish_event(run_id="r1", node="__workflow_complete__", status="completed")

    parent.publish_event.assert_not_called()


def test_falha_ao_publicar_nao_derruba_execucao():
    parent = MagicMock()
    parent.publish_event.side_effect = Exception("redis down")
    pub = _SubWorkflowEventPublisher(parent, "sub-1")

    pub.publish_event(run_id="r1", node="n1", status="started")  # não levanta


# ── 3. Contrato simetrico (ports na entrada) ─────────────────────────────────

@pytest.mark.asyncio
async def test_input_filtra_chaves_fora_do_contrato():
    from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

    node = SubWorkflowInput("in", {"ports": ["geometry"]})
    out = await node.execute({"geometry": 1, "segredo_do_pai": 2})

    assert out == {"geometry": 1}


@pytest.mark.asyncio
async def test_input_com_ports_vazio_e_passthrough():
    """Modo 'aceita tudo' — contrato opt-in."""
    from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

    node = SubWorkflowInput("in", {"ports": []})
    out = await node.execute({"a": 1, "b": 2})

    assert out == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_input_aceita_ports_serializado_em_json():
    """O helper da UI grava via JSON.stringify."""
    from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

    node = SubWorkflowInput("in", {"ports": '["geometry"]'})
    out = await node.execute({"geometry": 1, "outro": 2})

    assert out == {"geometry": 1}


@pytest.mark.asyncio
async def test_output_continua_filtrando():
    from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

    node = SubWorkflowOutput("out", {"ports": ["mapa"]})
    out = await node.execute({"mapa": "x", "interno": "y"})

    assert out["__subworkflow_output__"] == {"mapa": "x"}


@pytest.mark.asyncio
async def test_metadados_internos_nunca_atravessam():
    from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

    node = SubWorkflowOutput("out", {"ports": []})
    out = await node.execute({"ok": 1, "__interno__": 2})

    assert out["__subworkflow_output__"] == {"ok": 1}


# ── 4. Pool asyncpg por event loop ───────────────────────────────────────────

async def _async_cache_key(dsn):
    from flow.utils.get_asyncpg_pool import _cache_key
    return _cache_key(dsn)


def test_mesmo_dsn_em_loops_distintos_gera_chaves_distintas():
    """Pool e atrelado ao loop que o criou; reusar em outro quebra com
    'attached to a different loop'.

    Sincrono de proposito: nao da para rodar um segundo loop de dentro de um
    loop ativo, e o cenario real do bug era justamente dois loops separados.
    """
    import asyncio

    dsn = "postgresql://u:p@host/db"
    loop_a = asyncio.new_event_loop()
    loop_b = asyncio.new_event_loop()
    try:
        key_a = loop_a.run_until_complete(_async_cache_key(dsn))
        key_b = loop_b.run_until_complete(_async_cache_key(dsn))
    finally:
        loop_a.close()
        loop_b.close()

    assert key_a[1] == key_b[1] == dsn, "o DSN continua na chave"
    assert key_a[0] != key_b[0], "loops distintos nao podem compartilhar pool"
    assert key_a != key_b


def test_chave_fora_de_loop_nao_quebra():
    from flow.utils.get_asyncpg_pool import _cache_key

    assert _cache_key("postgresql://x")[0] is None
