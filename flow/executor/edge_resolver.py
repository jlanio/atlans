# flow/executor/edge_resolver.py
"""
Single edge resolver: given ONE edge and the source node's output, decides
what goes into the target node.

The SINGLE source of edge semantics. This logic used to be duplicated in two
places in flow/executor/core.py — the run's input assembly and the schema
simulation — which diverged in the "no keys" case (the run spread everything; the
simulation named by parent_id). Centralizing it here kills the run × preview divergence.
See docs/specs/edge-data-contract.md (PR 1).

Modes (strict — no blind guessing):
  - from_key present → {to_key or from_key: value} if the key exists in the output;
    if it does NOT exist, the edge does not contribute ({}) — never the "first value"
    (which crossed data from the wrong bucket in Switch and injected None into merges).
  - only to_key       → {to_key: 1st value} (rename; empty parent → does not contribute)
  - neither           → spreads all of the parent's outputs (whole dict)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping


# The spellings of a boolean the MCP validation accepts (Pydantic's lax `bool`,
# `validate_service.EdgeDefinition`). Only a JSON `true`/`false` used to count
# here: `"condition": "false"` passed validation as a valid branch, was saved as
# written and ran as a DATA edge — the rejected branch ran too.
_RAMO_VERDADEIRO = frozenset({"true", "t", "yes", "y", "on", "1"})
_RAMO_FALSO = frozenset({"false", "f", "no", "n", "off", "0"})


def condicao_do_ramo(cond: Any) -> bool | None:
    """`condition` as a branch: True/False, or None for a data edge."""
    if isinstance(cond, bool):
        return cond
    if isinstance(cond, str):
        texto = cond.lower()
        if texto in _RAMO_VERDADEIRO:
            return True
        if texto in _RAMO_FALSO:
            return False
        return None
    if isinstance(cond, (int, float)) and cond in (0, 1):
        return bool(cond)
    return None


# The SubWorkflow node's envelope output: the dict of ALL the child's ports
# (`RESULT_KEY` in flow/nodes/control/sub_workflow.py).
_ENVELOPE_DO_SUBFLUXO = "subWorkflowResult"


def from_key_efetiva(d: Mapping[str, Any]) -> str | None:
    """The `from_key` an edge really means.

    The editor used to save an edge dragged from a SubWorkflow's port `r2` with
    the port as `source_handle` and the envelope as `from_key` — its candidate
    list did not know the child's ports — and the run delivered the dict of ALL
    the ports instead of r2. The handle is what the person pulled, so that pair
    reads as the port: the same reading as the editor's `chaveEfetiva`
    (web/app/components/workflow/utils/edge-persistence.ts), which writes
    `from_key: r2` on the next save. The envelope chosen on purpose is saved
    without a handle and is left alone, as are the branch handles.
    """
    from_key = d.get("from_key") or None
    handle = d.get("source_handle")
    if (
        from_key == _ENVELOPE_DO_SUBFLUXO
        and isinstance(handle, str) and handle
        and handle not in (_ENVELOPE_DO_SUBFLUXO, "true", "false")
    ):
        return handle
    return from_key


@dataclass(frozen=True)
class Edge:
    """Typed view of an edge. `condition` is the branch routing of control
    nodes — orthogonal to the data mapping."""
    source: str
    target: str
    from_key: str | None = None
    to_key: str | None = None
    condition: bool | None = None

    @property
    def is_branch(self) -> bool:
        return self.condition is not None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Edge":
        cond = condicao_do_ramo(d.get("condition"))
        handle = d.get("source_handle")
        if cond is None and handle in ("true", "false"):
            # The branch handle with no usable `condition`. The editor draws
            # such an edge on that branch (`resolveSourceHandle`) and writes the
            # `condition` back on its next save; until then the run has to route
            # it the way the canvas shows it, not run it on both branches.
            cond = handle == "true"
        elif cond is not None and isinstance(handle, str) and handle and handle not in ("true", "false"):
            # Leaving a NAMED port it is a data edge, whatever `condition` says:
            # the editor once wrote `condition: false` on every edge leaving a
            # named handle (`sourceHandle === "true"` with sourceHandle "body"),
            # and the canvas draws those edges on their port. Read as a branch,
            # a source whose output has a boolean `branch` switched it off.
            cond = None
        # `or None` normalizes "" (falsy, treated as absent by the run) to None,
        # preserving the truthiness semantics of the original code.
        return cls(
            source=d["source"],
            target=d["target"],
            from_key=from_key_efetiva(d),
            to_key=d.get("to_key") or None,
            condition=cond,
        )


def _first_value(parent_outputs: Mapping[str, Any]) -> Any:
    return next(iter(parent_outputs.values()), None)


def resolve_edge_inputs(
    edge: "Mapping[str, Any] | Edge",
    parent_outputs: Mapping[str, Any],
    *,
    logger: Any = None,
    node_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """Inputs that THIS edge injects into the target node.

    Always returns a dict — mapped mode: {port: value}; spread mode: a shallow
    copy of the parent's output. The caller applies it with `inputs.update(resultado)`,
    which is identical to the previous `inputs[k] = v` / `inputs.update(parent_outputs)`.
    """
    e = edge if isinstance(edge, Edge) else Edge.from_dict(edge)

    if e.from_key:
        if e.from_key in parent_outputs:
            return {e.to_key or e.from_key: parent_outputs[e.from_key]}
        # from_key is not in the parent's output. NO longer falls back to the "first value"
        # (the blind guess that made a Switch with an empty bucket cross data from the
        # wrong bucket — F5, and a skipped parent inject None into the merge — F14). The
        # edge simply does NOT contribute. Flagging a stale from_key (typo) is the
        # job of static validation (`validate_service`), not of the run.
        if logger is not None:
            logger.warning(
                "[%s] from_key '%s' não encontrado no output de '%s' "
                "(keys: %s). A aresta não contribui.",
                node_id, e.from_key, parent_id, list(parent_outputs.keys()),
            )
        return {}

    if e.to_key:
        # to_key without from_key: rename of the parent's output. Sub-workflow contract
        # (source with no candidates → multi-port node). Empty parent → does not contribute.
        return {e.to_key: _first_value(parent_outputs)} if parent_outputs else {}

    return dict(parent_outputs)


def resolve_edge_schema_inputs(
    edge: "Mapping[str, Any] | Edge",
    parent_fields: List[Mapping[str, Any]],
) -> dict:
    """Mirror of `resolve_edge_inputs` on the SCHEMA plane (simulation/preview).

    `parent_fields`: list of {name, type} of the parent's declared/simulated output.
    Returns {port: "<type>"} on the SAME ports the run would produce — same
    strict semantics, keeping run × preview parity:
      - from_key that IS a declared field → {port: <type>};
      - from_key that is NOT a declared field → the edge does not contribute ({}), just
        like the run that does not find the key in the output. (Static validation
        flags the stale from_key from here.)
    """
    e = edge if isinstance(edge, Edge) else Edge.from_dict(edge)

    def _typed(f: Mapping[str, Any]) -> str:
        return f"<{f.get('type')}>"

    if e.from_key:
        match = next((f for f in parent_fields if f.get("name") == e.from_key), None)
        return {e.to_key or e.from_key: _typed(match)} if match is not None else {}

    if e.to_key:
        return {e.to_key: _typed(parent_fields[0])} if parent_fields else {}

    return {f["name"]: _typed(f) for f in parent_fields if f.get("name")}
