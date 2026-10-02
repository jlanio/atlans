# IBGE — atributos das camadas

Geoportal: [[Geosserviços/IBGE/Instituto Brasileiro de Geografia e Estatística — IBGE|Instituto Brasileiro de Geografia e Estatística — IBGE]]

Os campos abaixo vêm do `DescribeFeatureType` (XSD), sem download de feições. `gml:*` geralmente identifica a geometria.

## APONDS (2)

### `APONDS:aponds_ibge`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cd_mun` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `cd_apond` | `xsd:string` | true | 0..1 |
| `status` | `xsd:int` | true | 0..1 |
| `cor` | `xsd:string` | true | 0..1 |
| `dpoa` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geom_ibge` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `APONDS:aponds_prefeitura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cd_mun` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `cd_apond` | `xsd:string` | true | 0..1 |
| `status` | `xsd:int` | true | 0..1 |
| `cor` | `xsd:string` | true | 0..1 |
| `dpoa` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geom_prefeitura` | `gml:MultiPolygonPropertyType` | true | 0..1 |
