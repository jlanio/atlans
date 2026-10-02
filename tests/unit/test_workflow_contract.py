"""
Testes de flow.utils.workflow_contract:
- extract_contract a partir de definicoes do canvas
- validate_inputs_mapping contra contrato
- collect_subworkflow_references identifica nodes SubWorkflow
- validate_subworkflow_references_against_db (async) faz lookup no DB
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from flow.utils.workflow_contract import (
    collect_subworkflow_references,
    extract_contract,
    validate_inputs_mapping,
    validate_subworkflow_references_against_db,
)


# ── extract_contract ────────────────────────────────────────────────────────

class TestExtractContract:

    def test_empty_definition(self):
        result = extract_contract({})
        assert result == {
            "inputs": [],
            "outputs": [],
            "has_input_node": False,
            "has_output_node": False,
            # Contagens expostas para detectar contrato ambiguo (>1 node do
            # mesmo tipo torna o retorno indefinido).
            "input_node_count": 0,
            "output_node_count": 0,
        }

    def test_workflow_with_input_and_output_nodes(self):
        definition = {
            "nodes": [
                {"id": "in",  "name": "SubWorkflowInput",
                 "properties": {"ports": ["focos", "bbox"]}},
                {"id": "wfs", "name": "WFS"},
                {"id": "out", "name": "SubWorkflowOutput",
                 "properties": {"ports": ["resultado"]}},
            ],
            "edges": [],
        }
        result = extract_contract(definition)
        assert result["has_input_node"] is True
        assert result["has_output_node"] is True
        assert [p["name"] for p in result["inputs"]] == ["focos", "bbox"]
        assert [p["name"] for p in result["outputs"]] == ["resultado"]

    def test_input_node_only(self):
        definition = {
            "nodes": [
                {"id": "in",  "name": "SubWorkflowInput",
                 "properties": {"ports": ["focos"]}},
                {"id": "wfs", "name": "WFS"},
            ],
            "edges": [],
        }
        result = extract_contract(definition)
        assert result["has_input_node"] is True
        assert result["has_output_node"] is False
        assert [p["name"] for p in result["inputs"]] == ["focos"]
        assert result["outputs"] == []

    def test_dedupe_input_keys_preserves_order(self):
        """Chaves duplicadas em ports nao duplicam no contrato."""
        definition = {
            "nodes": [
                {"id": "in", "name": "SubWorkflowInput",
                 "properties": {"ports": ["focos", "focos", "bbox"]}},
            ],
        }
        result = extract_contract(definition)
        assert [p["name"] for p in result["inputs"]] == ["focos", "bbox"]

    def test_ports_as_json_string(self):
        """ports armazenado como JSON serializado (helper UI faz JSON.stringify)
        e parseado de volta para list[str]."""
        definition = {
            "nodes": [
                {"id": "in", "name": "SubWorkflowInput",
                 "properties": {"ports": '["focos", "bbox"]'}},
                {"id": "out", "name": "SubWorkflowOutput",
                 "properties": {"ports": '["resultado"]'}},
            ],
        }
        result = extract_contract(definition)
        assert [p["name"] for p in result["inputs"]] == ["focos", "bbox"]
        assert [p["name"] for p in result["outputs"]] == ["resultado"]

    def test_node_without_ports_returns_empty(self):
        """Node SubWorkflowInput presente mas sem ports declaradas: contrato
        vazio mas has_input_node=True (sinal para UI mostrar 'declare ports')."""
        definition = {
            "nodes": [{"id": "in", "name": "SubWorkflowInput", "properties": {}}],
        }
        result = extract_contract(definition)
        assert result["has_input_node"] is True
        assert result["inputs"] == []

    def test_ports_in_data_properties(self):
        """Canvas as vezes serializa properties dentro de data.properties."""
        definition = {
            "nodes": [
                {"id": "in", "name": "SubWorkflowInput",
                 "data": {"properties": {"ports": ["a", "b"]}}},
            ],
        }
        result = extract_contract(definition)
        assert [p["name"] for p in result["inputs"]] == ["a", "b"]


# ── validate_inputs_mapping ────────────────────────────────────────────────

class TestValidateInputsMapping:

    def test_all_keys_valid(self):
        contract = {"inputs": [{"name": "focos"}, {"name": "bbox"}]}
        errors = validate_inputs_mapping({"focos": "x", "bbox": "y"}, contract)
        assert errors == []

    def test_partial_mapping_ok(self):
        """Caller nao precisa popular TODAS as chaves declaradas."""
        contract = {"inputs": [{"name": "focos"}, {"name": "bbox"}]}
        errors = validate_inputs_mapping({"focos": "x"}, contract)
        assert errors == []

    def test_unknown_key_rejected(self):
        contract = {"inputs": [{"name": "focos"}]}
        errors = validate_inputs_mapping({"foco": "typo"}, contract)
        assert len(errors) == 1
        assert "foco" in errors[0]
        assert "focos" in errors[0]  # lista declaradas

    def test_empty_contract_skips_validation(self):
        """Workflow sem inputs declarados: nao valida (nao temos informacao)."""
        contract = {"inputs": []}
        errors = validate_inputs_mapping({"qualquer": "x"}, contract)
        assert errors == []

    def test_non_dict_mapping_returns_empty(self):
        contract = {"inputs": [{"name": "focos"}]}
        errors = validate_inputs_mapping(["lista"], contract)  # type: ignore
        assert errors == []


# ── collect_subworkflow_references ─────────────────────────────────────────

class TestCollectSubworkflowReferences:

    def test_extracts_subworkflow_nodes(self):
        definition = {
            "nodes": [
                {"id": "n1", "name": "WFS"},
                {
                    "id": "n2",
                    "name": "SubWorkflow",
                    "properties": {
                        "workflowHash": "abc123",
                        "inputsMapping": {"focos": "src"},
                    },
                },
                {
                    "id": "n3",
                    "name": "SubWorkflow",
                    "properties": {"workflowHash": "xyz789"},
                },
            ],
        }
        refs = collect_subworkflow_references(definition)
        assert len(refs) == 2
        assert refs[0] == {
            "node_id": "n2",
            "workflow_hash": "abc123",
            "inputs_mapping": {"focos": "src"},
        }
        assert refs[1]["workflow_hash"] == "xyz789"
        assert refs[1]["inputs_mapping"] == {}

    def test_subworkflow_without_hash_is_ignored(self):
        definition = {
            "nodes": [
                {"id": "n1", "name": "SubWorkflow", "properties": {"workflowHash": ""}},
            ],
        }
        assert collect_subworkflow_references(definition) == []


# ── validate_subworkflow_references_against_db ─────────────────────────────

class _FakeWorkflow:
    def __init__(self, id_hash, workspace_id, flag_ative, definition):
        self.id_hash = id_hash
        self.workspace_id = workspace_id
        self.flag_ative = flag_ative
        self.definition = definition


def _make_db(targets: dict):
    """Mock de AsyncSession.execute().scalars().all().

    Implementacao: retorna a lista de targets uma unica vez (validacao
    agora carrega tudo numa query — fix do N+1). Tests que esperam
    "nao existe" passam dict vazio.
    """
    db = MagicMock()
    db.statements = []            # o que foi executado, para inspecionar o SQL
    rows = list(targets.values())

    async def execute(stmt):
        db.statements.append(stmt)
        scalars = MagicMock()
        scalars.all = MagicMock(return_value=rows)
        result = MagicMock()
        result.scalars = MagicMock(return_value=scalars)
        return result

    db.execute = AsyncMock(side_effect=execute)
    return db


class TestValidateSubworkflowReferencesAgainstDb:

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_subworkflows(self):
        definition = {"nodes": [{"id": "n1", "name": "WFS"}], "edges": []}
        db = MagicMock()
        errors = await validate_subworkflow_references_against_db(definition, db)
        assert errors == []

    @pytest.mark.asyncio
    async def test_target_not_found(self):
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {"workflowHash": "ghost", "inputsMapping": {}},
            }],
        }
        db = _make_db({})  # nao tem nada
        errors = await validate_subworkflow_references_against_db(definition, db)
        assert any("nao existe" in e for e in errors)

    @pytest.mark.asyncio
    async def test_target_inactive(self):
        target = _FakeWorkflow("h1", "ws-1", False, {})
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {"workflowHash": "h1", "inputsMapping": {}},
            }],
        }
        db = _make_db({"h1": target})
        errors = await validate_subworkflow_references_against_db(
            definition, db, workspace_id="ws-1",
        )
        assert any("desativado" in e for e in errors)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("ativo", [True, False])
    async def test_target_other_workspace_reads_as_missing(self, ativo):
        """Com `workspace_id`, a query filtra pelo workspace e um alvo alheio lê
        como inexistente — ativo ou não. Distinguir "de outro workspace" de
        "não existe" (ou "desativado") seria um oráculo de existência e estado
        de workflows alheios para qualquer membro de qualquer workspace."""
        target = _FakeWorkflow("h1", "ws-OTHER", ativo, {})
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {"workflowHash": "h1", "inputsMapping": {}},
            }],
        }
        db = _make_db({"h1": target})   # sessão que devolve a linha de fora mesmo assim
        errors = await validate_subworkflow_references_against_db(
            definition, db, workspace_id="ws-1",
        )
        assert errors == [
            "Node SubWorkflow 'sub' aponta para workflow 'h1' que nao existe."
        ]
        sql = str(db.statements[0].compile(compile_kwargs={"literal_binds": True}))
        assert "workflows.workspace_id = 'ws-1'" in sql

    @pytest.mark.asyncio
    async def test_without_workspace_id_query_is_not_filtered(self):
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {"workflowHash": "h1", "inputsMapping": {}},
            }],
        }
        db = _make_db({})
        await validate_subworkflow_references_against_db(definition, db)
        sql = str(db.statements[0].compile(compile_kwargs={"literal_binds": True}))
        assert "workflows.workspace_id = " not in sql     # a coluna sai no SELECT; o filtro, não

    @pytest.mark.asyncio
    async def test_target_missing_contract(self):
        # Target ativo e sem SubWorkflowInput/Output nodes
        target = _FakeWorkflow(
            "h1", "ws-1", True,
            {"nodes": [{"id": "x", "name": "WFS"}], "edges": []},
        )
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {"workflowHash": "h1", "inputsMapping": {}},
            }],
        }
        db = _make_db({"h1": target})
        errors = await validate_subworkflow_references_against_db(
            definition, db, workspace_id="ws-1",
        )
        # Só a saída é obrigatória: SubWorkflowInput virou opcional, então o
        # erro deve citar apenas o que de fato impede o uso como sub-fluxo.
        assert any("SubWorkflowOutput" in e for e in errors)
        assert not any("SubWorkflowInput" in e for e in errors)

    @pytest.mark.asyncio
    async def test_invalid_mapping_key(self):
        target = _FakeWorkflow(
            "h1", "ws-1", True,
            {
                "nodes": [
                    {"id": "in",  "name": "SubWorkflowInput",
                     "properties": {"ports": ["focos"]}},
                    {"id": "out", "name": "SubWorkflowOutput",
                     "properties": {"ports": ["resultado"]}},
                ],
                "edges": [],
            },
        )
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {
                    "workflowHash": "h1",
                    "inputsMapping": {"foco_typo": "x"},  # chave invalida
                },
            }],
        }
        db = _make_db({"h1": target})
        errors = await validate_subworkflow_references_against_db(
            definition, db, workspace_id="ws-1",
        )
        assert any("foco_typo" in e for e in errors)

    @pytest.mark.asyncio
    async def test_valid_reference_passes(self):
        target = _FakeWorkflow(
            "h1", "ws-1", True,
            {
                "nodes": [
                    {"id": "in",  "name": "SubWorkflowInput"},
                    {"id": "out", "name": "SubWorkflowOutput"},
                ],
                "edges": [
                    {"source": "in", "target": "out", "from_key": "focos", "to_key": "focos"},
                ],
            },
        )
        definition = {
            "nodes": [{
                "id": "sub",
                "name": "SubWorkflow",
                "properties": {
                    "workflowHash": "h1",
                    "inputsMapping": {"focos": "minha_camada"},
                },
            }],
        }
        db = _make_db({"h1": target})
        errors = await validate_subworkflow_references_against_db(
            definition, db, workspace_id="ws-1",
        )
        assert errors == []
