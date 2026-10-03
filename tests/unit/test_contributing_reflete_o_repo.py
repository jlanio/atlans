# tests/unit/test_contributing_reflete_o_repo.py
"""
The CONTRIBUTING file tree describes the actual repository.

The `worker -> agent -> executor` rename stopped halfway: the code became
`executor_*`, and CONTRIBUTING kept documenting `agent_*` files that no longer
exist. On top of that, the tree once cited `flow/executor.py` — a file that
does not exist (the engine became the `flow/executor/` package).

This is not cosmetic. CONTRIBUTING is the first place a newcomer looks for
"where is the job dispatch"; a map pointing to nonexistent files costs that
person their trust in the rest of the document.

The test rebuilds the PATH of each `.py` from the indentation of the ASCII
drawing and requires it to exist at that path. The previous version only
compared the basename against a `**/nome.py` glob, so `flow/executor.py`
(nonexistent) passed because `app/models/executor.py` has the same basename — a
false positive that masked precisely the kind of error the test should catch. It
does not validate the reverse (a file with no mention): the tree is a curated
summary, not an `ls`.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "CONTRIBUTING.md"

# Branch markers of the tree drawing; each indentation level before them
# takes 4 columns ("│   " or "    ").
_GALHO = re.compile(r"[├└]── ")


def _arquivos_com_caminho() -> list[tuple[int, str]]:
    """(line, path relative to the root) of each `.py` cited in the trees.

    Rebuilds the directory by stacking the directory nodes (which end in `/`)
    by indentation depth, so that the full path — not just the basename — is
    checked. CONTRIBUTING has more than one tree: the main one (root
    `atlans/`, = repo root) and the tests one (root `tests/`). A `nome/` line
    with no branch and no indentation is the root of a tree and sets the prefix
    of the following paths: a folder that exists at the repo root (`tests/`)
    becomes the prefix; any other name (`atlans/`) is the repo itself. Not by
    the clone folder's name: CI clones into a folder named after the repository,
    and a repository with another name (a fork, the public copy) would break
    the test.
    """
    achados: list[tuple[int, str]] = []
    pilha: dict[int, str] = {}  # profundidade -> nome do diretorio naquele nivel
    base = ""                   # prefix of the current (sub)tree
    for i, linha in enumerate(DOC.read_text(encoding="utf-8").splitlines(), 1):
        m = _GALHO.search(linha)
        if not m:
            # Root of a (sub)tree: a bare `nome/`, with no branch and no indentation.
            token = re.split(r"\s{2,}|#", linha, maxsplit=1)[0]
            if re.fullmatch(r"[A-Za-z0-9_]+/", token):
                nome_raiz = token.rstrip("/")
                base = nome_raiz if (RAIZ / nome_raiz).is_dir() else ""
                pilha = {}
            continue
        profundidade = m.start() // 4
        # item name: first token after the branch, before any comment
        # (the drawing uses double spaces or `#` for each line's comments).
        nome = re.split(r"\s{2,}|#", linha[m.end():], maxsplit=1)[0].strip()
        if nome.endswith("/"):
            pilha[profundidade] = nome.rstrip("/")
            for d in [d for d in pilha if d > profundidade]:
                del pilha[d]
        elif nome.endswith(".py"):
            partes = ([base] if base else []) + [pilha[d] for d in sorted(pilha) if d < profundidade] + [nome]
            achados.append((i, "/".join(partes)))
    return achados


def test_todo_arquivo_py_citado_na_arvore_existe():
    arquivos = _arquivos_com_caminho()
    assert arquivos, "a arvore de diretorios do CONTRIBUTING sumiu — ajuste este teste"

    faltando = [
        f"CONTRIBUTING.md:{linha} cita {caminho}, que nao existe"
        for linha, caminho in arquivos
        if not (RAIZ / caminho).exists()
    ]

    assert not faltando, (
        "o mapa do CONTRIBUTING aponta para arquivos inexistentes:\n  "
        + "\n  ".join(faltando)
    )


def test_o_vocabulario_agent_nao_voltou_ao_documento():
    """`agent` was the middle name in a rename already completed in the code.

    Keeping it in the document makes the reader search for a vocabulary the
    repository has abandoned.
    """
    problemas = [
        f"CONTRIBUTING.md:{i} — {linha.strip()}"
        for i, linha in enumerate(DOC.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\bagents?_[a-z]+\.py\b", linha)
    ]
    assert not problemas, (
        "nome de arquivo com o prefixo `agent_` de volta ao CONTRIBUTING; "
        "o codigo usa `executor_`:\n  " + "\n  ".join(problemas)
    )
