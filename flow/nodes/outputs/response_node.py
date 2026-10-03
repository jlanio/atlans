# flow/nodes/outputs/response_node.py
"""
ResponseNode — returns data as the HTTP response when the workflow is triggered by a webhook.

When the executor finds this node in final_outputs, it inserts the __response__ key
into the job stats. The server uses that key to respond synchronously to the original
HTTP request that triggered the workflow.

Properties:
  statusCode  — HTTP status code returned (default: 200)
  contentType — Content-Type of the response (default: application/json)
  headers     — additional headers (key→value object)
  customBody  — literal/templated response body. Empty = uses bodyField/inputs.
                Accepts Jinja expressions interpolated by the executor before reaching
                this point (e.g. "Olá {{ inputs.nome }}" or "$NodePai.field").
  bodyField   — fallback when customBody is empty: name of the input field
                to use as the body; empty = first input.

Body priority order: customBody > bodyField > first input.

Large body (> WEBHOOK_RESPONSE_INLINE_LIMIT, default 1MB): uploaded to MinIO and
returns __response__.body_ref instead of an inline body, avoiding HoL blocking on
the executor→server WebSocket.
"""
import asyncio
import json
import os
from uuid import uuid4

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_INLINE_LIMIT = int(os.getenv("WEBHOOK_RESPONSE_INLINE_LIMIT", str(1 * 1024 * 1024)))


@register_node
class ResponseNode(BaseNode):

    @classmethod
    def description(cls) -> dict:
        return {
            "name":        "Response",
            "type":        "output",
            "description": "Retorna dados como resposta HTTP quando acionado por webhook.",
            "properties": [
                {
                    "name":        "statusCode",
                    "label":       "Status code",
                    "type":        "select",
                    "default":     "200",
                    "description": "Código HTTP de retorno.",
                    "options": [
                        {"value": "200", "label": "200 — OK"},
                        {"value": "201", "label": "201 — Created"},
                        {"value": "204", "label": "204 — No Content"},
                        {"value": "301", "label": "301 — Moved Permanently"},
                        {"value": "302", "label": "302 — Found (redirect)"},
                        {"value": "400", "label": "400 — Bad Request"},
                        {"value": "401", "label": "401 — Unauthorized"},
                        {"value": "403", "label": "403 — Forbidden"},
                        {"value": "404", "label": "404 — Not Found"},
                        {"value": "422", "label": "422 — Unprocessable Entity"},
                        {"value": "500", "label": "500 — Internal Server Error"},
                    ],
                },
                {
                    "name":        "contentType",
                    "label":       "Content-Type",
                    "type":        "select",
                    "default":     "application/json",
                    "description": "Tipo do conteúdo retornado no body.",
                    "options": [
                        {"value": "application/json", "label": "JSON (application/json)"},
                        {"value": "text/plain",       "label": "Texto (text/plain)"},
                        {"value": "text/html",        "label": "HTML (text/html)"},
                        {"value": "application/xml",  "label": "XML (application/xml)"},
                        {"value": "text/csv",         "label": "CSV (text/csv)"},
                    ],
                },
                {
                    "name":        "bodyMode",
                    "label":       "Origem do body",
                    "type":        "select",
                    "default":     "field",
                    "description": "De onde vem o corpo da resposta.",
                    "options": [
                        {"value": "empty",   "label": "Vazio (sem body)"},
                        {"value": "literal", "label": "Texto literal / template Jinja"},
                        {"value": "field",   "label": "Usar campo do input"},
                    ],
                },
                {
                    "name":        "customBody",
                    "label":       "Corpo customizado",
                    "type":        "code",
                    "default":     "",
                    "description": (
                        "Texto literal ou template Jinja a retornar como body. "
                        "Acesse outputs anteriores via alias do nó: "
                        "'Olá {{ WebhookTrigger.output.nome }}' ou "
                        "'$WebhookTrigger.output.nome'. Funções disponíveis: now(), uuid(), env."
                    ),
                    "visibleWhen": {"field": "bodyMode", "in": ["literal"]},
                },
                {
                    "name":        "bodyField",
                    "label":       "Campo de entrada",
                    "type":        "string",
                    "default":     "",
                    "description": (
                        "Nome do campo de entrada a usar como body. "
                        "Vazio = usa o primeiro input recebido."
                    ),
                    "visibleWhen": {"field": "bodyMode", "in": ["field"]},
                },
                {
                    "name":    "headers",
                    "label":   "Headers adicionais",
                    "type":    "object",
                    "default": {},
                },
            ],
            "outputs": [
                {"name": "__response__", "type": "object", "description": ""},
            ],
        }

    async def execute(self, inputs: dict) -> dict:
        self.validate()
        mode         = self.get_param("bodyMode", "field")
        custom_body  = self.get_param("customBody", "")
        field        = self.get_param("bodyField", "").strip()
        status_code  = self.get_param_int("statusCode", 200)
        content_type = self.get_param("contentType", "application/json")
        headers      = self.get_param("headers", {})
        task_id      = self._task_id
        workspace_id = self._workspace_id

        # Body resolution according to bodyMode:
        #   empty   → no body
        #   literal → customBody (text/Jinja already interpolated by the executor)
        #   field   → bodyField in the inputs (falling back to the first input)
        # Backward compat: old workflows without bodyMode fall into "field" and,
        # if customBody is filled in, it still takes precedence (same
        # behavior as before bodyMode existed).
        if mode == "empty":
            body = ""
        elif mode == "literal":
            if isinstance(custom_body, str):
                body = custom_body
            elif custom_body in (None, {}, []):
                body = ""
            else:
                # Jinja interpolou para dict/list — aceita.
                body = custom_body
        else:  # "field" (ou ausente em workflows legados)
            if isinstance(custom_body, str) and custom_body.strip() != "":
                body = custom_body
            elif not isinstance(custom_body, str) and custom_body not in (None, {}, []):
                body = custom_body
            elif field and field in inputs:
                body = inputs[field]
            elif inputs:
                body = next(iter(inputs.values()))
            else:
                body = {}

        # GeoDataFrame conversion, json.dumps and the MinIO upload are all
        # blocking (CPU + synchronous I/O). If they run directly on the event loop,
        # the 'started' callback scheduled via call_soon_threadsafe is stuck
        # until the end and the UI never paints the blue ring during the execution.
        # Run everything in a thread so the await yields immediately.
        return await asyncio.to_thread(
            _build_response, body, status_code, content_type, headers, task_id, workspace_id,
        )


def _build_response(
    body,
    status_code: int,
    content_type: str,
    headers: dict,
    task_id: str | None,
    workspace_id: str | None = None,
) -> dict:
    """Converts, serializes and (if large) uploads the body to MinIO.

    Runs synchronously because it is called inside asyncio.to_thread — keeps the
    event loop free to process other callbacks (such as the 'started' event
    scheduled by the executor before execute()).
    """
    # GeoDataFrame is not JSON-serializable — convert it to a dict.
    # Check GeoDataFrame before DataFrame, since GeoDataFrame is a subclass.
    import geopandas as gpd
    import pandas as pd

    if isinstance(body, gpd.GeoDataFrame):
        body = body.__geo_interface__

    # A plain DataFrame becomes a list of records — without this conversion, json.dumps
    # falls into the default=str fallback and returns the repr "<DataFrame NxM>".
    if isinstance(body, pd.DataFrame):
        body = body.to_dict(orient="records")

    # Serializes the body to measure its size. String/bytes go straight through
    # (keeps literal text without extra JSON quotes — useful for customBody +
    # Content-Type text/plain or text/html). Dict/list is serialized via json.dumps.
    # Above the limit, it is uploaded to MinIO and the inline body is replaced by
    # an S3 reference.
    if isinstance(body, bytes):
        body_bytes = body
    elif isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")

    if len(body_bytes) > _INLINE_LIMIT:
        body_ref = _upload_to_minio(body_bytes, content_type, task_id, workspace_id)
        return {
            "__response__": {
                "status_code":  status_code,
                "content_type": content_type,
                "headers":      headers,
                "body_ref":     body_ref,
            }
        }

    return {
        "__response__": {
            "status_code":  status_code,
            "content_type": content_type,
            "headers":      headers,
            "body":         body,
        }
    }


def _upload_to_minio(
    content: bytes, content_type: str, task_id: str | None, workspace_id: str | None = None,
) -> dict:
    """Uploads the response body to MinIO and returns the S3 reference.

    Same pattern as flow/executor/pin.py:upload_pin_to_minio — pre-signed URL
    obtained from /drive/executor-presign-upload.

    The key follows the `{prefix}/{workspace_id}/...` scheme the server requires in
    `_validate_agent_s3_key`: without the `workspace_id` as the second segment, the
    presign-upload (executor scope), the readback (workflow scope) and the
    artifact registration (run scope) rejected the key with 403 — the body_ref
    above WEBHOOK_RESPONSE_INLINE_LIMIT never reached the client.
    """
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    if not workspace_id:
        raise RuntimeError(
            "workspace_id ausente — não é possível escopar o body_ref da resposta no MinIO."
        )
    run_id = task_id or "unknown"
    s3_key = f"webhook-responses/{workspace_id}/{run_id}/{uuid4().hex}.bin"
    size = len(content)

    base_url, headers, verify = get_agent_http_config()

    def _do_upload() -> None:
        # Re-obtem a pre-signed URL a cada tentativa (TTL curto) e re-tenta o PUT.
        resp = httpx.post(
            f"{base_url}/drive/executor-presign-upload",
            json={"s3_key": s3_key, "content_type": content_type},
            headers=headers, verify=verify, follow_redirects=True, timeout=15,
        )
        resp.raise_for_status()
        upload_url = resp.json()["upload_url"]
        put_resp = httpx.put(
            upload_url,
            content=content,
            headers={"Content-Type": content_type},
            timeout=120, verify=verify,
        )
        put_resp.raise_for_status()

    # Best-effort: retries any failure (network/storage/5xx) — a webhook body
    # must not be lost to a transient blip.
    retry_sync(_do_upload, retryable_exc=(Exception,), label=f"webhook-response upload {s3_key}")

    logger.info("Webhook response enviado ao MinIO: %s (%d bytes)", s3_key, size)
    return {
        "s3_key":       s3_key,
        "size":         size,
        "content_type": content_type,
    }
