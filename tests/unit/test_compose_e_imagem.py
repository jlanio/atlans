# tests/unit/test_compose_e_imagem.py
"""Operational defaults of the API image and of the compose files.

Each one is a value that works on the first deploy and bites later: a file
watcher in the image's default command, logs with no ceiling, a password on a
command line, a port honoured on one side of a hop only.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOCKERFILE_API = RAIZ / "Dockerfile.api"


def _cmd(dockerfile: Path) -> list[str]:
    """The exec-form CMD of a Dockerfile (the last one wins, as in Docker)."""
    linhas = re.findall(r"^CMD (\[.*\])\s*$", dockerfile.read_text(encoding="utf-8"), re.M)
    assert linhas, f"{dockerfile.name} sem CMD na forma exec"
    return json.loads(linhas[-1])


def test_the_api_image_default_command_has_no_reload():
    """`--reload` restarts the API whenever a file changes and runs a single
    process: fine for the bind-mounted dev code (compose passes it there), wrong
    for whoever runs the image as is."""
    cmd = _cmd(DOCKERFILE_API)
    assert cmd[:2] == ["uvicorn", "app.main:app"]
    assert "--reload" not in cmd
