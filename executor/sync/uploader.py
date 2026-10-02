# executor/sync/uploader.py
"""
DriveUploader — envia datasets para o Drive do Workspace via pre-signed URLs (MinIO).
Fluxo: pede URL → PUT direto no MinIO → confirma na API.
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

# Tamanho de chunk do streaming/hash. Grande o bastante para nao pagar overhead
# de troca de contexto por 8 KB, pequeno o bastante para nao segurar memoria.
_CHUNK = 1024 * 1024


@dataclass
class UploadResult:
    """
    Resultado de um upload confirmado.

    `remote_name` e `remote_md5` descrevem o OBJETO que foi de fato enviado — que
    para um shapefile nao e nenhum dos arquivos locais, e sim o `<dataset>.zip`.
    Sem esses dois campos no manifesto, o proximo `_remote_to_local` via o zip
    como arquivo novo, baixava-o para a pasta do usuario e colidia na mesma
    chave do dataset, destruindo 'files'/'local_md5' a cada reinicio.
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
        """Fecha o cliente HTTP compartilhado (chamado no shutdown do manager)."""
        await self._http.aclose()

    def _headers(self) -> dict:
        """Sem headers de auth — identidade vem do cert mTLS no handshake TLS."""
        return {}

    @staticmethod
    def remote_name_for(dataset: Dataset) -> str:
        """Nome do objeto que sera criado no Drive para este dataset."""
        if dataset.type == "shapefile":
            return f"{dataset.name}.zip"
        primary = dataset.primary_path
        return primary.name if primary else dataset.name

    def _contained(self, path: Path, context: str) -> bool:
        """
        Revalida a contencao imediatamente antes de abrir o arquivo.

        O scanner ja pula symlinks, mas entre o scan e o upload a arvore pode ter
        mudado. O download e contido por `safe_join` desde sempre; o upload nao
        tinha contencao nenhuma — essa assimetria era o vetor de vazamento.
        """
        if is_inside(self.sync_dir, path):
            return True
        logger.error("Upload de '%s' recusado (%s): o caminho resolvido sai da pasta de sync '%s'.",
                     path.name, context, self.sync_dir)
        return False

    async def upload(self, dataset: Dataset, spatial_metadata: dict | None = None) -> UploadResult | None:
        """
        Faz upload de um dataset via pre-signed URL.
        Shapefile: zipa antes, envia como .zip.
        Retorna UploadResult ou None em caso de falha.
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
        """Registra o dataset no Drive SEM enviar os bytes (modo catalogo).

        Para dado pessoal (LGPD): o servidor passa a conhecer o arquivo — nome,
        tipo, tamanho, CRS, bbox, contagem de feicoes — e a saber que ele esta
        NESTE executor, mas o conteudo nunca sai da maquina.

        Devolve o mesmo `UploadResult` do `upload()` para que o manager trate os
        dois caminhos igual. `remote_md5` vai vazio de proposito: nao ha objeto
        remoto para comparar, e inventar um hash faria o diff do proximo ciclo
        concluir que o arquivo mudou.
        """
        primary = dataset.primary_path
        if not primary:
            logger.warning("Dataset '%s' sem arquivo principal — registro ignorado.", dataset.name)
            return None

        # Para shapefile o nome remoto e o do bundle ('<dataset>.zip'), o mesmo
        # que o upload usaria: o Drive mostra um item so, e trocar a convencao
        # aqui faria o mesmo dataset aparecer com dois nomes conforme o modo.
        remote_name = self.remote_name_for(dataset)

        corpo = {
            "filename": remote_name,
            "workspace_id": self.workspace_id,
            "size": dataset.total_size,
            "spatial_metadata": spatial_metadata or {},
            # Nome do dataset no manifesto local. E por ele que o executor
            # reencontra o arquivo na leitura — nao ha caminho trafegando.
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
        """Remove um arquivo do Drive. Devolve se o registro NAO esta mais la.

        A rota e `/drive/executor-file/{id}` — um endpoint mTLS de executor, e
        NAO o `DELETE /drive/{id}` do usuario. Os dois motivos sao o mesmo
        motivo de todos os outros metodos deste uploader usarem o prefixo
        `executor-`: o `/drive/{id}` cru exige JWT (que o executor nao tem) e, no
        host dos executores, o Traefik so roteia `/drive/executor-*` para a
        API. Apontar a delecao para `/drive/{id}` fazia o pedido morrer no
        Traefik com 404 — o arquivo NUNCA saia do Drive.

        **404 conta como sucesso.** O objetivo e "este registro nao deve
        existir", e um 404 do endpoint correto significa que ele ja nao existe
        (apagado pelo Drive web, ou por uma tentativa anterior). Tratar 404 como
        falha criava um retry que nunca converge. E a mesma politica do
        `allow_missing=True` que o servidor usa no `delete_strict`.
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
        # MD5 do conteudo REAL enviado, calculado fora do event loop. E esse valor
        # que o servidor devolve como `content_md5` no executor-list, entao e ele
        # que precisa ir para o manifesto — nao o hash combinado do dataset local.
        content_md5 = await em_thread(_file_md5, file_path)

        try:
            # As tres etapas usam o MESMO cliente: cada `AsyncClient` novo
            # refazia o handshake mTLS inteiro, entao um arquivo de 3 KB pagava
            # ~6 RTTs so de TLS — o mesmo custo de um raster de 2 GB.
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

            # 2. PUT direto no MinIO (sem headers de auth — URL pre-assinada).
            #    Streaming: ler o arquivo inteiro com f.read() estourava a memoria
            #    em raster/gpkg grandes E bloqueava o event loop. Com
            #    Content-Length explicito o httpx nao cai em Transfer-Encoding:
            #    chunked, que o MinIO recusa em URL pre-assinada.
            put_resp = await cliente.put(
                upload_url,
                content=_aiter_file(file_path),
                headers={"Content-Length": str(file_size)},
            )
            if put_resp.status_code not in (200, 201):
                logger.warning("PUT MinIO falhou: HTTP %d", put_resp.status_code)
                return None

            # 3. Confirma upload na API
            # CRS, bbox e contagem de feicoes so podem ser calculados por quem
            # tem o arquivo. Iam junto no modo `register` e eram descartados
            # aqui, entao todo dataset sincronizado pelo modo padrao aparecia no
            # Drive sem dado espacial nenhum.
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

        # Revalida CADA componente antes de abrir: o bundle e zipado sem passar
        # pelo validador (que so olha o .shp), entao um '.dbf' que virou symlink
        # para fora entraria no pacote sem nenhuma checagem.
        members: list[tuple[Path, str]] = []
        for finfo in dataset.files.values():
            if not self._contained(finfo.path, "componente de shapefile"):
                return None
            members.append((finfo.path, finfo.filename))

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # ZIP_DEFLATED de um bundle grande e CPU+I/O puro: rodar na corrotina
            # segurava o heartbeat de 30s (unico keepalive do executor) e o
            # servidor fechava a conexao com 4408, matando o run em andamento.
            await em_thread(_write_zip, tmp_path, members)

            logger.info("Shapefile '%s' empacotado (%d arquivos, %d bytes).",
                        dataset.name, len(members), tmp_path.stat().st_size)

            return await self._upload_file(tmp_path, zip_name, spatial_metadata)
        finally:
            tmp_path.unlink(missing_ok=True)


def _write_zip(zip_path: Path, members: list[tuple[Path, str]]):
    """Compacta os membros no zip. Sincrono por natureza — chamar via to_thread."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for source, arcname in members:
            zf.write(source, arcname)


def _file_md5(path: Path) -> str:
    """MD5 do conteudo. Sincrono por natureza — chamar via to_thread."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


async def _aiter_file(path: Path):
    """Gera o corpo do PUT em pedacos, lendo o disco fora do event loop.

    Pool de I/O, nao o pesado: no mesmo pool de 2 threads, um `_write_zip` de
    bundle de GB parava TODOS os PUTs em voo pelo tempo da compactacao — e o
    MinIO fecha conexao ociosa.
    """
    with open(path, "rb") as f:
        while True:
            chunk = await em_thread_io(f.read, _CHUNK)
            if not chunk:
                break
            yield chunk
