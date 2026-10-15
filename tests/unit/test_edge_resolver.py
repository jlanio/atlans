# tests/unit/test_edge_resolver.py
"""
Single edge resolver (flow/executor/edge_resolver.py) — PR 1 of the spec
docs/specs/edge-data-contract.md.

Pins down the run's historical cascade AND guarantees that the schema simulation
resolves the SAME ports (the run × preview divergence was the central bug).
"""
import pytest

from flow.executor.edge_resolver import (
    Edge,
    resolve_edge_inputs,
    resolve_edge_schema_inputs,
)


# ── Edge.from_dict ────────────────────────────────────────────────────────────

def test_from_dict_basic():
    e = Edge.from_dict({"source": "a", "target": "b", "from_key": "x", "to_key": "y"})
    assert (e.source, e.target, e.from_key, e.to_key) == ("a", "b", "x", "y")
    assert e.is_branch is False


def test_from_dict_empty_string_becomes_none():
    # The run treated "" as absent (falsy). The model preserves that.
    e = Edge.from_dict({"source": "a", "target": "b", "from_key": "", "to_key": ""})
    assert e.from_key is None and e.to_key is None


def test_from_dict_condition_e_branch():
    assert Edge.from_dict({"source": "a", "target": "b", "condition": True}).is_branch
    assert Edge.from_dict({"source": "a", "target": "b", "condition": False}).is_branch
    # What is not a boolean in any spelling the validation accepts stays a data edge.
    for nao_e_ramo in ("", "maybe", 2, 0.5, None, [], {}):
        assert Edge.from_dict({"source": "a", "target": "b", "condition": nao_e_ramo}).is_branch is False


@pytest.mark.parametrize("escrito, ramo", [
    ("true", True), ("false", False), ("True", True), ("FALSE", False),
    ("yes", True), ("no", False), ("on", True), ("off", False),
    ("t", True), ("f", False), ("y", True), ("n", False),
    ("1", True), ("0", False), (1, True), (0, False), (1.0, True), (0.0, False),
])
def test_from_dict_condition_escrita_como_a_validacao_aceita(escrito, ramo):
    # The MCP validation (Pydantic's lax bool) reports these as a valid branch;
    # read as a data edge, the rejected branch ran too.
    e = Edge.from_dict({"source": "a", "target": "b", "condition": escrito})
    assert e.is_branch and e.condition is ramo


@pytest.mark.parametrize("handle, ramo", [("true", True), ("false", False)])
def test_from_dict_handle_de_ramo_sem_condition(handle, ramo):
    # The editor draws this edge on the branch handle (and writes `condition` on
    # its next save); the run has to route it the same way meanwhile.
    e = Edge.from_dict({"source": "a", "target": "b", "source_handle": handle})
    assert e.is_branch and e.condition is ramo
    lixo = Edge.from_dict({"source": "a", "target": "b", "source_handle": handle, "condition": "maybe"})
    assert lixo.condition is ramo


def test_from_dict_condition_valida_vence_o_handle():
    e = Edge.from_dict({"source": "a", "target": "b", "source_handle": "true", "condition": False})
    assert e.condition is False


def test_from_dict_handle_de_dado_nao_vira_ramo():
    e = Edge.from_dict({"source": "a", "target": "b", "source_handle": "output", "from_key": "output"})
    assert e.is_branch is False


# ── An edge the editor saved from a SubWorkflow port with the envelope as key ──

def test_porta_do_subfluxo_com_o_envelope_entrega_a_porta():
    # Dragged from port `r2`, the editor used to save `from_key:
    # "subWorkflowResult"` (its candidates did not know the child's ports): the
    # run delivered the dict of ALL the ports instead of r2.
    saida = {"subWorkflowResult": {"r1": 1, "r2": 2}, "r1": 1, "r2": 2}
    aresta = {"source": "sub", "target": "b", "source_handle": "r2", "from_key": "subWorkflowResult"}
    assert Edge.from_dict(aresta).from_key == "r2"
    assert resolve_edge_inputs(aresta, saida) == {"r2": 2}
    assert resolve_edge_inputs({**aresta, "to_key": "data"}, saida) == {"data": 2}


@pytest.mark.parametrize("aresta, chave", [
    # The envelope chosen on purpose is saved without a handle.
    ({"from_key": "subWorkflowResult"}, "subWorkflowResult"),
    ({"source_handle": "", "from_key": "subWorkflowResult"}, "subWorkflowResult"),
    ({"source_handle": "subWorkflowResult", "from_key": "subWorkflowResult"}, "subWorkflowResult"),
    # A port with a key of its own, a branch handle, a handle with no key.
    ({"source_handle": "r2", "from_key": "r1"}, "r1"),
    ({"source_handle": "true", "from_key": "subWorkflowResult"}, "subWorkflowResult"),
    ({"source_handle": "r2"}, None),
])
def test_so_o_par_porta_e_envelope_muda_de_chave(aresta, chave):
    assert Edge.from_dict({"source": "a", "target": "b", **aresta}).from_key == chave


# ── resolve_edge_inputs (run) ─────────────────────────────────────────────────

def test_from_key_found():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo"}, {"geo": 1, "n": 2})
    assert out == {"geo": 1}


def test_from_key_with_to_key_renames():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"}, {"geo": 1})
    assert out == {"layer": 1}


def test_from_key_missing_does_not_contribute():
    # STRICT: a from_key that does not exist in the parent's output NO LONGER falls
    # back to the "first value" (the blind guess that crossed data in the Switch
    # and injected None in the merge). The edge does not contribute.
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "nope"}, {"geo": 1, "n": 2})
    assert out == {}


def test_from_key_missing_triggers_warning():
    class _L:
        def __init__(self): self.calls = 0
        def warning(self, *a, **k): self.calls += 1
    log = _L()
    resolve_edge_inputs({"source": "a", "target": "b", "from_key": "nope"}, {"geo": 1},
                        logger=log, node_id="b", parent_id="a")
    assert log.calls == 1


def test_only_to_key_first_value():
    out = resolve_edge_inputs({"source": "a", "target": "b", "to_key": "layer"}, {"geo": 9, "n": 2})
    assert out == {"layer": 9}


def test_without_keys_spreads_everything():
    parent = {"geo": 1, "n": 2}
    out = resolve_edge_inputs({"source": "a", "target": "b"}, parent)
    assert out == {"geo": 1, "n": 2}
    out["geo"] = 99  # it is a copy — must not mutate the parent's output
    assert parent["geo"] == 1


def test_empty_parent_does_not_crash_or_contribute():
    # STRICT: an empty parent no longer injects None into a named port (F14). It
    # does not blow up and does not contribute — not in from_key mode, nor
    # to_key-only, nor spread.
    assert resolve_edge_inputs({"source": "a", "target": "b", "from_key": "x"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b", "to_key": "y"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b"}, {}) == {}


# ── resolve_edge_schema_inputs (simulation) ───────────────────────────────────

FIELDS = [{"name": "geo", "type": "geodataframe"}, {"name": "n", "type": "number"}]


def test_schema_from_key_found():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "geo"}, FIELDS)
    assert out == {"geo": "<geodataframe>"}


def test_schema_from_key_with_to_key():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"}, FIELDS)
    assert out == {"layer": "<geodataframe>"}


def test_schema_only_to_key_first_field():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "to_key": "layer"}, FIELDS)
    assert out == {"layer": "<geodataframe>"}


def test_schema_without_keys_spreads_all_fields():
    # Divergence regression: BEFORE, the simulation named by parent_id and set
    # ONE field; now it spreads ALL of them, as the run does.
    out = resolve_edge_schema_inputs({"source": "a", "target": "b"}, FIELDS)
    assert out == {"geo": "<geodataframe>", "n": "<number>"}


def test_schema_from_key_missing_does_not_contribute():
    # STRICT (mirrors the run): a from_key that is not a declared field of the
    # parent does not contribute — same as the run not finding the key. (/validate
    # flags the typo.)
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "nope"}, FIELDS)
    assert out == {}


def test_schema_empty_parent_does_not_contribute():
    # STRICT: with no declared fields, no port is named — same as the run, which
    # with an empty parent does not contribute either. Run × preview parity: {} == {}.
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b"}, []) == {}


# ── Run × simulation parity (the anti-divergence guarantee) ───────────────────

def _keys_run(edge, parent_values):
    return set(resolve_edge_inputs(edge, parent_values).keys())


def _sim_keys(edge, fields):
    return set(resolve_edge_schema_inputs(edge, fields).keys())


def test_port_parity_run_vs_sim():
    parent_values = {f["name"]: object() for f in FIELDS}
    for edge in [
        {"source": "a", "target": "b", "from_key": "geo"},
        {"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"},
        {"source": "a", "target": "b", "to_key": "layer"},
        {"source": "a", "target": "b"},                       # spread — the case that diverged
        {"source": "a", "target": "b", "from_key": "ausente"},
    ]:
        assert _keys_run(edge, parent_values) == _sim_keys(edge, FIELDS), edge


def test_port_parity_with_empty_parent():
    # STRICT: with the parent producing nothing, NEITHER of them names a port — run
    # and preview omit equally ({} == {}). Run × preview parity holds here too
    # (before, the run injected None and the preview <unknown>; now both omit).
    for edge in [
        {"source": "a", "target": "b", "from_key": "geo"},
        {"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"},
        {"source": "a", "target": "b", "to_key": "layer"},
        {"source": "a", "target": "b"},                       # spread — ambos vazios
    ]:
        assert _keys_run(edge, {}) == _sim_keys(edge, []), edge
