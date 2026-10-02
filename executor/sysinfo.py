# executor/sysinfo.py
"""
Metricas de sistema do executor: hardware, limites de container e consumo do
proprio processo.

Extraido de connection.py, onde vivia porque o unico consumidor era o payload
de `capacity` enviado ao servidor. Com o painel local lendo as mesmas coisas a
1 Hz, faz mais sentido morar num modulo proprio — e evita que o dashboard
importe o modulo de rede so para pegar RAM livre.

## Custo das leituras

Tudo aqui e syscall bloqueante e TODOS os chamadores estao no event loop: o
painel a 1 Hz (`dashboard/tick.py`) e o `_capacity_loop` a cada 10 s. Por isso a
memoizacao mora NESTE modulo, e nao em cada chamador — assim ninguem precisa
lembrar de cachear, e o dado nunca diverge entre o painel e o `capacity` enviado
ao servidor. Ver `TTL_DISCO_S` e os memos de cgroup mais abaixo.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

logger = logging.getLogger("executor.sysinfo")


def _read_cgroup_value(path: str) -> int | None:
    """Lê um valor numérico de um arquivo de cgroup (v1 ou v2)."""
    try:
        with open(path) as f:
            val = int(f.read().strip())
            # cgroup v1 usa 'max' ou valor muito alto para "sem limite"
            if val >= 2**60:
                return None
            return val
    except (FileNotFoundError, ValueError, OSError):
        return None


# Fora do Linux /sys/fs/cgroup nao existe e nunca vai existir — este SIM e um
# fato imutavel, e e ele que gerava dois a quatro FileNotFoundError por segundo
# no Windows/macOS. A guarda de plataforma resolve esse caso sem cache nenhum.
_EH_LINUX = sys.platform.startswith("linux")

# Ja os limites do container (RAM total e cota de CPU) NAO sao imutaveis, ao
# contrario do que este modulo assumia: `docker update --memory/--cpus` e o
# in-place pod resize do k8s (GA no 1.33) reescrevem /sys/fs/cgroup/* com o
# container no ar, sem recriar nada nem reiniciar o processo. Com o memo
# permanente, aumentar o limite de 4 para 16 GiB deixava `ram_available_gb`
# preso em 0.0 para sempre (limite velho menor que o uso corrente), e reduzir de
# 4 para 2 GiB fazia o executor anunciar ~2,5 GB de folga que nao existem — no
# painel, no snapshot do desktop e no `capacity` que decide o dispatch.
#
# Memo com TTL curto: continua cortando ~97% dos open() por tick (o motivo da
# otimizacao) e volta a se autocorrigir logo depois de uma mudanca de limite.
TTL_CGROUP_S = 30.0

_SEM_LEITURA = float("-inf")  # nunca lido; nao usar 0.0 (monotonic pode ser < TTL)
_cache_ram_total: int | None = None
_cache_ram_total_em = _SEM_LEITURA
_cache_cpu_cores: float | None = None
_cache_cpu_cores_em = _SEM_LEITURA


def _get_cgroup_ram_total() -> int | None:
    """Limite de RAM do container via cgroup v2 ou v1. Memoizado por TTL — ver acima."""
    global _cache_ram_total, _cache_ram_total_em
    if not _EH_LINUX:
        return None
    agora = time.monotonic()
    if agora - _cache_ram_total_em < TTL_CGROUP_S:
        return _cache_ram_total
    # cgroup v2, com fallback para v1
    val = _read_cgroup_value("/sys/fs/cgroup/memory.max")
    if val is None:
        val = _read_cgroup_value("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    _cache_ram_total = val
    _cache_ram_total_em = agora
    return _cache_ram_total


def _get_cgroup_ram_available() -> int | None:
    """Calcula RAM disponível dentro do container via cgroup."""
    limit = _get_cgroup_ram_total()
    if limit is None:
        return None
    # cgroup v2: usage em memory.current
    usage = _read_cgroup_value("/sys/fs/cgroup/memory.current")
    if usage is not None:
        return max(limit - usage, 0)
    # cgroup v1: usage em memory.usage_in_bytes
    usage = _read_cgroup_value("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if usage is not None:
        return max(limit - usage, 0)
    return None


def _get_cgroup_cpu_cores() -> float | None:
    """Cota de CPU do container via cgroup v2 ou v1. Memoizada por TTL — ver acima.

    `process_metrics()` chama isto a cada tick do painel: sem o memo eram ate
    tres `open()` por segundo. Com TTL, um `docker update --cpus` volta a ser
    percebido em ate 30 s, em vez de deixar `cpu_pct_norm` normalizado pela cota
    antiga (barra de CPU achatada ou estourando 100 e sendo clampada) para
    sempre.
    """
    global _cache_cpu_cores, _cache_cpu_cores_em
    if not _EH_LINUX:
        return None
    agora = time.monotonic()
    if agora - _cache_cpu_cores_em < TTL_CGROUP_S:
        return _cache_cpu_cores
    _cache_cpu_cores = _ler_cgroup_cpu_cores()
    _cache_cpu_cores_em = agora
    return _cache_cpu_cores


def _ler_cgroup_cpu_cores() -> float | None:
    # cgroup v2: cpu.max → "quota period" (ex: "200000 100000" = 2 cores)
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            parts = f.read().strip().split()
            if parts[0] == "max":
                return None  # sem limite
            return round(int(parts[0]) / int(parts[1]), 1)
    except (FileNotFoundError, ValueError, OSError, IndexError):
        pass
    # cgroup v1: cpu.cfs_quota_us / cpu.cfs_period_us
    quota = _read_cgroup_value("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_cgroup_value("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and quota > 0 and period and period > 0:
        return round(quota / period, 1)
    return None


def _safe_disk_usage(psutil_mod):
    """psutil.disk_usage cross-platform com fallback silencioso.

    Windows: alguns bindings C do psutil (notavel: Anaconda 3.12+) estouram
    `SystemError: argument 1 (impossible<bad format char>)` mesmo com path
    'C:\\'. Tenta varias formas de root (drive do CWD, SystemDrive, C:\\, .\\)
    e retorna a primeira que funcionar. Se todas falharem, retorna None —
    system_info sem disk e melhor que loop de reconexao infinito.
    """
    if os.name == "nt":
        candidates = []
        try:
            drv = os.path.splitdrive(os.getcwd())[0]
            if drv:
                candidates.append(drv + os.sep)
        except Exception:
            pass
        sys_drive = os.environ.get("SystemDrive")
        if sys_drive:
            candidates.append(sys_drive + os.sep)
        candidates.extend(["C:\\", "."])
    else:
        candidates = ["/"]

    for path in candidates:
        try:
            return psutil_mod.disk_usage(path)
        except (SystemError, OSError, PermissionError):
            continue
    return None


def _collect_system_info() -> dict | None:
    """Coleta informações estáticas de hardware (CPU, RAM, disco, OS).

    Dentro de containers Docker/K8s, prioriza limites de cgroup para
    refletir os recursos efetivamente disponíveis ao container.
    """
    try:
        import psutil
        import platform
        # disk pode ser None se psutil.disk_usage falhar em todos os
        # candidatos (bug C-binding Windows, permissao negada, etc).
        # Reportamos 0 nesse caso — melhor que abortar system_info.
        disk = _safe_disk_usage(psutil)

        # CPU: prioriza limite de cgroup, fallback para psutil
        cpu_cores = _get_cgroup_cpu_cores() or psutil.cpu_count(logical=True)

        # RAM: prioriza limite de cgroup, fallback para psutil
        cgroup_ram = _get_cgroup_ram_total()
        ram_total = cgroup_ram if cgroup_ram else psutil.virtual_memory().total

        # Vai no handshake. O servidor so guarda os campos de SYSTEM_INFO_* (a
        # allowlist do protocolo, em flow/utils/protocolo_ws.py), cada um com o
        # tipo do seu grupo: campo novo aqui tem de entrar la, senao e
        # descartado com um WARNING a cada conexao.
        return {
            "hostname":      platform.node(),
            "os_name":       platform.system(),
            "os_version":    platform.release(),
            "cpu_cores":     cpu_cores,
            "ram_total_gb":  round(ram_total / (1024**3), 1),
            "disk_total_gb": round(disk.total / (1024**3), 1) if disk else 0,
            "container":     cgroup_ram is not None,
        }
    except ImportError:
        return None


def _disco_dos_artefatos(psutil_mod) -> object | None:
    """Uso do disco ONDE OS ARTEFATOS SÃO GRAVADOS.

    Não é o mesmo que `_safe_disk_usage`, que mede o drive do CWD — no app
    desktop o CWD é a pasta de instalação e os artefatos vão para o perfil do
    usuário, que pode estar em outra unidade (a pasta é configurável).

    Isto passou a importar de verdade com o modo de localidade local: um
    artefato marcado para não sair da máquina tem UMA cópia, e ela está aqui.
    Disco cheio deixa de ser inconveniente e vira perda de dado do cliente.

    Sobe a árvore até achar um diretório existente: a pasta configurada pode
    ainda não ter sido criada, e `disk_usage` num caminho inexistente levanta.
    """
    from executor.config import ARTIFACTS_DIR

    alvo = os.path.abspath(ARTIFACTS_DIR)
    for _ in range(8):
        if os.path.isdir(alvo):
            try:
                return psutil_mod.disk_usage(alvo)
            except (SystemError, OSError, PermissionError):
                return None
        pai = os.path.dirname(alvo)
        if pai == alvo:
            break
        alvo = pai
    return None


# ── Cache do disco ───────────────────────────────────────────────────────────
# Espaço livre em disco é a grandeza mais cara e mais lenta que este módulo
# mede: são dois `disk_usage` (o do CWD ainda tenta vários candidatos quando o
# binding do Windows falha) precedidos de até 8 `os.path.isdir` subindo a árvore
# até achar a pasta de artefatos. Com essa pasta numa unidade de rede ou num HD
# que dormiu, cada coleta bloqueia por centenas de milissegundos — e ela rodava
# a 1 Hz DENTRO do event loop, atrasando heartbeat, envio de resultados e
# recepção de jobs.
#
# A defesa é recoletar numa thread e servir o valor anterior enquanto ela roda:
# o event loop NUNCA espera por I/O de disco, nem na primeira coleta (numa
# unidade pendurada ela travaria a subida inteira do executor — sem heartbeat e
# sem receber job). Até a primeira coleta pousar, as chaves simplesmente não
# existem e o painel mostra "—".
#
# Sobre esse cache incidem três limites, e cada um existe por um sintoma:
#
# 1. TTL adaptativo (`_ttl_do_valor`). Longe do fim do disco, 60 s: é o que tira
#    a coleta do caminho quente. Perto do fim, 5 s — ver o docstring de
#    `_ttl_do_valor`.
# 2. Teto de idade (`IDADE_MAXIMA_DISCO_S`). Passado ele o valor vira
#    DESCONHECIDO (chaves ausentes -> None -> "—" no painel e no desktop) em vez
#    de continuar sendo servido como se fosse leitura corrente. Servir dado
#    velho é aceitável; servir dado velho indistinguível de dado fresco não é,
#    num gauge cuja única função é avisar antes de o artefato se perder.
# 3. Prazo da coleta em voo (`TIMEOUT_COLETA_DISCO_S`) com teto de threads
#    (`MAX_COLETAS_DISCO_EM_VOO`). `psutil.disk_usage` num NFS `hard` mount ou
#    num FUSE travado NÃO retorna nunca: a thread fica pendurada sem chegar a
#    soltar o contador. Sem prazo, ela seria um cadeado permanente contra
#    qualquer tentativa futura; só com prazo, o executor passaria a vazar uma
#    thread pendurada a cada 30 s para sempre. O teto fecha os dois lados —
#    algumas tentativas de recuperação e depois o número simplesmente vira
#    desconhecido, que é a resposta honesta.
TTL_DISCO_S = 60.0
TTL_DISCO_APERTADO_S = 5.0

# Espelha DISCO_BAIXO_GB de desktop/src/shared/disco.ts — o limiar a partir do
# qual o desktop começa a avisar. Divergir os dois faria o executor deixar de
# refrescar justamente na faixa em que o alerta é decidido.
DISCO_APERTADO_GB = 5.0

# ~3x o TTL longo: absorve uma coleta lenta e uma falha isolada (a retentativa
# só vem no vencimento do TTL seguinte) sem chegar a apagar o número.
IDADE_MAXIMA_DISCO_S = 180.0
TIMEOUT_COLETA_DISCO_S = 30.0
MAX_COLETAS_DISCO_EM_VOO = 3

_disco_lock = threading.Lock()
_disco_valor: dict = {}
_disco_expira = 0.0
_disco_em_voo = 0                   # threads de coleta que ainda não voltaram
_disco_coletado_em = _SEM_LEITURA   # monotonic da última coleta BEM-SUCEDIDA
_disco_iniciou_em = _SEM_LEITURA    # monotonic do último disparo de coleta
_disco_obsoleto_logado = False      # o aviso de obsoleto é avaliado a 1 Hz; logar uma vez


def _ttl_do_valor(valor: dict) -> float:
    """TTL adaptativo: curto quando o disco está apertado.

    A premissa antiga ("nenhuma decisão que este número suporta mudaria com o
    valor de um minuto atrás") é falsa perto do fim do disco. O toast "Disco
    quase cheio" (desktop/src/main/ui/notificacoes.ts) existe para avisar ANTES
    de o workflow falhar ao gravar, e um nó GIS gravando um raster consome os
    últimos GB em segundos: com 60 s fixos o aviso chegava depois da falha, e o
    texto ("já podem falhar ao gravar") virava constatação em vez de aviso.

    Longe do limiar o TTL longo continua valendo — é ele que tira o I/O de disco
    do caminho de 1 Hz.
    """
    livres = [v for k, v in valor.items()
              if k.endswith("_free_gb") and isinstance(v, (int, float))]
    if livres and min(livres) < DISCO_APERTADO_GB:
        return TTL_DISCO_APERTADO_S
    return TTL_DISCO_S


def _coletar_disco(psutil_mod) -> dict:
    """As syscalls de disco propriamente ditas. Roda FORA do lock."""
    metrics: dict = {}
    disk = _safe_disk_usage(psutil_mod)
    if disk is not None:
        metrics["disk_free_gb"] = round(disk.free / (1024**3), 1)

    # Disco dos artefatos, reportado à parte: pode ser outra unidade, e é
    # a que decide se um workflow consegue gravar o resultado.
    #
    # Em try PRÓPRIO: `_disco_dos_artefatos` importa `executor.config`, e um
    # ImportError ali derrubaria a coleta inteira. O efeito seria perder também
    # o disco do sistema por causa desta, em silêncio.
    try:
        art = _disco_dos_artefatos(psutil_mod)
        if art is not None:
            metrics["artifacts_disk_free_gb"] = round(art.free / (1024**3), 1)
            metrics["artifacts_disk_total_gb"] = round(art.total / (1024**3), 1)
    except Exception:
        pass
    return metrics


def _refrescar_disco(psutil_mod) -> None:
    global _disco_valor, _disco_expira, _disco_em_voo
    global _disco_coletado_em, _disco_obsoleto_logado
    try:
        novo = _coletar_disco(psutil_mod)
    except Exception as exc:
        # WARNING, não DEBUG: uma pasta de artefatos inacessível era totalmente
        # silenciosa, e é justamente o caso em que o operador precisa saber que
        # o número do painel parou de ser confiável.
        logger.warning("Falha ao coletar metricas de disco: %s", exc)
        novo = None
    agora = time.monotonic()
    with _disco_lock:
        if novo is not None:
            _disco_valor = novo
            _disco_coletado_em = agora
            _disco_obsoleto_logado = False
        # O TTL renova mesmo na falha: o valor antigo continua servindo (até o
        # teto de idade) e a próxima tentativa vem no vencimento seguinte, sem
        # martelar uma unidade que sumiu a cada tick.
        _disco_expira = agora + _ttl_do_valor(_disco_valor)
        _disco_em_voo = max(_disco_em_voo - 1, 0)


def _metricas_de_disco(psutil_mod) -> dict:
    """Espaço em disco memoizado. Ver a nota acima.

    Devolve `{}` (chaves ausentes -> `None` nos consumidores) enquanto a
    primeira coleta não pousa e sempre que o último valor bom passa de
    `IDADE_MAXIMA_DISCO_S`.
    """
    global _disco_em_voo, _disco_expira, _disco_iniciou_em, _disco_obsoleto_logado
    agora = time.monotonic()
    with _disco_lock:
        vencido = agora >= _disco_expira
        atual = _disco_valor
        # Enquanto uma coleta está em voo não se dispara outra: numa unidade de
        # rede pendurada, cada tick abriria uma thread nova. Mas com prazo — uma
        # coleta que passou de TIMEOUT_COLETA_DISCO_S está pendurada e pode não
        # voltar nunca, e sem essa saída ela travaria toda tentativa futura.
        pendurada = _disco_em_voo > 0 and (agora - _disco_iniciou_em) >= TIMEOUT_COLETA_DISCO_S
        disparar = (
            vencido
            and (_disco_em_voo == 0 or pendurada)
            and _disco_em_voo < MAX_COLETAS_DISCO_EM_VOO
        )
        if disparar:
            _disco_em_voo += 1
            _disco_iniciou_em = agora
            # Empurra o vencimento JÁ no disparo: se a coleta pendurar e nunca
            # chegar a `_refrescar_disco`, é isto que impede uma nova thread por
            # tick. O caminho normal sobrescreve isto ao terminar, então o TTL
            # curto do disco apertado não é perdido.
            _disco_expira = agora + max(_ttl_do_valor(atual), TIMEOUT_COLETA_DISCO_S)
        idade = agora - _disco_coletado_em
        obsoleto = bool(atual) and idade >= IDADE_MAXIMA_DISCO_S
        logar_obsoleto = obsoleto and not _disco_obsoleto_logado
        if logar_obsoleto:
            _disco_obsoleto_logado = True

    if disparar:
        try:
            threading.Thread(target=_refrescar_disco, args=(psutil_mod,),
                             name="sysinfo-disco", daemon=True).start()
        except Exception as exc:
            # Sem devolver a vaga aqui, um unico "can't start new thread"
            # congelaria as metricas de disco pelo resto da vida do processo.
            with _disco_lock:
                _disco_em_voo = max(_disco_em_voo - 1, 0)
                _disco_expira = 0.0
            logger.warning("Nao foi possivel iniciar a coleta de disco: %s", exc)

    if obsoleto:
        if logar_obsoleto:
            logger.warning(
                "Metricas de disco obsoletas (ultima coleta ha %.0fs, teto %.0fs): "
                "reportando desconhecido em vez do valor antigo. A pasta de artefatos "
                "pode estar numa unidade de rede que parou de responder.",
                idade, IDADE_MAXIMA_DISCO_S,
            )
        return {}
    return atual


def _resetar_caches() -> None:
    """Volta todo o estado memoizado do módulo ao ponto de partida.

    Existe para os TESTES. Sem isto, o primeiro teste que faz monkeypatch de
    `_read_cgroup_value` ou de `psutil.disk_usage` deixa o resultado gravado nos
    globais e contamina todos os seguintes do mesmo processo — inclusive os que
    nem falam de sysinfo, porque `_get_dynamic_metrics` é chamado de vários
    lugares. Nada em produção chama isto.
    """
    global _cache_ram_total, _cache_ram_total_em, _cache_cpu_cores, _cache_cpu_cores_em
    global _disco_valor, _disco_expira, _disco_em_voo
    global _disco_coletado_em, _disco_iniciou_em, _disco_obsoleto_logado
    global _PROC, _PROC_FALHOU
    _cache_ram_total = None
    _cache_ram_total_em = _SEM_LEITURA
    _cache_cpu_cores = None
    _cache_cpu_cores_em = _SEM_LEITURA
    with _disco_lock:
        _disco_valor = {}
        _disco_expira = 0.0
        _disco_em_voo = 0
        _disco_coletado_em = _SEM_LEITURA
        _disco_iniciou_em = _SEM_LEITURA
        _disco_obsoleto_logado = False
    _PROC = None
    _PROC_FALHOU = False


def _get_dynamic_metrics() -> dict:
    """Coleta métricas dinâmicas de sistema (RAM livre, disco livre).

    Prioriza limites de cgroup dentro de containers.

    O disco vem do cache (`_metricas_de_disco`); a RAM é lida na hora, porque é
    leitura barata — `GlobalMemoryStatusEx`, /proc/meminfo ou um arquivo local de
    cgroup, nada que possa parar numa unidade de rede — e é justamente a métrica
    que o operador espera ver mexer no painel enquanto um job pesado roda.
    """
    try:
        import psutil
    except ImportError:
        return {}

    metrics = dict(_metricas_de_disco(psutil))
    try:
        cgroup_avail = _get_cgroup_ram_available()
        if cgroup_avail is not None:
            metrics["ram_available_gb"] = round(cgroup_avail / (1024**3), 1)
        else:
            metrics["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 1)
    except Exception as exc:
        logger.debug("Falha ao coletar RAM disponivel: %s", exc)
    return metrics


# ── Consumo do proprio processo ──────────────────────────────────────────────
# psutil.Process().cpu_percent(interval=None) devolve a media desde a chamada
# ANTERIOR no mesmo objeto — por isso o Process e criado uma vez e guardado.
# Recriar a cada tick faria toda leitura voltar 0.0.
_PROC = None
_PROC_FALHOU = False


def _process() -> object | None:
    global _PROC, _PROC_FALHOU
    if _PROC_FALHOU:
        return None
    if _PROC is None:
        try:
            import psutil
            _PROC = psutil.Process()
            _PROC.cpu_percent(interval=None)  # aquece o baseline
        except Exception as exc:
            _PROC_FALHOU = True
            logger.debug("psutil.Process indisponivel — metricas do processo desligadas: %s", exc)
            return None
    return _PROC


def process_metrics() -> dict:
    """CPU%, RSS e threads do processo do executor. Nao bloqueia.

    Uma unica medida cobre a carga inteira: os workers sao corrotinas e o flow
    engine usa `asyncio.to_thread` no ThreadPoolExecutor do proprio processo
    (main.py), entao nao ha filhos para somar.

    `cpu_pct` pode passar de 100 (soma das threads); `cpu_pct_norm` divide pelo
    numero de nucleos para caber numa barra de 0 a 100. Retorna {} se o psutil
    faltar ou falhar — o painel mostra "—" em vez de derrubar o tick.
    """
    proc = _process()
    if proc is None:
        return {}
    try:
        import psutil
        cpu = proc.cpu_percent(interval=None)
        mem = proc.memory_info()
        cores = _get_cgroup_cpu_cores() or psutil.cpu_count(logical=True) or 1
        return {
            "cpu_pct":      round(cpu, 1),
            "cpu_pct_norm": round(min(cpu / cores, 100.0), 1),
            "rss_mb":       round(mem.rss / (1024**2), 1),
            "threads":      proc.num_threads(),
            "cpu_cores":    cores,
        }
    except Exception as exc:
        # Mesmo binding C que quebra disk_usage no Anaconda/Windows pode se
        # manifestar aqui. Degradar em silencio e melhor que um traceback por
        # segundo no arquivo de log.
        logger.debug("Falha ao coletar metricas do processo: %s", exc)
        return {}
