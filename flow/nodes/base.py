# flow/nodes/base.py
# Defines the abstract class that all nodes must extend
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNode(ABC):
    @classmethod
    @abstractmethod
    def description(cls) -> Dict[str, Any]:
        """
        Metadata for discovery and interface generation. The complete contract
        (closed vocabularies and accepted keys) lives in flow/nodes/contrato.py
        and is VALIDATED at import by @register_node — a typo here dies in CI.

        {
            'name': 'NomeUnico',         # Registry key (no spaces)
            'alias': 'Nome Legível',     # Name shown in the editor
            'description': '...',        # Node description
            'type': 'action',            # CATEGORY: trigger|action|spatial|datasource|output|control
            'properties': [              # Configurable parameters (form widgets)
                {
                    'name': 'param1',       # Parameter key
                    'type': 'string',       # TIPOS_DE_PROPRIEDADE (contrato.py): string|number|
                                            #   integer|boolean|object|select|chips|credential|
                                            #   keyvalue|code|ports|drive|artifact|sql
                    'default': '',          # Default value when not provided
                    'description': '...',   # Description shown in the editor
                    # select requires 'options'; credential requires 'credential_types';
                    # optional: label, drive_extensions, visibleWhen, suggest_columns.
                },
            ],
            'outputs': [                 # OUTPUT fields — the single, typed source:
                {                        #   the keys of the dict that execute() returns
                    'name': 'output',
                    'type': 'geodataframe',  # TIPOS_DE_CAMPO: geodataframe|string|number|
                                             #   boolean|object|list|any
                    'description': '...',
                    # 'port': True on fields with their own connection point on the
                    # canvas (2+ of them = named handles; none = anonymous output).
                },
            ],
            # 'inputs': [{'name': 'layerA'}, ...]  # named input ports (binary nodes: get_pair)
            # 'branches': True       # BRANCH node: true/false handles route the execution
            # 'dynamic_inputs': True     # inputs come from the `ports` property
            # 'dynamic_output': True     # outputs come from the `output_vars` property
            # 'outputs_from_ports': True # outputs come from the `ports` property (SubWorkflowInput)
            # 'requires_credential': True / 'source_kind': 'wfs'
        }
        """
        raise NotImplementedError("Método description() precisa ser implementado.")

    def __init__(self, node_id: str, parameters: dict):
        """
        Constructor common to all nodes.
        :param node_id: unique identifier of the node
        :param parameters: dictionary of parameters configured by the user
        """
        self.node_id = node_id
        self.parameters = parameters or {}
        # Injected by the executor — allow publishing custom events to the terminal
        self._publisher = None
        self._task_id: str | None = None
        self._debug_mode: bool = False
        self._workspace_id: str | None = None  # Isolamento multi-tenant
        self._workflow_hash: str | None = None  # Identifica o workflow para state cross-run
        # Context shared with the executor (same dict). Set by the
        # WorkflowExecutor at instantiation time. Today it carries
        # _subflow_ancestors (used by SubWorkflowNode for loop detection).
        self.context: Dict[str, Any] = {}

    async def setup(self) -> None:
        """Optional hook called before execute(). Useful for preparing resources."""

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method that contains the node's logic.
        :param inputs: input values from previous nodes mapped by name
        :return: output values mapped by name

        IMPLEMENT `execute_sync` WHENEVER THE NODE IS CPU-BOUND (pandas,
        geopandas, shapely, Jinja row by row). Only override `execute` when
        the node really awaits asynchronous I/O (asyncpg, httpx) — and, even then,
        send the heavy post-processing to `asyncio.to_thread`.

        The reason is architectural: in the external executor the engine runs on the
        SAME event loop that serves the WebSocket. While an `execute` blocks, heartbeat,
        capacity, node_events, results and the user's `cancel` stop being
        scheduled — past 90s the server closes the session with 4408 and the whole
        run dies, along with those of the OTHER jobs on the same executor. That's why
        the default here is NOT "run on the loop": it's dispatching the synchronous
        body to the dedicated thread pool (executor/main.py installs it as the default).
        """
        return await asyncio.to_thread(self.execute_sync, inputs)

    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        SYNCHRONOUS body of the node, executed in a pool thread (see `execute`).

        It may block freely — that's exactly what it exists for. What it must not
        do is touch the event loop: event publishing (`self._publisher`) is already
        thread-safe via `call_soon_threadsafe`, and so is `self.log` (logging is
        thread-safe), but don't create tasks or use `asyncio.get_running_loop()`
        from here.
        """
        raise NotImplementedError(
            f"'{type(self).__name__}' precisa implementar 'execute_sync' (nó "
            "CPU-bound) ou sobrescrever 'execute' (nó de I/O assíncrono)."
        )

    async def teardown(self) -> None:
        """Optional hook called after execute() (including on error). Useful for cleaning up resources."""

    # ── Parameter validation ─────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Applies the defaults declared in description()['properties'] to the node's parameters.
        Call self.validate() at the start of execute() to ensure that all
        required parameters have values and that the defaults are filled in.
        Replaces the pattern: props = self.description()['properties']; self.parameters = validate_node_parameters(...)
        """
        from flow.utils.parameter_validation import validate_node_parameters
        desc = self.description()
        props = desc.get("properties", [])
        self.parameters = validate_node_parameters(
            self.parameters, props, node_name=desc.get("name", type(self).__name__),
        )

    # ── Parameter helpers ────────────────────────────────────────────────────

    def get_param(self, name: str, default: Any = None) -> Any:
        """
        Returns the configured parameter's value, falling back to the default.
        Replaces direct use of self.parameters.get() to avoid confusion
        with self.properties (which doesn't exist in this class).
        """
        return self.parameters.get(name, default)

    def get_param_float(self, name: str, default: float = 0.0) -> float:
        """Returns the parameter converted to float."""
        try:
            return float(self.parameters.get(name, default))
        except (TypeError, ValueError):
            raise ValueError(f"Parâmetro '{name}' deve ser numérico. Recebido: {self.parameters.get(name)!r}")

    def get_param_int(self, name: str, default: int = 0) -> int:
        """Returns the parameter converted to int."""
        try:
            return int(float(self.parameters.get(name, default)))
        except (TypeError, ValueError):
            raise ValueError(f"Parâmetro '{name}' deve ser inteiro. Recebido: {self.parameters.get(name)!r}")

    def get_retry_params(self) -> tuple[int, float]:
        """Returns (retry_count, retry_delay_s) configured on the node (default: 0 retries, 5s wait)."""
        return self.get_param_int("retry_count", 0), self.get_param_float("retry_delay_s", 5.0)

    def get_param_bool(self, name: str, default: bool = False) -> bool:
        """Returns the parameter converted to bool (accepts True/False/'true'/'false')."""
        value = self.parameters.get(name, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "sim")
        return bool(value)

    # ── Input helpers ────────────────────────────────────────────────────────

    def get_input_gdf(self, inputs: Dict[str, Any], key: str):
        """
        Looks up and validates a GeoDataFrame in the inputs.
        Raises ValueError with a clear message if not found, not a GDF, or empty.
        """
        import geopandas as gpd
        value = inputs.get(key)
        if value is None:
            raise ValueError(f"Input '{key}' não encontrado. Inputs disponíveis: {list(inputs.keys())}")
        if not isinstance(value, gpd.GeoDataFrame):
            raise TypeError(f"Input '{key}' não é um GeoDataFrame (recebido: {type(value).__name__}).")
        if value.empty:
            raise ValueError(f"GeoDataFrame '{key}' está vazio.")
        return value

    def get_first_gdf(self, inputs: Dict[str, Any]):
        """
        Returns the first GeoDataFrame found in the inputs.
        Useful when the node doesn't require a specific key.

        With more than one candidate the choice is AMBIGUOUS and depends on the order
        of the edges in the definition. The node warns in the panel instead of
        processing one and silently ignoring the other — the classic symptom is a
        spatial filter that "works" with half the data because two parents delivered
        layers and only the first was read.
        """
        import geopandas as gpd
        candidatos = [
            k for k, v in inputs.items()
            if isinstance(v, gpd.GeoDataFrame) and not v.empty
        ]
        # Two keys pointing to the SAME object are not ambiguity: it's what
        # fork nodes produce, exposing the data that passed through them in
        # `result` besides the key that came from the parent. Comparing by identity
        # avoids the alarming warning about a choice that doesn't exist — either
        # key returns exactly the same GeoDataFrame.
        distintos = {id(inputs[k]) for k in candidatos}
        if len(distintos) > 1:
            self.log(
                f"Mais de uma camada chegou a este nó ({candidatos}); usando '{candidatos[0]}' "
                f"e ignorando as demais. Use as portas nomeadas do nó de origem para escolher."
            )
        if candidatos:
            return inputs[candidatos[0]]

        # The message needs to say WHAT arrived. Nodes like SaveToPostGIS accept
        # only GeoDataFrame, while DataInput delivers GeoDataFrame, DataFrame,
        # dict, list or bytes depending on the file extension — without the diagnostic
        # below, connecting a CSV to PostGIS failed with a text that didn't help
        # find out either the key or the type received.
        recebido = {k: type(v).__name__ for k, v in inputs.items()}
        vazios = [
            k for k, v in inputs.items()
            if isinstance(v, gpd.GeoDataFrame) and v.empty
        ]
        detalhe = f" GeoDataFrame(s) vazio(s): {vazios}." if vazios else ""
        raise ValueError(
            f"Nenhum GeoDataFrame encontrado nos inputs. Recebido: {recebido}.{detalhe}"
        )

    def get_pair(
        self,
        inputs: Dict[str, Any],
        chave_a: str = "layerA",
        chave_b: str = "layerB",
        *,
        operacao: str = "operação",
        crs: str | None = "exigir_igual",
        tipos_suportados: bool = False,
        nomes: tuple[str, str] | None = None,
    ):
        """
        Fetches the two layers of a binary node (A, B) and applies the node's CRS
        policy. Returns `(a, b)`. Previously each node rewrote the lookup and the check.

        crs:
          'exigir_igual' → refuses layers with different CRSs; whoever builds the workflow
                           standardizes beforehand with a reprojection node.
          'alinhar'      → requires a CRS on both layers. Reprojecting B to A's CRS
                           is the node's job, with `align_crs`, INSIDE the worker
                           thread: to_crs is O(n) and doesn't run on the event loop.
          None           → no check: the node handles the CRS on its own
                           (e.g.: `para_crs_metrico`).
        tipos_suportados: refuses GeometryCollection/null geometry on both.
        nomes: how each layer appears in missing-CRS messages
               (default: "camada '<chave>'").
        operacao: how the operation appears in refusal messages.
        """
        from flow.utils.geo_helpers import (
            reject_unsupported_geom_types,
            require_crs,
            require_same_crs,
        )
        a = self.get_input_gdf(inputs, chave_a)
        b = self.get_input_gdf(inputs, chave_b)
        if crs == "exigir_igual":
            require_same_crs(a, b, operation=operacao)
        elif crs == "alinhar":
            nome_a, nome_b = nomes or (f"camada '{chave_a}'", f"camada '{chave_b}'")
            require_crs(a, name=nome_a)
            require_crs(b, name=nome_b)
        elif crs is not None:
            # A typo here would silently turn off the check.
            raise ValueError(f"Política de CRS desconhecida: {crs!r}.")
        if tipos_suportados:
            reject_unsupported_geom_types(a, b, operation=operacao)
        return a, b

    # ── Execution context helpers ───────────────────────────────────────────

    def require_execution_context(self) -> tuple[str, str]:
        """
        Ensures the executor injected `_workspace_id` and `_task_id`.
        Returns `(workspace_id, task_id)`. Useful for output nodes that
        need to isolate artifacts by workspace/run.
        """
        workspace_id = getattr(self, "_workspace_id", None)
        task_id = getattr(self, "_task_id", None)
        if not workspace_id:
            raise RuntimeError("workspace_id nao injetado pelo executor.")
        if not task_id:
            raise RuntimeError("task_id nao injetado pelo executor.")
        return workspace_id, task_id

    def derive_label(self, label_param: str, output_path_param: str = "") -> str:
        """
        Resolves the node's `label`. Priority:
          1. label_param (if filled in).
          2. basename of output_path without extension.
          3. ValueError if both are empty.
        Reduces the boilerplate repeated in output nodes (save_geojson, save_to_s3, etc).
        """
        import os
        label = (label_param or "").strip()
        if label:
            return label
        path = (output_path_param or "").strip()
        if path:
            return os.path.splitext(os.path.basename(path))[0]
        raise ValueError(
            "Parametro 'label' e obrigatorio quando 'output_path' nao esta preenchido."
        )

    # ── Log helper ───────────────────────────────────────────────────────────

    def log(self, message: str) -> None:
        """
        Logs an informational message in the node's context.
        Convenient for nodes that don't want to import get_logger directly.
        """
        from flow.utils.logger import get_logger
        get_logger(f"node.{self.node_id}").info(message)

    # ── Protection against the self.properties typo ─────────────────────────

    @property
    def properties(self):
        raise AttributeError(
            f"'{type(self).__name__}' não possui 'properties'. "
            "Use 'self.parameters' ou 'self.get_param()' para acessar parâmetros configurados."
        )
