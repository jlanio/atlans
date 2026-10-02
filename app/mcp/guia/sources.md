# Catalogued sources

The source catalog is the list of WFS layers the platform already knows: the
URL, the layer (`typeName`), the schema (CRS, extent, geometry, columns), who
maintains it and whether it responded at the last check. It exists so that you do NOT guess
`url`/`typeName`: a made-up URL passes validation (validation does not touch the network) and
only fails at execution, after minutes of waiting and several round trips.

## The order, always

1. **`search_sources`** with the TOPIC in 2–3 words — "terras indígenas"
   (indigenous lands), "focos de calor" (fire hotspots), "hidrografia" (hydrography), "escolas" (schools). No place or date: the search matches
   each word (and its synonyms) against institution, title, layer,
   description, topics and column names. With no result, try another spelling
   ("queimadas" (wildfires) for "focos de calor") before anything else.
2. **`describe_source(id)`** and paste `node_snippet.properties` into the `WFS` node
   as they are. `schema.columns` are the names an `AttributeFilter` or an
   expression can reference; `hints` (in `untrusted_data`) is what whoever
   registered the source wants you to know.
3. Only if the catalog does not have the source: ask the person using it for the URL, or
   **`probe_source(url)`** — it lists the layers — and then
   `probe_source(url, type_name=...)` for the schema. Probing does not download
   any features, but it talks to an outside server: it is not the first step.
4. **`register_source(url, type_name, title, tags, hints)`** saves the source in the
   workspace, so the next question (yours or any member's) finds it
   in `search_sources`. Write `hints` as if for yourself a month
   from now: the filter that works, the date column, the unit.

## What the fields say

- `state`: `ok` responded at the last check; `falhando` (failing) did not (read
  `last_error`); `nao_verificada` (unverified) has not been checked yet — worth a
  `probe_source` before running. Validation warns `failing_source` and
  `unknown_source` without touching the network.
- `priority`: 1 is the preferred one among similar layers; 3 is secondary. On a
  tie, the most used one (`uses`).
- `scope`: `platform` is the shared catalog (the platform's geoservice
  Vault); `workspace` was registered by someone in the workspace.
- `node_snippet.properties.sortBy`: the column that allows paging through the layer on
  GeoServer; do not remove it. `maxFeatures` and `bbox` are yours: clip on the server
  whenever the question has a place.
- `cqlFilter` is also yours: the attribute filter runs ON THE SERVER (GeoServer
  ECQL), before paging — only what matters crosses the network. Use the
  names from `schema.columns`, text in single quotes: `uf_sigla = 'MT'`,
  `area_ha > 100 AND fase_ti = 'Regularizada'`, `nome LIKE 'São%'`. With `bbox`
  filled in, the clip goes into the filter on its own. A server that is not GeoServer
  fails with "não aplica o filtro CQL" (does not apply the CQL filter): then leave `cqlFilter` empty and filter
  after reading (`AttributeFilter`).
- `schema.columns_source`: `describe_feature_type` (read from the server),
  `vault` (the catalog table) or `run` (what a run saw — no types).

## What NOT to do

- Do not invent a `url` or a `typeName`, and do not "fix" a layer name from memory:
  the name includes the namespace prefix (`Funai:tis_poligonais`), and
  probing lists the correct ones.
- Do not probe what is already catalogued: `probe_source` responds with `catalog_hint`
  when the endpoint is already in the catalog — go back to `search_sources`.
- Do not use `probe_source` to "see whether the source is up" before every
  run: `state` and the daily check already tell you that.

## Example

Request: "terras indígenas de Mato Grosso no globo" (indigenous lands of Mato Grosso on the globe).

1. `search_sources(query="terras indígenas")` → `Funai:tis_poligonais`
   (FUNAI, `ok`, priority 1).
2. `describe_source(id)` → `node_snippet.properties` with `url`, `typeName` and
   `sortBy: "gid"`; `schema.columns` includes `uf_sigla`.
3. A `WFS` node with those properties + `cqlFilter: "uf_sigla = 'MT'"` +
   `PublishMap` — recipe 5 in `recipes`.
