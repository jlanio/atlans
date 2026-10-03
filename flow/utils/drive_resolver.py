# flow/utils/drive_resolver.py
"""
Resolves stored files (Workspace Drive or run Artifacts): asks the server
for a pre-signed URL, downloads to a temporary file and returns the local
path.

Used by the file-reading nodes (ReadGeoJSON, ReadShapefile, etc.),
and by DataInput (Drive or Artifacts context).

Contexts:
  Drive       — WorkspaceFile by id_hash (resolve_drive_file)
  Artifacts   — Artifact by id_hash (resolve_artifact_file)

The engine always runs on the executor (external/on-premise), which has no
access to the database nor MinIO credentials. Authorization and workspace scope
are decided by the server, which identifies the executor by its mTLS cert and
responds with a short-TTL pre-signed URL for that object:

  GET /drive/executor-download/{id}           → Drive file
  GET /drive/executor-download-artifact/{id}  → run artifact
"""
import os
import tempfile
from typing import TYPE_CHECKING

from flow.utils.logger import get_logger

if TYPE_CHECKING:
    # Only for annotations: `Path` is imported lazily inside the functions, like
    # the rest of this module's heavy imports. The annotations are strings and are
    # never evaluated at runtime — this block exists so the type checker and lint
    # can see the name.
    from pathlib import Path

logger = get_logger(__name__)


async def read_drive_file_as(drive_file_id, reader, *, label="arquivo", reraise=()):
    """Resolves the Drive file, calls `reader(temp_path)` in a thread and removes the
    temp file. Converts a read failure into a RuntimeError with the original name.

    Centralizes the resolve→read→unlink→wrap pattern repeated by the ReadGeoJSON/
    ReadShapefile/ReadGeoParquet/ReadCSVWithCoords nodes. `reader` is a sync callable
    `(temp_path) -> dados`. `reraise` is a tuple of exceptions to propagate as is
    (e.g. a column-validation ValueError in the CSV), without becoming RuntimeError.
    Returns `(dados, original_name)`.
    """
    import asyncio
    temp_path, _ext, original_name = await asyncio.to_thread(
        resolve_drive_file, drive_file_id
    )
    try:
        data = await asyncio.to_thread(reader, temp_path)
    except reraise:
        raise
    except Exception as e:
        raise RuntimeError(f"Erro ao ler {label} '{original_name}': {e}") from e
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    return data, original_name


def resolve_drive_file(drive_file_id: str) -> tuple[str, str, str]:
    """
    Gets the pre-signed URL + metadata of the Drive file via
    GET /drive/executor-download/{id_hash}, downloads it to a temp file and returns
    (temp_path, extension, original_name).

    The caller is responsible for removing the temp file after use.
    """
    return _fetch_and_stream(
        f"/drive/executor-download/{drive_file_id}",
        fallback_name=drive_file_id,
        not_found=f"Arquivo com id '{drive_file_id}' nao encontrado no Drive.",
        forbidden=f"Executor sem acesso ao arquivo '{drive_file_id}'.",
        meta_label=f"drive meta {drive_file_id}",
    )


def resolve_artifact_file(artifact_id: str) -> tuple[str, str, str]:
    """
    Gets the pre-signed URL + metadata of the artifact via
    GET /drive/executor-download-artifact/{id_hash}, downloads it to a temp file
    and returns (temp_path, extension, original_name).

    The caller is responsible for removing the temp file after use.
    """
    return _fetch_and_stream(
        f"/drive/executor-download-artifact/{artifact_id}",
        fallback_name=artifact_id,
        not_found=f"Artefato com id '{artifact_id}' nao encontrado.",
        forbidden=f"Executor sem acesso ao artefato '{artifact_id}'.",
        meta_label=f"artifact meta {artifact_id}",
    )


def _fetch_and_stream(
    path: str, *, fallback_name: str, not_found: str, forbidden: str, meta_label: str,
) -> tuple[str, str, str]:
    """Busca metadados + pre-signed URL em `path` e faz streaming para temp file."""
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    base_url, headers, verify = get_agent_http_config()

    # Idempotent GET: retry_sync retries only transient errors (connect/read).
    # Status handling (403/404/5xx) stays OUTSIDE the retry — those are
    # permanent and must not be retried.
    def _fetch_meta() -> "httpx.Response":
        return httpx.get(
            f"{base_url}{path}",
            headers=headers,
            verify=verify,
            timeout=30,
        )
    resp = retry_sync(_fetch_meta, label=meta_label)

    if resp.status_code == 403:
        raise PermissionError(forbidden)
    if resp.status_code == 404:
        raise FileNotFoundError(not_found)
    resp.raise_for_status()

    body = resp.json()
    original_name: str = body.get("original_name") or fallback_name
    ext: str = (body.get("extension") or "").lower()

    # Content that never left this executor (LGPD): the server does not have the
    # object and responds with the location instead of a pre-signed URL.
    if body.get("content_location") == "executor":
        dono = body.get("executor_id") or ""
        local_path = body.get("local_path")
        if local_path:
            # Artifact: the server DERIVED the path relative to the artifacts root
            # from the record (run_result_consumer).
            return _copy_local_to_temp(local_path, dono, ext, original_name)
        # Drive file cataloged by GeoSync: the server stores no path at
        # all — what knows where the file is is this machine's sync
        # manifest.
        return _resolve_do_manifesto_de_sync(_id_do_path(path), dono, ext, original_name)

    download_url: str = body["download_url"]
    return _stream_presigned_to_temp(download_url, ext, original_name, verify)


def _id_do_path(path: str) -> str:
    """Extracts the id_hash from the end of '/drive/executor-download/{id}'."""
    return path.rstrip("/").rsplit("/", 1)[-1]


def _resolve_do_manifesto_de_sync(
    id_hash: str, dono_id: str, ext: str, original_name: str,
) -> tuple[str, str, str]:
    """Finds a cataloged dataset by scanning the manifests of the sync folders.

    The server records that the file is local and on which executor, but NOT
    where it is: a path on the user's file system has no reason to exist in the
    database, and not transmitting any path rules out the path traversal attack
    class from the start.

    What knows the path is the `.atlans-sync.json` of each synced folder, which
    already maps `remote_id_hash -> dataset -> arquivos`.
    """
    import json
    import os as _os
    import shutil
    from pathlib import Path

    pastas = [p.strip() for p in (_os.getenv("EXECUTOR_SYNC_DIRS") or "").split(",") if p.strip()]
    if not pastas:
        raise FileNotFoundError(
            f"O arquivo '{original_name}' esta catalogado no executor "
            f"{dono_id or 'de origem'}, mas esta maquina nao tem nenhuma pasta "
            "de GeoSync configurada (EXECUTOR_SYNC_DIRS vazio)."
        )

    for pasta in pastas:
        manifesto = Path(pasta) / ".atlans-sync.json"
        try:
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue

        for ds_nome, ds in (dados.get("datasets") or {}).items():
            if not isinstance(ds, dict) or ds.get("remote_id_hash") != id_hash:
                continue

            alvo = _arquivo_principal(Path(pasta), ds)
            if alvo is None or not alvo.is_file():
                raise FileNotFoundError(
                    f"O dataset '{ds_nome}' esta no manifesto de '{pasta}', mas o "
                    "arquivo nao esta mais no disco. Ele foi movido ou apagado."
                )

            suffix = f".{ext}" if ext else alvo.suffix
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp.close()
            # Copies for the same reason as `_copy_local_to_temp`: the caller deletes
            # the returned path, and returning the user's file would destroy it.
            shutil.copyfile(alvo, tmp.name)
            logger.info("Dataset local resolvido pelo manifesto de sync: %s", alvo)
            return tmp.name, ext or alvo.suffix.lstrip("."), original_name

    raise FileNotFoundError(
        f"O arquivo '{original_name}' foi catalogado pelo executor "
        f"{dono_id or 'de origem'} e nao esta nas pastas de GeoSync desta "
        "maquina. Arquivos em modo catalogo so podem ser lidos por workflows "
        "que rodem naquele mesmo executor."
    )


def _arquivo_principal(pasta: "Path", ds: dict) -> "Path | None":
    """File to be read from a manifest dataset.

    Mirrors `Dataset.primary_path` in executor/sync/scanner.py: for a shapefile
    the dataset is a bundle (.shp/.dbf/.shx) and the one that is read is the
    `.shp`. Diverging from it would make ReadShapefile receive a `.dbf` and fail
    in an incomprehensible way.
    """
    arquivos = list((ds.get("files") or {}).keys())
    if not arquivos:
        return None
    if ds.get("type") == "shapefile":
        for nome in arquivos:
            if nome.lower().endswith(".shp"):
                return pasta / nome
        return None
    return pasta / arquivos[0]


def _copy_local_to_temp(
    local_path: str, dono_id: str, ext: str, original_name: str,
) -> tuple[str, str, str]:
    """Copies a local artifact to a temp file and returns the same triple.

    ⚠️ It COPIES, and does not return the original path — on purpose.

    `read_drive_file_as` does `os.unlink(temp_path)` in a `finally`, because up
    to now every returned path was a downloaded temp file. Returning the real
    file would make the FIRST workflow that read it DELETE the user's data,
    silently, and the damage would only show up much later.

    The copy is local, so it does not violate the locality policy. The cost is
    duplicated I/O; the alternative (signaling "do not delete" via the contract)
    requires revising the five read nodes and all future code that uses the
    helper — a bad trade for the first version.
    """
    import shutil
    from pathlib import Path

    from flow.utils.artifact_helpers import artifacts_root

    if not local_path:
        raise FileNotFoundError(
            f"O servidor marcou '{original_name}' como local do executor, mas nao "
            "informou o caminho. O registro do artefato pode estar incompleto."
        )

    raiz = Path(artifacts_root()).resolve()
    alvo = (raiz / local_path).resolve()

    # Confinement: `local_path` comes over the network. The server derives it (it
    # does not trust the executor), but relying on that would be outsourcing our
    # own security — a `../` here would give arbitrary file reads on the machine.
    if not alvo.is_relative_to(raiz):
        raise PermissionError(
            f"Caminho de artefato local fora do diretorio permitido: {local_path!r}"
        )

    if not alvo.is_file():
        # A named error instead of a raw FileNotFoundError: it almost always means
        # the artifact belongs to ANOTHER executor, and the operator needs to know
        # that rather than go looking for a file that was never here.
        raise FileNotFoundError(
            f"O artefato '{original_name}' foi mantido no executor "
            f"{dono_id or 'de origem'} e nao esta nesta maquina "
            f"({alvo}). Arquivos marcados para permanecer no executor so podem "
            "ser lidos por workflows que rodem naquele mesmo executor."
        )

    suffix = f".{ext}" if ext else ""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    shutil.copyfile(alvo, tmp.name)

    logger.info("Artefato local resolvido sem trafego de rede: %s", alvo)
    return tmp.name, ext, original_name


def _stream_presigned_to_temp(
    download_url: str, ext: str, original_name: str, verify,
) -> tuple[str, str, str]:
    """Streams a pre-signed URL to a temp file and returns
    (temp_path, ext, original_name). The caller removes the temp file."""
    import httpx
    from flow.utils.http_retry import retry_sync

    suffix = f".{ext}" if ext else ""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()

    def _download() -> None:
        # open("wb") truncates on each attempt → idempotent re-download into the temp file.
        with httpx.Client(timeout=300, verify=verify, follow_redirects=True) as client:
            with client.stream("GET", download_url) as stream:
                stream.raise_for_status()
                with open(tmp.name, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=65536):
                        f.write(chunk)

    try:
        retry_sync(_download, label=f"download {original_name}")
    except Exception as exc:
        os.unlink(tmp.name)
        raise FileNotFoundError(f"Falha ao baixar '{original_name}' do MinIO: {exc}")

    logger.info("Resolver: '%s' (ext=%s) baixado para %s", original_name, ext, tmp.name)
    return tmp.name, ext, original_name
