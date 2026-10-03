# app/mcp/catalogo.py
"""
The node catalog in two sizes: the index that fits in the context and the full sheet.

The `description()` of all registered nodes adds up to about 80 KB of JSON.
Delivering that in one call consumes the context budget of whoever is on the
other side before the conversation starts — and nine tenths of it is property
detail that only matters once the node has been chosen. Hence the split:

- `compact_index` answers "which nodes exist, and what for" in ~10 KB: name,
  type, the first sentence of the description and whether the node needs a
  credential;
- `descrever(brief=True)` answers "how do I configure this node" with the
  essential properties;
- `descrever(brief=False)` delivers the whole sheet plus the hints that are not
  in any field — that this node's outputs depend on what the user declares,
  that a given property expects a column name.

Everything is derived from the node registry at call time. No copied list: a
new node appears here in the same deploy in which it appears in the editor, and
a disabled node disappears from both.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable, Mapping

# The first sentence of a long description can still be long; the whole index
# is read at once, so the cut is worth more than the full sentence
# (whoever wants the whole text calls `describe_node`).
_MAX_ONE_LINE = 160

# Floor for accepting a segment as a sentence. The period that ends a sentence
# and the period of an abbreviation ("Ex.", "etc.", "p. ex.", "Obs.") are the
# same character, and cutting at the first one would fill the index with "Ex"
# and "etc" lines — which say nothing about the node. Below this length the
# segment is JOINED to the next one, never discarded: losing the rest of the
# sentence is worse than a slightly longer line. The value sits below any real
# short sentence ("Recorta camadas", "Ordena as linhas") and above the
# abbreviations that appear in the descriptions.
_MIN_ONE_LINE = 8

# Abbreviations that end with a period in the MIDDLE of a sentence and escape the
# floor above ("Junta SHP, GeoJSON, etc. Aceita ZIP." has 33 characters before
# the period). A short, explicit list on purpose: whatever is not here simply
# cuts as it always did — erring on the side of a shorter line is preferable to
# guessing grammar.
_ABBREVIATIONS = frozenset({"ex", "etc", "p", "pag", "obs", "cf", "fig", "aprox", "vs", "ref"})


def _description_text(desc: Any) -> str:
    """The description, whether it comes as text, a dict or a `NodeDefinition`."""
    if isinstance(desc, str):
        return desc
    if isinstance(desc, Mapping):
        return str(desc.get("description") or "")
    return str(getattr(desc, "description", None) or "")


def one_line(desc: Any) -> str:
    """The first sentence of the description, without the final period.

    The cut is at the first PARAGRAPH, not at the first line break: many
    catalog descriptions are written as running text and break mid-sentence,
    but almost all of them separate the long explanation with a blank line.

    Within the paragraph, the sentence ends at the first period followed by a
    SPACE — requiring the space is what protects decimals, which the catalog
    uses all the time ("buffer de 0.5 m"). That leaves abbreviations, which
    bring the space along: a segment too short to be a sentence ("Ex.",
    "p. ex.") or ending in a known abbreviation ("…, etc.") is joined to the
    next one, instead of cutting the description in the middle and leaving the
    index line without saying what the node is for.
    """
    paragraph = _description_text(desc).split("\n\n")[0]
    texto = " ".join(paragraph.split())
    if not texto:
        return ""
    partes = texto.split(". ")
    frase = partes[0]
    for seguinte in partes[1:]:
        if not _is_sentence_end(frase):
            frase = f"{frase}. {seguinte}"
            continue
        break
    frase = frase.rstrip(".")
    if len(frase) > _MAX_ONE_LINE:
        frase = frase[: _MAX_ONE_LINE - 1].rstrip() + "…"
    return frase


def _is_sentence_end(trecho: str) -> bool:
    """Does the period after this excerpt really end a sentence?

    Two refusals: the excerpt is too short to be a sentence (it is a whole
    abbreviation, "Ex.") or it ends in a known abbreviation ("…, etc.").
    """
    without_period = trecho.rstrip(".")
    if len(without_period) < _MIN_ONE_LINE:
        return False
    palavras = without_period.split()
    ultima = _normalize(palavras[-1]).strip(",;:()[]") if palavras else ""
    return ultima not in _ABBREVIATIONS


def _normalize(texto: str) -> str:
    """Lowercase and without accents — searching for "área" finds "area" and vice versa."""
    unaccented = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in unaccented if not unicodedata.combining(c)).casefold()


def _search_fields(d: Any) -> str:
    return " ".join(
        str(valor or "")
        for valor in (
            getattr(d, "name", None),
            getattr(d, "alias", None),
            getattr(d, "type", None),
            _description_text(d),
        )
    )


def compact_index(
    defs: Iterable[Any], *, query: str | None = None, tipo: str | None = None
) -> list[dict]:
    """The filtered index, sorted by name.

    The `query` filter runs over name, nickname, type and description: whoever
    searches for "postgres" does not know the node is called `DatabaseQuery`.
    """
    alvo = _normalize(query) if query else None
    itens: list[dict] = []
    for d in defs:
        if tipo and str(getattr(d, "type", "") or "") != tipo:
            continue
        if alvo and alvo not in _normalize(_search_fields(d)):
            continue
        itens.append(
            {
                "name": getattr(d, "name", None),
                "type": getattr(d, "type", None),
                "one_line": one_line(d),
                "requires_credential": bool(getattr(d, "requires_credential", False)),
            }
        )
    return sorted(itens, key=lambda i: str(i["name"] or ""))


def catalog_types(defs: Iterable[Any]) -> list[dict]:
    """`[{type, count}]` — the map that tells where to filter before listing everything."""
    contagem: dict[str, int] = {}
    for d in defs:
        chave = str(getattr(d, "type", "") or "sem_tipo")
        contagem[chave] = contagem.get(chave, 0) + 1
    return [{"type": tipo, "count": n} for tipo, n in sorted(contagem.items())]


def _essential_property(p: Any) -> dict:
    """The minimum to configure the property — no label, help or visibility."""
    item: dict[str, Any] = {"name": getattr(p, "name", None), "type": getattr(p, "type", None)}
    # `required` does not exist in today's catalog; it is read via getattr so that
    # the day it starts to exist the information shows up without touching this.
    if getattr(p, "required", None):
        item["required"] = True
    default = getattr(p, "default", None)
    if default is not None:
        item["default"] = default
    opcoes = getattr(p, "options", None)
    if opcoes:
        item["options"] = [
            {"value": getattr(o, "value", None), "label": getattr(o, "label", None)}
            for o in opcoes
        ]
    credential_types = getattr(p, "credential_types", None)
    if credential_types:
        item["credential_types"] = list(credential_types)
    return item


def _hints(d: Any) -> list[str]:
    """What the sheet does not say per field and makes a difference when building the node."""
    dicas: list[str] = []
    if getattr(d, "dynamic_inputs", False):
        dicas.append(
            "As entradas deste nó são as que você declarar na propriedade `ports`; "
            "as arestas que chegam usam esses nomes em `to_key`."
        )
    if getattr(d, "outputs_from_ports", False):
        dicas.append(
            "As saídas deste nó são as que você declarar na propriedade `ports`; "
            "cada porta é um ponto de saída próprio, nomeado em `from_key`."
        )
    if getattr(d, "dynamic_output", False):
        dicas.append(
            "As saídas deste nó vêm da propriedade `output_vars`, e não dos "
            "`outputs` do catálogo."
        )
    for p in getattr(d, "properties", None) or []:
        porta = getattr(p, "suggest_columns", None)
        if not porta:
            continue
        origem = "de qualquer entrada" if porta == "*" else f"que chega pela porta `{porta}`"
        dicas.append(
            f"A propriedade `{getattr(p, 'name', '')}` espera o NOME DE UMA COLUNA do dado {origem}."
        )
    if getattr(d, "requires_credential", False):
        dicas.append(
            "Este nó exige credencial: passe o identificador de `list_credentials`, "
            "nunca a string de conexão ou o token em si."
        )
    source_kind = getattr(d, "source_kind", None)
    if source_kind:
        dicas.append(
            f"Este nó lê uma FONTE EXTERNA ({source_kind}): não invente `url`/`typeName`. "
            f"Consulte `search_sources(kind=\"{source_kind}\")` e cole o `node_snippet` de "
            "`describe_source`; fonte fora do catálogo → `probe_source` e `register_source`."
        )
    return dicas


def descrever(d: Any, *, brief: bool) -> dict:
    """The node's sheet — essential or complete, always with the hints at the end."""
    if not brief:
        # `NodeDefinition`'s own `model_dump`: the full sheet is what the
        # editor consumes, and copying it field by field here would create a second
        # definition of what a node is, doomed to fall behind.
        ficha = d.model_dump(exclude_none=True) if hasattr(d, "model_dump") else dict(d)
        ficha["hints"] = _hints(d)
        return ficha

    return {
        "name": getattr(d, "name", None),
        "type": getattr(d, "type", None),
        "description": _description_text(d) or None,
        "properties": [_essential_property(p) for p in getattr(d, "properties", None) or []],
        "inputs": [
            {"name": getattr(p, "name", None), "description": getattr(p, "description", None)}
            for p in getattr(d, "inputs", None) or []
        ],
        "outputs": [
            {
                "name": getattr(c, "name", None),
                "type": getattr(c, "type", None),
                "description": getattr(c, "description", None),
            }
            for c in getattr(d, "outputs", None) or []
        ],
        "requires_credential": bool(getattr(d, "requires_credential", False)),
        "hints": _hints(d),
    }
