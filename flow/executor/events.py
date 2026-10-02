# flow/executor/events.py
"""Publicação de eventos de execução de nós."""
import time
from typing import Dict, Any
from flow.executor.utils import _build_debug_summary
from flow.utils.error_taxonomy import classify_error, is_retryable
from flow.utils.logger import get_logger
from flow.utils.publisher.events import (
    KIND_LIFECYCLE, KIND_DEBUG,
    LEVEL_INFO, LEVEL_WARN, LEVEL_ERROR,
)

logger = get_logger(__name__)


def publish_started(publisher, task_id: str, node_id: str, node_defs: Dict[str, Any]) -> None:
    try:
        node_def = node_defs.get(node_id, {})
        extra = {
            "node_name": node_def.get("name", node_id),
            "node_type": node_def.get("type", ""),
            # Denominador do progresso ("nó 7 de 12"). Reafirmado a cada nó, de
            # modo que um evento perdido no caminho não deixa o painel sem ele.
            "nodes_total": len(node_defs),
        }
        publisher.publish_event(
            task_id, node_id, "started", time.time(), extra=extra,
            kind=KIND_LIFECYCLE, level=LEVEL_INFO,
        )
    except Exception:
        logger.warning("Não foi possível publicar evento 'started' para %s", node_id)


def publish_completed(
    publisher,
    task_id: str,
    node_id: str,
    node_defs: Dict[str, Any],
    status: str,
    duration_ms: float,
    error: str = None,
    output_keys: list = None,
    output_columns: dict = None,
    branch_result: "bool | None" = None,
    cache_hit: "bool | None" = None,
    traceback_str: "str | None" = None,
    schema_drift: "dict | None" = None,
    exception: "BaseException | None" = None,
) -> None:
    try:
        node_def = node_defs.get(node_id, {})
        extra = {
            "node_name": node_def.get("name", node_id),
            "node_type": node_def.get("type", ""),
        }
        if output_keys is not None:
            extra["output_keys"] = output_keys
        # Colunas de cada saida. Vai junto do evento (e nao so no node_stats
        # persistido) para o editor ter sugestao de nome de coluna assim que o
        # run termina, sem uma segunda ida ao servidor. Num evento acima do teto
        # do protocolo ela sobrevive: a reducao (flow/utils/publisher/reducao.py)
        # corta antes o traceback e o schema_drift — chave pesada nova neste
        # `extra` entra em CHAVES_PESADAS_DO_EXTRA de la.
        if output_columns:
            extra["output_columns"] = output_columns
        if branch_result is not None:
            extra["branch_result"] = branch_result
        if cache_hit is not None:
            extra["cache_hit"] = cache_hit
        if traceback_str:
            extra["traceback"] = traceback_str
        if schema_drift:
            extra["schema_drift"] = schema_drift

        # Categoria de erro POR NÓ. A taxonomia já existia para o job inteiro
        # (executor → servidor); publicá-la aqui é o que permite o painel dizer
        # "entrada inválida, repetir não resolve" em vez de só cuspir o stack.
        if status == "failed" and exception is not None:
            category = classify_error(exception)
            extra["error_category"] = category
            extra["retryable"] = is_retryable(category)

        if status == "failed":
            level = LEVEL_ERROR
        elif schema_drift:
            level = LEVEL_WARN
        else:
            level = LEVEL_INFO

        publisher.publish_event(
            task_id, node_id, status, time.time(), duration_ms, error, extra,
            kind=KIND_LIFECYCLE, level=level,
        )
    except Exception:
        logger.warning("Não foi possível publicar evento '%s' para %s", status, node_id)


def publish_debug(
    publisher,
    task_id: str,
    node_id: str,
    node_defs: Dict[str, Any],
    inputs: dict,
    outputs: dict,
) -> None:
    try:
        node_def = node_defs.get(node_id, {})
        in_summary  = {f"in:{k}":  v for k, v in _build_debug_summary(inputs).items()}
        out_summary = {f"out:{k}": v for k, v in _build_debug_summary(outputs).items()}
        publisher.publish_event(
            run_id=task_id,
            node=node_id,
            status="debug",
            timestamp=time.time(),
            extra={
                "node_name": node_def.get("name", node_id),
                "node_type": node_def.get("type", ""),
                "debug_output": {**in_summary, **out_summary},
            },
            kind=KIND_DEBUG,
            level=LEVEL_INFO,
        )
    except Exception as e:
        logger.warning("[debug_mode] Falha ao publicar evento debug para %s: %s", node_id, e)
