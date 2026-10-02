# flow/utils/drive_resolver.py
"""
Resolve arquivos armazenados (Drive do Workspace ou Artefatos de execucao):
pede ao servidor uma pre-signed URL, baixa para arquivo temporario e retorna
o caminho local.

Usado pelos nos de leitura de arquivo (ReadGeoJSON, ReadShapefile, etc.),
e pelo DataInput (contexto Drive ou Artefatos).

Contextos:
  Drive       — WorkspaceFile por id_hash (resolve_drive_file)
  Artefatos   — Artifact por id_hash (resolve_artifact_file)

O motor roda sempre no executor (externo/on-premise), que nao tem acesso ao
banco nem credenciais do MinIO. Autorizacao e escopo de workspace sao decididos
pelo servidor, que identifica o executor pelo cert mTLS e responde com uma
pre-signed URL de TTL curto para aquele objeto:

  GET /drive/executor-download/{id}           → arquivo do Drive
  GET /drive/executor-download-artifact/{id}  → artefato de execucao
"""
import os
import tempfile
from typing import TYPE_CHECKING

from flow.utils.logger import get_logger

if TYPE_CHECKING:
    # So para anotacao: `Path` e importado tardiamente dentro das funcoes, como
    # o resto dos imports pesados deste modulo. As anotacoes sao strings e nunca
    # sao avaliadas em runtime — este bloco existe para que type checker e lint
    # enxerguem o nome.
    from pathlib import Path

logger = get_logger(__name__)


async def read_drive_file_as(drive_file_id, reader, *, label="arquivo", reraise=()):
    """Resolve o arquivo do Drive, chama `reader(temp_path)` em thread e remove o
    temp. Converte falha de leitura em RuntimeError com o nome original.

    Centraliza o padrão resolve→ler→unlink→wrap repetido pelos nós ReadGeoJSON/
    ReadShapefile/ReadGeoParquet/ReadCSVWithCoords. `reader` é um callable síncrono
    `(temp_path) -> dados`. `reraise` é uma tupla de exceções a propagar como estão
    (ex.: ValueError de validação de coluna no CSV), sem virar RuntimeError.
    Retorna `(dados, original_name)`.
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
    Obtem a pre-signed URL + metadados do arquivo do Drive via
    GET /drive/executor-download/{id_hash}, baixa para temp file e retorna
    (temp_path, extension, original_name).

    O caller e responsavel por remover o temp file apos o uso.
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
    Obtem a pre-signed URL + metadados do artefato via
    GET /drive/executor-download-artifact/{id_hash}, baixa para temp file e
    retorna (temp_path, extension, original_name).

    O caller e responsavel por remover o temp file apos o uso.
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

    # GET idempotente: retry_sync retenta apenas transitorios (connect/read).
    # O tratamento de status (403/404/5xx) fica FORA do retry — esses sao
    # permanentes e nao devem ser re-tentados.
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

    # Conteudo que nunca saiu deste executor (LGPD): o servidor nao tem o objeto
    # e responde com a localizacao em vez de uma pre-signed URL.
    if body.get("content_location") == "executor":
        dono = body.get("executor_id") or ""
        local_path = body.get("local_path")
        if local_path:
            # Artefato: o servidor DERIVOU o caminho relativo a raiz de
            # artefatos no registro (run_result_consumer).
            return _copy_local_to_temp(local_path, dono, ext, original_name)
        # Arquivo do Drive catalogado pelo GeoSync: o servidor nao guarda
        # caminho nenhum — quem sabe onde o arquivo esta e o manifesto de sync
        # desta maquina.
        return _resolve_do_manifesto_de_sync(_id_do_path(path), dono, ext, original_name)

    download_url: str = body["download_url"]
    return _stream_presigned_to_temp(download_url, ext, original_name, verify)


def _id_do_path(path: str) -> str:
    """Extrai o id_hash do final de '/drive/executor-download/{id}'."""
    return path.rstrip("/").rsplit("/", 1)[-1]


def _resolve_do_manifesto_de_sync(
    id_hash: str, dono_id: str, ext: str, original_name: str,
) -> tuple[str, str, str]:
    """Acha um dataset catalogado varrendo os manifestos das pastas de sync.

    O servidor guarda que o arquivo e local e de qual executor, mas NAO onde ele
    esta: um caminho do sistema de arquivos do usuario nao tem por que existir
    no banco, e nao trafegar caminho nenhum elimina de saida a classe de ataque
    de path traversal.

    Quem sabe o caminho e o `.atlans-sync.json` de cada pasta sincronizada, que
    ja mapeia `remote_id_hash -> dataset -> arquivos`.
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
            # Copia pelo mesmo motivo de `_copy_local_to_temp`: o caller apaga
            # o caminho devolvido, e devolver o arquivo do usuario o destruiria.
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
    """Arquivo a ser lido de um dataset do manifesto.

    Espelha `Dataset.primary_path` de executor/sync/scanner.py: num shapefile o
    dataset e um bundle (.shp/.dbf/.shx) e quem se le e o `.shp`. Divergir daqui
    faria o ReadShapefile receber um `.dbf` e falhar de forma incompreensivel.
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
    """Copia um artefato local para um temp file e devolve o mesmo trio.

    ⚠️ COPIA, e nao devolve o caminho original — de proposito.

    `read_drive_file_as` faz `os.unlink(temp_path)` num `finally`, porque ate
    aqui todo caminho devolvido era um temporario baixado. Devolver o arquivo
    real faria o PRIMEIRO workflow que o lesse APAGAR o dado do usuario, em
    silencio, e o estrago so apareceria muito depois.

    A copia e local, entao nao viola a politica de localidade. O custo e I/O
    duplicado; a alternativa (sinalizar "nao apague" pelo contrato) exige
    revisar os cinco nos de leitura e todo codigo futuro que use o helper —
    troca ruim para a primeira versao.
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

    # Confinamento: `local_path` vem pela rede. O servidor o deriva (nao confia
    # no executor), mas depender disso seria terceirizar a propria seguranca —
    # um `../` aqui daria leitura de arquivo arbitrario da maquina.
    if not alvo.is_relative_to(raiz):
        raise PermissionError(
            f"Caminho de artefato local fora do diretorio permitido: {local_path!r}"
        )

    if not alvo.is_file():
        # Erro nomeado em vez de FileNotFoundError cru: quase sempre significa
        # que o artefato pertence a OUTRO executor, e o operador precisa saber
        # disso e nao ficar procurando um arquivo que nunca esteve aqui.
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
    """Faz streaming de uma pre-signed URL para um temp file e retorna
    (temp_path, ext, original_name). O caller remove o temp file."""
    import httpx
    from flow.utils.http_retry import retry_sync

    suffix = f".{ext}" if ext else ""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()

    def _download() -> None:
        # open("wb") trunca a cada tentativa → re-download idempotente no temp.
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
