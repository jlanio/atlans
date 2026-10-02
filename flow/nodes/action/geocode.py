# flow/nodes/action/geocode.py
"""
Nó Geocode — geocodifica endereços via Nominatim (OpenStreetMap) e retorna um GeoDataFrame.
Sem chave de API necessária; respeita o Nominatim Usage Policy (1 req/s).

O servidor é o público (nominatim.openstreetmap.org) ou o que o executor
configurar em NOMINATIM_URL (um Nominatim próprio, para volume maior). O
User-Agent leva o site da instalação (flow/utils/identidade.py), como a política
pede; o campo do nó o substitui.
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
from flow.utils.identidade import user_agent as user_agent_da_instalacao
from flow.utils.logger import get_logger

logger = get_logger(__name__)

# O padrão antigo do campo, e o que continua no catálogo. O web grava os
# padrões no nó, e um executor anterior a esta versão chamaria o Nominatim com
# User-Agent vazio — o geopy recusa (ConfigurationError). Este nó trata o valor
# antigo como vazio: os dois querem dizer "o da instalação".
USER_AGENT_ANTIGO = "atlas-studio-geocode/1.0"


def user_agent_do_no(valor) -> str:
    """O User-Agent do campo, ou o da instalação quando ele é vazio ou o antigo."""
    texto = (valor or "").strip()
    if texto in ("", USER_AGENT_ANTIGO):
        return user_agent_da_instalacao("geocode")
    return texto


def _servidor_nominatim(ambiente=None) -> dict[str, str]:
    """`domain`/`scheme` do geopy para NOMINATIM_URL; vazio = o servidor público."""
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
                    # O editor oferece os nomes vistos na última execução do nó
                    # anterior — mesma dica do AttributeFilter.
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
                    "default": USER_AGENT_ANTIGO,
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
        servidor       = _servidor_nominatim()

        # Obtém o dado de entrada: pode ser GeoDataFrame ou DataFrame regular
        # Se houver um GDF, usa-o; caso contrário, pega o primeiro valor dos inputs
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
