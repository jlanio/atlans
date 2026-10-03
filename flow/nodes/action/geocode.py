# flow/nodes/action/geocode.py
"""
Geocode node — geocodes addresses via Nominatim (OpenStreetMap) and returns a GeoDataFrame.
No API key required; honors the Nominatim Usage Policy (1 req/s).

The server is the public one (nominatim.openstreetmap.org) or whatever the executor
configures in NOMINATIM_URL (a self-hosted Nominatim, for higher volume). The
User-Agent carries the installation's site (flow/utils/identidade.py), as the policy
asks; the node's field overrides it.
"""
import asyncio
import os
from urllib.parse import urlsplit
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.identidade import user_agent as installation_user_agent
from flow.utils.logger import get_logger

logger = get_logger(__name__)

# The field's old default, and the one still in the catalog. The web app writes
# the defaults into the node, and an executor older than this version would call
# Nominatim with an empty User-Agent — geopy refuses it (ConfigurationError). This
# node treats the old value as empty: both mean "the installation's".
LEGACY_USER_AGENT = "atlas-studio-geocode/1.0"


def user_agent_do_no(valor) -> str:
    """The field's User-Agent, or the installation's when it is empty or the old one."""
    texto = (valor or "").strip()
    if texto in ("", LEGACY_USER_AGENT):
        return installation_user_agent("geocode")
    return texto


def _nominatim_server(ambiente=None) -> dict[str, str]:
    """geopy `domain`/`scheme` for NOMINATIM_URL; empty = the public server."""
    ambiente = os.environ if ambiente is None else ambiente
    url = (ambiente.get("NOMINATIM_URL") or "").strip().rstrip("/")
    if not url:
        return {}
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise ValueError(f"NOMINATIM_URL={url!r} não é uma URL http(s) (ex.: https://nominatim.example.org).")
    return {"domain": partes.netloc + partes.path, "scheme": partes.scheme}


@register_node
class GeocodeNode(BaseNode):

    @classmethod
    def description(cls):
        return {
            "name": "GeocodeNode",
            "alias": "Geocodificação",
            "description": (
                "Geocodifica uma coluna de endereços usando o Nominatim (OSM). "
                "Retorna GeoDataFrame com geometria de pontos."
            ),
            "type": "action",
            "properties": [
                {
                    "name": "address_column",
                    "label": "Coluna de Endereço",
                    "type": "string",
                    "default": "address",
                    # The editor offers the names seen in the last run of the
                    # previous node — same hint as AttributeFilter.
                    "suggest_columns": "*",
                    "description": "Nome da coluna que contém os endereços a geocodificar.",
                },
                {
                    "name": "crs",
                    "label": "CRS de saída",
                    "type": "string",
                    "default": "EPSG:4326",
                    "description": "CRS de saída (padrão WGS84).",
                },
                {
                    "name": "delay_seconds",
                    "label": "Intervalo (s)",
                    "type": "number",
                    "default": 1.1,
                    "description": "Intervalo entre requisições (mín. 1s por Nominatim Usage Policy).",
                },
                {
                    "name": "user_agent",
                    "label": "User-Agent",
                    "type": "string",
                    "default": LEGACY_USER_AGENT,
                    "description": (
                        "User-Agent para as requisições Nominatim. Vazio ou o padrão = "
                        "Atlans/geocode com o site desta instalação, como a política de uso pede."
                    ),
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "GeoDataFrame com geometria de pontos geocodificados"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()
        from geopy.geocoders import Nominatim
        from geopy.extra.rate_limiter import RateLimiter

        address_column = self.parameters.get("address_column", "address")
        crs            = self.parameters.get("crs", "EPSG:4326")
        delay          = float(self.parameters.get("delay_seconds", 1.1))
        user_agent     = user_agent_do_no(self.parameters.get("user_agent"))
        servidor       = _nominatim_server()

        # Gets the input data: may be a GeoDataFrame or a regular DataFrame
        # If there is a GDF, uses it; otherwise, takes the first value of the inputs
        data = None
        for v in inputs.values():
            if isinstance(v, (gpd.GeoDataFrame, pd.DataFrame)):
                data = v
                break
        if data is None and inputs:
            data = next(iter(inputs.values()))
        if data is None:
            raise ValueError("Nenhum dado de entrada encontrado para geocodificação.")

        if isinstance(data, gpd.GeoDataFrame):
            df = pd.DataFrame(data.drop(columns="geometry", errors='ignore'))
        else:
            df = pd.DataFrame(data)

        if address_column not in df.columns:
            raise ValueError(f"Coluna '{address_column}' não encontrada na entrada.")

        def _geocode_all(df: pd.DataFrame) -> gpd.GeoDataFrame:
            geolocator = Nominatim(user_agent=user_agent, **servidor)
            geocode = RateLimiter(geolocator.geocode, min_delay_seconds=delay, error_wait_seconds=5)

            lats, lons, found = [], [], []
            for addr in df[address_column]:
                location = geocode(str(addr))
                if location:
                    lats.append(location.latitude)
                    lons.append(location.longitude)
                    found.append(True)
                else:
                    lats.append(None)
                    lons.append(None)
                    found.append(False)

            df["latitude"]  = lats
            df["longitude"] = lons
            df["geocoded"]  = found

            geometries = [
                Point(lon, lat) if lat is not None else None
                for lat, lon in zip(lats, lons)
            ]
            return gpd.GeoDataFrame(df, geometry=geometries, crs=crs)

        result = await asyncio.to_thread(_geocode_all, df)
        n_ok = int(result["geocoded"].sum())
        logger.info(f"Geocodificação concluída: {n_ok}/{len(result)} endereços encontrados.")
        return {"output": result}
