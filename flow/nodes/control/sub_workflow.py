import asyncio
from typing import Any, Dict
from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.nodes.outputs.sub_workflow_output import _parse_ports
from flow.utils.workflow_contract import MAX_PROFUNDIDADE
from flow.utils.logger import get_logger
from flow.utils.publisher.events import KIND_LIFECYCLE, LEVEL_INFO

logger = get_logger(__name__)

_CTX_ANCESTORS_KEY = "_subflow_ancestors"
_CTX_DISABLED_NODES_KEY = "_disabled_nodes"
_CTX_DEFINITIONS_KEY = "_subworkflow_definitions"

# Name of the wrapper returned to the parent. Reserved: an output port with this
# name would survive the return's `**public` and erase the whole dict.
RESULTADO = "subWorkflowResult"


def _onde_falhou(child: Any) -> str:
    """Suffix with the sub-workflow node that failed, when it can be known.

    `node_stats` is filled in each node's `finally`, so it's available
    even after the exception propagates.
    """
    stats = getattr(child, "node_stats", None) or {}
    quebrados = [
        (nid, info.get("node_name") or nid)
        for nid, info in stats.items()
        if isinstance(info, dict) and info.get("status") == "failed"
    ]
    if not quebrados:
        return ""
    nid, nome = quebrados[0]
    return f", no nó '{nome}' ({nid})"


class _SubWorkflowEventPublisher:
    """Forwards sub-workflow events to the parent's publisher, with a namespace.

    The child's node_ids don't exist on the parent's canvas — published raw, the
    frontend receives events from unknown nodes and discards them (or worse, paints
    the wrong node). By prefixing with the SubWorkflow node's id, the event stays
    traceable to the point of the graph that originated it, and the canvas can, in
    the future, drill down into the sub-workflow.

    The child's `__workflow_complete__` is NOT forwarded: it would end the parent's
    run in the frontend. The sub-workflow's completion is already signaled by the
    SubWorkflow node's own event.
    """

    _TERMINAL_NODE = "__workflow_complete__"

    def __init__(self, parent_publisher: Any, parent_node_id: str):
        self._parent = parent_publisher
        self._prefix = parent_node_id

    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Any = None,
        duration_ms: Any = None,
        error: Any = None,
        extra: Any = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        if node == self._TERMINAL_NODE:
            return
        meta = dict(extra or {})
        meta["subworkflow_parent_node"] = self._prefix
        # `nodes_total` is the progress denominator ("no 7 de 12") of the workflow that
        # emitted the event. Republished, it would make the parent's panel swap the
        # denominator for the child's in the middle of the run.
        meta.pop("nodes_total", None)
        try:
            self._parent.publish_event(
                run_id=run_id,
                node=f"{self._prefix}::{node}",
                status=status,
                timestamp=timestamp,
                duration_ms=duration_ms,
                error=error,
                extra=meta,
                kind=kind,
                level=level,
            )
        except Exception as exc:  # publicar evento nunca derruba a execucao
            logger.debug("Falha ao republicar evento do sub-fluxo: %s", exc)


@register_node
class SubWorkflowNode(BaseNode):
    """
    Control node that executes another workflow as a nested node.
    Allows composing complex workflows by reusing existing workflows.

    Properties:
      - workflowHash:     id_hash of the sub-workflow to execute
      - inputsMapping:    {"chave_sub_workflow": "chave_input_atual"}
      - timeoutSeconds:   maximum execution time (default 300)

    Hardening:
      - Loop detection via context["_subflow_ancestors"] (set of hashes)
      - Timeout via asyncio.timeout (only the sub-workflow's own deadline)
      - CancelledError propagated (cascading cancellation)
      - Specific messages (doesn't exist / deactivated / outside the workspace)
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            'name': 'SubWorkflow',
            'alias': 'Sub-Workflow',
            'description': (
                'Executa outro workflow como nó aninhado. '
                'Permite compor fluxos complexos reutilizando workflows existentes.'
            ),
            'type': 'control',
            'properties': [
                {
                    'name': 'workflowHash', 'required': True,
                    'label': 'Sub-workflow',
                    'type': 'string',
                    'default': '',
                    'description': 'id_hash do sub-workflow a ser executado.'
                },
                {
                    'name': 'inputsMapping',
                    'label': 'Mapeamento de entradas',
                    'type': 'object',
                    'default': {},
                    'description': (
                        'Mapeamento das entradas: '
                        '{"chave_sub_workflow": "chave_input_atual"}. '
                        'Se vazio, todos os inputs são repassados diretamente.'
                    )
                },
                {
                    'name': 'timeoutSeconds',
                    'label': 'Tempo limite (s)',
                    'type': 'integer',
                    'default': 300,
                    'description': (
                        'Tempo máximo de execução do sub-workflow em segundos. '
                        'Se exceder, o sub-fluxo é cancelado e o node falha.'
                    ),
                },
            ],
            'outputs': [
                {'name': 'subWorkflowResult', 'type': 'object', 'description': 'Resultado completo do sub-workflow executado'},
            ],
        }

    # ── Helpers internos ──────────────────────────────────────────────────

    def _check_subworkflow_contract(
        self, workflow_hash: str, definition: Dict[str, Any]
    ) -> None:
        """Ensures the sub-workflow declares its contract via SubWorkflowInput
        (entry point) and SubWorkflowOutput (public output).

        Without these two nodes, the caller has no way to map named inputs or
        consume named outputs — which made sub-workflows effectively
        unusable on the canvas (results indexed by node UUID).
        """
        inputs = [n for n in (definition.get("nodes") or []) if n.get("name") == "SubWorkflowInput"]
        outputs = [n for n in (definition.get("nodes") or []) if n.get("name") == "SubWorkflowOutput"]

        # SubWorkflowOutput is mandatory: it's what defines the return value.
        # We don't adopt n8n's "last executed node" — implicit and ambiguous
        # when the graph has branches.
        if not outputs:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' nao declara saida: falta o node "
                "SubWorkflowOutput. Adicione-o e conecte o que deve ser devolvido "
                "ao workflow chamador."
            )

        # SubWorkflowInput is OPTIONAL: a sub-workflow may receive nothing
        # (fixed source, internal parameters). Requiring it was bureaucracy.

        # At most one of each: `extract_contract` MERGES the ports of all
        # nodes of the type, but `collect_subworkflow_output` returns the FIRST
        # one found — with two, the contract announces ports the runtime never
        # delivers.
        if len(outputs) > 1:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' tem {len(outputs)} nodes "
                "SubWorkflowOutput. Apenas um e permitido — o contrato de saida "
                "precisa ser unico."
            )
        if len(inputs) > 1:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' tem {len(inputs)} nodes "
                "SubWorkflowInput. Apenas um e permitido."
            )

        # `subWorkflowResult` is the WRAPPER this node returns to the parent. A port
        # with that name would survive the return's `**public` and erase the whole
        # dict: whoever read `subWorkflowResult` expecting the public keys
        # would receive a raw value, with nothing explaining it.
        conflitantes = [
            p for p in _parse_ports((outputs[0].get("properties") or {}).get("ports"))
            if p == RESULTADO
        ] if outputs else []
        if conflitantes:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' declara uma saida chamada "
                f"'{RESULTADO}', que e o nome reservado do resultado devolvido ao "
                "workflow chamador. Renomeie essa porta no node SubWorkflowOutput."
            )

    def _check_disabled_nodes_in_definition(
        self, workflow_hash: str, definition: Dict[str, Any]
    ) -> None:
        """Blocks the sub-workflow if any node in it is on the admin's blacklist.

        The `_disabled_nodes` snapshot comes from the job envelope (server → executor)
        — propagated via WorkflowExecutor.context to all nodes. Allows
        blocking entire chains without having to query the server's DB at
        each level.
        """
        ctx = self.context or {}
        disabled: set[str] = ctx.get(_CTX_DISABLED_NODES_KEY) or set()
        if not disabled:
            return

        offenders = sorted({
            n.get("name") for n in (definition.get("nodes") or [])
            if n.get("name") in disabled
        })
        if offenders:
            raise ValueError(
                f"Sub-workflow '{workflow_hash}' contem node(s) desabilitados "
                f"pelo admin: {', '.join(offenders)}. Reabilite via "
                "/admin/settings ou substitua os nodes."
            )

    def _check_loop(self, workflow_hash: str) -> set[str]:
        """Checks whether the target workflow creates a cycle. Returns the new set of
        ancestors (current + hash) that will be injected into the child's context."""
        ctx = self.context or {}
        ancestors_raw = ctx.get(_CTX_ANCESTORS_KEY) or set()
        ancestors: set[str] = set(ancestors_raw) if not isinstance(ancestors_raw, set) else ancestors_raw

        if workflow_hash in ancestors:
            chain = " > ".join(list(ancestors) + [workflow_hash])
            raise ValueError(
                f"Loop detectado: workflow '{workflow_hash}' ja esta na cadeia "
                f"de execucao ({chain}). Sub-fluxos nao podem se chamar "
                "recursivamente, direta ou indiretamente."
            )

        return ancestors | {workflow_hash}

    def _fetch_definition_from_snapshot(self, workflow_hash: str) -> Dict[str, Any]:
        """Fetches the sub-workflow's definition from the snapshot sent by the server
        in the job envelope.

        The executor does NOT have DB access (only flow/ and executor/ in Docker). The
        entire chain of sub-workflows is pre-resolved by the server in
        workflow_execution_service.collect_subworkflow_definitions_recursive
        and sent via the job payload. We access it here via context.

        Raises ValueError when the hash is not in the snapshot — it may be:
        - Workflow doesn't exist / deactivated / another workspace (server didn't
          include it)
        - Chain exceeded max_depth (10) — unlikely
        - Operator changed workflowHash at runtime (impossible in persisted
          workflows, but defense in depth)
        """
        ctx = self.context or {}
        definitions: Dict[str, Dict[str, Any]] = ctx.get(_CTX_DEFINITIONS_KEY) or {}
        if workflow_hash in definitions:
            return definitions[workflow_hash]

        raise ValueError(
            f"Sub-workflow '{workflow_hash}' nao foi pre-resolvido pelo servidor. "
            "Causas comuns: workflow nao existe, esta desativado, ou pertence a "
            "outro workspace. Reabra o workflow chamador e re-salve para forcar "
            "uma revalidacao."
        )

    # ── Execucao ─────────────────────────────────────────────────────────

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 1) Parameter validation and extraction
        self.validate()

        workflow_hash = self.parameters.get('workflowHash', '').strip()
        inputs_mapping = self.parameters.get('inputsMapping', {})
        timeout = self.get_param_int("timeoutSeconds", 300)

        if not workflow_hash:
            raise ValueError("Parametro 'workflowHash' e obrigatorio e nao pode ser vazio.")

        if not isinstance(inputs_mapping, dict):
            raise TypeError(
                f"Parametro 'inputsMapping' deve ser um dicionario. "
                f"Tipo recebido: {type(inputs_mapping).__name__}"
            )
        if timeout <= 0:
            raise ValueError(
                f"Parametro 'timeoutSeconds' deve ser positivo (recebido: {timeout})."
            )

        logger.info(
            "SubWorkflowNode: iniciando sub-workflow '%s' (timeout=%ds, mapping=%s)",
            workflow_hash, timeout, list(inputs_mapping.keys()) or 'todos',
        )

        # 2) Loop detection — before any of the child's I/O.
        child_ancestors = self._check_loop(workflow_hash)

        # 2b) Depth. The server stops pre-resolving at MAX_PROFUNDIDADE
        # levels, and without this check the overflow reached the operator as
        # "workflow not found — doesn't exist, is deactivated, or belongs to another
        # workspace". None of the three was true, and the advice (re-save) didn't
        # help: they would go check three things that were correct.
        if len(child_ancestors) > MAX_PROFUNDIDADE:
            cadeia = " > ".join(list(child_ancestors)[:4]) + " > ..."
            raise ValueError(
                f"A cadeia de sub-fluxos passou de {MAX_PROFUNDIDADE} níveis ao "
                f"chamar '{workflow_hash}' ({cadeia}). O servidor só pré-resolve "
                f"até esse limite. Achate a cadeia — um sub-fluxo intermediário "
                "geralmente pode ser absorvido pelo chamador."
            )

        # 3) Resolves the child's definition in the envelope snapshot (the server
        # already pre-resolved the whole chain). No I/O, no DB, no app.* import.
        definition = self._fetch_definition_from_snapshot(workflow_hash)

        # 3.5) Validates that the sub-workflow doesn't use nodes disabled by the admin.
        # Runs AFTER resolving the definition (it needs the child's content).
        self._check_disabled_nodes_in_definition(workflow_hash, definition)

        # 3.6) Validates that the sub-workflow has a declared contract: SubWorkflowInput
        # as the entry point + SubWorkflowOutput as the public output. Without it,
        # the caller can't pass named data or read usable keys.
        self._check_subworkflow_contract(workflow_hash, definition)

        # 4) Builds the sub-workflow's inputs
        if inputs_mapping:
            # A missing source key ABORTS, not just warns.
            #
            # Before, the sub-workflow ran in full and returned None for that key: the
            # run finished green, the parent went on with a null, and the only sign was
            # a warning lost in the log. And the common case is not a typo
            # — it's the upstream edge being removed or having its `to_key` renamed
            # AFTER the mapping was done, when nobody is looking
            # at this node.
            faltando = [
                (sub_key, src_key)
                for sub_key, src_key in inputs_mapping.items()
                if src_key not in inputs
            ]
            if faltando:
                detalhe = "; ".join(f"'{s}' (para '{d}')" for d, s in faltando)
                raise ValueError(
                    f"O mapeamento de entradas aponta para chave(s) que não chegaram "
                    f"a este nó: {detalhe}. Chegaram: "
                    f"{sorted(inputs) or '<nenhuma>'}. Corrija o mapeamento ou "
                    "reconecte a origem — o sub-fluxo receberia nulo no lugar."
                )
            sub_inputs: Dict[str, Any] = {
                sub_key: inputs[src_key] for sub_key, src_key in inputs_mapping.items()
            }
        else:
            sub_inputs = dict(inputs)

        logger.info(
            "SubWorkflowNode: executando sub-workflow '%s' com inputs: %s",
            workflow_hash, list(sub_inputs.keys()),
        )

        # 5) Executes the sub-workflow ON THE SAME event loop, with a timeout.
        #
        # Before: asyncio.to_thread(run_sync) -> run_sync did asyncio.run(), i.e.,
        # a NEW event loop inside a thread. That brought three problems:
        #   a) wait_for canceled the wait, not the thread — on timeout the sub-workflow
        #      kept running, consuming CPU/RAM/connections and possibly writing
        #      artifacts after the node had already failed;
        #   b) the parent's CancelledError didn't cascade, for the same reason;
        #   c) globally cached asyncpg pools are bound to the loop that
        #      created them — reusing them on the child's loop breaks with "attached to a
        #      different loop".
        # Running in the same coroutine, the deadline really cancels and there's only one loop.
        #
        # Propagates the EXECUTION SCOPE (task_id, workspace_id, publisher, debug):
        # without it the child instantiated a bare WorkflowExecutor(definition) and every
        # node that calls require_scope() — DataOutput, PublishMap, SaveToS3,
        # SaveToShapefile, SaveToGeoparquet, SendEmail — failed with
        # "workspace_id nao injetado pelo executor".
        #
        # And the THREE envelope snapshots, without which the chain A→B→C fails at B:
        # _subflow_ancestors (loop detection), _disabled_nodes, _subworkflow_definitions.
        inherited_disabled = (self.context or {}).get(_CTX_DISABLED_NODES_KEY) or set()
        inherited_defs = (self.context or {}).get(_CTX_DEFINITIONS_KEY) or {}

        from flow.executor import WorkflowExecutor

        child = WorkflowExecutor(
            definition,
            task_id=self._task_id,
            workspace_id=self._workspace_id,
            # The CHILD's workflow_hash: the sub-workflow's artifacts and metrics must
            # be attributed to it, not to the parent.
            workflow_hash=workflow_hash,
            publisher=_SubWorkflowEventPublisher(self._publisher, self.node_id)
            if self._publisher else None,
            debug_mode=self._debug_mode,
            # Shares task_id with the parent (needed for require_scope in the
            # output nodes), so it must NOT clean up resources indexed by it:
            # the spill-to-disk lives in /tmp/atlans_spill/<task_id> and would be
            # deleted at the end of the sub-workflow, taking the parent's data with it.
            is_nested=True,
        )
        child.context[_CTX_ANCESTORS_KEY] = child_ancestors
        child.context[_CTX_DISABLED_NODES_KEY] = set(inherited_disabled)
        child.context[_CTX_DEFINITIONS_KEY] = dict(inherited_defs)

        def _erro_do_filho(e: BaseException) -> RuntimeError:
            logger.error(
                "SubWorkflowNode: erro durante execucao do sub-workflow '%s': %s",
                workflow_hash, e,
            )
            # Name the node that broke. Without this the message was just the raw cause
            # ("division by zero") — in a fifteen-node sub-workflow it locates
            # nothing, and the child's interior doesn't appear in the execution panel.
            return RuntimeError(
                f"Erro ao executar o sub-workflow '{workflow_hash}'"
                f"{_onde_falhou(child)}: {e}"
            )

        # `asyncio.timeout` and not `wait_for`: from 3.11 onward
        # `asyncio.TimeoutError` IS the built-in TimeoutError, and one from a node of
        # the child (the PythonScript deadline) would become "excedeu o timeout de 300s,
        # aumente timeoutSeconds" — the wrong advice. It's only the sub-workflow's
        # deadline if that one expired.
        prazo = asyncio.timeout(timeout)
        try:
            async with prazo:
                result = await child.run(initial_inputs=sub_inputs)
        except asyncio.CancelledError:
            # The parent's cancellation propagates to the child — don't swallow it.
            logger.info("SubWorkflowNode: sub-workflow '%s' cancelado.", workflow_hash)
            raise
        except TimeoutError as exc:
            if not prazo.expired():
                raise _erro_do_filho(exc) from exc
            raise RuntimeError(
                f"Sub-workflow '{workflow_hash}' excedeu o timeout de {timeout}s. "
                "Aumente 'timeoutSeconds' ou investigue por que o sub-fluxo trava."
            ) from exc
        except ValueError:
            # The child's validation errors (e.g.: loop detected at a deeper level)
            # must propagate without rewrapping.
            raise
        except Exception as e:
            raise _erro_do_filho(e) from e

        logger.info(
            "SubWorkflowNode: sub-workflow '%s' concluido. Chaves de resultado: %s",
            workflow_hash, list(result.keys()) if result else [],
        )

        # 6) Resolves the child's public outputs via SubWorkflowOutput.
        # The contract was validated in (3.6) — if there's no
        # __subworkflow_output__ here, it's an executor bug (node didn't execute).
        from flow.executor.result_helpers import collect_subworkflow_output

        public = collect_subworkflow_output(result)
        if public is None:
            raise RuntimeError(
                f"Sub-workflow '{workflow_hash}' concluiu mas o node "
                "SubWorkflowOutput nao foi executado nesta rodada. Verifique "
                "se ele esta conectado ao grafo ativo (algum branch pode estar "
                "isolando-o do fluxo)."
            )

        logger.info(
            "SubWorkflowNode: sub-workflow '%s' expos %d chave(s) publica(s) via "
            "SubWorkflowOutput: %s",
            workflow_hash, len(public), list(public.keys()),
        )
        return {RESULTADO: public, **public}
