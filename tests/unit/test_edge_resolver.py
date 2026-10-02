# tests/unit/test_edge_resolver.py
"""
Resolvedor único da aresta (flow/executor/edge_resolver.py) — PR 1 da spec
docs/specs/edge-data-contract.md.

Fixa a cascata histórica do run E garante que a simulação de schema resolve as
MESMAS portas (a divergência run × preview era o bug central).
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
    # O run tratava "" como ausente (falsy). O modelo preserva isso.
    e = Edge.from_dict({"source": "a", "target": "b", "from_key": "", "to_key": ""})
    assert e.from_key is None and e.to_key is None


def test_from_dict_condition_e_branch():
    assert Edge.from_dict({"source": "a", "target": "b", "condition": True}).is_branch
    assert Edge.from_dict({"source": "a", "target": "b", "condition": False}).is_branch
    # condition não-bool é ignorado (não vira ramo).
    assert Edge.from_dict({"source": "a", "target": "b", "condition": "true"}).is_branch is False


# ── resolve_edge_inputs (run) ─────────────────────────────────────────────────

def test_from_key_achado():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo"}, {"geo": 1, "n": 2})
    assert out == {"geo": 1}


def test_from_key_com_to_key_renomeia():
    out = resolve_edge_inputs({"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"}, {"geo": 1})
    assert out == {"layer": 1}


def test_from_key_ausente_nao_contribui():
    # STRICT: from_key que não existe no output do pai NÃO cai mais no "primeiro
    # valor" (o palpite cego que cruzava dados no Switch e injetava None no merge).
    # A aresta não contribui.
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
    out["geo"] = 99  # é cópia — não pode mutar o output do pai
    assert parent["geo"] == 1


def test_parent_vazio_nao_estoura_e_nao_contribui():
    # STRICT: pai vazio não injeta mais None em porta nomeada (F14). Não estoura
    # e não contribui — nem no modo from_key, nem no só-to_key, nem no spread.
    assert resolve_edge_inputs({"source": "a", "target": "b", "from_key": "x"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b", "to_key": "y"}, {}) == {}
    assert resolve_edge_inputs({"source": "a", "target": "b"}, {}) == {}


# ── resolve_edge_schema_inputs (simulação) ────────────────────────────────────

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
    # Regressão da divergência: ANTES a simulação nomeava por parent_id e punha
    # UM campo; agora espalha TODOS, como o run faz.
    out = resolve_edge_schema_inputs({"source": "a", "target": "b"}, FIELDS)
    assert out == {"geo": "<geodataframe>", "n": "<number>"}


def test_schema_from_key_ausente_nao_contribui():
    # STRICT (espelha o run): from_key que não é campo declarado do pai não
    # contribui — igual ao run que não acha a chave. (O /validate sinaliza o typo.)
    out = resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "nope"}, FIELDS)
    assert out == {}


def test_schema_parent_vazio_nao_contribui():
    # STRICT: sem campos declarados, nenhuma porta é nomeada — igual ao run, que
    # com pai vazio também não contribui. Paridade run × preview: {} == {}.
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "from_key": "x", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b", "to_key": "y"}, []) == {}
    assert resolve_edge_schema_inputs({"source": "a", "target": "b"}, []) == {}


# ── Paridade run × simulação (a garantia anti-divergência) ────────────────────

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
        {"source": "a", "target": "b"},                       # spread — o caso que divergia
        {"source": "a", "target": "b", "from_key": "ausente"},
    ]:
        assert _keys_run(edge, parent_values) == _keys_sim(edge, FIELDS), edge


def test_paridade_de_portas_com_pai_vazio():
    # STRICT: com o pai sem produzir nada, NENHUM dos dois nomeia porta — run e
    # preview omitem igualmente ({} == {}). A paridade run × preview vale também
    # aqui (antes o run injetava None e o preview <unknown>; agora ambos omitem).
    for edge in [
        {"source": "a", "target": "b", "from_key": "geo"},
        {"source": "a", "target": "b", "from_key": "geo", "to_key": "layer"},
        {"source": "a", "target": "b", "to_key": "layer"},
        {"source": "a", "target": "b"},                       # spread — ambos vazios
    ]:
        assert _keys_run(edge, {}) == _keys_sim(edge, []), edge
