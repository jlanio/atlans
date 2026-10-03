# tests/unit/test_validate_service.py
"""
`validar_definicao` called directly, without HTTP — the service's contract.

The MCP server tools (`validate_workflow` and the validation before saving)
consume this function; what these tests pin down is what they inherit from it:
the database session does NOT open without a credential or workspace,
`properties` and `parameters` are accepted as synonyms, the explicit
`workspace_id` beats the one in the body (the MCP resolves id-or-name before
calling), a non-member gets a 403 before any credential, a fatal definition
surfaces as `InvalidDefinitionError` carrying the report, and an empty registry
is a 503 (a boot failure, not a definition one). The report in detail is in
`test_validate_report.py`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import InvalidDefinitionError
from app.services.validate_service import WorkflowDefinition, validar_definicao

NS = "app.services.validate_service"
USUARIO = "usr-test-001"


def _no(id_hash: str, name: str, tipo: str = "datasource", **params) -> dict:
    return {"id": id_hash, "name": name, "type": tipo, "parameters": params}


def _no_session():
    """Any attempt to open a session fails the test."""
    return patch(f"{NS}.get_session_async", MagicMock(side_effect=AssertionError("sessão de banco aberta")))


def _fake_session():
    db = MagicMock()
    resultado = MagicMock()
    resultado.all.return_value = []
    db.execute = AsyncMock(return_value=resultado)

    @asynccontextmanager
    async def _ctx():
        yield db

    return patch(f"{NS}.get_session_async", _ctx)


def _fake_simulation(saidas: dict | None = None, visto: dict | None = None):
    """Replaces the real `simulate_runner`; `visto` receives node `n1` as the executor sees it."""
    from flow.executor.core import WorkflowExecutor

    async def _fake(self):
        if visto is not None:
            visto.update(self.node_mgr.node_defs["n1"])
        self.simulated_outputs = dict(saidas or {})
        return self.simulated_outputs

    return patch.object(WorkflowExecutor, "simulate_runner", _fake)


# ══════════════════════════════════════════════════════════════════════════════
# Common case — no database
# ══════════════════════════════════════════════════════════════════════════════

async def test_without_credential_or_workspace_opens_no_session():
    with _no_session(), _fake_simulation({"n1": {"status": "ok", "schema": []}}):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    assert saida["n1"] == {"status": "ok", "schema": []}
    assert saida["__report__"]["ok"] is True
    assert "__edge_diagnostics__" not in saida


async def test_dict_and_model_are_accepted_and_properties_is_a_synonym_of_parameters():
    """A `dict` goes through the same `WorkflowDefinition` as the endpoint:
    `properties` (persisted format) merges into `parameters` (body format) and
    the executor receives both pointing to the SAME dict; `alias` survives."""
    seen_dict: dict = {}
    seen_model: dict = {}
    no = {"id": "n1", "name": "ReadGeoJSON", "type": "datasource",
          "properties": {"path": "x.geojson"}, "alias": "Caixa", "position": {"x": 1, "y": 2}}

    with _no_session():
        with _fake_simulation(visto=seen_dict):
            await validar_definicao({"nodes": [no], "edges": []}, user_id=USUARIO, workspace_id=None)
        with _fake_simulation(visto=seen_model):
            await validar_definicao(
                WorkflowDefinition.model_validate({"nodes": [no], "edges": []}),
                user_id=USUARIO, workspace_id=None,
            )

    for visto in (seen_dict, seen_model):
        assert visto["parameters"] == {"path": "x.geojson"}
        assert visto["properties"] is visto["parameters"]
        assert visto["alias"] == "Caixa"
        assert "position" not in visto


async def test_parameters_wins_over_properties_on_conflict():
    visto: dict = {}
    no = {"id": "n1", "name": "ReadGeoJSON", "type": "datasource",
          "properties": {"path": "antigo.geojson", "so_aqui": 1}, "parameters": {"path": "novo.geojson"}}

    with _no_session(), _fake_simulation(visto=visto):
        await validar_definicao({"nodes": [no], "edges": []}, user_id=USUARIO, workspace_id=None)

    assert visto["parameters"] == {"path": "novo.geojson", "so_aqui": 1}


async def test_without_workspace_the_report_suggests_providing_one():
    from app.services.validate_service import HINT_WORKSPACE

    with _no_session(), _fake_simulation():
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    assert HINT_WORKSPACE in saida["__report__"]["hints"]


# ══════════════════════════════════════════════════════════════════════════════
# workspace_id — explicit beats the body; membership before everything
# ══════════════════════════════════════════════════════════════════════════════

async def test_explicit_workspace_id_wins_over_the_body():
    papel = AsyncMock(return_value="operator")
    subfluxo = AsyncMock(return_value=[])

    with _fake_session(), _fake_simulation(), \
         patch(f"{NS}.get_workspace_member_role", papel), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", subfluxo):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-do-corpo"},
            user_id=USUARIO, workspace_id="ws-explicito",
        )

    assert papel.await_args.args[1:] == ("ws-explicito", USUARIO)
    assert subfluxo.await_args.kwargs["workspace_id"] == "ws-explicito"
    # With a workspace, the hint to provide one makes no sense.
    assert saida["__report__"]["hints"] == []


async def test_workspace_id_none_lets_the_body_one_apply():
    """`None` here means "use what came in the definition" — the optional body field."""
    papel = AsyncMock(return_value="owner")

    with _fake_session(), _fake_simulation(), \
         patch(f"{NS}.get_workspace_member_role", papel), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])):
        await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": [], "workspace_id": "ws-do-corpo"},
            user_id=USUARIO, workspace_id=None,
        )

    assert papel.await_args.args[1:] == ("ws-do-corpo", USUARIO)


async def test_workspace_non_member_is_403_before_credentials():
    guarda = AsyncMock()

    with _fake_session(), _fake_simulation(), \
         patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value=None)), \
         patch(f"{NS}.assert_credentials_accessible", guarda):
        with pytest.raises(HTTPException) as exc:
            await validar_definicao(
                {"nodes": [_no("n1", "DatabaseSpatialQuery",
                               credential_id="8d3f7b1e-2c44-4a5a-9f0e-1b2c3d4e5f60", query="SELECT 1")],
                 "edges": []},
                user_id=USUARIO, workspace_id="ws-alheio",
            )

    assert exc.value.status_code == 403
    guarda.assert_not_awaited()


async def test_operator_role_carries_the_workspace_into_the_simulation_scope():
    from contextlib import contextmanager

    escopos: list = []

    # `credential_scope` is a synchronous context manager; the stub needs to be one too.
    @contextmanager
    def _fake_scope(*args, **kwargs):
        escopos.append((args, kwargs))
        yield

    with _fake_session(), _fake_simulation(), \
         patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value="operator")), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())), \
         patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])), \
         patch(f"{NS}.credential_scope", _fake_scope):
        await validar_definicao(
            {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id="ws-1",
        )

    assert escopos == [(({USUARIO},), {"shared_workspace_id": "ws-1"})]


async def test_wrong_type_or_expired_credential_becomes_error_before_execute():
    """Accessible is not usable: resolution silently leaves out a credential of a
    type the node does not accept and an expired one — and the node only
    refused at execution, with "credencial não resolvida" (credential not
    resolved). An error where the node consumes the injected secret (WFS,
    database); a warning where it uses its own id (DataOutput), because there
    the execution goes on and only the download is refused — and an error would
    keep the assistant from saving an edit to another node."""
    import flow.nodes.datasource.database_spatial_query  # noqa: F401 — registers the nodes
    import flow.nodes.datasource.wfs  # noqa: F401
    import flow.nodes.outputs.data_output  # noqa: F401

    cid_pg, cid_expired = "8d3f7b1e-2c44-4a5a-9f0e-1b2c3d4e5f60", "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"
    cid_authkey, cid_expired_token = "1a2b3c4d-0000-4000-8000-000000000001", "1a2b3c4d-0000-4000-8000-000000000002"
    catalogo = AsyncMock(return_value={
        cid_pg: ("postgresql", "valida", None),
        cid_expired: ("geoserver_authkey", "expirada", "2020-01-01T00:00:00Z"),
        cid_authkey: ("geoserver_authkey", "valida", None),
        cid_expired_token: ("webhook_token", "expirada", "2020-01-01T00:00:00Z"),
    })
    saidas = {n: {"status": "ok", "schema": []} for n in ("n1", "n2", "n3", "n4")}
    with _fake_session(), _fake_simulation(saidas), \
         patch(f"{NS}.assert_credentials_accessible", AsyncMock()), \
         patch(f"{NS}.tipos_e_validades", catalogo), \
         patch(f"{NS}.disabled_names", AsyncMock(return_value=set())):
        saida = await validar_definicao(
            {"nodes": [_no("n1", "WFS", url="https://geo.x/ows", typeName="ns:a", credential_id=cid_pg),
                       _no("n2", "WFS", url="https://geo.x/ows", typeName="ns:b", credential_id=cid_expired.upper()),
                       # A database node does not declare `credential_types`: the credential's SHAPE decides.
                       _no("n3", "DatabaseSpatialQuery", query="SELECT 1", credential_id=cid_authkey),
                       _no("n4", "DataOutput", "output", isPublic=False, credential_id=cid_expired_token)],
             "edges": []},
            user_id=USUARIO, workspace_id=None,
        )

    report = saida["__report__"]
    assert {(e["code"], e["node_id"]) for e in report["errors"]} == {
        ("credential_type_mismatch", "n1"), ("credential_expired", "n2"), ("credential_type_mismatch", "n3"),
    }
    assert report["ok"] is False
    assert "geoserver_authkey, wfs" in report["errors"][0]["message"]
    assert "não declara `http_auth`" in next(e["message"] for e in report["errors"] if e["node_id"] == "n3")
    (aviso,) = [w for w in report["warnings"] if w["code"] == "credential_expired"]
    assert aviso["node_id"] == "n4" and "download" in aviso["message"]
    assert catalogo.await_args.args[1] == {cid_pg, cid_expired.upper(), cid_authkey, cid_expired_token}


@pytest.mark.parametrize("expires_at, validade", [
    (None, "valida"), ("", "valida"),
    ("2099-01-01T00:00:00Z", "valida"), ("2099-01-01T00:00:00", "valida"),
    ("2020-01-01T00:00:00Z", "expirada"), ("2020-01-01T00:00:00-03:00", "expirada"),
    ("lixo", "invalida"),
])
def test_credential_validity_is_the_resolution_rule(expires_at, validade):
    from app.core.authorization.credential_loader import credential_validity

    assert credential_validity(expires_at) == validade


# ══════════════════════════════════════════════════════════════════════════════
# Erros estruturados
# ══════════════════════════════════════════════════════════════════════════════

async def test_fatal_definition_raises_as_invalid_definition_with_report():
    with _no_session(), pytest.raises(InvalidDefinitionError) as exc:
        await validar_definicao(
            {"nodes": [_no("n1", "NoQueNaoExiste", "action")], "edges": []}, user_id=USUARIO, workspace_id=None,
        )

    erro = exc.value
    assert erro.status_code == 422
    assert erro.report["ok"] is False
    assert erro.report["errors"][0]["code"] == "unknown_node"
    assert erro.report["errors"][0]["node_id"] == "n1"
    assert erro.report["disabled_nodes"] is None
    assert "não encontrado para instância" in erro.detail


async def test_empty_registry_is_503():
    # `patch.dict(..., clear=True)` empties and restores the SAME dict. Swapping
    # the object (`patch(..., {})`) would leave `flow.factory`, which captured
    # the original dict at import, looking at a registry this test never
    # cleared — and any `register_node` run during the patch window would be
    # lost, making the result depend on the order of the files in the suite.
    with _no_session(), patch.dict("flow.registry.NODE_REGISTRY", clear=True):
        with pytest.raises(HTTPException) as exc:
            await validar_definicao(
                {"nodes": [_no("n1", "ReadGeoJSON")], "edges": []}, user_id=USUARIO, workspace_id=None,
            )

    assert exc.value.status_code == 503


# ══════════════════════════════════════════════════════════════════════════════
# Source catalog — warnings without network
# ══════════════════════════════════════════════════════════════════════════════

_UNKNOWN_SOURCE_WARNING = {
    "code": "unknown_source", "severity": "warning", "node_id": "n1", "edge": None,
    "message": "nó 'WFS' (id=n1) aponta para url+typeName que não estão no catálogo.",
}


def _wfs(id_hash="n1"):
    return _no(id_hash, "WFS", url="https://geoserver.funai.gov.br/geoserver/ows", typeName="Funai:tis_poligonais")


def _db_for_the_catalog(conferir):
    """Fake session + what validation with a workspace queries, with the catalog stubbed."""
    return (
        _fake_session(),
        patch(f"{NS}.get_workspace_member_role", AsyncMock(return_value="editor")),
        patch(f"{NS}.disabled_names", AsyncMock(return_value=set())),
        patch(f"{NS}.validate_subworkflow_references_against_db", AsyncMock(return_value=[])),
        patch(f"{NS}.fontes_service.conferir_fontes_da_definicao", conferir),
    )


async def test_wfs_outside_the_catalog_becomes_warning_and_keeps_ok():
    from contextlib import ExitStack

    from app.services.validate_service import HINT_SOURCES

    conferir = AsyncMock(return_value=[_UNKNOWN_SOURCE_WARNING])
    with ExitStack() as pilha:
        for p in _db_for_the_catalog(conferir):
            pilha.enter_context(p)
        pilha.enter_context(_fake_simulation())
        saida = await validar_definicao(
            {"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1",
        )

    report = saida["__report__"]
    assert report["ok"] is True and report["errors"] == []
    assert _UNKNOWN_SOURCE_WARNING in report["warnings"]
    assert HINT_SOURCES in report["hints"]
    # The catalog receives the nodes in the executor's format and the WFS
    # descriptor (with `source_kind`), in the validation's workspace.
    nos, descritores, ws = conferir.await_args.args[1:]
    assert nos[0]["name"] == "WFS" and descritores["WFS"]["source_kind"] == "wfs" and ws == "ws-1"


async def test_cataloged_source_produces_no_warning_or_hint():
    from contextlib import ExitStack

    from app.services.validate_service import HINT_SOURCES

    with ExitStack() as pilha:
        for p in _db_for_the_catalog(AsyncMock(return_value=[])):
            pilha.enter_context(p)
        pilha.enter_context(_fake_simulation())
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1")

    report = saida["__report__"]
    assert report["warnings"] == [] and HINT_SOURCES not in report["hints"]


async def test_unavailable_catalog_does_not_break_validation():
    from contextlib import ExitStack

    with ExitStack() as pilha:
        for p in _db_for_the_catalog(AsyncMock(side_effect=RuntimeError("catálogo fora"))):
            pilha.enter_context(p)
        pilha.enter_context(_fake_simulation())
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id="ws-1")

    assert saida["__report__"]["ok"] is True and saida["__report__"]["warnings"] == []


async def test_without_workspace_the_catalog_is_not_queried():
    """Without proven membership there is no workspace catalog to look at — and no session."""
    conferir = AsyncMock(return_value=[_UNKNOWN_SOURCE_WARNING])
    with _no_session(), _fake_simulation(), patch(f"{NS}.fontes_service.conferir_fontes_da_definicao", conferir):
        saida = await validar_definicao({"nodes": [_wfs()], "edges": []}, user_id=USUARIO, workspace_id=None)

    conferir.assert_not_awaited()
    assert saida["__report__"]["warnings"] == []
