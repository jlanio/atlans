"""
Regression: WorkflowService.start_analysis needs to include disabled_nodes and
subworkflow_definitions in the job envelope. Before the fix, this path (used by
POST /workflows/.../execute, webhook and the cron schedule) sent an empty
envelope to the executor, and SubWorkflows failed with 'nao foi pre-
resolvido pelo servidor' (was not pre-resolved by the server).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workflow_service import WorkflowService, DispatchResult


def _make_workflow_with_subworkflow(child_hash: str = "child-1") -> MagicMock:
    """Simple workflow A with a SubWorkflow pointing to child_hash."""
    wf = MagicMock()
    wf.id_hash = "parent-A"
    wf.workspace_id = "ws-test"
    wf.flag_ative = True
    wf.pinned_outputs = None
    wf.pin_metadata = None
    wf.definition = {
        "nodes": [
            {
                "id": "trigger-1",
                "name": "WebhookTrigger",
                "properties": {},
            },
            {
                "id": "sub-1",
                "name": "SubWorkflow",
                "properties": {"workflowHash": child_hash, "inputsMapping": {}},
            },
        ],
        "edges": [],
    }
    return wf


def _make_child_workflow(hash_: str = "child-1") -> MagicMock:
    """Workflow B minimo com contrato declarado."""
    wf = MagicMock()
    wf.id_hash = hash_
    wf.workspace_id = "ws-test"
    wf.flag_ative = True
    wf.definition = {
        "nodes": [
            {"id": "in",  "name": "SubWorkflowInput"},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }
    return wf


@pytest.mark.asyncio
async def test_start_analysis_includes_subworkflow_definitions_in_dispatch():
    """The critical fix: start_analysis needs to collect the child's definition
    and pass it to _dispatch_job."""
    parent = _make_workflow_with_subworkflow("child-1")
    child = _make_child_workflow("child-1")

    captured_dispatch_kwargs: dict = {}

    # Mock of db.execute: it needs to be an AsyncMock, returning an object with
    # .scalars().all() = [child]
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[child])
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=scalars_mock)

    db = MagicMock()
    db.execute = AsyncMock(return_value=result_mock)

    # WorkflowService receives `db` and creates WorkflowCRUD internally.
    # We mock service.crud after instantiation to point to our db.
    service = WorkflowService(db)
    service.crud = MagicMock(db=db)

    # Mock of the wrappers that delegate to workflow_execution_service
    service._load_workflow = AsyncMock(return_value=(parent, parent.definition))
    service._resolve_candidates = AsyncMock(return_value=[MagicMock()])

    # Mock of _dispatch_job to capture the kwargs
    service._dispatch_job = AsyncMock(side_effect=lambda *a, **kw: captured_dispatch_kwargs.update(kw) or DispatchResult(id="task-123"))

    # Mock disabled_names to return an empty set (no disabled nodes)
    with patch("app.services.disabled_nodes_service.disabled_names",
               new=AsyncMock(return_value=set())):
        with patch(
            "app.services.workflow_service.resolve_credentials_from_ids",
            new=AsyncMock(return_value={}),
        ):
            with patch(
                "app.services.workflow_service._validate_trigger_credentials_only",
                new=AsyncMock(),
            ):
                result = await service.start_analysis(parent.id_hash, inputs={})

    # Assercoes
    assert result.id == "task-123"
    assert "subworkflow_definitions" in captured_dispatch_kwargs, \
        "_dispatch_job nao recebeu subworkflow_definitions"
    assert "disabled_nodes" in captured_dispatch_kwargs, \
        "_dispatch_job nao recebeu disabled_nodes"

    # The child's definition must have been collected and passed
    subdefs = captured_dispatch_kwargs["subworkflow_definitions"]
    assert "child-1" in subdefs, (
        f"subworkflow_definitions deveria conter 'child-1'. Recebido: {list(subdefs.keys())}"
    )


@pytest.mark.asyncio
async def test_start_analysis_with_no_subworkflows_passes_empty_dict():
    """Workflow without a SubWorkflow: subworkflow_definitions should be an empty
    dict (not None) so as not to break the contract with the executor."""
    wf = MagicMock()
    wf.id_hash = "simple-wf"
    wf.workspace_id = "ws-test"
    wf.flag_ative = True
    wf.pinned_outputs = None
    wf.pin_metadata = None
    wf.definition = {
        "nodes": [{"id": "n1", "name": "WebhookTrigger"}],
        "edges": [],
    }

    captured: dict = {}

    db = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[])
    result_mock = MagicMock()
    result_mock.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=result_mock)

    # WorkflowService receives `db` and creates WorkflowCRUD internally.
    # We mock service.crud after instantiation to point to our db.
    service = WorkflowService(db)
    service.crud = MagicMock(db=db)

    service._load_workflow = AsyncMock(return_value=(wf, wf.definition))
    service._resolve_candidates = AsyncMock(return_value=[MagicMock()])
    service._dispatch_job = AsyncMock(
        side_effect=lambda *a, **kw: captured.update(kw) or DispatchResult(id="task-x")
    )

    with patch("app.services.disabled_nodes_service.disabled_names",
               new=AsyncMock(return_value=set())):
        with patch(
            "app.services.workflow_service.resolve_credentials_from_ids",
            new=AsyncMock(return_value={}),
        ):
            with patch(
                "app.services.workflow_service._validate_trigger_credentials_only",
                new=AsyncMock(),
            ):
                await service.start_analysis(wf.id_hash, inputs={})

    assert captured.get("subworkflow_definitions") == {}
    assert captured.get("disabled_nodes") == []
