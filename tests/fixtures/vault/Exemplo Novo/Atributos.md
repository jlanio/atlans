# EXEMPLO — atributos das camadas

Geoportal: [[Geosserviços/Exemplo Novo/Serviço de Exemplo — EXEMPLO|Serviço de Exemplo — EXEMPLO]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## queimadas (2)

### `queimadas:focos_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `data_hora_gmt` | `xsd:dateTime` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |

### `queimadas:risco_fogo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `risco` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
