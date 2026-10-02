# executor/main.py
"""
Entry point do executor Atlas.

Fluxo de inicialização:
  1. Carrega configuração (env vars)
  2. Fixa a chave de assinatura do servidor (enroll ou TOFU em disco)
  3. Carrega a chave privada X25519 gerada no enrollment — nunca gera outra
  4. Inicia ExecutorJobQueue com workers
  5. Inicia ExecutorConnection (loop de reconnect automático)
  6. Aguarda SIGTERM/SIGINT para shutdown gracioso

Uso:
  python -m executor.main
  # ou
  python executor/main.py
"""
import asyncio
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from executor import config as _cfg  # noqa: F401  (carrega o .env antes de tudo)
from executor.logging_setup import configure_logging

# Roda no import, como sempre rodou: qualquer modulo importado abaixo ja loga
# num root configurado. O conteudo mora em executor/logging_setup.py.
configure_logging()

logger = logging.getLogger("executor")


# ── Auto-restart ──────────────────────────────────────────────────────────────
# Sob Docker (`restart: on-failure`), sair com codigo 1 basta — e permite pegar
# uma imagem nova. Rodando direto no Python nao ha supervisor: sem re-exec, um
# `config_changed` apenas encerraria o executor e ele nao voltaria.
#
# EXECUTOR_AUTO_RESTART: auto (default) | always | never
_AUTO_RESTART_MODE = os.getenv("EXECUTOR_AUTO_RESTART", "auto").strip().lower()

# Guarda anti-loop: se a causa do restart persistir (ex: servidor reenviando
# config_changed a cada conexao), re-executar sem limite viraria spin infinito.
_RESTART_COUNT_VAR  = "_EXECUTOR_RESTART_COUNT"
_RESTART_SINCE_VAR  = "_EXECUTOR_RESTART_SINCE"
_MAX_RESTARTS       = 5
_RESTART_WINDOW_SEC = 300


def _in_container() -> bool:
    """Detecta execucao em container (Docker/K8s), onde ja existe supervisor."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", encoding="utf-8") as f:
            content = f.read()
        return "docker" in content or "kubepods" in content or "containerd" in content
    except OSError:
        return False


def _build_restart_argv() -> list[str]:
    """Reconstroi a linha de comando original.

    `python -m executor` deixa sys.argv[0] apontando para __main__.py; re-executar
    esse path direto quebraria os imports do pacote. O __spec__ do __main__ diz
    se viemos de `-m` e qual era o modulo.
    """
    import __main__
    spec = getattr(__main__, "__spec__", None)
    if spec is not None and getattr(spec, "name", None):
        modulo = spec.name.removesuffix(".__main__")
        return [sys.executable, "-m", modulo, *sys.argv[1:]]
    return [sys.executable, *sys.argv]


def _restart_process() -> None:
    """Substitui o processo atual por uma instancia nova (os.execv).

    No-op quando ha supervisor externo (container) ou quando desabilitado —
    nesses casos o caller segue para sys.exit(1). So retorna em caso de no-op
    ou falha; em sucesso, o processo e substituido e nada apos isto executa.
    """
    if _AUTO_RESTART_MODE == "never":
        logger.info("Auto-restart desabilitado (EXECUTOR_AUTO_RESTART=never) — encerrando.")
        return
    if _AUTO_RESTART_MODE == "auto" and _in_container():
        logger.info("Em container — encerrando com codigo 1 para o supervisor reiniciar.")
        return

    # Guarda incondicional: vale ate para EXECUTOR_AUTO_RESTART=always.
    #
    # `os.execve` substitui o processo em POSIX, mas no Windows a implementacao
    # do CPython CRIA um processo novo e encerra o atual. O supervisor veria o
    # filho que ele conhece morrer, perderia o rastro do executor real — que
    # segue vivo, com PID novo, segurando a conexao WebSocket sob o mesmo
    # EXECUTOR_ID — e subiria um segundo. Duas conexoes do mesmo executor.
    #
    # Havendo supervisor, reiniciar e trabalho DELE: basta sair com codigo != 0.
    from executor.supervisor import VAR_PID, pid_configurado
    if pid_configurado() is not None:
        logger.info(
            "Sob supervisor externo (%s) — encerrando com codigo 1 em vez de "
            "re-executar; o restart e responsabilidade dele.", VAR_PID,
        )
        return

    # Janela deslizante de tentativas, propagada ao novo processo via env.
    agora = int(time.time())
    try:
        desde = int(os.getenv(_RESTART_SINCE_VAR, "") or agora)
        contagem = int(os.getenv(_RESTART_COUNT_VAR, "") or 0)
    except ValueError:
        desde, contagem = agora, 0
    if agora - desde > _RESTART_WINDOW_SEC:
        desde, contagem = agora, 0  # janela expirou

    if contagem >= _MAX_RESTARTS:
        logger.error(
            "Auto-restart abortado: %d reinicios em menos de %ds. A causa persiste "
            "(servidor reenviando config_changed?). Encerrando para nao entrar em loop.",
            contagem, _RESTART_WINDOW_SEC,
        )
        return

    env = {**os.environ, _RESTART_COUNT_VAR: str(contagem + 1), _RESTART_SINCE_VAR: str(desde)}
    argv = _build_restart_argv()
    logger.info("Reiniciando executor no mesmo processo (tentativa %d)...", contagem + 1)
    try:
        # O execve substitui o processo: sem fechar o painel antes, o processo
        # NOVO herdaria um terminal em modo alternativo, sem cursor.
        from executor import dashboard
        dashboard.emergency_stop()
        sys.stdout.flush()
        sys.stderr.flush()
        os.execve(argv[0], argv, env)
    except Exception as exc:
        logger.error("Falha ao reiniciar automaticamente (%s) — encerrando.", exc)


# NOTE: register_public_key_if_needed foi removido. A chave publica X25519 e
# enviada agora no enrollment (POST /executores/enroll) junto com o CSR Ed25519.
# Re-enrollment exige novo OTP — nao ha auto-registro silencioso.


def _observar_task(task: asyncio.Task) -> None:
    """Loga em ERROR se a task de background morrer com excecao.

    Task criada e nunca observada morre em silencio: um FileNotFoundError trivial
    matava a sincronizacao de uma pasta e nada aparecia nos logs — o
    `gather(..., return_exceptions=True)` do shutdown ainda CONSUMIA a excecao,
    entao nem o "Task exception was never retrieved" do asyncio surgia.
    """
    def _callback(t: asyncio.Task) -> None:
        if t.cancelled():
            return  # cancelamento e o caminho normal de shutdown
        exc = t.exception()
        if exc is not None:
            logger.error(
                "Task de background '%s' terminou com excecao: %s",
                t.get_name(), exc, exc_info=exc,
            )

    task.add_done_callback(_callback)


# Sentinela de "conte a fila inteira, sem discriminar run". Precisa ser um
# objeto proprio porque `None` e um run_id legitimo: e o balde dos eventos que
# nao pertencem a job nenhum (GeoSync).
_QUALQUER_RUN = object()


class _FilaContada(asyncio.Queue):
    """asyncio.Queue que conta itens ENFILEIRADOS e ENVIADOS, por run.

    Existe para medir progresso REAL do consumidor. O `qsize` nao serve: numa
    fila compartilhada por N jobs e pelo GeoSync ele sobe e desce por producao
    alheia — com um produtor mais rapido que o sender o qsize NUNCA diminui,
    ainda que o WebSocket esteja perfeitamente vivo. Foi assim que a barreira de
    node_events passou a desistir em 3s acusando "sem conexao" e a despachar o
    job_result antes dos eventos do proprio job.

    DUAS decisoes que o nome "confirmados" ja escondeu uma vez:

      1. `confirmados` avanca em `confirmar_envio()`, chamado pelo sender APENAS
         quando o `ws.send` retornou. Antes ele estava colado no `task_done()`,
         que e incondicional (o item pode ter sido re-enfileirado ou descartado
         por teto de tentativas): a barreira dava por "enviado" o que tinha
         FALHADO e despachava o job_result — carregando o `__workflow_complete__`
         — na frente dos eventos que ela existe para esperar.

      2. A contagem e POR run_id, nao so global. A fila e compartilhada: esperar
         a marca d'agua global fazia um workflow curto esperar o backlog de um
         workflow grande e do GeoSync antes de subir o proprio resultado.

    O `sink` opcional espia cada item de passagem — e por ele que o painel
    descobre em que no cada run esta e quanto o GeoSync ja transferiu. Espiar
    aqui, e nao nos emissores, e um ponto de toque em vez de dois
    (ExecutorEventPublisher e SyncEventEmitter ja convergem nesta fila) e pega
    de graca qualquer emissor futuro. Nada e consumido: o
    `_event_sender_loop` continua recebendo tudo.

    O `coletor` guarda o ultimo lifecycle por no que NAO conseguiu ser enviado,
    para o sender reenviar na reconexao (ver ColetorDeLifecycle). Mora na fila
    porque ela e o unico objeto que produtor (ExecutorEventPublisher) e
    consumidor (ExecutorConnection) ja compartilham.
    """

    def __init__(self, maxsize: int = 0, sink=None):
        super().__init__(maxsize)
        self.enfileirados: int = 0
        self.confirmados:  int = 0
        self.enfileirados_por_run: dict = {}
        self.confirmados_por_run:  dict = {}
        self._sink = sink
        from executor.event_publisher import ColetorDeLifecycle
        self.coletor = ColetorDeLifecycle()

    @staticmethod
    def _run_de(item) -> object:
        return item.get("run_id") if isinstance(item, dict) else None

    def _put(self, item):
        self.enfileirados += 1
        run_id = self._run_de(item)
        self.enfileirados_por_run[run_id] = self.enfileirados_por_run.get(run_id, 0) + 1
        if self._sink is not None:
            try:
                self._sink.on_event(item)
            except Exception:
                # Telemetria NUNCA derruba o publisher: esta excecao subiria
                # pelo call_soon_threadsafe do event_publisher, que roda fora
                # de qualquer try/except do caller.
                pass
        super()._put(item)

    def confirmar_envio(self, item) -> None:
        """Marca que o item SAIU de fato pelo WebSocket. So o sender chama."""
        self._resolver(item)

    def resolver_sem_envio(self, item) -> None:
        """Fecha a conta de um item que saiu da fila SEM ter sido enviado.

        Sao dois casos, e os dois desbalanceavam a marca d'agua:

          - re-enfileiramento: o `_put` conta o item DE NOVO (`enfileirados +1`)
            mas `confirmar_envio` so acontece no envio bem-sucedido. Cada
            retentativa deixava um deficit permanente de 1 naquele run, e a
            barreira de fim de job — que espera `confirmados >= alvo` — nunca
            fechava: saia sempre pelo timeout de estagnacao, atrasando o
            `job_result` (e o `__workflow_complete__`) em segundos;
          - descarte definitivo (teto de tentativas, fila cheia no requeue): o
            item foi contado na entrada e nunca sera enviado — sem contrapeso,
            `alvo` fica inalcancavel para sempre.

        Nos dois casos a entrada ANTERIOR do item esta encerrada; se ele voltar
        para a fila, ele volta como item novo e e contado de novo no `_put`.
        """
        self._resolver(item)

    def _resolver(self, item) -> None:
        self.confirmados += 1
        run_id = self._run_de(item)
        self.confirmados_por_run[run_id] = self.confirmados_por_run.get(run_id, 0) + 1

    def esquecer_run(self, run_id) -> None:
        """Expurga os contadores de um run terminado.

        Sem isto os dois dicts crescem para sempre num executor de vida longa —
        uma entrada por run executado.
        """
        self.enfileirados_por_run.pop(run_id, None)
        self.confirmados_por_run.pop(run_id, None)
        # O coletor guarda lifecycle por (run_id, no) para reenviar depois. Sem
        # este expurgo, um reenvio horas mais tarde ressuscitava as entradas
        # por-run que acabamos de apagar — e nada as removeria de novo,
        # reabrindo o vazamento O(runs) pela porta dos fundos.
        coletor = getattr(self, "coletor", None)
        if coletor is not None:
            coletor.esquecer_run(run_id)


async def _aguardar_confirmacao(
    fila: _FilaContada,
    *,
    rotulo: str,
    timeout: float,
    estagnado: float,
    run_id=_QUALQUER_RUN,
) -> bool:
    """Espera o consumidor enviar tudo que JA estava na fila. True = enviou.

    Barreira por MARCA D'AGUA: fotografa `enfileirados` e espera `confirmados`
    alcancar essa marca. Como a fila e FIFO com um unico consumidor, isso e
    exatamente "todos os itens que existiam neste instante ja foram enviados" —
    sem esperar pelo que outros produtores enfileirarem depois (era o defeito do
    `join()` global, que fazia o job A esperar pelos eventos do job B) e sem
    cortar cedo enquanto houver sender vivo progredindo.

    Com `run_id`, a marca d'agua e a DAQUELE run: o job so espera os proprios
    eventos, e nao o backlog que outro job ou o GeoSync ja tinham enfileirado a
    frente dele na mesma fila.

    Desiste em dois casos:
      - `estagnado` segundos sem NENHUMA confirmacao na fila INTEIRA — nao ha
        consumidor (WS caido, sender cancelado, executor em reconexao com
        backoff);
      - `timeout` total, teto do pior caso mesmo com um sender lento.

    A assimetria entre alvo e detector e proposital: "quanto falta" e uma
    propriedade DESTE run, mas "o sender esta vivo" e uma propriedade da FILA.
    Medir estagnacao pelo contador por-run acusava sender morto com o WebSocket
    perfeitamente vivo: a fila e FIFO unica e compartilhada, entao os eventos de
    um job curto ficam fisicamente atras do backlog de um workflow grande e do
    GeoSync. Enquanto o sender drenava esse backlog (facil passar de 3s num link
    de upload de cliente), `confirmados_por_run` do job curto nao saia do lugar,
    a barreira retornava False e o `job_result` — que carrega o
    `__workflow_complete__` — era despachado na frente dos proprios node_events
    do run, fechando o canvas com os nos girando.
    """
    if run_id is _QUALQUER_RUN:
        enfileirados = lambda: fila.enfileirados          # noqa: E731
        confirmados  = lambda: fila.confirmados           # noqa: E731
    else:
        enfileirados = lambda: fila.enfileirados_por_run.get(run_id, 0)   # noqa: E731
        confirmados  = lambda: fila.confirmados_por_run.get(run_id, 0)    # noqa: E731

    # Sempre GLOBAL: e a evidencia de que existe um consumidor drenando.
    progresso_global = lambda: fila.confirmados                            # noqa: E731

    agora  = asyncio.get_running_loop().time
    limite = agora() + timeout
    alvo   = enfileirados()
    marca  = progresso_global()
    ultimo_progresso = agora()

    while confirmados() < alvo:
        await asyncio.sleep(0.05)
        if progresso_global() > marca:
            marca = progresso_global()
            ultimo_progresso = agora()
        pendentes = alvo - confirmados()
        if pendentes <= 0:
            break
        if agora() - ultimo_progresso >= estagnado:
            logger.warning(
                "Nenhum %s confirmado em %.0fs — consumidor parado (WS caido ou "
                "sender encerrado); %d pendente(s) seguem para o proximo envio.",
                rotulo, estagnado, pendentes,
            )
            return False
        if agora() >= limite:
            logger.warning(
                "Timeout de %.0fs drenando %s — %d pendente(s) seguem para o "
                "proximo envio.",
                timeout, rotulo, pendentes,
            )
            return False
    return True


async def _drenar_eventos_pendentes(
    fila: _FilaContada,
    run_id=_QUALQUER_RUN,
    timeout: float = 30.0,
    estagnado: float = 3.0,
) -> None:
    """Espera os node_events ja emitidos subirem antes de despachar o resultado.

    O `__workflow_complete__` viaja junto do job_result; sem esta barreira ele
    chegava antes dos node_events do proprio job e a UI fechava o run com o
    grafo congelado/incompleto.

    A espera cobre exatamente os eventos DESTE run que existiam quando o job
    terminou (ver `_aguardar_confirmacao`) — nao os de outros jobs, nem os do
    GeoSync, que dividem a mesma fila.
    """
    # ExecutorEventPublisher enfileira via `call_soon_threadsafe` (publica de
    # dentro de asyncio.to_thread): os ultimos eventos do job ainda estao na fila
    # de callbacks do loop, nao na _event_queue. Ceder o controle uma vez faz
    # esses callbacks rodarem antes de fotografarmos a marca d'agua — sem isso a
    # barreira sairia justamente sem os eventos finais que ela existe para cobrir.
    await asyncio.sleep(0)
    await _aguardar_confirmacao(
        fila, rotulo="node_event", timeout=timeout, estagnado=estagnado, run_id=run_id,
    )


async def _drive_event_fanout(
    entrada: asyncio.Queue,
    managers: list,
    filas: list[asyncio.Queue],
) -> None:
    """Roteia cada drive_event recebido do servidor para o SyncManager dono da pasta.

    Contrato com executor/sync/manager.py: o manager expoe o metodo SINCRONO
    `claims_event(msg) -> bool`, que responde True quando o evento pertence a
    pasta dele. Se ninguem reivindicar, o evento vai para o PRIMEIRO manager (o
    "primario") — e o caso do arquivo novo, que ainda nao esta em manifesto
    nenhum. `getattr` porque o metodo pode nao existir ainda: ausencia conta
    como "nao reivindica" em vez de quebrar o roteamento.
    """
    while True:
        msg = await entrada.get()
        try:
            destino = 0
            for i, sm in enumerate(managers):
                claims = getattr(sm, "claims_event", None)
                if claims is None:
                    continue
                try:
                    if claims(msg):
                        destino = i
                        break
                except Exception as exc:
                    logger.warning(
                        "claims_event de '%s' falhou (%s) — ignorando este manager no roteamento.",
                        getattr(sm, "sync_dir", "?"), exc,
                    )
            try:
                filas[destino].put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning(
                    "Fila de drive_events de '%s' cheia — evento '%s' descartado.",
                    getattr(managers[destino], "sync_dir", "?"), msg.get("action", "?"),
                )
        finally:
            entrada.task_done()



def _causa_da_interrupcao(estado: str, limite_bytes: int | None) -> str:
    """Texto do resultado de um job que o processo anterior não terminou.

    O executor não sabe POR QUE morreu — o Docker zera o OOMKilled no restart —,
    então diz o que sabe (reiniciou, e em que ponto do job) e a causa mais
    provável, com o limite de memória do container para quem for investigar.
    """
    from executor import result_store

    if estado == result_store.ESTADO_NA_FILA:
        base = (
            "O executor foi encerrado antes de começar esta execução — o processo "
            "ou o container reiniciou enquanto ela esperava na fila."
        )
    else:
        base = (
            "O executor foi encerrado no meio desta execução e ela não terminou — "
            "o processo ou o container reiniciou."
        )
    if limite_bytes:
        gb = f"{limite_bytes / 1024 ** 3:.1f}".replace(".", ",")
        return f"{base} A causa mais comum é falta de memória: o limite do container é de {gb} GB."
    return f"{base} A causa mais comum é falta de memória na máquina."


def _fechar_orfaos_do_boot_anterior() -> int:
    """Transforma em falha, com a causa provável, cada job que o processo
    anterior aceitou e não terminou. Devolve quantos.

    Sem isto o servidor seguia com o run "Em andamento": o executor voltava em
    segundos (restart: on-failure), reconectava dentro da carência do servidor
    e ninguém mais sabia do job — foi o que aconteceu com um executor
    morto pelo OOM do cgroup no meio de uma análise.

    Best-effort: falha aqui é logada e o boot segue.
    """
    from executor import result_store

    if not result_store.tomar_posse_do_diario():
        logger.warning(
            "Outro processo do executor ainda usa este outbox (o anterior drenando?) — "
            "os jobs do diário são dele; nenhum foi convertido em falha."
        )
        return 0
    try:
        orfaos = result_store.carregar_em_voo()
    except Exception as exc:
        logger.warning("Falha ao ler o diário de jobs do boot anterior: %s", exc)
        return 0
    if not orfaos:
        return 0
    from executor.sysinfo import _get_cgroup_ram_total
    limite = _get_cgroup_ram_total()
    for orfao in orfaos:
        result_store.put({
            "job_id":         orfao["job_id"],
            "run_id":         orfao["job_id"],
            "status":         "error",
            "error":          _causa_da_interrupcao(orfao["estado"], limite),
            "error_category": "executor_lost",
        })
    logger.warning(
        "%d job(s) do processo anterior não terminaram (reinício abrupto) — "
        "reportados como falha: %s",
        len(orfaos), [o["job_id"] for o in orfaos],
    )
    return len(orfaos)

async def main():
    # Configuracao e enrollment sao pre-requisitos, nao algo que o executor
    # resolva sozinho ao subir. Aqui havia um wizard interativo que rodava
    # quando faltava EXECUTOR_ID; ele foi removido junto com executor/setup.py.
    #
    # Motivo: `input()` nao existe em nenhum dos ambientes em que o executor
    # roda de verdade — container sem -it, servico, e o app desktop, que da
    # spawn com os pipes capturados. O wizard so funcionava no terminal do
    # desenvolvedor, e nos demais estourava EOFError no lugar da mensagem util.
    #
    # Os caminhos que restam funcionam em todos eles:
    #   python -m executor enroll --executor-id=<ID> --otp=<OTP> --server=<URL>
    #   o formulario de vinculo do app desktop
    #
    # A checagem de fato acontece em `config.assert_configured()` /
    # `assert_enrolled()`, mais abaixo — DEPOIS de o canal com o supervisor
    # subir, para que a falha vire evento em vez de codigo de saida.
    from executor import config

    from executor.job_executor import execute_job, init_private_key
    from executor.job_queue import ExecutorJobQueue
    from executor.connection import ExecutorConnection
    from executor import dashboard, result_store
    from executor.stats import ExecutorStats, NullStats

    # ── Painel: decide cedo, liga tarde ───────────────────────────────────────
    # A decisao vem ja, para que as filas e a conexao nascam com o coletor certo.
    # O `Live` so assume a tela no passo 7 — o boot inteiro (banner, chave do
    # servidor, replay do outbox, erros de GeoSync) precisa sair no console
    # normal, que e onde o operador espera ver o que deu errado ao subir.
    #
    # Excecao a "liga tarde": no modo JSON o canal sobe JA, logo abaixo. O
    # consumidor e um programa, nao a tela — e um erro na fase 0 (chave do
    # servidor, cert) precisa chegar a ele como um evento `state`, e nao como
    # "o processo saiu com codigo 1".
    _dash_modo, _dash_motivo = dashboard.should_enable_from_process()
    _dash_on = _dash_modo != dashboard.MODO_OFF
    stats = (
        ExecutorStats(
            executor_id=config.EXECUTOR_ID,
            version=config.EXECUTOR_VERSION,
            server_url=config.SERVER_URL,
        )
        if _dash_on else NullStats()
    )

    # ── Banner ────────────────────────────────────────────────────────────────
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║       Atlans Executor v%s                ║", config.EXECUTOR_VERSION)
    logger.info("╚══════════════════════════════════════════╝")
    logger.info("  Executor ID:  %s", config.EXECUTOR_ID)
    logger.info("  Servidor:  %s", config.SERVER_URL)
    logger.info("  Workers:   %d  |  Fila: %d  |  Timeout: %ds", config.MAX_CONCURRENT, config.MAX_QUEUE_SIZE, config.JOB_TIMEOUT)
    if config.SYNC_DIRS.strip():
        logger.info("  GeoSync:   %s", config.SYNC_DIRS)
    if not _dash_on:
        # Um painel que nao aparece sem explicacao vira ticket de suporte.
        logger.info("  Painel:    desligado (%s)", _dash_motivo)
    logger.info("")

    from executor.sysinfo import _collect_system_info
    stats.system = _collect_system_info() or {}
    stats.sync_dirs = tuple(
        d.strip() for d in config.SYNC_DIRS.split(",") if d.strip()
    )

    # ── Canal com o supervisor (modo JSON) ────────────────────────────────────
    # Sobe ANTES da fase 0. O `shutdown_event` nasce aqui, e nao na fase 5, por
    # causa disso: o comando `shutdown` precisa funcionar durante o boot inteiro
    # — um app desktop que pede para parar enquanto o executor resolve a chave
    # do servidor nao pode ficar sem resposta ate a fase 5.
    shutdown_event = asyncio.Event()

    # A conexao so existe na fase 4. Ate la, `reconnect` e um no-op honesto: nao
    # ha backoff para interromper. O holder evita ter de religar o handler
    # depois, o que seria mais uma ordem sutil a manter correta.
    _conn_holder: dict = {}

    def _reconectar_agora() -> bool:
        conn_ = _conn_holder.get("conn")
        return bool(conn_.reconectar_agora()) if conn_ is not None else False

    _dash = None
    if _dash_modo == dashboard.MODO_JSON:
        _dash = await dashboard.start(
            stats,
            modo=dashboard.MODO_JSON,
            # Ligadas na fase 3 por `vincular_fontes`: a fila ainda nao existe.
            capacity_source=None,
            result_queue=None,
            intervalo=config.DASHBOARD_INTERVAL,
            ao_sair=shutdown_event.set,
            ao_reconectar=_reconectar_agora,
        )

    def _fase(nome: str, passo: str | None = None, detalhe: str | None = None) -> None:
        """Reporta a fase do boot ao supervisor. No-op sem canal.

        Sem isto, uma falha na fase 0 chega ao app desktop apenas como "o
        processo saiu com 1" — e a diferenca entre "cert expirado" e "sem rede"
        vira suporte por telefone.
        """
        if _dash is not None and hasattr(_dash, "emitir"):
            _dash.emitir("state", {"phase": nome, "step": passo, "detail": detalhe})

    async def _falhar_boot(passo: str, exc: BaseException) -> None:
        """Reporta a falha e encerra com 1.

        Sem isto, uma falha de boot chega ao supervisor so como codigo de saida.
        A diferenca entre "cert expirado" e "sem rede" e a diferenca entre a UI
        oferecer 'refazer enrollment' e oferecer 'tentar de novo' — e o passo
        exato so existe aqui.
        """
        _fase("failed", passo, detalhe=str(exc))
        if _dash is not None and _dash_modo == dashboard.MODO_JSON:
            await _dash.stop()          # drena o buffer antes de o processo sumir
        raise SystemExit(1)

    # ── Watchdog do supervisor (anti-orfao) ───────────────────────────────────
    from executor import supervisor as _supervisor
    _watchdog_task = _supervisor.criar_task(shutdown_event.set)

    # ── Configuracao e enrollment ─────────────────────────────────────────────
    # Estas checagens rodam DEPOIS de o canal subir, e nao antes.
    #
    # Ficavam la em cima, logo apos o import de config, e o efeito era ruim para
    # um supervisor: o processo saia com 1 sem emitir evento nenhum, entao o app
    # nao tinha como distinguir "falta enrollment" de "o executor caiu" — e
    # tratava como queda, religando em backoff para sempre uma condicao que so o
    # usuario resolve.
    #
    # Os dois passos sao separados porque a acao do usuario e diferente:
    # `config` pede configurar o EXECUTOR_ID, `enrollment` pede refazer o enroll.
    _fase("booting", "config")
    try:
        config.assert_configured()
    except SystemExit as exc:
        logger.error("%s", exc)     # a mensagem so aparecia por ser SystemExit
        await _falhar_boot("config", exc)
    try:
        config.assert_enrolled()
    except SystemExit as exc:
        logger.error("%s", exc)
        await _falhar_boot("enrollment", exc)

    _fase("booting", "server_key")

    # ── 0. Chave de assinatura do servidor (fixada localmente) ───────────────
    # Antes isto era um GET a cada boot, sem pinning e com follow_redirects=True:
    # quem vencesse o canal em qualquer reinicio entregava a propria chave e
    # passava a assinar jobs arbitrarios. Agora a chave vem do enroll (sem janela
    # nenhuma) ou de um TOFU unico que fica fixado em disco.
    # Ver executor/server_key.py para a ordem de precedencia completa.
    from executor.server_key import ServerKeyError, resolve_server_signing_key
    try:
        config.SERVER_SIGNING_PUBLIC_KEY = await resolve_server_signing_key(
            config.EXECUTOR_CERT_DIR, config.SERVER_URL,
        )
    except ServerKeyError as exc:
        logger.error(
            "Chave de assinatura do servidor indisponivel — o executor NAO sobe sem "
            "ela (rodar sem verificacao de assinatura aceitaria job de qualquer "
            "origem).\n%s", exc,
        )
        await _falhar_boot("server_key", exc)

    # ── 1. Inicializa chave privada X25519 (envelope decryption) ──────────────
    # init_private_key() carrega a chave via `crypto.load_private_key` (SOMENTE
    # leitura) e a guarda no global do job_executor. A chave foi gerada uma unica
    # vez no enrollment e salva em config.EXECUTOR_PRIVATE_KEY_PATH — se sumiu,
    # gerar outra faria o executor subir "online" com uma publica que nao casa
    # com a registrada no servidor e derrubar 100% dos jobs. Ver
    # crypto.PrivateKeyMissingError.
    from executor.crypto import PrivateKeyMissingError
    try:
        init_private_key()
    except PrivateKeyMissingError as exc:
        # Mesmo tratamento do ServerKeyError acima: a excecao existe justamente
        # para dar instrucao clara ao operador (refazer o enroll) — enterra-la
        # num traceback cru anularia o proposito dela.
        logger.error("%s", exc)
        await _falhar_boot("private_key", exc)

    # ── 2. Pool de threads proprio ────────────────────────────────────────────
    # Todo `asyncio.to_thread` do flow engine cai no executor DEFAULT do loop,
    # dimensionado em min(32, cpu_count + 4). Dois problemas: (a) N jobs
    # concorrentes disputam o mesmo pool sem nenhuma relacao com MAX_CONCURRENT;
    # (b) em Docker, cpu_count() reporta os cores do HOST, nao a quota do
    # container — o pool fica gigante e as threads so brigam por CPU.
    # Dimensionar a partir de MAX_CONCURRENT da a cada job uma folga previsivel.
    loop = asyncio.get_running_loop()
    _thread_pool = ThreadPoolExecutor(
        max_workers=max(8, config.MAX_CONCURRENT * 4),
        thread_name_prefix="atlas-exec",
    )
    loop.set_default_executor(_thread_pool)

    # ── 3. Cria filas de comunicação ──────────────────────────────────────────
    # Fila de resultados (executor → servidor). Precisa de LIMITE: sem WS vivo
    # ninguem drena, e cada resultado retido segura memoria ate o proximo envio.
    # Dimensionada pelo pior caso legitimo — tudo que pode estar em voo (fila +
    # jobs rodando) mais folga para o replay do outbox no boot.
    _result_queue = _FilaContada(
        maxsize=config.MAX_QUEUE_SIZE + config.MAX_CONCURRENT + 32
    )
    # Fila de eventos de nós (ExecutorEventPublisher → connection → servidor).
    # O `sink` do painel espia de passagem; com o painel off e um NullStats.
    _event_queue = _FilaContada(maxsize=500, sink=stats if _dash_on else None)
    # Fila de eventos Drive push (servidor → executor via WebSocket). É a fila de
    # ENTRADA: o fan-out abaixo distribui para a fila própria de cada SyncManager.
    _drive_event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    def _enqueue_result(result: dict) -> None:
        """Enfileira um resultado para o sender sem NUNCA bloquear.

        `await put()` numa fila cheia prenderia o worker do job indefinidamente
        quando o WS esta caido (ninguem drena). Se estourar, o resultado ja esta
        persistido no result_store (outbox) — mas logamos em ERROR porque o envio
        imediato foi perdido: descartar em silencio deixaria o run "running" no
        servidor sem nenhuma pista.

        Cuidado com a promessa do log: o replay do outbox REENVIA, mas o servidor
        RECUSA (`_is_run_terminal` em executor_ws_router) tudo que chegar depois
        de `_fail_orphan_runs_if_gone` ter fechado o run como orfao — e a fila so
        enche quando o WS ja esta fora ha bastante tempo, exatamente o cenario em
        que os runs ja foram fechados. Nao prometa recuperacao aqui.
        """
        try:
            _result_queue.put_nowait(result)
        except asyncio.QueueFull:
            logger.error(
                "Fila de resultados cheia (%d) — job '%s' nao sera enviado agora. "
                "O resultado fica no outbox e sera reenviado no proximo start, mas "
                "o servidor o recusa se ja tiver fechado o run como orfao.",
                _result_queue.qsize(), result.get("job_id", "?"),
            )

    async def on_execute(message: dict):
        """Executa o job e envia resultado ao servidor via WebSocket."""
        # Ponto UNICO por onde todo job passa — e por isso o lugar natural de
        # medir. A duracao daqui e ponta-a-ponta (inclui a barreira de eventos).
        job_id = message.get("envelope", {}).get("job_id", "?")
        _t0 = time.monotonic()
        # run_id == job_id no despacho do servidor (ver job_executor.execute_job).
        # Informar isso ja aqui e o que permite casar os node events com o job
        # certo: sem ele, com MAX_CONCURRENT jobs simultaneos todos comecariam
        # sem run_id e o primeiro evento a chegar seria atribuido a qualquer um.
        stats.on_job_started(job_id, run_id=job_id)
        # Diário: o job saiu da fila e começou. Se o processo morrer daqui até o
        # `result_store.put`, o próximo boot o reporta como interrompido no meio.
        result_store.marcar_executando(job_id)
        result = None
        status = "error"
        try:
            result = await execute_job(message, event_queue=_event_queue)
            status = result.get("status", "error")
            # A barreira e POR RUN: com a fila compartilhada, esperar a marca
            # d'agua global fazia este job esperar tambem o backlog de um
            # workflow grande e do GeoSync — ate 30s de "quase pronto" no painel.
            await _drenar_eventos_pendentes(_event_queue, result.get("run_id") or job_id)
            # 'output' carrega os final_outputs INTEIROS (GeoDataFrames, centenas de
            # MB). O servidor nunca usa esse campo — o sender ja o descartava na hora
            # de serializar — mas ate la ele mantinha vivo todo o grafo de objetos
            # dentro da fila e do outbox. Fora aqui, na origem.
            result.pop("output", None)
            # Persiste o resultado ANTES de enfileirar — garante que reinício do
            # processo não perde o envio. mark_sent() é chamado pelo sender loop
            # após o servidor confirmar.
            result_store.put(result)
            _enqueue_result(result)
        except asyncio.CancelledError:
            # Cancelamento do job (job_queue.cancel) ou do worker (shutdown).
            # Sem este ramo o `finally` contaria a interrupcao como erro.
            status = "cancelled"
            raise
        finally:
            # Contadores por run sao O(runs) e nada os apaga sozinho: sem este
            # expurgo, um executor de vida longa acumula uma entrada por job
            # executado nos dois dicts.
            _event_queue.esquecer_run((result or {}).get("run_id") or job_id)
            stats.on_job_finished(
                job_id, status, time.monotonic() - _t0,
                run_id=(result or {}).get("run_id"),
                metrics=((result or {}).get("stats") or {}).get("__metrics__"),
            )

    # Espaco maximo que o replay do outbox pode ocupar na _result_queue. O resto
    # fica reservado para os resultados dos jobs que estao rodando AGORA — eles
    # usam put_nowait e seriam DESCARTADOS se o backlog historico enchesse a fila.
    _RESERVA_OUTBOX = 8

    async def _replay_outbox() -> None:
        """Reenvia, em ritmo do sender, os resultados que ficaram do boot anterior.

        Antes isto era um for síncrono com put_nowait ANTES de a conexao existir:
        com a fila limitada (86 slots no default) e `load_pending()` sem LIMIT, um
        outbox com 300 linhas perdia 214 delas em ERROR — e como o outbox so e
        lido no boot, so drenava a 86 por reinicio. Aqui o replay vira task de
        background que espera espaco: nada e descartado e nada compete com os
        jobs vivos.

        Best-effort: qualquer falha e engolida com log — replay nunca pode
        impedir o executor de operar.
        """
        try:
            pending = await asyncio.to_thread(result_store.load_pending)
        except Exception as exc:
            logger.warning("Falha ao restaurar resultados pendentes (ignorando): %s", exc)
            return
        if not pending:
            return

        logger.info("Restaurando %d resultado(s) pendente(s) de execucoes anteriores.", len(pending))
        for r in pending:
            # Sem await entre a checagem e o put: put_nowait nao tem como falhar.
            while _result_queue.qsize() >= _RESERVA_OUTBOX:
                await asyncio.sleep(0.2)
            _result_queue.put_nowait(r)

    async def on_cancelled(message: dict):
        """Reporta ao servidor que o job foi cancelado.

        Sem isto o run ficaria "running" para sempre: a task interrompida nunca
        chega a produzir resultado, e o servidor só sabe que algo mudou quando
        recebe um job_result.
        """
        envelope = message.get("envelope", {})
        job_id = envelope.get("job_id", "?")
        # `cancel_reason` vem da job_queue quando o cancelamento NAO partiu do
        # usuario (ex: job que ainda estava na fila quando o executor encerrou).
        # Sem ele o operador via "cancelada pelo usuario" para algo que ninguem
        # cancelou. Sem 'output': o servidor nao usa e so ocuparia memoria/outbox.
        motivo = message.get("cancel_reason") or "Execução cancelada pelo usuário."
        # O servidor despacha com run_id == job_id (ver job_executor.execute_job).
        result = {
            "job_id": job_id,
            "run_id": job_id,
            "status": "cancelled",
            "error": motivo,
        }
        result_store.put(result)
        _enqueue_result(result)
        # Cobre o job cancelado ANTES de comecar (drenado da fila no shutdown):
        # esse nunca passa pelo on_execute, entao nao seria contado em lugar
        # nenhum. Se ja estava rodando, o `finally` do on_execute contou — e o
        # on_job_cancelled do coletor ignora o id que ja saiu.
        stats.on_job_cancelled(job_id, motivo)

    job_queue = ExecutorJobQueue(
        on_execute=on_execute,
        max_concurrent=config.MAX_CONCURRENT,
        max_queue_size=config.MAX_QUEUE_SIZE,
        on_cancelled=on_cancelled,
    )
    await job_queue.start()

    # ── 4. Conecta ao servidor ────────────────────────────────────────────────
    # `thread_pool`: a conexao precisa dele para reportar capacidade honesta —
    # queued/running contam JOBS e nao enxergam threads presas por um no que o
    # timeout nao consegue cancelar. Ver ExecutorConnection._pool_saturado.
    conn = ExecutorConnection(job_queue, _result_queue, event_queue=_event_queue,
                           drive_event_queue=_drive_event_queue, stats=stats,
                           thread_pool=_thread_pool)

    # A fila avisa a conexao no instante em que entra em drenagem, para o
    # capacity saturado sair na hora em vez de esperar o tick de 10s do
    # _capacity_loop (ver ExecutorJobQueue.shutdown e conn.push_capacity).
    # Ligado aqui porque a fila e construida ANTES da conexao — ela e argumento
    # do construtor dela.
    job_queue.set_on_draining(conn.push_capacity)

    # Agora o canal com o supervisor tem de onde ler capacidade, e o comando
    # `reconnect` passa a ter efeito.
    _conn_holder["conn"] = conn
    if _dash is not None and hasattr(_dash, "vincular_fontes"):
        _dash.vincular_fontes(capacity_source=job_queue.get_capacity,
                              result_queue=_result_queue)
    _fase("booting", "connection")

    # ── 5. Shutdown gracioso ──────────────────────────────────────────────────
    # O `shutdown_event` foi criado la em cima, antes da fase 0, para que o
    # comando `shutdown` do supervisor funcione durante o boot inteiro.

    def _on_signal():
        logger.info("Sinal de shutdown recebido — encerrando...")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except NotImplementedError:
            # Windows não suporta add_signal_handler em asyncio
            pass

    # ── 6. GeoSync — sincronizacao de pastas locais ────────────────────────────
    sync_tasks = []
    # Declarada fora de TODOS os `if` abaixo: `_sincronizar_agora` (mais adiante) fecha
    # sobre ela e e chamada pelo botao "Sincronizar agora" da UI. Com
    # EXECUTOR_SYNC_DIRS vazio o nome nunca era ligado, e a closure levantava
    # NameError no caso mais comum de todos — executor sem GeoSync configurado —
    # em vez de devolver o 0 que a UI usa para dizer "nao ha pasta configurada".
    _sync_managers: list = []
    if config.SYNC_DIRS.strip():
        from executor.sync.manager import SyncManager

        # Resolver workspace_id: .env > API (auto-detecção com validação)
        _sync_ws_id = config.WORKSPACE_ID
        _workspaces: list = []

        # Sempre consulta a API para obter workspaces acessiveis (mTLS confere identidade).
        try:
            from executor.utils import ws_to_http, mtls_httpx_kwargs
            base_url = ws_to_http(config.SERVER_URL)
            async with httpx.AsyncClient(timeout=15, follow_redirects=True, **mtls_httpx_kwargs(base_url)) as _c:
                _r = await _c.get(f"{base_url}/executores/{config.EXECUTOR_ID}/status")
                if _r.status_code == 200:
                    _agent_data = _r.json()
                    _workspaces = _agent_data.get("workspaces", [])
        except Exception as _exc:
            logger.warning("GeoSync: falha ao consultar status do executor: %s", _exc)

        if _sync_ws_id:
            # EXECUTOR_WORKSPACE_ID definido — valida que está na lista de workspaces acessíveis
            _accessible_ids = [w["id_hash"] for w in _workspaces]
            if _accessible_ids and _sync_ws_id not in _accessible_ids:
                logger.error(
                    "GeoSync desabilitado: workspace '%s' nao esta acessivel a este executor. "
                    "Verifique EXECUTOR_WORKSPACE_ID ou a configuracao de workspace no servidor.",
                    _sync_ws_id,
                )
                _sync_ws_id = None
            else:
                logger.info("GeoSync: workspace_id definido via .env: %s", _sync_ws_id)
        else:
            # Auto-detecção: só se a API retornar exatamente 1 workspace
            if len(_workspaces) == 1:
                _sync_ws_id = _workspaces[0]["id_hash"]
                logger.info(
                    "GeoSync: workspace auto-detectado: %s (%s)",
                    _workspaces[0].get("name", ""), _sync_ws_id,
                )
            elif len(_workspaces) > 1:
                logger.warning(
                    "GeoSync desabilitado: executor tem %d workspaces vinculados. "
                    "Defina EXECUTOR_WORKSPACE_ID no .env para ativar o GeoSync.",
                    len(_workspaces),
                )
            elif not _workspaces:
                logger.warning(
                    "GeoSync desabilitado: executor nao tem workspaces acessiveis "
                    "ou e do tipo default. Defina EXECUTOR_WORKSPACE_ID no .env ou "
                    "vincule um workspace ao executor no servidor.",
                )

        if _sync_ws_id:
            # Uma fila POR SyncManager. Antes todos recebiam a MESMA fila, e
            # `Queue.get()` acorda apenas UM waiter: com N pastas, cada
            # drive_event ia parar em 1 manager sorteado e os outros N-1 nunca o
            # viam. O fan-out abaixo e quem decide o destino.
            _sync_queues: list[asyncio.Queue] = []

            for sync_dir in config.SYNC_DIRS.split(","):
                sync_dir = sync_dir.strip()
                if not sync_dir:
                    continue
                sm_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
                sm = SyncManager(
                    sync_dir=sync_dir,
                    workspace_id=_sync_ws_id,
                    server_url=config.SERVER_URL,
                    executor_id=config.EXECUTOR_ID,
                    interval=config.SYNC_INTERVAL,
                    event_queue=_event_queue,
                    drive_event_queue=sm_queue,
                )
                _sync_managers.append(sm)
                _sync_queues.append(sm_queue)
                task = asyncio.create_task(sm.run(), name=f"geosync-{sync_dir}")
                _observar_task(task)
                sync_tasks.append(task)
                logger.info("GeoSync ativado: '%s' → workspace '%s'", sync_dir, _sync_ws_id)

            if _sync_managers:
                fanout = asyncio.create_task(
                    _drive_event_fanout(_drive_event_queue, _sync_managers, _sync_queues),
                    name="drive-event-fanout",
                )
                _observar_task(fanout)
                sync_tasks.append(fanout)

    # ── 6.5. Renewal automatico do cert mTLS (loop em background) ────────────
    from executor.renewal import renewal_loop
    renewal_task = asyncio.create_task(
        renewal_loop(config.SERVER_URL, config.EXECUTOR_CERT_DIR),
        name="cert-renewal",
    )

    # ── 7. Loop principal ─────────────────────────────────────────────────────
    # Órfãos do processo anterior viram resultado ANTES da conexão: entram no
    # outbox, saem pelo replay logo abaixo e já aparecem no primeiro inventário
    # como "resultado pendente" — o servidor não os fecha como perdidos.
    _fechar_orfaos_do_boot_anterior()

    conn_task = asyncio.create_task(conn.run(), name="executor-connection")

    # Replay do outbox SO depois de a conexao existir: ele se paga em ritmo do
    # _result_sender_loop e nao tem nada a fazer antes de haver sender.
    replay_task = asyncio.create_task(_replay_outbox(), name="outbox-replay")
    _observar_task(replay_task)

    # Painel: assume a tela agora, com o boot inteiro ja no scrollback. Daqui
    # para a frente o log passo-a-passo vai para o arquivo — `start()` devolve
    # None (e o console segue como estava) se o arquivo nao abrir.
    def _sincronizar_agora() -> int:
        """Acorda o ciclo de cada pasta do GeoSync. Devolve quantas responderam.

        Zero significa "nao ha GeoSync ativo" — pasta nao configurada, workspace
        ambiguo, ou o modo desligado. `json_runtime` transforma esse numero no
        `detalhe` do ack de `sync_now` ("N pasta(s) acordada(s)" ou "nenhuma
        pasta do GeoSync configurada").

        RESSALVA: o app desktop ainda NAO mostra esse detalhe. `window.atlas.
        comando()` resolve para o retorno de `Supervisor.enviar()`, que diz
        apenas se a escrita no stdin funcionou (desktop/src/main/index.ts), e o
        renderer imprime "Varredura solicitada." em qualquer caso
        (GeoSync.tsx). Levar o ack de volta ao renderer e trabalho na camada de
        IPC, nao aqui — mas o numero ja sai correto deste lado.

        Precisa ser definida ANTES do `dashboard.start` abaixo: ela e passada
        como argumento numa chamada que executa na hora, e defini-la depois
        tornava o nome uma local nao-ligada — `UnboundLocalError` no boot do
        modo RICH, que e o default de quem roda o executor num terminal.
        """
        return sum(1 for sm in _sync_managers if sm.sincronizar_agora())

    # O runtime JSON sobe antes da fase 0 e recebe o handler aqui, pela mesma
    # porta que ja usa para capacidade e fila. Sem isto, `sync_now` — o comando
    # que o app desktop dispara no botao "Sincronizar agora" — respondia sempre
    # "sem handler de sincronizacao": o handler so era entregue ao painel rich,
    # que o desktop nao usa.
    if _dash is not None and hasattr(_dash, "vincular_fontes"):
        _dash.vincular_fontes(ao_sincronizar=_sincronizar_agora)

    if _dash_modo == dashboard.MODO_RICH:
        _dash = await dashboard.start(
            stats,
            modo=dashboard.MODO_RICH,
            capacity_source=job_queue.get_capacity,
            result_queue=_result_queue,
            intervalo=config.DASHBOARD_INTERVAL,
            # A tecla 'q' entra pelo mesmo caminho de um SIGTERM: shutdown
            # ordenado, sem atalho. No Windows isso vale ainda mais, porque la
            # `add_signal_handler` nao registra nada e o Ctrl+C pode matar o
            # processo antes de qualquer `finally` rodar.
            ao_sair=shutdown_event.set,
            # Tecla 'r': corta o backoff de reconexao. Quem aperta sabe de algo
            # que o processo nao sabe — a rede voltou, o servidor subiu.
            ao_reconectar=conn.reconectar_agora,
            # "Sincronizar agora" da UI: acorda o ciclo do GeoSync sem esperar
            # o intervalo. Quem pede sabe de algo que o executor ainda nao viu.
            ao_sincronizar=_sincronizar_agora,
        )

    _fase("running")

    # Aguarda o QUE VIER PRIMEIRO: sinal do SO ou a conexao encerrar sozinha.
    #
    # Observar apenas o shutdown_event deixava o processo pendurado para sempre
    # sempre que o servidor encerrava a conexao (control revoked/shutdown/
    # config_changed, ou deny terminal 401/403/404): conn.run() retornava, o
    # conn_task terminava e ninguem percebia — executor vivo, desconectado e
    # sem reiniciar. Como restart_requested so e lido depois deste await, o
    # `sys.exit(1)` que dispara o restart do Docker nunca era alcancado.
    #
    # `revoked`/`shutdown` nao emitiam sinal algum (pendurava em qualquer SO) e
    # `config_changed` so emitia SIGTERM em POSIX (pendurava no Windows, onde
    # add_signal_handler nem chega a registrar o handler).
    stop_task = asyncio.create_task(shutdown_event.wait(), name="shutdown-signal")
    try:
        await asyncio.wait({stop_task, conn_task}, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        pass
    finally:
        stop_task.cancel()
        if _watchdog_task is not None:
            _watchdog_task.cancel()
        # O painel RICH sai ANTES do bloco 8, nao depois: o encerramento e
        # justamente quando o operador precisa ler o texto — "aguardando jobs
        # em andamento", resultados que ficaram para tras, traceback fatal. Com
        # o `Live` ainda no ar, a tela limparia e nada disso apareceria.
        #
        # O canal JSON faz o OPOSTO: fica de pe ate o fim do bloco 8. E durante
        # a drenagem que o supervisor mais precisa dele — e o que permite a UI
        # mostrar "3 jobs terminando" com numero real em vez de um spinner cego,
        # e distinguir encerramento ordenado de crash pelo `state: stopped`.
        if _dash is not None and _dash_modo == dashboard.MODO_RICH:
            await _dash.stop()
        _fase("draining")

    # ── 8. Shutdown ORDENADO ──────────────────────────────────────────────────
    # A ordem aqui e critica e estava invertida: o `conn_task.cancel()` vinha
    # ANTES do `job_queue.shutdown()`. Sem conexao nao existe _result_sender_loop,
    # entao nenhum resultado de job em andamento chegava ao servidor: ele marcava
    # os runs como orfaos (_fail_orphan_runs) e o replay do outbox no proximo boot
    # era recusado por idempotencia (_is_run_terminal). Acontecia em TODO deploy
    # com job em execucao.
    #
    # Correto: 1) terminar os jobs, 2) drenar os resultados pelo WS ainda vivo,
    # 3) so entao derrubar conexao, renewal e sync.
    # `job_queue.shutdown()` marca a fila como drenando LOGO na primeira linha, e
    # `get_capacity()` passa a anunciar saturacao a partir dai — e o que tira este
    # executor do topo do ranking least-loaded do servidor enquanto ele morre.
    logger.info("Shutdown: aguardando jobs em andamento...")
    await job_queue.shutdown(timeout=120)

    # O replay do outbox para AQUI: a partir de agora a _result_queue tem alvo
    # fixo (o que os jobs acabaram de produzir) e injetar backlog historico so
    # atrasaria a drenagem que ainda tem chance de ser aceita pelo servidor.
    replay_task.cancel()

    if conn_task.done():
        # Conexao encerrada em definitivo (revoked/shutdown/config_changed ou deny
        # terminal): conn.run() retornou e nao havera reconexao — nao existe
        # sender e esperar seria puro atraso.
        if not _result_queue.empty():
            logger.warning(
                "Conexao ja encerrada — %d resultado(s) ficam para o replay do outbox.",
                _result_queue.qsize(),
            )
    else:
        # `conn_task` vivo NAO significa sessao WS viva: durante o backoff de
        # reconexao o conn.run() esta apenas dormindo, sem _result_sender_loop
        # algum, e o `wait_for(join(), 30)` anterior pagava os 30s inteiros com
        # ninguem do outro lado — 150s de shutdown no pior caso, acima de
        # qualquer grace period default. Em vez de adivinhar pelo estado da task,
        # MEDIMOS: `_aguardar_confirmacao` desiste em 5s se nenhum resultado for
        # confirmado, e so continua esperando enquanto o sender progride.
        await _aguardar_confirmacao(
            _result_queue, rotulo="resultado", timeout=30, estagnado=5,
        )

    conn_task.cancel()
    renewal_task.cancel()
    for t in sync_tasks:
        t.cancel()
    # renewal_task estava sendo cancelada mas NAO aguardada aqui — o loop podia
    # ser destruido com a task ainda pendente ("Task was destroyed but it is
    # pending!") e o `finally` do renewal nunca rodava.
    await asyncio.gather(
        conn_task, renewal_task, replay_task, *sync_tasks, return_exceptions=True,
    )

    # Fecha pools asyncpg explicitamente antes do event loop encerrar
    # (evita RuntimeError: There is no current event loop no pool.release())
    try:
        from flow.utils.get_asyncpg_pool import close_all_pools
        await close_all_pools()
    except Exception as exc:
        logger.warning("Falha ao fechar pools asyncpg no shutdown: %s", exc)

    # Encerra o pool de threads proprio: cancel_futures descarta o que nunca
    # comecou; o join das threads vivas fica com o shutdown_default_executor()
    # que o asyncio.run() executa ao fechar o loop.
    _thread_pool.shutdown(wait=False, cancel_futures=True)
    # Mesmo tratamento para o pool do plano de controle (validacao/cripto), que
    # e separado justamente para nao compartilhar destino com os nos.
    from executor.job_executor import _CONTROL_POOL
    _CONTROL_POOL.shutdown(wait=False, cancel_futures=True)

    logger.info("Executor encerrado.")

    # Ultimo evento do canal, e so entao ele fecha (drenando o buffer). Um
    # supervisor que ve `stopped` sabe que foi encerramento ordenado; a ausencia
    # dele significa crash, e as duas coisas pedem tratamento diferente — religar
    # com backoff num caso, respeitar a decisao do usuario no outro.
    #
    # Deny autoritativo (close 4401/4403/4404, ou control `revoked`) e um
    # TERCEIRO caso, e nao pode sair como `stopped`: o executor foi removido ou
    # revogado no servidor, e so um enrollment novo o traz de volta. Reportado
    # como `failed` para que o supervisor pare em vez de religar contra um
    # servidor que ja disse nao — era um loop de reinicio a cada 2s.
    if conn.terminal_deny:
        _fase("failed", "revoked", detalhe=conn.terminal_deny)
    else:
        _fase("stopped", detalhe="restart_requested" if conn.restart_requested else None)

    if _dash is not None and _dash_modo == dashboard.MODO_JSON:
        await _dash.stop()

    if conn.restart_requested:
        _restart_process()
        sys.exit(1)  # Docker restart: on-failure → reinicia o container

    if conn.terminal_deny:
        # Codigo != 0 tambem para o supervisor do Docker: `restart: on-failure`
        # reinicia, mas o operador ve o motivo no log em vez de um exit 0
        # silencioso que sugere encerramento normal.
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        # Rede de seguranca do painel. O caminho normal ja o fechou no bloco 7,
        # mas uma excecao antes disso (ou o Ctrl+C do Windows, onde nao ha
        # signal handler registrado) deixaria o terminal no buffer alternativo
        # e sem cursor. emergency_stop e idempotente.
        from executor import dashboard
        dashboard.emergency_stop()
