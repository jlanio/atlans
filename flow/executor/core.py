# flow/executor/core.py
"""Orquestrador principal do workflow."""
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
# A regra do alias mora em flow/core/aliases.py (puro) para o lint estático
# aplicar a MESMA sem puxar o registry de nós. O nome com underscore segue
# existindo aqui: tests/unit/test_alias_expressions.py importa `_resolve_alias`
# de flow.executor.core.
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
    """Adia o resumo de um dict de inputs/outputs até o log ser realmente emitido.

    O `logging` só chama `__str__` de um argumento `%s` quando algum handler
    aceita o record. Antes o executor logava `f"... com inputs {inputs}"`: a
    f-string é interpolada EAGER, uma vez por nó, dentro do event loop, mesmo
    com o nível acima de DEBUG. Como `http_request` devolve o `response.json()`
    cru e `python_script` devolve qualquer objeto do usuário, um payload de
    dezenas de MB virava segundos de CPU e centenas de MB de pico só para
    montar uma string que ninguém ia ler.
    """
    __slots__ = ("_data",)

    def __init__(self, data: Any) -> None:
        self._data = data

    def __str__(self) -> str:
        if not isinstance(self._data, dict):
            return f"<{type(self._data).__name__}>"
        # Resume por chave (contagem/colunas para tabulares, 300 chars para
        # escalares). `with_bounds=False` tira o `total_bounds` do caminho de
        # log: é uma varredura O(n) sobre todas as geometrias (13,6 ms num GDF
        # de 300k feições) que só se justifica no evento de debug, que é opt-in
        # por `debug_mode`.
        # Não é custo zero: dicts e listas aninhados ainda passam por
        # json.dumps. O que se garante é que nada disso roda com o nível acima
        # de DEBUG, e que strings/bytes gigantes são fatiados ANTES de serem
        # serializados.
        return str(_build_debug_summary(self._data, with_bounds=False))


# Teto para esperar as threads de spill em voo no encerramento do run. Só é
# exercido em run cancelado/abortado; escrever um Parquet de ~50 MB fica bem
# abaixo disso, então o teto existe só para não travar o cleanup para sempre.
_SPILL_DRAIN_TIMEOUT_S = 30.0

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    Orquestra a execução do workflow, com renderização de parâmetros via Jinja2
    e sistema de "aliases" ($Alias) para referenciar outputs de nós anteriores.
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
        # Execucao aninhada (sub-workflow): compartilha task_id com o pai, entao
        # nao pode limpar recursos indexados por ele — quem limpa e o raiz.
        self.is_nested = is_nested
        self.definition = definition
        self.publisher = publisher
        self.debug_mode = debug_mode
        self.workspace_id = workspace_id
        self.workflow_hash = workflow_hash
        self.pinned_outputs = pinned_outputs or {}
        self.pin_metadata = pin_metadata or {}
        # Refs de pin GRAVADAS NESTA run (auto-pin). É o que volta ao servidor em
        # __updated_pinned_outputs__. Não pode ser derivado de pinned_outputs no
        # fim do run: lá também vivem as refs que vieram do servidor e apenas
        # passaram pela run — e o consumer re-deriva a s3_key com o task_id
        # ATUAL, então re-reportar uma ref antiga a repontava para um objeto que
        # nunca existiu (404 em toda run seguinte).
        self.updated_pin_refs: Dict[str, Any] = {}
        self.logger = get_logger(__name__)
        self.metrics_collector = MetricsCollector()

        self.node_stats: Dict[str, Any] = {}
        self.all_node_outputs: Dict[str, Dict[str, Any]] = {}
        # Contexto compartilhado entre nodes:
        # - _subflow_ancestors: set de hashes ja na cadeia, para SubWorkflowNode
        #   detectar loops em qualquer nivel.
        # - _disabled_nodes: snapshot enviado pelo servidor no envelope do job,
        #   usado por SubWorkflowNode para bloquear sub-fluxos que contenham
        #   nodes desabilitados pelo admin.
        # - _subworkflow_definitions: definitions pre-resolvidas da cadeia
        #   inteira de sub-workflows (servidor → executor via envelope). O executor
        #   nao tem acesso ao DB, entao SubWorkflowNode busca aqui.
        # Filhos copiam este dict e propagam para o executor aninhado.
        self.context: Dict[str, Any] = {
            "_disabled_nodes": set(disabled_nodes or []),
            "_subworkflow_definitions": dict(subworkflow_definitions or {}),
            # O proprio workflow ja esta na cadeia. Sem isto, um fluxo que se
            # chama a si mesmo so era barrado no SEGUNDO nivel — e ate la ele ja
            # tinha rodado inteiro mais uma vez, mandando o e-mail e gravando o
            # artefato de novo. Como o run termina em erro, e facil nao perceber
            # que os efeitos colaterais aconteceram em dobro.
            #
            # O sub-fluxo SOBRESCREVE esta chave com a cadeia que recebeu do pai
            # (SubWorkflowNode), entao aqui ela so importa para a raiz.
            "_subflow_ancestors": {workflow_hash} if workflow_hash else set(),
        }

        node_defs = {n['id']: n for n in definition.get('nodes', [])}
        edges = definition.get('edges', [])
        self.graph = WorkflowGraph(node_defs, edges, filter_isolated=True)
        self.execution_order = self.graph.compute_order()
        self.logger.info("Ordem de execução: %s", self.execution_order)

        self.node_mgr = NodeManager(node_defs)
        self.node_mgr.instantiate_nodes(self.execution_order)
        # auto_map_edges (backfill legado de from_key/to_key a partir de
        # outputKey*/inputKey* nos params) foi aposentado: nenhum nó nem o front
        # atual emitem esses params, e o front já grava from_key na aresta. A
        # semântica da aresta agora vem só da própria aresta. Ver
        # docs/specs/edge-data-contract.md §5.

        for node in self.node_mgr.nodes.values():
            node._publisher      = self.publisher
            node._task_id        = self.task_id
            node._debug_mode     = self.debug_mode
            node._workspace_id   = self.workspace_id
            node._workflow_hash  = self.workflow_hash
            # context do node aponta para o mesmo dict do executor — permite
            # SubWorkflowNode ler/escrever _subflow_ancestors transparente.
            node.context         = self.context

        self.incoming = {nid: ev for nid, ev in self.graph.incoming.items() if nid in self.execution_order}
        self.outgoing = {nid: ev for nid, ev in self.graph.outgoing.items() if nid in self.execution_order}
        # Arestas de RAMO desativadas neste run (por id do dict da aresta — o
        # mesmo objeto vive em incoming e outgoing, ver flow/core/graph.py). A
        # montagem de inputs consulta este conjunto para NAO injetar no merge o
        # dado de um ramo que nao foi tomado: filtrar so os pais com status
        # 'skipped' nao bastava, porque um no de controle vivo (status
        # 'completed') cuja aresta de ramo foi desativada continuava contribuindo.
        self._deactivated_edge_ids: set[int] = set()

        self.final_outputs: Dict[str, Any] = {}
        # Tasks de spill em voo. `asyncio.to_thread` não é cancelável, então
        # elas sobrevivem ao cancelamento do run e precisam ser drenadas antes
        # do rmtree do _cleanup_spill — ver _drain_spills.
        self._spill_inflight: "set[asyncio.Task]" = set()

    # ── Pin data ─────────────────────────────────────────────────────────────

    def _upload_pin_artifact(self, node_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        return _pin.upload_pin_artifact(node_id, outputs, self.workspace_id, self.task_id)

    @staticmethod
    def _download_pin_artifact(pinned: Dict[str, Any]) -> Dict[str, Any]:
        return _pin.download_pin_artifact(pinned)

    # ── Expression rendering ──────────────────────────────────────────────────

    def _render_node_parameters(self, node_id: str, named: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Renderiza parâmetros e retorna cópia renderizada (sem mutar o original)."""
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
        """Resolve pin data para um nó. Retorna outputs desserializados ou None."""
        pinned = self.pinned_outputs.get(node_id)
        if not pinned:
            return None

        # Verifica expiração
        node_meta = self.pin_metadata.get(node_id, {})
        expires_at_str = node_meta.get("expires_at")
        if expires_at_str:
            try:
                if utc_now_naive() > datetime.fromisoformat(expires_at_str):
                    # O objeto no MinIO nao e removido aqui: o executor nao tem
                    # credenciais de storage. O servidor apaga em
                    # DELETE /workflows/{id_hash}/pin/{node_id} e sobrescreve no
                    # re-pin (mesma s3_key).
                    self.logger.info("[%s] Pin data expirado — executando nó normalmente.", node_id)
                    return None
            except (ValueError, TypeError) as exc:
                logger.debug("Formato de pin inválido, ignorando: %s", exc)

        # Download do MinIO se necessário
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
        """Auto-cura de pin quebrado: zera a ref para o auto-pin regravar já nesta run.

        Sem isto, uma ref cujo objeto sumiu do MinIO (purga, bucket limpo,
        upload perdido) ficava presa para sempre: o auto-pin só dispara com a
        ref VAZIA, então toda run seguinte repetia o 404 e re-executava o nó.
        Só se aplica a pin com metadata (intenção explícita do usuário) — e NÃO
        ao pin expirado, cuja lacuna é deliberada até alguém re-pinar.
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

        # Duas linhas, dois níveis, de propósito: o QUE está rodando é a única
        # pista que `docker logs executor` dá quando o WebSocket para o servidor
        # cai, então fica em INFO com args %s (custo O(1), sem payload). O
        # conteúdo dos inputs é caro de resumir e fica em DEBUG.
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
                    # MUDANCA DE COMPORTAMENTO: so retenta erro TRANSITORIO
                    # (rede/timeout, ver flow/utils/error_taxonomy). Antes qualquer
                    # Exception era retentada, o que (a) reexecutava node.execute()
                    # inteiro num erro deterministico (validacao, dado ruim) sem
                    # chance de o resultado mudar e (b) repetia efeitos colaterais
                    # de nos nao idempotentes. A ultima tentativa tambem cai aqui.
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
                # Quais colunas cada saida tinha. E o que permite ao editor
                # sugerir nomes de coluna em vez de exigir que a pessoa execute
                # o fluxo so para descobrir o que chega no proximo no.
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
                # O dict leve de referências fica SÓ em all_node_outputs — é o
                # caminho de `parent_outputs`, o único que rehidrata via
                # `_load_from_disk`. `named[alias]`/`final_outputs` continuam
                # com o payload real de propósito: o contexto Jinja não
                # rehidrata nada, então devolver `spilled` aqui faria
                # `{{ Alias.gdf }}` renderizar `{'__spilled__': True, …}` e
                # deixaria `final_outputs` apontando para Parquets que
                # `_free_node_outputs` já apagou. Trocar pico de RAM por
                # corrupção silenciosa de dado é mau negócio.
                spilled = await self._spill_shielded(node_id, outputs)
                if spilled is not outputs:
                    self.all_node_outputs[node_id]["outputs"] = spilled
            _branch_result = outputs.get("branch") if outputs and isinstance(outputs.get("branch"), bool) else None

            # Schema drift: compara keys retornadas com o declarado no catálogo
            # (`outputs` do descriptor). A definition salva nunca carregou o
            # declarado, então a leitura antiga (node_def) comparava com nada.
            # Nós de saída dinâmica ficam de fora: neles quem manda é o payload
            # (`output_vars`, `ports`), não o descriptor.
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
            # `end_node` faz uma varredura O(n) sobre o GDF de saida
            # (`total_bounds` sempre; contagem de vertices/tipos no debug) — que
            # segurava o event loop no fim de cada no. Vai para thread. Com o
            # batch rodando nos em paralelo (`asyncio.gather`), varios `end_node`
            # passam a correr de fato concorrentes; o unico estado compartilhado
            # que tocam e `run_tracker.sample()`, agora protegido por lock em
            # ResourceTracker (o `nm` e por node_id).
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
            # `outputs` é o payload real (o dict leve de spill só foi parar em
            # all_node_outputs): o resumo de debug precisa das colunas/bounds
            # do GDF, não da referência.
            self._publish_debug(node_id, inputs, outputs or {})

        return node_id, outputs, duration_ms

    async def _spill_shielded(self, node_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Roda `_spill_to_disk` numa thread, blindado contra cancelamento.

        O shield é obrigatório e não é opcional trocar por um await nu: uma
        thread em execução não é cancelável, então cancelar o future só
        descartaria o resultado enquanto o Parquet continuaria sendo escrito —
        e ninguém saberia o path para apagá-lo. Registrando a task em
        `_spill_inflight` o `finally` de `run()` consegue esperá-la (ver
        `_drain_spills`) antes de apagar o diretório.
        """
        task = asyncio.ensure_future(
            asyncio.to_thread(_spill_to_disk, self.task_id, node_id, outputs)
        )
        self._spill_inflight.add(task)
        task.add_done_callback(self._spill_inflight.discard)
        return await asyncio.shield(task)

    async def _drain_spills(self) -> None:
        """Espera as escritas de spill em voo antes de o diretório ser apagado.

        Caminho de falha real: `executor/job_executor.py` envolve `run()` num
        `asyncio.wait_for(..., JOB_TIMEOUT)`. No estouro, o shield devolve
        CancelledError ao awaiter mas as threads seguem gravando; se o
        `shutil.rmtree` de `_cleanup_spill` rodar antes delas, cada thread cujo
        `os.makedirs` ainda não tinha rodado RECRIA o diretório e grava um
        Parquet que ninguém mais apaga — `_cleanup_spill` é o único ponto de
        limpeza do processo, não há janitor nem varredura na subida. Medido:
        5,5 MB órfãos permanentes num único run cancelado; com GDFs reais
        (>50 MB, o threshold) são centenas de MB no mesmo /tmp do ARTIFACTS_DIR.

        No caminho feliz o conjunto está vazio (cada spill é aguardado no nó),
        então isto custa um `if`.
        """
        pending = [t for t in self._spill_inflight if not t.done()]
        self._spill_inflight.clear()
        if not pending:
            return
        try:
            # `asyncio.wait` (e não `wait_for`) porque no timeout ele apenas
            # devolve o que sobrou em vez de cancelar — cancelar não pararia a
            # thread e ainda mascararia o erro. O teto evita que um spill
            # patológico segure o cleanup para sempre.
            _done, ainda = await asyncio.wait(pending, timeout=_SPILL_DRAIN_TIMEOUT_S)
        except asyncio.CancelledError:
            # Segundo cancelamento durante o dreno. Não dá para esperar mais,
            # mas o cleanup logo abaixo precisa rodar; o CancelledError que já
            # estava propagando pelo `finally` de run() segue seu curso.
            self.logger.warning("Dreno do spill cancelado — pode restar Parquet órfão.")
            return
        for task in _done:
            # Consome a exceção: ninguém mais vai await essas tasks (o awaiter
            # original levou CancelledError do shield) e o asyncio despejaria
            # "Task exception was never retrieved" no log do container.
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
        # `nodes` aponta para o dict vivo de all_node_outputs em vez de uma cópia
        # populada a cada nó: era um segundo índice node_id → entry que ninguém
        # lia (o contexto per-node de _run_node_with_tracking já usa
        # self.all_node_outputs) e que só servia para duplicar referências.
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
        # Nós que receberam dado por ALGUMA aresta ATIVA de um pai vivo. Um merge
        # com um pai vivo e um pai skipado NÃO pode ser skipado só porque o skip
        # do ramo irmão zerou o pending por último (F2 — antes o resultado
        # dependia da ordem do batch). "Pai vivo por aresta ativa" ≠ "tem pai
        # vivo": o próprio nó de bifurcação é vivo, mas o filho do ramo NÃO
        # tomado chega por aresta desativada e deve ser skipado.
        has_live_input: set = set()
        ready_nodes = deque([nid for nid in self.execution_order if pending_parents_count[nid] == 0])

        # try/finally: antes, um nó que levantasse exceção abortava o run ANTES
        # do _cleanup_spill. Os Parquets ficavam em /tmp e — pior — as cópias
        # relidas continuavam presas no _spill_cache, que é um dict de módulo:
        # num executor long-running, cada run que falhava vazava GeoDataFrames
        # inteiros pelo resto da vida do processo.
        try:
            while ready_nodes:
                tasks = []
                current_batch = list(ready_nodes)
                ready_nodes.clear()

                # Rastreia pais consumidos neste batch para decrementar APÓS execução
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
                            # Pai skipado (ramo não tomado) não contribui: a aresta
                            # some (F14), em vez de injetar None/vazio no merge. O
                            # resolvedor já omitiria (pai vazio → {}); pular aqui
                            # evita também um warning espúrio de "from_key ausente"
                            # sobre um {} esperado.
                            if self.node_stats.get(parent_id, {}).get("status") == "skipped":
                                continue
                            # Aresta de RAMO não tomada: o pai (nó de controle) está
                            # VIVO (status 'completed'), então o filtro de 'skipped'
                            # acima não a pega. Sem isto, um merge que também recebe
                            # dado real de outro pai (has_live_input, por isso RODA
                            # em vez de ser skipado) juntava silenciosamente a saída
                            # do ramo REJEITADO — resultado errado, sem erro.
                            if id(edge) in self._deactivated_edge_ids:
                                continue
                            # `_load_from_disk` faz `gpd.read_parquet` (disco +
                            # desserializacao de geometria): sincrono no loop, um
                            # GDF derramado de ~200MB o segurava por >1s sem
                            # agendar heartbeat/cancel de NENHUM job (a ESCRITA do
                            # spill ja ia para thread via `_spill_shielded`; a
                            # leitura nao). O cache interno e guardado por
                            # `_spill_lock`, entao chamar de outra thread e seguro.
                            parent_outputs = await asyncio.to_thread(
                                _load_from_disk, self.all_node_outputs[parent_id]['outputs']
                            )
                            # Fonte única da semântica da aresta (from_key/to_key/spread) —
                            # a MESMA usada pela simulação de schema abaixo. Ver
                            # flow/executor/edge_resolver.py e docs/specs/edge-data-contract.md.
                            inputs.update(resolve_edge_inputs(
                                edge, parent_outputs,
                                logger=self.logger, node_id=node_id, parent_id=parent_id,
                            ))
                            batch_consumed_parents.append(parent_id)

                    tasks.append(self._run_node_with_tracking(node_id, inputs))

                # Cancela os irmaos na PRIMEIRA falha. MUDANCA DE COMPORTAMENTO:
                # antes (asyncio.gather sozinho) um no que levantava deixava os
                # irmaos do mesmo batch rodando ate o fim — DEPOIS de o run ja ter
                # sido reportado como falho —, e eles ainda commitavam insert,
                # enviavam e-mail, subiam artefato (efeito colateral de um run que o
                # usuario ve como falho) e disparavam _spill_shielded apos a limpeza
                # (Parquet orfao). Agora tarefas explicitas: na 1a excecao os
                # pendentes sao cancelados e aguardados antes de propagar. Uma tarefa
                # presa em asyncio.to_thread nao morre (a thread segue), mas o
                # cancelamento impede o no cancelado de COMMITAR o efeito no await
                # seguinte.
                task_objs = [asyncio.ensure_future(t) for t in tasks]
                try:
                    results = await asyncio.gather(*task_objs)
                except BaseException:
                    for t in task_objs:
                        if not t.done():
                            t.cancel()
                    await asyncio.gather(*task_objs, return_exceptions=True)
                    raise

                # Decrementa remaining_consumers APÓS a execução do batch
                for parent_id in batch_consumed_parents:
                    remaining_consumers[parent_id] -= 1
                    if remaining_consumers[parent_id] <= 0:
                        self._free_node_outputs(parent_id)

                for node_id, outputs, duration_ms in results:
                    node_def = self.node_mgr.node_defs[node_id]

                    executed.add(node_id)
                    self.final_outputs[node_id] = outputs
                    alias = _resolve_alias(node_def)
                    # Só `named` guarda o alias. O `context[alias]` daqui era morto:
                    # o contexto que chega no Jinja é o construído por nó em
                    # _run_node_with_tracking, e render_node_parameters faz
                    # `context.update(named)` — a chave de topo já vem de `named`.
                    named[alias] = outputs

                    # Filtra edges ativas (branch filtering sem mutar self.outgoing).
                    # O roteamento é gateado pela presença de ARESTAS DE RAMO
                    # (condition bool), não pelo output cru "branch":
                    #  - F7: um nó comum (python_script, http_request) cujo output
                    #    tenha uma chave booleana 'branch' NÃO sequestra o
                    #    roteamento — sem arestas de ramo, nada é filtrado/skipado.
                    #  - F8: arestas de DADO (sem condition) permanecem SEMPRE
                    #    ativas; só as arestas de ramo com condition != branch são
                    #    desativadas. Antes, condition=None != branch desativava a
                    #    aresta de dado e skipava o alvo.
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

                        # Propaga skip só para o alvo das arestas de RAMO não escolhidas
                        deactivated = [e for e in branch_edges if e.get("condition") != branch]
                        for edge in deactivated:
                            # Registra a aresta desativada para a montagem de inputs
                            # do alvo NAO injetar a saida deste ramo (o alvo pode
                            # sobreviver por ter outro pai vivo). Feito ANTES de o
                            # alvo virar ready (proximo batch), entao a montagem ja
                            # a ve.
                            self._deactivated_edge_ids.add(id(edge))
                            self._propagate_skip(
                                edge["target"], pending_parents_count,
                                remaining_consumers, executed,
                                ready_nodes, has_live_input,
                            )

                    for edge in active_edges:
                        child_id = edge["target"]
                        # Aresta ativa vinda deste nó, que acabou de rodar (vivo):
                        # o filho recebeu dado real. Marca ANTES do pending para
                        # que um skip posterior de ramo irmão o veja e não o apague.
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
        """Propaga skip para nodes de um branch não selecionado.

        Decrementa pending_parents_count e, quando TODOS os pais de `node_id`
        já foram resolvidos (pending == 0), decide:
          - se o nó recebeu dado por ALGUMA aresta ATIVA de um pai vivo
            (`has_live_input`) → tem input real e DEVE rodar: entra em
            `ready_nodes` em vez de virar skipped. É o merge/diamante em que um
            ramo morreu mas o outro entregou dado (F2); antes o resultado
            dependia da ordem do batch — o skip do ramo irmão podia zerar o
            pending por último e apagar o nó vivo;
          - senão (todos os pais chegaram por skip / aresta desativada) → marca
            skipped e propaga recursivamente.

        `pending == 0` garante que todo pai já foi resolvido (executou ou foi
        skipado), então `has_live_input` está completo aqui.
        """
        if node_id in executed:
            return

        pending_parents_count[node_id] -= 1
        if pending_parents_count[node_id] > 0:
            # Ainda tem outro pai pendente — não pode decidir ainda
            return

        if node_id in has_live_input:
            # Recebeu dado por aresta ativa de um pai vivo: roda, não skipa.
            if node_id not in executed:
                ready_nodes.append(node_id)
            return

        # Marca como executado (skipped) para não entrar em ready_nodes
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

        # Propaga skip para filhos
        for edge in self.outgoing.get(node_id, []):
            self._propagate_skip(
                edge["target"], pending_parents_count,
                remaining_consumers, executed,
                ready_nodes, has_live_input,
            )

    def _free_node_outputs(self, node_id: str) -> None:
        """Solta a referência em `all_node_outputs` e apaga o spill de um nó já consumido.

        NÃO remove o alias de `named`: ele alimenta o contexto Jinja e precisa
        continuar disponível para `{{ Alias.x }}` em nós posteriores.

        Por isso a economia de RAM aqui é parcial e proposital — `named[alias]`
        e `final_outputs[node_id]` seguem apontando para o payload real, que só
        morre com o executor. O que esta chamada libera de fato são as CÓPIAS:
        o Parquet em disco e a cópia relida que o `_spill_cache` (dict de
        módulo) manteria viva pelo resto da vida do processo.
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

            # `outputs_from_ports` (SubWorkflowInput) declara `outputs: []`
            # sem `dynamic_output`, mas as saídas reais são as `ports` do payload:
            # segue pelo caminho declarado, não pelo estático.
            if not desc.get("dynamic_output") and not desc.get("outputs_from_ports"):
                self.simulated_outputs[node_id] = {
                    "status": "ok",
                    "schema": schema_do_catalogo(desc),
                    "schema_source": "static",
                }
                continue

            simulate_fn = getattr(node_cls, "simulate", None)
            if not simulate_fn:
                # Antes era só `continue`, e o nó SUMIA da resposta: oito nós do
                # catálogo (PythonScript, Switch, ReadGeoJSON, WFS, DataInput...)
                # têm `dynamic_output` e nenhum `simulate()`, então o /validate
                # os omitia em silêncio — painel sem schema e `from_key` errado
                # saindo deles passando sem diagnóstico. As saídas estão escritas
                # na própria definição (`output_vars`, `rules`/`fallback_output`,
                # `ports`) ou no `outputs` do catálogo; `schema_source` diz de onde o
                # schema veio, para o consumidor saber o quanto confiar nele.
                try:
                    declarado = schema_declarado(node_def, desc)
                except ValueError as exc:
                    # Declaração que o run recusaria em validate() (`output_vars`
                    # vazio/não-string): mesma frase, status "error". Antes virava
                    # schema vazio com `ok` — e sem saídas conhecidas o diagnóstico
                    # de aresta se desligava junto.
                    self.logger.warning(
                        "Saída declarada inválida no nó %s (%s): %s", node_id, node_type, exc,
                    )
                    self.simulated_outputs[node_id] = {"status": "error", "error": str(exc)}
                    continue
                if declarado is None:
                    # Sem `outputs` no catálogo e sem nada declarado no payload não há o
                    # que afirmar — mas o nó fica na resposta, com a origem dizendo
                    # isso. Omitir era exatamente o silêncio que este ramo remove.
                    self.simulated_outputs[node_id] = {
                        "status": "ok", "schema": [], "schema_source": "unknown",
                    }
                else:
                    self.simulated_outputs[node_id] = {
                        "status": "ok", "schema": declarado, "schema_source": "declared",
                    }
                continue

            try:
                # A assinatura e (parametros_do_no, lista_de_propriedades). Antes
                # recebia o node_def inteiro e a CLASSE: `for prop in props`
                # levantava TypeError('type' object is not iterable), que o
                # except abaixo transformava em {"status": "error"}. Resultado:
                # `simulate()` nunca era chamado e /workflows/validate devolvia
                # erro para todo no com dynamic_output.
                #
                # `parameters` e o formato do corpo da validacao; `properties` e o
                # da definition salva — mesma tolerancia de `node_props` no
                # servidor.
                params = validate_node_parameters(
                    node_def.get("parameters") or node_def.get("properties") or {},
                    desc.get("properties", []),
                    # Do descriptor, nao do payload: a validacao aceita
                    # definition arbitraria, e o nome so entra formatado no log.
                    # O lookup no registry ja garantiu que o tipo existe.
                    node_name=desc.get("name", node_type),
                )
                simulated_inputs: Dict[str, Any] = {}
                for edge in self.incoming.get(node_id, []):
                    parent_id = edge["source"]
                    parent_output = self.simulated_outputs.get(parent_id)
                    if not parent_output or parent_output.get("status") != "ok":
                        continue

                    # MESMO resolvedor do run, no plano de schema: as portas que a
                    # simulação nomeia passam a bater com as que o run produz (antes
                    # o caso "sem chaves" divergia — run espalhava, sim nomeava por
                    # parent_id). Ver flow/executor/edge_resolver.py.
                    #
                    # F11: `schema` pode ser [] (SubWorkflowInput/Output têm
                    # outputs=[]). `.get("schema", [{}])` só usa o default
                    # quando a CHAVE falta; com lista vazia, [][0] estourava
                    # IndexError, o except marcava o FILHO como error e cascateava
                    # por todo o preview. Normaliza a lista vazia aqui.
                    schema_list = parent_output.get("schema") or []
                    parent_fields = schema_list[0].get("fields", []) if schema_list else []
                    simulated_inputs.update(resolve_edge_schema_inputs(edge, parent_fields))

                schema = await simulate_fn(params, simulated_inputs)
                self.simulated_outputs[node_id] = {
                    "status": "ok", "schema": schema, "schema_source": "simulated",
                }
            except Exception as exc:
                # O preview segue (status "error" so neste no), mas a causa nao
                # pode ser muda: engolida aqui, um simulate() quebrado aparecia
                # como "no sem schema" e ninguem descobria o porque.
                self.logger.warning(
                    "simulate() falhou no nó %s (%s): %s", node_id, node_type, exc,
                )
                self.simulated_outputs[node_id] = {"status": "error", "error": str(exc)}

        return self.simulated_outputs

    def validate_edges(self) -> "list[dict]":
        """Diagnósticos estáticos de aresta a partir do schema simulado.

        Aqui mora o enforcement strict que o RUN não faz (o run só omite a porta,
        para não derrubar um fluxo por causa de uma saída opcional/dinâmica). A
        checagem estática tem o schema declarado à mão e pode acusar antes de
        rodar, sem risco de falso-positivo em runtime:

          - `from_key` que NÃO é saída declarada da origem → **erro** (fiação
            defasada — a aresta não entregaria nada no run);
          - aresta de dado sem `from_key`/`to_key` saindo de origem com >1 saída
            → **aviso** de ambiguidade (espalha tudo; convém nomear a porta).

        Exige `simulate_runner()` rodado antes (usa `self.simulated_outputs`).
        Origem sem schema conhecido (simulate() que falhou, `outputs`
        vazio, `schema_source: unknown`) não gera diagnóstico — não dá para
        afirmar typo sem as saídas declaradas. Saídas declaradas na definição
        (`schema_source: declared`) contam como conhecidas: um `from_key` fora
        de `output_vars` é erro.
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
