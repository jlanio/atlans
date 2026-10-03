# Data source catalog (WFS)

The Home assistant and the editor assistant spent most of the time of a
response **hunting for external data**: guessing the `url` and `typeName` of a
WFS, finding out from the error that the layer did not exist, waiting 3 × 60 s of
timeout on a made-up URL. None of the tools listed layers, probed an
address or searched by theme; `validate_workflow` does not touch the network, so a
wrong URL passed with `ok: true` and only blew up in `run_workflow`; and the WFS node
redid the GetCapabilities on every run and every retry.

This document describes the **internal source catalog** that solves this in
phase 1: the `fontes_de_dados` table, the versioned seed in `catalogo/`, the
four MCP tools, the "catalog first" rule in the playbooks, the validation
warning, learning from runs, per-endpoint verification and the executor's
cache. **Nothing changes in the interface** in this phase — what changes is the
assistant's behavior: before any hunting, it queries the catalog.

## What a source is

A row of `fontes_de_dados` is **one layer of one service**: today, always a
WFS (`tipo="wfs"`, node `WFS`). The fields that matter:

| Field | Meaning |
|---|---|
| `workspace_id` | `NULL` = a **platform** source (visible to everyone); filled in = a workspace source. The search combines both |
| `url`, `type_name` | The already-normalized endpoint (no query/fragment) and the layer (`ns:camada`) |
| `chave` | `sha256(workspace\|tipo\|url\|type_name)`, UNIQUE — it is what makes the upsert idempotent |
| `propriedades` | What gets pasted into the node: `url`, `typeName`, `sortBy` when there is an id column, and `version` (stored; see phase 2) |
| `instituicao`, `grupo`, `titulo`, `descricao`, `temas`, `dicas` | The metadata from the Vault (or from the GetCapabilities, or from whoever registered it) |
| `esquema` | `crs`, `bbox`, `geometry_type`, `geometry_column`, `columns[{name,type,xsd,nullable}]`, `feature_count`, `columns_source` |
| `busca` | Normalized text (no accents, lowercase) with institution, group, title, layer, host, description, themes and columns — it is on this that the search runs `LIKE` |
| `prioridade` | 1 preferred · 2 normal · 3 secondary (from the Vault: `#preferida`, `#secundaria`, frontmatter `prioridade`) |
| `origem` | `vault` (the seed), `aprendida` (learned from a run), `manual` (`register_source`). An origin is never downgraded: `aprendida` does not overwrite `vault`/`manual` |
| `estado` | `ok`, `falhando`, `nao_verificada` — the result of the last verification, with `verificada_em` and `ultimo_erro` |
| `usos`, `usada_em` | How many successful runs used the source |
| `vault_hash` | Hash of the parsed record; reimporting skips what has not changed |

The table is born in the zero baseline: the CREATE lives in `scripts/init_schema.sql` (the
body of the single alembic revision — F3 of the simplification) next to the model
`app/models/fonte_de_dados.py`, and `tests/unit/test_init_schema_bootstrap.py`
ties script and models to each other, column by column. `chave` is a simple UNIQUE
(and not a composite UNIQUE with a null `workspace_id`) so as to be portable between
Postgres and the tests' SQLite. `JSON`, not JSONB, for the same reason.

## Where it comes from: the seed in `catalogo/`

`catalogo/geoservicos/` is the seed that ships with the repository, maintained as
a vault of Markdown notes: one folder per institution, with the institution's note
(`Endpoint WFS`, purpose, WFS version), `Camadas.md` and `Atributos.md`. The
names, titles and schemas of the layers are the ones each service publishes (see the
origin note in [`catalogo/README.md`](../catalogo/README.md)). The
format, the optional extensions (frontmatter, inline tags, `_sinonimos.md`) and the
step-by-step for updating are in [`catalogo/README.md`](../catalogo/README.md).

In the current seed: 114 folders; **76 institutions with WFS → 25,492 layers, all
with attributes** (IBGE alone has 9,759, in WFS 1.0.0). The other folders are
ArcGIS REST or "(Metadados em validação)" placeholders and are left out with the
reason `sem_endpoint_wfs` — ready for a future phase.

The parser is `app/services/fontes_vault.py` (pure, no database): `read_folder()`
returns one `RegistroDoVault` per layer or one `Skipped(pasta, motivo)` per
folder that does not get in. The fixtures in `tests/fixtures/vault/` are real excerpts.

### Import at startup

`app/core/fontes_catalogo.py` runs as a background task of the API's lifespan
(`app/main.py`):

1. `importar_catalogo_no_arranque()` reads `FONTES_CATALOGO_DIR` (outside `.env`,
   `catalogo/geoservicos`; empty or nonexistent = no import). Every worker
   loads the synonyms from `_sinonimos.md` (they live in the process's memory).
   The API starts before `alembic upgrade head`: the import **waits for the table
   to exist** (up to 10 min) and only then does the worker that grabs the Redis lock
   `fontes_catalogo:lock` (TTL 600 s) import; if the import fails, it
   releases the lock, so the next startup does not wait for the TTL.
2. `fontes_service.importar_pasta()` compares the `{chave: vault_hash}` of the
   `origem='vault'` rows with the folder: it inserts the new ones in batches of 500, updates the ones
   with a different hash, skips the identical ones and sets `deleted_at` on the ones that vanished from the folder
   (soft delete — the row and the history remain). **Starting again with the same folder
   is one query and zero writes.**
3. Next, an initial verification **of only what is pending** (never
   verified or expired) — see "Per-endpoint verification".

`Dockerfile.api` copies `catalogo/` into the image; without it the import does not
run in production. The folder is excluded from `detect-secrets` (the baseline excludes
`^catalogo/`) and from the pre-commit size limit.

### An oversized record must not take the batch down with it

In a real installation the import once died at record 6,779: 48 of the 25,492
records had a `titulo` over 255 characters (IBGE indicators reach 276) and the
column was `VARCHAR(255)`. Since the commit is **per batch of 500**, the
`StringDataRightTruncationError` aborted everything from there on — 6,500 records
stayed in the database, **19 thousand were lost** and the only signal was an ERROR in the log. The assistant was left
without three quarters of the layers.

Three changes, and the third is the one that prevents a repeat:

1. **`titulo` became `TEXT`** (today directly in `scripts/init_schema.sql`; the historical migration `a3c81d7e2f46` made the switch). A title is written by people; any
   fixed limit will overflow again in the next catalog, and `descricao`/`dicas` were already `TEXT`.
2. **Edge guard by field type.** The DISPLAY ones (`instituicao`, `grupo`) are
   truncated at the column limit — a label without its tail is still useful. The FUNCTIONAL ones
   (`type_name`, `url`) **cannot** be truncated: `type_name` goes literally into the
   WFS query and the `chave` derives from it, so a truncation would create a source that points to
   a nonexistent layer. These cause the record to be **skipped**, with the reason in the summary.
   The limit comes from the COLUMN (`fontes_service._column_limit`), not from a copied constant.
3. **`tests/unit/test_catalogo_cabe_nas_colunas.py`**, and this is the test that was missing: the
   SQLite of the other tests **ignores the `VARCHAR` size**, so the overflow was
   invisible to the whole suite — it passed in CI and failed on PostgreSQL. The new test reads
   the repository's REAL catalog and compares each field with the column limit, with no database
   at all. It fails on the day someone adds a record that production would reject.

## The "catalog first" rule

It lives in five places, so that no surface forgets it:

- **Authoring guide**, topic `sources` (`app/mcp/guia/sources.md`,
  `get_authoring_guide(topic="sources")`, resource
  `atlans://guide/authoring/sources`): the mandatory order — `search_sources`
  with the theme in two or three spellings → `describe_source` and paste
  `node_snippet.properties` → only when there is no result, ask the user for the URL or
  `probe_source` → `register_source` so as not to probe twice.
- **MCP server instructions** (`app/mcp/instrucoes.py`): "fonte externa
  (WFS) nunca é inventada nem sondada de primeira" (an external source, WFS, is
  never invented nor probed right away).
- **Playbooks** of the Home (`assistente_superficie.py`), of the editor assistant
  (`assistente_service.py`) and of the `criar_fluxo` prompt (`app/mcp/prompts.py`):
  step 2, before `search_nodes`/`describe_node`.
- **`describe_node("WFS")`**: the node declares `source_kind: "wfs"` in its description
  (`flow/nodes/datasource/wfs.py`, field `source_kind` in `NodeDefinition`) and the
  node catalog adds the hint "não invente `url`/`typeName`: consulte
  `search_sources`" (do not invent the url/typeName: query search_sources). No
  `if name == "WFS"` — any node that declares `source_kind` gets the hint. The field is not a node property, so the
  editor's form does not change.
- **Recipe 5** of the guide (`recipes.md`): a cataloged WFS
  (`Funai:tis_poligonais`) → `AttributeFilter` → `PublishMap`, with `sortBy`.

## The four MCP tools

`app/mcp/tools/fontes.py`; guards in `app/mcp/guardas.py`.

| Tool | Scope | Role | Quota | What it does |
|---|---|---|---|---|
| `search_sources(query, workspace_id?, kind?, institution?, limit=20)` | `workflows:read` | viewer | general | Search WITHOUT network. Lightweight items (`id, kind, node, scope, state, verified_at, uses, priority, type_name, host, institution, group`) with title and themes in `untrusted_data`; `total`; `hint` when there is no result |
| `describe_source(source_id)` | `workflows:read` | viewer | general | The record card: `node_snippet` (`{name: "WFS", type: "datasource", properties: {url, typeName, sortBy?, maxFeatures}}` — only properties the node declares today), summarized schema (up to 50 columns), `state/origin/verified_at/uses/institution`; title, description, hints and themes in `untrusted_data` |
| `probe_source(url, type_name?, version="2.0.0")` | `workflows:write` | editor | `probe` (10/min) | Probes a WFS: without `type_name`, lists the layers (`layers_listed`, up to 50); with `type_name`, the DescribeFeatureType schema plus CRS/bbox (`layer_described`). Does not create a source, but **updates** one already cataloged in scope. Returns `catalog_hint` when the same host is already cataloged |
| `register_source(url, type_name, workspace_id?, version, title?, description?, tags?, hints?)` | `workflows:write` | editor | `probe` | Validates the layer against the list, DescribeFeatureType, `manual/ok` upsert into the workspace catalog; returns the record card + `outcome: created\|updated` |

- `probe_source` and `register_source` are the only tools with
  `openWorldHint: true` (field `open_world` in `Guarda`): they make the server
  talk to a public URL. Private IPs, loopback and link-local remain
  blocked by the SSRF validation; the `probe` bucket limits them to 10/min per token.
- On both assistant surfaces they go through **without a click**
  (`ESCRITAS_SEM_CLIQUE` on the Home, `ESCREVEM_MAS_PASSAM` in the editor): probing and
  registering a source is the normal way of working, not a destructive action.
- Probe errors become `erro("source_unreachable", …, reason=<código>)` with
  `codigo ∈ {timeout, http_status, ssrf, tamanho, tls, sem_camadas,
  camada_inexistente, xml, rede}` — and `candidates` when the layer does not exist
  but there are similar ones.

### How the search works

`fontes_service.buscar()`: the query is normalized (no accents, lowercase),
the connectives are dropped ("de", "em", "do"…), each term is expanded by the synonyms
(the default map `DEFAULT_SYNONYMS` + the Vault's `_sinonimos.md`) and becomes
`(busca LIKE '%t%' OR busca LIKE '%sin1%' …)`; between terms, AND. The scope is
`workspace_id IN (…) OR workspace_id IS NULL`, without the deleted ones. The order:
`estado='ok'` first, then `prioridade`, `usos` descending and title.
`institution` matches exactly or by normalized text; `limit` goes up to 100.
That is 25 thousand rows × ~300 bytes: the scan costs milliseconds; a trigram index
remains a possible evolution if the catalog grows.

## Validation warns, without network

`validate_workflow` (and the REST validation route) now queries the catalog
for nodes with `source_kind == "wfs"` when there is a `workspace_id`
(`fontes_service.conferir_fontes_da_definicao`):

- `unknown_source` — the `url`+`typeName` are not in the workspace catalog nor
  in the platform's; the message says to use `search_sources`, or
  `probe_source`/`register_source` before running.
- `failing_source` — the source exists, but failed in the last verification (with
  `verificada_em` and the first 160 characters of `ultimo_erro`).

They are **warnings** (`ok` still means "no errors") and the validation **fails open**: an
unavailable database does not bring down the report. The editor's validation panel shows the
warning as it shows any other — no component changes.

## The catalog learns from runs

The `fontes` phase of the result consumer (`app/core/run_result_consumer.py`,
between `pins` and `notificacao`, isolated by `_run_phase`): for a
`success` run with some `WFS` node, `fontes_service.aprender_de_execucao()` does the
`aprendida/ok` upsert in the run's workspace, with `esquema = {crs, bbox,
feature_count}` from the spatial metrics and `columns` from `output_columns`
(`columns_source: "run"`). `usos` only counts on the first close
(`first_close`) — a redelivery from the queue neither duplicates nor inflates it. A schema is only
replaced by a more complete one (`describe_feature_type` > `vault` > `run`), and the
merge preserves what only the other one had. `FONTES_APRENDER_DAS_EXECUCOES=false`
turns it off.

## Per-endpoint verification

25 thousand layers are not 25 thousand probes: **one GetCapabilities per distinct
URL** marks all the layers of that URL (`fontes_service.verify_endpoint`).
Present in the capabilities → `ok`, with CRS and bbox in the schema (and title, abstract and
keywords when they were missing); absent → `falhando` ("camada não consta no
GetCapabilities", the layer is not listed in the GetCapabilities); endpoint down → all
`falhando` with the error. In the seed that is 76 requests per round.

`run_verificacao_loop()` repeats the round every `FONTES_VERIFICACAO_INTERVAL`
seconds (default 1 day; 0 turns it off — and also turns off the initial verification),
only in the worker that grabs the interval's Redis lock, with at most two endpoints
in parallel and a jittered pause between them. Each endpoint has its own database
session: a failure of one does not stop the round.

`probe_source` with a layer and `register_source` verify ONE source live
(`fontes_service.sondar_wfs`: GetCapabilities + DescribeFeatureType).

Probe limits: GetCapabilities 30 s and 32 MB (IBGE's lists 9,759
FeatureTypes); DescribeFeatureType 15 s and 2 MB. The XML is parsed with the standard
library after rejecting `<!DOCTYPE`/`<!ENTITY`. Every trip to the network goes through
`validate_url_ssrf` + `safe_httpx_request` (`flow/utils/geo_helpers.py`);
`owslib` is not used on the server. The editor's `GET /nodes/wfs/layers` route
became a thin wrapper of `fontes_service.listar_camadas_wfs`, with the same body
and the same statuses. With `credential_id` (and the `workflow_id` of the workflow being edited),
it lists with the node's credential — the layers a GeoServer hides from
anonymous users —, in the same scope as the validation (`validate_service`): the credentials of whoever
asks and, for operator or above in the workflow's workspace, the ones shared with it.
It is the workflow that determines the workspace, not the client (a nonexistent workflow is a 404). The
credential rules (authkey in the URL or in the header, Basic; a secret of at
least 6 characters, so it can be redacted in messages and logs) are the node's,
in `flow/utils/credencial_wfs.py` — and the Credenciais (Credentials) screen applies them on
saving and on **Testar** (Test).

## The executor does not repeat the GetCapabilities

`flow/nodes/datasource/wfs.py` keeps the `WebFeatureService` by `(url, version)`
in a process cache: TTL `WFS_CAPABILITIES_TTL_S` (default 3600 s; 0 turns it off),
a cap of 64 entries, `threading.Lock` (the node runs in `asyncio.to_thread`). The
construction happens outside the lock — holding the lock for up to 60 s would block every
WFS node of the process because of one slow server. When the requested layer is not
in the cached object, the node redoes the GetCapabilities **once** before reporting
"not found" (a layer published minutes ago must not become a false
negative). A `getfeature` failure does not invalidate the cache. The log says
"WFS capabilities: cache" or "rede em N ms" (network in N ms).

## Configuration

| Variable | Default | Where | Effect |
|---|---|---|---|
| `FONTES_CATALOGO_DIR` | `catalogo/geoservicos` | API | Folder imported at startup; empty (`FONTES_CATALOGO_DIR=`) or nonexistent = no import |
| `FONTES_APRENDER_DAS_EXECUCOES` | `true` | API | The consumer's `fontes` phase |
| `FONTES_VERIFICACAO_INTERVAL` | `86400` | API | Interval of the per-endpoint verification, in seconds; 0 turns off all probing initiated by the server |
| `WFS_CAPABILITIES_TTL_S` | `3600` | Executor | Cache of the WFS node's GetCapabilities; 0 turns it off |

## Tests

- `tests/unit/test_fontes_vault.py` — parser, with real fixtures (FUNAI, IBGE in
  1.0.0, ArcGIS and placeholder ignored, new format with frontmatter/tags/synonyms).
- `tests/unit/test_fontes_service.py` — URL/key/search, capabilities parsers
  (1.0/1.1/2.0) and XSD, translation of network errors, upsert, search scope and
  order, checking, learning, verification, idempotent import.
- `tests/unit/test_mcp_fontes.py` — the four tools, parity with `GUARDAS`,
  `probe` bucket, `open_world`.
- `tests/unit/test_fontes_catalogo.py` — import at startup (flag, lock,
  synonyms, zero writes on the second startup), per-endpoint verification (only the
  pending ones, isolated failure, parallelism 2) and the loop; the Redis lock and the loop
  shared by all background tasks, in `tests/unit/test_tarefas_de_fundo.py`.
- `tests/unit/test_validate_service.py`, `test_consumer_aprende_fontes.py`,
  `test_wfs_node.py`, `test_nodes_router_wfs_layers.py`, `test_mcp_catalogo.py`,
  `test_mcp_guia.py`, `test_mcp_prompts.py`, `test_mcp_servidor.py`,
  `test_docs_mcp.py`, `test_assistente_superficie.py`, `test_assistente_service.py`.

## What is left for phase 2

- **The interface.** The catalog does not appear in the UI in this phase. The previewer of the
  proposal ("Fontes" (Sources) tab in the editor, source record card, state badge on the WFS node)
  remains as a reference: https://claude.ai/artifact/ENuwsPVJCGWVRTpZ8rnm14.
- **`version` in the WFS node.** The catalog stores `propriedades.version` (IBGE =
  1.0.0), but `describe_source` does not put it in the `node_snippet` while the node does not
  declare it — IBGE's GeoServer answers to both versions, and per-endpoint
  verification confirms with its own GetCapabilities 2.0.0.
- **ArcGIS REST** (~34.5 thousand layers in the folders ignored today): `tipo="arcgis_rest"`,
  node `HttpRequest`.
- A trigram index on `busca` if the catalog grows far beyond the seed.
