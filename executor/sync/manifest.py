# executor/sync/manifest.py
"""
Manifesto local de sincronizacao (.atlans-sync.json).
Persiste estado de cada dataset: hash, remote_id, status, metadados.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from executor.sync.pool import em_thread
from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

_MANIFEST_FILE = ".atlans-sync.json"
_VERSION = 2


def remote_name_of(ds_name: str, ds_info: dict) -> str | None:
    """
    Nome do OBJETO no Drive que representa este dataset.

    Para um shapefile isso nao e nenhum arquivo local: o uploader envia o bundle
    como '<dataset>.zip'. Manifestos gravados antes de 'remote_name' existir
    caem no mesmo nome deterministico.
    """
    name = ds_info.get("remote_name")
    if name:
        return name
    if ds_info.get("type") == "shapefile":
        return f"{ds_name}.zip"
    return None


class SyncManifest:
    def __init__(self, sync_dir: str, workspace_id: str, executor_id: str):
        self.path = Path(sync_dir) / _MANIFEST_FILE
        self.workspace_id = workspace_id
        self.executor_id = executor_id
        self._data: dict = self._load()
        # Write-behind: cada mutacao so avanca um contador de versao; quem grava
        # e o `flush()` do fim do ciclo. Antes, um unico upload disparava TRES
        # reserializacoes do JSON inteiro — sincronizar N datasets custava O(N²)
        # bytes gravados, no mesmo loop que sustenta o WebSocket.
        #
        # E um CONTADOR, e nao um flag booleano, porque o flush grava fora do
        # loop: com flag, ou se limpava antes da gravacao (e um disco cheio
        # deixava o estado so na memoria, com o manifesto marcado como limpo —
        # um kill nessa janela re-enviava a pasta inteira e deixava copias orfas
        # no Drive), ou se limpava depois (e as mutacoes ocorridas DURANTE a
        # gravacao eram esquecidas). Com versao, sabemos exatamente qual
        # snapshot chegou ao disco.
        self._versao = 0
        self._versao_no_disco = 0
        self._ultimo_flush = 0.0
        self._gravando = False

        # Indices invertidos para o roteamento de drive_events. Sem eles,
        # `claims_event` varria todos os datasets de todas as pastas a CADA
        # evento push — com 3 pastas de 2000 datasets e uma publicacao em lote,
        # sao milhoes de comparacoes de dicionario dentro do event loop.
        self._by_remote_id: dict[str, str] = {}
        self._by_remote_name: dict[str, str] = {}
        self._by_file: dict[str, str] = {}
        self._reindexar()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ver = data.get("version", 1)
                if ver == _VERSION:
                    return data
                if ver == 1:
                    return self._migrate_v1(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Manifesto corrompido, recriando: %s", e)
        return self._empty()

    def _migrate_v1(self, data: dict) -> dict:
        """Migra manifesto v1 para v2 (adiciona campos bidi-sync)."""
        data["version"] = 2
        data.setdefault("sync_mode", "upload")
        for ds in data.get("datasets", {}).values():
            ds.setdefault("remote_md5", None)
            ds.setdefault("local_md5", None)
            ds.setdefault("sync_direction", "local")
        logger.info("Manifesto migrado de v1 para v2.")
        return data

    def _empty(self) -> dict:
        return {
            "version": _VERSION,
            "workspace_id": self.workspace_id,
            "executor_id": self.executor_id,
            "sync_mode": "upload",
            "last_full_scan": None,
            "datasets": {},
            "pending_queue": [],
        }

    # ── Persistencia ─────────────────────────────────────────────────────────

    def _escrever(self, conteudo: str) -> bool:
        """Grava o manifesto de forma atomica (.tmp + os.replace).

        Um crash no meio do `json.dump` deixava o arquivo truncado; o `_load`
        recriava do zero e o executor re-enviava a pasta inteira.

        Devolve se o conteudo chegou mesmo ao disco: quem chama PRECISA saber,
        porque so ai pode considerar a versao persistida. Engolindo o OSError e
        dando a gravacao como feita, um disco cheio virava perda silenciosa de
        estado — o sintoma seria o manifesto parando de salvar, sem nenhum erro
        visivel no fluxo de sync.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(conteudo)
            os.replace(str(tmp), str(self.path))
            # Reaplicado a CADA gravacao, e nao so na criacao: no Windows o
            # os.replace (MoveFileEx) faz o manifesto herdar os atributos do
            # `.tmp`, que nasce visivel — sem isto o arquivo voltaria a aparecer
            # no Explorer no primeiro flush. Escrever no `.tmp` e depois ocultar
            # o destino tambem evita o outro lado da armadilha: o open("w") de um
            # CREATE_ALWAYS sobre um arquivo JA oculto falha com acesso negado no
            # Windows — por isso nunca gravamos direto no caminho final.
            ocultar_no_windows(self.path)
            return True
        except OSError as e:
            logger.error("Erro ao salvar manifesto: %s", e)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _serializar(self) -> str:
        # Sem `indent=2`: e arquivo de maquina, e a indentacao dobrava o volume
        # gravado a cada ciclo sem beneficio nenhum.
        return json.dumps(self._data, default=str)

    def _marcar_sujo(self) -> None:
        self._versao += 1

    @property
    def _sujo(self) -> bool:
        """Ha mutacao ainda nao confirmada em disco?"""
        return self._versao != self._versao_no_disco

    async def flush(self, min_intervalo: float = 0.0) -> None:
        """Grava o manifesto se ele mudou, fora do event loop.

        `min_intervalo` > 0 e o flush oportunista de dentro de um lote de
        uploads: durabilidade a cada T segundos, em vez de uma reserializacao
        completa por dataset. O fim do ciclo chama sem intervalo (forcado).

        A serializacao acontece AQUI, no loop, e nao na thread: o dict e mutado
        pelo loop e um `json.dumps` concorrente veria o dicionario mudando de
        tamanho no meio da iteracao.

        Com uploads concorrentes, duas gravacoes simultaneas disputariam o mesmo
        `.tmp`: quem chega durante uma gravacao desiste e deixa o manifesto
        sujo — o flush do fim do ciclo leva o estado mais novo.

        A versao gravada e capturada ANTES da serializacao e so vira
        `_versao_no_disco` se a gravacao confirmar. Assim: gravacao que falha
        (disco cheio) mantem o manifesto sujo e o proximo flush tenta de novo; e
        mutacao ocorrida durante a gravacao continua pendente, em vez de ser
        dada como salva junto com o snapshot anterior.
        """
        if not self._sujo or self._gravando:
            return
        if min_intervalo and (time.monotonic() - self._ultimo_flush) < min_intervalo:
            return
        versao = self._versao
        conteudo = self._serializar()
        # O relogio do rate-limit anda mesmo se a gravacao falhar: senao, com o
        # disco cheio, cada dataset do lote pagaria uma reserializacao completa.
        self._ultimo_flush = time.monotonic()
        self._gravando = True
        try:
            gravou = await em_thread(self._escrever, conteudo)
        finally:
            self._gravando = False
        if gravou:
            self._versao_no_disco = versao

    # ── Indices invertidos ───────────────────────────────────────────────────

    def _reindexar(self):
        self._by_remote_id.clear()
        self._by_remote_name.clear()
        self._by_file.clear()
        for name, ds in self._data["datasets"].items():
            if isinstance(ds, dict):
                self._indexar(name, ds)

    def _indexar(self, name: str, ds: dict):
        rid = ds.get("remote_id_hash")
        if rid:
            self._by_remote_id[rid] = name
        rname = remote_name_of(name, ds)
        if rname:
            self._by_remote_name[rname] = name
        for fname in ds.get("files") or {}:
            self._by_file[fname] = name

    def _desindexar(self, name: str, ds: dict | None):
        """Tira do indice as chaves da versao ANTERIOR da entrada.

        Um indice defasado faria o push cair na pasta errada ou duplicar a
        entrada, entao a remocao e por VALOR: so sai do indice o que ainda
        aponta para este dataset.
        """
        if not isinstance(ds, dict):
            return
        rid = ds.get("remote_id_hash")
        if rid and self._by_remote_id.get(rid) == name:
            del self._by_remote_id[rid]
        rname = remote_name_of(name, ds)
        if rname and self._by_remote_name.get(rname) == name:
            del self._by_remote_name[rname]
        for fname in ds.get("files") or {}:
            if self._by_file.get(fname) == name:
                del self._by_file[fname]

    def find(self, id_hash: str = "", original_name: str = "") -> str | None:
        """
        Localiza a chave de manifesto que representa um objeto remoto.

        Ordem de confianca: id remoto → nome do objeto remoto → nome de arquivo
        local. O casamento por 'remote_name' e o que reconhece o '<dataset>.zip'
        de um shapefile — cujos arquivos no manifesto sao os componentes
        .shp/.dbf/..., nunca o nome do pacote que foi efetivamente enviado.
        """
        if id_hash:
            achado = self._by_remote_id.get(id_hash)
            if achado is not None:
                return achado
        if original_name:
            return (self._by_remote_name.get(original_name)
                    or self._by_file.get(original_name))
        return None

    def find_by_remote_id(self, id_hash: str) -> str | None:
        return self._by_remote_id.get(id_hash) if id_hash else None

    # ── Datasets ─────────────────────────────────────────────────────────────

    def get_dataset(self, name: str) -> dict | None:
        return self._data["datasets"].get(name)

    def set_dataset(self, name: str, dataset: dict):
        self._desindexar(name, self._data["datasets"].get(name))
        self._data["datasets"][name] = dataset
        self._indexar(name, dataset)
        self._marcar_sujo()

    def remove_dataset(self, name: str):
        self._desindexar(name, self._data["datasets"].get(name))
        self._data["datasets"].pop(name, None)
        self._marcar_sujo()

    def all_datasets(self) -> dict:
        return self._data["datasets"]

    def mark_synced(self, name: str, remote_id_hash: str, spatial_metadata: dict | None = None,
                    local_md5: str | None = None, remote_md5: str | None = None):
        ds = self._data["datasets"].get(name, {})
        self._desindexar(name, ds)
        ds["remote_id_hash"] = remote_id_hash
        ds["status"] = "synced"
        ds["synced_at"] = datetime.now(timezone.utc).isoformat()
        if spatial_metadata:
            ds["spatial_metadata"] = spatial_metadata
        if local_md5:
            ds["local_md5"] = local_md5
        if remote_md5:
            ds["remote_md5"] = remote_md5
        self._data["datasets"][name] = ds
        self._indexar(name, ds)
        self._marcar_sujo()

    def mark_pending(self, name: str, action: str):
        ds = self._data["datasets"].get(name, {})
        ds["status"] = "pending"
        ds["pending_action"] = action
        self._data["datasets"][name] = ds
        self._indexar(name, ds)
        self._marcar_sujo()

    # ── Queue ────────────────────────────────────────────────────────────────

    def enqueue(self, action: str, dataset_name: str, extra: dict | None = None):
        """Enfileira uma operacao pendente. IDEMPOTENTE por (action, dataset).

        A fila e um conjunto de operacoes a fazer, nao um historico: dois itens
        `('upload', 'parcelas')` significam a mesma coisa. E o duplicado nao era
        inofensivo — como cada falha de upload deixa a entrada do manifesto sem
        'files', o `diff` do ciclo seguinte reenfileirava o mesmo dataset, e a
        fila crescia um item por ciclo. Cada um deles era executado sem backoff
        (o agendamento so alcanca o item de fato executado), pagando
        validate + extract_metadata + MD5 do dataset inteiro a cada 30s.

        Reenfileirar NAO reinicia o backoff do item que ja esta la: so atualiza
        os extras (o `remote_id_hash` de um delete, por exemplo).
        """
        existente = next(
            (q for q in self._data["pending_queue"]
             if q.get("dataset") == dataset_name and q.get("action") == action),
            None,
        )
        if existente is not None:
            if extra:
                existente.update(extra)
                self._marcar_sujo()
            return

        item = {
            "action": action,
            "dataset": dataset_name,
            "retries": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_attempt": None,
            # Epoch da proxima tentativa. 0 = tentar no proximo ciclo. E o que
            # substituiu o `asyncio.sleep(backoff)` que congelava a pasta
            # inteira dentro do ciclo.
            "next_attempt_at": 0.0,
            **(extra or {}),
        }
        self._data["pending_queue"].append(item)
        self._marcar_sujo()

    def dequeue(self, dataset_name: str):
        self._data["pending_queue"] = [
            q for q in self._data["pending_queue"] if q["dataset"] != dataset_name
        ]
        self._marcar_sujo()

    def pending_items(self) -> list[dict]:
        return self._data["pending_queue"]

    def update_retry(self, item: dict, next_attempt_at: float = 0.0):
        """Contabiliza a falha NO ITEM que foi executado.

        Recebe o proprio dict da fila (e nao o nome do dataset) porque casar por
        nome atualizava sempre o PRIMEIRO homonimo: com a fila trazendo itens
        equivalentes, os demais ficavam eternamente com next_attempt_at=0 e
        retries=0 — reexecutados a cada ciclo, sem backoff e sem nunca esgotar
        as tentativas.
        """
        item["retries"] = item.get("retries", 0) + 1
        item["last_attempt"] = datetime.now(timezone.utc).isoformat()
        item["next_attempt_at"] = next_attempt_at
        self._marcar_sujo()

    # ── Scan ─────────────────────────────────────────────────────────────────

    def set_last_scan(self):
        self._data["last_full_scan"] = datetime.now(timezone.utc).isoformat()
        self._marcar_sujo()
