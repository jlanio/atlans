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
from flow.utils.definition_lint import CHAVES_SECRETAS, lint_definition

# ```json ... ``` blocks of a markdown document.
_BLOCO_JSON = re.compile(r"```json\n(.*?)\n```", re.S)

# Sentences the server has disproven and that must not survive in a topic:
# a nonexistent node name became a structured 422 (with `unknown_node` in the
# report), and the skill's scripts were replaced by the tools.
PROIBIDOS = ("HTTP 500", "validar.py", "catalogo.py")

# Ceiling per topic. It is not aesthetics: the guide is read per call, and a
# topic that doesn't fit in one read stops being consulted.
LIMITE_BYTES = 8 * 1024


def _descritores() -> dict:
    return {nome: cls.description() for nome, cls in NODE_REGISTRY.items()}


def _blocos_json(texto: str) -> list[dict]:
    return [json.loads(bloco) for bloco in _BLOCO_JSON.findall(texto)]


def _valores_de_chave(valor, chave_alvo: str) -> list:
    """All values stored under `chave_alvo`, at any depth."""
    achados: list = []
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            if str(chave).lower() == chave_alvo.lower():
                achados.append(sub)
            achados.extend(_valores_de_chave(sub, chave_alvo))
    elif isinstance(valor, list):
        for item in valor:
            achados.extend(_valores_de_chave(item, chave_alvo))
    return achados


# ── The nine topics ───────────────────────────────────────────────────────────


def test_sao_nove_topicos_na_ordem_de_leitura():
    assert guia.TOPICOS == (
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


@pytest.mark.parametrize("topico", guia.TOPICOS)
def test_topico_tem_texto_e_cabe_numa_leitura(topico):
    texto = guia.ler_topico(topico)
    assert texto.strip(), f"{topico} está vazio"
    # A topic must stand on its own: a title and more than one paragraph.
    assert texto.lstrip().startswith("#"), f"{topico} não começa por um título"
    assert len(texto) > 400, f"{topico} é curto demais para valer sozinho"
    assert len(texto.encode("utf-8")) <= LIMITE_BYTES, f"{topico} passou de {LIMITE_BYTES} bytes"


def test_topico_desconhecido_e_recusado_sem_tocar_no_disco():
    # The name comes from the client: building a `Path` with it would be directory traversal.
    for entrada in ("inexistente", "../__init__", "/etc/passwd", ""):
        with pytest.raises(ValueError) as exc:
            guia.ler_topico(entrada)
        assert "Tópico desconhecido" in str(exc.value)


@pytest.mark.parametrize("topico", guia.TOPICOS)
def test_topico_nao_repete_afirmacao_desmentida(topico):
    texto = guia.ler_topico(topico)
    for proibido in PROIBIDOS:
        assert proibido not in texto, f"{topico} ainda menciona {proibido!r}"


@pytest.mark.parametrize("topico", guia.TOPICOS)
def test_topico_nao_carrega_segredo(topico):
    texto = guia.ler_topico(topico)
    # A personal token's secret: not even as an example.
    assert "atl_pat_" not in texto, f"{topico} carrega o prefixo de um token pessoal"
    # And no secret property filled in inside the JSON examples.
    for definicao in _blocos_json(texto):
        for chave in CHAVES_SECRETAS:
            preenchidos = [v for v in _valores_de_chave(definicao, chave) if v not in (None, "", {}, [])]
            assert not preenchidos, f"{topico} preenche '{chave}' num exemplo"


def test_overview_ensina_o_relatorio_estruturado():
    """What replaced the old claim about a nonexistent node name."""
    texto = guia.ler_topico("overview")
    for codigo in ("unknown_node", "duplicate_node_id", "cycle", "invalid_credential_id"):
        assert codigo in texto
    assert "report.errors" in texto
    # And today's rule about the input format.
    assert "`parameters`" in texto and "`properties`" in texto


def test_inputs_cobre_os_tres_caminhos_de_entrada():
    texto = guia.ler_topico("inputs")
    assert "params_schema" in texto
    assert "{{ inputs." in texto
    assert "payloadField" in texto
    assert "ports" in texto
    assert "suggested_params_schema" in texto


# ── The recipes ───────────────────────────────────────────────────────────────


def test_sao_cinco_receitas():
    texto = guia.ler_topico("recipes")
    titulos = re.findall(r"^## \d+\.", texto, re.M)
    assert len(titulos) == 5, f"esperava 5 receitas, achei {len(titulos)}"


def test_receitas_sao_json_valido_e_passam_no_lint():
    """The lock that keeps the guide from teaching a broken workflow.

    `lint_definition` is the same lint as `/validate`. A FATAL error here is a
    definition the platform would refuse — exactly what must not be written in
    the guide as an example to copy.
    """
    texto = guia.ler_topico("recipes")
    definicoes = _blocos_json(texto)
    # Four recipes, and the sub-workflow one carries both ends (child and parent).
    assert len(definicoes) >= 4

    nomes = set(NODE_REGISTRY)
    descritores = _descritores()
    for indice, definicao in enumerate(definicoes, start=1):
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


def test_receitas_so_referenciam_nos_do_catalogo():
    texto = guia.ler_topico("recipes")
    nomes = set(NODE_REGISTRY)
    for definicao in _blocos_json(texto):
        for no in definicao["nodes"]:
            assert no["name"] in nomes, f"nó '{no['name']}' não existe no catálogo"


def test_receitas_usam_credential_id_como_uuid():
    """A credential goes in by id; an id that is not a UUID is fatal in the lint."""
    import uuid

    texto = guia.ler_topico("recipes")
    encontrados = 0
    for definicao in _blocos_json(texto):
        for valor in _valores_de_chave(definicao, "credential_id"):
            if valor in (None, ""):
                continue
            uuid.UUID(str(valor))  # raises if it is not a UUID
            encontrados += 1
    assert encontrados >= 1, "nenhuma receita mostra o uso de credential_id"
