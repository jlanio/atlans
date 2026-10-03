# app/services/drive_service.py
"""Drive service — business logic for file management via MinIO."""
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage as s3
from app.core.drive_events import emit_drive_event
from app.core.utils.busca import contem
from app.core.utils.datetime_utils import utc_now_naive
from app.core.exceptions import (
    DuplicateResourceError,
    FileTooLargeError,
    FileNotFoundError,
    DangerousInnerExtensionError,
    EmptyFileError,
    FileExtensionNotAllowedError,
    ConteudoNoExecutorError,
    InvalidFileOperationError,
    WorkflowNotFoundError,
    WorkspaceAccessDeniedError,
)
from app.core.rbac import ROLE_EDITOR
from app.core.utils.logger import get_logger
from app.models.platform_file_settings import PlatformFileSettings, AllowedFileExtension
from app.models.workspace_file import WorkspaceFile

logger = get_logger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]")
_DEFAULT_EXTENSIONS = ["csv", "geojson", "json", "kml", "gpkg", "shp", "dbf", "prj", "shx"]
_DANGEROUS_EXTS = frozenset({"php", "exe", "bat", "cmd", "sh", "ps1", "py", "rb", "pl", "cgi", "asp", "aspx", "jsp"})


# ── Helpers puros ─────────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """Strict ASCII slug — used in the S3 KEY, where the restricted alphabet matters.

    Do not use for `original_name`: it destroys accents and spaces in the name
    the user sees (`área de risco.gpkg` -> `_rea_de_risco.gpkg`). That is what
    `safe_display_name` is for.
    """
    # Normalizes Windows separators (\) to POSIX (/) before extracting the basename
    name = os.path.basename(name.replace("\\", "/"))
    name = _SLUG_RE.sub("_", name)
    return name[:200] or "arquivo"


# Control characters + quotes and ';' — the last two would break the
# `Content-Disposition: attachment; filename="..."` generated in the presigned GET.
_UNSAFE_DISPLAY_RE = re.compile(r'[\x00-\x1f\x7f";\\/]')


def safe_display_name(name: str) -> str:
    """Safe basename PRESERVING accents and spaces — for `original_name`.

    SEC: ALWAYS apply before persisting into `WorkspaceFile.original_name`.
    That field is propagated to the executor via `emit_drive_event` and used as
    the write destination in GeoSync (`sync_dir / original_name`) — a name like
    `../../../etc/x.geojson`, or an absolute path, escaped the synced directory
    and became an arbitrary file write on the executor's host.

    What is removed: path components, separators, control characters and the
    ones that would break the Content-Disposition header. What is preserved:
    everything else, Unicode included — over-sanitizing here would only degrade
    the name displayed in the UI with no security gain.
    """
    # Normalizes Windows separators (\) to POSIX (/) before extracting the basename
    name = os.path.basename(name.replace("\\", "/"))
    name = _UNSAFE_DISPLAY_RE.sub("_", name)
    # '.' e '..' viram nomes de arquivo comuns; dotfiles continuam permitidos.
    if name.strip() in ("", ".", ".."):
        return "arquivo"
    return name[:200]


def make_s3_key(workspace_id: str, original_name: str, prefix: str = "drive") -> str:
    sanitized = sanitize_name(original_name)
    file_id = str(uuid4())
    return f"{prefix}/{workspace_id}/{file_id}_{sanitized}"


def file_or_404(wf):
    if wf is None:
        raise FileNotFoundError("Arquivo nao encontrado.")
    return wf


def _recusar_se_local(wf) -> None:
    """Blocks READING, by the platform, of content that lives on the executor.

    There is no object in storage. Proxying the download would bring the data to
    the server, which is exactly what the locality policy forbids — and without
    the guard the call dies in boto3 with a silent 500.
    """
    if getattr(wf, "content_location", "minio") != "executor":
        return
    raise ConteudoNoExecutorError(
        "O conteudo deste arquivo permanece no executor e nunca foi enviado "
        "para a nuvem, entao nao ha o que baixar pela plataforma. Ele continua "
        "disponivel para workflows que rodem naquele mesmo executor."
    )


def _recusar_se_catalogado(wf) -> None:
    """Blocks destructive operations on a file that only exists on the executor.

    A cataloged file (GeoSync in "Manter apenas no executor" (keep only on the
    executor) mode) has `s3_key = NULL`: the platform keeps the record, never the
    bytes. Deleting this record would remove nothing from the disk of whoever has
    the file, and telling the executor to delete it would be destroying user data
    that never belonged to the platform.

    The way out is in the message, and not in an "are you sure?": whoever wants
    the file gone deletes the file, or removes the folder from GeoSync.
    """
    if getattr(wf, "content_location", "minio") != "executor":
        return
    raise ConteudoNoExecutorError(
        "Este registro reflete um arquivo que permanece no executor e nunca foi "
        "enviado para a nuvem — exclui-lo aqui nao apagaria o arquivo. Para "
        "remove-lo, apague o arquivo na pasta sincronizada do executor, ou tire "
        "essa pasta do GeoSync."
    )


# ── DriveService ──────────────────────────────────────────────────────────────

class DriveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Configuracoes e extensoes ─────────────────────────────────────────

    async def get_settings(self) -> PlatformFileSettings:
        result = await self.db.execute(select(PlatformFileSettings).where(PlatformFileSettings.id == 1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = PlatformFileSettings(id=1, max_size_mb=200)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def get_allowed_extensions(self) -> set[str]:
        await self._seed_extensions_if_empty()
        result = await self.db.execute(
            select(AllowedFileExtension.extension).where(AllowedFileExtension.enabled == True)  # noqa: E712
        )
        return {row[0] for row in result.all()}

    async def _seed_extensions_if_empty(self):
        count = (await self.db.execute(sa_func.count(AllowedFileExtension.id))).scalar() or 0
        if count == 0:
            for ext in _DEFAULT_EXTENSIONS:
                self.db.add(AllowedFileExtension(extension=ext))
            await self.db.commit()

    # ── Validacao ─────────────────────────────────────────────────────────

    async def validate_upload(self, filename: str, size: int) -> str:
        """Validates extension (including double extension) and size. Returns the extension.

        Each rejection has its own subclass of `FileValidationError` (and its own
        `error_code`): it is by the code, not by the sentence, that the web app
        classifies it.
        """
        ext = Path(filename).suffix.lstrip(".").lower()
        if not ext:
            raise FileExtensionNotAllowedError("Arquivo sem extensao.")

        # Bloqueia double extensions (ex: file.php.csv, file.exe.json)
        stem = Path(filename).stem
        if "." in stem:
            inner_ext = stem.rsplit(".", 1)[-1].lower()
            if inner_ext in _DANGEROUS_EXTS:
                raise DangerousInnerExtensionError(f"Nome de arquivo com extensao interna perigosa: '.{inner_ext}'.")

        allowed = await self.get_allowed_extensions()
        if ext not in allowed:
            raise FileExtensionNotAllowedError(f"Extensao '.{ext}' nao permitida.")

        settings = await self.get_settings()
        max_bytes = settings.max_size_mb * 1024 * 1024
        if size > max_bytes:
            raise FileTooLargeError(f"Arquivo excede {settings.max_size_mb}MB.")

        return ext

    # ── Listagem ──────────────────────────────────────────────────────────

    async def list_files(
        self,
        workspace_id: str,
        search: Optional[str] = None,
        ext: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WorkspaceFile], int]:
        """Returns a tuple (items, total) of the workspace's confirmed files."""
        query = select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.status == "confirmed",
        )
        count_query = select(sa_func.count(WorkspaceFile.id)).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.status == "confirmed",
        )

        if search:
            # The user's `%` and `_` are literals, not wildcards (see `contem`).
            nome_contem = contem(WorkspaceFile.original_name, search)
            query = query.where(nome_contem)
            count_query = count_query.where(nome_contem)
        if ext:
            query = query.where(WorkspaceFile.extension == ext.lower())
            count_query = count_query.where(WorkspaceFile.extension == ext.lower())

        total = (await self.db.execute(count_query)).scalar() or 0
        # Sorts by LAST WRITE. An overwritten file keeps its original
        # created_at — sorting by it would make freshly written content
        # show up at the end of the list, together with the oldest files.
        # coalesce covers rows that were never updated (updated_at NULL).
        ultima_escrita = sa_func.coalesce(
            WorkspaceFile.content_written_at, WorkspaceFile.created_at
        )
        query = query.order_by(ultima_escrita.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.db.execute(query)).scalars().all()

        return items, total

    async def list_files_for_agent(self, workspace_id: str) -> list[dict]:
        """Returns a simplified list of confirmed files (for executors)."""
        result = await self.db.execute(
            select(
                WorkspaceFile.id_hash, WorkspaceFile.original_name,
                WorkspaceFile.extension, WorkspaceFile.size,
                WorkspaceFile.content_md5, WorkspaceFile.created_at, WorkspaceFile.updated_at,
            ).where(
                WorkspaceFile.workspace_id == workspace_id,
                WorkspaceFile.status == "confirmed",
            ).order_by(
                sa_func.coalesce(
                    WorkspaceFile.content_written_at, WorkspaceFile.created_at
                ).desc()
            )
        )

        return [{
            "id_hash": r.id_hash, "original_name": r.original_name,
            "extension": r.extension, "size": r.size,
            "content_md5": r.content_md5,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        } for r in result.all()]

    # ── Upload multipart ──────────────────────────────────────────────────

    async def upload_file(
        self,
        workspace_id: str,
        original_name: str,
        content: bytes,
        uploaded_by: str,
    ) -> WorkspaceFile:
        """Faz upload multipart direto ao MinIO e cria registro confirmado."""
        if len(content) == 0:
            raise EmptyFileError("Arquivo vazio.")

        original_name = safe_display_name(original_name)
        ext = await self.validate_upload(original_name, len(content))
        mime_type, _ = mimetypes.guess_type(original_name)
        s3_key = make_s3_key(workspace_id, original_name)

        # Direct upload to MinIO
        content_md5 = await s3.upload_async(s3_key, content, content_type=mime_type or "application/octet-stream")

        wf = WorkspaceFile(
            workspace_id=workspace_id,
            s3_key=s3_key,
            original_name=original_name,
            extension=ext,
            mime_type=mime_type,
            size=len(content),
            content_md5=content_md5,
            uploaded_by=uploaded_by,
            status="confirmed",
        )
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)

        await emit_drive_event(workspace_id, "file_created", {
            "id_hash": wf.id_hash, "original_name": wf.original_name,
            "extension": wf.extension, "size": wf.size, "content_md5": wf.content_md5,
        })

        return wf

    # ── Upload via presigned URL ──────────────────────────────────────────

    async def create_upload_url(
        self,
        workspace_id: str,
        filename: str,
        size: int,
        uploaded_by: str,
    ) -> dict:
        """Cria registro pendente e gera presigned PUT URL."""
        filename = safe_display_name(filename)
        ext = await self.validate_upload(filename, size)
        mime_type, _ = mimetypes.guess_type(filename)
        s3_key = make_s3_key(workspace_id, filename)

        wf = WorkspaceFile(
            workspace_id=workspace_id,
            s3_key=s3_key,
            original_name=filename,
            extension=ext,
            mime_type=mime_type,
            size=size,
            uploaded_by=uploaded_by,
            status="pending",
        )
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)

        upload_url = await s3.presigned_put_async(s3_key, content_type=mime_type or "application/octet-stream")
        return {"upload_url": upload_url, "id_hash": wf.id_hash, "s3_key": s3_key}

    async def create_agent_upload_url(
        self,
        workspace_id: str,
        filename: str,
        size: int,
        uploaded_by: str,
        s3_key_override: Optional[str] = None,
        content_type_override: Optional[str] = None,
        overwrite: bool = False,
    ) -> dict:
        """Creates a pending record and generates a presigned PUT URL (for executors).

        `overwrite=True` reuses the file with the same name that already exists
        in the workspace instead of creating another. Without it, a scheduled
        DataOutput piled up one copy per run, all with the same name in the Drive.

        Reusing means keeping the SAME row and the SAME s3_key:

        - the `id_hash` does not change, so a DataInput pointing to this file
          stays valid and starts reading the new version — recreating the row
          would make the reference point forever to the old content;
        - the preserved s3_key makes the PUT overwrite the object in MinIO,
          without leaving the previous one orphaned taking up disk.
        """
        filename = safe_display_name(filename)
        # Artifact uploads (s3_key_override) skip the Drive's extension validation
        if s3_key_override:
            ext = Path(filename).suffix.lstrip(".").lower() if filename else ""
        else:
            ext = await self.validate_upload(filename, size)

        mime_type, _ = mimetypes.guess_type(filename)
        s3_key = s3_key_override or make_s3_key(workspace_id, filename)
        # Uses the body's content_type (the executor sends the exact type) or one detected via mimetypes
        final_ct = content_type_override or mime_type or "application/octet-stream"

        wf = None
        if overwrite:
            # Most recent among the confirmed ones: if there are already duplicates
            # from previous runs, it overwrites the one the user sees at the top
            # of the listing and leaves the old ones intact for manual removal.
            existente = await self.db.execute(
                select(WorkspaceFile)
                .where(
                    WorkspaceFile.workspace_id == workspace_id,
                    WorkspaceFile.original_name == filename,
                    WorkspaceFile.status == "confirmed",
                )
                .order_by(WorkspaceFile.created_at.desc())
                .limit(1)
            )
            wf = existente.scalar_one_or_none()

        reaproveitou = wf is not None
        if wf is not None:
            s3_key = wf.s3_key          # PUT sobrescreve o objeto existente

            # Does NOT go back to "pending" and does NOT touch `size`. Marking it
            # pending took the file out of the listing during the upload and,
            # worse, made it eligible for cleanup_pending_workspace_files, which
            # deletes pending rows with created_at older than the TTL — and the
            # created_at here is that of the ORIGINAL creation, already expired
            # on any file older than 24h. A failed upload would destroy the
            # intact file that existed. The PUT to MinIO is atomic: either it
            # replaces the whole thing, or the previous content remains.
            # size/content_md5 are updated in confirm_upload, from the real object.
            wf.mime_type = final_ct
            wf.uploaded_by = uploaded_by
        else:
            wf = WorkspaceFile(
                workspace_id=workspace_id,
                s3_key=s3_key,
                original_name=filename,
                extension=ext,
                mime_type=final_ct,
                size=size,
                uploaded_by=uploaded_by,
                status="pending",
            )
            self.db.add(wf)

        await self.db.commit()
        await self.db.refresh(wf)

        # Pre-signed URL for the executor (uses MINIO_EXTERNAL_ENDPOINT, reachable outside Docker)
        upload_url = await s3.presigned_put_async(s3_key, content_type=final_ct)
        # `reused` tells the caller what actually happened. Without it the executor
        # could only repeat the intent ("I asked to overwrite"), never the
        # outcome — and an overwrite that did not find the file was
        # indistinguishable from one that did.
        return {
            "upload_url": upload_url,
            "id_hash": wf.id_hash,
            "s3_key": s3_key,
            "reused": reaproveitou,
        }

    # ── Upload confirmation ───────────────────────────────────────────────

    def _e_upload_de_drive_pendente(self, wf: WorkspaceFile) -> bool:
        """Is the confirm closing a Drive upload that has not been accepted yet?

        Only that case can be rejected destructively, and the scope is narrow on
        purpose — each condition here prevents concrete damage:

        - `status == "pending"`: the row was created for THIS upload and never
          appeared in the listing. Without it, `confirm_upload` — which does not
          filter by status and is reachable by any editor of the workspace —
          would become a delete button: re-confirming someone else's already
          accepted file that was above the CURRENT ceiling (the admin may have
          lowered `max_size_mb` later) would be enough for the object and the
          record to vanish.
        - key under `drive/`: run artifacts come in through
          `create_agent_upload_url(s3_key_override=...)`, which skips
          `validate_upload` ENTIRELY — extension and size. There was never a
          ceiling for them, and applying it now would bring down the run (the
          executor does `raise_for_status` on the confirm) and, with
          `overwrite=True`, would delete the good file that was in the Drive.
          The ceiling here exists to mirror the validation of the DECLARED
          size; where there was no validated declaration, there is nothing to
          recheck.
        - the key's workspace equal to the row's: `_validate_agent_s3_key`
          checks the key against ALL of the executor's workspaces, not against
          the row's, so an `s3_key_override` can point to another workspace's
          object. Deleting through that path would destroy someone else's bytes.
        """
        if wf.status != "pending" or not wf.s3_key:
            return False
        partes = wf.s3_key.split("/")
        return len(partes) > 2 and partes[0] == "drive" and partes[1] == wf.workspace_id

    def _e_artefato_de_execucao_pendente(self, wf: WorkspaceFile) -> bool:
        """Is the confirm closing a run artifact (via s3_key_override)?

        Run artifacts come in through `create_agent_upload_url(s3_key_override=
        ...)`, which skips `validate_upload` ENTIRELY — extension AND size. There
        was never a DECLARED size, so there is nothing for the ceiling to
        recheck, and applying it would bring down the run (the executor does
        `raise_for_status` on the confirm) — the bug that rejected large run
        artifacts. The key lives under `artifacts/{ws}/...`; requiring the
        workspace of the row ITSELF keeps the guard against cross-workspace keys,
        which do NOT fit here and are still rejected.
        """
        if wf.status != "pending" or not wf.s3_key:
            return False
        partes = wf.s3_key.split("/")
        return len(partes) > 2 and partes[0] == "artifacts" and partes[1] == wf.workspace_id

    async def _recusar_acima_do_teto(self, wf: WorkspaceFile, tamanho_real: int) -> None:
        """Applies `max_size_mb` to the REAL object, on confirm. Without it the ceiling is optional.

        In the upload via presigned URL, the client is the one stating the size:
        `create_upload_url` validates the number that came in the body and the
        PUT goes straight to MinIO, which knows no limit at all. Declaring 1 KB
        and sending 5 GB got through — and `confirm_upload` even MEASURED the
        object (`head_async`) and wrote the true size to `size` without ever
        comparing it to the ceiling. The file entered the listing, counted
        toward the quota and could be downloaded.

        Rejecting requires deleting the object: it is already in storage, and a
        rejection that left the bytes there would just be a slower way of
        accepting them — the reconcile's `cleanup_pending_workspace_files`
        deletes the expired ROW, never the object. The row goes too because,
        without the object, it describes nothing.

        Whatever does NOT fit `_e_upload_de_drive_pendente` is also rejected,
        but without deleting anything: better an object above the ceiling that
        the reconcile flags as drift than a deletion path with no confirmation
        and no trash.
        """
        settings = await self.get_settings()
        max_bytes = settings.max_size_mb * 1024 * 1024
        if tamanho_real <= max_bytes:
            return

        # A run artifact (s3_key_override) skipped validate_upload: it did not
        # declare a size, so there is nothing to recheck. Accepts without
        # deleting — applying the ceiling here would bring down the run.
        # Already-confirmed ones and cross-workspace keys do NOT fit and are
        # still rejected below.
        if self._e_artefato_de_execucao_pendente(wf):
            logger.info(
                "Drive: artefato de execucao '%s' (ws=%s) tem %s bytes, acima do teto "
                "de %sMB — aceito (upload de execucao nao declara tamanho ao teto).",
                wf.original_name, wf.workspace_id, tamanho_real, settings.max_size_mb,
            )
            return

        # Locals BEFORE the delete: after the commit the instance has been removed
        # from the session and reading an attribute from it is an error.
        s3_key, nome, ws_id = wf.s3_key, wf.original_name, wf.workspace_id
        excedeu = f"'{nome}' (ws={ws_id}) tem {tamanho_real} bytes, acima do teto de {settings.max_size_mb}MB"

        if not self._e_upload_de_drive_pendente(wf):
            logger.warning("Drive: %s — confirmacao recusada; objeto e registro mantidos.", excedeu)
            raise FileTooLargeError(f"Arquivo excede {settings.max_size_mb}MB.")

        logger.warning("Drive: %s — recusado; objeto e registro removidos.", excedeu)
        # `storage.delete` is best-effort and NEVER raises: it returns False. An
        # `except` here would be dead code — what informs is the return value.
        if not await s3.delete_async(s3_key):
            # The rejection does not depend on this. The orphan bytes show up in the
            # reconcile's drift; accepting the file to avoid leaving garbage would be worse.
            logger.error("Drive: falha ao apagar objeto recusado %s — ficou orfao no storage.", s3_key)

        await self.db.delete(wf)
        await self.db.commit()
        raise FileTooLargeError(f"Arquivo excede {settings.max_size_mb}MB.")

    async def confirm_upload(
        self,
        id_hash: str,
        exclude_agent_id: Optional[str] = None,
        spatial_metadata: Optional[dict] = None,
    ) -> WorkspaceFile:
        """Confirms that the upload completed by checking existence in MinIO.

        `spatial_metadata` (CRS, bbox, feature count) can only be computed by
        whoever has the file — the executor. In `register` mode it was already
        sent; in `upload` mode, which is GeoSync's default, it was discarded, and
        the file showed up in the Drive with no spatial data at all. It is
        optional because an old executor confirms with no body at all.
        """
        result = await self.db.execute(select(WorkspaceFile).where(WorkspaceFile.id_hash == id_hash))
        wf = file_or_404(result.scalar_one_or_none())

        obj = await s3.head_async(wf.s3_key)
        if not obj:
            raise FileNotFoundError("Arquivo nao encontrado no storage.")

        await self._recusar_acima_do_teto(wf, obj["size"])

        # content_md5 is only filled in here, on confirm. Arriving already filled
        # means this row was reused by an upload with overwrite=True — for the
        # executor's GeoSync that is file_updated, not file_created (see
        # executor/sync/manager.py, which handles both).
        acao = "file_updated" if wf.content_md5 else "file_created"

        wf.status = "confirmed"
        wf.size = obj["size"]
        wf.content_md5 = obj["etag"]
        # Explicit, and not via onupdate: on an overwrite with IDENTICAL content
        # the three fields above get the same values, no attribute becomes
        # dirty, SQLAlchemy emits no UPDATE and `updated_at` would not advance —
        # the freshly written file would not move up in the listing and the user
        # would see no sign at all that the workflow ran.
        wf.content_written_at = utc_now_naive()
        # Only overwrites when something came: a confirm with no metadata (old
        # executor, or a dataset with no readable vector layer) must not erase
        # what an earlier pass had already recorded.
        if spatial_metadata:
            wf.spatial_metadata = spatial_metadata
        await self.db.commit()

        await emit_drive_event(wf.workspace_id, acao, {
            "id_hash": wf.id_hash, "original_name": wf.original_name,
            "extension": wf.extension, "size": wf.size, "content_md5": wf.content_md5,
        }, exclude_agent_id=exclude_agent_id)

        return wf

    # ── Metadados e download ──────────────────────────────────────────────

    async def get_file(self, id_hash: str) -> WorkspaceFile:
        result = await self.db.execute(select(WorkspaceFile).where(WorkspaceFile.id_hash == id_hash))
        return file_or_404(result.scalar_one_or_none())

    async def generate_download_url(self, wf: WorkspaceFile) -> dict:
        # The guard lives HERE, and not in the router: the executor's path
        # (/drive/executor-download) already rejected local content, and the
        # user's (/drive/{id}/download) went straight to the presign with
        # `s3_key=None` — boto3 validates `Key=None` on the CLIENT and raises
        # ParamValidationError, which is not a ClientError, escapes every
        # `except` along the path and becomes a 500 that explains nothing. The
        # UI hides the button; the route remains reachable via shortcut, list
        # cache or direct call.
        _recusar_se_local(wf)
        url = await s3.presigned_get_async(wf.s3_key, filename=wf.original_name)
        return {"download_url": url, "filename": wf.original_name}

    # ── Delecao ───────────────────────────────────────────────────────────

    async def delete_file(self, wf: WorkspaceFile) -> None:
        """Deletes a file from S3 and from the database, emitting an event.

        Policy: S3 FIRST via delete_strict. If it fails (except 'not found'), it
        does not delete the DB record — so reconciliation tries again and the
        object does not become an orphan in MinIO consuming disk with no trace in
        the report.

        A CATALOGED file (`content_location='executor'`) is rejected: see
        `_recusar_se_catalogado`.
        """
        _recusar_se_catalogado(wf)
        del_info = {
            "id_hash": wf.id_hash, "original_name": wf.original_name,
            "extension": wf.extension, "size": wf.size,
        }
        del_ws = wf.workspace_id

        # `if wf.s3_key` is defensive, and not redundant with the guard above:
        # without it, a null key reaches boto3, which validates `Key=None` on the
        # CLIENT and raises ParamValidationError — which is NOT a ClientError,
        # escapes `delete_strict`'s `except` and becomes a 500. A 500 from a null
        # key must not depend on a guard ten lines away.
        if wf.s3_key:
            try:
                await s3.delete_strict_async(wf.s3_key, allow_missing=True)
            except Exception as exc:
                logger.error(
                    "delete_file cancelado para %s: S3 falhou (%s). Registro preservado.",
                    wf.s3_key, exc,
                )
                raise

        await self.db.delete(wf)
        await self.db.commit()

        await emit_drive_event(del_ws, "file_deleted", del_info)

    async def delete_agent_file(self, wf: WorkspaceFile, executor_id: str) -> None:
        """Removes a file from the Drive on the order of the executor that syncs the folder.

        Mirrors `delete_file`, with ONE deliberate difference: it accepts the
        CATALOGED file (`content_location='executor'`). The user's path rejects it
        — deleting it from the web would not remove the bytes, which live on the
        executor — and `_recusar_se_catalogado` says, in its own message, "apague
        o arquivo na pasta sincronizada do executor" (delete the file in the
        executor's synced folder). That is exactly the request that arrives here:
        the owning executor itself reporting that the file left the folder.
        Deleting the record is the correct outcome, not a forbidden operation.

        Guard: only the executor that OWNS the catalog entry can delete it — one
        executor does not remove the record of content that lives on another.
        """
        if (
            wf.content_location == "executor"
            and wf.content_executor_id
            and wf.content_executor_id != executor_id
        ):
            raise InvalidFileOperationError(
                "Arquivo catalogado em outro executor — remoção negada."
            )

        del_info = {
            "id_hash": wf.id_hash, "original_name": wf.original_name,
            "extension": wf.extension, "size": wf.size,
        }
        del_ws = wf.workspace_id

        # S3 FIRST, same policy as `delete_file`: if the object does not go, the
        # record stays standing for reconciliation to try again, instead of
        # becoming an orphan in MinIO. Catalog entries have `s3_key=None` and skip this step.
        if wf.s3_key:
            try:
                await s3.delete_strict_async(wf.s3_key, allow_missing=True)
            except Exception as exc:
                logger.error(
                    "delete_agent_file cancelado para %s: S3 falhou (%s). Registro preservado.",
                    wf.s3_key, exc,
                )
                raise

        await self.db.delete(wf)
        await self.db.commit()

        # Excludes the executor itself from the fan-out: it has already removed the
        # file locally (it was the one that originated the deletion), so resending
        # `file_deleted` would only trigger a redundant `_discard_dataset` on it.
        await emit_drive_event(del_ws, "file_deleted", del_info, exclude_agent_id=executor_id)

    async def batch_delete_files(
        self,
        id_hashes: list[str],
        workspace_ids: list[str],
        current_user_id: str,
    ) -> tuple[int, int]:
        """Deletes multiple files.

        Returns `(apagados, catalogados_pulados)`. The second number exists so
        the UI does not say "5 files deleted" when 2 were cataloged and were
        ignored — a count that lies is worse than none.
        """
        from app.api.dependencies import _has_min_workspace_role
        from app.models.workspace import Workspace as _Workspace
        from app.models.workspace_member import WorkspaceMember as _WM

        if not id_hashes:
            raise InvalidFileOperationError("Lista de id_hashes vazia.")
        if len(id_hashes) > 100:
            raise InvalidFileOperationError("Máximo de 100 arquivos por operação.")

        result = await self.db.execute(
            select(WorkspaceFile).where(WorkspaceFile.id_hash.in_(id_hashes))
        )
        files = result.scalars().all()

        # Preloads roles to avoid N+1 in the loop
        unique_ws_ids = {f.workspace_id for f in files if f.workspace_id in workspace_ids}
        _owner_result = await self.db.execute(
            select(_Workspace.id_hash).where(
                _Workspace.id_hash.in_(unique_ws_ids),
                _Workspace.owner_id == current_user_id,
                _Workspace.deleted_at.is_(None),
            )
        )
        _owned_ws = {r[0] for r in _owner_result.all()}
        _member_result = await self.db.execute(
            select(_WM.workspace_id, _WM.role).where(
                _WM.workspace_id.in_(unique_ws_ids),
                _WM.user_id == current_user_id,
            )
        )
        _role_map = {r[0]: r[1] for r in _member_result.all()}

        def _can_edit_ws(ws_id: str) -> bool:
            if ws_id in _owned_ws:
                return True
            return _has_min_workspace_role(_role_map.get(ws_id), ROLE_EDITOR)

        deleted = 0
        skipped_s3 = 0
        skipped_local = 0
        # Events to emit AFTER the commit. The fields are captured while the
        # instance is alive: after the commit it is expired and reading any
        # attribute would trigger a refresh of a row that no longer exists.
        eventos: list[tuple[str, dict]] = []
        for wf in files:
            if wf.workspace_id not in workspace_ids:
                continue
            if not _can_edit_ws(wf.workspace_id):
                continue
            # Cataloged: SKIPS instead of bringing down the batch. A mixed batch is the
            # normal case — selecting everything in a folder that has both kinds —
            # and failing entirely because of them would prevent deleting the rest.
            if wf.content_location == "executor":
                skipped_local += 1
                continue
            # S3 PRIMEIRO. Falha -> pula (reconcile/cleanup tenta depois).
            if wf.s3_key:
                try:
                    await s3.delete_strict_async(wf.s3_key, allow_missing=True)
                except Exception as exc:
                    logger.warning(
                        "batch_delete: pulando '%s' (S3 falhou: %s).",
                        wf.s3_key, exc,
                    )
                    skipped_s3 += 1
                    continue
            eventos.append((wf.workspace_id, {
                "id_hash": wf.id_hash, "original_name": wf.original_name,
                "extension": wf.extension, "size": wf.size,
            }))
            await self.db.delete(wf)
            deleted += 1

        await self.db.commit()

        # Same promise as `delete_file`: each confirmed removal notifies the
        # workspace's executors (`file_deleted`), so that an executor in
        # download/bidirectional mode removes its local copy. Without this, a
        # batch deletion from the UI vanished from the Drive but came back to
        # life on the executor on the next cycle (it re-downloaded the file, with
        # the server as the source of truth). Only AFTER the commit — announcing
        # something a rollback undid would be a lie — and best-effort:
        # `emit_drive_event` swallows its own failures, so a Redis outage does
        # not undo the already persisted removal.
        for ws_id, info in eventos:
            await emit_drive_event(ws_id, "file_deleted", info)

        if skipped_s3:
            logger.info("batch_delete: %d pulados por falha no S3.", skipped_s3)
        if skipped_local:
            logger.info(
                "batch_delete: %d pulados por serem catalogados (conteudo no executor).",
                skipped_local,
            )
        return deleted, skipped_local

    # ── Presigned URLs sem registro (executor interno) ───────────────────────

    async def presign_upload(self, s3_key: str, content_type: str = "application/octet-stream") -> dict:
        upload_url = await s3.presigned_put_async(s3_key, content_type=content_type)
        return {"upload_url": upload_url, "s3_key": s3_key}

    async def presign_download(self, s3_key: str, agent_ws_ids: list[str]) -> dict:
        """Gera presigned GET URL validando ownership do s3_key."""
        # pin-cache/ and artifacts/ use workspace_id in the path (artifacts/{ws_id}/{task_id}/file)
        # Direct validation via the path — does not depend on a database record
        # (SendEmail artifacts may not be in the Artifact table yet)
        if s3_key.startswith(("pin-cache/", "artifacts/")):
            parts = s3_key.split("/")
            ws_id_in_key = parts[1] if len(parts) > 1 else ""
            if ws_id_in_key not in agent_ws_ids:
                raise WorkspaceAccessDeniedError("Acesso negado.")
        else:
            result = await self.db.execute(select(WorkspaceFile).where(WorkspaceFile.s3_key == s3_key))
            wf = result.scalar_one_or_none()
            if wf is None or wf.workspace_id not in agent_ws_ids:
                raise WorkspaceAccessDeniedError("Acesso negado.")

        filename = s3_key.rsplit("/", 1)[-1] if "/" in s3_key else s3_key
        download_url = await s3.presigned_get_async(s3_key, filename=filename)
        return {"download_url": download_url}

    # ── Admin: extensoes ──────────────────────────────────────────────────

    async def update_settings(self, max_size_mb: int) -> PlatformFileSettings:
        settings = await self.get_settings()
        settings.max_size_mb = max_size_mb
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def list_extensions(self) -> list[AllowedFileExtension]:
        await self._seed_extensions_if_empty()
        result = await self.db.execute(select(AllowedFileExtension).order_by(AllowedFileExtension.extension))
        return result.scalars().all()

    async def add_extension(self, extension: str) -> AllowedFileExtension:
        ext = extension.lower().lstrip(".")
        existing = await self.db.execute(select(AllowedFileExtension).where(AllowedFileExtension.extension == ext))
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(f"Extensao '{ext}' ja existe.")
        new_ext = AllowedFileExtension(extension=ext)
        self.db.add(new_ext)
        await self.db.commit()
        await self.db.refresh(new_ext)
        return new_ext

    async def remove_extension(self, extension: str) -> None:
        ext = extension.lower().lstrip(".")
        result = await self.db.execute(select(AllowedFileExtension).where(AllowedFileExtension.extension == ext))
        obj = result.scalar_one_or_none()
        if not obj:
            raise FileNotFoundError(f"Extensao '{ext}' nao encontrada.")
        await self.db.delete(obj)
        await self.db.commit()

    # ── Trigger workflow (executor) ──────────────────────────────────────────

    async def trigger_workflow(self, workflow_id_hash: str, agent_ws_ids: list[str], inputs: dict) -> dict:
        if not workflow_id_hash:
            raise InvalidFileOperationError("workflow_id_hash obrigatorio.")

        from app.models.models import Workflow
        wf_result = await self.db.execute(
            select(Workflow).where(
                Workflow.id_hash == workflow_id_hash,
                Workflow.workspace_id.in_(agent_ws_ids),
                Workflow.flag_ative == True,  # noqa: E712
            )
        )
        wf = wf_result.scalar_one_or_none()
        if not wf:
            raise WorkflowNotFoundError("Workflow nao encontrado, inativo ou de outro workspace.")

        from app.services.workflow_service import WorkflowService
        service = WorkflowService(self.db)
        task_id = await service.execute_workflow(wf, inputs=inputs)

        return {"task_id": task_id, "workflow_id_hash": workflow_id_hash, "status": "dispatched"}
