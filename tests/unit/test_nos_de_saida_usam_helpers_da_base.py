# tests/unit/test_nos_de_saida_usam_helpers_da_base.py
"""
Nos de saida e os helpers que a BaseNode ja oferece.

`BaseNode.require_execution_context()` e `BaseNode.derive_label()` existem
justamente para os nos de saida, e `save_geojson` ja os usava — era o modelo
comprovado. Os outros reimplementavam os dois na mao, verbatim.

Alem disso, `save_to_shapefile` e `save_to_geoparquet` carregavam um ramo
`if tamanho > 10MB: fileobj else: content` com ~12 linhas duplicadas e o
comentario "streaming para arquivos grandes". O ramo era um NO-OP:
`persistir_artefato` faz `content = fileobj.read()` nos DOIS caminhos (executor
e MinIO), entao as duas metades produziam exatamente o mesmo resultado. O
comentario descrevia um comportamento que nunca existiu.

O que este teste tambem protege: a diferenca de `save_to_s3`, que NAO pode ser
unificada.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SAIDAS = RAIZ / "flow" / "nodes" / "outputs"

# Nos que resolvem workspace_id/task_id (os que gravam artefato).
COM_CONTEXTO = ["save_to_shapefile", "save_to_geoparquet", "save_to_s3", "data_output", "carta_imagem"]


def _fonte(modulo: str) -> str:
    return (SAIDAS / f"{modulo}.py").read_text(encoding="utf-8")


# ── require_execution_context ────────────────────────────────────────────────

@pytest.mark.parametrize("modulo", COM_CONTEXTO)
def test_contexto_de_execucao_vem_do_helper(modulo):
    fonte = _fonte(modulo)
    assert "require_execution_context()" in fonte, (
        f"{modulo} deixou de usar o helper da BaseNode"
    )
    assert 'raise RuntimeError("workspace_id nao injetado' not in fonte, (
        f"{modulo} voltou a reimplementar a checagem de contexto"
    )
    assert 'raise RuntimeError("task_id nao injetado' not in fonte, (
        f"{modulo} voltou a reimplementar a checagem de contexto"
    )


def test_o_helper_continua_devolvendo_os_dois_valores():
    """Ancora o contrato: os nos desempacotam `(workspace_id, task_id)`."""
    from flow.nodes.base import BaseNode

    fonte = inspect.getsource(BaseNode.require_execution_context)
    assert "return workspace_id, task_id" in fonte


# ── derive_label ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modulo", ["save_to_shapefile", "save_to_geoparquet"])
def test_label_vem_do_helper(modulo):
    fonte = _fonte(modulo)
    assert "self.derive_label(" in fonte, f"{modulo} deixou de usar derive_label"
    assert "os.path.splitext(os.path.basename(output_path))" not in fonte, (
        f"{modulo} voltou a derivar o label na mao"
    )


def test_save_to_s3_NAO_usa_derive_label_e_isso_e_proposital():
    """A diferenca que impede a unificacao.

    `save_to_s3` deriva o label da CHAVE S3, nao de um outputPath, e cai num
    fallback `'s3_export'` quando o basename sai vazio (chave terminada em '/',
    por exemplo). `derive_label` nao tem esse fallback: levanta ValueError. Se
    alguem "unificar" este no, uma chave sem basename passa a derrubar a
    execucao em vez de gravar o artefato.
    """
    fonte = _fonte("save_to_s3")
    assert "'s3_export'" in fonte, (
        "o fallback de save_to_s3 sumiu — derive_label levantaria ValueError "
        "onde antes havia um nome padrao"
    )


# ── O ramo no-op ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("modulo", ["save_to_shapefile", "save_to_geoparquet"])
def test_o_ramo_de_10mb_nao_voltou(modulo):
    fonte = _fonte(modulo)
    assert "10 * 1024 * 1024" not in fonte, (
        f"{modulo}: o ramo `if tamanho > 10MB` voltou — ele e no-op, "
        "persistir_artefato le o fileobj inteiro nos dois caminhos"
    )


@pytest.mark.parametrize("modulo", ["save_to_shapefile", "save_to_geoparquet"])
def test_persistir_artefato_e_chamado_UMA_vez(modulo):
    """Duas chamadas com os mesmos argumentos e o ramo duplicado de volta.

    A persistencia agora roda em `asyncio.to_thread(persistir_artefato, ...)`
    (tira o upload bloqueante do event loop), entao `persistir_artefato` aparece
    como ARGUMENTO, nao como `func` de um Call. Conta-se a REFERENCIA ao nome
    (uma so; o import e um `ast.alias`, nao um `ast.Name`), que segue provando
    que ha exatamente uma persistencia — nao as duas do ramo por tamanho.
    """
    arvore = ast.parse(_fonte(modulo))
    usos = [
        n for n in ast.walk(arvore)
        if isinstance(n, ast.Name) and n.id == "persistir_artefato"
        and isinstance(n.ctx, ast.Load)
    ]
    assert len(usos) == 1, (
        f"{modulo}: {len(usos)} usos de persistir_artefato — esperado 1"
    )


def test_persistir_artefato_le_o_fileobj_nos_dois_caminhos():
    """A premissa que torna o ramo removido um no-op.

    Se um dos caminhos passar a fazer upload em streaming de verdade, o ramo
    volta a fazer sentido — e este teste avisa que a premissa mudou.
    """
    fonte = (RAIZ / "flow" / "utils" / "artifact_helpers.py").read_text(encoding="utf-8")
    ocorrencias = fonte.count("content = fileobj.read()")
    assert ocorrencias >= 2, (
        "artifact_helpers deixou de ler o fileobj inteiro em algum caminho — "
        "reavalie se o ramo por tamanho volta a ser necessario"
    )
