"""
O que o sub-fluxo CONTA quando algo dá errado.

Os seis defeitos cobertos aqui tinham o mesmo formato: a execução seguia (ou
parava) sem dizer o que de fato aconteceu, e o operador ia investigar a coisa
errada. Nenhum era um crash — todos eram silêncio, ou uma mensagem que apontava
para o lugar errado.
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
    """Definição mínima que passa no contrato — Input + Output declarados."""
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


# ── 1. mapeamento apontando para chave que não chega ────────────────────────

class TestMapeamentoOrfao:
    """Antes: o dict do filho recebia `None` na chave e o run terminava verde."""

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
        # Sem a lista do que chegou, o operador não tem como corrigir o
        # mapeamento sem sair adivinhando nomes.
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
    """Antes: a raiz não constava dos ancestrais, então A→A só era pego no
    SEGUNDO nível — depois de o primeiro já ter rodado os efeitos colaterais
    (e-mail enviado, arquivo publicado) uma vez a mais."""

    def test_a_raiz_entra_nos_ancestrais(self):
        ex = WorkflowExecutor(
            {"nodes": [], "edges": []},
            task_id="t1",
            workflow_hash="RAIZ",
        )
        assert ex.context["_subflow_ancestors"] == {"RAIZ"}

    def test_sem_hash_o_conjunto_fica_vazio(self):
        # Execução avulsa (sem workflow salvo) não tem o que semear, e semear
        # `None` faria qualquer sub-fluxo sem hash bater falso-positivo.
        ex = WorkflowExecutor({"nodes": [], "edges": []}, task_id="t1")
        assert ex.context["_subflow_ancestors"] == set()

    @pytest.mark.asyncio
    async def test_o_no_barra_a_chamada_a_raiz(self):
        node = _no(workflow_hash="RAIZ", context={"_subflow_ancestors": {"RAIZ"}})
        with pytest.raises(ValueError, match="Loop detectado"):
            await node.execute({})


# ── 3. porta de saída com o nome reservado ──────────────────────────────────

class TestPortaReservada:
    """Antes: o node devolvia `{RESULTADO: tudo, **tudo}` — uma porta chamada
    `subWorkflowResult` sobrescrevia o envelope e quem lesse a chave recebia o
    valor daquela porta, sem erro."""

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



# ── 4. cadeia mais funda que o limite ───────────────────────────────────────

class TestProfundidade:
    """Antes: o servidor parava de pré-resolver em MAX_PROFUNDIDADE e o node
    dizia "não existe, está desativado, ou é de outro workspace" — as três
    falsas. O conselho ("re-salve o workflow") também não resolvia."""

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
        # Uma cadeia curta com o snapshot vazio é um problema DIFERENTE, e a
        # mensagem antiga é a certa para ele.
        node = _no(
            workflow_hash="ALVO",
            context={"_subflow_ancestors": {"A", "B"}, "_subworkflow_definitions": {}},
        )
        with pytest.raises(ValueError, match="pre-resolvido|pré-resolvido"):
            await node.execute({})


# ── 5. qual nó do filho falhou ──────────────────────────────────────────────

class _ChildFalso:
    def __init__(self, stats):
        self.node_stats = stats


class TestOndeFalhou:
    """Antes: "Erro ao executar o sub-workflow 'F': division by zero" — num
    sub-fluxo de quinze nós isso não localiza nada."""

    def test_nomeia_o_no_que_falhou(self):
        child = _ChildFalso({
            "a": {"status": "completed", "node_name": "Ler"},
            "b": {"status": "failed", "node_name": "PythonScript"},
        })
        onde = _onde_falhou(child)
        assert "PythonScript" in onde and "b" in onde

    def test_vazio_quando_nenhum_no_falhou(self):
        # Timeout/cancelamento não marcam nó como failed; inventar um nó ali
        # seria pior que não dizer nada.
        assert _onde_falhou(_ChildFalso({"a": {"status": "completed"}})) == ""

    def test_tolera_child_sem_stats(self):
        assert _onde_falhou(object()) == ""

    def test_cai_no_id_quando_o_no_nao_tem_nome(self):
        assert "b" in _onde_falhou(_ChildFalso({"b": {"status": "failed"}}))


# ── 6. eventos do filho no painel do pai ────────────────────────────────────

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
        # É o que a linha do painel usa para saber a qual nó do canvas se
        # amarrar — sem isso ela ficava órfã e clicar nela não fazia nada.
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
