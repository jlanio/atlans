# tests/unit/test_mcp_guia.py
"""
The authoring guide — the content, not the transport.

This file exists for a single reason: the guide TEACHES how to build workflows,
and a wrong guide costs more than wrong code — whoever reads it trusts it and
reproduces it. So what is verifiable is verified here: the eight topics exist
and have text, none of them repeats a claim already disproven by today's
server, and every recipe is a workflow that actually passes the lint.

The lint (`flow/utils/definition_lint.py`) is the same one `/validate` runs
before simulating. A recipe with a wrong node name, a duplicate id or a cycle
would be refused by the platform — and would be in the guide, teaching the error.
"""
from __future__ import annotations

import json
import re

import pytest

import flow.nodes  # noqa: F401  (popula o NODE_REGISTRY)
from app.mcp import guia
from flow.registry import NODE_REGISTRY
from flow.utils.definition_lint import SECRET_KEYS, lint_definition

# ```json ... ``` blocks of a markdown document.
_JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)

# Sentences the server has disproven and that must not survive in a topic:
# a nonexistent node name became a structured 422 (with `unknown_node` in the
# report), and the skill's scripts were replaced by the tools.
FORBIDDEN = ("HTTP 500", "validar.py", "catalogo.py")

# Ceiling per topic. It is not aesthetics: the guide is read per call, and a
# topic that doesn't fit in one read stops being consulted.
BYTE_LIMIT = 8 * 1024


def _descriptors() -> dict:
    return {nome: cls.description() for nome, cls in NODE_REGISTRY.items()}


def _json_blocks(texto: str) -> list[dict]:
    return [json.loads(bloco) for bloco in _JSON_BLOCK.findall(texto)]


def _values_for_key(valor, target_key: str) -> list:
    """All values stored under `target_key`, at any depth."""
    achados: list = []
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            if str(chave).lower() == target_key.lower():
                achados.append(sub)
            achados.extend(_values_for_key(sub, target_key))
    elif isinstance(valor, list):
        for item in valor:
            achados.extend(_values_for_key(item, target_key))
    return achados


# ── The nine topics ───────────────────────────────────────────────────────────


def test_there_are_nine_topics_in_reading_order():
    assert guia.TOPICS == (
        "overview",
        "edges",
        "credentials",
        "expressions",
        "inputs",
        "sources",
        "sql",
        "pitfalls",
        "recipes",
    )


@pytest.mark.parametrize("topico", guia.TOPICS)
def test_topic_has_text_and_fits_in_one_read(topico):
    texto = guia.ler_topico(topico)
    assert texto.strip(), f"{topico} está vazio"
    # A topic must stand on its own: a title and more than one paragraph.
    assert texto.lstrip().startswith("#"), f"{topico} não começa por um título"
    assert len(texto) > 400, f"{topico} é curto demais para valer sozinho"
    assert len(texto.encode("utf-8")) <= BYTE_LIMIT, f"{topico} passou de {BYTE_LIMIT} bytes"


def test_unknown_topic_is_refused_without_touching_the_disk():
    # The name comes from the client: building a `Path` with it would be directory traversal.
    for entrada in ("inexistente", "../__init__", "/etc/passwd", ""):
        with pytest.raises(ValueError) as exc:
            guia.ler_topico(entrada)
        assert "Tópico desconhecido" in str(exc.value)


@pytest.mark.parametrize("topico", guia.TOPICS)
def test_topic_does_not_repeat_a_refuted_claim(topico):
    texto = guia.ler_topico(topico)
    for proibido in FORBIDDEN:
        assert proibido not in texto, f"{topico} ainda menciona {proibido!r}"


@pytest.mark.parametrize("topico", guia.TOPICS)
def test_topic_carries_no_secret(topico):
    texto = guia.ler_topico(topico)
    # A personal token's secret: not even as an example.
    assert "atl_pat_" not in texto, f"{topico} carrega o prefixo de um token pessoal"
    # And no secret property filled in inside the JSON examples.
    for definicao in _json_blocks(texto):
        for chave in SECRET_KEYS:
            preenchidos = [v for v in _values_for_key(definicao, chave) if v not in (None, "", {}, [])]
            assert not preenchidos, f"{topico} preenche '{chave}' num exemplo"


def test_overview_teaches_the_structured_report():
    """What replaced the old claim about a nonexistent node name."""
    texto = guia.ler_topico("overview")
    for codigo in ("unknown_node", "duplicate_node_id", "cycle", "invalid_credential_id"):
        assert codigo in texto
    assert "report.errors" in texto
    # And today's rule about the input format.
    assert "`parameters`" in texto and "`properties`" in texto


def test_inputs_covers_the_three_input_paths():
    texto = guia.ler_topico("inputs")
    assert "params_schema" in texto
    assert "{{ inputs." in texto
    assert "payloadField" in texto
    assert "ports" in texto
    assert "suggested_params_schema" in texto


# ── The recipes ───────────────────────────────────────────────────────────────


def test_there_are_five_recipes():
    texto = guia.ler_topico("recipes")
    titulos = re.findall(r"^## \d+\.", texto, re.M)
    assert len(titulos) == 5, f"esperava 5 receitas, achei {len(titulos)}"


def test_recipes_are_valid_json_and_pass_the_lint():
    """The lock that keeps the guide from teaching a broken workflow.

    `lint_definition` is the same lint as `/validate`. A FATAL error here is a
    definition the platform would refuse — exactly what must not be written in
    the guide as an example to copy.
    """
    texto = guia.ler_topico("recipes")
    definitions = _json_blocks(texto)
    # Four recipes, and the sub-workflow one carries both ends (child and parent).
    assert len(definitions) >= 4

    nomes = set(NODE_REGISTRY)
    descritores = _descriptors()
    for indice, definicao in enumerate(definitions, start=1):
        assert definicao.get("nodes"), f"receita {indice} sem nós"
        relatorio = lint_definition(
            definicao["nodes"],
            definicao.get("edges") or [],
            registry_names=nomes,
            descriptors=descritores,
        )
        fatais = [d.code for d in relatorio.errors if d.fatal]
        assert not fatais, f"receita {indice} tem erro fatal: {fatais}"
        # Neither fatal nor non-fatal: a recipe is an example, it comes out clean.
        assert not relatorio.errors, (
            f"receita {indice}: {[(d.code, d.message) for d in relatorio.errors]}"
        )


def test_recipes_only_reference_catalog_nodes():
    texto = guia.ler_topico("recipes")
    nomes = set(NODE_REGISTRY)
    for definicao in _json_blocks(texto):
        for no in definicao["nodes"]:
            assert no["name"] in nomes, f"nó '{no['name']}' não existe no catálogo"


def test_recipes_use_credential_id_as_uuid():
    """A credential goes in by id; an id that is not a UUID is fatal in the lint."""
    import uuid

    texto = guia.ler_topico("recipes")
    encontrados = 0
    for definicao in _json_blocks(texto):
        for valor in _values_for_key(definicao, "credential_id"):
            if valor in (None, ""):
                continue
            uuid.UUID(str(valor))  # raises if it is not a UUID
            encontrados += 1
    assert encontrados >= 1, "nenhuma receita mostra o uso de credential_id"
