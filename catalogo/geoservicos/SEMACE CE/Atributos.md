# SEMACE CE — atributos das camadas

Geoportal: [[Geosserviços/SEMACE CE/Superintendência Estadual do Meio Ambiente do Ceará — SEMACE|Superintendência Estadual do Meio Ambiente do Ceará — SEMACE]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## SEMACECE (5)

### `SEMACECE:auto_infracao_20122018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `auto` | `xsd:string` | true | 0..1 |
| `cpf_cnpj` | `xsd:long` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `infracao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `data_lavra` | `xsd:string` | true | 0..1 |
| `valor` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `n` | `xsd:string` | true | 0..1 |
| `e` | `xsd:string` | true | 0..1 |
| `fundamenta` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `SEMACECE:auto_infracao_20192023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `auto` | `xsd:string` | true | 0..1 |
| `cpf_cnpj` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `infracao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `data_lavra` | `xsd:string` | true | 0..1 |
| `valor` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `n` | `xsd:int` | true | 0..1 |
| `e` | `xsd:int` | true | 0..1 |
| `fundamenta` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `SEMACECE:tcrda_semace_2017_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `num_tcrda` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `cnpj_cpf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `n` | `xsd:int` | true | 0..1 |
| `e` | `xsd:int` | true | 0..1 |
| `area_ha` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `SEMACECE:termo_embargo_poligono_20122023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `termo` | `xsd:string` | true | 0..1 |
| `auto` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `n` | `xsd:string` | true | 0..1 |
| `e` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SEMACECE:termos_20122023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `termo` | `xsd:string` | true | 0..1 |
| `auto` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `geometria` | `xsd:string` | true | 0..1 |
| `n` | `xsd:int` | true | 0..1 |
| `e` | `xsd:int` | true | 0..1 |
| `area_ha` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |
