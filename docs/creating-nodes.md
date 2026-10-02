# How to Create a New Node

This guide explains, step by step, how to add a new node to the Atlans workflow engine.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Step 1 — Choose the category](#step-1--choose-the-category)
- [Step 2 — Create the node file](#step-2--create-the-node-file)
- [Step 3 — Implement `description()`](#step-3--implement-description)
- [Step 4 — Implement `execute()` (or `execute_sync()`)](#step-4--implement-execute-or-execute_sync)
- [Step 5 — Automatic registration](#step-5--automatic-registration)
- [Step 6 — Check in the editor](#step-6--check-in-the-editor)
- [Reference: BaseNode](#reference-basenode)
- [Reference: Property types](#reference-property-types)
- [Annotated examples](#annotated-examples)
- [Final checklist](#final-checklist)

---

## Core Concepts

A **node** is an atomic unit of processing inside a DAG workflow. Each node:

- Receives an `inputs` dictionary with the outputs of the previous nodes
- Has parameters the user can configure (accessed via `self.get_param()` / `self.parameters`)
- Returns an `outputs` dictionary that feeds the following nodes

```
      [Node A]
         │ output "output" ──(edge: from_key/to_key)──▶
         ▼
      [Node B]  ← inputs = {"output": GeoDataFrame}
         │ output "output" ──▶
         ▼
      [Node C]
```

> **How data crosses the edge.** The keys that arrive in `inputs` are defined **on the
> edge itself** (`from_key`/`to_key`, chosen on the canvas), not by node parameters. A
> new node should **read/write fixed output keys** (by convention, `output`) and declare them
> in `outputs`; whoever wires the nodes picks the port in the editor. The old pattern of
> `inputKey`/`outputKey` parameters has been **retired** — no node in the repository uses it and the runtime no
> longer interprets it (see `docs/specs/edge-data-contract.md`). Do not create
> `inputKey`/`outputKey` parameters: they would simply be discarded.

---

## Step 1 — Choose the category

Put the node file in the semantically correct category:

| Folder | When to use | Existing nodes (reference) |
|-------|-------------|----------------------------|
| `flow/nodes/action/` | Attribute transformations, HTTP requests, geocoding, scripts | `SetFields`, `Sort`, `RemoveDuplicates`, `HttpRequest`, `GeocodeNode`, `PythonScript` |
| `flow/nodes/spatial/` | Geometric operations (buffer, clip, dissolve, spatial join…) | `Buffer`, `Clip`, `Dissolve`, `SpatialJoin`, `CentroidNode`, `UnionNode`, `Simplify`, … |
| `flow/nodes/datasource/` | Data reading (database, files, WFS, APIs) | `DatabaseSpatialQuery`, `ReadGeoJSON`, `ReadShapefile`, `WFS`, `DataInput`, … |
| `flow/nodes/outputs/` | Writing results (files, database, S3, webhook, email) | `SaveGeoJSON`, `SaveToPostGIS`, `SaveToS3`, `SendEmail`, `SendWebhook` |
| `flow/nodes/control/` | Flow control (conditional, loop, merge, sub-workflow, routing) | `Conditional`, `Switch`, `Merge`, `Loop`, `JinjaBranch`, `SubWorkflow` |
| `flow/nodes/trigger/` | Execution triggers (schedule, webhook, file) | `ScheduleTrigger`, `WebhookTrigger`, `FileTrigger`, `GeofenceTrigger` |

> Note: the category `type` (used in `description()`) is **singular** — for the
> `outputs/` folder the `type` is `"output"`. Note also that the registry `name` of some nodes carries
> the `Node` suffix (`GeocodeNode`, `CentroidNode`, `UnionNode`, `SimplifyNode`), while others
> do not (`Buffer`, `Clip`). The `name` is free — it only has to be unique (see Step 3).

---

## Step 2 — Create the node file

**There is no `_template.py`.** Create the file from scratch, or copy an existing node close to
what you need and adapt it:

```bash
# From scratch:
touch flow/nodes/spatial/meu_no.py

# Or by copying a simple node as a starting point:
cp flow/nodes/spatial/simplify.py flow/nodes/spatial/meu_no.py
```

The file name must be `snake_case`. The class name can be `PascalCase`.

Minimal skeleton:

```python
import asyncio
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class MeuNo(BaseNode):
    @classmethod
    def description(cls) -> Dict[str, Any]:
        ...

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...
```

---

## Step 3 — Implement `description()`

The `description()` method is a `classmethod` that returns the node's metadata. This metadata
is used by:
- **Registry** — to identify and instantiate the node by its `name` field
- **Visual editor** — to generate the configuration form automatically
- **`/nodes/` API** — to list the available nodes
- **Schema simulation (`validate_service`, the MCP `validate_workflow` tool)** — via `outputs`/`dynamic_output`

```python
@classmethod
def description(cls) -> Dict[str, Any]:
    return {
        # Unique identifier in the registry — no spaces, no accents.
        # It is the registry KEY (flow/registry.py) and is saved in the workflow
        # definition in the node's "name" field. The factory instantiates the node by looking up
        # node_def["name"] in NODE_REGISTRY (flow/factory.py). DO NOT CHANGE it once the
        # node is in use in production — create a new node if you need to change it.
        "name": "MeuNo",

        # Name shown to the user in the visual editor
        "alias": "Meu Nó",

        # Full description — shows up as tooltip/help in the editor
        "description": "Realiza X operação sobre Y dados, retornando Z resultado.",

        # The node's CATEGORY (sets icon/color in the editor and is used in the graph filter).
        # It is NOT the identifier — the identifier is "name" above.
        # Values: "trigger" | "action" | "spatial" | "datasource" | "output" | "control"
        "type": "spatial",

        # Parameters the user can configure
        "properties": [
            {
                "name": "distance",         # parameter key in self.parameters
                "label": "Distância",       # label shown in the editor (optional, recommended)
                "type": "number",           # see the type table below
                "default": 100,             # default applied by self.validate()
                "description": "Distância do buffer em unidades do CRS.",
            },
        ],

        # Output fields — the SINGLE SOURCE of the output contract: the keys of the
        # dict that execute() returns, with their type. Used by the editor (schema
        # panel, port selector, autocomplete), by simulation/preview and
        # by "schema drift" detection in the executor.
        #   - `port: True` marks a field with its own connection point on the
        #     canvas (2+ of them ⇒ named handles; none ⇒ anonymous output).
        #   - BRANCH nodes (Conditional and the like) declare `"branches": True`:
        #     the output points are true/false and route the execution.
        "outputs": [
            {"name": "output", "type": "geodataframe",
             "description": "GeoDataFrame com o resultado."},
        ],
    }
```

### Special property fields

Besides `name`/`type`/`default`/`description`, a property can have:

```python
# List of options (renders a select). Use type "select"; each option is an
# {value, label} object. self.validate() validates the value against the "value"s.
{
    "name": "crs",
    "label": "CRS de saída",
    "type": "select",
    "default": "EPSG:4326",
    "description": "Sistema de referência de coordenadas.",
    "options": [
        {"value": "EPSG:4326",  "label": "WGS 84 (4326)"},
        {"value": "EPSG:31983", "label": "SIRGAS 2000 / UTM 23S (31983)"},
    ],
},

# Conditional display: only shows the field when another parameter has a certain value.
{
    "name": "fieldName",
    "label": "Campo",
    "type": "string",
    "default": "",
    "description": "Nome do campo a avaliar.",
    "visibleWhen": {"field": "metric", "in": ["field"]},
},
```

### Nodes that require a credential

Two patterns are in use, both valid:

```python
# (a) Database nodes (DatabaseSpatialQuery, SaveToPostGIS): they signal it with
#     requires_credential + a credential_id parameter (string). The SERVER
#     resolves the credential and injects the decrypted connectionString (see Step 4).
"requires_credential": True,
# ... in properties:
{"name": "credential_id",     "type": "string", "default": "", "description": "UUID da credencial."},
{"name": "connectionString",  "type": "string", "default": "", "description": "DSN (injetada automaticamente)."},

# (b) Credential selector in the editor: a property of type "credential" with
#     credential_types (PLURAL, a list) filtering the compatible types
#     (e.g. HttpRequest, SaveToS3, SaveGeoJSON with optional webhook).
{
    "name": "credential_id",
    "type": "credential",
    "credential_types": ["http_bearer", "http_basic"],
    "default": "",
    "description": "Credencial de autenticação.",
},
```

### Dynamic output (`dynamic_output` + `simulate`)

If the node produces outputs that depend on the parameters/input (e.g. `Switch` with N buckets,
`DatabaseSpatialQuery` whose schema comes from the SQL), set `"dynamic_output": True` and,
optionally, implement a `classmethod async simulate(cls, parameters, simulated_inputs)`
that returns the schema list. That is what validation (`validate_service`) uses to predict the schema
without executing (see `flow/nodes/datasource/database_spatial_query.py::simulate`); the response marks
those nodes with `schema_source: "simulated"`. Without `simulate`, the `dynamic_output` node **does not vanish**
from the response: validate derives the outputs from the payload itself — `output_vars` (PythonScript),
`rules[].output` + `fallback_output` (Switch), `ports` (`outputs_from_ports`,
`SubWorkflowInput`) — or, failing those, from the catalog's `outputs`, and marks
`schema_source: "declared"`. It is an
approximation from the declaration: implementing `simulate()` is still what gives the real schema.

---

## Step 4 — Implement `execute()` (or `execute_sync()`)

The node's logic lives in `execute()` (asynchronous) OR in `execute_sync()` (synchronous, for
CPU-bound nodes). Pick one:

- **`execute_sync(self, inputs)`** — for **CPU-bound** nodes (pandas/GeoPandas/Shapely, Jinja
  row by row). The base class dispatches the synchronous body to a dedicated thread pool
  automatically — you do **not** need `asyncio.to_thread`. It is the form `BaseNode`
  recommends for heavy CPU work (e.g. `flow/nodes/action/field_transformer.py`).
- **`async def execute(self, inputs)`** — when the node **truly awaits asynchronous I/O**
  (`asyncpg`, `httpx` with `await`). In that case, send the **blocking** work (parsing,
  GeoPandas computations) into `asyncio.to_thread()` so it does not block the event loop. It is the
  pattern of most existing nodes (e.g. `buffer.py`, `simplify.py`).

Mandatory rules for either one:

1. **Call `self.validate()` on the first line** — it applies the declared defaults and coerces the
   types (`number`→float, `integer`→int, `select` validated against the options). Practically
   every node does this.
2. Access parameters via `self.get_param()` / `self.parameters` (never `self.properties` —
   that attribute raises an error on purpose).
3. Get the input with `self.get_first_gdf(inputs)` (first GeoDataFrame) or
   `self.get_input_gdf(inputs, key)` (specific key).
4. Return a `dict` of outputs with fixed keys (e.g. `{"output": gdf}`).
5. **Idempotency:** the executor may call `execute()` more than once on a retry
   (see `retry_count`/`retry_delay_s` in the reference). Avoid non-repeatable side effects
   or make them idempotent.

Example (I/O or mixed node — `async execute` + `to_thread` for the heavy part):

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Defaults + type validation
    self.validate()

    # 2. Parameters (already coerced by self.validate())
    distance = self.get_param_float("distance", 100.0)

    # 3. Input — first available GeoDataFrame
    gdf = self.get_first_gdf(inputs)

    # 4. Blocking work in a separate thread (does not block the event loop)
    def _apply_buffer(df):
        return df.copy().assign(geometry=df.geometry.buffer(distance))

    result = await asyncio.to_thread(_apply_buffer, gdf)

    # 5. Summary log
    logger.info("%s: buffer de %.1f aplicado em %d feições.",
                self.__class__.__name__, distance, len(result))

    # 6. Return with a fixed output key
    return {"output": result}
```

The same logic as a **CPU-bound** node (no `async`, no `to_thread` — the base takes care of the thread):

```python
def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    self.validate()
    distance = self.get_param_float("distance", 100.0)
    gdf = self.get_first_gdf(inputs)
    result = gdf.copy().assign(geometry=gdf.geometry.buffer(distance))
    return {"output": result}
```

### Handling credentials

The **server** (not the executor) resolves the credential and injects the decrypted value into the
node's parameters before execution (see `app/services/credential_resolver.py`). For the database
types, the value arrives in the **`connectionString`** parameter (camelCase); for HTTP, it arrives in
`http_auth`.

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    self.validate()
    # The decrypted connectionString was injected by the server from credential_id.
    conn_str = self.get_param("connectionString")   # NOT "connection_string"
    if not conn_str:
        raise ValueError("Credencial não resolvida: 'connectionString' vazia.")

    def _query(cs):
        import geopandas as gpd
        return gpd.read_postgis("SELECT * FROM tabela", cs, geom_col="geom")

    result = await asyncio.to_thread(_query, conn_str)
    return {"output": result}
```

> Database nodes usually use the helper `flow/utils/credencial.py::obter_conexao(self.parameters)`,
> which reads and validates `parameters["connectionString"]`.

### Publishing output to the user's log terminal

The attributes injected by the executor let you publish events. The publisher is an instance
of `WorkflowEventPublisher` (abstract class, **synchronous** method `publish_event(...)`) — there
is no `RedisPublisher` and no `publish()` method. To send lines to the user's terminal
(the equivalent of `print()`), use the module helper `publish_stdout`, exactly as
`PythonScript` does (`flow/nodes/action/python_script.py`):

```python
from flow.utils.publisher.events import publish_stdout

# self._publisher may be None outside the execution context — the helper handles that.
publish_stdout(self._publisher, self._task_id, self.node_id,
               [f"Processando {len(gdf)} feições..."])
```

For a plain log message (without the user's terminal), prefer `self.log("...")` or the
module `logger`.

---

## Step 5 — Automatic registration

`registry.py` discovers your node automatically when it imports the module. All you need is to add the
`@register_node` decorator to the class:

```python
from flow.registry import register_node
from flow.nodes.base import BaseNode

@register_node   # ← This is all that registration needs
class MeuNo(BaseNode):
    ...
```

> `registry.py` uses `pkgutil.walk_packages` to import every module under `flow/nodes/`
> recursively. You do not need to edit any other file. The decorator checks that the
> class inherits from `BaseNode` and that the `name` from `description()` is unique (duplicate names
> raise an error at boot).

**Important:** the `"name"` value in `description()` is the permanent identifier. The factory
instantiates the node by looking up `node_def["name"]` in the registry (`flow/factory.py`). Once
production workflows use that name, **do not change it** — create a new node if you need to change the
behavior.

If renaming is unavoidable, it goes in the SAME commit: an entry in `NOMES_ANTIGOS`
(`flow/nodes/contrato.py`, old name → new), the mapping of the properties that changed in
`app/services/nos_renomeados.py` and, at deploy, `python -m app.cli migrar-nos --aplicar`. It was
for lack of this that the July 27 rename (`DriveTrigger` → `DataInput`, `ArtifactOutput` →
`DataOutput`) left saved workflows failing every day with "Node 'DriveTrigger' não encontrado".
With the entry in the map, the lint and the factory also start telling you where the node went.

---

## Step 6 — Check in the editor

1. Restart the worker and the API:
   ```bash
   docker compose restart api worker
   ```

2. Open `http://localhost:8000/docs` → `GET /nodes/` → check that your node shows up in the list

3. Open `http://localhost:3000` → open a workflow → in the node palette (drawer) → your node
   should appear in the correct category

4. Drag the node onto the canvas, configure the parameters and run a test workflow

---

## Reference: BaseNode

Methods and attributes available to every node (`flow/nodes/base.py`):

### Lifecycle

| Method | Description |
|--------|-----------|
| `description()` (classmethod, abstract) | Node metadata (required) |
| `async execute(self, inputs)` | Main logic (asynchronous). Default: dispatches `execute_sync` to the thread pool |
| `execute_sync(self, inputs)` | Synchronous body for CPU-bound nodes (implement this OR override `execute`) |
| `async setup(self)` | Optional hook called BEFORE `execute()` |
| `async teardown(self)` | Optional hook called AFTER `execute()` (including on error) |
| `validate(self)` | Applies defaults from `description()['properties']` and coerces types. Call it at the start of `execute()` |

### Parameter access

| Method | Description |
|--------|-----------|
| `self.get_param(name, default)` | Returns the parameter as is |
| `self.get_param_float(name, default)` | Converts to `float`, raises `ValueError` if invalid |
| `self.get_param_int(name, default)` | Converts to `int` (via `int(float(...))`) |
| `self.get_param_bool(name, default)` | Converts to `bool` (accepts `True`/`"true"`/`"1"`/`"yes"`/`"sim"`) |
| `self.get_retry_params()` | Returns `(retry_count, retry_delay_s)` (defaults `0`, `5.0`) |

### Input access

| Method | Description |
|--------|-----------|
| `self.get_input_gdf(inputs, key)` | GeoDataFrame by key. Raises `ValueError` if missing/empty, `TypeError` if it is not a GeoDataFrame |
| `self.get_first_gdf(inputs)` | First non-empty GeoDataFrame. Warns if there is more than one distinct candidate; raises `ValueError` if there is none |

### Attributes injected by the executor

| Attribute | Type | Description |
|----------|------|-----------|
| `self.node_id` | `str` | Node identifier within the workflow |
| `self.parameters` | `dict` | Parameters configured by the user |
| `self.context` | `dict` | Context shared with the executor (e.g. `_subflow_ancestors`) |
| `self._publisher` | `WorkflowEventPublisher \| None` | Event publisher (may be `None` outside the execution context) |
| `self._task_id` | `str \| None` | ID of the current run/task |
| `self._workspace_id` | `str \| None` | Workspace ID (multi-tenant isolation) |
| `self._workflow_hash` | `str \| None` | Workflow hash (cross-run state) |
| `self._debug_mode` | `bool` | `True` if the workflow is in debug mode |

Context helpers: `self.require_execution_context()` (ensures `_workspace_id`/`_task_id`) and
`self.derive_label(...)` (resolves the `label` of output nodes).

### Retries

The executor reads `retry_count` and `retry_delay_s` from the node's parameters (defaults `0` and `5.0`s) and
re-runs `execute()` when an exception is raised. These are **platform** parameters — they do not need
to be declared in `properties`, and they are not reported as "discarded". Since `execute()` may
run more than once, keep it **idempotent**.

### Logging

```python
# Option 1: module logger (recommended)
from flow.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Mensagem")

# Option 2: instance helper (no import)
self.log("Mensagem")
```

---

## Reference: Property types

| `type` | Rendering in the editor | Note |
|--------|----------------------|------------|
| `"string"` | Text input | Default for most parameters |
| `"number"` | Numeric input | `self.validate()` already coerces to `float`; read it with `get_param_float()` |
| `"integer"` | Integer numeric input | `self.validate()` coerces to `int`; read it with `get_param_int()` |
| `"boolean"` | Checkbox | Use `get_param_bool()` for safe reading |
| `"select"` | Dropdown | Requires `options: [{"value":…, "label":…}]`; `self.validate()` validates the value |
| `"object"` | JSON editor | Accepts `dict` or `list` (serialized JSON is decoded) |
| `"code"` | Monaco editor (Python) | For nodes that take code as a parameter (e.g. `PythonScript`) |
| `"credential"` | Credential select | Requires `credential_types` (a list) to filter by compatible type |
| `"ports"` | Input port editor | Only with `"dynamic_inputs": True`; stores a list of names (identifiers). With 2+ ports the editor stores each edge's `to_key`; with 0/1 the edge is anonymous (e.g. `PythonScript`, `CartaImagem`). Read it with `_parse_ports()` |
| `"keyvalue"` | Key → value pairs | Flat two-column list (e.g. `HttpRequest` headers, `CartaImagem` per-port colors). Arrives as a `dict` (or as a JSON string in an old workflow): read it with a tolerant parser |

> In `outputs[].type`, the `type` describes the **type of the output data** (e.g.
> `"geodataframe"`, `"any"`, `"number"`, `"boolean"`), not a UI widget.

> **Jinja in string values:** `"string"`/`"object"` properties may contain Jinja2
> expressions (`{{ row.campo }}`, `{{ env.VARIAVEL }}`). The `SetFields` node
> (`flow/nodes/action/field_transformer.py`) uses this for per-row transformations, with a
> `jinja2.sandbox.SandboxedEnvironment` (a **sandboxed** environment, not a raw `jinja2.Environment`).

---

## Annotated examples

### Simple spatial operation node (CPU-bound via `async execute` + `to_thread`)

```python
# flow/nodes/spatial/simplify_geometry.py
import asyncio
import geopandas as gpd
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class SimplifyGeometry(BaseNode):
    """Remove vértices desnecessários preservando a topologia."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "SimplifyGeometry",
            "alias": "Simplificar Geometria",
            "description": "Simplifica geometrias reduzindo o número de vértices.",
            "type": "spatial",
            "properties": [
                {
                    "name": "tolerance",
                    "label": "Tolerância",
                    "type": "number",
                    "default": 1.0,
                    "description": "Tolerância na unidade do CRS. Valores maiores = mais simplificação.",
                },
                {
                    "name": "preserveTopology",
                    "label": "Preservar topologia",
                    "type": "boolean",
                    "default": True,
                    "description": "Se ativado, preserva a topologia durante a simplificação.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe",
                 "description": "GeoDataFrame com geometrias simplificadas."},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        tolerance = self.get_param_float("tolerance", 1.0)
        preserve_topology = self.get_param_bool("preserveTopology", True)

        # Input: first available GeoDataFrame (the port is chosen on the edge)
        gdf = self.get_first_gdf(inputs)

        def _simplify(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            result = df.copy()
            result[result.geometry.name] = df.geometry.simplify(
                tolerance, preserve_topology=preserve_topology
            )
            return result

        result = await asyncio.to_thread(_simplify, gdf)

        logger.info("%s: tolerância=%.2f aplicada em %d feições.",
                    self.__class__.__name__, tolerance, len(result))

        # FIXED output key (declared in outputs)
        return {"output": result}
```

### Node that consumes an external API (real asynchronous I/O)

```python
# flow/nodes/datasource/fetch_geojson_url.py
import asyncio
import io
import httpx
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class FetchGeoJsonUrl(BaseNode):
    """Baixa um GeoJSON de uma URL e o disponibiliza como GeoDataFrame."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "FetchGeoJsonUrl",
            "alias": "Buscar GeoJSON por URL",
            "description": "Faz download de um GeoJSON público e o converte em GeoDataFrame.",
            "type": "datasource",
            "properties": [
                {
                    "name": "url",
                    "label": "URL",
                    "type": "string",
                    "default": "",
                    "description": "URL pública do arquivo GeoJSON.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe",
                 "description": "GeoDataFrame carregado da URL."},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import geopandas as gpd

        self.validate()
        url = self.get_param("url", "")
        if not url:
            raise ValueError("O parâmetro 'url' é obrigatório.")

        # Asynchronous download — httpx is already async, no asyncio.to_thread
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Blocking parsing — runs in a thread
        def _parse(content: bytes):
            return gpd.read_file(io.BytesIO(content))

        gdf = await asyncio.to_thread(_parse, response.content)

        logger.info("%s: %d feições carregadas de %s.",
                    self.__class__.__name__, len(gdf), url)
        return {"output": gdf}
```

---

## Configuration helpers — the criterion

The editor's form is GENERATED from the schema (`node-config-form.tsx`): fields,
labels, help tooltip (`description`), required asterisk
(`required`), example in the input (`placeholder`), conditional visibility
(`visibleWhen`), column suggestions (`suggest_columns`) and options (`options`).

**A node-specific component (helper) only exists when there is BEHAVIOR
that the schema does not express** — service probing (WFS GetCapabilities),
webhook testing, the asynchronous sub-workflow contract, the recurrence editor.
Never for layout: color, grouping, explanatory text and examples belong in the
schema, where the MCP and validation also see them. The FileTriggerHelper —
two decorated inputs — is the counterexample that died under this rule.

## Final checklist

Before submitting the PR with the new node, confirm:

- [ ] File in the correct category folder
- [ ] Class decorated with `@register_node`
- [ ] `description()` has a unique `name` (no spaces, unique across the whole project)
- [ ] `outputs` declared (typed output fields), correct category `type`
- [ ] `self.validate()` called at the start of `execute()`/`execute_sync()`
- [ ] Parameters accessed via `self.get_param()` (never `self.properties`)
- [ ] Inputs accessed via `self.get_first_gdf()` / `self.get_input_gdf()` (no `inputKey`/`outputKey` parameters)
- [ ] CPU-bound nodes use `execute_sync` OR `asyncio.to_thread` inside `async execute`
- [ ] Asynchronous I/O (`httpx`/`asyncpg`) with `await`, without `to_thread`
- [ ] `execute()` idempotent (may be re-run by a retry)
- [ ] FIXED output keys (e.g. `{"output": ...}`)
- [ ] Errors raised with `raise ValueError(mensagem clara)`
- [ ] Logger set up with `logger = get_logger(__name__)`
- [ ] Comments and strings in Brazilian Portuguese
- [ ] Tested locally: the node shows up in `GET /nodes/` and in the visual editor
