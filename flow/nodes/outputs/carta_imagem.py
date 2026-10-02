# flow/nodes/outputs/carta_imagem.py
"""
CartaImagem — a carta imagem (PNG, JPG ou PDF) das camadas que o fluxo escolher.

Um no so, de saida, com PORTAS DINAMICAS: cada porta e uma camada da carta e a
pessoa liga a ela a saida que quiser ver desenhada. O que nao esta ligado fica
de fora — e assim que "nem toda camada do fluxo precisa aparecer na imagem".
Nao ha gancho de fim de run e nao precisa haver: o proprio grafo garante que
este no roda depois de todas as camadas ligadas as suas portas.

As regras do editor que mandam aqui (web/app/components/workflow/utils/
resolve-edge-keys.ts e node-ports.ts):

  - com DUAS ou mais portas, cada uma vira um ponto de conexao proprio e o
    editor grava o `to_key` da aresta com o nome da porta — a camada chega em
    `inputs[nome_da_porta]`;
  - com uma porta ou nenhuma, a aresta e anonima e o executor ESPALHA o dict do
    no anterior: a camada chega como `inputs["output"]` (ou a chave que o pai
    usar), nunca pelo nome da porta. Por isso este no tem dois modos, e o
    editor barra a segunda aresta nesse caso (duas espalhariam os dois dicts
    na mesma chave e a ultima venceria, sem que o no pudesse perceber);
  - o nome da porta tem de ser identificador (sem espaco nem acento), entao o
    rotulo da legenda tem campo proprio (`rotulos`).

A renderizacao acontece NO EXECUTOR, com matplotlib: as camadas ja estao em
memoria e o arquivo segue a localidade dos dados como qualquer outro artefato
(inclusive "manter apenas no executor"). O matplotlib e importado so na hora de
desenhar: `flow/` e importado pela API e pelos testes de catalogo, e o import
custa meio segundo e memoria. O fundo de mapa (tiles da web) passa pelas mesmas
guardas de SSRF dos nos de HTTP.

O que esta fora desta versao, por decisao: previa inline (a carta e um artefato
para baixar), cartao na Home, reprojecao do fundo (com fundo a carta e sempre
EPSG:3857).
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
    descrever_localidade,
    persistir_artefato,
    propriedade_localidade,
    resolver_localidade,
)
from flow.utils.backoff import espera_exponencial
from flow.utils.carta import (
    FORMATOS,
    PALETA,
    FUNDOS_COM_NOME,
    TAMANHO_DO_TILE,
    comprimento_da_escala,
    cor_valida,
    creditos_com_fundo,
    crs_da_carta,
    crs_e_projetado,
    dimensoes_da_pagina,
    escurecer,
    extensao_com_margem,
    extensao_dos_tiles,
    fundo_configurado,
    servidor_injetou,
    extensao_no_quadro,
    fator_de_escala_3857,
    lon_lat_de_3857,
    marcas_da_grade,
    parse_mapa,
    quadro_do_mapa,
    rotulo_da_escala,
    rotulo_da_porta,
    rotulo_de_coordenada,
    tiles_da_extensao,
    url_do_tile,
    validar_template,
    zoom_para,
)
from flow.utils.executor_http import slugify
from flow.utils.geo_helpers import safe_httpx_request, validate_url_ssrf
from flow.utils.identidade import user_agent
from flow.utils.logger import get_logger
from flow.utils.workflow_contract import _parse_ports

logger = get_logger(__name__)

TENTATIVAS_POR_TILE = 3
STATUS_TRANSITORIOS = frozenset({502, 503, 504})
TETO_DE_BYTES_POR_TILE = 2_000_000
CONEXOES_SIMULTANEAS = 2      # a politica de uso do OpenStreetMap
AVISO_DE_FEICOES = 200_000    # acima disto o desenho fica lento e o PDF sai rasterizado

MENSAGEM_SEM_MATPLOTLIB = (
    "A carta imagem precisa do matplotlib no executor: atualize a imagem do "
    "executor (Docker) ou o app desktop para uma versao que o inclua."
)


@dataclass
class _Camada:
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
    """Separado para o teste simular um executor sem a biblioteca."""
    import matplotlib
    return matplotlib


def _carregar_matplotlib():
    """Import preguicoso + backend Agg, os dois ANTES de qualquer desenho.

    `gdf.plot` importa o pyplot por dentro (geopandas.plotting), e o pyplot
    resolve o backend na hora — na thread do render. No app desktop o Tk e
    podado do runtime, e o fallback tatearia backends inexistentes. `use("Agg")`
    e deterministico e seguro em thread; nada aqui chama `plt.*`.

    O cache de fontes (fontlist-*.json) vai para um diretorio que o executor
    sabe que e gravavel, em vez do HOME — no primeiro import o matplotlib
    varre as fontes do sistema e grava o resultado.
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
        raise RuntimeError(MENSAGEM_SEM_MATPLOTLIB) from exc
    matplotlib.use("Agg")
    return matplotlib


@register_node
class CartaImagem(BaseNode):
    """Compoe as camadas ligadas as portas numa carta (PNG, JPG ou PDF)."""

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
            # Entradas DECLARADAS PELO USUARIO, via `ports` — o mesmo mecanismo do
            # Script Python e do SubWorkflowOutput. Com duas ou mais portas o
            # editor grava o `to_key` de cada aresta e cada camada chega pelo
            # nome; com uma ou nenhuma a aresta e anonima (ver o cabecalho).
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
                    # INJETADA pelo servidor no despacho, para os fundos com nome:
                    # a URL e a atribuicao que a instalacao configurou (MAPA_*).
                    # Declarada porque `validate()` reconstroi os parametros a
                    # partir desta lista; a UI a esconde pelo nome.
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
                    # Nao ha download a proteger num artefato que fica no executor.
                    "visibleWhen": {"field": "localidade", "in": ["herdar"]},
                },
                propriedade_localidade(),
            ],
        }

    # ── Execucao ─────────────────────────────────────────────────────────────

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # formato, tamanho e fundo ja validados contra as options pelo
        # self.validate(); as options sao as chaves de FORMATOS, TAMANHOS e
        # FUNDOS_COM_NOME (ver test_carta_imagem).
        formato = self.get_param("formato", "png")
        mime, ext = FORMATOS[formato]
        tamanho = self.get_param("tamanho", "a4-paisagem")
        dpi = self.get_param_int("dpi", 150)
        largura_pol, altura_pol, largura_px, altura_px = dimensoes_da_pagina(tamanho, dpi)

        titulo = (self.get_param("titulo", "") or "").strip() or "Carta"
        subtitulo = (self.get_param("subtitulo", "") or "").strip()
        creditos_param = (self.get_param("creditos", "") or "").strip()
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
            template = validar_template(self.get_param("fundo_url", ""))
        elif fundo != "nenhum":
            injetado = self.get_param("fundo_da_instalacao")
            configurado = fundo_configurado(fundo, injetado)
            variavel = FUNDOS_COM_NOME[fundo][0] + (
                " ou MAPA_SATELITE_URL" if fundo == "hibrido" else ""
            )
            if configurado is None and servidor_injetou(injetado):
                raise ValueError(
                    f"O fundo '{fundo}' nao esta configurado nesta instalacao "
                    f"({variavel} no servidor). Use 'Ruas' ou uma URL personalizada de tiles."
                )
            if configurado is None:
                # Executor atualizado antes do servidor: o servidor anterior a
                # esta versao nao manda o fundo, e o executor nao tem o seu.
                raise ValueError(
                    f"O servidor nao mandou o fundo '{fundo}' (servidor anterior a esta "
                    f"versao do executor?) e o executor nao tem {variavel}. Atualize o "
                    "servidor, ou defina a variavel no executor."
                )
            template, atribuicao = configurado

        portas = _parse_ports(self.parameters.get("ports"))
        rotulos = parse_mapa(self.get_param("rotulos", {}))
        cores = parse_mapa(self.get_param("cores", {}))
        for porta, cor in cores.items():
            if not cor_valida(cor):
                raise ValueError(
                    f"Cor '{cor}' da porta '{porta}' invalida: use hexadecimal, ex.: #e7723b."
                )

        localidade, quem = resolver_localidade(self.get_param("localidade", None))
        credential_id = self.get_param("credential_id", "") or None
        if localidade == EXECUTOR:
            # Nao ha download a proteger num artefato que fica no executor.
            credential_id = None
        label = self.derive_label(titulo, "")
        workspace_id, task_id = self.require_execution_context()

        filename = f"{slugify(titulo)}.{ext}"
        self._reservar_nome(filename)

        camadas = self._camadas(inputs, portas, rotulos, cores)
        total = sum(len(c.gdf) for c in camadas)

        # ── CRS: a ordem importa — sem CRS e 4326 ANTES de qualquer reprojecao ──
        caixa_4326 = await asyncio.to_thread(self._caixa_4326, camadas)
        crs_texto, aviso = crs_da_carta(caixa_4326, crs_param, fundo)
        if aviso:
            self.log(aviso)
        camadas = await asyncio.to_thread(_reprojetar, camadas, crs_texto)
        projetado = crs_e_projetado(crs_texto)
        crs_e_3857 = _e_3857(crs_texto)
        caixa = _caixa_das_camadas(camadas)
        # A moldura e fixa (o quadro na pagina); a extensao cresce ate a proporcao
        # dela — e e ESTA extensao que o fundo de mapa precisa cobrir.
        _e, _b, largura_q, altura_q = quadro_do_mapa(legenda)
        proporcao = (largura_q * largura_pol) / (altura_q * altura_pol)
        extensao = extensao_no_quadro(extensao_com_margem(caixa, projetado), proporcao)

        if escala and not projetado:
            self.log(
                f"Escala grafica pulada: a carta esta em {crs_texto}, que nao e um CRS "
                "projetado (as distancias nao sao metros). Use 'auto' ou um EPSG projetado."
            )
            escala = False

        fundo_img, fundo_extensao = None, None
        if template:
            fundo_img, fundo_extensao = await self._baixar_fundo(template, extensao, largura_px)
        creditos = creditos_com_fundo(creditos_param, atribuicao)

        if total > AVISO_DE_FEICOES:
            self.log(
                f"{total} feicoes na carta: o desenho fica lento e o PDF sai rasterizado. "
                "Simplifique ou filtre as camadas antes se precisar de vetor puro."
            )

        render = _Render(
            camadas=camadas, extensao=extensao, crs_texto=crs_texto, crs_e_3857=crs_e_3857,
            largura_pol=largura_pol, altura_pol=altura_pol, largura_px=largura_px,
            altura_px=altura_px, dpi=dpi, formato=formato, titulo=titulo,
            subtitulo=subtitulo, creditos=creditos, opacidade=opacidade, legenda=legenda,
            escala=escala, norte=norte, grade=grade, fundo=fundo_img,
            fundo_extensao=fundo_extensao, rasterizar=total > AVISO_DE_FEICOES,
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
        self.log(descrever_localidade(localidade, quem))
        onde = "neste executor" if localidade == EXECUTOR else "no MinIO"
        self.log(
            f"Carta salva {onde}: {s3_key} ({formato}, {largura_px}x{altura_px} px, "
            f"{len(camadas)} camada(s), {total} feicoes, CRS {crs_texto})"
        )

        # Chaves PLANAS, as mesmas do static_output: o executor compara as chaves
        # de topo com as declaradas e acende o aviso de drift no painel se nao
        # casarem (flow/executor/core.py, "schema drift").
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

    def _reservar_nome(self, filename: str) -> None:
        """Dois nos com o mesmo titulo gravariam a MESMA chave S3 e o servidor
        deduplicaria em silencio, sobrando uma carta so. O registro fica no
        `context` do run (compartilhado por todos os nos), e e feito de forma
        sincrona antes do primeiro `await` — o batch roda em `gather`,
        cooperativo, entao nao ha corrida. Guarda o node_id: um retry do MESMO
        no nao e colisao."""
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

    def _camadas(self, inputs: Dict[str, Any], portas: list, rotulos: dict, cores: dict) -> list:
        import geopandas as gpd

        def e_camada(v: Any) -> bool:
            return isinstance(v, gpd.GeoDataFrame) and not v.empty and bool(v.geometry.notna().any())

        camadas: list[_Camada] = []
        if len(portas) >= 2:
            for i, porta in enumerate(portas):
                valor = (inputs or {}).get(porta)
                if not e_camada(valor):
                    self.log(f"Porta '{porta}' sem camada (nao ligada ou vazia): fora da carta.")
                    continue
                camadas.append(_Camada(
                    porta=porta,
                    rotulo=rotulo_da_porta(porta, rotulos),
                    cor=cores.get(porta) or PALETA[i % len(PALETA)],
                    gdf=valor[valor.geometry.notna()],
                ))
            conhecidas = set(portas)
        else:
            # Aresta anonima: o dict do pai foi espalhado nos inputs. A camada e
            # o primeiro GeoDataFrame que chegou (o criterio de get_first_gdf).
            candidatos = [k for k, v in (inputs or {}).items() if e_camada(v)]
            if candidatos:
                if len({id(inputs[k]) for k in candidatos}) > 1:
                    self.log(
                        f"Mais de uma camada chegou a este no ({candidatos}); usando "
                        f"'{candidatos[0]}'. Declare duas ou mais portas para desenhar varias."
                    )
                nome = portas[0] if portas else "camada"
                rotulo = rotulo_da_porta(nome, rotulos) if portas else (rotulos.get(nome) or "Camada")
                valor = inputs[candidatos[0]]
                camadas.append(_Camada(
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

    def _caixa_4326(self, camadas: list) -> tuple:
        """A extensao de todas as camadas em lon/lat, para estimar o CRS.

        Camada sem CRS e tratada como EPSG:4326 AQUI, antes de qualquer
        reprojecao: `to_crs` sem CRS de origem falharia, e um `set_crs` com o
        CRS da carta rotularia graus como metros.
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

    async def _baixar_fundo(self, template: str, extensao_3857: tuple, largura_px: int):
        """Baixa e monta o mosaico de tiles que cobre a extensao (EPSG:3857).

        Cada URL passa pela guarda de SSRF (`safe_httpx_request` pina o IP,
        bloqueia redirect e limita o corpo), como nos nos de HTTP: um template
        escrito no fluxo nao pode alcancar a rede interna nem os metadados da
        nuvem. Duas conexoes por vez e retry so em erro transitorio (a politica
        de uso do OpenStreetMap); 4xx e erro definitivo.
        """
        z = zoom_para(extensao_3857, largura_px)
        z, tx0, tx1, ty0, ty1 = tiles_da_extensao(extensao_3857, z)
        await asyncio.to_thread(validate_url_ssrf, url_do_tile(template, z, tx0, ty0))

        semaforo = asyncio.Semaphore(CONEXOES_SIMULTANEAS)
        # O site da instalação no User-Agent, como a política do OSM pede
        # (flow/utils/identidade.py).
        cabecalhos = {"User-Agent": user_agent("carta")}

        async def um_tile(x: int, y: int):
            url = url_do_tile(template, z, x, y)
            async with semaforo:
                for tentativa in range(TENTATIVAS_POR_TILE):
                    ultima = tentativa == TENTATIVAS_POR_TILE - 1
                    try:
                        resposta = await safe_httpx_request(
                            "GET", url, timeout=20.0,
                            headers=cabecalhos,
                            max_response_bytes=TETO_DE_BYTES_POR_TILE,
                        )
                    except httpx.TransportError as exc:
                        if ultima:
                            raise ValueError(
                                f"Fundo de mapa: nao foi possivel baixar {url} ({exc})."
                            ) from exc
                        await asyncio.sleep(espera_exponencial(tentativa, teto=5.0, inicial=0.5))
                        continue
                    if resposta.status_code in STATUS_TRANSITORIOS and not ultima:
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
        imagem = await asyncio.to_thread(_montar_mosaico, tiles, tx0, tx1, ty0, ty1)
        self.log(f"Fundo de mapa: {len(tiles)} tile(s) no zoom {z}.")
        return imagem, extensao_dos_tiles(tx0, tx1, ty0, ty1, z)


# ── Funcoes de modulo (rodam em thread, sem `self`) ──────────────────────────

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


def _caixa_das_camadas(camadas: list) -> tuple:
    caixas = [tuple(float(v) for v in c.gdf.total_bounds) for c in camadas]
    return (
        min(b[0] for b in caixas), min(b[1] for b in caixas),
        max(b[2] for b in caixas), max(b[3] for b in caixas),
    )


def _tipo_de_geometria(gdf: Any) -> str:
    tipos = set(gdf.geom_type.dropna().str.replace("Multi", "", regex=False))
    if tipos and tipos <= {"Point"}:
        return "ponto"
    if tipos and tipos <= {"LineString", "LinearRing"}:
        return "linha"
    return "poligono"


def _montar_mosaico(tiles: list, tx0: int, tx1: int, ty0: int, ty1: int):
    from PIL import Image

    largura = (tx1 - tx0 + 1) * TAMANHO_DO_TILE
    altura = (ty1 - ty0 + 1) * TAMANHO_DO_TILE
    mosaico = Image.new("RGB", (largura, altura), "white")
    for x, y, conteudo in tiles:
        tile = Image.open(io.BytesIO(conteudo)).convert("RGB")
        if tile.size != (TAMANHO_DO_TILE, TAMANHO_DO_TILE):
            tile = tile.resize((TAMANHO_DO_TILE, TAMANHO_DO_TILE))
        mosaico.paste(tile, ((x - tx0) * TAMANHO_DO_TILE, (y - ty0) * TAMANHO_DO_TILE))
    return mosaico


def _renderizar(r: _Render) -> bytes:
    """Desenha a carta e devolve os bytes do arquivo. Roda em thread.

    API orientada a objeto do matplotlib (Figure + FigureCanvasAgg): sem
    pyplot, sem `rc_context` (estado global compartilhado entre threads) —
    tamanhos e cores vao por artista.
    """
    _carregar_matplotlib()
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.ticker import FixedLocator, FuncFormatter

    fig = Figure(figsize=(r.largura_pol, r.altura_pol), dpi=r.dpi)
    FigureCanvasAgg(fig)

    # O mapa a esquerda; a coluna da direita so existe com legenda. A extensao
    # ja veio na proporcao deste quadro (extensao_no_quadro), entao o eixo
    # nao encolhe.
    caixa_mapa = list(quadro_do_mapa(r.legenda))
    ax = fig.add_axes(caixa_mapa)
    x0, y0, x1, y1 = r.extensao

    if r.fundo is not None and r.fundo_extensao is not None:
        ax.imshow(
            np.asarray(r.fundo), extent=r.fundo_extensao, origin="upper",
            zorder=0, interpolation="bilinear",
        )
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    # `box`: o eixo encolhe para manter a proporcao e os limites ficam EXATOS —
    # e o que permite ancorar escala e norte por fracao da extensao.
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor("#f4f4f4" if r.fundo is None else "white")

    # Simplificacao a 1 pixel: e o que segura o desenho de camadas grandes sem
    # mudar nada visivel.
    largura_px_mapa = max(caixa_mapa[2] * r.largura_px, 1.0)
    tolerancia = (x1 - x0) / largura_px_mapa

    alcas: list = []
    for i, c in enumerate(r.camadas):
        gdf = c.gdf
        geometria = gdf.geometry.simplify(tolerancia, preserve_topology=True)
        gdf = gdf.set_geometry(geometria)
        borda = escurecer(c.cor)
        comum = dict(ax=ax, zorder=1 + i, alpha=r.opacidade, rasterized=r.rasterizar)
        tipo = _tipo_de_geometria(gdf)
        if tipo == "ponto":
            gdf.plot(color=c.cor, edgecolor=borda, linewidth=0.4, markersize=18, **comum)
            alcas.append(Line2D(
                [0], [0], linestyle="", marker="o", markerfacecolor=c.cor,
                markeredgecolor=borda, markersize=7, alpha=r.opacidade,
            ))
        elif tipo == "linha":
            gdf.plot(color=c.cor, linewidth=1.4, **comum)
            alcas.append(Line2D([0], [0], color=c.cor, linewidth=2, alpha=r.opacidade))
        else:
            gdf.plot(color=c.cor, edgecolor=borda, linewidth=0.6, **comum)
            alcas.append(Patch(facecolor=c.cor, edgecolor=borda, alpha=r.opacidade))
    # gdf.plot pode mexer nos limites (autoscale); a extensao da carta manda.
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    if r.grade:
        xs, ys = marcas_da_grade(r.extensao, r.crs_texto)
        ax.xaxis.set_major_locator(FixedLocator(xs))
        ax.yaxis.set_major_locator(FixedLocator(ys))
        crs_texto = r.crs_texto
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: rotulo_de_coordenada(v, "x", crs_texto)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: rotulo_de_coordenada(v, "y", crs_texto)))
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
        fator = 1.0
        if r.crs_e_3857:
            _lon, lat_c = lon_lat_de_3857((x0 + x1) / 2, (y0 + y1) / 2)
            fator = fator_de_escala_3857(lat_c)
        metros = comprimento_da_escala((x1 - x0) * fator)
        if metros > 0:
            comprimento = metros / fator            # em unidades do mapa
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
            ax.text(bx + comprimento, by + h * 1.7, rotulo_da_escala(metros), fontsize=7,
                    ha="center", va="bottom", zorder=42)

    if r.legenda:
        ax_leg = fig.add_axes([0.76, 0.11, 0.22, 0.79])
        ax_leg.axis("off")
        ax_leg.legend(
            alcas, [c.rotulo for c in r.camadas], loc="upper left", frameon=False,
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
