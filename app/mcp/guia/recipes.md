# Receitas

Cinco definições completas que passam na validação. Copie, troque os ids de
arquivo, credencial e sub-fluxo pelos seus (`list_drive_files`,
`list_credentials`, `list_workflows`) e valide antes de gravar.

Os UUIDs abaixo são exemplos. Credencial entra SEMPRE por `credential_id` —
nunca a string de conexão.

## 1. Arquivo do Drive → Buffer → GeoJSON

A espinha mais comum: uma camada do Drive, uma transformação, um arquivo de
saída.

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

`from_key: "output"` é obrigatório na primeira aresta: o `DataInput` tem duas
saídas (`output` e `metadata`) e sem a chave as duas espalhariam para o
`Buffer`.

## 2. Webhook → filtro → resposta HTTP

Fluxo síncrono: quem chama o webhook recebe o resultado no corpo da resposta.

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

Com `payloadField` vazio, o corpo do POST já é o `inputs` do gatilho. O
`bodyField: "output"` casa com o `from_key` da última aresta: o valor chega ao
`Response` sob o nome `output`.

## 3. PostGIS → Dissolve → publicar no mapa

Consulta espacial parametrizada, agregação por coluna e publicação no portal
do fluxo.

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

O gatilho está aqui por causa do parâmetro: `inputs` só são os valores de quem
executa DENTRO de um nó `type: "trigger"`. Do gatilho para a frente, o valor é
referenciado pelo alias — daí `$Chamada.output.municipio` no `queryParams`, que
vira bind de `:municipio` e preserva o tipo.

## 4. Sub-fluxo: filho e pai

O filho declara o próprio contrato de entrada e de saída; o pai o chama pelo
`id_hash`.

**Filho** — grave primeiro e guarde o `id` que a criação devolve:

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

**Pai** — `workflowHash` é o `id` do filho; `inputsMapping` liga
`{porta do filho: chave que chega ao nó}`:

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

Cada porta declarada no `SubWorkflowInput` vira uma saída nomeada do gatilho,
e a aresta que sai dela leva `from_key` com o nome da porta — é assim que o
filho escolhe o que passar adiante. No `SubWorkflowOutput`, ao contrário, cada
aresta que chega precisa de `to_key` distinto: é o nome da porta de saída do
sub-fluxo. Chave fora das `ports` é descartada nas duas pontas.

## 5. Fonte catalogada (WFS) filtrada no servidor → publicar no mapa

`url` e `typeName` vieram de `describe_source(...).node_snippet`, nunca de
cabeça (tópico `sources`); `sortBy` pagina a camada no GeoServer e o filtro
por atributo (`cqlFilter`) roda no servidor, antes da paginação. Se o servidor
não aplicar CQL (o nó falha dizendo isso), tire o `cqlFilter` e ponha um
`AttributeFilter` depois da leitura.

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
