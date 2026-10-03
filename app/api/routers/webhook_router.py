import asyncio
import json
import os
from json import JSONDecodeError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response

from app.api.dependencies import get_workflow_service
from app.core.exceptions import NoExecutorAvailableError
from app.core.rate_limiter import _client_key, limiter
from app.core.utils.logger import get_logger
from app.core.utils.workflow_triggers import has_webhook_trigger
from app.services.workflow_service import (
    WorkflowInactiveError,
    WorkflowNotFoundError,
    WorkflowService,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
    # No global JWT authentication — access control is per credential on the WebhookTrigger node:
    # no credential_id → open access; with credential_id → token validated in start_analysis.
)

# Seconds to wait for the ResponseNode's response before returning 504.
# Floor of 1 s because the value goes straight to BRPOP, where 0 means "block
# forever" — exactly what this timeout exists to avoid.
_WEBHOOK_RESPONSE_TIMEOUT = max(1, int(os.getenv("WEBHOOK_RESPONSE_TIMEOUT", "60")))
_MAX_WEBHOOK_BODY = 10 * 1024 * 1024  # 10 MB

# ── ResponseNode response allowlist ──────────────────────────────────────────
#
# `/webhook/execute/{id_hash}` has no JWT (by design — the control is the
# WebhookTrigger node's credential), and the response body/headers come from the
# ResponseNode, that is, from the workflow's author. The raw headers allowed
# overwriting what SecurityHeadersMiddleware had just applied.
#
# The list below mirrors the ResponseNode's `contentType` dropdown
# (flow/nodes/outputs/response_node.py) PLUS the types only body_ref produces.
# It cannot be stricter than the node: downgrading a type the UI offers
# would silently break existing workflows, with a warning only in the server log.
_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/geo+json",
    "text/plain",
    "text/csv",
    "text/xml",
    "text/html",
}

# Types the browser RENDERS as a document. `text/html` is a legitimate option
# of the node, but the body may echo the request input — reflected XSS on the
# API ORIGIN, whose default CSP carries `script-src 'unsafe-inline'`.
#
# The response is not downgraded (that would break the feature): it is flagged in
# `request.state`, and SecurityHeadersMiddleware swaps the CSP for one with
# `sandbox` — opaque origin, no script and no forms. The HTML keeps
# rendering; the script inside it does not run.
#
# The flag has to go through `request.state` because the middleware OVERWRITES
# `Content-Security-Policy` on every response: a header set here would be
# discarded.
# Audit (SEG-08): it is not just text/html. The browser RENDERS XML documents
# and runs inline `<script>` in an XML with the XHTML namespace (and SVG is XML). Since
# these types are in the node's allowlist and the response goes out on the API ORIGIN
# (default CSP with `unsafe-inline`), they ALSO need the `sandbox` CSP.
_RENDERABLE_CONTENT_TYPES = {
    "text/html", "application/xml", "text/xml", "application/xhtml+xml",
    "image/svg+xml",
}

# Headers the workflow can NOT set: the security ones (which the middleware
# applies), those that pin identity in the browser, and those Starlette itself
# computes. Content-Type is left out because it comes from `content_type`, already validated.
_BLOCKED_HEADERS = frozenset({
    "content-security-policy", "content-security-policy-report-only",
    "x-frame-options", "x-content-type-options", "strict-transport-security",
    "referrer-policy", "permissions-policy", "x-xss-protection",
    "set-cookie", "access-control-allow-origin", "access-control-allow-credentials",
    "content-type", "content-length", "content-encoding", "transfer-encoding",
})


def _sanitize_node_response(resp: dict, request: Request) -> tuple[str, dict]:
    """Returns safe (content_type, headers) from what the ResponseNode asked for.

    A type outside the allowlist becomes `text/plain`: the content still reaches the
    caller — it just stops being interpreted as markup by the browser. Downgrading
    is better than refusing, because the workflow has already run and the data already exists.

    A renderable type that IS in the allowlist (text/html) passes intact, but sets
    `request.state.corpo_nao_confiavel` so the middleware hardens the CSP.
    """
    content_type = str(resp.get("content_type") or "application/json")
    base = content_type.split(";")[0].strip().lower()
    if base not in _ALLOWED_CONTENT_TYPES:
        logger.warning(
            "[webhook] content_type '%s' fora da allowlist — rebaixado para text/plain.",
            content_type,
        )
        content_type = "text/plain; charset=utf-8"
        base = "text/plain"

    if base in _RENDERABLE_CONTENT_TYPES:
        request.state.corpo_nao_confiavel = True

    # `headers` comes from the executor's JSON and the node exposes it as a free field of type
    # `object` — there is no guarantee it is a dict. Without this guard, a string or
    # list raised AttributeError and became a 500 in the generic handler.
    brutos = resp.get("headers")
    if not isinstance(brutos, dict):
        if brutos:
            logger.warning("[webhook] `headers` do ResponseNode nao e um objeto — ignorado.")
        brutos = {}

    headers = {
        str(k): str(v) for k, v in brutos.items()
        if str(k).lower() not in _BLOCKED_HEADERS
    }
    headers["Content-Type"] = content_type
    return content_type, headers


def _webhook_rate_key(request: Request) -> str:
    """Rate-limit key (IP, workflow_hash).

    Before it was only the IP — a botnet with 1000 IPs generated 20,000 req/min. Now an
    (IP, workflow) pair is counted in isolation: a botnet can still try a thousand
    distinct workflows, but hitting ONE specific workflow requires IP rotation
    for each window.

    The IP is the real client's (`_client_key`, the X-Forwarded-For read
    behind Traefik). slowapi's `get_remote_address` returned the proxy's IP
    for everyone: there was a single bucket per workflow, shared among
    all callers — with the counters in Redis, anyone who knew the URL
    would exhaust the workflow's 20/min for everyone else.
    """
    workflow_hash = request.path_params.get("id_hash") or "unknown"
    return f"{_client_key(request)}:{workflow_hash}"


@router.post("/execute/{id_hash}", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute", key_func=_webhook_rate_key)
async def webhook_trigger(
    id_hash: str,
    request: Request,
    background_tasks: BackgroundTasks,
    service: WorkflowService = Depends(get_workflow_service),
):
    """
    Triggers a workflow via Webhook.

    Behavior:
      - Workflow without a ResponseNode → returns 202 with {"task_id": "..."} immediately.
      - Workflow with a ResponseNode → waits for the executor to run it and returns the HTTP
        response defined by the node (customizable status_code, body, headers).
        Returns 504 if the executor does not respond within WEBHOOK_RESPONSE_TIMEOUT seconds.
    """
    # 1) Validates size and tries to read a JSON body; if it is not JSON, body = {}
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_WEBHOOK_BODY:
                raise HTTPException(status_code=413, detail=f"Payload excede {_MAX_WEBHOOK_BODY // (1024*1024)}MB.")
        except ValueError:
            pass
    try:
        body = await request.json()
    except JSONDecodeError:
        body = {}

    debug_mode = bool(body.pop("debug_mode", False))
    # no_wait=True: returns 202 immediately without waiting for the ResponseNode.
    # The canvas always sends no_wait=True to keep real-time visual feedback.
    # External callers (curl, integrations) omit the parameter and get a synchronous response.
    no_wait   = bool(body.pop("no_wait", False))
    logger.info("[webhook] acionando workflow %s debug_mode=%s no_wait=%s", id_hash, debug_mode, no_wait)

    # 1b) Validates that the workflow has a WebhookTrigger before dispatching.
    # Without this, workflows with other trigger types (ScheduleTrigger,
    # FileTrigger, etc) would be run via arbitrary HTTP — improper
    # behavior: the webhook endpoint should only trigger workflows explicitly
    # configured with that trigger.
    try:
        wf = await service.get_workflow_by_hash(id_hash)
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado",
        )
    if not wf.flag_ative:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow está desativado e não pode ser executado.",
        )
    if not has_webhook_trigger(wf.definition or {}):
        logger.warning(
            "[webhook] tentativa de disparo em workflow sem WebhookTrigger (id_hash=%s)",
            id_hash,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow não possui node WebhookTrigger — endpoint de webhook não é válido para este fluxo.",
        )

    # 2) Triggers the analysis
    try:
        async_result = await service.start_analysis(
            id_hash, inputs=body, request=request, debug_mode=debug_mode,
            # The workflow was just loaded and decrypted above for the
            # WebhookTrigger check; without passing it along, the dispatch redid
            # the SELECT and deserialized the entire `definition` a second time.
            workflow=wf,
            # No `triggered_by`: the caller is an external system, not a
            # user — inventing an owner here would open up private credentials.
            trigger_source="webhook",
        )
    except WorkflowNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow não encontrado",
        )
    except WorkflowInactiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workflow está desativado e não pode ser executado.",
        )
    except NoExecutorAvailableError as exc:
        # ANONYMOUS caller: generic body, without executor names, counts
        # or policy (spec §6). The detailed reason stays in the log and in the owner's
        # history. Stateless: no run was created on this path, so an
        # integrator hammering away does not amplify writes. `Retry-After` guides the
        # backoff; the idempotency key was NOT consumed (it is only written after
        # a successful dispatch), so the resend really tries again.
        logger.warning("[webhook] sem executor para %s (%s): %s", id_hash, exc.category, exc.detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execução temporariamente indisponível para este workflow.",
            headers={"Retry-After": "60"},
        )

    task_id = async_result.id

    # 3) If there is no ResponseNode or the caller asked for an async response, return 202 immediately
    if no_wait or not getattr(async_result, "has_response_node", False):
        return JSONResponse({"task_id": task_id}, status_code=202)

    # 4) Waits for a synchronous response via Redis BRPOP
    from app.core.redis import get_redis_pool
    rc = get_redis_pool()
    try:
        raw = await asyncio.wait_for(
            # The timeout goes in the command ITSELF. Without it BRPOP was `timeout=0`
            # — indefinite blocking on the Redis server — and the only one giving up was
            # the `wait_for` here: the connection stayed stuck until Redis noticed the
            # closed socket. Each in-flight synchronous webhook thus held one
            # connection of the SHARED pool (idempotency, WS rate limit,
            # JWT blacklist, run_results queue), which has no size ceiling:
            # a webhook spike marched toward Redis's `maxclients` and
            # took everything else down with it.
            rc.brpop(f"webhook_response:{task_id}", timeout=_WEBHOOK_RESPONSE_TIMEOUT),
            # Safety net for a Redis that does not even honor its own
            # timeout; normal expiration now comes back as `raw is None`.
            timeout=_WEBHOOK_RESPONSE_TIMEOUT + 5,
        )
    except asyncio.TimeoutError:
        raw = None

    if raw is None:
        logger.warning("[webhook] timeout aguardando ResponseNode (task_id=%s)", task_id)
        return JSONResponse(
            {
                "error":   "timeout",
                "task_id": task_id,
                "message": "O workflow não respondeu no tempo esperado.",
            },
            status_code=504,
        )

    payload = json.loads(raw[1])

    # 5) Workflow failed before reaching the ResponseNode
    if payload.get("job_status") != "ok":
        error_msg = payload.get("error") or "Workflow falhou."
        logger.error("[webhook] workflow falhou (task_id=%s): %s", task_id, error_msg)
        return JSONResponse(
            {"error": error_msg, "task_id": task_id},
            status_code=500,
        )

    # 6) Builds the HTTP response from the ResponseNode's data
    resp = payload.get("response") or {}
    http_status  = resp.get("status_code", 200)
    _content_type, extra_headers = _sanitize_node_response(resp, request)

    # 6a) Body stored in MinIO (large body, avoids HoL on the executor→server WS):
    # streams directly from MinIO to the caller and schedules immediate removal.
    body_ref = resp.get("body_ref")
    if body_ref and body_ref.get("s3_key"):
        s3_key = body_ref["s3_key"]
        logger.info(
            "[webhook] ResponseNode retornou body_ref=%s status=%d (task_id=%s)",
            s3_key, http_status, task_id,
        )
        # The s3_key comes from the executor (a machine under the user's control) and here it
        # would be used to READ and then DELETE an object from MinIO — which uses a
        # single bucket for the prefixes of all workspaces. Without the guard, an
        # executor returned `s3_key = "drive/<workspace_alheio>/<arquivo>"` and the
        # webhook served another tenant's content to the caller, deleting the object
        # afterwards. Same guard already applied on the other executor→server paths.
        from app.api.routers.executor_drive_router import _validate_agent_s3_key
        # Audit (SEG-71): besides the per-workspace scope, requires the
        # `webhook-responses/` prefix — the ResponseNode body is always written there
        # (response_node.py). Without it, a `body_ref` pointing to
        # `drive/{ws}/…` or `artifacts/{ws}/…` of the SAME workspace would make the
        # webhook serve and then DELETE that object.
        prefix_ok = isinstance(s3_key, str) and s3_key.startswith(
            f"webhook-responses/{wf.workspace_id}/"
        )
        try:
            _validate_agent_s3_key(s3_key, [wf.workspace_id])
            if not prefix_ok:
                raise HTTPException(status_code=403, detail="body_ref fora de webhook-responses/")
        except HTTPException as exc:
            logger.error(
                "[webhook] s3_key rejeitada (%s) no task_id=%s: %s",
                exc.detail, task_id, s3_key,
            )
            return JSONResponse(
                {"error": "Resposta do workflow inválida.", "task_id": task_id},
                status_code=502,
            )

        from app.core import storage as s3
        # Downloads into memory (synchronous boto3 operation in a threadpool). For very
        # large bodies, chunked streaming of get_object would be possible,
        # but it requires extra plumbing of boto3.StreamingBody in async.
        try:
            content_bytes = await asyncio.to_thread(s3.download, s3_key)
        except Exception as exc:
            logger.error("[webhook] falha ao baixar body do MinIO '%s': %s", s3_key, exc)
            return JSONResponse(
                {"error": "Falha ao recuperar resposta do storage.", "task_id": task_id},
                status_code=502,
            )
        # Deletes from MinIO in the background; the Artifact registered by executor_ws_router
        # is also removed by the global cleanup when expires_at passes (safety net).
        background_tasks.add_task(_delete_webhook_response_artifact, s3_key)
        return Response(
            content=content_bytes,
            status_code=http_status,
            headers=extra_headers,
        )

    body_data = resp.get("body")
    if isinstance(body_data, (dict, list)):
        content = json.dumps(body_data, ensure_ascii=False)
    else:
        content = str(body_data) if body_data is not None else ""

    logger.info("[webhook] ResponseNode retornou status=%d (task_id=%s)", http_status, task_id)
    return Response(
        content=content,
        status_code=http_status,
        headers=extra_headers,
    )


async def _delete_webhook_response_artifact(s3_key: str) -> None:
    """Removes the object from MinIO and the matching Artifact row after the caller receives the body.

    Run in BackgroundTasks — if it fails, the global cleanup removes it via expires_at.
    """
    from sqlalchemy import delete as sa_delete

    from app.core import storage as s3
    from app.core.db import get_session_async
    from app.models.artifact import Artifact

    try:
        await s3.delete_async(s3_key)
    except Exception as exc:
        logger.warning("[webhook] falha ao remover objeto MinIO '%s': %s", s3_key, exc)

    try:
        async with get_session_async() as db:
            await db.execute(sa_delete(Artifact).where(Artifact.s3_key == s3_key))
            await db.commit()
    except Exception as exc:
        logger.warning("[webhook] falha ao remover linha Artifact s3_key='%s': %s", s3_key, exc)
