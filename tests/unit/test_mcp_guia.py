# tests/unit/test_mcp_guia.py
"""
O guia de autoria — o conteúdo, não o transporte.

Este arquivo existe por uma razão só: o guia ENSINA a montar fluxo, e um guia
errado custa mais caro que código errado — quem o lê confia e reproduz. Então
o que é verificável fica verificado aqui: os oito tópicos existem e têm texto,
nenhum deles repete afirmação que já foi desmentida pelo servidor de hoje, e
cada receita é um fluxo que de fato passa no lint.

O lint (`flow/utils/definition_lint.py`) é o mesmo que o `/validate` roda antes
de simular. Uma receita com nome de nó errado, id duplicado ou ciclo seria
recusada pela plataforma — e estaria no guia, ensinando o erro.
"""
from __future__ import annotations

import json
import re

import pytest

import flow.nodes  # noqa: F401  (popula o NODE_REGISTRY)
from app.mcp import guia
from flow.registry import NODE_REGISTRY
from flow.utils.definition_lint import CHAVES_SECRETAS, lint_definition

# Blocos ```json ... ``` de um markdown.
_BLOCO_JSON = re.compile(r"```json\n(.*?)\n```", re.S)

# Frases que o servidor desmentiu e que não podem sobreviver num tópico:
# o nome de nó inexistente virou 422 estruturado (com `unknown_node` no
# relatório), e os scripts da skill foram substituídos pelas tools.
PROIBIDOS = ("HTTP 500", "validar.py", "catalogo.py")

# Teto por tópico. Não é estética: o guia é lido por chamada, e um tópico que
# não cabe numa leitura deixa de ser consultado.
LIMITE_BYTES = 8 * 1024


def _descritores() -> dict:
    return {nome: cls.description() for nome, cls in NODE_REGISTRY.items()}


def _blocos_json(texto: str) -> list[dict]:
    return [json.loads(bloco) for bloco in _BLOCO_JSON.findall(texto)]


def _valores_de_chave(valor, chave_alvo: str) -> list:
    """Todos os valores gravados sob `chave_alvo`, em qualquer profundidade."""
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


# ── Os nove tópicos ───────────────────────────────────────────────────────────


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
    # Um tópico precisa valer sozinho: título e mais de um parágrafo.
    assert texto.lstrip().startswith("#"), f"{topico} não começa por um título"
    assert len(texto) > 400, f"{topico} é curto demais para valer sozinho"
    assert len(texto.encode("utf-8")) <= LIMITE_BYTES, f"{topico} passou de {LIMITE_BYTES} bytes"


def test_topico_desconhecido_e_recusado_sem_tocar_no_disco():
    # O nome vem do cliente: montar `Path` com ele seria travessia de diretório.
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
    # Segredo de token pessoal: nem como exemplo.
    assert "atl_pat_" not in texto, f"{topico} carrega o prefixo de um token pessoal"
    # E nenhuma propriedade secreta preenchida dentro dos exemplos em JSON.
    for definicao in _blocos_json(texto):
        for chave in CHAVES_SECRETAS:
            preenchidos = [v for v in _valores_de_chave(definicao, chave) if v not in (None, "", {}, [])]
            assert not preenchidos, f"{topico} preenche '{chave}' num exemplo"


def test_overview_ensina_o_relatorio_estruturado():
    """O que substituiu a afirmação antiga sobre nome de nó inexistente."""
    texto = guia.ler_topico("overview")
    for codigo in ("unknown_node", "duplicate_node_id", "cycle", "invalid_credential_id"):
        assert codigo in texto
    assert "report.errors" in texto
    # E a regra de hoje sobre o formato de entrada.
    assert "`parameters`" in texto and "`properties`" in texto


def test_inputs_cobre_os_tres_caminhos_de_entrada():
    texto = guia.ler_topico("inputs")
    assert "params_schema" in texto
    assert "{{ inputs." in texto
    assert "payloadField" in texto
    assert "ports" in texto
    assert "suggested_params_schema" in texto


# ── As receitas ───────────────────────────────────────────────────────────────


def test_sao_cinco_receitas():
    texto = guia.ler_topico("recipes")
    titulos = re.findall(r"^## \d+\.", texto, re.M)
    assert len(titulos) == 5, f"esperava 5 receitas, achei {len(titulos)}"


def test_receitas_sao_json_valido_e_passam_no_lint():
    """A trava que impede o guia de ensinar fluxo quebrado.

    `lint_definition` é o mesmo lint do `/validate`. Um erro FATAL aqui é uma
    definição que a plataforma recusaria — exatamente o que não pode estar
    escrito no guia como exemplo a copiar.
    """
    texto = guia.ler_topico("recipes")
    definicoes = _blocos_json(texto)
    # Quatro receitas, e a do sub-fluxo traz as duas pontas (filho e pai).
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
        # Nem fatal nem não-fatal: uma receita é exemplo, sai limpa.
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
    """Credencial entra por id; um id que não é UUID é fatal no lint."""
    import uuid

    texto = guia.ler_topico("recipes")
    encontrados = 0
    for definicao in _blocos_json(texto):
        for valor in _valores_de_chave(definicao, "credential_id"):
            if valor in (None, ""):
                continue
            uuid.UUID(str(valor))  # levanta se não for UUID
            encontrados += 1
    assert encontrados >= 1, "nenhuma receita mostra o uso de credential_id"
