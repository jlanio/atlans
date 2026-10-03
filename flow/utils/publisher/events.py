from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Sequence

from flow.utils.logger import get_logger

logger = get_logger(__name__)

# ── Event vocabulary ─────────────────────────────────────────────────────────
#
# `status` describes the node's LIFECYCLE and nothing else. The message's severity
# and origin travel in their own fields (`level` and `kind`) — before, everything
# was piled into `status` ("started"/"completed"/"failed" alongside "debug" and
# "log"), which forced the run panel to filter by negation ("everything that is
# neither an error nor a print") and made it impossible to tell stdout from lifecycle.

KIND_LIFECYCLE = "lifecycle"   # started / completed / failed of a node
KIND_STDOUT    = "stdout"      # print() line captured from inside the node
KIND_DEBUG     = "debug"       # resumo de inputs/outputs (debug mode)

LEVEL_INFO  = "info"
LEVEL_WARN  = "warn"
LEVEL_ERROR = "error"


class WorkflowEventPublisher(ABC):
    """
    Abstract interface for publishing workflow events.
    Every event must have the same JSON structure:
      {
        "run_id": str,
        "node": str,                  # node id or "__workflow_complete__"
        "kind": str,                  # "lifecycle" | "stdout" | "debug"
        "level": str,                 # "info" | "warn" | "error"
        "status": str,                # "started" | "completed" | "failed"
        "timestamp": float,           # epoch seconds UTC
        "duration_ms": Optional[float], # only on completed/failed
        "error": Optional[str],       # only on failed
        "extra": Optional[dict]       # any other metadata (branch, overhead…)
      }
    """
    @abstractmethod
    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Optional[float] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        """
        :param run_id:      run identifier
        :param node:        node identifier (or '__workflow_complete__')
        :param status:      "started", "completed" or "failed"
        :param timestamp:   moment of the event (in seconds since epoch UTC). If None, it is filled in automatically.
        :param duration_ms: node duration in ms (for completed/failed)
        :param error:       string with stack/message if it failed
        :param extra:       other data (e.g. branch, overhead_ms…)
        :param kind:        origin of the line — lifecycle / stdout / debug
        :param level:       severity — info / warn / error
        """
        ...


def publish_stdout(publisher, run_id: str, node_id: str, lines: Sequence[str]) -> None:
    """Publishes a BATCH of print() lines captured from inside a node.

    kind=stdout is what separates this from the lifecycle: in the run panel the
    user's output lives in its own tab, grouped by node, with no icon/status/
    duration per line (a print has none of those three things).

    The batch is the point: one event PER LINE made `for i in range(50000): print(i)`
    overflow the 500-slot queue — which is shared by all jobs and by
    GeoSync — and the server's rate limit, taking down telemetry of OTHER
    workflows along with it. The emitter does the aggregation (PythonScript's
    `_LoggingStream`), closing the batch every ~200 ms or every N lines.

    `extra['lines']` is the ONLY source of truth (one entry per printed line).
    There is no `extra['message']` anymore: publishing the same text twice doubled
    the payload, and a batch of 200 lines of ~160 characters exceeded the 64 KB of
    `TETO_NODE_EVENT_BYTES` (flow/utils/publisher/reducao.py); the sender then
    reduced the event to the control fields — which did not include `extra` — and
    the panel lost all 200 lines at once, silently. Today the reduction keeps the
    prefix of `lines` that fits, but the batch still has to fit whole. Consumers
    read `lines` and join with \\n if they need text.

    Lives here, and not in flow/executor/events.py, because the caller is a node —
    importing the `flow.executor` package from inside `flow.nodes` would close the
    executor → registry → nodes → executor cycle.
    """
    if not (publisher and run_id and lines):
        return
    linhas = list(lines)
    try:
        publisher.publish_event(
            run_id=run_id,
            node=node_id,
            status="log",
            extra={"lines": linhas},
            kind=KIND_STDOUT,
            level=LEVEL_INFO,
        )
    except Exception as exc:
        # Publishing output must never bring down the user's script execution —
        # but swallowing without a trace would hide a broken publisher.
        logger.debug("Falha ao publicar stdout do nó %s: %s", node_id, exc)
