# Known pitfalls

Almost every defect on this platform is silent: the workflow finishes green and the
data is wrong. The list below is what has already bitten, with the reason.

## Execution

- **Pin on an output node suppresses the write.** Pin mode returns the saved
  result instead of executing the node. On an output node this means nothing is
  written, no e-mail goes out — and the run reports success, with the
  `rowsInserted` of the run in which it was pinned. Pin is for an EXPENSIVE node
  upstream, never for a terminal node.
- **`HttpRequest` 4xx and 5xx count as success.** There is no
  `raise_for_status`: a 401 becomes normal output and the workflow moves on. If the workflow
  depends on the response, put a `Conditional` on `status_code` right after it.
- **A binary `HttpRequest` response becomes text.** The body goes through
  `response.json()` and falls back to `response.text`. A ZIP or a shapefile is
  decoded as an unrecoverable string.
- **There is no raster support.** The engine works with vector data. A request that involves
  satellite imagery or an elevation model has no possible workflow here — say
  so instead of building one that does not run.
- **A download URL lasts 5 minutes.** The presigned URLs for artifacts and for
  Drive files expire quickly; use them right away, do not store them. Content
  that stayed on the executor (`content_location: "executor"`) has no remote
  download at all.

## Validation

- **Validation and execution are not the same thing.** Validation simulates: it resolves
  each node's schema and walks the graph without writing a row or sending an e-mail. The
  only external access is the one by `DatabaseSpatialQuery`, which opens a connection to
  discover the columns. A `WFS` node is NOT probed: a wrong URL passes. What
  validation does is check the catalog — `unknown_source` (a source nobody
  cataloged) and `failing_source` (a source that failed its last check) are
  warnings; see the `sources` topic.
- **The report comes back whole.** A nonexistent node name does not stop the
  check of the rest: it goes in as `unknown_node` in `report.errors[]` along
  with everything else. The codes that bring the definition down are `unknown_node`,
  `duplicate_node_id`, `cycle`, `invalid_credential_id` and `construction_error`
  — in that case the tool returns the `validation` error with the `report` attached, and nothing
  is saved. Fix everything and revalidate just once.
- **`schema_source` says where each node's schema came from.** `static` (from the
  catalog), `simulated` (the node ran the simulation), `declared` (inferred from the
  definition: `output_vars` of `PythonScript`, `rules`/`fallback_output` of
  `Switch`, `ports` of `SubWorkflowInput`) or `unknown` (a dynamic-output node
  with nothing declarable — empty schema, but the node stays in the response). `unknown`
  is not a failure; it means "only known at execution time".
- **`disabled_nodes` and `subworkflow_errors` can come back `null`.** That is not an empty
  list: it means "not checked". Without `workspace_id` validation does not open a database
  session, so there is no way to know whether a node is disabled on the installation
  or whether the referenced sub-workflow exists. Provide `workspace_id` when the
  workflow has a sub-workflow or a credential — `report.hints` asks for it.
- **Reserved keys.** When iterating the schemas by `node_id`, skip every key
  that starts with `__` (`__report__`, `__edge_diagnostics__` and whatever comes next).

## Structure

- **An invented property disappears.** It does not become an execution error: the node discards it and
  runs with the default. Validation flags it as an `undeclared_property` warning —
  read the warnings.
- **A nonexistent `from_key` does not bring down the run**, it only omits the port. The check is
  static: `edge_from_key_unknown`.
- **An edge without a key leaving a node with several outputs** spreads everything, and the child
  ends up depending on the order of the parent's keys: `edge_spread_ambiguous`.
- **`fallback_output: ""` on `Switch`** emits the `''` port, which no edge
  can name — the wiring from it is dead. An absent key falls back to the
  default; a present but empty key does not.
- **An `object` property written as unreadable text** (`rules` of `Switch`,
  `queryParams`, `headers`) fails parameter validation before the node
  executes: `invalid_json_property`.
