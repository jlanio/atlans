# tests/unit/test_log_temporario_dos_scripts.py
"""scripts/lib/ui.sh: the log of `ui_run` is a private temporary file.

bootstrap.sh and up.sh (which source ui.sh) run as root on servers, and every
`ui_run` writes the command's output — the database check, the CA, the
migrations — to `UI_LOG`. It was `${TMPDIR:-/tmp}/atlans-$$.log`: a name anyone
could predict (and plant as a symlink beforehand) and a file readable by every
user of the host. Now it comes from mktemp and goes away on exit.

ui.sh is SOURCED here by bash, as the scripts do.
"""
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
UI_SH = RAIZ / "scripts" / "lib" / "ui.sh"

_SCRIPT = """
set -euo pipefail
. "$UI_SH"
printf 'caminho=%s\\n' "$UI_LOG"
printf 'pid=%s\\n' "$$"
printf 'modo=%s\\n' "$(stat -c %a "$UI_LOG" 2>/dev/null || stat -f %Lp "$UI_LOG")"
ui_run "eco" sh -c 'echo saida-do-comando'
printf 'log=%s\\n' "$(cat "$UI_LOG")"
"""


def _rodar(tmp_path: Path) -> dict[str, str]:
    ambiente = {**os.environ, "TMPDIR": str(tmp_path), "UI_SH": str(UI_SH), "NO_COLOR": "1"}
    r = subprocess.run(
        ["bash", "-c", _SCRIPT], env=ambiente, capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    return dict(
        linha.split("=", 1) for linha in r.stdout.splitlines() if "=" in linha
    )


def test_the_log_is_private_unpredictable_and_removed_on_exit(tmp_path):
    lido = _rodar(tmp_path)
    caminho = Path(lido["caminho"])
    assert caminho.parent == tmp_path
    assert caminho.name != f"atlans-{lido['pid']}.log"
    assert lido["modo"] == "600"
    # ui_run still writes to it.
    assert lido["log"] == "saida-do-comando"
    # The EXIT trap removed it.
    assert not caminho.exists()
    assert list(tmp_path.iterdir()) == []
