# executor/stats.py
"""
Coletor de estatisticas do executor.

Agrega em memoria tudo que o painel mostra. Stdlib pura, sem psutil e sem
rich: `connection.py` e `main.py` importam este modulo, e nao podem depender
de nada que sugira interface grafica.

Duas metades:

  ESCRITA  — metodos `on_*`, chamados dos hooks. Todos O(1), todos
             best-effort (nunca levantam: telemetria quebrada nao pode
             derrubar a execucao de um workflow).

  LEITURA  — `snapshot()`, chamado uma vez por tick do painel. Recebe por
             parametro os valores que sao lidos "na hora" (capacidade da fila,
             recursos do sistema), para nao guardar referencias a objetos
             vivos do executor.

Nada aqui parseia mensagem de log. As duracoes, estados e contadores vem dos
dados estruturados que ja circulam pelo executor — mensagem de log e texto em
portugues que muda sem aviso, e uma metrica que depende disso quebra em
silencio na primeira reescrita.
"""
from __future__ import annotations

import dataclasses
import functools
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

logger = logging.getLogger("executor.stats")

_JANELA_PADRAO_S = 3600.0     # "ultima hora"
_MAX_AMOSTRAS = 5000          # teto de memoria num executor de alta vazao
_TAIL_PADRAO = 200            # linhas de log guardadas para o rodape
_DEDUPE_SYNC = 256            # eventos de sync recentes, para ignorar reenvio


# ── Estruturas de saida ──────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RunningJob:
    job_id: str
    run_id: str | None
    elapsed_s: float
    node: str | None          # nome do no em execucao
    nodes_done: int
    nodes_total: int | None


@dataclass(frozen=True, slots=True)
class LogLine:
    ts: str
    level: str
    alias: str
    msg: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    # identidade
    executor_id: str
    version: str
    server_url: str
    system: Mapping[str, object]
    uptime_s: float
    # Ha quanto tempo as contagens medem. Igual ao uptime, exceto depois de um
    # reset pela tecla 'z' — e o que permite o painel dizer "zerado ha 5m" em
    # vez de deixar o operador achando que o executor acabou de subir.
    contando_ha_s: float

    # workflows
    total_ok: int
    total_error: int
    total_cancelled: int
    success_rate: float
    last_hour_total: int
    last_hour_error: int
    throughput_per_min: float

    # tempos (janela de 1 h, exceto `slowest`, que e desde o boot)
    avg_duration_s: float | None
    p50_duration_s: float | None
    p95_duration_s: float | None
    slowest: tuple[str, float] | None
    last_finished: tuple[str, str, float] | None
    running: tuple[RunningJob, ...]

    # recursos
    proc_cpu_pct: float | None
    proc_cpu_pct_norm: float | None
    proc_rss_mb: float | None
    proc_threads: int | None
    cpu_cores: float | None
    ram_available_gb: float | None
    ram_total_gb: float | None
    disk_free_gb: float | None
    disk_total_gb: float | None
    # Disco DA PASTA DE ARTEFATOS — pode ser outra unidade que a do sistema, e
    # e a que decide se um workflow consegue gravar o resultado. Com localidade
    # local (LGPD) o artefato tem uma copia so, e ela esta nesse disco.
    artifacts_disk_free_gb: float | None
    artifacts_disk_total_gb: float | None
    wf_cpu_peak_pct: float | None
    wf_mem_peak_mb: float | None
    nodes_executed_total: int
    nodes_failed_total: int

    # fila e conexao
    queued: int
    running_count: int
    max_concurrent: int
    max_queue: int
    result_queue_size: int
    outbox_pending: int
    conn_state: str
    conn_since_s: float | None
    reconnects: int
    heartbeat_age_s: float | None
    next_retry_in_s: float | None

    # geosync
    sync_dirs: tuple[str, ...]
    sync_files_up: int
    sync_bytes_up: int
    sync_files_down: int
    sync_bytes_down: int
    sync_errors: int
    sync_conflicts: int
    sync_current: str | None
    # Inventario do manifesto, publicado pelo manager ao fim de cada ciclo.
    # `total` e o que o executor CONHECE — nao o que existe no Drive, que
    # exigiria uma chamada de rede a cada tick.
    sync_total: int
    sync_synced: int
    sync_pending: int

    # rodape
    log_tail: tuple[LogLine, ...]
    log_warn_count: int
    log_error_count: int


# ── Serializacao ─────────────────────────────────────────────────────────────
# Esta e a mesma metade de LEITURA descrita no topo do modulo, so que para um
# consumidor que nao e o terminal. Mora aqui, e nao no pacote dashboard/, para
# que a fonte do dado e o formato do dado nao possam divergir: quem adiciona um
# campo ao Snapshot ganha o campo no JSON sem fazer nada, e ha teste que falha
# se um campo ficar de fora.
#
# `json` nao viola a regra de "nada que sugira interface grafica" do cabecalho:
# e stdlib de serializacao, nao de apresentacao.

def _json_safe(valor, casas: int):
    """Converte recursivamente para tipos que o `json` aceita.

    Arredondar corta ruido: `uptime_s` com 12 casas muda a cada tick e nao diz
    nada. O fallback para `str` e deliberado — um valor exotico vindo de
    `system` (que e montado por sysinfo e pode mudar) degrada para texto em vez
    de derrubar a serializacao inteira e, com ela, o canal com o app.
    """
    if valor is None or isinstance(valor, (bool, int, str)):
        return valor
    if isinstance(valor, float):
        # inf/nan nao sao JSON valido; viram null em vez de quebrar o parser.
        return round(valor, casas) if valor == valor and abs(valor) != float("inf") else None
    if isinstance(valor, dict):
        return {str(k): _json_safe(v, casas) for k, v in valor.items()}
    if isinstance(valor, (list, tuple, set, frozenset)):
        return [_json_safe(v, casas) for v in valor]
    return str(valor)


def snapshot_to_dict(s: Snapshot, *, casas: int = 3) -> dict:
    """Serializa um `Snapshot` para dict pronto para `json.dumps`.

    Os unicos campos que nao saem do `asdict` direto sao `slowest` e
    `last_finished`: no dataclass sao tuplas heterogeneas, que em JSON virariam
    arrays posicionais do tipo `["run-7","error",12.4]`. Do outro lado da ponte
    isso vira `snap.slowest[1]` — um indice sem nome que ninguem consegue ler e
    que quebra em silencio se a ordem mudar. Viram objetos nomeados.
    """
    d = dataclasses.asdict(s)

    d["slowest"] = (
        {"run_id": s.slowest[0], "duration_s": s.slowest[1]} if s.slowest else None
    )
    d["last_finished"] = (
        {"run_id": s.last_finished[0], "status": s.last_finished[1],
         "duration_s": s.last_finished[2]}
        if s.last_finished else None
    )
    return _json_safe(d, casas)


# ── Percentil ────────────────────────────────────────────────────────────────

def percentile(ordenados: Sequence[float], q: float) -> float | None:
    """Percentil por interpolacao linear (mesma convencao do numpy).

    `statistics.quantiles` nao serve aqui: ele exige n >= 2 e devolve os cortes
    de uma distribuicao, nao o valor em q. Com poucas amostras — o caso comum
    num executor que acabou de subir — precisamos de algo que funcione com n=1.
    """
    n = len(ordenados)
    if n == 0:
        return None
    if n == 1:
        return float(ordenados[0])
    pos = (n - 1) * q
    baixo = int(pos)
    alto = min(baixo + 1, n - 1)
    frac = pos - baixo
    return float(ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * frac)


def _fmt_ts(epoch: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(epoch))


def _travado(metodo):
    """Serializa o acesso ao estado do coletor — ver a nota do `_lock`."""
    @functools.wraps(metodo)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return metodo(self, *args, **kwargs)
    return wrapper


# ── Coletor ──────────────────────────────────────────────────────────────────

@dataclass
class _RunState:
    """Estado vivo de um job em execucao, montado a partir dos node events."""
    job_id: str
    run_id: str | None = None
    started_at: float = 0.0
    node: str | None = None
    nodes_done: int = 0
    nodes_total: int | None = None


class ExecutorStats:
    """Agregador. Uma instancia por processo, criada em main() quando o painel liga."""

    def __init__(
        self,
        *,
        executor_id: str = "",
        version: str = "",
        server_url: str = "",
        clock: Callable[[], float] = time.monotonic,
        janela_s: float = _JANELA_PADRAO_S,
        max_amostras: int = _MAX_AMOSTRAS,
        tail: int = _TAIL_PADRAO,
        observer: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.executor_id = executor_id
        self.version = version
        self.server_url = server_url
        # Recebe (tipo, dados) a cada mudanca de estado relevante, para quem
        # precisa do evento na hora em vez de esperar o proximo tick — o painel
        # rich nao precisa (ele repinta o snapshot inteiro), mas o app desktop
        # sim: `last_finished` guarda UM job, entao dois terminando dentro do
        # mesmo segundo fariam o primeiro sumir do historico.
        #
        # CONTRATO: o observer roda com o `_lock` segurado e e chamado de
        # qualquer thread. Ele PRECISA ser O(1) e nao-bloqueante — tipicamente
        # um append em buffer limitado. Um observer que faz I/O aqui trava
        # `on_log_record`, que e chamado das threads do flow engine, e o
        # executor inteiro para.
        self._observer = observer
        self._clock = clock
        self._janela = janela_s
        self._t0 = clock()

        # A maior parte dos hooks roda no event loop, mas `on_log_record` nao:
        # o flow engine loga de dentro dos `asyncio.to_thread`, entao ele chega
        # pela thread que emitiu o registro. Sem o lock, um `append` durante o
        # `snapshot()` levanta "deque mutated during iteration" — e como o
        # runtime desliga o painel apos 3 falhas seguidas de render, um executor
        # com log ativo o suficiente perdia o painel sozinho.
        # Reentrante porque `on_job_cancelled` delega para `on_job_finished`.
        self._lock = threading.RLock()

        self.system: dict = {}
        self.sync_dirs: tuple[str, ...] = ()

        # Marco dos CONTADORES, separado do `_t0` do processo. A tecla 'z' move
        # so este: o uptime continua sendo ha quanto tempo o executor esta no ar
        # (informacao de sistema), enquanto as contagens recomecam do zero. Sem
        # a separacao, a vazao logo apos um reset dividiria 0 execucoes por
        # horas de uptime e mostraria ~0 wf/min para sempre.
        self._contadores_desde = self._t0

        # workflows — contadores acumulados vivem FORA da janela deslizante,
        # senao "total desde o boot" viraria "total na ultima hora".
        self._ok = 0
        self._erro = 0
        self._cancelado = 0
        self._soma_duracoes = 0.0
        self._n_duracoes = 0
        self._slowest: tuple[str, float] | None = None
        self._last_finished: tuple[str, str, float] | None = None
        self._nodes_executed = 0
        self._nodes_failed = 0
        self._wf_cpu_peak: float | None = None
        self._wf_mem_peak: float | None = None

        # janela deslizante: (ts, duracao_s, status)
        self._janela_jobs: deque[tuple[float, float, str]] = deque(maxlen=max_amostras)

        # jobs em execucao
        self._running: dict[str, _RunState] = {}
        self._run_para_job: dict[str, str] = {}
        # Ids ja contabilizados. Um job cancelado em execucao chega DUAS vezes:
        # pelo `finally` do on_execute e pelo on_cancelled da fila. Sem esta
        # memoria curta ele apareceria duas vezes no total.
        self._finalizados: deque[str] = deque(maxlen=256)
        self._finalizados_set: set[str] = set()

        # conexao
        self._conn_state = "offline"
        self._conn_desde: float | None = None
        self._reconnects = 0
        self._ultimo_heartbeat: float | None = None
        self._proximo_retry: float | None = None

        # geosync
        self._sync_up_arq = 0
        self._sync_up_bytes = 0
        self._sync_down_arq = 0
        self._sync_down_bytes = 0
        self._sync_erros = 0
        self._sync_conflitos = 0
        self._sync_atual: str | None = None
        self._sync_total = 0
        self._sync_synced = 0
        self._sync_pending = 0
        # Reenvio de evento pelo _requeue_event da connection faria o MESMO
        # upload contar duas vezes. O timestamp e fixado no emit e sobrevive
        # a requeue, entao serve de chave de identidade.
        self._sync_vistos: deque[tuple] = deque(maxlen=_DEDUPE_SYNC)
        self._sync_vistos_set: set[tuple] = set()

        # log
        self._tail: deque[LogLine] = deque(maxlen=tail)
        self._janela_logs: deque[tuple[float, int]] = deque(maxlen=max_amostras)

    @_travado
    def reset(self) -> None:
        """Zera as contagens da sessao sem tocar no estado vivo.

        O que ZERA: workflows, tempos, metricas de no, GeoSync, reconexoes e o
        buffer de alertas. O que PERMANECE: os jobs em execucao (estao rodando
        de verdade), o estado da conexao e o uptime do processo.
        """
        agora = self._clock()
        self._contadores_desde = agora

        self._ok = self._erro = self._cancelado = 0
        self._soma_duracoes = 0.0
        self._n_duracoes = 0
        self._slowest = None
        self._last_finished = None
        self._nodes_executed = self._nodes_failed = 0
        self._wf_cpu_peak = self._wf_mem_peak = None
        self._janela_jobs.clear()

        self._sync_up_arq = self._sync_up_bytes = 0
        self._sync_down_arq = self._sync_down_bytes = 0
        self._sync_erros = self._sync_conflitos = 0

        self._reconnects = 0
        self._tail.clear()
        self._janela_logs.clear()

        # `_finalizados` e `_sync_vistos` NAO sao zerados: sao memorias de
        # deduplicacao, nao contadores. Limpa-las faria um evento reenviado
        # logo apos o reset contar de novo.

    def set_observer(self, observer: Callable[[str, dict], None] | None) -> None:
        """Liga (ou desliga) o observer depois da construcao.

        Existe por uma dependencia circular no boot: o coletor e criado em
        `main()` para que as filas e a conexao ja nascam com ele, mas quem
        consome os eventos — o runtime do canal NDJSON — so existe depois, e
        precisa do proprio coletor como argumento. Um dos dois tem de ser
        ligado em dois tempos.

        Vale o mesmo CONTRATO do parametro do construtor: O(1) e nao-bloqueante.
        """
        self._observer = observer

    def _emitir(self, tipo: str, dados: dict) -> None:
        """Entrega ao observer, best-effort. Mesma regra dos hooks `on_*`:
        telemetria quebrada nunca derruba a execucao de um workflow."""
        obs = self._observer
        if obs is None:
            return
        try:
            obs(tipo, dados)
        except Exception:
            pass

    # ── Escrita: jobs ────────────────────────────────────────────────────────

    @_travado
    def on_job_started(self, job_id: str, run_id: str | None = None) -> None:
        st = _RunState(job_id=job_id, run_id=run_id, started_at=self._clock())
        self._running[job_id] = st
        if run_id:
            self._run_para_job[run_id] = job_id
        self._emitir("job", {"event": "started", "job_id": job_id, "run_id": run_id})

    @_travado
    def on_job_finished(
        self,
        job_id: str,
        status: str,
        duracao_s: float,
        *,
        run_id: str | None = None,
        metrics: Mapping | None = None,
    ) -> None:
        st = self._running.pop(job_id, None)
        rid = run_id or (st.run_id if st else None) or job_id
        if st and st.run_id:
            self._run_para_job.pop(st.run_id, None)

        self._marcar_finalizado(job_id)
        agora = self._clock()
        if status == "ok":
            self._ok += 1
        elif status == "cancelled":
            self._cancelado += 1
        else:
            status = "error"
            self._erro += 1

        self._janela_jobs.append((agora, duracao_s, status))
        self._last_finished = (rid, status, duracao_s)

        # Cancelado nao entra na media: um job morto aos 2s nao diz nada sobre
        # quanto tempo um workflow leva, e puxaria a media para baixo.
        if status != "cancelled":
            self._soma_duracoes += duracao_s
            self._n_duracoes += 1
            if self._slowest is None or duracao_s > self._slowest[1]:
                self._slowest = (rid, duracao_s)

        self._absorver_metrics(metrics)
        run = (metrics or {}).get("run") or {}
        self._emitir("job", {
            "event": "cancelled" if status == "cancelled" else "finished",
            "job_id": job_id, "run_id": rid, "status": status,
            "duration_s": duracao_s,
            "nodes_executed": run.get("nodes_executed"),
            "nodes_failed": run.get("nodes_failed"),
        })

    @_travado
    def on_job_cancelled(self, job_id: str, motivo: str | None = None) -> None:
        """Cancelamento reportado pela fila.

        Chega para o job que foi interrompido em execucao (ja contado pelo
        `finally` do on_execute) e para o que foi descartado sem nunca rodar
        (nao contado em lugar nenhum). Distinguimos pela memoria de ids
        finalizados: sem isso, o primeiro caso somaria duas vezes.
        """
        if job_id in self._finalizados_set:
            return
        if job_id in self._running:
            # Delega — e o on_job_finished que emite, senao o evento sairia
            # duplicado para o mesmo cancelamento.
            self.on_job_finished(job_id, "cancelled", 0.0)
            return
        self._marcar_finalizado(job_id)
        self._cancelado += 1
        self._janela_jobs.append((self._clock(), 0.0, "cancelled"))
        self._emitir("job", {
            "event": "cancelled", "job_id": job_id, "run_id": None,
            "status": "cancelled", "duration_s": 0.0, "motivo": motivo,
        })

    def _marcar_finalizado(self, job_id: str) -> None:
        if job_id in self._finalizados_set:
            return
        if len(self._finalizados) == self._finalizados.maxlen:
            self._finalizados_set.discard(self._finalizados[0])
        self._finalizados.append(job_id)
        self._finalizados_set.add(job_id)

    def _absorver_metrics(self, metrics: Mapping | None) -> None:
        """Extrai o bloco `run` de stats['__metrics__'] (flow/metrics/collector)."""
        if not metrics:
            return
        try:
            run = metrics.get("run") or {}
            self._nodes_executed += int(run.get("nodes_executed") or 0)
            self._nodes_failed += int(run.get("nodes_failed") or 0)
            cpu = run.get("cpu_peak_pct")
            if cpu is not None:
                self._wf_cpu_peak = max(self._wf_cpu_peak or 0.0, float(cpu))
            mem = run.get("mem_peak_mb")
            if mem is not None:
                self._wf_mem_peak = max(self._wf_mem_peak or 0.0, float(mem))
        except Exception:
            pass  # telemetria malformada nao e motivo para nada quebrar

    # ── Escrita: eventos da fila (node events + sync events) ─────────────────

    @_travado
    def on_event(self, event: Mapping) -> None:
        try:
            if event.get("type") == "sync_event":
                self._on_sync_event(event)
            else:
                self._on_node_event(event)
        except Exception:
            pass

    def _on_node_event(self, event: Mapping) -> None:
        run_id = event.get("run_id")
        if not run_id:
            return
        job_id = self._run_para_job.get(run_id)
        st = self._running.get(job_id) if job_id else None
        if st is None:
            # O payload trouxe um run_id diferente do job_id. Casa por eliminacao
            # — mas SO se houver exatamente um candidato: com varios jobs
            # simultaneos sem run_id, escolher "o primeiro" atribuiria o no de um
            # job ao outro, e um painel que mente e pior que um painel incompleto.
            candidatos = [c for c in self._running.values() if c.run_id is None]
            if len(candidatos) != 1:
                return
            st = candidatos[0]
            st.run_id = run_id
            self._run_para_job[run_id] = st.job_id

        status = (event.get("status") or "").lower()
        extra = event.get("extra") or {}
        nome = extra.get("node_name") or event.get("node")

        if status in ("started", "running"):
            st.node = nome
        elif status in ("completed", "failed", "skipped", "pinned", "cached"):
            st.nodes_done += 1
            st.node = None

        total = extra.get("nodes_total")
        if total:
            try:
                st.nodes_total = int(total)
            except (TypeError, ValueError):
                pass

    def _on_sync_event(self, event: Mapping) -> None:
        chave = (event.get("event"), event.get("dataset"), event.get("timestamp"))
        if chave in self._sync_vistos_set:
            return  # reenvio pelo _requeue_event — ja contabilizado
        if len(self._sync_vistos) == self._sync_vistos.maxlen:
            self._sync_vistos_set.discard(self._sync_vistos[0])
        self._sync_vistos.append(chave)
        self._sync_vistos_set.add(chave)

        nome = event.get("event")
        dataset = event.get("dataset") or ""
        try:
            total_bytes = int(event.get("total_bytes") or 0)
        except (TypeError, ValueError):
            total_bytes = 0

        if nome == "file_uploaded":
            self._sync_up_arq += max(int(event.get("file_count") or 1), 1)
            self._sync_up_bytes += total_bytes
            self._sync_atual = None
        elif nome == "file_downloaded":
            self._sync_down_arq += 1
            self._sync_down_bytes += total_bytes
            self._sync_atual = None
        elif nome == "file_uploading":
            self._sync_atual = f"↑ {dataset}"
        elif nome == "file_downloading":
            self._sync_atual = f"↓ {dataset}"
        elif nome == "sync_error":
            self._sync_erros += 1
            self._sync_atual = None
        elif nome == "conflict_detected":
            self._sync_conflitos += 1
        elif nome in ("sync_complete", "sync_started"):
            self._sync_atual = None
        elif nome == "sync_inventory":
            # Substitui, nao acumula: e uma fotografia do manifesto, nao um
            # contador de eventos.
            try:
                self._sync_total = int(event.get("total") or 0)
                self._sync_synced = int(event.get("synced") or 0)
                self._sync_pending = int(event.get("pending") or 0)
            except (TypeError, ValueError):
                pass

        self._emitir("sync", {
            "event": nome, "dataset": dataset, "total_bytes": total_bytes,
        })

    # ── Escrita: conexao ─────────────────────────────────────────────────────

    @_travado
    def on_connecting(self) -> None:
        self._conn_state = "reconnecting" if self._reconnects or self._conn_desde else "connecting"
        self._emitir("conn", {"state": self._conn_state, "reconnects": self._reconnects})

    @_travado
    def on_connected(self) -> None:
        if self._conn_desde is not None:
            self._reconnects += 1
        self._conn_state = "connected"
        self._conn_desde = self._clock()
        self._proximo_retry = None
        self._emitir("conn", {"state": "connected", "reconnects": self._reconnects})

    @_travado
    def on_disconnected(self, *, proximo_retry_s: float | None = None, terminal: bool = False) -> None:
        self._conn_state = "terminal" if terminal else "reconnecting"
        self._proximo_retry = None if terminal else proximo_retry_s
        self._ultimo_heartbeat = None
        self._emitir("conn", {
            "state": self._conn_state, "reconnects": self._reconnects,
            "next_retry_in_s": self._proximo_retry,
        })

    @_travado
    def on_heartbeat(self) -> None:
        self._ultimo_heartbeat = self._clock()

    # ── Escrita: log ─────────────────────────────────────────────────────────

    @_travado
    def on_log_record(self, record: logging.LogRecord, alias: str, level: str) -> None:
        try:
            self._tail.append(LogLine(
                ts=_fmt_ts(record.created),
                level=level.strip(),
                alias=alias.strip(),
                msg=record.getMessage(),
            ))
            self._janela_logs.append((self._clock(), record.levelno))
        except Exception:
            pass

    # ── Leitura ──────────────────────────────────────────────────────────────

    def _podar(self) -> None:
        limite = self._clock() - self._janela
        while self._janela_jobs and self._janela_jobs[0][0] < limite:
            self._janela_jobs.popleft()
        while self._janela_logs and self._janela_logs[0][0] < limite:
            self._janela_logs.popleft()

    @_travado
    def snapshot(
        self,
        *,
        capacity: Mapping | None = None,
        recursos: Mapping | None = None,
        processo: Mapping | None = None,
        outbox_pending: int = 0,
        result_queue_size: int = 0,
    ) -> Snapshot:
        self._podar()
        agora = self._clock()
        cap = capacity or {}
        rec = recursos or {}
        proc = processo or {}

        duracoes = sorted(d for _, d, s in self._janela_jobs if s != "cancelled")
        hora_total = len(self._janela_jobs)
        hora_erro = sum(1 for _, _, s in self._janela_jobs if s == "error")

        finalizados = self._ok + self._erro + self._cancelado
        # 1.0 num executor recem-subido: mostrar "0% de sucesso" antes da
        # primeira execucao seria alarme falso.
        taxa = (self._ok / finalizados) if finalizados else 1.0

        uptime = agora - self._t0
        # A vazao mede desde o marco dos CONTADORES, nao do processo: depois de
        # um reset, dividir as execucoes novas por horas de uptime daria ~0.
        medindo_ha = agora - self._contadores_desde
        vazao = (hora_total / (min(medindo_ha, self._janela) / 60.0)) if medindo_ha > 1 else 0.0

        running = tuple(
            RunningJob(
                job_id=st.job_id,
                run_id=st.run_id,
                elapsed_s=agora - st.started_at,
                node=st.node,
                nodes_done=st.nodes_done,
                nodes_total=st.nodes_total,
            )
            for st in sorted(self._running.values(), key=lambda s: s.started_at)
        )

        return Snapshot(
            executor_id=self.executor_id,
            version=self.version,
            server_url=self.server_url,
            system=dict(self.system),
            uptime_s=uptime,
            contando_ha_s=medindo_ha,
            total_ok=self._ok,
            total_error=self._erro,
            total_cancelled=self._cancelado,
            success_rate=taxa,
            last_hour_total=hora_total,
            last_hour_error=hora_erro,
            throughput_per_min=round(vazao, 2),
            avg_duration_s=(self._soma_duracoes / self._n_duracoes) if self._n_duracoes else None,
            p50_duration_s=percentile(duracoes, 0.50),
            p95_duration_s=percentile(duracoes, 0.95),
            slowest=self._slowest,
            last_finished=self._last_finished,
            running=running,
            proc_cpu_pct=proc.get("cpu_pct"),
            proc_cpu_pct_norm=proc.get("cpu_pct_norm"),
            proc_rss_mb=proc.get("rss_mb"),
            proc_threads=proc.get("threads"),
            cpu_cores=proc.get("cpu_cores") or self.system.get("cpu_cores"),
            ram_available_gb=rec.get("ram_available_gb"),
            ram_total_gb=self.system.get("ram_total_gb"),
            disk_free_gb=rec.get("disk_free_gb"),
            disk_total_gb=self.system.get("disk_total_gb"),
            artifacts_disk_free_gb=rec.get("artifacts_disk_free_gb"),
            artifacts_disk_total_gb=rec.get("artifacts_disk_total_gb"),
            wf_cpu_peak_pct=self._wf_cpu_peak,
            wf_mem_peak_mb=self._wf_mem_peak,
            nodes_executed_total=self._nodes_executed,
            nodes_failed_total=self._nodes_failed,
            queued=int(cap.get("queued") or 0),
            running_count=int(cap.get("running") or 0),
            max_concurrent=int(cap.get("max_concurrent") or 0),
            max_queue=int(cap.get("max_queue") or 0),
            result_queue_size=result_queue_size,
            outbox_pending=outbox_pending,
            conn_state=self._conn_state,
            conn_since_s=(agora - self._conn_desde) if self._conn_desde is not None else None,
            reconnects=self._reconnects,
            heartbeat_age_s=(agora - self._ultimo_heartbeat) if self._ultimo_heartbeat else None,
            next_retry_in_s=self._proximo_retry,
            sync_dirs=self.sync_dirs,
            sync_total=self._sync_total,
            sync_synced=self._sync_synced,
            sync_pending=self._sync_pending,
            sync_files_up=self._sync_up_arq,
            sync_bytes_up=self._sync_up_bytes,
            sync_files_down=self._sync_down_arq,
            sync_bytes_down=self._sync_down_bytes,
            sync_errors=self._sync_erros,
            sync_conflicts=self._sync_conflitos,
            sync_current=self._sync_atual,
            log_tail=tuple(self._tail),
            log_warn_count=sum(1 for _, lv in self._janela_logs if lv == logging.WARNING),
            log_error_count=sum(1 for _, lv in self._janela_logs if lv >= logging.ERROR),
        )


class NullStats:
    """Mesma superficie, tudo no-op.

    Existe para que `connection.py` e `main.py` chamem `self._stats.on_X()` sem
    nenhum `if stats is not None` espalhado — com o painel desligado, o custo e
    uma chamada de funcao vazia por evento.
    """
    executor_id = ""
    version = ""
    server_url = ""
    system: dict = {}
    sync_dirs: tuple = ()

    # Aceita os mesmos kwargs do ExecutorStats (inclusive `observer`) para que a
    # troca entre os dois seja um `if` no construtor, e nada alem disso.
    def __init__(self, *a, **k) -> None: ...

    # `reset` faltava: o painel chama `stats.reset()` na tecla 'z' e o comando
    # `reset_stats` do IPC faz o mesmo. Com o coletor desligado isso levantava
    # AttributeError em vez de nao fazer nada.
    def reset(self, *a, **k) -> None: ...
    def set_observer(self, *a, **k) -> None: ...
    def on_job_started(self, *a, **k) -> None: ...
    def on_job_finished(self, *a, **k) -> None: ...
    def on_job_cancelled(self, *a, **k) -> None: ...
    def on_event(self, *a, **k) -> None: ...
    def on_connecting(self, *a, **k) -> None: ...
    def on_connected(self, *a, **k) -> None: ...
    def on_disconnected(self, *a, **k) -> None: ...
    def on_heartbeat(self, *a, **k) -> None: ...
    def on_log_record(self, *a, **k) -> None: ...
    def snapshot(self, *a, **k) -> None: return None
