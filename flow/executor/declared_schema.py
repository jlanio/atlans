# flow/executor/declared_schema.py
"""A node's outputs DECLARED in its own definition, without executing anything.

A node with `dynamic_output` and no `simulate()` silently vanished from
/workflows/validate (8 catalog nodes), and the schema panel had nothing to show —
even when the real outputs are written in the payload: PythonScript's
`output_vars`, Switch's `fallback_output` + `rules[].output`, SubWorkflowInput's
`ports`. This module reads those declarations and returns the schema in the
simulation's canonical format: `[{"fields": [{"name", "type"}, ...]}]`.

Pure: only stdlib and flow.utils.workflow_contract (also pure).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from flow.utils.workflow_contract import _parse_ports


def _campos(nomes: list) -> list:
    """List of names → grouped form; the type is "any" because only the run knows it."""
    return [{"fields": [{"name": nome, "type": "any"} for nome in nomes]}]


def _output_vars(bruto: Any) -> list:
    """`output_vars` exactly as the run treats it: `validate()` requires a string
    and PythonScript rejects the empty list — with the SAME messages, so that
    validation flags what the run would flag. Previously, empty became schema `[]`
    with `ok`, and with no known outputs the edge diagnostics were switched off."""
    if not isinstance(bruto, str):
        raise ValueError("O parâmetro 'output_vars' deve ser uma string.")
    nomes = [item.strip() for item in bruto.split(",") if item.strip()]
    if not nomes:
        raise ValueError("'output_vars' deve conter ao menos um nome de variável.")
    return nomes


def _regras(bruto: Any) -> list:
    """Switch's `rules`: native list or JSON serialized by the editor.
    Anything unreadable becomes an empty list — the lint, not this, flags it."""
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except (ValueError, TypeError):
            return []
    if not isinstance(bruto, list):
        return []
    return [regra for regra in bruto if isinstance(regra, dict)]


def _e_saida_utilizavel(campo: Any) -> bool:
    """Internal protocol keys (`__response__`, `__artifact__`) are not
    outputs an edge can consume — the executor strips them from what the node
    delivers. Same filter as the catalog (app/services/node_service.py)."""
    if not isinstance(campo, dict):
        return False
    nome = campo.get("name")
    return isinstance(nome, str) and bool(nome) and not nome.startswith("__")


def schema_do_catalogo(desc: dict) -> list:
    """The descriptor's `outputs` (typed fields) in the simulation's grouped form.

    The catalog declares the fields in a flat list `[{"name", "type", ...}]`;
    simulate()'s canonical format is still grouped, so the conversion lives
    here — in one place only."""
    campos = [c for c in (desc.get("outputs") or []) if _e_saida_utilizavel(c)]
    return [{"fields": campos}]


def schema_declarado(node_def: dict, desc: dict) -> Optional[list]:
    """Output schema that the definition + the descriptor allow us to assert.

    Order of precedence, from the most specific declaration to the most generic:
      1. `output_vars` (PythonScript): each variable is an output;
      2. `rules` + `fallback_output` (Switch): the fallback and the rules' outputs,
         which is exactly what the run emits (all of them, even empty ones);
      3. `outputs_from_ports` (SubWorkflowInput): each port is an output;
      4. the descriptor's `outputs` (the catalog's typed fields);
      5. None — nothing to assert (the caller decides what to do).

    Raises ValueError, with the message the run would use, when the declaration is
    invalid (`output_vars` empty or non-string, `fallback_output` non-string).

    `parameters` is the validation body's format; `properties` is the saved
    definition's — same tolerance as simulate_runner.
    """
    params = node_def.get("parameters") or node_def.get("properties") or {}
    if not isinstance(params, dict):
        params = {}
    props = {
        prop.get("name")
        for prop in (desc.get("properties") or [])
        if isinstance(prop, dict)
    }

    if "output_vars" in props:
        return _campos(_output_vars(params.get("output_vars", "result")))

    if "rules" in props and "fallback_output" in props:
        # Espelha switch.py: `parameters.get("fallback_output", "output_0")` —
        # chave ausente cai no default; presente e vazia emite a porta ''.
        fallback = params.get("fallback_output", "output_0")
        if not isinstance(fallback, str):
            raise ValueError("O parâmetro 'fallback_output' deve ser uma string.")
        saidas = [fallback]
        for regra in _regras(params.get("rules")):
            saida = regra.get("output")
            if isinstance(saida, str) and saida and saida not in saidas:
                saidas.append(saida)
        return _campos(saidas)

    if desc.get("outputs_from_ports"):
        portas = _parse_ports(params.get("ports"))
        if portas:
            return _campos(portas)

    if desc.get("outputs") is not None:
        return schema_do_catalogo(desc)

    return None
