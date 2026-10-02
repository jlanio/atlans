# app/services/fundos_do_mapa.py
"""
Os fundos de mapa da instalação nos nós Carta.

A Carta oferece fundos com nome (satélite, satélite com rótulos, ruas), e a URL
de cada um é da INSTALAÇÃO (MAPA_*_URL, `app/core/config.py`), não do código.
Quem roda a Carta é o executor, que não tem essa configuração: o servidor a
põe no nó ao despachar, como faz com as credenciais (`credential_resolver`).

O valor injetado SEMPRE substitui o que vier na definição, nas duas formas
de propriedades que um nó pode ter (`properties`, a que o executor lê, e
`data.properties`, a do canvas): um `fundo_da_instalacao` escrito à mão no
workflow não passa por fundo da instalação. Sem configuração para o fundo
escolhido, vai com a URL vazia — e é a chave `url` que diz ao executor que o
servidor respondeu: a instalação não tem aquele fundo, e ele cai no próprio
ambiente ou, para "ruas", no OpenStreetMap. Sem a chave, quem despachou foi
um servidor anterior a esta versão.
"""
from __future__ import annotations

import copy

from app.core import config

NO_DA_CARTA = "CartaImagem"


SEM_FUNDO: dict[str, str] = {"url": "", "credito": ""}


def _propriedades(no: dict) -> list[dict]:
    """Todos os dicionários de propriedades do nó: o executor lê `properties`,
    e o canvas grava em `data.properties`."""
    achadas = []
    if isinstance(no.get("properties"), dict):
        achadas.append(no["properties"])
    dados = no.get("data")
    if isinstance(dados, dict) and isinstance(dados.get("properties"), dict):
        achadas.append(dados["properties"])
    return achadas


def injetar_fundos_de_mapa(definition: dict, fundos: dict[str, dict[str, str]] | None = None) -> dict:
    """A definição com o fundo da instalação em cada nó Carta (cópia, se mudar)."""
    nos = definition.get("nodes") if isinstance(definition, dict) else None
    if not nos or not any(isinstance(n, dict) and n.get("name") == NO_DA_CARTA for n in nos):
        return definition
    fundos = config.MAPA_FUNDOS if fundos is None else fundos
    enriched = copy.deepcopy(definition)
    for no in enriched["nodes"]:
        if not isinstance(no, dict) or no.get("name") != NO_DA_CARTA:
            continue
        for props in _propriedades(no):
            fundo = str(props.get("fundo") or "nenhum").strip().lower()
            props["fundo_da_instalacao"] = dict(fundos.get(fundo) or SEM_FUNDO)
    return enriched
