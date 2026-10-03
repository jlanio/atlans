# app/services/fundos_do_mapa.py
"""
The installation's map basemaps in Carta nodes.

Carta offers named basemaps (satellite, satellite with labels, streets), and each
one's URL belongs to the INSTALLATION (MAPA_*_URL, `app/core/config.py`), not to the code.
What runs Carta is the executor, which does not have that configuration: the server
puts it into the node when dispatching, as it does with credentials (`credential_resolver`).

The injected value ALWAYS replaces whatever comes in the definition, in both forms
of properties a node can have (`properties`, the one the executor reads, and
`data.properties`, the canvas's): a `fundo_da_instalacao` written by hand in the
workflow does not pass for an installation basemap. With no configuration for the
chosen basemap, it goes with an empty URL — and it is the `url` key that tells the
executor the server answered: the installation does not have that basemap, and it
falls back to its own environment or, for "ruas" (streets), to OpenStreetMap. Without
the key, the dispatcher was a server older than this version.
"""
from __future__ import annotations

import copy

from app.core import config

IMAGE_MAP_NODE = "CartaImagem"


NO_BASEMAP: dict[str, str] = {"url": "", "credito": ""}


def _property_dicts(no: dict) -> list[dict]:
    """Every property dictionary of the node: the executor reads `properties`,
    and the canvas writes to `data.properties`."""
    found = []
    if isinstance(no.get("properties"), dict):
        found.append(no["properties"])
    dados = no.get("data")
    if isinstance(dados, dict) and isinstance(dados.get("properties"), dict):
        found.append(dados["properties"])
    return found


def inject_basemaps(definition: dict, fundos: dict[str, dict[str, str]] | None = None) -> dict:
    """The definition with the installation basemap in each Carta node (a copy, if it changes)."""
    nos = definition.get("nodes") if isinstance(definition, dict) else None
    if not nos or not any(isinstance(n, dict) and n.get("name") == IMAGE_MAP_NODE for n in nos):
        return definition
    fundos = config.MAPA_FUNDOS if fundos is None else fundos
    enriched = copy.deepcopy(definition)
    for no in enriched["nodes"]:
        if not isinstance(no, dict) or no.get("name") != IMAGE_MAP_NODE:
            continue
        for props in _property_dicts(no):
            fundo = str(props.get("fundo") or "nenhum").strip().lower()
            props["fundo_da_instalacao"] = dict(fundos.get(fundo) or NO_BASEMAP)
    return enriched
