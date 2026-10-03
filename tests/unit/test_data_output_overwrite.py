"""DataOutput's "overwrite" option on the Drive.

Without it, a scheduled DataOutput piled up one copy per run — all with the
same name on the Drive, and whoever consumed the file by id kept reading the
first version.
"""
from unittest.mock import patch

import pytest


def _make_data_output(params: dict):
    from flow.nodes.outputs.data_output import DataOutput
    node = DataOutput("n1", params)
    node._task_id = "task-1"
    node._workspace_id = "ws-1"
    return node


async def _run(params: dict) -> dict:
    node = _make_data_output(params)
    captured: dict = {}

    def _fake_upload(**kwargs):
        captured.update(kwargs)
        return "artifacts/ws-1/task-1/resultado.json", {"local_fallback": False}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_fake_upload):
        await node.execute({"in": {"a": 1}})
    return captured


@pytest.mark.asyncio
async def test_overwrite_propagated_in_drive_context():
    captured = await _run({"label": "resultado", "context": "drive", "overwrite": True})

    assert captured["create_drive_entry"] is True
    assert captured["overwrite"] is True


@pytest.mark.asyncio
async def test_overwrite_off_by_default():
    """Conservative default: whoever configures nothing keeps the old behavior."""
    captured = await _run({"label": "resultado", "context": "drive"})

    assert captured["overwrite"] is False


@pytest.mark.asyncio
async def test_overwrite_ignored_for_artifacts():
    """An artifact already has its own s3_key per run (includes task_id) — no collision."""
    captured = await _run({"label": "resultado", "context": "artifacts", "overwrite": True})

    assert captured["create_drive_entry"] is False
    assert captured["overwrite"] is False


@pytest.mark.asyncio
async def test_overwrite_as_string_is_rejected_in_validation():
    """type=boolean requires a real bool — a string does not pass validate().

    Documents why the node does not coerce "true"/"false": the parameter never
    arrives here as a string.
    """
    with pytest.raises(ValueError, match="booleano"):
        await _run({"label": "resultado", "context": "drive", "overwrite": "true"})
