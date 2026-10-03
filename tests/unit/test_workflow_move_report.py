# tests/unit/test_workflow_move_report.py
"""Impact report for moving a workflow.

Since move never blocks, the report is the ONLY thing that tells the user what
is going to break. A warning that does not show up is worse than no report: it
gives the impression that everything is fine.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import workflow_move_report as rep


DESTINO = "ws-destino"
ORIGEM = "ws-origem"


def _node(nid, name, props, ntype="datasource", em_data=False):
    """`em_data=True` grava em data.properties — o formato do canvas (XYFlow)."""
    node = {"id": nid, "name": name, "type": ntype}
    if em_data:
        node["data"] = {"properties": props}
    else:
        node["properties"] = props
    return node


def _wf(**kw):
    base = {
        "id_hash": "wf-1", "pinned_outputs": None, "group_id": None,
        "portal_access": "disabled", "notification_url": None,
    }
    base.update(kw)
    return MagicMock(**base)


def _codes(avisos):
    return {a["code"] for a in avisos}


# ── Property collector ───────────────────────────────────────────────────────

def test_collector_reads_data_properties_and_properties():
    """The canvas writes to data.properties; reading only `properties` would
    produce a false negative precisely in the most common format."""
    definition = {"nodes": [
        _node("n1", "DataInput", {"driveFileId": "f-1"}),
        _node("n2", "DataInput", {"driveFileId": "f-2"}, em_data=True),
    ]}

    achado = rep._collect_prop(definition, "driveFileId")

    assert achado == {"f-1": ["n1"], "f-2": ["n2"]}


def test_subworkflow_collector_uses_the_same_chain():
    """flow/'s `collect_subworkflow_references` reads only `properties` — which is
    why the report has its own collector."""
    definition = {"nodes": [
        _node("s1", "SubWorkflow", {"workflowHash": "wf-b"}, ntype="control", em_data=True),
    ]}

    assert rep._collect_subworkflow_refs(definition) == {"wf-b": ["s1"]}


def test_collector_ignores_empty_values():
    definition = {"nodes": [_node("n1", "DataInput", {"driveFileId": "  "})]}

    assert rep._collect_prop(definition, "driveFileId") == {}


# ── Credenciais ──────────────────────────────────────────────────────────────

def _db_with(rows_per_call):
    """`db.execute` devolvendo resultados diferentes a cada chamada."""
    db = MagicMock()
    resultados = []
    for linhas in rows_per_call:
        r = MagicMock()
        r.all.return_value = linhas
        r.scalars.return_value.all.return_value = linhas
        r.scalar_one_or_none.return_value = linhas
        resultados.append(r)
    db.execute = AsyncMock(side_effect=resultados)
    return db


@pytest.mark.asyncio
async def test_warns_about_credential_whose_owner_cannot_reach_the_target():
    """The credential scope comes from the members of the workflow's workspace.
    Without a warning, the symptom at runtime is just a WARNING in the server log."""
    definition = {"nodes": [_node("n1", "WFS", {"credential_id": "11111111-1111-1111-1111-111111111111"})]}
    db = _db_with([[("11111111-1111-1111-1111-111111111111", "Banco Prod", "usr-alheio")]])

    with patch.object(rep, "workspace_credential_owners", new=AsyncMock(return_value={"usr-membro"})):
        avisos = await rep._avisar_credenciais(db, definition, DESTINO)

    assert _codes(avisos) == {"credentials_unresolvable"}
    assert avisos[0]["details"]["credential_name"] == "Banco Prod"
    assert avisos[0]["details"]["node_ids"] == ["n1"]


@pytest.mark.asyncio
async def test_does_not_warn_when_the_owner_is_a_target_member():
    definition = {"nodes": [_node("n1", "WFS", {"credential_id": "11111111-1111-1111-1111-111111111111"})]}
    db = _db_with([[("11111111-1111-1111-1111-111111111111", "Banco Prod", "usr-membro")]])

    with patch.object(rep, "workspace_credential_owners", new=AsyncMock(return_value={"usr-membro"})):
        avisos = await rep._avisar_credenciais(db, definition, DESTINO)

    assert avisos == []


@pytest.mark.asyncio
async def test_credential_in_trigger_is_flagged():
    """In a trigger the effect is noisy (403 on trigger), not silent — the
    message needs to say so."""
    definition = {"nodes": [
        _node("t1", "WebhookTrigger", {"credential_id": "11111111-1111-1111-1111-111111111111"}, ntype="trigger"),
    ]}
    db = _db_with([[("11111111-1111-1111-1111-111111111111", "Token", "usr-alheio")]])

    with patch.object(rep, "workspace_credential_owners", new=AsyncMock(return_value=set())):
        avisos = await rep._avisar_credenciais(db, definition, DESTINO)

    assert avisos[0]["details"]["is_trigger"] is True
    assert "403" in avisos[0]["message"]


@pytest.mark.asyncio
async def test_nonexistent_credential_has_its_own_code():
    definition = {"nodes": [_node("n1", "WFS", {"credential_id": "11111111-1111-1111-1111-111111111111"})]}
    db = _db_with([[]])

    with patch.object(rep, "workspace_credential_owners", new=AsyncMock(return_value={"usr-1"})):
        avisos = await rep._avisar_credenciais(db, definition, DESTINO)

    assert _codes(avisos) == {"credential_not_found"}


@pytest.mark.asyncio
async def test_without_credentials_does_not_query_the_database():
    db = MagicMock(execute=AsyncMock())

    assert await rep._avisar_credenciais(db, {"nodes": []}, DESTINO) == []
    db.execute.assert_not_awaited()


# ── Sub-workflows ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warns_about_subworkflow_left_outside_the_target():
    definition = {"nodes": [_node("s1", "SubWorkflow", {"workflowHash": "wf-b"}, ntype="control")]}
    db = _db_with([[("wf-b", "Consolidação", ORIGEM)]])

    avisos = await rep._avisar_subworkflows(db, definition, DESTINO)

    assert _codes(avisos) == {"subworkflow_out_of_scope"}


@pytest.mark.asyncio
async def test_does_not_warn_about_subworkflow_already_in_target():
    definition = {"nodes": [_node("s1", "SubWorkflow", {"workflowHash": "wf-b"}, ntype="control")]}
    db = _db_with([[("wf-b", "Consolidação", DESTINO)]])

    assert await rep._avisar_subworkflows(db, definition, DESTINO) == []


# ── Dependentes reversos ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warns_about_reverse_dependent():
    """Collateral that is not in the moved workflow's definition, but in the others'."""
    dependent_def = {"nodes": [_node("s1", "SubWorkflow", {"workflowHash": "wf-1"}, ntype="control")]}
    db = _db_with([[("wf-a", "Relatório mensal", dependent_def)]])

    avisos = await rep._avisar_dependentes(db, "wf-1", ORIGEM)

    assert _codes(avisos) == {"reverse_dependents"}
    assert avisos[0]["details"]["workflow_name"] == "Relatório mensal"


@pytest.mark.asyncio
async def test_prefilter_false_positive_is_discarded():
    """The LIKE on the JSON may match the hash in another field; the confirmation is done in Python."""
    other_def = {"nodes": [_node("n1", "DataInput", {"driveFileId": "wf-1"})]}
    db = _db_with([[("wf-a", "Outro", other_def)]])

    assert await rep._avisar_dependentes(db, "wf-1", ORIGEM) == []


# ── Arquivos ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warns_about_drive_file_from_source():
    definition = {"nodes": [_node("n1", "DataInput", {"driveFileId": "f-1"})]}
    db = _db_with([[("f-1", "malha.geojson", ORIGEM)]])

    avisos = await rep._avisar_arquivos(db, definition, DESTINO)

    assert _codes(avisos) == {"drive_refs_out_of_scope"}
    assert "malha.geojson" in avisos[0]["message"]


@pytest.mark.asyncio
async def test_warns_about_artifact_from_source():
    definition = {"nodes": [_node("n1", "DataInput", {"artifactId": "a-1"})]}
    db = _db_with([[("a-1", "saida.parquet", ORIGEM)]])

    avisos = await rep._avisar_arquivos(db, definition, DESTINO)

    assert _codes(avisos) == {"artifact_refs_out_of_scope"}


@pytest.mark.asyncio
async def test_does_not_warn_about_file_already_in_target():
    definition = {"nodes": [_node("n1", "DataInput", {"driveFileId": "f-1"})]}
    db = _db_with([[("f-1", "malha.geojson", DESTINO)]])

    assert await rep._avisar_arquivos(db, definition, DESTINO) == []


# ── Workspace configuration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_warns_about_executor_change():
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", "exec-b", None),
    ]])

    avisos = await rep._avisar_workspace(db, _wf(), ORIGEM, DESTINO)

    assert _codes(avisos) == {"executor_changed"}


@pytest.mark.asyncio
async def test_target_without_executor_mentions_the_default_pool():
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", None, None),
    ]])

    avisos = await rep._avisar_workspace(db, _wf(), ORIGEM, DESTINO)

    assert "padrão" in avisos[0]["message"]


@pytest.mark.asyncio
async def test_does_not_warn_when_the_executor_is_the_same():
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", "exec-a", None),
    ]])

    assert await rep._avisar_workspace(db, _wf(), ORIGEM, DESTINO) == []


@pytest.mark.asyncio
async def test_warns_about_notification_url_outside_the_allowlist():
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", "exec-a", ["parceiro.com"]),
    ]])
    wf = _wf(notification_url="https://interno.example.com/hook")

    avisos = await rep._avisar_workspace(db, wf, ORIGEM, DESTINO)

    assert _codes(avisos) == {"notification_url_blocked"}


@pytest.mark.asyncio
async def test_empty_allowlist_raises_no_warning():
    """Without an allowlist only the default SSRF check applies — nothing changes with the move."""
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", "exec-a", []),
    ]])
    wf = _wf(notification_url="https://interno.example.com/hook")

    assert await rep._avisar_workspace(db, wf, ORIGEM, DESTINO) == []


@pytest.mark.asyncio
async def test_url_allowed_by_the_allowlist_raises_no_warning():
    db = _db_with([[
        (ORIGEM, "Origem", "exec-a", None),
        (DESTINO, "Destino", "exec-a", ["*.parceiro.com"]),
    ]])
    wf = _wf(notification_url="https://api.parceiro.com/hook")

    assert await rep._avisar_workspace(db, wf, ORIGEM, DESTINO) == []


# ── Estado ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_active_runs_reports_the_total_not_the_sample_size():
    """The run_ids sample is capped at 5; counting its result would make the
    message say '5' for any number above that."""
    db = _db_with([
        12,                              # COUNT of runs in progress
        ["r1", "r2", "r3", "r4", "r5"],  # amostra (limit 5)
        0,                               # total de runs (history_left_behind)
        0,                               # portal layers
    ])

    avisos = await rep._avisar_estado(db, _wf(), {"nodes": []})

    ativo = next(a for a in avisos if a["code"] == "active_runs")
    assert "12 execução" in ativo["message"]
    assert ativo["details"]["total"] == 12
    assert len(ativo["details"]["run_ids"]) == 5


@pytest.mark.asyncio
async def test_no_runs_in_progress_raises_no_warning():
    db = _db_with([0, 0, 0])

    avisos = await rep._avisar_estado(db, _wf(), {"nodes": []})

    assert "active_runs" not in _codes(avisos)


# ── Resiliencia ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_failure_does_not_break_the_move():
    """The feature's contract is that moving does not fail. An empty report would
    be read as 'no impact' — hence the explicit code."""
    db = MagicMock(execute=AsyncMock(side_effect=RuntimeError("banco fora do ar")))

    avisos = await rep.collect_warnings(db, _wf(), {"nodes": []}, ORIGEM, DESTINO)

    assert _codes(avisos) == {"report_incomplete"}


@pytest.mark.asyncio
async def test_warnings_come_before_infos():
    """On screen, what breaks needs to show up first."""
    avisos = [
        {"code": "a", "severity": "info", "message": "", "details": {}},
        {"code": "b", "severity": "warning", "message": "", "details": {}},
    ]
    with patch.object(rep, "_avisar_credenciais", new=AsyncMock(return_value=avisos)), \
         patch.object(rep, "_avisar_subworkflows", new=AsyncMock(return_value=[])), \
         patch.object(rep, "_avisar_dependentes", new=AsyncMock(return_value=[])), \
         patch.object(rep, "_avisar_arquivos", new=AsyncMock(return_value=[])), \
         patch.object(rep, "_avisar_workspace", new=AsyncMock(return_value=[])), \
         patch.object(rep, "_avisar_estado", new=AsyncMock(return_value=[])):
        resultado = await rep.collect_warnings(MagicMock(), _wf(), {"nodes": []}, ORIGEM, DESTINO)

    assert [a["severity"] for a in resultado] == ["warning", "info"]
