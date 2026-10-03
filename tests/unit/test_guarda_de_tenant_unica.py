# tests/unit/test_guarda_de_tenant_unica.py
"""
Single point for the workspace membership guard.

`verify_workspace_access` exists in app/api/dependencies.py and was already used by
four routers. Two others — drive and artifacts — reimplemented the same
check by hand, ten times:

    if wf.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

Copying is not just ugliness. The variation between the copies is what let through
the artifact download with an expired token: one path checked expiration, the other
did not, and nobody compared the two. As long as the guard is copied, the next
authorization fix will apply to a subset of the places.

This test locks in the consolidation. It does NOT require every comparison with
workspace_ids to disappear — two survive on purpose and are listed in
EXCECOES, each with its reason.
"""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Comparisons with workspace_ids that are NOT the guard and must remain.
EXCECOES = {
    # Batch deletion loop: the message names WHICH artifact was denied, which
    # the generic helper does not do. Losing that would leave the user not knowing
    # which item in the batch blocked the operation.
    ("app/api/routers/artifacts_router.py", "batch_delete_artifacts"),
    # Batch filter in the Drive: `continue`, not `raise`. Skipping someone else's file
    # and carrying on with the rest is the intended behavior — raising 403 here
    # would bring down the whole deletion because of one item.
    ("app/services/drive_service.py", "batch_delete_files"),
}

ARQUIVOS = [
    "app/core/authorization/workflow_access.py",
    "app/api/routers/drive_router.py",
    "app/api/routers/artifacts_router.py",
    "app/api/routers/workflow_groups_router.py",
    "app/api/routers/credentials_router.py",
    "app/api/routers/workflows_router.py",
    "app/services/drive_service.py",
]


def _enclosing_function(arvore, linha: int) -> str:
    melhor = "<modulo>"
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.lineno <= linha <= (no.end_lineno or no.lineno):
                melhor = no.name
    return melhor


def test_the_tenant_guard_is_not_reimplemented_by_hand():
    violacoes = []
    for rel in ARQUIVOS:
        caminho = RAIZ / rel
        if not caminho.exists():
            continue
        fonte = caminho.read_text(encoding="utf-8")
        arvore = ast.parse(fonte, rel)
        for i, linha in enumerate(fonte.splitlines(), 1):
            if "not in workspace_ids" not in linha:
                continue
            funcao = _enclosing_function(arvore, i)
            if (rel, funcao) in EXCECOES:
                continue
            violacoes.append(f"{rel}:{i} em {funcao}() — {linha.strip()}")

    assert not violacoes, (
        "guarda de tenant reimplementada a mao; use "
        "app.api.dependencies.verify_workspace_access (ou registre a excecao "
        "com o motivo, se o comportamento for mesmo diferente):\n  "
        + "\n  ".join(violacoes)
    )


def test_the_registered_exceptions_still_exist():
    """If an exception disappears, it must leave the list — otherwise the test loosens
    silently and starts allowing a new copy in the same place."""
    for rel, funcao in EXCECOES:
        fonte = (RAIZ / rel).read_text(encoding="utf-8")
        arvore = ast.parse(fonte, rel)
        nomes = {
            no.name for no in ast.walk(arvore)
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert funcao in nomes, f"{rel}: {funcao}() sumiu — remova a excecao"


def test_no_workspace_ids_depends_is_left_unused():
    """The parameter costs one SQL query per request.

    Five workflow_groups routes declared it and never read it. It was not a hole —
    all of them check the role (today via `require_workspace_role`), which is a
    strict superset of the check — but it was one query per request for nothing,
    and an unused authorization `Depends` gives the impression that the route is
    protected by it.
    """
    violacoes = []
    for rel in ARQUIVOS:
        caminho = RAIZ / rel
        if not caminho.exists():
            continue
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), rel)
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = [a.arg for a in no.args.args + no.args.kwonlyargs]
            if "workspace_ids" not in params:
                continue
            usado = any(
                isinstance(n, ast.Name) and n.id == "workspace_ids"
                and isinstance(n.ctx, ast.Load)
                for n in ast.walk(no)
            )
            if not usado:
                violacoes.append(f"{rel}:{no.lineno} {no.name}()")

    assert not violacoes, (
        "Depends(get_user_workspace_ids) declarado e nunca lido — uma query SQL "
        "por request para nada:\n  " + "\n  ".join(violacoes)
    )
