# VALEC — atributos das camadas

Geoportal: [[Geosserviços/VALEC/Engenharia, Construções e Ferrovias S.A. — VALEC|Engenharia, Construções e Ferrovias S.A. — VALEC]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## VALEC (3)

### `VALEC:area_utilidade_publica_fico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `VALEC:area_utilidade_publica_fiol_ii_iii`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `VALEC:trecho_ferroviario_infrasa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `empreendim` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `subconcess` | `xsd:string` | true | 0..1 |
| `ext` | `xsd:double` | true | 0..1 |
| `bitola` | `xsd:string` | true | 0..1 |
| `label` | `xsd:string` | true | 0..1 |
| `participac` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
