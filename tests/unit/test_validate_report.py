# tests/unit/test_validate_report.py
"""
Robust validation — the `validar_definicao` report.

Before, a nonexistent node, a duplicate id and a cycle blew up inside
`WorkflowExecutor.__init__` and became a generic 500 ("Unexpected error
occurred"): the phrase the skill's script looked for to give the catalog hint
never arrived. Now these cases surface as `DefinicaoInvalidaError` (422) with
the report attached, and the normal output gains `__report__` — without changing
what already existed (`{node_id: ...}` and `__edge_diagnostics__`).

What the tests pin down, beyond that: the database session is still NOT opened
when there is no credential, `workspace_id` or SubWorkflow; with `workspace_id`,
membership is checked before the credentials; the simulation scope carries the
workspace; `properties` is a synonym of `parameters` (including for the
credential guard, which used to look only at `parameters`).

These cases started as the HTTP contract of `POST /workflows/validate`. The
route was removed (it had no caller) and the rules still hold in the core, which
the MCP `validate_workflow` tool consumes — which is why they call the service
directly. The service basics (session, synonyms, explicit `workspace_id`) are in
`test_validate_service.py`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.exceptions import CredentialAccessDeniedError, DefinicaoInvalidaError
from app.services.validate_service import validar_definicao

NS = "app.services.validate_service"
USUARIO = "usr-test-001"


async def _validar(corpo: dict) -> dict:
    """The way the REST route called it: `workspace_id` comes from the body, when it does."""
    return await validar_definicao(corpo, user_id=USUARIO, workspace_id=None)


def _no(id_hash: str, name: str, tipo: str = "datasource", **params) -> dict:
    return {"id": id_hash, "name": name, "type": tipo, "parameters": params}


def _sessao_falsa(linhas=None):
    """The service's `get_session_async` with a `db` whose `execute().all()` returns `linhas`."""
    db = MagicMock()
    resultado = MagicMock()
    resultado.all.return_value = linhas or []
    db.execute = AsyncMock(return_value=resultado)

    @asynccontextmanager
    async def _ctx():
        yield db

    return patch(f"{NS}.get_session_async", _ctx)


def _sem_sessao():
    """Any attempt to open a session fails the test."""
    return patch(f"{NS}.get_session_async", MagicMock(side_effect=AssertionError("sessão de banco aberta")))


def _simulacao_falsa(saidas: dict):
    from flow.executor.core import WorkflowExecutor

    async def _fake(self):
        self.simulated_outputs = dict(saidas)
        return self.simulated_outputs

    return patch.object(WorkflowExecutor, "simulate_runner", _fake)


def _patches_de_workspace(*, papel="operator", desabilitados=(), subfluxo=()):
    """`papel=None` = not a member of the given workspace."""
    return (
        patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value=papel)),
        patch(f"{NS}.disabled_names", AsyncMock(return_value=set(desabilitados))),
        patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=list(subfluxo))),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Structured 422 — what used to be a 500
# ══════════════════════════════════════════════════════════════════════════════
#
# Nonexistent node (the base case) is in
# `test_validate_service.py::test_definicao_fatal_sobe_como_definicao_invalida_com_report`.

async def test_ciclo_e_definicao_invalida():
    with pytest.raises(DefinicaoInvalidaError) as exc:
        await _validar({
            "nodes": [_no("a", "ReadGeoJSON"), _no("b", "ReadGeoJSON")],
            "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
        })

    codigos = [e["code"] for e in exc.value.report["errors"]]
    assert "cycle" in codigos
    assert "Ciclo detectado" in exc.value.detail


async def test_id_duplicado_e_definicao_invalida():
    with pytest.raises(DefinicaoInvalidaError) as exc:
        await _validar({"nodes": [_no("n1", "ReadGeoJSON"), _no("n1", "ReadGeoJSON")], "edges": []})

    assert exc.value.report["errors"][0]["code"] == "duplicate_node_id"


async def test_construction_error_vira_definicao_invalida():
    from flow.executor.core import WorkflowExecutor

    with patch.object(WorkflowExecutor, "__init__", side_effect=ValueError("nó recusou o construtor")):
        with pytest.raises(DefinicaoInvalidaError) as exc:
            await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": []})

    assert exc.value.status_code == 422
    assert exc.value.report["errors"][-1]["code"] == "construction_error"
    assert "nó recusou o construtor" in exc.value.detail


# ══════════════════════════════════════════════════════════════════════════════
# Normal output — compatible, with __report__
# ══════════════════════════════════════════════════════════════════════════════

async def test_aresta_orfa_vira_aviso_e_saida_declarada():
    """ReadGeoJSON has `dynamic_output` and no `simulate`: it used to vanish from
    the response; now it is included with the declared schema."""
    saida = await _validar({
        "nodes": [_no("n1", "ReadGeoJSON"), _no("n2", "Merge", "control", strategy="first")],
        "edges": [{"source": "n1", "target": "n2"}, {"source": "n2", "target": "ghost"}],
    })

    assert saida["n1"]["status"] == "ok" and saida["n1"]["schema_source"] == "declared"
    assert saida["n1"]["schema"][0]["fields"][0]["name"] == "output"
    report = saida["__report__"]
    assert report["ok"] is True
    avisos = [w for w in report["warnings"] if w["code"] == "orphan_edge"]
    assert avisos and avisos[0]["edge"] == {"source": "n2", "target": "ghost"}
    assert any("workspace_id" in h for h in report["hints"])


async def test_report_sempre_presente_e_edge_diagnostics_so_quando_ha():
    so_um = {"n1": {"status": "ok", "schema": [{"fields": [{"name": "a", "type": "any"}]}]}}
    with _simulacao_falsa(so_um):
        saida = await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": []})
    assert "__report__" in saida
    assert "__edge_diagnostics__" not in saida

    dois = {
        "n1": {"status": "ok", "schema": [{"fields": [{"name": "a", "type": "any"}]}]},
        "n2": {"status": "ok", "schema": []},
    }
    with _simulacao_falsa(dois):
        saida = await _validar({
            "nodes": [_no("n1", "ReadGeoJSON"), _no("n2", "Merge", "control", strategy="first")],
            "edges": [{"source": "n1", "target": "n2", "from_key": "nope"}],
        })
    assert saida["__edge_diagnostics__"][0]["severity"] == "error"
    erros = [e for e in saida["__report__"]["errors"] if e["code"] == "edge_from_key_unknown"]
    assert erros and erros[0]["edge"] == {"source": "n1", "target": "n2", "from_key": "nope"}
    assert saida["__report__"]["ok"] is False


async def test_simulate_error_entra_nos_errors():
    with _simulacao_falsa({"n1": {"status": "error", "error": "boom"}}):
        saida = await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": []})

    report = saida["__report__"]
    assert report["ok"] is False
    erro = report["errors"][0]
    assert (erro["code"], erro["node_id"], erro["message"]) == ("simulate_error", "n1", "boom")


async def test_suggested_params_schema_so_de_trigger():
    saida = await _validar({
        "nodes": [
            _no("t", "WebhookTrigger", "trigger", payloadField="{{ inputs.campo }}"),
            _no("n1", "ReadGeoJSON", "datasource", path="{{ inputs.arquivo }}"),
        ],
        "edges": [{"source": "t", "target": "n1"}],
    })

    report = saida["__report__"]
    assert report["suggested_params_schema"] == {"campo": {"type": "string", "required": True}}
    assert any("heurístico" in h for h in report["hints"])


# ══════════════════════════════════════════════════════════════════════════════
# Database session: only when there is something to check
# ══════════════════════════════════════════════════════════════════════════════

async def test_sem_credencial_e_sem_workspace_nao_abre_sessao():
    with _sem_sessao():
        saida = await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": []})

    report = saida["__report__"]
    assert report["disabled_nodes"] is None and report["subworkflow_errors"] is None
    assert any("workspace_id" in h for h in report["hints"])


async def test_credential_id_invalido_reprova_sem_ir_ao_banco():
    """An id that is not a UUID fails the definition BEFORE any session: neither
    the credential guard nor the simulation resolver opens the database (the
    refusal comes before simulating). Failing it as FATAL matters: the
    `force=True` of the building tools overrides common errors, never fatal
    ones — and a 201 with `__report__.ok: false` would let a credential typo be
    saved."""
    from flow.executor.core import WorkflowExecutor

    sessao_do_resolvedor = MagicMock(side_effect=AssertionError("sessão de banco aberta pelo resolvedor"))
    with _sem_sessao(), patch(
        "app.core.authorization.credential_loader.get_session_async", sessao_do_resolvedor,
    ), patch.object(WorkflowExecutor, "simulate_runner", new=AsyncMock()) as sim:
        with pytest.raises(DefinicaoInvalidaError) as exc:
            await _validar({
                "nodes": [_no("n1", "DatabaseSpatialQuery", credential_id="nao-e-uuid", query="SELECT 1")],
                "edges": [],
            })

    assert exc.value.error_code == "invalid_definition"
    assert "não é um UUID" in exc.value.detail and "nao-e-uuid" in exc.value.detail
    assert [e["code"] for e in exc.value.report["errors"]] == ["invalid_credential_id"]
    assert exc.value.report["ok"] is False
    sim.assert_not_awaited()                     # simulated nothing
    sessao_do_resolvedor.assert_not_called()


async def test_credential_id_sob_properties_e_guardado():
    """With the `properties → parameters` merge, a `credential_id` under
    `properties` now reaches `simulate()` — the guard has to see it through the
    same path (before, the whole dict was dropped by the schema)."""
    from flow.executor.core import WorkflowExecutor

    with _sessao_falsa(), patch.object(WorkflowExecutor, "simulate_runner", new=AsyncMock()) as sim:
        with pytest.raises(CredentialAccessDeniedError) as exc:
            await _validar({
                "nodes": [{"id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
                           "properties": {"credential_id": str(uuid4()), "query": "SELECT 1"}}],
                "edges": [],
            })

    assert exc.value.status_code == 403
    sim.assert_not_awaited()


async def test_403_de_credencial_sem_workspace_sugere_informar_o_workspace():
    """Without `workspace_id` the scope is only the user's own: the credential may
    be shared, and the 403 needs to say what is missing."""
    with _sessao_falsa(), _simulacao_falsa({}):
        with pytest.raises(CredentialAccessDeniedError) as exc:
            await _validar({
                "nodes": [_no("n1", "DatabaseSpatialQuery", credential_id=str(uuid4()), query="SELECT 1")],
                "edges": [],
            })

    assert exc.value.error_code == "credential_access_denied"
    assert "workspace_id" in exc.value.detail


async def test_subworkflow_sem_workspace_nao_consulta_o_banco():
    """Without proven membership, checking the sub-workflow by hash would be an
    oracle for the existence, state and ports of other workspaces' workflows."""
    with _sem_sessao(), _simulacao_falsa({}):
        saida = await _validar({"nodes": [_no("n1", "SubWorkflow", "control", workflowHash="x")], "edges": []})

    report = saida["__report__"]
    assert report["subworkflow_errors"] is None
    assert any("workspace_id" in h for h in report["hints"])


async def test_parameters_que_nao_e_objeto_junto_de_properties_e_erro_de_validacao():
    """A TypeError inside the validator would escape as an internal error (it was
    a 500 in REST) — the class of masked error that the merge must not
    reintroduce. It surfaces as `ValidationError`, which the caller translates."""
    with pytest.raises(ValidationError):
        await _validar({
            "nodes": [{"id": "n1", "name": "ReadGeoJSON", "type": "datasource",
                       "properties": {"a": 1}, "parameters": [1, 2]}],
            "edges": [],
        })


# ══════════════════════════════════════════════════════════════════════════════
# workspace_id: membership, disabled nodes, sub-workflows, credential scope
# ══════════════════════════════════════════════════════════════════════════════
#
# Non-member WITH a credential (403 before the credential guard) is in
# `test_validate_service.py::test_nao_membro_do_workspace_e_403_antes_das_credenciais`.

async def test_workspace_id_de_que_nao_participa_e_403():
    from flow.executor.core import WorkflowExecutor

    a, b, c = _patches_de_workspace(papel=None)
    with _sessao_falsa(), a, b, c, patch.object(WorkflowExecutor, "simulate_runner", new=AsyncMock()) as sim:
        with pytest.raises(HTTPException) as exc:
            await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-test-001"})

    assert exc.value.status_code == 403
    sim.assert_not_awaited()


async def test_viewer_valida_so_com_as_proprias_credenciais():
    """Executing requires `operator`; the simulation connects to the credential's
    database, so a shared credential only enters the scope of someone who could
    run it."""
    from app.core.authorization import credential_loader
    from flow.executor.core import WorkflowExecutor

    visto = {}

    async def _fake(self):
        visto["escopo"] = credential_loader._scope.get()
        self.simulated_outputs = {}
        return self.simulated_outputs

    a, b, c = _patches_de_workspace(papel="viewer")
    with _sessao_falsa(), a, b, c, \
         patch(f"{NS}.assert_credentials_accessible", new=AsyncMock()) as guarda, \
         patch.object(WorkflowExecutor, "simulate_runner", _fake):
        saida = await _validar({
            "nodes": [_no("n1", "DatabaseSpatialQuery", credential_id=str(uuid4()), query="SELECT 1")],
            "edges": [], "workspace_id": "ws-test-001",
        })

    assert guarda.await_args.kwargs["shared_workspace_id"] is None
    assert visto["escopo"] == credential_loader.EscopoDeCredenciais(frozenset({USUARIO}), None)
    assert any("operator" in h for h in saida["__report__"]["hints"])


async def test_workspace_id_valido_acusa_no_desabilitado():
    a, b, c = _patches_de_workspace(desabilitados=("ReadGeoJSON",))
    with _sessao_falsa(), a, b, c:
        saida = await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-test-001"})

    report = saida["__report__"]
    assert report["disabled_nodes"] == ["ReadGeoJSON"]
    erros = [e for e in report["errors"] if e["code"] == "disabled_node"]
    assert erros and erros[0]["node_id"] == "n1"
    assert report["ok"] is False
    assert not any("workspace_id" in h for h in report["hints"])


async def test_subfluxo_inexistente_aparece_no_report():
    msg = "Node SubWorkflow 'n2' aponta para workflow 'x' que nao existe."
    a, b, c = _patches_de_workspace(subfluxo=(msg,))
    with _sessao_falsa(), a, b, c as sub:
        saida = await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-test-001"})

    report = saida["__report__"]
    assert report["subworkflow_errors"] == [msg]
    assert [e["message"] for e in report["errors"] if e["code"] == "subworkflow_reference"] == [msg]
    assert sub.await_args.kwargs["workspace_id"] == "ws-test-001"


async def test_credencial_compartilhada_e_checada_com_o_workspace():
    """The guard receives the workspace: a credential shared with it passes;
    without `workspace_id`, only the user's own (`shared_workspace_id=None`)."""
    cred = str(uuid4())
    corpo = {
        "nodes": [_no("n1", "DatabaseSpatialQuery", credential_id=cred, query="SELECT 1")],
        "edges": [],
    }
    a, b, c = _patches_de_workspace()
    with _sessao_falsa(), a, b, c, _simulacao_falsa({}), \
         patch(f"{NS}.assert_credentials_accessible", new=AsyncMock()) as guarda:
        await _validar({**corpo, "workspace_id": "ws-test-001"})
        await _validar(corpo)

    primeira, segunda = guarda.await_args_list
    assert primeira.kwargs["shared_workspace_id"] == "ws-test-001"
    assert segunda.kwargs["shared_workspace_id"] is None
    assert set(primeira.args[1]) == {cred}


async def test_escopo_da_simulacao_carrega_o_workspace():
    from app.core.authorization import credential_loader
    from flow.executor.core import WorkflowExecutor

    visto = {}

    async def _fake(self):
        visto["escopo"] = credential_loader._scope.get()
        self.simulated_outputs = {}
        return self.simulated_outputs

    a, b, c = _patches_de_workspace()
    with _sessao_falsa(), a, b, c, patch.object(WorkflowExecutor, "simulate_runner", _fake):
        await _validar({"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-test-001"})

    assert visto["escopo"] == credential_loader.EscopoDeCredenciais(frozenset({USUARIO}), "ws-test-001")
