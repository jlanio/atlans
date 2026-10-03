# tests/unit/test_change_detector.py
"""Tests for the ChangeDetector node — branching on input change.

Covers:
  - Determinism of _stable_hash (reordered dict, float precision, sets)
  - Incremental hash of DataFrame/GeoDataFrame
  - Branching: first run, identical, changed, fields filter
  - Fail-closed when the state backend fails

The node talks to the server via /internal/change-detector (mTLS) — the executor
has no access to Redis. The branching tests use _FakeBackend, a double of the
SWAP endpoint (a single POST that stores the current hash and returns the previous one).
"""
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from flow.nodes.control.change_detector import (
    ChangeDetector,
    _stable_hash,
    _canonicalize,
)


# ── _stable_hash: determinismo ────────────────────────────────────────────────

def test_dict_keys_in_different_order_same_hash():
    a = {"foo": 1, "bar": 2}
    b = {"bar": 2, "foo": 1}
    assert _stable_hash(a) == _stable_hash(b)


def test_nested_dict_same_hash():
    a = {"x": {"y": 1, "z": 2}}
    b = {"x": {"z": 2, "y": 1}}
    assert _stable_hash(a) == _stable_hash(b)


def test_dict_different_value_different_hash():
    a = {"foo": 1}
    b = {"foo": 2}
    assert _stable_hash(a) != _stable_hash(b)


def test_float_precision_normalized():
    # 0.1 + 0.2 == 0.30000000000000004 != 0.3 em float — round(x, 12) cobre.
    a = {"v": 0.1 + 0.2}
    b = {"v": 0.3}
    assert _stable_hash(a) == _stable_hash(b)


def test_nan_inf_stable():
    nan = float("nan")
    assert _stable_hash({"v": nan}) == _stable_hash({"v": float("nan")})
    assert _stable_hash({"v": float("inf")}) == _stable_hash({"v": float("inf")})


def test_bytes_differs_from_string():
    assert _stable_hash(b"abc") != _stable_hash("abc")


def test_set_order_irrelevant():
    assert _stable_hash({1, 2, 3}) == _stable_hash({3, 1, 2})


def test_fields_filter_ignores_volatile_fields():
    base = {"feature_count": 150, "bbox": [10.0, 20.0]}
    with_timestamp = {**base, "queried_at": "2026-04-28T10:00:00Z"}
    # Without a filter, the hashes differ (timestamp changes).
    assert _stable_hash(base) != _stable_hash(with_timestamp)
    # With a filter including only the stable fields, the hashes are equal.
    assert _stable_hash(base, ["feature_count", "bbox"]) == _stable_hash(
        with_timestamp, ["feature_count", "bbox"]
    )


def test_list_order_matters():
    """Lista preserva ordem: [1,2,3] != [3,2,1]."""
    assert _stable_hash([1, 2, 3]) != _stable_hash([3, 2, 1])


def test_hash_eh_sha256_hex_64_chars():
    h = _stable_hash({"v": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ── DataFrame ─────────────────────────────────────────────────────────────────

def test_dataframe_same_structure_same_hash():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df2 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert _stable_hash(df1) == _stable_hash(df2)


def test_dataframe_rows_in_different_order_same_hash():
    """Cumulative XOR is insensitive to row order — desired."""
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3]})
    df2 = pd.DataFrame({"a": [3, 1, 2]})
    assert _stable_hash(df1) == _stable_hash(df2)


def test_dataframe_different_row_different_hash():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2, 3]})
    df2 = pd.DataFrame({"a": [1, 2, 4]})
    assert _stable_hash(df1) != _stable_hash(df2)


def test_dataframe_extra_column_different_hash():
    pd = pytest.importorskip("pandas")
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert _stable_hash(df1) != _stable_hash(df2)


# ── _canonicalize: tipos primitivos ───────────────────────────────────────────

def test_canonicalize_preserves_primitives():
    assert _canonicalize(None, None) is None
    assert _canonicalize(True, None) is True
    assert _canonicalize(42, None) == 42
    assert _canonicalize("foo", None) == "foo"


# ── Node ChangeDetector — branching ──────────────────────────────────────────

class _FakeBackend:
    """Double of the POST /internal/change-detector/{key} endpoint (atomic swap).

    `stored=None` → previous_hash None (first run). `swap_exc` simulates an
    unavailable backend — the node decides the branch by the `on_backend_error`
    policy. Each swap stores the received hash as the new `stored`, so two
    consecutive swaps exercise the real two-run cycle.
    """

    def __init__(self, stored: str | None = None, *, swap_exc=None):
        self.stored = stored
        self.swap_exc = swap_exc
        self.swaps: list[tuple[str, dict]] = []

    @property
    def client_cls(self):
        backend = self

        class FakeAsyncClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def request(self, method, url, *a, **kwargs):
                assert method == "POST", f"esperado POST de swap, veio {method}"
                if backend.swap_exc:
                    raise backend.swap_exc
                body = kwargs.get("json") or {}
                backend.swaps.append((url, body))
                anterior = backend.stored
                backend.stored = body.get("hash")
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"previous_hash": anterior}
                return resp

        return FakeAsyncClient


def _make_node(properties=None):
    """Instantiates ChangeDetector with default test properties."""
    node = ChangeDetector(node_id="n-test", parameters=properties or {})
    node._workflow_hash = "wfh-test"
    node._workspace_id = "ws-test"
    return node


async def _run(node, inputs, backend: _FakeBackend):
    """Executa o node contra o backend fake."""
    with patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://srv", {}, True)), \
            patch("httpx.AsyncClient", backend.client_cls):
        return await node.execute(inputs)


@pytest.mark.asyncio
async def test_first_run_branch_true():
    backend = _FakeBackend(stored=None)  # never ran
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] is None
    assert len(result["current_hash"]) == 64
    assert len(backend.swaps) == 1
    assert result["reason"] == "primeira_execucao"


@pytest.mark.asyncio
async def test_identical_input_branch_false():
    same_hash = _stable_hash({"a": 1})
    backend = _FakeBackend(stored=same_hash)
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is False
    assert result["previous_hash"] == same_hash
    assert result["current_hash"] == same_hash
    assert result["reason"] == "sem_mudanca"


@pytest.mark.asyncio
async def test_input_changed_branch_true():
    backend = _FakeBackend(stored="a" * 64)  # hash antigo qualquer
    result = await _run(_make_node(), {"data": {"a": 999}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] == "a" * 64
    assert result["current_hash"] != "a" * 64
    assert result["reason"] == "mudou"


@pytest.mark.asyncio
async def test_data_passed_through():
    """The original input is exposed as 'data' in the output on both branches."""
    payload = {"foo": "bar", "n": 42}
    result = await _run(_make_node(), {"x": payload}, _FakeBackend())

    assert result["output"] == payload


@pytest.mark.asyncio
async def test_fields_filter_applied():
    """With fields_filter, changes in fields outside the list do NOT mark changed."""
    expected_hash = _stable_hash({"a": 1, "b": 2}, ["a", "b"])
    backend = _FakeBackend(stored=expected_hash)

    # Same a/b, but with an additional timestamp. fields_filter must ignore it.
    result = await _run(
        _make_node({"fields": "a,b"}),
        {"data": {"a": 1, "b": 2, "ts": "2026-04-28T10:00"}},
        backend,
    )

    assert result["branch"] is False  # only timestamp changed, fields ignores it


@pytest.mark.asyncio
@pytest.mark.parametrize("guardado", [
    "a,b",           # OLD format (CSV), already saved in the definitions
    ["a", "b"],      # a real list (object editor)
    '["a","b"]',     # JSON string — what the chips field stores
])
async def test_fields_accepts_chips_list_json_and_csv(guardado):
    """The field became chips and started storing a JSON string. The three
    formats have to filter THE SAME — a workflow saved before doesn't change
    behavior."""
    expected_hash = _stable_hash({"a": 1, "b": 2}, ["a", "b"])
    backend = _FakeBackend(stored=expected_hash)
    result = await _run(
        _make_node({"fields": guardado}),
        {"data": {"a": 1, "b": 2, "ts": "2026-04-28T10:00"}},
        backend,
    )
    assert result["branch"] is False


@pytest.mark.asyncio
async def test_ttl_in_hours_converted_to_seconds():
    backend = _FakeBackend()
    await _run(_make_node({"ttl_hours": 2}), {"data": {"a": 1}}, backend)

    assert backend.swaps[0][1]["ttl_seconds"] == 7200


@pytest.mark.asyncio
async def test_ttl_zero_no_expiration():
    backend = _FakeBackend()
    await _run(_make_node({"ttl_hours": 0}), {"data": {"a": 1}}, backend)

    # ttl_seconds=0 → the server stores with no expiry.
    assert backend.swaps[0][1]["ttl_seconds"] == 0


@pytest.mark.asyncio
async def test_backend_down_default_fail_closed_branch_true():
    """Unavailable backend with the default policy → branch=True (fail-closed)."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()):
        result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert result["previous_hash"] is None  # we couldn't read
    assert result["reason"] == "backend_indisponivel"


@pytest.mark.asyncio
async def test_backend_down_policy_no_change():
    """on_backend_error=sem_mudanca: an infra blip does NOT trigger the expensive effect."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()):
        result = await _run(
            _make_node({"on_backend_error": "sem_mudanca"}), {"data": {"a": 1}}, backend
        )

    assert result["branch"] is False
    assert result["reason"] == "backend_indisponivel"


@pytest.mark.asyncio
async def test_backend_down_policy_fail():
    """on_backend_error=falhar: the run fails visibly instead of deciding blindly."""
    backend = _FakeBackend(swap_exc=httpx.ConnectError("backend down"))
    with patch("asyncio.sleep", AsyncMock()), pytest.raises(RuntimeError) as exc:
        await _run(
            _make_node({"on_backend_error": "falhar"}), {"data": {"a": 1}}, backend
        )

    assert "backend de estado indisponível" in str(exc.value)


@pytest.mark.asyncio
async def test_scope_workspace_uses_shared_key():
    backend = _FakeBackend()
    await _run(
        _make_node({"scope": "workspace", "shared_key": "monitor_zones"}),
        {"data": {"a": 1}},
        backend,
    )

    # Checks the key format — it must use the ws prefix and the shared_key.
    assert backend.swaps[0][0].endswith("/internal/change-detector/ws:ws-test:monitor_zones")


@pytest.mark.asyncio
async def test_scope_workspace_without_shared_key_uses_node_id():
    backend = _FakeBackend()
    await _run(
        _make_node({"scope": "workspace", "shared_key": ""}),
        {"data": {"a": 1}},
        backend,
    )

    assert backend.swaps[0][0].endswith("/internal/change-detector/ws:ws-test:n-test")


@pytest.mark.asyncio
async def test_scope_workflow_default():
    backend = _FakeBackend()
    await _run(_make_node(), {"data": {"a": 1}}, backend)  # scope default = "workflow"

    assert backend.swaps[0][0].endswith("/internal/change-detector/wf:wfh-test:n-test")


# ── Extended canonicalization: stable types ──────────────────────────────────

def test_hash_datetime_stable():
    import datetime as dt
    a = {"ts": dt.datetime(2025, 1, 1, 12, 0, 0)}
    b = {"ts": dt.datetime(2025, 1, 1, 12, 0, 0)}
    assert _stable_hash(a) == _stable_hash(b)
    # Momento diferente → hash diferente.
    c = {"ts": dt.datetime(2025, 1, 1, 12, 0, 1)}
    assert _stable_hash(a) != _stable_hash(c)
    # date and time also canonicalize.
    assert _stable_hash({"d": dt.date(2025, 1, 1)}) == _stable_hash({"d": dt.date(2025, 1, 1)})


def test_hash_uuid_stable():
    from uuid import UUID
    u = UUID("12345678-1234-5678-1234-567812345678")
    assert _stable_hash({"id": u}) == _stable_hash({"id": UUID(str(u))})
    other = UUID("87654321-4321-8765-4321-876543218765")
    assert _stable_hash({"id": u}) != _stable_hash({"id": other})


def test_hash_decimal_path_enum():
    from decimal import Decimal
    from pathlib import PurePosixPath
    from enum import Enum

    class Color(Enum):
        RED = 1
        BLUE = 2

    # Decimal preserves precision (str), stable across equal instances.
    assert _stable_hash({"v": Decimal("1.10")}) == _stable_hash({"v": Decimal("1.10")})
    assert _stable_hash({"v": Decimal("1.10")}) != _stable_hash({"v": Decimal("1.1")})
    # Path canonicalizes via as_posix.
    assert _stable_hash({"p": PurePosixPath("/a/b")}) == _stable_hash({"p": PurePosixPath("/a/b")})
    # Enum: name + value.
    assert _stable_hash({"c": Color.RED}) == _stable_hash({"c": Color.RED})
    assert _stable_hash({"c": Color.RED}) != _stable_hash({"c": Color.BLUE})


def test_hash_unknown_type_fail_fast():
    from flow.nodes.control.change_detector import ChangeDetectorTypeError

    class Custom:
        def __init__(self, x):
            self.x = x

    with pytest.raises(ChangeDetectorTypeError) as exc:
        _stable_hash({"obj": Custom(1)})
    # The message includes the type's path for diagnosis.
    assert "Custom" in str(exc.value)


@pytest.mark.asyncio
async def test_hash_unknown_type_in_node_fail_safe():
    """Input with a non-hashable type → node falls back to branch=True (fail-safe), doesn't break."""
    class Custom:
        pass

    result = await _run(_make_node(), {"data": {"obj": Custom()}}, _FakeBackend())

    assert result["branch"] is True
    assert result["previous_hash"] is None


@pytest.mark.asyncio
async def test_corrupted_hash_in_backend():
    """Invalid value in the backend (non-hex/wrong size) → treated as the first run."""
    backend = _FakeBackend(stored="nao-eh-um-hash-valido")  # lixo
    result = await _run(_make_node(), {"data": {"a": 1}}, backend)

    # Hash corrompido vira None → previous_hash None → branch True (mudou).
    assert result["previous_hash"] is None
    assert result["branch"] is True
    assert result["reason"] == "primeira_execucao"


# ── http_retry helper ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_http_retry_em_503(monkeypatch):
    """Transient 503 twice + 200 → returns 200 after retries."""
    from unittest.mock import MagicMock
    from flow.utils.http_retry import async_request_with_retry

    seq = [503, 503, 200]
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, method, url, *a, **k):
            r = MagicMock()
            r.status_code = seq[calls["n"]]
            calls["n"] += 1
            return r

    # Doesn't really sleep.
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    with patch("httpx.AsyncClient", FakeClient):
        resp = await async_request_with_retry("GET", "https://x/y", base_delay=0)

    assert resp.status_code == 200
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_http_retry_gives_up_after_max(monkeypatch):
    """503 always → returns the last 503 after max_attempts (caller fails closed)."""
    from unittest.mock import MagicMock
    from flow.utils.http_retry import async_request_with_retry

    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, method, url, *a, **k):
            calls["n"] += 1
            r = MagicMock()
            r.status_code = 503
            return r

    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    with patch("httpx.AsyncClient", FakeClient):
        resp = await async_request_with_retry("GET", "https://x/y", max_attempts=3, base_delay=0)

    assert resp.status_code == 503
    assert calls["n"] == 3  # 1 + 2 retries


# ── cleanup after workflow delete ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_keys_no_delete_workflow():
    """delete_workflow remove keys change_detector:wf:{hash}:* do Redis."""
    from app.services.workflow_service import _cleanup_change_detector_keys

    existing = [
        "change_detector:wf:wfh-test:n-1",
        "change_detector:wf:wfh-test:n-2",
    ]
    deleted: list[str] = []

    class FakeRedis:
        async def scan_iter(self, match=None, count=None):
            for k in existing:
                yield k
        async def delete(self, key):
            deleted.append(key)

    with patch("app.core.redis.get_redis_pool", return_value=FakeRedis()):
        removed = await _cleanup_change_detector_keys("wfh-test")

    assert removed == 2
    assert set(deleted) == set(existing)


@pytest.mark.asyncio
async def test_cleanup_keys_redis_failure_does_not_propagate():
    """A Redis failure during cleanup doesn't propagate (best-effort)."""
    from app.services.workflow_service import _cleanup_change_detector_keys

    class BrokenRedis:
        def scan_iter(self, *a, **k):
            raise ConnectionError("redis down")

    with patch("app.core.redis.get_redis_pool", return_value=BrokenRedis()):
        removed = await _cleanup_change_detector_keys("wfh-test")

    assert removed == 0  # removed nothing, but didn't raise


# ── v2 of the table hash: modular sum instead of XOR ─────────────────────────

def test_dataframe_swapped_duplicate_pair_is_detected():
    """v1 regression: XOR canceled out pairs of identical rows — swapping {x, x}
    for {y, y} kept n_rows/cols/dtypes AND the aggregate, passing as 'no
    change'. The modular sum detects it."""
    pd = pytest.importorskip("pandas")
    from flow.nodes.control.change_detector import _hash_dataframe

    a = pd.DataFrame({"v": ["x", "x", "z"]})
    b = pd.DataFrame({"v": ["y", "y", "z"]})
    assert _hash_dataframe(a) != _hash_dataframe(b)
    assert _stable_hash(a) != _stable_hash(b)


def test_geodataframe_swapped_duplicate_pair_is_detected():
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("shapely")
    from shapely.geometry import Point
    from flow.nodes.control.change_detector import _hash_geodataframe

    a = gpd.GeoDataFrame({"v": [1, 1, 2]}, geometry=[Point(0, 0), Point(0, 0), Point(1, 1)])
    b = gpd.GeoDataFrame({"v": [1, 1, 2]}, geometry=[Point(2, 2), Point(2, 2), Point(1, 1)])
    assert _hash_geodataframe(a) != _hash_geodataframe(b)


def test_dataframe_signature_is_versioned():
    """The bump to v2 is explicit in the signature — it invalidates the v1 hashes
    a single time after the deploy, on purpose."""
    pd = pytest.importorskip("pandas")
    from flow.nodes.control.change_detector import _hash_dataframe

    assinatura = _hash_dataframe(pd.DataFrame({"v": [1]}))
    assert assinatura["__df__"] == 2
    assert "soma" in assinatura and "xor" not in assinatura


# ── ignore_fields: exclusion with a dotted path ──────────────────────────────

def test_ignore_at_root():
    with_ts = {"a": 1, "fetched_at": "2026-08-31T10:00"}
    assert _stable_hash(with_ts, None, ["fetched_at"]) == _stable_hash({"a": 1})


def test_ignore_dotted_path():
    a = {"a": 2, "meta": {"updated_at": "ontem", "fonte": "wfs"}}
    b = {"a": 2, "meta": {"updated_at": "hoje", "fonte": "wfs"}}
    assert _stable_hash(a, None, ["meta.updated_at"]) == _stable_hash(b, None, ["meta.updated_at"])
    # Without the ignore, the two differ — the filter is what makes them equal.
    assert _stable_hash(a) != _stable_hash(b)


def test_ignore_descends_into_list_of_records():
    a = {"items": [{"v": 1, "ts": 10}, {"v": 2, "ts": 20}]}
    b = {"items": [{"v": 1, "ts": 99}, {"v": 2, "ts": 77}]}
    assert _stable_hash(a, None, ["items.ts"]) == _stable_hash(b, None, ["items.ts"])


def test_ignore_removes_dataframe_column():
    pd = pytest.importorskip("pandas")
    a = {"tabela": pd.DataFrame({"v": [1, 2], "fetched_at": ["t1", "t2"]})}
    b = {"tabela": pd.DataFrame({"v": [1, 2], "fetched_at": ["t9", "t8"]})}
    assert _stable_hash(a, None, ["tabela.fetched_at"]) == _stable_hash(b, None, ["tabela.fetched_at"])
    # A missing column is not an error: the input is already as the filter wants.
    without_column = {"tabela": pd.DataFrame({"v": [1, 2]})}
    assert _stable_hash(without_column, None, ["tabela.fetched_at"]) == _stable_hash(
        a, None, ["tabela.fetched_at"]
    )


def test_ignore_does_not_mutate_the_input():
    original = {"a": 1, "meta": {"updated_at": "x", "k": 2}}
    _stable_hash(original, None, ["meta.updated_at", "a"])
    assert original == {"a": 1, "meta": {"updated_at": "x", "k": 2}}


@pytest.mark.asyncio
async def test_ignore_fields_applied_in_node():
    """The node's ignore_fields param: only the ignored field changed → 'Sem mudança' (no change)."""
    esperado = _stable_hash({"a": 1}, None, None)
    backend = _FakeBackend(stored=esperado)
    result = await _run(
        _make_node({"ignore_fields": "ts"}),
        {"data": {"a": 1, "ts": "2026-08-31T10:00"}},
        backend,
    )
    assert result["branch"] is False
    assert result["reason"] == "sem_mudanca"


@pytest.mark.asyncio
@pytest.mark.parametrize("guardado", ["ts", ["ts"], '["ts"]'])
async def test_ignore_fields_accepts_chips_list_json_and_csv(guardado):
    """Same format tolerance as `fields` — including the old CSV."""
    esperado = _stable_hash({"a": 1}, None, None)
    backend = _FakeBackend(stored=esperado)
    result = await _run(
        _make_node({"ignore_fields": guardado}),
        {"data": {"a": 1, "ts": "2026-08-31T10:00"}},
        backend,
    )
    assert result["branch"] is False
    assert result["reason"] == "sem_mudanca"


# ── silent first run ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_silent_first_run_records_baseline_without_triggering():
    backend = _FakeBackend(stored=None)
    result = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 1}}, backend
    )

    assert result["branch"] is False                      # doesn't trigger the alert
    assert result["reason"] == "primeira_execucao"
    assert len(backend.swaps) == 1                        # but the baseline was stored
    # The next run with the SAME input is still 'Sem mudança'...
    result2 = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 1}}, backend
    )
    assert result2["branch"] is False and result2["reason"] == "sem_mudanca"
    # ...e com input DIFERENTE dispara normalmente.
    result3 = await _run(
        _make_node({"primeira_execucao": "sem_mudanca"}), {"data": {"a": 2}}, backend
    )
    assert result3["branch"] is True and result3["reason"] == "mudou"


# ── ttl_hours tolerante a campo limpo ────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_ttl_hours_falls_back_to_default():
    """A field cleared in the UI ('') must not bring down the run — uses the 168h default."""
    backend = _FakeBackend()
    result = await _run(_make_node({"ttl_hours": ""}), {"data": {"a": 1}}, backend)

    assert result["branch"] is True
    assert backend.swaps[0][1]["ttl_seconds"] == 168 * 3600


# ── multiple inputs ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multiple_inputs_all_enter_the_hash():
    """Two edges connected: both go into the hash (sorted by name) — before, the
    second was silently discarded and a change in it went unnoticed."""
    backend = _FakeBackend()
    r1 = await _run(_make_node(), {"b": {"y": 2}, "a": {"x": 1}}, backend)
    assert r1["current_hash"] == _stable_hash({"a": {"x": 1}, "b": {"y": 2}})

    # A change ONLY in the second input is detected.
    r2 = await _run(_make_node(), {"a": {"x": 1}, "b": {"y": 999}}, backend)
    assert r2["branch"] is True and r2["reason"] == "mudou"


@pytest.mark.asyncio
async def test_cleanup_ws_keys_no_delete_do_workspace():
    """ws:* keys (shared_key) belong to no workflow — the workspace cascade is the
    only place that can clean them up; with ttl_hours=0 they would live
    forever."""
    from app.services.workflow_service import _cleanup_change_detector_ws_keys

    existing = [
        "change_detector:ws:ws-alvo:monitor_zones",
        "change_detector:ws:ws-alvo:outra-chave",
    ]
    deleted: list[str] = []
    patterns: list[str] = []

    class FakeRedis:
        def scan_iter(self, match=None, count=None):
            patterns.append(match)
            async def _gen():
                for k in existing:
                    yield k
            return _gen()
        async def delete(self, key):
            deleted.append(key)

    with patch("app.core.redis.get_redis_pool", return_value=FakeRedis()):
        removed = await _cleanup_change_detector_ws_keys("ws-alvo")

    assert removed == 2
    assert set(deleted) == set(existing)
    assert patterns == ["change_detector:ws:ws-alvo:*"]


@pytest.mark.asyncio
async def test_workspace_soft_delete_triggers_ws_cleanup():
    """The workspace cascade must call the ws:* cleanup in addition to the per-workflow one."""
    from app.services import workflow_service as ws_mod
    import datetime as dt

    db = AsyncMock()
    rows = MagicMock()
    rows.all.return_value = [("wf-1", None)]
    upd = MagicMock()
    upd.rowcount = 1
    db.execute = AsyncMock(side_effect=[rows, MagicMock(), upd])

    with patch.object(ws_mod, "_cleanup_change_detector_keys", new=AsyncMock()) as per_wf, \
            patch.object(ws_mod, "_cleanup_change_detector_ws_keys", new=AsyncMock()) as by_ws:
        await ws_mod.soft_delete_workspace_workflows(db, "ws-alvo", dt.datetime(2026, 8, 31))

    per_wf.assert_awaited_once_with("wf-1")
    by_ws.assert_awaited_once_with("ws-alvo")
