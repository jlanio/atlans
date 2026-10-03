# tests/integration/test_carta_no_executor.py
"""
The image map running on the real EXECUTOR, not the isolated node.

What only shows up when assembling the graph: the two layers arriving via each
edge's `to_key` (named ports), the anonymous edge of a single port (the
parent's dict spread), and the completion event without `schema_drift` — the
flat keys the node returns match the declared `outputs`.
"""
import asyncio
from unittest.mock import MagicMock, patch


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

CAMADA = (
    "r = gpd.GeoDataFrame({'a': [1, 2]}, "
    "geometry=gpd.points_from_xy([%(x)s, %(x)s + 0.1], [-9.0, -9.1]), crs='EPSG:4326')"
)


def _script(node_id, x):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": CAMADA % {"x": x}, "output_vars": "r", "timeout": 20}}


def _image_map(node_id, ports):
    return {"id": node_id, "type": "output", "name": "CartaImagem",
            "properties": {"ports": ports, "dpi": 72, "titulo": "Carta do executor"}}


def _run(nodes, edges):
    from flow.executor import WorkflowExecutor

    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    capturado = {}

    def fake_persist(**kwargs):
        capturado.update(kwargs)
        return f"artifacts/ws-1/t/{kwargs['filename']}", {
            "output_key": kwargs["label"], "format": kwargs["fmt"],
            "filename": kwargs["filename"], "size_bytes": len(kwargs["content"]),
        }

    with patch("flow.nodes.outputs.carta_imagem.persistir_artefato", side_effect=fake_persist):
        resultado = asyncio.run(
            WorkflowExecutor({"nodes": nodes, "edges": edges}, task_id="t",
                             publisher=publisher, workspace_id="ws-1").run()
        )
    return resultado, capturado, publisher


def _completion_event(publisher, node_id):
    """The node lifecycle event: `publish_event(task_id, node_id, status,
    ts, duration, error, extra, ...)` — `extra` carries `output_keys` and, only
    when there is drift, `schema_drift`."""
    for chamada in publisher.publish_event.call_args_list:
        args = chamada.args
        if len(args) >= 7 and args[1] == node_id and isinstance(args[6], dict) \
                and "output_keys" in args[6]:
            return args[2], args[6]
    raise AssertionError(f"sem evento de conclusao para '{node_id}'")


def test_two_ports_each_receive_one_layer_via_to_key():
    resultado, capturado, publisher = _run(
        [_script("a", -63.0), _script("b", -62.0), _image_map("c", ["focos", "municipios"])],
        [{"source": "a", "target": "c", "from_key": "r", "to_key": "focos"},
         {"source": "b", "target": "c", "from_key": "r", "to_key": "municipios"}],
    )
    assert resultado["c"]["camadas"] == 2
    assert capturado["features"] == 4
    assert capturado["content"].startswith(PNG_SIGNATURE)
    assert capturado["filename"] == "carta_do_executor.png"

    status, extra = _completion_event(publisher, "c")
    assert status != "failed"
    assert "schema_drift" not in extra, extra.get("schema_drift")
    assert "artifact_filename" in extra["output_keys"]


def test_one_port_with_anonymous_edge_draws_the_spread_layer():
    """With one port the editor does not write `to_key`: the executor spreads the
    parent's dict and the layer arrives as `r`, not as `lotes`. The image map
    draws it anyway, and the legend carries the port name."""
    resultado, capturado, _ = _run(
        [_script("a", -63.0), _image_map("c", ["lotes"])],
        [{"source": "a", "target": "c", "from_key": "r"}],
    )
    assert resultado["c"]["camadas"] == 1
    assert capturado["features"] == 2


def test_node_is_in_catalog_as_output_with_dynamic_inputs():
    from flow.registry import NODE_REGISTRY, auto_discover_nodes
    auto_discover_nodes()

    d = NODE_REGISTRY["CartaImagem"].description()
    assert d["type"] == "output" and d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["type"] == "ports" and ports["default"] == []
