# tests/unit/test_url_do_redis.py
"""REDIS_URL with a password that has characters reserved in URLs.

docker-compose.yml builds `redis://:${REDIS_PASSWORD}@redis:6379/0` by plain
interpolation: with a `/` in the password, the rest of it became the URL path
(and the database), and with a `%41`, redis-py's unquote changed the password.
The API now percent-encodes the password it also receives in REDIS_PASSWORD —
in config.REDIS_URL and in the rate limiter's storage — and leaves any other
URL alone.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from redis.connection import parse_url

from app.core import rate_limiter
from app.core.utils.url_do_redis import redis_url_with_encoded_password

RAIZ = Path(__file__).resolve().parents[2]

_SENHAS_DIFICEIS = [
    "S3CR3T/cauda-secreta",
    "a@b:c",
    "com%41percento",
    "pergunta?e#hash",
    "a[b]c",
    "mais+igual=",
]


@pytest.mark.parametrize("senha", _SENHAS_DIFICEIS)
def test_the_compose_url_reaches_redis_with_the_same_password(senha):
    url = redis_url_with_encoded_password(f"redis://:{senha}@redis:6379/0", senha)
    partes = parse_url(url)
    assert partes["password"] == senha
    assert (partes["host"], partes["port"], partes["db"]) == ("redis", 6379, 0)


def test_a_url_safe_password_is_left_as_it_is():
    url = "redis://:0a1b2c3d@redis:6379/0"  # pragma: allowlist secret
    assert redis_url_with_encoded_password(url, "0a1b2c3d") == url


@pytest.mark.parametrize("url", [
    "redis://redis:6379/0",                          # no password in the URL
    "redis://:outra@redis:6379/0",                   # another password
    "redis://usuario:a/b@redis:6379/0",              # with a user: not the compose shape
    "redis://:a%2Fb@redis:6379/0",                   # already encoded
    "unix:///var/run/redis.sock",
    "",
])
def test_any_other_url_is_left_alone(url):
    """An explicit REDIS_URL keeps working: only the compose shape is encoded."""
    assert redis_url_with_encoded_password(url, "a/b") == url


def test_without_redis_password_nothing_changes():
    url = "redis://:a/b@redis:6379/0"
    assert redis_url_with_encoded_password(url, None) == url
    assert redis_url_with_encoded_password(url, "") == url


def test_config_encodes_the_url_compose_builds():
    """config reads the environment at import: a clean interpreter."""
    senha = "S3CR3T/cauda@x"
    ambiente = {
        **os.environ,
        "PYTHONPATH": str(RAIZ),
        "REDIS_URL": f"redis://:{senha}@redis:6379/0",
        "REDIS_PASSWORD": senha,
    }
    saida = subprocess.run(
        [sys.executable, "-c", "import json; from app.core import config; print(json.dumps(config.REDIS_URL))"],
        cwd=RAIZ, env=ambiente, capture_output=True, text=True, timeout=120,
    )
    assert saida.returncode == 0, saida.stderr[-2000:]
    url = json.loads(saida.stdout.strip().splitlines()[-1])
    assert url == "redis://:S3CR3T%2Fcauda%40x@redis:6379/0"
    assert parse_url(url)["password"] == senha


def test_the_rate_limiter_uses_the_encoded_url(monkeypatch):
    senha = "S3CR3T/cauda-secreta"
    monkeypatch.delenv("RATE_LIMIT_STORAGE_URI", raising=False)
    monkeypatch.setenv("REDIS_URL", f"redis://:{senha}@127.0.0.1:1/0")
    monkeypatch.setenv("REDIS_PASSWORD", senha)
    lim = rate_limiter.create_limiter()
    assert type(lim._storage).__name__ == "RedisStorage"
    kwargs = lim._storage.storage.connection_pool.connection_kwargs
    assert (kwargs["password"], kwargs["port"], kwargs["db"]) == (senha, 1, 0)
