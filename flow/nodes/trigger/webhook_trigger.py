import json
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)

_GEOJSON_TYPES = ("FeatureCollection", "Feature")


def _try_geojson_to_gdf(obj):
    """Tenta converter um objeto (dict ou string) em GeoDataFrame se for GeoJSON.

    Busca recursivamente: primeiro o objeto raiz, depois valores string/dict
    dentro do dict (1 nível de profundidade).
    Retorna GeoDataFrame ou None.
    """
    import geopandas as gpd

    def _convert(data):
        if not isinstance(data, dict) or data.get("type") not in _GEOJSON_TYPES:
            return None
        features = data.get("features", []) if data["type"] == "FeatureCollection" else [data]
        gdf = gpd.GeoDataFrame.from_features(features)
        if not gdf.crs:
            gdf = gdf.set_crs("EPSG:4326")
        return gdf

    # 1) String raiz → tenta parsear como JSON
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except (json.JSONDecodeError, ValueError):
            return None

    # 2) Dict raiz é GeoJSON?
    if isinstance(obj, dict):
        gdf = _convert(obj)
        if gdf is not None:
            return gdf

        # 3) Varre valores do dict procurando GeoJSON (string ou dict aninhado)
        for value in obj.values():
            candidate = value
            if isinstance(value, str):
                try:
                    candidate = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    continue
            gdf = _convert(candidate)
            if gdf is not None:
                return gdf

    return None


@register_node
class WebhookTrigger(BaseNode):
    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'WebhookTrigger',
            'alias': 'Gatilho por Web',
            'description': 'Inicia um workflow a partir de payload HTTP.',
            'type': 'trigger',
            'dynamic_output': False,
            'properties': [
                {
                    'name': 'alias',
                    'type': 'string',
                    'default': '',
                    'description': 'Nome amigável do webhook'
                },
                {
                    'name': 'payloadField',
                    'label': 'Campo do payload',
                    'type': 'string',
                    'default': '',
                    'description': 'Opcional. Se definido, o body é lido de inputs[payloadField]. Se vazio, inputs ja eh o payload.'
                },
                {
                    'name': 'credential_id',
                    'type': 'string',
                    'default': '',
                    'description': 'UUID da credencial (usado apenas para rastreio)'
                },
                {
                    'name': 'payload_schema',
                    'label': 'Schema do payload',
                    'type': 'object',
                    'default': {},
                    'description': 'Schema de validacao do payload (gerado pela tabela de campos)'
                },
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'Corpo do webhook'},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        # Configuração
        field = (self.parameters.get('payloadField') or '').strip()

        # Resolução do payload:
        #   - field definido → lê de inputs[field] (caller envelopa)
        #   - field vazio    → inputs ja eh o payload (default p/ webhook HTTP)
        raw = inputs.get(field) if field else inputs

        if raw is None:
            payload: Dict[str, Any] = {}
        elif isinstance(raw, str):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {field or 'payload': raw}
        elif isinstance(raw, dict):
            payload = raw
        else:
            payload = {field or 'payload': raw}

        # Valida payload contra o schema definido pelo usuario (se houver)
        schema = self.parameters.get('payload_schema')
        if schema and isinstance(schema, dict) and schema.get("properties"):
            from jsonschema import Draft7Validator
            validator = Draft7Validator(schema)
            errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
            if errors:
                parts = [f"'{err.json_path or '$'}': {err.message}" for err in errors]
                if len(parts) == 1:
                    raise ValueError(f"Payload invalido em {parts[0]}")
                raise ValueError(
                    f"Payload invalido — {len(parts)} erros: " + "; ".join(parts)
                )

        # Auto-detecção recursiva: converte GeoJSON para GeoDataFrame
        # Funciona com GeoJSON no raiz, em campo string ou dict aninhado
        try:
            gdf = _try_geojson_to_gdf(payload)
            if gdf is not None:
                logger.info(
                    "WebhookTrigger - GeoJSON detectado, convertido para GeoDataFrame (%d features, CRS=%s)",
                    len(gdf), gdf.crs,
                )
                return {"output": gdf}
        except Exception as exc:
            logger.warning(
                "WebhookTrigger - falha na conversão GeoJSON→GeoDataFrame: %s. Entregando como dict.",
                exc,
            )

        logger.info(f"WebhookTrigger - payload extraído em '{field}' e exposto como 'output'")
        return {"output": payload}
