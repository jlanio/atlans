# tests/unit/test_save_to_s3_credencial.py
"""SaveToS3 uses the vault's `s3` credential; the secret no longer lives in the definition.

Before, the `s3` type existed in the vault (with a connection test) and no node
used it: SaveToS3 asked for an `awsSecretAccessKey` typed into the node, stored in
plain text. And since the secret lists compare the exact NAME, the field escaped
the lint, the read redaction and the log mask.
"""
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point

import flow.nodes.outputs.save_to_s3  # noqa: F401 — registers the node
from app.core.utils.redacao import definition_contains_secret, redact_definition
from app.services.credential_resolver import (
    inject_credentials,
    receiving_property,
    s3_auth_from_credential,
)
from flow.factory import _without_secrets
from flow.nodes.outputs.save_to_s3 import SaveToS3Node
from flow.utils.definition_lint import lint_definition

CID = "5d1e9a3c-7b24-4f60-8c11-2e9f0a4b6d73"
SEGREDO = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # pragma: allowlist secret

_CRED_S3 = {
    "type": "s3", "access_key_id": "AKIAEXEMPLO", "secret_access_key": SEGREDO,
    "region": "sa-east-1", "bucket": "bucket-da-credencial", "endpoint_url": "",
    "expires_at": "2099-01-01T00:00:00Z",
}


def _definition(**props):
    return {"nodes": [{"id": "n1", "name": "SaveToS3", "type": "output",
                       "properties": {"key": "saida/a.geojson", "credential_id": CID, **props}}]}


# ── Resolution ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_s3_credential_enters_s3_auth_only_with_catalog_fields():
    saida = await inject_credentials(_definition(), pre_resolved={CID: dict(_CRED_S3)})
    props = saida["nodes"][0]["properties"]
    assert props["s3_auth"] == {
        "access_key_id": "AKIAEXEMPLO", "secret_access_key": SEGREDO,
        "region": "sa-east-1", "bucket": "bucket-da-credencial",
    }
    assert "credential_id" not in props


@pytest.mark.asyncio
async def test_legacy_use_webhook_token_leaves_the_id_to_protect_the_copy():
    saida = await inject_credentials(
        _definition(registerArtifact=True), pre_resolved={CID: {"type": "webhook_token", "token": "T"}},
    )
    props = saida["nodes"][0]["properties"]
    assert props["credential_id"] == CID and "s3_auth" not in props


def test_s3_credential_property_and_shape():
    assert receiving_property("s3") == "s3_auth"
    assert s3_auth_from_credential({"type": "postgresql", "connectionString": "x"}) is None


# ── Execution ────────────────────────────────────────────────────────────────


def _gdf():
    return gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")


def _boto3():
    """`boto3.session.Session` doubled; returns (patch, the session's `client`)."""
    sessao = MagicMock()
    return patch("boto3.session.Session", sessao), sessao.return_value.client


async def _execute(**props):
    dublê, fabrica = _boto3()
    cliente = fabrica.return_value
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "saida/a.geojson", **props})
        saida = await no.execute({"in": _gdf()})
    return fabrica, cliente, saida


@pytest.mark.asyncio
async def test_run_uses_the_injected_credential_and_its_default_bucket():
    s3_auth = s3_auth_from_credential(dict(_CRED_S3))
    fabrica, cliente, saida = await _execute(s3_auth=s3_auth)
    fabrica.assert_called_once_with(
        "s3", region_name="sa-east-1", aws_access_key_id="AKIAEXEMPLO", aws_secret_access_key=SEGREDO,
    )
    assert cliente.put_object.call_args.kwargs["Bucket"] == "bucket-da-credencial"
    assert saida["output"]["s3Uri"] == "s3://bucket-da-credencial/saida/a.geojson"


@pytest.mark.asyncio
async def test_node_bucket_and_region_override_the_credentials():
    s3_auth = s3_auth_from_credential(dict(_CRED_S3))
    fabrica, cliente, _ = await _execute(s3_auth=s3_auth, bucketName="do-no", region="us-west-2")
    assert fabrica.call_args.kwargs["region_name"] == "us-west-2"
    assert cliente.put_object.call_args.kwargs["Bucket"] == "do-no"


@pytest.mark.asyncio
async def test_credential_endpoint_reaches_boto3():
    s3_auth = {**s3_auth_from_credential(dict(_CRED_S3)), "endpoint_url": "https://s3.compativel.exemplo"}
    with patch("flow.utils.geo_helpers.validate_url_ssrf", return_value=("203.0.113.9", "s3.compativel.exemplo")):
        fabrica, _, _ = await _execute(s3_auth=s3_auth)
    assert fabrica.call_args.kwargs["endpoint_url"] == "https://s3.compativel.exemplo"


@pytest.mark.asyncio
async def test_internal_endpoint_is_rejected_as_in_the_credential_test():
    s3_auth = {**s3_auth_from_credential(dict(_CRED_S3)), "endpoint_url": "http://169.254.169.254"}
    dublê, fabrica = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson", "s3_auth": s3_auth})
        with pytest.raises(ValueError):
            await no.execute({"in": _gdf()})
    fabrica.assert_not_called()


@pytest.mark.asyncio
async def test_old_workflow_with_keys_in_the_node_keeps_the_same_identity():
    """Without an S3 credential, the old fields are still read: silently switching
    to the executor's default chain would change WHO writes to the bucket."""
    fabrica, _, _ = await _execute(
        bucketName="b", awsAccessKeyId="AKIAANTIGA", awsSecretAccessKey="segredo-antigo",  # pragma: allowlist secret
    )
    fabrica.assert_called_once_with(
        "s3", region_name="us-east-1", aws_access_key_id="AKIAANTIGA", aws_secret_access_key="segredo-antigo",
    )


@pytest.mark.asyncio
async def test_without_credential_or_keys_the_default_chain_applies():
    fabrica, _, _ = await _execute(bucketName="b")
    fabrica.assert_called_once_with("s3", region_name="us-east-1")


@pytest.mark.asyncio
async def test_no_bucket_in_node_or_credential_refuses():
    dublê, _ = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson"})
        with pytest.raises(ValueError, match="bucketName"):
            await no.execute({"in": _gdf()})


# ── The old field is a secret in every list ─────────────────────────────────


def test_secret_key_typed_in_the_node_is_rejected_on_save():
    caminhos = definition_contains_secret(_definition(awsSecretAccessKey=SEGREDO))
    assert any(c.endswith("awsSecretAccessKey") for c in caminhos)


def test_secret_key_typed_in_the_node_is_flagged_by_lint():
    no = {"id": "n1", "name": "SaveToS3", "type": "output",
          "parameters": {"key": "a.geojson", "awsSecretAccessKey": SEGREDO}}
    relatorio = lint_definition([no], [], registry_names={"SaveToS3"})
    diagnostics = [d for d in relatorio.errors if d.code == "secret_in_definition"]
    assert diagnostics and "awsSecretAccessKey" in diagnostics[0].message
    assert SEGREDO not in diagnostics[0].message


def test_read_redacts_the_secret_key_and_s3_auth():
    saida = redact_definition(_definition(awsSecretAccessKey=SEGREDO, s3_auth={"secret_access_key": SEGREDO}))
    assert SEGREDO not in str(saida)


def test_factory_log_masks_the_secret_key_and_s3_auth():
    masked = _without_secrets({"awsSecretAccessKey": SEGREDO, "s3_auth": {"secret_access_key": SEGREDO}, "key": "k"})
    assert masked == {"awsSecretAccessKey": "***", "s3_auth": "***", "key": "k"}


# ── Validation: severity according to the credential's use ─────────────────


def _check(tipo: str):
    from app.services.validate_service import _check_credentials
    from flow.utils.definition_lint import LintReport

    rel = LintReport()
    nos = [{"id": "n1", "name": "SaveToS3", "parameters": {"credential_id": CID}}]
    descriptors = {"SaveToS3": SaveToS3Node.description()}
    _check_credentials(rel, nos, descriptors, {CID: (tipo, "expirada", "2020-01-01T00:00:00Z")})
    return rel


def test_expired_s3_credential_is_an_error_because_the_node_consumes_it():
    rel = _check("s3")
    assert [d.code for d in rel.errors] == ["credential_expired"]


def test_expired_legacy_use_webhook_token_stays_a_warning():
    rel = _check("webhook_token")
    assert not rel.errors
    assert [d.code for d in rel.warnings] == ["credential_expired"]


def _check_with(tipo: str, register_artifact):
    from app.services.validate_service import _check_credentials
    from flow.utils.definition_lint import LintReport

    rel = LintReport()
    nos = [{"id": "n1", "name": "SaveToS3",
            "parameters": {"credential_id": CID, "registerArtifact": register_artifact}}]
    _check_credentials(rel, nos, {"SaveToS3": SaveToS3Node.description()}, {CID: (tipo, "valida", None)})
    return rel


@pytest.mark.parametrize("ligado", [True, "true"])
def test_s3_credential_with_registered_copy_warns_the_copy_is_unprotected(ligado):
    """The same field serves both things: choosing the S3 one removes the Webhook Token from the copy."""
    rel = _check_with("s3", ligado)
    assert [d.code for d in rel.warnings] == ["artifact_copy_unprotected"]
    assert not rel.errors


def test_without_registered_copy_or_with_token_there_is_no_warning():
    assert not _check_with("s3", False).warnings
    assert not _check_with("webhook_token", True).warnings


# ── Credential that did not resolve ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_unresolved_s3_credential_without_copy_refuses_instead_of_switching_identity():
    """Without `s3_auth` and with the id in place, the upload went out with the
    executor's default chain — another identity, silently. Now it refuses, like HttpRequest."""
    dublê, fabrica = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson", "bucketName": "b", "credential_id": CID})
        with pytest.raises(ValueError, match="não pôde ser resolvida"):
            await no.execute({"in": _gdf()})
    fabrica.assert_not_called()


@pytest.mark.asyncio
async def test_old_token_without_registered_copy_drops_at_resolution_and_the_workflow_continues():
    """A Webhook Token left over in the node with the copy turned off protects nothing:
    the server removes it, and the node does not confuse that with an unresolved S3 credential."""
    saida = await inject_credentials(
        _definition(registerArtifact=False), pre_resolved={CID: {"type": "webhook_token", "token": "T"}},
    )
    props = saida["nodes"][0]["properties"]
    assert "credential_id" not in props and "s3_auth" not in props
    fabrica, _, _ = await _execute(bucketName="b", **{k: v for k, v in props.items() if k != "key"})
    fabrica.assert_called_once()
