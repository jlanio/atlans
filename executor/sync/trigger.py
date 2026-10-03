# executor/sync/trigger.py
"""
SyncTrigger — dispara workflows automaticamente apos sync de arquivos.
Configurado via EXECUTOR_SYNC_TRIGGERS (JSON).
"""
import fnmatch
import json
import logging

from executor.sync.http import HTTPClient, CONTROL_TIMEOUT

logger = logging.getLogger("executor.sync")


class SyncTrigger:
    """
    Dispara workflows apos sync bem-sucedido.

    Config (env EXECUTOR_SYNC_TRIGGERS):
    [
        {
            "pattern": "*.geojson",
            "workflow_id_hash": "abc123",
            "inputs": {"file_name": "{{original_name}}"}
        }
    ]
    """

    def __init__(self, server_url: str, executor_id: str):
        from executor.utils import ws_to_http, mtls_httpx_kwargs
        self._base_url = ws_to_http(server_url)
        self._agent_id = executor_id
        self._httpx_kwargs = mtls_httpx_kwargs(self._base_url)
        self._http = HTTPClient(self._httpx_kwargs)
        self._triggers = self._load_triggers()

    async def aclose(self):
        """Closes the shared HTTP client (called at manager shutdown)."""
        await self._http.aclose()

    @property
    def enabled(self) -> bool:
        return len(self._triggers) > 0

    def _load_triggers(self) -> list[dict]:
        from executor import config
        raw = config.SYNC_TRIGGERS.strip()
        if not raw:
            return []
        try:
            triggers = json.loads(raw)
            if isinstance(triggers, list):
                logger.info("SyncTrigger: %d trigger(s) configurado(s).", len(triggers))
                return triggers
        except json.JSONDecodeError as e:
            logger.warning("EXECUTOR_SYNC_TRIGGERS JSON invalido: %s", e)
        return []

    def _headers(self) -> dict:
        """No auth headers — identity comes from the mTLS cert."""
        return {}

    async def on_file_synced(self, dataset_name: str, remote_info: dict):
        """Verifica triggers e dispara workflows correspondentes."""
        if not self._triggers:
            return

        original_name = remote_info.get("original_name", dataset_name)

        for trigger in self._triggers:
            pattern = trigger.get("pattern", "")
            wf_hash = trigger.get("workflow_id_hash", "")
            if not pattern or not wf_hash:
                continue

            if fnmatch.fnmatch(original_name, pattern) or fnmatch.fnmatch(dataset_name, pattern):
                inputs = self._resolve_inputs(trigger.get("inputs", {}), remote_info, dataset_name)
                await self._execute_workflow(wf_hash, inputs)

    def _resolve_inputs(self, template: dict, remote_info: dict, dataset_name: str) -> dict:
        """Replaces {{key}} placeholders in the inputs."""
        resolved = {}
        context = {
            "dataset_name": dataset_name,
            "original_name": remote_info.get("original_name", dataset_name),
            "id_hash": remote_info.get("id_hash", ""),
            "extension": remote_info.get("extension", ""),
            "size": str(remote_info.get("size", 0)),
        }
        for key, val in template.items():
            if isinstance(val, str):
                for ctx_key, ctx_val in context.items():
                    val = val.replace("{{" + ctx_key + "}}", str(ctx_val))
            resolved[key] = val
        return resolved

    async def _execute_workflow(self, workflow_id_hash: str, inputs: dict):
        """Dispara execucao do workflow via API."""
        url = f"{self._base_url}/drive/executor-trigger-workflow"
        try:
            resp = await self._http().post(
                url,
                json={"workflow_id_hash": workflow_id_hash, "inputs": inputs},
                headers=self._headers(), timeout=CONTROL_TIMEOUT,
            )

            if resp.status_code in (200, 201, 202):
                logger.info("Workflow '%s' disparado com sucesso apos sync.", workflow_id_hash[:8])
            else:
                logger.warning("Falha ao disparar workflow '%s': HTTP %d — %s",
                               workflow_id_hash[:8], resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.error("Erro ao disparar workflow '%s': %s", workflow_id_hash[:8], exc)
