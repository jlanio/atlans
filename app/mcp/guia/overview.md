# The definition format

A workflow is a graph: `nodes` that do something and `edges` that carry the
data from one to the other. What is here was read from the executor and from the
server's schemas, not from documentation. Where there is a pitfall, it comes with the reason.

```json
{
  "nodes": [
    { "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
      "properties": { "query": "SELECT ...", "credential_id": "uuid" },
      "position": { "x": 0, "y": 0 } }
  ],
  "edges": [
    { "source": "n1", "target": "n2", "from_key": "output", "to_key": "camada" }
  ],
  "viewport": { "x": 0, "y": 0, "zoom": 1 }
}
```

- `id` is free-form; it only needs to be unique within the workflow. Two nodes with the same id
  are not a warning: the executor would build `{id: nó}` and the last one would win, so
  validation rejects the whole definition (`duplicate_node_id`).
- `name` has to match the catalog's `name` EXACTLY (`search_nodes`).
  A wrong name is rejected with the code `unknown_node` — together with everything else
  that is wrong, in a single report.
- `type` is the node's group in the catalog (`trigger`, `datasource`, `spatial`,
  `control`, `action`, `output`). Copy what `describe_node` returns: that is how
  the server knows which nodes read run parameters (see `inputs`).
- `position` does not affect execution, but without it the nodes pile up in the corner of the
  editor. Use a grid: 320 px horizontally, 180 vertically.

## The report comes whole, all at once

`validate_workflow` runs a static lint before simulating, and it is
CUMULATIVE: a wrong name does not stop the checking of the other nodes. What
comes back is `report.errors[]` and `report.warnings[]`, each item with
`{code, severity, node_id, edge, message}`.

Five codes bring down the definition (the tool returns the `validation` error with the
`report` attached, and nothing is saved):

| `code` | What it is |
|---|---|
| `unknown_node` | a `name` that does not exist in the catalog |
| `duplicate_node_id` | two nodes with the same `id` |
| `cycle` | the graph loops back on itself |
| `invalid_credential_id` | a `credential_id` that is not a UUID |
| `construction_error` | the executor could not build the workflow |

The other codes (invalid alias, undeclared property, orphan edge, unreachable
node, unknown `from_key`) come as an error or a warning in the same
report, without preventing the rest from being read. `report.ok` is `false` whenever there is
any error; a warning does not bring it down.

Fix everything the report pointed out and validate again — not one thing per
round.

## `properties` × `parameters`

The saved definition uses **`properties`**. The tools accept both names as
synonyms (on conflict, `parameters` wins), and always save `properties`.
Write `properties` and don't think about it again.

## Only what is declared survives

`BaseNode.validate()` REBUILDS the node's parameters from the properties
declared in the catalog and **discards every key that is not there**. An
invented property does not become an execution error: it disappears, and the node runs
with the default.

Practical consequence: check the name of each property with
`describe_node` before writing — `name` accepts a list (up to 8 per
call), so ask for the sheets of all the workflow's nodes in a single call. A `timeOut` in place of `timeout` is
silently ignored — in validation it shows up as the warning
`undeclared_property`, which is easy to read and easy to ignore. Don't ignore it.
