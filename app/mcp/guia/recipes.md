# Recipes

Five complete definitions that pass validation. Copy them, swap the file,
credential and sub-workflow ids for your own (`list_drive_files`,
`list_credentials`, `list_workflows`) and validate before saving.

The UUIDs below are examples. A credential ALWAYS goes in through `credential_id` —
never the connection string.

## 1. Drive file → Buffer → GeoJSON

The most common backbone: one layer from the Drive, one transformation, one output
file.

```json
{
  "nodes": [
    { "id": "fonte", "name": "DataInput", "type": "datasource", "alias": "Lotes",
      "properties": { "context": "drive", "driveFileId": "9c1f4b7a-2d55-4e90-8a31-6b0c7e4f2a18", "crs": "EPSG:4326" },
      "position": { "x": 0, "y": 0 } },
    { "id": "faixa", "name": "Buffer", "type": "spatial", "alias": "Faixa",
      "properties": { "distance": 50, "distanceUnit": "meters", "capStyle": "round", "joinStyle": "round", "quadSegs": 8 },
      "position": { "x": 320, "y": 0 } },
    { "id": "saida", "name": "SaveGeoJSON", "type": "output",
      "properties": { "label": "faixa_50m", "outputPath": "", "crs": "EPSG:4326" },
      "position": { "x": 640, "y": 0 } }
  ],
  "edges": [
    { "source": "fonte", "target": "faixa", "from_key": "output" },
    { "source": "faixa", "target": "saida", "from_key": "output" }
  ]
}
```

`from_key: "output"` is required on the first edge: `DataInput` has two
outputs (`output` and `metadata`) and without the key both would spread into the
`Buffer`.

## 2. Webhook → filter → HTTP response

A synchronous workflow: whoever calls the webhook gets the result in the response body.

```json
{
  "nodes": [
    { "id": "entrada", "name": "WebhookTrigger", "type": "trigger", "alias": "Chamada",
      "properties": { "payloadField": "", "payload_schema": {} },
      "position": { "x": 0, "y": 0 } },
    { "id": "filtro", "name": "AttributeFilter", "type": "action", "alias": "Ativos",
      "properties": { "attributeName": "situacao", "operator": "==", "compareTo": "ativo" },
      "position": { "x": 320, "y": 0 } },
    { "id": "resposta", "name": "Response", "type": "output",
      "properties": { "statusCode": "200", "contentType": "application/json", "bodyMode": "field", "bodyField": "output", "headers": {} },
      "position": { "x": 640, "y": 0 } }
  ],
  "edges": [
    { "source": "entrada", "target": "filtro", "from_key": "output" },
    { "source": "filtro", "target": "resposta", "from_key": "output" }
  ]
}
```

With an empty `payloadField`, the POST body is already the trigger's `inputs`. The
`bodyField: "output"` matches the `from_key` of the last edge: the value reaches the
`Response` under the name `output`.

## 3. PostGIS → Dissolve → publish to the map

A parameterized spatial query, aggregation by column and publication on the
workflow's portal.

```json
{
  "nodes": [
    { "id": "entrada", "name": "WebhookTrigger", "type": "trigger", "alias": "Chamada",
      "properties": { "payloadField": "", "payload_schema": {} },
      "position": { "x": 0, "y": 0 } },
    { "id": "consulta", "name": "DatabaseSpatialQuery", "type": "datasource", "alias": "Focos",
      "properties": {
        "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05",
        "query": "SELECT bairro, area_ha, geom FROM focos WHERE municipio = :municipio",
        "queryParams": { "municipio": "{{ $Chamada.output.municipio }}" },
        "geometryColumn": "geom",
        "crs": "EPSG:4326",
        "timeout": 120
      },
      "position": { "x": 320, "y": 0 } },
    { "id": "agrupa", "name": "Dissolve", "type": "spatial", "alias": "PorBairro",
      "properties": { "byColumn": "bairro", "aggFunc": "sum" },
      "position": { "x": 640, "y": 0 } },
    { "id": "mapa", "name": "PublishMap", "type": "output",
      "properties": { "title": "Focos por bairro", "color": "#d97706", "opacity": 0.6, "visible_fields": "bairro,area_ha", "crs": "EPSG:4326" },
      "position": { "x": 960, "y": 0 } }
  ],
  "edges": [
    { "source": "entrada", "target": "consulta", "from_key": "output" },
    { "source": "consulta", "target": "agrupa", "from_key": "output" },
    { "source": "agrupa", "target": "mapa", "from_key": "output" }
  ]
}
```

The trigger is here because of the parameter: `inputs` are the values of whoever
runs the workflow only INSIDE a `type: "trigger"` node. From the trigger onward, the value is
referenced by the alias — hence `$Chamada.output.municipio` in `queryParams`, which
becomes a bind of `:municipio` and preserves the type.

## 4. Sub-workflow: child and parent

The child declares its own input and output contract; the parent calls it by its
`id_hash`.

**Child** — save it first and keep the `id` that the creation returns:

```json
{
  "nodes": [
    { "id": "entrada", "name": "SubWorkflowInput", "type": "trigger", "alias": "Contrato",
      "properties": { "ports": ["focos"] },
      "position": { "x": 0, "y": 0 } },
    { "id": "faixa", "name": "Buffer", "type": "spatial", "alias": "Faixa",
      "properties": { "distance": 250, "distanceUnit": "meters" },
      "position": { "x": 320, "y": 0 } },
    { "id": "saida", "name": "SubWorkflowOutput", "type": "output",
      "properties": { "ports": ["faixa_de_risco"] },
      "position": { "x": 640, "y": 0 } }
  ],
  "edges": [
    { "source": "entrada", "target": "faixa", "from_key": "focos" },
    { "source": "faixa", "target": "saida", "from_key": "output", "to_key": "faixa_de_risco" }
  ]
}
```

**Parent** — `workflowHash` is the child's `id`; `inputsMapping` maps
`{porta do filho: chave que chega ao nó}` (child's port: key that
arrives at the node):

```json
{
  "nodes": [
    { "id": "entrada", "name": "WebhookTrigger", "type": "trigger", "alias": "Chamada",
      "properties": { "payloadField": "", "payload_schema": {} },
      "position": { "x": 0, "y": 0 } },
    { "id": "filho", "name": "SubWorkflow", "type": "control", "alias": "Risco",
      "properties": { "workflowHash": "b7d41e62-08fa-4c13-9f77-5a2c9e10d834", "inputsMapping": { "focos": "output" }, "timeoutSeconds": 300 },
      "position": { "x": 320, "y": 0 } },
    { "id": "saida", "name": "SaveGeoJSON", "type": "output",
      "properties": { "label": "faixa_de_risco", "outputPath": "", "crs": "EPSG:4326" },
      "position": { "x": 640, "y": 0 } }
  ],
  "edges": [
    { "source": "entrada", "target": "filho", "from_key": "output" },
    { "source": "filho", "target": "saida", "from_key": "subWorkflowResult" }
  ]
}
```

Each port declared in `SubWorkflowInput` becomes a named output of the trigger,
and the edge leaving it carries a `from_key` with the port's name — that is how the
child chooses what to pass along. In `SubWorkflowOutput`, conversely, each
incoming edge needs a distinct `to_key`: it is the name of the sub-workflow's
output port. A key outside the `ports` is discarded at both ends.

## 5. Cataloged source (WFS) filtered on the server → publish to the map

`url` and `typeName` came from `describe_source(...).node_snippet`, never from
memory (topic `sources`); `sortBy` pages the layer on the GeoServer and the
attribute filter (`cqlFilter`) runs on the server, before pagination. If the server
does not apply CQL (the node fails saying so), remove the `cqlFilter` and put an
`AttributeFilter` after the read.

```json
{
  "nodes": [
    { "id": "fonte", "name": "WFS", "type": "datasource", "alias": "TIs_MT",
      "properties": { "url": "https://geoserver.funai.gov.br/geoserver/ows", "typeName": "Funai:tis_poligonais",
                      "maxFeatures": 5000, "cqlFilter": "uf_sigla = 'MT'", "crs": "EPSG:4326", "sortBy": "gid" },
      "position": { "x": 0, "y": 0 } },
    { "id": "mapa", "name": "PublishMap", "type": "output",
      "properties": { "title": "Terras indígenas — MT", "color": "#d97706", "opacity": 0.6, "visible_fields": "terrai_nome,fase_ti", "crs": "EPSG:4326" },
      "position": { "x": 320, "y": 0 } }
  ],
  "edges": [
    { "source": "fonte", "target": "mapa", "from_key": "output" }
  ]
}
```
