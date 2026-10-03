# flow/nodes/outputs/carta_imagem.py
"""
CartaImagem — the image map (PNG, JPG or PDF) of whichever layers the workflow chooses.

A single output node with DYNAMIC PORTS: each port is a layer of the map, and
the person connects to it whatever output they want drawn. What is not
connected is left out — that is how "not every layer of the workflow needs to
appear in the image". There is no end-of-run hook, and none is needed: the
graph itself guarantees this node runs after every layer connected to its ports.

The editor rules that apply here (web/app/components/workflow/utils/
resolve-edge-keys.ts and node-ports.ts):

  - with TWO or more ports, each becomes its own connection point and the
    editor writes the edge's `to_key` with the port name — the layer arrives in
    `inputs[nome_da_porta]`;
  - with one port or none, the edge is anonymous and the executor SPREADS the
    previous node's dict: the layer arrives as `inputs["output"]` (or whatever
    key the parent uses), never by the port name. That is why this node has two
    modes, and the editor blocks the second edge in that case (two would spread
    both dicts onto the same key and the last would win, with no way for the
    node to notice);
  - the port name must be an identifier (no spaces or accents), so the legend
    label has its own field (`rotulos`).

Rendering happens ON THE EXECUTOR, with matplotlib: the layers are already in
memory and the file follows the data locality like any other artifact
(including "keep only on the executor"). matplotlib is imported only when it is
time to draw: `flow/` is imported by the API and by the catalog tests, and the
import costs half a second plus memory. The basemap (web tiles) goes through
the same SSRF guards as the HTTP nodes.

Deliberately out of this version: inline preview (the image map is an artifact
to download), a card on the Home page, reprojection of the basemap (with a
basemap the image map is always EPSG:3857).
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import httpx

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.artifact_helpers import (
    EXECUTOR,
    artifacts_root,
    describe_locality,
    persistir_artefato,
    locality_property,
    resolve_locality,
)
from flow.utils.backoff import espera_exponencial
from flow.utils.carta import (
    FORMATOS,
    PALETA,
    NAMED_BASEMAPS,
    TILE_SIZE,
    scale_length,
    valid_color,
    credits_with_basemap,
    image_map_crs,
    crs_is_projected,
    page_dimensions,
    darken,
    extent_with_margin,
    tiles_extent,
    configured_basemap,
    server_injected,
    extent_in_frame,
    scale_factor_3857,
    lon_lat_de_3857,
    grid_ticks,
    parse_map,
    map_frame,
    scale_label,
    port_label,
    coordinate_label,
    tiles_for_extent,
    url_do_tile,
    validate_template,
    zoom_para,
)
from flow.utils.executor_http import slugify
from flow.utils.geo_helpers import safe_httpx_request, validate_url_ssrf
from flow.utils.identidade import user_agent
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports

logger = get_logger(__name__)

ATTEMPTS_PER_TILE = 3
TRANSIENT_STATUSES = frozenset({502, 503, 504})
MAX_BYTES_PER_TILE = 2_000_000
CONCURRENT_CONNECTIONS = 2      # the OpenStreetMap usage policy
FEATURE_WARNING = 200_000    # acima disto o desenho fica lento e o PDF sai rasterizado

NO_MATPLOTLIB_MESSAGE = (
    "A carta imagem precisa do matplotlib no executor: atualize a imagem do "
    "executor (Docker) ou o app desktop para uma versao que o inclua."
)


@dataclass
class _Layer:
    porta: str
    rotulo: str
    cor: str
    gdf: Any


@dataclass
class _Render:
    camadas: list
    extensao: tuple
    crs_texto: str
    crs_e_3857: bool
    largura_pol: float
    altura_pol: float
    largura_px: int
    altura_px: int
    dpi: int
    formato: str
    titulo: str
    subtitulo: str
    creditos: str
    opacidade: float
    legenda: bool
    escala: bool
    norte: bool
    grade: bool
    fundo: Any
    fundo_extensao: tuple | None
    rasterizar: bool


def _importar_matplotlib():
    """Separate so the test can simulate an executor without the library."""
    import matplotlib
    return matplotlib


def _load_matplotlib():
    """Lazy import + Agg backend, both BEFORE any drawing.

    `gdf.plot` imports pyplot internally (geopandas.plotting), and pyplot
    resolves the backend on the spot — in the render thread. In the desktop app
    Tk is pruned from the runtime, and the fallback would probe nonexistent
    backends. `use("Agg")` is deterministic and thread-safe; nothing here calls
    `plt.*`.

    The font cache (fontlist-*.json) goes to a directory the executor knows is
    writable, instead of HOME — on the first import matplotlib scans the system
    fonts and writes the result.
    """
    raiz = Path(artifacts_root()) / ".mpl"
    try:
        raiz.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(raiz))
    except OSError:
        pass
    try:
        matplotlib = _importar_matplotlib()
    except ImportError as exc:
        raise RuntimeError(NO_MATPLOTLIB_MESSAGE) from exc
    matplotlib.use("Agg")
    return matplotlib


@register_node
class CartaImagem(BaseNode):
    """Composes the layers connected to the ports into an image map (PNG, JPG or PDF)."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "CartaImagem",
            "alias": "Carta imagem",
            "type": "output",
            "description": (
                "Gera uma carta imagem (PNG, JPG ou PDF) com as camadas ligadas as "
                "portas do no: titulo, legenda, escala grafica, seta de norte, grade de "
                "coordenadas e fundo de mapa, cada um opcional. Cada porta e uma camada; "
                "o arquivo vira um artefato da execucao."
            ),
            # Inputs DECLARED BY THE USER, via `ports` — the same mechanism as the
            # Python Script and SubWorkflowOutput. With two or more ports the
            # editor writes each edge's `to_key` and each layer arrives by
            # name; with one or none the edge is anonymous (see the header).
            "dynamic_inputs": True,
            "dynamic_output": False,
            "outputs": [
                {"name": "artifact_filename", "type": "string", "description": "Nome do arquivo da carta"},
                {"name": "artifact_s3_key", "type": "string", "description": "Chave do artefato no MinIO (ou caminho local no executor)"},
                {"name": "format", "type": "string", "description": "png, jpg ou pdf"},
                {"name": "size_bytes", "type": "number", "description": "Tamanho do arquivo em bytes"},
                {"name": "camadas", "type": "number", "description": "Quantas camadas foram desenhadas"},
                {"name": "largura_px", "type": "number", "description": "Largura da pagina em pixels"},
                {"name": "altura_px", "type": "number", "description": "Altura da pagina em pixels"},
            ],
            "properties": [
                {
                    "name": "ports",
                    "label": "Camadas (portas de entrada)",
                    "type": "ports",
                    "default": [],
                    "description": (
                        "Uma porta por camada, na ordem de desenho (a primeira fica por baixo). "
                        "Sem portas ou com uma so, o no aceita UMA conexao — a camada que chegar. "
                        "Com duas ou mais, uma conexao por porta. O nome da porta vira o rotulo "
                        "da legenda, salvo se voce der outro em 'Rotulos'."
                    ),
                },
                {"name": "titulo", "label": "Titulo", "type": "string", "default": "Carta",
                 "description": "Titulo da carta; tambem da nome ao arquivo."},
                {"name": "subtitulo", "label": "Subtitulo", "type": "string", "default": "",
                 "description": "Linha abaixo do titulo (opcional)."},
                {"name": "creditos", "label": "Creditos", "type": "string", "default": "",
                 "description": "Fonte dos dados, autoria etc., no rodape (opcional). A atribuicao do fundo de mapa entra sozinha."},
                {
                    "name": "formato",
                    "label": "Formato",
                    "type": "select",
                    "default": "png",
                    "options": [
                        {"value": "png", "label": "PNG"},
                        {"value": "jpg", "label": "JPG"},
                        {"value": "pdf", "label": "PDF (vetorial)"},
                    ],
                },
                {
                    "name": "tamanho",
                    "label": "Tamanho da pagina",
                    "type": "select",
                    "default": "a4-paisagem",
                    "options": [
                        {"value": "a4-paisagem", "label": "A4 paisagem"},
                        {"value": "a4-retrato", "label": "A4 retrato"},
                        {"value": "a3-paisagem", "label": "A3 paisagem"},
                        {"value": "a3-retrato", "label": "A3 retrato"},
                    ],
                },
                {"name": "dpi", "label": "Resolucao (dpi)", "type": "integer", "default": 150,
                 "description": "72 a 300. Vale para PNG/JPG e para o fundo de mapa dentro do PDF."},
                {"name": "rotulos", "label": "Rotulos da legenda", "type": "keyvalue", "default": {},
                 "description": "Porta → rotulo. Vazio: o nome da porta (com _ virando espaco)."},
                {"name": "cores", "label": "Cores", "type": "keyvalue", "default": {},
                 "description": "Porta → cor em hexadecimal (#RRGGBB). Vazio: a paleta da carta."},
                {"name": "opacidade", "label": "Opacidade das camadas", "type": "number", "default": 0.7,
                 "description": "De 0 (transparente) a 1 (opaca)."},
                {"name": "legenda", "label": "Legenda", "type": "boolean", "default": True},
                {"name": "escala", "label": "Escala grafica", "type": "boolean", "default": True,
                 "description": "So em CRS projetado (UTM, 3857); em graus a escala e pulada com aviso."},
                {"name": "norte", "label": "Seta de norte", "type": "boolean", "default": True},
                {"name": "grade", "label": "Grade de coordenadas", "type": "boolean", "default": False,
                 "description": "Linhas e rotulos de coordenadas nas bordas."},
                {
                    "name": "fundo",
                    "label": "Fundo de mapa",
                    "type": "select",
                    "default": "nenhum",
                    "options": [
                        {"value": "nenhum", "label": "Nenhum"},
                        {"value": "hibrido", "label": "Satelite com rotulos"},
                        {"value": "satelite", "label": "Satelite"},
                        {"value": "ruas", "label": "Ruas"},
                        {"value": "personalizado", "label": "URL personalizada de tiles"},
                    ],
                    "description": (
                        "Tiles baixados da web na hora da execucao (o executor precisa de "
                        "internet). Com fundo, a carta e sempre EPSG:3857. Satelite e "
                        "satelite com rotulos sao os que a instalacao configurou "
                        "(MAPA_*_URL); ruas e o OpenStreetMap, se ela nao tiver outro."
                    ),
                },
                {
                    # INJECTED by the server at dispatch, for the named basemaps:
                    # the URL and attribution the installation configured (MAPA_*).
                    # Declared because `validate()` rebuilds the parameters from
                    # this list; the UI hides it by name.
                    "name": "fundo_da_instalacao",
                    "label": "Fundo da instalacao",
                    "type": "object",
                    "default": {},
                    "description": "Preenchido automaticamente pelo servidor. Nao editavel.",
                },
                {"name": "fundo_url", "label": "URL dos tiles", "type": "string", "default": "",
                 "description": "Template com {z}, {x} e {y}, ex.: https://tiles.exemplo.org/{z}/{x}/{y}.png",
                 "visibleWhen": {"field": "fundo", "in": ["personalizado"]}},
                {"name": "crs", "label": "CRS da carta", "type": "string", "default": "auto",
                 "description": (
                     "'auto' = UTM local estimado pela extensao das camadas; ou um codigo como "
                     "EPSG:31980. Com fundo de mapa a carta e sempre EPSG:3857."
                 )},
                {
                    "name": "credential_id",
                    "type": "credential",
                    "default": "",
                    "description": "Token Bearer para proteger o download. Sem credencial, o artefato e publico.",
                    "credential_types": ["webhook_token"],
                    # There is no download to protect on an artifact that stays on the executor.
                    "visibleWhen": {"field": "localidade", "in": ["herdar"]},
                },
                locality_property(),
            ],
        }

    # ── Execucao ─────────────────────────────────────────────────────────────

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # format, size and basemap already validated against the options by
        # self.validate(); the options are the keys of FORMATOS, TAMANHOS and
        # NAMED_BASEMAPS (see test_carta_imagem).
        formato = self.get_param("formato", "png")
        mime, ext = FORMATOS[formato]
        tamanho = self.get_param("tamanho", "a4-paisagem")
        dpi = self.get_param_int("dpi", 150)
        largura_pol, altura_pol, largura_px, altura_px = page_dimensions(tamanho, dpi)

        titulo = (self.get_param("titulo", "") or "").strip() or "Carta"
        subtitulo = (self.get_param("subtitulo", "") or "").strip()
        credits_param = (self.get_param("creditos", "") or "").strip()
        opacidade = min(1.0, max(0.0, self.get_param_float("opacidade", 0.7)))
        legenda = self.get_param_bool("legenda", True)
        escala = self.get_param_bool("escala", True)
        norte = self.get_param_bool("norte", True)
        grade = self.get_param_bool("grade", False)
        crs_param = (self.get_param("crs", "auto") or "auto").strip()

        fundo = self.get_param("fundo", "nenhum")
        template: str | None = None
        atribuicao: str | None = None
        if fundo == "personalizado":
            template = validate_template(self.get_param("fundo_url", ""))
        elif fundo != "nenhum":
            injetado = self.get_param("fundo_da_instalacao")
            configurado = configured_basemap(fundo, injetado)
            variavel = NAMED_BASEMAPS[fundo][0] + (
                " ou MAPA_SATELITE_URL" if fundo == "hibrido" else ""
            )
            if configurado is None and server_injected(injetado):
                raise ValueError(
                    f"O fundo '{fundo}' nao esta configurado nesta instalacao "
                    f"({variavel} no servidor). Use 'Ruas' ou uma URL personalizada de tiles."
                )
            if configurado is None:
                # Executor updated before the server: a server older than this
                # version does not send the basemap, and the executor has none of its own.
                raise ValueError(
                    f"O servidor nao mandou o fundo '{fundo}' (servidor anterior a esta "
                    f"versao do executor?) e o executor nao tem {variavel}. Atualize o "
                    "servidor, ou defina a variavel no executor."
                )
            template, atribuicao = configurado

        portas = _parse_ports(self.parameters.get("ports"))
        rotulos = parse_map(self.get_param("rotulos", {}))
        cores = parse_map(self.get_param("cores", {}))
        for porta, cor in cores.items():
            if not valid_color(cor):
                raise ValueError(
                    f"Cor '{cor}' da porta '{porta}' invalida: use hexadecimal, ex.: #e7723b."
                )

        localidade, quem = resolve_locality(self.get_param("localidade", None))
        credential_id = self.get_param("credential_id", "") or None
        if localidade == EXECUTOR:
            # There is no download to protect on an artifact that stays on the executor.
            credential_id = None
        label = self.derive_label(titulo, "")
        workspace_id, task_id = self.require_execution_context()

        filename = f"{slugify(titulo)}.{ext}"
        self._reserve_name(filename)

        camadas = self._layers(inputs, portas, rotulos, cores)
        total = sum(len(c.gdf) for c in camadas)

        # ── CRS: order matters — no CRS means 4326, BEFORE any reprojection ──
        bbox_4326 = await asyncio.to_thread(self._bbox_4326, camadas)
        crs_texto, aviso = image_map_crs(bbox_4326, crs_param, fundo)
        if aviso:
            self.log(aviso)
        camadas = await asyncio.to_thread(_reprojetar, camadas, crs_texto)
        projetado = crs_is_projected(crs_texto)
        crs_e_3857 = _e_3857(crs_texto)
        caixa = _layers_bbox(camadas)
        # The frame is fixed (the box on the page); the extent grows to its
        # aspect ratio — and it is THIS extent that the basemap must cover.
        _e, _b, width_q, height_q = map_frame(legenda)
        aspect_ratio = (width_q * largura_pol) / (height_q * altura_pol)
        extensao = extent_in_frame(extent_with_margin(caixa, projetado), aspect_ratio)

        if escala and not projetado:
            self.log(
                f"Escala grafica pulada: a carta esta em {crs_texto}, que nao e um CRS "
                "projetado (as distancias nao sao metros). Use 'auto' ou um EPSG projetado."
            )
            escala = False

        basemap_img, fundo_extensao = None, None
        if template:
            basemap_img, fundo_extensao = await self._download_basemap(template, extensao, largura_px)
        creditos = credits_with_basemap(credits_param, atribuicao)

        if total > FEATURE_WARNING:
            self.log(
                f"{total} feicoes na carta: o desenho fica lento e o PDF sai rasterizado. "
                "Simplifique ou filtre as camadas antes se precisar de vetor puro."
            )

        render = _Render(
            camadas=camadas, extensao=extensao, crs_texto=crs_texto, crs_e_3857=crs_e_3857,
            largura_pol=largura_pol, altura_pol=altura_pol, largura_px=largura_px,
            altura_px=altura_px, dpi=dpi, formato=formato, titulo=titulo,
            subtitulo=subtitulo, creditos=creditos, opacidade=opacidade, legenda=legenda,
            escala=escala, norte=norte, grade=grade, fundo=basemap_img,
            fundo_extensao=fundo_extensao, rasterizar=total > FEATURE_WARNING,
        )
        content = await asyncio.to_thread(_renderizar, render)

        s3_key, artifact_meta = await asyncio.to_thread(
            persistir_artefato,
            localidade=localidade,
            content=content,
            filename=filename,
            content_type=mime,
            workspace_id=workspace_id,
            task_id=task_id,
            label=label,
            fmt=formato,
            features=total,
            credential_id=credential_id,
        )
        self.log(describe_locality(localidade, quem))
        onde = "neste executor" if localidade == EXECUTOR else "no MinIO"
        self.log(
            f"Carta salva {onde}: {s3_key} ({formato}, {largura_px}x{altura_px} px, "
            f"{len(camadas)} camada(s), {total} feicoes, CRS {crs_texto})"
        )

        # FLAT keys, the same as static_output: the executor compares the top-level
        # keys with the declared ones and lights the drift warning on the panel if
        # they don't match (flow/executor/core.py, "schema drift").
        return {
            "artifact_filename": filename,
            "artifact_s3_key": s3_key,
            "format": formato,
            "size_bytes": len(content),
            "camadas": len(camadas),
            "largura_px": largura_px,
            "altura_px": altura_px,
            "__artifact__": artifact_meta,
        }

    # ── Partes ───────────────────────────────────────────────────────────────

    def _reserve_name(self, filename: str) -> None:
        """Two nodes with the same title would write the SAME S3 key and the server
        would silently deduplicate, leaving a single image map. The record lives
        in the run's `context` (shared by all nodes), and it is made
        synchronously before the first `await` — the batch runs in `gather`,
        cooperatively, so there is no race. Stores the node_id: a retry of the
        SAME node is not a collision."""
        ctx = getattr(self, "context", None)
        if not isinstance(ctx, dict):
            return
        usados = ctx.setdefault("__cartas__", {})
        dono = usados.get(filename)
        if dono is not None and dono != self.node_id:
            raise ValueError(
                f"Ja existe uma carta '{filename}' neste fluxo: de titulos diferentes a "
                "cada no Carta imagem."
            )
        usados[filename] = self.node_id

    def _layers(self, inputs: Dict[str, Any], portas: list, rotulos: dict, cores: dict) -> list:
        import geopandas as gpd

        def is_layer(v: Any) -> bool:
            return isinstance(v, gpd.GeoDataFrame) and not v.empty and bool(v.geometry.notna().any())

        camadas: list[_Layer] = []
        if len(portas) >= 2:
            for i, porta in enumerate(portas):
                valor = (inputs or {}).get(porta)
                if not is_layer(valor):
                    self.log(f"Porta '{porta}' sem camada (nao ligada ou vazia): fora da carta.")
                    continue
                camadas.append(_Layer(
                    porta=porta,
                    rotulo=port_label(porta, rotulos),
                    cor=cores.get(porta) or PALETA[i % len(PALETA)],
                    gdf=valor[valor.geometry.notna()],
                ))
            conhecidas = set(portas)
        else:
            # Anonymous edge: the parent's dict was spread into the inputs. The layer is
            # the first GeoDataFrame that arrived (the get_first_gdf criterion).
            candidatos = [k for k, v in (inputs or {}).items() if is_layer(v)]
            if candidatos:
                if len({id(inputs[k]) for k in candidatos}) > 1:
                    self.log(
                        f"Mais de uma camada chegou a este no ({candidatos}); usando "
                        f"'{candidatos[0]}'. Declare duas ou mais portas para desenhar varias."
                    )
                nome = portas[0] if portas else "camada"
                rotulo = port_label(nome, rotulos) if portas else (rotulos.get(nome) or "Camada")
                valor = inputs[candidatos[0]]
                camadas.append(_Layer(
                    porta=nome, rotulo=rotulo,
                    cor=cores.get(nome) or PALETA[0],
                    gdf=valor[valor.geometry.notna()],
                ))
            conhecidas = {portas[0]} if portas else {"camada"}

        for chave in sorted((set(cores) | set(rotulos)) - conhecidas):
            self.log(f"'{chave}' em Cores/Rotulos nao e uma porta deste no; ignorado.")

        if not camadas:
            raise ValueError(
                "Nenhuma camada chegou a carta. Ligue uma camada ao no — ou declare duas ou "
                "mais portas em 'Camadas' e ligue uma camada a cada uma."
            )
        return camadas

    def _bbox_4326(self, camadas: list) -> tuple:
        """The extent of all layers in lon/lat, to estimate the CRS.

        A layer without a CRS is treated as EPSG:4326 HERE, before any
        reprojection: `to_crs` without a source CRS would fail, and a `set_crs`
        with the map's CRS would label degrees as meters.
        """
        from pyproj import Transformer

        caixas = []
        for c in camadas:
            if c.gdf.crs is None:
                self.log(f"Camada '{c.rotulo}' sem CRS: tratada como EPSG:4326.")
                c.gdf = c.gdf.set_crs("EPSG:4326")
            x0, y0, x1, y1 = (float(v) for v in c.gdf.total_bounds)
            if not _e_4326(c.gdf.crs):
                t = Transformer.from_crs(c.gdf.crs, "EPSG:4326", always_xy=True)
                x0, y0, x1, y1 = t.transform_bounds(x0, y0, x1, y1)
            caixas.append((x0, y0, x1, y1))
        return (
            min(b[0] for b in caixas), min(b[1] for b in caixas),
            max(b[2] for b in caixas), max(b[3] for b in caixas),
        )

    async def _download_basemap(self, template: str, extent_3857: tuple, largura_px: int):
        """Downloads and assembles the tile mosaic that covers the extent (EPSG:3857).

        Each URL goes through the SSRF guard (`safe_httpx_request` pins the IP,
        blocks redirects and limits the body), as in the HTTP nodes: a template
        written in the workflow cannot reach the internal network or the cloud
        metadata. Two connections at a time and retry only on transient errors
        (the OpenStreetMap usage policy); 4xx is a definitive error.
        """
        z = zoom_para(extent_3857, largura_px)
        z, tx0, tx1, ty0, ty1 = tiles_for_extent(extent_3857, z)
        await asyncio.to_thread(validate_url_ssrf, url_do_tile(template, z, tx0, ty0))

        semaforo = asyncio.Semaphore(CONCURRENT_CONNECTIONS)
        # The installation's site in the User-Agent, as the OSM policy asks
        # (flow/utils/identidade.py).
        cabecalhos = {"User-Agent": user_agent("carta")}

        async def um_tile(x: int, y: int):
            url = url_do_tile(template, z, x, y)
            async with semaforo:
                for tentativa in range(ATTEMPTS_PER_TILE):
                    ultima = tentativa == ATTEMPTS_PER_TILE - 1
                    try:
                        resposta = await safe_httpx_request(
                            "GET", url, timeout=20.0,
                            headers=cabecalhos,
                            max_response_bytes=MAX_BYTES_PER_TILE,
                        )
                    except httpx.TransportError as exc:
                        if ultima:
                            raise ValueError(
                                f"Fundo de mapa: nao foi possivel baixar {url} ({exc})."
                            ) from exc
                        await asyncio.sleep(espera_exponencial(tentativa, teto=5.0, inicial=0.5))
                        continue
                    if resposta.status_code in TRANSIENT_STATUSES and not ultima:
                        await asyncio.sleep(espera_exponencial(tentativa, teto=5.0, inicial=0.5))
                        continue
                    if resposta.status_code >= 400:
                        raise ValueError(
                            f"Fundo de mapa: o servidor de tiles respondeu "
                            f"{resposta.status_code} para {url}."
                        )
                    return x, y, resposta.content
            raise ValueError(f"Fundo de mapa: nao foi possivel baixar {url}.")

        tiles = await asyncio.gather(*(
            um_tile(x, y) for y in range(ty0, ty1 + 1) for x in range(tx0, tx1 + 1)
        ))
        imagem = await asyncio.to_thread(_build_mosaic, tiles, tx0, tx1, ty0, ty1)
        self.log(f"Fundo de mapa: {len(tiles)} tile(s) no zoom {z}.")
        return imagem, tiles_extent(tx0, tx1, ty0, ty1, z)


# ── Module functions (run in a thread, without `self`) ──────────────────────

def _e_4326(crs: Any) -> bool:
    try:
        return crs is not None and crs.to_epsg() == 4326
    except Exception:
        return False


def _e_3857(crs_texto: str) -> bool:
    from pyproj import CRS
    try:
        return CRS.from_user_input(crs_texto).to_epsg() == 3857
    except Exception:
        return False


def _reprojetar(camadas: list, crs_texto: str) -> list:
    from pyproj import CRS
    alvo = CRS.from_user_input(crs_texto)
    for c in camadas:
        if c.gdf.crs is None:
            c.gdf = c.gdf.set_crs("EPSG:4326")
        if not c.gdf.crs.equals(alvo):
            c.gdf = c.gdf.to_crs(alvo)
    return camadas


def _layers_bbox(camadas: list) -> tuple:
    caixas = [tuple(float(v) for v in c.gdf.total_bounds) for c in camadas]
    return (
        min(b[0] for b in caixas), min(b[1] for b in caixas),
        max(b[2] for b in caixas), max(b[3] for b in caixas),
    )


def _geometry_type(gdf: Any) -> str:
    tipos = set(gdf.geom_type.dropna().str.replace("Multi", "", regex=False))
    if tipos and tipos <= {"Point"}:
        return "ponto"
    if tipos and tipos <= {"LineString", "LinearRing"}:
        return "linha"
    return "poligono"


def _build_mosaic(tiles: list, tx0: int, tx1: int, ty0: int, ty1: int):
    from PIL import Image

    largura = (tx1 - tx0 + 1) * TILE_SIZE
    altura = (ty1 - ty0 + 1) * TILE_SIZE
    mosaico = Image.new("RGB", (largura, altura), "white")
    for x, y, conteudo in tiles:
        tile = Image.open(io.BytesIO(conteudo)).convert("RGB")
        if tile.size != (TILE_SIZE, TILE_SIZE):
            tile = tile.resize((TILE_SIZE, TILE_SIZE))
        mosaico.paste(tile, ((x - tx0) * TILE_SIZE, (y - ty0) * TILE_SIZE))
    return mosaico


def _renderizar(r: _Render) -> bytes:
    """Draws the image map and returns the file's bytes. Runs in a thread.

    matplotlib's object-oriented API (Figure + FigureCanvasAgg): no pyplot, no
    `rc_context` (global state shared across threads) — sizes and colors go
    per artist.
    """
    _load_matplotlib()
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.ticker import FixedLocator, FuncFormatter

    fig = Figure(figsize=(r.largura_pol, r.altura_pol), dpi=r.dpi)
    FigureCanvasAgg(fig)

    # The map on the left; the right column exists only with a legend. The extent
    # already came in this frame's aspect ratio (extent_in_frame), so the
    # axis does not shrink.
    map_box = list(map_frame(r.legenda))
    ax = fig.add_axes(map_box)
    x0, y0, x1, y1 = r.extensao

    if r.fundo is not None and r.fundo_extensao is not None:
        ax.imshow(
            np.asarray(r.fundo), extent=r.fundo_extensao, origin="upper",
            zorder=0, interpolation="bilinear",
        )
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    # `box`: the axis shrinks to keep the aspect ratio and the limits stay EXACT —
    # which is what allows anchoring the scale bar and north arrow by fraction
    # of the extent.
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor("#f4f4f4" if r.fundo is None else "white")

    # Simplification to 1 pixel: this is what keeps large layers drawable without
    # changing anything visible.
    map_width_px = max(map_box[2] * r.largura_px, 1.0)
    tolerancia = (x1 - x0) / map_width_px

    handles: list = []
    for i, c in enumerate(r.camadas):
        gdf = c.gdf
        geometria = gdf.geometry.simplify(tolerancia, preserve_topology=True)
        gdf = gdf.set_geometry(geometria)
        borda = darken(c.cor)
        comum = dict(ax=ax, zorder=1 + i, alpha=r.opacidade, rasterized=r.rasterizar)
        tipo = _geometry_type(gdf)
        if tipo == "ponto":
            gdf.plot(color=c.cor, edgecolor=borda, linewidth=0.4, markersize=18, **comum)
            handles.append(Line2D(
                [0], [0], linestyle="", marker="o", markerfacecolor=c.cor,
                markeredgecolor=borda, markersize=7, alpha=r.opacidade,
            ))
        elif tipo == "linha":
            gdf.plot(color=c.cor, linewidth=1.4, **comum)
            handles.append(Line2D([0], [0], color=c.cor, linewidth=2, alpha=r.opacidade))
        else:
            gdf.plot(color=c.cor, edgecolor=borda, linewidth=0.6, **comum)
            handles.append(Patch(facecolor=c.cor, edgecolor=borda, alpha=r.opacidade))
    # gdf.plot may touch the limits (autoscale); the map's extent wins.
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    if r.grade:
        xs, ys = grid_ticks(r.extensao, r.crs_texto)
        ax.xaxis.set_major_locator(FixedLocator(xs))
        ax.yaxis.set_major_locator(FixedLocator(ys))
        crs_texto = r.crs_texto
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: coordinate_label(v, "x", crs_texto)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: coordinate_label(v, "y", crs_texto)))
        ax.grid(True, linestyle=":", linewidth=0.5, color="#555555", zorder=30)
        ax.tick_params(labelsize=6.5, length=2, colors="#333333")
        for rotulo in ax.get_yticklabels():
            rotulo.set_rotation(90)
            rotulo.set_va("center")
    else:
        ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False)
    for espinha in ax.spines.values():
        espinha.set_linewidth(0.8)
        espinha.set_color("#222222")

    if r.norte:
        ax.annotate(
            "N", xy=(0.965, 0.955), xytext=(0.965, 0.865),
            xycoords="axes fraction", textcoords="axes fraction",
            ha="center", va="center", fontsize=12, fontweight="bold", color="#111111",
            arrowprops=dict(arrowstyle="-|>", color="#111111", lw=1.5),
            bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="none", alpha=0.85),
            zorder=50,
        )

    if r.escala:
        factor = 1.0
        if r.crs_e_3857:
            _lon, lat_c = lon_lat_de_3857((x0 + x1) / 2, (y0 + y1) / 2)
            factor = scale_factor_3857(lat_c)
        metros = scale_length((x1 - x0) * factor)
        if metros > 0:
            comprimento = metros / factor            # in map units
            bx = x0 + 0.03 * (x1 - x0)
            by = y0 + 0.04 * (y1 - y0)
            h = 0.012 * (y1 - y0)
            ax.add_patch(Rectangle(
                (bx - 0.012 * (x1 - x0), by - 0.012 * (y1 - y0)),
                comprimento + 0.024 * (x1 - x0), h + 0.055 * (y1 - y0),
                facecolor="white", edgecolor="none", alpha=0.8, zorder=40,
            ))
            ax.add_patch(Rectangle((bx, by), comprimento / 2, h, facecolor="#111111",
                                   edgecolor="#111111", linewidth=0.6, zorder=41))
            ax.add_patch(Rectangle((bx + comprimento / 2, by), comprimento / 2, h,
                                   facecolor="white", edgecolor="#111111", linewidth=0.6, zorder=41))
            ax.text(bx, by + h * 1.7, "0", fontsize=7, ha="center", va="bottom", zorder=42)
            ax.text(bx + comprimento, by + h * 1.7, scale_label(metros), fontsize=7,
                    ha="center", va="bottom", zorder=42)

    if r.legenda:
        ax_leg = fig.add_axes([0.76, 0.11, 0.22, 0.79])
        ax_leg.axis("off")
        ax_leg.legend(
            handles, [c.rotulo for c in r.camadas], loc="upper left", frameon=False,
            title="Legenda", title_fontsize=10, fontsize=9, borderaxespad=0.0,
        )

    fig.suptitle(r.titulo, x=0.04, y=0.965, ha="left", fontsize=15, fontweight="bold", color="#111111")
    if r.subtitulo:
        fig.text(0.04, 0.925, r.subtitulo, fontsize=10, color="#444444", ha="left", va="center")
    if r.creditos:
        fig.text(0.04, 0.045, r.creditos, fontsize=7.5, color="#555555", ha="left", va="center")
    hoje = _dt.date.today().strftime("%d/%m/%Y")
    fig.text(0.96, 0.045, f"{hoje} · {r.crs_texto}", fontsize=7.5, color="#555555",
             ha="right", va="center")

    buf = io.BytesIO()
    extra: dict = {"pil_kwargs": {"quality": 90}} if r.formato == "jpg" else {}
    fig.savefig(buf, format=r.formato, dpi=r.dpi, facecolor="white", **extra)
    return buf.getvalue()
