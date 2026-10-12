# tests/integration/test_salvar_arquivo_no_executor.py
"""
"Salvar arquivo" running on the real EXECUTOR, wired to the next node.

What only shows up when assembling the graph: the executor compares the keys
the node returns with the declared `outputs`. Nested under "output", every run
showed schema drift, and an edge taking `artifact_s3_key` delivered nothing to
the node after it.
"""
import asyncio
from unittest.mock import MagicMock, patch

CAMADA = (
    "r = gpd.GeoDataFrame({'nome': ['A', 'B']}, "
    "geometry=gpd.points_from_xy([-63.9, -63.8], [-8.7, -8.8]), crs='EPSG:4326')"
)


def _run(nodes, edges):
    from flow.executor import WorkflowExecutor

    publisher = MagicMock()
    publisher.publish_event = MagicMock()

    def fake_persist(**kwargs):
        return f"artifacts/ws-1/t/{kwargs['filename']}", {
            "output_key": kwargs["label"], "format": kwargs["fmt"], "filename": kwargs["filename"],
        }

    with patch("flow.nodes.outputs.save_file.persistir_artefato", side_effect=fake_persist):
        resultado = asyncio.run(
            WorkflowExecutor({"nodes": nodes, "edges": edges}, task_id="t",
                             publisher=publisher, workspace_id="ws-1").run()
        )
    return resultado, publisher


def _completion_event(publisher, node_id):
    for chamada in publisher.publish_event.call_args_list:
        args = chamada.args
        if len(args) >= 7 and args[1] == node_id and isinstance(args[6], dict) \
                and "output_keys" in args[6]:
            return args[2], args[6]
    raise AssertionError(f"sem evento de conclusao para '{node_id}'")


def test_the_next_node_receives_the_saved_files_key():
    resultado, publisher = _run(
        [
            {"id": "a", "type": "action", "name": "PythonScript",
             "properties": {"code": CAMADA, "output_vars": "r", "timeout": 20}},
            {"id": "s", "type": "output", "name": "SaveFile",
             "properties": {"label": "obras", "formato": "csv"}},
            {"id": "b", "type": "action", "name": "PythonScript",
             "properties": {"code": "chave_recebida = chave", "output_vars": "chave_recebida", "timeout": 20}},
        ],
        [
            {"source": "a", "target": "s", "from_key": "r"},
            {"source": "s", "target": "b", "from_key": "artifact_s3_key", "to_key": "chave"},
        ],
    )

    status, extra = _completion_event(publisher, "s")
    assert status != "failed"
    assert "schema_drift" not in extra, extra.get("schema_drift")
    assert resultado["b"]["chave_recebida"] == "artifacts/ws-1/t/obras.csv"
