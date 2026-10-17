"""Every tool the assistant's model can call has a label on the panel's timeline.

The timeline shows `toolLabel(nome)` (`web/app/components/home/assistente/rotulos.ts`),
and a name missing from its table goes to the screen raw. The table
(`web/app/components/home/i18n/secoes/assistente.ts`, `ferramentas`) is kept by
hand, and nothing checked it against the tools: `desenhar_no_canvas`, the editor's
own tool, is not an MCP tool and was left out, so its step read
"desenhar_no_canvas" in the middle of a conversation in Portuguese.

The tools come from where the model gets them: every MCP tool (`GUARDAS`) and the
local tools of each surface (`ferramentas_extras`). The table is read with regex
(there is no TypeScript runtime here), in its three languages. The reverse is not
checked: the table may name tools the model never reaches (see `rotulos.ts`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.mcp.guardas import GUARDAS
from app.services.assistente_service import EDITOR
from app.services.assistente_superficie import HOME

RAIZ = Path(__file__).resolve().parents[2]
DICIONARIO = RAIZ / "web" / "app" / "components" / "home" / "i18n" / "secoes" / "assistente.ts"
IDIOMAS = ("pt", "en", "es")


def _ferramentas_do_modelo() -> set[str]:
    return set(GUARDAS) | {f["name"] for superficie in (EDITOR, HOME) for f in superficie.ferramentas_extras}


def _rotulos(idioma: str) -> set[str]:
    """The keys of `ferramentas` in that language's dictionary (`const pt`, `const en`...)."""
    texto = DICIONARIO.read_text(encoding="utf-8")
    inicio = re.search(rf"^(?:export )?const {idioma}\b", texto, re.M)
    assert inicio, f"dicionário {idioma} não encontrado"
    bloco = re.search(r"\bferramentas: \{(.*?)\n  \}", texto[inicio.end():], re.S)
    assert bloco, f"tabela de ferramentas de {idioma} não encontrada"
    return set(re.findall(r"^\s+([a-z_]+):", bloco.group(1), re.M))


@pytest.mark.parametrize("idioma", IDIOMAS)
def test_every_tool_the_model_can_call_has_a_label(idioma):
    rotulos = _rotulos(idioma)
    # A table the regex stopped reading would make the check below pass with nothing to compare.
    assert len(rotulos) > 20

    faltam = _ferramentas_do_modelo() - rotulos
    assert not faltam, f"sem rótulo em {idioma}: {sorted(faltam)}"
