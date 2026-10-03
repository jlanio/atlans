# tests/unit/test_credential_resolver_wfs.py
"""The WFS node's credentials arrive in `http_auth`, like HttpRequest's.

Before, the "wfs" credential was resolved, had its `credential_id` removed and
vanished with nothing in its place — the node went out anonymous. Now it and
the new `geoserver_authkey` are injected, with only the fields that
authenticate (the closed list: no `expires_at` crossing over to the executor).
"""
import pytest

from app.services.credential_resolver import http_auth_from_credential, inject_credentials

pytestmark = pytest.mark.asyncio

CID = "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05"


def _definition():
    return {"nodes": [{"id": "n1", "name": "WFS", "type": "datasource",
                       "properties": {"url": "https://geo.x/ows", "typeName": "ns:c", "credential_id": CID}}]}


async def test_geoserver_authkey_goes_in_http_auth():
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K", "parameter": "authkey",
                       "location": "url", "expires_at": "2027-01-01T00:00:00Z"}}
    saida = await inject_credentials(_definition(), pre_resolved=resolvido)
    props = saida["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K", "parameter": "authkey", "location": "url"}
    assert "credential_id" not in props


async def test_uppercase_id_is_also_resolved():
    # The resolver returns the canonical id (lowercase); stored in uppercase on
    # the node, it matched nothing and the credential vanished without warning —
    # while the /validate guard, which converts to UUID, accepted it.
    definicao = _definition()
    definicao["nodes"][0]["properties"]["credential_id"] = CID.upper()
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    props = saida["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K"} and "credential_id" not in props


async def test_wfs_basic_credential_no_longer_disappears():
    resolvido = {CID: {"type": "wfs", "username": "u", "password": "p"}}
    saida = await inject_credentials(_definition(), pre_resolved=resolvido)
    assert saida["nodes"][0]["properties"]["http_auth"] == {"type": "wfs", "username": "u", "password": "p"}


async def test_the_stored_definition_does_not_receive_the_secret():
    definicao = _definition()
    await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    assert "http_auth" not in definicao["nodes"][0]["properties"]  # only the dispatch copy


async def test_credential_http_auth_only_for_request_signers():
    # The database one becomes `connectionString`, not `http_auth`: the WFS listing rejects it.
    assert http_auth_from_credential({"type": "postgresql", "connectionString": "postgresql://h/db"}) is None
    assert http_auth_from_credential(
        {"type": "geoserver_authkey", "token": "K", "location": "header", "expires_at": "2027-01-01T00:00:00Z"}
    ) == {"type": "geoserver_authkey", "token": "K", "location": "header"}


# ── The credential type against what the node declares ───────────────────────
# Only the screen filters by type; via the API and the assistant any type arrives.

import flow.nodes.datasource.wfs  # noqa: E402,F401 — registers the WFS node


@pytest.mark.parametrize("cred", [
    {"type": "postgresql", "connectionString": "postgresql://leitor:senha@h/db"},  # pragma: allowlist secret
    {"type": "smtp", "host": "smtp.x", "password": "p"},
    {"type": "http_bearer", "token": "T"},
])
async def test_type_the_node_does_not_accept_injects_nothing_and_keeps_the_id(cred):
    saida = await inject_credentials(_definition(), pre_resolved={CID: cred})
    props = saida["nodes"][0]["properties"]
    # The node rejects with "não pôde ser resolvida" (could not be resolved)
    # instead of querying anonymously — and the database DSN does not travel
    # to a WFS node.
    assert props["credential_id"] == CID
    assert "connectionString" not in props and "http_auth" not in props


async def test_the_type_decides_not_the_dsn_left_in_data():
    # A credential that used to be a database one and became an authkey: the edit
    # changed the type and kept the fields, and the old `connectionString` won.
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K",
                       "connectionString": "postgresql://leitor:senha@h/db"}}  # pragma: allowlist secret
    props = (await inject_credentials(_definition(), pre_resolved=resolvido))["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K"}
    assert "connectionString" not in props and "credential_id" not in props


async def test_database_node_with_authkey_credential_receives_nothing_and_keeps_the_id():
    import flow.nodes.datasource.database_spatial_query  # noqa: F401 — registers the node
    definicao = {"nodes": [{"id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
                            "properties": {"credential_id": CID, "query": "SELECT 1"}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "geoserver_authkey", "token": "K"}})
    props = saida["nodes"][0]["properties"]
    assert props["credential_id"] == CID and "http_auth" not in props and "connectionString" not in props


async def test_node_name_only_in_data_is_also_checked():
    # The editor stores name and properties in `data`; the type is checked the same way.
    definicao = {"nodes": [{"id": "n1", "type": "datasource",
                            "data": {"name": "WFS", "properties": {"url": "https://geo.x/ows", "credential_id": CID}}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "postgresql", "connectionString": "postgresql://h/db"}})
    props = saida["nodes"][0]["data"]["properties"]
    assert props["credential_id"] == CID and "connectionString" not in props


async def test_only_the_type_fields_travel():
    # A credential that used to be Basic and became an authkey still carries user
    # and password in `data`: only what the catalog declares for the type goes
    # to the executor.
    resolvido = {CID: {"type": "geoserver_authkey", "token": "K", "username": "u", "password": "p", "location": "header"}}
    props = (await inject_credentials(_definition(), pre_resolved=resolvido))["nodes"][0]["properties"]
    assert props["http_auth"] == {"type": "geoserver_authkey", "token": "K", "location": "header"}
    assert http_auth_from_credential({"type": "wfs", "username": "u", "password": "p", "token": "T"}) == {
        "type": "wfs", "username": "u", "password": "p",
    }
    assert http_auth_from_credential({"type": "http_bearer", "token": "T", "password": "p"}) == {"type": "http_bearer", "token": "T"}


async def test_node_that_does_not_declare_the_property_does_not_receive_the_credential(monkeypatch):
    # A node that accepts the type but does not declare `http_auth`: `validate()`
    # discards what is not in the descriptor, and the node lost the credential
    # AND the id — it went out anonymous with no one warning. With the id in
    # place, it rejects.
    from flow.registry import NODE_REGISTRY

    class _NoHttpAuth:
        @classmethod
        def description(cls):
            return {"name": "SemHttpAuth", "properties": [
                {"name": "credential_id", "type": "credential", "credential_types": ["http_bearer"]},
            ]}

    monkeypatch.setitem(NODE_REGISTRY, "SemHttpAuth", _NoHttpAuth)
    definicao = {"nodes": [{"id": "n1", "name": "SemHttpAuth", "type": "action", "properties": {"credential_id": CID}}]}
    props = (await inject_credentials(definicao, pre_resolved={CID: {"type": "http_bearer", "token": "T"}}))["nodes"][0]["properties"]
    assert props == {"credential_id": CID}


async def test_non_public_dataoutput_keeps_the_credential_id():
    # The webhook_token does not become a DSN nor HTTP authentication: DataOutput
    # uses the id ITSELF to protect the artifact. Removing it made the node
    # reject with "exige uma credencial" (requires a credential) with the
    # credential chosen.
    import flow.nodes.outputs.data_output  # noqa: F401 — registers the node
    definicao = {"nodes": [{"id": "n1", "name": "DataOutput", "type": "output",
                            "properties": {"isPublic": False, "credential_id": CID}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "webhook_token", "token": "T"}})
    assert saida["nodes"][0]["properties"]["credential_id"] == CID


async def test_node_outside_the_registry_behaves_as_before():
    definicao = {"nodes": [{"id": "n1", "name": "NoQueNaoExiste", "type": "datasource",
                            "properties": {"credential_id": CID}}]}
    saida = await inject_credentials(definicao, pre_resolved={CID: {"type": "postgresql", "connectionString": "postgresql://h/db"}})
    props = saida["nodes"][0]["properties"]
    assert props["connectionString"] == "postgresql://h/db" and "credential_id" not in props
