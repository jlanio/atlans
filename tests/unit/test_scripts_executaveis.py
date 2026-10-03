# tests/unit/test_scripts_executaveis.py
"""
Every script the Makefile calls as `./scripts/...` needs the executable bit
in git.

`make bootstrap` is the first step of a fresh install (docs/self-hosting.md),
and the Makefile's four scripts were in git without the bit: on a clean clone,
`make bootstrap` stopped at "Permission denied" before doing anything. Checked
in the git index, not on disk, because the index mode is what reaches every clone.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _called_by_makefile() -> list[str]:
    texto = (RAIZ / "Makefile").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^\t\./(scripts/[\w.-]+)", texto, re.M)))


def test_there_are_scripts_called_by_makefile():
    assert len(_called_by_makefile()) >= 4, _called_by_makefile()


def test_makefile_scripts_are_executable_in_git():
    modos = {}
    for script in _called_by_makefile():
        linha = subprocess.run(
            ["git", "-C", str(RAIZ), "ls-files", "-s", "--", script],
            check=True, capture_output=True, text=True,
        ).stdout
        modos[script] = linha.split()[0] if linha else "fora do git"
    assert {s: m for s, m in modos.items() if m != "100755"} == {}
