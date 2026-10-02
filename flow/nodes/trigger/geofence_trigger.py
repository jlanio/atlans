import asyncio
import json
import geopandas as gpd
from shapely.geometry import shape, Point
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
logger = get_logger(__name__)


@register_node
class GeofenceTriggerNode(BaseNode):

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'GeofenceTrigger',
            'alias': 'Gatilho de Geofence',
            'description': (
                'Verifica se um ponto ou conjunto de pontos está dentro de uma zona '
                'geográfica (geofence) e aciona o workflow.'
            ),
            'type': 'trigger',
            'dynamic_output': False,
            'properties': [
                {
                    'name': 'geofenceGeoJSON',
                    'label': 'Geometria da cerca',
                    'type': 'string',
                    'default': '',
                    'description': (
                        'GeoJSON string da zona de geofence (Polygon ou MultiPolygon).'
                    )
                },
                {
                    'name': 'latitude',
                    'label': 'Latitude',
                    'type': 'string',
                    'default': '',
                    'description': (
                        'Latitude do ponto a verificar (se não vier dos inputs).'
                    )
                },
                {
                    'name': 'longitude',
                    'label': 'Longitude',
                    'type': 'string',
                    'default': '',
                    'description': (
                        'Longitude do ponto a verificar (se não vier dos inputs).'
                    )
                },
                {
                    'name': 'latKey',
                    'label': 'Chave da latitude',
                    'type': 'string',
                    'default': 'lat',
                    'description': (
                        'Chave em inputs para latitude (se ponto vem dos inputs).'
                    )
                },
                {
                    'name': 'lonKey',
                    'label': 'Chave da longitude',
                    'type': 'string',
                    'default': 'lon',
                    'description': (
                        'Chave em inputs para longitude (se ponto vem dos inputs).'
                    )
                },
            ],
            'outputs': [
                {'name': 'output', 'type': 'object', 'description': 'Resultado da verificação de geofence'},
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers (run in a thread to avoid blocking the event loop)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_geofence(geojson_str: str):
        """
        Parse a GeoJSON string and return a Shapely geometry.
        Raises ValueError when the string is empty, invalid JSON, or not a
        Polygon / MultiPolygon geometry.
        """
        if not geojson_str or not geojson_str.strip():
            raise ValueError(
                "O parâmetro 'geofenceGeoJSON' é obrigatório e não pode estar vazio."
            )

        try:
            geojson_obj = json.loads(geojson_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"'geofenceGeoJSON' não é um JSON válido: {exc}"
            ) from exc

        # Accept both a bare geometry dict and a GeoJSON Feature / FeatureCollection
        geom_type = geojson_obj.get('type', '')

        if geom_type == 'Feature':
            geom_dict = geojson_obj.get('geometry')
            if geom_dict is None:
                raise ValueError(
                    "O Feature GeoJSON não contém uma geometria ('geometry' é null)."
                )
        elif geom_type == 'FeatureCollection':
            features = geojson_obj.get('features', [])
            if not features:
                raise ValueError(
                    "O FeatureCollection GeoJSON está vazio (sem features)."
                )
            # Use only the first feature for the geofence boundary
            geom_dict = features[0].get('geometry')
            if geom_dict is None:
                raise ValueError(
                    "A primeira feature do FeatureCollection não possui geometria."
                )
        else:
            # Assume a raw geometry object
            geom_dict = geojson_obj

        allowed_types = {'Polygon', 'MultiPolygon'}
        actual_type = geom_dict.get('type', '')
        if actual_type not in allowed_types:
            raise ValueError(
                f"'geofenceGeoJSON' deve ser do tipo Polygon ou MultiPolygon, "
                f"mas recebeu '{actual_type}'."
            )

        try:
            geofence_shape = shape(geom_dict)
        except Exception as exc:
            raise ValueError(
                f"Não foi possível criar a geometria Shapely a partir do GeoJSON: {exc}"
            ) from exc

        if not geofence_shape.is_valid:
            # Attempt an automatic repair via buffer(0) before failing
            geofence_shape = geofence_shape.buffer(0)
            if not geofence_shape.is_valid:
                raise ValueError(
                    "A geometria do geofence é inválida e não pôde ser corrigida automaticamente."
                )

        return geofence_shape

    @staticmethod
    def _check_single_point(
        geofence_shape, lat: float, lon: float
    ) -> Dict[str, Any]:
        """Return a result dict indicating whether (lat, lon) is inside the geofence."""
        point = Point(lon, lat)
        inside = point.within(geofence_shape)
        logger.info(
            "GeofenceTrigger - ponto (lat=%.6f, lon=%.6f) inside=%s",
            lat, lon, inside
        )
        return {
            'inside': bool(inside),
            'latitude': lat,
            'longitude': lon,
        }

    @staticmethod
    def _check_geodataframe(
        geofence_shape, gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Reproject *gdf* to EPSG:4326 if needed and return only the rows whose
        geometry falls within *geofence_shape*.
        """
        # Ensure the GDF has a CRS; assume EPSG:4326 when none is set
        if gdf.crs is None:
            logger.warning(
                "GeofenceTrigger - GeoDataFrame sem CRS definido; assumindo EPSG:4326."
            )
            gdf = gdf.set_crs(epsg=4326)

        if gdf.crs.to_epsg() != 4326:
            logger.info(
                "GeofenceTrigger - reprojetando GeoDataFrame de %s para EPSG:4326.",
                gdf.crs.to_string()
            )
            gdf = gdf.to_crs(epsg=4326)

        mask = gdf.geometry.within(geofence_shape)
        filtered = gdf[mask].copy()
        logger.info(
            "GeofenceTrigger - GeoDataFrame: %d/%d features dentro do geofence.",
            len(filtered), len(gdf)
        )
        return filtered

    # ------------------------------------------------------------------
    # Main execute method
    # ------------------------------------------------------------------

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        geojson_str: str = self.parameters.get('geofenceGeoJSON', '').strip()
        lat_key: str = self.parameters.get('latKey', 'lat')
        lon_key: str = self.parameters.get('lonKey', 'lon')
        param_lat: str = self.parameters.get('latitude', '').strip()
        param_lon: str = self.parameters.get('longitude', '').strip()

        # --- 1. Parse geofence (offloaded to a thread) -------------------
        geofence_shape = await asyncio.to_thread(
            self._parse_geofence, geojson_str
        )

        # --- 2. Detect input mode ----------------------------------------

        # Priority A: a GeoDataFrame provided by an upstream node
        # Look for the first GeoDataFrame value in inputs
        input_gdf: gpd.GeoDataFrame | None = None
        for v in inputs.values():
            if isinstance(v, gpd.GeoDataFrame):
                input_gdf = v
                break

        if input_gdf is not None:
            # --- Mode: GeoDataFrame batch check --------------------------
            logger.info(
                "GeofenceTrigger - modo GeoDataFrame (%d features).", len(input_gdf)
            )
            filtered_gdf = await asyncio.to_thread(
                self._check_geodataframe, geofence_shape, input_gdf
            )
            return {'output': filtered_gdf}

        # Priority B: lat/lon provided in runtime inputs (trigger payload)
        input_lat = inputs.get(lat_key)
        input_lon = inputs.get(lon_key)

        if input_lat is not None and input_lon is not None:
            try:
                lat = float(input_lat)
                lon = float(input_lon)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Não foi possível converter as chaves de input '{lat_key}'/'{lon_key}' "
                    f"para float: {exc}"
                ) from exc

            logger.info(
                "GeofenceTrigger - modo ponto via inputs (keys='%s'/'%s').",
                lat_key, lon_key
            )
            result = await asyncio.to_thread(
                self._check_single_point, geofence_shape, lat, lon
            )
            return {'output': result}

        # Priority C: static lat/lon parameters
        if param_lat and param_lon:
            try:
                lat = float(param_lat)
                lon = float(param_lon)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Não foi possível converter os parâmetros 'latitude'/'longitude' "
                    f"para float: {exc}"
                ) from exc

            logger.info(
                "GeofenceTrigger - modo ponto via parâmetros estáticos "
                "(lat=%.6f, lon=%.6f).", lat, lon
            )
            result = await asyncio.to_thread(
                self._check_single_point, geofence_shape, lat, lon
            )
            return {'output': result}

        # Nothing usable was found
        raise ValueError(
            "GeofenceTrigger: nenhuma coordenada de ponto foi fornecida. "
            "Informe 'latitude'/'longitude' nos parâmetros, passe as chaves "
            f"'{lat_key}'/'{lon_key}' nos inputs, ou conecte um nó que produza "
            "um GeoDataFrame."
        )
