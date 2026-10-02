# app/services/drive_service.py
"""Servico de Drive — logica de negocio para gerenciamento de arquivos via MinIO."""
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
    """Slug ASCII estrito — usado na CHAVE S3, onde o alfabeto restrito importa.

    Não usar para `original_name`: destrói acentos e espaços do nome que o
    usuário vê (`área de risco.gpkg` -> `_rea_de_risco.gpkg`). Para isso existe
    `safe_display_name`.
    """
    # Normaliza separadores Windows (\) para POSIX (/) antes de extrair o basename
    name = os.path.basename(name.replace("\\", "/"))
    name = _SLUG_RE.sub("_", name)
    return name[:200] or "arquivo"


# Caracteres de controle + aspas e ';' — os últimos dois quebrariam o
# `Content-Disposition: attachment; filename="..."` gerado no presigned GET.
_UNSAFE_DISPLAY_RE = re.compile(r'[\x00-\x1f\x7f";\\/]')


def safe_display_name(name: str) -> str:
    """Basename seguro PRESERVANDO acentos e espaços — para `original_name`.

    SEG: aplicar SEMPRE antes de persistir em `WorkspaceFile.original_name`.
    Esse campo é propagado ao executor via `emit_drive_event` e usado como
    destino de escrita no GeoSync (`sync_dir / original_name`) — um nome como
    `../../../etc/x.geojson`, ou um caminho absoluto, escapava do diretório
    sincronizado e virava escrita arbitrária de arquivo no host do executor.

    O que é removido: componentes de path, separadores, caracteres de controle
    e os que quebrariam o header Content-Disposition. O que é preservado:
    tudo o mais, inclusive Unicode — sanitizar demais aqui só degradaria o
    nome exibido na UI sem ganho de segurança.
    """
    # Normaliza separadores Windows (\) para POSIX (/) antes de extrair o basename
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
    """Barra a LEITURA pela plataforma de conteudo que mora no executor.

    Nao ha objeto no storage. Proxiar o download traria o dado ao servidor, que
    e exatamente o que a politica de localidade proibe — e sem o guard a
    chamada morre no boto3 com um 500 mudo.
    """
    if getattr(wf, "content_location", "minio") != "executor":
        return
    raise ConteudoNoExecutorError(
        "O conteudo deste arquivo permanece no executor e nunca foi enviado "
        "para a nuvem, entao nao ha o que baixar pela plataforma. Ele continua "
        "disponivel para workflows que rodem naquele mesmo executor."
    )


def _recusar_se_catalogado(wf) -> None:
    """Barra operacoes destrutivas sobre um arquivo que so existe no executor.

    Um arquivo catalogado (GeoSync em modo "Manter apenas no executor") tem
    `s3_key = NULL`: a plataforma guarda a ficha, nunca os bytes. Apagar este
    registro nao removeria nada do disco de quem tem o arquivo, e mandar o
    executor apaga-lo seria destruir dado do usuario que nunca pertenceu a
    plataforma.

    A saida esta na mensagem, e nao num "tem certeza?": quem quer que o arquivo
    suma apaga o arquivo, ou tira a pasta do GeoSync.
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
        """Valida extensao (incluindo double extension) e tamanho. Retorna a extensao.

        Cada recusa tem a sua subclasse de `FileValidationError` (e o seu
        `error_code`): e pelo codigo, e nao pela frase, que o web a classifica.
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
        """Retorna tupla (items, total) de arquivos confirmados do workspace."""
        query = select(WorkspaceFile).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.status == "confirmed",
        )
        count_query = select(sa_func.count(WorkspaceFile.id)).where(
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.status == "confirmed",
        )

        if search:
            # `%` e `_` do usuario sao literais, nao curingas (ver `contem`).
            nome_contem = contem(WorkspaceFile.original_name, search)
            query = query.where(nome_contem)
            count_query = count_query.where(nome_contem)
        if ext:
            query = query.where(WorkspaceFile.extension == ext.lower())
            count_query = count_query.where(WorkspaceFile.extension == ext.lower())

        total = (await self.db.execute(count_query)).scalar() or 0
        # Ordena pela ULTIMA ESCRITA. Um arquivo sobrescrito mantem o
        # created_at original — ordenar por ele faria o conteudo recem-gravado
        # aparecer no fim da lista, junto dos arquivos mais antigos.
        # coalesce cobre linhas que nunca sofreram update (updated_at NULL).
        ultima_escrita = sa_func.coalesce(
            WorkspaceFile.content_written_at, WorkspaceFile.created_at
        )
        query = query.order_by(ultima_escrita.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.db.execute(query)).scalars().all()

        return items, total

    async def list_files_for_agent(self, workspace_id: str) -> list[dict]:
        """Retorna lista simplificada de arquivos confirmados (para executores)."""
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

        # Upload direto ao MinIO
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
        """Cria registro pendente e gera presigned PUT URL (para executores).

        `overwrite=True` reaproveita o arquivo de mesmo nome que ja exista no
        workspace em vez de criar outro. Sem isso, um DataOutput agendado
        acumulava uma copia por execucao, todas com o mesmo nome no Drive.

        Reaproveitar significa manter a MESMA linha e a MESMA s3_key:

        - o `id_hash` nao muda, entao um DataInput apontando para este arquivo
          continua valido e passa a ler a versao nova — recriar a linha faria a
          referencia apontar para sempre ao conteudo antigo;
        - a s3_key preservada faz o PUT sobrescrever o objeto no MinIO, sem
          deixar o anterior orfao ocupando disco.
        """
        filename = safe_display_name(filename)
        # Uploads de artefatos (s3_key_override) pulam validacao de extensao do Drive
        if s3_key_override:
            ext = Path(filename).suffix.lstrip(".").lower() if filename else ""
        else:
            ext = await self.validate_upload(filename, size)

        mime_type, _ = mimetypes.guess_type(filename)
        s3_key = s3_key_override or make_s3_key(workspace_id, filename)
        # Usa content_type do body (executor envia o tipo exato) ou detectado via mimetypes
        final_ct = content_type_override or mime_type or "application/octet-stream"

        wf = None
        if overwrite:
            # Mais recente entre os confirmados: se ja houver duplicatas de
            # execucoes anteriores, sobrescreve a que o usuario ve no topo da
            # listagem e deixa as antigas intactas para remocao manual.
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

            # NAO volta para "pending" e NAO mexe em `size`. Marcar pending
            # tirava o arquivo da listagem durante o upload e, pior, o tornava
            # elegivel para cleanup_pending_workspace_files, que apaga pending
            # com created_at anterior ao TTL — e o created_at aqui e o da
            # criacao ORIGINAL, ja vencido em qualquer arquivo com mais de 24h.
            # Um upload que falhasse destruiria o arquivo integro que existia.
            # O PUT no MinIO e atomico: ou substitui inteiro, ou o conteudo
            # anterior permanece. size/content_md5 sao atualizados no
            # confirm_upload, a partir do objeto real.
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

        # Pre-signed URL para executor (usa MINIO_EXTERNAL_ENDPOINT, acessivel fora do Docker)
        upload_url = await s3.presigned_put_async(s3_key, content_type=final_ct)
        # `reused` diz ao chamador o que de fato aconteceu. Sem ele o executor
        # so podia repetir a intencao ("pedi para sobrescrever"), nunca o
        # desfecho — e um overwrite que nao encontrou o arquivo era
        # indistinguivel de um que encontrou.
        return {
            "upload_url": upload_url,
            "id_hash": wf.id_hash,
            "s3_key": s3_key,
            "reused": reaproveitou,
        }

    # ── Confirmacao de upload ─────────────────────────────────────────────

    def _e_upload_de_drive_pendente(self, wf: WorkspaceFile) -> bool:
        """O confirm esta fechando um upload de Drive que ainda nao foi aceito?

        So esse caso pode ser recusado destrutivamente, e o escopo e estreito de
        proposito — cada condicao aqui evita um estrago concreto:

        - `status == "pending"`: a linha foi criada para ESTE upload e nunca
          apareceu na listagem. Sem isso, `confirm_upload` — que nao filtra por
          status e e alcancavel por qualquer editor do workspace — viraria um
          botao de apagar: bastava re-confirmar arquivo alheio ja aceito que
          estivesse acima do teto CORRENTE (o admin pode ter baixado
          `max_size_mb` depois) para o objeto e o registro sumirem.
        - chave sob `drive/`: artefatos de execucao entram por
          `create_agent_upload_url(s3_key_override=...)`, que pula
          `validate_upload` INTEIRA — extensao e tamanho. Nunca houve teto para
          eles, e aplica-lo agora derrubaria a run (o executor faz
          `raise_for_status` no confirm) e, com `overwrite=True`, apagaria o
          arquivo bom que estava no Drive. O teto aqui existe para espelhar a
          validacao do tamanho DECLARADO; onde nao houve declaracao validada,
          nao ha o que reconferir.
        - workspace da chave igual ao da linha: `_validate_agent_s3_key` confere
          a chave contra TODOS os workspaces do executor, nao contra o da linha,
          entao um `s3_key_override` pode apontar para o objeto de outro
          workspace. Apagar por esse caminho destruiria bytes alheios.
        """
        if wf.status != "pending" or not wf.s3_key:
            return False
        partes = wf.s3_key.split("/")
        return len(partes) > 2 and partes[0] == "drive" and partes[1] == wf.workspace_id

    def _e_artefato_de_execucao_pendente(self, wf: WorkspaceFile) -> bool:
        """O confirm esta fechando um artefato de execucao (via s3_key_override)?

        Artefatos de execucao entram por `create_agent_upload_url(s3_key_override=
        ...)`, que pula `validate_upload` INTEIRA — extensao E tamanho. Nunca houve
        tamanho DECLARADO, entao nao ha o que o teto reconferir, e aplica-lo
        derrubaria a run (o executor faz `raise_for_status` no confirm) — o bug que
        recusava artefato de execucao grande. A chave mora sob `artifacts/{ws}/...`;
        exigir o workspace da PROPRIA linha mantem a guarda contra chave
        cross-workspace, que NAO se enquadra aqui e segue recusada.
        """
        if wf.status != "pending" or not wf.s3_key:
            return False
        partes = wf.s3_key.split("/")
        return len(partes) > 2 and partes[0] == "artifacts" and partes[1] == wf.workspace_id

    async def _recusar_acima_do_teto(self, wf: WorkspaceFile, tamanho_real: int) -> None:
        """Aplica `max_size_mb` ao objeto REAL, no confirm. Sem isso o teto e opcional.

        No upload por URL pre-assinada quem diz o tamanho e o cliente: o
        `create_upload_url` valida o numero que veio no corpo e o PUT vai
        direto ao MinIO, que nao conhece limite nenhum. Declarar 1 KB e enviar
        5 GB passava — e o `confirm_upload` ainda MEDIA o objeto (`head_async`)
        e gravava o tamanho verdadeiro em `size` sem nunca compara-lo ao teto.
        O arquivo entrava na listagem, contava na cota e podia ser baixado.

        Recusar exige apagar o objeto: ele ja esta no storage, e uma recusa que
        deixasse os bytes la seria so uma forma mais lenta de aceita-los — o
        `cleanup_pending_workspace_files` do reconcile apaga a LINHA vencida,
        nunca o objeto. A linha vai junto porque, sem o objeto, ela nao descreve
        nada.

        Quem NAO se enquadra em `_e_upload_de_drive_pendente` tambem e recusado,
        mas sem apagar nada: melhor um objeto acima do teto que o reconcile
        acusa como divergencia do que um caminho de exclusao sem confirmacao e
        sem lixeira.
        """
        settings = await self.get_settings()
        max_bytes = settings.max_size_mb * 1024 * 1024
        if tamanho_real <= max_bytes:
            return

        # Artefato de execucao (s3_key_override) pulou validate_upload: nao
        # declarou tamanho, entao nao ha o que reconferir. Aceita sem apagar —
        # aplicar o teto aqui derrubaria a run. Ja-confirmados e chaves
        # cross-workspace NAO se enquadram e seguem recusados abaixo.
        if self._e_artefato_de_execucao_pendente(wf):
            logger.info(
                "Drive: artefato de execucao '%s' (ws=%s) tem %s bytes, acima do teto "
                "de %sMB — aceito (upload de execucao nao declara tamanho ao teto).",
                wf.original_name, wf.workspace_id, tamanho_real, settings.max_size_mb,
            )
            return

        # Locais ANTES do delete: depois do commit a instancia esta removida da
        # sessao e ler atributo dela e erro.
        s3_key, nome, ws_id = wf.s3_key, wf.original_name, wf.workspace_id
        excedeu = f"'{nome}' (ws={ws_id}) tem {tamanho_real} bytes, acima do teto de {settings.max_size_mb}MB"

        if not self._e_upload_de_drive_pendente(wf):
            logger.warning("Drive: %s — confirmacao recusada; objeto e registro mantidos.", excedeu)
            raise FileTooLargeError(f"Arquivo excede {settings.max_size_mb}MB.")

        logger.warning("Drive: %s — recusado; objeto e registro removidos.", excedeu)
        # `storage.delete` e best-effort e NUNCA levanta: devolve False. Um
        # `except` aqui seria codigo morto — o que informa e o retorno.
        if not await s3.delete_async(s3_key):
            # A recusa nao depende disso. Os bytes orfaos aparecem no drift do
            # reconcile; aceitar o arquivo para nao deixar lixo seria pior.
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
        """Confirma que o upload foi concluido verificando existencia no MinIO.

        `spatial_metadata` (CRS, bbox, contagem de feicoes) so pode ser calculado
        por quem tem o arquivo — o executor. No modo `register` ele ja era
        enviado; no modo `upload`, que e o default do GeoSync, era descartado, e
        o arquivo aparecia no Drive sem nenhum dado espacial. Vem opcional
        porque executor antigo confirma sem corpo nenhum.
        """
        result = await self.db.execute(select(WorkspaceFile).where(WorkspaceFile.id_hash == id_hash))
        wf = file_or_404(result.scalar_one_or_none())

        obj = await s3.head_async(wf.s3_key)
        if not obj:
            raise FileNotFoundError("Arquivo nao encontrado no storage.")

        await self._recusar_acima_do_teto(wf, obj["size"])

        # content_md5 so e preenchido aqui, no confirm. Ja vir preenchido
        # significa que esta linha foi reaproveitada por um upload com
        # overwrite=True — para o GeoSync do executor isso e file_updated, nao
        # file_created (ver executor/sync/manager.py, que trata os dois).
        acao = "file_updated" if wf.content_md5 else "file_created"

        wf.status = "confirmed"
        wf.size = obj["size"]
        wf.content_md5 = obj["etag"]
        # Explicito, e nao via onupdate: numa sobrescrita com conteudo IDENTICO
        # os tres campos acima recebem os mesmos valores, nenhum atributo fica
        # sujo, o SQLAlchemy nao emite UPDATE e `updated_at` nao avancaria — o
        # arquivo recem-gravado nao subiria na listagem e o usuario nao veria
        # sinal nenhum de que o workflow rodou.
        wf.content_written_at = utc_now_naive()
        # Só sobrescreve quando veio algo: um confirm sem metadado (executor
        # antigo, ou dataset sem camada vetorial legível) não pode apagar o que
        # uma passada anterior já tinha registrado.
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
        # A guarda vive AQUI, e nao no router: o caminho do executor
        # (/drive/executor-download) ja recusava conteudo local, e o do usuario
        # (/drive/{id}/download) chegava direto no presign com `s3_key=None` —
        # o boto3 valida `Key=None` no CLIENTE e levanta ParamValidationError,
        # que nao e ClientError, escapa de todo `except` do caminho e vira um
        # 500 que nao explica nada. A UI esconde o botao; a rota continua
        # alcancavel por atalho, cache da lista ou chamada direta.
        _recusar_se_local(wf)
        url = await s3.presigned_get_async(wf.s3_key, filename=wf.original_name)
        return {"download_url": url, "filename": wf.original_name}

    # ── Delecao ───────────────────────────────────────────────────────────

    async def delete_file(self, wf: WorkspaceFile) -> None:
        """Deleta arquivo do S3 e do banco, emitindo evento.

        Politica: S3 PRIMEIRO via delete_strict. Se falhar (exceto 'not found'),
        nao apaga o registro do DB — assim a reconciliacao tenta de novo e o
        objeto nao vira orfao no MinIO consumindo disco sem reflexo no relatorio.

        Arquivo CATALOGADO (`content_location='executor'`) e recusado: ver
        `_recusar_se_catalogado`.
        """
        _recusar_se_catalogado(wf)
        del_info = {
            "id_hash": wf.id_hash, "original_name": wf.original_name,
            "extension": wf.extension, "size": wf.size,
        }
        del_ws = wf.workspace_id

        # `if wf.s3_key` e defensivo, e nao redundante com a guarda acima: sem
        # ele, uma chave nula chega ao boto3, que valida `Key=None` no CLIENTE e
        # levanta ParamValidationError — que NAO e ClientError, escapa do
        # `except` de `delete_strict` e vira 500. Um 500 por chave nula nao pode
        # depender de um guard a dez linhas de distancia.
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
        """Remove um arquivo do Drive por ordem do executor que sincroniza a pasta.

        Espelha `delete_file`, com UMA diferenca deliberada: aceita o arquivo
        CATALOGADO (`content_location='executor'`). O caminho do usuario o recusa
        — apaga-lo pelo web nao removeria os bytes, que vivem no executor — e
        `_recusar_se_catalogado` manda, na propria mensagem, "apague o arquivo na
        pasta sincronizada do executor". E exatamente esse pedido que chega aqui:
        o proprio executor dono avisando que o arquivo saiu da pasta. Apagar a
        ficha e o desfecho correto, nao uma operacao proibida.

        Guarda: so o executor DONO do catalogo pode apaga-lo — um executor nao
        remove a ficha de conteudo que vive em outro.
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

        # S3 PRIMEIRO, mesma politica de `delete_file`: se o objeto nao sai, o
        # registro fica de pe para a reconciliacao tentar de novo, em vez de
        # virar orfao no MinIO. Catalogo tem `s3_key=None` e pula esta etapa.
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

        # Exclui o proprio executor do fan-out: ele ja removeu o arquivo
        # localmente (foi ele quem originou a delecao), entao reenviar o
        # `file_deleted` so provocaria um `_discard_dataset` redundante nele.
        await emit_drive_event(del_ws, "file_deleted", del_info, exclude_agent_id=executor_id)

    async def batch_delete_files(
        self,
        id_hashes: list[str],
        workspace_ids: list[str],
        current_user_id: str,
    ) -> tuple[int, int]:
        """Deleta multiplos arquivos.

        Devolve `(apagados, catalogados_pulados)`. O segundo numero existe para a
        UI nao dizer "5 arquivos deletados" quando 2 eram catalogados e foram
        ignorados — uma contagem que mente e pior que nenhuma.
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

        # Pre-carrega roles para evitar N+1 no loop
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
        # Eventos a emitir DEPOIS do commit. Os campos sao capturados enquanto a
        # instancia esta viva: apos o commit ela esta expirada e ler qualquer
        # atributo dispararia um refresh de uma linha que ja nao existe.
        eventos: list[tuple[str, dict]] = []
        for wf in files:
            if wf.workspace_id not in workspace_ids:
                continue
            if not _can_edit_ws(wf.workspace_id):
                continue
            # Catalogado: PULA em vez de derrubar o lote. Um lote misto e o caso
            # normal — selecionar tudo numa pasta que tem os dois tipos — e
            # falhar inteiro por causa deles impediria apagar o resto.
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

        # Mesma promessa do `delete_file`: cada remocao confirmada avisa os
        # executores do workspace (`file_deleted`), para que um executor em
        # download/bidirectional remova a copia local. Sem isto, a exclusao em
        # lote pela UI sumia do Drive mas ressuscitava no executor no ciclo
        # seguinte (ele rebaixava o arquivo, servidor como fonte de verdade).
        # So DEPOIS do commit — anunciar algo que um rollback desfez seria
        # mentira — e best-effort: `emit_drive_event` engole as proprias falhas,
        # entao um Redis fora do ar nao desfaz a remocao ja persistida.
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
        # pin-cache/ e artifacts/ usam workspace_id no path (artifacts/{ws_id}/{task_id}/file)
        # Validação direta pelo path — não depende de registro no banco
        # (artefatos do SendEmail podem não estar na tabela Artifact ainda)
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
