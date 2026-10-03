# app/api/routers/assistente_camadas_router.py
"""Layers of the Home globe (`home` surface), with a MEMBER gate.

Two routes, both JWT + member of the resource's workspace (never the portal
gate, which requires publication/allowlist):

- `GET /assistente/camadas/{artifact_id}` — what Home needs to put a run output
  on the globe (geojson via signed URL, mvt via tiles, or unavailable with
  the reason). Its own limiter of 60/min: the 10/min ceiling of the public download
  (`artifacts_router`) would strangle a globe with several layers.
- `GET /assistente/tiles/{workflow_hash}/{layer_key}/{z}/{x}/{y}.pbf` — the vector
  tiles of a published layer, served to the MEMBER (the portal only serves
  published/shared ones). Reuses the portal's `ST_AsMVT` query (`tile_mvt`).
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

# Expiry of the GeoJSON's pre-signed link. Same as the collection tools': short,
# because the web app fetches it right away and keeps the FeatureCollection in memory.
VALIDADE_DO_LINK_S = 900


def _e_4326(crs: Optional[str]) -> bool:
    """Is the CRS WGS84? Accepts the forms the pipeline writes ("EPSG:4326", "4326").

    Only 4326 goes to the globe: MapLibre places coordinates as lon/lat, and a
    FeatureCollection in a native CRS would show up in the wrong place. A missing CRS
    counts as 4326 — it is the GeoJSON default and what the pipeline produces unless
    explicitly chosen otherwise.
    """
    if not crs:
        return True
    return crs.strip().upper().replace("EPSG:", "").strip() == "4326"


def _chave_da_camada(filename: Optional[str]) -> Optional[str]:
    """The `layer_key` THIS artifact would have, derived from the file name.

    Same normalization as `portal_router._publicar` (which rewrites the received
    `layer_key` before saving), so both ends agree even when the layer
    title had characters outside [a-z0-9-_].
    """
    if not filename:
        return None
    bruto = filename.removesuffix(".geojson").strip()
    if not bruto:
        return None
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in bruto).lower()


async def _camada_publicada(db: AsyncSession, art: Artifact):
    """THIS artifact's `PortalLayer`, or None when there is no way to tell which one it is.

    The slice is always the artifact's RUN. `portal_router._publicar` UPSERTs on
    `(workflow_hash, layer_key)` and rewrites the row in place (geojson, bbox,
    geometry_type, run_id): the row ALWAYS reflects the latest publication of that
    key. Matching only on `(workflow_hash, layer_key)` made the artifact of run
    #1 serve the tiles and bbox of run #5, labeled as the old artifact.

    Within the run, the `layer_key` derived from the file name is the tiebreaker — a
    workflow with two PublishMap nodes in the same run produces TWO rows of the same
    run, and picking "the first" delivered the other node's layer. With no matching
    key, it accepts the run's layer only when it is UNIQUE; on a tie, it returns
    None instead of choosing silently.

    None sends the artifact to the GeoJSON branch (that run's data, correct) or
    to `indisponivel`.
    """
    if not art.run_id:
        # Without a run there is no way to know whether the published row is this artifact's.
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
    # MEMBER gate: 403 if the artifact belongs to none of the user's workspaces.
    verify_workspace_access(art.workspace_id, workspace_ids)

    # Spatial metrics already computed during the run (bbox/crs/geometry_type), with no
    # recomputation. The key is (run_id, node_id) — ONE row per NODE, not per output —,
    # and the collector overwrites `spatial` on each of the node's outputs: on a
    # multi-output node what remains is the metadata of the LAST GeoDataFrame iterated,
    # which may not be this artifact's.
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

    # With more than one output on the node, `bbox` and `geometry_type` are ambiguous:
    # framing another layer's extent or labeling the wrong geometry is worse than not
    # framing and not labeling. The `crs`, on the other hand, is KEPT: it only serves
    # the guard in step 2, and erring on the side of refusing a layer is safer
    # than drawing it in the wrong place.
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
        # `bbox` only comes along when reliable (4326); otherwise the web app does not frame.
        bbox=bbox if _e_4326(crs) else None,
        workflow_id=art.workflow_hash,
        run_id=art.run_id,
        expires_at=art.expires_at,
        # The two conditions `_url_de_download` (artifacts_router) imposes, in this
        # order: `content_location == "executor"` is refused with 409 (the `keepLocal`
        # flag forbids the server from fetching the content) and without `s3_key` there
        # is no object in storage (404). Computing it here spares the web app from
        # finding out by trial and error — and it is what makes the download button
        # DISAPPEAR instead of failing on click.
        baixavel=art.content_location != "executor" and bool(art.s3_key),
    )

    def indisponivel(hint: str) -> CamadaDoGlobo:
        return CamadaDoGlobo(tipo="indisponivel", available=False, hint=hint, **base)

    # 1) Published on the portal (PublishMap): vector tiles served to the member.
    #    Matched by (workflow_hash, the artifact's RUN) and, within the run, by the
    #    LAYER_KEY: the `portal_layers` row is rewritten in place on each
    #    publication of the same key, so it only describes this artifact while
    #    its `run_id` is still the artifact's; and a workflow with two PublishMap
    #    nodes in the same run produces TWO rows of the same run, where "the first"
    #    delivered the other node's layer — the person asked for "rios" (rivers) and
    #    got "municipios" (municipalities).
    #    The discriminator exists: the artifact writes `filename = f"{safe_key}.geojson"`
    #    and the publication uses the same `safe_key` as `layer_key`
    #    (flow/nodes/outputs/publish_map.py, app/api/routers/portal_router.py).
    #    It comes BEFORE the CRS guard: the portal forces 4326 (`ST_SetSRID(...,4326)`)
    #    when publishing, so the published layer is always 4326, whatever
    #    CRS the source node's metrics recorded.
    if art.is_published and art.workflow_hash:
        camada_pub = await _camada_publicada(db, art)
        if camada_pub is not None:
            return CamadaDoGlobo(
                **{
                    **base,
                    "tipo": "mvt",
                    "available": True,
                    "mvt": {"workflow_id": art.workflow_hash, "layer_key": camada_pub.layer_key},
                    # The PortalLayer bbox is always 4326 (forced at publication).
                    "bbox": camada_pub.bbox,
                    "geometry_type": camada_pub.geometry_type or geometry_type,
                }
            )

    # 2) GeoJSON in storage: pre-signed URL, the web app fetches it and keeps it in memory.
    #    The CRS guard lives HERE: the web app reads the raw coordinates of the
    #    FeatureCollection, and MapLibre treats them as lon/lat — CRS != 4326
    #    would show up in the wrong place, and v1 does not reproject.
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

    # 3) No preview: the most specific reason that applies.
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
# Its own ceiling, higher than its sibling's 60/min because the unit is different: a
# single pan of the globe requests dozens of tiles, and each tile costs one cycle of
# the Next route handler (`/terra`, with session decoding), the gate's SELECT and an
# `ST_AsMVT`. 600/min lets normal use through and still sets a ceiling — before, this
# was the ONLY new route with no limiter at all.
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
    """Same query as the portal tile, with a MEMBER gate instead of the portal
    one: the owner sees their own layers on the globe without publishing to the world.
    Uniform 404 when the workflow does not exist, was deleted, is not the user's, or
    does not have the layer — never reveals which of the four.

    `deleted_at IS NULL` in the query: the soft delete does not delete the
    `PortalLayer` either, so without this filter whoever had (or reconstructed) the URL
    kept receiving the geometries of a deleted workflow, indefinitely. It does NOT
    filter by `flag_ative` — unlike the public portal: a paused workflow
    is not a deleted workflow, and the member keeps seeing on the globe what already exists."""
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

    # Uniform 404: nonexistent workflow, someone else's, or without the layer. Does not distinguish.
    if gate is None or gate.workspace_id not in workspace_ids or gate.layer_id is None:
        raise HTTPException(status_code=404, detail="Camada nao encontrada.")

    tile_data = await tile_mvt(db, layer_id=gate.layer_id, layer_key=layer_key, z=z, x=x, y=y)
    if not tile_data:
        return Response(content=b"", status_code=204)
    # `private`, NOT `public` like the portal: a tile of an unpublished layer must not
    # sit in a shared cache. And WITHOUT `Access-Control-Allow-Origin: *`.
    return Response(
        content=tile_data,
        media_type="application/x-protobuf",
        headers={"Cache-Control": "private, max-age=300"},
    )
