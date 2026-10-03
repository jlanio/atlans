import asyncio
import json
import os

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.artifact_helpers import artifacts_root, exigir_envio_permitido
from flow.utils.executor_http import get_agent_http_config, slugify
from flow.utils.geo_helpers import gdf_para_geojson
from flow.utils.parameter_validation import colunas_pedidas


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _montar_envelope_gzip(cabecalho: dict, geojson_str: str) -> tuple[bytes, int]:
    """Builds the publish JSON envelope and compresses it — meant to run in a thread.

    Embeds the `geojson_str` (already serialized by `to_json`) RAW, without
    reparsing it: removes the redundant json.loads->json.dumps of the whole
    geojson. `cabecalho` always has keys here, so `json.dumps` ends in '}' and
    inserting `,"geojson":<str>` before the closing brace produces valid JSON.
    Returns (compressed, payload_size) for logging the compression ratio.
    """
    import gzip
    cabeca = json.dumps(cabecalho, ensure_ascii=False)
    corpo = (cabeca[:-1] + ',"geojson":' + geojson_str + "}").encode("utf-8")
    return gzip.compress(corpo), len(corpo)


@register_node
class PublishMap(BaseNode):
    @classmethod
    def description(cls) -> dict:
        return {
            "name":        "PublishMap",
            "alias":       "Publicar no Mapa",
            "description": (
                "Publica um GeoDataFrame como camada no portal publico do workflow. "
                "Envia os dados diretamente para a API via HTTP (comprimido com gzip). "
                "Configure titulo, cor e campos visiveis."
            ),
            "type": "output",
            "dynamic_output": False,
            "outputs": [
                {"name": "published_features", "type": "number", "description": "Numero de features publicadas"},
                {"name": "published_layer_id", "type": "string", "description": "ID da camada no portal"},
            ],
            "properties": [
                {
                    "name":        "title",
                    "label":       "Título",
                    "type":        "string",
                    "default":     "Camada",
                    "description": "Nome da camada exibido na legenda do portal.",
                },
                {
                    "name":        "color",
                    "label":       "Cor",
                    "type":        "string",
                    "default":     "#3b82f6",
                    "description": "Cor hex para fill e stroke da camada (ex: #e74c3c).",
                },
                {
                    "name":        "opacity",
                    "label":       "Opacidade",
                    "type":        "number",
                    "default":     0.5,
                    "description": "Opacidade do fill entre 0 e 1.",
                },
                {
                    "name":        "description",
                    "label":       "Descrição",
                    "type":        "string",
                    "default":     "",
                    "description": "Texto descritivo exibido abaixo do titulo no portal.",
                },
                {
                    "name":        "visible_fields",
                    "label":       "Campos visíveis",
                    "type":        "chips",
                    # Single-input node: '*' and the port would amount to the same thing.
                    "suggest_columns": "*",
                    # Default "" (and not []): an executor with an older flow/ validates
                    # it as type "string" — a list in the default brought the run down.
                    "default":     "",
                    "description": (
                        "Campos do GeoDataFrame a exibir no popup do portal. "
                        "Deixe vazio para exibir todos os campos."
                    ),
                },
                {
                    "name":        "crs",
                    "label":       "CRS de destino",
                    "type":        "string",
                    "default":     "EPSG:4326",
                    "description": "CRS de saida (o portal requer WGS84/EPSG:4326).",
                },
            ],
        }

    def _build_artifact_meta(
        self,
        title: str,
        safe_key: str,
        features_count: int,
        publish_config: dict,
        is_published: bool,
    ) -> dict:
        return {
            "output_key":     title,
            "format":         "geojson",
            "features":       features_count,
            "filename":       f"{safe_key}.geojson",
            "credential_id":  None,
            "is_published":   is_published,
            "publish_config": publish_config,
        }

    async def execute(self, inputs: dict) -> dict:
        self.validate()

        title          = str(self.get_param("title", "Camada")).strip() or "Camada"
        color          = str(self.get_param("color", "#3b82f6")).strip() or "#3b82f6"
        opacity        = self.get_param_float("opacity", 0.5)
        description    = str(self.get_param("description", "")).strip()
        crs            = str(self.get_param("crs", "EPSG:4326")).strip() or "EPSG:4326"
        # Tag field: accepts a list, a JSON string (what the screen saves) and the
        # CSV of old definitions.
        visible_fields = colunas_pedidas(self.get_param("visible_fields", []))

        workflow_hash = getattr(self, "_workflow_hash", None)
        workspace_id  = getattr(self, "_workspace_id", None)
        task_id       = self._task_id

        if not task_id:
            raise RuntimeError("task_id nao injetado pelo executor.")

        # Publishing IS sending the geometry to the portal — there is no local version
        # of this. On a machine that retains its data, the node fails instead of
        # publishing: a workflow does not loosen the executor's policy. Before any
        # serialization, so as not to spend CPU on a result that will be refused.
        exigir_envio_permitido(
            f"PublishMap '{title}'",
            "publicar uma camada exige enviar a geometria ao portal",
        )

        # Looks for a GeoDataFrame in the inputs (raises ValueError if missing or empty)
        value = self.get_first_gdf(inputs)

        # Reprojeta, normaliza datetime (numa copia) e serializa
        geojson_str = await asyncio.to_thread(gdf_para_geojson, value, crs)
        # `len(value)` (O(1)) instead of `json.loads(geojson_str)` just to
        # count: `to_json` emits one feature per GDF row, so the count is
        # the same — and the parse of the whole geojson leaves the event loop.
        features_count = len(value)

        safe_key = slugify(title)

        publish_config = {
            "title":          title,
            "color":          color,
            "opacity":        opacity,
            "description":    description,
            "visible_fields": visible_fields,
        }

        layer_id = await self._publish_to_api(
            workflow_hash=workflow_hash,
            workspace_id=workspace_id,
            run_id=task_id,
            layer_key=safe_key,
            geojson_str=geojson_str,
            publish_config=publish_config,
        )

        if layer_id:
            self.log(f"Camada '{title}' publicada no portal ({features_count} features).")
            return {
                "output": {
                    "published_features": features_count,
                    "published_layer_id": layer_id,
                },
                "__artifact__": self._build_artifact_meta(
                    title, safe_key, features_count, publish_config, is_published=True
                ),
            }

        # Fallback: salvar localmente se API falhar
        self.log("Fallback: salvando GeoJSON localmente.")
        if not workspace_id:
            raise RuntimeError("workspace_id nao injetado pelo executor.")

        # `artifacts_root()`, and not `os.getenv("ARTIFACT_DIR")` directly: the
        # executor sets `EXECUTOR_ARTIFACTS_DIR`, and `ARTIFACT_DIR` only shows up
        # via `setdefault` in job_executor.py — which does not run on the
        # in-process path. Diverging from the single root wrote the file out of
        # reach of the retention purge and of the read resolver.
        rel = f"{workspace_id}/{task_id}/{safe_key}.geojson"
        task_dir = os.path.join(artifacts_root(), workspace_id, task_id)
        os.makedirs(task_dir, exist_ok=True)

        file_path = os.path.join(task_dir, f"{safe_key}.geojson")
        await asyncio.to_thread(_write_text, file_path, geojson_str)

        self.log(f"Camada salva localmente: {file_path} ({features_count} features)")
        meta = self._build_artifact_meta(
            title, safe_key, features_count, publish_config, is_published=False
        )
        # Without this the server derives an s3_key for an object that was NEVER
        # uploaded (the portal failed, that is why we ended up here) and an
        # artifact is born whose download responds 404.
        meta.update({
            "s3_key": None,
            "content_location": "executor",
            "local_path": rel,
            "size_bytes": len(geojson_str.encode("utf-8")),
            # `content_location` says WHERE the content is — and it is only here,
            # there is no object in storage and nothing will upload one later. `local_fallback`
            # says WHY — and it was degradation, the portal refused. They are different
            # questions, and marking False here would count a failure as policy.
            "local_fallback": True,
        })
        return {
            "output": {
                "published_features": features_count,
                "published_layer_id": None,
            },
            "__artifact__": meta,
        }

    async def _publish_to_api(
        self,
        workflow_hash: str | None,
        workspace_id: str | None,
        run_id: str | None,
        layer_key: str,
        geojson_str: str,
        publish_config: dict,
    ) -> str | None:
        """
        Sends compressed (gzip) GeoJSON to POST /artifacts/portal/publish.
        Returns layer_id on success, None on failure (triggers the local fallback).
        """
        if not workflow_hash or not workspace_id:
            self.log("Aviso: metadados do workflow ausentes — fallback local.")
            return None

        base_url, auth_headers, verify = get_agent_http_config()
        url = f"{base_url}/artifacts/portal/publish"

        cabecalho = {
            "workflow_hash":  workflow_hash,
            "workspace_id":   workspace_id,
            "run_id":         run_id,
            "layer_key":      layer_key,
            "publish_config": publish_config,
        }
        # Building the envelope (json.dumps of several MB) + gzip.compress go to a
        # thread: they ran on the executor's event loop and held up the WS
        # heartbeat/cancel. The helper embeds the ALREADY serialized geojson raw.
        compressed, tamanho = await asyncio.to_thread(
            _montar_envelope_gzip, cabecalho, geojson_str
        )
        ratio = (1 - len(compressed) / tamanho) * 100 if tamanho else 0
        self.log(
            f"Enviando ao portal: {tamanho:,} bytes "
            f"-> {len(compressed):,} bytes (gzip {ratio:.0f}% reducao)"
        )

        idem_key = f"{workflow_hash}:{layer_key}:{run_id}"
        headers = {
            "Content-Type":      "application/json",
            "Content-Encoding":  "gzip",
            **auth_headers,
            "X-Idempotency-Key": idem_key,
        }

        # Timeout proportional to size: assumes a minimum of 30 KB/s, floor 60s, cap 600s
        upload_timeout = max(60, min(600, len(compressed) // 30_000))

        try:
            from flow.utils.http_retry import async_request_with_retry
            # Idempotent upload (X-Idempotency-Key) → retrying transient errors is safe.
            resp = await async_request_with_retry(
                "POST", url,
                client_kwargs={"timeout": upload_timeout, "follow_redirects": True, "verify": verify},
                content=compressed, headers=headers,
                label="publish_map portal",
            )

            if resp.status_code in (200, 201):
                return resp.json().get("layer_id")

            if resp.status_code == 409:
                self.log("Portal: camada ja publicada neste run (idempotencia).")
                return resp.json().get("layer_id")

            self.log(
                f"Aviso: falha ao publicar no portal "
                f"(HTTP {resp.status_code}): {resp.text[:200]}"
            )
            return None

        except Exception as exc:
            import traceback
            self.log(
                f"Aviso: nao foi possivel publicar no portal: "
                f"{type(exc).__name__}: {exc}\n"
                f"{traceback.format_exc()[:500]}"
            )
            return None
