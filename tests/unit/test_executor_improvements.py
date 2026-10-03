# tests/unit/test_executor_improvements.py
"""
Unit tests for the performance and resilience improvements in flow/executor.py:

  M1 — async _spill_to_disk (asyncio.shield + to_thread)
  M2 — Uniqueness of spill files (UUID suffix)
  M3 — Timeouts configurable via env vars
  M4 — Retry with exponential backoff in the httpx upload
  M5 — async _render_node_parameters (to_thread)
  M6 — Temp file instead of BytesIO in _upload_pin_artifact
"""

import asyncio
import os
import re
import pytest
from unittest.mock import MagicMock, patch


# ── Helpers compartilhados ────────────────────────────────────────────────────

def _make_presign_response(upload_url: str = "http://minio/presigned") -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"upload_url": upload_url}
    return r


def _make_put_response() -> MagicMock:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    return r


def _make_executor(params: dict = None):
    """Creates a minimal WorkflowExecutor with a Merge node connected to a trigger.
    The edge is needed so that node-1 is not filtered out by filter_isolated=True."""
    from flow.executor import WorkflowExecutor

    definition = {
        "nodes": [
            {
                "id": "trigger-1",
                "type": "trigger",
                "name": "WebhookTrigger",
                "properties": {},
            },
            {
                "id": "node-1",
                "type": "control",
                "name": "Merge",
                "properties": {"alias": "MergeAlias"},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "trigger-1", "target": "node-1"},
        ],
    }
    publisher = MagicMock()
    publisher.publish_event = MagicMock()
    executor = WorkflowExecutor(definition, task_id="test-task-001", publisher=publisher)
    if params:
        executor.node_mgr.nodes["node-1"].parameters.update(params)
    return executor


# ── M3: Configurable timeouts ─────────────────────────────────────────────────

class TestTimeoutConstants:
    """M3 — Timeout constants must exist and have the correct defaults."""

    def test_constants_exist(self):
        import flow.executor.pin as mod
        assert hasattr(mod, "_PIN_PRESIGN_TIMEOUT")
        assert hasattr(mod, "_PIN_UPLOAD_TIMEOUT")
        assert hasattr(mod, "_PIN_RETRY_COUNT")
        assert hasattr(mod, "_PIN_RETRY_MAX_DELAY")

    def test_defaults(self):
        import flow.executor.pin as mod
        # Expected defaults when env vars are not set
        assert mod._PIN_PRESIGN_TIMEOUT == int(os.getenv("PIN_PRESIGN_TIMEOUT", "15"))
        assert mod._PIN_UPLOAD_TIMEOUT == int(os.getenv("PIN_UPLOAD_TIMEOUT", "120"))
        assert mod._PIN_RETRY_COUNT == int(os.getenv("PIN_UPLOAD_MAX_RETRIES", "2"))
        assert mod._PIN_RETRY_MAX_DELAY == int(os.getenv("PIN_UPLOAD_RETRY_MAX_DELAY", "30"))

    def test_env_var_read_on_import(self, monkeypatch):
        """After a reload with a custom env var, the constant must reflect the value."""
        import importlib
        import flow.executor.pin as pin_mod

        monkeypatch.setenv("PIN_PRESIGN_TIMEOUT", "7")
        monkeypatch.setenv("PIN_UPLOAD_TIMEOUT", "45")
        importlib.reload(pin_mod)

        assert pin_mod._PIN_PRESIGN_TIMEOUT == 7
        assert pin_mod._PIN_UPLOAD_TIMEOUT == 45

        # Cleanup: restore defaults so as not to affect other tests
        monkeypatch.delenv("PIN_PRESIGN_TIMEOUT", raising=False)
        monkeypatch.delenv("PIN_UPLOAD_TIMEOUT", raising=False)
        importlib.reload(pin_mod)


# ── M2: UUID suffix in the spill file name ────────────────────────────────────

class TestSpillFileUniqueness:
    """M2 — Spill files must have a UUID suffix to avoid collisions."""

    def test_name_pattern_has_hex_suffix(self):
        """The node_key_<8hex>.parquet pattern must be valid."""
        import uuid
        node_id = "nó-abc"
        key = "output"
        suffix = uuid.uuid4().hex[:8]
        filename = f"{node_id}_{key}_{suffix}.parquet"
        assert re.search(r"[0-9a-f]{8}\.parquet$", filename), (
            f"'{filename}' não termina com 8 chars hex + .parquet"
        )

    def test_two_consecutive_suffixes_are_distinct(self):
        """Two UUIDs generated in a row must differ (astronomically high probability)."""
        import uuid
        s1 = uuid.uuid4().hex[:8]
        s2 = uuid.uuid4().hex[:8]
        assert s1 != s2

    def test_spill_generates_unique_paths_for_same_node(self, tmp_path, monkeypatch):
        """_spill_to_disk called twice for the same node generates distinct paths."""
        import geopandas as gpd
        from shapely.geometry import Point
        import flow.executor.spill as spill

        # The patch goes on the module that READS the constants. Tiny ceiling: any
        # GeoDataFrame exceeds it and is actually written to tmp_path.
        monkeypatch.setattr(spill, "_SPILL_BASE_DIR", str(tmp_path))
        monkeypatch.setattr(spill, "_SPILL_THRESHOLD_MB", 1e-9)

        gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
        written_paths = [
            spill._spill_to_disk("task-999", "node-X", {"data": gdf})["data"]["__spill_path__"]
            for _ in range(2)
        ]

        assert written_paths[0] != written_paths[1], (
            "Dois spills do mesmo nó devem gerar paths únicos"
        )
        for p in written_paths:
            basename = os.path.basename(p)
            assert re.match(r"node-X_data_[0-9a-f]{8}\.parquet$", basename), (
                f"'{basename}' não segue o padrão node_key_<8hex>.parquet"
            )


# ── M4: Retry with exponential backoff ───────────────────────────────────────

class TestUploadPinRetry:
    """M4 — upload_pin_to_minio must retry with exponential backoff."""

    @pytest.fixture(autouse=True)
    def agent_env(self, monkeypatch):
        monkeypatch.setenv("EXECUTOR_ID", "executor-test-001")
        monkeypatch.setenv("EXECUTOR_API_KEY", "test-key")
        monkeypatch.setenv("EXECUTOR_SERVER_URL", "http://localhost:8000")

    def test_success_without_retry(self):
        """An upload that succeeds on the 1st attempt must not call time.sleep."""
        from flow.executor import pin

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 2), \
             patch("time.sleep") as mock_sleep, \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", return_value=_make_put_response()), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(b"data", "key.json", "application/json")

        mock_sleep.assert_not_called()

    def test_retries_after_transient_failure(self):
        """A failure on the 1st PUT attempt must trigger a retry and succeed on the 2nd."""
        from flow.executor import pin

        put_calls = {"n": 0}

        def flaky_put(*args, **kwargs):
            put_calls["n"] += 1
            if put_calls["n"] == 1:
                raise ConnectionError("Timeout")
            return _make_put_response()

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 2), \
             patch("time.sleep") as mock_sleep, \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=flaky_put), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(b"data", "key.json", "application/json")

        assert put_calls["n"] == 2
        # A range, not an exact value: the wait is now spread over 50-100%
        # (see flow/utils/backoff.py). Pinning `== 1` here meant pinning the
        # absence of jitter, which is precisely the defect — two executors that
        # failed at the same instant retried at the same instant.
        mock_sleep.assert_called_once()
        (espera,), _ = mock_sleep.call_args
        assert 0.5 <= espera <= 1.0

    def test_raises_exception_when_retries_run_out(self):
        """After exhausting _PIN_RETRY_COUNT attempts, it must re-raise the last exception."""
        from flow.executor import pin

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 2), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=OSError("Storage indisponível")), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            with pytest.raises(OSError, match="Storage indisponível"):
                pin.upload_pin_to_minio(b"data", "key.json", "application/json")

    def test_exponential_backoff(self):
        """The wait must double on each attempt, within the jitter range."""
        from flow.executor import pin

        sleep_delays: list[int] = []

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 3), \
             patch("flow.executor.pin._PIN_RETRY_MAX_DELAY", 60), \
             patch("time.sleep", side_effect=lambda d: sleep_delays.append(d)), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=Exception("falha")), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            with pytest.raises(Exception):
                pin.upload_pin_to_minio(b"data", "key.json", "application/json")

        # 3 retries → 3 sleeps. With 50-100% proportional jitter, each wait falls
        # in the range [0.5 x 2^k, 2^k]: [0.5–1], [1–2], [2–4]. The ranges touch
        # but do not overlap, so the sequence remains non-decreasing — the
        # exponential growth stays verifiable without pinning the value.
        assert len(sleep_delays) == 3
        for k, espera in enumerate(sleep_delays):
            assert 0.5 * (2 ** k) <= espera <= 2 ** k, (k, espera)
        assert sleep_delays == sorted(sleep_delays)

    def test_backoff_respects_cap(self):
        """The delay must not exceed _PIN_RETRY_MAX_DELAY."""
        from flow.executor import pin

        sleep_delays: list[int] = []

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 5), \
             patch("flow.executor.pin._PIN_RETRY_MAX_DELAY", 3), \
             patch("time.sleep", side_effect=lambda d: sleep_delays.append(d)), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=Exception("falha")), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            with pytest.raises(Exception):
                pin.upload_pin_to_minio(b"data", "key.json", "application/json")

        assert all(d <= 3 for d in sleep_delays), (
            f"Algum delay excedeu o cap de 3s: {sleep_delays}"
        )


# ── M6: Temp file instead of BytesIO ─────────────────────────────────────────

class TestUploadPinWithPath:
    """M6 — upload_pin_to_minio must accept a file path (str) as well as bytes."""

    @pytest.fixture(autouse=True)
    def agent_env(self, monkeypatch):
        monkeypatch.setenv("EXECUTOR_ID", "executor-test-001")
        monkeypatch.setenv("EXECUTOR_API_KEY", "test-key")
        monkeypatch.setenv("EXECUTOR_SERVER_URL", "http://localhost:8000")

    def test_path_is_read_and_bytes_sent(self, tmp_path):
        """When content is a path (str), the file's bytes must be sent in the PUT."""
        from flow.executor import pin

        expected = b"fake parquet bytes"
        f = tmp_path / "pin.parquet"
        f.write_bytes(expected)

        captured: dict = {}

        def capture_put(url, **kwargs):
            captured["content"] = kwargs.get("content")
            return _make_put_response()

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 0), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=capture_put), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(str(f), "pin/key.parquet", "application/octet-stream")

        assert captured["content"] == expected

    def test_temp_file_removed_after_agent_upload(self, tmp_path):
        """The temporary file must be deleted after upload in the executor context."""
        from flow.executor import pin

        f = tmp_path / "pin.parquet"
        f.write_bytes(b"data")

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 0), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", return_value=_make_put_response()), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(str(f), "pin/key.parquet", "application/octet-stream")

        assert not f.exists(), "Arquivo temporário deve ser removido após upload"

    def test_direct_bytes_removes_nothing(self, tmp_path):
        """When content is bytes, no file must be removed."""
        from flow.executor import pin

        sentinel = tmp_path / "nao_deve_ser_removido.txt"
        sentinel.write_text("preservado")

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 0), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", return_value=_make_put_response()), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(b"raw bytes", "pin/key.json", "application/json")

        assert sentinel.exists()


# ── M5: async _render_node_parameters ────────────────────────────────────────

class TestRenderNodeParameters:
    """M5 — _render_node_parameters deve continuar renderizando corretamente via to_thread."""

    def test_jinja2_rendered(self):
        """A simple Jinja2 expression must be processed."""
        executor = _make_executor({"msg": "{{ 1 + 1 }}"})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "2024-01-01",
            "uuid": lambda: "uuid-test",
            "env": {},
        }
        rendered = executor._render_node_parameters("node-1", {}, context)
        assert rendered["msg"] == "2"

    def test_without_jinja2_does_not_modify(self):
        """Parameters without expressions must not be changed."""
        executor = _make_executor({"url": "https://example.com", "count": 42})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "now",
            "uuid": lambda: "u",
            "env": {},
        }
        rendered = executor._render_node_parameters("node-1", {}, context)
        assert rendered["url"] == "https://example.com"
        assert rendered["count"] == 42

    def test_jinja2_via_asyncio_to_thread(self):
        """_render_node_parameters must work correctly when called via asyncio.to_thread."""
        executor = _make_executor({"val": "{{ 3 * 7 }}"})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "now",
            "uuid": lambda: "u",
            "env": {},
        }

        async def run():
            return await asyncio.to_thread(executor._render_node_parameters, "node-1", {}, context)

        rendered = asyncio.run(run())
        assert rendered["val"] == "21"

    def test_invalid_expression_raises_value_error(self):
        """A Jinja2 expression with an undefined variable must raise ValueError."""
        # StrictUndefined makes Jinja2 raise UndefinedError → caught as ValueError
        executor = _make_executor({"x": "{{ variavel_que_nao_existe_xyz }}"})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "now",
            "uuid": lambda: "u",
            "env": {},
        }
        with pytest.raises(ValueError):
            executor._render_node_parameters("node-1", {}, context)


# ── M1: async _spill_to_disk (integrated behavior) ───────────────────────────

class TestSpillToDiskAsync:
    """M1 — _spill_to_disk must be called via asyncio.to_thread (not block the event loop)."""

    # Runs like the production executor (executor/job_executor.py): `run()` on the loop.
    _DEFINICAO = {
        "nodes": [{"id": "m1", "type": "control", "name": "Merge", "properties": {}}],
        "edges": [],
    }

    def test_executor_completes_without_error(self):
        """A minimal workflow must complete without errors after the async changes."""
        from flow.executor import WorkflowExecutor

        executor = WorkflowExecutor(
            self._DEFINICAO, task_id="async-spill-test-001",
            publisher=MagicMock(publish_event=MagicMock()),
        )
        asyncio.run(executor.run(initial_inputs={}))
        assert executor.node_stats["m1"]["status"] == "completed"

    def test_spill_does_not_block_parallel_tasks(self):
        """The spill of the node output goes through asyncio.to_thread."""
        from flow.executor import WorkflowExecutor

        spill_was_called = {"via_thread": False}
        original_to_thread = asyncio.to_thread

        async def spy_to_thread(func, *args, **kwargs):
            if getattr(func, "__name__", "") == "_spill_to_disk":
                spill_was_called["via_thread"] = True
            return await original_to_thread(func, *args, **kwargs)

        executor = WorkflowExecutor(
            self._DEFINICAO, task_id="parallel-spill-test",
            publisher=MagicMock(publish_event=MagicMock()),
        )
        with patch("flow.executor.core.asyncio.to_thread", side_effect=spy_to_thread), \
             patch("flow.executor.spill._SPILL_THRESHOLD_MB", 0):  # 0 = spill disabled, does not test the real path
            asyncio.run(executor.run(initial_inputs={}))
        assert spill_was_called["via_thread"]
