# PGGM — atributos das camadas

Geoportal: [[Geosserviços/PGGM/Programa de Geologia e Geofísica Marinha — PGGM|Programa de Geologia e Geofísica Marinha — PGGM]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## PGGM (6)

### `PGGM:bioclasticos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `inpoly_fid` | `xsd:long` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PGGM:cascalhos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inpoly_fid` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PGGM:cascalhos_bioclasticos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `fid_raster` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `inpoly_fid` | `xsd:long` | true | 0..1 |
| `fid_rast_1` | `xsd:long` | true | 0..1 |
| `id_1` | `xsd:long` | true | 0..1 |
| `gridcode_1` | `xsd:long` | true | 0..1 |
| `inpoly_f_1` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PGGM:vulnerabilidade_costeira_erosao_regiao_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `length` | `xsd:double` | true | 0..1 |
| `vc` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `PGGM:vulnerabilidade_costeira_estabilidade_regiao_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `length` | `xsd:double` | true | 0..1 |
| `vc` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `PGGM:vulnerabilidade_costeira_progradacao_regiao_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `length` | `xsd:double` | true | 0..1 |
| `vc` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
