# tests/unit/test_nos_de_saida_usam_helpers_da_base.py
"""
Output nodes and the helpers BaseNode already offers.

`BaseNode.require_execution_context()` and `BaseNode.derive_label()` exist
precisely for the output nodes, and `save_geojson` already used them — it was
the proven model. The others reimplemented both by hand, verbatim.

Besides that, `save_to_shapefile` and `save_to_geoparquet` carried an
`if tamanho > 10MB: fileobj else: content` branch with ~12 duplicated lines and
the comment "streaming para arquivos grandes" (streaming for large files). The
branch was a NO-OP: `persistir_artefato` does `content = fileobj.read()` on BOTH
paths (executor and MinIO), so the two halves produced exactly the same result.
The comment described a behavior that never existed.

What this test also protects: the difference in `save_to_s3`, which CANNOT be
unified.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SAIDAS = RAIZ / "flow" / "nodes" / "outputs"

# Nodes that resolve workspace_id/task_id (the ones that save an artifact).
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
    """Anchors the contract: the nodes unpack `(workspace_id, task_id)`."""
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
    """The difference that prevents unification.

    `save_to_s3` derives the label from the S3 KEY, not from an outputPath, and
    falls back to `'s3_export'` when the basename comes out empty (a key ending
    in '/', for example). `derive_label` has no such fallback: it raises
    ValueError. If someone "unifies" this node, a key without a basename starts
    bringing down the execution instead of saving the artifact.
    """
    fonte = _fonte("save_to_s3")
    assert "'s3_export'" in fonte, (
        "o fallback de save_to_s3 sumiu — derive_label levantaria ValueError "
        "onde antes havia um nome padrao"
    )


# ── The no-op branch ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("modulo", ["save_to_shapefile", "save_to_geoparquet"])
def test_o_ramo_de_10mb_nao_voltou(modulo):
    fonte = _fonte(modulo)
    assert "10 * 1024 * 1024" not in fonte, (
        f"{modulo}: o ramo `if tamanho > 10MB` voltou — ele e no-op, "
        "persistir_artefato le o fileobj inteiro nos dois caminhos"
    )


@pytest.mark.parametrize("modulo", ["save_to_shapefile", "save_to_geoparquet"])
def test_persistir_artefato_e_chamado_UMA_vez(modulo):
    """Two calls with the same arguments and the duplicated branch back.

    Persistence now runs in `asyncio.to_thread(persistir_artefato, ...)`
    (moves the blocking upload off the event loop), so `persistir_artefato`
    appears as an ARGUMENT, not as a Call's `func`. What is counted is the
    REFERENCE to the name (just one; the import is an `ast.alias`, not an
    `ast.Name`), which still proves there is exactly one persistence — not the
    two of the size-based branch.
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
    """The premise that makes the removed branch a no-op.

    If one of the paths starts doing real streaming upload, the branch makes
    sense again — and this test warns that the premise changed.
    """
    fonte = (RAIZ / "flow" / "utils" / "artifact_helpers.py").read_text(encoding="utf-8")
    ocorrencias = fonte.count("content = fileobj.read()")
    assert ocorrencias >= 2, (
        "artifact_helpers deixou de ler o fileobj inteiro em algum caminho — "
        "reavalie se o ramo por tamanho volta a ser necessario"
    )
