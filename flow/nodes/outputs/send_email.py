# flow/nodes/outputs/send_email.py
"""
Node de envio de e-mail via Resend API (através do endpoint interno do servidor).

O executor não possui RESEND_API_KEY — o envio é delegado ao servidor via
POST /internal/send-email, autenticado por mTLS (cert client validado
pelo Traefik e propagado via `X-Forwarded-Tls-Client-Cert-Info`).

Modos de anexo (attachMode):
  - "link"  → espera URL de artefato no input (vinda de node anterior como DataOutput/SaveToS3)
  - "auto"  → se houver GeoDataFrame no input, salva como artefato no MinIO e gera link de download
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.logger import get_logger
from flow.utils.geo_helpers import gdf_para_geojson

logger = get_logger(__name__)


def _get_presigned_url_for_s3_key(s3_key: str) -> str | None:
    """Gera presigned download URL a partir de um s3_key via POST /drive/executor-presign-download."""
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    base_url, headers, verify = get_agent_http_config()

    def _fetch() -> str | None:
        resp = httpx.post(
            f"{base_url}/drive/executor-presign-download",
            json={"s3_key": s3_key},
            headers=headers,
            verify=verify,
            follow_redirects=True,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("download_url")

    try:
        # Geracao de presign é idempotente → retry seguro.
        return retry_sync(_fetch, label=f"presign s3_key {s3_key}")
    except Exception as exc:
        logger.warning("Não foi possível gerar presigned URL para s3_key=%s: %s", s3_key, exc)
        return None


def _call_send_email_endpoint(
    to: list[str],
    subject: str,
    html: str,
    workspace_id: str | None = None,
    task_id: str | None = None,
) -> dict:
    """Chama POST /internal/send-email no servidor (bloqueante).

    SEM retry automatico: envio de e-mail NAO e idempotente — re-tentar um
    request cujo 5xx/timeout veio APOS o servidor ja ter disparado o e-mail
    duplicaria a mensagem. Para tornar seguro, o endpoint /internal/send-email
    precisaria de uma idempotency key (ex: hash de to+subject+run_id). Ate la,
    falha aqui propaga e o operador reenvia conscientemente.
    """
    import httpx
    from flow.utils.executor_http import get_agent_http_config

    base_url, headers, verify = get_agent_http_config()

    # O remetente e definido pelo servidor (RESEND_FROM_EMAIL) — o executor nao
    # escolhe o "from" para nao poder forjar enderecos do dominio da plataforma.
    # workspace_id + task_id atam o envio a uma execucao REAL de um workspace que
    # o executor atende (auditoria SEG-07): o servidor recusa envio sem run vivo.
    payload: dict[str, Any] = {
        "to": to,
        "subject": subject,
        "html": html,
        "workspace_id": workspace_id,
        "task_id": task_id,
    }

    resp = httpx.post(
        f"{base_url}/internal/send-email",
        json=payload,
        headers=headers,
        verify=verify,
        follow_redirects=True,
        timeout=30,
    )
    if resp.status_code >= 400:
        # raise_for_status() retornava apenas "Server error 'X' for url..."
        # Extrai o `detail` do JSON (FastAPI HTTPException retorna nesse formato)
        # para o operador ver o motivo real (ex: "Missing html or text field")
        # em vez de so o status code.
        detail = ""
        try:
            payload_err = resp.json()
            if isinstance(payload_err, dict):
                detail = str(payload_err.get("detail", ""))
        except Exception:
            detail = resp.text[:300]
        raise RuntimeError(
            f"Servidor recusou envio (status={resp.status_code}): {detail or '<sem detalhes>'}"
        )
    try:
        return resp.json()
    except Exception as parse_err:
        raise RuntimeError(
            f"Resposta inválida do servidor (status={resp.status_code}, "
            f"body={resp.text[:300]!r}): {parse_err}"
        ) from parse_err


@register_node
class SendEmailNode(BaseNode):
    """
    Envia e-mail via Resend delegando ao servidor (POST /internal/send-email).
    Suporta dois modos de anexo:
      - "link": recebe URL de artefato do input de um node anterior
      - "auto": salva GeoDataFrame como artefato no MinIO e inclui link no email
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "SendEmail",
            "alias": "Enviar E-mail",
            "description": (
                "Envia e-mail via Resend API (delegado ao servidor). "
                "Suporta links de artefatos para download (modo link ou auto). "
                "Aceita inputs dinâmicos do node anterior: email_body, email_subject, email_to."
            ),
            "type": "output",
            "dynamic_output": False,
            "outputs": [
                {"name": "sent", "type": "boolean", "description": "Indica se o e-mail foi enviado com sucesso"},
                {"name": "recipients", "type": "number", "description": "Quantidade de destinatários"},
                {"name": "artifact_s3_key", "type": "string", "description": "Chave S3 do artefato gerado (modo auto, vazio se não aplicável)"},
            ],
            "properties": [
                {
                    "name": "toAddresses", "required": True,
                    "label": "Destinatários",
                    "type": "string",
                    "default": "",
                    "description": "Destinatários separados por vírgula.",
                },
                {
                    "name": "subject", "required": True,
                    "label": "Assunto",
                    "type": "string",
                    "default": "",
                    "description": "Assunto do e-mail.",
                },
                {
                    "name": "body",
                    "label": "Corpo",
                    "type": "string",
                    "default": "",
                    "description": "Corpo do e-mail em HTML.",
                },
                {
                    "name": "attachMode",
                    "label": "Modo de anexo",
                    "type": "select",
                    "default": "none",
                    "description": "Modo de anexo ao e-mail.",
                    "options": [
                        {"value": "none", "label": "Sem anexo"},
                        {"value": "link", "label": "Link de artefato (node anterior)"},
                        {"value": "auto", "label": "Gerar artefato e incluir link"},
                    ],
                },
                {
                    "name": "artifactLabel",
                    "label": "Nome do artefato",
                    "type": "string",
                    "default": "resultado",
                    "description": (
                        "Nome do artefato gerado (ex: 'buffer_analysis'). "
                        "Usado apenas no modo 'auto'."
                    ),
                },
                {
                    "name": "artifactFormat",
                    "label": "Formato do artefato",
                    "type": "select",
                    "default": "geojson",
                    "description": "Formato do artefato no modo 'auto'.",
                    "options": [
                        {"value": "geojson", "label": "GeoJSON"},
                        {"value": "geoparquet", "label": "GeoParquet"},
                    ],
                },
            ],
        }

    def _resolve_artifact_url_from_inputs(self, inputs: Dict[str, Any]) -> str | None:
        """Procura URL ou s3_key de artefato nos outputs do node anterior."""
        _url_keys = ("artifactUrl", "artifact_url", "download_url")
        _s3_key = "artifact_s3_key"

        def _search_dict(d: dict) -> str | None:
            for key in _url_keys:
                if key in d and d[key]:
                    return d[key]
            if _s3_key in d and d[_s3_key]:
                return d[_s3_key]
            # Busca dentro de "output" wrappado (padrão novo)
            if "output" in d and isinstance(d["output"], dict):
                return _search_dict(d["output"])
            return None

        for value in inputs.values():
            if isinstance(value, dict):
                found = _search_dict(value)
                if found:
                    return found
            elif isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                return value
        return None

    async def _auto_save_artifact(self, inputs: Dict[str, Any]) -> tuple[str, str, str | None]:
        """
        Salva GeoDataFrame do input como artefato no MinIO.
        Retorna (s3_key, filename, drive_file_id).
        """
        from flow.utils.artifact_helpers import exigir_envio_permitido, upload_artifact_to_minio
        from flow.utils.executor_http import slugify

        # O anexo automático PRODUZ um arquivo novo e manda o link dele. Não há
        # versão local disso que ainda signifique alguma coisa: um link que
        # ninguém consegue abrir não é resultado degradado, é resultado nenhum.
        #
        # Falha em vez de enviar. Enviar seria um workflow contrariando a
        # política da máquina — exatamente o que ela existe para impedir. E falha
        # em vez de pular: um e-mail que sai sem o anexo, com o run verde,
        # ninguém descobre.
        #
        # Só este modo é barrado. `none` e `link` não expõem nada de novo.
        exigir_envio_permitido(
            f"SendEmail (anexo automático de '{self.parameters.get('artifactLabel', 'resultado')}')",
            "o anexo automático precisa enviar o arquivo ao servidor para gerar "
            "um link de download",
        )

        gdf = self.get_first_gdf(inputs)

        label = self.parameters.get("artifactLabel", "resultado").strip() or "resultado"
        fmt = self.parameters.get("artifactFormat", "geojson").strip().lower()
        safe_label = slugify(label)

        workspace_id = getattr(self, "_workspace_id", None)
        if not workspace_id:
            raise RuntimeError("workspace_id não injetado pelo executor.")
        if not self._task_id:
            raise RuntimeError("task_id não injetado pelo executor.")

        if fmt == "geoparquet":
            import io
            filename = f"{safe_label}.parquet"
            buf = io.BytesIO()
            await asyncio.to_thread(gdf.to_parquet, buf, index=False)
            content = buf.getvalue()
            content_type = "application/x-parquet"
        else:
            filename = f"{safe_label}.geojson"
            json_str = await asyncio.to_thread(gdf_para_geojson, gdf)
            content = json_str.encode("utf-8")
            content_type = "application/geo+json"
            fmt = "geojson"

        s3_key, artifact_meta = await asyncio.to_thread(
            upload_artifact_to_minio,
            content=content,
            filename=filename,
            content_type=content_type,
            workspace_id=workspace_id,
            task_id=self._task_id,
            label=label,
            fmt=fmt,
            features=len(gdf),
        )

        self.log(f"Artefato salvo no MinIO: {s3_key}")
        return s3_key, filename, artifact_meta

    def _build_artifact_html(self, artifact_ref: str, filename: str | None = None) -> str:
        """Gera bloco HTML com link de download do artefato."""
        display_name = filename or artifact_ref.split("/")[-1] if "/" in artifact_ref else artifact_ref

        if artifact_ref.startswith("http://") or artifact_ref.startswith("https://"):
            download_link = artifact_ref
        else:
            # s3_key → URL pública via MinIO externo. Sem MINIO_EXTERNAL_ENDPOINT
            # não há endereço: a chave crua num `href` seria um link RELATIVO,
            # morto, e o e-mail sai sem o bloco do anexo (como no modo "link").
            minio_ext = os.getenv("MINIO_EXTERNAL_ENDPOINT", "").rstrip("/")
            if not minio_ext:
                self.log(
                    "AVISO: o anexo não tem link de download (sem URL pré-assinada nem "
                    f"MINIO_EXTERNAL_ENDPOINT) e o e-mail vai sair sem ele: '{artifact_ref}'."
                )
                return ""
            minio_bucket = os.getenv("MINIO_BUCKET", "atlans-drive")
            download_link = f"{minio_ext}/{minio_bucket}/{artifact_ref}"
            display_name = f"📎 {display_name}"

        return (
            '<br><hr style="border:none;border-top:1px solid #ddd;margin:16px 0">'
            "<p><strong>Anexo disponível para download:</strong></p>"
            f'<p><a href="{download_link}" '
            f'style="color:#FF6A00;text-decoration:underline">{display_name}</a></p>'
        )

    _FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "body":    ("email_body", "emailBody", "body"),
        "subject": ("email_subject", "emailSubject", "subject"),
        "to":      ("email_to", "emailTo", "to"),
    }

    def _resolve_dynamic_field(self, inputs: Dict[str, Any], field_name: str) -> str | None:
        """Procura um campo pelo nome exato nos inputs e dentro de dicts aninhados."""
        if field_name in inputs and isinstance(inputs[field_name], str):
            return inputs[field_name]
        for value in inputs.values():
            if isinstance(value, dict):
                # Busca dentro de "output" wrappado (padrão novo)
                wrapped = value.get("output")
                inner = wrapped if isinstance(wrapped, dict) else value
                if field_name not in inner:
                    continue
                v = inner[field_name]
                if isinstance(v, str):
                    return v
        return None

    def _resolve_field(self, inputs: Dict[str, Any], field: str) -> str | None:
        """Resolve um campo tentando cada alias em ordem até encontrar valor não-vazio."""
        for alias in self._FIELD_ALIASES[field]:
            val = self._resolve_dynamic_field(inputs, alias)
            if val:
                return val
        return None

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        # Parâmetros do node (propriedades estáticas)
        to_raw = self.parameters.get("toAddresses", "").strip()
        subject = self.parameters.get("subject", "").strip()
        body = self.parameters.get("body", "")
        attach_mode = self.parameters.get("attachMode", "none").strip().lower()

        # Inputs dinâmicos (output de node anterior) sobrescrevem propriedades estáticas
        if val := self._resolve_field(inputs, "body"):
            body = val
        if val := self._resolve_field(inputs, "subject"):
            subject = val
        if val := self._resolve_field(inputs, "to"):
            to_raw = val

        if not to_raw:
            raise ValueError("Parâmetro 'toAddresses' é obrigatório (propriedade ou input dinâmico 'email_to').")
        if not subject:
            raise ValueError("Parâmetro 'subject' é obrigatório (propriedade ou input dinâmico 'email_subject').")
        # Body vazio era enviado como html="" e o Resend rejeitava com
        # "Missing html or text field" — o servidor convertia em 502 e o
        # operador via apenas "Bad Gateway" sem pista da causa.
        if not body.strip():
            raise ValueError(
                "Parâmetro 'body' é obrigatório (propriedade ou input dinâmico "
                "'email_body'). Em attachMode='link', preencha 'body' mesmo que "
                "o anexo apareça depois — o texto principal não é gerado "
                "automaticamente."
            )

        recipients = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        if not recipients:
            raise ValueError("Nenhum destinatário válido encontrado em 'toAddresses'.")

        artifact_s3_key = ""
        _artifact_meta = None

        # A autenticacao das chamadas ao servidor acontece via cert mTLS do
        # executor, montado por get_agent_http_config a partir de
        # EXECUTOR_SERVER_URL/EXECUTOR_CERT_DIR.

        # ── Modo link: busca URL/s3_key do input ────────────────────────────
        if attach_mode == "link":
            artifact_ref = self._resolve_artifact_url_from_inputs(inputs)
            if artifact_ref:
                # Se é s3_key (não URL), gera presigned URL
                if not artifact_ref.startswith(("http://", "https://")):
                    presigned = await asyncio.to_thread(
                        _get_presigned_url_for_s3_key, artifact_ref
                    )
                    if presigned:
                        artifact_ref = presigned

                if artifact_ref.startswith(("http://", "https://")):
                    body += self._build_artifact_html(artifact_ref)
                else:
                    # Sem presign, `artifact_ref` continua sendo a referência
                    # crua do nó anterior, e `_build_artifact_html` a colocaria
                    # num `href` — um link RELATIVO num e-mail HTML, que não
                    # leva a lugar nenhum. O e-mail sairia anunciando "anexo
                    # disponível para download" com um link morto.
                    #
                    # O caso comum é justamente um artefato mantido no executor:
                    # não existe objeto no storage, então não há o que assinar.
                    self.log(
                        "AVISO: o artefato referenciado não tem link de download "
                        f"('{artifact_ref}') e o e-mail vai sair SEM o anexo. "
                        "Isso acontece quando o conteúdo foi mantido no executor "
                        "— nesse caso não há download pela plataforma."
                    )
            else:
                logger.warning(
                    "attachMode='link' mas nenhum artefato encontrado nos inputs. "
                    "E-mail será enviado sem link de download."
                )

        # ── Modo auto: salva GDF como artefato e gera presigned link ────────
        elif attach_mode == "auto":
            s3_key, filename, artifact_meta = await self._auto_save_artifact(inputs)
            artifact_s3_key = s3_key
            _artifact_meta = artifact_meta
            # Gera presigned URL via s3_key (path-based validation, sem depender da tabela Artifact)
            download_url = await asyncio.to_thread(
                _get_presigned_url_for_s3_key, s3_key
            )
            body += self._build_artifact_html(download_url or s3_key, filename)

        logger.info(
            "Enviando e-mail via servidor para %d destinatário(s): %s",
            len(recipients), recipients,
        )

        try:
            await asyncio.to_thread(
                _call_send_email_endpoint,
                recipients, subject, body,
                getattr(self, "_workspace_id", None), getattr(self, "_task_id", None),
            )
        except Exception as e:
            logger.error("Erro ao enviar e-mail via servidor: %s", e)
            raise RuntimeError(f"Erro ao enviar e-mail via servidor: {e}") from e

        logger.info("E-mail enviado com sucesso para %d destinatário(s).", len(recipients))
        result: dict = {
            "output": {
                "sent": True,
                "recipients": len(recipients),
                "artifact_s3_key": artifact_s3_key,
            },
        }
        if _artifact_meta:
            result["__artifact__"] = _artifact_meta
        return result
