# executor/sync/uploader.py
"""
DriveUploader — sends datasets to the Workspace Drive via pre-signed URLs (MinIO).
Flow: request URL → direct PUT to MinIO → confirm with the API.
"""
import hashlib
import logging
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from executor.sync.http import ClienteHTTP, TIMEOUT_CONTROLE
from executor.sync.paths import is_inside
from executor.sync.pool import em_thread, em_thread_io
from executor.sync.scanner import Dataset

logger = logging.getLogger("executor.sync")

# Chunk size for streaming/hashing. Large enough not to pay context-switch
# overhead per 8 KB, small enough not to hold on to memory.
_CHUNK = 1024 * 1024


@dataclass
class UploadResult:
    """
    Result of a confirmed upload.

    `remote_name` and `remote_md5` describe the OBJECT that was actually sent — which
    for a shapefile is none of the local files, but the `<dataset>.zip`.
    Without these two fields in the manifest, the next `_remote_to_local` saw the zip
    as a new file, downloaded it into the user's folder and collided on the same
    dataset key, destroying 'files'/'local_md5' on every restart.
    """
    id_hash: str
    remote_name: str
    remote_md5: str


class DriveUploader:
    def __init__(self, server_url: str, executor_id: str, workspace_id: str, sync_dir: str | Path):
        from executor.utils import ws_to_http, mtls_httpx_kwargs
        self.base_url = ws_to_http(server_url)
        self.executor_id = executor_id
        self.workspace_id = workspace_id
        self.sync_dir = Path(sync_dir)
        self._httpx_kwargs = mtls_httpx_kwargs(self.base_url)
        self._http = ClienteHTTP(self._httpx_kwargs)

    async def aclose(self):
        """Closes the shared HTTP client (called on manager shutdown)."""
        await self._http.aclose()

    def _headers(self) -> dict:
        """No auth headers — identity comes from the mTLS cert in the TLS handshake."""
        return {}

    @staticmethod
    def remote_name_for(dataset: Dataset) -> str:
        """Name of the object that will be created in the Drive for this dataset."""
        if dataset.type == "shapefile":
            return f"{dataset.name}.zip"
        primary = dataset.primary_path
        return primary.name if primary else dataset.name

    def _contained(self, path: Path, context: str) -> bool:
        """
        Revalidates containment right before opening the file.

        The scanner already skips symlinks, but between the scan and the upload the
        tree may have changed. The download has been contained by `safe_join` from
        the start; the upload had no containment at all — that asymmetry was the
        leak vector.
        """
        if is_inside(self.sync_dir, path):
            return True
        logger.error("Upload de '%s' recusado (%s): o caminho resolvido sai da pasta de sync '%s'.",
                     path.name, context, self.sync_dir)
        return False

    async def upload(self, dataset: Dataset, spatial_metadata: dict | None = None) -> UploadResult | None:
        """
        Uploads a dataset via a pre-signed URL.
        Shapefile: zipped first, sent as .zip.
        Returns UploadResult, or None on failure.
        """
        if dataset.type == "shapefile":
            return await self._upload_shapefile(dataset, spatial_metadata)

        primary = dataset.primary_path
        if not primary:
            logger.warning("Dataset '%s' sem arquivo principal — upload ignorado.", dataset.name)
            return None
        if not self._contained(primary, "arquivo unico"):
            return None
        return await self._upload_file(primary, primary.name, spatial_metadata)

    async def register(self, dataset: Dataset, spatial_metadata: dict | None = None) -> UploadResult | None:
        """Registers the dataset in the Drive WITHOUT sending the bytes (catalog mode).

        For personal data (LGPD): the server gets to know the file — name,
        type, size, CRS, bbox, feature count — and that it is on THIS
        executor, but the content never leaves the machine.

        Returns the same `UploadResult` as `upload()` so the manager treats both
        paths the same way. `remote_md5` is left empty on purpose: there is no
        remote object to compare against, and making up a hash would make the next
        cycle's diff conclude that the file changed.
        """
        primary = dataset.primary_path
        if not primary:
            logger.warning("Dataset '%s' sem arquivo principal — registro ignorado.", dataset.name)
            return None

        # For a shapefile the remote name is the bundle's ('<dataset>.zip'), the same
        # one the upload would use: the Drive shows a single item, and changing the
        # convention here would make the same dataset show up under two names
        # depending on the mode.
        remote_name = self.remote_name_for(dataset)

        corpo = {
            "filename": remote_name,
            "workspace_id": self.workspace_id,
            "size": dataset.total_size,
            "spatial_metadata": spatial_metadata or {},
            # Dataset name in the local manifest. It is how the executor finds the
            # file again on read — no path travels over the wire.
            "dataset_name": dataset.name,
        }

        try:
            resp = await self._http().post(
                f"{self.base_url}/drive/executor-register",
                json=corpo, headers=self._headers(), timeout=TIMEOUT_CONTROLE,
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "Registro de catalogo falhou: HTTP %d — %s",
                    resp.status_code, resp.text[:200],
                )
                return None
            id_hash = resp.json()["id_hash"]
        except Exception as e:
            logger.error("Erro ao registrar '%s' no catalogo: %s", dataset.name, e)
            return None

        logger.info(
            "Catalogado sem enviar conteudo: '%s' → %s (%d bytes ficam no executor)",
            dataset.name, id_hash, dataset.total_size,
        )
        return UploadResult(id_hash=id_hash, remote_name=remote_name, remote_md5="")

    async def delete(self, remote_id_hash: str) -> bool:
        """Removes a file from the Drive. Returns whether the record is NO LONGER there.

        The route is `/drive/executor-file/{id}` — an executor mTLS endpoint, and
        NOT the user's `DELETE /drive/{id}`. The two reasons are the same reason
        every other method of this uploader uses the `executor-` prefix: the bare
        `/drive/{id}` requires a JWT (which the executor does not have) and, on the
        executors host, Traefik only routes `/drive/executor-*` to the API.
        Pointing the deletion at `/drive/{id}` made the request die at Traefik
        with a 404 — the file NEVER left the Drive.

        **404 counts as success.** The goal is "this record must not exist", and
        a 404 from the correct endpoint means it no longer exists (deleted from the
        web Drive, or by an earlier attempt). Treating 404 as a failure created a
        retry that never converges. It is the same policy as the
        `allow_missing=True` the server uses in `delete_strict`.
        """
        url = f"{self.base_url}/drive/executor-file/{remote_id_hash}"
        try:
            resp = await self._http().delete(url, headers=self._headers(),
                                             timeout=TIMEOUT_CONTROLE)
            if resp.status_code in (200, 204):
                logger.info("Arquivo %s removido do Drive.", remote_id_hash)
                return True
            elif resp.status_code == 404:
                logger.info(
                    "Arquivo %s ja nao existia no Drive — nada a remover.",
                    remote_id_hash,
                )
                return True
            else:
                logger.warning("Falha ao remover %s: HTTP %d", remote_id_hash, resp.status_code)
                return False
        except Exception as e:
            logger.error("Erro ao remover %s do Drive: %s", remote_id_hash, e)
            return False

    async def _upload_file(
        self, file_path: Path | None, filename: str, spatial_metadata: dict | None = None,
    ) -> UploadResult | None:
        """Upload via pre-signed URL: pede URL → PUT no MinIO → confirma."""
        if not file_path or not file_path.exists():
            return None

        file_size = file_path.stat().st_size
        # MD5 of the ACTUAL content sent, computed off the event loop. That value is
        # what the server returns as `content_md5` in executor-list, so it is what
        # has to go into the manifest — not the combined hash of the local dataset.
        content_md5 = await em_thread(_file_md5, file_path)

        try:
            # All three steps use the SAME client: each new `AsyncClient`
            # redid the whole mTLS handshake, so a 3 KB file paid
            # ~6 RTTs of TLS alone — the same cost as a 2 GB raster.
            cliente = self._http()

            # 1. Pede pre-signed PUT URL
            resp = await cliente.post(
                f"{self.base_url}/drive/executor-upload-url",
                json={"filename": filename, "size": file_size},
                headers=self._headers(), timeout=TIMEOUT_CONTROLE,
            )
            if resp.status_code not in (200, 201):
                logger.warning("Upload URL falhou: HTTP %d — %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            upload_url = data["upload_url"]
            id_hash = data["id_hash"]

            # 2. Direct PUT to MinIO (no auth headers — pre-signed URL).
            #    Streaming: reading the whole file with f.read() blew the memory
            #    on large rasters/gpkgs AND blocked the event loop. With an
            #    explicit Content-Length httpx does not fall back to
            #    Transfer-Encoding: chunked, which MinIO rejects on a pre-signed URL.
            put_resp = await cliente.put(
                upload_url,
                content=_aiter_file(file_path),
                headers={"Content-Length": str(file_size)},
            )
            if put_resp.status_code not in (200, 201):
                logger.warning("PUT MinIO falhou: HTTP %d", put_resp.status_code)
                return None

            # 3. Confirm the upload with the API
            # CRS, bbox and feature count can only be computed by whoever
            # has the file. They were sent in `register` mode and discarded
            # here, so every dataset synced in the default mode showed up in the
            # Drive with no spatial data at all.
            confirm_resp = await cliente.post(
                f"{self.base_url}/drive/executor-confirm-upload/{id_hash}",
                json={"spatial_metadata": spatial_metadata or {}},
                headers=self._headers(), timeout=TIMEOUT_CONTROLE,
            )
            if confirm_resp.status_code not in (200, 201):
                logger.warning("Confirm falhou: HTTP %d — %s", confirm_resp.status_code, confirm_resp.text[:200])
                return None

            logger.info("Upload OK: '%s' → %s", filename, id_hash)
            return UploadResult(id_hash=id_hash, remote_name=filename, remote_md5=content_md5)

        except Exception as e:
            logger.error("Erro no upload de '%s': %s", filename, e)
            return None

    async def _upload_shapefile(
        self, dataset: Dataset, spatial_metadata: dict | None = None,
    ) -> UploadResult | None:
        """Empacota Shapefile em zip e faz upload."""
        zip_name = self.remote_name_for(dataset)

        # Revalidate EACH component before opening: the bundle is zipped without going
        # through the validator (which only looks at the .shp), so a '.dbf' that
        # became a symlink pointing outside would get into the package unchecked.
        members: list[tuple[Path, str]] = []
        for finfo in dataset.files.values():
            if not self._contained(finfo.path, "componente de shapefile"):
                return None
            members.append((finfo.path, finfo.filename))

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # ZIP_DEFLATED of a large bundle is pure CPU+I/O: running it in the coroutine
            # held up the 30s heartbeat (the executor's only keepalive) and the
            # server closed the connection with 4408, killing the run in progress.
            await em_thread(_write_zip, tmp_path, members)

            logger.info("Shapefile '%s' empacotado (%d arquivos, %d bytes).",
                        dataset.name, len(members), tmp_path.stat().st_size)

            return await self._upload_file(tmp_path, zip_name, spatial_metadata)
        finally:
            tmp_path.unlink(missing_ok=True)


def _write_zip(zip_path: Path, members: list[tuple[Path, str]]):
    """Compresses the members into the zip. Synchronous by nature — call via to_thread."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for source, arcname in members:
            zf.write(source, arcname)


def _file_md5(path: Path) -> str:
    """MD5 of the content. Synchronous by nature — call via to_thread."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


async def _aiter_file(path: Path):
    """Yields the PUT body in chunks, reading the disk off the event loop.

    I/O pool, not the heavy one: in the same 2-thread pool, a `_write_zip` of a
    GB-sized bundle stalled ALL in-flight PUTs for the duration of the compression —
    and MinIO closes idle connections.
    """
    with open(path, "rb") as f:
        while True:
            chunk = await em_thread_io(f.read, _CHUNK)
            if not chunk:
                break
            yield chunk
