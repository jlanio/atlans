# SQL

The `DatabaseQuery` and `DatabaseSpatialQuery` nodes take the query in `query` and
the values in `queryParams`. The credential goes in through `credential_id` — never the
connection string (see the `credentials` topic).

```json
{ "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
  "properties": {
    "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05",
    "query": "SELECT id, nome, geom FROM lotes WHERE bairro = :bairro AND area > :minima",
    "queryParams": { "bairro": "{{ inputs.bairro }}", "minima": 500 },
    "geometryColumn": "geom",
    "crs": "EPSG:4326"
  } }
```

`:placeholder` is the safe path: the value becomes a bind, not concatenated text.
Interpolating with Jinja directly in the SQL also works, but it builds the query by
concatenation — prefer the bind.

`:nome` inside a string or an SQL comment is **not** treated as a
placeholder, so `WHERE obs = 'as :10 horas'` does not become any parameter.

`queryParams` is rendered with Jinja before the bind and preserves the TYPE when the
value is a single expression: `{{ inputs.minima }}` with 500 delivers the integer 500.

Two operational notes:

- `timeout` (seconds) exists in both nodes and is worth tuning for a heavy
  query; the default is 120.
- `DatabaseSpatialQuery` declares a dynamic output AND implements simulation: it
  **connects to the credential's database during validation** to discover the
  columns. It writes nothing, but it opens a connection — that is why the shared
  credential only enters the validation scope from the `operator` role up.
