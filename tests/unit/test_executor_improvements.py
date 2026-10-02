# tests/unit/test_executor_improvements.py
"""
Testes unitários para as melhorias de performance e resiliência em flow/executor.py:

  M1 — _spill_to_disk assíncrono (asyncio.shield + to_thread)
  M2 — Unicidade dos arquivos de spill (sufixo UUID)
  M3 — Timeouts configuráveis via env vars
  M4 — Retry com backoff exponencial no upload httpx
  M5 — _render_node_parameters assíncrono (to_thread)
  M6 — Temp file em vez de BytesIO em _upload_pin_artifact
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
    """Cria WorkflowExecutor mínimo com um nó Merge conectado a um trigger.
    A edge é necessária para que node-1 não seja filtrado por filter_isolated=True."""
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


# ── M3: Timeouts configuráveis ────────────────────────────────────────────────

class TestTimeoutConstants:
    """M3 — Constantes de timeout devem existir e ter os defaults corretos."""

    def test_constantes_existem(self):
        import flow.executor.pin as mod
        assert hasattr(mod, "_PIN_PRESIGN_TIMEOUT")
        assert hasattr(mod, "_PIN_UPLOAD_TIMEOUT")
        assert hasattr(mod, "_PIN_RETRY_COUNT")
        assert hasattr(mod, "_PIN_RETRY_MAX_DELAY")

    def test_defaults(self):
        import flow.executor.pin as mod
        # Defaults esperados quando env vars não estão definidas
        assert mod._PIN_PRESIGN_TIMEOUT == int(os.getenv("PIN_PRESIGN_TIMEOUT", "15"))
        assert mod._PIN_UPLOAD_TIMEOUT == int(os.getenv("PIN_UPLOAD_TIMEOUT", "120"))
        assert mod._PIN_RETRY_COUNT == int(os.getenv("PIN_UPLOAD_MAX_RETRIES", "2"))
        assert mod._PIN_RETRY_MAX_DELAY == int(os.getenv("PIN_UPLOAD_RETRY_MAX_DELAY", "30"))

    def test_env_var_lida_no_import(self, monkeypatch):
        """Após reload com env var customizada, a constante deve refletir o valor."""
        import importlib
        import flow.executor.pin as pin_mod

        monkeypatch.setenv("PIN_PRESIGN_TIMEOUT", "7")
        monkeypatch.setenv("PIN_UPLOAD_TIMEOUT", "45")
        importlib.reload(pin_mod)

        assert pin_mod._PIN_PRESIGN_TIMEOUT == 7
        assert pin_mod._PIN_UPLOAD_TIMEOUT == 45

        # Cleanup: restaura defaults para não afetar outros testes
        monkeypatch.delenv("PIN_PRESIGN_TIMEOUT", raising=False)
        monkeypatch.delenv("PIN_UPLOAD_TIMEOUT", raising=False)
        importlib.reload(pin_mod)


# ── M2: UUID suffix no nome do arquivo de spill ───────────────────────────────

class TestSpillFileUniqueness:
    """M2 — Arquivos de spill devem ter sufixo UUID para evitar colisões."""

    def test_padrao_do_nome_tem_sufixo_hex(self):
        """O padrão node_key_<8hex>.parquet deve ser válido."""
        import uuid
        node_id = "nó-abc"
        key = "output"
        suffix = uuid.uuid4().hex[:8]
        filename = f"{node_id}_{key}_{suffix}.parquet"
        assert re.search(r"[0-9a-f]{8}\.parquet$", filename), (
            f"'{filename}' não termina com 8 chars hex + .parquet"
        )

    def test_dois_sufixos_consecutivos_sao_distintos(self):
        """Dois UUIDs gerados seguidos devem ser diferentes (probabilidade astronomicamente alta)."""
        import uuid
        s1 = uuid.uuid4().hex[:8]
        s2 = uuid.uuid4().hex[:8]
        assert s1 != s2

    def test_spill_gera_paths_unicos_para_mesmo_no(self, tmp_path, monkeypatch):
        """_spill_to_disk chamado duas vezes para o mesmo nó gera paths distintos."""
        import geopandas as gpd
        from shapely.geometry import Point
        import flow.executor.spill as spill

        # O patch vai no módulo que LÊ as constantes. Teto ínfimo: qualquer
        # GeoDataFrame passa dele e é gravado de verdade em tmp_path.
        monkeypatch.setattr(spill, "_SPILL_BASE_DIR", str(tmp_path))
        monkeypatch.setattr(spill, "_SPILL_THRESHOLD_MB", 1e-9)

        gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")
        paths_gravados = [
            spill._spill_to_disk("task-999", "node-X", {"data": gdf})["data"]["__spill_path__"]
            for _ in range(2)
        ]

        assert paths_gravados[0] != paths_gravados[1], (
            "Dois spills do mesmo nó devem gerar paths únicos"
        )
        for p in paths_gravados:
            basename = os.path.basename(p)
            assert re.match(r"node-X_data_[0-9a-f]{8}\.parquet$", basename), (
                f"'{basename}' não segue o padrão node_key_<8hex>.parquet"
            )


# ── M4: Retry com backoff exponencial ────────────────────────────────────────

class TestUploadPinRetry:
    """M4 — upload_pin_to_minio deve retentar com backoff exponencial."""

    @pytest.fixture(autouse=True)
    def agent_env(self, monkeypatch):
        monkeypatch.setenv("EXECUTOR_ID", "executor-test-001")
        monkeypatch.setenv("EXECUTOR_API_KEY", "test-key")
        monkeypatch.setenv("EXECUTOR_SERVER_URL", "http://localhost:8000")

    def test_sucesso_sem_retry(self):
        """Upload bem-sucedido na 1ª tentativa não deve chamar time.sleep."""
        from flow.executor import pin

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 2), \
             patch("time.sleep") as mock_sleep, \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", return_value=_make_put_response()), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(b"data", "key.json", "application/json")

        mock_sleep.assert_not_called()

    def test_retenta_apos_falha_transitoria(self):
        """Falha na 1ª tentativa do PUT deve disparar retry e ter sucesso na 2ª."""
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
        # Faixa, e nao valor exato: a espera passou a ser dispersa em 50-100%
        # (ver flow/utils/backoff.py). Cravar `== 1` aqui era cravar a ausencia
        # de jitter, que e justamente o defeito — dois executores que falhavam
        # no mesmo instante retentavam no mesmo instante.
        mock_sleep.assert_called_once()
        (espera,), _ = mock_sleep.call_args
        assert 0.5 <= espera <= 1.0

    def test_levanta_excecao_ao_esgotar_retries(self):
        """Após esgotar _PIN_RETRY_COUNT tentativas, deve re-lançar a última exceção."""
        from flow.executor import pin

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 2), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", side_effect=OSError("Storage indisponível")), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            with pytest.raises(OSError, match="Storage indisponível"):
                pin.upload_pin_to_minio(b"data", "key.json", "application/json")

    def test_backoff_exponencial(self):
        """A espera deve dobrar a cada tentativa, dentro da faixa do jitter."""
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

        # 3 retries → 3 sleeps. Com jitter proporcional de 50-100%, cada espera
        # cai na faixa [0,5 x 2^k, 2^k]: [0,5–1], [1–2], [2–4]. As faixas se
        # tocam mas nao se sobrepoem, entao a sequencia continua nao-decrescente
        # — o crescimento exponencial segue verificavel sem cravar o valor.
        assert len(sleep_delays) == 3
        for k, espera in enumerate(sleep_delays):
            assert 0.5 * (2 ** k) <= espera <= 2 ** k, (k, espera)
        assert sleep_delays == sorted(sleep_delays)

    def test_backoff_respeitado_cap(self):
        """O delay não deve ultrapassar _PIN_RETRY_MAX_DELAY."""
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


# ── M6: Temp file em vez de BytesIO ──────────────────────────────────────────

class TestUploadPinWithPath:
    """M6 — upload_pin_to_minio deve aceitar path de arquivo (str) além de bytes."""

    @pytest.fixture(autouse=True)
    def agent_env(self, monkeypatch):
        monkeypatch.setenv("EXECUTOR_ID", "executor-test-001")
        monkeypatch.setenv("EXECUTOR_API_KEY", "test-key")
        monkeypatch.setenv("EXECUTOR_SERVER_URL", "http://localhost:8000")

    def test_path_e_lido_e_bytes_enviados(self, tmp_path):
        """Quando content é um path (str), os bytes do arquivo devem ser enviados no PUT."""
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

    def test_arquivo_temp_removido_apos_upload_agente(self, tmp_path):
        """O arquivo temporário deve ser deletado após upload no contexto executor."""
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

    def test_bytes_direto_nao_remove_nada(self, tmp_path):
        """Quando content é bytes, nenhum arquivo deve ser removido."""
        from flow.executor import pin

        sentinela = tmp_path / "nao_deve_ser_removido.txt"
        sentinela.write_text("preservado")

        with patch("flow.executor.pin._PIN_RETRY_COUNT", 0), \
             patch("time.sleep"), \
             patch("httpx.post", return_value=_make_presign_response()), \
             patch("httpx.put", return_value=_make_put_response()), \
             patch("flow.utils.executor_http.get_agent_http_config",
                   return_value=("http://localhost:8000", {}, True)):
            pin.upload_pin_to_minio(b"raw bytes", "pin/key.json", "application/json")

        assert sentinela.exists()


# ── M5: _render_node_parameters assíncrono ───────────────────────────────────

class TestRenderNodeParameters:
    """M5 — _render_node_parameters deve continuar renderizando corretamente via to_thread."""

    def test_jinja2_renderizado(self):
        """Expressão Jinja2 simples deve ser processada."""
        executor = _make_executor({"msg": "{{ 1 + 1 }}"})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "2024-01-01",
            "uuid": lambda: "uuid-test",
            "env": {},
        }
        rendered = executor._render_node_parameters("node-1", {}, context)
        assert rendered["msg"] == "2"

    def test_sem_jinja2_nao_modifica(self):
        """Parâmetros sem expressões não devem ser alterados."""
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
        """_render_node_parameters deve funcionar corretamente quando chamado via asyncio.to_thread."""
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

    def test_expressao_invalida_levanta_value_error(self):
        """Expressão Jinja2 com variável indefinida deve lançar ValueError."""
        # StrictUndefined faz o Jinja2 lançar UndefinedError → capturado como ValueError
        executor = _make_executor({"x": "{{ variavel_que_nao_existe_xyz }}"})
        context = {
            "inputs": {}, "nodes": {}, "named": {},
            "now": lambda fmt=None: "now",
            "uuid": lambda: "u",
            "env": {},
        }
        with pytest.raises(ValueError):
            executor._render_node_parameters("node-1", {}, context)


# ── M1: _spill_to_disk assíncrono (comportamento integrado) ──────────────────

class TestSpillToDiskAsync:
    """M1 — _spill_to_disk deve ser chamado via asyncio.to_thread (não bloquear o event loop)."""

    # Roda como o executor de produção (executor/job_executor.py): `run()` no loop.
    _DEFINICAO = {
        "nodes": [{"id": "m1", "type": "control", "name": "Merge", "properties": {}}],
        "edges": [],
    }

    def test_executor_completa_sem_erro(self):
        """Workflow mínimo deve completar sem erros após as alterações async."""
        from flow.executor import WorkflowExecutor

        executor = WorkflowExecutor(
            self._DEFINICAO, task_id="async-spill-test-001",
            publisher=MagicMock(publish_event=MagicMock()),
        )
        asyncio.run(executor.run(initial_inputs={}))
        assert executor.node_stats["m1"]["status"] == "completed"

    def test_spill_nao_bloqueia_tarefas_paralelas(self):
        """O spill do output do nó passa por asyncio.to_thread."""
        from flow.executor import WorkflowExecutor

        spill_foi_chamado = {"via_thread": False}
        original_to_thread = asyncio.to_thread

        async def spy_to_thread(func, *args, **kwargs):
            if getattr(func, "__name__", "") == "_spill_to_disk":
                spill_foi_chamado["via_thread"] = True
            return await original_to_thread(func, *args, **kwargs)

        executor = WorkflowExecutor(
            self._DEFINICAO, task_id="parallel-spill-test",
            publisher=MagicMock(publish_event=MagicMock()),
        )
        with patch("flow.executor.core.asyncio.to_thread", side_effect=spy_to_thread), \
             patch("flow.executor.spill._SPILL_THRESHOLD_MB", 0):  # 0 = spill desabilitado, não testa o path real
            asyncio.run(executor.run(initial_inputs={}))
        assert spill_foi_chamado["via_thread"]
