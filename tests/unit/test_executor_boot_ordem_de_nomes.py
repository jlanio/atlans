# tests/unit/test_executor_boot_ordem_de_nomes.py
"""
Ordem de ligacao de nomes no boot do executor.

`main()` passava `ao_sincronizar=_sincronizar_agora` para `dashboard.start(...)`
— uma chamada que executa NA HORA — mas so definia `_sincronizar_agora` DEPOIS,
no mesmo escopo. Em Python isso nao e "definido mais tarde": o nome vira uma
local nao-ligada e a leitura levanta `UnboundLocalError`.

O efeito era um crash de inicializacao no modo RICH, que e o default de quem
roda o executor num terminal (`agent_main` so captura `KeyboardInterrupt`, entao
o processo morria). Passou despercebido porque os dois caminhos empacotados
forcam outro modo: o app desktop usa `json` e o compose usa `off`.

Dois testes, em niveis diferentes de abstracao de proposito:

  ESPECIFICO   a regressao exata, verificada no escopo real de `main()`.
  GERAL        varredura por qualquer outra closure usada antes de existir no
               mesmo escopo — a classe inteira do erro, nao so esta instancia.
"""
from __future__ import annotations

import ast
import symtable
from pathlib import Path

import pytest

FONTE = Path(__file__).resolve().parents[2] / "executor" / "main.py"


def _arvore():
    return ast.parse(FONTE.read_text(encoding="utf-8"))


def _funcao(nome: str):
    for no in ast.walk(_arvore()):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    pytest.fail(f"funcao '{nome}' nao encontrada em {FONTE}")


# ── ESPECIFICO ───────────────────────────────────────────────────────────────

def test_sincronizar_agora_e_definido_antes_de_ser_passado_ao_dashboard():
    """A regressao exata: def na frente do uso, no escopo de main()."""
    main = _funcao("main")

    definicao = [
        no.lineno for no in ast.walk(main)
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        and no.name == "_sincronizar_agora"
    ]
    assert definicao, "_sincronizar_agora sumiu de main() — o painel RICH depende dela"

    usos = [
        no.lineno for no in ast.walk(main)
        if isinstance(no, ast.Name) and no.id == "_sincronizar_agora"
        and isinstance(no.ctx, ast.Load)
    ]
    assert usos, "ninguem mais passa _sincronizar_agora — o botao 'Sincronizar agora' morreu"

    assert min(definicao) < min(usos), (
        f"_sincronizar_agora e definida na linha {min(definicao)} mas usada na "
        f"{min(usos)} — UnboundLocalError no boot do modo RICH"
    )


def test_symtable_confirma_que_o_nome_e_local_de_main():
    """Ancora a premissa do teste acima.

    A ordem so importa porque o nome e LOCAL de `main()`. Se um dia ele virar
    global ou parametro, o teste de ordem perde o sentido e este aqui avisa.
    """
    st = symtable.symtable(FONTE.read_text(encoding="utf-8"), str(FONTE), "exec")

    def achar(tabela, nome):
        if tabela.get_name() == nome:
            return tabela
        for filha in tabela.get_children():
            achada = achar(filha, nome)
            if achada:
                return achada
        return None

    main = achar(st, "main")
    assert main is not None
    simbolo = next(s for s in main.get_symbols() if s.get_name() == "_sincronizar_agora")
    assert simbolo.is_local(), "premissa mudou: o nome deixou de ser local de main()"


# ── GERAL ────────────────────────────────────────────────────────────────────

def test_nenhuma_closure_de_main_e_usada_antes_de_existir():
    """Varre a classe inteira do erro, nao apenas a instancia ja corrigida.

    Para cada funcao aninhada definida diretamente em `main()`, exige que
    nenhuma leitura do nome apareca antes da linha do `def`. Uma leitura dentro
    do corpo de OUTRA aninhada nao conta: ela so roda quando chamada, e a essa
    altura o nome ja esta ligado.
    """
    main = _funcao("main")

    aninhadas = {
        no.name: no.lineno
        for no in main.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    corpos_aninhados = [
        no for no in main.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    def dentro_de_aninhada(linha: int) -> bool:
        return any(
            f.lineno <= linha <= (f.end_lineno or f.lineno) for f in corpos_aninhados
        )

    problemas = []
    for no in ast.walk(main):
        if not (isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load)):
            continue
        definida_em = aninhadas.get(no.id)
        if definida_em is None:
            continue
        if no.lineno < definida_em and not dentro_de_aninhada(no.lineno):
            problemas.append(f"{no.id} usada na linha {no.lineno}, definida na {definida_em}")

    assert not problemas, (
        "closure(s) de main() usadas antes de existir — UnboundLocalError no boot:\n  "
        + "\n  ".join(problemas)
    )
