import asyncio
import json
import geopandas as gpd
import httpx
import pandas as pd
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.geo_helpers import gdf_para_geojson, safe_httpx_request
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class SendWebhookNode(BaseNode):
    """
    Sends an HTTP request (webhook) with workflow data as the JSON payload.
    If a GeoDataFrame is found in the inputs, it is serialized as GeoJSON and
    included in the payload. Includes SSRF protection.
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SendWebhook',
            'alias': 'Enviar Webhook',
            'description': 'Envia uma requisição HTTP (webhook) com dados do workflow como payload JSON.',
            'type': 'output',
            'dynamic_output': False,
            'outputs': [
                {'name': 'status', 'type': 'number', 'description': 'Código de status HTTP da resposta'},
                {'name': 'url', 'type': 'string', 'description': 'URL para a qual o webhook foi enviado'},
            ],
            'properties': [
                {
                    'name': 'url',
                    'required': True,
                    'label': 'URL',
                    'type': 'string',
                    'default': '',
                    'description': 'URL de destino do webhook.'
                },
                {
                    'name': 'method',
                    'label': 'Método',
                    'type': 'select',
                    'default': 'POST',
                    'description': 'Método HTTP do webhook.',
                    'options': [
                        {'value': 'POST',   'label': 'POST'},
                        {'value': 'PUT',    'label': 'PUT'},
                        {'value': 'PATCH',  'label': 'PATCH'},
                        {'value': 'GET',    'label': 'GET'},
                        {'value': 'DELETE', 'label': 'DELETE'},
                    ],
                },
                {
                    'name': 'headers',
                    'label': 'Cabeçalhos',
                    'type': 'object',
                    'default': {},
                    'description': 'Headers HTTP adicionais a serem enviados com a requisição.'
                },
                {
                    'name': 'includeMetadata',
                    'label': 'Incluir metadados',
                    'type': 'string',
                    'default': 'false',
                    'description': (
                        "Se 'true', inclui metadados adicionais (contagem de feições, CRS) "
                        "no payload enviado."
                    )
                }
            ]
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        url = self.parameters.get('url', '').strip()
        method = self.parameters.get('method', 'POST').strip().upper()
        headers = self.parameters.get('headers') or {}
        include_metadata_str = self.parameters.get('includeMetadata', 'false').strip().lower()
        include_metadata = include_metadata_str in ('true', '1', 'yes')

        if not url:
            raise ValueError("Parâmetro 'url' é obrigatório.")

        # Monta o payload JSON
        payload: Dict[str, Any] = {}

        # Tenta encontrar um GeoDataFrame nos inputs (best-effort)
        gdf: gpd.GeoDataFrame | None = None
        try:
            gdf = self.get_first_gdf(inputs)
        except (ValueError, TypeError):
            pass  # Sem GDF — tenta DataFrame puro abaixo

        if gdf is not None and not gdf.empty:
            try:
                geojson_str = await asyncio.to_thread(gdf_para_geojson, gdf, nat_como_nulo=True)
                payload['data'] = json.loads(geojson_str)
            except Exception as e:
                raise RuntimeError(f"Erro ao serializar GeoDataFrame para GeoJSON: {e}") from e

            if include_metadata:
                payload['metadata'] = {
                    'feature_count': len(gdf),
                    'crs': str(gdf.crs) if gdf.crs else None,
                    'columns': list(gdf.columns)
                }
        else:
            # Fallback: DataFrame puro vira lista de records.
            df = next(
                (v for v in inputs.values()
                 if isinstance(v, pd.DataFrame) and not isinstance(v, gpd.GeoDataFrame)),
                None,
            )
            if df is not None and not df.empty:
                payload['data'] = df.to_dict(orient="records")
                if include_metadata:
                    payload['metadata'] = {
                        'row_count': len(df),
                        'columns': list(df.columns),
                    }
            else:
                logger.warning("Nenhum GeoDataFrame ou DataFrame encontrado nos inputs. Enviando payload vazio.")

        # Ensures a JSON Content-Type
        if 'Content-Type' not in headers and 'content-type' not in headers:
            headers = {**headers, 'Content-Type': 'application/json'}

        logger.info(f"Enviando webhook {method} para: {url}")

        # SEG (SSRF): safe_httpx_request validates the URL AND pins the resolved IP.
        # We used to call validate_url_ssrf and discard the result, and
        # httpx re-resolved DNS (TOCTOU / DNS rebinding to metadata/internal).
        try:
            response = await safe_httpx_request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
                timeout=30,
            )
        except httpx.RequestError as e:
            logger.error(f"Erro de rede ao enviar webhook para '{url}': {e}")
            raise RuntimeError(f"Erro de rede ao enviar webhook: {e}") from e
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar webhook para '{url}': {e}")
            raise RuntimeError(f"Erro ao enviar webhook: {e}") from e

        logger.info(f"Webhook enviado. Status HTTP: {response.status_code}")
        return {'output': {'status': response.status_code, 'url': url}}
