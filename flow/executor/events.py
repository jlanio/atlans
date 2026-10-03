# flow/executor/events.py
"""Publishing of node execution events."""
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
            # Progress denominator ("node 7 of 12"). Restated on every node,
            # so that an event lost along the way does not leave the panel without it.
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
        # Columns of each output. Goes along with the event (and not only in the
        # persisted node_stats) so the editor has column name suggestions as soon as
        # the run finishes, without a second trip to the server. In an event above the
        # protocol ceiling it survives: the reduction (flow/utils/publisher/reducao.py)
        # cuts the traceback and schema_drift first — a new heavy key in this
        # `extra` goes into CHAVES_PESADAS_DO_EXTRA there.
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

        # Error category PER NODE. The taxonomy already existed for the whole job
        # (executor → server); publishing it here is what lets the panel say
        # "invalid input, retrying will not help" instead of just spitting out the stack.
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
