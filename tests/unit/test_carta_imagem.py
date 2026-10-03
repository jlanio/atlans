# tests/unit/test_carta_imagem.py
"""
The CartaImagem node (flow/nodes/outputs/carta_imagem.py) — contract, the two
input modes, the three formats, the basemap, locality and the guards.

`persistir_artefato` is replaced by a double that captures what the node sends:
without it the node would try the presign on the server (the conftest doesn't
define EXECUTOR_SYNC_MODE). The render is real, at 72 dpi, so the test is fast;
what is asserted about the image is each format's signature bytes and the
`_Render` the node built — captured by a double that wraps the real render.
"""
from __future__ import annotations

import io
from unittest.mock import patch

import geopandas as gpd
import httpx
import pytest
from shapely.geometry import Point, Polygon

from flow.nodes.outputs import carta_imagem
from flow.nodes.outputs.carta_imagem import MENSAGEM_SEM_MATPLOTLIB, CartaImagem
from flow.registry import NODE_REGISTRY, auto_discover_nodes
from flow.utils import carta

auto_discover_nodes()

ASSINATURA = {"png": b"\x89PNG\r\n\x1a\n", "jpg": b"\xff\xd8\xff", "pdf": b"%PDF-"}
MIME = {"png": "image/png", "jpg": "image/jpeg", "pdf": "application/pdf"}
RAPIDO = {"dpi": 72}
CHAVES_DECLARADAS = {
    "artifact_filename", "artifact_s3_key", "format", "size_bytes",
    "camadas", "largura_px", "altura_px",
}


@pytest.fixture
def pontos():
    return gpd.GeoDataFrame(
        {"n": range(12)},
        geometry=[Point(-63.9 + i * 0.05, -8.8 + (i % 3) * 0.02) for i in range(12)],
        crs="EPSG:4326",
    )


@pytest.fixture
def poligonos():
    return gpd.GeoDataFrame(
        {"a": [1, 2]},
        geometry=[
            Polygon([(-64.0, -8.9), (-63.6, -8.9), (-63.6, -8.6), (-64.0, -8.6)]),
            Polygon([(-63.5, -8.85), (-63.2, -8.85), (-63.2, -8.65), (-63.5, -8.65)]),
        ],
        crs="EPSG:4326",
    )


def _no(params: dict, node_id: str = "n1", ctx: dict | None = None) -> CartaImagem:
    node = CartaImagem(node_id, {**RAPIDO, **params})
    node._task_id = "task-1"
    node._workspace_id = "ws-1"
    node._workflow_hash = "wf"
    if ctx is not None:
        node.context = ctx
    return node


@pytest.fixture
def persistido():
    """Captures the kwargs of `persistir_artefato`; nothing goes out to the network."""
    capturado: dict = {}

    def fake(**kwargs):
        capturado.update(kwargs)
        return f"artifacts/ws-1/task-1/{kwargs['filename']}", {
            "output_key": kwargs["label"], "format": kwargs["fmt"],
            "filename": kwargs["filename"], "size_bytes": len(kwargs["content"]),
            "content_location": "minio",
        }

    with patch("flow.nodes.outputs.carta_imagem.persistir_artefato", side_effect=fake):
        yield capturado


@pytest.fixture
def render():
    """The `_Render` the node built, captured around the real render."""
    capturado: dict = {}
    original = carta_imagem._renderizar

    def espiao(r):
        capturado["render"] = r
        return original(r)

    with patch("flow.nodes.outputs.carta_imagem._renderizar", side_effect=espiao):
        yield capturado


def _tile_png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (120, 160, 90)).save(buf, format="PNG")
    return buf.getvalue()


# ── Contrato ─────────────────────────────────────────────────────────────────

def test_contrato_do_no():
    assert "CartaImagem" in NODE_REGISTRY
    d = CartaImagem.description()
    assert d["type"] == "output"
    assert d["dynamic_inputs"] is True
    assert d["dynamic_output"] is False
    props = {p["name"]: p for p in d["properties"]}
    assert props["ports"]["type"] == "ports" and props["ports"]["default"] == []
    assert [o["value"] for o in props["formato"]["options"]] == ["png", "jpg", "pdf"]
    assert [o["value"] for o in props["localidade"]["options"]] == ["herdar", "executor"]
    assert props["localidade"]["default"] == "herdar"
    assert props["credential_id"]["visibleWhen"] == {"field": "localidade", "in": ["herdar"]}
    assert props["fundo_url"]["visibleWhen"] == {"field": "fundo", "in": ["personalizado"]}
    assert props["rotulos"]["type"] == "keyvalue" and props["cores"]["type"] == "keyvalue"
    declaradas = {f["name"] for f in d["outputs"]}
    assert declaradas == CHAVES_DECLARADAS


def test_options_batem_com_as_tabelas_da_carta():
    """execute indexes FORMATOS, TAMANHOS and FUNDOS_COM_NOME directly by the select's
    value, without checking: what guarantees the value is one of the options is
    `validate()`. So each option needs its own entry in the table."""
    props = {p["name"]: p for p in CartaImagem.description()["properties"]}

    def valores(nome):
        return {o["value"] for o in props[nome]["options"]}

    assert valores("formato") == set(carta.FORMATOS)
    assert valores("tamanho") == set(carta.TAMANHOS)
    assert valores("fundo") - {"nenhum", "personalizado"} == set(carta.FUNDOS_COM_NOME)


@pytest.mark.asyncio
async def test_o_catalogo_projeta_o_no_com_as_entradas_dinamicas():
    from app.services.node_service import NodeService

    async def _sem_desabilitados(_db):
        return set()

    with patch("app.services.node_service.disabled_names", _sem_desabilitados):
        defs = await NodeService().list_nodes(db=None)
    d = next(x for x in defs if x.name == "CartaImagem")
    assert d.type == "output"
    assert d.dynamic_inputs is True
    assert {p.name for p in d.properties} >= {"ports", "titulo", "formato", "fundo", "crs", "localidade"}


# ── Duas portas, tres formatos ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duas_portas_desenham_duas_camadas(persistido, pontos, poligonos):
    resultado = await _no({"ports": ["focos", "municipios"]}).execute(
        {"focos": pontos, "municipios": poligonos}
    )
    assert persistido["content"].startswith(ASSINATURA["png"])
    assert persistido["content_type"] == "image/png"
    assert persistido["fmt"] == "png"
    assert persistido["filename"] == "carta.png"
    assert persistido["label"] == "Carta"
    assert persistido["features"] == len(pontos) + len(poligonos)
    assert persistido["workspace_id"] == "ws-1" and persistido["task_id"] == "task-1"
    # FLAT keys, the declared ones — and the artifact's meta.
    assert set(resultado) == CHAVES_DECLARADAS | {"__artifact__"}
    assert resultado["camadas"] == 2
    assert resultado["format"] == "png"
    assert resultado["artifact_filename"] == "carta.png"
    assert resultado["artifact_s3_key"] == "artifacts/ws-1/task-1/carta.png"
    assert resultado["size_bytes"] == len(persistido["content"])
    # A4 paisagem a 72 dpi.
    assert (resultado["largura_px"], resultado["altura_px"]) == (842, 595)
    assert resultado["__artifact__"]["format"] == "png"


@pytest.mark.parametrize("formato", ["jpg", "pdf"])
@pytest.mark.asyncio
async def test_formato_decide_extensao_mime_e_assinatura(persistido, pontos, poligonos, formato):
    resultado = await _no({"ports": ["a", "b"], "formato": formato, "titulo": "Minha carta"}).execute(
        {"a": pontos, "b": poligonos}
    )
    assert persistido["content"].startswith(ASSINATURA[formato])
    assert persistido["content_type"] == MIME[formato]
    assert persistido["fmt"] == formato
    assert persistido["filename"] == f"minha_carta.{formato}"
    assert resultado["format"] == formato


# ── One port, no port ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_uma_porta_com_aresta_anonima_desenha_com_o_nome_da_porta(persistido, render, poligonos):
    """With ONE port the editor doesn't store `to_key`: the parent's dict arrives
    spread out (`output`), not under the port name. The layer has to get in
    anyway, and the legend carries the port name."""
    resultado = await _no({"ports": ["lotes"]}).execute({"output": poligonos})
    assert resultado["camadas"] == 1
    camada = render["render"].camadas[0]
    assert camada.porta == "lotes" and camada.rotulo == "lotes"


@pytest.mark.asyncio
async def test_sem_portas_desenha_a_camada_que_chegar(persistido, render, pontos):
    resultado = await _no({"ports": []}).execute({"output": pontos})
    assert resultado["camadas"] == 1
    assert render["render"].camadas[0].rotulo == "Camada"


@pytest.mark.asyncio
async def test_porta_nao_ligada_e_pulada_com_aviso(persistido, pontos):
    node = _no({"ports": ["a", "b"]})
    avisos: list[str] = []
    node.log = avisos.append
    resultado = await node.execute({"a": pontos})
    assert resultado["camadas"] == 1
    assert any("Porta 'b' sem camada" in a for a in avisos)


@pytest.mark.asyncio
async def test_nenhuma_camada_e_erro(persistido):
    with pytest.raises(ValueError, match="Nenhuma camada"):
        await _no({"ports": ["a", "b"]}).execute({})
    with pytest.raises(ValueError, match="Nenhuma camada"):
        await _no({"ports": []}).execute({"output": "nao e camada"})


# ── Estilo ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rotulos_e_cores_por_porta(persistido, render, pontos, poligonos):
    await _no({
        "ports": ["focos_de_calor", "municipios"],
        "rotulos": {"focos_de_calor": "Focos de calor"},
        "cores": '{"focos_de_calor": "#eb5757"}',   # JSON in a string also works
    }).execute({"focos_de_calor": pontos, "municipios": poligonos})
    a, b = render["render"].camadas
    assert (a.rotulo, a.cor) == ("Focos de calor", "#eb5757")
    assert b.rotulo == "municipios" and b.cor == carta.PALETA[1]


@pytest.mark.asyncio
async def test_cor_invalida_nomeia_a_porta(persistido, pontos):
    with pytest.raises(ValueError, match="focos"):
        await _no({"ports": ["focos", "b"], "cores": {"focos": "laranja"}}).execute({"focos": pontos})


@pytest.mark.asyncio
async def test_dpi_e_teto_de_pixels(persistido, pontos, monkeypatch):
    with pytest.raises(ValueError, match="dpi"):
        await _no({"dpi": 600}).execute({"output": pontos})
    monkeypatch.setattr(carta, "TETO_DE_PIXELS", 100_000)
    with pytest.raises(ValueError, match="Mpx"):
        await _no({"dpi": 150}).execute({"output": pontos})


@pytest.mark.asyncio
async def test_titulo_repetido_no_mesmo_run_e_erro_mas_retry_nao(persistido, pontos):
    ctx: dict = {}
    await _no({"titulo": "Repetida"}, node_id="n1", ctx=ctx).execute({"output": pontos})
    with pytest.raises(ValueError, match="titulos diferentes"):
        await _no({"titulo": "Repetida"}, node_id="n2", ctx=ctx).execute({"output": pontos})
    # The SAME node running again (retry) is not a collision.
    await _no({"titulo": "Repetida"}, node_id="n1", ctx=ctx).execute({"output": pontos})


# ── CRS ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_camada_sem_crs_e_tratada_como_4326(persistido, render, poligonos):
    sem_crs = poligonos.set_crs(None, allow_override=True)
    node = _no({})
    avisos: list[str] = []
    node.log = avisos.append
    await node.execute({"output": sem_crs})
    r = render["render"]
    assert r.crs_texto == "EPSG:32720"
    x0, _, x1, _ = r.extensao
    assert x1 - x0 > 10_000            # meters, not degrees
    assert any("sem CRS" in a for a in avisos)


@pytest.mark.asyncio
async def test_crs_geografico_pula_a_escala_com_aviso(persistido, render, poligonos):
    node = _no({"crs": "EPSG:4326"})
    avisos: list[str] = []
    node.log = avisos.append
    await node.execute({"output": poligonos})
    assert render["render"].escala is False
    assert any("Escala grafica pulada" in a for a in avisos)


# ── Basemap ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sem_espera(monkeypatch):
    monkeypatch.setattr(carta_imagem, "espera_exponencial", lambda *a, **k: 0.0)


# The hybrid a configured server would inject into the node (MAPA_HIBRIDO_*).
HIBRIDO_DE_TESTE = {"url": "https://hibrido.example.org/{z}/{x}/{y}.jpg", "credito": "© Hibrido de Teste"}


@pytest.mark.asyncio
async def test_fundo_baixa_tiles_forca_3857_e_credita_o_osm(persistido, render, pontos, poligonos):
    chamadas: list[dict] = []
    tile = _tile_png()

    async def fake(method, url, **kwargs):
        chamadas.append({"url": url, **kwargs})
        return httpx.Response(200, content=tile, request=httpx.Request(method, url))

    with patch("flow.nodes.outputs.carta_imagem.safe_httpx_request", side_effect=fake), \
         patch("flow.nodes.outputs.carta_imagem.validate_url_ssrf", return_value=("1.2.3.4", "tile.openstreetmap.org")):
        await _no({"ports": ["a", "b"], "fundo": "ruas", "creditos": "Fonte: INPE"}).execute(
            {"a": pontos, "b": poligonos}
        )
    r = render["render"]
    assert r.crs_texto == "EPSG:3857" and r.crs_e_3857
    assert r.fundo is not None and r.fundo_extensao is not None
    assert r.creditos == "Fonte: INPE · © OpenStreetMap contributors"
    assert chamadas and all(c["url"].startswith("https://tile.openstreetmap.org/") for c in chamadas)
    assert all(c["headers"]["User-Agent"].startswith("Atlans/carta") for c in chamadas)
    # O mosaico cobre a extensao da carta.
    xmin, xmax, ymin, ymax = r.fundo_extensao
    x0, y0, x1, y1 = r.extensao
    assert xmin <= x0 and xmax >= x1 and ymin <= y0 and ymax >= y1


@pytest.mark.asyncio
async def test_tile_5xx_e_retentado_e_404_e_definitivo(persistido, sem_espera, pontos):
    tile = _tile_png()
    vistas: dict[str, int] = {}

    async def instavel(method, url, **kwargs):
        vistas[url] = vistas.get(url, 0) + 1
        status = 503 if vistas[url] < 3 else 200
        return httpx.Response(status, content=tile if status == 200 else b"", request=httpx.Request(method, url))

    with patch("flow.nodes.outputs.carta_imagem.safe_httpx_request", side_effect=instavel), \
         patch("flow.nodes.outputs.carta_imagem.validate_url_ssrf", return_value=("1.2.3.4", "h")):
        resultado = await _no({"fundo": "hibrido", "fundo_da_instalacao": HIBRIDO_DE_TESTE}).execute({"output": pontos})
    assert resultado["camadas"] == 1
    assert all(n == 3 for n in vistas.values())

    async def sumido(method, url, **kwargs):
        vistas[url] = vistas.get(url, 0) + 1
        return httpx.Response(404, content=b"", request=httpx.Request(method, url))

    vistas.clear()
    with patch("flow.nodes.outputs.carta_imagem.safe_httpx_request", side_effect=sumido), \
         patch("flow.nodes.outputs.carta_imagem.validate_url_ssrf", return_value=("1.2.3.4", "h")):
        with pytest.raises(ValueError, match="404"):
            await _no({"fundo": "hibrido", "fundo_da_instalacao": HIBRIDO_DE_TESTE}).execute({"output": pontos})
    assert all(n == 1 for n in vistas.values()), "4xx nao e retentado"


@pytest.mark.asyncio
async def test_template_personalizado_sem_marcadores_e_erro(persistido, pontos):
    with pytest.raises(ValueError, match="marcadores"):
        await _no({"fundo": "personalizado", "fundo_url": "https://t.exemplo.org/{z}/{x}.png"}).execute(
            {"output": pontos}
        )


@pytest.mark.asyncio
async def test_template_para_a_rede_interna_e_barrado(persistido, pontos):
    """The SSRF guard of the HTTP nodes applies here: a template written in the workflow
    doesn't reach the cloud metadata nor the internal network."""
    chamou = []

    async def nunca(method, url, **kwargs):
        chamou.append(url)
        raise AssertionError("nao pode baixar")

    with patch("flow.nodes.outputs.carta_imagem.safe_httpx_request", side_effect=nunca):
        with pytest.raises(ValueError):
            await _no({"fundo": "personalizado",
                       "fundo_url": "http://169.254.169.254/{z}/{x}/{y}"}).execute({"output": pontos})
    assert chamou == []


# ── Localidade e executor antigo ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_localidade_executor_grava_no_disco_sem_rede(tmp_path, monkeypatch, pontos):
    monkeypatch.setenv("EXECUTOR_SYNC_MODE", "catalog")
    monkeypatch.setenv("EXECUTOR_ARTIFACTS_DIR", str(tmp_path))

    def explode(*a, **k):
        raise AssertionError("nenhum byte pode sair da maquina")

    for nome in ("post", "put", "get", "request", "stream"):
        monkeypatch.setattr(httpx, nome, explode, raising=False)
    monkeypatch.setattr(httpx, "Client", explode)
    monkeypatch.setattr(httpx, "AsyncClient", explode)

    resultado = await _no({"credential_id": "cred-1"}).execute({"output": pontos})
    arquivo = tmp_path / "ws-1" / "task-1" / "carta.png"
    assert arquivo.read_bytes().startswith(ASSINATURA["png"])
    assert resultado["artifact_s3_key"] == "ws-1/task-1/carta.png"
    meta = resultado["__artifact__"]
    assert meta["content_location"] == "executor" and meta["s3_key"] is None
    assert meta["credential_id"] is None, "nao ha download a proteger no executor"


@pytest.mark.asyncio
async def test_sem_matplotlib_o_erro_diz_para_atualizar_o_executor(persistido, pontos, monkeypatch):
    def sem_lib():
        raise ImportError("No module named 'matplotlib'")

    monkeypatch.setattr(carta_imagem, "_importar_matplotlib", sem_lib)
    with pytest.raises(RuntimeError) as e:
        await _no({}).execute({"output": pontos})
    assert str(e.value) == MENSAGEM_SEM_MATPLOTLIB
