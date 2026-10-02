# tests/integration/test_executor_integration.py
"""
Testes de integração para flow/executor.py.
Cobrem o fluxo completo de execução: encadeamento de nós, paralelismo,
renderização Jinja2, publicação de eventos, erros e liberação de memória (M5).

Estes testes documentam o comportamento atual e servem como rede de
segurança para a refatoração do executor em múltiplos módulos.
"""
import asyncio
from unittest.mock import MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_node(node_id, alias=None, strategy="first", extra_props=None):
    """Cria definição de nó Merge com os parâmetros fornecidos."""
    props = {"strategy": strategy}
    if alias:
        props["alias"] = alias
    if extra_props:
        props.update(extra_props)
    return {"id": node_id, "type": "control", "name": "Merge", "properties": props}


def make_edge(source, target, from_key=None, to_key=None):
    """Cria definição de aresta."""
    edge = {"source": source, "target": target}
    if from_key:
        edge["from_key"] = from_key
    if to_key:
        edge["to_key"] = to_key
    return edge


def make_workflow(nodes, edges):
    """Cria definição de workflow."""
    return {"nodes": nodes, "edges": edges}


def make_publisher():
    """Cria mock de publisher com coleta de eventos."""
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    return publisher


def executar(definition, task_id, publisher):
    """Roda o workflow como o executor de produção (executor/job_executor.py):
    `run()` no loop e, com ou sem falha, os node_stats do que chegou a rodar.

    Devolve (status, erro, node_stats), com status "success" ou "failed".
    """
    from flow.executor import WorkflowExecutor

    executor = WorkflowExecutor(definition, task_id=task_id, publisher=publisher)
    try:
        asyncio.run(executor.run(initial_inputs={}))
    except Exception as exc:
        return "failed", str(exc), executor.node_stats
    return "success", None, executor.node_stats


# ── Encadeamento de nós ───────────────────────────────────────────────────────

class TestEncadeamento:
    """Execução de workflow com nós encadeados linearmente."""

    def test_tres_nos_em_cadeia_todos_executam(self):
        """Workflow A→B→C deve executar os 3 nós com status 'completed'."""
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node("node-b", alias="NodeB"),
                make_node("node-c", alias="NodeC"),
            ],
            edges=[
                make_edge("node-a", "node-b", from_key="output", to_key="output"),
                make_edge("node-b", "node-c", from_key="output", to_key="output"),
            ],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-chain-001",
            publisher=make_publisher(),
        )

        assert status == "success", f"Esperado 'success', obtido '{status}': {error}"
        for node_id in ["node-a", "node-b", "node-c"]:
            assert node_id in stats, f"{node_id} não está em node_stats"
            assert stats[node_id]["status"] == "completed"

    def test_cadeia_respeita_ordem_topologica(self):
        """Na cadeia A→B, a ordem topológica deve colocar A antes de B."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-order-001", publisher=make_publisher()
        )
        order = executor.execution_order

        assert order.index("node-a") < order.index("node-b"), (
            "node-a deve preceder node-b na ordem topológica"
        )

    def test_output_de_no_intermediario_flui_para_filho(self):
        """Output de A deve chegar como input em B via aresta."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b", strategy="all")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="entrada")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-flow-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        # node-b recebe 'entrada' de node-a; com strategy='all', o output é
        # {'output': {'entrada': <valor>}}, confirmando que o input chegou
        b_output = executor.final_outputs.get("node-b", {})
        assert "output" in b_output, "node-b deve ter produzido um output"
        # O valor mapeado ('entrada') deve estar presente no dict retornado por 'all'
        merged = b_output.get("output")
        if isinstance(merged, dict):
            assert "entrada" in merged, (
                "Com strategy='all', o output de node-b deve conter a chave 'entrada'"
            )


# ── Renderização Jinja2 ───────────────────────────────────────────────────────

class TestJinja2Renderizacao:
    """Renderização de parâmetros via Jinja2 durante execução real."""

    def test_expressao_jinja2_renderizada_no_parametro(self):
        """Parâmetro com expressão Jinja2 deve ser resolvido antes da execução do nó."""
        # strategy renderiza para 'last' via Jinja2
        # Se a renderização NÃO acontecer, o nó recebe "{{ 'la' + 'st' }}"
        # (inválido), levanta ValueError e o workflow falha.
        definition = make_workflow(
            nodes=[make_node("node-jinja", strategy="{{ 'la' + 'st' }}")],
            edges=[],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-jinja-001",
            publisher=make_publisher(),
        )

        assert status == "success", (
            f"Expressão Jinja2 não foi renderizada corretamente: {error}"
        )

    def test_jinja2_acessa_inputs_do_no(self):
        """Parâmetro de node-b pode referenciar 'inputs' (dados vindos via aresta)."""
        # node-b recebe 'output' de node-a via aresta.
        # A estratégia é: se inputs.output for None → 'last', caso contrário usa o valor.
        # Como node-a retorna {'output': None}, strategy deve renderizar para 'last'.
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node("node-b", strategy="{{ inputs.output or 'last' }}"),
            ],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-jinja-inputs-001",
            publisher=make_publisher(),
        )

        assert status == "success", (
            f"Renderização de 'inputs' via Jinja2 falhou: {error}"
        )
        assert stats["node-b"]["status"] == "completed"

    def test_m5_libera_named_antes_da_renderizacao(self):
        """
        M5 libera outputs (e remove de 'named') durante a preparação de inputs,
        ANTES do asyncio.gather iniciar os coroutines. Portanto, 'named.NodeA'
        NÃO está disponível quando node-b renderiza seus parâmetros.
        Este teste documenta esse comportamento atual.
        """
        # Se named.NodeA estivesse disponível, strategy renderizaria para 'all'
        # (válido). Como não está, a expressão falha com UndefinedError e o
        # executor retorna status 'failed'.
        definition = make_workflow(
            nodes=[
                make_node("node-a", alias="NodeA"),
                make_node(
                    "node-b",
                    strategy="{{ named.NodeA.output }}",
                ),
            ],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-m5-named-001",
            publisher=make_publisher(),
        )

        # M5 libera 'NodeA' antes do render → expressão falha
        assert status == "failed", (
            "M5 deve liberar named.NodeA antes da renderização — "
            "expressão deve falhar com UndefinedError"
        )


# ── Publicação de eventos ────────────────────────────────────────────────────

class TestPublicacaoDeEventos:
    """Verificação de que eventos corretos são publicados durante a execução."""

    def test_started_e_completed_publicados_por_no(self):
        """Cada nó deve gerar ao menos um evento 'started' e um 'completed'."""
        publisher = make_publisher()
        eventos = []

        def captura(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = captura

        status, _, _ = executar(
            definition=make_workflow(
                nodes=[make_node("no-x"), make_node("no-y")],
                edges=[make_edge("no-x", "no-y", from_key="output", to_key="output")],
            ),
            task_id="test-eventos-001",
            publisher=publisher,
        )

        assert status == "success"
        for node_id in ["no-x", "no-y"]:
            statuses = {e["status"] for e in eventos if e["node"] == node_id}
            assert "started" in statuses, f"Evento 'started' ausente para {node_id}"
            assert "completed" in statuses, f"Evento 'completed' ausente para {node_id}"

    def test_started_antecede_completed_para_cada_no(self):
        """Para cada nó, 'started' deve ser publicado antes de 'completed'."""
        publisher = make_publisher()
        eventos = []

        def captura(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = captura

        executar(
            definition=make_workflow(nodes=[make_node("no-seq")], edges=[]),
            task_id="test-seq-001",
            publisher=publisher,
        )

        eventos_no = [e for e in eventos if e["node"] == "no-seq"]
        statuses = [e["status"] for e in eventos_no]

        assert "started" in statuses and "completed" in statuses
        assert statuses.index("started") < statuses.index("completed"), (
            "'started' deve anteceder 'completed'"
        )

    def test_publisher_chamado_pelo_menos_uma_vez_por_no(self):
        """Número de chamadas ao publisher deve ser >= número de nós."""
        publisher = make_publisher()
        n_nos = 3

        executar(
            definition=make_workflow(
                nodes=[make_node(f"no-{i}") for i in range(n_nos)],
                edges=[],
            ),
            task_id="test-calls-001",
            publisher=publisher,
        )

        assert publisher.publish_event.call_count >= n_nos, (
            "Publisher deve ser chamado ao menos uma vez por nó"
        )


# ── Execução paralela ────────────────────────────────────────────────────────

class TestParalelismo:
    """Nós sem dependências entre si devem poder executar em paralelo."""

    def test_diamante_todos_nos_executam(self):
        """Workflow A→[B,C]→D deve executar os 4 nós com sucesso."""
        definition = make_workflow(
            nodes=[
                make_node("node-a"),
                make_node("node-b"),
                make_node("node-c"),
                make_node("node-d", strategy="all"),
            ],
            edges=[
                make_edge("node-a", "node-b", from_key="output", to_key="b_in"),
                make_edge("node-a", "node-c", from_key="output", to_key="c_in"),
                make_edge("node-b", "node-d", from_key="output", to_key="b_out"),
                make_edge("node-c", "node-d", from_key="output", to_key="c_out"),
            ],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-diamond-001",
            publisher=make_publisher(),
        )

        assert status == "success", f"Falha no workflow em diamante: {error}"
        for node_id in ["node-a", "node-b", "node-c", "node-d"]:
            assert node_id in stats, f"{node_id} não foi executado"
            assert stats[node_id]["status"] == "completed"

    def test_diamante_ordem_topologica_correta(self):
        """D deve aparecer após B e C na ordem topológica do diamante."""
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node(n) for n in ["node-a", "node-b", "node-c", "node-d"]],
            edges=[
                make_edge("node-a", "node-b"),
                make_edge("node-a", "node-c"),
                make_edge("node-b", "node-d"),
                make_edge("node-c", "node-d"),
            ],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-diamond-order", publisher=make_publisher()
        )
        idx = {n: executor.execution_order.index(n) for n in ["node-a", "node-b", "node-c", "node-d"]}

        assert idx["node-a"] < idx["node-b"], "A deve preceder B"
        assert idx["node-a"] < idx["node-c"], "A deve preceder C"
        assert idx["node-b"] < idx["node-d"], "B deve preceder D"
        assert idx["node-c"] < idx["node-d"], "C deve preceder D"


# ── Tratamento de erros ───────────────────────────────────────────────────────

class TestTratamentoDeErros:
    """Comportamento do executor quando um nó falha."""

    def test_no_invalido_retorna_status_failed(self):
        """Nó com strategy inválida deve falhar e retornar status 'failed'."""
        definition = make_workflow(
            nodes=[make_node("node-ruim", strategy="invalida")],
            edges=[],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-error-001",
            publisher=make_publisher(),
        )

        assert status == "failed", "Esperado status 'failed' para nó com erro"
        assert error is not None
        assert stats["node-ruim"]["status"] == "failed"
        assert stats["node-ruim"]["error"] is not None

    def test_erro_em_no_intermediario_stats_do_antecessor_preservados(self):
        """Quando B falha (A→B), os stats de A (que completou) devem estar presentes."""
        definition = make_workflow(
            nodes=[
                make_node("node-ok"),
                make_node("node-fail", strategy="invalida"),
            ],
            edges=[make_edge("node-ok", "node-fail", from_key="output", to_key="output")],
        )

        status, error, stats = executar(
            definition=definition,
            task_id="test-partial-001",
            publisher=make_publisher(),
        )

        assert status == "failed"
        assert "node-ok" in stats
        assert stats["node-ok"]["status"] == "completed", (
            "node-ok completou antes da falha — stats devem ser preservados"
        )
        assert stats["node-fail"]["status"] == "failed"

    def test_erro_publica_evento_completed_com_status_failed(self):
        """Quando um nó falha, um evento 'completed' com a falha deve ser publicado."""
        publisher = make_publisher()
        eventos = []

        def captura(run_id, node, status, *args, **kwargs):
            eventos.append({"node": node, "status": status})

        publisher.publish_event.side_effect = captura

        executar(
            definition=make_workflow(
                nodes=[make_node("node-ruim", strategy="invalida")],
                edges=[],
            ),
            task_id="test-error-events-001",
            publisher=publisher,
        )

        eventos_no = [e for e in eventos if e["node"] == "node-ruim"]
        statuses = [e["status"] for e in eventos_no]
        assert "started" in statuses, "Evento 'started' ausente mesmo em nó que falha"
        assert "failed" in statuses, "Evento 'failed'/'completed' ausente para nó que falha"


# ── Liberação de memória (M5) ────────────────────────────────────────────────

class TestLiberacaoDeMemoria:
    """Otimização M5: outputs de nós são liberados após consumo pelos filhos."""

    def test_outputs_intermediarios_liberados_de_all_node_outputs(self):
        """
        Após execução de A→B, all_node_outputs de A deve ser liberado
        (B consumiu os dados de A, acionando _free_node_outputs).
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-m5-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.all_node_outputs["node-a"]["outputs"] == {}, (
            "M5: outputs de node-a devem ser liberados após node-b consumir"
        )

    def test_final_outputs_preservados_apos_liberacao_m5(self):
        """
        final_outputs deve conter os valores originais mesmo após
        all_node_outputs ser limpo por M5.
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(
            nodes=[make_node("node-a"), make_node("node-b")],
            edges=[make_edge("node-a", "node-b", from_key="output", to_key="output")],
        )

        executor = WorkflowExecutor(
            definition, task_id="test-m5-002", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        # final_outputs não é afetado pela liberação de all_node_outputs
        assert "output" in executor.final_outputs["node-a"], (
            "final_outputs deve preservar output de node-a mesmo após M5"
        )
        assert "output" in executor.final_outputs["node-b"], (
            "final_outputs deve preservar output de node-b mesmo após M5"
        )

    def test_no_folha_sem_filhos_tambem_e_liberado(self):
        """
        Nó folha (sem filhos) também deve ter outputs liberados após execução
        (remaining_consumers == 0 → _free_node_outputs chamado).
        """
        from flow.executor import WorkflowExecutor

        definition = make_workflow(nodes=[make_node("node-isolado")], edges=[])

        executor = WorkflowExecutor(
            definition, task_id="test-m5-leaf-001", publisher=make_publisher()
        )
        asyncio.run(executor.run(initial_inputs={}))

        assert executor.all_node_outputs["node-isolado"]["outputs"] == {}, (
            "M5: nó folha deve ter outputs liberados ao final da execução"
        )
