# tests/unit/test_change_detector_router.py
"""Tests for the /internal/change-detector router — the executor's HTTP bridge to
the server's Redis, where ChangeDetector stores hashes."""
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

@contextmanager
def _bypass_auth_and_db(*, workflow_workspace_id: str | None = "ws-test-001"):
    """Replaces _auth_agent and get_db (there is no real DB in unit tests).

    The real router calls drive_router's `_auth_agent`, which authenticates the
    executor by its mTLS cert. For unit tests of the router itself, it is enough
    to simulate auth success and use a mock session.

    `_authorize_key` queries the database to find out which workspace the
    workflow of a `wf:*` key belongs to. The mock DB returns `workflow_workspace_id` —
    pass a value outside `_resolved_ws_ids` (or None) to exercise the 403.
    """
    from app.main import app
    from app.api.dependencies import get_db

    async def _fake_db():
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=workflow_workspace_id)
        db.execute = AsyncMock(return_value=result)
        yield db

    fake_agent = MagicMock()
    fake_agent.id_hash = "executor-test-001"
    fake_agent._resolved_ws_ids = ["ws-test-001"]

    app.dependency_overrides[get_db] = _fake_db
    auth_patch = patch(
        "app.api.routers.change_detector_router._auth_agent",
        new_callable=AsyncMock,
        return_value=fake_agent,
    )
    auth_patch.start()
    try:
        yield
    finally:
        auth_patch.stop()
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def fake_redis():
    """Cliente Redis fake que armazena chaves em dict in-memory."""
    store = {}
    ttls = {}

    rc = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _set(key, value, ex=None, get=False):
        anterior = store.get(key)
        store[key] = value if isinstance(value, str) else value.decode()
        if ex is None:
            ttls.pop(key, None)
        else:
            ttls[key] = ex
        return anterior if get else True

    async def _setex(key, ttl, value):
        store[key] = value if isinstance(value, str) else value.decode()
        ttls[key] = ttl
        return True

    async def _ttl(key):
        if key not in store:
            return -2
        return ttls.get(key, -1)

    class _Pipe:
        """Pipeline fake: enfileira get/ttl (sync) e executa na ordem (async)."""
        def __init__(self):
            self._ops = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        def get(self, key):
            self._ops.append(("get", key))
            return self

        def ttl(self, key):
            self._ops.append(("ttl", key))
            return self

        async def execute(self):
            saidas = []
            for op, key in self._ops:
                saidas.append(await (_get(key) if op == "get" else _ttl(key)))
            return saidas

    rc.get = _get
    rc.set = _set
    rc.setex = _setex
    rc.ttl = _ttl
    rc.pipeline = lambda *a, **k: _Pipe()
    rc._store = store
    rc._ttls = ttls
    return rc


# ── SWAP (POST) ───────────────────────────────────────────────────────────────

SWAP_URL = "/internal/change-detector/wf:wfh-abc:n-xyz"


@pytest.mark.asyncio
async def test_swap_first_time_returns_previous_none_and_writes(client, fake_redis):
    payload = {"hash": "c" * 64, "ttl_seconds": 7200}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] is None
    assert fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] == "c" * 64
    assert fake_redis._ttls["change_detector:wf:wfh-abc:n-xyz"] == 7200


@pytest.mark.asyncio
async def test_swap_returns_the_previous_and_writes_the_new(client, fake_redis):
    """The single operation: decision (previous) and write (new) in the same round
    trip — without the read→decide→write window in which two simultaneous runs
    read the same old hash and both decided 'Mudou' (changed)."""
    fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] = "a" * 64
    payload = {"hash": "b" * 64, "ttl_seconds": 3600}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] == "a" * 64
    assert fake_redis._store["change_detector:wf:wfh-abc:n-xyz"] == "b" * 64


@pytest.mark.asyncio
async def test_swap_without_ttl_writes_without_expiration(client, fake_redis):
    payload = {"hash": "d" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 200
    assert "change_detector:wf:wfh-abc:n-xyz" in fake_redis._store
    assert "change_detector:wf:wfh-abc:n-xyz" not in fake_redis._ttls


@pytest.mark.asyncio
async def test_swap_invalid_hash_returns_422(client, fake_redis):
    """A hash that isn't SHA-256 hex (64 lowercase chars) is rejected."""
    payload = {"hash": "nao-eh-sha256", "ttl_seconds": 3600}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_negative_ttl_returns_422(client, fake_redis):
    payload = {"hash": "e" * 64, "ttl_seconds": -1}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_excessive_ttl_returns_422(client, fake_redis):
    payload = {"hash": "f" * 64, "ttl_seconds": 99_999_999}  # > 1 ano
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_swap_invalid_key_format_returns_400(client, fake_redis):
    """Keys outside the allowed prefix (wf:/ws:) are rejected."""
    payload = {"hash": "a" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/idempotency:abc", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_swap_redis_unavailable_returns_503(client):
    """Failure to connect to Redis → 503; the executor decides the branch by the
    node's on_backend_error policy."""
    failing_redis = AsyncMock()
    failing_redis.set = AsyncMock(side_effect=ConnectionError("redis down"))
    payload = {"hash": "a" * 64, "ttl_seconds": 0}
    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=failing_redis):
        resp = await client.post(SWAP_URL, json=payload)
    assert resp.status_code == 503


# ── Escopo (cross-tenant) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_from_another_workspace_returns_403(client, fake_redis):
    """An executor must not touch the state of a workflow outside its workspaces:
    the out-of-scope swap is blocked BEFORE touching Redis."""
    fake_redis._store["change_detector:wf:wfh-alheio:n-xyz"] = "h" * 64
    with _bypass_auth_and_db(workflow_workspace_id="ws-de-outro-tenant"), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/wf:wfh-alheio:n-xyz",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403
    assert fake_redis._store["change_detector:wf:wfh-alheio:n-xyz"] == "h" * 64


@pytest.mark.asyncio
async def test_nonexistent_workflow_returns_403(client, fake_redis):
    """Doesn't distinguish 'doesn't exist' from 'isn't yours' — prevents enumeration."""
    with _bypass_auth_and_db(workflow_workspace_id=None), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/wf:nao-existe:n-xyz",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scope_foreign_ws_returns_403(client, fake_redis):
    """A 'ws:' key for a workspace outside the executor's list is denied."""
    with _bypass_auth_and_db(), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/ws:ws-alheio:shared-key",
                                 json={"hash": "a" * 64, "ttl_seconds": 0})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scope_own_ws_allowed(client, fake_redis):
    fake_redis._store["change_detector:ws:ws-test-001:shared-key"] = "i" * 64
    with _bypass_auth_and_db(), \
            patch("app.api.routers.change_detector_router.get_redis_pool", return_value=fake_redis):
        resp = await client.post("/internal/change-detector/ws:ws-test-001:shared-key",
                                 json={"hash": "e" * 64, "ttl_seconds": 0})
    assert resp.status_code == 200
    assert resp.json()["previous_hash"] == "i" * 64


@pytest.mark.asyncio
async def test_swap_is_a_single_atomic_operation(client):
    """Atomicity is not observable in a serialized fake, so this test locks down
    the PATTERN: the whole swap must be a single SET ... GET. A separate GET
    followed by a SET would reopen exactly the race window (two simultaneous runs
    reading the same old hash) that the endpoint exists to close."""
    chamadas: list = []
    rc = AsyncMock()

    async def _set(key, value, ex=None, get=False):
        chamadas.append(("set", bool(get)))
        return None

    rc.set = _set
    rc.get = AsyncMock(side_effect=AssertionError("GET separado reabre a corrida"))

    with _bypass_auth_and_db(), patch("app.api.routers.change_detector_router.get_redis_pool", return_value=rc):
        resp = await client.post(SWAP_URL, json={"hash": "a" * 64, "ttl_seconds": 60})

    assert resp.status_code == 200
    assert chamadas == [("set", True)]
