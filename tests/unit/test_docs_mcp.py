# tests/unit/test_docs_mcp.py
"""
`docs/mcp.md` does not go stale relative to what the screen and the server deliver.

The connection snippets exist in two places on purpose: the token creation
screen (`CLIENTES`, in `create-token.tsx`) shows the command at the moment the
secret appears, and `docs/mcp.md` is the single source for whoever connects
later. Duplication is the right choice here — the user should not need to open
the other place — but duplication without verification becomes divergence: the
day the URL or the header shape changes, one of the two is lying.

So this test reads the TSX with regex (there is no TypeScript runtime here) and
requires each snippet to appear *verbatim* in the document; that none of them
carries a real secret (`atl_pat_` + 43 chars — copying a command from the
document must not leak anyone's token); and that every tool registered in
`app/mcp/guardas.py` has a row in the document's tools table — the reverse is not
checked, because the document announces tools from the next PR marked as such.

The error example in the "Errors" section is also checked against the server: it
quotes the `hint` of `forbidden_scope` verbatim, and that hint once sent everyone
to "gerar um token em /settings/tokens" (generate a token at /settings/tokens) —
a page only the administrator can reach.
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

# `atl_pat_` followed by the real secret's 43 urlsafe chars (app/core/authorization/pat.py).
SEGREDO = re.compile(r"atl_pat_[A-Za-z0-9_-]{43}")

# The snippets are plain string literals or a JSON.stringify of an object
# literal; the tool -> guard table is a dict of `"nome": Guarda(...)`.
# The example domain of docs/mcp.md: the screen uses the installation's.
URL_DO_DOC = "https://atlans.example.org/mcp"
_SNIPPET_SIMPLES = re.compile(r"^\s*snippet:\s*'([^']*)',\s*$", re.MULTILINE)
_ENTRADA_GUARDA = re.compile(r'^\s*"([a-z][a-z0-9_]*)"\s*:\s*Guarda\(', re.MULTILINE)
_LINHA_DE_TOOL = re.compile(r"^\|\s*`([a-z][a-z0-9_]*)`\s*\|", re.MULTILINE)


def _doc() -> str:
    assert DOC.exists(), "docs/mcp.md sumiu — ajuste este teste junto"
    return DOC.read_text(encoding="utf-8")


def _snippets_da_tela() -> list[str]:
    """The `snippet:` entries of `CLIENTES`, with the TSX escapes already resolved.

    The screen's snippets carry the `URL_DO_MCP` marker (the screen replaces it
    with the page's origin); the document has them with the example domain
    `URL_DO_DOC`. The `mcp.json` snippet is not a literal: it is a
    `JSON.stringify(..., null, 2)` of the same object, rebuilt here to compare
    with the document's block without depending on running JavaScript.
    """
    fonte = TSX.read_text(encoding="utf-8")
    marcador = re.search(r'export const URL_DO_MCP\s*=\s*"([^"]+)"', fonte)
    assert marcador, "URL_DO_MCP deixou de ser exportado de create-token.tsx"
    # The only possible escape in a single-quoted TSX literal.
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
    """A command copied from the document (or the screen) can never leak a token."""
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
    """The document's `forbidden_scope` JSON block, byte for byte the server's."""
    from mcp.server.mcpserver.exceptions import ToolError

    from app.mcp.escopo import exigir_escopo
    from tests.unit._mcp_harness import escopo_falso

    with pytest.raises(ToolError) as exc:
        exigir_escopo(escopo_falso(scopes={"workflows:read"}), "workflows:write")
    bloco = json.dumps(json.loads(str(exc.value)), ensure_ascii=False, indent=2)
    assert bloco in _doc(), "o exemplo de erro em docs/mcp.md divergiu do servidor:\n" + bloco
