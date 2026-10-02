# executor/sync/downloader.py
"""
DriveDownloader — lista e baixa arquivos do Drive via pre-signed URLs (MinIO).
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from executor.sync.http import ClienteHTTP, TIMEOUT_CONTROLE
from executor.sync.pool import em_thread_io

logger = logging.getLogger("executor.sync")

# Mesmo chunk do uploader: escrever em pedacos de 64 KB fazia um salto de thread
# a cada 64 KB de raster.
_CHUNK = 1024 * 1024


@dataclass
class RemoteFileInfo:
    """Metadados de um arquivo remoto no Drive."""
    id_hash: str
    original_name: str
    extension: str
    size: int
    content_md5: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class DriveDownloader:
    """Baixa arquivos do Drive do Workspace via pre-signed URLs."""

    def __init__(self, server_url: str, executor_id: str, workspace_id: str):
        from executor.utils import ws_to_http, mtls_httpx_kwargs
        self.base_url = ws_to_http(server_url)
        self.executor_id = executor_id
        self.workspace_id = workspace_id
        self._httpx_kwargs = mtls_httpx_kwargs(self.base_url)
        self._http = ClienteHTTP(self._httpx_kwargs)

    async def aclose(self):
        """Fecha o cliente HTTP compartilhado (chamado no shutdown do manager)."""
        await self._http.aclose()

    def _headers(self) -> dict:
        """Sem headers de auth — identidade vem do cert mTLS."""
        return {}

    async def list_remote(self) -> list[RemoteFileInfo] | None:
        """
        Lista arquivos do workspace no Drive.
        Retorna lista ou None em caso de erro.
        """
        try:
            resp = await self._http().get(
                f"{self.base_url}/drive/executor-list",
                params={"workspace_id": self.workspace_id},
                headers=self._headers(), timeout=TIMEOUT_CONTROLE,
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
                headers=self._headers(), timeout=TIMEOUT_CONTROLE,
            )
            if resp.status_code != 200:
                logger.warning("Falha ao obter download URL '%s' (HTTP %d).", id_hash, resp.status_code)
                return False

            download_url = resp.json().get("download_url")
            if not download_url:
                logger.warning("Resposta sem download_url para '%s'.", id_hash)
                return False

            # 2. Download streaming direto do MinIO.
            #    A gravacao vai para o pool de I/O, espelhando o `_aiter_file`
            #    do uploader: com `f.write()` sincrono na corrotina, baixar um
            #    raster grande segurava o event loop, o heartbeat de 30s
            #    atrasava e a conexao caia com 4408 — matando o run em curso. E
            #    e o pool de I/O, nao o pesado: la o zip/validate de outro
            #    dataset parava este download por minutos.
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            async with cliente.stream("GET", download_url) as stream:
                if stream.status_code != 200:
                    logger.warning("Download MinIO falhou para '%s' (HTTP %d).", id_hash, stream.status_code)
                    return False

                with open(tmp_path, "wb", buffering=_CHUNK) as f:
                    async for chunk in stream.aiter_bytes(chunk_size=_CHUNK):
                        await em_thread_io(f.write, chunk)

            # Entre volumes o rename vira copia — nao pode ficar no loop.
            await em_thread_io(os.replace, str(tmp_path), str(dest_path))
            logger.info("Arquivo '%s' baixado para '%s'.", id_hash[:8], dest_path.name)
            return True

        except Exception as exc:
            logger.error("Erro ao baixar '%s': %s", id_hash, exc)
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            return False
