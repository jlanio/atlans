# flow/nodes/outputs/response_node.py
"""
ResponseNode — retorna dados como resposta HTTP quando o workflow é acionado por webhook.

Quando o executor encontra este nó em final_outputs, insere a chave __response__
nos stats do job. O servidor usa essa chave para responder sincronamente à requisição
HTTP original que disparou o workflow.

Propriedades:
  statusCode  — código HTTP de retorno (padrão: 200)
  contentType — Content-Type da resposta (padrão: application/json)
  headers     — headers adicionais (objeto chave→valor)
  customBody  — corpo literal/templated da resposta. Vazio = usa bodyField/inputs.
                Aceita expressões Jinja interpoladas pelo executor antes de chegar
                aqui (ex: "Olá {{ inputs.nome }}" ou "$NodePai.field").
  bodyField   — fallback quando customBody está vazio: nome do campo do input
                a usar como body; vazio = primeiro input.

Ordem de prioridade do body: customBody > bodyField > primeiro input.

Body grande (> WEBHOOK_RESPONSE_INLINE_LIMIT, default 1MB): sobe para o MinIO e
retorna __response__.body_ref em vez de body inline, evitando HoL blocking no
WebSocket executor→servidor.
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

        # Resolução do body conforme bodyMode:
        #   empty   → sem body
        #   literal → customBody (texto/Jinja já interpolado pelo executor)
        #   field   → bodyField nos inputs (com fallback para o primeiro input)
        # Compat retroativa: workflows antigos sem bodyMode caem em "field" e
        # se houver customBody preenchido, ele ainda prevalece (mesmo
        # comportamento que existia antes do bodyMode).
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

        # Conversão GeoDataFrame, json.dumps e upload ao MinIO são todos
        # bloqueantes (CPU + I/O síncrono). Se rodarem direto no event loop,
        # o callback 'started' agendado via call_soon_threadsafe fica preso
        # até o fim e a UI nunca pinta o ring azul durante a execução. Roda
        # tudo numa thread para que o await yielde imediatamente.
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
    """Converte, serializa e (se grande) faz upload do body ao MinIO.

    Roda síncrona porque é chamada dentro de asyncio.to_thread — mantém o
    event loop livre para processar outros callbacks (como o evento 'started'
    agendado pelo executor antes de execute()).
    """
    # GeoDataFrame não é serializável em JSON — converte para dict.
    # Checa GeoDataFrame antes de DataFrame, ja que GeoDataFrame eh subclasse.
    import geopandas as gpd
    import pandas as pd

    if isinstance(body, gpd.GeoDataFrame):
        body = body.__geo_interface__

    # DataFrame puro vira lista de records — sem essa conversão, json.dumps
    # cai no fallback default=str e devolve a repr "<DataFrame NxM>".
    if isinstance(body, pd.DataFrame):
        body = body.to_dict(orient="records")

    # Serializa o body para medir tamanho. String/bytes vão direto (preserva
    # texto literal sem aspas extras de JSON — útil para customBody +
    # Content-Type text/plain ou text/html). Dict/list serializa via json.dumps.
    # Acima do limite, sobe para o MinIO e substitui o body inline por uma
    # referência S3.
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
    """Sobe o body da resposta para o MinIO e retorna a referência S3.

    Mesmo padrão de flow/executor/pin.py:upload_pin_to_minio — pre-signed URL
    obtida em /drive/executor-presign-upload.

    A key segue o esquema `{prefix}/{workspace_id}/...` que o servidor exige em
    `_validate_agent_s3_key`: sem o `workspace_id` como segundo segmento, o
    presign-upload (escopo do executor), o readback (escopo do workflow) e o
    registro do artefato (escopo do run) rejeitavam a key com 403 — o body_ref
    acima de WEBHOOK_RESPONSE_INLINE_LIMIT nunca chegava ao cliente.
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

    # Best-effort: retenta qualquer falha (rede/storage/5xx) — body de webhook
    # nao pode ser perdido por um blip transitorio.
    retry_sync(_do_upload, retryable_exc=(Exception,), label=f"webhook-response upload {s3_key}")

    logger.info("Webhook response enviado ao MinIO: %s (%d bytes)", s3_key, size)
    return {
        "s3_key":       s3_key,
        "size":         size,
        "content_type": content_type,
    }
