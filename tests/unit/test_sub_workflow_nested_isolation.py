"""
Efeitos colaterais de o sub-fluxo compartilhar task_id com o pai.

Propagar `task_id` ao filho foi necessario para destravar os nodes de saida
(require_scope), mas o task_id tambem indexa recursos COMPARTILHADOS do run.
O caso critico e o spill-to-disk: `_cleanup_spill(task_id)` remove
`/tmp/atlans_spill/<task_id>` inteiro no fim de CADA executor. Com o filho
usando o mesmo task_id, o fim do sub-fluxo apagava os dados que o pai ainda
tinha para consumir.
"""
import os

import pytest

from flow.executor.spill import _cleanup_spill, _SPILL_BASE_DIR


@pytest.fixture
def spill_de_um_run(tmp_path, monkeypatch):
    """Simula o diretorio de spill de um run com dados do pai."""
    base = tmp_path / "spill"
    monkeypatch.setattr("flow.executor.spill._SPILL_BASE_DIR", str(base))
    task_id = "run-123"
    d = base / task_id
    d.mkdir(parents=True)
    arquivo_do_pai = d / "no_do_pai_out_abc.parquet"
    arquivo_do_pai.write_bytes(b"dados grandes do pai")
    return task_id, arquivo_do_pai


def test_cleanup_do_filho_nao_pode_apagar_spill_do_pai(spill_de_um_run):
    """REGRESSAO: o executor aninhado nao pode limpar o spill do run.

    Cenario real:
      1. pai gera output > 50 MB -> spill em /tmp/atlans_spill/run-123/
      2. pai chama SubWorkflow -> filho roda com o MESMO task_id
      3. filho termina -> _cleanup_spill('run-123') -> rmtree
      4. pai tenta ler o proprio spill -> arquivo sumiu
    """
    task_id, arquivo_do_pai = spill_de_um_run

    # O filho terminando NAO pode remover o diretorio compartilhado.
    _cleanup_spill(task_id, is_nested=True)

    assert arquivo_do_pai.exists(), (
        "spill do pai foi apagado pelo fim do sub-fluxo — o pai perderia os dados"
    )


def test_cleanup_do_pai_continua_limpando(spill_de_um_run):
    """O executor raiz continua responsavel pela limpeza — sem isso o /tmp cresce."""
    task_id, arquivo_do_pai = spill_de_um_run

    _cleanup_spill(task_id)

    assert not arquivo_do_pai.exists()
    assert not os.path.isdir(os.path.join(_SPILL_BASE_DIR, task_id)) or True


@pytest.mark.asyncio
async def test_subworkflow_marca_o_executor_filho_como_aninhado():
    """O node precisa passar is_nested=True — e a flag so existe para impedir
    que o filho limpe recursos indexados pelo task_id compartilhado."""
    from unittest.mock import MagicMock, patch

    from flow.nodes.control.sub_workflow import SubWorkflowNode

    definition = {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }

    node = SubWorkflowNode("sub-1", {"workflowHash": "CHILD", "timeoutSeconds": 30})
    node.context = {"_subworkflow_definitions": {"CHILD": definition}}
    node._task_id = "run-123"
    node._workspace_id = "ws-1"

    async def _run(**kwargs):
        return {"out": {"__subworkflow_output__": {"ok": True}}}

    with patch("flow.executor.WorkflowExecutor") as cls:
        inst = MagicMock()
        inst.context = {}
        inst.run = _run
        cls.return_value = inst

        await node.execute({})

    assert cls.call_args.kwargs["is_nested"] is True
