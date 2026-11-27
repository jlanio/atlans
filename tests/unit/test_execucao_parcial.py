"""
"Executar até este nó" (app/services/execucao_parcial.py): the server cuts the
definition down to the target node and its ancestors before the dispatch.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import WorkflowInputValidationError
from app.services.execucao_parcial import ate_o_no


def _definicao():
    #   gatilho → wfs → buffer → salvar
    #                ↘ filtro ↗        (filtro also feeds buffer)
    #   outro (no edges), email ← salvar
    nos = ["gatilho", "wfs", "filtro", "buffer", "salvar", "email", "outro"]
    arestas = [
        ("gatilho", "wfs"), ("wfs", "buffer"), ("wfs", "filtro"),
        ("filtro", "buffer"), ("buffer", "salvar"), ("salvar", "email"),
    ]
    return {
        "nodes": [{"id": n, "name": n} for n in nos],
        "edges": [{"id": f"{a}-{b}", "source": a, "target": b} for a, b in arestas],
        "settings": {"timeout": 30},
    }


def test_mantem_o_no_e_todos_os_ancestrais_e_nada_depois():
    podada = ate_o_no(_definicao(), "buffer")
    assert {n["id"] for n in podada["nodes"]} == {"gatilho", "wfs", "filtro", "buffer"}
    assert {e["id"] for e in podada["edges"]} == {"gatilho-wfs", "wfs-buffer", "wfs-filtro", "filtro-buffer"}
    assert podada["settings"] == {"timeout": 30}


def test_o_proprio_gatilho_roda_sozinho():
    podada = ate_o_no(_definicao(), "gatilho")
    assert [n["id"] for n in podada["nodes"]] == ["gatilho"]
    assert podada["edges"] == []


def test_nao_altera_a_definicao_original():
    original = _definicao()
    ate_o_no(original, "wfs")
    assert len(original["nodes"]) == 7 and len(original["edges"]) == 6


def test_arestas_orfas_ou_quebradas_sao_ignoradas():
    d = _definicao()
    d["edges"] += [{"source": "fantasma", "target": "buffer"}, {"target": "buffer"}, None]
    podada = ate_o_no(d, "buffer")
    assert {n["id"] for n in podada["nodes"]} == {"gatilho", "wfs", "filtro", "buffer"}
    assert len(podada["edges"]) == 4


def test_no_inexistente_e_422():
    with pytest.raises(WorkflowInputValidationError):
        ate_o_no(_definicao(), "nao-existe")


@pytest.mark.asyncio
async def test_start_analysis_despacha_so_a_definicao_podada():
    from app.services.workflow_service import DispatchResult, WorkflowService
    from app.models.workflow import Workflow
    from app.crud.workflow_crud import WorkflowCRUD
    from unittest.mock import MagicMock

    db = AsyncMock()
    svc = WorkflowService(db)
    svc.crud = AsyncMock(spec=WorkflowCRUD)
    svc.crud.db = db
    wf = Workflow(name="wf", definition=_definicao(), flag_ative=True)
    wf.id_hash, wf.workspace_id = "wf-1", "ws-1"
    wf.pinned_outputs = wf.pin_metadata = None
    svc._load_workflow = AsyncMock(return_value=(wf, _definicao()))
    svc._resolve_candidates = AsyncMock(return_value=[MagicMock(id_hash="ag-1", public_key="PEM")])
    capturado = {}

    async def _despacho(wf_, definition, *a, **k):
        capturado["definition"] = definition
        return DispatchResult(id="task-1")

    svc._dispatch_job = _despacho
    with patch("app.services.disabled_nodes_service.disabled_names", new=AsyncMock(return_value=set())), \
         patch("flow.utils.workflow_contract.collect_subworkflow_definitions_recursive", new=AsyncMock(return_value={})):
        await svc.start_analysis("wf-1", autenticar_entrada=False, run_until="filtro")

    assert {n["id"] for n in capturado["definition"]["nodes"]} == {"gatilho", "wfs", "filtro"}
