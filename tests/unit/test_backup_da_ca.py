# tests/unit/test_backup_da_ca.py
"""scripts/backup-stepca.sh: the CA backup is readable only by whoever made it.

The `step-ca-data` volume holds the CA's private keys and `secrets/password` —
the password of those keys, in clear text. The tarball used to be written by
`tar` as root inside an alpine container, with no umask: it landed 0644 in
`backups/`, readable by every user of the host.

The script is EXECUTED, with a `docker` stand-in first in the PATH (the suite
has no Docker): a copy of its logic here would stay green with the script broken.
"""
import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "backup-stepca.sh"

# `docker volume inspect` succeeds; `docker run ... tar czf - ...` writes the
# "archive" to stdout, as the real tar does, and fails when asked to.
_DOCKER_FALSO = """#!/bin/sh
case "$1" in
    volume) exit 0 ;;
    run) printf 'conteudo-do-tar'; exit "${DOCKER_FALSO_SAIDA:-0}" ;;
esac
exit 1
"""


def _modo(caminho: Path) -> int:
    return stat.S_IMODE(caminho.stat().st_mode)


@pytest.fixture
def rodar(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(_DOCKER_FALSO)
    docker.chmod(0o755)
    destino = tmp_path / "backups"

    def _rodar(**env):
        ambiente = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "BACKUP_DIR": str(destino),
            **env,
        }
        # The test runner's umask (usually 022) is what the old version inherited.
        return subprocess.run(
            ["bash", str(SCRIPT)], env=ambiente, capture_output=True, text=True, timeout=30,
        )

    return _rodar, destino


def test_the_archive_is_0600_in_a_0700_directory_owned_by_the_caller(rodar):
    executar, destino = rodar
    r = executar()
    assert r.returncode == 0, r.stderr

    (arquivo,) = destino.glob("step-ca-*.tar.gz")
    assert _modo(destino) == 0o700
    assert _modo(arquivo) == 0o600
    # Written by the host shell, not by the container's root.
    assert arquivo.stat().st_uid == os.getuid()
    assert arquivo.read_bytes() == b"conteudo-do-tar"
    assert not list(destino.glob("*.partial"))


def test_an_existing_directory_and_old_archives_are_tightened(rodar):
    executar, destino = rodar
    destino.mkdir(mode=0o755)
    destino.chmod(0o755)
    antigo = destino / "step-ca-2026-01-01-0300.tar.gz"
    antigo.write_bytes(b"velho")
    antigo.chmod(0o644)

    r = executar()
    assert r.returncode == 0, r.stderr
    assert _modo(destino) == 0o700
    assert _modo(antigo) == 0o600


def test_a_failed_tar_leaves_no_archive_behind(rodar):
    """An interrupted tar would otherwise count as a backup in the retention."""
    executar, destino = rodar
    r = executar(DOCKER_FALSO_SAIDA="1")
    assert r.returncode != 0
    assert list(destino.iterdir()) == []


def test_retention_keeps_the_most_recent(rodar):
    executar, destino = rodar
    destino.mkdir()
    agora = time.time()
    for i in range(3):
        velho = destino / f"step-ca-2026-01-0{i + 1}-0300.tar.gz"
        velho.write_bytes(b"x")
        os.utime(velho, (agora - 86400 * (10 - i), agora - 86400 * (10 - i)))

    r = executar(BACKUP_RETAIN="2")
    assert r.returncode == 0, r.stderr
    restantes = sorted(p.name for p in destino.glob("step-ca-*.tar.gz"))
    assert len(restantes) == 2
    assert "step-ca-2026-01-03-0300.tar.gz" in restantes   # the newest of the old ones
    assert "step-ca-2026-01-01-0300.tar.gz" not in restantes


def test_a_directory_that_cannot_be_tightened_still_gets_the_backup(rodar, tmp_path):
    """A directory owned by root while the backup runs as a docker-group user
    (or an NFS export with root_squash): exiting lost the CA's only copy. The
    backup is written with a warning — the archive is 0600 regardless (fix
    review)."""
    executar, destino = rodar
    bin_dir = tmp_path / "bin"
    chmod_falso = bin_dir / "chmod"
    # Fails only for the directory itself; archives still get their mode.
    chmod_falso.write_text(
        '#!/bin/sh\n[ "$2" = "$BACKUP_DIR" ] && exit 1\nexec /bin/chmod "$@"\n'
    )
    chmod_falso.chmod(0o755)

    resultado = executar()

    assert resultado.returncode == 0, resultado.stderr
    assert "AVISO" in resultado.stderr
    (arquivo,) = destino.glob("step-ca-*.tar.gz")
    assert _modo(arquivo) == 0o600
