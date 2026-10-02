# tests/integration/test_carta_no_executor.py
"""
A carta imagem rodando no EXECUTOR de verdade, e nao o no isolado.

O que so aparece montando o grafo: as duas camadas chegando pelo `to_key` de
cada aresta (portas nomeadas), a aresta anonima de uma porta so (o dict do pai
espalhado), e o evento de conclusao sem `schema_drift` — as chaves planas que
o no devolve casam com os `outputs` declarados.
"""
import asyncio
from unittest.mock import MagicMock, patch


ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

CAMADA = (
    "r = gpd.GeoDataFrame({'a': [1, 2]}, "
    "geometry=gpd.points_from_xy([%(x)s, %(x)s + 0.1], [-9.0, -9.1]), crs='EPSG:4326')"
)


def _script(node_id, x):
    return {"id": node_id, "type": "action", "name": "PythonScript",
            "properties": {"code": CAMADA % {"x": x}, "output_vars": "r", "timeout": 20}}


def _carta(node_id, ports):
    return {"id": node_id, "type": "output", "name": "CartaImagem",
            "properties": {"ports": ports, "dpi": 72, "titulo": "Carta do executor"}}


def _rodar(nodes, edges):
    from flow.executor import WorkflowExecutor

    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    capturado = {}

    def fake_persistir(**kwargs):
        capturado.update(kwargs)
        return f"artifacts/ws-1/t/{kwargs['filename']}", {
            "output_key": kwargs["label"], "format": kwargs["fmt"],
            "filename": kwargs["filename"], "size_bytes": len(kwargs["content"]),
        }

    with patch("flow.nodes.outputs.carta_imagem.persistir_artefato", side_effect=fake_persistir):
        resultado = asyncio.run(
            WorkflowExecutor({"nodes": nodes, "edges": edges}, task_id="t",
                             publisher=publisher, workspace_id="ws-1").run()
        )
    return resultado, capturado, publisher


def _evento_de_conclusao(publisher, node_id):
    """O evento de ciclo de vida do no: `publish_event(task_id, node_id, status,
    ts, duration, error, extra, ...)` — o `extra` leva `output_keys` e, so
    quando ha drift, `schema_drift`."""
    for chamada in publisher.publish_event.call_args_list:
        args = chamada.args
        if len(args) >= 7 and args[1] == node_id and isinstance(args[6], dict) \
                and "output_keys" in args[6]:
            return args[2], args[6]
    raise AssertionError(f"sem evento de conclusao para '{node_id}'")


def test_duas_portas_recebem_uma_camada_cada_pelo_to_key():
    resultado, capturado, publisher = _rodar(
        [_script("a", -63.0), _script("b", -62.0), _carta("c", ["focos", "municipios"])],
        [{"source": "a", "target": "c", "from_key": "r", "to_key": "focos"},
         {"source": "b", "target": "c", "from_key": "r", "to_key": "municipios"}],
    )
    assert resultado["c"]["camadas"] == 2
    assert capturado["features"] == 4
    assert capturado["content"].startswith(ASSINATURA_PNG)
    assert capturado["filename"] == "carta_do_executor.png"

    status, extra = _evento_de_conclusao(publisher, "c")
    assert status != "failed"
    assert "schema_drift" not in extra, extra.get("schema_drift")
    assert "artifact_filename" in extra["output_keys"]


def test_uma_porta_com_aresta_anonima_desenha_a_camada_espalhada():
    """Com uma porta o editor nao grava `to_key`: o executor espalha o dict do
    pai e a camada chega como `r`, nao como `lotes`. A carta a desenha assim
    mesmo, e a legenda leva o nome da porta."""
    resultado, capturado, _ = _rodar(
        [_script("a", -63.0), _carta("c", ["lotes"])],
        [{"source": "a", "target": "c", "from_key": "r"}],
    )
    assert resultado["c"]["camadas"] == 1
    assert capturado["features"] == 2


def test_o_no_esta_no_catalogo_como_saida_de_entradas_dinamicas():
    from flow.registry import NODE_REGISTRY, auto_discover_nodes
    auto_discover_nodes()

    d = NODE_REGISTRY["CartaImagem"].description()
    assert d["type"] == "output" and d.get("dynamic_inputs") is True
    ports = next(p for p in d["properties"] if p["name"] == "ports")
    assert ports["type"] == "ports" and ports["default"] == []
