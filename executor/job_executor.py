# executor/job_executor.py
"""
Executor de jobs do executor.

Responsabilidades:
  1. Validar o job (job_validator.validate_job)
  2. Descriptografar o payload em memória (executor/crypto.py)
  3. Executar o flow/ localmente com timeout
  4. Limpar referências sensíveis após execução
  5. Retornar o resultado (dict) para envio ao servidor
"""
import asyncio
import json
import logging
import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse

from executor import config
from executor.crypto import decrypt_job_payload, load_private_key
from executor.job_validator import JobValidationError, validate_job

logger = logging.getLogger(__name__)

# ─── Setup de import do flow engine (1x no import do módulo) ──────────────────
# O executor roda em um processo separado; flow/ está no diretório-pai. Antes, o
# path era ajustado e o import era feito dentro de _run_workflow — isso causava
# re-scan do registry de nós (~60 módulos via importlib) em cada job.
#
# Fazendo aqui no top-level, o custo é pago uma vez no startup do executor e todo
# job subsequente reusa o cache de módulos do Python.
_AGENT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AGENT_ROOT not in sys.path:
    sys.path.insert(0, _AGENT_ROOT)

# ARTIFACT_DIR precisa estar no env ANTES de importar flow/nodes (o fallback local
# de artefatos em flow/utils/artifact_helpers.py lê a variável). setdefault
# preserva valor já set via docker-compose.
os.environ.setdefault("ARTIFACT_DIR", config.ARTIFACTS_DIR)

# Imports do flow engine — feitos 1x no startup do executor em vez de por job.
from flow.executor import WorkflowExecutor  # type: ignore  # noqa: E402
from flow.executor.result_helpers import collect_artifacts, collect_response  # noqa: E402
from executor.event_publisher import ExecutorEventPublisher  # noqa: E402

# Chave privada carregada uma vez na inicialização do módulo
_agent_private_key = None

# SEG: o cache anti-replay (`_nonce_seen`, em job_validator) é um check-and-set
# num OrderedDict de módulo. Enquanto a validação rodava no event loop, o próprio
# loop serializava esse par de operações de graça; agora ela roda no pool de
# threads, e sem este lock dois jobs concorrentes poderiam intercalar checagem e
# registro do MESMO nonce e ambos passarem — um replay aceito. O custo é nulo:
# está fora do caminho de dados e a validação leva milissegundos.
_VALIDACAO_LOCK = threading.Lock()

# Pool DEDICADO ao plano de controle (validacao de assinatura + descriptografia
# do envelope). NAO e o pool default do loop, que e onde rodam os nos — inclusive
# o PythonScript, que executa codigo arbitrario do usuario.
#
# O motivo e concreto: `asyncio.to_thread` NAO cancela nada. Um PythonScript com
# `while True: pass` (que passa pelo validate_code_ast) estoura o
# `asyncio.wait_for` do no, libera o slot do job e deixa a THREAD viva para
# sempre. Poucas execucoes assim ocupam todos os workers do pool default; se a
# validacao morasse la, o executor parava de conseguir sequer ACEITAR ou RECUSAR
# um job — nenhum node_event, nenhum job_result, o run pendurado em "running"
# ate o servidor marca-lo como orfao. Aqui a recepcao de trabalho fica imune a
# no travado.
#
# Dois workers bastam: a validacao leva milissegundos e e serializada pelo
# _VALIDACAO_LOCK de qualquer forma.
_CONTROL_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="atlas-ctrl")


def _validar_e_descriptografar(message: dict) -> dict:
    """Assinatura Ed25519 + anti-replay + descriptografia, fora do event loop.

    Roda inteiro numa thread (ver `execute_job`). Vale a pena mesmo com a GIL:
    `verify`/`decrypt` do `cryptography` são OpenSSL e LIBERAM a GIL, então o
    trabalho realmente sai do loop. Antes, um job com definição grande
    (sub-fluxos pré-resolvidos + pinned_outputs) deixava o executor mudo por
    centenas de milissegundos ANTES do primeiro node_event — e, com jobs em
    rajada, as pausas se somavam na frente do heartbeat e dos eventos dos jobs
    já em andamento.
    """
    with _VALIDACAO_LOCK:
        validate_job(message)
    if _agent_private_key is None:
        raise RuntimeError("Chave privada não inicializada. Chame init_private_key() no startup.")
    return decrypt_job_payload(message, _agent_private_key)


def init_private_key():
    """Carrega a chave privada X25519 do executor. Deve ser chamado no startup.

    Usa `load_private_key` (somente leitura): se a chave do enrollment sumiu, o
    startup falha alto com instrucao de refazer o enroll em vez de gerar um par
    novo — que faria o executor subir "online" e derrubar 100% dos jobs.
    """
    global _agent_private_key
    _agent_private_key = load_private_key(
        key_b64=config.EXECUTOR_PRIVATE_KEY,
        key_path=config.EXECUTOR_PRIVATE_KEY_PATH,
    )
    logger.info("Chave privada X25519 do executor carregada.")


def _error_result(job_id, run_id, error: str, category: str, stats: dict | None = None) -> dict:
    """Monta o resultado de falha com a taxonomia (category + retryable).

    `stats` carrega o que ja foi executado antes da falha (node_stats parciais +
    __metrics__). Sem isso o servidor sobrescrevia node_stats com {} — o painel
    perdia os nos que rodaram, workflow_run_metrics/node_run_metrics ficavam sem
    linha nenhuma e, porque o upsert de UsageDaily vive dentro de
    _persist_metrics, falha nenhuma era contabilizada: o dashboard mostrava taxa
    de erro 0% permanente.
    """
    from flow.utils.error_taxonomy import is_retryable
    return {
        "job_id": job_id, "run_id": run_id, "status": "error", "output": None,
        "stats": stats or {},
        "error": error, "error_category": category, "retryable": is_retryable(category),
    }


# ── Tetos do payload de stats ────────────────────────────────────────────────
# Limitar aqui, na ORIGEM, e nao na hora de serializar. `_dumps_result` media o
# tamanho fazendo `json.dumps` do job_result INTEIRO (ate 16 MB) — e ate tres
# vezes, quando estourava — dentro do event loop, justamente no instante em que
# o workflow termina: heartbeat atrasava, os node_events dos outros jobs paravam
# de subir e o `cancel` que o usuario acabou de clicar nao era lido. Com o
# payload limitado por construcao, aquele caminho vira o que devia ter sido
# desde sempre: uma rede de seguranca que na pratica nunca dispara.
#
# As chaves de controle (__response__/__artifacts__/__metrics__/
# __updated_pinned_outputs__) NAO entram no corte: sem __response__ o BRPOP do
# webhook sincrono fica preso, e as demais alimentam metricas e pins.
_MAX_NODE_STAT_BYTES  = 8 * 1024
_MAX_NODE_STATS_BYTES = 4 * 1024 * 1024
_MAX_STAT_ERROR_CHARS = 2_000
# Teto REDUZIDO de colunas por porta quando o stat estoura _MAX_NODE_STAT_BYTES.
# A origem ja corta em MAX_COLUNAS (200 — flow/executor/utils.py); descartar o
# resto de uma vez era tudo-ou-nada: quanto mais larga a tabela, mais certo o
# descarte, e o editor ficava sem sugestao de coluna exatamente onde ela mais
# vale. As 50 primeiras cabem com folga no teto e ainda alimentam a sugestao.
_MAX_STAT_COLUNAS_POR_PORTA = 50
# Campos sem os quais a linha de node_run_metrics deixa de servir para o painel.
_STAT_CAMPOS_ESSENCIAIS = (
    "node_name", "duration_ms", "status", "cache_hit", "started_at",
    "input_features", "output_features",
)


def _tamanho_json(obj) -> int:
    """Tamanho serializado aproximado, em bytes. `default=str` nunca levanta."""
    try:
        return len(json.dumps(obj, default=str))
    except Exception:
        return _MAX_NODE_STAT_BYTES + 1  # ilegivel = trata como grande demais


def _reduzir_stat_de_no(stat: dict) -> dict:
    """Degrada o stat de um no em degraus, do corte mais barato ao mais cru.

    Ordem: (1) mensagem de erro truncada; (2) cada lista de output_columns
    truncada as _MAX_STAT_COLUNAS_POR_PORTA primeiras; (3) output_columns
    descartado; (4) so os campos essenciais. Cada degrau re-mede e para assim
    que couber — descartar as colunas por inteiro, que era o primeiro corte,
    virou penultimo recurso: elas alimentam a sugestao de coluna do editor.
    O corte e marcado com o `__truncated__` do stat, como os demais; a lista
    truncada NAO ganha item-marcador (mesma regra de `_colunas_das_saidas`:
    a UI renderia o marcador como sugestao clicavel).
    """
    reduzido = dict(stat)
    reduzido["__truncated__"] = True

    erro = reduzido.get("error")
    if isinstance(erro, str) and len(erro) > _MAX_STAT_ERROR_CHARS:
        reduzido["error"] = erro[:_MAX_STAT_ERROR_CHARS] + "…[truncado]"
        if _tamanho_json(reduzido) <= _MAX_NODE_STAT_BYTES:
            return reduzido

    colunas = reduzido.get("output_columns")
    if isinstance(colunas, dict) and any(
        isinstance(lista, list) and len(lista) > _MAX_STAT_COLUNAS_POR_PORTA
        for lista in colunas.values()
    ):
        reduzido["output_columns"] = {
            porta: lista[:_MAX_STAT_COLUNAS_POR_PORTA] if isinstance(lista, list) else lista
            for porta, lista in colunas.items()
        }
        if _tamanho_json(reduzido) <= _MAX_NODE_STAT_BYTES:
            return reduzido

    reduzido.pop("output_columns", None)
    if _tamanho_json(reduzido) <= _MAX_NODE_STAT_BYTES:
        return reduzido
    # Ultimo recurso: so o que o painel de nos precisa para desenhar a linha.
    essencial = {k: reduzido.get(k) for k in _STAT_CAMPOS_ESSENCIAIS if k in reduzido}
    essencial["__truncated__"] = True
    return essencial


def _limitar_node_stats(node_stats: dict) -> dict:
    """Aplica teto por no e teto agregado ao node_stats, preservando a ordem."""
    limitado: dict = {}
    total = 0
    omitidos = 0
    for node_id, stat in (node_stats or {}).items():
        if omitidos:
            omitidos += 1
            continue
        if not isinstance(stat, dict):
            limitado[node_id] = stat
            continue
        tamanho = _tamanho_json(stat)
        if tamanho > _MAX_NODE_STAT_BYTES:
            stat = _reduzir_stat_de_no(stat)
            tamanho = _tamanho_json(stat)
        if total + tamanho > _MAX_NODE_STATS_BYTES:
            omitidos = 1
            continue
        total += tamanho
        limitado[node_id] = stat
    if omitidos:
        logger.warning(
            "node_stats excedeu %d bytes — %d no(s) omitido(s) do resultado.",
            _MAX_NODE_STATS_BYTES, omitidos,
        )
        limitado["__truncated__"] = True
        limitado["__nodes_omitidos__"] = omitidos
    return limitado


def _collect_stats(executor, status: str) -> dict:
    """
    Monta o dict de stats a partir do estado ATUAL do WorkflowExecutor.

    Usado tanto no caminho de sucesso quanto no de falha — em falha os dados sao
    parciais (so os nos que chegaram a rodar), e parcial vale muito mais que
    vazio: e o que alimenta o painel de nos e as tabelas *_run_metrics.
    Cada coleta e isolada: um erro montando artefatos nao pode custar as metricas
    (nem, no caminho de erro, mascarar a excecao original).

    O node_stats sai daqui JA limitado (ver `_limitar_node_stats`) — o tamanho do
    job_result nao pode depender de quantos nos o workflow tem.
    """
    stats: dict = _limitar_node_stats(executor.node_stats)

    try:
        artifacts = collect_artifacts(executor.final_outputs)
        if artifacts:
            stats["__artifacts__"] = artifacts
        response = collect_response(executor.final_outputs)
        if response:
            stats["__response__"] = response
    except Exception as exc:
        logger.warning("Falha ao coletar artefatos/resposta (status=%s): %s", status, exc)

    # Metricas de execucao (CPU, RAM, bytes, spatial). O status do run nao vai
    # aqui: o servidor grava o do proprio WorkflowRun.
    try:
        stats["__metrics__"] = executor.metrics_collector.build_metrics()
    except Exception as exc:
        logger.warning("Falha ao coletar metricas (status=%s): %s", status, exc)

    # Referencias S3 leves dos pins GRAVADOS NESTA RUN (auto-pin). Reportar
    # `pinned_outputs` inteiro — como era feito — incluia as refs que vieram do
    # servidor e apenas passaram pela run; o consumer re-deriva a s3_key com o
    # task_id ATUAL, entao cada run corrompia as refs que nao regravou,
    # apontando-as para objetos inexistentes (404 permanente no pin).
    try:
        updated_pins = {nid: out for nid, out in getattr(executor, "updated_pin_refs", {}).items()
                        if out and isinstance(out, dict) and "__pin_s3_key__" in out}
        if updated_pins:
            stats["__updated_pinned_outputs__"] = updated_pins
    except Exception as exc:
        logger.warning("Falha ao coletar pins atualizados: %s", exc)

    return stats


def _partial_stats(holder: dict, status: str) -> dict:
    """
    Stats parciais do executor que estava rodando quando o job morreu.

    `holder` e preenchido por `_run_workflow` ANTES do `executor.run()`, entao o
    WorkflowExecutor continua alcancavel mesmo quando a corrotina e destruida —
    inclusive no timeout, em que o prazo (`asyncio.timeout`) a cancela e nada e
    retornado. Vazio quando a falha aconteceu antes de existir executor
    (validacao, decrypt, job_type desconhecido).
    """
    executor = holder.get("executor")
    if executor is None:
        return {}
    try:
        return _collect_stats(executor, status=status)
    except Exception as exc:
        logger.warning("Falha ao coletar stats parciais (status=%s): %s", status, exc)
        return {}


async def execute_job(message: dict, event_queue: asyncio.Queue | None = None) -> dict:
    """
    Ponto de entrada principal para execução de um job.

    Retorna dict com:
      {
        "job_id":  str,
        "run_id":  str | None,
        "status":  "ok" | "error",
        "output":  any,        # resultado do flow (se ok)
        "stats":   dict,       # node_stats + __metrics__/__artifacts__/...
        "error":   str | None, # mensagem de erro (se error)
      }

    "stats" vem preenchido TAMBEM quando o job falha ou estoura o timeout (com
    os nos que chegaram a rodar) — o servidor sobrescreve node_stats com o que
    vier aqui e alimenta workflow_run_metrics/UsageDaily a partir de
    __metrics__. So fica vazio quando a falha antecede a execucao (validacao,
    descriptografia, job_type desconhecido).
    """
    envelope = message.get("envelope", {})
    job_id   = envelope.get("job_id", "?")
    # run_id é extraído do payload descriptografado; até lá usa job_id como fallback,
    # pois o servidor define run_id == job_id ao despachar para o executor.
    run_id   = job_id
    payload  = None
    # Holder mutavel: `_run_workflow` publica aqui o WorkflowExecutor assim que o
    # cria, para que os caminhos de erro/timeout alcancem os stats parciais.
    stats_holder: dict = {}
    # Marcado antes do try, e nao logo antes do prazo: a duracao do log de
    # conclusao inclui a validacao e a descriptografia.
    _t0 = time.monotonic()

    try:
        # ── 1 e 2. Validação de segurança + descriptografia, numa thread ──────
        # A ordem interna continua a mesma (assinatura → destinatário → prazo →
        # nonce → decrypt): quem garante isso é `_validar_e_descriptografar`.
        logger.debug("Job '%s': validando assinatura e descriptografando payload.", job_id)
        # run_in_executor(_CONTROL_POOL, ...) e nao asyncio.to_thread: to_thread
        # cai no pool DEFAULT, o mesmo dos nos e do script do usuario. Ver
        # _CONTROL_POOL — um PythonScript em laco infinito nao pode impedir o
        # executor de aceitar/recusar o proximo job.
        payload = await asyncio.get_running_loop().run_in_executor(
            _CONTROL_POOL, _validar_e_descriptografar, message
        )
        run_id  = payload.get("run_id") or job_id
        logger.debug("Job '%s': payload descriptografado (run_id=%s).", job_id, run_id)

        job_type = envelope.get("job_type", "")
        logger.info("Job '%s': iniciando execução (type=%s, run_id=%s, timeout=%ds).",
                    job_id, job_type, run_id, config.JOB_TIMEOUT)

        # ── 3. Execução com timeout ───────────────────────────────────────────
        # `asyncio.timeout` e não `wait_for`: do Python 3.11 em diante
        # `asyncio.TimeoutError` É o TimeoutError embutido, e um nó que levanta
        # o dele (o prazo do PythonScript, um socket que expira) cairia no
        # tratamento do prazo do JOB — "Job expirou após 3600s" no lugar da
        # mensagem do nó. Só é o prazo do job se ele expirou; o resto sobe para
        # o `except Exception`, como no 3.10.
        prazo = asyncio.timeout(config.JOB_TIMEOUT)
        try:
            async with prazo:
                dispatch_result = await _dispatch(
                    job_type, payload, envelope,
                    event_queue=event_queue, stats_holder=stats_holder,
                )
        except TimeoutError:
            if not prazo.expired():
                raise
            msg = f"Job expirou após {config.JOB_TIMEOUT}s."
            logger.error("Job '%s': timeout — %s", job_id, msg)
            return _error_result(job_id, run_id, msg, "timeout",
                                 stats=_partial_stats(stats_holder, "timeout"))
        _elapsed = time.monotonic() - _t0

        # _dispatch retorna {"result": ..., "stats": ...} para run_workflow;
        # outros tipos podem retornar o valor direto — trata ambos os casos.
        if isinstance(dispatch_result, dict) and "stats" in dispatch_result:
            output = dispatch_result.get("result")
            stats  = dispatch_result.get("stats") or {}
        else:
            output = dispatch_result
            stats  = {}

        logger.info("Job '%s' concluído em %.1fs (run_id=%s).", job_id, _elapsed, run_id)
        return {"job_id": job_id, "run_id": run_id, "status": "ok", "output": output,
                "stats": stats, "error": None}

    except JobValidationError as exc:
        # Rejeitado antes de existir executor — nao ha stats parciais a coletar.
        logger.error("Job '%s' reprovado na validação de segurança: %s", job_id, exc)
        return _error_result(job_id, run_id, str(exc), "validation")

    except Exception as exc:
        from flow.utils.error_taxonomy import classify_error
        category = classify_error(exc)
        logger.error("Job '%s' falhou (category=%s): %s", job_id, category, exc, exc_info=True)
        return _error_result(job_id, run_id, str(exc), category,
                             stats=_partial_stats(stats_holder, "error"))

    finally:
        # ── 4. Limpeza de memória ─────────────────────────────────────────────
        # Solta a referencia do executor para o payload descriptografado. NAO e
        # um "apagar da memoria": sub-objetos ainda referenciados por nos que
        # rodaram (ex: connectionString ja copiada para dentro de um node)
        # continuam vivos. O que isso garante e que este dict nao segure sozinho
        # o payload inteiro depois do job terminar.
        #
        # Nao chamamos gc.collect(): rodava geracao 2 em TODO job (inclusive nas
        # saidas antecipadas por JobValidationError), na corrotina e segurando a
        # GIL — travando as threads de to_thread dos jobs concorrentes — sem
        # ganho algum, ja que o objeto grande (final_outputs) esta vivo no valor
        # de retorno e o payload sai por refcount.
        if payload is not None:
            payload.clear()
            del payload


async def _dispatch(job_type: str, payload: dict, envelope: dict,
                    event_queue: asyncio.Queue | None = None,
                    stats_holder: dict | None = None) -> any:
    """
    Roteia o job para o handler correto com base em job_type.

    job_type suportados:
      "run_workflow" — executa um workflow do flow/ engine localmente
    """
    if job_type == "run_workflow":
        return await _run_workflow(payload, envelope, event_queue=event_queue,
                                   stats_holder=stats_holder)

    raise ValueError(f"Tipo de job desconhecido: '{job_type}'")


def _apply_host_aliases(conn_str: str) -> str:
    """
    Reescreve hostname (e porta) de uma connection string usando HOST_ALIASES.
    Ex: "postgresql+asyncpg://user:pass@db:5432/geobd"  # pragma: allowlist secret
        com alias db=localhost:5433
     → "postgresql+asyncpg://user:pass@localhost:5433/geobd"  # pragma: allowlist secret
    """
    if not config.HOST_ALIASES or not conn_str:
        return conn_str
    try:
        parsed = urlparse(conn_str)
        internal_host = parsed.hostname
        if internal_host and internal_host in config.HOST_ALIASES:
            external = config.HOST_ALIASES[internal_host]
            # Reconstrói netloc preservando userinfo (user:pass@)
            netloc = parsed.netloc
            at_idx = netloc.rfind("@")
            userinfo = netloc[:at_idx + 1] if at_idx >= 0 else ""
            if ":" in external:
                new_netloc = f"{userinfo}{external}"
            else:
                port_part = f":{parsed.port}" if parsed.port else ""
                new_netloc = f"{userinfo}{external}{port_part}"
            conn_str = urlunparse(parsed._replace(netloc=new_netloc))
            logger.debug("connectionString reescrito: %s → %s (alias %s=%s)",
                         internal_host, external, internal_host, external)
    except Exception as exc:
        logger.warning("Falha ao reescrever connectionString: %s", exc)
    return conn_str


def _rewrite_connection_strings(workflow_def: dict) -> None:
    """
    Percorre os nós do workflow e aplica HOST_ALIASES em todos os connectionStrings.
    Necessário quando o executor roda fora do Docker e as credenciais usam
    hostnames internos (ex: 'db') que não são resolvíveis externamente.
    """
    if not config.HOST_ALIASES:
        return
    for node in workflow_def.get("nodes", []):
        props = (node.get("data", {}) or {}).get("properties") or node.get("properties") or {}
        if "connectionString" in props and isinstance(props["connectionString"], str):
            props["connectionString"] = _apply_host_aliases(props["connectionString"])



async def _run_workflow(payload: dict, envelope: dict,
                        event_queue: asyncio.Queue | None = None,
                        stats_holder: dict | None = None) -> dict:
    """
    Executa um workflow localmente usando o flow/ engine (WorkflowExecutor).

    `stats_holder` (opcional) recebe o WorkflowExecutor assim que ele e criado
    — ver `_partial_stats`.

    O payload deve conter:
      {
        "workflow_definition": dict,  — definição do DAG (nós, arestas, config)
        "run_id":              str,   — UUID do WorkflowRun para reporting
        "params":              dict,  — parâmetros de entrada (opcional)
        "workspace_id":        str,   — workspace_id para isolamento (opcional)
        "debug_mode":          bool,  — modo debug (opcional)
      }
    """
    workflow_def = payload.get("workflow_definition")
    if not workflow_def:
        raise ValueError("Payload sem 'workflow_definition'.")

    # Reescreve hostnames internos do Docker nos connectionStrings (ex: db → localhost:5433)
    _rewrite_connection_strings(workflow_def)

    params         = payload.get("params") or {}
    run_id         = payload.get("run_id") or envelope.get("job_id")
    workspace_id   = payload.get("workspace_id")
    workflow_hash  = payload.get("workflow_hash")
    debug_mode     = payload.get("debug_mode", False)
    pinned_outputs = payload.get("pinned_outputs") or {}
    pin_metadata   = payload.get("pin_metadata") or {}
    # Snapshot dos nodes desabilitados no momento do despacho. Usado pelo
    # SubWorkflowNode para validar sub-fluxos no executor sem consultar o DB.
    disabled_nodes = payload.get("disabled_nodes") or []
    # Definitions de toda a cadeia de sub-workflows pre-resolvida pelo
    # servidor (executor nao tem acesso ao DB).
    subworkflow_definitions = payload.get("subworkflow_definitions") or {}

    n_nodes = len(workflow_def.get("nodes", []))
    n_edges = len(workflow_def.get("edges", []))
    logger.info("Workflow: %d nós, %d arestas (run_id=%s, workspace=%s).",
                n_nodes, n_edges, run_id, workspace_id)

    publisher = None
    if event_queue is not None:
        publisher = ExecutorEventPublisher(event_queue)

    executor = WorkflowExecutor(
        definition=workflow_def,
        task_id=run_id,
        publisher=publisher,
        debug_mode=debug_mode,
        workspace_id=workspace_id,
        workflow_hash=workflow_hash,
        pinned_outputs=pinned_outputs,
        pin_metadata=pin_metadata,
        disabled_nodes=disabled_nodes,
        subworkflow_definitions=subworkflow_definitions,
    )

    # Publica o executor ANTES de rodar: se a corrotina morrer (excecao ou
    # cancelamento pelo prazo do job, `asyncio.timeout`), ela nao retorna nada, e
    # este e o unico caminho para `execute_job` alcancar os stats dos nos que
    # ja tinham rodado.
    if stats_holder is not None:
        stats_holder["executor"] = executor

    logger.info("Ordem de execução calculada: %s", executor.execution_order)

    result = await executor.run(initial_inputs=params)
    logger.info("Workflow concluído. Nós executados: %d.", len(executor.node_stats))

    stats = _collect_stats(executor, status="success")
    return {"result": result, "stats": stats}
