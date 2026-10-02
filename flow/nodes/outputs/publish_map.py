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
    """Monta o envelope JSON do publish e comprime — feito para rodar em thread.

    Embute o `geojson_str` (que `to_json` ja serializou) CRU, sem reparsa-lo:
    elimina o json.loads->json.dumps redundante do geojson inteiro. `cabecalho`
    tem sempre chaves aqui, entao `json.dumps` termina em '}' e inserir
    `,"geojson":<str>` antes do fecho produz JSON valido. Devolve
    (comprimido, tamanho_do_payload) para o log da razao de compressao.
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
                    # Nó de entrada única: '*' e a porta dariam no mesmo.
                    "suggest_columns": "*",
                    # Default "" (e não []): executor com flow/ anterior valida
                    # como type "string" — lista no default derrubava a run.
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
        # Campo de fichas: aceita lista, JSON-string (o que a tela grava) e o
        # CSV das definitions antigas.
        visible_fields = colunas_pedidas(self.get_param("visible_fields", []))

        workflow_hash = getattr(self, "_workflow_hash", None)
        workspace_id  = getattr(self, "_workspace_id", None)
        task_id       = self._task_id

        if not task_id:
            raise RuntimeError("task_id nao injetado pelo executor.")

        # Publicar E enviar a geometria ao portal — nao ha versao local disto.
        # Numa maquina que retem os dados, o no falha em vez de publicar: um
        # workflow nao afrouxa a politica do executor. Antes de qualquer
        # serializacao, para nao gastar CPU num resultado que sera recusado.
        exigir_envio_permitido(
            f"PublishMap '{title}'",
            "publicar uma camada exige enviar a geometria ao portal",
        )

        # Busca GeoDataFrame nos inputs (levanta ValueError se ausente ou vazio)
        value = self.get_first_gdf(inputs)

        # Reprojeta, normaliza datetime (numa copia) e serializa
        geojson_str = await asyncio.to_thread(gdf_para_geojson, value, crs)
        # `len(value)` (O(1)) no lugar de `json.loads(geojson_str)` so para
        # contar: `to_json` emite uma feicao por linha do GDF, entao a contagem
        # e a mesma — e some o parse do geojson inteiro no event loop.
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

        # `artifacts_root()`, e nao `os.getenv("ARTIFACT_DIR")` direto: o
        # executor define `EXECUTOR_ARTIFACTS_DIR`, e `ARTIFACT_DIR` so aparece
        # via `setdefault` em job_executor.py — que nao roda no caminho
        # in-process. Divergir da raiz unica gravava o arquivo fora do alcance
        # da purga por retencao e do resolver de leitura.
        rel = f"{workspace_id}/{task_id}/{safe_key}.geojson"
        task_dir = os.path.join(artifacts_root(), workspace_id, task_id)
        os.makedirs(task_dir, exist_ok=True)

        file_path = os.path.join(task_dir, f"{safe_key}.geojson")
        await asyncio.to_thread(_write_text, file_path, geojson_str)

        self.log(f"Camada salva localmente: {file_path} ({features_count} features)")
        meta = self._build_artifact_meta(
            title, safe_key, features_count, publish_config, is_published=False
        )
        # Sem isto o servidor deriva uma s3_key para um objeto que NUNCA foi
        # enviado (o portal falhou, foi por isso que caimos aqui) e nasce um
        # artefato cujo download responde 404.
        meta.update({
            "s3_key": None,
            "content_location": "executor",
            "local_path": rel,
            "size_bytes": len(geojson_str.encode("utf-8")),
            # `content_location` diz ONDE o conteudo esta — e ele esta so aqui,
            # nao ha objeto no storage e nada vai enviar um depois. `local_fallback`
            # diz POR QUE — e foi degradacao, o portal recusou. Sao perguntas
            # diferentes, e marcar False aqui contaria uma falha como politica.
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
        Envia GeoJSON comprimido (gzip) para POST /artifacts/portal/publish.
        Retorna layer_id em caso de sucesso, None em caso de falha (aciona fallback local).
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
        # Montagem do envelope (json.dumps de varios MB) + gzip.compress vao para
        # thread: rodavam no event loop do executor e seguravam heartbeat/cancel
        # do WS. O helper embute o geojson JA serializado cru.
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

        # Timeout proporcional ao tamanho: assume mínimo 30 KB/s, floor 60s, cap 600s
        upload_timeout = max(60, min(600, len(compressed) // 30_000))

        try:
            from flow.utils.http_retry import async_request_with_retry
            # Upload idempotente (X-Idempotency-Key) → retry de transitorios é seguro.
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
