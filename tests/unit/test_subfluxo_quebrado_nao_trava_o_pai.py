# tests/unit/test_subfluxo_quebrado_nao_trava_o_pai.py
"""
A child that changed no longer locks every save of its parent.

The PUT validated every SubWorkflow reference of the parent on every save. When
the CHILD changed — deactivated, moved to another workspace, an input port
renamed — each save of the parent failed with 422, including saves that did not
touch the SubWorkflow node and the silent save before Executar: the person could
neither keep nor run any edit. Only the references a save creates or changes
are validated now; the run still refuses a broken one, saying why.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.routers import workflows_router as WR
from app.schemas.workflow import WorkflowUpdate


def _definicao(hash_do_filho="filho-1", mapping=None, extra_edges=()):
    return {
        "nodes": [
            {"id": "t", "name": "WebhookTrigger", "type": "trigger", "properties": {}},
            {"id": "sub", "name": "SubWorkflow", "type": "control",
             "properties": {"workflowHash": hash_do_filho, "inputsMapping": mapping or {"focos": "output"}}},
        ],
        "edges": [{"source": "t", "target": "sub", "from_key": "output"}, *extra_edges],
    }


class _User:
    id_hash = "u-1"


@pytest.fixture
def rota(monkeypatch):
    monkeypatch.setattr(WR.limiter, "enabled", False)
    monkeypatch.setattr(WR, "_recusar_segredo", lambda *a, **k: None)

    validadas = []

    async def _filho_desativado(definition, db, workspace_id=None):
        validadas.append([n["id"] for n in definition.get("nodes") or []])
        return ["Node SubWorkflow 'sub' aponta para workflow 'filho-1' que esta desativado."]

    import flow.utils.workflow_contract as contrato
    monkeypatch.setattr(contrato, "validate_subworkflow_references_against_db", _filho_desativado)

    gravadas = []

    class _Service:
        async def update_workflow(self, id_hash, workflow_in, **kw):
            gravadas.append(workflow_in.definition)
            return {"id_hash": id_hash}

    def salvar(salva, nova):
        class _Wf:
            id_hash = "pai"
            workspace_id = "ws-1"
            definition = salva

        return WR.update_workflow(
            request=None, workflow_in=WorkflowUpdate(definition=nova), service=_Service(),
            wf=_Wf(), db=None, current_user=_User(),
        )

    return salvar, validadas, gravadas


async def test_editar_outra_coisa_do_pai_salva_mesmo_com_o_filho_quebrado(rota):
    salvar, validadas, gravadas = rota
    nova = _definicao(extra_edges=[{"source": "sub", "target": "t2", "from_key": "faixa"}])
    await salvar(_definicao(), nova)

    assert validadas == []          # the unchanged reference is not re-validated
    assert gravadas == [nova]


async def test_trocar_o_filho_ainda_e_validado(rota):
    salvar, validadas, gravadas = rota
    with pytest.raises(HTTPException) as exc:
        await salvar(_definicao(), _definicao(hash_do_filho="filho-2"))

    assert exc.value.status_code == 422
    assert validadas == [["sub"]]
    assert gravadas == []


async def test_mudar_o_mapeamento_ainda_e_validado(rota):
    salvar, validadas, _ = rota
    with pytest.raises(HTTPException):
        await salvar(_definicao(), _definicao(mapping={"focos": "outra"}))
    assert validadas == [["sub"]]


async def test_referencia_nova_e_validada(rota):
    salvar, validadas, _ = rota
    sem_subfluxo = {"nodes": [{"id": "t", "name": "WebhookTrigger", "properties": {}}], "edges": []}
    with pytest.raises(HTTPException):
        await salvar(sem_subfluxo, _definicao())
    assert validadas == [["sub"]]
