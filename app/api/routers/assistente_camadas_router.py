# app/api/routers/assistente_camadas_router.py
"""Camadas do globo da Home (superficie `home`), com portao de MEMBRO.

Duas rotas, ambas JWT + membro do workspace do recurso (nunca o portao de
portal, que exige publicacao/allowlist):

- `GET /assistente/camadas/{artifact_id}` — o que a Home precisa para por uma saida
  de execucao no globo (geojson por URL assinada, mvt por tiles, ou indisponivel
  com o motivo). Limiter proprio de 60/min: o teto de 10/min do download publico
  (`artifacts_router`) estrangularia um globo com varias camadas.
- `GET /assistente/tiles/{workflow_hash}/{layer_key}/{z}/{x}/{y}.pbf` — os tiles
  vetoriais de uma camada publicada, servidos ao MEMBRO (o portal so serve
  publicado/compartilhado). Reusa a query `ST_AsMVT` do portal (`tile_mvt`).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user, get_user_workspace_ids
from app.api.routers.portal_router import tile_mvt
from app.core.authorization.workflow_access import verify_workspace_access
from app.core.rate_limiter import limiter
from app.core.storage import presigned_get_async
from app.models.artifact import Artifact
from app.models.models import Workflow
from app.models.portal_layer import PortalLayer
from app.models.run_metrics import NodeRunMetrics
from app.schemas.assistente import CamadaDoGlobo

router = APIRouter(prefix="/assistente", tags=["assistente"])

# Prazo do link pre-assinado do GeoJSON. Igual ao das tools de acervo: curto,
# porque a web faz o fetch na hora e guarda a FeatureCollection em memoria.
VALIDADE_DO_LINK_S = 900


def _e_4326(crs: Optional[str]) -> bool:
    """O CRS e WGS84? Aceita as formas que o pipeline grava ("EPSG:4326", "4326").

    Só o 4326 vai para o globo: o MapLibre coloca coordenadas como lon/lat, e uma
    FeatureCollection em CRS nativo apareceria no lugar errado. CRS ausente conta
    como 4326 — é o default do GeoJSON e o que o pipeline produz salvo escolha
    explícita.
    """
    if not crs:
        return True
    return crs.strip().upper().replace("EPSG:", "").strip() == "4326"


def _chave_da_camada(filename: Optional[str]) -> Optional[str]:
    """O `layer_key` que ESTE artefato teria, a partir do nome do arquivo.

    Mesma normalizacao de `portal_router._publicar` (que reescreve o `layer_key`
    recebido antes de gravar), para as duas pontas concordarem mesmo quando o
    titulo da camada tinha caractere fora de [a-z0-9-_].
    """
    if not filename:
        return None
    bruto = filename.removesuffix(".geojson").strip()
    if not bruto:
        return None
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in bruto).lower()


async def _camada_publicada(db: AsyncSession, art: Artifact):
    """A `PortalLayer` DESTE artefato, ou None quando nao da para saber qual e.

    O recorte e sempre o RUN do artefato. `portal_router._publicar` faz UPSERT em
    `(workflow_hash, layer_key)` e reescreve a linha no lugar (geojson, bbox,
    geometry_type, run_id): a linha reflete SEMPRE a ultima publicacao daquela
    chave. Casar so por `(workflow_hash, layer_key)` fazia o artefato da execucao
    #1 servir os tiles e a bbox da execucao #5, rotulados como o artefato antigo.

    Dentro do run, o `layer_key` derivado do nome do arquivo e o desempate — um
    fluxo com dois nos PublishMap na mesma execucao produz DUAS linhas do mesmo
    run, e escolher "a primeira" entregava a camada do outro no. Sem chave que
    case, aceita a camada do run so quando ela e UNICA; havendo empate, devolve
    None em vez de escolher em silencio.

    None manda o artefato para o ramo GeoJSON (o dado daquele run, correto) ou
    para `indisponivel`.
    """
    if not art.run_id:
        # Sem run nao ha como saber se a linha publicada e deste artefato.
        return None

    colunas = (PortalLayer.layer_key, PortalLayer.bbox, PortalLayer.geometry_type)
    do_run = (
        await db.execute(
            select(*colunas)
            .where(
                PortalLayer.workflow_hash == art.workflow_hash,
                PortalLayer.run_id == art.run_id,
            )
            .order_by(PortalLayer.id.asc())
        )
    ).all()
    if not do_run:
        return None

    chave = _chave_da_camada(art.filename)
    if chave:
        exata = next((linha for linha in do_run if linha.layer_key == chave), None)
        if exata is not None:
            return exata

    return do_run[0] if len(do_run) == 1 else None


@router.get(
    "/camadas/{artifact_id}",
    response_model=CamadaDoGlobo,
    summary="Metadados de uma saida de execucao para o globo da Home",
)
@limiter.limit("60/minute")
async def camada_do_globo(
    artifact_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    art = (
        await db.execute(select(Artifact).where(Artifact.id_hash == artifact_id))
    ).scalar_one_or_none()
    if art is None:
        raise HTTPException(status_code=404, detail="Artefato nao encontrado.")
    # Portao de MEMBRO: 403 se o artefato nao e de nenhum workspace do usuario.
    verify_workspace_access(art.workspace_id, workspace_ids)

    # Metricas espaciais ja calculadas na execucao (bbox/crs/geometry_type), sem
    # recalculo. A chave e (run_id, node_id) — UMA linha por NO, nao por saida —,
    # e o coletor sobrescreve `spatial` a cada saida do no: num no multi-saida o
    # que sobra e o metadado da ULTIMA GeoDataFrame iterada, que pode nao ser
    # deste artefato.
    metrics = None
    saidas_do_no = 0
    if art.run_id and art.node_id:
        metrics = (
            await db.execute(
                select(
                    NodeRunMetrics.geometry_type,
                    NodeRunMetrics.crs,
                    NodeRunMetrics.bbox,
                )
                .where(
                    NodeRunMetrics.run_id == art.run_id,
                    NodeRunMetrics.node_id == art.node_id,
                )
            )
        ).first()
        saidas_do_no = int(
            (
                await db.execute(
                    select(func.count(Artifact.id)).where(
                        Artifact.run_id == art.run_id, Artifact.node_id == art.node_id
                    )
                )
            ).scalar()
            or 0
        )

    # Com mais de uma saida no no, `bbox` e `geometry_type` sao ambiguos: enquadrar
    # a extensao de outra camada ou rotular a geometria errada e pior que nao
    # enquadrar e nao rotular. O `crs`, ao contrario, e MANTIDO: ele so serve a
    # guarda do passo 2, e errar para o lado de recusar uma camada e mais seguro
    # que desenha-la no lugar errado.
    ambiguo = saidas_do_no > 1
    geometry_type = metrics.geometry_type if metrics and not ambiguo else None
    crs = metrics.crs if metrics else None
    bbox = metrics.bbox if metrics and not ambiguo else None

    base = dict(
        artifact_id=art.id_hash,
        nome=art.filename,
        output_key=art.output_key,
        format=art.format,
        features=art.features,
        size_bytes=art.size_bytes,
        geometry_type=geometry_type,
        crs=crs,
        # `bbox` so acompanha quando confiavel (4326); senao a web nao enquadra.
        bbox=bbox if _e_4326(crs) else None,
        workflow_id=art.workflow_hash,
        run_id=art.run_id,
        expires_at=art.expires_at,
        # As duas condicoes que `_url_de_download` (artifacts_router) impoe, nesta
        # ordem: `content_location == "executor"` e recusado com 409 (a marcacao
        # `keepLocal` proibe o servidor de buscar o conteudo) e sem `s3_key` nao
        # ha objeto no storage (404). Calcular aqui poupa a web de descobrir por
        # tentativa e erro — e e o que deixa o botao de baixar SUMIR em vez de
        # falhar no clique.
        baixavel=art.content_location != "executor" and bool(art.s3_key),
    )

    def indisponivel(hint: str) -> CamadaDoGlobo:
        return CamadaDoGlobo(tipo="indisponivel", available=False, hint=hint, **base)

    # 1) Publicada no portal (PublishMap): tiles vetoriais servidos ao membro.
    #    Casada por (workflow_hash, RUN do artefato) e, dentro do run, pelo
    #    LAYER_KEY: a linha de `portal_layers` e reescrita in place a cada
    #    publicacao da mesma chave, entao ela so descreve este artefato quando o
    #    `run_id` dela ainda e o dele; e um fluxo com dois nos PublishMap na mesma
    #    execucao produz DUAS linhas do mesmo run, onde "a primeira" entregava a
    #    camada do outro no — a pessoa pedia "rios" e recebia "municipios".
    #    O discriminador existe: o artefato grava `filename = f"{safe_key}.geojson"`
    #    e a publicacao usa o mesmo `safe_key` como `layer_key`
    #    (flow/nodes/outputs/publish_map.py, app/api/routers/portal_router.py).
    #    Vem ANTES da guarda de CRS: o portal forca 4326 (`ST_SetSRID(...,4326)`)
    #    ao publicar, entao a camada publicada e sempre 4326, qualquer que seja o
    #    CRS que as metricas do no de origem registraram.
    if art.is_published and art.workflow_hash:
        camada_pub = await _camada_publicada(db, art)
        if camada_pub is not None:
            return CamadaDoGlobo(
                **{
                    **base,
                    "tipo": "mvt",
                    "available": True,
                    "mvt": {"workflow_id": art.workflow_hash, "layer_key": camada_pub.layer_key},
                    # bbox do PortalLayer e sempre 4326 (forcado na publicacao).
                    "bbox": camada_pub.bbox,
                    "geometry_type": camada_pub.geometry_type or geometry_type,
                }
            )

    # 2) GeoJSON no storage: URL pre-assinada, a web faz fetch e guarda em memoria.
    #    A guarda de CRS mora AQUI: a web le as coordenadas cruas da
    #    FeatureCollection, e o MapLibre as trata como lon/lat — CRS != 4326
    #    apareceria no lugar errado, e a v1 nao reprojeta.
    if art.format == "geojson" and art.content_location != "executor" and art.s3_key:
        if not _e_4326(crs):
            return indisponivel(
                "esta camada esta num sistema de coordenadas diferente de WGS84 (EPSG:4326) "
                "e a versao atual nao a reprojeta para o globo"
            )
        url = await presigned_get_async(
            art.s3_key, expires=VALIDADE_DO_LINK_S, filename=art.filename
        )
        return CamadaDoGlobo(
            **{
                **base,
                "tipo": "geojson",
                "available": True,
                "download_url": url,
                "url_expires_in": VALIDADE_DO_LINK_S,
            }
        )

    # 3) Sem previa: o motivo mais especifico que couber.
    if art.content_location == "executor":
        return indisponivel(
            "o conteudo desta camada permanece no executor e nunca foi enviado para a "
            "nuvem: nao ha previa no globo"
        )
    if art.format != "geojson":
        return indisponivel(
            f"a versao atual so poe GeoJSON e camadas publicadas no globo; este artefato e '{art.format}'"
        )
    return indisponivel("esta camada nao tem conteudo no storage")


@router.get(
    "/tiles/{workflow_hash}/{layer_key}/{z}/{x}/{y}.pbf",
    summary="Tile MVT de uma camada publicada, com portao de membro",
)
# Teto proprio, e mais alto que os 60/min da irma porque a unidade e outra: um
# unico pan do globo pede dezenas de tiles, e cada tile custa um ciclo do route
# handler do Next (`/terra`, com decode de sessao), o SELECT do portao e um
# `ST_AsMVT`. 600/min deixa o uso normal passar e ainda poe um teto — antes esta
# era a UNICA rota nova sem limiter nenhum.
@limiter.limit("600/minute")
async def tile_do_membro(
    workflow_hash: str,
    layer_key: str,
    z: int,
    x: int,
    y: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    workspace_ids: List[str] = Depends(get_user_workspace_ids),
):
    """Mesma consulta do tile do portal, com portao de MEMBRO no lugar do de
    portal: o dono ve as proprias camadas no globo sem publicar para o mundo.
    404 uniforme quando o fluxo nao existe, foi apagado, nao e do usuario, ou nao
    tem a camada — nunca revela qual dos quatro.

    `deleted_at IS NULL` na consulta: o soft delete tambem nao apaga o
    `PortalLayer`, entao sem este filtro quem tivesse (ou reconstruisse) a URL
    continuava recebendo as geometrias de um fluxo apagado, indefinidamente. NAO
    se filtra por `flag_ative` — diferente do portal publico: um fluxo pausado
    nao e um fluxo apagado, e o membro segue vendo no globo o que ja existe."""
    gate = (
        await db.execute(
            select(Workflow.workspace_id, PortalLayer.id.label("layer_id"))
            .select_from(Workflow)
            .outerjoin(
                PortalLayer,
                (PortalLayer.workflow_hash == Workflow.id_hash)
                & (PortalLayer.layer_key == layer_key),
            )
            .where(Workflow.id_hash == workflow_hash, Workflow.deleted_at.is_(None))
        )
    ).first()

    # 404 uniforme: fluxo inexistente, alheio, ou sem a camada. Nao distingue.
    if gate is None or gate.workspace_id not in workspace_ids or gate.layer_id is None:
        raise HTTPException(status_code=404, detail="Camada nao encontrada.")

    tile_data = await tile_mvt(db, layer_id=gate.layer_id, layer_key=layer_key, z=z, x=x, y=y)
    if not tile_data:
        return Response(content=b"", status_code=204)
    # `private`, NAO `public` como o portal: um tile de camada nao-publicada nao
    # pode ficar em cache compartilhado. E SEM `Access-Control-Allow-Origin: *`.
    return Response(
        content=tile_data,
        media_type="application/x-protobuf",
        headers={"Cache-Control": "private, max-age=300"},
    )
