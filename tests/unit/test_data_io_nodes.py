"""
Padronizacao simetrica Entrada/Saida de Dados:
- DataOutput: o toggle isPublic mapeia para credential_id (publico = sem
  credencial; nao-publico = exige credencial), sem tocar o banco.

Resolucao de Drive/Artefatos (entrada) vive em test_drive_resolver.py.
"""
from unittest.mock import patch

import pytest


# ── DataOutput: toggle isPublic → credential_id ───────────────────────────────

def _make_data_output(params: dict):
    from flow.nodes.outputs.data_output import DataOutput
    node = DataOutput("n1", params)
    node._task_id = "task-1"
    node._workspace_id = "ws-1"
    return node


@pytest.mark.asyncio
async def test_dataoutput_publico_ignora_credencial():
    node = _make_data_output({
        "label": "resultado", "context": "artifacts",
        "isPublic": True, "credential_id": "cred-xyz",
    })
    captured = {}

    def _fake_upload(**kwargs):
        captured.update(kwargs)
        return "artifacts/ws-1/task-1/resultado.json", {"local_fallback": False}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_fake_upload):
        await node.execute({"in": {"a": 1}})

    # Publico → nao propaga credencial, mesmo se preenchida.
    assert captured["credential_id"] is None
    assert captured["create_drive_entry"] is False


@pytest.mark.asyncio
async def test_dataoutput_nao_publico_exige_credencial():
    node = _make_data_output({
        "label": "resultado", "context": "artifacts",
        "isPublic": False, "credential_id": "",
    })
    with pytest.raises(ValueError, match="credencial"):
        await node.execute({"in": {"a": 1}})


@pytest.mark.asyncio
async def test_dataoutput_nao_publico_propaga_credencial():
    node = _make_data_output({
        "label": "resultado", "context": "artifacts",
        "isPublic": False, "credential_id": "cred-xyz",
    })
    captured = {}

    def _fake_upload(**kwargs):
        captured.update(kwargs)
        return "artifacts/ws-1/task-1/resultado.json", {"local_fallback": False}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_fake_upload):
        await node.execute({"in": {"a": 1}})

    assert captured["credential_id"] == "cred-xyz"


@pytest.mark.asyncio
async def test_dataoutput_drive_nunca_usa_credencial():
    node = _make_data_output({
        "label": "resultado", "context": "drive",
        "isPublic": False, "credential_id": "cred-xyz",
    })
    captured = {}

    def _fake_upload(**kwargs):
        captured.update(kwargs)
        return "drive/ws-1/resultado.json", {"local_fallback": False}

    with patch("flow.nodes.outputs.data_output.upload_artifact_to_minio", side_effect=_fake_upload):
        await node.execute({"in": {"a": 1}})

    # Contexto Drive → credencial irrelevante; create_drive_entry True.
    assert captured["credential_id"] is None
    assert captured["create_drive_entry"] is True
