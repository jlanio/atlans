# tests/unit/test_compose_e_imagem.py
"""Operational defaults of the API image and of the compose files.

Each one is a value that works on the first deploy and bites later: a file
watcher in the image's default command, logs with no ceiling, a password on a
command line, a port honoured on one side of a hop only.
"""
import json
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
DOCKERFILE_API = RAIZ / "Dockerfile.api"
COMPOSE = RAIZ / "docker-compose.yml"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


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


# ── The Redis password ───────────────────────────────────────────────────────

# `redis-cli -a <password>` (or `--pass`): the password in argv, visible in `ps`
# — on the host too, for a process in a container.
_SENHA_NA_LINHA = re.compile(r"redis-cli\b[^\n|;]*\s(-a|--pass)\s")


def test_redis_cli_never_takes_the_password_on_the_command_line():
    arquivos = [COMPOSE, RAIZ / "scripts" / "smoke.sh", *sorted((RAIZ / "docs").rglob("*.md"))]
    achados = [
        f"{arquivo.relative_to(RAIZ)}: {linha.strip()}"
        for arquivo in arquivos
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if _SENHA_NA_LINHA.search(linha)
    ]
    assert achados == []
    teste = " ".join(_compose()["services"]["redis"]["healthcheck"]["test"])
    assert 'REDISCLI_AUTH="$${REDIS_PASSWORD}" redis-cli' in teste


def test_smoke_does_not_put_the_password_in_the_docker_command_line():
    """`docker compose exec -e REDISCLI_AUTH=<password>` is argv of the host's docker."""
    smoke = (RAIZ / "scripts" / "smoke.sh").read_text(encoding="utf-8")
    assert "-e REDISCLI_AUTH=" not in smoke
    assert 'REDISCLI_AUTH="$(cat)" redis-cli' in smoke


def test_the_api_receives_the_redis_password_to_encode_the_url():
    """REDIS_URL is interpolated verbatim; the API encodes it with REDIS_PASSWORD
    (app/core/utils/url_do_redis.py)."""
    env = _compose()["x-api-env"]
    assert env["REDIS_URL"] == "redis://:${REDIS_PASSWORD}@redis:6379/0"
    assert env["REDIS_PASSWORD"] == "${REDIS_PASSWORD}"


# ── API_PORT ─────────────────────────────────────────────────────────────────


def _uvicorn_port(comando: str) -> str:
    return re.search(r"--port (\d+)", comando).group(1)


def test_the_web_reaches_the_api_on_the_port_it_listens_on():
    """API_PORT was half honoured: web-prod called api-prod:${API_PORT} while
    uvicorn always listens on the port of its command — any other API_PORT
    broke the site. The internal hop uses the container's port."""
    servicos = _compose()["services"]
    porta = _uvicorn_port(servicos["api-prod"]["command"])
    assert servicos["web-prod"]["environment"]["API_INTERNA"] == f"http://api-prod:{porta}"
    rotulos = servicos["api-prod"]["labels"]
    assert f"traefik.http.services.api-svc.loadbalancer.server.port={porta}" in rotulos


def test_the_dev_browser_port_is_the_published_port():
    """In dev the browser goes to localhost:NEXT_PUBLIC_API_PORT: the API has to
    be published on that same host port (and listen on its own in the container)."""
    servicos = _compose()["services"]
    porta = _uvicorn_port(servicos["api"]["command"])
    assert servicos["api"]["ports"] == [f"127.0.0.1:${{API_PORT:-8000}}:{porta}"]
    assert servicos["web-dev"]["environment"]["NEXT_PUBLIC_API_PORT"] == "${API_PORT:-8000}"


# ── Logs with a ceiling ──────────────────────────────────────────────────────

LOGS_POR_DRIVER = RAIZ / "docker-compose.logs.yml"
COMPOSE_EXECUTOR = RAIZ / "docker-compose.executor.yml"
_POR_DRIVER = "${LOG_DRIVER:-json-file}"


def _blocos_por_driver() -> dict:
    return yaml.safe_load(LOGS_POR_DRIVER.read_text(encoding="utf-8"))["services"]


def _assert_bounded(nome: str, logging: dict) -> None:
    """json-file only with max-size/max-file; journald (its own ceiling) without
    them — Docker refuses to create the container with an option the driver
    does not know."""
    opcoes = logging.get("options") or {}
    if logging["driver"] == "json-file":
        assert opcoes.get("max-size") == "${LOG_MAX_SIZE:-10m}", nome
        assert opcoes.get("max-file") == "${LOG_MAX_FILE:-5}", nome
    else:
        assert logging["driver"] == "journald", nome
        assert not {"max-size", "max-file"} & set(opcoes), nome


def test_every_service_log_has_a_ceiling():
    """A service without `logging` gets the daemon's default — json-file with no
    ceiling on a stock Docker: Traefik's access log, Redis' saves every minute
    and the executor's jobs grew until the disk filled."""
    blocos = _blocos_por_driver()
    for nome, bloco in blocos.items():
        _assert_bounded(f"docker-compose.logs.yml:{nome}", bloco["logging"])

    executor = yaml.safe_load(COMPOSE_EXECUTOR.read_text(encoding="utf-8"))["services"]
    servicos = {
        **{f"docker-compose.yml:{n}": s for n, s in _compose()["services"].items()},
        **{f"docker-compose.executor.yml:{n}": s for n, s in executor.items()},
    }
    for nome, servico in servicos.items():
        if "extends" in servico:
            # api-prod and web-prod: the block of LOG_DRIVER, which exists for
            # both documented drivers.
            assert servico["extends"]["file"] == "docker-compose.logs.yml", nome
            base = servico["extends"]["service"]
            assert base.endswith(f"-{_POR_DRIVER}"), nome
            prefixo = base.removesuffix(_POR_DRIVER)
            assert {f"{prefixo}json-file", f"{prefixo}journald"} <= set(blocos), nome
            assert "logging" not in servico, nome
            continue
        assert "logging" in servico, f"{nome}: sem logging, vale o padrao do daemon"
        _assert_bounded(nome, servico["logging"])


def test_the_api_and_web_keep_their_journald_tags():
    """docs/operations.md: `journalctl -t atlans-api` / `-t atlans-web`."""
    blocos = _blocos_por_driver()
    servicos = _compose()["services"]
    for servico, tag in (("api-prod", "atlans-api"), ("web-prod", "atlans-web")):
        prefixo = servicos[servico]["extends"]["service"].removesuffix(_POR_DRIVER)
        for driver in ("json-file", "journald"):
            assert blocos[f"{prefixo}{driver}"]["logging"]["options"]["tag"] == tag


def test_the_traefik_access_log_is_not_an_unrotated_file():
    """Written to /var/log/traefik/access.log it grew forever (Traefik does not
    rotate it). By default it goes to the container output, under the rotation
    above; a file is an explicit choice (TRAEFIK_ACCESSLOG_FILEPATH)."""
    comando = _compose()["services"]["traefik"]["command"]
    caminhos = [a for a in comando if a.startswith("--accesslog.filepath=")]
    assert caminhos == ["--accesslog.filepath=${TRAEFIK_ACCESSLOG_FILEPATH:-/dev/stdout}"]
