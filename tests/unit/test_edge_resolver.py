# tests/unit/test_edge_resolver.py
"""
Single edge resolver (flow/executor/edge_resolver.py) — PR 1 of the spec
docs/specs/edge-data-contract.md.

Pins down the run's historical cascade AND guarantees that the schema simulation
resolves the SAME ports (the run × preview divergence was the central bug).
"""
from flow.executor.edge_resolver import (
    Edge,
    resolve_edge_inputs,
    resolve_edge_schema_inputs,
)


# ── Edge.from_dict ────────────────────────────────────────────────────────────

def test_from_dict_basico():
    e = Edge.from_dict({"source": "a", "target": "b", "from_key": "x", "to_key": "y"})
    assert (e.source, e.target, e.from_key, e.to_key) == ("a", "b", "x", "y")
    assert e.is_branch is False


def test_from_dict_string_vazia_vira_none():
    # The run treated "" as absent (falsy). The model preserves that.
    e = Edge.from_dict({"source": "a", "target": "b", "from_key": "", "to_key": ""})
    assert e.from_key is None and e.to_key is None


def test_from_dict_condition_e_branch():
    assert Edge.from_dict({"source": "a", "target": "b", "condition": True}).is_branch
    assert Edge.from_dict({"source": "a", "target": "b", "condition": False}).is_branch
    # a non-bool condition is ignored (does not become a branch).
    assert Edge.from_dict({"source": "a", "target": "b", "condition": "true"}).is_branch is False


# ── resolve_edge_inputs (run) ─────────────────────────────────────────────────

def test_from_key_achado():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo"}, {"geo": 1, "n": 2})
    assert out == {"geo": 1}


def test_from_key_com_to_key_renomeia():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"}, {"geo": 1})
    assert out == {"layer": 1}


def test_from_key_ausente_nao_contribui():
    # STRICT: a from_key that does not exist in the parent's output NO LONGER falls
    # back to the "first value" (the blind guess that crossed data in the Switch
    # and injected None in the merge). The edge does not contribute.
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "nope"}, {"geo": 1, "n": 2})
    assert out == {}


def test_from_key_ausente_dispara_warning():
    class _L:
        def __init__(self): self.calls = 0
        def warning(self, *a, **k): self.calls += 1
    log = _L()
    resolve_edge_inputs({"source": "a", "target": "b", "from_key": "nope"}, {"geo": 1},
                        logger=log, node_id="b", parent_id="a")
    assert log.calls == 1


def test_so_to_key_primeiro_valor():
    out = resolve_edge_inputs({"source": "a", "target": "b", "to_key": "layer"}, {"geo": 9, "n": 2})
    assert out == {"layer": 9}


def test_sem_chaves_espalha_tudo():
    parent = {"geo": 1, "n": 2}
    out = resolve_edge_inputs({"source": "a", "target": "b"}, parent)
    assert out == {"geo": 1, "n": 2}
    out["geo"] = 99  # it is a copy — must not mutate the parent's output
    assert parent["geo"] == 1


def test_parent_vazio_nao_estoura_e_nao_contribui():
    # STRICT: an empty parent no longer injects None into a named port (F14). It
    # does not blow up and does not contribute — not in from_key mode, nor
    # to_key-only, nor spread.
    assert resolve_edge_inputs({"source": "a", "target": "b", "from_key": "x"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b", "to_key": "y"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b"}, {}) == {}


# ── resolve_edge_schema_inputs (simulation) ───────────────────────────────────

FIELDS = [{"name": "geo", "type": "geodataframe"}, {"name": "n", "type": "number"}]


def test_schema_from_key_achado():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "geo"}, FIELDS)
    assert out == {"geo": "<geodataframe>"}


def test_schema_from_key_com_to_key():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"}, FIELDS)
    assert out == {"layer": "<geodataframe>"}


def test_schema_so_to_key_primeiro_campo():
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "to_key": "layer"}, FIELDS)
    assert out == {"layer": "<geodataframe>"}


def test_schema_sem_chaves_espalha_todos_os_campos():
    # Divergence regression: BEFORE, the simulation named by parent_id and set
    # ONE field; now it spreads ALL of them, as the run does.
    out = resolve_edge_schema_inputs({"source": "a", "target": "b"}, FIELDS)
    assert out == {"geo": "<geodataframe>", "n": "<number>"}


def test_schema_from_key_ausente_nao_contribui():
    # STRICT (mirrors the run): a from_key that is not a declared field of the
    # parent does not contribute — same as the run not finding the key. (/validate
    # flags the typo.)
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "nope"}, FIELDS)
    assert out == {}


def test_schema_parent_vazio_nao_contribui():
    # STRICT: with no declared fields, no port is named — same as the run, which
    # with an empty parent does not contribute either. Run × preview parity: {} == {}.
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b"}, []) == {}


# ── Run × simulation parity (the anti-divergence guarantee) ───────────────────

def _keys_run(edge, parent_values):
    return set(resolve_edge_inputs(edge, parent_values).keys())


def _keys_sim(edge, fields):
    return set(resolve_edge_schema_inputs(edge, fields).keys())


def test_paridade_de_portas_run_vs_sim():
    parent_values = {f["name"]: object() for f in FIELDS}
    for edge in [
        {"source": "a", "target": "b", "from_key": "geo"},
        {"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"},
        {"source": "a", "target": "b", "to_key": "layer"},
        {"source": "a", "target": "b"},                       # spread — the case that diverged
        {"source": "a", "target": "b", "from_key": "ausente"},
    ]:
        assert _keys_run(edge, parent_values) == _keys_sim(edge, FIELDS), edge


def test_paridade_de_portas_com_pai_vazio():
    # STRICT: with the parent producing nothing, NEITHER of them names a port — run
    # and preview omit equally ({} == {}). Run × preview parity holds here too
    # (before, the run injected None and the preview <unknown>; now both omit).
    for edge in [
        {"source": "a", "target": "b", "from_key": "geo"},
        {"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"},
        {"source": "a", "target": "b", "to_key": "layer"},
        {"source": "a", "target": "b"},                       # spread — ambos vazios
    ]:
        assert _keys_run(edge, {}) == _keys_sim(edge, []), edge
