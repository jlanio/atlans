"""
Testes do node SubWorkflow apos o hardening (loop detection, timeout,
mensagens especificas, cancelamento cascata).
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

try:
    from flow.nodes.control.sub_workflow import SubWorkflowNode
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

pytestmark = pytest.mark.skipif(not _AVAILABLE, reason="SubWorkflowNode indisponivel")


def _valid_child_definition() -> dict:
    """Definicao minima de sub-workflow valido (com Input + Output)."""
    return {
        "nodes": [
            {"id": "in",  "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


def _valid_child_final_outputs(public: dict | None = None) -> dict:
    """Simula final_outputs do filho contendo __subworkflow_output__."""
    return {"uuid-out": {"__subworkflow_output__": public if public is not None else {}}}


def _make_node(
    *,
    workflow_hash: str = "TARGET",
    inputs_mapping: dict | None = None,
    timeout_seconds: int = 300,
    workspace_id: str | None = "ws-1",
    context: dict | None = None,
    resolver=None,
) -> SubWorkflowNode:
    """Cria SubWorkflowNode pronto para chamar .execute()."""
    node = SubWorkflowNode(
        node_id="n1",
        parameters={
            "workflowHash": workflow_hash,
            "inputsMapping": inputs_mapping or {},
            "timeoutSeconds": timeout_seconds,
        },
    )
    node._workspace_id = workspace_id
    node._task_id = "task-test"
    # context default popula _subworkflow_definitions via resolver (se passado).
    ctx = dict(context) if context else {}
    if resolver is not None:
        # Resolver retorna a definicao OU levanta ValueError. Populamos o
        # snapshot do envelope simulando o que o servidor faria. Se o resolver
        # levantar, gravamos snapshot vazio — _fetch_definition_from_snapshot
        # vai falhar com "nao foi pre-resolvido pelo servidor" como esperado.
        try:
            snapshot = {workflow_hash: resolver(workflow_hash, workspace_id)}
        except ValueError:
            snapshot = {}
        # Preserva _subworkflow_definitions ja existentes no context (se algum
        # teste setou explicitamente).
        existing = ctx.get("_subworkflow_definitions") or {}
        existing.update(snapshot)
        ctx["_subworkflow_definitions"] = existing
    node.context = ctx
    return node


# ── Loop detection ──────────────────────────────────────────────────────────

class TestLoopDetection:

    @pytest.mark.asyncio
    async def test_detects_direct_self_loop(self):
        """Workflow que tenta chamar a si mesmo (A -> A) falha."""
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"A"}},
        )
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_detects_indirect_loop(self):
        """Cadeia A -> B -> C -> A detectada via set de ancestrais."""
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"B", "C", "A"}},
        )
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_no_loop_when_target_is_new(self):
        """Sem loop -> tenta resolver definicao do snapshot do envelope."""
        # Snapshot vazio: SubWorkflowNode vai falhar com mensagem do snapshot.
        node = _make_node(
            workflow_hash="A",
            context={"_subflow_ancestors": {"B"}, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="nao foi pre-resolvido"):
            await node.execute({})


def _async_run(returns=None, sleep=None, capture=None, capture_flag=False):
    """Dublê de `WorkflowExecutor.run` — corrotina.

    A implementação passou a aguardar `child.run(...)` no MESMO event loop
    (antes: `asyncio.to_thread(run_sync)`, que criava loop novo em thread).
    Com isso o `wait_for` cancela de verdade, então o dublê precisa ser
    cancelável — `asyncio.sleep`, não `time.sleep`.
    """
    async def _run(**kwargs):
        if capture is not None:
            capture.update({"ok": True} if capture_flag else kwargs)
        if sleep:
            await asyncio.sleep(sleep)
        return returns
    return _run


# ── Timeout ─────────────────────────────────────────────────────────────────

class TestTimeout:

    @pytest.mark.asyncio
    async def test_timeout_raises_runtime_error_quickly(self):
        """Sub-workflow que demora mais que timeout falha em ~timeout segundos."""

        def slow_resolver(hash_, ws_id):
            # Retorna definicao minima (vazia) — o WorkflowExecutor com
            # nenhum node termina rapido, mas vamos fazer run() travar
            # via patch abaixo.
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="B",
            timeout_seconds=1,
            resolver=slow_resolver,
        )

        # Patch run() para dormir muito mais que o timeout.
        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(sleep=3)  # > timeout=1s
            mock_executor_cls.return_value = mock_executor

            start = time.monotonic()
            with pytest.raises(RuntimeError, match="excedeu o timeout de 1s"):
                await node.execute({})
            elapsed = time.monotonic() - start

        # Deveria ter levantado em ~1s, nao em ~5s
        assert elapsed < 3.0, f"Timeout demorou demais: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_timeout_de_um_no_do_filho_nao_vira_timeout_do_sub_fluxo(self):
        """O PythonScript do filho levanta o TimeoutError embutido quando o
        script estoura o prazo DELE. Do 3.11 em diante ele é o mesmo
        `asyncio.TimeoutError`, e o erro virava "excedeu o timeout de 300s,
        aumente timeoutSeconds" — o conselho errado. Tem de sair como erro do
        filho, com a causa."""
        node = _make_node(workflow_hash="B", timeout_seconds=300,
                          resolver=lambda h, w: _valid_child_definition())

        async def _run(**kwargs):
            raise TimeoutError("Execução do script excedeu o limite de 1 segundos.")

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _run
            mock_executor_cls.return_value = mock_executor

            with pytest.raises(RuntimeError) as capturado:
                await node.execute({})

        mensagem = str(capturado.value)
        assert "excedeu o timeout de" not in mensagem
        assert "Erro ao executar o sub-workflow 'B'" in mensagem
        assert "excedeu o limite de 1 segundos" in mensagem

    @pytest.mark.asyncio
    async def test_timeout_zero_or_negative_rejected(self):
        node = _make_node(workflow_hash="X", timeout_seconds=0)
        with pytest.raises(ValueError, match="timeoutSeconds"):
            await node.execute({})


# ── Mensagens especificas (fallback DB) ─────────────────────────────────────

class TestMessages:

    @pytest.mark.asyncio
    async def test_hash_not_in_snapshot_raises_helpful_message(self):
        """Hash nao incluido no snapshot do envelope: mensagem orienta operador
        sobre as causas (nao existe / desativado / outro workspace) e sugere
        re-salvar o workflow chamador."""
        node = _make_node(
            workflow_hash="ghost",
            context={"_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="nao foi pre-resolvido pelo servidor"):
            await node.execute({})


# ── Cancelamento cascata ────────────────────────────────────────────────────

class TestCancellation:

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """Cancel da task do pai -> CancelledError nao virá RuntimeError."""

        def slow_resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="C", timeout_seconds=30, resolver=slow_resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(sleep=3)
            mock_executor_cls.return_value = mock_executor

            task = asyncio.create_task(node.execute({}))
            await asyncio.sleep(0.05)  # da chance do to_thread comecar
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task


# ── Inputs mapping ──────────────────────────────────────────────────────────

class TestInputsMapping:

    @pytest.mark.asyncio
    async def test_empty_mapping_passes_all_inputs(self):
        """inputsMapping vazio -> todos os inputs do pai vao para o filho."""
        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="D", inputs_mapping={}, resolver=resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}), capture=captured)
            mock_executor_cls.return_value = mock_executor

            await node.execute({"layer": "data1", "filter": "data2"})

        assert captured["initial_inputs"] == {"layer": "data1", "filter": "data2"}

    @pytest.mark.asyncio
    async def test_mapping_translates_keys(self):
        """inputsMapping {'a': 'src_a'} -> filho recebe 'a' com valor de 'src_a'."""
        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="D",
            inputs_mapping={"sub_in": "parent_out"},
            resolver=resolver,
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}), capture=captured)
            mock_executor_cls.return_value = mock_executor

            await node.execute({"parent_out": "DATA", "other": "IGNORED"})

        assert captured["initial_inputs"] == {"sub_in": "DATA"}


# ── Disabled nodes (snapshot via envelope) ──────────────────────────────────

class TestDisabledNodes:

    @pytest.mark.asyncio
    async def test_child_with_disabled_node_is_blocked(self):
        """Sub-fluxo cuja definicao contem node desabilitado pelo admin falha
        com mensagem clara, ANTES de instanciar o executor."""

        def resolver(hash_, ws_id):
            return {
                "nodes": [
                    {"id": "n1", "name": "WebhookTrigger"},
                    {"id": "n2", "name": "SendEmail"},  # desabilitado
                ],
                "edges": [],
            }

        node = _make_node(
            workflow_hash="CHILD",
            resolver=resolver,
            context={"_disabled_nodes": {"SendEmail"}},
        )

        with pytest.raises(ValueError, match="SendEmail"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_child_without_disabled_nodes_runs(self):
        """Snapshot vazio nao bloqueia nada."""

        captured: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="CHILD",
            resolver=resolver,
            context={"_disabled_nodes": set()},
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"r": 1}), capture=captured, capture_flag=True)
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        assert captured.get("ok") is True
        assert result["r"] == 1

    @pytest.mark.asyncio
    async def test_disabled_nodes_snapshot_propagates_to_grandchild(self):
        """Cadeia A→B→C: snapshot do envelope do servidor (em A) deve chegar
        ao executor de B, que por sua vez propaga para C."""
        injected_context: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="B",
            resolver=resolver,
            context={
                "_disabled_nodes": {"SendEmail"},
                "_subflow_ancestors": {"A"},
            },
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = injected_context
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            await node.execute({})

        # O sub-executor (de B) recebeu o snapshot. Quando ele instanciar
        # outro SubWorkflow para C, este vai validar contra esse set.
        assert injected_context.get("_disabled_nodes") == {"SendEmail"}


# ── Ancestor propagation ────────────────────────────────────────────────────

class TestAncestorPropagation:

    @pytest.mark.asyncio
    async def test_child_executor_inherits_ancestors_plus_self(self):
        """Filho recebe set de ancestrais com o hash atual incluido."""
        injected_context: dict = {}

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(
            workflow_hash="LEAF",
            resolver=resolver,
            context={"_subflow_ancestors": {"ROOT", "MID"}},
        )

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = injected_context
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            await node.execute({})

        ancestors = injected_context.get("_subflow_ancestors")
        assert ancestors == {"ROOT", "MID", "LEAF"}


# ── Validacoes basicas ──────────────────────────────────────────────────────

class TestBasicValidation:

    @pytest.mark.asyncio
    async def test_missing_workflow_hash_raises(self):
        node = _make_node(workflow_hash="")
        with pytest.raises(ValueError, match="workflowHash"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_non_dict_inputs_mapping_raises(self):
        """List em inputsMapping e rejeitada (pelo validate() do BaseNode antes
        do check custom do node — ambos resultam em ValueError com 'inputsMapping')."""
        node = SubWorkflowNode(
            node_id="n1",
            parameters={
                "workflowHash": "A",
                "inputsMapping": ["not", "a", "dict"],
                "timeoutSeconds": 60,
            },
        )
        node.context = {}
        with pytest.raises((ValueError, TypeError), match="inputsMapping"):
            await node.execute({})


# ── Contrato de saida via SubWorkflowOutput ─────────────────────────────────

class TestSubWorkflowOutputContract:
    """Quando o workflow filho usa SubWorkflowOutput, o pai recebe outputs
    com chaves nomeadas (utilizaveis no canvas) em vez do dict de UUIDs."""

    @pytest.mark.asyncio
    async def test_uses_subworkflow_output_when_present(self):
        """final_outputs do filho contem __subworkflow_output__: usa esse dict."""

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="CHILD", resolver=resolver)

        # Simula execucao: child final_outputs com 2 nodes — um deles tem
        # __subworkflow_output__.
        child_final_outputs = {
            "uuid-wfs": {"output": "<gdf>"},
            "uuid-output-node": {"__subworkflow_output__": {"focos": "<gdf>", "total": 26}},
        }

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=child_final_outputs)
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        # subWorkflowResult deve ser o dict PUBLICO (nao final_outputs cru)
        assert result["subWorkflowResult"] == {"focos": "<gdf>", "total": 26}
        # Chaves nomeadas spread
        assert result["focos"] == "<gdf>"
        assert result["total"] == 26
        # UUIDs do final_outputs NAO devem vazar
        assert "uuid-wfs" not in result
        assert "uuid-output-node" not in result

    @pytest.mark.asyncio
    async def test_raises_when_output_node_didnt_run(self):
        """Contrato passa (definition tem SubWorkflowOutput) mas o node nao
        executou (branch excluiu) — RuntimeError explicativo."""

        def resolver(hash_, ws_id):
            return _valid_child_definition()

        node = _make_node(workflow_hash="NORUN", resolver=resolver)

        # Simula final_outputs SEM __subworkflow_output__ (output node ficou de fora)
        child_final_outputs = {"uuid-wfs": {"output": "<gdf>"}}

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=child_final_outputs)
            mock_executor_cls.return_value = mock_executor

            with pytest.raises(RuntimeError, match="SubWorkflowOutput nao foi executado"):
                await node.execute({})

    @pytest.mark.asyncio
    async def test_subworkflow_output_node_strips_internal_keys(self):
        """SubWorkflowOutput nao deve vazar chaves __artifact__ / __response__
        para o caller — sao metadados internos do node anterior."""
        from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

        node = SubWorkflowOutput(node_id="out", parameters={})
        result = await node.execute({
            "focos": "<gdf>",
            "__artifact__": {"s3_key": "x"},
            "__response__": {"status": 200},
            "outro": 42,
        })

        public = result["__subworkflow_output__"]
        assert public == {"focos": "<gdf>", "outro": 42}
        assert "__artifact__" not in public
        assert "__response__" not in public

    @pytest.mark.asyncio
    async def test_subworkflow_output_empty_inputs(self):
        """Node sem inputs conectados: retorna dict publico vazio."""
        from flow.nodes.outputs.sub_workflow_output import SubWorkflowOutput

        node = SubWorkflowOutput(node_id="out", parameters={})
        result = await node.execute({})
        assert result == {"__subworkflow_output__": {}}


# ── Contrato: SubWorkflowOutput obrigatorio, SubWorkflowInput opcional ──────

class TestSubWorkflowContract:
    """Só a SAÍDA é obrigatória.

    SubWorkflowOutput define o valor de retorno — sem ele o pai não tem o que
    consumir, e não adotamos o "último node executado" do n8n (implícito e
    ambíguo com ramos). Já SubWorkflowInput é opcional: um sub-fluxo pode não
    receber nada (fonte fixa, parâmetros internos), e exigi-lo era burocracia.
    """

    @pytest.mark.asyncio
    async def test_missing_input_is_allowed(self):
        """Sub-fluxo sem entry point roda — só não recebe dados do pai."""
        def resolver(hash_, ws_id):
            return {
                "nodes": [{"id": "out", "name": "SubWorkflowOutput"}],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)

        with patch("flow.executor.WorkflowExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor.context = {}
            mock_executor.run = _async_run(returns=_valid_child_final_outputs({"ok": True}))
            mock_executor_cls.return_value = mock_executor

            result = await node.execute({})

        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_multiple_outputs_raises(self):
        """Dois SubWorkflowOutput tornam o retorno ambíguo: extract_contract une
        as portas de todos, mas collect_subworkflow_output devolve o primeiro."""
        def resolver(hash_, ws_id):
            return {
                "nodes": [
                    {"id": "in", "name": "SubWorkflowInput"},
                    {"id": "out1", "name": "SubWorkflowOutput"},
                    {"id": "out2", "name": "SubWorkflowOutput"},
                ],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError, match="Apenas um e permitido"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_missing_output_raises(self):
        def resolver(hash_, ws_id):
            return {
                "nodes": [{"id": "in", "name": "SubWorkflowInput"}],
                "edges": [],
            }

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError, match="SubWorkflowOutput"):
            await node.execute({})

    @pytest.mark.asyncio
    async def test_missing_both_reports_only_output(self):
        """Sem nenhum dos dois, o erro cita só o que de fato falta: a saída."""
        def resolver(hash_, ws_id):
            return {"nodes": [{"id": "wfs", "name": "WFS"}], "edges": []}

        node = _make_node(workflow_hash="X", resolver=resolver)
        with pytest.raises(ValueError) as exc_info:
            await node.execute({})
        assert "SubWorkflowOutput" in str(exc_info.value)
        assert "SubWorkflowInput" not in str(exc_info.value)


# ── SubWorkflowInput (trigger) ──────────────────────────────────────────────

class TestSubWorkflowInputNode:

    @pytest.mark.asyncio
    async def test_exposes_inputs_as_outputs(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        result = await node.execute({"focos": "<gdf>", "bbox": "BBOX"})
        assert result == {"focos": "<gdf>", "bbox": "BBOX"}

    @pytest.mark.asyncio
    async def test_strips_internal_keys(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        result = await node.execute({
            "focos": "<gdf>",
            "__artifact__": {"x": 1},
        })
        assert result == {"focos": "<gdf>"}

    @pytest.mark.asyncio
    async def test_empty_inputs_returns_empty(self):
        from flow.nodes.trigger.sub_workflow_input import SubWorkflowInput

        node = SubWorkflowInput(node_id="in", parameters={})
        assert await node.execute({}) == {}
