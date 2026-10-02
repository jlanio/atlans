# tests/unit/test_guarda_de_tenant_unica.py
"""
Ponto unico da guarda de pertencimento a workspace.

`verify_workspace_access` existe em app/api/dependencies.py e ja era usada por
quatro routers. Outros dois — drive e artifacts — reimplementavam a mesma
checagem a mao, dez vezes:

    if wf.workspace_id not in workspace_ids:
        raise HTTPException(status_code=403, detail="Acesso negado.")

Copia nao e so feiura. A variacao entre as copias foi o que deixou passar o
download de artefato com token expirado: um caminho conferia expiracao, o outro
nao, e ninguem comparava os dois. Enquanto a guarda for copiada, a proxima
correcao de autorizacao vai valer para um subconjunto dos lugares.

Este teste trava a consolidacao. Ele NAO exige que toda comparacao com
workspace_ids desapareca — duas sobrevivem de proposito e estao listadas em
EXCECOES, cada uma com o motivo.
"""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Comparacoes com workspace_ids que NAO sao a guarda e devem permanecer.
EXCECOES = {
    # Laco de exclusao em lote: a mensagem nomeia QUAL artefato foi negado, o
    # que o helper generico nao faz. Perder isso deixaria o usuario sem saber
    # qual item do lote barrou a operacao.
    ("app/api/routers/artifacts_router.py", "batch_delete_artifacts"),
    # Filtro de lote no Drive: `continue`, nao `raise`. Pular um arquivo alheio
    # e seguir com o resto e comportamento pretendido — levantar 403 aqui
    # derrubaria a exclusao inteira por causa de um item.
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


def _funcao_que_contem(arvore, linha: int) -> str:
    melhor = "<modulo>"
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if no.lineno <= linha <= (no.end_lineno or no.lineno):
                melhor = no.name
    return melhor


def test_a_guarda_de_tenant_nao_e_reimplementada_a_mao():
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
            funcao = _funcao_que_contem(arvore, i)
            if (rel, funcao) in EXCECOES:
                continue
            violacoes.append(f"{rel}:{i} em {funcao}() — {linha.strip()}")

    assert not violacoes, (
        "guarda de tenant reimplementada a mao; use "
        "app.api.dependencies.verify_workspace_access (ou registre a excecao "
        "com o motivo, se o comportamento for mesmo diferente):\n  "
        + "\n  ".join(violacoes)
    )


def test_as_excecoes_registradas_ainda_existem():
    """Se uma excecao sumir, ela tem de sair da lista — senao o teste afrouxa
    em silencio e passa a permitir uma copia nova no mesmo lugar."""
    for rel, funcao in EXCECOES:
        fonte = (RAIZ / rel).read_text(encoding="utf-8")
        arvore = ast.parse(fonte, rel)
        nomes = {
            no.name for no in ast.walk(arvore)
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert funcao in nomes, f"{rel}: {funcao}() sumiu — remova a excecao"


def test_nenhum_depends_de_workspace_ids_fica_sem_uso():
    """O parametro custa uma query SQL por request.

    Cinco rotas de workflow_groups o declaravam e nunca liam. Nao era furo —
    todas conferem o papel (hoje por `exigir_papel_no_workspace`), que e
    superconjunto estrito da checagem — mas era uma query por request para nada,
    e um `Depends` de autorizacao sem uso passa a impressao de que a rota esta
    protegida por ele.
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
