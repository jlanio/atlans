# tests/unit/test_docs_mcp.py
"""
`docs/mcp.md` nao envelhece em relacao ao que a tela e o servidor entregam.

Os snippets de conexao existem em dois lugares de proposito: a tela de criacao
de token (`CLIENTES`, em `create-token.tsx`) mostra o comando na hora em que o
segredo aparece, e o `docs/mcp.md` e a fonte unica para quem conecta depois.
Duplicacao e a escolha certa aqui — o usuario nao deveria precisar abrir o
outro lugar — mas duplicacao sem verificacao vira divergencia: o dia em que a
URL ou a forma do header mudar, um dos dois fica mentindo.

Entao este teste le o TSX com regex (nao ha runtime de TypeScript aqui) e exige
que cada snippet apareca *verbatim* no documento; que nenhum deles carregue um
segredo de verdade (`atl_pat_` + 43 chars — copiar um comando do documento nao
pode vazar token de ninguem); e que toda tool registrada em `app/mcp/guardas.py`
tenha uma linha na tabela de ferramentas do documento — o inverso nao e
verificado, porque o documento anuncia tools do PR seguinte marcadas como tal.

O exemplo de erro da secao "Erros" tambem e conferido contra o servidor: ele
cita o `hint` de `forbidden_scope` verbatim, e esse hint ja mandou qualquer um
"gerar um token em /settings/tokens" — pagina que so o administrador alcanca.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DOC = RAIZ / "docs" / "mcp.md"
TSX = RAIZ / "web" / "app" / "components" / "tokens" / "dialog-content" / "create-token.tsx"
GUARDAS = RAIZ / "app" / "mcp" / "guardas.py"

# `atl_pat_` seguido dos 43 chars urlsafe do segredo real (app/core/authorization/pat.py).
SEGREDO = re.compile(r"atl_pat_[A-Za-z0-9_-]{43}")

# Os snippets sao literais de string simples ou um JSON.stringify de um objeto
# literal; a tabela de tool -> guarda e um dict de `"nome": Guarda(...)`.
# O dominio de exemplo de docs/mcp.md: a tela usa o da instalacao.
URL_DO_DOC = "https://atlans.example.org/mcp"
_SNIPPET_SIMPLES = re.compile(r"^\s*snippet:\s*'([^']*)',\s*$", re.MULTILINE)
_ENTRADA_GUARDA = re.compile(r'^\s*"([a-z][a-z0-9_]*)"\s*:\s*Guarda\(', re.MULTILINE)
_LINHA_DE_TOOL = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|", re.MULTILINE)


def _doc() -> str:
    assert DOC.exists(), "docs/mcp.md sumiu — ajuste este teste junto"
    return DOC.read_text(encoding="utf-8")


def _snippets_da_tela() -> list[str]:
    """Os `snippet:` de `CLIENTES`, com as escapadas do TSX ja resolvidas.

    Os snippets da tela levam o marcador `URL_DO_MCP` (a tela o troca pela
    origem da pagina); o documento os traz com o dominio de exemplo `URL_DO_DOC`.
    O snippet do `mcp.json` nao e literal: e um `JSON.stringify(..., null, 2)`
    do mesmo objeto, reconstruido aqui para comparar com o bloco do documento sem
    depender de rodar JavaScript.
    """
    fonte = TSX.read_text(encoding="utf-8")
    marcador = re.search(r'export const URL_DO_MCP\s*=\s*"([^"]+)"', fonte)
    assert marcador, "URL_DO_MCP deixou de ser exportado de create-token.tsx"
    # Unica escapada possivel num literal de aspas simples do TSX.
    simples = [
        s.replace("\\'", "'").replace(marcador.group(1), URL_DO_DOC)
        for s in _SNIPPET_SIMPLES.findall(fonte)
    ]
    assert len(simples) >= 2, "os snippets literais de CLIENTES mudaram de forma — ajuste a regex"

    mcp_json = (
        "{\n"
        '  "mcpServers": {\n'
        '    "atlans": {\n'
        f'      "url": "{URL_DO_DOC}",\n'
        '      "headers": {\n'
        '        "Authorization": "Bearer ${ATLANS_TOKEN}"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    )
    return [*simples, mcp_json]


def test_cada_snippet_da_tela_aparece_no_documento():
    doc = _doc()
    faltando = [s for s in _snippets_da_tela() if s not in doc]
    assert not faltando, "snippet da tela que nao esta em docs/mcp.md:\n" + "\n\n".join(faltando)


def test_nenhum_snippet_carrega_um_segredo():
    """Comando copiado do documento (ou da tela) nunca pode vazar um token."""
    for origem, texto in (("docs/mcp.md", _doc()), ("create-token.tsx", TSX.read_text(encoding="utf-8"))):
        achados = SEGREDO.findall(texto)
        assert not achados, f"{origem} tem o que parece um segredo de PAT: {achados}"


def test_toda_tool_registrada_esta_na_tabela_do_documento():
    if not GUARDAS.exists():
        pytest.skip("app/mcp/guardas.py ainda nao existe — a tabela do doc sera conferida quando entrar")

    registradas = set(_ENTRADA_GUARDA.findall(GUARDAS.read_text(encoding="utf-8")))
    assert registradas, "GUARDAS deixou de ser um dict de `\"nome\": Guarda(...)` — ajuste a regex"

    documentadas = set(_LINHA_DE_TOOL.findall(_doc()))
    faltando = sorted(registradas - documentadas)
    assert not faltando, (
        "tool registrada em app/mcp/guardas.py sem linha na tabela de docs/mcp.md: " + ", ".join(faltando)
    )


def test_o_exemplo_de_erro_do_documento_e_o_que_o_servidor_devolve():
    """O bloco JSON de `forbidden_scope` do documento, byte a byte o do servidor."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo
    from tests.unit._mcp_harness import escopo_falso

    with pytest.raises(ToolError) as exc:
        exigir_escopo(escopo_falso(scopes={"workflows:read"}), "workflows:write")
    bloco = json.dumps(json.loads(str(exc.value)), ensure_ascii=False, indent=2)
    assert bloco in _doc(), "o exemplo de erro em docs/mcp.md divergiu do servidor:\n" + bloco
