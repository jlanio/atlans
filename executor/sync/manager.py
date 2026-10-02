# executor/sync/manager.py
"""
SyncManager — orquestrador principal do GeoSync.
Coordena watcher, scanner, validator, uploader e manifesto.
"""
import asyncio
import logging
import time
import weakref
from pathlib import Path

from flow.utils.backoff import espera_exponencial

from executor.sync.manifest import SyncManifest
from executor.sync.pool import em_thread
from executor.sync.scanner import DatasetScanner, Dataset, SUPPORTED_EXTENSIONS
from executor.sync.validator import validate_dataset
from executor.sync.metadata import extract_metadata
from executor.sync.uploader import DriveUploader, UploadResult
from executor.sync.watcher import FileWatcher
from executor.sync.queue import SyncQueue
from executor.sync.ignore import IgnoreFilter
from executor.sync.paths import (
    TRASH_DIR_NAME,
    TRASH_RETENTION_DAYS,
    TRASH_WARN_BYTES,
    move_dataset_to_trash,
    purge_trash,
    safe_join_or_none,
)
from executor.sync.events import SyncEventEmitter
from executor.sync.downloader import DriveDownloader
from executor.sync.trigger import SyncTrigger
from executor.sync.sync_config import (
    SYNC_CONCURRENCY,
    SYNC_FLUSH_INTERVAL,
    SYNC_FULL_HASH_INTERVAL,
    SYNC_MAX_QUIET_WAIT,
    SYNC_MIN_CYCLE,
    SYNC_QUIET_PERIOD,
    SyncConfig,
)
from executor import config as agent_config

logger = logging.getLogger("executor.sync")

# Teto do backoff aplicado quando um ciclo inteiro de sync falha.
_MAX_CYCLE_BACKOFF = 300

# Teto de transferencias simultaneas do PROCESSO, nao de cada pasta. O motivo do
# teto e o LINK (em conexao de campo, concorrencia alta piora o tempo total e
# arrisca estourar o timeout de 300s do PUT/GET) e o link e um so: com um
# semaforo por manager, tres pastas configuradas viravam 3xSYNC_CONCURRENCY
# transferencias disputando a mesma banda e as threads que as alimentam.
#
# E indexado pelo event loop porque um `asyncio.Semaphore` de modulo se prende
# ao primeiro loop que o aguarda — o que quebraria qualquer processo (ou teste)
# que rode mais de um loop na vida.
_semaforos_de_transferencia: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _semaforo_de_transferencia() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    semaforo = _semaforos_de_transferencia.get(loop)
    if semaforo is None:
        semaforo = asyncio.Semaphore(SYNC_CONCURRENCY)
        _semaforos_de_transferencia[loop] = semaforo
    return semaforo

# Intervalo entre expurgos da lixeira. O ciclo roda a cada `interval` (30s por
# padrao); varrer a lixeira nesse ritmo seria I/O puro em vao.
_TRASH_PURGE_INTERVAL = 6 * 3600


class SyncManager:
    """
    Gerencia a sincronizacao de uma pasta local com o Drive do Workspace.
    Suporta modos: upload, download, bidirectional.
    """

    def __init__(
        self,
        sync_dir: str,
        workspace_id: str,
        server_url: str,
        executor_id: str,
        interval: int = 30,
        event_queue: asyncio.Queue | None = None,
        drive_event_queue: asyncio.Queue | None = None,
    ):
        self.sync_dir = Path(sync_dir)
        self.workspace_id = workspace_id
        self.interval = interval

        # Cria pasta se nao existir
        self.sync_dir.mkdir(parents=True, exist_ok=True)

        # Componentes — autenticacao via mTLS (cert + chave do EXECUTOR_CERT_DIR).
        self.ignore = IgnoreFilter(sync_dir)
        self.events = SyncEventEmitter(event_queue)
        self.manifest = SyncManifest(sync_dir, workspace_id, executor_id)
        self.scanner = DatasetScanner(sync_dir, ignore_filter=self.ignore)
        self.uploader = DriveUploader(server_url, executor_id, workspace_id, sync_dir)
        self.watcher = FileWatcher(sync_dir, self._on_change, ignore_filter=self.ignore)
        self.downloader = DriveDownloader(server_url, executor_id, workspace_id)
        self.trigger = SyncTrigger(server_url, executor_id)
        self.sync_config = SyncConfig(sync_dir)
        self.queue = SyncQueue(self.manifest, self._execute_pending)
        self.sync_mode = agent_config.SYNC_MODE  # upload | download | bidirectional

        self._change_flag = asyncio.Event()
        self._drive_events = drive_event_queue  # Fila de eventos push do servidor
        self._drive_task: asyncio.Task | None = None
        self._syncing = False  # Flag para ignorar eventos do watcher durante sync
        self._last_trash_purge = 0.0
        # Ritmo do ciclo: `_ultimo_ciclo` sustenta o piso entre varreduras
        # disparadas pelo watcher e `_forcar_ciclo` e o furo do comando da UI.
        self._ultimo_ciclo = 0.0
        self._forcar_ciclo = False
        # None = ainda nao houve varredura com hash nesta execucao. Nao serve
        # 0.0 como "nunca": `time.monotonic()` e o uptime da maquina, e num
        # notebook ligado ha 5 minutos a conta daria "faz pouco tempo".
        self._ultimo_hash_completo: float | None = None
        # Scan compartilhado pelos itens de UMA passada da fila de retry.
        self._scan_da_fila: dict[str, Dataset] | None = None
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None  # construido fora do loop — run() preenche

    def sincronizar_agora(self) -> bool:
        """Acorda o ciclo sem esperar o intervalo. Devolve se conseguiu.

        O loop dorme em `_change_flag` com timeout de `interval` — o mesmo
        mecanismo que o watcher usa para avisar de mudanca local. Um comando
        vindo da UI e so mais um jeito de bater nessa porta.

        Diferenca: `_forcar_ciclo` fura o piso de intervalo e a espera por
        estabilizacao. O piso existe para conter a rajada do watchdog durante
        uma copia; um clique do usuario e intencao explicita e nao pode esperar.
        """
        loop = self._loop
        if loop is None:
            self._forcar_ciclo = True
            self._change_flag.set()
            return True
        try:
            loop.call_soon_threadsafe(self._acordar_forcado)
            return True
        except RuntimeError:
            return False  # loop ja fechado

    def _acordar_forcado(self):
        self._forcar_ciclo = True
        self._change_flag.set()

    def _emitir_inventario(self) -> None:
        """Publica quantos datasets ha, quantos em dia e quantos na fila.

        Sai como evento de sync, e nao como leitura direta do manifesto pelo
        stats: o manifesto e de outro processo logico (a task de sync) e le/grava
        em disco — consulta-lo a 1 Hz a partir do coletor de metricas colocaria
        I/O no caminho do snapshot. Emitir ao fim do ciclo custa nada e o dado
        so muda quando o ciclo roda.

        Best-effort: um inventario que falhe nao pode derrubar a sincronizacao.
        """
        try:
            datasets = self.manifest.all_datasets()
            pendentes = len(self.manifest.pending_items())
            sincronizados = sum(
                1 for d in datasets.values() if d.get("status") == "synced"
            )
            self.events.emit(
                "sync_inventory",
                dataset="",
                total=len(datasets),
                synced=sincronizados,
                pending=pendentes,
            )
        except Exception:
            logger.debug("Inventario de sync de '%s' falhou.", self.sync_dir, exc_info=True)

    def _on_change(self):
        """
        Callback do watcher — sinaliza que houve mudanca (ignorado durante sync).

        Roda na THREAD do watchdog, nunca no event loop: `asyncio.Event.set()`
        agenda os callbacks dos waiters com `loop.call_soon`, que nao e
        thread-safe (mexe na fila de prontos sem acordar o selector). Marshalamos
        com `call_soon_threadsafe`; sem loop (uso sincrono em teste) setamos
        direto.
        """
        if self._syncing:
            return
        loop = self._loop
        if loop is None:
            self._change_flag.set()
            return
        try:
            loop.call_soon_threadsafe(self._change_flag.set)
        except RuntimeError:
            pass  # loop ja fechado (shutdown) — nao ha ciclo para acordar

    # ── Fan-out de drive events ──────────────────────────────────────────────

    def claims_event(self, msg: dict) -> bool:
        """
        Diz se ESTE manager e o dono de um drive_event.

        Com varias pastas de sync, o main.py entrega cada evento push a um
        manager so. Este predicado e a peca que decide qual: True quando o
        arquivo do evento ja e conhecido por esta pasta (mesmo id remoto, mesmo
        objeto remoto, mesmo nome de arquivo local, ou mesmo nome de dataset).

        Contrato: sincrono, barato (tres lookups O(1) nos indices do manifesto)
        e NUNCA levanta — na duvida devolve False e o fan-out entrega ao
        primario.
        """
        try:
            file_info = msg.get("file") or {}
            id_hash = file_info.get("id_hash") or ""
            original_name = file_info.get("original_name") or ""
            if not id_hash and not original_name:
                return False

            if self._find_dataset(id_hash, original_name):
                return True

            if original_name:
                # Nome ainda nao sincronizado mas que casa com um dataset desta
                # pasta (ex: 'parcelas.geojson' e o dataset 'parcelas').
                stem = original_name.rsplit(".", 1)[0].lower()
                if stem in self.manifest.all_datasets():
                    return True
            return False
        except Exception:  # noqa: BLE001 — predicado de roteamento nunca pode quebrar o fan-out
            return False

    def _find_dataset(self, id_hash: str = "", original_name: str = "") -> str | None:
        """Delega aos indices invertidos do manifesto (ver SyncManifest.find)."""
        return self.manifest.find(id_hash, original_name)

    async def run(self):
        """Loop principal de sync."""
        logger.info("GeoSync iniciado: pasta='%s' workspace='%s' modo='%s' intervalo=%ds",
                    self.sync_dir, self.workspace_id, self.sync_mode, self.interval)

        # O watcher entrega eventos de outra thread — `_on_change` precisa saber
        # para qual loop marshalar.
        self._loop = asyncio.get_running_loop()
        self.watcher.start()

        try:
            # Reconciliacao inicial (unica chamada a list_remote). Uma falha aqui
            # (Drive fora do ar, disco com arquivo em transito) nao pode impedir
            # o loop periodico de comecar.
            try:
                await self._full_sync()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error("Reconciliacao inicial de '%s' falhou — seguindo para o loop periodico.",
                             self.sync_dir, exc_info=True)

            # Task dedicada para drive events (roda em paralelo com o loop).
            # Guardamos a referencia: sem isso o GC pode coletar a task.
            if self._drive_events:
                self._drive_task = asyncio.create_task(self._drive_event_loop(), name="drive-event-loop")

            # Um ciclo que morre por excecao matava a sincronizacao da pasta em
            # silencio ate o processo reiniciar — bastava um FileNotFoundError de
            # temporario do QGIS. O ciclo agora e isolado e o erro fica visivel.
            consecutive_errors = 0
            while True:
                try:
                    await self._maybe_purge_trash()

                    # Processa fila pendente (retry). O scan e compartilhado por
                    # todos os itens da passada: antes cada item `upload`
                    # escaneava a pasta INTEIRA para achar um dataset so.
                    self._scan_da_fila = None
                    try:
                        await self.queue.process_pending()
                    finally:
                        self._scan_da_fila = None
                    await self.manifest.flush()

                    # Antes de dormir: o estado do manifesto agora e o que a UI
                    # deve mostrar ate o proximo ciclo.
                    self._emitir_inventario()

                    # Aguarda mudanca local ou timeout
                    acordou_por_evento = False
                    try:
                        await asyncio.wait_for(self._change_flag.wait(), timeout=self.interval)
                        self._change_flag.clear()
                        acordou_por_evento = True
                    except asyncio.TimeoutError:
                        pass

                    if acordou_por_evento:
                        await self._esperar_pasta_estabilizar()
                    self._forcar_ciclo = False

                    # Sync local → remoto
                    if self.sync_mode in ("upload", "bidirectional", "catalog"):
                        await self._local_to_remote_only()

                    consecutive_errors = 0
                except asyncio.CancelledError:
                    raise
                except Exception:
                    consecutive_errors += 1
                    backoff = espera_exponencial(consecutive_errors, teto=_MAX_CYCLE_BACKOFF)
                    logger.error(
                        "Ciclo de sync de '%s' falhou (%d consecutiva(s)) — nova tentativa em %.1fs.",
                        self.sync_dir, consecutive_errors, backoff, exc_info=True,
                    )
                    await asyncio.sleep(backoff)

        except asyncio.CancelledError:
            logger.info("GeoSync encerrado.")
        finally:
            if self._drive_task:
                self._drive_task.cancel()
            self.watcher.stop()
            await self._fechar_clientes()

    async def _fechar_clientes(self):
        """Fecha os clientes httpx de longa duracao.

        Eles vivem enquanto o manager vive (keep-alive e o ponto). Sem
        fechamento explicito no encerramento, os sockets vazam ate o processo
        morrer — e no desktop o executor e religado sem reiniciar o Electron.
        """
        for componente in (self.uploader, self.downloader, self.trigger):
            fechar = getattr(componente, "aclose", None)
            if fechar is None:
                continue
            try:
                await fechar()
            except Exception:
                logger.debug("Falha ao fechar cliente HTTP de %s.", type(componente).__name__,
                             exc_info=True)

    async def _esperar_pasta_estabilizar(self):
        """
        Segura o ciclo ate a pasta parar de mudar.

        Sem isto, copiar um arquivo grande para dentro da pasta fazia o executor
        varrer+hashear tudo a cada ~2 segundos, em ciclos encostados um no
        outro: a copia disputava I/O com a varredura e a maquina travava. Duas
        barreiras, ambas so para ciclos acordados pelo WATCHER:

          * piso de `SYNC_MIN_CYCLE` entre o fim de um ciclo e o inicio do
            proximo;
          * debounce de CICLO (nao de caminho): so libera quando nao chegar
            evento novo por `SYNC_QUIET_PERIOD`, com teto de
            `SYNC_MAX_QUIET_WAIT` para uma copia de horas nao adiar o sync para
            sempre.

        `sincronizar_agora()` fura as duas — e comando do usuario.
        """
        loop = asyncio.get_running_loop()
        limite = loop.time() + SYNC_MAX_QUIET_WAIT
        piso = self._ultimo_ciclo + SYNC_MIN_CYCLE

        while not self._forcar_ciclo:
            agora = loop.time()
            if agora >= limite:
                return
            espera = min(max(piso - agora, SYNC_QUIET_PERIOD), limite - agora)
            if espera <= 0:
                return
            self._change_flag.clear()
            try:
                await asyncio.wait_for(self._change_flag.wait(), timeout=espera)
            except asyncio.TimeoutError:
                if loop.time() >= piso:
                    return  # piso cumprido e nenhum evento novo na janela

    async def _maybe_purge_trash(self):
        """
        Expurga descartes antigos da lixeira, no maximo uma vez a cada 6h.

        A lixeira mora dentro do sync_dir (para o move ser um rename no mesmo
        volume) e por isso consome a cota do notebook de campo, sem nada que a
        mostre ao tecnico: pasta com ponto, ignorada por scanner e watcher. Numa
        pasta bidirectional com rotatividade normal — raster diario substituido
        no Drive — sao dezenas de GB em algumas semanas, e o unico sintoma seria
        o manifesto parando de salvar.
        """
        agora = time.monotonic()
        if self._last_trash_purge and agora - self._last_trash_purge < _TRASH_PURGE_INTERVAL:
            return
        self._last_trash_purge = agora

        removidos, restantes = await em_thread(purge_trash, self.sync_dir)
        if removidos:
            logger.info("Lixeira de '%s': %d descarte(s) com mais de %d dias removido(s).",
                        self.sync_dir, removidos, TRASH_RETENTION_DAYS)
        if restantes > TRASH_WARN_BYTES:
            logger.warning("Lixeira de '%s' ocupa %s — pasta oculta, o tecnico nao a enxerga.",
                           self.sync_dir, _format_size(restantes))
            self.events.emit("sync_error", dataset=TRASH_DIR_NAME,
                             error=f"Lixeira do sync ocupando {_format_size(restantes)}")

    async def _drive_event_loop(self):
        """Loop dedicado para processar drive events push do servidor."""
        logger.info("Drive event loop iniciado.")
        while True:
            try:
                event = await self._drive_events.get()
                await self._process_drive_event(event)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Erro ao processar drive_event em '%s'.", self.sync_dir, exc_info=True)

    async def _process_drive_event(self, event: dict):
        """Processa um evento push do servidor (file_created, file_deleted, file_updated)."""
        action = event.get("action", "")
        file_info = event.get("file", {})
        id_hash = file_info.get("id_hash", "")
        original_name = file_info.get("original_name", "")
        content_md5 = file_info.get("content_md5")

        logger.info("Processando drive_event: action=%s, file=%s, id=%s", action, original_name, id_hash[:8] if id_hash else "?")

        if not id_hash or not original_name:
            logger.warning("drive_event sem id_hash ou original_name — ignorado.")
            return

        # Gate de MODO antes de QUALQUER acao. O gate vivia dentro do branch de
        # file_created/file_updated, entao 'file_deleted' rodava tambem em
        # SYNC_MODE=upload (o padrao): um admin limpando arquivos antigos no
        # Drive disparava unlink() nos originais no disco do tecnico, incluindo
        # todos os componentes .shp/.dbf/.shx/.prj. O caminho por polling sempre
        # respeitou o modo — a divergencia era o bug.
        if self.sync_mode not in ("download", "bidirectional"):
            logger.debug("drive_event '%s' ignorado: SYNC_MODE=%s nao consome mudancas do Drive.",
                         action, self.sync_mode)
            return

        self._syncing = True
        try:
            if action == "file_deleted":
                # Casa SO por id remoto: descartar arquivo local por semelhanca
                # de nome seria destrutivo demais para um evento push.
                ds_name = self._find_dataset(id_hash=id_hash)
                if ds_name:
                    self._discard_dataset(ds_name, "push: deletado no Drive")

            elif action in ("file_created", "file_updated"):
                # Ignora extensões não reconhecidas pelo scanner
                if Path(original_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                    logger.debug("Push event '%s' ignorado (extensão não suportada).", original_name)
                    return

                # Sync seletivo
                if not self.sync_config.should_download(original_name, id_hash):
                    return

                # Reaproveita a chave do dataset ja conhecido — derivar uma chave
                # nova a cada push duplicava a entrada no manifesto.
                ds_key = self._find_dataset(id_hash, original_name)
                ds_info = (self.manifest.get_dataset(ds_key) or {}) if ds_key else {}

                # Mesmo guard do caminho por polling: o push consome mudancas do
                # Drive exatamente como ele, e nao pode gravar um dataset de
                # arquivo unico por cima de uma entrada multi-arquivo.
                if ds_key and self._bundle_blocks_download(ds_key, ds_info, id_hash,
                                                           original_name, content_md5):
                    return

                # Baixa o arquivo — destino sempre contido no sync_dir.
                dest = safe_join_or_none(self.sync_dir, original_name, context="push download")
                if dest is None:
                    self.events.emit("sync_error", dataset=original_name,
                                     error="Nome de arquivo rejeitado por seguranca")
                    return

                # Conflito: o push herdava so metade do contrato do polling —
                # gravava por cima da edicao de campo sem emitir conflict_detected
                # e sem respeitar SYNC_CONFLICT_STRATEGY.
                if ds_key and self.sync_mode == "bidirectional":
                    locais = [
                        p for p in (
                            safe_join_or_none(self.sync_dir, fname, context="push conflito")
                            for fname in (ds_info.get("files") or {})
                        )
                        if p is not None and p.exists()
                    ]
                    if locais:
                        local_md5_now = await em_thread(_paths_md5, locais)
                        if not self._resolve_conflict(ds_key, ds_info, local_md5_now, locais):
                            return

                self.events.emit("file_downloading", dataset=original_name)
                success = await self.downloader.download(id_hash, dest)

                if success:
                    from executor.sync.scanner import _compute_md5
                    downloaded_md5 = await em_thread(_compute_md5, dest)
                    ds_key = ds_key or _new_remote_ds_key(original_name, self.manifest.all_datasets())
                    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

                    # size/mtime do arquivo NO DISCO: sao eles que o atalho do
                    # `diff` compara no proximo ciclo.
                    from executor.sync.scanner import entrada_de_manifesto
                    self.manifest.set_dataset(ds_key, {
                        "type": ext,
                        "files": {original_name: entrada_de_manifesto(dest, downloaded_md5)},
                        "status": "synced",
                        "remote_id_hash": id_hash,
                        "remote_name": original_name,
                        "remote_md5": content_md5 or downloaded_md5,
                        "local_md5": downloaded_md5,
                        "sync_direction": "remote",
                    })
                    self._emit_downloaded(original_name, dest)
                    logger.info("Push sync: '%s' baixado (%s).", original_name, action)
                else:
                    self.events.emit("sync_error", dataset=original_name, error="Download falhou")
        finally:
            await self.manifest.flush()
            # Ordem importa: limpar o flag ANTES de reabrir `_syncing`. Ao
            # contrario, um evento de arquivo que chegasse nessa fresta era
            # apagado pelo clear() e a mudanca so seria vista 30s depois.
            self._change_flag.clear()
            self._syncing = False

    def _discard_dataset(self, ds_name: str, reason: str) -> bool:
        """
        Descarta um dataset local por ordem do Drive — para a lixeira, nao unlink
        — e SO entao remove a entrada do manifesto. Devolve True se concluiu.

        Nao existe lixeira do SO nesse caminho nem re-download de recuperacao: um
        engano do lado do servidor apagaria trabalho de campo irreversivelmente.

        A entrada do manifesto so cai quando TODOS os arquivos sairam do disco.
        Removendo-a mesmo com o move falhando (QGIS com o .geojson aberto: no
        Windows o handle sem FILE_SHARE_DELETE faz o rename levantar
        PermissionError), o arquivo ficava no disco sem manifesto — e o
        _local_to_remote seguinte o via como dataset NOVO e o re-enviava ao
        Drive, disparando ate o trigger de ingestao. O admin apagava de novo e o
        ciclo se repetia. Falhou: mantem a entrada e reenfileira o descarte.
        """
        ds_info = self.manifest.get_dataset(ds_name) or {}
        alvos: list[Path] = []
        for fname in ds_info.get("files") or {}:
            local_file = safe_join_or_none(self.sync_dir, fname, context=reason)
            if local_file is not None and local_file.exists():
                alvos.append(local_file)

        falhos = move_dataset_to_trash(self.sync_dir, ds_name, alvos)
        if falhos:
            logger.warning("Dataset '%s' mantido no manifesto: %d de %d arquivo(s) nao foram "
                           "para a lixeira (%s).", ds_name, len(falhos), len(alvos), reason)
            self.manifest.mark_pending(ds_name, "discard")
            # `enqueue` e idempotente por (action, dataset): reenfileirar o mesmo
            # descarte a cada tentativa nao duplica o item nem zera o backoff.
            self.manifest.enqueue("discard", ds_name)
            self.events.emit("sync_error", dataset=ds_name,
                             error="Arquivo em uso — descarte local adiado")
            return False

        if alvos:
            logger.info("Dataset '%s': %d arquivo(s) movido(s) para a lixeira (%s).",
                        ds_name, len(alvos), reason)
        self.manifest.remove_dataset(ds_name)
        self.events.emit("file_deleted_local", dataset=ds_name)
        return True

    def _bundle_blocks_download(self, ds_name: str, ds_info: dict, remote_id: str,
                                remote_name: str, remote_md5: str | None) -> bool:
        """
        Protege uma entrada MULTI-ARQUIVO do manifesto de um download de arquivo
        unico. True = nao baixe (o caso ja foi tratado ou recusado aqui).

        Um shapefile vive no Drive como um unico '<dataset>.zip' que NOS
        enviamos, enquanto o manifesto guarda os componentes .shp/.dbf/.shx.
        Gravar qualquer download nessa chave troca 'files' por um dataset de
        arquivo unico — e o estrago nao para no manifesto: o diff() do ciclo
        seguinte acusa o bundle como modificado, re-envia com id novo e manda
        deletar o id que ficou na entrada, que pode ser o objeto de OUTRO usuario
        do workspace. Dois casos, mesma resposta:

          * mesmo id remoto → e o nosso proprio bundle voltando; nada a baixar,
            so realinhamos o MD5 remoto (o hash do zip nunca bate com o hash
            combinado dos componentes, entao a comparacao normal mandaria
            baixa-lo por cima para sempre);
          * id diferente → objeto alheio que apenas COLIDE de nome, seja com o
            '<ds>.zip' derivado, seja com o nome de um componente. Nao ha destino
            seguro: o scanner agrupa tudo pelo stem, o arquivo ficaria orfao no
            disco e voltaria a ser baixado todo ciclo. Recusamos e avisamos o
            painel — adotar o id alheio (o que o codigo fazia) deixava a nossa
            copia real orfa no Drive e apontava o dataset para conteudo de
            terceiro.
        """
        if ds_info.get("type") != "shapefile" and len(ds_info.get("files") or {}) <= 1:
            return False

        if remote_id and remote_id == ds_info.get("remote_id_hash"):
            if remote_md5 and remote_md5 != ds_info.get("remote_md5"):
                self.manifest.mark_synced(
                    ds_name, remote_id, remote_md5=remote_md5,
                    local_md5=ds_info.get("local_md5"),
                )
            return True

        logger.warning("Objeto remoto '%s' (%s) ignorado: colide com o dataset multi-arquivo "
                       "'%s' (id remoto %s).", remote_name, (remote_id or "?")[:8], ds_name,
                       (ds_info.get("remote_id_hash") or "-")[:8])
        self.events.emit("sync_error", dataset=remote_name,
                         error=f"Nome colide com o dataset local '{ds_name}'")
        return True

    def _emit_downloaded(self, dataset: str, dest: Path) -> None:
        """Emite `file_downloaded` com o tamanho do arquivo que acabou de chegar.

        O downloader escreve em streaming e nao contabiliza nada; medir o
        arquivo pronto e mais simples que somar chunks no hot loop, e da o
        mesmo numero. Best-effort: um `stat` que falhe nao pode impedir o
        evento, que e o que a UI usa para saber que o download terminou.
        """
        try:
            total = dest.stat().st_size
        except OSError:
            total = 0
        self.events.emit("file_downloaded", dataset=dataset, total_bytes=total)

    def _resolve_conflict(self, ds_name: str, ds_info: dict, local_md5_now: str,
                          local_paths: list[Path]) -> bool:
        """
        Politica de conflito quando o objeto remoto E os arquivos locais mudaram
        desde o ultimo sync. Devolve True se o download pode prosseguir.

        Vive fora dos dois caminhos que consomem o Drive (polling e push) de
        proposito: o push ia direto de `should_download` para `download` e
        gravava por cima da edicao de campo — sem `conflict_detected` no painel e
        sem o backup `_local_<timestamp>` que keep-both promete.
        """
        saved_local_md5 = ds_info.get("local_md5") or ""
        if not saved_local_md5 or local_md5_now == saved_local_md5:
            return True  # so o remoto mudou — download normal

        self.events.emit("conflict_detected", dataset=ds_name)
        strategy = agent_config.SYNC_CONFLICT_STRATEGY
        logger.warning("Conflito em '%s' — estrategia: %s", ds_name, strategy)

        if strategy == "local-wins":
            return False
        if strategy == "keep-both":
            from datetime import datetime as _dt
            suffix = _dt.now().strftime("%Y%m%dT%H%M%S")
            for path in local_paths:
                backup = path.with_name(f"{path.stem}_local_{suffix}{path.suffix}")
                try:
                    path.rename(backup)
                except OSError as exc:
                    # Sem backup nao existe "keep both": abortar o download e o
                    # unico desfecho que nao perde a versao local.
                    logger.error("Backup de '%s' falhou (%s) — download de '%s' abortado.",
                                 path.name, exc, ds_name)
                    self.events.emit("sync_error", dataset=ds_name, error="Backup local falhou")
                    return False
                logger.info("Backup: %s → %s", path.name, backup.name)
        return True

    async def _local_to_remote_only(self):
        """Detecta mudancas locais e faz upload. Sem polling remoto."""
        self._syncing = True
        try:
            await self._local_to_remote()
            self.manifest.set_last_scan()
        finally:
            await self.manifest.flush()
            self._change_flag.clear()
            self._syncing = False
            # Marca o fim do ciclo DEPOIS do trabalho: o piso conta a partir
            # daqui, senao uma varredura de 2 minutos ja nasceria vencida.
            self._ultimo_ciclo = asyncio.get_running_loop().time()

    async def _full_sync(self):
        """Executa scan completo e sincroniza diferencas."""
        self._syncing = True
        try:
            self.events.emit("sync_started")

            # ── 1. Upload local → remoto ─────────────────────────────────────
            # `catalog` entra aqui: registra o dataset no servidor. NAO entra
            # no bloco de download — nao ha objeto remoto para baixar, e o
            # arquivo de origem ja esta nesta maquina.
            if self.sync_mode in ("upload", "bidirectional", "catalog"):
                await self._local_to_remote()

            # ── 2. Download remoto → local ───────────────────────────────────
            if self.sync_mode in ("download", "bidirectional"):
                await self._remote_to_local()

            self.manifest.set_last_scan()
            self.events.emit("sync_complete")
        finally:
            await self.manifest.flush()
            # Descarta os avisos gerados durante o sync (downloads proprios)
            self._change_flag.clear()
            self._syncing = False

    async def _em_paralelo(self, corrotinas: list, contexto: str):
        """Roda as transferencias com teto de concorrencia, sem derrubar o lote.

        O teto e baixo (SYNC_CONCURRENCY) de proposito: em link de campo,
        concorrencia alta piora o tempo total e arrisca estourar o timeout de
        300s da transferencia. `return_exceptions=True` porque um dataset que
        falha nao pode cancelar os outros — cada `_upload_dataset` ja cuida do
        proprio enfileiramento para retry.
        """
        if not corrotinas:
            return
        # Semaforo do PROCESSO (ver `_semaforo_de_transferencia`): o teto vale
        # para o link, que todas as pastas compartilham. Obtido aqui, e nao no
        # __init__, porque o manager e construido antes do event loop existir.
        semaforo = _semaforo_de_transferencia()

        async def _limitada(coro):
            async with semaforo:
                return await coro

        resultados = await asyncio.gather(*(_limitada(c) for c in corrotinas),
                                          return_exceptions=True)
        for resultado in resultados:
            if isinstance(resultado, asyncio.CancelledError):
                raise resultado
            if isinstance(resultado, Exception):
                logger.error("Operacao de %s em '%s' falhou: %s",
                             contexto, self.sync_dir, resultado, exc_info=resultado)

    async def _local_to_remote(self):
        """Detecta mudancas locais e faz upload para o Drive."""
        # scan() e I/O sincrono pesado (stat de tudo): fora do event loop.
        # O executor usa ping_interval=None, entao o heartbeat aplicativo de 30s
        # e o UNICO keepalive — bloquear o loop derruba a conexao (close 4408) e
        # mata o run em andamento.
        current_datasets = await em_thread(self.scanner.scan)
        manifest_datasets = self.manifest.all_datasets()

        # Rede de seguranca do atalho (size, mtime): de tempos em tempos o diff
        # rehasheia tudo, para pegar a reescrita rara que preserva o mtime.
        agora = time.monotonic()
        hash_completo = (self._ultimo_hash_completo is None
                         or (agora - self._ultimo_hash_completo) >= SYNC_FULL_HASH_INTERVAL)

        # diff() tambem vai para a thread: e ele que dispara `file_hashes()` e,
        # com ele, o MD5 dos arquivos candidatos (o scan so faz stat).
        new_ds, modified_ds, removed_ds = await em_thread(
            self.scanner.diff, current_datasets, manifest_datasets, hash_completo
        )

        # O marcador so e carimbado DEPOIS do diff concluir. Marcado antes, ele
        # era consumido por uma passada que talvez nunca acontecesse: o diff com
        # force_hash abre TODOS os arquivos da pasta e qualquer OSError levava o
        # ciclo inteiro para o backoff do `run()` — mas a rede de seguranca ja
        # constava como cumprida e so voltaria 1h depois (no boot, nunca). Um
        # arquivo reescrito com (size, mtime) preservados ficava horas sem subir.
        if hash_completo:
            self._ultimo_hash_completo = agora

        # Novos datasets — so faz upload se nao veio do remoto.
        # A lista guarda (nome, dataset) e nao corrotinas: ainda ha um `await`
        # ate o gather, e uma corrotina criada e nunca aguardada vira warning.
        a_enviar: list[tuple[str, Dataset]] = []
        for name in new_ds:
            old = manifest_datasets.get(name, {})
            if old.get("sync_direction") == "remote":
                continue  # Acabou de ser baixado do Drive, nao re-uplodar
            a_enviar.append((name, current_datasets[name]))

        # Modificados — ignora se veio do remoto e nao foi editado localmente
        for name in modified_ds:
            ds = current_datasets[name]
            old = manifest_datasets.get(name, {})

            if old.get("sync_direction") == "remote":
                # Calcula MD5 atual do arquivo local. Le o disco de novo, entao
                # tem a mesma janela do diff: se o arquivo sumiu ou esta travado
                # agora, deixa para o proximo ciclo em vez de derrubar o ciclo
                # inteiro (o `run()` cairia no backoff e a pasta pararia).
                try:
                    local_md5 = await em_thread(_dataset_md5, ds)
                except OSError as exc:
                    logger.info("Dataset '%s' indisponivel para leitura (%s) — adiado para o "
                                "proximo ciclo.", name, exc)
                    continue
                saved_md5 = old.get("local_md5", "")
                if local_md5 == saved_md5:
                    continue  # Nao mudou desde o download — nao re-uplodar

            # O DELETE da copia antiga acontece DENTRO de _upload_dataset: e o
            # unico ponto por onde passam tanto o upload direto quanto o retry
            # da fila.
            a_enviar.append((name, ds))

        # Os uploads sao I/O independente entre si: em serie, a primeira
        # sincronizacao de 200 arquivos pequenos passava o tempo todo esperando
        # round-trip com o link ocioso.
        await self._em_paralelo(
            [self._upload_dataset(nome, dataset) for nome, dataset in a_enviar], "upload")

        # Removidos localmente
        for name in removed_ds:
            old = manifest_datasets.get(name, {})

            # Arquivo que veio do remoto — re-baixar (servidor e fonte de verdade)
            if old.get("sync_direction") == "remote" and self.sync_mode in ("download", "bidirectional"):
                rid = old.get("remote_id_hash")
                if rid:
                    # Reconstroi nome do arquivo a partir do manifest
                    fnames = list(old.get("files", {}).keys())
                    fname = fnames[0] if fnames else f"{name}.{old.get('type', 'bin')}"
                    dest = safe_join_or_none(self.sync_dir, fname, context="re-download")
                    if dest is None:
                        continue
                    logger.info("Re-baixando '%s' (deletado localmente, servidor e fonte de verdade).", fname)
                    self.events.emit("file_downloading", dataset=fname)
                    success = await self.downloader.download(rid, dest)
                    if success:
                        from executor.sync.scanner import _compute_md5
                        downloaded_md5 = await em_thread(_compute_md5, dest)
                        old["local_md5"] = downloaded_md5
                        old["status"] = "synced"
                        old["files"] = {fname: {"md5": downloaded_md5, "size": dest.stat().st_size, "mtime": dest.stat().st_mtime}}
                        self.manifest.set_dataset(name, old)
                        self._emit_downloaded(fname, dest)
                    else:
                        self.events.emit("sync_error", dataset=fname, error="Re-download falhou")
                continue

            old_id = old.get("remote_id_hash")
            if old_id:
                success = await self.uploader.delete(old_id)
                if success:
                    self.manifest.remove_dataset(name)
                    logger.info("Dataset '%s' removido do Drive.", name)
                else:
                    self.manifest.enqueue("delete", name, {"remote_id_hash": old_id})
            else:
                self.manifest.remove_dataset(name)

    async def _remote_to_local(self):
        """Detecta mudancas no Drive e baixa/remove localmente."""
        all_remote = await self.downloader.list_remote()
        if all_remote is None:
            return  # Erro de conexao — nao tomar decisoes de delecao

        # all_remote pode ser [] se Drive vazio — ainda precisamos detectar delecoes

        manifest_datasets = self.manifest.all_datasets()

        # A correspondencia manifesto ↔ objeto remoto sai dos indices invertidos
        # do proprio manifesto (id remoto → nome do objeto remoto → nome de
        # arquivo local). Reconstrui-los aqui a cada ciclo era O(datasets) em vao
        # — e o casamento por 'remote_name', que impede o '<dataset>.zip' de um
        # shapefile de ser confundido com arquivo novo, e o mesmo dos dois lados.
        conhecido = self.manifest.find_by_remote_id

        # Deduplica por original_name: mantém apenas o mais recente (lista ja vem
        # ordenada por created_at desc do endpoint) — EXCETO quando um dos
        # homonimos e justamente o objeto que o manifesto ja referencia. Um
        # 'parcelas.zip' alheio, mais novo, descartava da iteracao a nossa
        # propria copia e o dataset acabava reapontado para o arquivo do outro.
        latest_by_name: dict[str, object] = {}
        for rf in all_remote:
            anterior = latest_by_name.get(rf.original_name)
            if anterior is None or (conhecido(rf.id_hash) is not None
                                    and conhecido(anterior.id_hash) is None):
                latest_by_name[rf.original_name] = rf

        remote_files = list(latest_by_name.values())
        # Set de TODOS os IDs remotos (para deteccao de delecao, inclui duplicados)
        all_remote_ids = {rf.id_hash for rf in all_remote}

        # UM unico scan para todo o laco. Antes, scanner.scan() era chamado
        # DENTRO do laco por-arquivo-remoto: O(n x bytes) de leitura sincrona
        # dentro da corrotina, suficiente para estourar o heartbeat de 30s.
        local_datasets: dict[str, Dataset] = {}
        if self.sync_mode == "bidirectional":
            local_datasets = await em_thread(self.scanner.scan)

        pendentes = []
        for rf in remote_files:
            # Ignora extensões não reconhecidas pelo scanner (evita loop de re-download)
            if Path(rf.original_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                logger.debug("Arquivo remoto '%s' ignorado (extensão não suportada).", rf.original_name)
                continue

            # Sync seletivo
            if not self.sync_config.should_download(rf.original_name, rf.id_hash):
                continue

            pendentes.append(self._sincronizar_remoto(rf, manifest_datasets, local_datasets))

        # Downloads tambem sao I/O independente: em serie, entrar num workspace
        # novo mostrava um `file_downloading` de cada vez com o link ocioso.
        await self._em_paralelo(pendentes, "download")

        # ── Detecta delecoes remotas ─────────────────────────────────────────
        # Se o remote_id_hash do manifest nao existe mais no Drive, remove localmente.
        # No modo bidirectional: remove independente de quem criou (servidor e fonte de verdade).
        # No modo download: idem.
        for ds_name, ds_info in list(manifest_datasets.items()):
            rid = ds_info.get("remote_id_hash")
            if not rid:
                continue  # Nunca foi sincronizado com o remoto
            if rid not in all_remote_ids:
                self._discard_dataset(ds_name, "deletado no Drive")

    async def _sincronizar_remoto(self, rf, manifest_datasets: dict,
                                  local_datasets: dict[str, Dataset]):
        """Decide e executa o que fazer com UM objeto do Drive.

        Extraido do laco de `_remote_to_local` para poder rodar em paralelo com
        os demais. Nao ha corrida na alocacao de chave: entre `_new_remote_ds_key`
        e o `set_dataset` nao existe `await`, entao a segunda corrotina ja
        enxerga a chave que a primeira acabou de ocupar.
        """
        ds_name = self.manifest.find(rf.id_hash, rf.original_name)
        ds_info = manifest_datasets.get(ds_name, {}) if ds_name else {}

        # Verifica se precisa baixar
        if ds_name and ds_info:
            # Entrada multi-arquivo (bundle shapefile): nunca gravar um
            # download por cima dela — ver _bundle_blocks_download.
            if self._bundle_blocks_download(ds_name, ds_info, rf.id_hash,
                                            rf.original_name, rf.content_md5):
                return

            saved_remote_md5 = ds_info.get("remote_md5")
            saved_remote_id = ds_info.get("remote_id_hash")

            # Mesmo ID e MD5? Nada mudou.
            if saved_remote_id == rf.id_hash:
                if not rf.content_md5 or rf.content_md5 == saved_remote_md5:
                    return  # Sem mudanca

            # MD5 diferente ou ID diferente → mudou no remoto
            if rf.content_md5 and saved_remote_md5 and rf.content_md5 == saved_remote_md5:
                # Mesmo conteudo, ID diferente (re-upload identico) — atualiza ID no manifest
                self.manifest.mark_synced(
                    ds_name, rf.id_hash, remote_md5=rf.content_md5,
                    local_md5=ds_info.get("local_md5"),
                )
                return

            # Sem MD5 remoto? Nao da pra comparar — pula (evita loop infinito)
            if not rf.content_md5:
                return

            # ── Conflito (bidirectional) ─────────────────────────────────────
            if self.sync_mode == "bidirectional":
                current_local = local_datasets.get(ds_name)
                if current_local:
                    local_md5_now = await em_thread(_dataset_md5, current_local)
                    if not self._resolve_conflict(
                        ds_name, ds_info, local_md5_now,
                        [finfo.path for finfo in current_local.files.values()],
                    ):
                        return

        # ── Download ─────────────────────────────────────────────────────────
        dest = safe_join_or_none(self.sync_dir, rf.original_name, context="download remoto")
        if dest is None:
            self.events.emit("sync_error", dataset=rf.original_name,
                             error="Nome de arquivo rejeitado por seguranca")
            return
        self.events.emit("file_downloading", dataset=rf.original_name)
        success = await self.downloader.download(rf.id_hash, dest)

        if not success:
            self.events.emit("sync_error", dataset=rf.original_name, error="Download falhou")
            return

        self._emit_downloaded(rf.original_name, dest)
        # Calcula MD5 do arquivo baixado (para comparacao futura)
        from executor.sync.scanner import _compute_md5
        downloaded_md5 = await em_thread(_compute_md5, dest)

        ds_key = ds_name or _new_remote_ds_key(rf.original_name, manifest_datasets)
        # size/mtime saem do arquivo que esta NO DISCO, nao do que o servidor
        # declarou: sao eles que o atalho do `diff` compara no proximo ciclo, e
        # um tamanho divergente faria o arquivo ser rehasheado para sempre.
        from executor.sync.scanner import entrada_de_manifesto
        self.manifest.set_dataset(ds_key, {
            "type": rf.extension,
            "files": {rf.original_name: entrada_de_manifesto(dest, downloaded_md5)},
            "status": "synced",
            "remote_id_hash": rf.id_hash,
            "remote_name": rf.original_name,
            "remote_md5": rf.content_md5 or downloaded_md5,
            "local_md5": downloaded_md5,
            "sync_direction": "remote",
            "synced_at": rf.updated_at or rf.created_at,
        })
        if not ds_name:
            logger.info("Novo arquivo remoto '%s' baixado (dataset '%s').", rf.original_name, ds_key)

    async def _upload_dataset(self, name: str, ds: Dataset,
                              enqueue_on_failure: bool = True) -> UploadResult | None:
        """Valida, extrai metadados e faz upload de um dataset."""
        # validate_dataset abre o arquivo com geopandas/rasterio e extract_metadata
        # le o dataset inteiro: I/O + CPU pesados, fora do event loop.
        result = await em_thread(validate_dataset, ds)
        if not result.valid:
            for err in result.errors:
                logger.error("Validacao '%s': %s", name, err)
            return None

        # Extrai metadados espaciais
        spatial_meta = None
        if ds.primary_path:
            try:
                spatial_meta = await em_thread(extract_metadata, ds.primary_path, ds.type)
                spatial_meta["dataset_files"] = list(ds.files.keys())
            except Exception as e:
                logger.warning("Metadados de '%s' indisponiveis: %s", name, e)

        # Calcula MD5 local antes do upload (tambem popula o cache de FileInfo).
        local_md5 = await em_thread(_dataset_md5, ds)

        # Marca como uploading MESCLANDO na entrada existente. Substituir a
        # entrada perdia 'remote_id_hash' — a copia antiga ficava orfa no Drive e
        # o _remote_to_local ignorava um dataset sem id remoto.
        # E 'files' NAO e gravado aqui de proposito: se o processo morrer antes do
        # upload confirmar, um manifesto com os MD5 novos faz o diff() concluir
        # "em dia" e o arquivo nunca mais sobe.
        ds_info = dict(self.manifest.get_dataset(name) or {})
        old_id = ds_info.get("remote_id_hash")
        ds_info["type"] = ds.type
        ds_info["status"] = "uploading"
        ds_info["sync_direction"] = "local"
        self.manifest.set_dataset(name, ds_info)

        # Modo catalogo (LGPD): registra os metadados e NAO envia os bytes. O
        # arquivo permanece na pasta do usuario e so pode ser lido por workflows
        # que rodem neste executor.
        if self.sync_mode == "catalog":
            self.events.emit("file_cataloging", dataset=name, total_bytes=ds.total_size)
            upload = await self.uploader.register(ds, spatial_meta)
        else:
            self.events.emit("file_uploading", dataset=name, total_bytes=ds.total_size)
            upload = await self.uploader.upload(ds, spatial_meta)

        if upload:
            # So agora o estado local vira "a versao no Drive": grava os arquivos
            # e o nome/MD5 do OBJETO remoto (para shapefile, o '<dataset>.zip').
            ds_info = dict(self.manifest.get_dataset(name) or {})
            ds_info["files"] = {fname: finfo.to_dict() for fname, finfo in ds.files.items()}
            ds_info["remote_name"] = upload.remote_name
            self.manifest.set_dataset(name, ds_info)

            self.manifest.mark_synced(
                name, upload.id_hash, spatial_meta,
                local_md5=local_md5,
                remote_md5=upload.remote_md5,
            )
            # Flush OPORTUNISTA: durabilidade a cada SYNC_FLUSH_INTERVAL
            # segundos, em vez de reserializar o manifesto inteiro por dataset
            # (era isso que fazia a sincronizacao inicial de uma pasta grande
            # ficar mais lenta a cada arquivo). O flush do fim do ciclo fecha a
            # conta. A ordem documentada acima segue valendo: o que fica na
            # janela e o estado ANTIGO, que so causa re-upload, nunca um MD5
            # novo dado como confirmado.
            await self.manifest.flush(min_intervalo=SYNC_FLUSH_INTERVAL)

            # UPLOAD PRIMEIRO, delete da copia antiga depois — e AQUI, nao no
            # chamador. Deletar antes do PUT abria janela de perda TOTAL (um
            # crash entre o DELETE e o PUT sumia com o arquivo do Drive enquanto
            # o disco continuava batendo com o manifesto: o diff() considerava
            # "em dia" e ninguem re-enviava). Mas deletar no _local_to_remote
            # deixava o retry da SyncQueue de fora — ele chama _upload_dataset
            # direto e nao conhece o id antigo — e a copia obsoleta ficava no
            # bucket para sempre com o MESMO original_name, voltando depois como
            # "arquivo novo" no _remote_to_local e ressuscitando conteudo velho.
            if old_id and old_id != upload.id_hash:
                if not await self.uploader.delete(old_id):
                    logger.warning("Versao antiga de '%s' (%s) permanece no Drive — delete falhou.",
                                   name, old_id[:8])

            # total_bytes/file_count vao no evento porque o painel acumula o
            # volume transferido na sessao; os dois valores ja estao em maos
            # (o log da linha seguinte usa ambos).
            self.events.emit("file_uploaded", dataset=name,
                             total_bytes=ds.total_size, file_count=len(ds.files))
            logger.info("Dataset '%s' sincronizado → %s (%d arquivo(s), %s).",
                        name, upload.id_hash, len(ds.files), _format_size(ds.total_size))

            # Dispara workflow se configurado
            if self.trigger.enabled:
                primary = ds.primary_path
                await self.trigger.on_file_synced(name, {
                    "id_hash": upload.id_hash,
                    "original_name": primary.name if primary else name,
                    "extension": ds.type,
                    "size": ds.total_size,
                })
            return upload

        if enqueue_on_failure:
            self.manifest.enqueue("upload", name)
        self.manifest.mark_pending(name, "upload")
        self.events.emit("sync_error", dataset=name, error="Upload falhou")
        logger.warning("Dataset '%s': upload falhou — enfileirado para retry.", name)
        return None

    async def _execute_pending(self, item: dict) -> bool:
        """Executor para a SyncQueue."""
        action = item["action"]
        dataset_name = item["dataset"]

        if action == "upload":
            # Um scan por PASSADA da fila, nao por item: com 5 itens pendentes,
            # o retry varria a pasta inteira 5 vezes so para achar 5 datasets.
            if self._scan_da_fila is None:
                self._scan_da_fila = await em_thread(self.scanner.scan)
            current = self._scan_da_fila
            ds = current.get(dataset_name)
            if not ds:
                logger.info("Dataset '%s' nao existe mais — removendo da fila.", dataset_name)
                return True
            # Reusa o caminho normal para o retry gravar 'files'/'remote_name'
            # exatamente como o upload direto. enqueue_on_failure=False porque o
            # item ja esta na fila — a SyncQueue cuida do retry.
            upload = await self._upload_dataset(dataset_name, ds, enqueue_on_failure=False)
            return upload is not None

        elif action == "delete":
            remote_id = item.get("remote_id_hash")
            if remote_id:
                return await self.uploader.delete(remote_id)
            return True

        elif action == "discard":
            # Descarte local adiado: o arquivo estava travado por outro processo
            # (QGIS com o .shp aberto). Enquanto nao sair do disco, a entrada do
            # manifesto continua de pe para o diff() nao re-enviar o arquivo.
            if self.manifest.get_dataset(dataset_name) is None:
                return True
            return self._discard_dataset(dataset_name, "retry: deletado no Drive")

        return False


def _new_remote_ds_key(original_name: str, existing: dict) -> str:
    """
    Chave de manifesto para um arquivo remoto ainda desconhecido.

    O stem puro colide entre um bundle ('parcelas', com .shp/.dbf/.shx) e um
    objeto homonimo do Drive ('parcelas.zip'): a segunda gravacao sobrescrevia
    'files'/'local_md5' do primeiro e o ciclo seguinte deletava + reenviava com
    um id novo, quebrando qualquer no que referenciasse o id antigo. Quando o
    stem ja esta ocupado, qualifica a chave com a extensao.
    """
    stem, _, ext = original_name.rpartition(".")
    if not stem:  # nome sem extensao
        stem, ext = original_name, ""
    stem = stem.lower()
    if stem not in existing:
        return stem
    return f"{stem}.{ext.lower()}" if ext else stem


def _dataset_md5(ds: Dataset) -> str:
    """Calcula MD5 combinado de todos os arquivos de um dataset."""
    hashes = ds.file_hashes()
    if len(hashes) == 1:
        return next(iter(hashes.values()))
    return "|".join(sorted(hashes.values()))


def _paths_md5(paths: list[Path]) -> str:
    """
    Mesmo hash combinado de `_dataset_md5`, mas a partir de caminhos soltos —
    o caminho de push conhece os arquivos pelo manifesto, nao por um Dataset
    escaneado (escanear a pasta inteira a cada evento push seria caro demais).
    Sincrono: o chamador roda em thread.
    """
    from executor.sync.scanner import _compute_md5

    hashes = sorted(_compute_md5(p) for p in paths)
    if len(hashes) == 1:
        return hashes[0]
    return "|".join(hashes)


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
