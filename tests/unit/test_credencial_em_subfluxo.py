"""
Database credential used INSIDE a sub-workflow.

The executor has no DB: the server swaps `credential_id` for the DSN when
building the envelope and removes the id. That only happened in the root
definition — the chain of sub-workflows traveled raw in the same envelope. A
database node inside a sub-workflow reached the executor with the id and no
connection, and died with
"'connectionString' é obrigatório (deve ser resolvido antes da execução)":
a sentence that describes a server problem as if it were node configuration.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workflow_execution_service import (
    _collect_credential_ids,
    _dispatch_job,
)
from app.services.workflow_service import WorkflowService, DispatchResult
from flow.utils.credencial import get_connection

CRED_PARENT = "cred-do-pai"
CRED_CHILD = "cred-do-filho"


def _parent_def(child_hash="child-1"):
    return {
        "nodes": [
            {"id": "trigger-1", "name": "WebhookTrigger", "properties": {}},
            {"id": "sub-1", "name": "SubWorkflow",
             "properties": {"workflowHash": child_hash, "inputsMapping": {}}},
        ],
        "edges": [],
    }


def _child_def():
    return {
        "nodes": [
            {"id": "in", "name": "SubWorkflowInput"},
            {"id": "db", "name": "DatabaseSpatialQuery",
             "properties": {"credential_id": CRED_CHILD, "query": "SELECT 1"}},
            {"id": "out", "name": "SubWorkflowOutput"},
        ],
        "edges": [],
    }


# ── collecting the ids ──────────────────────────────────────────────────────

class TestIdCollection:

    def test_merges_parent_and_child_credentials(self):
        pai = _parent_def()
        pai["nodes"].append(
            {"id": "db-pai", "name": "DatabaseQuery",
             "properties": {"credential_id": CRED_PARENT}}
        )
        ids = _collect_credential_ids(pai, _child_def())
        assert set(ids) == {CRED_PARENT, CRED_CHILD}

    def test_root_only_still_works(self):
        # The signature now accepts several definitions; the call with just one
        # is the one the rest of the code makes.
        assert _collect_credential_ids(_child_def()) == [CRED_CHILD]

    def test_tolerates_empty_or_null_definition(self):
        assert _collect_credential_ids({}, None, _child_def()) == [CRED_CHILD]


# ── resolution at dispatch ──────────────────────────────────────────────────

class TestResolutionInDispatch:

    @pytest.mark.asyncio
    async def test_the_child_credential_is_resolved(self):
        """Without this, `pre_resolved` did not contain the child's credential and
        the injection had nothing to inject, even after it started walking the
        sub-workflows."""
        pai = MagicMock()
        pai.id_hash, pai.workspace_id, pai.flag_ative = "parent-A", "ws-test", True
        pai.pinned_outputs = pai.pin_metadata = None
        pai.definition = _parent_def()

        filho = MagicMock()
        filho.id_hash, filho.workspace_id, filho.flag_ative = "child-1", "ws-test", True
        filho.definition = _child_def()

        scalars = MagicMock()
        scalars.all = MagicMock(return_value=[filho])
        res = MagicMock()
        res.scalars = MagicMock(return_value=scalars)
        db = MagicMock()
        db.execute = AsyncMock(return_value=res)

        service = WorkflowService(db)
        service.crud = MagicMock(db=db)
        service._load_workflow = AsyncMock(return_value=(pai, pai.definition))
        service._resolve_candidates = AsyncMock(return_value=[MagicMock()])
        service._dispatch_job = AsyncMock(return_value=DispatchResult(id="task-1"))

        resolver = AsyncMock(return_value={CRED_CHILD: {"connectionString": "dsn://x"}})
        with (
            patch("app.services.disabled_nodes_service.disabled_names",
                  new=AsyncMock(return_value=set())),
            patch("app.services.workflow_service.resolve_credentials_from_ids", new=resolver),
            patch("app.services.workflow_service._validate_trigger_credentials_only",
                  new=AsyncMock()),
        ):
            await service.start_analysis(pai.id_hash, inputs={})

        resolver.assert_awaited()
        pedidos = resolver.await_args.args[0]
        assert CRED_CHILD in pedidos, (
            f"a credencial do sub-fluxo não foi pedida ao resolver: {pedidos}"
        )

    @pytest.mark.asyncio
    async def test_the_envelope_carries_the_dsn_inside_the_subworkflow(self):
        """What the executor actually receives: `connectionString` in the child's
        node, and `credential_id` removed."""
        wf = MagicMock()
        wf.id_hash, wf.workspace_id = "parent-A", "ws-test"
        wf.pinned_outputs = wf.pin_metadata = None

        # The pending->running UPDATE is built with the real model, so it cannot
        # be swapped for a mock; the whole `db` is fake and nothing reaches
        # the database.
        transicao = MagicMock()
        transicao.rowcount = 1
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock(return_value=transicao)
        capturado: dict = {}

        def _capture(**kwargs):
            # The payload arrives already serialized: the dispatch does the json.dumps
            # only once, outside the candidates loop.
            import json as _json
            capturado.update(_json.loads(kwargs["payload"]))
            return {"job": "cifrado"}

        agente = MagicMock()
        agente.id_hash = "exec-1"
        agente.name = "exec"
        agente.public_key = "pk"

        with (
            patch("app.services.workflow_execution_service.inject_credentials",
                  new=AsyncMock(side_effect=_fake_inject)),
            patch("app.services.workflow_execution_service.build_job_message",
                  new=MagicMock(side_effect=_capture)),
            patch("app.services.workflow_execution_service.executor_registry.send_job",
                  new=AsyncMock(return_value=True)),
        ):
            await _dispatch_job(
                wf, _parent_def(), [agente], None, False, db=db,
                pre_resolved={CRED_CHILD: {"connectionString": "dsn://filho"}},
                subworkflow_definitions={"child-1": _child_def()},
            )

        no_db = capturado["subworkflow_definitions"]["child-1"]["nodes"][1]
        props = no_db["properties"]
        assert props.get("connectionString") == "dsn://filho", (
            "o sub-fluxo foi para o envelope sem a conexão resolvida"
        )
        assert "credential_id" not in props, (
            "o id da credencial não deveria viajar junto do DSN"
        )


async def _fake_inject(definition, pre_resolved=None, **_):
    """Same contract as `inject_credentials`, without touching the database."""
    from app.services.credential_resolver import inject_credentials
    return await inject_credentials(definition, pre_resolved=pre_resolved or {})


# ── the message the operator reads ──────────────────────────────────────────

class TestNodeMessage:

    def test_returns_the_dsn_when_resolved(self):
        assert get_connection({"connectionString": " dsn://x "}) == "dsn://x"

    def test_credential_chosen_but_not_resolved_blames_the_server(self):
        # `credential_id` surviving is the trail: `inject_credentials` removes it
        # precisely when injecting the DSN.
        with pytest.raises(ValueError) as exc:
            get_connection({"credential_id": CRED_CHILD})
        msg = str(exc.value)
        assert "servidor não a resolveu" in msg
        assert "Escolha uma" not in msg, "manda configurar algo que já está configurado"

    def test_without_any_credential_asks_to_configure_the_node(self):
        with pytest.raises(ValueError) as exc:
            get_connection({})
        msg = str(exc.value)
        assert "Nenhuma credencial" in msg and "Credencial" in msg
        assert "servidor" not in msg, "acusa o servidor de um erro de configuração"

    def test_blank_string_counts_as_absent(self):
        with pytest.raises(ValueError, match="Nenhuma credencial"):
            get_connection({"connectionString": "   ", "credential_id": "  "})
