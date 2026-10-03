# tests/conftest.py
"""
Fixtures shared across all tests.
"""
import os
import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

# Ensures critical environment variables exist before importing the app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum!!")
os.environ.setdefault("APP_SECRET", "test-app-secret-for-unit-tests!!")
os.environ.setdefault("FERNET_KEY", "aTjxua8UQDFu3W4os-o9LeGQ9P_pv58w0I6xuzSdnQE=")
# executor/config.py raises ValueError on import if EXECUTOR_ID does not exist.
# Without this, any test that imports executor.* passes on the machine of whoever
# has executor/.env configured and breaks during CI collection.
os.environ.setdefault("EXECUTOR_ID", "executor-test-0000")
# A default scheduling time zone DIFFERENT from UTC, on purpose: it is the only
# way for the tests to tell "the configured default" (AGENDAMENTO_FUSO_PADRAO)
# from the UTC that `datetime` would give by accident. The code's default is
# UTC. UTC-4 all year round (no daylight saving time): the result does not
# change with the date of the run.
os.environ.setdefault("AGENDAMENTO_FUSO_PADRAO", "America/La_Paz")
# The suite's global limiter always counts in memory. Without this it would use
# REDIS_URL — which exists in the dev container — or a RATE_LIMIT_STORAGE_URI
# from a dev .env, and would run against the real Redis, with counters that
# survive between runs (the editor's 60/hour bucket fills up in three runs).
# Tests of the storage build their own limiter.
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"


# ── Logging isolation ──────────────────────────────────────────────────────────

# The LogRecord factory as the process was born with it, captured BEFORE
# collection: test modules that import `executor.main` at the top already swap
# it during collection (the module calls `configure_logging()` on import).
import logging as _logging

_ORIGINAL_FACTORY = _logging.getLogRecordFactory()


def _reset_factory() -> None:
    from flow.utils import redacao_log, segredos_vivos

    _logging.setLogRecordFactory(_ORIGINAL_FACTORY)
    # `segredos_vivos` installs itself once and remembers that it did: the flag is
    # restored too, otherwise it would never reinstall itself on the clean factory.
    redacao_log._installed = False
    segredos_vivos._installed = False


@pytest.fixture(autouse=True)
def _isolated_logrecord_factory():
    """The executor's secret redaction lives in the PROCESS's LogRecord factory
    (`flow.utils.redacao_log.install_in_process`). Without this reset, an
    import of `executor.main` would leave it on for the whole suite, and tests
    that check the `***` from `segredos_vivos` (or a token prefix in an audit
    line) would see `<REDACTED>` depending on the suite order. Tests of the
    redaction install it inside the test itself."""
    _reset_factory()
    yield
    _reset_factory()


# ── Extensions ────────────────────────────────────────────────────────────────


@pytest.fixture
def empty_registry(monkeypatch):
    """An EMPTY extension registry in place of the real one (app/extensoes).

    It is the core alone, as in the free distribution — and the test hangs on
    it only what it wants (a fake `plano_e_teto`, a contribution to the
    dashboard). The routes the app already included remain; what gets swapped
    is what the core consults on each request.
    """
    from app import extensoes

    novo = extensoes.Registro()
    monkeypatch.setattr(extensoes, "_registro", novo)
    return novo


# ── Infrastructure mocks ───────────────────────────────────────────────────────


@pytest.fixture
def mock_redis():
    """Mock of the async Redis client (idempotency)."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.lpush = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_current_user():
    """Fake authenticated user for injection via dependency_overrides."""
    user = MagicMock()
    user.id_hash = "usr-test-001"
    user.is_active = True
    user.role = "user"
    return user


@pytest.fixture
def mock_workspace_ids():
    """List of workspace IDs accessible to the test user."""
    return ["ws-test-001"]


@pytest.fixture
async def client(mock_redis, mock_current_user, mock_workspace_ids):
    """
    AsyncClient with the real app and all infra (Redis, DB, MinIO, scheduler) mocked.
    Automatically authenticates as mock_current_user in workspace ws-test-001.
    """
    from httpx import AsyncClient, ASGITransport

    from app.main import app
    from app.api.dependencies import get_current_user, get_user_workspace_ids

    async def _current_user():
        return mock_current_user

    async def _workspace_ids():
        return mock_workspace_ids

    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_user_workspace_ids] = _workspace_ids

    mock_sched = MagicMock()
    mock_sched.start = AsyncMock()
    mock_sched.stop = AsyncMock()

    with ExitStack() as stack:
        stack.enter_context(patch("app.main._wait_for_db", new_callable=AsyncMock))
        # Centralized Redis pool: injects the mock directly into the redis.py module
        stack.enter_context(patch("app.core.redis._pool", mock_redis))
        stack.enter_context(patch("app.core.redis.init_redis", AsyncMock(return_value=mock_redis)))
        stack.enter_context(patch("app.core.redis.close_redis", AsyncMock()))
        stack.enter_context(patch("app.core.storage.ensure_bucket"))
        stack.enter_context(patch("app.core.run_result_consumer.run_consumer_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.artifact_cleanup.run_cleanup_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.fontes_catalogo.importar_catalogo_no_arranque", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.fontes_catalogo.run_verificacao_loop", new_callable=AsyncMock))
        stack.enter_context(patch("app.core.async_scheduler.scheduler", mock_sched))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


