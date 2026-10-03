# tests/unit/test_executor_boot_ordem_de_nomes.py
"""
Name binding order in the executor boot.

`main()` passed `on_sync=_sincronizar_agora` to `dashboard.start(...)`
— a call that executes RIGHT AWAY — but only defined `_sincronizar_agora` AFTER,
in the same scope. In Python that is not "defined later": the name becomes an
unbound local and reading it raises `UnboundLocalError`.

The effect was a startup crash in RICH mode, which is the default for anyone
running the executor in a terminal (`agent_main` only catches `KeyboardInterrupt`,
so the process died). It went unnoticed because the two packaged paths force
another mode: the desktop app uses `json` and the compose uses `off`.

Two tests, at different levels of abstraction on purpose:

  SPECIFIC     the exact regression, checked in the real scope of `main()`.
  GENERAL      a sweep for any other closure used before it exists in the
               same scope — the whole class of the error, not just this instance.
"""
from __future__ import annotations

import ast
import symtable
from pathlib import Path

import pytest

FONTE = Path(__file__).resolve().parents[2] / "executor" / "main.py"


def _tree():
    return ast.parse(FONTE.read_text(encoding="utf-8"))


def _function(nome: str):
    for no in ast.walk(_tree()):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    pytest.fail(f"funcao '{nome}' nao encontrada em {FONTE}")


# ── ESPECIFICO ───────────────────────────────────────────────────────────────

def test_sync_now_is_defined_before_being_passed_to_the_dashboard():
    """The exact regression: def ahead of the use, in the scope of main()."""
    main = _function("main")

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


def test_symtable_confirms_the_name_is_local_to_main():
    """Anchors the premise of the test above.

    The order only matters because the name is LOCAL to `main()`. If it ever
    becomes a global or a parameter, the order test loses its meaning and this
    one warns.
    """
    st = symtable.symtable(FONTE.read_text(encoding="utf-8"), str(FONTE), "exec")

    def achar(tabela, nome):
        if tabela.get_name() == nome:
            return tabela
        for child in tabela.get_children():
            found = achar(child, nome)
            if found:
                return found
        return None

    main = achar(st, "main")
    assert main is not None
    symbol = next(s for s in main.get_symbols() if s.get_name() == "_sincronizar_agora")
    assert symbol.is_local(), "premissa mudou: o nome deixou de ser local de main()"


# ── GERAL ────────────────────────────────────────────────────────────────────

def test_no_main_closure_is_used_before_it_exists():
    """Sweeps the whole class of the error, not just the instance already fixed.

    For each nested function defined directly in `main()`, requires that no read
    of the name appear before the line of the `def`. A read inside the body of
    ANOTHER nested function does not count: it only runs when called, and by
    then the name is already bound.
    """
    main = _function("main")

    nested_calls = {
        no.name: no.lineno
        for no in main.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    nested_bodies = [
        no for no in main.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    def inside_nested(linha: int) -> bool:
        return any(
            f.lineno <= linha <= (f.end_lineno or f.lineno) for f in nested_bodies
        )

    problemas = []
    for no in ast.walk(main):
        if not (isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load)):
            continue
        defined_at = nested_calls.get(no.id)
        if defined_at is None:
            continue
        if no.lineno < defined_at and not inside_nested(no.lineno):
            problemas.append(f"{no.id} usada na linha {no.lineno}, definida na {defined_at}")

    assert not problemas, (
        "closure(s) de main() usadas antes de existir — UnboundLocalError no boot:\n  "
        + "\n  ".join(problemas)
    )
