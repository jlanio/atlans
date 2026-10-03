# flow/utils/artifact_helpers.py
"""
Shared helper for uploading artifacts to MinIO.

Upload via a pre-signed URL obtained from the server (the executor has no MinIO
credentials). Fallback: save locally if the upload fails.

Also defines DATA LOCALITY (LGPD) — whether the result of an output node
leaves the machine or not. The vocabulary lives here, and not in each node, because
the choice must mean the same thing in all of them: three names for the same
concept was exactly the problem this unification solves.
"""
import logging
import os
from typing import BinaryIO

logger = logging.getLogger(__name__)


# ── Data locality (LGPD) ──────────────────────────────────────────────────────

HERDAR = "herdar"
SERVIDOR = "servidor"
EXECUTOR = "executor"


class EnvioBloqueadoError(RuntimeError):
    """The executor retains the data and the node only works by sending.

    Its own exception, and not a `ValueError`, because it is not a node
    configuration error: the workflow is correct and it is the MACHINE that does
    not allow it. Whoever reads the log needs to tell "you built it wrong" apart
    from "not allowed here".
    """


def localidade_padrao() -> str:
    """THIS machine's policy: `servidor` or `executor`.

    Read from `EXECUTOR_SYNC_MODE == "catalog"`, which is the SAME variable the
    desktop app's GeoSync screen already writes under the label "Localidade dos
    dados → Manter apenas no executor" (Data locality → Keep only on the
    executor). Reusing it, instead of creating another, is what makes the label
    apply to everything that leaves here — until now it protected the synced
    folder and let workflows send whatever they wanted.

    Read from the environment for the same reason as `artifacts_root()`: `flow/`
    runs both inside the executor and in-process on the server, and importing
    `executor/config.py` from here would invert the dependency. On the server the
    variable does not exist, and the policy is `servidor` — which is correct: the
    content is already there.
    """
    modo = (os.getenv("EXECUTOR_SYNC_MODE") or "").strip().lower()
    return EXECUTOR if modo == "catalog" else SERVIDOR


def resolver_localidade(escolha: str | None) -> tuple[str, str]:
    """Translates the node's choice into (effective locality, who decided).

    The machine's policy is a PROHIBITION, not a default: the workflow can
    tighten it, never loosen it. That is why the rule is an `or` — it is enough
    for one of the two to ask for the content to stay.

    `quem` is 'executor' or 'nó', so the log tells the truth instead of
    "herdado" (inherited) when the two coincided.
    """
    pediu_local = (escolha or HERDAR).strip().lower() == EXECUTOR
    if localidade_padrao() == EXECUTOR:
        return EXECUTOR, "executor"
    return (EXECUTOR, "nó") if pediu_local else (SERVIDOR, "executor")


def descrever_localidade(efetiva: str, quem: str) -> str:
    """Sentence for the run log. It is the ONLY place where whoever built the
    workflow sees what "Herdar do executor" (inherit from the executor) became —
    the editor does not know the destination machine."""
    onde = "fica apenas neste executor" if efetiva == EXECUTOR else "vai para o servidor"
    return f"Localidade dos dados: o conteúdo {onde} (definido pelo {quem})."


def exigir_envio_permitido(no: str, o_que_exige: str) -> None:
    """Blocks a node that ONLY works by sending, when the machine retains the data.

    Single point of refusal: the message lives here, and a new node that depends
    on sending has one line to call instead of rewriting the explanation.

    Fails instead of skipping. A node that leaves itself out keeps the run green
    and nobody finds out that the layer was never published or that the e-mail
    went out without an attachment — it is the worst of outcomes, because it
    produces no signal at all.
    """
    if localidade_padrao() != EXECUTOR:
        return
    # No arrow (U+2192) nor any character outside latin-1: this message
    # travels through the executor's log, which may end up on a cp1252 console —
    # and a UnicodeEncodeError while EXPLAINING a refusal would replace the
    # explanation with a traceback.
    raise EnvioBloqueadoError(
        f"{no} não foi executado.\n\n"
        "Este executor está configurado para manter os dados apenas nele "
        '(app do executor: GeoSync > Localidade dos dados > "Manter apenas no '
        f'executor"), e {o_que_exige}.\n\n'
        f"O que fazer: remova o nó {no} deste workflow, ou execute-o num "
        "executor que possa enviar dados ao servidor."
    )


def propriedade_localidade(visible_when=None) -> dict:
    """Schema fragment for the `localidade` field, identical in every output node.

    Copying the dict into each node would make the labels diverge over time.

    NO `description`: the configuration panel renders it as a paragraph right
    below the field, and the text that explained the whole policy took up more
    space than all the node's other fields combined. The two labels already
    say what each option does, and the run log reports the effective locality
    on every run — which is where the information actually matters, because
    only there is it known on which machine the workflow ran.

    There is NO "send to the server" option. It would be the only choice able
    to go against the machine's policy, and an option the executor silently
    ignores is worse than no option at all: the person ticks it, believes it,
    and the behavior is something else.
    """
    prop = {
        "name":    "localidade",
        "label":   "Localidade dos dados",
        "type":    "select",
        "default": HERDAR,
        "options": [
            {"value": HERDAR,   "label": "Herdar do executor"},
            {"value": EXECUTOR, "label": "Manter apenas no executor"},
        ],
    }
    if visible_when is not None:
        prop["visibleWhen"] = visible_when
    return prop


def _upload_via_presigned_url(content: bytes, filename: str, content_type: str,
                               workspace_id: str, task_id: str,
                               create_drive_entry: bool = False,
                               overwrite: bool = False) -> tuple[str, str | None, bool]:
    """
    Upload via a pre-signed URL (executor flow).

    create_drive_entry=True  → POST /drive/executor-upload-url (creates a WorkspaceFile in Drive)
    create_drive_entry=False → POST /drive/executor-presign-upload (only uploads to MinIO)

    `overwrite` only has an effect in the Drive flow: the server reuses the
    file with the same name instead of creating another.

    Returns (s3_key, drive_file_id | None, reused). `reused` is what the SERVER
    did — not what was asked. An old server does not return the field; in that
    case it stays False and the caller does not claim what it cannot verify.
    """
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    base_url, headers, verify = get_agent_http_config()

    s3_key = f"artifacts/{workspace_id}/{task_id}/{filename}"

    if create_drive_entry:
        # Full flow: creates WorkspaceFile + upload + confirmation.
        # We do NOT wrap the executor-upload-url POST in a retry — it creates a
        # WorkspaceFile and retrying could duplicate the Drive entry.
        # Only the PUT (upload to MinIO) is idempotent (overwrites the object).
        resp = httpx.post(
            f"{base_url}/drive/executor-upload-url",
            json={"filename": filename, "size": len(content), "workspace_id": workspace_id, "s3_key_override": s3_key, "content_type": content_type, "overwrite": overwrite},
            headers=headers, verify=verify, follow_redirects=True, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        upload_url = data["upload_url"]
        file_id = data["id_hash"]
        s3_key = data.get("s3_key", s3_key)
        reused = bool(data.get("reused", False))

        def _put() -> None:
            put_resp = httpx.put(
                upload_url, content=content,
                headers={"Content-Type": content_type}, timeout=120, verify=verify,
            )
            put_resp.raise_for_status()
        retry_sync(_put, label=f"artifact upload {s3_key}")

        confirm_resp = httpx.post(
            f"{base_url}/drive/executor-confirm-upload/{file_id}",
            headers=headers, verify=verify, follow_redirects=True, timeout=15,
        )
        confirm_resp.raise_for_status()

        logger.info(
            "Artefato enviado ao MinIO + Drive via pre-signed URL: %s (%s)",
            s3_key, "sobrescreveu arquivo existente" if reused else "arquivo novo",
        )
        return s3_key, file_id, reused
    else:
        # Simple flow: only uploads to MinIO (no WorkspaceFile). Presign + PUT
        # are idempotent (fixed s3_key) → retrying the whole block is safe;
        # gets the presign URL again on each attempt (short TTL).
        def _presign_and_put() -> None:
            resp = httpx.post(
                f"{base_url}/drive/executor-presign-upload",
                json={"s3_key": s3_key, "content_type": content_type},
                headers=headers, verify=verify, follow_redirects=True, timeout=30,
            )
            resp.raise_for_status()
            upload_url = resp.json()["upload_url"]
            put_resp = httpx.put(
                upload_url, content=content,
                headers={"Content-Type": content_type}, timeout=120, verify=verify,
            )
            put_resp.raise_for_status()
        retry_sync(_presign_and_put, label=f"artifact upload {s3_key}")

        logger.info("Artefato enviado ao MinIO via pre-signed URL: %s", s3_key)
        return s3_key, None, False


def artifacts_root() -> str:
    """Root of the artifacts on the executor's disk.

    Single point: resolving a local artifact (flow/utils/drive_resolver.py)
    and the retention cleanup (executor/artifact_purge.py) must reach
    exactly the same directory the write used.
    """
    return os.getenv("EXECUTOR_ARTIFACTS_DIR", os.getenv("ARTIFACT_DIR", "./artifacts"))


def local_relative_path(workspace_id: str, task_id: str, filename: str) -> str:
    """The artifact's path RELATIVE to `artifacts_root()`, with forward slashes.

    Relative, and not absolute, because this value travels to the server and back:
    an absolute path would leak the directory structure of the user's machine and
    would break if `EXECUTOR_ARTIFACTS_DIR` changed between runs.
    """
    return f"{workspace_id}/{task_id}/{filename}"


def _write_local(content: bytes, workspace_id: str, task_id: str, filename: str) -> str:
    """Writes the artifact to the executor's disk. Returns the absolute path."""
    task_dir = os.path.join(artifacts_root(), workspace_id, task_id)
    os.makedirs(task_dir, exist_ok=True)
    file_path = os.path.join(task_dir, filename)

    with open(file_path, "wb") as fh:
        fh.write(content)
    return file_path


def _save_local_fallback(
    content: bytes,
    workspace_id: str,
    task_id: str,
    filename: str,
) -> str:
    """Saves the artifact locally because the UPLOAD FAILED. Returns the path.

    Not to be confused with `save_artifact_local`: here local is degradation,
    there it is policy. Both write to the same place, but they mean opposite
    things to whoever reads the log and to the record on the server.
    """
    file_path = _write_local(content, workspace_id, task_id, filename)
    logger.info("Artefato salvo localmente (fallback): %s", file_path)
    return file_path


def save_artifact_local(
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
) -> tuple[str, dict]:
    """
    Writes the artifact ONLY to the executor's disk. Not a single byte leaves the machine.

    Exists for personal data (LGPD): the server receives only the catalog entry —
    name, format, size, feature count — and the record of which executor has the
    file. The content never reaches MinIO nor travels over the network.

    Same signature and same return value as `upload_artifact_to_minio`, so the
    output node can choose between the two without handling each one differently.

    There is NO fallback here, and that is deliberate: if the local write fails,
    the exception propagates and the node fails. Falling back to the upload would
    send to the cloud precisely the data that was marked not to leave.
    """
    if not filename:
        raise ValueError("filename é obrigatório para salvar artefato.")
    if not workspace_id or not task_id:
        raise ValueError("workspace_id e task_id são obrigatórios.")

    if content is None and fileobj is not None:
        pos = fileobj.tell()
        content = fileobj.read()
        fileobj.seek(pos)
    if content is None:
        raise ValueError("Deve fornecer content (bytes) ou fileobj.")

    file_path = _write_local(content, workspace_id, task_id, filename)
    rel = local_relative_path(workspace_id, task_id, filename)
    logger.info("Artefato mantido no executor (não enviado ao MinIO): %s", file_path)

    return rel, {
        "output_key": label or filename,
        "format": fmt,
        "features": features,
        "filename": filename,
        "credential_id": credential_id,
        # No s3_key: there is no object. The server must NOT derive one — see
        # _register_artifacts in app/core/run_result_consumer.py.
        "s3_key": None,
        "content_location": "executor",
        "local_path": rel,
        "size_bytes": len(content),
        # Distinct from `local_fallback`: here local was requested, it was not a failure.
        "local_fallback": False,
        "drive_file_id": None,
        "drive_reused": False,
    }


def persistir_artefato(
    localidade: str,
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    content_type: str = "application/octet-stream",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
) -> tuple[str, dict]:
    """Writes the artifact wherever the ALREADY RESOLVED locality says.

    Exists so the output nodes do not repeat the `if` — which is the exact point
    where personal data leaks if someone forgets to copy it into a new node.
    `save_artifact_local` and `upload_artifact_to_minio` have identical signatures
    and return values precisely for this.

    Receives the already resolved locality, and not the raw choice, because the
    caller needs it anyway for logging (see `descrever_localidade`) —
    resolving twice would leave room for the two to diverge.
    """
    if localidade == EXECUTOR:
        return save_artifact_local(
            content=content, fileobj=fileobj, filename=filename,
            workspace_id=workspace_id, task_id=task_id, label=label,
            fmt=fmt, features=features, credential_id=credential_id,
        )
    return upload_artifact_to_minio(
        content=content, fileobj=fileobj, filename=filename,
        content_type=content_type, workspace_id=workspace_id, task_id=task_id,
        label=label, fmt=fmt, features=features, credential_id=credential_id,
    )


def pasta_do_geosync() -> str | None:
    """First folder of `EXECUTOR_SYNC_DIRS`, or None.

    Only the first: GeoSync syncs everything against ONE workspace, and the
    desktop app already restricts the configuration to one folder.
    """
    pastas = [p.strip() for p in (os.getenv("EXECUTOR_SYNC_DIRS") or "").split(",") if p.strip()]
    return pastas[0] if pastas else None


def _publicar_com_retry(temporario: str, destino: str, tentativas: int = 4) -> None:
    """`os.replace` with a short retry, because of Windows.

    The GeoSync scanner runs in a THREAD of this same process and opens the
    files in the folder to compute MD5. On Windows, `os.replace` over a file
    that another handle keeps open fails with PermissionError — POSIX allows
    it, Windows does not. The window is small, but the collision happens
    precisely in the common case: a recurring workflow rewriting the same
    file in a folder scanned every 10 s.

    Without this, the symptom would be the run failing with "[WinError 5] Acesso
    negado" (access denied), which tells the reader nothing. Four attempts amply
    cover the time of one hash; if it still fails, the exception propagates —
    the problem is not transient.
    """
    import time

    for tentativa in range(tentativas):
        try:
            os.replace(temporario, destino)
            return
        except PermissionError:
            if tentativa == tentativas - 1:
                raise
            logger.debug(
                "Arquivo '%s' em uso (provavelmente o scanner do GeoSync); "
                "tentando de novo.", destino,
            )
            time.sleep(0.25 * (tentativa + 1))


def salvar_na_pasta_do_geosync(
    content: bytes, filename: str, workspace_id: str, overwrite: bool = False,
) -> str:
    """Writes a Drive file into the synced folder. Returns the path.

    GeoSync catalogs it on the next scan (`uploader.register` →
    `POST /drive/executor-register`), and from then on it is a Drive file like
    any other cataloged one: it shows up with the badge, has no download, and is
    resolved by the sync manifest. None of that had to be written — it already
    existed for catalog mode, and reusing it is what spared a new column,
    migration and endpoint.

    ⚠️ ATOMIC write. The scanner sweeps the folder every 10 s and recognizes the
    file by size and mtime; caught mid-write, it would be cataloged half-done.
    We write to a name starting with a dot — which the scanner ignores
    (`executor/sync/scanner.py`) — and do an `os.replace`, which is atomic on the
    same file system.
    """
    import uuid

    # ⚠️ ONLY in catalog mode. This is the guard that prevents the exact opposite of
    # what the option promises: in `upload` or `bidirectional`, GeoSync sweeps the
    # folder every 10 s and SENDS the bytes of everything it finds (`_upload_dataset`
    # only calls `register` when the mode is `catalog`). Writing here on such a
    # machine would publish to MinIO, within seconds, the file someone had just
    # marked not to leave — and with no sign at all that it happened.
    if localidade_padrao() != EXECUTOR:
        raise ValueError(
            "Não é possível manter um arquivo do Drive apenas neste executor "
            "enquanto ele estiver sincronizando a pasta com o servidor: o "
            "GeoSync enviaria o arquivo na varredura seguinte.\n\n"
            "O que fazer: configure a máquina para reter os dados (app do "
            'executor: GeoSync > Localidade dos dados > "Manter apenas no '
            'executor"), ou troque o destino deste nó para Artefatos, que '
            "aceita conteúdo local em qualquer modo de sincronização."
        )

    pasta = pasta_do_geosync()
    if not pasta:
        raise ValueError(
            "Este executor não tem nenhuma pasta do GeoSync configurada, e é ela "
            "que recebe os arquivos do Drive mantidos localmente. Configure uma "
            "no app do executor (GeoSync → Pasta), ou envie este arquivo para o "
            "servidor."
        )
    if not os.path.isdir(pasta):
        raise ValueError(f"A pasta do GeoSync não existe mais neste computador: {pasta}")

    # GeoSync syncs against ONE workspace. If it was pinned in `.env` and is not
    # the run's, writing here would publish the file to the WRONG Drive — another
    # customer's, possibly. Empty means auto-detection, which only happens
    # when there is an accessible workspace (executor/main.py) and therefore matches.
    ws_sync = (os.getenv("EXECUTOR_WORKSPACE_ID") or "").strip()
    if ws_sync and ws_sync != workspace_id:
        raise ValueError(
            f"A pasta do GeoSync deste executor sincroniza com o workspace "
            f"'{ws_sync}', mas este workflow roda no workspace '{workspace_id}'. "
            "O arquivo iria para o Drive errado."
        )

    destino = os.path.join(pasta, filename)
    if os.path.exists(destino) and not overwrite:
        raise ValueError(
            f"Já existe um arquivo chamado '{filename}' na pasta do GeoSync "
            f"({pasta}). Ligue 'Sobrescrever se já existir' para substituí-lo, "
            "ou mude o nome do arquivo neste nó."
        )

    temporario = os.path.join(pasta, f".atlans-tmp-{uuid.uuid4().hex}")
    try:
        with open(temporario, "wb") as fh:
            fh.write(content)
        _publicar_com_retry(temporario, destino)
    except BaseException:
        # An orphaned temp file would be invisible to the user (starts with a dot) and
        # to the scanner, and would take up disk space forever.
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise

    logger.info("Arquivo do Drive gravado na pasta do GeoSync: %s", destino)
    return destino


def upload_artifact_to_minio(
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    content_type: str = "application/octet-stream",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
    create_drive_entry: bool = False,
    overwrite: bool = False,
) -> tuple[str, dict]:
    """
    Uploads an artifact to MinIO via a pre-signed URL obtained from the server.
    If the upload fails, saves it locally (executor disk) as a fallback.

    `overwrite` only applies with create_drive_entry=True — see _upload_via_presigned_url.
    """
    if not filename:
        raise ValueError("filename é obrigatório para upload de artefato.")
    if not workspace_id or not task_id:
        raise ValueError("workspace_id e task_id são obrigatórios.")

    # Convert fileobj to bytes if needed. Validated before the try so that a
    # programming error (no content) does not fall into the local fallback
    # writing an empty file.
    if content is None and fileobj is not None:
        pos = fileobj.tell()
        content = fileobj.read()
        fileobj.seek(pos)
    if content is None:
        raise ValueError("Deve fornecer content (bytes) ou fileobj para upload.")

    s3_key = f"artifacts/{workspace_id}/{task_id}/{filename}"
    local_fallback = False
    drive_file_id: str | None = None
    drive_reused = False

    try:
        s3_key, drive_file_id, drive_reused = _upload_via_presigned_url(
            content, filename, content_type, workspace_id, task_id,
            create_drive_entry=create_drive_entry,
            overwrite=overwrite,
        )
    except Exception as exc:
        logger.warning("Upload via pre-signed URL falhou — salvando localmente: %s (%s)", filename, exc)
        _save_local_fallback(content, workspace_id, task_id, filename)
        local_fallback = True

    artifact_meta = {
        "output_key": label or filename,
        "format": fmt,
        "features": features,
        "filename": filename,
        "credential_id": credential_id,
        "s3_key": s3_key,
        # Always 'minio' on this route, EVEN when the upload failed and the
        # content stayed on disk: the fallback is a state to fix, not a
        # locality policy. Treating the two as equal would turn a network
        # outage into "protected data" in the server's record.
        "content_location": "minio",
        "local_fallback": local_fallback,
        # Size of the content, already at hand. Only used by the server when the
        # artifact ends up registered as local (keepLocal OR fallback) — there,
        # there is no object for a HEAD to measure. Without this, an artifact that
        # fell into the fallback showed up in Drive/Artifacts with an unknown size.
        "size_bytes": len(content),
        "drive_file_id": drive_file_id,
        # True when the server reused the existing WorkspaceFile. Always
        # False outside the Drive flow and when the upload fell into the local fallback.
        "drive_reused": drive_reused,
    }

    return s3_key, artifact_meta
