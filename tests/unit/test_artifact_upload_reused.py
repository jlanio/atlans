"""HTTP seam between the executor and the Drive on artifact upload.

There was a node test (propagates `overwrite`) and a service test (reuses the
row), but nothing covering the middle: the POST body that connects the two. A
field forgotten there went unnoticed by both green ends.

Also covers the way back: `reused` says what the SERVER did, and it is what
lets the node log the outcome instead of the intent.
"""
from unittest.mock import MagicMock, patch

import pytest

from flow.utils.artifact_helpers import upload_artifact_to_minio


def _response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


class _Httpx:
    """httpx double: keeps the POST body and responds like the server."""

    def __init__(self, upload_payload: dict):
        self.upload_payload = upload_payload
        self.posts: list[tuple[str, dict]] = []

    def post(self, url, json=None, **kwargs):
        self.posts.append((url, json or {}))
        if "executor-upload-url" in url:
            return _response(self.upload_payload)
        return _response({})

    def put(self, *args, **kwargs):
        return _response({})

    @property
    def upload_body(self) -> dict:
        return next(corpo for url, corpo in self.posts if "executor-upload-url" in url)


def _upload(overwrite: bool, server_response: dict) -> tuple[dict, _Httpx]:
    fake = _Httpx(server_response)
    with patch("httpx.post", side_effect=fake.post), \
         patch("httpx.put", side_effect=fake.put), \
         patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://api", {}, False)):
        _s3_key, meta = upload_artifact_to_minio(
            content=b"{}", filename="resultado.geojson",
            content_type="application/geo+json",
            workspace_id="ws-1", task_id="task-1",
            create_drive_entry=True, overwrite=overwrite,
        )
    return meta, fake


REUSE_RESPONSE = {"upload_url": "https://minio/put", "id_hash": "f-1",
                  "s3_key": "drive/ws-1/antigo.geojson", "reused": True}
NEW_RESPONSE = {"upload_url": "https://minio/put", "id_hash": "f-2",
                 "s3_key": "artifacts/ws-1/task-1/resultado.geojson", "reused": False}


def test_overwrite_goes_in_the_post_body():
    """The link no test covered."""
    _meta, fake = _upload(overwrite=True, server_response=REUSE_RESPONSE)

    assert fake.upload_body["overwrite"] is True
    assert fake.upload_body["filename"] == "resultado.geojson"
    assert fake.upload_body["workspace_id"] == "ws-1"


def test_overwrite_off_is_also_sent():
    _meta, fake = _upload(overwrite=False, server_response=NEW_RESPONSE)

    assert fake.upload_body["overwrite"] is False


def test_reused_from_server_reaches_meta():
    meta, _fake = _upload(overwrite=True, server_response=REUSE_RESPONSE)

    assert meta["drive_reused"] is True
    assert meta["drive_file_id"] == "f-1"


def test_requesting_overwrite_without_finding_file_does_not_become_reuse():
    """The case the node's old message announced as an overwrite."""
    meta, _fake = _upload(overwrite=True, server_response=NEW_RESPONSE)

    assert meta["drive_reused"] is False


def test_server_s3_key_prevails():
    """No reuso o servidor devolve a s3_key ORIGINAL — o PUT substitui o objeto."""
    meta, _fake = _upload(overwrite=True, server_response=REUSE_RESPONSE)

    assert meta["s3_key"] == "drive/ws-1/antigo.geojson"


def test_old_server_without_the_field_does_not_claim_reuse():
    without_field = {"upload_url": "https://minio/put", "id_hash": "f-3", "s3_key": "k"}

    meta, _fake = _upload(overwrite=True, server_response=without_field)

    assert meta["drive_reused"] is False


def test_local_fallback_does_not_claim_reuse():
    """Upload failed: nothing went to the Drive, so nothing was overwritten."""
    with patch("httpx.post", side_effect=RuntimeError("sem rede")), \
         patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://api", {}, False)), \
         patch("flow.utils.artifact_helpers._save_local_fallback", return_value="/tmp/x"):
        _s3_key, meta = upload_artifact_to_minio(
            content=b"{}", filename="resultado.geojson", workspace_id="ws-1",
            task_id="task-1", create_drive_entry=True, overwrite=True,
        )

    assert meta["local_fallback"] is True
    assert meta["drive_reused"] is False


def test_workflow_without_drive_does_not_claim_reuse():
    fake = _Httpx({"upload_url": "https://minio/put"})
    with patch("httpx.post", side_effect=fake.post), \
         patch("httpx.put", side_effect=fake.put), \
         patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://api", {}, False)):
        _s3_key, meta = upload_artifact_to_minio(
            content=b"{}", filename="r.json", workspace_id="ws-1",
            task_id="task-1", create_drive_entry=False, overwrite=True,
        )

    assert meta["drive_reused"] is False
    # An artifact does not go through the endpoint that creates WorkspaceFile.
    assert all("executor-upload-url" not in url for url, _ in fake.posts)


# ── Node log: asserts the outcome, not the intent ────────────────────────────

async def _logs_do_no(params: dict, extra_meta: dict) -> list[str]:
    from flow.nodes.outputs.data_output import DataOutput

    node = DataOutput("n1", params)
    node._task_id, node._workspace_id = "task-1", "ws-1"
    linhas: list[str] = []

    def _fake_upload(**_kwargs):
        return "artifacts/ws-1/task-1/r.json", {"local_fallback": False, **extra_meta}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_fake_upload), \
         patch.object(DataOutput, "log", lambda self, m: linhas.append(m)):
        await node.execute({"in": {"a": 1}})
    return linhas


@pytest.mark.asyncio
async def test_log_claims_overwrite_only_when_it_happened():
    linhas = await _logs_do_no(
        {"label": "r", "context": "drive", "overwrite": True}, {"drive_reused": True},
    )

    assert any("sobrescrito" in linha.lower() for linha in linhas)


@pytest.mark.asyncio
async def test_log_says_it_created_new_when_there_was_nothing_to_overwrite():
    """Regression: the old message announced an overwrite whenever the option
    was on — precisely the case that needed to be visible."""
    linhas = await _logs_do_no(
        {"label": "r", "context": "drive", "overwrite": True}, {"drive_reused": False},
    )

    texto = " ".join(linhas).lower()
    assert "sobrescrito" not in texto
    assert "novo" in texto
