"""
What the sub-workflow TELLS when something goes wrong.

The six defects covered here had the same shape: execution went on (or stopped)
without saying what actually happened, and the operator went to investigate the
wrong thing. None was a crash — all were silence, or a message that pointed to
the wrong place.
"""
from __future__ import annotations

import pytest

from flow.executor.core import WorkflowExecutor
from flow.nodes.control.sub_workflow import (
    RESULTADO,
    SubWorkflowNode,
    _onde_falhou,
    _SubWorkflowEventPublisher,
)
from flow.utils.workflow_contract import MAX_PROFUNDIDADE


def _filho_valido() -> dict:
    """Minimal definition that passes the contract — Input + Output declared."""
    return {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


def _no(*, workflow_hash="ALVO", inputs_mapping=None, context=None) -> SubWorkflowNode:
    node = SubWorkflowNode(
        node_id="n1",
        parameters={
            "workflowHash": workflow_hash,
            "inputsMapping": inputs_mapping or {},
            "timeoutSeconds": 300,
        },
    )
    node._workspace_id = "ws-1"
    node._task_id = "task-test"
    node.context = dict(context or {})
    return node


# ── 1. mapping pointing to a key that does not arrive ───────────────────────

class TestMapeamentoOrfao:
    """Before: the child's dict received `None` under the key and the run finished green."""

    @pytest.mark.asyncio
    async def test_falha_nomeando_a_chave_que_faltou_e_as_que_chegaram(self):
        node = _no(
            inputs_mapping={"area": "buffer_out"},
            context={"_subworkflow_definitions": {"ALVO": _filho_valido()}},
        )
        with pytest.raises(ValueError) as exc:
            await node.execute({"output": {"x": 1}, "gdf": 2})

        msg = str(exc.value)
        assert "buffer_out" in msg, "não diz qual chave de origem faltou"
        assert "area" in msg, "não diz para qual porta do filho ela ia"
        # Without the list of what arrived, the operator has no way to fix the
        # mapping without guessing names.
        assert "gdf" in msg and "output" in msg

    @pytest.mark.asyncio
    async def test_diz_quando_nada_chegou(self):
        node = _no(
            inputs_mapping={"area": "buffer_out"},
            context={"_subworkflow_definitions": {"ALVO": _filho_valido()}},
        )
        with pytest.raises(ValueError, match="<nenhuma>"):
            await node.execute({})


# ── 2. fluxo que chama a si mesmo ───────────────────────────────────────────

class TestAutoReferenciaDaRaiz:
    """Before: the root was not among the ancestors, so A→A was only caught at the
    SECOND level — after the first had already run the side effects (e-mail
    sent, file published) one extra time."""

    def test_a_raiz_entra_nos_ancestrais(self):
        ex = WorkflowExecutor(
            {"nodes": [], "edges": []},
            task_id="t1",
            workflow_hash="RAIZ",
        )
        assert ex.context["_subflow_ancestors"] == {"RAIZ"}

    def test_sem_hash_o_conjunto_fica_vazio(self):
        # An ad hoc execution (no saved workflow) has nothing to seed, and seeding
        # `None` would make any sub-workflow without a hash hit a false positive.
        ex = WorkflowExecutor({"nodes": [], "edges": []}, task_id="t1")
        assert ex.context["_subflow_ancestors"] == set()

    @pytest.mark.asyncio
    async def test_o_no_barra_a_chamada_a_raiz(self):
        node = _no(workflow_hash="RAIZ", context={"_subflow_ancestors": {"RAIZ"}})
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})


# ── 3. output port with the reserved name ───────────────────────────────────

class TestPortaReservada:
    """Before: the node returned `{RESULTADO: tudo, **tudo}` — a port named
    `subWorkflowResult` overwrote the envelope and whoever read the key got the
    value of that port, with no error."""

    def _definicao(self, portas):
        return {
            "nodes": [
                {"id": "in", "name": "SubWorkflowInput"},
                {"id": "out", "name": "SubWorkflowOutput",
                 "properties": {"ports": portas}},
            ],
            "edges": [],
        }

    def test_recusa_a_porta_reservada(self):
        node = _no()
        with pytest.raises(ValueError, match=RESULTADO):
            node._check_subworkflow_contract("ALVO", self._definicao([RESULTADO]))

    def test_aceita_portas_normais(self):
        node = _no()
        node._check_subworkflow_contract("ALVO", self._definicao(["area", "total"]))



# ── 4. chain deeper than the limit ──────────────────────────────────────────

class TestProfundidade:
    """Before: the server stopped pre-resolving at MAX_PROFUNDIDADE and the node
    said "não existe, está desativado, ou é de outro workspace" (does not exist,
    is deactivated, or belongs to another workspace) — all three false. The
    advice ("re-salve o workflow", re-save the workflow) did not solve it either."""

    @pytest.mark.asyncio
    async def test_diz_que_a_cadeia_estourou(self):
        ancestrais = {f"N{i}" for i in range(MAX_PROFUNDIDADE)}
        node = _no(
            workflow_hash="FUNDO",
            context={"_subflow_ancestors": ancestrais, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError) as exc:
            await node.execute({})

        msg = str(exc.value)
        assert str(MAX_PROFUNDIDADE) in msg and "níveis" in msg
        assert "não foi pré-resolvido" not in msg
        assert "outro workspace" not in msg, "mantém a causa falsa que enganava"

    @pytest.mark.asyncio
    async def test_dentro_do_limite_a_mensagem_continua_a_do_snapshot(self):
        # A short chain with an empty snapshot is a DIFFERENT problem, and the
        # old message is the right one for it.
        node = _no(
            workflow_hash="ALVO",
            context={"_subflow_ancestors": {"A", "B"}, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="pre-resolvido|pré-resolvido"):
            await node.execute({})


# ── 5. which node of the child failed ───────────────────────────────────────

class _ChildFalso:
    def __init__(self, stats):
        self.node_stats = stats


class TestOndeFalhou:
    """Before: "Erro ao executar o sub-workflow 'F': division by zero" — in a
    fifteen-node sub-workflow that pinpoints nothing."""

    def test_nomeia_o_no_que_falhou(self):
        child = _ChildFalso({
            "a": {"status": "completed", "node_name": "Ler"},
            "b": {"status": "failed", "node_name": "PythonScript"},
        })
        onde = _onde_falhou(child)
        assert "PythonScript" in onde and "b" in onde

    def test_vazio_quando_nenhum_no_falhou(self):
        # Timeout/cancellation do not mark a node as failed; inventing a node there
        # would be worse than saying nothing.
        assert _onde_falhou(_ChildFalso({"a": {"status": "completed"}})) == ""

    def test_tolera_child_sem_stats(self):
        assert _onde_falhou(object()) == ""

    def test_cai_no_id_quando_o_no_nao_tem_nome(self):
        assert "b" in _onde_falhou(_ChildFalso({"b": {"status": "failed"}}))


# ── 6. the child's events in the parent's panel ─────────────────────────────

class _PublisherEspiao:
    def __init__(self):
        self.eventos = []

    def publish_event(self, **kwargs):
        self.eventos.append(kwargs)


class TestRepublicacaoDeEventos:

    def test_marca_o_no_pai_para_o_painel_achar_no_canvas(self):
        espiao = _PublisherEspiao()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "filho-3", "started", extra={"node_name": "Buffer"})

        ev = espiao.eventos[0]
        assert ev["node"] == "no-pai::filho-3"
        # It is what the panel row uses to know which canvas node to attach to
        # — without it the row was orphaned and clicking it did nothing.
        assert ev["extra"]["subworkflow_parent_node"] == "no-pai"

    def test_descarta_o_denominador_de_progresso_do_filho(self):
        espiao = _PublisherEspiao()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "filho-3", "started", extra={"nodes_total": 3})
        assert "nodes_total" not in espiao.eventos[0]["extra"]

    def test_nao_repassa_o_fim_do_run_do_filho(self):
        espiao = _PublisherEspiao()
        pub = _SubWorkflowEventPublisher(espiao, "no-pai")
        pub.publish_event("run-1", "__workflow_complete__", "completed")
        assert espiao.eventos == [], "encerraria o run do pai no painel"
