# flow/executor/core.py
"""Main workflow orchestrator."""
import time
import asyncio
import traceback as _traceback
from datetime import datetime
from collections import defaultdict, deque
from typing import Optional, Dict, Any

from flow.utils.datetime_utils import utc_from_timestamp_naive, utc_now_naive
from flow.utils.logger import get_logger
from flow.utils.publisher.events import WorkflowEventPublisher
from flow.metrics.collector import MetricsCollector
from flow.core.graph import WorkflowGraph
# The alias rule lives in flow/core/aliases.py (pure) so that the static lint
# applies the SAME one without pulling in the node registry. The underscored
# name still exists here: tests/unit/test_alias_expressions.py imports
# `_resolve_alias` from flow.executor.core.
from flow.core.aliases import resolve_alias as _resolve_alias
from flow.executor.declared_schema import schema_declarado, schema_do_catalogo
from flow.utils.parameter_validation import validate_node_parameters
from flow.utils.safe_env import safe_env

from flow.executor.node_manager import NodeManager
from flow.executor.utils import _count_gdf_features, _colunas_das_saidas, _build_debug_summary
from flow.executor.spill import _spill_to_disk, _load_from_disk, _cleanup_spill, _delete_spill_files
from flow.executor.rendering import expr_svc, render_node_parameters
from flow.executor.edge_resolver import Edge, resolve_edge_inputs, resolve_edge_schema_inputs
from flow.utils.error_taxonomy import classify_error, is_retryable
import flow.executor.pin as _pin
import flow.executor.events as _events


class _LazySummary:
    """Defers summarizing an inputs/outputs dict until the log is actually emitted.

    `logging` only calls `__str__` on a `%s` argument when some handler
    accepts the record. The executor used to log `f"... com inputs {inputs}"`: the
    f-string is interpolated EAGERLY, once per node, inside the event loop, even
    with the level above DEBUG. Since `http_request` returns the raw
    `response.json()` and `python_script` returns any user object, a payload of
    tens of MB turned into seconds of CPU and hundreds of MB of peak memory just
    to build a string nobody was going to read.
    """
    __slots__ = ("_data",)

    def __init__(self, data: Any) -> None:
        self._data = data

    def __str__(self) -> str:
        if not isinstance(self._data, dict):
            return f"<{type(self._data).__name__}>"
        # Summarizes per key (count/columns for tabular data, 300 chars for
        # scalars). `with_bounds=False` takes `total_bounds` off the logging
        # path: it is an O(n) scan over all geometries (13.6 ms on a GDF
        # of 300k features) that is only justified in the debug event, which is
        # opt-in via `debug_mode`.
        # It is not zero-cost: nested dicts and lists still go through
        # json.dumps. What is guaranteed is that none of this runs with the level
        # above DEBUG, and that huge strings/bytes are sliced BEFORE being
        # serialized.
        return str(_build_debug_summary(self._data, with_bounds=False))


# Ceiling for waiting on in-flight spill threads when the run shuts down. Only
# exercised on a canceled/aborted run; writing a ~50 MB Parquet is well
# below this, so the ceiling exists only so cleanup does not hang forever.
_SPILL_DRAIN_TIMEOUT_S = 30.0

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    Orchestrates the workflow execution, with parameter rendering via Jinja2
    and an "aliases" system ($Alias) to reference outputs of previous nodes.
    """
    def __init__(
        self,
        definition: Dict[str, Any],
        task_id: Optional[str] = None,
        publisher: Optional[WorkflowEventPublisher] = None,
        debug_mode: bool = False,
        workspace_id: Optional[str] = None,
        workflow_hash: Optional[str] = None,
        pinned_outputs: Optional[Dict[str, Any]] = None,
        pin_metadata: Optional[Dict[str, Any]] = None,
        disabled_nodes: Optional[list[str]] = None,
        subworkflow_definitions: Optional[Dict[str, Dict[str, Any]]] = None,
        is_nested: bool = False,
    ):
        self.task_id = task_id
        # Nested execution (sub-workflow): shares task_id with the parent, so it
        # cannot clean up resources indexed by it — the root does the cleanup.
        self.is_nested = is_nested
        self.definition = definition
        self.publisher = publisher
        self.debug_mode = debug_mode
        self.workspace_id = workspace_id
        self.workflow_hash = workflow_hash
        self.pinned_outputs = pinned_outputs or {}
        self.pin_metadata = pin_metadata or {}
        # Pin refs WRITTEN IN THIS run (auto-pin). This is what goes back to the server in
        # __updated_pinned_outputs__. It cannot be derived from pinned_outputs at
        # the end of the run: that also holds the refs that came from the server and
        # merely passed through the run — and the consumer re-derives the s3_key with
        # the CURRENT task_id, so re-reporting an old ref repointed it to an object that
        # never existed (404 on every subsequent run).
        self.updated_pin_refs: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
        self.metrics_collector = MetricsCollector()

        self.node_stats: Dict[str, Any] = {}
        self.all_node_outputs: Dict[str, Dict[str, Any]] = {}
        # Context shared between nodes:
        # - _subflow_ancestors: set of hashes already in the chain, so SubWorkflowNode
        #   can detect loops at any level.
        # - _disabled_nodes: snapshot sent by the server in the job envelope,
        #   used by SubWorkflowNode to block sub-workflows that contain
        #   nodes disabled by the admin.
        # - _subworkflow_definitions: pre-resolved definitions of the whole chain
        #   of sub-workflows (server → executor via envelope). The executor
        #   has no DB access, so SubWorkflowNode looks them up here.
        # Children copy this dict and propagate it to the nested executor.
        self.context: Dict[str, Any] = {
            "_disabled_nodes": set(disabled_nodes or []),
            "_subworkflow_definitions": dict(subworkflow_definitions or {}),
            # The workflow itself is already in the chain. Without this, a workflow that
            # calls itself was only blocked at the SECOND level — and by then it had
            # already run in full one more time, sending the email and writing the
            # artifact again. Since the run ends in an error, it is easy to miss
            # that the side effects happened twice.
            #
            # The sub-workflow OVERWRITES this key with the chain it received from the
            # parent (SubWorkflowNode), so here it only matters for the root.
            "_subflow_ancestors": {workflow_hash} if workflow_hash else set(),
        }

        node_defs = {n['id']: n for n in definition.get('nodes', [])}
        edges = definition.get('edges', [])
        self.graph = WorkflowGraph(node_defs, edges, filter_isolated=True)
        self.execution_order = self.graph.compute_order()
        self.logger.info("Ordem de execução: %s", self.execution_order)

        self.node_mgr = NodeManager(node_defs)
        self.node_mgr.instantiate_nodes(self.execution_order)
        # auto_map_edges (legacy backfill of from_key/to_key from
        # outputKey*/inputKey* in params) was retired: no node nor the current
        # front end emits those params, and the front end already writes from_key
        # on the edge. Edge semantics now come only from the edge itself. See
        # docs/specs/edge-data-contract.md §5.

        for node in self.node_mgr.nodes.values():
            node._publisher      = self.publisher
            node._task_id        = self.task_id
            node._debug_mode     = self.debug_mode
            node._workspace_id   = self.workspace_id
            node._workflow_hash  = self.workflow_hash
            # the node's context points to the same dict as the executor — lets
            # SubWorkflowNode read/write _subflow_ancestors transparently.
            node.context         = self.context

        self.incoming = {nid: ev for nid, ev in self.graph.incoming.items() if nid in self.execution_order}
        self.outgoing = {nid: ev for nid, ev in self.graph.outgoing.items() if nid in self.execution_order}
        # BRANCH edges deactivated in this run (by id of the edge dict — the
        # same object lives in incoming and outgoing, see flow/core/graph.py). The
        # input assembly checks this set so as NOT to inject into the merge the
        # data from a branch that was not taken: filtering only parents with status
        # 'skipped' was not enough, because a live control node (status
        # 'completed') whose branch edge was deactivated kept contributing.
        self._deactivated_edge_ids: set[int] = set()

        self.final_outputs: Dict[str, Any] = {}
        # In-flight spill tasks. `asyncio.to_thread` is not cancelable, so
        # they survive the run's cancellation and need to be drained before
        # _cleanup_spill's rmtree — see _drain_spills.
        self._spill_inflight: "set[asyncio.Task]" = set()

    # ── Pin data ─────────────────────────────────────────────────────────────

    def _upload_pin_artifact(self, node_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        return _pin.upload_pin_artifact(node_id, outputs, self.workspace_id, self.task_id)

    @staticmethod
    def _download_pin_artifact(pinned: Dict[str, Any]) -> Dict[str, Any]:
        return _pin.download_pin_artifact(pinned)

    # ── Expression rendering ──────────────────────────────────────────────────

    def _render_node_parameters(self, node_id: str, named: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Renders parameters and returns a rendered copy (without mutating the original)."""
        return render_node_parameters(self.node_mgr.nodes[node_id], node_id, named, context)

    # ── Event publishing ──────────────────────────────────────────────────────

    def _publish_debug(self, node_id: str, inputs: dict, outputs: dict) -> None:
        _events.publish_debug(self.publisher, self.task_id, node_id, self.node_mgr.node_defs, inputs, outputs)

    def _publish_started(self, node_id: str) -> None:
        _events.publish_started(self.publisher, self.task_id, node_id, self.node_mgr.node_defs)

    def _publish_completed(self, node_id: str, status: str, duration_ms: float, error: str = None, output_keys: list = None, output_columns: dict = None, branch_result: "bool | None" = None, cache_hit: "bool | None" = None, traceback_str: "str | None" = None, schema_drift: "dict | None" = None, exception: "BaseException | None" = None) -> None:
        _events.publish_completed(self.publisher, self.task_id, node_id, self.node_mgr.node_defs, status, duration_ms, error, output_keys, output_columns, branch_result, cache_hit, traceback_str, schema_drift, exception)

    # ── Pin data resolution ──────────────────────────────────────────────────

    async def _resolve_pin_data(self, node_id: str):
        """Resolves pin data for a node. Returns deserialized outputs or None."""
        pinned = self.pinned_outputs.get(node_id)
        if not pinned:
            return None

        # Checks expiration
        node_meta = self.pin_metadata.get(node_id, {})
        expires_at_str = node_meta.get("expires_at")
        if expires_at_str:
            try:
                if utc_now_naive() > datetime.fromisoformat(expires_at_str):
                    # The object in MinIO is not removed here: the executor has no
                    # storage credentials. The server deletes it on
                    # DELETE /workflows/{id_hash}/pin/{node_id} and overwrites it on
                    # re-pin (same s3_key).
                    self.logger.info("[%s] Pin data expirado — executando nó normalmente.", node_id)
                    return None
            except (ValueError, TypeError) as exc:
                logger.debug("Formato de pin inválido, ignorando: %s", exc)

        # Download from MinIO if needed
        if "__pin_s3_key__" in pinned:
            try:
                pinned = await asyncio.to_thread(self._download_pin_artifact, pinned)
            except Exception as exc:
                self.logger.warning("[%s] Erro ao baixar pin: %s — executando normalmente.", node_id, exc)
                self._marcar_pin_para_regravar(node_id)
                return None
            if not pinned:
                self.logger.warning("[%s] Falha ao baixar pin do MinIO — executando normalmente.", node_id)
                self._marcar_pin_para_regravar(node_id)
                return None

        return pinned

    def _marcar_pin_para_regravar(self, node_id: str) -> None:
        """Self-healing of a broken pin: clears the ref so auto-pin rewrites it in this very run.

        Without this, a ref whose object vanished from MinIO (purge, bucket wiped,
        lost upload) stayed stuck forever: auto-pin only fires with an
        EMPTY ref, so every subsequent run repeated the 404 and re-executed the node.
        Only applies to a pin with metadata (explicit user intent) — and NOT
        to an expired pin, whose gap is deliberate until someone re-pins.
        """
        if node_id in self.pin_metadata:
            self.pinned_outputs[node_id] = {}
            self.logger.info("[%s] Pin sem objeto no storage — será regravado nesta execução.", node_id)

    # ── Node execution ────────────────────────────────────────────────────────

    async def _run_node_with_tracking(self, node_id: str, inputs: Dict[str, Any]) -> tuple:
        node_def = self.node_mgr.node_defs[node_id]
        # Shallow copy: evita deepcopy de GDFs acumulados em named/nodes
        context = {
            "inputs": inputs,
            "nodes": self.all_node_outputs,
            "named": dict(self.expression_context["named"]),
            "now": self.expression_context["now"],
            "uuid": self.expression_context["uuid"],
            "env": self.expression_context["env"],
        }
        named = context["named"]

        rendered = await asyncio.to_thread(self._render_node_parameters, node_id, named, context)
        self.node_mgr.nodes[node_id].parameters = rendered

        # ── Pin data check ────────────────────────────────────────────────
        pinned = await self._resolve_pin_data(node_id)

        if pinned:
            self.logger.info("[%s] Usando output fixado (pin data).", node_id)
            self.node_stats[node_id] = {
                "node_name": node_def.get("name", node_id),
                "duration_ms": 0.0,
                "status": "pinned",
                "cache_hit": True,
                "input_features": _count_gdf_features(inputs),
                "output_features": _count_gdf_features(pinned),
                "error": None,
                "started_at": utc_now_naive().isoformat(),
                "output_keys": list(pinned.keys()),
                "output_columns": _colunas_das_saidas(pinned),
            }
            self.all_node_outputs[node_id] = {
                "outputs": pinned,
                "meta": {"timestamp": utc_now_naive().isoformat(), "duration_ms": 0.0},
            }
            self._publish_completed(node_id, "completed", 0.0, cache_hit=True, output_keys=list(pinned.keys()) if isinstance(pinned, dict) else [],
                                        output_columns=_colunas_das_saidas(pinned))
            if self.debug_mode and self.publisher:
                self._publish_debug(node_id, inputs, pinned)
            return node_id, pinned, 0.0

        node = self.node_mgr.nodes[node_id]

        self._publish_started(node_id)

        node_name_m = node_def.get("name", node_id) if isinstance(node_def, dict) else str(node_id)
        node_type_m = node_def.get("type", "") if isinstance(node_def, dict) else ""
        self.metrics_collector.start_node(node_id, node_name_m, node_type_m)

        # Two lines, two levels, on purpose: WHAT is running is the only
        # clue `docker logs executor` gives when the WebSocket to the server
        # drops, so it stays at INFO with %s args (O(1) cost, no payload). The
        # content of the inputs is expensive to summarize and stays at DEBUG.
        self.logger.info("Executando nó %s (%s)", node_id, node_def.get("name", node_id))
        self.logger.debug("[%s] inputs: %s", node_id, _LazySummary(inputs))
        start_ts = time.time()
        error = None
        error_traceback: "str | None" = None
        status = "completed"
        outputs = {}

        try:
            await node.setup()
            _retry_count, _retry_delay_s = node.get_retry_params()
            for _attempt in range(_retry_count + 1):
                try:
                    outputs = await node.execute(inputs)
                    break
                except Exception as _exc:
                    # BEHAVIOR CHANGE: only retries TRANSIENT errors
                    # (network/timeout, see flow/utils/error_taxonomy). Previously any
                    # Exception was retried, which (a) re-executed the whole
                    # node.execute() on a deterministic error (validation, bad data) with
                    # no chance of the result changing and (b) repeated side effects
                    # of non-idempotent nodes. The last attempt also lands here.
                    if _attempt >= _retry_count or not is_retryable(classify_error(_exc)):
                        raise
                    self.logger.warning(
                        "Nó %s falhou (tentativa %d/%d): %s. Retentando em %ss...",
                        node_id, _attempt + 1, _retry_count + 1, _exc, _retry_delay_s,
                    )
                    await asyncio.sleep(_retry_delay_s)
        except Exception as e:
            outputs = {}
            error = e
            status = "failed"
            error_traceback = _traceback.format_exc()
            self.logger.error("Erro no nó %s: %s", node_id, e)
            raise
        finally:
            try:
                await node.teardown()
            except Exception as _td_exc:
                self.logger.warning("Erro no teardown do nó %s: %s", node_id, _td_exc)
            duration_ms = (time.time() - start_ts) * 1000
            node_name = node_def.get("name", node_id)
            self.node_stats[node_id] = {
                "node_name": node_name,
                "duration_ms": round(duration_ms, 2),
                "status": status,
                "cache_hit": False,
                "input_features": _count_gdf_features(inputs),
                "output_features": _count_gdf_features(outputs) if outputs else None,
                "error": str(error) if error else None,
                "started_at": utc_from_timestamp_naive(start_ts).isoformat(),
                "output_keys": list(outputs.keys()) if isinstance(outputs, dict) else [],
                # Which columns each output had. This is what lets the editor
                # suggest column names instead of requiring the person to run
                # the workflow just to find out what reaches the next node.
                "output_columns": _colunas_das_saidas(outputs) if isinstance(outputs, dict) else None,
            }
            self.all_node_outputs[node_id] = {
                "outputs": outputs,
                "meta": {
                    "timestamp": utc_now_naive().isoformat(),
                    "duration_ms": duration_ms,
                },
            }
            if status == "completed" and outputs:
                # The lightweight dict of references lives ONLY in all_node_outputs — that is
                # the `parent_outputs` path, the only one that rehydrates via
                # `_load_from_disk`. `named[alias]`/`final_outputs` keep the
                # real payload on purpose: the Jinja context does not
                # rehydrate anything, so returning `spilled` here would make
                # `{{ Alias.gdf }}` render `{'__spilled__': True, …}` and
                # would leave `final_outputs` pointing at Parquets that
                # `_free_node_outputs` has already deleted. Trading peak RAM for
                # silent data corruption is a bad deal.
                spilled = await self._spill_shielded(node_id, outputs)
                if spilled is not outputs:
                    self.all_node_outputs[node_id]["outputs"] = spilled
            _branch_result = outputs.get("branch") if outputs and isinstance(outputs.get("branch"), bool) else None

            # Schema drift: compares the returned keys with what the catalog declares
            # (the descriptor's `outputs`). The saved definition never carried the
            # declared ones, so the old read (node_def) compared against nothing.
            # Dynamic-output nodes are left out: for them the payload rules
            # (`output_vars`, `ports`), not the descriptor.
            _decl_cls = self.node_mgr.factory.get(node_def.get("name"))
            _decl_desc = getattr(_decl_cls, "description", lambda: {})() if _decl_cls else {}
            _declared_keys: set[str] = set()
            if not _decl_desc.get("dynamic_output") and not _decl_desc.get("outputs_from_ports"):
                _declared_keys = {
                    _c["name"] for _c in (_decl_desc.get("outputs") or [])
                    if isinstance(_c, dict) and "name" in _c
                }
            _actual_keys = set(outputs.keys()) if isinstance(outputs, dict) else set()
            _actual_keys -= {"__artifact__", "__response__"}
            _missing = sorted(_declared_keys - _actual_keys) if _declared_keys else []
            _extra   = sorted(_actual_keys - _declared_keys) if _declared_keys else []
            _schema_drift = {"missing": _missing, "extra": _extra} if (_missing or _extra) else None
            if _missing:
                self.logger.warning("[%s] Output faltando keys declaradas: %s", node_id, _missing)
            if _extra:
                self.logger.info("[%s] Output retornou keys nao declaradas: %s", node_id, _extra)

            self._publish_completed(node_id, status, duration_ms, str(error) if error else None,
                                    output_keys=list(outputs.keys()) if isinstance(outputs, dict) else [],
                                    output_columns=_colunas_das_saidas(outputs) if isinstance(outputs, dict) else None,
                                    branch_result=_branch_result,
                                    traceback_str=error_traceback,
                                    schema_drift=_schema_drift,
                                    exception=error)
            # `end_node` does an O(n) scan over the output GDF
            # (`total_bounds` always; vertex/type counts in debug) — which
            # held up the event loop at the end of each node. It goes to a thread. With
            # the batch running nodes in parallel (`asyncio.gather`), several `end_node`
            # calls now actually run concurrently; the only shared state
            # they touch is `run_tracker.sample()`, now protected by a lock in
            # ResourceTracker (`nm` is per node_id).
            await asyncio.to_thread(
                self.metrics_collector.end_node,
                node_id=node_id,
                inputs=inputs,
                outputs=outputs,
                status=status,
                duration_ms=round(duration_ms, 2),
                error=str(error) if error else None,
                debug_mode=self.debug_mode,
            )

        if (status == "completed" and outputs
                and node_id in self.pinned_outputs and not self.pinned_outputs[node_id]
                and node_id in self.pin_metadata):
            try:
                pin_ref = await asyncio.to_thread(self._upload_pin_artifact, node_id, outputs)
                self.pinned_outputs[node_id] = pin_ref
                self.updated_pin_refs[node_id] = pin_ref
                self.logger.info("[%s] Auto-pin: artefato salvo no MinIO (%s)", node_id, pin_ref.get("__pin_format__"))
            except Exception as exc:
                self.logger.warning("[%s] Auto-pin falhou: %s", node_id, exc)

        if self.debug_mode and self.publisher and status == "completed":
            # `outputs` is the real payload (the lightweight spill dict only ended up in
            # all_node_outputs): the debug summary needs the GDF's columns/bounds,
            # not the reference.
            self._publish_debug(node_id, inputs, outputs or {})

        return node_id, outputs, duration_ms

    async def _spill_shielded(self, node_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Runs `_spill_to_disk` in a thread, shielded against cancellation.

        The shield is mandatory and swapping it for a bare await is not an option: a
        running thread is not cancelable, so canceling the future would only
        discard the result while the Parquet kept being written —
        and nobody would know the path to delete it. By registering the task in
        `_spill_inflight`, the `finally` of `run()` can wait for it (see
        `_drain_spills`) before deleting the directory.
        """
        task = asyncio.ensure_future(
            asyncio.to_thread(_spill_to_disk, self.task_id, node_id, outputs)
        )
        self._spill_inflight.add(task)
        task.add_done_callback(self._spill_inflight.discard)
        return await asyncio.shield(task)

    async def _drain_spills(self) -> None:
        """Waits for in-flight spill writes before the directory is deleted.

        Real failure path: `executor/job_executor.py` wraps `run()` in an
        `asyncio.wait_for(..., JOB_TIMEOUT)`. On timeout, the shield returns
        CancelledError to the awaiter but the threads keep writing; if
        `_cleanup_spill`'s `shutil.rmtree` runs before them, each thread whose
        `os.makedirs` had not run yet RECREATES the directory and writes a
        Parquet that nobody deletes anymore — `_cleanup_spill` is the process's only
        cleanup point; there is no janitor nor a sweep at startup. Measured:
        5.5 MB of permanent orphans in a single canceled run; with real GDFs
        (>50 MB, the threshold) it is hundreds of MB in the same /tmp as ARTIFACTS_DIR.

        On the happy path the set is empty (each spill is awaited in the node),
        so this costs one `if`.
        """
        pending = [t for t in self._spill_inflight if not t.done()]
        self._spill_inflight.clear()
        if not pending:
            return
        try:
            # `asyncio.wait` (and not `wait_for`) because on timeout it just
            # returns what is left instead of canceling — canceling would not stop the
            # thread and would also mask the error. The ceiling keeps a
            # pathological spill from holding up cleanup forever.
            _done, ainda = await asyncio.wait(pending, timeout=_SPILL_DRAIN_TIMEOUT_S)
        except asyncio.CancelledError:
            # Second cancellation during the drain. We cannot wait any longer,
            # but the cleanup right below must run; the CancelledError that was
            # already propagating through run()'s `finally` continues on its way.
            self.logger.warning("Dreno do spill cancelado — pode restar Parquet órfão.")
            return
        for task in _done:
            # Consumes the exception: nobody else will await these tasks (the original
            # awaiter got CancelledError from the shield) and asyncio would dump
            # "Task exception was never retrieved" into the container log.
            if not task.cancelled() and task.exception() is not None:
                self.logger.warning("Spill falhou durante o encerramento: %s", task.exception())
        if ainda:
            self.logger.warning(
                "%d escrita(s) de spill ainda em voo após %.0fs — o cleanup pode "
                "deixar Parquet órfão em disco.", len(ainda), _SPILL_DRAIN_TIMEOUT_S,
            )

    # ── Workflow orchestration ────────────────────────────────────────────────

    async def run(self, initial_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start_time = time.time()
        self.initial_inputs = initial_inputs or {}
        self.final_outputs = {}
        self.all_node_outputs = {}
        self.node_stats = {}

        named: Dict[str, Any] = {}
        # `nodes` points to the live all_node_outputs dict instead of a copy
        # populated on each node: it was a second node_id → entry index that nobody
        # read (the per-node context of _run_node_with_tracking already uses
        # self.all_node_outputs) and that only served to duplicate references.
        context: Dict[str, Any] = {
            "inputs": {},
            "nodes": self.all_node_outputs,
            "named": named,
            "now": expr_svc.env.globals["now"],
            "uuid": expr_svc.env.globals["uuid"],
            "env": safe_env(),
        }
        self.expression_context = context

        pending_parents_count = defaultdict(int)
        for edges in self.incoming.values():
            for edge in edges:
                pending_parents_count[edge['target']] += 1

        remaining_consumers: Dict[str, int] = defaultdict(int)
        for node_id in self.execution_order:
            for edge in self.outgoing.get(node_id, []):
                remaining_consumers[edge['source']] += 1

        executed = set()
        # Nodes that received data through SOME ACTIVE edge from a live parent. A merge
        # with one live parent and one skipped parent must NOT be skipped just because
        # the sibling branch's skip zeroed the pending count last (F2 — previously the
        # result depended on the batch order). "Live parent via active edge" ≠ "has a
        # live parent": the fork node itself is live, but the child of the branch NOT
        # taken arrives through a deactivated edge and must be skipped.
        has_live_input: set = set()
        ready_nodes = deque([nid for nid in self.execution_order if pending_parents_count[nid] == 0])

        # try/finally: previously, a node that raised an exception aborted the run BEFORE
        # _cleanup_spill. The Parquets stayed in /tmp and — worse — the reread
        # copies stayed stuck in _spill_cache, which is a module-level dict:
        # on a long-running executor, each failed run leaked whole GeoDataFrames
        # for the rest of the process's life.
        try:
            while ready_nodes:
                tasks = []
                current_batch = list(ready_nodes)
                ready_nodes.clear()

                # Tracks parents consumed in this batch to decrement AFTER execution
                batch_consumed_parents: list = []

                for node_id in current_batch:
                    if node_id in executed:
                        continue

                    node_def = self.node_mgr.node_defs[node_id]
                    node_type = node_def.get('type')

                    if node_type == 'trigger':
                        inputs = self.initial_inputs.get(node_id, self.initial_inputs) or {}
                    else:
                        inputs = {}
                        for edge in self.incoming.get(node_id, []):
                            parent_id = edge['source']
                            # A skipped parent (branch not taken) does not contribute: the edge
                            # disappears (F14), instead of injecting None/empty into the
                            # merge. The resolver would already omit it (empty parent →
                            # {}); skipping here also avoids a spurious "from_key
                            # missing" warning about an expected {}.
                            if self.node_stats.get(parent_id, {}).get("status") == "skipped":
                                continue
                            # BRANCH edge not taken: the parent (control node) is
                            # LIVE (status 'completed'), so the 'skipped' filter
                            # above does not catch it. Without this, a merge that also
                            # receives real data from another parent (has_live_input,
                            # which is why it RUNS instead of being skipped) silently
                            # joined in the output of the REJECTED branch — wrong
                            # result, no error.
                            if id(edge) in self._deactivated_edge_ids:
                                continue
                            # `_load_from_disk` does `gpd.read_parquet` (disk +
                            # geometry deserialization): synchronous on the loop, a
                            # ~200MB spilled GDF held it for >1s without
                            # scheduling heartbeat/cancel for ANY job (the spill
                            # WRITE already went to a thread via `_spill_shielded`;
                            # the read did not). The internal cache is guarded by
                            # `_spill_lock`, so calling it from another thread is safe.
                            parent_outputs = await asyncio.to_thread(
                                _load_from_disk, self.all_node_outputs[parent_id]['outputs']
                            )
                            # Single source of edge semantics (from_key/to_key/spread) —
                            # the SAME one used by the schema simulation below. See
                            # flow/executor/edge_resolver.py and docs/specs/edge-data-contract.md.
                            inputs.update(resolve_edge_inputs(
                                edge, parent_outputs,
                                logger=self.logger, node_id=node_id, parent_id=parent_id,
                            ))
                            batch_consumed_parents.append(parent_id)

                    tasks.append(self._run_node_with_tracking(node_id, inputs))

                # Cancels the siblings on the FIRST failure. BEHAVIOR CHANGE:
                # previously (asyncio.gather alone) a node that raised left its
                # siblings in the same batch running to the end — AFTER the run had
                # already been reported as failed —, and they still committed inserts,
                # sent emails, uploaded artifacts (side effects of a run the
                # user sees as failed) and fired _spill_shielded after cleanup
                # (orphan Parquet). Now explicit tasks: on the 1st exception the
                # pending ones are canceled and awaited before propagating. A task
                # stuck in asyncio.to_thread does not die (the thread carries on), but
                # cancellation keeps the canceled node from COMMITTING the effect at
                # the next await.
                task_objs = [asyncio.ensure_future(t) for t in tasks]
                try:
                    results = await asyncio.gather(*task_objs)
                except BaseException:
                    for t in task_objs:
                        if not t.done():
                            t.cancel()
                    await asyncio.gather(*task_objs, return_exceptions=True)
                    raise

                # Decrements remaining_consumers AFTER the batch executes
                for parent_id in batch_consumed_parents:
                    remaining_consumers[parent_id] -= 1
                    if remaining_consumers[parent_id] <= 0:
                        self._free_node_outputs(parent_id)

                for node_id, outputs, duration_ms in results:
                    node_def = self.node_mgr.node_defs[node_id]

                    executed.add(node_id)
                    self.final_outputs[node_id] = outputs
                    alias = _resolve_alias(node_def)
                    # Only `named` holds the alias. The `context[alias]` here was dead:
                    # the context that reaches Jinja is the per-node one built in
                    # _run_node_with_tracking, and render_node_parameters does
                    # `context.update(named)` — the top-level key already comes from `named`.
                    named[alias] = outputs

                    # Filters active edges (branch filtering without mutating self.outgoing).
                    # Routing is gated by the presence of BRANCH EDGES
                    # (bool condition), not by the raw "branch" output:
                    #  - F7: an ordinary node (python_script, http_request) whose output
                    #    has a boolean 'branch' key does NOT hijack
                    #    routing — without branch edges, nothing is filtered/skipped.
                    #  - F8: DATA edges (no condition) ALWAYS remain
                    #    active; only branch edges with condition != branch are
                    #    deactivated. Previously, condition=None != branch deactivated the
                    #    data edge and skipped the target.
                    outgoing_edges = self.outgoing.get(node_id, [])
                    active_edges = outgoing_edges
                    branch_edges = [e for e in outgoing_edges if Edge.from_dict(e).is_branch]
                    if branch_edges and "branch" in outputs and isinstance(outputs.get("branch"), bool):
                        branch = outputs["branch"]
                        self.logger.info("[%s] Resultado do branch: %s", node_id, branch)
                        active_edges = [
                            e for e in outgoing_edges
                            if not Edge.from_dict(e).is_branch or e.get("condition") == branch
                        ]

                        # Propagates skip only to the target of the BRANCH edges not chosen
                        deactivated = [e for e in branch_edges if e.get("condition") != branch]
                        for edge in deactivated:
                            # Records the deactivated edge so the target's input assembly
                            # does NOT inject this branch's output (the target may
                            # survive by having another live parent). Done BEFORE the
                            # target becomes ready (next batch), so the assembly
                            # already sees it.
                            self._deactivated_edge_ids.add(id(edge))
                            self._propagate_skip(
                                edge["target"], pending_parents_count,
                                remaining_consumers, executed,
                                ready_nodes, has_live_input,
                            )

                    for edge in active_edges:
                        child_id = edge["target"]
                        # Active edge coming from this node, which just ran (live):
                        # the child received real data. Marked BEFORE pending so
                        # that a later skip of a sibling branch sees it and does not erase it.
                        has_live_input.add(child_id)
                        pending_parents_count[child_id] -= 1
                        if pending_parents_count[child_id] == 0 and child_id not in executed:
                            ready_nodes.append(child_id)

                    if remaining_consumers[node_id] == 0:
                        self._free_node_outputs(node_id)
        finally:
            await self._drain_spills()
            _cleanup_spill(self.task_id, is_nested=self.is_nested)

        elapsed = time.time() - start_time
        self.logger.info("Workflow concluído em %.2fs (task_id=%s)", elapsed, self.task_id)
        return self.final_outputs

    def _propagate_skip(
        self,
        node_id: str,
        pending_parents_count: dict,
        remaining_consumers: dict,
        executed: set,
        ready_nodes: deque,
        has_live_input: set,
    ) -> None:
        """Propagates skip to the nodes of an unselected branch.

        Decrements pending_parents_count and, when ALL parents of `node_id`
        have been resolved (pending == 0), decides:
          - if the node received data through SOME ACTIVE edge from a live parent
            (`has_live_input`) → it has real input and MUST run: it goes into
            `ready_nodes` instead of becoming skipped. This is the merge/diamond where one
            branch died but the other delivered data (F2); previously the result
            depended on the batch order — the sibling branch's skip could zero the
            pending count last and erase the live node;
          - otherwise (all parents arrived via skip / deactivated edge) → marks it
            skipped and propagates recursively.

        `pending == 0` guarantees that every parent has been resolved (executed or
        skipped), so `has_live_input` is complete here.
        """
        if node_id in executed:
            return

        pending_parents_count[node_id] -= 1
        if pending_parents_count[node_id] > 0:
            # Still has another pending parent — cannot decide yet
            return

        if node_id in has_live_input:
            # Received data through an active edge from a live parent: runs, does not skip.
            if node_id not in executed:
                ready_nodes.append(node_id)
            return

        # Marks as executed (skipped) so it does not enter ready_nodes
        executed.add(node_id)
        self.node_stats[node_id] = {
            "node_name": self.node_mgr.node_defs.get(node_id, {}).get("name", node_id),
            "duration_ms": 0.0,
            "status": "skipped",
            "cache_hit": False,
            "input_features": None,
            "output_features": None,
            "error": None,
            "started_at": None,
            "output_keys": [],
        }
        self.all_node_outputs[node_id] = {"outputs": {}, "meta": {}}
        self.logger.debug("Nó %s skipado (branch não selecionado).", node_id)

        # Libera remaining_consumers dos pais deste node
        for edge in self.incoming.get(node_id, []):
            parent_id = edge["source"]
            remaining_consumers[parent_id] -= 1
            if remaining_consumers[parent_id] <= 0:
                self._free_node_outputs(parent_id)

        # Propagates skip to children
        for edge in self.outgoing.get(node_id, []):
            self._propagate_skip(
                edge["target"], pending_parents_count,
                remaining_consumers, executed,
                ready_nodes, has_live_input,
            )

    def _free_node_outputs(self, node_id: str) -> None:
        """Drops the reference in `all_node_outputs` and deletes the spill of an already-consumed node.

        Does NOT remove the alias from `named`: it feeds the Jinja context and must
        remain available for `{{ Alias.x }}` in later nodes.

        That is why the RAM savings here are partial, on purpose — `named[alias]`
        and `final_outputs[node_id]` keep pointing at the real payload, which only
        dies with the executor. What this call actually frees are the COPIES:
        the Parquet on disk and the reread copy that `_spill_cache` (a module-level
        dict) would keep alive for the rest of the process's life.
        """
        entry = self.all_node_outputs.get(node_id)
        if entry and entry.get("outputs"):
            self.logger.debug("Liberando outputs do nó %s da memória.", node_id)
            _delete_spill_files(entry["outputs"])
            entry["outputs"] = {}

    async def simulate_runner(self) -> Dict[str, Any]:
        self.simulated_outputs = {}
        for node_id in self.execution_order:
            node_def = self.node_mgr.node_defs[node_id]
            node_type = node_def.get("name")
            node_cls = self.node_mgr.factory.get(node_type)
            if not node_cls:
                continue

            desc = getattr(node_cls, "description", lambda: {})()

            # `outputs_from_ports` (SubWorkflowInput) declares `outputs: []`
            # without `dynamic_output`, but the real outputs are the payload's `ports`:
            # it takes the declared path, not the static one.
            if not desc.get("dynamic_output") and not desc.get("outputs_from_ports"):
                self.simulated_outputs[node_id] = {
                    "status": "ok",
                    "schema": schema_do_catalogo(desc),
                    "schema_source": "static",
                }
                continue

            simulate_fn = getattr(node_cls, "simulate", None)
            if not simulate_fn:
                # It used to be just `continue`, and the node VANISHED from the response: eight
                # catalog nodes (PythonScript, Switch, ReadGeoJSON, WFS, DataInput...)
                # have `dynamic_output` and no `simulate()`, so /validate
                # silently omitted them — panel without a schema and a wrong `from_key`
                # coming out of them passing with no diagnostic. The outputs are written
                # in the definition itself (`output_vars`, `rules`/`fallback_output`,
                # `ports`) or in the catalog's `outputs`; `schema_source` says where the
                # schema came from, so the consumer knows how much to trust it.
                try:
                    declarado = schema_declarado(node_def, desc)
                except ValueError as exc:
                    # A declaration the run would reject in validate() (`output_vars`
                    # empty/non-string): same message, status "error". Previously it
                    # became an empty schema with `ok` — and with no known outputs the
                    # edge diagnostics were switched off along with it.
                    self.logger.warning(
                        "Saída declarada inválida no nó %s (%s): %s", node_id, node_type, exc,
                    )
                    self.simulated_outputs[node_id] = {"status": "error", "error": str(exc)}
                    continue
                if declarado is None:
                    # With no `outputs` in the catalog and nothing declared in the payload there is
                    # nothing to assert — but the node stays in the response, with the
                    # source saying so. Omitting it was exactly the silence this branch removes.
                    self.simulated_outputs[node_id] = {
                        "status": "ok", "schema": [], "schema_source": "unknown",
                    }
                else:
                    self.simulated_outputs[node_id] = {
                        "status": "ok", "schema": declarado, "schema_source": "declared",
                    }
                continue

            try:
                # The signature is (node_parameters, property_list). Previously it
                # received the whole node_def and the CLASS: `for prop in props`
                # raised TypeError('type' object is not iterable), which the
                # except below turned into {"status": "error"}. Result:
                # `simulate()` was never called and /workflows/validate returned
                # an error for every node with dynamic_output.
                #
                # `parameters` is the validation body's format; `properties` is the
                # saved definition's — same tolerance as `node_props` on the
                # server.
                params = validate_node_parameters(
                    node_def.get("parameters") or node_def.get("properties") or {},
                    desc.get("properties", []),
                    # From the descriptor, not the payload: validation accepts an
                    # arbitrary definition, and the name only goes formatted into the log.
                    # The registry lookup has already guaranteed the type exists.
                    node_name=desc.get("name", node_type),
                )
                simulated_inputs: Dict[str, Any] = {}
                for edge in self.incoming.get(node_id, []):
                    parent_id = edge["source"]
                    parent_output = self.simulated_outputs.get(parent_id)
                    if not parent_output or parent_output.get("status") != "ok":
                        continue

                    # The SAME resolver as the run, on the schema plane: the ports the
                    # simulation names now match the ones the run produces (previously
                    # the "no keys" case diverged — the run spread, the simulation named
                    # by parent_id). See flow/executor/edge_resolver.py.
                    #
                    # F11: `schema` may be [] (SubWorkflowInput/Output have
                    # outputs=[]). `.get("schema", [{}])` only uses the default
                    # when the KEY is missing; with an empty list, [][0] raised
                    # IndexError, the except marked the CHILD as error and it cascaded
                    # through the whole preview. Normalizes the empty list here.
                    schema_list = parent_output.get("schema") or []
                    parent_fields = schema_list[0].get("fields", []) if schema_list else []
                    simulated_inputs.update(resolve_edge_schema_inputs(edge, parent_fields))

                schema = await simulate_fn(params, simulated_inputs)
                self.simulated_outputs[node_id] = {
                    "status": "ok", "schema": schema, "schema_source": "simulated",
                }
            except Exception as exc:
                # The preview goes on (status "error" only on this node), but the cause
                # cannot be silent: swallowed here, a broken simulate() showed up
                # as "node without schema" and nobody found out why.
                self.logger.warning(
                    "simulate() falhou no nó %s (%s): %s", node_id, node_type, exc,
                )
                self.simulated_outputs[node_id] = {"status": "error", "error": str(exc)}

        return self.simulated_outputs

    def validate_edges(self) -> "list[dict]":
        """Static edge diagnostics from the simulated schema.

        This is where the strict enforcement lives that the RUN does not do (the run
        only omits the port, so as not to bring down a workflow over an
        optional/dynamic output). The static check has the hand-declared schema and
        can flag before running, with no risk of a false positive at runtime:

          - `from_key` that is NOT a declared output of the source → **error** (stale
            wiring — the edge would deliver nothing in the run);
          - data edge without `from_key`/`to_key` coming from a source with >1 output
            → ambiguity **warning** (spreads everything; better to name the port).

        Requires `simulate_runner()` to have run first (uses `self.simulated_outputs`).
        A source with no known schema (simulate() that failed, empty `outputs`,
        `schema_source: unknown`) produces no diagnostic — a typo cannot be
        asserted without the declared outputs. Outputs declared in the definition
        (`schema_source: declared`) count as known: a `from_key` outside
        `output_vars` is an error.
        """
        diagnostics: "list[dict]" = []
        for node_id in self.execution_order:
            for edge in self.incoming.get(node_id, []):
                parent_id = edge["source"]
                parent_output = self.simulated_outputs.get(parent_id)
                if not parent_output or parent_output.get("status") != "ok":
                    continue
                schema_list = parent_output.get("schema") or []
                fields = schema_list[0].get("fields", []) if schema_list else []
                names = {f.get("name") for f in fields if f.get("name")}
                if not names:
                    continue

                from_key = edge.get("from_key")
                to_key = edge.get("to_key")
                is_branch = Edge.from_dict(edge).is_branch

                if from_key:
                    if from_key not in names:
                        diagnostics.append({
                            "severity": "error",
                            "source": parent_id,
                            "target": node_id,
                            "from_key": from_key,
                            "message": (
                                f"from_key '{from_key}' não é uma saída de "
                                f"'{parent_id}'. Saídas: {sorted(names)}."
                            ),
                        })
                elif not to_key and not is_branch and len(names) > 1:
                    diagnostics.append({
                        "severity": "warning",
                        "source": parent_id,
                        "target": node_id,
                        "message": (
                            f"aresta sem from_key de '{parent_id}' ({len(names)} "
                            f"saídas: {sorted(names)}): espalha todas. Especifique "
                            f"from_key para evitar ambiguidade."
                        ),
                    })
        return diagnostics
