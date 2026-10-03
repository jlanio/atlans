# executor/sync/downloader.py
"""
DriveDownloader — lista e baixa arquivos do Drive via pre-signed URLs (MinIO).
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from executor.sync.http import HTTPClient, CONTROL_TIMEOUT
from executor.sync.pool import em_thread_io

logger = logging.getLogger("executor.sync")

# Same chunk as the uploader: writing in 64 KB pieces caused a thread hop
# every 64 KB of raster.
_CHUNK = 1024 * 1024


@dataclass
class RemoteFileInfo:
    """Metadata of a remote file in Drive."""
    id_hash: str
    original_name: str
    extension: str
    size: int
    content_md5: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class DriveDownloader:
    """Downloads files from the Workspace Drive via pre-signed URLs."""

    def __init__(self, server_url: str, executor_id: str, workspace_id: str):
        from executor.utils import ws_to_http, mtls_httpx_kwargs
        self.base_url = ws_to_http(server_url)
        self.executor_id = executor_id
        self.workspace_id = workspace_id
        self._httpx_kwargs = mtls_httpx_kwargs(self.base_url)
        self._http = HTTPClient(self._httpx_kwargs)

    async def aclose(self):
        """Closes the shared HTTP client (called at manager shutdown)."""
        await self._http.aclose()

    def _headers(self) -> dict:
        """No auth headers — identity comes from the mTLS cert."""
        return {}

    async def list_remote(self) -> list[RemoteFileInfo] | None:
        """
        Lists the workspace's files in Drive.
        Returns a list, or None on error.
        """
        try:
            resp = await self._http().get(
                f"{self.base_url}/drive/executor-list",
                params={"workspace_id": self.workspace_id},
                headers=self._headers(), timeout=CONTROL_TIMEOUT,
            )

            if resp.status_code != 200:
                logger.warning("Falha ao listar Drive (HTTP %d): %s", resp.status_code, resp.text[:200])
                return None

            return [
                RemoteFileInfo(
                    id_hash=f["id_hash"],
                    original_name=f["original_name"],
                    extension=f.get("extension", ""),
                    size=f.get("size", 0),
                    content_md5=f.get("content_md5"),
                    created_at=f.get("created_at"),
                    updated_at=f.get("updated_at"),
                )
                for f in resp.json().get("files", [])
            ]

        except Exception as exc:
            logger.error("Erro ao listar Drive: %s", exc)
            return None

    async def download(self, id_hash: str, dest_path: Path) -> bool:
        """Baixa arquivo via pre-signed GET URL do MinIO."""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            cliente = self._http()

            # 1. Pede pre-signed GET URL
            resp = await cliente.get(
                f"{self.base_url}/drive/executor-download/{id_hash}",
                headers=self._headers(), timeout=CONTROL_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning("Falha ao obter download URL '%s' (HTTP %d).", id_hash, resp.status_code)
                return False

            download_url = resp.json().get("download_url")
            if not download_url:
                logger.warning("Resposta sem download_url para '%s'.", id_hash)
                return False

            # 2. Streaming download straight from MinIO.
            #    The write goes to the I/O pool, mirroring the uploader's
            #    `_aiter_file`: with a synchronous `f.write()` in the coroutine,
            #    downloading a large raster held the event loop, the 30s
            #    heartbeat lagged and the connection dropped with 4408 — killing
            #    the run in progress. And it's the I/O pool, not the heavy one:
            #    there, another dataset's zip/validate stalled this download for
            #    minutes.
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            async with cliente.stream("GET", download_url) as stream:
                if stream.status_code != 200:
                    logger.warning("Download MinIO falhou para '%s' (HTTP %d).", id_hash, stream.status_code)
                    return False

                with open(tmp_path, "wb", buffering=_CHUNK) as f:
                    async for chunk in stream.aiter_bytes(chunk_size=_CHUNK):
                        await em_thread_io(f.write, chunk)

            # Across volumes the rename becomes a copy — it can't stay on the loop.
            await em_thread_io(os.replace, str(tmp_path), str(dest_path))
            logger.info("Arquivo '%s' baixado para '%s'.", id_hash[:8], dest_path.name)
            return True

        except Exception as exc:
            logger.error("Erro ao baixar '%s': %s", id_hash, exc)
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            return False
