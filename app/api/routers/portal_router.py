# app/api/routers/portal_router.py
"""
Public sharing portal — endpoints for viewing maps,
publishing layers (PublishMap node), MVT tiles and GeoJSON download.
"""
import asyncio
import zlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.artifact import Artifact
from app.models.models import Workflow, WorkflowRun
from app.models.portal_layer import PortalLayer
from app.models.portal_feature import PortalFeature
from app.core.constants import REDIS_TTL_1H
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/artifacts",
    tags=["portal"],
)


# ── Portal access gate (reusable) ─────────────────────────────────────────────

async def enforce_portal_access(wf: "Workflow | None", request: Request) -> None:
    """Applies the portal's access control. Raises HTTPException if denied.

    disabled/nonexistent/inactive -> 404; public -> open; private -> access
    Bearer + member of portal_shared_with (401/403).

    Extracted from get_portal_data to also be applied to tiles and download —
    which before only checked 'disabled', leaking a private portal's geometries
    to anyone who knew workflow_hash + layer_key (low entropy).

    Accepts both the `Workflow` entity and a Row with the three columns the
    gate reads (`flag_ative`, `portal_access`, `portal_shared_with`) — the MVT tile
    projects only those so as not to load the workflow's `definition` per tile.
    """
    if not wf or not wf.flag_ative or wf.portal_access == "disabled":
        raise HTTPException(status_code=404, detail="Portal nao encontrado.")
    if wf.portal_access != "private":
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticacao necessaria.")
    token = auth_header[7:]

    # decode + audience(access) + type + blacklist, at the single point. Requires access
    # (blocks refresh/ws-token) and rejects a token revoked at logout.
    from app.api.dependencies import validate_access_token_claims
    claims = await validate_access_token_claims(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Token invalido.")

    allowed = [item.lower() for item in (wf.portal_shared_with or [])]
    if claims.get("sub", "") not in allowed and claims.get("username", "").lower() not in allowed:
        raise HTTPException(status_code=403, detail="Acesso negado a este portal.")


def _headers_do_tile(portal_access: str) -> dict:
    """Cache/CORS of an MVT tile according to the portal's visibility.

    The gate already 404s disabled/inactive; what remains here is public or private. A
    PRIVATE portal cannot go out as `public, max-age`: the browser (and any CDN that
    honors `public`) would keep the geometry and serve it for up to 1 h AFTER the owner
    revokes access — or to a request WITHOUT a Bearer. The endpoint's own comment
    says "nada de cache com TTL" (no TTL cache); the header contradicted it. Private ->
    `private, no-store` and no `Access-Control-Allow-Origin: *` (the origin of an
    authenticated response is not opened up). Public stays cacheable/CDN.
    """
    if portal_access == "public":
        return {"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"}
    return {"Cache-Control": "private, no-store"}


# ── GET /artifacts/portal/{workflow_hash} ─────────────────────────────────────

@router.get("/portal/{workflow_hash}", summary="Dados do portal publico de um workflow")
async def get_portal_data(
    workflow_hash: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns metadata and published layers of a workflow's portal.
    Access controlled by portal_access: disabled->404, public->open, private->JWT required.
    """
    # Projects only the gate's 4 columns + the response name — not the whole
    # entity, which would drag along the `definition` (the workflow, dozens of KB) in a
    # public endpoint called on every portal open. Same pattern as the MVT.
    result = await db.execute(
        select(
            Workflow.name, Workflow.flag_ative,
            Workflow.portal_access, Workflow.portal_shared_with,
        ).where(Workflow.id_hash == workflow_hash)
    )
    wf = result.first()
    await enforce_portal_access(wf, request)

    # Fetch layer metadata (without geojson_data)
    _pl_cols = (
        PortalLayer.id_hash, PortalLayer.layer_key, PortalLayer.features,
        PortalLayer.bbox, PortalLayer.geometry_type,
        PortalLayer.title, PortalLayer.color, PortalLayer.opacity,
        PortalLayer.description, PortalLayer.visible_fields,
        PortalLayer.updated_at,
    )
    layers_result = await db.execute(
        select(*_pl_cols).where(PortalLayer.workflow_hash == workflow_hash)
    )

    layers = []
    run_date = None
    for pl in layers_result.all():
        if pl.updated_at:
            ts = pl.updated_at.isoformat()
            if run_date is None or ts > run_date:
                run_date = ts
        layers.append({
            "id_hash": pl.id_hash,
            "layer_key": pl.layer_key,
            "filename": f"{pl.layer_key}.geojson",
            "features": pl.features,
            "bbox": pl.bbox,
            "geometry_type": pl.geometry_type,
            # `updated_at` becomes part of the tile URL (cache-busting). Without it,
            # MapLibre/Cloudflare/browser serve stale tiles after a re-publication.
            "updated_at": pl.updated_at.isoformat() if pl.updated_at else None,
            "publish_config": {
                "title": pl.title,
                "color": pl.color,
                "opacity": pl.opacity,
                "description": pl.description,
                "visible_fields": pl.visible_fields,
            },
        })

    # Fallback: se portal_layers vazio, tenta artifacts (compatibilidade)
    if not layers:
        run_result = await db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_hash == workflow_hash, WorkflowRun.status == "success")
            .order_by(WorkflowRun.end_time.desc())
            .limit(1)
        )
        last_run = run_result.scalar_one_or_none()
        if last_run:
            run_date = last_run.end_time.isoformat() if last_run.end_time else None
            artifacts_result = await db.execute(
                select(Artifact).where(
                    Artifact.run_id == last_run.task_id,
                    Artifact.is_published == True,
                )
            )
            for art in artifacts_result.scalars().all():
                layers.append({
                    "id_hash": art.id_hash,
                    "filename": art.filename,
                    "features": art.features,
                    "publish_config": art.publish_config,
                })

    return {
        "workflow_name": wf.name,
        "portal_access": wf.portal_access,
        "run_date": run_date,
        "layers": layers,
    }


# ── POST /artifacts/portal/publish ────────────────────────────────────────────

_MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
# Ceiling on the incoming BODY (compressed or not). A legitimate gzip of 50 MB of
# GeoJSON fits WELL below this; above it is a bomb or an absurd payload, rejected
# before being materialized.
_MAX_COMPRESSED_BYTES = _MAX_UNCOMPRESSED_BYTES


class _BodyTooLarge(Exception):
    """Body (compressed or decompressed) exceeded the configured ceiling."""


async def _read_limited_body(request: Request, teto: int) -> bytes:
    """Reads the body in chunks, cutting at the ceiling — never buffers an absurd body.

    `await request.body()` materializes the whole body in RAM before any
    check; here a body above the ceiling is rejected as soon as it crosses it, without
    being read in full.
    """
    pedacos: list[bytes] = []
    total = 0
    async for pedaco in request.stream():
        total += len(pedaco)
        if total > teto:
            raise _BodyTooLarge()
        pedacos.append(pedaco)
    return b"".join(pedacos)


def _decompress_gzip_with_ceiling(raw: bytes, teto: int) -> bytes:
    """Decompresses gzip in chunks, cutting at the ceiling — never materializes the bomb.

    `gzip.decompress()` would decompress the ENTIRE payload before any size
    check; a bomb (a few KB -> GBs) would bring down the API through memory. The
    decompressobj stops producing at the first byte above the ceiling. Synchronous and
    CPU-bound — call it via asyncio.to_thread so as not to block the event loop.
    """
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = espera cabecalho gzip
    saida = bytearray()
    dados = raw
    while True:
        # +1 on the limit to detect the overflow exactly at the ceiling
        saida += d.decompress(dados, max(1, teto + 1 - len(saida)))
        if len(saida) > teto:
            raise _BodyTooLarge()
        dados = d.unconsumed_tail
        if not dados:
            break
    saida += d.flush()
    if len(saida) > teto:
        raise _BodyTooLarge()
    return bytes(saida)


@router.post("/portal/publish", status_code=201,
             summary="Publica uma camada no portal (chamado pelo no PublishMap)")
async def publish_portal_layer(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Recebe GeoJSON comprimido (gzip) e faz upsert na portal_layers."""
    import json as _json
    from app.api.dependencies import get_agent_from_mtls
    from uuid import uuid4

    # ── 1. Autenticacao via mTLS
    try:
        executor = await get_agent_from_mtls(request, db)
    except HTTPException:
        raise

    # ── 2. Read + decompress with a ceiling (anti-bomb, off the event loop)
    # Reads in chunks cutting at the ceiling (never buffers an absurd body) and, if
    # gzip, decompresses incrementally stopping at the first byte above the limit
    # — a bomb (a few KB -> GBs) is rejected without being materialized. Decompressing
    # and the json.loads (50 MB) go to a thread so as not to block the event loop.
    try:
        raw_body = await _read_limited_body(request, _MAX_COMPRESSED_BYTES)
    except _BodyTooLarge:
        raise HTTPException(status_code=413, detail=f"Payload excede {_MAX_UNCOMPRESSED_BYTES // (1024*1024)}MB.")

    if request.headers.get("Content-Encoding", "") == "gzip":
        try:
            raw_body = await asyncio.to_thread(_decompress_gzip_with_ceiling, raw_body, _MAX_UNCOMPRESSED_BYTES)
        except _BodyTooLarge:
            raise HTTPException(status_code=413, detail=f"Payload excede {_MAX_UNCOMPRESSED_BYTES // (1024*1024)}MB.")
        except Exception:
            raise HTTPException(status_code=400, detail="Falha na descompressao gzip.")

    try:
        body = await asyncio.to_thread(_json.loads, raw_body)
    except _json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON invalido.")

    # ── 3. Validacao
    workflow_hash = body.get("workflow_hash")
    workspace_id  = body.get("workspace_id")
    run_id        = body.get("run_id")
    layer_key     = body.get("layer_key")
    geojson       = body.get("geojson")
    publish_config = body.get("publish_config", {})

    if not all([workflow_hash, workspace_id, layer_key, geojson]):
        raise HTTPException(status_code=422, detail="Campos obrigatorios: workflow_hash, workspace_id, layer_key, geojson.")

    # ── 4. Autorizacao
    from app.services.user_executor_service import get_agent_workspace_ids
    agent_ws_ids = await get_agent_workspace_ids(db, executor.id_hash, executor.is_default)
    if workspace_id not in agent_ws_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    wf_result = await db.execute(
        select(Workflow).where(Workflow.id_hash == workflow_hash, Workflow.workspace_id == workspace_id)
    )
    if not wf_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # ── 5. Validacao GeoJSON
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection":
        raise HTTPException(status_code=400, detail="GeoJSON deve ser um FeatureCollection.")
    features_list = geojson.get("features", [])
    if not isinstance(features_list, list):
        raise HTTPException(status_code=400, detail="GeoJSON.features deve ser uma lista.")

    _MAX_FEATURES = 500_000
    if len(features_list) > _MAX_FEATURES:
        raise HTTPException(status_code=400, detail=f"Limite de {_MAX_FEATURES} features excedido ({len(features_list)}).")

    # Basic validation of the features' structure
    for i, feat in enumerate(features_list[:10]):  # valida amostra
        if not isinstance(feat, dict):
            raise HTTPException(status_code=400, detail=f"Feature[{i}] não é um objeto válido.")
        geom = feat.get("geometry")
        if geom and isinstance(geom, dict):
            coords = geom.get("coordinates")
            if coords is None:
                raise HTTPException(status_code=400, detail=f"Feature[{i}].geometry sem coordinates.")

    safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in layer_key).lower()

    # ── 6. Idempotencia
    idem_key = request.headers.get("X-Idempotency-Key", "")
    if idem_key:
        try:
            from app.core.redis import get_redis_pool
            rc = get_redis_pool()
            existing = await rc.get(f"portal:idem:{idem_key}")
            if existing:
                return _json.loads(existing)
        except Exception as exc:
            logger.debug("Falha ao verificar idempotência no Redis (portal): %s", exc)

    # ── 7. UPSERT portal_layers
    result = await db.execute(
        select(PortalLayer).where(PortalLayer.workflow_hash == workflow_hash, PortalLayer.layer_key == safe_key)
    )
    existing_layer = result.scalar_one_or_none()

    title    = publish_config.get("title", "Camada")
    color    = publish_config.get("color", "#3b82f6")
    opacity  = publish_config.get("opacity", 0.5)
    desc     = publish_config.get("description", "")
    vis_flds = publish_config.get("visible_fields", [])

    _layer_bbox = None
    _geom_type = None
    if features_list:
        _first_geom = features_list[0].get("geometry", {})
        _geom_type = _first_geom.get("type")
        _bboxes = [_compute_bbox_from_geom(f.get("geometry")) for f in features_list if f.get("geometry")]
        _bboxes = [b for b in _bboxes if b]
        if _bboxes:
            _layer_bbox = [min(b[0] for b in _bboxes), min(b[1] for b in _bboxes),
                           max(b[2] for b in _bboxes), max(b[3] for b in _bboxes)]

    if existing_layer:
        existing_layer.geojson_data = geojson
        existing_layer.features = len(features_list)
        existing_layer.title = title
        existing_layer.color = color
        existing_layer.opacity = opacity
        existing_layer.description = desc
        existing_layer.visible_fields = vis_flds
        existing_layer.bbox = _layer_bbox
        existing_layer.geometry_type = _geom_type
        existing_layer.run_id = run_id
        layer_id_hash = existing_layer.id_hash
    else:
        new_layer = PortalLayer(
            id_hash=str(uuid4()), workflow_hash=workflow_hash, layer_key=safe_key,
            geojson_data=geojson, features=len(features_list),
            title=title, color=color, opacity=opacity, description=desc,
            visible_fields=vis_flds, bbox=_layer_bbox, geometry_type=_geom_type, run_id=run_id,
        )
        db.add(new_layer)
        layer_id_hash = new_layer.id_hash

    await db.flush()

    # ── 8. Portal features (PostGIS)
    from sqlalchemy import text as sa_text
    layer_pk_result = await db.execute(
        select(PortalLayer.id).where(PortalLayer.workflow_hash == workflow_hash, PortalLayer.layer_key == safe_key)
    )
    layer_pk = layer_pk_result.scalar_one()

    await db.execute(delete(PortalFeature).where(PortalFeature.layer_id == layer_pk))

    _BATCH_SIZE = 500
    rows = []
    for feat in features_list:
        geom_json = feat.get("geometry")
        props = feat.get("properties", {})
        if not geom_json:
            continue
        import json as _j
        bbox = _compute_bbox_from_geom(geom_json)
        rows.append({
            "layer_id": layer_pk, "properties": _j.dumps(props), "geom_str": _j.dumps(geom_json),
            "min_x": bbox[0] if bbox else 0, "min_y": bbox[1] if bbox else 0,
            "max_x": bbox[2] if bbox else 0, "max_y": bbox[3] if bbox else 0,
        })

    _insert_sql = sa_text("""
        INSERT INTO portal_features (layer_id, properties, geom, min_x, min_y, max_x, max_y)
        VALUES (:layer_id, :properties, ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(:geom_str), 4326)), :min_x, :min_y, :max_x, :max_y)
    """)
    for i in range(0, len(rows), _BATCH_SIZE):
        await db.execute(_insert_sql, rows[i:i + _BATCH_SIZE])

    await db.commit()

    # ── 9. Cache idempotencia
    response_body = {"status": "ok", "layer_id": layer_id_hash, "features_stored": len(features_list)}
    if idem_key:
        try:
            from app.core.redis import get_redis_pool
            rc = get_redis_pool()
            await rc.setex(f"portal:idem:{idem_key}", REDIS_TTL_1H, _json.dumps(response_body))
        except Exception as exc:
            logger.debug("Falha ao salvar idempotência no Redis (portal): %s", exc)

    logger.info("Portal: camada '%s' publicada (workflow=%s, features=%d).", safe_key, workflow_hash, len(features_list))
    return response_body


# ── GET /artifacts/portal/layers/{id}/download ────────────────────────────────

@router.get("/portal/layers/{layer_id_hash}/download",
            summary="Download do GeoJSON de uma camada do portal")
async def download_portal_layer(
    layer_id_hash: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serves the GeoJSON stored in portal_layers straight from the database."""
    from fastapi.responses import JSONResponse
    result = await db.execute(select(PortalLayer).where(PortalLayer.id_hash == layer_id_hash))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Camada nao encontrada.")

    # SEC: resolves the owning workflow and applies the same gate. Before, the entire
    # GeoJSON went out without any check, only the layer UUID was needed.
    wf_result = await db.execute(
        select(
            Workflow.flag_ative, Workflow.portal_access, Workflow.portal_shared_with,
        ).where(Workflow.id_hash == pl.workflow_hash)
    )
    await enforce_portal_access(wf_result.first(), request)

    return JSONResponse(
        content=pl.geojson_data,
        headers={"Content-Disposition": f'attachment; filename="{pl.layer_key}.geojson"'},
    )


# ── GET /artifacts/tiles/{wf}/{layer}/{z}/{x}/{y}.pbf ────────────────────────

@router.get("/tiles/{workflow_hash}/{layer_key}/{z}/{x}/{y}.pbf",
            summary="Tile MVT de uma camada do portal")
async def get_mvt_tile(
    workflow_hash: str, layer_key: str,
    z: int, x: int, y: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Gera tile MVT via ST_AsMVT do PostGIS."""
    from fastapi.responses import Response

    # PERF: a pan/zoom on the portal requests dozens of tiles, and each one paid THREE
    # trips to Postgres: workflow (whole entity, dragging along the workflow's full
    # `definition`), layer and the ST_AsMVT. Here the first two become a
    # single one, with an outerjoin and only the columns the gate uses.
    #
    # SEC: same gate as get_portal_data, and it is still read from the database on every
    # tile — no TTL cache, which would make a portal marked as private
    # keep serving geometries until the deadline expired. Before, only 'disabled' was
    # checked and private portal tiles went out without auth.
    gate_result = await db.execute(
        select(
            Workflow.flag_ative,
            Workflow.portal_access,
            Workflow.portal_shared_with,
            PortalLayer.id.label("layer_id"),
        )
        .select_from(Workflow)
        .outerjoin(
            PortalLayer,
            (PortalLayer.workflow_hash == Workflow.id_hash)
            & (PortalLayer.layer_key == layer_key),
        )
        .where(Workflow.id_hash == workflow_hash)
    )
    gate = gate_result.first()

    await enforce_portal_access(gate, request)

    layer_id = gate.layer_id
    if layer_id is None:
        raise HTTPException(status_code=404, detail="Camada nao encontrada.")

    tile_data = await tile_mvt(db, layer_id=layer_id, layer_key=layer_key, z=z, x=x, y=y)

    headers = _headers_do_tile(gate.portal_access)
    if not tile_data:
        return Response(content=b"", status_code=204, headers=headers)
    return Response(
        content=tile_data,
        media_type="application/x-protobuf",
        headers=headers,
    )


async def tile_mvt(db: AsyncSession, *, layer_id: int, layer_key: str, z: int, x: int, y: int) -> bytes | None:
    """The `ST_AsMVT` query for ONE layer — the core shared between the portal
    tile (here) and the Home tile (`assistente_camadas_router`, with a MEMBER gate
    instead of the portal one). Receives the `layer_id` ALREADY resolved and authorized
    by the caller: it does no gating at all. Returns the protobuf bytes, or None when the
    tile intersects no feature (the caller responds 204)."""
    from sqlalchemy import text

    tile_query = text("""
        SELECT ST_AsMVT(q, :layer_name, 4096, 'geom') FROM (
            SELECT
                ST_AsMVTGeom(ST_Transform(pf.geom, 3857), ST_TileEnvelope(:z, :x, :y), 4096, 64, true) AS geom,
                pf.properties
            FROM portal_features pf
            WHERE pf.layer_id = :layer_id AND pf.geom IS NOT NULL
              AND ST_Intersects(pf.geom, ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326))
        ) q
    """)
    result = await db.execute(tile_query, {"layer_name": layer_key, "z": z, "x": x, "y": y, "layer_id": layer_id})
    tile_data = result.scalar()
    return bytes(tile_data) if tile_data else None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_bbox_from_geom(geom: dict) -> tuple | None:
    coords = _extract_geom_coords(geom)
    if not coords:
        return None
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (min(xs), min(ys), max(xs), max(ys))


def _extract_geom_coords(geom: dict) -> list:
    t = geom.get("type", "")
    c = geom.get("coordinates")
    if t == "Point":
        return [c] if c else []
    if t in ("MultiPoint", "LineString"):
        return c or []
    if t in ("MultiLineString", "Polygon"):
        return [pt for ring in (c or []) for pt in ring]
    if t == "MultiPolygon":
        return [pt for poly in (c or []) for ring in poly for pt in ring]
    if t == "GeometryCollection":
        return [pt for g in geom.get("geometries", []) for pt in _extract_geom_coords(g)]
    return []
