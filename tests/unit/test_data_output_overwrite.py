"""Opção "sobrescrever" do DataOutput no Drive.

Sem ela, um DataOutput agendado acumulava uma cópia por execução — todas com o
mesmo nome no Drive, e quem consumia o arquivo por id continuava lendo a
primeira versão.
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
async def test_overwrite_propagado_no_contexto_drive():
    captured = await _run({"label": "resultado", "context": "drive", "overwrite": True})

    assert captured["create_drive_entry"] is True
    assert captured["overwrite"] is True


@pytest.mark.asyncio
async def test_overwrite_desligado_por_padrao():
    """Default conservador: quem não configurar nada mantém o comportamento antigo."""
    captured = await _run({"label": "resultado", "context": "drive"})

    assert captured["overwrite"] is False


@pytest.mark.asyncio
async def test_overwrite_ignorado_em_artefatos():
    """Artefato já tem s3_key própria por execução (inclui task_id) — não colide."""
    captured = await _run({"label": "resultado", "context": "artifacts", "overwrite": True})

    assert captured["create_drive_entry"] is False
    assert captured["overwrite"] is False


@pytest.mark.asyncio
async def test_overwrite_como_string_e_rejeitado_na_validacao():
    """type=boolean exige bool de verdade — string não passa pelo validate().

    Documenta por que o nó não coage "true"/"false": o parâmetro nunca chega
    como string até aqui.
    """
    with pytest.raises(ValueError, match="booleano"):
        await _run({"label": "resultado", "context": "drive", "overwrite": "true"})
