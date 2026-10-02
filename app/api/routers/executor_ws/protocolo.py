# app/api/routers/executor_ws/protocolo.py
"""
Saneamento e limites do protocolo WS do executor: campos obrigatórios,
tetos de payload e rate limit por conexão. O vocabulário (versão, tipos, chaves
reservadas de stats, campos de system_info) é o de flow/utils/protocolo_ws.py;
o teto e a redução de node_event, os de flow/utils/publisher/reducao.py (ver
`_serialize_node_event` em resultados.py).
"""
import json
import time

from app.core.utils.logger import get_logger

from app.core.executor_connections import _DEFAULT_CAPACITY, executor_registry
from flow.utils.protocolo_ws import (
    STATS_CONTROLE_DESCARTADO,
    STATS_TRUNCADO,
    SYSTEM_INFO_BOOLEANOS,
    SYSTEM_INFO_NUMEROS,
    SYSTEM_INFO_TEXTOS,
    reduzir_stats,
)

logger = get_logger(__name__)


# Rate limit por executor (janela deslizante grosseira). Não derruba a conexão:
# um workflow legítimo com fan-out alto emite rajadas, e matar o socket falharia
# o run inteiro. O excedente é descartado e uma linha agregada de WARNING é
# emitida por janela.
#
# DUAS FAIXAS de node_event de propósito. Um teto único de 200/s tratava
# `completed` de nó como se fosse linha de log e DESCARTAVA eventos de ciclo de
# vida — descarte total e permanente, sem re-enfileiramento. O executor drena a
# fila de eventos em rajada (main.py → _drenar_eventos_pendentes), então um
# workflow de ~300 nós triviais emite 600+ eventos em 2-3s e passa do teto: o
# frontend perde o `completed` de vários nós e, como `completeExecution` só
# rebaixa nó preso quando o run é 'cancelled', o usuário vê um run "concluído
# com sucesso" com metade do grafo girando para sempre — e reabrir o run
# reproduz o mesmo estado, porque o histórico é a mesma fonte truncada.
# O volume de lifecycle é limitado pelo número de nós do workflow, não pelo
# capricho do produtor; o teto alto continua sendo um limite duro contra abuso,
# só que fora do alcance do tráfego honesto.
_NODE_EVENT_RATE_LIMIT = 200            # stdout/debug e futuros eventos de log

_NODE_EVENT_LIFECYCLE_RATE_LIMIT = 2000  # started/completed/failed de nó

_RATE_WINDOW = 1.0

# job_result também é rate-limited, mas com teto próprio: descartar um deles
# deixa o run pendurado em 'running' até o watchdog, então o valor precisa estar
# MUITO acima do tráfego honesto (um job_result por job; o default do executor é
# EXECUTOR_MAX_CONCURRENT=4). Existe só para tampar o loop de flood.
_JOB_RESULT_RATE_LIMIT = 50

# sync_event era o ÚNICO tipo do protocolo sem rate limit e sem teto de bytes: o
# emissor manda um evento por transição de arquivo, então um GeoSync de milhares
# de arquivos gerava milhares de mensagens que congelavam o loop junto com os
# node_events dos workflows. O teto é alto porque a UI usa esses eventos para a
# barra de progresso; os terminais são isentos (ver `_sync_event_allowed`).
_SYNC_EVENT_RATE_LIMIT = 300

_MAX_SYNC_EVENT_BYTES = 16 * 1024

# Evento que fecha o CICLO do sync — um por execução (sync/manager: `sync_complete`
# é emitido uma única vez no fim). Descartá-lo por rajada deixaria a barra de
# progresso presa em 99% para sempre, então ele é isento do rate limit.
#
# `sync_error` e `conflict_detected` NÃO entram aqui: apesar do nome, o executor
# os emite DENTRO dos laços por dataset/arquivo. Com MinIO fora do ar ou
# credencial expirada, um GeoSync de 3000 arquivos vira 3000 mensagens isentas —
# exatamente a rajada que o rate limit existe para conter, e que ainda enche a
# fila da conexão e atrapalha a coalescência dos node_events.
_SYNC_TERMINAL_EVENTS = frozenset({"sync_complete"})

# Balde PRÓPRIO para os eventos de problema (um por arquivo). Separado do balde
# de progresso de propósito: uma rajada de erro não pode consumir a cota do
# `file_uploaded` (a barra pararia de andar) nem o contrário. O teto é folgado o
# bastante para a UI mostrar os primeiros erros de um dataset e apertado o
# bastante para a falha em massa não virar flood.
_SYNC_PROBLEM_EVENTS = frozenset({"sync_error", "conflict_detected"})

_SYNC_PROBLEM_RATE_LIMIT = 50

# ── Tetos de bytes do job_result ─────────────────────────────────────────────
# O executor honesto já se auto-limita em 16 MB e trunca `stats`
# (executor/connection.py), mas o modelo de ameaça aqui é o executor
# COMPROMETIDO — para o qual a auto-limitação dele não vale nada. `error` e
# `stats` do job_result iam CRUS para três destinos duradouros: a fila
# `run_results` (sem TTL), o histórico `workflow:{run}:history` (teto de 5000
# ENTRADAS, não de bytes) e o Postgres (WorkflowRun.error_message é Text sem
# limite e node_stats é JSON). 15 MB por mensagem, em loop, enchiam o mesmo
# Redis que guarda presença de executores e blacklist de certs.
_MAX_JOB_ERROR_CHARS = 8 * 1024

# `stats` carrega o body inline do ResponseNode (__response__), cujo limite do
# lado do executor é WEBHOOK_RESPONSE_INLINE_LIMIT (default 1 MB) — acima disso
# ele sobe para o MinIO e manda só o body_ref. 4 MB dá folga para o body inline
# + stats por-nó de um workflow grande e ainda corta 4x do teto do frame.
_MAX_JOB_STATS_BYTES = 4 * 1024 * 1024

def _e_ciclo_de_vida(msg: dict) -> bool:
    """True para node_event que carrega ESTADO DO GRAFO (started/completed/failed).

    `kind` ausente conta como ciclo de vida: é o default do produtor
    (flow/utils/publisher/events.publish_event). Errar para este lado é o certo —
    o custo de tratar um log como ciclo de vida é ocupar um slot; o custo do
    inverso é um nó girando para sempre no canvas do usuário.
    """
    kind = msg.get("kind")
    return kind is None or kind == "lifecycle"

def _e_telemetria(msg_type: str, msg: dict) -> bool:
    """True para o que pode ser perdido sem mentir sobre o estado do sistema.

    São os `sync_event` (progresso do GeoSync, que o executor emite por arquivo)
    e os `node_event` de stdout/debug. Tudo o mais — ciclo de vida e job_result —
    carrega estado que a UI não tem como reconstruir sozinha.
    """
    if msg_type == "sync_event":
        # `sync_complete` é emitido UMA vez por ciclo e fecha a barra de
        # progresso do GeoSync. Sacrificá-lo aqui deixaria a barra presa em 99%
        # para sempre — o mesmo motivo pelo qual ele já é isento do rate limit
        # (ver `_SYNC_TERMINAL_EVENTS`). As duas políticas têm de concordar.
        return msg.get("event") not in _SYNC_TERMINAL_EVENTS
    return msg_type == "node_event" and not _e_ciclo_de_vida(msg)

# Campos obrigatórios por tipo de mensagem. Faltas → erro explícito para
# o executor em vez do antigo silent-drop.
_REQUIRED_FIELDS: dict[str, set[str]] = {
    "job_result": {"job_id", "status"},
    "node_event": {"run_id", "node"},
    "capacity":   {"queued", "running", "max_concurrent", "max_queue"},
    "ack":        {"job_id"},
    "sync_event": {"event"},
    "inventario": {"ativos"},
}

def _missing_fields(msg_type: str, msg: dict) -> list[str]:
    """Retorna campos obrigatórios ausentes no payload. [] se OK."""
    req = _REQUIRED_FIELDS.get(msg_type)
    if not req:
        return []
    return [f for f in req if msg.get(f) is None]

# ── Sanitização de `capacity` ────────────────────────────────────────────────
# Os campos iam CRUS para o registry. Um executor mandando {"queued": {"n": 0}}
# fazia `_resolve_candidates` (workflow_execution_service) estourar TypeError
# NÃO TRATADO em `cap["running"] + cap["queued"]` → 500 no POST /execute da
# plataforma INTEIRA enquanto aquele executor estivesse online. A defesa tem que
# ser aqui, na entrada: o service confia no formato do registry.

def _coerce_count(value, field: str, errors: list[str]) -> int | None:
    """Coage um contador de capacity para int >= 0. Acumula o motivo em `errors`."""
    # bool é subclasse de int — True viraria 1 silenciosamente.
    if isinstance(value, bool):
        errors.append(f"{field}: booleano não é um contador válido")
        return None
    if isinstance(value, int):
        n = value
    elif isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            errors.append(f"{field}: valor não finito")
            return None
        n = int(value)
    elif isinstance(value, str):
        try:
            n = int(value.strip())
        except ValueError:
            errors.append(f"{field}: string não numérica")
            return None
    else:
        errors.append(f"{field}: tipo {type(value).__name__} não é numérico")
        return None
    if n < 0:
        errors.append(f"{field}: negativo ({n})")
        return None
    return n

def _coerce_gauge(value) -> float | None:
    """Coage métrica informativa (disco/RAM livre) para float >= 0, ou None.

    Diferente dos contadores, um valor ruim aqui não invalida a mensagem — só
    some do payload. Ninguém decide dispatch com base nesses campos.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")) or f < 0:
        return None
    return round(f, 3)

def _sanitize_capacity(executor_id: str, msg: dict) -> tuple[dict | None, list[str]]:
    """Valida/coage o payload de capacity e aplica o clamp dos limites do banco.

    A capacidade é AUTO-DECLARADA. O clamp fecha os TETOS: sem ele contra
    Executor.max_concurrent_jobs e max_queue_size, um executor anunciava
    max_queue=10**9 e o `is_full` nunca disparava — dreno ILIMITADO do pool
    default. Com o clamp o dreno vira limitado (max_concurrent + max_queue do
    registro).

    O QUE O CLAMP *NÃO* FECHA — e não pode fechar aqui: `queued` e `running`
    continuam sendo números crus do executor. Não clampamos esses dois PARA
    BAIXO de propósito: reduzir uma carga declarada só ajudaria quem mente e
    prejudicaria quem, após um limite ser reduzido no banco, ainda tem jobs em
    voo acima do novo teto. Na ORDENAÇÃO do dispatch a mentira para baixo não
    compensa: a carga usada é a contada pelo servidor — runs
    `pending`/`running` do host no banco (`_situacoes` em
    workflow_execution_service) —, e a declarada só serve para dizer "cheio".
    Anunciar zero não põe o executor na frente de ninguém. O `is_full` do
    `send_job` continua olhando só a declarada: quem mente para baixo acumula até
    o teto clampado, e a fronteira que segura isso é administrativa (só admin
    põe máquina no pool default).
    """
    errors: list[str] = []
    queued         = _coerce_count(msg.get("queued", 0), "queued", errors)
    running        = _coerce_count(msg.get("running", 0), "running", errors)
    max_concurrent = _coerce_count(msg.get("max_concurrent", 0), "max_concurrent", errors)
    max_queue      = _coerce_count(msg.get("max_queue", 0), "max_queue", errors)
    if errors:
        return None, errors

    conn = executor_registry.get(executor_id)
    limit_concurrent = conn.max_concurrent_limit if conn else _DEFAULT_CAPACITY["max_concurrent"]
    limit_queue      = conn.max_queue_limit if conn else _DEFAULT_CAPACITY["max_queue"]

    capacity = {
        "queued":         queued,
        "running":        running,
        "max_concurrent": min(max_concurrent, limit_concurrent),
        "max_queue":      min(max_queue, limit_queue),
        "disk_free_gb":     _coerce_gauge(msg.get("disk_free_gb")),
        "ram_available_gb": _coerce_gauge(msg.get("ram_available_gb")),
    }
    if max_concurrent > limit_concurrent or max_queue > limit_queue:
        logger.warning(
            "Executor '%s' declarou capacidade acima do registro "
            "(max_concurrent=%d>%d, max_queue=%d>%d) — clampada.",
            executor_id, max_concurrent, limit_concurrent, max_queue, limit_queue,
        )
    # Carga declarada acima dos próprios tetos é incoerente (bug do agente ou
    # payload forjado). Não alteramos o valor — ver o docstring —, mas o
    # operador precisa do sinal: é o único rastro de capacity mentirosa.
    if running > limit_concurrent or queued > limit_queue:
        logger.warning(
            "Executor '%s' declarou carga incoerente com o registro "
            "(running=%d>%d, queued=%d>%d) — mantida como reportada.",
            executor_id, running, limit_concurrent, queued, limit_queue,
        )
    return capacity, []

# ── Sanitização de `system_info` ─────────────────────────────────────────────
# Ia cru para a coluna JSONB. `"system_info": "pwn"` (string truthy) fazia
# ExecutorOut.from_model levantar ValidationError → 500 PERMANENTE em
# GET /executores/ e /{id}, até alguém corrigir a linha na mão. Variante de
# volume: 15 MB persistidos por reconexão. Qualquer usuário que possa criar um
# executor dedicado chega aqui — não precisa ser admin. A allowlist (os campos
# que o executor manda, por tipo) é a do protocolo: SYSTEM_INFO_* em
# flow/utils/protocolo_ws.py.
_SYSTEM_INFO_STR_MAX = 200

_SYSTEM_INFO_MAX_BYTES = 8192

def _sanitize_system_info(executor_id: str, raw) -> dict | None:
    """Aplica allowlist + coerção + teto de tamanho. None se nada aproveitável."""
    if not isinstance(raw, dict):
        logger.warning(
            "Executor '%s' enviou system_info do tipo %s (esperado objeto) — descartado.",
            executor_id, type(raw).__name__,
        )
        return None

    clean: dict = {}
    for key in SYSTEM_INFO_TEXTOS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            clean[key] = value.strip()[:_SYSTEM_INFO_STR_MAX]
    for key in SYSTEM_INFO_NUMEROS:
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value != value or value in (float("inf"), float("-inf")) or value < 0:
            continue
        clean[key] = round(float(value), 2)
    for key in SYSTEM_INFO_BOOLEANOS:
        value = raw.get(key)
        if isinstance(value, bool):
            clean[key] = value

    dropped = set(raw) - set(clean)
    if dropped:
        logger.warning(
            "Executor '%s': campos de system_info fora da allowlist ou inválidos descartados: %s",
            executor_id, sorted(dropped)[:20],
        )

    if not clean:
        return None

    # Teto final: a allowlist já limita, mas o cinto duplo protege de qualquer
    # campo novo adicionado sem limite explícito no futuro.
    if len(json.dumps(clean)) > _SYSTEM_INFO_MAX_BYTES:
        logger.warning(
            "Executor '%s': system_info excedeu %d bytes mesmo após allowlist — descartado.",
            executor_id, _SYSTEM_INFO_MAX_BYTES,
        )
        return None
    return clean

# ── Sanitização de `executor_version` ────────────────────────────────────────
# Vai para a coluna VARCHAR(20) que a tela de executores mostra. Fora do formato
# é descartada, não cortada — "2.3.1-beta+build.1234" truncado é outra versão —,
# e o banco fica com a última versão boa. Sem a checagem, um valor longo
# estouraria a coluna no meio do loop de recebimento e derrubaria a conexão.
_EXECUTOR_VERSION_MAX = 20

def _sanitize_executor_version(executor_id: str, raw) -> str | None:
    """A versão declarada no handshake, ou None se ausente ou inválida."""
    if raw is None:
        return None
    ver = raw.strip() if isinstance(raw, str) else ""
    if ver and len(ver) <= _EXECUTOR_VERSION_MAX and ver.isprintable():
        return ver
    # Corta ANTES do repr: o frame pode ter megabytes.
    amostra = repr(raw[:40]) if isinstance(raw, str) else type(raw).__name__
    logger.warning(
        "Executor '%s' enviou executor_version inválida (%s) — descartada.",
        executor_id, amostra,
    )
    return None

# ── Rate limit por executor ──────────────────────────────────────────────────
# (executor_id, bucket) → {"window_start": monotonic, "count": int, "suppressed": int}.
# Limpo no finally do handler (ver `agent_websocket`). Buckets separados para que
# uma rajada de debug não consuma a cota do ciclo de vida nem a do job_result.
_rate_state: dict[tuple[str, str], dict] = {}

def _rate_allowed(executor_id: str, bucket: str, limit: int) -> bool:
    """Janela deslizante por (executor, bucket). False = descartar a mensagem."""
    now = time.monotonic()
    key = (executor_id, bucket)
    state = _rate_state.get(key)
    if state is None or (now - state["window_start"]) >= _RATE_WINDOW:
        if state is not None and state["suppressed"]:
            logger.warning(
                "Executor '%s': %d mensagem(ns) de '%s' descartadas por rate limit (>%d/%.0fs).",
                executor_id, state["suppressed"], bucket, limit, _RATE_WINDOW,
            )
        _rate_state[key] = {"window_start": now, "count": 1, "suppressed": 0}
        return True
    if state["count"] >= limit:
        state["suppressed"] += 1
        return False
    state["count"] += 1
    return True

def _drop_rate_state(executor_id: str) -> None:
    """Esquece todos os buckets de um executor (chamado no unregister)."""
    for key in [k for k in _rate_state if k[0] == executor_id]:
        _rate_state.pop(key, None)

def _node_event_allowed(executor_id: str, msg: dict) -> bool:
    """Rate limit de node_event, com faixa separada para ciclo de vida.

    `kind` ausente conta como lifecycle: é o default do produtor
    (flow/utils/publisher/events.publish_event). Um adversário que omita o campo
    cai na faixa alta, o que é aceito de propósito — o teto de bytes por evento
    continua valendo e 2000 eventos/s de 64 KB já é um limite duro.
    """
    if _e_ciclo_de_vida(msg):
        return _rate_allowed(executor_id, "node_event:lifecycle", _NODE_EVENT_LIFECYCLE_RATE_LIMIT)
    return _rate_allowed(executor_id, "node_event:log", _NODE_EVENT_RATE_LIMIT)

def _sync_event_allowed(executor_id: str, msg: dict) -> bool:
    """Rate limit de sync_event, em três faixas.

    O volume vem das transições por arquivo (`file_uploading`/`file_uploaded`):
    num dataset com milhares de arquivos são milhares de mensagens. Descartar o
    `sync_complete` na rajada, porém, deixaria a barra de progresso da UI presa
    para sempre — ele é o único de fato um-por-ciclo e o único isento.

    `sync_error`/`conflict_detected` são por ARQUIVO: isentá-los devolvia
    integralmente o flood que o teto existe para conter (MinIO fora do ar =
    um evento por arquivo do dataset). Ficam num balde próprio e mais apertado.
    """
    evento = msg.get("event")
    if evento in _SYNC_TERMINAL_EVENTS:
        return True
    if evento in _SYNC_PROBLEM_EVENTS:
        return _rate_allowed(executor_id, "sync_event:problema", _SYNC_PROBLEM_RATE_LIMIT)
    return _rate_allowed(executor_id, "sync_event", _SYNC_EVENT_RATE_LIMIT)

def _cap_job_result(executor_id: str, msg: dict) -> tuple[dict, str]:
    """Impõe o teto de bytes de `error` e `stats` na ENTRADA do job_result.

    Devolve uma cópia rasa com os dois campos já limitados, para que TODOS os
    destinos (Redis efêmero, fila `run_results`, `workflow:{run}:history`,
    webhook_response e, via consumer, as colunas `error_message`/`node_stats`)
    usem o mesmo payload contido. A truncagem de `stats` é a do protocolo
    (`reduzir_stats` em flow/utils/protocolo_ws.py), a mesma que o executor
    aplica antes de enviar: primeiro derruba os stats por-nó preservando as
    chaves de controle; se nem elas couberem, derruba tudo e marca
    `__control_dropped__`, que o handler de webhook já sabe transformar em erro
    explícito em vez de deixar o BRPOP em timeout.

    PERF: devolve TAMBÉM o JSON de `stats` já serializado. A medição do teto
    exige um `json.dumps` de até 4 MB; o caller precisava do mesmo JSON para a
    fila `run_results` e refazia o dumps — CPU pura, síncrona, com o event loop
    do worker inteiro parado. Serializar uma vez e reaproveitar corta isso pela
    metade sem mudar nenhum limite.
    """
    capped = dict(msg)

    error = capped.get("error")
    if error is not None:
        # Um executor comprometido manda o que quiser aqui: dict/list passavam
        # inteiros para `error_message` (Text, sem limite no Postgres).
        if not isinstance(error, str):
            error = repr(error)
        if len(error) > _MAX_JOB_ERROR_CHARS:
            logger.warning(
                "Executor '%s': campo 'error' do job_result com %d chars (job=%s) "
                "excede o teto de %d — truncado.",
                executor_id, len(error), capped.get("job_id"), _MAX_JOB_ERROR_CHARS,
            )
            error = error[:_MAX_JOB_ERROR_CHARS] + "…[truncado pelo servidor]"
        capped["error"] = error

    stats = capped.get("stats")
    if stats is None:
        return capped, "{}"

    if not isinstance(stats, dict):
        logger.warning(
            "Executor '%s': 'stats' do job_result veio como %s (esperado objeto) "
            "— descartado.", executor_id, type(stats).__name__,
        )
        capped["stats"] = {}
        return capped, "{}"

    try:
        stats_json = json.dumps(stats, default=str)
    except (TypeError, ValueError):
        # Recursivo/não serializável: o consumer estouraria na hora do
        # json.dumps do run_results e a mensagem viraria erro silencioso.
        logger.warning(
            "Executor '%s': 'stats' do job_result não é serializável — descartado.",
            executor_id,
        )
        capped["stats"] = {STATS_TRUNCADO: True, STATS_CONTROLE_DESCARTADO: True}
        return capped, json.dumps(capped["stats"])

    size = len(stats_json)
    if size > _MAX_JOB_STATS_BYTES:
        # A régua daqui é só `stats`, contra o teto do que o servidor guarda.
        reduced, stats_json, preservou = reduzir_stats(
            stats, size, _MAX_JOB_STATS_BYTES, lambda s: json.dumps(s, default=str),
        )
        if preservou:
            logger.warning(
                "Executor '%s': 'stats' do job_result com %d bytes (job=%s) excede o "
                "teto de %d — stats por-nó removidos, chaves de controle preservadas.",
                executor_id, size, capped.get("job_id"), _MAX_JOB_STATS_BYTES,
            )
        else:
            logger.warning(
                "Executor '%s': 'stats' do job_result com %d bytes (job=%s) excede o "
                "teto de %d mesmo preservando as chaves de controle — descartado.",
                executor_id, size, capped.get("job_id"), _MAX_JOB_STATS_BYTES,
            )
        capped["stats"] = reduced

    return capped, stats_json
