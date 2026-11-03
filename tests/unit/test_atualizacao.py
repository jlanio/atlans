# tests/unit/test_atualizacao.py
"""scripts/update.sh and scripts/rollback.sh (make update, make rollback).

The scripts are EXECUTED on a real git repository made here — an "origin" and
the installation's clone — with a `docker` stand-in first in the PATH (the
suite has no Docker) and stand-ins for up.sh, smoke.sh and backup-stepca.sh,
which log how they were called. A copy of their logic here would stay green
with the scripts broken.

What is pinned down:
- nothing changes before the backups (a missing required variable, a dirty
  tree or a failed pg_dump stop the update with HEAD where it was);
- the database URL never goes on a command line, and the dump is born 0600;
- the record in backups/atualizacoes/ is what the rollback reads, and the
  rollback brings back the code (on the same branch) and the kept images,
  without a build.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
}

# Answers what update.sh and rollback.sh ask Docker; logs every call. The
# running services come from FAKE_SERVICES; FAKE_DUMP_FAIL makes pg_dump fail;
# FAKE_MISSING lists images `docker image inspect` does not find.
_DOCKER_FALSO = r"""#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "$FAKE_LOG"
if [ "$1" = compose ]; then
    shift
    while [ "${1:-}" = --profile ]; do shift 2; done
    case "${1:-}" in
        ps)
            shift
            if [ "${1:-}" = --services ]; then printf '%s\n' $FAKE_SERVICES; exit 0; fi
            if [ "${1:-}" = -q ]; then
                shift
                if [ -n "${1:-}" ]; then
                    case "$1" in api-prod|api) echo c-api ;; esac
                else
                    printf '%s\n' c-api c-web
                fi
                exit 0
            fi
            exit 0 ;;
        logs) printf '%s\n' "${FAKE_TRAEFIK_LOG:-}"; exit 0 ;;
        up) exit "${FAKE_COMPOSE_UP_EXIT:-0}" ;;
    esac
    exit 0
fi
case "$1" in
    info) [ "${2:-}" = -f ] && echo /tmp; exit 0 ;;
    volume) exit 0 ;;
    inspect)
        case "$3:$4" in
            *Config.Image*:c-api) echo atlans-api:local ;;
            *Config.Image*:c-web) echo atlans-web:local ;;
            *.Image*:c-api) echo sha256:aaaa ;;
            *.Image*:c-web) echo sha256:bbbb ;;
            *) exit 1 ;;
        esac
        exit 0 ;;
    tag) exit 0 ;;
    image)
        case "$2" in
            inspect) case " ${FAKE_MISSING:-} " in *" $3 "*) exit 1 ;; esac; exit 0 ;;
            rm) exit 0 ;;
        esac ;;
    run)
        printf 'env PGURL=%s\n' "${PGURL:-}" >> "$FAKE_LOG"
        case "$*" in
            *psql*) echo 170011 ;;
            *pg_dump*) [ "${FAKE_DUMP_FAIL:-0}" = 1 ] && exit 1; printf 'PGDMP-fake' ;;
        esac
        exit 0 ;;
esac
exit 0
"""

_STUB = """#!/usr/bin/env bash
printf '%s %s\\n' "{nome}" "$*" >> "$FAKE_LOG"
{extra}
exit "${{{saida}:-0}}"
"""

_BACKUP_CA = "mkdir -p backups && : > backups/step-ca-$(date +%F-%H%M%S).tar.gz"

_ENV = (
    'ATLANS_LANG=pt\n'
    'MINIO_ROOT_USER=atlans-x\n'
    'DATABASE_URL="postgresql+asyncpg://atlans:s3cr3t-pw@db.interno:5432/atlans?ssl=require"\n'
)
_COMPOSE = "x-minio:\n  MINIO_ROOT_USER: ${MINIO_ROOT_USER:?defina}\n"
_EXEMPLO = "ATLANS_LANG=\nMINIO_ROOT_USER=change-me\nDATABASE_URL=\n"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, **_GIT_ENV},
    ).stdout.strip()


def _modo(caminho: Path) -> int:
    return stat.S_IMODE(caminho.stat().st_mode)


class Instalacao:
    """An origin, a working clone that publishes versions, and the installation."""

    def __init__(self, base: Path):
        self.base = base
        self.log = base / "docker.log"
        self.log.write_text("")
        self.bin = base / "bin"
        self.bin.mkdir()
        (self.bin / "docker").write_text(_DOCKER_FALSO)
        (self.bin / "docker").chmod(0o755)

        self.origem = base / "origin.git"
        _git(base, "init", "--bare", "-b", "main", str(self.origem))
        self.trabalho = base / "trabalho"
        _git(base, "clone", str(self.origem), str(self.trabalho))
        t = self.trabalho
        (t / "scripts" / "lib").mkdir(parents=True)
        for nome in ("update.sh", "rollback.sh"):
            shutil.copy(RAIZ / "scripts" / nome, t / "scripts" / nome)
        shutil.copytree(RAIZ / "scripts" / "lib", t / "scripts" / "lib", dirs_exist_ok=True)
        for nome, saida, extra in (
            ("up.sh", "FAKE_UP_EXIT", ""),
            ("smoke.sh", "FAKE_SMOKE_EXIT", ""),
            ("backup-stepca.sh", "FAKE_CA_EXIT", _BACKUP_CA),
        ):
            arq = t / "scripts" / nome
            arq.write_text(_STUB.format(nome=nome, saida=saida, extra=extra))
            arq.chmod(0o755)
        (t / "alembic" / "versions").mkdir(parents=True)
        (t / "alembic" / "versions" / ".gitkeep").write_text("")
        (t / ".gitignore").write_text(".env\nbackups/\n")
        (t / ".env.example").write_text(_EXEMPLO)
        (t / "docker-compose.yml").write_text(_COMPOSE)
        (t / "app.txt").write_text("v1\n")
        _git(t, "add", "-A")
        _git(t, "commit", "-m", "v1")
        _git(t, "push", "origin", "main")
        self.v1 = _git(t, "rev-parse", "HEAD")

        self.dir = base / "instalacao"
        _git(base, "clone", str(self.origem), str(self.dir))
        (self.dir / ".env").write_text(_ENV)

    def publicar(self, mensagem: str, arquivos: dict[str, str] | None = None, tag: str | None = None) -> str:
        t = self.trabalho
        (t / "app.txt").write_text(mensagem + "\n")
        for nome, conteudo in (arquivos or {}).items():
            (t / nome).parent.mkdir(parents=True, exist_ok=True)
            (t / nome).write_text(conteudo)
        _git(t, "add", "-A")
        _git(t, "commit", "-m", mensagem)
        _git(t, "push", "origin", "main")
        if tag:
            _git(t, "tag", tag)
            _git(t, "push", "origin", tag)
        return _git(t, "rev-parse", "HEAD")

    def rodar(self, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        ambiente = {
            **os.environ, **_GIT_ENV,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_LOG": str(self.log),
            "FAKE_SERVICES": "api-prod web-prod traefik",
            "NO_COLOR": "1",
            "TMPDIR": str(self.base),
            **env,
        }
        return subprocess.run(
            ["bash", f"scripts/{script}", *args], cwd=self.dir, env=ambiente,
            capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
        )

    def head(self) -> str:
        return _git(self.dir, "rev-parse", "HEAD")

    def ramo(self) -> str:
        return subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=self.dir,
            capture_output=True, text=True,
        ).stdout.strip()

    def registros(self) -> list[Path]:
        return sorted((self.dir / "backups" / "atualizacoes").glob("*.txt"))

    def registro(self, caminho: Path | None = None) -> dict[str, str]:
        caminho = caminho or self.registros()[-1]
        linhas = caminho.read_text().splitlines()
        return dict(linha.split("=", 1) for linha in linhas if "=" in linha)

    def chamadas(self) -> str:
        return self.log.read_text()


@pytest.fixture
def inst(tmp_path):
    return Instalacao(tmp_path)


def _saida(r: subprocess.CompletedProcess) -> str:
    return r.stdout + r.stderr


# ── update ───────────────────────────────────────────────────────────────────

def test_check_shows_what_changes_and_touches_nothing(inst):
    inst.publicar("v2: nova tela", {".env.example": _EXEMPLO + "NOVA_OPCIONAL=\n"})
    r = inst.rodar("update.sh", "--check")
    assert r.returncode == 0, _saida(r)
    assert "v2: nova tela" in r.stdout
    assert "NOVA_OPCIONAL" in r.stdout
    assert inst.head() == inst.v1
    assert not (inst.dir / "backups").exists()
    assert "docker tag" not in inst.chamadas() and "docker run" not in inst.chamadas()


def test_update_backs_up_keeps_images_moves_code_and_records(inst):
    v2 = inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == v2
    assert inst.ramo() == "main"

    reg = inst.registro()
    assert reg["ESTADO"] == "concluida"
    assert (reg["MODO"], reg["DE"], reg["PARA"], reg["RAMO"]) == ("prod", inst.v1, v2, "main")
    curto = inst.v1[:12]
    assert reg["IMAGENS"].split() == [
        f"atlans-api:local=atlans-rollback/atlans-api-local:{curto}",
        f"atlans-web:local=atlans-rollback/atlans-web-local:{curto}",
    ]
    chamadas = inst.chamadas()
    assert f"docker tag sha256:aaaa atlans-rollback/atlans-api-local:{curto}" in chamadas

    # The dump: from the API's network namespace, 0600, with the URL that
    # libpq takes (no +asyncpg, no ?ssl=) and never on a command line.
    dump = Path(reg["BANCO"])
    assert dump.read_bytes() == b"PGDMP-fake"
    assert _modo(dump) == 0o600
    assert "--network container:c-api" in chamadas
    assert "env PGURL=postgresql://atlans:s3cr3t-pw@db.interno:5432/atlans\n" in chamadas
    assert all("s3cr3t-pw" not in linha for linha in chamadas.splitlines() if linha.startswith("docker "))
    assert "postgres:17-alpine" in chamadas
    assert not list((inst.dir / "backups").glob(".atlans-db-*"))

    assert reg["CA"].endswith(".tar.gz") and Path(reg["CA"]).exists()
    assert "up.sh prod --yes --no-prompt" in chamadas
    assert "smoke.sh" in chamadas
    assert _modo(inst.registros()[-1]) == 0o600
    assert _modo(inst.dir / "backups" / "atualizacoes") == 0o700


def test_without_yes_and_without_a_terminal_nothing_changes(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh")
    assert r.returncode == 1
    assert inst.head() == inst.v1
    assert not (inst.dir / "backups").exists()
    assert "docker run" not in inst.chamadas()


def test_a_required_variable_missing_stops_before_any_backup(inst):
    inst.publicar("v2", {"docker-compose.yml": _COMPOSE + "  NOVA: ${NOVA_OBRIGATORIA:?defina}\n"})
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 1
    assert "NOVA_OBRIGATORIA" in _saida(r)
    assert inst.head() == inst.v1
    assert not (inst.dir / "backups").exists()


def test_a_changed_tracked_file_stops_the_update(inst):
    inst.publicar("v2")
    (inst.dir / "app.txt").write_text("mexido a mao\n")
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 1
    assert "app.txt" in _saida(r)
    assert inst.head() == inst.v1


def test_untracked_files_do_not_stop_the_update(inst):
    v2 = inst.publicar("v2")
    (inst.dir / "atlans-root.crt").write_text("cert\n")
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == v2


def test_a_failed_dump_stops_before_the_code_moves(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_DUMP_FAIL="1")
    assert r.returncode == 1
    assert inst.head() == inst.v1
    assert inst.registro()["ESTADO"] == "falhou"
    assert not list((inst.dir / "backups").glob(".atlans-db-*"))
    assert not list((inst.dir / "backups").glob("atlans-db-*.dump"))
    assert "up.sh" not in inst.chamadas()


def test_skip_db_backup_runs_no_pg_dump(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", "--skip-db-backup")
    assert r.returncode == 0, _saida(r)
    assert "pg_dump" not in inst.chamadas()
    assert inst.registro()["BANCO"] == ""


def test_a_failed_start_is_recorded_and_points_to_rollback(inst):
    v2 = inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_UP_EXIT="1")
    assert r.returncode == 1
    assert "make rollback" in _saida(r)
    assert inst.head() == v2
    assert inst.registro()["ESTADO"] == "falhou"


def test_a_failed_smoke_test_is_recorded(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_SMOKE_EXIT="1")
    assert r.returncode == 1
    assert inst.registro()["ESTADO"] == "falhou"


def test_a_dropped_traefik_route_fails_the_update(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_TRAEFIK_LOG='middleware "rate-mcp@file" does not exist')
    assert r.returncode == 1
    assert "rate-mcp" in _saida(r)
    assert inst.registro()["ESTADO"] == "falhou"


def test_once_done_a_second_run_has_nothing_to_do(inst):
    inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.chamadas().count("up.sh ") == 1
    assert len(inst.registros()) == 1


def test_code_already_pulled_without_a_record_still_brings_it_up(inst):
    """A git pull without the rebuild: the code is current, the containers are not."""
    v2 = inst.publicar("v2")
    _git(inst.dir, "pull", "--ff-only")
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == v2
    assert "up.sh prod" in inst.chamadas()
    reg = inst.registro()
    assert reg["DE"] == reg["PARA"] == v2


def test_the_mode_comes_from_what_is_running(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_SERVICES="api web-dev redis")
    assert r.returncode == 0, _saida(r)
    assert inst.registro()["MODO"] == "dev"
    assert "up.sh dev --no-executor --yes --no-prompt" in inst.chamadas()


def test_nothing_running_and_no_mode_given_stops(inst):
    inst.publicar("v2")
    r = inst.rodar("update.sh", "--yes", FAKE_SERVICES="")
    assert r.returncode == 1
    assert inst.head() == inst.v1


def test_the_images_of_older_updates_are_released(inst):
    for n in (2, 3, 4):
        inst.publicar(f"v{n}")
        r = inst.rodar("update.sh", "--yes")
        assert r.returncode == 0, _saida(r)
    primeiro, segundo, terceiro = (inst.registro(p) for p in inst.registros())
    assert primeiro.get("IMAGENS_REMOVIDAS") == "1"
    assert "IMAGENS_REMOVIDAS" not in segundo and "IMAGENS_REMOVIDAS" not in terceiro
    for par in primeiro["IMAGENS"].split():
        assert f"docker image rm {par.split('=', 1)[1]}" in inst.chamadas()


# ── rollback ─────────────────────────────────────────────────────────────────

def test_rollback_brings_back_code_on_the_branch_and_images_without_build(inst):
    inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    reg = inst.registro()

    r = inst.rodar("rollback.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == inst.v1
    assert inst.ramo() == "main"
    chamadas = inst.chamadas()
    for par in reg["IMAGENS"].split():
        original, guardada = par.split("=", 1)
        assert f"docker tag {guardada} {original}" in chamadas
    assert "up.sh prod --no-build --yes --no-prompt" in chamadas
    assert inst.registro()["ESTADO"] == "revertida"

    # Undone once: a second rollback does not reach further back on its own.
    r = inst.rodar("rollback.sh", "--yes")
    assert r.returncode == 1
    assert inst.head() == inst.v1


def test_rollback_builds_when_a_kept_image_is_gone(inst):
    inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    guardada = inst.registro()["IMAGENS"].split()[0].split("=", 1)[1]
    r = inst.rodar("rollback.sh", "--yes", FAKE_MISSING=guardada)
    assert r.returncode == 0, _saida(r)
    assert "up.sh prod --yes --no-prompt" in inst.chamadas()
    assert "--no-build" not in inst.chamadas()


def test_rollback_warns_about_migrations_and_shows_the_downgrade(inst):
    inst.publicar("v2", {"alembic/versions/20261201_0002_nova.py": "revision = 'x'\n"})
    assert inst.rodar("update.sh", "--yes").returncode == 0
    r = inst.rodar("rollback.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert "alembic downgrade -1" in r.stdout
    assert inst.head() == inst.v1


def test_rollback_without_yes_and_without_a_terminal_changes_nothing(inst):
    v2 = inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    r = inst.rodar("rollback.sh")
    assert r.returncode == 1
    assert inst.head() == v2
    assert inst.registro()["ESTADO"] == "concluida"


def test_update_to_a_tag_and_back_returns_to_the_branch(inst):
    v2 = inst.publicar("v2", tag="v2.0.0")
    r = inst.rodar("update.sh", "--yes", "--to", "v2.0.0")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == v2
    assert inst.ramo() == ""

    r = inst.rodar("rollback.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == inst.v1
    assert inst.ramo() == "main"


def test_rollback_list_shows_the_updates(inst):
    inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    r = inst.rodar("rollback.sh", "--list")
    assert r.returncode == 0
    assert "concluida" in r.stdout
    assert inst.v1[:12] in r.stdout


# ── up.sh --no-build ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("args, esperado, ausente", [
    ((), "up -d --build", "--no-build"),
    (("--no-build",), "up -d --no-build", "up -d --build"),
])
def test_up_sh_builds_unless_asked_not_to(tmp_path, args, esperado, ausente):
    """The real up.sh, stopped at the compose call (the stand-in fails it)."""
    pasta = tmp_path / "inst"
    (pasta / "secrets").mkdir(parents=True)
    shutil.copytree(RAIZ / "scripts", pasta / "scripts")
    (pasta / ".env").write_text(_ENV + "STEPCA_PROVISIONER_PASSWORD=x\n")
    (pasta / "secrets" / "stepca_password.txt").write_text("x\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # volume inspect fails (no CA yet), compose up fails: up.sh stops there.
    (bin_dir / "docker").write_text(
        '#!/usr/bin/env bash\nprintf \'docker %s\\n\' "$*" >> "$FAKE_LOG"\n'
        'case "$*" in volume*|*" up "*) exit 1 ;; esac\nexit 0\n'
    )
    (bin_dir / "docker").chmod(0o755)
    log = tmp_path / "docker.log"
    r = subprocess.run(
        ["bash", "scripts/up.sh", "dev", "--no-executor", "--no-prompt", *args], cwd=pasta,
        env={**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
             "FAKE_LOG": str(log), "NO_COLOR": "1", "TMPDIR": str(tmp_path)},
        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
    )
    assert r.returncode == 1
    chamadas = log.read_text()
    assert esperado in chamadas, r.stdout + r.stderr
    assert ausente not in chamadas


# ── failures halfway ─────────────────────────────────────────────────────────

def test_running_again_after_a_failed_start_picks_up_with_the_old_backups(inst):
    """The way back stays the version before: not the broken state of now."""
    v2 = inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes", FAKE_UP_EXIT="1").returncode == 1
    assert inst.registro()["ETAPA"] == "codigo"

    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert len(inst.registros()) == 1
    reg = inst.registro()
    assert (reg["ESTADO"], reg["DE"], reg["PARA"]) == ("concluida", inst.v1, v2)
    chamadas = inst.chamadas()
    assert chamadas.count("pg_dump") == 1
    assert chamadas.count("docker tag sha256:aaaa") == 1
    assert chamadas.count("up.sh prod") == 2


def test_rollback_skips_an_update_that_stopped_before_the_code(inst):
    v2 = inst.publicar("v2")
    assert inst.rodar("update.sh", "--yes").returncode == 0
    inst.publicar("v3")
    assert inst.rodar("update.sh", "--yes", FAKE_DUMP_FAIL="1").returncode == 1
    assert inst.head() == v2

    r = inst.rodar("rollback.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert inst.head() == inst.v1
    primeiro, segundo = (inst.registro(p) for p in inst.registros())
    assert primeiro["ESTADO"] == "revertida"
    assert segundo["ESTADO"] == "falhou"


def test_an_update_that_rewrites_update_sh_still_finishes_as_it_began(inst):
    """git rewrites the running script; bash already read all of it."""
    novo = "#!/usr/bin/env bash\necho 'update.sh NOVO'\nexit 7\n" + "# x\n" * 400
    v2 = inst.publicar("v2", {"scripts/update.sh": novo, "scripts/rollback.sh": novo})
    r = inst.rodar("update.sh", "--yes")
    assert r.returncode == 0, _saida(r)
    assert "NOVO" not in r.stdout
    assert inst.head() == v2
    assert inst.registro()["ESTADO"] == "concluida"
