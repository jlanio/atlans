# app/api/routers/portal_router.py
"""
Portal de compartilhamento publico — endpoints para visualizacao de mapas,
publicacao de camadas (PublishMap node), tiles MVT e download de GeoJSON.
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


# ── Gate de acesso ao portal (reutilizavel) ───────────────────────────────────

async def enforce_portal_access(wf: "Workflow | None", request: Request) -> None:
    """Aplica o controle de acesso do portal. Levanta HTTPException se negado.

    disabled/inexistente/inativo -> 404; public -> livre; private -> Bearer de
    access + membro de portal_shared_with (401/403).

    Extraido de get_portal_data para ser aplicado tambem em tiles e download —
    que antes so checavam 'disabled', vazando as geometrias de um portal privado
    a qualquer um que soubesse workflow_hash + layer_key (baixa entropia).

    Aceita tanto a entidade `Workflow` quanto uma Row com as tres colunas que o
    gate le (`flag_ative`, `portal_access`, `portal_shared_with`) — o tile MVT
    projeta so essas para nao carregar a `definition` do fluxo por tile.
    """
    if not wf or not wf.flag_ative or wf.portal_access == "disabled":
        raise HTTPException(status_code=404, detail="Portal nao encontrado.")
    if wf.portal_access != "private":
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticacao necessaria.")
    token = auth_header[7:]

    # decode + audience(access) + type + blacklist, no ponto único. Exige access
    # (bloqueia refresh/ws-token) e rejeita token revogado no logout.
    from app.api.dependencies import validate_access_token_claims
    claims = await validate_access_token_claims(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Token invalido.")

    allowed = [item.lower() for item in (wf.portal_shared_with or [])]
    if claims.get("sub", "") not in allowed and claims.get("username", "").lower() not in allowed:
        raise HTTPException(status_code=403, detail="Acesso negado a este portal.")


def _headers_do_tile(portal_access: str) -> dict:
    """Cache/CORS de um tile MVT conforme a visibilidade do portal.

    O gate ja 404 disabled/inativo; aqui sobra public ou private. Um portal
    PRIVADO nao pode sair como `public, max-age`: o browser (e qualquer CDN que
    honre `public`) guardaria a geometria e a serviria por ate 1 h APOS o dono
    revogar o acesso — ou a uma requisicao SEM Bearer. O proprio comentario do
    endpoint diz "nada de cache com TTL"; o header contradizia isso. Privado ->
    `private, no-store` e sem `Access-Control-Allow-Origin: *` (nao se abre a
    origem de uma resposta autenticada). Publico segue cacheavel/CDN.
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
    Retorna metadados e camadas publicadas do portal de um workflow.
    Acesso controlado por portal_access: disabled->404, public->livre, private->JWT obrigatorio.
    """
    # Projeta só as 4 colunas do gate + o nome da resposta — não a entidade
    # inteira, que arrastaria a `definition` (o fluxo, dezenas de KB) num
    # endpoint público chamado a cada abertura do portal. Mesmo padrão do MVT.
    result = await db.execute(
        select(
            Workflow.name, Workflow.flag_ative,
            Workflow.portal_access, Workflow.portal_shared_with,
        ).where(Workflow.id_hash == workflow_hash)
    )
    wf = result.first()
    await enforce_portal_access(wf, request)

    # Busca metadados das camadas (sem geojson_data)
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
            # `updated_at` vira parte da URL do tile (cache-busting). Sem isso,
            # MapLibre/Cloudflare/browser servem tiles velhos apos uma re-publicacao.
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
# Teto do CORPO que entra (comprimido ou nao). Um gzip legitimo de 50 MB de
# GeoJSON cabe MUITO abaixo disto; acima e bomba ou payload absurdo, recusado
# antes de ser materializado.
_MAX_COMPRESSED_BYTES = _MAX_UNCOMPRESSED_BYTES


class _CorpoGrandeDemais(Exception):
    """Corpo (comprimido ou descomprimido) passou do teto configurado."""


async def _ler_corpo_limitado(request: Request, teto: int) -> bytes:
    """Le o corpo em blocos, cortando no teto — nunca bufferiza um corpo absurdo.

    `await request.body()` materializa o corpo inteiro na RAM antes de qualquer
    checagem; aqui um corpo acima do teto e recusado assim que passa, sem ser
    lido por inteiro.
    """
    pedacos: list[bytes] = []
    total = 0
    async for pedaco in request.stream():
        total += len(pedaco)
        if total > teto:
            raise _CorpoGrandeDemais()
        pedacos.append(pedaco)
    return b"".join(pedacos)


def _descomprimir_gzip_com_teto(raw: bytes, teto: int) -> bytes:
    """Descomprime gzip em blocos, cortando no teto — nunca materializa a bomba.

    `gzip.decompress()` descomprimiria o payload INTEIRO antes de qualquer check
    de tamanho; uma bomba (poucos KB -> GBs) derrubaria a API por memoria. O
    decompressobj para de produzir no primeiro byte acima do teto. Sincrono e
    CPU-bound — chame via asyncio.to_thread para nao travar o event loop.
    """
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)  # 16 = espera cabecalho gzip
    saida = bytearray()
    dados = raw
    while True:
        # +1 no limite para detectar o estouro exatamente no teto
        saida += d.decompress(dados, max(1, teto + 1 - len(saida)))
        if len(saida) > teto:
            raise _CorpoGrandeDemais()
        dados = d.unconsumed_tail
        if not dados:
            break
    saida += d.flush()
    if len(saida) > teto:
        raise _CorpoGrandeDemais()
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

    # ── 2. Leitura + descompressao com teto (anti-bomba, fora do event loop)
    # Le em blocos com corte no teto (nunca bufferiza um corpo absurdo) e, se
    # gzip, descomprime incrementalmente parando no primeiro byte acima do limite
    # — uma bomba (poucos KB -> GBs) e recusada sem materializar. descomprimir e
    # o json.loads (50 MB) vao para thread para nao travar o event loop.
    try:
        raw_body = await _ler_corpo_limitado(request, _MAX_COMPRESSED_BYTES)
    except _CorpoGrandeDemais:
        raise HTTPException(status_code=413, detail=f"Payload excede {_MAX_UNCOMPRESSED_BYTES // (1024*1024)}MB.")

    if request.headers.get("Content-Encoding", "") == "gzip":
        try:
            raw_body = await asyncio.to_thread(_descomprimir_gzip_com_teto, raw_body, _MAX_UNCOMPRESSED_BYTES)
        except _CorpoGrandeDemais:
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

    # Validação básica de estrutura das features
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
    """Serve o GeoJSON armazenado na portal_layers direto do banco."""
    from fastapi.responses import JSONResponse
    result = await db.execute(select(PortalLayer).where(PortalLayer.id_hash == layer_id_hash))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(status_code=404, detail="Camada nao encontrada.")

    # SEG: resolve o workflow dono e aplica o mesmo gate. Antes o GeoJSON
    # inteiro saia sem qualquer checagem, bastando o UUID da camada.
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

    # PERF: um pan/zoom no portal pede dezenas de tiles, e cada um pagava TRES
    # idas ao Postgres: workflow (entidade inteira, arrastando a `definition`
    # completa do fluxo), camada e o ST_AsMVT. Aqui as duas primeiras viram uma
    # só, com outerjoin e apenas as colunas que o gate usa.
    #
    # SEG: mesmo gate de get_portal_data, e continua sendo lido do banco a cada
    # tile — nada de cache com TTL, que faria um portal marcado como privado
    # seguir servindo geometrias até o prazo vencer. Antes so 'disabled' era
    # checado e tiles de portal privado saiam sem auth.
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
    """A query `ST_AsMVT` de UMA camada — o miolo compartilhado entre o tile do
    portal (aqui) e o tile da Home (`assistente_camadas_router`, com portao de MEMBRO
    em vez do de portal). Recebe o `layer_id` JA resolvido e autorizado por quem
    chama: nao faz gate nenhum. Devolve os bytes do protobuf, ou None quando o
    tile nao intersecta nenhuma feicao (o chamador responde 204)."""
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
