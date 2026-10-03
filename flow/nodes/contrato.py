# flow/nodes/contrato.py
"""The contract of a node's description() — closed vocabularies and validation.

The `type` field accumulated three roles with mixed vocabularies and none of
them validated: the node's CATEGORY, the output FIELD TYPE and the PROPERTY
TYPE (form widget). A typo in any of them passed silently through import and
became a visual defect far from the cause — a node without an icon, a field
without an editor, a port without a type.

Here the three vocabularies become closed sets, and `validar_description`
runs at import (via `register_node`): a malformed node dies in CI with the
sentence pointing to the field, not on the screen.
"""
from typing import Any

# Node category — decides the palette, the icon and the grouping in the editor.
CATEGORIAS = frozenset({"trigger", "action", "spatial", "datasource", "output", "control"})

# Type of the DATA that leaves through an `outputs` field (not a UI widget).
TIPOS_DE_CAMPO = frozenset({"geodataframe", "string", "number", "boolean", "object", "list", "any"})

# Type of a property — the editor form's WIDGET. `integer` is not a
# synonym of `number`: the form rounds and uses step=1 (numeric-field.tsx).
TIPOS_DE_PROPRIEDADE = frozenset({
    "string", "number", "integer", "boolean", "object", "select", "chips",
    "credential", "keyvalue", "code", "ports", "drive", "artifact", "sql",
})

# Every key a description() may have. A key outside the set is almost
# always a typo (`output` for `outputs`) — and a typo here breaks nothing
# right away: the field simply stops existing for the editor and for validate.
CHAVES_DO_DESCRIPTION = frozenset({
    "name", "alias", "description", "type", "properties", "outputs", "inputs",
    "dynamic_inputs", "dynamic_output", "outputs_from_ports", "branches",
    "requires_credential", "source_kind",
})

CHAVES_DE_PROPRIEDADE = frozenset({
    "name", "label", "type", "default", "description", "credential_types",
    "drive_extensions", "options", "visibleWhen", "suggest_columns",
    "required", "placeholder",
})


# Names that once existed in the catalog and where they went. The 07/27 rename
# (commit ff11c196, "app em dev, sem shim") did not migrate saved workflows: a
# workflow with `DriveTrigger` failed every day at startup with "Node 'DriveTrigger'
# não encontrado". Who reads this: `python -m app.cli migrar-nos` (which rewrites
# the saved definitions) and the unknown-node messages from the lint and the factory,
# which now say where the node went instead of just that it doesn't exist.
# Renaming a node from now on = a new entry here, in the same commit.
NOMES_ANTIGOS: dict[str, str] = {
    "DriveTrigger": "DataInput",
    "ArtifactOutput": "DataOutput",
}


# Nodes that left the catalog with no replacement, and why. The executor builds
# all nodes before the run — including those of a branch that won't run —, so
# a saved workflow with one of them stops running entirely: the message has to
# say the node was removed, and not suggest a typo.
NOS_REMOVIDOS: dict[str, str] = {
    "Cluster": (
        "dependia do scikit-learn, que nenhuma instalação do executor traz, e "
        "falhava em todo run"
    ),
}


def dica_de_no_desconhecido(nome: str) -> str:
    """Addendum to the unknown-node message (renamed or removed);
    empty if the name never existed."""
    novo = NOMES_ANTIGOS.get(nome)
    if novo:
        return (
            f" Este nó foi renomeado para '{novo}': troque-o no editor, ou peça ao "
            "administrador para rodar `python -m app.cli migrar-nos --aplicar`."
        )
    motivo = NOS_REMOVIDOS.get(nome)
    if motivo:
        return f" Este nó saiu do catálogo ({motivo}): tire-o do fluxo no editor."
    return ""


def _erro(nome: str, msg: str) -> ValueError:
    return ValueError(f"description() de '{nome}': {msg}")


def validar_description(desc: Any) -> None:
    """Validates a complete description(). Raises ValueError with the exact cause.

    Runs at import of the node's module (register_node), so the cost is paid
    once per process — and a malformed node never reaches the registry.
    """
    if not isinstance(desc, dict):
        raise ValueError(f"description() deve devolver dict, não {type(desc).__name__}.")

    nome = desc.get("name")
    if not isinstance(nome, str) or not nome or " " in nome:
        raise ValueError(f"description() sem 'name' válido (sem espaços): {nome!r}.")

    estranhas = set(desc) - CHAVES_DO_DESCRIPTION
    if estranhas:
        raise _erro(nome, f"chaves desconhecidas {sorted(estranhas)} — typo? "
                          f"Aceitas: {sorted(CHAVES_DO_DESCRIPTION)}.")

    categoria = desc.get("type")
    if categoria not in CATEGORIAS:
        raise _erro(nome, f"'type' (categoria) inválido: {categoria!r}. "
                          f"Aceitos: {sorted(CATEGORIAS)}.")

    props = desc.get("properties")
    if not isinstance(props, list):
        raise _erro(nome, "'properties' deve ser uma lista (mesmo vazia).")
    for p in props:
        if not isinstance(p, dict) or not p.get("name"):
            raise _erro(nome, f"propriedade sem 'name': {p!r}.")
        estranhas = set(p) - CHAVES_DE_PROPRIEDADE
        if estranhas:
            raise _erro(nome, f"propriedade '{p['name']}' com chaves desconhecidas "
                              f"{sorted(estranhas)}.")
        tipo = p.get("type")
        if tipo not in TIPOS_DE_PROPRIEDADE:
            raise _erro(nome, f"propriedade '{p['name']}' com type inválido: {tipo!r}. "
                              f"Aceitos: {sorted(TIPOS_DE_PROPRIEDADE)}.")
        if tipo == "select" and not p.get("options"):
            raise _erro(nome, f"propriedade '{p['name']}' é select sem 'options'.")
        if tipo == "credential" and not p.get("credential_types"):
            raise _erro(nome, f"propriedade '{p['name']}' é credential sem 'credential_types'.")
        if p.get("required") is not None and not isinstance(p["required"], bool):
            raise _erro(nome, f"propriedade '{p['name']}': 'required' deve ser bool.")
        if p.get("placeholder") is not None and not isinstance(p["placeholder"], str):
            raise _erro(nome, f"propriedade '{p['name']}': 'placeholder' deve ser string.")

    saidas = desc.get("outputs")
    if saidas is not None:
        if not isinstance(saidas, list):
            raise _erro(nome, "'outputs' deve ser uma lista de campos.")
        for c in saidas:
            if not isinstance(c, dict) or not c.get("name"):
                raise _erro(nome, f"campo de saída sem 'name': {c!r}.")
            tipo = c.get("type")
            if tipo not in TIPOS_DE_CAMPO:
                raise _erro(nome, f"campo de saída '{c['name']}' com type inválido: {tipo!r}. "
                                  f"Aceitos: {sorted(TIPOS_DE_CAMPO)}.")
            estranhas = set(c) - {"name", "type", "description", "port"}
            if estranhas:
                raise _erro(nome, f"campo de saída '{c['name']}' com chaves desconhecidas "
                                  f"{sorted(estranhas)}.")

    entradas = desc.get("inputs")
    if entradas is not None:
        if not isinstance(entradas, list):
            raise _erro(nome, "'inputs' deve ser uma lista de portas.")
        for p in entradas:
            if not isinstance(p, dict) or not p.get("name"):
                raise _erro(nome, f"porta de entrada sem 'name': {p!r}.")
            tipo = p.get("type")
            if tipo is not None and tipo not in TIPOS_DE_CAMPO:
                raise _erro(nome, f"porta de entrada '{p['name']}' com type inválido: {tipo!r}. "
                                  f"Aceitos: {sorted(TIPOS_DE_CAMPO)}.")
            estranhas = set(p) - {"name", "type", "description"}
            if estranhas:
                raise _erro(nome, f"porta de entrada '{p['name']}' com chaves desconhecidas "
                                  f"{sorted(estranhas)}.")

    for flag in ("dynamic_inputs", "dynamic_output", "outputs_from_ports",
                 "branches", "requires_credential"):
        valor = desc.get(flag)
        if valor is not None and not isinstance(valor, bool):
            raise _erro(nome, f"'{flag}' deve ser bool, não {type(valor).__name__}.")
